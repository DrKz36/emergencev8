# src/backend/main.py
from __future__ import annotations

import os
import sys
import json
import time
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

# --- PYTHONPATH ---
SRC_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = SRC_DIR.parent
sys.path.append(str(REPO_ROOT))

logger = logging.getLogger("emergence")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")

from backend.containers import ServiceContainer  # type: ignore
from backend.core.database.schema import initialize_database  # type: ignore

def _import_router(dotted: str):
  try:
    module = __import__(dotted, fromlist=["router"])
    return getattr(module, "router", None)
  except Exception as e:
    logger.warning(f"Router non trouvé: {dotted} — {e}")
    return None

# Routers REST
DOCUMENTS_ROUTER = _import_router("backend.features.documents.router")
DASHBOARD_ROUTER = _import_router("backend.features.dashboard.router")
DEBATE_ROUTER    = _import_router("backend.features.debate.router")
CHAT_ROUTER      = _import_router("backend.features.chat.router")
THREADS_ROUTER   = _import_router("backend.features.threads.router")
MEMORY_ROUTER    = _import_router("backend.features.memory.router")
# 🔧 Router dev-auth (sert /dev-auth.html)
DEV_AUTH_ROUTER  = _import_router("backend.features.dev_auth.router")  # <-- ajout

def _migrations_dir() -> str:
  return str(Path(__file__).resolve().parent / "core" / "migrations")

class _BootTimer:
  def __init__(self, name: str = "BOOT-APP"):
    self.name = name
    self.t0 = time.perf_counter()
  def mark(self, label: str):
    dt = (time.perf_counter() - self.t0) * 1000
    logger.info(f"[{self.name}] {label}: +{dt:.1f} ms (cum {dt:.1f} ms)")

async def _startup(container: ServiceContainer):
  bt = _BootTimer("BOOT")
  logger.info("Démarrage backend Émergence…")

  fast_boot = os.getenv("EMERGENCE_FAST_BOOT") or os.getenv("EMERGENCE_SKIP_MIGRATIONS")
  try:
    db_manager = container.db_manager()
    if fast_boot:
      await db_manager.connect()
      logger.info("DB connectée (FAST_BOOT=on).")
    else:
      await initialize_database(db_manager, _migrations_dir())
      logger.info("DB initialisée (migrations exécutées).")
  except Exception as e:
    logger.warning(f"Initialisation DB partielle/repoussée: {e}")
  bt.mark("db_ready")

  # Wire DI (inclut debate.router)
  try:
    import backend.features.chat.router as chat_router_module      # type: ignore
    import backend.features.dashboard.router as dashboard_module   # type: ignore
    import backend.features.documents.router as documents_module   # type: ignore
    import backend.features.debate.router as debate_module         # type: ignore
    # dev_auth n'a pas de DI à câbler
    container.wire(modules=[chat_router_module, dashboard_module, documents_module, debate_module])
    logger.info("DI wired (chat|dashboard|documents|debate.router).")
  except Exception as e:
    logger.warning(f"Wire DI partiel: {e}")
  bt.mark("di_wired")

  # 🔌 Mémoire : câbler l'analyseur ↔ chat_service et l'exposer via session_manager
  try:
    memory_analyzer = container.memory_analyzer()
    chat_service = container.chat_service()
    memory_analyzer.set_chat_service(chat_service)  # rend l'analyseur "ready"
    try:
      session_manager = container.session_manager()
      setattr(session_manager, "memory_analyzer", memory_analyzer)
    except Exception:
      pass
    logger.info("MemoryAnalyzer câblé (chat_service injecté, session_manager.memory_analyzer exposé).")
  except Exception as e:
    logger.warning(f"Câblage MemoryAnalyzer partiel: {e}")
  bt.mark("memory_wired")

def create_app() -> FastAPI:
  container = ServiceContainer()
  app = FastAPI(title="Émergence API", version="7.1")
  app.state.service_container = container

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

  def _mount_router(router, desired_prefix: str):
    if router is None:
      return
    try:
      prefix_attr = getattr(router, "prefix", "") or ""
      if isinstance(prefix_attr, str) and prefix_attr.startswith("/api"):
        app.include_router(router, tags=getattr(router, "tags", None))
      else:
        app.include_router(router, prefix=desired_prefix, tags=getattr(router, "tags", None))
      logger.info(f"Router monté: {desired_prefix or '(no-prefix)'}")
    except Exception as e:
      logger.error(f"Échec du montage du router {desired_prefix}: {e}")

  # REST
  _mount_router(DOCUMENTS_ROUTER, "/api/documents")
  _mount_router(DEBATE_ROUTER,    "/api/debate")
  _mount_router(DASHBOARD_ROUTER, "/api/dashboard")
  _mount_router(THREADS_ROUTER,   "/api/threads")
  _mount_router(MEMORY_ROUTER,    "/api/memory")

  # 🔧 dev-auth (sert /dev-auth.html et /api/_dev-auth-diag)
  _mount_router(DEV_AUTH_ROUTER, "")  # URL = /dev-auth.html

  # WebSocket
  try:
    from backend.features.chat.router import router as CHAT_WS_ROUTER  # type: ignore
    app.include_router(CHAT_WS_ROUTER)
    logger.info("Router WebSocket 'chat' monté.")
  except Exception as e:
    logger.error(f"Impossible de monter le router WebSocket: {e}")

  # Static
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
