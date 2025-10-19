# src/backend/main.py
from __future__ import annotations

import logging
import os
import re
import sys
from pathlib import Path
from contextlib import asynccontextmanager
from typing import AsyncGenerator
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
SYNC_ROUTER = _import_router("backend.features.sync.router")  # Auto-sync inter-agents
SETTINGS_ROUTER = _import_router("backend.features.settings.router")  # Application settings
BETA_REPORT_ROUTER = _import_router("backend.features.beta_report.router")  # Beta feedback reports


def _migrations_dir() -> str:
    return str(Path(__file__).resolve().parent / "core" / "migrations")


async def _startup(container: ServiceContainer):
    import time
    startup_start = time.perf_counter()
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

    # 🔥 P2.1 - Warm-up: Pré-charger SBERT et Chroma/Qdrant
    try:
        vector_service = container.vector_service()
        vector_service._ensure_inited()  # Force lazy init NOW
        logger.info(f"VectorService pré-chargé (backend={vector_service.backend}, model={vector_service.embed_model_name})")
    except Exception as e:
        logger.warning(f"VectorService warm-up échoué: {e}")

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

    # Log startup duration
    startup_duration_ms = int((time.perf_counter() - startup_start) * 1000)
    logger.info(f"✅ Startup completed in {startup_duration_ms}ms")


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

        try:
            response = await call_next(request)

            # Vérifier que la réponse est valide
            if response is None:
                logger.error(f"No response returned in DenyListMiddleware for {request.url.path}")
                return PlainTextResponse("Internal server error: no response", status_code=500)

            return response
        except RuntimeError as exc:
            # Gérer le cas où call_next() lève "No response returned"
            if "No response returned" in str(exc):
                logger.error(f"RuntimeError in DenyListMiddleware for {request.url.path}: {exc}")
                return PlainTextResponse("Internal server error: no response", status_code=500)
            raise
        except Exception as exc:
            logger.error(f"Unexpected error in DenyListMiddleware for {request.url.path}: {exc}", exc_info=True)
            return PlainTextResponse("Internal server error", status_code=500)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Lifespan context manager pour gérer l'initialisation et la fermeture des services.
    Remplace les @app.on_event("startup"/"shutdown") pour centraliser le cycle de vie.
    """
    container = app.state.service_container
    logger.info("🚀 Lifespan: Démarrage backend Émergence…")

    # === STARTUP ===
    try:
        await _startup(container)
    except Exception as e:
        logger.error(f"Lifespan startup: _startup failed: {e}", exc_info=True)

    # 🔧 Démarrer MemoryTaskQueue (P1.1)
    try:
        from backend.features.memory.task_queue import get_memory_queue
        queue = get_memory_queue()
        await queue.start()
        logger.info("MemoryTaskQueue started")
    except Exception as e:
        logger.warning(f"MemoryTaskQueue startup failed: {e}")

    # 🔧 Démarrer AutoSyncService
    try:
        from backend.features.sync.auto_sync_service import get_auto_sync_service
        sync_service = get_auto_sync_service()
        await sync_service.start()
        logger.info("AutoSyncService started")
    except Exception as e:
        logger.warning(f"AutoSyncService startup failed: {e}")

    # 🔧 Démarrer le nettoyage automatique des sessions inactives
    try:
        session_manager = container.session_manager()
        session_manager.start_cleanup_task()
        logger.info("SessionManager cleanup task started (inactivity timeout: 3 min)")
    except Exception as e:
        logger.warning(f"SessionManager cleanup task startup failed: {e}")

    logger.info("✅ Lifespan: Backend prêt")

    yield  # Application running

    # === SHUTDOWN ===
    logger.info("🔻 Lifespan: Arrêt backend Émergence…")

    # 🔧 Arrêter MemoryTaskQueue
    try:
        from backend.features.memory.task_queue import get_memory_queue
        queue = get_memory_queue()
        await queue.stop()
        logger.info("MemoryTaskQueue stopped")
    except Exception as e:
        logger.warning(f"MemoryTaskQueue shutdown failed: {e}")

    # 🔧 Arrêter AutoSyncService
    try:
        from backend.features.sync.auto_sync_service import get_auto_sync_service
        sync_service = get_auto_sync_service()
        await sync_service.stop()
        logger.info("AutoSyncService stopped")
    except Exception as e:
        logger.warning(f"AutoSyncService shutdown failed: {e}")

    # 🔧 Arrêter le nettoyage automatique des sessions
    try:
        session_manager = container.session_manager()
        await session_manager.stop_cleanup_task()
        logger.info("SessionManager cleanup task stopped")
    except Exception as e:
        logger.warning(f"SessionManager cleanup task shutdown failed: {e}")

    # Fermer DB
    try:
        await container.db_manager().disconnect()
        logger.info("DB disconnected")
    except Exception as e:
        logger.warning(f"DB disconnect failed: {e}")

    # Fermer VoiceService httpx client si présent
    try:
        voice_client_provider = getattr(container, "voice_http_client", None)
        if voice_client_provider is not None:
            client = voice_client_provider()
            close = getattr(client, "aclose", None)
            if callable(close):
                await close()
                logger.info("VoiceService httpx client closed")
    except Exception as e:
        logger.warning(f"VoiceService client close failed: {e}")

    # Unwire DI
    try:
        container.unwire()
        logger.info("DI container unwired")
    except Exception as e:
        logger.warning(f"Container unwire failed: {e}")

    logger.info("✅ Lifespan: Arrêt backend terminé")


def create_app() -> FastAPI:
    container = ServiceContainer()
    app = FastAPI(
        title="Émergence API",
        version="8.0",
        lifespan=lifespan
    )
    app.state.service_container = container

    # 🔒 Redirige automatiquement /route ↔ /route/
    app.router.redirect_slashes = True

    # Monitoring middlewares (première couche)
    try:
        from backend.core.middleware import (
            MonitoringMiddleware,
            SecurityMiddleware,
            RateLimitMiddleware,
        )
        app.add_middleware(MonitoringMiddleware)
        app.add_middleware(SecurityMiddleware)
        app.add_middleware(RateLimitMiddleware, requests_per_minute=300)  # 300 req/min global
        logger.info("Monitoring middlewares activés (dont rate limiting 300/min)")
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

    @app.get("/api/health", tags=["Health"])
    async def health():
        return {"status": "ok", "message": "Emergence Backend is running."}

    @app.get("/healthz", tags=["Health"], include_in_schema=False)
    async def healthz_simple():
        """Simple liveness check (k8s-style)"""
        return {"ok": True}

    @app.get("/ready", tags=["Health"], include_in_schema=False)
    async def ready_check(request: Request):
        """Readiness check - vérifie DB + Chroma disponibles"""
        try:
            # Check DB
            db_manager = app.state.service_container.db_manager()
            conn = await db_manager._ensure_connection()
            cursor = await conn.execute("SELECT 1")
            await cursor.fetchone()

            # Check VectorService (lazy-load safe)
            vector_service = app.state.service_container.vector_service()
            vector_service._ensure_inited()

            return {"ok": True, "db": "up", "vector": "up"}
        except Exception as e:
            logger.error(f"/ready check failed: {e}")
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=503,
                content={"ok": False, "error": str(e)}
            )

    @app.post("/api/beta-report-test", tags=["Beta"])
    async def beta_report_test():
        return {"status": "test", "message": "Direct endpoint works!"}

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

    _mount_router(BETA_REPORT_ROUTER, "/api")  # Beta report endpoints at /api/beta-report (FIRST!)
    _mount_router(DOCUMENTS_ROUTER, "/api/documents")
    _mount_router(DEBATE_ROUTER, "/api/debate")
    _mount_router(DASHBOARD_ROUTER, "/api/dashboard")
    _mount_router(ADMIN_DASHBOARD_ROUTER, "/api")  # Admin routes at /api/admin/dashboard/*
    _mount_router(BENCHMARKS_ROUTER, "/api/benchmarks")
    _mount_router(THREADS_ROUTER, "/api/threads")
    _mount_router(MEMORY_ROUTER, "/api/memory")
    _mount_router(AUTH_ROUTER)
    _mount_router(DEV_AUTH_ROUTER)  # éventuel
    _mount_router(METRICS_ROUTER)  # Prometheus metrics at /metrics
    _mount_router(MONITORING_ROUTER)  # Monitoring endpoints at /api/monitoring/*
    _mount_router(SYNC_ROUTER, "/api")  # Auto-sync endpoints at /api/sync/*
    _mount_router(SETTINGS_ROUTER)  # Settings endpoints at /api/settings/*

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
        DOCS_PATH = BASE / "docs"
        INDEX_PATH = BASE / "index.html"
        if SRC_PATH.exists():
            app.mount("/src", StaticFiles(directory=str(SRC_PATH)), name="src")
        if ASSETS_PATH.exists():
            app.mount("/assets", StaticFiles(directory=str(ASSETS_PATH)), name="assets")
        if DOCS_PATH.exists():
            app.mount("/docs", StaticFiles(directory=str(DOCS_PATH)), name="docs")
            logger.info(f"Dossier /docs monté: {DOCS_PATH}")
        if INDEX_PATH.exists():
            app.mount("/", StaticFiles(html=True, directory=str(BASE)), name="base")
    except Exception as e:
        logger.error(f"Impossible de monter les fichiers statiques: {e}")

    return app


app = create_app()
