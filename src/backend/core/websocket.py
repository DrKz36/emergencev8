# src/backend/core/websocket.py
# V12.0 – WsOutbox integration (coalescence + backpressure)
# Improvements:
# - WsOutbox per-connection for message batching (25ms coalescence)
# - Backpressure (512 msg queue) to prevent burst overload
# - Better handling of abrupt client disconnections
# - Graceful cleanup on protocol-level errors
# - Reduced error noise in production logs
import logging
import asyncio
from typing import Dict, Any, List, Optional, Callable

from fastapi import APIRouter, WebSocket, HTTPException
from starlette.websockets import WebSocketDisconnect

from .session_manager import SessionManager
from .ws_outbox import WsOutbox
from backend.shared import dependencies  # auth WS (allowlist + sub=uid)

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self, session_manager: SessionManager):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        # Map WebSocket -> WsOutbox
        self.outboxes: Dict[WebSocket, WsOutbox] = {}
        self.session_manager = session_manager

        # 🆕 Handshake handler for agent-specific context sync
        self.handshake_handler = None
        try:
            from backend.core.ws.handlers.handshake import HandshakeHandler
            from backend.core.memory.memory_sync import MemorySyncManager

            # Get vector_service from session_manager if available
            vector_service = getattr(session_manager, "vector_service", None)
            if vector_service:
                memory_sync = MemorySyncManager(vector_service)
                self.handshake_handler = HandshakeHandler(memory_sync)
                logger.info("✅ Handshake handler initialized for agent-specific context sync")
            else:
                logger.warning("⚠️ Vector service not available, handshake disabled")
        except Exception as e:
            logger.warning(f"⚠️ Failed to initialize handshake handler: {e}")

        try:
            setattr(self.session_manager, "connection_manager", self)
        except Exception as e:
            logger.warning(f"Impossible d'exposer ConnectionManager dans SessionManager: {e}")
        logger.info("ConnectionManager initialisé.")

    async def _accept_with_subprotocol(self, websocket: WebSocket) -> Optional[str]:
        requested = None
        try:
            requested = websocket.headers.get("sec-websocket-protocol")
        except Exception:
            requested = None

        selected = None
        if requested:
            try:
                for p in [s.strip().lower() for s in requested.split(",") if s.strip()]:
                    if p in {"jwt", "bearer"}:
                        selected = p
                        break
            except Exception as e:
                logger.warning(f"Parsing sec-websocket-protocol échoué: {e}")

        await websocket.accept(subprotocol=selected)
        if selected:
            logger.info(f"WebSocket accepté avec sous-protocole: {selected}")
        else:
            logger.info("WebSocket accepté sans sous-protocole compatible.")
        return selected


    async def connect(
        self,
        websocket: WebSocket,
        session_id: str,
        user_id: str = "default_user",
        thread_id: Optional[str] = None,
        *,
        client_session_id: Optional[str] = None,
    ) -> str:
        await self._accept_with_subprotocol(websocket)

        history_limit = 200
        alias = client_session_id if client_session_id and client_session_id != session_id else None
        first_connection = session_id not in self.active_connections
        if first_connection:
            self.active_connections[session_id] = []
            previously_cached = self.session_manager.get_session(session_id)
            session = await self.session_manager.ensure_session(
                session_id=session_id,
                user_id=user_id,
                thread_id=thread_id,
                history_limit=history_limit,
            )
            if alias:
                try:
                    self.session_manager.register_session_alias(session_id, alias)
                except Exception as exc:
                    logger.debug(
                        "WS alias registration failed (%s -> %s): %s",
                        alias,
                        session_id,
                        exc,
                    )
            if previously_cached:
                logger.info(
                    "Client connected. Session %s already in memory (thread=%s, alias=%s).",
                    session_id,
                    thread_id,
                    alias,
                )
            elif getattr(session, "end_time", None):
                logger.info(
                    "Session %s restored from DB for user %s (thread=%s, alias=%s).",
                    session_id,
                    user_id,
                    thread_id,
                    alias,
                )
            else:
                logger.info(
                    "Client connected. New session %s created for %s (thread=%s, alias=%s).",
                    session_id,
                    user_id,
                    thread_id,
                    alias,
                )
        else:
            await self.session_manager.ensure_session(
                session_id=session_id,
                user_id=user_id,
                thread_id=thread_id,
                history_limit=history_limit,
            )
            if alias:
                try:
                    self.session_manager.register_session_alias(session_id, alias)
                except Exception as exc:
                    logger.debug(
                        "WS alias refresh failed (%s -> %s): %s",
                        alias,
                        session_id,
                        exc,
                    )
            logger.info(
                "New client for existing session %s (thread=%s, alias=%s).",
                session_id,
                thread_id,
                alias,
            )

        self.active_connections[session_id].append(websocket)

        # 🆕 Créer et démarrer WsOutbox pour cette connexion
        outbox = WsOutbox(websocket)
        self.outboxes[websocket] = outbox
        await outbox.start()
        logger.debug(f"WsOutbox started for session {session_id}")

        est_payload = {"session_id": session_id, "thread_id": thread_id}
        if alias:
            est_payload["client_session_id"] = alias

        try:
            await websocket.send_json(
                {
                    "type": "ws:session_established",
                    "payload": est_payload,
                }
            )
        except (WebSocketDisconnect, RuntimeError) as err:
            logger.warning(
                "Client disconnected immediately (session %s). Cleanup... Error: %s",
                session_id,
                err,
            )
            await self.disconnect(session_id, websocket)
            return

        try:
            history_export = self.session_manager.export_history_for_transport(
                session_id, limit=history_limit
            )
            metadata = self.session_manager.get_session_metadata(session_id)
            meta_payload = {k: metadata.get(k) for k in ("summary", "concepts", "entities") if metadata.get(k)}
            if history_export or meta_payload:
                restored_payload = {
                    "session_id": session_id,
                    "thread_id": thread_id,
                    "messages": history_export,
                    "metadata": meta_payload,
                    "history_count": len(history_export),
                    "source": "session_manager",
                }
                if alias:
                    restored_payload["client_session_id"] = alias
                await websocket.send_json(
                    {"type": "ws:session_restored", "payload": restored_payload}
                )
        except Exception as restore_err:
            logger.debug("Unable to send restored history for %s: %s", session_id, restore_err)

    def _resolve_session_id(self, session_id: str) -> str:
        resolver = getattr(self.session_manager, "resolve_session_id", None)
        if callable(resolver):
            try:
                resolved = resolver(session_id)
                if isinstance(resolved, str) and resolved:
                    return resolved
            except Exception:
                pass
        return session_id

    async def disconnect(self, session_id: str, websocket: WebSocket) -> None:
        # 🆕 Arrêter WsOutbox proprement
        outbox = self.outboxes.pop(websocket, None)
        if outbox:
            await outbox.stop()
            logger.debug(f"WsOutbox stopped for session {session_id}")

        resolved_id = self._resolve_session_id(session_id)
        conns = self.active_connections.get(resolved_id, [])
        if websocket in conns:
            conns.remove(websocket)
        if not conns:
            if resolved_id in self.active_connections:
                del self.active_connections[resolved_id]

            async def _finalize() -> None:
                try:
                    await self.session_manager.finalize_session(resolved_id)
                    logger.info("Session %s finalized (async task).", resolved_id)
                except Exception as exc:  # pragma: no cover - logging only
                    logger.warning("finalize_session(%s) raised: %s", resolved_id, exc)

            try:
                asyncio.create_task(_finalize())
            except RuntimeError:
                await _finalize()
            logger.info(
                "Last client disconnected. Finalization of session %s scheduled.",
                resolved_id,
            )
        else:
            logger.info(
                "A client disconnected, %s connection(s) remain for %s.",
                len(conns),
                resolved_id,
            )

    async def send_personal_message(self, message: dict[str, Any], session_id: str) -> None:
        """
        Envoie un message à tous les clients d'une session via WsOutbox.

        WsOutbox gère automatiquement:
        - Coalescence (25ms window)
        - Backpressure (drop si queue pleine)
        - Batching des messages
        """
        resolved_id = self._resolve_session_id(session_id)
        connections = self.active_connections.get(resolved_id, [])
        for ws in list(connections):
            try:
                # 🆕 Envoyer via WsOutbox au lieu de ws.send_json()
                outbox = self.outboxes.get(ws)
                if outbox:
                    await outbox.send(message)
                else:
                    # Fallback si pas d'outbox (ne devrait pas arriver)
                    logger.warning(f"No outbox for session {resolved_id}, using fallback send_json")
                    await ws.send_json(message)
            except WebSocketDisconnect as exc:
                logger.info(
                    "Client disconnected during send (session=%s, code=%s)",
                    resolved_id,
                    getattr(exc, "code", "unknown")
                )
                await self.disconnect(resolved_id, ws)
            except RuntimeError as exc:
                # Connection lost during send (abrupt disconnection)
                logger.info(
                    "Client connection lost during send (session=%s): %s",
                    resolved_id,
                    exc
                )
                await self.disconnect(resolved_id, ws)
            except Exception as exc:
                # Unexpected error during send
                logger.error(
                    "Unexpected send error (session=%s): %s",
                    resolved_id,
                    exc,
                    exc_info=True
                )
                await self.disconnect(resolved_id, ws)

    async def send_system_message(self, session_id: str, payload: dict[str, Any]) -> None:
        """Envoie un message système à une session (ex: avertissement d'inactivité)."""
        message = {
            "type": "ws:system_notification",
            "payload": payload
        }
        await self.send_personal_message(message, session_id)

    async def send_to_session(self, session_id: str, message: dict[str, Any]) -> None:
        """Envoie un message générique à une session (wrapper pour handshake)."""
        await self.send_personal_message(message, session_id)

    async def send_agent_hello(
        self,
        session_id: str,
        agent_id: str,
        model: str,
        provider: str,
        user_id: str
    ) -> None:
        """
        Envoie un message HELLO pour synchroniser le contexte agent.

        Args:
            session_id: ID session WebSocket
            agent_id: ID agent (anima, neo, nexus)
            model: Modèle LLM
            provider: Provider LLM
            user_id: ID utilisateur
        """
        if not self.handshake_handler:
            logger.debug("[ConnectionManager] Handshake handler not available, skipping HELLO")
            return

        try:
            await self.handshake_handler.send_hello(
                connection_manager=self,
                session_id=session_id,
                agent_id=agent_id,
                model=model,
                provider=provider,
                user_id=user_id
            )
        except Exception as e:
            logger.error(f"[ConnectionManager] Error sending HELLO: {e}", exc_info=True)

    async def close_session(
        self,
        session_id: str,
        *,
        code: int = 4401,
        reason: str = "session_revoked",
    ) -> int:
        resolved_id = self._resolve_session_id(session_id)
        connections = self.active_connections.pop(resolved_id, [])
        if not connections:
            return 0
        closed = 0
        notice = {"type": "ws:auth_required", "payload": {"reason": reason, "code": code}}
        for ws in list(connections):
            try:
                await ws.send_json(notice)
            except Exception:
                pass
            try:
                await ws.close(code=code)
            except Exception:
                pass
            closed += 1
        logger.info(
            "Session %s: closed %s WebSocket connection(s) (reason=%s).",
            resolved_id,
            closed,
            reason,
        )
        return closed

