import sys
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI, Header, HTTPException
from fastapi.testclient import TestClient
from typing import Optional

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
_invalidated_tokens = set()


@pytest.fixture(scope="function")
def auth_app_factory():
    """Factory pour créer app avec endpoints complets pour E2E"""
    # Reset storage au début de chaque test
    _mock_users.clear()
    _mock_threads.clear()
    _mock_messages.clear()
    _mock_sessions.clear()
    _invalidated_tokens.clear()

    def _create(**kwargs) -> FastAPI:
        app = FastAPI()

        # Helper pour extraire user depuis token
        def get_current_user(authorization: Optional[str] = Header(None)):
            if not authorization:
                raise HTTPException(status_code=401, detail="Missing token")
            token = authorization.replace("Bearer ", "")
            if token in _invalidated_tokens:
                raise HTTPException(status_code=401, detail="Token invalidated")
            user = _mock_sessions.get(token)
            if not user:
                raise HTTPException(status_code=401, detail="Invalid token")
            return user

        # Endpoints auth complets pour E2E
        @app.post("/api/auth/register")
        async def register(body: dict):
            email = body.get("email")
            password = body.get("password")
            if email in _mock_users:
                raise HTTPException(status_code=400, detail="User exists")
            user_id = len(_mock_users) + 1
            _mock_users[email] = {"id": user_id, "email": email, "password": password}
            return {"id": user_id, "email": email}

        @app.post("/api/auth/login")
        async def login(body: dict):
            import uuid
            email = body.get("email")
            password = body.get("password")
            user = _mock_users.get(email)
            if not user or user["password"] != password:
                raise HTTPException(status_code=401, detail="Invalid credentials")
            # Générer token unique à chaque login pour éviter collision avec tokens invalidés
            token = f"token_{user['id']}_{uuid.uuid4().hex[:8]}"
            _mock_sessions[token] = user
            return {"access_token": token, "user": user}

        @app.post("/api/auth/logout")
        async def logout(authorization: Optional[str] = Header(None)):
            if authorization:
                token = authorization.replace("Bearer ", "")
                _invalidated_tokens.add(token)
            return {"status": "ok"}

        @app.post("/api/threads")
        async def create_thread(body: dict, authorization: Optional[str] = Header(None)):
            user = get_current_user(authorization)
            title = body.get("title", "Untitled")
            thread_id = f"thread_{len(_mock_threads) + 1}"
            _mock_threads[thread_id] = {
                "id": thread_id,
                "title": title,
                "messages": [],
                "user_id": user["id"]
            }
            return {"id": thread_id, "title": title}

        @app.get("/api/threads")
        async def list_threads(authorization: Optional[str] = Header(None)):
            user = get_current_user(authorization)
            # Filtrer threads par user_id
            user_threads = [t for t in _mock_threads.values() if t.get("user_id") == user["id"]]
            return user_threads

        @app.get("/api/threads/{thread_id}/messages")
        async def get_messages(thread_id: str, authorization: Optional[str] = Header(None)):
            user = get_current_user(authorization)
            thread = _mock_threads.get(thread_id, {})
            # Vérifier ownership
            if thread.get("user_id") != user["id"]:
                raise HTTPException(status_code=403, detail="Forbidden")
            return thread.get("messages", [])

        @app.post("/api/chat")
        async def send_message(body: dict, authorization: Optional[str] = Header(None)):
            user = get_current_user(authorization)
            message = body.get("message")
            thread_id = body.get("thread_id")
            if thread_id and thread_id in _mock_threads:
                thread = _mock_threads[thread_id]
                if thread.get("user_id") != user["id"]:
                    raise HTTPException(status_code=403, detail="Forbidden")
                msg = {"role": "user", "content": message}
                thread["messages"].append(msg)
                # Simuler réponse assistant
                response = {"role": "assistant", "content": f"Response to: {message}"}
                thread["messages"].append(response)
            return {"status": "ok"}

        return app

    return _create


@pytest.fixture
def authenticated_user(auth_app_factory):
    """Crée et authentifie un utilisateur pour les tests"""
    # Réutiliser l'app partagée
    email = "testuser@e2e.local"
    password = "TestPass123!"

    # Register dans le storage global
    if email not in _mock_users:
        user_id = len(_mock_users) + 1
        _mock_users[email] = {"id": user_id, "email": email, "password": password}
        token = f"token_{user_id}"
        _mock_sessions[token] = _mock_users[email]
    else:
        user = _mock_users[email]
        token = f"token_{user['id']}"

    return {
        "email": email,
        "token": token,
        "id": _mock_users[email]["id"],
    }


@pytest.fixture
def client(auth_app_factory, authenticated_user):
    """Client de test pour E2E avec auth automatique"""
    app = auth_app_factory()
    test_client = TestClient(app)
    # Injecter le header Authorization automatiquement
    test_client.headers.update({"Authorization": f"Bearer {authenticated_user['token']}"})
    return test_client
