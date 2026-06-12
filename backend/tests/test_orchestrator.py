"""Tests for orchestrator."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.orchestrator import (
    DiscussionState,
    Orchestrator,
    SSEEventType,
    parse_host_action,
)
from app.services.convergence_judge import ConvergenceResult


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
    assert orchestrator.should_continue()

    orchestrator.current_round = 2
    assert orchestrator.should_continue()

    orchestrator.current_round = 3
    assert not orchestrator.should_continue()


@pytest.mark.asyncio
async def test_sse_event_type_has_token():
    """Test SSEEventType enum includes TOKEN."""
    # Assert
    assert hasattr(SSEEventType, "TOKEN")
    assert SSEEventType.TOKEN == "token"


@pytest.mark.asyncio
async def test_expert_turn_sends_token_events():
    """Test _run_expert_turn sends TOKEN events for each chunk."""
    mock_session = AsyncMock()
    mock_on_event = AsyncMock()
    room = MagicMock(
        id="room-1",
        goal="Test goal",
        round_limit=3,
        participants=[
            MagicMock(
                role_card_id="role-1",
                provider_id="provider-1",
                provider=MagicMock(
                    base_url="http://test.com",
                    default_model="gpt-4",
                ),
            )
        ],
    )

    orchestrator = Orchestrator(
        session=mock_session,
        room=room,
        on_event=mock_on_event,
    )
    orchestrator.current_round = 1
    orchestrator._get_user_guidance_context = AsyncMock(return_value="")

    async def mock_stream(*args, **kwargs):
        for chunk in ["Hello", " world", "!"]:
            yield chunk

    with (
        patch("app.services.model_client.create_model_client") as mock_create_client,
        patch("app.services.role_card_service.role_card_service") as mock_role_card_service,
        patch("app.services.message_service.message_service") as mock_message_service,
        patch("app.services.crypto.crypto_service") as mock_crypto_service,
        patch("app.services.provider_service.provider_service") as mock_provider_service,
    ):
        mock_client = MagicMock()
        mock_client.chat_completion_stream = mock_stream
        mock_create_client.return_value = mock_client

        mock_role_card = MagicMock()
        mock_role_card.name = "Expert 1"
        mock_role_card.description = "Test expert"
        mock_role_card.expertise = []
        mock_role_card.responsibilities = []
        mock_role_card.constraints = []
        mock_role_card_service.get_by_id = AsyncMock(return_value=mock_role_card)

        mock_provider = MagicMock()
        mock_provider.api_key_encrypted = "encrypted"
        mock_provider_service.get_by_id = AsyncMock(return_value=mock_provider)

        mock_crypto_service.decrypt.return_value = "api-key"

        mock_message = MagicMock()
        mock_message.id = "msg-1"
        mock_message_service.create = AsyncMock(return_value=mock_message)

        participant = {
            "role_card_id": "role-1",
            "name": "Expert 1",
            "provider_id": "provider-1",
            "model": "gpt-4",
            "base_url": "http://test.com",
        }
        await orchestrator._run_expert_turn(participant)

        token_events = [
            call for call in mock_on_event.call_args_list if call[0][0] == SSEEventType.TOKEN
        ]
        assert len(token_events) == 3

        assert token_events[0][0][1]["room_id"] == "room-1"
        assert token_events[0][0][1]["role"] == "Expert 1"
        assert token_events[0][0][1]["content"] == "Hello"

        assert token_events[1][0][1]["content"] == " world"
        assert token_events[2][0][1]["content"] == "!"


@pytest.mark.asyncio
async def test_expert_turn_sends_message_after_stream():
    """Test _run_expert_turn sends MESSAGE event after stream completes."""
    mock_session = AsyncMock()
    mock_on_event = AsyncMock()
    room = MagicMock(
        id="room-1",
        goal="Test goal",
        round_limit=3,
        participants=[
            MagicMock(
                role_card_id="role-1",
                provider_id="provider-1",
                provider=MagicMock(
                    base_url="http://test.com",
                    default_model="gpt-4",
                ),
            )
        ],
    )

    orchestrator = Orchestrator(
        session=mock_session,
        room=room,
        on_event=mock_on_event,
    )
    orchestrator.current_round = 1
    orchestrator._get_user_guidance_context = AsyncMock(return_value="")

    async def mock_stream(*args, **kwargs):
        for chunk in ["Test", " response"]:
            yield chunk

    with (
        patch("app.services.model_client.create_model_client") as mock_create_client,
        patch("app.services.role_card_service.role_card_service") as mock_role_card_service,
        patch("app.services.message_service.message_service") as mock_message_service,
        patch("app.services.crypto.crypto_service") as mock_crypto_service,
        patch("app.services.provider_service.provider_service") as mock_provider_service,
    ):
        mock_client = MagicMock()
        mock_client.chat_completion_stream = mock_stream
        mock_create_client.return_value = mock_client

        mock_role_card = MagicMock()
        mock_role_card.name = "Expert 1"
        mock_role_card.description = "Test expert"
        mock_role_card.expertise = []
        mock_role_card.responsibilities = []
        mock_role_card.constraints = []
        mock_role_card_service.get_by_id = AsyncMock(return_value=mock_role_card)

        mock_provider = MagicMock()
        mock_provider.api_key_encrypted = "encrypted"
        mock_provider_service.get_by_id = AsyncMock(return_value=mock_provider)

        mock_crypto_service.decrypt.return_value = "api-key"

        mock_message = MagicMock()
        mock_message.id = "msg-1"
        mock_message_service.create = AsyncMock(return_value=mock_message)

        participant = {
            "role_card_id": "role-1",
            "name": "Expert 1",
            "provider_id": "provider-1",
            "model": "gpt-4",
            "base_url": "http://test.com",
        }
        await orchestrator._run_expert_turn(participant)

        message_events = [
            call for call in mock_on_event.call_args_list if call[0][0] == SSEEventType.MESSAGE
        ]
        assert len(message_events) == 1

        msg_data = message_events[0][0][1]
        assert msg_data["id"] == "msg-1"
        assert msg_data["room_id"] == "room-1"
        assert msg_data["sender_type"] == "expert"
        assert msg_data["sender_id"] == "role-1"
        assert msg_data["content"] == "Test response"
        assert msg_data["round"] == 1


@pytest.mark.asyncio
async def test_orchestrator_turn_sends_token_events():
    """Test _run_orchestrator_turn sends TOKEN events for each chunk."""
    mock_session = AsyncMock()
    mock_on_event = AsyncMock()
    room = MagicMock(
        id="room-1",
        goal="Test goal",
        round_limit=3,
        participants=[
            MagicMock(
                role_card_id="role-1",
                provider_id="provider-1",
                provider=MagicMock(
                    base_url="http://test.com",
                    default_model="gpt-4",
                ),
            )
        ],
    )

    orchestrator = Orchestrator(
        session=mock_session,
        room=room,
        on_event=mock_on_event,
    )
    orchestrator.current_round = 1
    orchestrator._get_user_guidance_context = AsyncMock(return_value="")

    async def mock_stream(*args, **kwargs):
        for chunk in ["Let", " me", " think", "..."]:
            yield chunk

    with (
        patch("app.services.model_client.create_model_client") as mock_create_client,
        patch("app.services.message_service.message_service") as mock_message_service,
        patch("app.services.crypto.crypto_service") as mock_crypto_service,
        patch("app.services.provider_service.provider_service") as mock_provider_service,
        patch("app.services.context_builder.context_builder") as mock_context_builder,
    ):
        mock_client = MagicMock()
        mock_client.chat_completion_stream = mock_stream
        mock_create_client.return_value = mock_client

        mock_provider = MagicMock()
        mock_provider.api_key_encrypted = "encrypted"
        mock_provider_service.get_by_id = AsyncMock(return_value=mock_provider)

        mock_crypto_service.decrypt.return_value = "api-key"

        mock_message = MagicMock()
        mock_message.id = "msg-orch-1"
        mock_message_service.create = AsyncMock(return_value=mock_message)

        mock_context_builder.build_orchestrator_prompt.return_value = "test prompt"

        result = await orchestrator._run_orchestrator_turn()

        token_events = [
            call for call in mock_on_event.call_args_list if call[0][0] == SSEEventType.TOKEN
        ]
        assert len(token_events) == 4
        assert token_events[0][0][1]["content"] == "Let"
        assert token_events[1][0][1]["content"] == " me"

        assert result == "Let me think..."


@pytest.mark.asyncio
async def test_orchestrator_turn_sends_message_after_stream():
    """Test _run_orchestrator_turn sends MESSAGE event after stream completes."""
    mock_session = AsyncMock()
    mock_on_event = AsyncMock()
    room = MagicMock(
        id="room-1",
        goal="Test goal",
        round_limit=3,
        participants=[
            MagicMock(
                role_card_id="role-1",
                provider_id="provider-1",
                provider=MagicMock(
                    base_url="http://test.com",
                    default_model="gpt-4",
                ),
            )
        ],
    )

    orchestrator = Orchestrator(
        session=mock_session,
        room=room,
        on_event=mock_on_event,
    )
    orchestrator.current_round = 1
    orchestrator._get_user_guidance_context = AsyncMock(return_value="")

    async def mock_stream(*args, **kwargs):
        for chunk in ["Round", " 1", " complete"]:
            yield chunk

    with (
        patch("app.services.model_client.create_model_client") as mock_create_client,
        patch("app.services.message_service.message_service") as mock_message_service,
        patch("app.services.crypto.crypto_service") as mock_crypto_service,
        patch("app.services.provider_service.provider_service") as mock_provider_service,
        patch("app.services.context_builder.context_builder") as mock_context_builder,
    ):
        mock_client = MagicMock()
        mock_client.chat_completion_stream = mock_stream
        mock_create_client.return_value = mock_client

        mock_provider = MagicMock()
        mock_provider.api_key_encrypted = "encrypted"
        mock_provider_service.get_by_id = AsyncMock(return_value=mock_provider)

        mock_crypto_service.decrypt.return_value = "api-key"

        mock_message = MagicMock()
        mock_message.id = "msg-orch-1"
        mock_message_service.create = AsyncMock(return_value=mock_message)

        mock_context_builder.build_orchestrator_prompt.return_value = "test prompt"

        await orchestrator._run_orchestrator_turn()

        message_events = [
            call for call in mock_on_event.call_args_list if call[0][0] == SSEEventType.MESSAGE
        ]
        assert len(message_events) == 1

        msg_data = message_events[0][0][1]
        assert msg_data["id"] == "msg-orch-1"
        assert msg_data["room_id"] == "room-1"
        assert msg_data["sender_type"] == "orchestrator"
        assert msg_data["content"] == "Round 1 complete"
        assert msg_data["round"] == 1


@pytest.mark.asyncio
async def test_orchestrator_turn_includes_user_guidance_in_summary():
    """User guidance should be visible to the host before choosing the next turn."""
    mock_session = AsyncMock()
    mock_on_event = AsyncMock()
    room = MagicMock(
        id="room-1",
        goal="Test goal",
        round_limit=3,
        participants=[
            MagicMock(
                role_card_id="role-1",
                provider_id="provider-1",
                provider=MagicMock(base_url="http://test.com", default_model="gpt-4"),
            )
        ],
    )
    orchestrator = Orchestrator(session=mock_session, room=room, on_event=mock_on_event)
    orchestrator.current_round = 2
    orchestrator.rolling_summary = "已有讨论摘要"
    orchestrator._get_room_status = AsyncMock(return_value="running")
    orchestrator._get_user_guidance_context = AsyncMock(
        return_value="## 用户最新指引\n- 第 1 轮用户指引：请优先评估风险"
    )

    async def mock_stream(*args, **kwargs):
        yield "ACTION: next:role-1"

    with (
        patch("app.services.model_client.create_model_client") as mock_create_client,
        patch("app.services.message_service.message_service") as mock_message_service,
        patch("app.services.crypto.crypto_service") as mock_crypto_service,
        patch("app.services.provider_service.provider_service") as mock_provider_service,
        patch("app.services.context_builder.context_builder") as mock_context_builder,
    ):
        mock_client = MagicMock()
        mock_client.chat_completion_stream = mock_stream
        mock_create_client.return_value = mock_client

        mock_provider = MagicMock()
        mock_provider.api_key_encrypted = "encrypted"
        mock_provider_service.get_by_id = AsyncMock(return_value=mock_provider)
        mock_crypto_service.decrypt.return_value = "api-key"

        mock_message = MagicMock(id="msg-orch-1")
        mock_message_service.create = AsyncMock(return_value=mock_message)
        mock_context_builder.build_orchestrator_prompt.return_value = "test prompt"

        await orchestrator._run_orchestrator_turn()

    prompt_kwargs = mock_context_builder.build_orchestrator_prompt.call_args.kwargs
    assert "已有讨论摘要" in prompt_kwargs["rolling_summary"]
    assert "请优先评估风险" in prompt_kwargs["rolling_summary"]


@pytest.mark.asyncio
async def test_expert_turn_includes_user_guidance_context():
    """User guidance submitted mid-discussion should be passed to the next expert."""
    mock_session = AsyncMock()
    mock_on_event = AsyncMock()
    room = MagicMock(
        id="room-1",
        goal="Test goal",
        round_limit=3,
        participants=[
            MagicMock(
                role_card_id="role-1",
                provider_id="provider-1",
                provider=MagicMock(base_url="http://test.com", default_model="gpt-4"),
            )
        ],
    )
    orchestrator = Orchestrator(session=mock_session, room=room, on_event=mock_on_event)
    orchestrator.current_round = 1
    orchestrator._get_room_status = AsyncMock(return_value="running")
    orchestrator._get_user_guidance_context = AsyncMock(
        return_value="## 用户最新指引\n- 第 1 轮用户指引：请下一位专家优先评估风险"
    )

    async def mock_stream(*args, **kwargs):
        yield "专家回复"

    with (
        patch("app.services.model_client.create_model_client") as mock_create_client,
        patch("app.services.role_card_service.role_card_service") as mock_role_card_service,
        patch("app.services.message_service.message_service") as mock_message_service,
        patch("app.services.crypto.crypto_service") as mock_crypto_service,
        patch("app.services.provider_service.provider_service") as mock_provider_service,
        patch("app.services.context_builder.context_builder") as mock_context_builder,
    ):
        mock_client = MagicMock()
        mock_client.chat_completion_stream = mock_stream
        mock_create_client.return_value = mock_client

        mock_role_card = MagicMock()
        mock_role_card.name = "Expert 1"
        mock_role_card.description = "Test expert"
        mock_role_card.expertise = []
        mock_role_card.responsibilities = []
        mock_role_card.constraints = []
        mock_role_card_service.get_by_id = AsyncMock(return_value=mock_role_card)

        mock_provider = MagicMock()
        mock_provider.api_key_encrypted = "encrypted"
        mock_provider_service.get_by_id = AsyncMock(return_value=mock_provider)
        mock_crypto_service.decrypt.return_value = "api-key"

        mock_message = MagicMock(id="msg-1")
        mock_message_service.create = AsyncMock(return_value=mock_message)
        mock_context_builder.build_expert_prompt.return_value = "test prompt"

        await orchestrator._run_expert_turn(
            {
                "role_card_id": "role-1",
                "name": "Expert 1",
                "provider_id": "provider-1",
                "model": "gpt-4",
                "base_url": "http://test.com",
            }
        )

    prompt_kwargs = mock_context_builder.build_expert_prompt.call_args.kwargs
    assert "请下一位专家优先评估风险" in prompt_kwargs["additional_context"]


@pytest.mark.asyncio
async def test_auto_generate_artifact_uses_user_messages_from_database():
    """Final artifacts should include user guidance messages stored during discussion."""
    mock_session = AsyncMock()
    mock_on_event = AsyncMock()
    room = MagicMock(
        id="room-1",
        name="Room 1",
        goal="Test goal",
        round_limit=1,
        output_directory="/tmp/out",
        participants=[
            MagicMock(
                role_card_id="role-1",
                provider_id="provider-1",
                role_card=MagicMock(name="Expert 1"),
                provider=MagicMock(base_url="http://test.com", default_model="gpt-4"),
            )
        ],
    )
    orchestrator = Orchestrator(session=mock_session, room=room, on_event=mock_on_event)

    db_messages = [
        SimpleNamespace(
            sender_type="user",
            sender_id=None,
            content="用户补充：优先处理稳定性",
            round=1,
            citations=None,
        ),
        SimpleNamespace(
            sender_type="expert",
            sender_id="role-1",
            content="专家回复",
            round=1,
            citations=None,
        ),
    ]

    with (
        patch("app.services.message_service.message_service") as mock_message_service,
        patch("app.services.artifact_writer.ArtifactWriter") as artifact_writer_cls,
    ):
        mock_message_service.get_by_room = AsyncMock(return_value=db_messages)
        writer = MagicMock()
        final_artifact = SimpleNamespace(
            id="artifact-1",
            title="Result",
            file_path="/tmp/out/result.md",
            artifact_type="markdown",
            artifact_kind="final",
            summary=None,
        )
        discussion_log = SimpleNamespace(
            id="artifact-log",
            title="Result 讨论记录",
            file_path="/tmp/out/discussion-log.md",
            artifact_type="markdown",
            artifact_kind="discussion_log",
            summary=None,
        )
        writer.generate_artifact = AsyncMock(
            return_value=SimpleNamespace(
                final_artifact=final_artifact,
                discussion_log=discussion_log,
                artifacts=[final_artifact, discussion_log],
                fallback_used=False,
            )
        )
        artifact_writer_cls.return_value = writer

        result = await orchestrator._auto_generate_artifact()

    assert result["id"] == "artifact-1"
    artifact_messages = writer.generate_artifact.await_args.kwargs["messages"]
    assert any(
        message["sender_type"] == "user" and "优先处理稳定性" in message["content"]
        for message in artifact_messages
    )


# ============================================================
# Tests for convergence logic (Phase 3.2)
# ============================================================


def test_parse_host_action_converge():
    """Test parsing ACTION: converge from host message."""
    content = "讨论已充分，ACTION: converge"
    action = parse_host_action(content)
    assert action is not None
    assert action["type"] == "converge"


def test_parse_host_action_synthesize():
    """Test parsing ACTION: synthesize from host message."""
    content = "可以开始总结了，ACTION: synthesize"
    action = parse_host_action(content)
    assert action is not None
    assert action["type"] == "synthesize"


def test_parse_host_action_next():
    """Legacy ACTION: next should be treated as focus."""
    content = "请下一位发言，ACTION: next:expert_1"
    action = parse_host_action(content)
    assert action is not None
    assert action["type"] == "focus"
    assert action["expert_ids"] == ["expert_1"]


def test_parse_host_action_next_chinese_name():
    """Legacy ACTION: next with Chinese names should be treated as focus."""
    content = "请后端工程师继续补充，ACTION: next:后端工程师"
    action = parse_host_action(content)
    assert action is not None
    assert action["type"] == "focus"
    assert action["expert_ids"] == ["后端工程师"]


def test_parse_host_action_focus_multiple_experts():
    """Test parsing ACTION: focus with multiple experts."""
    content = "本轮重点看前后端协作，ACTION: focus:后端工程师,前端工程师"
    action = parse_host_action(content)
    assert action is not None
    assert action["type"] == "focus"
    assert action["expert_ids"] == ["后端工程师", "前端工程师"]


def test_parse_host_action_none():
    """Test parsing when no ACTION is present."""
    content = "请大家继续讨论"
    action = parse_host_action(content)
    assert action is None


def test_parse_host_action_continue():
    """Test parsing ACTION: continue from host message."""
    content = "请大家继续补充风险点，ACTION: continue"
    action = parse_host_action(content)
    assert action is not None
    assert action["type"] == "continue"


@pytest.mark.asyncio
async def test_action_converge_stops_after_judge_confirms():
    """ACTION: converge only stops after the convergence judge confirms."""
    mock_session = AsyncMock()
    mock_on_event = AsyncMock()
    room = MagicMock(
        id="room-1",
        goal="Test goal",
        round_limit=5,
        participants=[
            MagicMock(
                role_card_id="role-1",
                provider_id="provider-1",
                provider=MagicMock(
                    base_url="http://test.com",
                    default_model="gpt-4",
                ),
            )
        ],
    )

    orchestrator = Orchestrator(
        session=mock_session,
        room=room,
        on_event=mock_on_event,
    )

    orchestrator._run_orchestrator_turn = AsyncMock(return_value="讨论充分，ACTION: converge")
    orchestrator._run_expert_turn = AsyncMock()
    orchestrator._update_rolling_summary = AsyncMock()
    orchestrator._auto_generate_artifact = AsyncMock(return_value=None)
    orchestrator.load_shared_sources = AsyncMock()
    orchestrator._check_convergence = AsyncMock(return_value=True)

    result = await orchestrator.run_discussion()

    assert result["success"] is True
    assert result["total_rounds"] == 1
    assert orchestrator._run_expert_turn.call_count == 1
    orchestrator._check_convergence.assert_awaited_once()


@pytest.mark.asyncio
async def test_action_synthesize_stops_after_judge_confirms():
    """ACTION: synthesize only stops after the convergence judge confirms."""
    mock_session = AsyncMock()
    mock_on_event = AsyncMock()
    room = MagicMock(
        id="room-1",
        goal="Test goal",
        round_limit=5,
        participants=[
            MagicMock(
                role_card_id="role-1",
                provider_id="provider-1",
                provider=MagicMock(
                    base_url="http://test.com",
                    default_model="gpt-4",
                ),
            )
        ],
    )

    orchestrator = Orchestrator(
        session=mock_session,
        room=room,
        on_event=mock_on_event,
    )

    orchestrator._run_orchestrator_turn = AsyncMock(return_value="可以总结了，ACTION: synthesize")
    orchestrator._run_expert_turn = AsyncMock()
    orchestrator._update_rolling_summary = AsyncMock()
    orchestrator._auto_generate_artifact = AsyncMock(return_value=None)
    orchestrator.load_shared_sources = AsyncMock()
    orchestrator._check_convergence = AsyncMock(return_value=True)

    result = await orchestrator.run_discussion()

    assert result["success"] is True
    assert result["total_rounds"] == 1
    orchestrator._check_convergence.assert_awaited_once()


@pytest.mark.asyncio
async def test_action_converge_continues_when_judge_disagrees():
    """Host convergence suggestions should not end the discussion without confirmation."""
    mock_session = AsyncMock()
    mock_on_event = AsyncMock()
    room = MagicMock(
        id="room-1",
        goal="Test goal",
        round_limit=2,
        participants=[
            MagicMock(
                role_card_id="role-1",
                provider_id="provider-1",
                provider=MagicMock(
                    base_url="http://test.com",
                    default_model="gpt-4",
                ),
            )
        ],
    )

    orchestrator = Orchestrator(
        session=mock_session,
        room=room,
        on_event=mock_on_event,
    )

    orchestrator._run_orchestrator_turn = AsyncMock(return_value="讨论充分，ACTION: converge")
    orchestrator._run_expert_turn = AsyncMock()
    orchestrator._update_rolling_summary = AsyncMock()
    orchestrator._auto_generate_artifact = AsyncMock(return_value=None)
    orchestrator.load_shared_sources = AsyncMock()
    orchestrator._check_convergence = AsyncMock(return_value=False)

    result = await orchestrator.run_discussion()

    assert result["success"] is True
    assert result["total_rounds"] == 2
    assert orchestrator._run_expert_turn.call_count == 2


@pytest.mark.asyncio
async def test_action_focus_runs_all_experts_with_focused_first():
    """Test that ACTION: focus prioritizes selected experts but still runs all experts."""
    mock_session = AsyncMock()
    mock_on_event = AsyncMock()
    backend_role = MagicMock()
    backend_role.name = "后端工程师"
    frontend_role = MagicMock()
    frontend_role.name = "前端工程师"
    room = MagicMock(
        id="room-1",
        goal="Test goal",
        round_limit=1,
        participants=[
            MagicMock(
                role_card_id="role-1",
                role_card=backend_role,
                provider_id="provider-1",
                provider=MagicMock(base_url="http://test.com", default_model="gpt-4"),
            ),
            MagicMock(
                role_card_id="role-2",
                role_card=frontend_role,
                provider_id="provider-1",
                provider=MagicMock(base_url="http://test.com", default_model="gpt-4"),
            ),
        ],
    )

    orchestrator = Orchestrator(session=mock_session, room=room, on_event=mock_on_event)
    orchestrator._run_orchestrator_turn = AsyncMock(
        return_value="请后端先补充，ACTION: focus:后端工程师"
    )
    orchestrator._run_expert_turn = AsyncMock()
    orchestrator._update_rolling_summary = AsyncMock()
    orchestrator._auto_generate_artifact = AsyncMock(return_value=None)
    orchestrator.load_shared_sources = AsyncMock()
    orchestrator._get_room_status = AsyncMock(return_value="running")

    result = await orchestrator.run_discussion()

    assert result["success"] is True
    assert orchestrator._run_expert_turn.call_count == 2
    first_call = orchestrator._run_expert_turn.call_args_list[0]
    second_call = orchestrator._run_expert_turn.call_args_list[1]
    assert first_call.args[0]["name"] == "后端工程师"
    assert first_call.args[2] is True
    assert second_call.args[0]["name"] == "前端工程师"
    assert second_call.args[2] is False


@pytest.mark.asyncio
async def test_no_keyword_fallback_when_no_action():
    """Keyword-like expert messages should not stop discussion without judge approval."""
    mock_session = AsyncMock()
    mock_on_event = AsyncMock()
    room = MagicMock(
        id="room-1",
        goal="Test goal",
        round_limit=5,
        participants=[
            MagicMock(
                role_card_id="role-1",
                provider_id="provider-1",
                provider=MagicMock(
                    base_url="http://test.com",
                    default_model="gpt-4",
                ),
            )
        ],
    )

    orchestrator = Orchestrator(
        session=mock_session,
        room=room,
        on_event=mock_on_event,
    )

    orchestrator.current_round = 2
    orchestrator.all_messages = [
        {"round": 1, "sender_type": "expert", "content": "同意这个方案"},
        {"round": 1, "sender_type": "expert", "content": "没有异议"},
        {"round": 2, "sender_type": "expert", "content": "可行"},
        {"round": 2, "sender_type": "expert", "content": "LGTM"},
    ]

    orchestrator._run_orchestrator_turn = AsyncMock(return_value="请大家继续讨论")
    orchestrator._run_expert_turn = AsyncMock()
    orchestrator._update_rolling_summary = AsyncMock()
    orchestrator._auto_generate_artifact = AsyncMock(return_value=None)
    orchestrator.load_shared_sources = AsyncMock()
    orchestrator._check_convergence = AsyncMock(return_value=False)

    call_count = 0

    def mock_should_continue():
        nonlocal call_count
        call_count += 1
        return call_count <= 1

    orchestrator.should_continue = mock_should_continue

    result = await orchestrator.run_discussion()

    assert result["success"] is True
    orchestrator._check_convergence.assert_awaited_once()


@pytest.mark.asyncio
async def test_force_convergence_at_max_rounds():
    """Test that discussion stops at max rounds regardless of convergence."""
    mock_session = AsyncMock()
    mock_on_event = AsyncMock()
    room = MagicMock(
        id="room-1",
        goal="Test goal",
        round_limit=3,
        participants=[
            MagicMock(
                role_card_id="role-1",
                provider_id="provider-1",
                provider=MagicMock(
                    base_url="http://test.com",
                    default_model="gpt-4",
                ),
            )
        ],
    )

    orchestrator = Orchestrator(
        session=mock_session,
        room=room,
        on_event=mock_on_event,
    )

    # Mock _run_orchestrator_turn to return no ACTION
    orchestrator._run_orchestrator_turn = AsyncMock(return_value="继续讨论")
    orchestrator._run_expert_turn = AsyncMock()
    orchestrator._update_rolling_summary = AsyncMock()
    orchestrator._auto_generate_artifact = AsyncMock(return_value=None)
    orchestrator.load_shared_sources = AsyncMock()

    result = await orchestrator.run_discussion()

    assert result["success"] is True
    assert result["total_rounds"] == 3  # Stopped at max rounds


@pytest.mark.asyncio
async def test_min_2_rounds_before_convergence():
    """Test that convergence requires at least 2 rounds."""
    mock_session = AsyncMock()
    mock_on_event = AsyncMock()
    room = MagicMock(
        id="room-1",
        goal="Test goal",
        round_limit=5,
        participants=[
            MagicMock(
                role_card_id="role-1",
                provider_id="provider-1",
                provider=MagicMock(
                    base_url="http://test.com",
                    default_model="gpt-4",
                ),
            )
        ],
    )

    orchestrator = Orchestrator(
        session=mock_session,
        room=room,
        on_event=mock_on_event,
    )

    # Set up state: only 1 round completed with convergence keywords
    orchestrator.current_round = 1
    orchestrator.all_messages = [
        {"round": 1, "sender_type": "expert", "content": "同意"},
        {"round": 1, "sender_type": "expert", "content": "没有异议"},
    ]

    # _check_convergence should return False because current_round < 2
    assert await orchestrator._check_convergence() is False


@pytest.mark.asyncio
async def test_llm_convergence_judge_result_controls_convergence():
    """LLM judge scores control convergence decisions."""
    mock_session = AsyncMock()
    room = MagicMock(
        id="room-1",
        goal="Test goal",
        round_limit=5,
        participants=[
            MagicMock(
                role_card_id="role-1",
                provider_id="provider-1",
                provider=MagicMock(base_url="http://test.com", default_model="gpt-4"),
            )
        ],
    )
    orchestrator = Orchestrator(session=mock_session, room=room)
    orchestrator.current_round = 2
    orchestrator.all_messages = [
        {"round": 2, "sender_type": "expert", "sender_id": "A", "content": "方向一致"},
        {"round": 2, "sender_type": "expert", "sender_id": "B", "content": "没有冲突"},
    ]

    judge = MagicMock()
    judge.judge = AsyncMock(
        return_value=ConvergenceResult(
            agreement_score=90,
            conflict_score=0,
            should_converge=True,
            reasoning="方向一致",
        )
    )
    with patch("app.services.convergence_judge.ConvergenceJudge", return_value=judge):
        assert await orchestrator._check_convergence() is True

    judge.judge.assert_awaited_once()
    assert judge.judge.await_args.kwargs["fallback_provider_id"] == "provider-1"


@pytest.mark.asyncio
async def test_llm_convergence_judge_failure_continues():
    """Convergence judge failures should degrade to continuing discussion."""
    mock_session = AsyncMock()
    room = MagicMock(
        id="room-1",
        goal="Test goal",
        round_limit=5,
        participants=[MagicMock(role_card_id="role-1", provider_id="provider-1")],
    )
    orchestrator = Orchestrator(session=mock_session, room=room)
    orchestrator.current_round = 2
    orchestrator.all_messages = [
        {"round": 2, "sender_type": "expert", "sender_id": "A", "content": "同意"},
        {"round": 2, "sender_type": "expert", "sender_id": "B", "content": "可行"},
    ]

    judge = MagicMock()
    judge.judge = AsyncMock(side_effect=RuntimeError("api unavailable"))
    with patch("app.services.convergence_judge.ConvergenceJudge", return_value=judge):
        assert await orchestrator._check_convergence() is False
