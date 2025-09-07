from __future__ import annotations

import os, sys, logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, APIRouter, Query
from fastapi.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

logger = logging.getLogger("emergence")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")

# --- PYTHONPATH / ARBO ---
SRC_DIR = Path(__file__).resolve().parent.parent   # -> /app/src
REPO_ROOT = SRC_DIR.parent                         # -> /app
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


# Routers REST/WS
DOCUMENTS_ROUTER = _import_router("backend.features.documents.router")
DASHBOARD_ROUTER = _import_router("backend.features.dashboard.router")
DEBATE_ROUTER    = _import_router("backend.features.debate.router")
CHAT_ROUTER      = _import_router("backend.features.chat.router")  # ← WS
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
    app = FastAPI(title="Émergence API", version="7.2")
    app.state.service_container = container

    # Redirect /route -> /route/
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

    # --- Mount REST routers ---
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

    # WS (chat)
    _mount_router(CHAT_ROUTER)  # pas de prefix → /ws/{session_id}

    # ---------- Extension: /api/memory/tend-garden ----------
    memory_ext = APIRouter(tags=["Memory"])

    @memory_ext.api_route("/tend-garden", methods=["GET", "POST"])
    async def tend_garden(thread_id: Optional[str] = Query(default=None, description="Optionnel: traiter un thread précis")):
        """
        Déclenche la consolidation STM→LTM + vectorisation. Renvoie le rapport du jardinier.
        """
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

    # ---------- Static mounts (frontend) ----------
    # Buts:
    #  - /src/frontend/*  : JS/CSS front (sans exposer /src/backend)
    #  - /assets/*        : images, styles
    #  - /                : sert /app/index.html (html=True) + fallback SPA
    try:
        BASE = REPO_ROOT                   # /app
        SRC_PATH = SRC_DIR                 # /app/src
        FRONTEND_PATH = SRC_PATH / "frontend"
        ASSETS_PATH = BASE / "assets"
        INDEX_PATH = BASE / "index.html"

        # 1) /src → cible prioritaire sur /app/src/frontend ; fallback /app/src si besoin
        if FRONTEND_PATH.exists():
            app.mount("/src", StaticFiles(directory=str(FRONTEND_PATH), html=False), name="src")
            logger.info("Static mount: /src -> /app/src/frontend")
        elif SRC_PATH.exists():
            # Fallback (peut exposer backend ; déconseillé mais garde compat)
            app.mount("/src", StaticFiles(directory=str(SRC_PATH), html=False), name="src")
            logger.warning("Static mount: /src -> /app/src (fallback). Vérifie que /src/backend n'est pas référencé côté UI.")

        # 2) /assets
        if ASSETS_PATH.exists():
            app.mount("/assets", StaticFiles(directory=str(ASSETS_PATH), html=False), name="assets")
            logger.info("Static mount: /assets -> /app/assets")
        else:
            logger.warning("Static mount ignoré : /app/assets introuvable.")

        # 3) / (SPA root) — monter en DERNIER pour ne pas intercepter /api/* ni /ws*
        if INDEX_PATH.exists():
            app.mount("/", StaticFiles(directory=str(BASE), html=True), name="spa-root")
            logger.info("Static mount: / -> /app (html=True, sert index.html)")
        else:
            logger.warning("index.html manquant : / renverra 404.")

    except Exception as e:
        logger.error(f"Impossible de monter les fichiers statiques: {e}")

    return app


app = create_app()
