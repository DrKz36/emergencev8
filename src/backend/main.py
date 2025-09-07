from __future__ import annotations

import os
import sys
import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, APIRouter, Query, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from starlette.staticfiles import StaticFiles

# ---------------------------------------------------------------------
# Logger
# ---------------------------------------------------------------------
logger = logging.getLogger("emergence")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)

# ---------------------------------------------------------------------
# Paths (ARBO)
# /app              -> REPO_ROOT
# /app/src          -> SRC_DIR
# /app/src/frontend -> FRONTEND_DIR (exposé)
# /app/assets       -> ASSETS_DIR  (exposé si présent)
# ---------------------------------------------------------------------
SRC_DIR = Path(__file__).resolve().parent.parent   # /app/src
REPO_ROOT = SRC_DIR.parent                         # /app
FRONTEND_DIR = SRC_DIR / "frontend"                # /app/src/frontend
ASSETS_DIR = REPO_ROOT / "assets"                  # /app/assets
INDEX_HTML = REPO_ROOT / "index.html"

# Assure import backend.*
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# DI / DB imports
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
CHAT_ROUTER      = _import_router("backend.features.chat.router")      # WS
THREADS_ROUTER   = _import_router("backend.features.threads.router")
MEMORY_ROUTER    = _import_router("backend.features.memory.router")
DEV_AUTH_ROUTER  = _import_router("backend.features.dev_auth.router")  # optionnel


def _migrations_dir() -> str:
    return str(Path(__file__).resolve().parent / "core" / "migrations")


async def _startup(container: ServiceContainer):
    logger.info("Démarrage backend Émergence…")
    # DB init (safe-boot)
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

    # Wire DI
    try:
        import backend.features.chat.router as chat_router_module
        import backend.features.dashboard.router as dashboard_module
        import backend.features.documents.router as documents_module
        import backend.features.debate.router as debate_module
        container.wire(modules=[chat_router_module, dashboard_module, documents_module, debate_module])
        logger.info("DI wired (chat|dashboard|documents|debate.router).")
    except Exception as e:
        logger.warning(f"Wire DI partiel: {e}")

    # MemoryAnalyzer hook
    try:
        analyzer = container.memory_analyzer()
        chat_svc = container.chat_service()
        analyzer.set_chat_service(chat_svc)
        logger.info("MemoryAnalyzer hook: ChatService injecté (ready=True).")
    except Exception as e:
        logger.warning(f"MemoryAnalyzer hook non appliqué: {e}")


def create_app() -> FastAPI:
    container = ServiceContainer()
    app = FastAPI(title="Émergence API", version="7.4")
    app.state.service_container = container
    app.router.redirect_slashes = True

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
    )

    @app.on_event("startup")
    async def _on_startup():
        await _startup(container)
        logger.info("Static mounts v7.4: FRONTEND=%s | ASSETS=%s | INDEX=%s",
                    FRONTEND_DIR.exists(), ASSETS_DIR.exists(), INDEX_HTML.exists())

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

    # -------------------------- Health --------------------------
    @app.get("/api/health", tags=["Health"])
    async def health():
        return {"status": "ok", "message": "Emergence Backend is running."}

    # ----------------------- REST / WS --------------------------
    def _mount_router(router, prefix: str | None = None):
        if not router:
            return
        try:
            if prefix:
                app.include_router(router, prefix=prefix, tags=getattr(router, "tags", None))
            else:
                app.include_router(router, tags=getattr(router, "tags", None))
            logger.info(f"Router monté: {prefix or '(no-prefix)'}")
        except Exception as e:
            logger.error(f"Échec montage router {prefix}: {e}")

    _mount_router(DOCUMENTS_ROUTER, "/api/documents")
    _mount_router(DEBATE_ROUTER,    "/api/debate")
    _mount_router(DASHBOARD_ROUTER, "/api/dashboard")
    _mount_router(THREADS_ROUTER,   "/api/threads")
    _mount_router(MEMORY_ROUTER,    "/api/memory")
    _mount_router(DEV_AUTH_ROUTER)  # éventuel
    _mount_router(CHAT_ROUTER)      # WS (ex: /ws/{session_id})

    # -------- Extension mémoire: /api/memory/tend-garden -------
    memory_ext = APIRouter(tags=["Memory"])

    @memory_ext.api_route("/tend-garden", methods=["GET", "POST"])
    async def tend_garden(thread_id: Optional[str] = Query(default=None, description="Optionnel: traiter un thread précis")):
        try:
            from backend.features.memory.gardener import MemoryGardener
            db  = app.state.service_container.db_manager()
            vec = app.state.service_container.vector_service()
            anl = app.state.service_container.memory_analyzer()
            gardener = MemoryGardener(db_manager=db, vector_service=vec, analyzer=anl)
            report = await gardener.tend_the_garden(thread_id=thread_id)
            return {"status": "success", "report": report}
        except Exception as e:
            logger.error(f"tend-garden failed: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    app.include_router(memory_ext, prefix="/api/memory")

    # --------------------- Static front -------------------------
    # ⚠ Sécurité :
    #   - On N'EXPOSE PAS /app ni /app/src complet.
    #   - /src = UNIQUEMENT /app/src/frontend
    #   - /assets = /app/assets (si présent)
    #   - "/" : on renvoie index.html explicitement (pas de StaticFiles sur /)
    if FRONTEND_DIR.exists():
        app.mount("/src", StaticFiles(directory=str(FRONTEND_DIR), html=False), name="src")
        logger.info("Static mount: /src -> /app/src/frontend")
    else:
        logger.warning("Static mount ignoré: /app/src/frontend introuvable.")

    if ASSETS_DIR.exists():
        app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR), html=False), name="assets")
        logger.info("Static mount: /assets -> /app/assets")
    else:
        logger.warning("Static mount ignoré: /app/assets introuvable.")

    # Root file server — rendu index.html, SANS exposer l'arbo
    @app.get("/", include_in_schema=False)
    async def serve_root():
        if INDEX_HTML.exists():
            return FileResponse(str(INDEX_HTML))
        raise HTTPException(status_code=404, detail="Not Found")

    # SPA fallback : toute route non /api/* ni /ws* renvoie index.html
    @app.get("/{path:path}", include_in_schema=False)
    async def spa_fallback(path: str, request: Request):
        # Ne pas intercepter /api/* ni /ws*
        if path.startswith("api") or path.startswith("ws"):
            raise HTTPException(status_code=404, detail="Not Found")
        if INDEX_HTML.exists():
            return FileResponse(str(INDEX_HTML))
        raise HTTPException(status_code=404, detail="Not Found")

    return app


app = create_app()
