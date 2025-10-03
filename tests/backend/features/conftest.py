import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pytest
from fastapi import FastAPI

ROOT_DIR = Path(__file__).resolve().parents[3]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from backend.core.database import schema
from backend.core.database.manager import DatabaseManager
from backend.features.auth.models import AuthConfig
from backend.features.auth.router import router as auth_router
from backend.features.auth.service import AuthService


@dataclass
class AuthTestContext:
    app: FastAPI
    service: AuthService
    db: DatabaseManager


class _AuthContainer:
    def __init__(self, auth_service: AuthService) -> None:
        self._auth_service = auth_service

    def auth_service(self) -> AuthService:
        return self._auth_service


@pytest.fixture
def auth_app_factory(tmp_path):
    created: list[AuthTestContext] = []

    async def _create(
        name: str,
        *,
        admin_emails: Iterable[str] | None = None,
        dev_mode: bool = False,
        dev_default_email: str | None = None,
        token_ttl_seconds: int = 3600,
        rate_limiter=None,
    ) -> AuthTestContext:
        db_path = tmp_path / f"{name}.db"
        db = DatabaseManager(str(db_path))
        await schema.create_tables(db)
        config = AuthConfig(
            secret=f"{name}-secret",
            issuer="tests.emergence",
            audience="tests.emergence",
            token_ttl_seconds=token_ttl_seconds,
            admin_emails=set(admin_emails or []),
            dev_mode=dev_mode,
            dev_default_email=dev_default_email,
        )
        service = AuthService(db_manager=db, config=config, rate_limiter=rate_limiter)
        await service.bootstrap()

        app = FastAPI()
        app.include_router(auth_router)
        app.state.service_container = _AuthContainer(service)

        context = AuthTestContext(app=app, service=service, db=db)
        created.append(context)
        return context

    yield _create

    for context in created:
        asyncio.run(context.db.disconnect())
