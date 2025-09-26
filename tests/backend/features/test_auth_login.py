# ruff: noqa: E402
import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from typing import Optional

ROOT_DIR = Path(__file__).resolve().parents[3]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from backend.core.database.manager import DatabaseManager
from backend.core.database import schema
from backend.features.auth.models import AuthConfig, LoginResponse, SessionStatusResponse
from backend.features.auth.service import AuthService
from backend.features.auth.router import router as auth_router


class _Container:
    def __init__(self, auth_service: AuthService) -> None:
        self._auth_service = auth_service

    def auth_service(self) -> AuthService:
        return self._auth_service


async def _build_app(
    db_path: Path,
    admin_email: str,
    *,
    dev_mode: bool = False,
    dev_default_email: Optional[str] = None,
) -> tuple[FastAPI, AuthService, DatabaseManager]:
    db = DatabaseManager(str(db_path))
    await schema.create_tables(db)
    config = AuthConfig(
        secret="test-secret",
        issuer="test-issuer",
        audience="test-audience",
        token_ttl_seconds=3600,
        admin_emails={admin_email},
        dev_mode=dev_mode,
        dev_default_email=dev_default_email,
    )
    auth_service = AuthService(db_manager=db, config=config)
    await auth_service.bootstrap()

    app = FastAPI()
    app.include_router(auth_router)
    app.state.service_container = _Container(auth_service)
    return app, auth_service, db


def test_login_logout_flow(tmp_path):
    async def scenario():
        admin_email = "admin@example.com"
        app, auth_service, db = await _build_app(tmp_path / "auth-login.db", admin_email)
        admin_password = "AdminPass123!"
        await auth_service.set_allowlist_password(admin_email, admin_password, actor="tests")

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            # Admin login via API
            resp = await client.post("/api/auth/login", json={"email": admin_email, "password": admin_password})
            assert resp.status_code == 200
            login_body = LoginResponse(**resp.json())
            assert login_body.email == admin_email
            assert resp.cookies.get("id_token") == login_body.token
            assert resp.cookies.get("emergence_session_id") == login_body.session_id
            set_cookie_headers = [value.lower() for value in resp.headers.get_list("set-cookie")]
            assert any('id_token=' in cookie and 'samesite=lax' in cookie for cookie in set_cookie_headers)
            assert any('emergence_session_id=' in cookie and 'samesite=lax' in cookie for cookie in set_cookie_headers)

            # Session endpoint should reflect token metadata
            headers = {"Authorization": f"Bearer {login_body.token}"}
            session_resp = await client.get("/api/auth/session", headers=headers)
            assert session_resp.status_code == 200
            session_body = SessionStatusResponse(**session_resp.json())
            assert session_body.email == admin_email
            assert session_body.role == "admin"
            assert session_body.session_id == login_body.session_id
            assert session_body.expires_at > datetime.now(timezone.utc)

            # Logout clears the session
            logout_resp = await client.post("/api/auth/logout", json={}, headers=headers)
            assert logout_resp.status_code == 204
            # httpx>=0.28 drops expired cookies from the response jar, returning None after deletion.
            assert logout_resp.cookies.get("id_token") in ("", None)
            assert logout_resp.cookies.get("emergence_session_id") in ("", None)
            logout_set_cookie = [value.lower() for value in logout_resp.headers.get_list("set-cookie")]
            assert any('id_token=' in cookie and 'max-age=0' in cookie and 'samesite=lax' in cookie for cookie in logout_set_cookie)
            assert any('emergence_session_id=' in cookie and 'max-age=0' in cookie and 'samesite=lax' in cookie for cookie in logout_set_cookie)

            row = await db.fetch_one(
                "SELECT revoked_at FROM auth_sessions WHERE id = ?",
                (login_body.session_id,),
            )
            assert row is not None
            assert row["revoked_at"] is not None

            # Further logout calls are idempotent
            repeat_logout = await client.post("/api/auth/logout", json={}, headers=headers)
            assert repeat_logout.status_code == 204


        await db.disconnect()

    asyncio.run(scenario())

def test_login_wrong_password(tmp_path):
    async def scenario():
        admin_email = "admin@example.com"
        app, auth_service, db = await _build_app(tmp_path / "auth-login-wrong.db", admin_email)
        await auth_service.set_allowlist_password(admin_email, "AdminPass123!", actor="tests")

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            resp = await client.post("/api/auth/login", json={"email": admin_email, "password": "WrongPass999"})
            assert resp.status_code == 401

        await db.disconnect()

    asyncio.run(scenario())




def test_dev_login_auto_session(tmp_path):
    async def scenario():
        admin_email = "admin@example.com"
        app, auth_service, db = await _build_app(
            tmp_path / "auth-dev-login.db",
            admin_email,
            dev_mode=True,
            dev_default_email="dev@example.com",
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            resp = await client.post("/api/auth/dev/login")
            assert resp.status_code == 200
            body = LoginResponse(**resp.json())
            assert body.email == "dev@example.com"
            assert resp.cookies.get("id_token") == body.token
            assert resp.cookies.get("emergence_session_id") == body.session_id

            session_row = await db.fetch_one(
                "SELECT email FROM auth_sessions WHERE id = ?",
                (body.session_id,),
            )
            assert session_row is not None
            assert session_row["email"] == "dev@example.com"

        await db.disconnect()

    asyncio.run(scenario())


def test_dev_login_disabled_returns_404(tmp_path):
    async def scenario():
        admin_email = "admin@example.com"
        app, auth_service, db = await _build_app(tmp_path / "auth-dev-disabled.db", admin_email)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            resp = await client.post("/api/auth/dev/login")
            assert resp.status_code == 404

        await db.disconnect()

    asyncio.run(scenario())
