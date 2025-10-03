# ruff: noqa: E402
import asyncio
import json
import sys
from datetime import datetime, timezone, timedelta
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
from backend.features.memory.gardener import MemoryGardener
from backend.features.auth.models import AuthConfig
from backend.features.auth.service import AuthService

# Tests rely on AuthService-issued tokens; dev bypass headers are no longer used.

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
        if "$or" in where:
            clauses = where.get("$or") or []
            return any(self._matches(clause or {}, metadata) for clause in clauses)
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

    def count(self) -> int:
        return len(self.items)


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
    def __init__(self, default_owner_id: str) -> None:
        self._default_owner_id = default_owner_id
        self.active_sessions: dict[str, str] = {}

    def register(self, session_id: str, owner_id: str | None = None) -> None:
        if not session_id:
            return
        self.active_sessions[session_id] = owner_id or self._default_owner_id

    def _resolve(self, session_id: str | None) -> str:
        if session_id and session_id in self.active_sessions:
            return self.active_sessions[session_id]
        return self._default_owner_id

    def get_user_id_for_session(self, session_id: str):
        return self._resolve(session_id)

    def get_user(self, session_id: str):
        return self._resolve(session_id)

    def get_owner(self, session_id: str):
        return self._resolve(session_id)

    def get_session_owner(self, session_id: str):
        return self._resolve(session_id)


class FakeContainer:
    def __init__(
        self,
        db_manager: DatabaseManager,
        vector_service: FakeVectorService,
        session_manager: FakeSessionManager,
        auth_service: AuthService,
        memory_analyzer = None,
    ) -> None:
        self._db = db_manager
        self._vector = vector_service
        self._session = session_manager
        self._auth = auth_service
        self._memory_analyzer = memory_analyzer

    def db_manager(self):
        return self._db

    def vector_service(self):
        return self._vector

    def session_manager(self):
        return self._session

    def auth_service(self):
        return self._auth

    def memory_analyzer(self):
        return self._memory_analyzer




TEST_AUTH_EMAIL = "memory-tester@example.com"
TEST_AUTH_PASSWORD = "MemoryPass123!"


async def _prepare_auth_context(db: DatabaseManager, email: str = TEST_AUTH_EMAIL, password: str = TEST_AUTH_PASSWORD):
    config = AuthConfig(
        secret="memory-tests-secret",
        issuer="memory-tests",
        audience="memory-tests",
        token_ttl_seconds=3600,
        admin_emails=set(),
        dev_mode=False,
        dev_default_email=None,
    )
    auth_service = AuthService(db_manager=db, config=config)
    await auth_service.bootstrap()
    await auth_service.upsert_allowlist(email, role="member", note="tests", actor="tests", password=password)
    login = await auth_service.login(
        email,
        password,
        ip_address="127.0.0.1",
        user_agent="memory-tests-suite",
    )
    return auth_service, login


def _auth_headers(login, *, session_id: str | None = None) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {login.token}"}
    headers["X-Session-Id"] = session_id or login.session_id
    headers["X-User-Id"] = login.user_id
    return headers

def test_filter_history_for_agent_preserves_target_messages():
    history = [
        {"role": "assistant", "agent_id": "anima", "content": "bonjour"},
        {"role": "assistant", "agent_id": "neo", "content": "salut"},
        {"role": "user", "content": "ok"},
        {"role": "system", "content": "meta"},
    ]
    filtered = MemoryGardener._filter_history_for_agent(history, 'neo')
    assert any((item.get('agent_id') or '').lower() == 'neo' for item in filtered)
    assert all((item.get('role') or '').lower() != 'assistant' or (item.get('agent_id') or '').lower() == 'neo' for item in filtered)
    assert any((item.get('role') or '').lower() == 'user' for item in filtered)


def test_filter_history_for_agent_no_agent_returns_original():
    history = [
        {"role": "assistant", "agent_id": "anima", "content": "bonjour"},
        {"role": "user", "content": "ok"},
    ]
    assert MemoryGardener._filter_history_for_agent(history, None) == history


async def _run_memory_clear_scenario(tmp_path):
    db_path = tmp_path / "memory-clear.db"
    db = DatabaseManager(str(db_path))
    await db.connect()
    await schema.create_tables(db)

    auth_service, login = await _prepare_auth_context(db)

    session_id = "session-clear-1"
    owner_id = login.user_id
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
    collection.add("vec-1", {"session_id": session_id, "source_session_id": session_id, "user_id": owner_id})
    collection.add("vec-2", {"session_id": "other", "source_session_id": "other", "user_id": owner_id})
    vector_service = FakeVectorService(collection)
    session_manager = FakeSessionManager(owner_id)
    session_manager.register(session_id, owner_id)
    container = FakeContainer(db, vector_service, session_manager, auth_service)

    app = FastAPI()
    app.include_router(memory_router.router, prefix="/api/memory")
    app.state.service_container = container

    headers = _auth_headers(login, session_id=session_id)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/memory/clear",
            json={"session_id": session_id},
            headers=headers,
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
    expected_filter = {
        "$and": [
            {"$or": [{"session_id": session_id}, {"source_session_id": session_id}]},
            {"user_id": owner_id},
        ]
    }
    assert vector_service.deleted_filters == [expected_filter]

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



