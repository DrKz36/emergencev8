# ruff: noqa: E402
import asyncio
import sys
from pathlib import Path

from httpx import ASGITransport, AsyncClient

ROOT_DIR = Path(__file__).resolve().parents[3]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from backend.features.auth.rate_limiter import RateLimiterConfig, SlidingWindowRateLimiter


def test_login_rate_limit(auth_app_factory):
    async def scenario():
        test_email = "tester@example.com"
        limiter = SlidingWindowRateLimiter(RateLimiterConfig(attempts=2, window_seconds=300))
        ctx = await auth_app_factory(
            "auth-rate",
            admin_emails={"admin@example.com"},
            rate_limiter=limiter,
        )
        await ctx.service.upsert_allowlist(
            test_email,
            role="member",
            note=None,
            actor="admin@example.com",
            password="TesterPass123!",
        )

        transport = ASGITransport(app=ctx.app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            for attempt in range(3):
                resp = await client.post(
                    "/api/auth/login",
                    json={"email": "blocked@example.com", "password": "WrongPass123!"},
                )
                if attempt < 2:
                    assert resp.status_code == 401
                else:
                    assert resp.status_code == 429
                    assert "Retry-After" in resp.headers

            success = await client.post(
                "/api/auth/login",
                json={"email": test_email, "password": "TesterPass123!"},
            )
            assert success.status_code == 200

    asyncio.run(scenario())
