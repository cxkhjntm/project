"""Tests for discussion API endpoints."""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.room import Room, RoomParticipant
from app.routers.discussion import (
    control_discussion,
    create_user_message,
    get_discussion_status,
    get_messages,
    start_discussion,
    stream_discussion_events,
    stream_messages,
)
from app.schemas.discussion import DiscussionAction, DiscussionControlRequest


@pytest.fixture
def sample_room():
    room = Room(
        id="test-room-id",
        name="Test Room",
        goal="Test goal",
        mode="code_document",
        strategy="standard",
        output_directory="/tmp/test",
        round_limit=5,
        status="draft",
    )
    room.participants = [
        RoomParticipant(
            room_id="test-room-id",
            role_card_id="test-role-id",
            provider_id="test-provider-id",
        )
    ]
    return room


def _mock_session_with_room(room_or_none):
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = room_or_none

    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.execute = AsyncMock(return_value=mock_result)
    return mock_session


@pytest.mark.asyncio
async def test_start_discussion_room_not_found():
    session = _mock_session_with_room(None)

    with pytest.raises(HTTPException) as exc_info:
        await start_discussion("nonexistent-id", session)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Room not found"


@pytest.mark.asyncio
async def test_start_discussion_running_is_idempotent(sample_room):
    sample_room.status = "running"
    session = _mock_session_with_room(sample_room)

    with (
        patch("app.routers.discussion.discussion_runtime.ensure_started") as ensure_started,
        patch(
            "app.routers.discussion._discussion_event_response",
            new_callable=AsyncMock,
        ) as response,
    ):
        response.return_value = "sse-response"
        result = await start_discussion("test-room-id", session)

    assert result == "sse-response"
    ensure_started.assert_called_once_with("test-room-id")
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_start_discussion_no_participants(sample_room):
    sample_room.participants = []
    session = _mock_session_with_room(sample_room)

    with pytest.raises(HTTPException) as exc_info:
        await start_discussion("test-room-id", session)

    assert exc_info.value.status_code == 400
    assert "no participants" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_messages_room_not_found():
    session = _mock_session_with_room(None)

    with pytest.raises(HTTPException) as exc_info:
        await get_messages("nonexistent-id", session=session)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Room not found"


@pytest.mark.asyncio
async def test_stream_messages_room_not_found():
    session = _mock_session_with_room(None)

    with pytest.raises(HTTPException) as exc_info:
        await stream_messages("nonexistent-id", session=session)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Room not found"


@pytest.mark.asyncio
async def test_stream_discussion_events_room_not_found():
    session = _mock_session_with_room(None)

    with pytest.raises(HTTPException) as exc_info:
        await stream_discussion_events("nonexistent-id", session=session)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Room not found"


@pytest.mark.asyncio
async def test_stream_discussion_events_running_recovers_runtime(sample_room):
    sample_room.status = "running"
    session = _mock_session_with_room(sample_room)

    with (
        patch("app.routers.discussion.discussion_runtime.ensure_started") as ensure_started,
        patch("app.routers.discussion.discussion_runtime.subscribe") as subscribe,
        patch(
            "app.routers.discussion.message_service.get_latest_round",
            new_callable=AsyncMock,
        ) as latest_round,
    ):
        latest_round.return_value = 1
        response = await stream_discussion_events("test-room-id", session=session)

    assert response is not None
    ensure_started.assert_called_once_with("test-room-id")
    subscribe.assert_called_once_with("test-room-id")


