# src/backend/main.py
from __future__ import annotations

import os, sys, logging, time
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

logger = logging.getLogger("emergence")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")

# --- PYTHONPATH ---
SRC_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = SRC_DIR.parent
sys.path.append(str(REPO_ROOT))

from backend.containers import ServiceContainer
from backend.core.database.schema import initialize_database

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
DEBATE_ROUTER    = _import_router("backend.features.debate.router")
CHAT_ROUTER      = _import_router("backend.features.chat.router")  # ← WS ici
THREADS_ROUTER   = _import_router("backend.features.threads.router")
MEMORY_ROUTER    = _import_router("backend.features.memory.router")
DEV_AUTH_ROUTER  = _import_router("backend.features.dev_auth.router")  # optionnel

def _migrations_dir() -> str:
    return str(Path(__file__).resolve().parent / "core" / "migrations")

async def _startup(container: ServiceContainer):
    logger.info("Démarrage backend Émergence…")
    try:
        db_manager = container.db_manager()
        fast_boot = os.getenv("EMERGENCE_FAST_BOOT") or os.getenv("EMERGENCE_SKIP_MIGRATIONS")
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
        container.wire(modules=[chat_router_module, dashboard_module, documents_module, debate_module])
        logger.info("DI wired (chat|dashboard|documents|debate.router).")
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

def create_app() -> FastAPI:
    container = ServiceContainer()
    app = FastAPI(title="Émergence API", version="7.2")
    app.state.service_container = container

    # 🔒 Redirige automatiquement /route ↔ /route/
    app.router.redirect_slashes = True

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
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
                app.include_router(router, prefix=desired_prefix, tags=getattr(router, "tags", None))
            else:
                app.include_router(router, tags=getattr(router, "tags", None))
            logger.info(f"Router monté: {desired_prefix or '(no-prefix)'}")
        except Exception as e:
            logger.error(f"Échec du montage router {desired_prefix}: {e}")

    _mount_router(DOCUMENTS_ROUTER, "/api/documents")
    _mount_router(DEBATE_ROUTER,    "/api/debate")
    _mount_router(DASHBOARD_ROUTER, "/api/dashboard")
    _mount_router(THREADS_ROUTER,   "/api/threads")
    _mount_router(MEMORY_ROUTER,    "/api/memory")
    _mount_router(DEV_AUTH_ROUTER)  # éventuel

    # ⚠️ WS: **uniquement** features.chat.router (déclare /ws/{session_id})
    _mount_router(CHAT_ROUTER)  # pas de prefix → garde /ws/{session_id}

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
