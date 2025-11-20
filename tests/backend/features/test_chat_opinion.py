# ruff: noqa: E402
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pytest

ROOT_DIR = Path(__file__).resolve().parents[3]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from backend.features.chat.service import ChatService  # noqa: E402
from backend.shared.models import ChatMessage, Role  # noqa: E402


class DummySessionManager:
    def __init__(self) -> None:
        self.added_messages: List[Tuple[str, ChatMessage]] = []
        self._history: List[Dict[str, Any]] = [
            {
                "id": "user-1",
                "role": "user",
                "content": "Quelle est la capitale de la France ?",
            },
            {
                "id": "assistant-1",
                "role": "assistant",
                "agent": "neo",
                "content": "La reponse initiale evoque Lyon.",
            },
        ]

    def get_message_by_id(
        self, session_id: str, message_id: str
    ) -> Optional[Dict[str, Any]]:
        if message_id == "assistant-1":
            return dict(self._history[1])
        return None

    def get_full_history(self, session_id: str) -> List[Dict[str, Any]]:
        return [dict(item) for item in self._history]

    async def add_message_to_session(
        self, session_id: str, message: ChatMessage
    ) -> None:
        self.added_messages.append((session_id, message))


class DummyConnectionManager:
    def __init__(self) -> None:
        self.sent: List[Tuple[str, Dict[str, Any]]] = []

    async def send_personal_message(
        self, payload: Dict[str, Any], session_id: str
    ) -> None:
        self.sent.append((session_id, payload))


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio("asyncio")
async def test_request_opinion_builds_instruction_and_calls_stream() -> None:
    service = object.__new__(ChatService)
    service.broadcast_agents = ["anima", "neo", "nexus"]
    service.prompts = {}
    session_manager = DummySessionManager()
    service.session_manager = session_manager
    connection_manager = DummyConnectionManager()

    calls: List[Dict[str, Any]] = []

    async def fake_process(
        session_id: str,
        agent_id: str,
        use_rag: bool,
        connection_manager: DummyConnectionManager,
        doc_ids: Optional[List[int]] = None,
        origin_agent_id: Optional[str] = None,
        opinion_request: Optional[Dict[str, Any]] = None,
    ) -> None:
        calls.append(
            {
                "session_id": session_id,
                "agent_id": agent_id,
                "use_rag": use_rag,
                "connection_manager": connection_manager,
                "doc_ids": list(doc_ids or []),
                "origin_agent_id": origin_agent_id,
                "opinion_request": dict(opinion_request or {}),
            }
        )

    service._process_agent_response_stream = fake_process  # type: ignore[attr-defined]

    await service.request_opinion(
        session_id="sess-123",
        target_agent_id="anima",
        source_agent_id="neo",
        message_id="assistant-1",
        message_text=None,
        connection_manager=connection_manager,
        request_id="front-uuid-42",
    )

    assert len(session_manager.added_messages) == 1
    sess_id, note = session_manager.added_messages[0]
    assert sess_id == "sess-123"
    assert isinstance(note, ChatMessage)
    assert note.role == Role.USER
    assert note.meta and note.meta["opinion_request"]["target_agent"] == "anima"
    assert note.id == "front-uuid-42"
    assert note.meta["opinion_request"]["request_id"] == "front-uuid-42"

    assert len(calls) == 1
    call = calls[0]
    assert call["session_id"] == "sess-123"
    assert call["agent_id"] == "anima"
    assert call["doc_ids"] == []
    assert call["origin_agent_id"] is None

    opinion_payload = call["opinion_request"]
    assert opinion_payload["source_agent_id"] == "neo"
    assert opinion_payload["target_message_id"] == "assistant-1"
    assert opinion_payload["request_note_id"] == "front-uuid-42"

    instruction = opinion_payload["instruction"]
    assert "La reponse initiale evoque Lyon." in instruction
    assert "Quelle est la capitale de la France ?" in instruction

    opinion_meta = opinion_payload["opinion_meta"]
    assert opinion_meta["of_message_id"] == "assistant-1"
    assert opinion_meta["source_agent_id"] == "neo"
    assert opinion_meta["reviewer_agent_id"] == "anima"
    assert opinion_meta["request_note_id"] == "front-uuid-42"
    assert connection_manager.sent == []
