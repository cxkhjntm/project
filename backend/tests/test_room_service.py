"""Tests for room service."""

import pytest

from app.schemas.room import ParticipantInput, RoomCreate
from app.services.room_service import RoomService


@pytest.fixture
def room_service() -> RoomService:
    """Create room service instance."""
    return RoomService()


@pytest.fixture
def sample_room_data() -> RoomCreate:
    """Sample room creation data."""
    return RoomCreate(
        name="Test Room",
        goal="Test discussion goal",
        mode="code_document",
        strategy="standard",
        output_directory="/tmp/test-output",
        round_limit=5,
        participants=[
            ParticipantInput(
                role_card_id="test-role-id",
                provider_id="test-provider-id",
            )
        ],
    )


class TestRoomService:
    """Test room service operations."""

    def test_service_instantiation(self, room_service: RoomService) -> None:
        """Test service can be instantiated."""
        assert room_service is not None

    def test_room_data_creation(self, sample_room_data: RoomCreate) -> None:
        """Test room data schema."""
        assert sample_room_data.name == "Test Room"
        assert sample_room_data.goal == "Test discussion goal"
        assert len(sample_room_data.participants) == 1
        assert sample_room_data.participants[0].role_card_id == "test-role-id"