@pytest.mark.asyncio
async def test_create_user_message_running_round_and_broadcast(sample_room):
    sample_room.status = "running"
    session = _mock_session_with_room(sample_room)

    async def create_message(_session, data):
        assert data.round == 1
        assert data.content == "请下一位专家优先评估风险"
        return SimpleNamespace(
            id="msg-1",
            room_id=data.room_id,
            sender_type=data.sender_type,
            sender_id=data.sender_id,
            content=data.content,
            citations=data.citations,
            round=data.round,
            created_at=datetime(2026, 6, 9, 12, 0, 0),
        )

    with (
        patch(
            "app.routers.discussion.message_service.get_latest_round",
            new_callable=AsyncMock,
        ) as latest_round,
        patch(
            "app.routers.discussion.message_service.create",
            new_callable=AsyncMock,
        ) as create,
        patch(
            "app.routers.discussion.discussion_runtime.broadcast",
            new_callable=AsyncMock,
        ) as broadcast,
    ):
        latest_round.return_value = 0
        create.side_effect = create_message

        result = await create_user_message(
            "test-room-id",
            {"content": "  请下一位专家优先评估风险  "},
            session,
        )

    assert result.id == "msg-1"
    assert result.round == 1
    session.commit.assert_awaited_once()
    broadcast.assert_awaited_once()
    room_id, event_type, payload = broadcast.await_args.args
    assert room_id == "test-room-id"
    assert event_type == "message"
    assert payload["sender_type"] == "user"
    assert payload["content"] == "请下一位专家优先评估风险"
    assert payload["round"] == 1


@pytest.mark.asyncio
async def test_start_discussion_completed_is_allowed(sample_room):
    sample_room.status = "completed"
    session = _mock_session_with_room(sample_room)

    sample_room.participants[0].provider = MagicMock()
    sample_room.participants[0].provider.default_model = "gpt-4"
    sample_room.participants[0].provider.base_url = "https://api.openai.com/v1"
    sample_room.participants[0].role_card = MagicMock()
    sample_room.participants[0].role_card.name = "Test Expert"

    with (
        patch("app.routers.discussion.discussion_runtime.ensure_started") as ensure_started,
        patch(
            "app.routers.discussion._discussion_event_response",
            new_callable=AsyncMock,
        ) as response,
    ):
        response.return_value = "sse-response"
        result = await start_discussion("test-room-id", session)

    assert result == "sse-response"
    assert sample_room.status == "running"
    ensure_started.assert_called_once_with("test-room-id")
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_control_discussion_start(sample_room):
    sample_room.status = "draft"
    session = _mock_session_with_room(sample_room)
    request = DiscussionControlRequest(action=DiscussionAction.START)

    with (
        patch("app.routers.discussion.discussion_runtime.ensure_started") as ensure_started,
        patch(
            "app.routers.discussion.discussion_runtime.broadcast",
            new_callable=AsyncMock,
        ),
        patch(
            "app.routers.discussion.message_service.get_latest_round",
            new_callable=AsyncMock,
        ) as latest_round,
    ):
        latest_round.return_value = 0
        result = await control_discussion("test-room-id", request, session)

    assert result["status"] == "running"
    assert result["action"] == "start"
    session.commit.assert_awaited_once()
    ensure_started.assert_called_once_with("test-room-id")


@pytest.mark.asyncio
async def test_control_discussion_start_running_is_idempotent(sample_room):
    sample_room.status = "running"
    session = _mock_session_with_room(sample_room)
    request = DiscussionControlRequest(action=DiscussionAction.START)

    with (
        patch("app.routers.discussion.discussion_runtime.ensure_started") as ensure_started,
        patch(
            "app.routers.discussion.discussion_runtime.broadcast",
            new_callable=AsyncMock,
        ),
        patch(
            "app.routers.discussion.message_service.get_latest_round",
            new_callable=AsyncMock,
        ) as latest_round,
    ):
        latest_round.return_value = 1
        result = await control_discussion("test-room-id", request, session)

    assert result["status"] == "running"
    assert result["action"] == "start"
    ensure_started.assert_called_once_with("test-room-id")
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_control_discussion_pause(sample_room):
    sample_room.status = "running"
    session = _mock_session_with_room(sample_room)
    request = DiscussionControlRequest(action=DiscussionAction.PAUSE)

    result = await control_discussion("test-room-id", request, session)

    assert result["status"] == "paused"
    assert result["action"] == "pause"


