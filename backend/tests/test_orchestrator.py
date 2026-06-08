"""Tests for orchestrator."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.orchestrator import Orchestrator, DiscussionState, SSEEventType


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


@pytest.mark.asyncio
async def test_sse_event_type_has_token():
    """Test SSEEventType enum includes TOKEN."""
    # Assert
    assert hasattr(SSEEventType, 'TOKEN')
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
    
    async def mock_stream(*args, **kwargs):
        for chunk in ["Hello", " world", "!"]:
            yield chunk
    
    with patch('app.services.model_client.create_model_client') as mock_create_client, \
         patch('app.services.role_card_service.role_card_service') as mock_role_card_service, \
         patch('app.services.message_service.message_service') as mock_message_service, \
         patch('app.services.crypto.crypto_service') as mock_crypto_service, \
         patch('app.services.provider_service.provider_service') as mock_provider_service:
        
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
            call for call in mock_on_event.call_args_list
            if call[0][0] == SSEEventType.TOKEN
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
    
    async def mock_stream(*args, **kwargs):
        for chunk in ["Test", " response"]:
            yield chunk
    
    with patch('app.services.model_client.create_model_client') as mock_create_client, \
         patch('app.services.role_card_service.role_card_service') as mock_role_card_service, \
         patch('app.services.message_service.message_service') as mock_message_service, \
         patch('app.services.crypto.crypto_service') as mock_crypto_service, \
         patch('app.services.provider_service.provider_service') as mock_provider_service:
        
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
            call for call in mock_on_event.call_args_list
            if call[0][0] == SSEEventType.MESSAGE
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
    
    async def mock_stream(*args, **kwargs):
        for chunk in ["Let", " me", " think", "..."]:
            yield chunk
    
    with patch('app.services.model_client.create_model_client') as mock_create_client, \
         patch('app.services.message_service.message_service') as mock_message_service, \
         patch('app.services.crypto.crypto_service') as mock_crypto_service, \
         patch('app.services.provider_service.provider_service') as mock_provider_service, \
         patch('app.services.context_builder.context_builder') as mock_context_builder:
        
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
            call for call in mock_on_event.call_args_list
            if call[0][0] == SSEEventType.TOKEN
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
    
    async def mock_stream(*args, **kwargs):
        for chunk in ["Round", " 1", " complete"]:
            yield chunk
    
    with patch('app.services.model_client.create_model_client') as mock_create_client, \
         patch('app.services.message_service.message_service') as mock_message_service, \
         patch('app.services.crypto.crypto_service') as mock_crypto_service, \
         patch('app.services.provider_service.provider_service') as mock_provider_service, \
         patch('app.services.context_builder.context_builder') as mock_context_builder:
        
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
        
        message_events = [
            call for call in mock_on_event.call_args_list
            if call[0][0] == SSEEventType.MESSAGE
        ]
        assert len(message_events) == 1
        
        msg_data = message_events[0][0][1]
        assert msg_data["id"] == "msg-orch-1"
        assert msg_data["room_id"] == "room-1"
        assert msg_data["sender_type"] == "orchestrator"
        assert msg_data["content"] == "Round 1 complete"
        assert msg_data["round"] == 1
