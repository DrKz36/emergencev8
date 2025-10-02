import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[3]
SRC_DIR = ROOT_DIR / 'src'
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from backend.features.chat.service import ChatService


def test_compute_chunk_delta_returns_initial_chunk():
    total, delta = ChatService._compute_chunk_delta('', 'Bonjour')
    assert total == 'Bonjour'
    assert delta == 'Bonjour'


def test_compute_chunk_delta_handles_prefixed_chunk():
    total, delta = ChatService._compute_chunk_delta('Bonjour', 'Bonjour tout le monde')
    assert total == 'Bonjour tout le monde'
    assert delta == ' tout le monde'


def test_compute_chunk_delta_skips_duplicate_chunk():
    total, delta = ChatService._compute_chunk_delta('Salut', 'Salut')
    assert total == 'Salut'
    assert delta == ''


def test_compute_chunk_delta_appends_plain_delta():
    total, delta = ChatService._compute_chunk_delta('Hello', ' world')
    assert total == 'Hello world'
    assert delta == ' world'
