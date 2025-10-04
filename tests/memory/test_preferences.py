import asyncio
import json
from copy import deepcopy

import pytest

from backend.features.memory.gardener import MemoryGardener, _preference_record_id


class DummyVectorCollection:
    def __init__(self, name: str):
        self.name = name
        self.items = {}

    def get(self, ids=None, **_):
        ids = ids or []
        result_ids = []
        metadatas = []
        documents = []
        for record_id in ids:
            item = self.items.get(record_id)
            if item:
                result_ids.append(record_id)
                metadatas.append(item.get("metadata", {}))
                documents.append(item.get("text", ""))
        return {"ids": result_ids, "metadatas": metadatas, "documents": documents}


class DummyVectorService:
    def __init__(self):
        self.collections = {}
        self.add_calls = []

    def get_or_create_collection(self, name: str):
        if name not in self.collections:
            self.collections[name] = DummyVectorCollection(name)
        return self.collections[name]

    def add_items(self, collection, items, item_text_key: str = "text"):
        self.add_calls.append(items)
        for item in items:
            collection.items[item["id"]] = {
                "id": item["id"],
                "text": item[item_text_key],
                "metadata": deepcopy(item.get("metadata", {})),
            }


class DummyDBManager:
    def __init__(self):
        self.events = []

    async def execute(self, query: str, params=None):
        self.events.append((query, params))


class DummyMemoryAnalyzer:
    def __init__(self, chat_service=None):
        self.chat_service = chat_service

    def set_chat_service(self, chat_service):
        self.chat_service = chat_service


class DummyConnectionManager:
    def __init__(self):
        self.messages = []

    async def send_personal_message(self, payload, session_id):
        self.messages.append((payload, session_id))


class DummySessionManager:
    def __init__(self, connection_manager):
        self.connection_manager = connection_manager


class DummyChatService:
    def __init__(self, connection_manager):
        self.session_manager = DummySessionManager(connection_manager)


def build_preference_record(user_id: str, pref_type: str = "preference", topic: str = "ton", *, confidence: float, source_message_id: str):
    topic_key = topic.lower()
    record_id = _preference_record_id(user_id, pref_type, topic_key)
    return {
        "id": record_id,
        "type": pref_type,
        "topic": topic,
        "topic_normalized": topic_key,
        "action": "parler doucement",
        "timeframe": "ongoing",
        "timeframe_raw": None,
        "sentiment": "positive",
        "confidence": confidence,
        "user_id": user_id,
        "canonical_text": "Je prefere un ton plus doux.",
        "source_message_id": source_message_id,
        "summary": "Preference pour un ton doux",
    }


def test_store_preference_records_deduplicates_existing():
    async def scenario():
        db_manager = DummyDBManager()
        vector_service = DummyVectorService()
        analyzer = DummyMemoryAnalyzer()
        gardener = MemoryGardener(db_manager=db_manager, vector_service=vector_service, memory_analyzer=analyzer)

        session_id = "thread-1"
        user_id = "user-1"

        first_record = build_preference_record(user_id, confidence=0.7, source_message_id="msg-1")
        inserted_first = await gardener._store_preference_records([first_record], session_id, user_id)

        assert inserted_first == 1
        stored_item = vector_service.collections[MemoryGardener.PREFERENCE_COLLECTION_NAME].items[first_record["id"]]
        assert stored_item["metadata"]["occurrences"] == 1
        assert stored_item["metadata"]["confidence"] == pytest.approx(0.7)

        assert len(db_manager.events) == 1
        assert db_manager.events[0][1][0] == "memory_preference"
        payload_first = json.loads(db_manager.events[0][1][1])
        assert payload_first["occurrences"] == 1

        second_record = build_preference_record(user_id, confidence=0.5, source_message_id="msg-2")
        inserted_second = await gardener._store_preference_records([second_record], session_id, user_id)

        assert inserted_second == 0

        updated_item = vector_service.collections[MemoryGardener.PREFERENCE_COLLECTION_NAME].items[first_record["id"]]
        assert updated_item["metadata"]["occurrences"] == 2
        assert updated_item["metadata"]["confidence"] == pytest.approx(0.6, abs=1e-4)
        assert set(updated_item["metadata"]["source_message_ids"]) == {"msg-1", "msg-2"}

        assert len(db_manager.events) == 2
        payload_second = json.loads(db_manager.events[-1][1][1])
        assert payload_second["occurrences"] == 2

    asyncio.run(scenario())


def test_store_preference_records_emits_banner_when_threshold_crossed():
    async def scenario():
        connection_manager = DummyConnectionManager()
        chat_service = DummyChatService(connection_manager)
        analyzer = DummyMemoryAnalyzer(chat_service=chat_service)
        db_manager = DummyDBManager()
        vector_service = DummyVectorService()
        gardener = MemoryGardener(db_manager=db_manager, vector_service=vector_service, memory_analyzer=analyzer)

        session_id = "thread-2"
        user_id = "user-7"

        initial_record = build_preference_record(user_id, confidence=0.4, source_message_id="msg-a")
        await gardener._store_preference_records([initial_record], session_id, user_id)
        assert connection_manager.messages == []

        boost_record = build_preference_record(user_id, confidence=0.9, source_message_id="msg-b")
        await gardener._store_preference_records([boost_record], session_id, user_id)

        assert len(connection_manager.messages) == 1
        payload, sid = connection_manager.messages[0]
        assert sid == session_id
        assert payload["type"] == "ws:memory_banner"
        assert payload["payload"]["variant"] == "preference_captured"
        assert payload["payload"]["confidence"] >= 0.6
        assert payload["payload"]["source_message_id"] == "msg-b"

    asyncio.run(scenario())