def _find_handler(sm: SessionManager) -> Optional[Callable[..., Any]]:
    for name in ("on_client_message", "ingest_ws_message", "handle_client_message", "dispatch"):
        fn = getattr(sm, name, None)
        if callable(fn):
            return cast(Callable[..., Any], fn)
    return None

def get_websocket_router(container: Any) -> APIRouter:
    router = APIRouter()

    @router.websocket("/ws/{session_id}")
    async def websocket_endpoint(websocket: WebSocket, session_id: str):
        requested_session_id = session_id
        user_id_hint = websocket.query_params.get("user_id")
        thread_id = websocket.query_params.get("thread_id")

        async def _reject_ws(reason: str, close_code: int = 4401) -> None:
            try:
                requested = websocket.headers.get("sec-websocket-protocol") or ""
                selected = None
                for p in [s.strip().lower() for s in requested.split(",") if s.strip()]:
                    if p in {"jwt", "bearer"}:
                        selected = p
                        break
                await websocket.accept(subprotocol=selected)
            except Exception as ae:
                logger.warning("WS accept() before close failed: %s", ae)
            try:
                await websocket.send_json(
                    {
                        "type": "ws:auth_required",
                        "payload": {"reason": reason, "code": close_code},
                    }
                )
            except Exception:
                pass
            try:
                await websocket.close(code=close_code)
            except Exception:
                pass

        try:
            user_id = await dependencies.get_user_id_for_ws(websocket, user_id=user_id_hint)
        except HTTPException as exc:
            reason = exc.detail if isinstance(exc.detail, str) else "invalid_or_missing_token"
            close_code = 4401 if exc.status_code in (401, 403) else 1008
            logger.warning("WS auth failed -> close %s : %s", close_code, exc)
            await _reject_ws(reason, close_code)
            return
        except Exception as err:
            logger.error("WS auth unexpected error -> close 1008 : %s", err)
            await _reject_ws("unexpected_error", 1008)
            return

        claims = getattr(getattr(websocket, "state", None), "auth_claims", {})
        auth_email = None
        auth_session_id = None
        session_revoked = False
        if isinstance(claims, dict):
            auth_email = claims.get("email")
            auth_session_id = claims.get("session_id") or claims.get("sid")
            session_revoked = bool(claims.get("session_revoked"))
        canonical_session_id = str(auth_session_id or requested_session_id or "").strip() or requested_session_id
        if session_revoked:
            logger.warning(
                "WS auth refused: session %s marked as revoked.",
                auth_session_id or "<unknown>",
            )
            await _reject_ws("session_revoked", 4401)
            return
        if auth_email:
            websocket.scope["auth_email"] = auth_email
            logger.info(
                "WS auth accepted for %s (sub=%s, session=%s, alias=%s)",
                auth_email,
                user_id,
                canonical_session_id,
                requested_session_id if requested_session_id != canonical_session_id else None,
            )
        websocket.scope["auth_session_id"] = canonical_session_id
        if requested_session_id != canonical_session_id:
            websocket.scope["client_session_id"] = requested_session_id

        session_manager: SessionManager = container.session_manager()
        conn_manager = getattr(session_manager, "connection_manager", None)
        if conn_manager is None:
            conn_manager = ConnectionManager(session_manager)

        alias_value = requested_session_id if requested_session_id != canonical_session_id else None
        await conn_manager.connect(
            websocket,
            canonical_session_id,
            user_id=user_id,
            thread_id=thread_id,
            client_session_id=alias_value,
        )

        handler = _find_handler(session_manager)
        target_session_id = canonical_session_id
        try:
            while True:
                data = await websocket.receive_json()
                if handler:
                    try:
                        res = handler(target_session_id, data)
                        if asyncio.iscoroutine(res):
                            await res
                    except TypeError:
                        res = handler(data, target_session_id)
                        if asyncio.iscoroutine(res):
                            await res
                else:
                    await conn_manager.send_personal_message(
                        {"type": "ws:ack", "payload": {"received": True, "echo": data}},
                        target_session_id,
                    )
        except WebSocketDisconnect as e:
            # Normal disconnection - client closed connection gracefully
            logger.info(
                "Client disconnected gracefully (session=%s, code=%s)",
                target_session_id,
                getattr(e, "code", "unknown")
            )
            await conn_manager.disconnect(target_session_id, websocket)
        except RuntimeError as err:
            # Protocol-level errors (e.g., connection lost during send/receive)
            # These are often caused by abrupt client disconnections
            err_msg = str(err).lower()
            if "websocket" in err_msg or "connection" in err_msg or "disconnect" in err_msg:
                logger.info(
                    "Client disconnected abruptly (session=%s): %s",
                    target_session_id,
                    err
                )
            else:
                logger.error("WS RuntimeError (session=%s): %s", target_session_id, err)
            await conn_manager.disconnect(target_session_id, websocket)
        except asyncio.CancelledError:
            # Task cancellation (e.g., server shutdown)
            logger.info("WebSocket task cancelled (session=%s)", target_session_id)
            await conn_manager.disconnect(target_session_id, websocket)
            raise  # Re-raise to allow proper cleanup
        except Exception as err:
            # Unexpected errors
            logger.error(
                "Unexpected WebSocket error (session=%s): %s",
                target_session_id,
                err,
                exc_info=True
            )
            await conn_manager.disconnect(target_session_id, websocket)

    return router

