# encoding: utf-8
# src/backend/main.py
# V7.2 — Health robuste (/api/health + /health) + init DB via schema.initialize_database

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

# ⬇️ La bonne API de migrations/DDL est dans schema.py
from backend.core.database.schema import initialize_database  # <-- clé du fix
from backend.containers import ServiceContainer

logger = logging.getLogger("emergence")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"),
                    format="%(asctime)s %(levelname)s [%(name)s] %(message)s")


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


def _import_router(module_path: str):
    try:
        return importlib.import_module(module_path)
    except Exception as e:
        logger.warning(f"Impossible d'importer {module_path}: {e}")
        return None

DOCUMENTS_ROUTER = _import_router("backend.features.documents.router")
DASHBOARD_ROUTER = _import_router("backend.features.dashboard.router")
DEBATE_ROUTER    = _import_router("backend.features.debate.router")
CHAT_ROUTER      = _import_router("backend.features.chat.router")
MEMORY_ROUTER    = _import_router("backend.features.memory.router")
DEV_AUTH_ROUTER  = _import_router("backend.features.dev_auth.router")
THREADS_ROUTER   = _import_router("backend.features.threads.router")

def _migrations_dir() -> str:
    return str(Path(__file__).resolve().parent / "core" / "migrations")

async def _startup(container: ServiceContainer):
    t = _BootTimer()
    logger.info("Démarrage backend Émergence…")

    # 1) DB init via schema.initialize_database (crée tables + micro-upgrades + .sql)
    try:
        db_manager = container.db_manager()
        await initialize_database(db_manager, _migrations_dir())  # <-- fix
        logger.info("DB initialisée (tables + migrations).")
    except Exception as e:
        logger.warning(f"Initialisation DB partielle/repoussée: {e}")
    t.mark("db_ready")

    # 2) Wire DI (chat / debate / memory) – optionnel
    try:
        import backend.features.chat.router as chat_router_module      # type: ignore
        import backend.features.debate.router as debate_router_module  # type: ignore
        import backend.features.memory.router as memory_router_module  # type: ignore
        container.wire(modules=[chat_router_module, debate_router_module, memory_router_module])
        logger.info("DI wired (chat.router, debate.router, memory.router).")
    except Exception as e:
        logger.warning(f"Wire DI partiel: {e}")
    t.mark("di_wired")

    # 3) Injection tardive (ChatService -> MemoryAnalyzer)
    try:
        analyzer = container.memory_analyzer()
        chat = container.chat_service()
        analyzer.set_chat_service(chat)
    except Exception as e:
        logger.warning(f"Injection tardive MemoryAnalyzer/ChatService: {e}")

    t.dump_to_file(os.getenv("EMERGENCE_BOOT_LOG"))
    t.mark("startup_done")

async def _shutdown(container: ServiceContainer):
    try:
        await container.db_manager().disconnect()
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

    app = FastAPI(title="Émergence API", version="7.2")
    app.state.service_container = container

    # CORS simple (même origin en dev → OK)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    t.mark("middleware_ready")

    @app.on_event("startup")
    async def _on_startup(): await _startup(container)
    @app.on_event("shutdown")
    async def _on_shutdown(): await _shutdown(container)

    # Health publics
    @app.get("/api/health", include_in_schema=False)
    async def health_api():  return {"status":"ok","message":"Emergence Backend is running."}
    @app.get("/health", include_in_schema=False)
    async def health_root(): return {"status":"ok","message":"Emergence Backend is running."}

    # Routers REST
    def _mount(mod, prefix: str, name: str):
        if mod and getattr(mod, "router", None):
            app.include_router(mod.router, prefix=prefix)
            logger.info(f"Router '{name}' monté sur {prefix}")
    _mount(DOCUMENTS_ROUTER, "/api/documents", "documents")
    _mount(DEBATE_ROUTER,    "/api/debate",    "debate")
    _mount(DASHBOARD_ROUTER, "/api/dashboard", "dashboard")
    _mount(MEMORY_ROUTER,    "/api/memory",    "memory")
    _mount(THREADS_ROUTER,   "/api/threads",   "threads")

    # WebSocket « chat »
    if CHAT_ROUTER and getattr(CHAT_ROUTER, "router", None):
        app.include_router(CHAT_ROUTER.router)
        logger.info("Router WebSocket 'chat' monté.")

    # Page /dev-auth.html (debug GIS)
    if DEV_AUTH_ROUTER and getattr(DEV_AUTH_ROUTER, "router", None):
        app.include_router(DEV_AUTH_ROUTER.router, include_in_schema=False)
        logger.info("Router 'dev_auth' monté sur")

    # Statiques (racine du repo)
    static_dir = Path(__file__).resolve().parents[2]
    if static_dir.exists():
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
        logger.info(f"Fichiers statiques montés depuis: {static_dir}")

    return app

app = create_app()
