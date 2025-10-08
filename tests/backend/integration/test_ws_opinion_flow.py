# ruff: noqa: E402
"""
Integration test for WebSocket opinion flow with duplicate detection.
Tests the router-level logic for chat.opinion → ws:error (opinion_already_exists).
"""
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock

import pytest

ROOT_DIR = Path(__file__).resolve().parents[3]
SRC_DIR = ROOT_DIR / 'src'
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from backend.features.chat.router import _history_has_opinion_request
from backend.features.chat.service import ChatService
from backend.shared.models import ChatMessage, Role


@pytest.fixture
def anyio_backend() -> str:
    return 'asyncio'


class MockSessionManager:
    """Mock session manager for tracking opinion history."""

    def __init__(self) -> None:
        self.history: List[Dict[str, Any]] = []

    def get_full_history(self, session_id: str) -> List[Dict[str, Any]]:
        return self.history

    async def add_message_to_session(self, session_id: str, message: ChatMessage) -> None:
        self.history.append({
            'id': message.id,
            'role': message.role.value if hasattr(message.role, 'value') else str(message.role),
            'agent': message.agent,
            'content': message.content,
            'meta': message.meta or {},
        })


class MockConnectionManager:
    """Mock connection manager for tracking sent messages."""

    def __init__(self, session_manager: MockSessionManager) -> None:
        self.session_manager = session_manager
        self.sent_messages: List[Dict[str, Any]] = []

    async def send_personal_message(self, message: Dict[str, Any], session_id: str) -> None:
        self.sent_messages.append(message)


@pytest.mark.anyio('asyncio')
async def test_opinion_flow_with_duplicate_detection() -> None:
    """
    Integration test for opinion flow:
    1. Request opinion → adds note + response to history
    2. Retry same opinion → detected as duplicate by _history_has_opinion_request
    3. Router should send ws:error with code=opinion_already_exists
    """
    session_id = 'test-session-123'
    session_manager = MockSessionManager()
    connection_manager = MockConnectionManager(session_manager)

    # Simulate ChatService adding note + response to history
    chat_service = MagicMock(spec=ChatService)
    chat_service.broadcast_agents = ['anima', 'neo', 'nexus']

    async def mock_request_opinion(
        session_id: str,
        target_agent_id: str,
        source_agent_id: str | None,
        message_id: str | None,
        message_text: str | None,
        connection_manager: MockConnectionManager,
        request_id: str | None,
    ) -> None:
        # Add user note
        note = ChatMessage(
            id=request_id or 'note-id',
            session_id=session_id,
            role=Role.USER,
            agent=target_agent_id,
            content=f'[Opinion request] {message_text or message_id}',
            timestamp=datetime.now(timezone.utc).isoformat(),
            meta={'opinion_request': {'target_agent': target_agent_id}},
        )
        await connection_manager.session_manager.add_message_to_session(session_id, note)

        # Add assistant response
        response = ChatMessage(
            id='response-id',
            session_id=session_id,
            role=Role.ASSISTANT,
            agent=target_agent_id,
            content='Mock opinion response',
            timestamp=datetime.now(timezone.utc).isoformat(),
            meta={'opinion': {'request_note_id': request_id or 'note-id'}},
        )
        await connection_manager.session_manager.add_message_to_session(session_id, response)

    chat_service.request_opinion = AsyncMock(side_effect=mock_request_opinion)

    # --- First opinion request (should succeed) ---
    target_agent = 'anima'
    message_id = 'msg-123'
    request_id_1 = 'req-001'

    # Check duplicate (should be False initially)
    history = session_manager.get_full_history(session_id)
    is_duplicate = _history_has_opinion_request(
        history, target_agent=target_agent, source_agent='neo', message_id=message_id
    )
    assert not is_duplicate, 'First request should not be a duplicate'

    # Process opinion
    await chat_service.request_opinion(
        session_id=session_id,
        target_agent_id=target_agent,
        source_agent_id='neo',
        message_id=message_id,
        message_text='Test message',
        connection_manager=connection_manager,
        request_id=request_id_1,
    )

    # Verify history has note + response
    assert len(session_manager.history) == 2
    note, response = session_manager.history
    assert note['role'] == 'user'
    assert note['meta']['opinion_request']['target_agent'] == target_agent
    assert response['role'] == 'assistant'
    assert response['meta']['opinion']['request_note_id'] == request_id_1

    # --- Second opinion request (duplicate - should be detected) ---
    _request_id_2 = 'req-002'
    history = session_manager.get_full_history(session_id)
    is_duplicate = _history_has_opinion_request(
        history, target_agent=target_agent, source_agent='neo', message_id=message_id
    )
    assert is_duplicate, 'Second request should be detected as duplicate'

    # Router should NOT call chat_service.request_opinion again
    # and should send ws:error with code=opinion_already_exists
    if is_duplicate:
        await connection_manager.send_personal_message(
            {
                'type': 'ws:error',
                'payload': {
                    'message': 'Avis déjà disponible pour cette réponse.',
                    'code': 'opinion_already_exists',
                },
            },
            session_id,
        )

    # Verify error was sent
    assert len(connection_manager.sent_messages) == 1
    error_msg = connection_manager.sent_messages[0]
    assert error_msg['type'] == 'ws:error'
    assert error_msg['payload']['code'] == 'opinion_already_exists'
    assert 'Avis déjà disponible' in error_msg['payload']['message']

    # Verify opinion was only called once
    assert chat_service.request_opinion.call_count == 1
    assert len(session_manager.history) == 2  # Still 2 messages, no duplicates


@pytest.mark.anyio('asyncio')
async def test_opinion_different_targets_not_duplicate() -> None:
    """Test that opinions for different targets are not considered duplicates."""
    session_id = 'test-session-456'
    session_manager = MockSessionManager()

    # Add opinion for Anima
    await session_manager.add_message_to_session(
        session_id,
        ChatMessage(
            id='note-1',
            session_id=session_id,
            role=Role.USER,
            agent='anima',
            content='Opinion request',
            timestamp=datetime.now(timezone.utc).isoformat(),
            meta={'opinion_request': {'target_agent': 'anima'}},
        ),
    )
    await session_manager.add_message_to_session(
        session_id,
        ChatMessage(
            id='resp-1',
            session_id=session_id,
            role=Role.ASSISTANT,
            agent='anima',
            content='Anima response',
            timestamp=datetime.now(timezone.utc).isoformat(),
            meta={'opinion': {'request_note_id': 'note-1'}},
        ),
    )

    history = session_manager.get_full_history(session_id)

    # Check for Neo opinion (different target) - should NOT be duplicate
    is_duplicate = _history_has_opinion_request(
        history, target_agent='neo', source_agent='anima', message_id='msg-123'
    )
    assert not is_duplicate, 'Different target agent should not be duplicate'
