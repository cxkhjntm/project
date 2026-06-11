"""Tests for artifact writer service."""

import os
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.artifact_writer import ArtifactWriter


@pytest.fixture
def sample_messages():
    """Create sample message dicts for testing."""
    return [
        {
            "id": "msg-1",
            "sender_type": "orchestrator",
            "sender_id": None,
            "content": "Welcome to the discussion. Today we will plan the new API.",
            "round": 1,
            "created_at": datetime(2025, 1, 1, 10, 0, 0, tzinfo=UTC),
        },
        {
            "id": "msg-2",
            "sender_type": "expert",
            "sender_id": "role-architect",
            "content": "I recommend using a RESTful design with FastAPI.",
            "round": 1,
            "created_at": datetime(2025, 1, 1, 10, 1, 0, tzinfo=UTC),
        },
        {
            "id": "msg-3",
            "sender_type": "expert",
            "sender_id": "role-pm",
            "content": "We should focus on MVP scope first.",
            "round": 1,
            "created_at": datetime(2025, 1, 1, 10, 2, 0, tzinfo=UTC),
        },
        {
            "id": "msg-4",
            "sender_type": "orchestrator",
            "sender_id": None,
            "content": "Good points. Let's continue to the next round.",
            "round": 2,
            "created_at": datetime(2025, 1, 1, 10, 3, 0, tzinfo=UTC),
        },
        {
            "id": "msg-5",
            "sender_type": "expert",
            "sender_id": "role-architect",
            "content": "For the database layer, I suggest SQLAlchemy with async support.",
            "round": 2,
            "created_at": datetime(2025, 1, 1, 10, 4, 0, tzinfo=UTC),
        },
    ]


@pytest.fixture
def output_dir(tmp_path):
    """Provide a temporary output directory."""
    return str(tmp_path / "test_output")


@pytest.fixture
def writer(db_session: AsyncSession):
    """Create an ArtifactWriter instance."""
    return ArtifactWriter(session=db_session)


class TestBuildMarkdownContent:
    """Tests for the _build_markdown_content method."""

    def test_build_markdown_with_header_and_goal(self, writer, sample_messages):
        """Test markdown includes room name as title and goal."""
        markdown = writer._build_markdown_content(
            room_name="API Design Room",
            goal="Design the new REST API",
            messages=sample_messages,
        )

        assert "# API Design Room" in markdown
        assert "Design the new REST API" in markdown

    def test_build_markdown_groups_by_round(self, writer, sample_messages):
        """Test markdown groups messages by round number."""
        markdown = writer._build_markdown_content(
            room_name="Test Room",
            goal="Test goal",
            messages=sample_messages,
        )

        assert "Round 1" in markdown
        assert "Round 2" in markdown

    def test_build_markdown_includes_all_messages(self, writer, sample_messages):
        """Test markdown includes content from all messages."""
        markdown = writer._build_markdown_content(
            room_name="Test Room",
            goal="Test goal",
            messages=sample_messages,
        )

        assert "Welcome to the discussion" in markdown
        assert "RESTful design with FastAPI" in markdown
        assert "MVP scope first" in markdown
        assert "SQLAlchemy with async support" in markdown

    def test_build_markdown_labels_orchestrator(self, writer, sample_messages):
        """Test markdown labels orchestrator messages correctly."""
        markdown = writer._build_markdown_content(
            room_name="Test Room",
            goal="Test goal",
            messages=sample_messages,
        )

        assert "主持人" in markdown

    def test_build_markdown_labels_experts(self, writer, sample_messages):
        """Test markdown labels expert messages with sender_id."""
        markdown = writer._build_markdown_content(
            room_name="Test Room",
            goal="Test goal",
            messages=sample_messages,
        )

        assert "role-architect" in markdown
        assert "role-pm" in markdown

    def test_build_markdown_includes_timestamp(self, writer, sample_messages):
        """Test markdown includes generation timestamp."""
        markdown = writer._build_markdown_content(
            room_name="Test Room",
            goal="Test goal",
            messages=sample_messages,
        )

        assert "生成时间" in markdown


