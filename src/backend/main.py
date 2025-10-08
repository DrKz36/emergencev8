# src/backend/main.py
from __future__ import annotations

import logging
import os
import re
import sys
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, PlainTextResponse
from starlette.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("emergence")
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s"
)

# --- PYTHONPATH ---
SRC_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = SRC_DIR.parent

# Ajoute explicitement le dossier `src/` pour que les imports `backend.*` fonctionnent
# même lorsque le fichier est lancé directement (`python src/backend/main.py`).
# L'ancien comportement n'ajoutait que la racine du dépôt, ce qui laissait le
# package `backend` introuvable et empêchait le démarrage du serveur.
for path in (SRC_DIR, REPO_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.append(path_str)

from backend.containers import ServiceContainer  # noqa: E402
from backend.core.database.schema import initialize_database  # noqa: E402
from backend.core.config import DENYLIST_ENABLED, DENYLIST_PATTERNS  # noqa: E402


def _import_router(dotted: str):
    try:
        module = __import__(dotted, fromlist=["router"])
        return getattr(module, "router", None)
    except Exception as e:
        logger.warning(f"Router non trouvé: {dotted} — {e}")
        return None


# Routers REST/WS
DOCUMENTS_ROUTER = _import_router("backend.features.documents.router")
DASHBOARD_ROUTER = _import_router("backend.features.dashboard.router")
ADMIN_DASHBOARD_ROUTER = _import_router("backend.features.dashboard.admin_router")
DEBATE_ROUTER = _import_router("backend.features.debate.router")
BENCHMARKS_ROUTER = _import_router("backend.features.benchmarks.router")
CHAT_ROUTER = _import_router("backend.features.chat.router")  # ← WS ici
THREADS_ROUTER = _import_router("backend.features.threads.router")
MEMORY_ROUTER = _import_router("backend.features.memory.router")
AUTH_ROUTER = _import_router("backend.features.auth.router")
DEV_AUTH_ROUTER = _import_router("backend.features.dev_auth.router")  # optionnel
METRICS_ROUTER = _import_router("backend.features.metrics.router")  # Prometheus metrics
MONITORING_ROUTER = _import_router("backend.features.monitoring.router")  # Monitoring & observability


def _migrations_dir() -> str:
    return str(Path(__file__).resolve().parent / "core" / "migrations")


async def _startup(container: ServiceContainer):
    logger.info("Démarrage backend Émergence…")
    try:
        db_manager = container.db_manager()
        fast_boot = os.getenv("EMERGENCE_FAST_BOOT") or os.getenv(
            "EMERGENCE_SKIP_MIGRATIONS"
        )
        if fast_boot:
            await db_manager.connect()
            logger.info("DB connectée (FAST_BOOT=on).")
        else:
            await initialize_database(db_manager, _migrations_dir())
            logger.info("DB initialisée (migrations exécutées).")
    except Exception as e:
        logger.warning(f"Initialisation DB partielle: {e}")

    # Wire DI (inclut chat.router → Provide[...] ok)
    try:
        import backend.features.chat.router as chat_router_module
        import backend.features.dashboard.router as dashboard_module
        import backend.features.documents.router as documents_module
        import backend.features.debate.router as debate_module
        import backend.features.benchmarks.router as benchmarks_module

        container.wire(
            modules=[
                chat_router_module,
                dashboard_module,
                documents_module,
                debate_module,
                benchmarks_module,
            ]
        )
        logger.info("DI wired (chat|dashboard|documents|debate|benchmarks.router).")
    except Exception as e:
        logger.warning(f"Wire DI partiel: {e}")

    # 🔗 MemoryAnalyzer ← ChatService (hook P0)
    try:
        analyzer = container.memory_analyzer()
        chat_svc = container.chat_service()
        analyzer.set_chat_service(chat_svc)
        logger.info("MemoryAnalyzer hook: ChatService injecté (ready=True).")
    except Exception as e:
        logger.warning(f"MemoryAnalyzer hook non appliqué: {e}")


    try:
        auth_service = container.auth_service()
        await auth_service.bootstrap()
        logger.info("AuthService bootstrap terminé.")
    except Exception as e:
        logger.warning(f"AuthService bootstrap non appliqué: {e}")


# --- Middleware Deny-list (404 early) ---
class DenyListMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, enabled: bool, patterns: list[str]):
        super().__init__(app)
        self.enabled = enabled
        self.patterns = [(p, re.compile(p, re.IGNORECASE)) for p in patterns]

    async def dispatch(self, request: Request, call_next):
        if self.enabled and request.scope.get("type") == "http":
            path = request.url.path
            for raw, rx in self.patterns:
                if rx.search(path):
                    logger.info(f"DenyList: 404 bloqué path={path} (pattern={raw})")
                    return PlainTextResponse("Not Found", status_code=404)
        return await call_next(request)


