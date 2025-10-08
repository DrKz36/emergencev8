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


# Mock storage pour simuler persistence
_mock_users = {}
_mock_threads = {}
_mock_messages = {}
_mock_sessions = {}


@pytest.fixture
def auth_app_factory():
    """Factory pour créer app avec endpoints complets pour E2E"""

    def _create(**kwargs) -> FastAPI:
        app = FastAPI()

        # Endpoints auth complets pour E2E
        @app.post("/api/auth/register")
        async def register(email: str, password: str):
            if email in _mock_users:
                return {"error": "User exists"}, 400
            user_id = len(_mock_users) + 1
            _mock_users[email] = {"id": user_id, "email": email, "password": password}
            return {"id": user_id, "email": email}

        @app.post("/api/auth/login")
        async def login(email: str, password: str):
            user = _mock_users.get(email)
            if not user or user["password"] != password:
                return {"error": "Invalid credentials"}, 401
            token = f"token_{user['id']}"
            _mock_sessions[token] = user
            return {"access_token": token, "user": user}

        @app.post("/api/auth/logout")
        async def logout():
            return {"status": "ok"}

        @app.post("/api/threads")
        async def create_thread(title: str = "Untitled"):
            thread_id = f"thread_{len(_mock_threads) + 1}"
            _mock_threads[thread_id] = {"id": thread_id, "title": title, "messages": []}
            return {"id": thread_id, "title": title}

        @app.get("/api/threads")
        async def list_threads():
            return list(_mock_threads.values())

        @app.get("/api/threads/{thread_id}/messages")
        async def get_messages(thread_id: str):
            thread = _mock_threads.get(thread_id, {})
            return thread.get("messages", [])

        @app.post("/api/chat")
        async def send_message(message: str, thread_id: str = None):
            if thread_id and thread_id in _mock_threads:
                msg = {"role": "user", "content": message}
                _mock_threads[thread_id]["messages"].append(msg)
                # Simuler réponse assistant
                response = {"role": "assistant", "content": f"Response to: {message}"}
                _mock_threads[thread_id]["messages"].append(response)
            return {"status": "ok"}

        return app

    # Reset storage entre tests
    _mock_users.clear()
    _mock_threads.clear()
    _mock_messages.clear()
    _mock_sessions.clear()

    return _create


@pytest.fixture
def client(auth_app_factory):
    """Client de test pour E2E"""
    app = auth_app_factory()
    return TestClient(app)


@pytest.fixture
def authenticated_user(client):
    """Crée et authentifie un utilisateur pour les tests"""
    email = "testuser@e2e.local"
    password = "TestPass123!"

    # Register
    client.post("/api/auth/register", json={"email": email, "password": password})

    # Login
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    data = response.json()

    return {
        "email": email,
        "token": data.get("access_token"),
        "id": data.get("user", {}).get("id"),
    }
