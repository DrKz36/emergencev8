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
from backend.features.auth.models import AuthConfig
from backend.features.auth.rate_limiter import RateLimiterConfig, SlidingWindowRateLimiter
from backend.features.auth.service import AuthService
from backend.features.auth.router import router as auth_router


class _Container:
    def __init__(self, auth_service: AuthService) -> None:
        self._auth_service = auth_service

    def auth_service(self) -> AuthService:
        return self._auth_service


async def _prepare_app(db_path: Path, allowed_email: str) -> tuple[FastAPI, AuthService, DatabaseManager]:
    db = DatabaseManager(str(db_path))
    await schema.create_tables(db)
    config = AuthConfig(
        secret="rate-secret",
        issuer="rate-issuer",
        audience="rate-audience",
        token_ttl_seconds=3600,
        admin_emails={allowed_email},
    )
    limiter = SlidingWindowRateLimiter(RateLimiterConfig(attempts=2, window_seconds=300))
    auth_service = AuthService(db_manager=db, config=config, rate_limiter=limiter)
    await auth_service.bootstrap()

    app = FastAPI()
    app.include_router(auth_router)
    app.state.service_container = _Container(auth_service)
    return app, auth_service, db


def test_login_rate_limit(tmp_path):
    async def scenario():
        test_email = "tester@example.com"
        app, auth_service, db = await _prepare_app(tmp_path / "auth-rate.db", allowed_email="admin@example.com")
        await auth_service.upsert_allowlist(test_email, role="member", note=None, actor="admin@example.com")

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            # First attempt for non-allowlisted email to trigger limiter quickly
            for attempt in range(3):
                resp = await client.post("/api/auth/login", json={"email": "blocked@example.com"})
                if attempt < 2:
                    assert resp.status_code == 401
                else:
                    assert resp.status_code == 429
                    assert "Retry-After" in resp.headers

            # Successful login should reset limiter for allowed email
            success = await client.post("/api/auth/login", json={"email": test_email})
            assert success.status_code == 200

        await db.disconnect()

    asyncio.run(scenario())

