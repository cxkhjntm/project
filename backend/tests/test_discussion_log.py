"""Tests for discussion log generator service."""

import os
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.discussion_log import DiscussionLogGenerator


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
            "created_at": datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
        },
        {
            "id": "msg-2",
            "sender_type": "expert",
            "sender_id": "role-architect",
            "content": "I recommend using a RESTful design with FastAPI.",
            "round": 1,
            "created_at": datetime(2025, 1, 1, 10, 1, 0, tzinfo=timezone.utc),
        },
        {
            "id": "msg-3",
            "sender_type": "expert",
            "sender_id": "role-pm",
            "content": "We should focus on MVP scope first.",
            "round": 1,
            "created_at": datetime(2025, 1, 1, 10, 2, 0, tzinfo=timezone.utc),
        },
        {
            "id": "msg-4",
            "sender_type": "orchestrator",
            "sender_id": None,
            "content": "Good points. Let's continue to the next round.",
            "round": 2,
            "created_at": datetime(2025, 1, 1, 10, 3, 0, tzinfo=timezone.utc),
        },
        {
            "id": "msg-5",
            "sender_type": "expert",
            "sender_id": "role-architect",
            "content": "For the database layer, I suggest SQLAlchemy with async support.",
            "round": 2,
            "created_at": datetime(2025, 1, 1, 10, 4, 0, tzinfo=timezone.utc),
        },
    ]


@pytest.fixture
def output_dir(tmp_path):
    """Provide a temporary output directory."""
    return str(tmp_path / "test_output")


@pytest.fixture
def log_generator(db_session: AsyncSession):
    """Create a DiscussionLogGenerator instance."""
    return DiscussionLogGenerator(session=db_session)


class TestBuildLogContent:
    """Tests for the _build_log_content method."""

    def test_build_log_with_title_and_goal(self, log_generator, sample_messages):
        """Test log includes room name as title and goal."""
        content = log_generator._build_log_content(
            room_name="API Design Room",
            goal="Design the new REST API",
            messages=sample_messages,
        )

        assert "# API Design Room" in content
        assert "Design the new REST API" in content

    def test_build_log_groups_by_round(self, log_generator, sample_messages):
        """Test log groups messages by round number."""
        content = log_generator._build_log_content(
            room_name="Test Room",
            goal="Test goal",
            messages=sample_messages,
        )

        assert "Round 1" in content
        assert "Round 2" in content

    def test_build_log_includes_all_messages(self, log_generator, sample_messages):
        """Test log includes content from all messages."""
        content = log_generator._build_log_content(
            room_name="Test Room",
            goal="Test goal",
            messages=sample_messages,
        )

        assert "Welcome to the discussion" in content
        assert "RESTful design with FastAPI" in content
        assert "MVP scope first" in content
        assert "SQLAlchemy with async support" in content

    def test_build_log_labels_orchestrator(self, log_generator, sample_messages):
        """Test log labels orchestrator messages correctly."""
        content = log_generator._build_log_content(
            room_name="Test Room",
            goal="Test goal",
            messages=sample_messages,
        )

        assert "主持人" in content

    def test_build_log_labels_experts(self, log_generator, sample_messages):
        """Test log labels expert messages with sender_id."""
        content = log_generator._build_log_content(
            room_name="Test Room",
            goal="Test goal",
            messages=sample_messages,
        )

        assert "role-architect" in content
        assert "role-pm" in content

    def test_build_log_includes_timestamp(self, log_generator, sample_messages):
        """Test log includes generation timestamp."""
        content = log_generator._build_log_content(
            room_name="Test Room",
            goal="Test goal",
            messages=sample_messages,
        )

        assert "生成时间" in content

    def test_build_log_includes_message_count(self, log_generator, sample_messages):
        """Test log includes summary with message count."""
        content = log_generator._build_log_content(
            room_name="Test Room",
            goal="Test goal",
            messages=sample_messages,
        )

        assert "5 条消息" in content

    def test_build_log_includes_round_count(self, log_generator, sample_messages):
        """Test log includes summary with round count."""
        content = log_generator._build_log_content(
            room_name="Test Room",
            goal="Test goal",
            messages=sample_messages,
        )

        assert "2 轮讨论" in content

    def test_build_log_includes_expert_count(self, log_generator, sample_messages):
        """Test log includes summary with expert count."""
        content = log_generator._build_log_content(
            room_name="Test Room",
            goal="Test goal",
            messages=sample_messages,
        )

        assert "2 位专家参与" in content


