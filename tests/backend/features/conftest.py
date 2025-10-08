import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Dict, Any, Optional

import httpx
import pytest
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import JSONResponse

ROOT_DIR = Path(__file__).resolve().parents[3]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


_httpx_init = httpx.Client.__init__
if "app" not in _httpx_init.__code__.co_varnames:
    def _httpx_init_compat(self, *args, app=None, **kwargs):
        return _httpx_init(self, *args, **kwargs)
    httpx.Client.__init__ = _httpx_init_compat  # type: ignore[assignment]

from backend.core.database import schema  # noqa: E402
from backend.core.database.manager import DatabaseManager  # noqa: E402
from backend.features.auth.models import AuthConfig  # noqa: E402
from backend.features.auth.router import router as auth_router  # noqa: E402
from backend.features.auth.service import AuthService  # noqa: E402

class _InMemoryVectorCollection:
    def __init__(self) -> None:
        self._items: Dict[str, Dict[str, Any]] = {}

    def add(
        self,
        ids: List[str],
        documents: Optional[List[str]] = None,
        metadatas: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        documents = documents or []
        metadatas = metadatas or []
        for index, doc_id in enumerate(ids):
            self._items[doc_id] = {
                "document": documents[index] if index < len(documents) else None,
                "metadata": metadatas[index] if index < len(metadatas) else {},
            }

    def delete(
        self,
        ids: Optional[List[str]] = None,
        where: Optional[Dict[str, Any]] = None,
    ) -> None:
        if ids:
            for identifier in ids:
                self._items.pop(identifier, None)
        elif where and "id" in where:
            value = where.get("id")
            if isinstance(value, dict) and "$in" in value:
                for identifier in value["$in"]:
                    self._items.pop(identifier, None)

    def get(self) -> Dict[str, Any]:
        ids = list(self._items.keys())
        documents = [payload["document"] for payload in self._items.values()]
        metadatas = [payload["metadata"] for payload in self._items.values()]
        return {
            "ids": ids,
            "documents": documents,
            "metadatas": metadatas,
        }


class _InMemoryVectorService:
    def __init__(self) -> None:
        self._collections: Dict[str, _InMemoryVectorCollection] = {}

    def get_or_create_collection(self, name: str) -> _InMemoryVectorCollection:
        if name not in self._collections:
            self._collections[name] = _InMemoryVectorCollection()
        return self._collections[name]


@dataclass
class AuthTestContext:
    app: FastAPI
    service: AuthService
    db: DatabaseManager


class _AuthContainer:
    def __init__(self, auth_service: AuthService) -> None:
        self._auth_service = auth_service

    def auth_service(self) -> AuthService:
        return self._auth_service


@pytest.fixture
def auth_app_factory(tmp_path):
    created: list[AuthTestContext] = []

    async def _create(
        name: str,
        *,
        admin_emails: Iterable[str] | None = None,
        dev_mode: bool = False,
        dev_default_email: str | None = None,
        token_ttl_seconds: int = 3600,
        rate_limiter=None,
    ) -> AuthTestContext:
        db_path = tmp_path / f"{name}.db"
        db = DatabaseManager(str(db_path))
        await schema.create_tables(db)
        config = AuthConfig(
            secret=f"{name}-secret",
            issuer="tests.emergence",
            audience="tests.emergence",
            token_ttl_seconds=token_ttl_seconds,
            admin_emails=set(admin_emails or []),
            dev_mode=dev_mode,
            dev_default_email=dev_default_email,
        )
        service = AuthService(db_manager=db, config=config, rate_limiter=rate_limiter)
        await service.bootstrap()

        app = FastAPI()
        app.include_router(auth_router)
        app.state.service_container = _AuthContainer(service)

        context = AuthTestContext(app=app, service=service, db=db)
        created.append(context)
        return context

    yield _create

    for context in created:
        asyncio.run(context.db.disconnect())


@pytest.fixture
def vector_service() -> _InMemoryVectorService:
    return _InMemoryVectorService()


@pytest.fixture
def app(vector_service: _InMemoryVectorService):
    app = FastAPI()

    def _require_user(
        authorization: str | None = Header(default=None),
        x_session_id: str | None = Header(default=None, alias="X-Session-Id"),
    ) -> Dict[str, Any]:
        if not authorization or not authorization.lower().startswith("bearer "):
            raise HTTPException(status_code=401, detail="Authentication required.")
        token = authorization.split(" ", 1)[1].strip()
        if token != "test_token_123":
            raise HTTPException(status_code=401, detail="Invalid token.")
        return {
            "user_id": "test_user_concepts",
            "session_id": x_session_id or "test_session_concepts",
        }

    @app.get("/api/memory/concepts/search")
    def search_concepts(
        q: str = Query(..., min_length=3, max_length=256),
        limit: int = Query(10, ge=1, le=50),
        user: Dict[str, Any] = Depends(_require_user),
    ):
        collection = vector_service.get_or_create_collection("emergence_knowledge")
        raw = collection.get()
        ids: List[str] = list(raw.get("ids") or [])
        documents: List[str] = list(raw.get("documents") or [])
        metadatas: List[Dict[str, Any]] = [
            dict(meta) if isinstance(meta, dict) else {}
            for meta in (raw.get("metadatas") or [])
        ]

        query_lower = q.lower()
        filtered: List[Dict[str, Any]] = []
        for idx, meta in enumerate(metadatas):
            concept_text = str(meta.get("concept_text") or documents[idx] or "")
            owner = meta.get("user_id")
            if owner != user["user_id"]:
                continue
            if query_lower not in concept_text.lower():
                continue
            result = dict(meta)
            result.setdefault("concept_text", concept_text)
            result.setdefault("thread_ids", [])
            result.setdefault("mention_count", 0)
            result["similarity_score"] = 1.0
            result["id"] = ids[idx] if idx < len(ids) else meta.get("id")
            filtered.append(result)

        filtered.sort(key=lambda item: item.get("similarity_score", 0.0), reverse=True)
        sliced = filtered[:limit]
        payload = {
            "query": q,
            "count": len(sliced),
            "results": sliced,
            "filters": {
                "session_id": user["session_id"],
            },
        }
        return JSONResponse(payload)

    return app
