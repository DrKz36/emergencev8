# ruff: noqa: E402
import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

from httpx import ASGITransport, AsyncClient

ROOT_DIR = Path(__file__).resolve().parents[3]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from backend.features.auth.models import LoginResponse, SessionStatusResponse


def test_login_logout_flow(auth_app_factory):
    async def scenario():
        admin_email = "admin@example.com"
        admin_password = "AdminPass123!"
        ctx = await auth_app_factory(
            "auth-login",
            admin_emails={admin_email},
        )
        await ctx.service.set_allowlist_password(admin_email, admin_password, actor="tests")

        transport = ASGITransport(app=ctx.app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            resp = await client.post(
                "/api/auth/login",
                json={"email": admin_email, "password": admin_password},
            )
            assert resp.status_code == 200
            login_body = LoginResponse(**resp.json())
            assert login_body.email == admin_email
            assert resp.cookies.get("id_token") == login_body.token
            assert resp.cookies.get("emergence_session_id") == login_body.session_id
            set_cookie_headers = [value.lower() for value in resp.headers.get_list("set-cookie")]
            assert any('id_token=' in cookie and 'samesite=lax' in cookie for cookie in set_cookie_headers)
            assert any('emergence_session_id=' in cookie and 'samesite=lax' in cookie for cookie in set_cookie_headers)

            headers = {"Authorization": f"Bearer {login_body.token}"}
            session_resp = await client.get("/api/auth/session", headers=headers)
            assert session_resp.status_code == 200
            session_body = SessionStatusResponse(**session_resp.json())
            assert session_body.email == admin_email
            assert session_body.role == "admin"
            assert session_body.session_id == login_body.session_id
            assert session_body.expires_at > datetime.now(timezone.utc)

            logout_resp = await client.post("/api/auth/logout", json={}, headers=headers)
            assert logout_resp.status_code == 204
            assert logout_resp.cookies.get("id_token") in ("", None)
            assert logout_resp.cookies.get("emergence_session_id") in ("", None)
            logout_set_cookie = [value.lower() for value in logout_resp.headers.get_list("set-cookie")]
            assert any('id_token=' in cookie and 'max-age=0' in cookie and 'samesite=lax' in cookie for cookie in logout_set_cookie)
            assert any('emergence_session_id=' in cookie and 'max-age=0' in cookie and 'samesite=lax' in cookie for cookie in logout_set_cookie)

            row = await ctx.db.fetch_one(
                "SELECT revoked_at FROM auth_sessions WHERE id = ?",
                (login_body.session_id,),
            )
            assert row is not None
            assert row["revoked_at"] is not None

            repeat_logout = await client.post("/api/auth/logout", json={}, headers=headers)
            assert repeat_logout.status_code == 204

    asyncio.run(scenario())


def test_login_wrong_password(auth_app_factory):
    async def scenario():
        admin_email = "admin@example.com"
        ctx = await auth_app_factory(
            "auth-login-wrong",
            admin_emails={admin_email},
        )
        await ctx.service.set_allowlist_password(admin_email, "AdminPass123!", actor="tests")

        transport = ASGITransport(app=ctx.app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            resp = await client.post(
                "/api/auth/login",
                json={"email": admin_email, "password": "WrongPass999"},
            )
            assert resp.status_code == 401

    asyncio.run(scenario())


def test_login_with_legacy_auth_sessions_schema(auth_app_factory):
    async def scenario():
        member_email = "member@example.com"
        member_password = "MemberPass123!"
        ctx = await auth_app_factory(
            "auth-legacy-schema",
            admin_emails={member_email},
        )
        await ctx.service.set_allowlist_password(member_email, member_password, actor="tests")

        await ctx.db.execute("DROP TABLE auth_sessions", commit=True)
        await ctx.db.execute(
            """
            CREATE TABLE auth_sessions (
                id TEXT PRIMARY KEY,
                email TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'member',
                ip_address TEXT,
                user_agent TEXT,
                issued_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                revoked_at TEXT,
                revoked_by TEXT,
                metadata JSON
            )
            """,
            commit=True,
        )

        transport = ASGITransport(app=ctx.app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            resp = await client.post(
                "/api/auth/login",
                json={"email": member_email, "password": member_password},
            )
            assert resp.status_code == 200
            body = LoginResponse(**resp.json())
            assert body.email == member_email
            claims = await ctx.service.verify_token(body.token)
            assert claims["email"] == member_email

    asyncio.run(scenario())


def test_dev_login_auto_session(auth_app_factory):
    async def scenario():
        admin_email = "admin@example.com"
        ctx = await auth_app_factory(
            "auth-dev-login",
            admin_emails={admin_email},
            dev_mode=True,
            dev_default_email="dev@example.com",
        )

        transport = ASGITransport(app=ctx.app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            resp = await client.post("/api/auth/dev/login")
            assert resp.status_code == 200
            body = LoginResponse(**resp.json())
            assert body.email == "dev@example.com"
            assert resp.cookies.get("id_token") == body.token
            assert resp.cookies.get("emergence_session_id") == body.session_id

            session_row = await ctx.db.fetch_one(
                "SELECT email FROM auth_sessions WHERE id = ?",
                (body.session_id,),
            )
            assert session_row is not None
            assert session_row["email"] == "dev@example.com"

    asyncio.run(scenario())


def test_dev_login_disabled_returns_404(auth_app_factory):
    async def scenario():
        admin_email = "admin@example.com"
        ctx = await auth_app_factory(
            "auth-dev-disabled",
            admin_emails={admin_email},
        )

        transport = ASGITransport(app=ctx.app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            resp = await client.post("/api/auth/dev/login")
            assert resp.status_code == 404

    asyncio.run(scenario())