class TestGenerateArtifact:
    """Tests for the generate_artifact method."""

    async def test_creates_output_file(self, writer, sample_messages, output_dir, db_session):
        """Test that generate_artifact creates the output markdown file."""
        # Arrange - create room in DB
        from app.models.room import Room

        room = Room(
            id="room-1",
            name="Test Room",
            goal="Test goal",
            output_directory=output_dir,
        )
        db_session.add(room)
        await db_session.flush()

        # Create messages in DB
        from app.models.message import Message

        for msg in sample_messages:
            db_msg = Message(
                id=msg["id"],
                room_id="room-1",
                sender_type=msg["sender_type"],
                sender_id=msg["sender_id"],
                content=msg["content"],
                round=msg["round"],
            )
            db_session.add(db_msg)
        await db_session.flush()

        # Act
        artifact = await writer.generate_artifact(
            room_id="room-1",
            room_name="Test Room",
            goal="Test goal",
            messages=sample_messages,
            output_directory=output_dir,
        )

        # Assert
        assert os.path.isfile(artifact.file_path)
        with open(artifact.file_path, encoding="utf-8") as f:
            content = f.read()
        assert "Test Room" in content
        assert "Test goal" in content

    async def test_saves_database_record(self, writer, sample_messages, output_dir, db_session):
        """Test that generate_artifact saves an Artifact record to the database."""
        from app.models.room import Room

        room = Room(
            id="room-2",
            name="DB Test Room",
            goal="DB test goal",
            output_directory=output_dir,
        )
        db_session.add(room)
        await db_session.flush()

        artifact = await writer.generate_artifact(
            room_id="room-2",
            room_name="DB Test Room",
            goal="DB test goal",
            messages=sample_messages,
            output_directory=output_dir,
        )

        # Verify the returned artifact has DB fields
        assert artifact.id is not None
        assert artifact.room_id == "room-2"
        assert artifact.artifact_type == "markdown"
        assert artifact.title == "DB Test Room"
        assert artifact.file_path is not None

    async def test_returns_artifact_metadata(self, writer, sample_messages, output_dir, db_session):
        """Test that generate_artifact returns correct metadata."""
        from app.models.room import Room

        room = Room(
            id="room-3",
            name="Meta Test Room",
            goal="Meta test goal",
            output_directory=output_dir,
        )
        db_session.add(room)
        await db_session.flush()

        artifact = await writer.generate_artifact(
            room_id="room-3",
            room_name="Meta Test Room",
            goal="Meta test goal",
            messages=sample_messages,
            output_directory=output_dir,
        )

        assert artifact.artifact_type == "markdown"
        assert artifact.title == "Meta Test Room"
        assert artifact.summary is not None
        assert len(artifact.summary) > 0

    async def test_generates_unique_directory_per_run(
        self, writer, sample_messages, output_dir, db_session
    ):
        """Test that each artifact run creates a unique subdirectory."""
        from app.models.room import Room

        room = Room(
            id="room-4",
            name="Unique Dir Room",
            goal="Test unique dirs",
            output_directory=output_dir,
        )
        db_session.add(room)
        await db_session.flush()

        artifact = await writer.generate_artifact(
            room_id="room-4",
            room_name="Unique Dir Room",
            goal="Test unique dirs",
            messages=sample_messages,
            output_directory=output_dir,
        )

        # file_path should be inside a timestamped subdirectory
        assert output_dir in artifact.file_path
        assert artifact.file_path.endswith("final-plan.md")

    async def test_empty_messages_raises_error(self, writer, output_dir, db_session):
        """Test that generate_artifact raises ValueError for empty messages."""
        with pytest.raises(ValueError, match="No messages"):
            await writer.generate_artifact(
                room_id="room-empty",
                room_name="Empty Room",
                goal="No goal",
                messages=[],
                output_directory=output_dir,
            )

    async def test_file_contains_structured_content(
        self, writer, sample_messages, output_dir, db_session
    ):
        """Test that the generated file has proper Markdown structure."""
        from app.models.room import Room

        room = Room(
            id="room-5",
            name="Structure Test Room",
            goal="Structure test goal",
            output_directory=output_dir,
        )
        db_session.add(room)
        await db_session.flush()

        artifact = await writer.generate_artifact(
            room_id="room-5",
            room_name="Structure Test Room",
            goal="Structure test goal",
            messages=sample_messages,
            output_directory=output_dir,
        )

        with open(artifact.file_path, encoding="utf-8") as f:
            content = f.read()

        # Check Markdown structure
        assert "> 📋" in content  # Header annotation
        assert "## " in content  # Sections
        assert "---" in content  # Horizontal rules or metadata separators

    async def test_file_contains_discussion_synthesis(
        self, writer, sample_messages, output_dir, db_session
    ):
        """Test that generated content includes extracted conclusions from discussion messages."""
        from app.models.room import Room

        room = Room(
            id="room-synthesis",
            name="Synthesis Room",
            goal="Synthesize real discussion content",
            output_directory=output_dir,
        )
        db_session.add(room)
        await db_session.flush()

        artifact = await writer.generate_artifact(
            room_id="room-synthesis",
            room_name="Synthesis Room",
            goal="Synthesize real discussion content",
            messages=sample_messages,
            output_directory=output_dir,
        )

        with open(artifact.file_path, encoding="utf-8") as f:
            content = f.read()

        assert "## 4. 总体方案" in content
        assert "专家 (role-architect): I recommend using a RESTful design with FastAPI." in content
        assert "专家 (role-pm): We should focus on MVP scope first." in content

    async def test_llm_synthesis_generates_final_without_raw_discussion(
        self, writer, sample_messages, output_dir, db_session
    ):
        """LLM synthesis should write a final deliverable while full logs stay separate."""
        from app.models.room import Room

        room = Room(
            id="room-llm",
            name="LLM Room",
            goal="Produce real final doc",
            output_directory=output_dir,
        )
        db_session.add(room)
        await db_session.flush()

        client = SimpleNamespace(
            chat_completion=AsyncMock(
                return_value=SimpleNamespace(
                    content="# Produce real final doc\n\n## 决策摘要\n- Use FastAPI for the API."
                )
            )
        )
        writer._build_synthesis_client = AsyncMock(return_value=client)

        result = await writer.generate_artifact(
            room_id="room-llm",
            room_name="LLM Room",
            goal="Produce real final doc",
            messages=sample_messages,
            output_directory=output_dir,
        )

        assert result.fallback_used is False
        assert result.final_artifact.artifact_kind == "final"
        assert result.discussion_log.artifact_kind == "discussion_log"

        with open(result.final_artifact.file_path, encoding="utf-8") as f:
            final_content = f.read()
        with open(result.discussion_log.file_path, encoding="utf-8") as f:
            log_content = f.read()

        assert "Use FastAPI for the API" in final_content
        assert "Welcome to the discussion" not in final_content
        assert "Welcome to the discussion" in log_content

    async def test_fallback_marks_summary_and_still_writes_log(
        self, writer, sample_messages, output_dir, db_session
    ):
        """Fallback generation should still produce both files and mark fallback=true."""
        from app.models.room import Room

        room = Room(
            id="room-fallback",
            name="Fallback Room",
            goal="Fallback generation",
            output_directory=output_dir,
        )
        db_session.add(room)
        await db_session.flush()

        writer._build_synthesis_client = AsyncMock(return_value=None)

        result = await writer.generate_artifact(
            room_id="room-fallback",
            room_name="Fallback Room",
            goal="Fallback generation",
            messages=sample_messages,
            output_directory=output_dir,
        )

        assert result.fallback_used is True
        assert "fallback=true" in result.final_artifact.summary
        assert os.path.isfile(result.final_artifact.file_path)
        assert os.path.isfile(result.discussion_log.file_path)

    async def test_repeated_generation_uses_unique_directories(
        self, writer, sample_messages, output_dir, db_session
    ):
        """Test repeated artifact generation does not overwrite the same directory."""
        from app.models.room import Room

        room = Room(
            id="room-repeat",
            name="Repeat Room",
            goal="Repeat generation",
            output_directory=output_dir,
        )
        db_session.add(room)
        await db_session.flush()

        first = await writer.generate_artifact(
            room_id="room-repeat",
            room_name="Repeat Room",
            goal="Repeat generation",
            messages=sample_messages,
            output_directory=output_dir,
        )
        second = await writer.generate_artifact(
            room_id="room-repeat",
            room_name="Repeat Room",
            goal="Repeat generation",
            messages=sample_messages,
            output_directory=output_dir,
        )

        assert os.path.dirname(first.file_path) != os.path.dirname(second.file_path)

    async def test_missing_output_directory_raises_error(self, writer, sample_messages):
        """Test that artifact generation requires an output directory."""
        with pytest.raises(ValueError, match="Output directory"):
            await writer.generate_artifact(
                room_id="room-no-output",
                room_name="No Output Room",
                goal="No output directory",
                messages=sample_messages,
                output_directory="",
            )


