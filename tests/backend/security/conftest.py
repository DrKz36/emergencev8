import asyncio
import sys
from pathlib import Path
from typing import Iterable
from dataclasses import dataclass

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

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

    def _create(
        name: str = "security_test",
        *,
        admin_emails: Iterable[str] | None = None,
        dev_mode: bool = False,
        dev_default_email: str | None = None,
        token_ttl_seconds: int = 3600,
        rate_limiter=None,
    ) -> FastAPI:
        """Simplifié pour retourner directement l'app (non async)"""
        db_path = tmp_path / f"{name}.db"
        db = DatabaseManager(str(db_path))

        # Création synchrone pour compatibilité
        async def _setup():
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
            return service

        service = asyncio.run(_setup())

        app = FastAPI()
        app.include_router(auth_router)
        app.state.service_container = _AuthContainer(service)

        context = AuthTestContext(app=app, service=service, db=db)
        created.append(context)
        return app

    yield _create

    for context in created:
        asyncio.run(context.db.disconnect())


@pytest.fixture
def client(auth_app_factory):
    """Client de test avec app authentifiée"""
    app = auth_app_factory()
    return TestClient(app)


@pytest.fixture
def authenticated_user(auth_app_factory):
    """Utilisateur authentifié pour les tests"""
    # Pour l'instant, retourne juste un placeholder
    # Les tests E2E créeront de vrais users
    return {"email": "test@security.local", "id": 1}
