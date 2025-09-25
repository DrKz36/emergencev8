# ruff: noqa: E402
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

ROOT_DIR = Path(__file__).resolve().parents[3]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from backend.core.database import schema
from backend.core.database.manager import DatabaseManager
from backend.features.memory import router as memory_router


class FakeCollection:
    """Minimal vector collection stub supporting get/delete with filters."""

    def __init__(self, name: str = "emergence_knowledge") -> None:
        self.name = name
        self.items: dict[str, dict[str, str]] = {}

    def add(self, item_id: str, metadata: dict[str, str]) -> None:
        self.items[item_id] = dict(metadata)

    def _matches(self, where: dict, metadata: dict[str, str]) -> bool:
        if not where:
            return True
        if "$and" in where:
            clauses = where.get("$and") or []
            return all(self._matches(clause or {}, metadata) for clause in clauses)
        for key, expected in where.items():
            if metadata.get(key) != expected:
                return False
        return True

    def get(self, where: dict | None = None):
        where = where or {}
        matched_ids = [
            item_id
            for item_id, metadata in self.items.items()
            if self._matches(where, metadata)
        ]
        return {
            "ids": matched_ids,
            "metadatas": [self.items[item_id] for item_id in matched_ids],
        }

    def delete(self, where: dict | None = None) -> None:
        where = where or {}
        for item_id, metadata in list(self.items.items()):
            if self._matches(where, metadata):
                self.items.pop(item_id, None)


class FakeVectorService:
    """Vector service stub that records delete filters."""

    def __init__(self, collection: FakeCollection) -> None:
        self._collection = collection
        self.deleted_filters: list[dict] = []

    def get_or_create_collection(self, name: str):
        return self._collection

    def delete_vectors(self, collection: FakeCollection, where_filter: dict) -> None:
        self.deleted_filters.append(dict(where_filter))
        collection.delete(where=where_filter)


class FakeSessionManager:
    def __init__(self, owner_id: str) -> None:
        self._owner_id = owner_id

    def get_user_id_for_session(self, _session_id: str):
        return self._owner_id

    def get_user(self, _session_id: str):
        return self._owner_id

    def get_owner(self, _session_id: str):
        return self._owner_id

    def get_session_owner(self, _session_id: str):
        return self._owner_id


class FakeContainer:
    def __init__(self, db_manager: DatabaseManager, vector_service: FakeVectorService, session_manager: FakeSessionManager) -> None:
        self._db = db_manager
        self._vector = vector_service
        self._session = session_manager

    def db_manager(self):
        return self._db

    def vector_service(self):
        return self._vector

    def session_manager(self):
        return self._session


async def _run_memory_clear_scenario(tmp_path):
    db_path = tmp_path / "memory-clear.db"
    db = DatabaseManager(str(db_path))
    await db.connect()
    await schema.create_tables(db)

    session_id = "session-clear-1"
    owner_id = "owner-42"
    now_iso = datetime.now(timezone.utc).isoformat()
    history = json.dumps([{"role": "user", "content": "hello"}])
    concepts = json.dumps(["concept-A"])
    entities = json.dumps(["entity-A"])

    await db.execute(
        """
        INSERT INTO sessions (id, user_id, created_at, updated_at, session_data, summary, extracted_concepts, extracted_entities)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session_id,
            owner_id,
            now_iso,
            now_iso,
            history,
            "temporary summary",
            concepts,
            entities,
        ),
    )

    collection = FakeCollection()
    collection.add("vec-1", {"source_session_id": session_id, "user_id": owner_id})
    collection.add("vec-2", {"source_session_id": "other", "user_id": owner_id})
    vector_service = FakeVectorService(collection)
    session_manager = FakeSessionManager(owner_id)
    container = FakeContainer(db, vector_service, session_manager)

    app = FastAPI()
    app.include_router(memory_router.router, prefix="/api/memory")
    app.state.service_container = container

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/memory/clear",
            json={"session_id": session_id},
            headers={"X-Dev-Bypass": "1", "X-User-ID": owner_id},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    cleared = payload["cleared"]
    assert cleared["session_id"] == session_id
    assert cleared["stm"] is True
    assert cleared["ltm_before"] == 1
    assert cleared["ltm_deleted"] == 1

    row = await db.fetch_one(
        "SELECT summary, extracted_concepts, extracted_entities FROM sessions WHERE id = ?",
        (session_id,),
    )
    assert row is not None
    assert row["summary"] is None
    assert row["extracted_concepts"] is None
    assert row["extracted_entities"] is None

    assert "vec-1" not in collection.items
    assert "vec-2" in collection.items
    assert vector_service.deleted_filters == [
        {"$and": [{"source_session_id": session_id}, {"user_id": owner_id}]}
    ]

    await db.disconnect()


def test_memory_clear_resets_short_and_long_term(tmp_path):
    asyncio.run(_run_memory_clear_scenario(tmp_path))



async def _run_memory_endpoints_require_auth():
    app = FastAPI()
    app.include_router(memory_router.router, prefix="/api/memory")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response_tend = await client.post("/api/memory/tend-garden")
        assert response_tend.status_code == 401
        response_tend_get = await client.get("/api/memory/tend-garden")
        assert response_tend_get.status_code == 401
        response_clear = await client.post(
            "/api/memory/clear",
            json={"session_id": "unauthorized-session"},
        )
        assert response_clear.status_code == 401


def test_memory_endpoints_require_auth():
    asyncio.run(_run_memory_endpoints_require_auth())


async def _run_memory_tend_garden_get_authorized():
    app = FastAPI()
    app.include_router(memory_router.router, prefix="/api/memory")

    class DummyGardener:
        def __init__(self) -> None:
            self.calls: list[str | None] = []

        async def tend_the_garden(self, thread_id: str | None = None):
            self.calls.append(thread_id)
            return {"status": "success", "runs": 1}

    gardener = DummyGardener()
    original_getter = memory_router._get_gardener_from_request
    try:
        memory_router._get_gardener_from_request = lambda request: gardener  # type: ignore[assignment]
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get(
                "/api/memory/tend-garden",
                headers={"X-Dev-Bypass": "1", "X-User-ID": "authorized-user"},
            )
        assert response.status_code == 200
        assert response.json() == {"status": "success", "runs": 1}
    finally:
        memory_router._get_gardener_from_request = original_getter

    assert gardener.calls == [None]



def test_memory_tend_garden_get_authorized():
    asyncio.run(_run_memory_tend_garden_get_authorized())
