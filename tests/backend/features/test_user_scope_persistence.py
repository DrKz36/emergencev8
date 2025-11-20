# ruff: noqa: E402
import asyncio
import json
import hashlib
import os
import sys
from pathlib import Path
from datetime import datetime, timezone

import pytest

ROOT_DIR = Path(__file__).resolve().parents[3]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from backend.core.database.manager import DatabaseManager
from backend.core.database import schema, queries
from backend.core.database.backfill import run_user_scope_backfill
from backend.features.auth.models import AuthConfig
from backend.features.auth.service import AuthService, AuthError
from backend.core.session_manager import SessionManager
from backend.shared.models import ChatMessage, Role


async def _prepare_auth_service(
    db_path: Path, email: str, password: str
) -> tuple[AuthService, DatabaseManager]:
    db = DatabaseManager(str(db_path))
    await schema.create_tables(db)

    config = AuthConfig(
        secret="test-secret",
        issuer="emergence.local",
        audience="emergence-app",
        token_ttl_seconds=3600,
        admin_emails={"admin@example.com"},
        dev_mode=False,
    )
    service = AuthService(db, config)
    await service.bootstrap()

    # Inject the test user in the allowlist with a password
    hashed = service._hash_password(password)
    await db.execute(
        """
        INSERT OR REPLACE INTO auth_allowlist (email, role, note, created_at, created_by, password_hash, password_updated_at)
        VALUES (?, 'member', 'test-user', datetime('now'), 'tests', ?, datetime('now'))
        """,
        (email, hashed),
    )
    return service, db


def test_login_populates_user_scope(tmp_path):
    async def scenario():
        email = "user@example.com"
        password = "P@ssw0rd!1"
        db_path = tmp_path / "auth-user-scope.db"

        service, db = await _prepare_auth_service(db_path, email, password)

        login = await service.login(email, password, "127.0.0.1", "pytest")
        expected_user_id = hashlib.sha256(email.encode("utf-8")).hexdigest()

        assert login.user_id == expected_user_id

        row = await db.fetch_one(
            "SELECT user_id FROM auth_sessions WHERE id = ?",
            (login.session_id,),
        )
        assert row is not None
        assert row["user_id"] == expected_user_id

        thread_id = await queries.create_thread(
            db,
            session_id=login.session_id,
            user_id=expected_user_id,
            type_="chat",
            title="Cross device thread",
        )
        await queries.add_message(
            db,
            thread_id,
            session_id=login.session_id,
            user_id=expected_user_id,
            role="user",
            content="Hello world",
            agent_id=None,
            tokens=None,
            meta=None,
        )

        threads = await queries.get_threads(
            db,
            session_id="new-session-id",
            user_id=expected_user_id,
            type_="chat",
            limit=5,
        )
        assert any(t["id"] == thread_id for t in threads)

        messages = await queries.get_messages(
            db,
            thread_id,
            session_id="another-session",
            user_id=expected_user_id,
            limit=10,
        )
        assert any(m["content"] == "Hello world" for m in messages)

        await db.disconnect()

    asyncio.run(scenario())


def test_verify_token_restores_missing_session(tmp_path):
    async def scenario():
        email = "restore@example.com"
        password = "S3ss10n!"
        db_path = tmp_path / "auth-verify-restore.db"

        service, db = await _prepare_auth_service(db_path, email, password)

        login = await service.login(email, password, "127.0.0.1", "pytest-restore")
        claims_before = await service.verify_token(login.token)
        assert claims_before.get("session_id") == login.session_id

        await db.execute(
            "DELETE FROM auth_sessions WHERE id = ?",
            (login.session_id,),
            commit=True,
        )

        restored_claims = await service.verify_token(login.token)
        assert restored_claims.get("session_id") == login.session_id
        assert restored_claims.get("email") == email

        row = await db.fetch_one(
            "SELECT metadata FROM auth_sessions WHERE id = ?",
            (login.session_id,),
        )
        assert row is not None
        meta = row["metadata"]
        assert meta
        metadata = json.loads(meta)
        assert metadata.get("restored_from_claims") is True

        await db.disconnect()

    asyncio.run(scenario())


def test_verify_token_handles_revoked_session(tmp_path):
    async def scenario():
        email = "revoked@example.com"
        password = "Rev0keMe!"
        db_path = tmp_path / "auth-verify-revoked.db"

        service, db = await _prepare_auth_service(db_path, email, password)

        login = await service.login(email, password, "127.0.0.1", "pytest-revoke")

        await service.logout(login.session_id, actor="tests")

        with pytest.raises(AuthError) as excinfo:
            await service.verify_token(login.token)
        assert excinfo.value.status_code == 401

        claims = await service.verify_token(login.token, allow_revoked=True)
        assert claims.get("session_revoked") is True
        assert claims.get("email") == email

        await db.disconnect()

    asyncio.run(scenario())


