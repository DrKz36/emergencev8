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

    # 2) Wire DI (sans instancier les services lourds)
    try:
        import backend.features.chat.router as chat_router_module  # type: ignore
        container.wire(modules=[chat_router_module])
        logger.info("DI wired (chat.router).")
    except Exception as e:
        logger.warning(f"Wire DI partiel (chat.router): {e}")
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

    # WebSocket Chat — lazy container access
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

    # --- Static: servir l'app web (robuste + diagnostique) ---
    # Résolution robuste des chemins (par défaut /app dans le conteneur)
    BASE = Path(os.getenv("EMERGENCE_STATIC_ROOT") or REPO_ROOT).resolve()
    SRC_PATH = Path(os.getenv("EMERGENCE_STATIC_SRC") or (BASE / "src")).resolve()
    ASSETS_PATH = Path(os.getenv("EMERGENCE_STATIC_ASSETS") or (BASE / "assets")).resolve()
    INDEX_PATH = BASE / "index.html"

    try:
        mounts = []

        # /src → /app/src (ou override via env)
        if SRC_PATH.exists():
            app.mount("/src", StaticFiles(directory=str(SRC_PATH), check_dir=False), name="src-static")
            mounts.append(f"/src->{SRC_PATH}")
        else:
            logger.warning(f"[static] Répertoire /src introuvable: {SRC_PATH}")

        # /assets → /app/assets (ou override via env)
        if ASSETS_PATH.exists():
            app.mount("/assets", StaticFiles(directory=str(ASSETS_PATH), check_dir=False), name="assets-static")
            mounts.append(f"/assets->{ASSETS_PATH}")
        else:
            logger.warning(f"[static] Répertoire /assets introuvable: {ASSETS_PATH}")

        # / → racine repo (sert index.html)
        if BASE.exists():
            app.mount("/", StaticFiles(directory=str(BASE), html=True, check_dir=False), name="root")
            mounts.append(f"/->{BASE} (html=True)")
        else:
            logger.error(f"[static] Racine introuvable: {BASE}")

        logger.info("Fichiers statiques montés: " + " | ".join(mounts) if mounts else "Aucun montage statique actif.")
    except Exception as e:
        logger.error(f"Impossible de monter les fichiers statiques: {e}")
    t.mark("static_mounted")

    # Endpoint de diagnostic simple
    @app.get("/api/_static-diag", tags=["Health"])
    async def _static_diag():
        return {
            "base": str(BASE),
            "src": {"path": str(SRC_PATH), "exists": SRC_PATH.exists()},
            "assets": {"path": str(ASSETS_PATH), "exists": ASSETS_PATH.exists()},
            "index_html": {"path": str(INDEX_PATH), "exists": INDEX_PATH.exists()},
        }

    t.dump_to_file(os.getenv("EMERGENCE_BOOT_LOG"))
    return app


def _mount_local_ws(app: FastAPI, container: ServiceContainer) -> None:
    """WS minimal /ws/{session_id} — sans instancier de manager tant qu'aucune connexion n'arrive."""
    async def _get_user_id(user_id: str = Depends(dependencies.get_user_id_from_websocket)) -> str:
        return user_id

    @app.websocket("/ws/{session_id}")
    async def websocket_endpoint(websocket: WebSocket, session_id: str, user_id: str = Depends(_get_user_id)):
        manager = container.connection_manager()
        await manager.connect(websocket, session_id=session_id, user_id=user_id)
        try:
            while True:
                data = await websocket.receive_text()
                try:
                    chat_service = container.chat_service()
                    if hasattr(chat_service, "handle_ws_message"):
                        await chat_service.handle_ws_message(session_id, user_id, data, websocket)
                    elif hasattr(chat_service, "process_message"):
                        result = await chat_service.process_message(session_id=session_id, user_id=user_id, message=data)
                        await websocket.send_text(result if isinstance(result, str) else str(result))
                    else:
                        await websocket.send_text(data)  # écho
                except Exception:
                    await websocket.send_text(data)
        except WebSocketDisconnect:
            await manager.disconnect(session_id, websocket)


# Crée l'app au module import pour uvicorn
app = create_app()
