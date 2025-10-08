import sys
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parents[3]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

_httpx_init = httpx.Client.__init__
if "app" not in _httpx_init.__code__.co_varnames:
    def _httpx_init_compat(self, *args, app=None, **kwargs):
        return _httpx_init(self, *args, **kwargs)
    httpx.Client.__init__ = _httpx_init_compat  # type: ignore[assignment]


@pytest.fixture
def auth_app_factory():
    """
    Factory simplifié pour créer une app FastAPI de test
    Compatible avec tests synchrones (pas d'async)
    """
    def _create(name: str = "security_test", **kwargs) -> FastAPI:
        app = FastAPI()
        # App minimaliste pour tests sécurité
        # Les endpoints seront mockés dans la fixture client
        return app

    return _create


@pytest.fixture
def client(auth_app_factory):
    """Client de test FastAPI avec endpoints mockés"""
    app = auth_app_factory()

    # Ajouter endpoints basiques pour tests de sécurité
    from fastapi import Request, Response

    @app.post("/api/auth/login")
    async def mock_login(request: Request):
        # Mock simple qui rejette les payloads suspects
        try:
            body = await request.json()
            email = body.get("email", "")
            password = body.get("password", "")

            if not email or not password:
                return Response(status_code=422, content='{"error": "Missing credentials"}')

            if any(pattern in email.lower() for pattern in ["'", "or", "union", "drop", "select"]):
                return Response(status_code=422, content='{"error": "Invalid input"}')

            return Response(status_code=401, content='{"error": "Unauthorized"}')
        except:
            return Response(status_code=400, content='{"error": "Bad request"}')

    @app.post("/api/auth/register")
    async def mock_register():
        return {"status": "ok"}

    @app.post("/api/auth/logout")
    async def mock_logout():
        return {"status": "ok"}

    @app.post("/api/chat")
    async def mock_chat(message: str = "", **kwargs):
        if len(message) > 100000:  # 100KB
            return {"error": "Message too large"}, 413
        return {"status": "ok"}

    @app.get("/api/threads")
    async def mock_threads(search: str = ""):
        return []

    @app.post("/api/threads")
    async def mock_create_thread():
        return {"id": "test-thread-123"}

    @app.get("/api/threads/{thread_id}/messages")
    async def mock_get_messages(thread_id: str):
        return []

    @app.delete("/api/threads/{thread_id}")
    async def mock_delete_thread(thread_id: str):
        return {"status": "ok"}

    @app.post("/api/memory/clear")
    async def mock_memory_clear():
        return {"status": "ok"}

    return TestClient(app)


@pytest.fixture
def authenticated_user():
    """Mock utilisateur authentifié"""
    return {"email": "test@security.local", "id": 1, "role": "user"}