async def _run_memory_tend_garden_post_with_agent(tmp_path):
    db_path = tmp_path / "memory-tend-agent.db"
    db = DatabaseManager(str(db_path))
    await db.connect()
    await schema.create_tables(db)

    auth_service, login = await _prepare_auth_context(db)

    vector_service = FakeVectorService(FakeCollection())
    session_manager = FakeSessionManager(login.user_id)
    session_manager.register("session-agent", login.user_id)
    container = FakeContainer(db, vector_service, session_manager, auth_service)

    app = FastAPI()
    app.include_router(memory_router.router, prefix="/api/memory")
    app.state.service_container = container

    captured = {}

    class DummyGardener:
        async def tend_the_garden(
            self,
            consolidation_limit: int = 10,
            thread_id: str | None = None,
            session_id: str | None = None,
            agent_id: str | None = None,
        ):
            captured['limit'] = consolidation_limit
            captured['thread_id'] = thread_id
            captured['session_id'] = session_id
            captured['agent_id'] = agent_id
            return {"status": "success", "message": "OK", "consolidated_sessions": 0, "new_concepts": 0}

    original_getter = memory_router._get_gardener_from_request
    transport = ASGITransport(app=app)
    try:
        memory_router._get_gardener_from_request = lambda request: DummyGardener()  # type: ignore[assignment]
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post(
                "/api/memory/tend-garden",
                json={"thread_id": "thread-123", "agent_id": "Neo"},
                headers=_auth_headers(login, session_id="session-agent"),
            )
        assert response.status_code == 200
    finally:
        memory_router._get_gardener_from_request = original_getter
        await db.disconnect()

    assert captured == {
        "limit": 10,
        "thread_id": "thread-123",
        "session_id": "session-agent",
        "agent_id": "Neo",
    }


async def _run_memory_tend_garden_get_authorized(tmp_path):
    db_path = tmp_path / "memory-tend-get.db"
    db = DatabaseManager(str(db_path))
    await db.connect()
    await schema.create_tables(db)

    auth_service, login = await _prepare_auth_context(db)

    vector_service = FakeVectorService(FakeCollection())
    session_manager = FakeSessionManager(login.user_id)
    container = FakeContainer(db, vector_service, session_manager, auth_service)

    app = FastAPI()
    app.include_router(memory_router.router, prefix="/api/memory")
    app.state.service_container = container

    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get(
                "/api/memory/tend-garden",
                headers=_auth_headers(login),
            )
        assert response.status_code == 200
        payload = response.json()
        assert payload.get("status") in {"ok", "success"}
        assert payload.get("total") == 0
        assert payload.get("ltm_count") == 0
        assert isinstance(payload.get("summaries"), list)
        legacy_report = payload.get("legacy_report")
        if legacy_report is not None:
            assert legacy_report.get("status") in {"ok", "success"}
    finally:
        await db.disconnect()



def test_memory_tend_garden_post_forwards_agent(tmp_path):
    asyncio.run(_run_memory_tend_garden_post_with_agent(tmp_path))


def test_memory_tend_garden_get_authorized(tmp_path):
    asyncio.run(_run_memory_tend_garden_get_authorized(tmp_path))



async def _run_memory_tend_garden_get_with_data(tmp_path):
    db_path = tmp_path / "memory-history.db"
    db = DatabaseManager(str(db_path))
    await db.connect()
    await schema.create_tables(db)

    auth_service, login = await _prepare_auth_context(db)

    owner_id = login.user_id
    now = datetime.now(timezone.utc)
    rows = [
        (
            "session-old",
            now - timedelta(minutes=5),
            now - timedelta(minutes=2),
            "Resume ancien",
            ["concept-alpha", "concept-beta"],
            ["entity-1"],
        ),
        (
            "session-new",
            now - timedelta(minutes=1),
            now,
            "Resume recent",
            ["concept-gamma"],
            ["entity-2", "entity-3"],
        ),
    ]

    try:
        for session_id, created_at, updated_at, summary, concepts, entities in rows:
            await db.execute(
                """
                INSERT INTO sessions (id, user_id, created_at, updated_at, session_data, summary, extracted_concepts, extracted_entities)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    owner_id,
                    created_at.isoformat(),
                    updated_at.isoformat(),
                    json.dumps([{"messages": "seed"}]),
                    summary,
                    json.dumps(concepts),
                    json.dumps(entities),
                ),
            )

        collection = FakeCollection()
        collection.add("vec-a", {"session_id": "session-old", "source_session_id": "session-old", "user_id": owner_id})
        collection.add("vec-b", {"session_id": "session-new", "source_session_id": "session-new", "user_id": owner_id})
        collection.add("vec-c", {"session_id": "session-new", "source_session_id": "session-new", "user_id": owner_id})
        vector_service = FakeVectorService(collection)
        session_manager = FakeSessionManager(owner_id)
        session_manager.register("session-old", owner_id)
        session_manager.register("session-new", owner_id)
        container = FakeContainer(db, vector_service, session_manager, auth_service)

        app = FastAPI()
        app.include_router(memory_router.router, prefix="/api/memory")
        app.state.service_container = container

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get(
                "/api/memory/tend-garden",
                headers=_auth_headers(login),
            )

        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "ok"
        assert payload["total"] == 2
        assert payload["ltm_count"] == 3

        summaries = payload["summaries"]
        assert isinstance(summaries, list)
        assert len(summaries) == 2
        assert summaries[0]["session_id"] == "session-new"
        assert summaries[0]["concept_count"] == 1
        assert summaries[0]["entity_count"] == 2
        assert summaries[1]["session_id"] == "session-old"
        assert summaries[1]["concept_count"] == 2
        assert summaries[1]["entity_count"] == 1
    finally:
        await db.disconnect()


def test_memory_tend_garden_get_returns_history(tmp_path):
    asyncio.run(_run_memory_tend_garden_get_with_data(tmp_path))

