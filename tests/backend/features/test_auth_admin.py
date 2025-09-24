# ruff: noqa: E402
import asyncio
import sys
from pathlib import Path

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

ROOT_DIR = Path(__file__).resolve().parents[3]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from backend.core.database.manager import DatabaseManager
from backend.core.database import schema
from backend.features.auth.models import AuthConfig, AllowlistCreatePayload, SessionRevokePayload
from backend.features.auth.service import AuthService
from backend.features.auth.router import router as auth_router


class _Container:
    def __init__(self, auth_service: AuthService) -> None:
        self._auth_service = auth_service

    def auth_service(self) -> AuthService:
        return self._auth_service


async def _setup_app(db_path: Path, admin_email: str) -> tuple[FastAPI, AuthService, DatabaseManager]:
    db = DatabaseManager(str(db_path))
    await schema.create_tables(db)
    config = AuthConfig(
        secret="admin-secret",
        issuer="test-issuer",
        audience="test-audience",
        token_ttl_seconds=3600,
        admin_emails={admin_email},
    )
    rate_limiter = None
    auth_service = AuthService(db_manager=db, config=config, rate_limiter=rate_limiter)
    await auth_service.bootstrap()

    app = FastAPI()
    app.include_router(auth_router)
    app.state.service_container = _Container(auth_service)
    return app, auth_service, db


def test_admin_allowlist_and_sessions(tmp_path):
    async def scenario():
        admin_email = "admin@example.com"
        member_email = "member@example.com"
        app, auth_service, db = await _setup_app(tmp_path / "auth-admin.db", admin_email)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            # Admin login via API
            login_resp = await client.post("/api/auth/login", json={"email": admin_email})
            assert login_resp.status_code == 200
            admin_token = login_resp.json()["token"]
            headers = {"Authorization": f"Bearer {admin_token}"}

            # Create user allowlist entry
            payload = AllowlistCreatePayload(email=member_email, role="member", note="pytest").model_dump()
            create_resp = await client.post("/api/auth/admin/allowlist", json=payload, headers=headers)
            assert create_resp.status_code == 201
            assert create_resp.json()["email"] == member_email

            # Listing should contain member
            list_resp = await client.get("/api/auth/admin/allowlist", headers=headers)
            assert list_resp.status_code == 200
            emails = [item["email"] for item in list_resp.json()["items"]]
            assert member_email in emails

            # Login as member to create active session
            member_login = await client.post("/api/auth/login", json={"email": member_email})
            assert member_login.status_code == 200
            member_body = member_login.json()
            member_session = member_body["session_id"]

            # Sessions endpoint should list active session
            sessions_resp = await client.get("/api/auth/admin/sessions", params={"status_filter": "active"}, headers=headers)
            assert sessions_resp.status_code == 200
            sessions = sessions_resp.json()["items"]
            assert any(item["id"] == member_session for item in sessions)

            # Revoke the member session
            revoke_payload = SessionRevokePayload(session_id=member_session).model_dump()
            revoke_resp = await client.post("/api/auth/admin/sessions/revoke", json=revoke_payload, headers=headers)
            assert revoke_resp.status_code == 200
            assert revoke_resp.json()["updated"] == 1

            row = await db.fetch_one("SELECT revoked_at FROM auth_sessions WHERE id = ?", (member_session,))
            assert row is not None and row["revoked_at"] is not None

            # Remove allowlist entry and ensure login denied (423)
            delete_resp = await client.delete(f"/api/auth/admin/allowlist/{member_email}", headers=headers)
            assert delete_resp.status_code == 204

            denied_resp = await client.post("/api/auth/login", json={"email": member_email})
            assert denied_resp.status_code == 423

            # Include revoked entries in list
            revoked_list = await client.get("/api/auth/admin/allowlist", params={"include_revoked": "true"}, headers=headers)
            assert revoked_list.status_code == 200
            revoked_emails = [item["email"] for item in revoked_list.json()["items"]]
            assert member_email in revoked_emails

        await db.disconnect()

    asyncio.run(scenario())