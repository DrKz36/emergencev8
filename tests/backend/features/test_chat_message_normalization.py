# ruff: noqa: E402
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[3]
SRC_DIR = ROOT_DIR / 'src'
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from backend.features.chat.service import ChatService
from backend.shared.models import ChatMessage, AgentMessage, Role


def _make_service() -> ChatService:
    # Bypass __init__ to access helper methods without configuring dependencies.
    return object.__new__(ChatService)


def test_message_to_dict_normalizes_role_from_dict():
    service = _make_service()
    original = {'role': ' USER  ', 'content': 'hello world'}

    result = service._message_to_dict(original)

    assert result['role'] == 'user'
    assert result['content'] == 'hello world'
    assert original['role'] == ' USER  '  # ensure original input is untouched


def test_message_to_dict_supports_chatmessage_model():
    service = _make_service()
    msg = ChatMessage(
        id='m-1',
        session_id='s-1',
        role=Role.USER,
        agent='user',
        content='Salut',
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    result = service._message_to_dict(msg)

    assert result['role'] == 'user'
    assert result['content'] == 'Salut'
    assert result['id'] == 'm-1'


def test_message_to_dict_handles_agentmessage_with_message_field():
    service = _make_service()
    msg = AgentMessage(
        id='agent-1',
        session_id='s-42',
        role=Role.ASSISTANT,
        agent='anima',
        message='Bonjour !',
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    result = service._message_to_dict(msg)

    assert result['role'] == 'assistant'
    assert result['message'] == 'Bonjour !'
    assert result['session_id'] == 's-42'


class LegacyMessage:
    def __init__(self):
        self.id = 'legacy-1'
        self.session_id = 'legacy-session'
        self.role = Role.USER
        self.message = 'Legacy payload'
        self.agent = 'user'
        self.timestamp = '2025-09-27T10:00:00Z'


def test_message_to_dict_collects_attributes_from_legacy_object():
    service = _make_service()
    legacy = LegacyMessage()

    result = service._message_to_dict(legacy)

    assert result['role'] == 'user'
    assert result['message'] == 'Legacy payload'
    assert result['id'] == 'legacy-1'
    assert result['session_id'] == 'legacy-session'
