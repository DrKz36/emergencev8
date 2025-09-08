from __future__ import annotations

import os, sys, logging
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, APIRouter, Query, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from starlette.staticfiles import StaticFiles

APP_VERSION = "7.4.2"
logger = logging.getLogger("emergence")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")

SRC_DIR      = Path(__file__).resolve().parent.parent      # /app/src
REPO_ROOT    = SRC_DIR.parent                               # /app
FRONTEND_SRC = SRC_DIR / "frontend"                         # /app/src/frontend (dev + compat prod)
ASSETS_DIR   = REPO_ROOT / "assets"                         # /app/assets
STATIC_DIR   = Path(os.environ.get("STATIC_DIR", "/app/static"))  # /app/static (build dist)
INDEX_DEV    = REPO_ROOT / "index.html"
INDEX_DIST   = STATIC_DIR / "index.html"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from backend.containers import ServiceContainer
from backend.core.database.schema import initialize_database

def _import_router(dotted: str):
    try:
        module = __import__(dotted, fromlist=["router"])
        return getattr(module, "router", None)
    except Exception as e:
        logger.warning(f"Router non trouvé: {dotted} — {e}")
        return None

DOCUMENTS_ROUTER = _import_router("backend.features.documents.router")
DASHBOARD_ROUTER = _import_router("backend.features.dashboard.router")
DEBATE_ROUTER    = _import_router("backend.features.debate.router")
CHAT_ROUTER      = _import_router("backend.features.chat.router")
THREADS_ROUTER   = _import_router("backend.features.threads.router")
MEMORY_ROUTER    = _import_router("backend.features.memory.router")
DEV_AUTH_ROUTER  = _import_router("backend.features.dev_auth.router")

def _migrations_dir() -> str:
    return str(Path(__file__).resolve().parent / "core" / "migrations")

async def _startup(container: ServiceContainer):
    logger.info("Démarrage backend Émergence…")
    try:
        db_manager = container.db_manager()
        fast_boot = os.getenv("EMERGENCE_FAST_BOOT") or os.getenv("EMERGENCE_SKIP_MIGRATIONS")
        if fast_boot:
            await db_manager.connect()
        else:
            await initialize_database(db_manager, _migrations_dir())
        logger.info("DB prête.")
    except Exception as e:
        logger.warning(f"Init DB partielle: {e}")

    # DI
    try:
        import backend.features.chat.router as chat_router_module
        import backend.features.dashboard.router as dashboard_module
        import backend.features.documents.router as documents_module
        import backend.features.debate.router as debate_module
        container.wire(modules=[chat_router_module, dashboard_module, documents_module, debate_module])
    except Exception as e:
        logger.warning(f"Wire DI partiel: {e}")

    logger.info(
        "Static mounts v%s: STATIC_DIR=%s(exists=%s) | ASSETS=%s(exists=%s) | FRONTEND_SRC=%s(exists=%s) | INDEX_DEV=%s(exists=%s)",
        APP_VERSION, STATIC_DIR, STATIC_DIR.exists(), ASSETS_DIR, ASSETS_DIR.exists(),
        FRONTEND_SRC, FRONTEND_SRC.exists(), INDEX_DEV, INDEX_DEV.exists()
    )

def create_app() -> FastAPI:
    container = ServiceContainer()
    app = FastAPI(title="Émergence API", version=APP_VERSION)
    app.state.service_container = container
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
        try:    await container.db_manager().disconnect()
        except: pass
        try:    container.unwire()
        except: pass
        logger.info("Arrêt backend Émergence terminé.")

    # Health
    @app.get("/api/health", tags=["Health"])
    async def health(response: Response):
        response.headers["X-App-Version"] = APP_VERSION
        return {"status": "ok", "message": "Emergence Backend is running.", "version": APP_VERSION}

    # Routers REST/WS
    def _mount_router(router, prefix: Optional[str] = None):
        if not router: return
        try:
            app.include_router(router, prefix=prefix) if prefix else app.include_router(router)
            logger.info(f"Router monté: {prefix or '(no-prefix)'}")
        except Exception as e:
            logger.error(f"Échec montage router {prefix}: {e}")

    _mount_router(DOCUMENTS_ROUTER, "/api/documents")
    _mount_router(DEBATE_ROUTER,    "/api/debate")
    _mount_router(DASHBOARD_ROUTER, "/api/dashboard")
    _mount_router(THREADS_ROUTER,   "/api/threads")
    _mount_router(MEMORY_ROUTER,    "/api/memory")
    _mount_router(DEV_AUTH_ROUTER)
    _mount_router(CHAT_ROUTER)

    # ---------- Statics ----------
    # 1) Prod: dist/ prioritaire (index de build)
    if STATIC_DIR.exists() and INDEX_DIST.exists():
        app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static-root")
        logger.info("Static root (dist) monté sur / -> %s", STATIC_DIR)
    else:
        # Dev fallback sur index.html racine si dist absent
        @app.get("/", include_in_schema=False)
        async def _index_dev():
            if INDEX_DEV.exists():
                return FileResponse(str(INDEX_DEV))
            raise HTTPException(status_code=404, detail="Not Found")

    # 2) Compat immédiate: /src -> /app/src/frontend (uniquement FE, pas le backend)
    if FRONTEND_SRC.exists():
        app.mount("/src", StaticFiles(directory=str(FRONTEND_SRC), html=False), name="src-frontend")
        logger.info("Compat: /src -> %s", FRONTEND_SRC)

    # 3) /assets (logos, favicons)
    if ASSETS_DIR.exists():
        app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR), html=False), name="assets")

    return app

app = create_app()
