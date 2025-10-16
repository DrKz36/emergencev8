import asyncio
import json


def test_bootstrap_seeds_allowlist_from_env(auth_app_factory, monkeypatch):
    monkeypatch.setenv(
        "AUTH_ALLOWLIST_SEED",
        json.dumps(
            [
                {
                    "email": "seed@example.com",
                    "password": "SeedPass123!",
                    "role": "member",
                    "note": "seed-entry",
                }
            ]
        ),
    )

    async def scenario():
        ctx = await auth_app_factory("auth-bootstrap-seed", admin_emails=set())
        row = await ctx.db.fetch_one(
            "SELECT email, role, password_hash, password_must_reset FROM auth_allowlist WHERE email = ?",
            ("seed@example.com",),
        )
        assert row is not None
        assert row["role"] == "member"
        password_hash = row["password_hash"]
        assert isinstance(password_hash, str) and password_hash.startswith("$2")
        # Non-admin entries should still require a password reset by default
        assert row["password_must_reset"] in (1, True)

    asyncio.run(scenario())


def test_bootstrap_seed_skips_invalid_entries(auth_app_factory, monkeypatch):
    monkeypatch.setenv(
        "AUTH_ALLOWLIST_SEED",
        json.dumps(
            [
                {"email": "   "},
                "not-a-dict",
                {"role": "member"},  # missing email
            ]
        ),
    )

    async def scenario():
        ctx = await auth_app_factory("auth-bootstrap-invalid", admin_emails=set())
        row = await ctx.db.fetch_one(
            "SELECT COUNT(*) AS count FROM auth_allowlist",
        )
        assert row is not None
        assert row["count"] == 0

    asyncio.run(scenario())


def test_bootstrap_seed_from_file(auth_app_factory, monkeypatch, tmp_path):
    payload = [
        {
            "email": "file-seed@example.com",
            "password": "FileSeedPass123!",
            "role": "admin",
            "note": "seed-from-file",
        }
    ]
    seed_file = tmp_path / "allowlist_seed.json"
    seed_file.write_text(json.dumps(payload), encoding="utf-8")

    monkeypatch.delenv("AUTH_ALLOWLIST_SEED", raising=False)
    monkeypatch.setenv("AUTH_ALLOWLIST_SEED_PATH", str(seed_file))

    async def scenario():
        ctx = await auth_app_factory("auth-bootstrap-file", admin_emails=set())
        row = await ctx.db.fetch_one(
            "SELECT email, role, password_hash, password_must_reset FROM auth_allowlist WHERE email = ?",
            ("file-seed@example.com",),
        )
        assert row is not None
        assert row["role"] == "admin"
        assert row["password_hash"]
        # Admin seed should have password_must_reset cleared.
        assert row["password_must_reset"] in (0, False, None)

    asyncio.run(scenario())