class TestArtifactWriterEdgeCases:
    """Edge case tests for ArtifactWriter."""

    async def test_single_message_artifact(self, writer, output_dir, db_session):
        """Test artifact generation with only one message."""
        from app.models.room import Room

        room = Room(
            id="room-single",
            name="Single Message Room",
            goal="Single message goal",
            output_directory=output_dir,
        )
        db_session.add(room)
        await db_session.flush()

        single_message = [
            {
                "id": "msg-single",
                "sender_type": "orchestrator",
                "sender_id": None,
                "content": "This discussion has concluded.",
                "round": 1,
                "created_at": datetime(2025, 1, 1, 10, 0, 0, tzinfo=UTC),
            }
        ]

        artifact = await writer.generate_artifact(
            room_id="room-single",
            room_name="Single Message Room",
            goal="Single message goal",
            messages=single_message,
            output_directory=output_dir,
        )

        assert artifact is not None
        assert os.path.isfile(artifact.file_path)

        with open(artifact.file_path, encoding="utf-8") as f:
            content = f.read()
        assert "This discussion has concluded" in content

    def test_sender_label_unknown_type(self, writer):
        """Test that unknown sender types get a generic label."""
        label = writer._get_sender_label("unknown_type", "some-id")
        assert "unknown_type" in label

    def test_sender_label_orchestrator(self, writer):
        """Test orchestrator gets correct label."""
        label = writer._get_sender_label("orchestrator", None)
        assert label == "主持人"

    def test_sender_label_expert(self, writer):
        """Test expert gets correct label."""
        label = writer._get_sender_label("expert", "role-architect")
        assert label == "专家 (role-architect)"

    def test_sender_label_system(self, writer):
        """Test system gets correct label."""
        label = writer._get_sender_label("system", None)
        assert label == "系统"
