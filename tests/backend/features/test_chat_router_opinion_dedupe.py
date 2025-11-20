# ruff: noqa: E402
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[3]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from backend.features.chat.router import _history_has_opinion_request


def test_history_has_opinion_request_detects_duplicate():
    history = [
        {
            "id": "assistant-1",
            "role": "assistant",
            "meta": {
                "opinion": {
                    "source_agent_id": "neo",
                    "request_note_id": "note-1",
                }
            },
        },
        {
            "id": "note-1",
            "role": "user",
            "meta": {
                "opinion_request": {
                    "target_agent": "anima",
                    "source_agent": "neo",
                    "requested_message_id": "assistant-1",
                }
            },
        },
    ]

    assert _history_has_opinion_request(
        history, target_agent="anima", source_agent="neo", message_id="assistant-1"
    )
    assert _history_has_opinion_request(
        history, target_agent="anima", source_agent="", message_id="assistant-1"
    )
    assert not _history_has_opinion_request(
        history, target_agent="anima", source_agent="nexus", message_id="assistant-1"
    )
    assert not _history_has_opinion_request(
        history, target_agent="neo", source_agent="neo", message_id="assistant-1"
    )
    assert not _history_has_opinion_request(
        history, target_agent="anima", source_agent="neo", message_id="assistant-2"
    )


def test_history_has_opinion_request_requires_response():
    history = [
        {
            "id": "note-1",
            "role": "user",
            "meta": {
                "opinion_request": {
                    "target_agent": "anima",
                    "source_agent": "neo",
                    "requested_message_id": "assistant-1",
                    "request_id": "note-1",
                }
            },
        },
    ]

    assert not _history_has_opinion_request(
        history, target_agent="anima", source_agent="neo", message_id="assistant-1"
    )
    assert not _history_has_opinion_request(
        history, target_agent="anima", source_agent="", message_id="assistant-1"
    )

    history.append(
        {
            "id": "assistant-1",
            "role": "assistant",
            "meta": {
                "opinion": {
                    "source_agent_id": "neo",
                    "reviewer_agent_id": "anima",
                    "of_message_id": "assistant-1",
                    "request_note_id": "note-1",
                }
            },
        }
    )

    assert _history_has_opinion_request(
        history, target_agent="anima", source_agent="neo", message_id="assistant-1"
    )


class _DummyMessage:
    def __init__(self, role, meta):
        self.role = role
        self.meta = meta


def test_history_has_opinion_request_handles_multiple_agents_and_objects():
    history = [
        _DummyMessage(
            "user",
            {
                "opinion_request": {
                    "target_agent_id": "neo",
                    "source_agent_id": "anima",
                    "message_id": "assistant-1",
                    "note_id": "note-neo",
                }
            },
        ),
        _DummyMessage(
            "assistant",
            {
                "opinion": {
                    "agent_id": "neo",
                    "source_agent": "anima",
                    "message_id": "assistant-1",
                    "request_id": "note-neo",
                }
            },
        ),
        _DummyMessage(
            "user",
            {
                "opinion_request": {
                    "target_agent_id": "nexus",
                    "source_agent": "anima",
                    "requested_message_id": "assistant-1",
                    "request_id": "note-nexus",
                }
            },
        ),
        _DummyMessage(
            "assistant",
            {
                "opinion": {
                    "reviewer_agent": "nexus",
                    "source_agent_id": "anima",
                    "of_message": "assistant-1",
                    "note_id": "note-nexus",
                }
            },
        ),
    ]

    assert _history_has_opinion_request(
        history, target_agent="neo", source_agent="anima", message_id="assistant-1"
    )
    assert _history_has_opinion_request(
        history, target_agent="nexus", source_agent="anima", message_id="assistant-1"
    )
    assert not _history_has_opinion_request(
        history, target_agent="anima", source_agent="anima", message_id="assistant-1"
    )
    assert not _history_has_opinion_request(
        history, target_agent="nexus", source_agent="neo", message_id="assistant-1"
    )

    history.extend(
        [
            _DummyMessage(
                "user",
                {
                    "opinion_request": {
                        "target_agent": "anima",
                        "requested_message_id": "assistant-2",
                    }
                },
            ),
            _DummyMessage(
                "assistant",
                {
                    "opinion": {
                        "reviewer_agent_id": "anima",
                        "of_message_id": "assistant-2",
                    }
                },
            ),
        ]
    )

    assert _history_has_opinion_request(
        history, target_agent="anima", source_agent="", message_id="assistant-2"
    )
