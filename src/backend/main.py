from __future__ import annotations

import os
import sys
import json
import time
import logging
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

# --- PYTHONPATH (exécutions depuis racine repo) ---
SRC_DIR = Path(__file__).resolve().parent.parent  # …/src
REPO_ROOT = SRC_DIR.parent                        # …/
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

logger = logging.getLogger("emergence")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)

# Imports après correction du PYTHONPATH
from backend.containers import ServiceContainer  # type: ignore
from backend.core.database.schema import initialize_database  # type: ignore
from backend.shared import dependencies  # type: ignore


# --- Boot timer simple --------------------------------------------------------
class _BootTimer:
    def __init__(self, name: str = "BOOT"):
        self.name = name
        self.t0 = time.perf_counter()
        self.last = self.t0
        self.stamps = []

    def mark(self, label: str):
        now = time.perf_counter()
        delta = (now - self.last) * 1000
        total = (now - self.t0) * 1000
        self.stamps.append({"label": label, "ms_since_last": round(delta, 1), "ms_since_start": round(total, 1)})
        self.last = now
        logger.info(f"[{self.name}] {label}: +{delta:.1f} ms (cum {total:.1f} ms)")

    def dump_to_file(self, path: str | None):
        if not path:
            return
        try:
            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(self.stamps, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning(f"[{self.name}] Échec écriture log perf: {e}")


# --- Import des routers REST (tolérant aux absences) --------------------------
def _import_router(dotted: str):
    try:
        module = __import__(dotted, fromlist=["router"])
        r = getattr(module, "router", None)
        if r is None:
            logger.warning(f"Le module {dotted} n'expose pas 'router'. Ignoré.")
        return r
    except Exception as e:
        logger.warning(f"Router non trouvé: {dotted} — {e}")
        return None

DOCUMENTS_ROUTER = _import_router("backend.features.documents.router")
DASHBOARD_ROUTER = _import_router("backend.features.dashboard.router")
DEBATE_ROUTER    = _import_router("backend.features.debate.router")
CHAT_ROUTER      = _import_router("backend.features.chat.router")


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
            # Connexion rapide uniquement (pas de migrations au boot)
            await db_manager.connect()
            logger.info("DB connectée (FAST_BOOT=on). Migrations reportées au premier usage.")
        else:
            await initialize_database(db_manager, _migrations_dir())
            logger.info("DB initialisée (migrations exécutées).")
    except Exception as e:
        logger.warning(f"Initialisation DB partielle/repoussée: {e}")
    t.mark("db_ready")

    # 2) Wire DI (ajout de debate.router)
    try:
        import backend.features.chat.router as chat_router_module      # type: ignore
        import backend.features.debate.router as debate_router_module  # type: ignore
        container.wire(modules=[chat_router_module, debate_router_module])
        logger.info("DI wired (chat.router, debate.router).")
    except Exception as e:
        logger.warning(f"Wire DI partiel: {e}")
    t.mark("di_wired")

    # 3) Dump facultatif des métriques de boot (si EMERGENCE_BOOT_LOG défini)
    t.dump_to_file(os.getenv("EMERGENCE_BOOT_LOG"))
    t.mark("startup_done")


async def _shutdown(container: ServiceContainer):
    try:
        db_manager = container.db_manager()
        # Correctif: le manager expose 'disconnect()'
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

    app = FastAPI(title="Émergence API", version="7.0")
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
            logger.info(f"Router monté: {router} (prefix effectif: {desired_prefix})")
        except Exception as e:
            logger.error(f"Échec du montage du router {router}: {e}")

    _mount_router(DOCUMENTS_ROUTER, "/api/documents")
    _mount_router(DEBATE_ROUTER,    "/api/debate")
    _mount_router(DASHBOARD_ROUTER, "/api/dashboard")
    t.mark("routers_mounted")

    # WebSocket Chat — lazy container access (aucune instanciation au boot)
    if CHAT_ROUTER is not None:
        try:
            app.include_router(CHAT_ROUTER)
            logger.info("Router WebSocket 'chat' monté.")
        except Exception as e:
            logger.error(f"Impossible de monter le router WebSocket: {e} — fallback local activé.")
            _mount_local_ws(app, container)
    else:
        _mount_local_ws(app, container)
    t.mark("ws_ready")

    try:
        app.mount("/", StaticFiles(directory=str(REPO_ROOT), html=True), name="static")
        logger.info(f"Fichiers statiques montés depuis: {REPO_ROOT}")
    except Exception as e:
        logger.error(f"Impossible de monter les fichiers statiques: {e}")
    t.mark("static_mounted")

    t.dump_to_file(os.getenv("EMERGENCE_BOOT_LOG"))
    return app


def _mount_local_ws(app: FastAPI, container: ServiceContainer) -> None:
    """WS minimal /ws/{session_id} — sans instancier de manager tant qu'aucune connexion n'arrive."""
    async def _get_user_id(user_id: str = Depends(dependencies.get_user_id_from_websocket)) -> str:
        return user_id

    @app.websocket("/ws/{session_id}")
    async def websocket_endpoint(websocket: WebSocket, session_id: str, user_id: str = Depends(_get_user_id)):
        # Lazy: on n’instancie le connection_manager qu’ici
        manager = container.connection_manager()
        await manager.connect(websocket, session_id=session_id, user_id=user_id)
        try:
            while True:
                data = await websocket.receive_text()
                try:
                    chat_service = container.chat_service()  # aussi lazy
                    if hasattr(chat_service, "handle_ws_message"):
                        await chat_service.handle_ws_message(session_id, user_id, data, websocket)
                    elif hasattr(chat_service, "process_message"):
                        result = await chat_service.process_message(session_id=session_id, user_id=user_id, message=data)
                        await websocket.send_text(result if isinstance(result, str) else str(result))
                    else:
                        await websocket.send_text(data)  # écho basique
                except Exception:
                    await websocket.send_text(data)
        except WebSocketDisconnect:
            await manager.disconnect(session_id, websocket)


# Crée l'app au module import pour uvicorn
app = create_app()
