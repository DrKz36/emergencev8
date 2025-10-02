# ruff: noqa: E402
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[3]
SRC_DIR = ROOT_DIR / 'src'
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from backend.features.chat.router import _history_has_opinion_request

def test_history_has_opinion_request_detects_duplicate():
    history = [
        {
            'id': 'assistant-1',
            'role': 'assistant',
            'meta': {
                'opinion': {
                    'source_agent_id': 'neo',
                    'request_note_id': 'note-1',
                }
            },
        },
        {
            'id': 'note-1',
            'role': 'user',
            'meta': {
                'opinion_request': {
                    'target_agent': 'anima',
                    'source_agent': 'neo',
                    'requested_message_id': 'assistant-1',
                }
            },
        },
    ]

    assert _history_has_opinion_request(history, target_agent='anima', source_agent='neo', message_id='assistant-1')
    assert _history_has_opinion_request(history, target_agent='anima', source_agent='', message_id='assistant-1')
    assert not _history_has_opinion_request(history, target_agent='anima', source_agent='nexus', message_id='assistant-1')
    assert not _history_has_opinion_request(history, target_agent='neo', source_agent='neo', message_id='assistant-1')
    assert not _history_has_opinion_request(history, target_agent='anima', source_agent='neo', message_id='assistant-2')