class TestGenerateLog:
    """Tests for the generate_log method."""

    async def test_creates_output_file(self, log_generator, sample_messages, output_dir, db_session):
        """Test that generate_log creates the output markdown file."""
        from app.models.room import Room

        room = Room(
            id="room-1",
            name="Test Room",
            goal="Test goal",
            output_directory=output_dir,
        )
        db_session.add(room)
        await db_session.flush()

        artifact = await log_generator.generate_log(
            room_id="room-1",
            room_name="Test Room",
            goal="Test goal",
            messages=sample_messages,
            output_directory=output_dir,
        )

        assert os.path.isfile(artifact.file_path)
        with open(artifact.file_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "Test Room" in content
        assert "Test goal" in content

    async def test_saves_database_record(self, log_generator, sample_messages, output_dir, db_session):
        """Test that generate_log saves an Artifact record to the database."""
        from app.models.room import Room

        room = Room(
            id="room-2",
            name="DB Test Room",
            goal="DB test goal",
            output_directory=output_dir,
        )
        db_session.add(room)
        await db_session.flush()

        artifact = await log_generator.generate_log(
            room_id="room-2",
            room_name="DB Test Room",
            goal="DB test goal",
            messages=sample_messages,
            output_directory=output_dir,
        )

        assert artifact.id is not None
        assert artifact.room_id == "room-2"
        assert artifact.artifact_type == "markdown"
        assert artifact.title == "DB Test Room"
        assert artifact.file_path is not None

    async def test_returns_artifact_metadata(self, log_generator, sample_messages, output_dir, db_session):
        """Test that generate_log returns correct metadata."""
        from app.models.room import Room

        room = Room(
            id="room-3",
            name="Meta Test Room",
            goal="Meta test goal",
            output_directory=output_dir,
        )
        db_session.add(room)
        await db_session.flush()

        artifact = await log_generator.generate_log(
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

    async def test_generates_unique_directory_per_run(self, log_generator, sample_messages, output_dir, db_session):
        """Test that each log run creates a unique subdirectory."""
        from app.models.room import Room

        room = Room(
            id="room-4",
            name="Unique Dir Room",
            goal="Test unique dirs",
            output_directory=output_dir,
        )
        db_session.add(room)
        await db_session.flush()

        artifact = await log_generator.generate_log(
            room_id="room-4",
            room_name="Unique Dir Room",
            goal="Test unique dirs",
            messages=sample_messages,
            output_directory=output_dir,
        )

        assert output_dir in artifact.file_path
        assert artifact.file_path.endswith("discussion-log.md")

    async def test_empty_messages_raises_error(self, log_generator, output_dir, db_session):
        """Test that generate_log raises ValueError for empty messages."""
        with pytest.raises(ValueError, match="No messages"):
            await log_generator.generate_log(
                room_id="room-empty",
                room_name="Empty Room",
                goal="No goal",
                messages=[],
                output_directory=output_dir,
            )

    async def test_file_contains_structured_content(self, log_generator, sample_messages, output_dir, db_session):
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

        artifact = await log_generator.generate_log(
            room_id="room-5",
            room_name="Structure Test Room",
            goal="Structure test goal",
            messages=sample_messages,
            output_directory=output_dir,
        )

        with open(artifact.file_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert content.startswith("# ")
        assert "## " in content
        assert "---" in content

    async def test_file_path_is_discussion_log(self, log_generator, sample_messages, output_dir, db_session):
        """Test that the output file is named discussion-log.md."""
        from app.models.room import Room

        room = Room(
            id="room-6",
            name="Filename Test Room",
            goal="Filename test goal",
            output_directory=output_dir,
        )
        db_session.add(room)
        await db_session.flush()

        artifact = await log_generator.generate_log(
            room_id="room-6",
            room_name="Filename Test Room",
            goal="Filename test goal",
            messages=sample_messages,
            output_directory=output_dir,
        )

        assert "discussion-log.md" in artifact.file_path


class TestDiscussionLogEdgeCases:
    """Edge case tests for DiscussionLogGenerator."""

    async def test_single_message_log(self, log_generator, output_dir, db_session):
        """Test log generation with only one message."""
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
                "created_at": datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
            }
        ]

        artifact = await log_generator.generate_log(
            room_id="room-single",
            room_name="Single Message Room",
            goal="Single message goal",
            messages=single_message,
            output_directory=output_dir,
        )

        assert artifact is not None
        assert os.path.isfile(artifact.file_path)

        with open(artifact.file_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "This discussion has concluded" in content

    def test_sender_label_unknown_type(self, log_generator):
        """Test that unknown sender types get a generic label."""
        label = log_generator._get_sender_label("unknown_type", "some-id")
        assert "unknown_type" in label

    def test_sender_label_orchestrator(self, log_generator):
        """Test orchestrator gets correct label."""
        label = log_generator._get_sender_label("orchestrator", None)
        assert label == "主持人"

    def test_sender_label_expert(self, log_generator):
        """Test expert gets correct label."""
        label = log_generator._get_sender_label("expert", "role-architect")
        assert label == "专家 (role-architect)"

    def test_sender_label_system(self, log_generator):
        """Test system gets correct label."""
        label = log_generator._get_sender_label("system", None)
        assert label == "系统"

    async def test_artifact_type_is_markdown(self, log_generator, sample_messages, output_dir, db_session):
        """Test that generated artifact has correct type."""
        from app.models.room import Room

        room = Room(
            id="room-type",
            name="Type Test Room",
            goal="Type test goal",
            output_directory=output_dir,
        )
        db_session.add(room)
        await db_session.flush()

        artifact = await log_generator.generate_log(
            room_id="room-type",
            room_name="Type Test Room",
            goal="Type test goal",
            messages=sample_messages,
            output_directory=output_dir,
        )

        assert artifact.artifact_type == "markdown"

    def test_build_summary(self, log_generator, sample_messages):
        """Test _build_summary generates correct summary."""
        summary = log_generator._build_summary(sample_messages)

        assert "5 条消息" in summary
        assert "2 轮讨论" in summary
        assert "2 位专家参与" in summary
