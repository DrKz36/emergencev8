# tests/memory/test_preference_extractor.py

import pytest
from backend.features.memory.preference_extractor import (
    PreferenceExtractor,
    PreferenceRecord,
)


class MockLLMClient:
    """Mock LLM pour tests"""

    async def get_structured_llm_response(self, agent_id, prompt, json_schema):
        """Simule réponse LLM structurée"""
        # Détection basique du type basé sur le contenu du prompt
        if "préfère" in prompt.lower() or "aime" in prompt.lower():
            return {
                "type": "preference",
                "topic": "Python",
                "action": "apprendre",
                "timeframe": "ongoing",
                "sentiment": "positive",
                "confidence": 0.9,
                "entities": ["FastAPI"],
            }
        elif "veux" in prompt.lower() or "vais" in prompt.lower():
            return {
                "type": "intent",
                "topic": "projet",
                "action": "créer",
                "timeframe": "ongoing",
                "sentiment": "positive",
                "confidence": 0.85,
                "entities": [],
            }
        elif "évite" in prompt.lower() or "refuse" in prompt.lower():
            return {
                "type": "constraint",
                "topic": "framework",
                "action": "éviter",
                "timeframe": "ongoing",
                "sentiment": "negative",
                "confidence": 0.8,
                "entities": ["jQuery"],
            }
        else:
            return {
                "type": "neutral",
                "topic": "unknown",
                "action": "",
                "timeframe": "ongoing",
                "sentiment": "neutral",
                "confidence": 0.5,
                "entities": [],
            }


@pytest.fixture
def mock_llm():
    return MockLLMClient()


@pytest.mark.asyncio
async def test_extract_preference(mock_llm):
    """Test extraction préférence basique"""
    extractor = PreferenceExtractor(mock_llm)

    messages = [
        {"role": "user", "content": "Je préfère Python à Java", "id": "msg1"},
        {"role": "assistant", "content": "Compris", "id": "msg2"},
    ]

    records = await extractor.extract(
        messages, user_sub="user123", thread_id="thread1"
    )

    assert len(records) == 1
    assert records[0].type == "preference"
    assert records[0].topic == "Python"
    assert records[0].confidence >= 0.6
    assert records[0].thread_id == "thread1"


@pytest.mark.asyncio
async def test_extract_intent(mock_llm):
    """Test extraction intention"""
    extractor = PreferenceExtractor(mock_llm)

    messages = [
        {"role": "user", "content": "Je vais créer un nouveau projet", "id": "msg1"}
    ]

    records = await extractor.extract(
        messages, user_sub="user123", thread_id="thread1"
    )

    assert len(records) == 1
    assert records[0].type == "intent"
    assert records[0].confidence >= 0.6


@pytest.mark.asyncio
async def test_extract_constraint(mock_llm):
    """Test extraction contrainte"""
    extractor = PreferenceExtractor(mock_llm)

    messages = [
        {"role": "user", "content": "J'évite d'utiliser jQuery", "id": "msg1"}
    ]

    records = await extractor.extract(
        messages, user_sub="user123", thread_id="thread1"
    )

    assert len(records) == 1
    assert records[0].type == "constraint"
    assert records[0].sentiment == "negative"


@pytest.mark.asyncio
async def test_lexical_filtering(mock_llm):
    """Test que le filtrage lexical réduit les appels LLM"""
    extractor = PreferenceExtractor(mock_llm)

    messages = [
        {"role": "user", "content": "Bonjour comment ça va ?", "id": "msg1"},
        {"role": "user", "content": "Quelle heure est-il ?", "id": "msg2"},
    ]

    records = await extractor.extract(
        messages, user_sub="user123", thread_id="thread1"
    )

    assert len(records) == 0  # Aucun verbe cible
    assert extractor.stats["filtered"] == 2  # 2 messages filtrés
    assert extractor.stats["classified"] == 0  # Aucun appel LLM


@pytest.mark.asyncio
async def test_low_confidence_filtering(mock_llm):
    """Test que les extractions à faible confiance sont ignorées"""

    class LowConfidenceLLM:
        async def get_structured_llm_response(self, agent_id, prompt, json_schema):
            return {
                "type": "preference",
                "topic": "test",
                "action": "faire",
                "timeframe": "ongoing",
                "sentiment": "neutral",
                "confidence": 0.4,  # Sous le seuil de 0.6
                "entities": [],
            }

    extractor = PreferenceExtractor(LowConfidenceLLM())

    messages = [{"role": "user", "content": "Je préfère le café", "id": "msg1"}]

    records = await extractor.extract(
        messages, user_sub="user123", thread_id="thread1"
    )

    assert len(records) == 0  # Filtré par confiance < 0.6


@pytest.mark.asyncio
async def test_preference_record_id_generation():
    """Test génération ID unique"""
    id1 = PreferenceRecord.generate_id("user1", "Python", "preference")
    id2 = PreferenceRecord.generate_id("user1", "Python", "preference")
    id3 = PreferenceRecord.generate_id("user2", "Python", "preference")

    # Même user + topic + type = même ID (déduplication)
    assert id1 == id2

    # User différent = ID différent
    assert id1 != id3


@pytest.mark.asyncio
async def test_multiple_messages(mock_llm):
    """Test extraction depuis plusieurs messages"""
    extractor = PreferenceExtractor(mock_llm)

    messages = [
        {"role": "user", "content": "Je préfère Python", "id": "msg1"},
        {"role": "user", "content": "Je vais apprendre FastAPI", "id": "msg2"},
        {"role": "user", "content": "J'évite les frameworks lourds", "id": "msg3"},
        {
            "role": "user",
            "content": "Bonjour",
            "id": "msg4",
        },  # Devrait être filtré
    ]

    records = await extractor.extract(
        messages, user_sub="user123", thread_id="thread1"
    )

    # 3 messages avec verbes cibles, 1 filtré
    assert len(records) == 3
    assert extractor.stats["filtered"] == 1
    assert extractor.stats["classified"] == 3


@pytest.mark.asyncio
async def test_preference_record_to_dict():
    """Test conversion PreferenceRecord vers dict"""
    record = PreferenceRecord(
        id="test123",
        type="preference",
        topic="Python",
        action="apprendre",
        text="Je préfère Python",
        timeframe="ongoing",
        sentiment="positive",
        confidence=0.9,
        entities=["FastAPI"],
        source_message_id="msg1",
        thread_id="thread1",
        captured_at="2025-01-01T00:00:00",
    )

    record_dict = record.to_dict()

    assert record_dict["type"] == "preference"
    assert record_dict["topic"] == "Python"
    assert record_dict["confidence"] == 0.9
    assert isinstance(record_dict, dict)
