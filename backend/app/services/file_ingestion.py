"""File ingestion service for processing uploaded files and folders."""

import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.shared_source import SharedSource
from app.utils.file_filter import (
    read_file_content,
    scan_directory,
    is_allowed_extension,
    is_file_too_large,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

CONTENT_BUDGET_TOTAL = 200_000
CONTENT_BUDGET_PER_FILE = 50_000
CONTENT_BUDGET_PER_FOLDER_FILE = 20_000
MAX_FILES_PER_FOLDER = 50


class FileIngestionService:
    """Service for processing files and folders."""

    async def save_uploaded_file(
        self,
        session: AsyncSession,
        room_id: str,
        filename: str,
        content: bytes,
    ) -> SharedSource | None:
        """Save an uploaded file and create a SharedSource.

        Args:
            session: Database session
            room_id: Room ID
            filename: Original filename
            content: File content bytes

        Returns:
            Created SharedSource or None if file rejected
        """
        if not is_allowed_extension(filename):
            logger.warning("Rejected file: invalid extension", filename=filename)
            return None

        if is_file_too_large(len(content)):
            logger.warning("Rejected file: too large", filename=filename, size=len(content))
            return None

        file_id = str(uuid.uuid4())
        ext = Path(filename).suffix
        saved_name = f"{file_id}{ext}"
        file_path = UPLOAD_DIR / saved_name

        file_path.write_bytes(content)

        source = SharedSource(
            id=file_id,
            room_id=room_id,
            source_type="file",
            path=str(file_path),
            content=filename,  # Original filename stored in content field
            file_count=1,
        )
        session.add(source)
        await session.flush()

        logger.info("Saved uploaded file", source_id=file_id, filename=filename)
        return source

    async def add_folder_source(
        self,
        session: AsyncSession,
        room_id: str,
        folder_path: str,
    ) -> SharedSource | None:
        """Add a folder as a shared source.

        Args:
            session: Database session
            room_id: Room ID
            folder_path: Path to folder

        Returns:
            Created SharedSource or None if folder invalid
        """
        path = Path(folder_path)
        if not path.exists() or not path.is_dir():
            logger.warning("Invalid folder path", path=folder_path)
            return None

        try:
            files = scan_directory(folder_path)
        except Exception as e:
            logger.error("Failed to scan folder", path=folder_path, error=str(e))
            return None

        source = SharedSource(
            id=str(uuid.uuid4()),
            room_id=room_id,
            source_type="folder",
            path=folder_path,
            file_count=len(files),
        )
        session.add(source)
        await session.flush()

        logger.info("Added folder source", source_id=source.id, path=folder_path, file_count=len(files))
        return source

    async def add_text_source(
        self,
        session: AsyncSession,
        room_id: str,
        text_content: str,
    ) -> SharedSource:
        """Add pasted text as a shared source.

        Args:
            session: Database session
            room_id: Room ID
            text_content: Pasted text content

        Returns:
            Created SharedSource
        """
        source = SharedSource(
            id=str(uuid.uuid4()),
            room_id=room_id,
            source_type="text",
            content=text_content,
            file_count=0,
        )
        session.add(source)
        await session.flush()

        logger.info("Added text source", source_id=source.id, length=len(text_content))
        return source

    async def get_room_sources(
        self, session: AsyncSession, room_id: str
    ) -> list[SharedSource]:
        """Get all sources for a room.

        Args:
            session: Database session
            room_id: Room ID

        Returns:
            List of shared sources
        """
        result = await session.execute(
            select(SharedSource)
            .where(SharedSource.room_id == room_id)
            .order_by(SharedSource.created_at)
        )
        return list(result.scalars().all())

    async def delete_source(
        self, session: AsyncSession, source_id: str
    ) -> bool:
        """Delete a shared source.

        Args:
            session: Database session
            source_id: Source ID

        Returns:
            True if deleted, False if not found
        """
        result = await session.execute(
            select(SharedSource).where(SharedSource.id == source_id)
        )
        source = result.scalar_one_or_none()
        if not source:
            return False

        if source.source_type == "file" and source.path:
            try:
                Path(source.path).unlink(missing_ok=True)
            except OSError:
                pass

        await session.delete(source)
        await session.flush()

        logger.info("Deleted source", source_id=source_id)
        return True

    def get_file_content_for_room(self, sources: list[SharedSource]) -> str:
        """Get aggregated file content for a room's sources.

        Args:
            sources: List of shared sources

        Returns:
            Aggregated content string (truncated to CONTENT_BUDGET_TOTAL)
        """
        parts = []
        total_chars = 0

        for source in sources:
            if total_chars >= CONTENT_BUDGET_TOTAL:
                parts.append("\n... [content budget exhausted]")
                break

            if source.source_type == "file" and source.path:
                content = read_file_content(source.path, max_chars=CONTENT_BUDGET_PER_FILE)
                if content:
                    header = f"\n{'='*60}\nFILE: {source.content or source.path}\n{'='*60}\n"
                    parts.append(header + content)
                    total_chars += len(content)

            elif source.source_type == "folder" and source.path:
                try:
                    files = scan_directory(source.path)
                    for f in files[:MAX_FILES_PER_FOLDER]:
                        if total_chars >= CONTENT_BUDGET_TOTAL:
                            break
                        content = read_file_content(f["path"], max_chars=CONTENT_BUDGET_PER_FOLDER_FILE)
                        if content:
                            header = f"\n{'='*60}\nFILE: {f['relative_path']}\n{'='*60}\n"
                            parts.append(header + content)
                            total_chars += len(content)
                except Exception as e:
                    parts.append(f"\n[Error scanning folder: {e}]")

            elif source.source_type == "text" and source.content:
                remaining = CONTENT_BUDGET_TOTAL - total_chars
                text = source.content[:remaining]
                parts.append(f"\n{'='*60}\nPASTED TEXT\n{'='*60}\n{text}")
                total_chars += len(text)

        return "\n".join(parts)


file_ingestion_service = FileIngestionService()
