# src/backend/main.py
# V7.1 — Startup robuste : DB + DI + injection tardive ChatService->MemoryAnalyzer + routers + statiques.
from __future__ import annotations

import os
import time
import importlib
import logging
from pathlib import Path
from typing import Optional, Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

from backend.core.database.schema import initialize_database
from backend.containers import ServiceContainer

logger = logging.getLogger("emergence")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")


# --- Mini timer de boot -------------------------------------------------------
class _BootTimer:
    def __init__(self, label: str = "BOOT"):
        self.label = label
        self._t0 = time.perf_counter()
        self._marks = []

    def mark(self, name: str) -> None:
        t = time.perf_counter()
        dt = (t - (self._marks[-1][1] if self._marks else self._t0)) * 1000
        cum = (t - self._t0) * 1000
        logger.info(f"[{self.label}] {name}: +{dt:.1f} ms (cum {cum:.1f} ms)")
        self._marks.append((name, t))

    def dump_to_file(self, path: Optional[str]) -> None:
        if not path:
            return
        try:
            with open(path, "a", encoding="utf-8") as f:
                for name, t in self._marks:
                    f.write(f"{self.label};{name};{t - self._t0:.6f}\n")
        except Exception:
            pass


# --- Helpers -----------------------------------------------------------------
def _import_router(module_path: str):
    try:
        module = importlib.import_module(module_path)
        return module
    except Exception as e:
        logger.warning(f"Impossible d'importer {module_path}: {e}")
        return None


DOCUMENTS_ROUTER = _import_router("backend.features.documents.router")
DASHBOARD_ROUTER = _import_router("backend.features.dashboard.router")
DEBATE_ROUTER    = _import_router("backend.features.debate.router")
CHAT_ROUTER      = _import_router("backend.features.chat.router")
MEMORY_ROUTER    = _import_router("backend.features.memory.router")


def _migrations_dir() -> str:
    # Aligné sur l'arbo: src/backend/core/migrations
    return str(Path(__file__).resolve().parent / "core" / "migrations")


# --- Startup / Shutdown -------------------------------------------------------
async def _startup(container: ServiceContainer):
    t = _BootTimer()
    logger.info("Démarrage backend Émergence…")

    # 1) DB ready (fast boot option)
    fast_boot = os.getenv("EMERGENCE_FAST_BOOT") or os.getenv("EMERGENCE_SKIP_MIGRATIONS")
    try:
        db_manager = container.db_manager()
        if fast_boot:
            await db_manager.connect()
            logger.info("DB connectée (FAST_BOOT=on). Migrations reportées au premier usage.")
        else:
            await initialize_database(db_manager, _migrations_dir())
            logger.info("DB initialisée (migrations exécutées).")
    except Exception as e:
        logger.warning(f"Initialisation DB partielle/repoussée: {e}")
    t.mark("db_ready")

    # 2) Wire DI (chat / debate / memory)
    try:
        import backend.features.chat.router as chat_router_module      # type: ignore
        import backend.features.debate.router as debate_router_module  # type: ignore
        import backend.features.memory.router as memory_router_module  # type: ignore
        container.wire(modules=[chat_router_module, debate_router_module, memory_router_module])
        logger.info("DI wired (chat.router, debate.router).")
    except Exception as e:
        logger.warning(f"Wire DI partiel: {e}")
    t.mark("di_wired")

    # 3) Injection tardive (ChatService -> MemoryAnalyzer)
    try:
        analyzer = container.memory_analyzer()
        chat = container.chat_service()
        # SessionManager a déjà reçu memory_analyzer via DI ; on relie ici le ChatService à l’analyseur
        analyzer.set_chat_service(chat)
    except Exception as e:
        logger.warning(f"Injection tardive MemoryAnalyzer/ChatService: {e}")

    # 4) Dump facultatif des métriques de boot
    t.dump_to_file(os.getenv("EMERGENCE_BOOT_LOG"))
    t.mark("startup_done")


async def _shutdown(container: ServiceContainer):
    try:
        db_manager = container.db_manager()
        await db_manager.disconnect()
    except Exception as e:
        logger.warning(f"Arrêt DB: {e}")
    try:
        container.unwire()
    except Exception as e:
        logger.warning(f"Unwire DI: {e}")
    logger.info("Arrêt backend Émergence terminé.")


def create_app() -> FastAPI:
    t = _BootTimer("BOOT-APP")
    container = ServiceContainer()
    t.mark("container_ready")

    app = FastAPI(title="Émergence API", version="7.1")
    app.state.service_container = container

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    t.mark("middleware_ready")

    @app.on_event("startup")
    async def _on_startup():
        await _startup(container)

    @app.on_event("shutdown")
    async def _on_shutdown():
        await _shutdown(container)

    # --- PUBLIC: Healthcheck (exempt de toute auth applicative) ---------------
    @app.get("/api/health", tags=["Public"])
    async def health():
        return {"status": "ok", "message": "Emergence Backend is running."}

    # --- Montage des routers REST --------------------------------------------
    def _mount_router(router_module: Any, prefix: str, name: str) -> None:
        if router_module and getattr(router_module, "router", None):
            app.include_router(router_module.router, prefix=prefix)
            logger.info(f"Router monté: {router_module} (prefix effectif: {prefix})")

    _mount_router(DOCUMENTS_ROUTER, "/api/documents", "documents")
    _mount_router(DEBATE_ROUTER,    "/api/debate",    "debate")
    _mount_router(DASHBOARD_ROUTER, "/api/dashboard", "dashboard")
    _mount_router(MEMORY_ROUTER,    "/api/memory",    "memory")
    # Le router WebSocket « chat » est dans features.chat.router
    if CHAT_ROUTER and getattr(CHAT_ROUTER, "router", None):
        app.include_router(CHAT_ROUTER.router)
        logger.info("Router WebSocket 'chat' monté.")

    # --- Fichiers statiques ---------------------------------------------------
    # Racine du projet (2 niveaux au-dessus de backend/)
    static_dir = Path(__file__).resolve().parents[2]
    if static_dir.exists():
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
        logger.info(f"Fichiers statiques montés depuis: {static_dir}")

    return app


# Instance module-level pour uvicorn : backend.main:app
app = create_app()
