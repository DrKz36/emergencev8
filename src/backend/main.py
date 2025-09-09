from __future__ import annotations

import os, sys, logging, re
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse
from starlette.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import PlainTextResponse

APP_VERSION = "7.5.2"  # +patch denylist
logger = logging.getLogger("emergence")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")

SRC_DIR      = Path(__file__).resolve().parent.parent           # /app/src
REPO_ROOT    = SRC_DIR.parent                                   # /app
FRONTEND_SRC = SRC_DIR / "frontend"                             # /app/src/frontend
ASSETS_DIR   = REPO_ROOT / "assets"                             # /app/assets  (repo)
STATIC_DIR   = Path(os.environ.get("STATIC_DIR", "/app/static"))# /app/static  (build Vite)
INDEX_DEV    = REPO_ROOT / "index.html"
INDEX_DIST   = STATIC_DIR / "index.html"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# --- Routers import (conservé) ---
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

# ---------------------- Security: Denylist Middleware ----------------------
_DENY_PATTERNS = [
    re.compile(r"^/\.git(?:/|$)"),  # enforce 403 for any /.git path
    # NOTE: ajouter d’autres patterns si nécessaire (ex: r"^/\.env$")
]

class DenylistMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        path = request.scope.get("path", "")
        for pat in _DENY_PATTERNS:
            if pat.match(path):
                # Short-circuit BEFORE any static mount or SPA fallback
                return PlainTextResponse("Forbidden", status_code=403)
        return await call_next(request)
# ---------------------------------------------------------------------------

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

    # DI wire (logs si modules absents)
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

    # Security first: deny sensitive paths BEFORE anything else
    app.add_middleware(DenylistMiddleware)

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
    _mount_router(CHAT_ROUTER)  # contient WS: /ws/{session_id}

    # ---------- Statics ----------
    # 0) Assets Vite en priorité sur /assets (résout les 404)
    vite_assets = STATIC_DIR / "assets"
    if vite_assets.exists():
        app.mount("/assets", StaticFiles(directory=str(vite_assets), html=False), name="vite-assets")
        logger.info("Mount /assets -> %s (vite build)", vite_assets)
    elif ASSETS_DIR.exists():
        app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR), html=False), name="repo-assets")
        logger.info("Mount /assets -> %s (repo assets)", ASSETS_DIR)

    # 1) Compat immédiate: /src -> /app/src/frontend (uniquement FE)
    if FRONTEND_SRC.exists():
        app.mount("/src", StaticFiles(directory=str(FRONTEND_SRC), html=False), name="src-frontend")
        logger.info("Compat: /src -> %s", FRONTEND_SRC)

    # 2) Build Vite complète exposée sous /static (html=True pour servir index directement si besoin)
    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR), html=True), name="static-dist")
        logger.info("Mount /static -> %s", STATIC_DIR)

    # 3) SPA catch-all GET, sans casser /api|/ws|/assets|/src
    @app.get("/", include_in_schema=False)
    async def _root():
        if INDEX_DIST.exists(): return FileResponse(str(INDEX_DIST))
        if INDEX_DEV.exists():  return FileResponse(str(INDEX_DEV))
        return PlainTextResponse("UI unavailable", status_code=503)

    @app.get("/{full_path:path}", include_in_schema=False)
    async def _spa(full_path: str):
        # La denylist est déjà appliquée par le middleware. On protège ici les prefixes API/WS/STATIQUES.
        if re.match(r"^(api|ws|assets|src)(/|$)", full_path):
            raise HTTPException(status_code=404, detail="Not Found")
        if INDEX_DIST.exists(): return FileResponse(str(INDEX_DIST))
        if INDEX_DEV.exists():  return FileResponse(str(INDEX_DEV))
        return PlainTextResponse("UI unavailable", status_code=503)

    return app

app = create_app()
