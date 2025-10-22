from types import ModuleType
from unittest.mock import Mock
import sys


def _register_dummy_module(name: str) -> ModuleType:
    module = ModuleType(name.split('.')[-1])
    sys.modules[name] = module
    return module


# Stub external dependencies used by ChatService to simplify import for this unit test.
_register_dummy_module("google")
_register_dummy_module("google.generativeai")
_openai = _register_dummy_module("openai")
setattr(_openai, "AsyncOpenAI", object)
setattr(_openai, "OpenAI", object)
_anthropic = _register_dummy_module("anthropic")
setattr(_anthropic, "AsyncAnthropic", object)
setattr(_anthropic, "Anthropic", object)
_register_dummy_module("anthropic.types")
_message_param = _register_dummy_module("anthropic.types.message_param")
setattr(_message_param, "MessageParam", object)

_chromadb = _register_dummy_module("chromadb")
_config_module = _register_dummy_module("chromadb.config")
setattr(_config_module, "Settings", object)
_types_module = _register_dummy_module("chromadb.types")
setattr(_types_module, "Collection", object)
_sentence_module = _register_dummy_module("sentence_transformers")
setattr(_sentence_module, "SentenceTransformer", object)

from backend.features.chat.service import ChatService  # noqa: E402


def test_extract_group_title_handles_large_inputs() -> None:
    """Ensure title extraction handles very large inputs without crashing."""
    large_content = ("Docker " * 10000) + ("Kubernetes " * 10000)
    concepts = [{"content": large_content}]

    service = Mock(spec=ChatService)

    title = ChatService._extract_group_title(service, concepts)

    assert title, "Le titre ne doit pas être vide même pour un contenu volumineux"
    lowered = title.lower()
    assert "docker" in lowered or "kubernetes" in lowered, (
        "Le titre devrait contenir un mot-clé représentatif malgré la taille du contenu"
    )