def create_app() -> FastAPI:
    container = ServiceContainer()
    app = FastAPI(title="Émergence API", version="7.2")
    app.state.service_container = container

    # 🔒 Redirige automatiquement /route ↔ /route/
    app.router.redirect_slashes = True

    # Monitoring middlewares (première couche)
    try:
        from backend.core.middleware import (
            MonitoringMiddleware,
            SecurityMiddleware,
        )
        app.add_middleware(MonitoringMiddleware)
        app.add_middleware(SecurityMiddleware)
        logger.info("Monitoring middlewares activés")
    except Exception as e:
        logger.warning(f"Monitoring middlewares non activés: {e}")

    # CORS d'abord...
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # ...puis DenyList en dernier pour être outermost (court-circuit rapide)
    app.add_middleware(
        DenyListMiddleware, enabled=DENYLIST_ENABLED, patterns=DENYLIST_PATTERNS
    )

    @app.on_event("startup")
    async def _on_startup():
        await _startup(container)

    @app.on_event("shutdown")
    async def _on_shutdown():
        try:
            await container.db_manager().disconnect()
        except Exception:
            pass
        try:
            voice_client_provider = getattr(container, "voice_http_client", None)
            if voice_client_provider is not None:
                client = voice_client_provider()
                close = getattr(client, "aclose", None)
                if callable(close):
                    await close()
        except Exception:
            pass
        try:
            container.unwire()
        except Exception:
            pass
        logger.info("Arrêt backend Émergence terminé.")

    @app.get("/api/health", tags=["Health"])
    async def health():
        return {"status": "ok", "message": "Emergence Backend is running."}

    # --- Mount REST routers (prefix si nécessaire) ---
    def _mount_router(router, desired_prefix: str = ""):
        if router is None:
            return
        try:
            if desired_prefix:
                app.include_router(
                    router, prefix=desired_prefix, tags=getattr(router, "tags", None)
                )
            else:
                app.include_router(router, tags=getattr(router, "tags", None))
            logger.info(f"Router monté: {desired_prefix or '(no-prefix)'}")
        except Exception as e:
            logger.error(f"Échec du montage router {desired_prefix}: {e}")

    _mount_router(DOCUMENTS_ROUTER, "/api/documents")
    _mount_router(DEBATE_ROUTER, "/api/debate")
    _mount_router(DASHBOARD_ROUTER, "/api/dashboard")
    _mount_router(ADMIN_DASHBOARD_ROUTER, "/api")  # Admin routes at /api/admin/dashboard/*
    _mount_router(BENCHMARKS_ROUTER, "/api/benchmarks")
    _mount_router(THREADS_ROUTER, "/api/threads")
    _mount_router(MEMORY_ROUTER, "/api/memory")
    _mount_router(AUTH_ROUTER)
    _mount_router(DEV_AUTH_ROUTER)  # éventuel
    _mount_router(METRICS_ROUTER, "/api")  # Prometheus metrics at /api/metrics
    _mount_router(MONITORING_ROUTER)  # Monitoring endpoints at /api/monitoring/*

    # ⚠️ WS: **uniquement** features.chat.router (déclare /ws/{session_id})
    _mount_router(CHAT_ROUTER)  # pas de prefix → garde /ws/{session_id}

    # 🔁 Redirect dev-only : /auth.html → /dev-auth.html si AUTH_DEV_MODE actif
    try:
        if str(os.getenv("AUTH_DEV_MODE", "0")).lower() in {"1", "true", "yes", "on"}:

            @app.get("/auth.html", include_in_schema=False)
            async def _auth_redirect():
                return RedirectResponse(url="/dev-auth.html", status_code=302)
    except Exception as e:
        logger.warning(f"Redirect /auth.html non installé: {e}")

    # Static (best-effort)
    try:
        BASE = REPO_ROOT
        SRC_PATH = BASE / "src"
        ASSETS_PATH = BASE / "assets"
        INDEX_PATH = BASE / "index.html"
        if SRC_PATH.exists():
            app.mount("/src", StaticFiles(directory=str(SRC_PATH)), name="src")
        if ASSETS_PATH.exists():
            app.mount("/assets", StaticFiles(directory=str(ASSETS_PATH)), name="assets")
        if INDEX_PATH.exists():
            app.mount("/", StaticFiles(html=True, directory=str(BASE)), name="base")
    except Exception as e:
        logger.error(f"Impossible de monter les fichiers statiques: {e}")

    return app


app = create_app()