def test_verify_token_handles_expired_session(tmp_path):
    async def scenario():
        email = "expired@example.com"
        password = "Exp1red!"
        db_path = tmp_path / "auth-verify-expired.db"

        service, db = await _prepare_auth_service(db_path, email, password)

        login = await service.login(email, password, "127.0.0.1", "pytest-expired")

        await db.execute(
            "UPDATE auth_sessions SET expires_at = datetime('now', '-5 minutes') WHERE id = ?",
            (login.session_id,),
            commit=True,
        )

        with pytest.raises(AuthError) as excinfo:
            await service.verify_token(login.token)
        assert excinfo.value.status_code == 401

        claims = await service.verify_token(login.token, allow_expired=True)
        assert claims.get("expires_at") <= datetime.now(timezone.utc)

        await db.disconnect()

    asyncio.run(scenario())


def test_verify_token_rejects_revoked_allowlist_entry(tmp_path):
    async def scenario():
        email = "revoked-user@example.com"
        password = "St1llRevoked!"
        db_path = tmp_path / "auth-verify-allowlist.db"

        service, db = await _prepare_auth_service(db_path, email, password)

        login = await service.login(email, password, "127.0.0.1", "pytest-allowlist")

        await db.execute(
            "UPDATE auth_allowlist SET revoked_at = datetime('now'), revoked_by = 'tests' WHERE email = ?",
            (email,),
            commit=True,
        )

        with pytest.raises(AuthError) as excinfo:
            await service.verify_token(login.token)
        assert excinfo.value.status_code == 401

        await db.disconnect()

    asyncio.run(scenario())


