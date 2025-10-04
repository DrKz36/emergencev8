import types

from backend.features.chat.service import ChatService


class DummyPart:
    def __init__(self, text):
        self.text = text


def call(raw):
    return ChatService._normalize_openai_delta_content(raw)


def test_normalizes_list_of_parts():
    parts = [DummyPart('R\u00e9ponse '), DummyPart('initiale'), DummyPart(' compl\u00e8te')]
    assert call(parts) == 'R\u00e9ponse initiale compl\u00e8te'


def test_normalizes_list_of_dicts():
    parts = [{'text': 'Bonjour'}, {'text': ' monde'}, {'no_text': 'ignored'}]
    assert call(parts) == 'Bonjour monde'


def test_handles_string_and_none():
    assert call('plain text') == 'plain text'
    assert call(None) == ''


def test_fallback_to_str():
    raw = types.SimpleNamespace(value='x')
    assert call(raw).startswith('namespace')
