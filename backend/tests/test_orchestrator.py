"""Tests for orchestrator."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.orchestrator import Orchestrator, DiscussionState


@pytest.mark.asyncio
async def test_orchestrator_initialization():
    """Test orchestrator initialization."""
    # Arrange
    mock_session = AsyncMock()
    room = MagicMock(
        id="room-1",
        goal="Test goal",
        round_limit=3,
        participants=[
            MagicMock(
                role_card_id="role-1",
                role_card=MagicMock(name="Expert 1"),
                provider=MagicMock(
                    base_url="http://test.com",
                    default_model="gpt-4",
                ),
            )
        ],
    )
    
    # Act
    orchestrator = Orchestrator(session=mock_session, room=room)
    
    # Assert
    assert orchestrator.room_id == "room-1"
    assert orchestrator.goal == "Test goal"
    assert orchestrator.max_rounds == 3
    assert orchestrator.current_round == 0
    assert orchestrator.state == DiscussionState.INITIALIZED


@pytest.mark.asyncio
async def test_orchestrator_should_continue():
    """Test round limit enforcement."""
    # Arrange
    mock_session = AsyncMock()
    room = MagicMock(
        id="room-1",
        goal="Test goal",
        round_limit=3,
        participants=[MagicMock()],
    )
    orchestrator = Orchestrator(session=mock_session, room=room)
    
    # Act & Assert
    assert orchestrator.should_continue() == True
    
    orchestrator.current_round = 2
    assert orchestrator.should_continue() == True
    
    orchestrator.current_round = 3
    assert orchestrator.should_continue() == False