def test_threads_api_cross_session_listing(auth_app_factory):
    async def scenario():
        email = "member@example.com"
        password = "Str0ngP@ss!"
        ctx = await auth_app_factory(
            "threads-cross-session",
            admin_emails={email},
        )
        await ctx.service.set_allowlist_password(email, password, actor="tests")

        class Container:
            def __init__(self, db_manager: DatabaseManager, auth: AuthService) -> None:
                self._db_manager = db_manager
                self._auth_service = auth

            def db_manager(self) -> DatabaseManager:
                return self._db_manager

            def auth_service(self) -> AuthService:
                return self._auth_service

        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient
        from backend.features.threads import router as threads_router

        app = FastAPI()
        app.include_router(threads_router.router, prefix="/api/threads")
        app.state.service_container = Container(ctx.db, ctx.service)

        login_primary = await ctx.service.login(
            email, password, "127.0.0.1", "pytest-primary"
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            create_resp = await client.post(
                "/api/threads",
                json={"type": "chat", "title": "Cross session thread"},
                headers={
                    "Authorization": f"Bearer {login_primary.token}",
                    "X-Session-Id": login_primary.session_id,
                },
            )
            assert create_resp.status_code == 201
            payload = create_resp.json()
            thread_id = payload["id"]

            message_resp = await client.post(
                f"/api/threads/{thread_id}/messages",
                json={"role": "user", "content": "Persist across sessions"},
                headers={
                    "Authorization": f"Bearer {login_primary.token}",
                    "X-Session-Id": login_primary.session_id,
                },
            )
            assert message_resp.status_code == 201

            login_secondary = await ctx.service.login(
                email, password, "127.0.0.1", "pytest-secondary"
            )

            list_resp = await client.get(
                "/api/threads",
                headers={
                    "Authorization": f"Bearer {login_secondary.token}",
                    "X-Session-Id": login_secondary.session_id,
                },
            )
            assert list_resp.status_code == 200
            items = list_resp.json().get("items", [])
            assert any(item["id"] == thread_id for item in items)

            messages_resp = await client.get(
                f"/api/threads/{thread_id}/messages",
                headers={
                    "Authorization": f"Bearer {login_secondary.token}",
                    "X-Session-Id": login_secondary.session_id,
                },
                params={"limit": 20},
            )
            assert messages_resp.status_code == 200
            messages = messages_resp.json().get("items", [])
            assert any(msg["content"] == "Persist across sessions" for msg in messages)

    asyncio.run(scenario())


def test_session_manager_persists_messages_when_thread_binding_missing(tmp_path):
    async def scenario():
        db_path = tmp_path / "session-manager-fallback.db"

        db = DatabaseManager(str(db_path))
        await schema.create_tables(db)

        session_manager = SessionManager(db)

        session_id = "session-fallback"
        user_id = "user-fallback"
        thread_id = await queries.create_thread(
            db,
            session_id=session_id,
            user_id=user_id,
            type_="chat",
            title="Fallback thread",
        )

        await session_manager.ensure_session(
            session_id, user_id, thread_id="bogus-thread"
        )
        session_manager._session_threads[session_id] = "bogus-thread"

        message = ChatMessage(
            id="msg-fallback",
            session_id=session_id,
            role=Role.USER,
            agent="user",
            content="Hello from fallback",
            timestamp=datetime.now(timezone.utc).isoformat(),
            cost=None,
            tokens=None,
            agents=None,
            use_rag=False,
            doc_ids=[],
        )

        await session_manager.add_message_to_session(session_id, message)

        rows = await queries.get_messages(
            db,
            thread_id,
            session_id=session_id,
            user_id=user_id,
            limit=10,
        )
        assert any(r.get("content") == "Hello from fallback" for r in rows)

        assert session_manager._session_threads.get(session_id) == thread_id

        await db.disconnect()

    asyncio.run(scenario())


def test_user_scope_backfill_remaps_legacy_placeholder(tmp_path):
    async def scenario():
        email = "gonzalefernando@gmail.com"
        expected_user_id = hashlib.sha256(email.encode("utf-8")).hexdigest()
        previous_default = os.environ.get("AUTH_DEV_DEFAULT_EMAIL")
        db_path = tmp_path / "legacy-placeholder.db"
        file_path = str(db_path / "legacy.txt")

        db = DatabaseManager(str(db_path))
        await schema.create_tables(db)

        now = datetime.now(timezone.utc).isoformat()

        try:
            os.environ["AUTH_DEV_DEFAULT_EMAIL"] = email

            await db.execute(
                """
                INSERT INTO threads (id, session_id, user_id, type, title, agent_id, meta, archived, created_at, updated_at)
                VALUES (?, ?, ?, 'chat', ?, NULL, NULL, 0, ?, ?)
                """,
                ("legacy-thread", "legacy-session", "FG", "Legacy thread", now, now),
            )
            await db.execute(
                """
                INSERT INTO messages (id, thread_id, role, agent_id, content, tokens, meta, created_at, session_id, user_id)
                VALUES (?, ?, 'user', NULL, ?, NULL, NULL, ?, ?, ?)
                """,
                (
                    "legacy-message",
                    "legacy-thread",
                    "Hello legacy",
                    now,
                    "legacy-session",
                    "FG",
                ),
            )
            await db.execute(
                """
                INSERT INTO documents (id, filename, filepath, status, char_count, chunk_count, error_message, uploaded_at, session_id, user_id)
                VALUES (?, ?, ?, 'ready', NULL, NULL, NULL, ?, ?, ?)
                """,
                (1, "legacy.txt", file_path, now, "legacy-session", "FG"),
            )
            await db.execute(
                """
                INSERT INTO document_chunks (id, document_id, chunk_index, content, session_id, user_id)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                ("chunk-1", 1, 0, "legacy content", "legacy-session", "FG"),
            )
            await db.execute(
                """
                INSERT INTO thread_docs (thread_id, doc_id, session_id, user_id, weight, last_used_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                ("legacy-thread", 1, "legacy-session", "FG", 1.0, now),
            )

            await run_user_scope_backfill(db)

            thread_row = await db.fetch_one(
                "SELECT user_id FROM threads WHERE id = ?",
                ("legacy-thread",),
            )
            assert thread_row and thread_row["user_id"] == expected_user_id

            message_row = await db.fetch_one(
                "SELECT user_id FROM messages WHERE id = ?",
                ("legacy-message",),
            )
            assert message_row and message_row["user_id"] == expected_user_id

            document_row = await db.fetch_one(
                "SELECT user_id FROM documents WHERE id = ?",
                (1,),
            )
            assert document_row and document_row["user_id"] == expected_user_id

            chunk_row = await db.fetch_one(
                "SELECT user_id FROM document_chunks WHERE id = ?",
                ("chunk-1",),
            )
            assert chunk_row and chunk_row["user_id"] == expected_user_id

            link_row = await db.fetch_one(
                "SELECT user_id FROM thread_docs WHERE thread_id = ?",
                ("legacy-thread",),
            )
            assert link_row and link_row["user_id"] == expected_user_id

            threads = await queries.get_threads(
                db,
                session_id="fresh-session",
                user_id=expected_user_id,
                type_="chat",
                limit=5,
            )
            assert any(t["id"] == "legacy-thread" for t in threads)

            docs = await queries.get_thread_docs(
                db,
                "legacy-thread",
                session_id="fresh-session",
                user_id=expected_user_id,
            )
            assert any(doc["doc_id"] == 1 for doc in docs)
        finally:
            if previous_default is None:
                os.environ.pop("AUTH_DEV_DEFAULT_EMAIL", None)
            else:
                os.environ["AUTH_DEV_DEFAULT_EMAIL"] = previous_default
            await db.disconnect()

    asyncio.run(scenario())