@pytest.mark.asyncio
async def test_control_discussion_pause_invalid_status(sample_room):
    sample_room.status = "draft"
    session = _mock_session_with_room(sample_room)
    request = DiscussionControlRequest(action=DiscussionAction.PAUSE)

    with pytest.raises(HTTPException) as exc_info:
        await control_discussion("test-room-id", request, session)

    assert exc_info.value.status_code == 400
    assert "not running" in exc_info.value.detail


@pytest.mark.asyncio
async def test_control_discussion_resume(sample_room):
    sample_room.status = "paused"
    session = _mock_session_with_room(sample_room)
    request = DiscussionControlRequest(action=DiscussionAction.RESUME)

    result = await control_discussion("test-room-id", request, session)

    assert result["status"] == "running"
    assert result["action"] == "resume"


@pytest.mark.asyncio
async def test_control_discussion_resume_invalid_status(sample_room):
    sample_room.status = "running"
    session = _mock_session_with_room(sample_room)
    request = DiscussionControlRequest(action=DiscussionAction.RESUME)

    with pytest.raises(HTTPException) as exc_info:
        await control_discussion("test-room-id", request, session)

    assert exc_info.value.status_code == 400
    assert "not paused" in exc_info.value.detail


@pytest.mark.asyncio
async def test_control_discussion_stop_from_running(sample_room):
    sample_room.status = "running"
    session = _mock_session_with_room(sample_room)
    request = DiscussionControlRequest(action=DiscussionAction.STOP)

    result = await control_discussion("test-room-id", request, session)

    assert result["status"] == "stopped"
    assert result["action"] == "stop"


@pytest.mark.asyncio
async def test_control_discussion_stop_from_paused(sample_room):
    sample_room.status = "paused"
    session = _mock_session_with_room(sample_room)
    request = DiscussionControlRequest(action=DiscussionAction.STOP)

    result = await control_discussion("test-room-id", request, session)

    assert result["status"] == "stopped"
    assert result["action"] == "stop"


@pytest.mark.asyncio
async def test_control_discussion_stop_invalid_status(sample_room):
    sample_room.status = "draft"
    session = _mock_session_with_room(sample_room)
    request = DiscussionControlRequest(action=DiscussionAction.STOP)

    with pytest.raises(HTTPException) as exc_info:
        await control_discussion("test-room-id", request, session)

    assert exc_info.value.status_code == 400
    assert "cannot be stopped" in exc_info.value.detail


@pytest.mark.asyncio
async def test_control_discussion_room_not_found():
    session = _mock_session_with_room(None)
    request = DiscussionControlRequest(action=DiscussionAction.START)

    with pytest.raises(HTTPException) as exc_info:
        await control_discussion("nonexistent-id", request, session)

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_get_discussion_status(sample_room):
    sample_room.status = "running"
    session = _mock_session_with_room(sample_room)

    result = await get_discussion_status("test-room-id", session)

    assert result.room_id == "test-room-id"
    assert result.status == "running"
    assert result.total_rounds == 5
    assert result.is_paused is False
    assert result.can_pause is True
    assert result.can_resume is False
    assert result.can_stop is True


@pytest.mark.asyncio
async def test_get_discussion_status_paused(sample_room):
    sample_room.status = "paused"
    session = _mock_session_with_room(sample_room)

    result = await get_discussion_status("test-room-id", session)

    assert result.status == "paused"
    assert result.is_paused is True
    assert result.can_pause is False
    assert result.can_resume is True
    assert result.can_stop is True


@pytest.mark.asyncio
async def test_get_discussion_status_draft(sample_room):
    sample_room.status = "draft"
    session = _mock_session_with_room(sample_room)

    result = await get_discussion_status("test-room-id", session)

    assert result.status == "draft"
    assert result.is_paused is False
    assert result.can_pause is False
    assert result.can_resume is False
    assert result.can_stop is False


@pytest.mark.asyncio
async def test_get_discussion_status_room_not_found():
    session = _mock_session_with_room(None)

    with pytest.raises(HTTPException) as exc_info:
        await get_discussion_status("nonexistent-id", session)

    assert exc_info.value.status_code == 404
