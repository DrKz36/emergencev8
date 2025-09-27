# src/backend/core/session_manager.py
# V13.2 - FIX: Alignement avec queries.py V5.1 et ajout du chargement de session.
import logging
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple, Set
from uuid import uuid4

# Imports corrigés pour refléter la structure réelle
from backend.shared.models import Session, ChatMessage, AgentMessage, Role
from backend.core.database.manager import DatabaseManager
from backend.core.database import queries  # Import du module queries
from backend.features.memory.analyzer import MemoryAnalyzer

logger = logging.getLogger(__name__)

class SessionManager:
    """
    Gère les sessions de chat actives en mémoire et leur persistance.
    V13.2: Ajout du chargement de session depuis la BDD et correction des dépendances.
    """

    def __init__(self, db_manager: DatabaseManager, memory_analyzer: Optional[MemoryAnalyzer] = None):
        self.db_manager = db_manager
        self.memory_analyzer = memory_analyzer
        self.active_sessions: Dict[str, Session] = {}
        self._session_user_cache: Dict[str, str] = {}
        # ConnectionManager sera injecté dynamiquement par websocket.ConnectionManager
        self.connection_manager = None  # type: ignore[attr-defined]
        self._session_threads: Dict[str, str] = {}
        self._session_users: Dict[str, str] = {}
        self._hydrated_threads: Dict[Tuple[str, str], bool] = {}
        self._session_alias_to_canonical: Dict[str, str] = {}
        self._session_canonical_to_aliases: Dict[str, Set[str]] = {}
        is_ready = self.memory_analyzer is not None
        logger.info(f"SessionManager V13.2 initialisé. MemoryAnalyzer prêt : {is_ready}")

    def _ensure_analyzer_ready(self):
        """Vérifie que le service dépendant est bien injecté avant utilisation."""
        if not self.memory_analyzer:
            logger.error("Dépendance 'memory_analyzer' non injectée dans SessionManager.")
            raise ReferenceError("SessionManager: memory_analyzer manquant.")

    async def ensure_session(self, session_id: str, user_id: str, *, thread_id: Optional[str] = None,
                             history_limit: int = 200) -> Session:
        """Garantit qu'une session est active en mémoire et hydratée depuis les persistances disponibles."""
        session_id = self.resolve_session_id(session_id)
        session = self.active_sessions.get(session_id)

        if not session:
            session = await self.load_session_from_db(session_id)
            if not session:
                session = Session(
                    id=session_id,
                    user_id=user_id,
                    start_time=datetime.now(timezone.utc),
                    end_time=None,
                    history=[],
                )
                if thread_id:
                    session.metadata["thread_id"] = thread_id
                self.active_sessions[session_id] = session
                logger.info(f"Session active créée : {session_id} pour l'utilisateur {user_id}")
            else:
                logger.info(f"Session {session_id} rechargée depuis la BDD")

        resolved_user_id = user_id or session.user_id or self._session_user_cache.get(session_id)
        if resolved_user_id:
            resolved_user_id_str = str(resolved_user_id)
            session.user_id = resolved_user_id_str
            self._session_users[session_id] = resolved_user_id_str
            self._session_user_cache[session_id] = resolved_user_id_str

        if thread_id:
            self._session_threads[session_id] = thread_id
            if not isinstance(session.metadata, dict):
                session.metadata = {}
            session.metadata["thread_id"] = thread_id

            hydrated_key = (session_id, thread_id)
            if not session.history or not self._hydrated_threads.get(hydrated_key):
                await self._hydrate_session_from_thread(session_id, thread_id, history_limit)
                self._hydrated_threads[hydrated_key] = True
        else:
            if session.history:
                logger.debug(f"Session {session_id} dispose déjà d'un historique en mémoire.")

        return session

    def create_session(self, session_id: str, user_id: str):
        """Crée une session et la garde active en mémoire (compatibilité synchrone)."""
        session_id = self.resolve_session_id(session_id)
        if session_id in self.active_sessions:
            logger.warning(f"Tentative de création d'une session déjà existante: {session_id}")
            return self.active_sessions[session_id]

        session = Session(
            id=session_id,
            user_id=user_id,
            start_time=datetime.now(timezone.utc),
            end_time=None,
            history=[],
        )
        self.active_sessions[session_id] = session

        if user_id:
            uid = str(user_id)
            session.user_id = uid
            self._session_users[session_id] = uid
            self._session_user_cache[session_id] = uid

        logger.info(f"Session active créée : {session_id} pour l'utilisateur {user_id}")
        return session




    def register_session_alias(self, session_id: str, alias: Optional[str]) -> None:
        if not alias:
            return
        alias_str = str(alias)
        if not alias_str or alias_str == session_id:
            return
        canonical = str(session_id)
        self._session_alias_to_canonical[alias_str] = canonical
        self._session_canonical_to_aliases.setdefault(canonical, set()).add(alias_str)

    def resolve_session_id(self, session_id: str) -> str:
        candidate = str(session_id)
        return self._session_alias_to_canonical.get(candidate, candidate)

    def _cleanup_session_aliases(self, session_id: str) -> None:
        canonical = str(session_id)
        aliases = self._session_canonical_to_aliases.pop(canonical, set())
        for alias in aliases:
            self._session_alias_to_canonical.pop(alias, None)

    def get_user_id_for_session(self, session_id: str) -> Optional[str]:
        """Retourne l'identifiant utilisateur associé à la session (cache + fallback)."""
        session_id = self.resolve_session_id(session_id)
        session = self.active_sessions.get(session_id)
        if session and getattr(session, 'user_id', None):
            uid = str(session.user_id)
            self._session_user_cache.setdefault(session_id, uid)
            self._session_users.setdefault(session_id, uid)
            return uid
        cached_uid = self._session_users.get(session_id) or self._session_user_cache.get(session_id)
        return str(cached_uid) if cached_uid else None

    def get_session_metadata(self, session_id: str) -> Dict[str, Any]:
        """Garantit la présence d'un dictionnaire de métadonnées pour la session active."""
        session_id = self.resolve_session_id(session_id)
        session = self.active_sessions.get(session_id)
        if not session:
            return {}
        meta = session.metadata
        if not isinstance(meta, dict):
            meta = {}
            session.metadata = meta
        return meta

    def update_session_metadata(self, session_id: str, *, summary: Optional[str] = None, concepts: Optional[List[str]] = None, entities: Optional[List[str]] = None) -> None:
        session_id = self.resolve_session_id(session_id)
        session = self.active_sessions.get(session_id)
        if not session:
            logger.debug(f"update_session_metadata ignoré: session {session_id} introuvable")
            return
        meta = self.get_session_metadata(session_id)
        if summary is not None:
            meta['summary'] = summary
        if concepts is not None:
            meta['concepts'] = concepts
        if entities is not None:
            meta['entities'] = entities
        try:
            session.metadata = meta
        except Exception:
            pass

    def get_session(self, session_id: str) -> Optional[Session]:
        """Récupère une session depuis le cache mémoire actif."""
        session_id = self.resolve_session_id(session_id)
        return self.active_sessions.get(session_id)

    async def load_session_from_db(self, session_id: str) -> Optional[Session]:
        """
        NOUVEAU V13.2: Charge une session depuis la BDD si elle n'est pas active.
        C'est le chaînon manquant pour travailler sur des sessions passées.
        """
        session_id = self.resolve_session_id(session_id)
        if session_id in self.active_sessions:
            return self.active_sessions[session_id]

        logger.info(f"Session {session_id} non active, tentative de chargement depuis la BDD...")
        # On utilise la nouvelle fonction de queries.py
        session_row = await queries.get_session_by_id(self.db_manager, session_id)

        if not session_row:
            logger.warning(f"Session {session_id} non trouvée en BDD.")
            return None

        try:
            # Reconstruction de l'objet Session à partir des données de la BDD
            session_dict = dict(session_row)
            history_json = session_dict.get('session_data', '[]')
            
            # Reconstruction de l'historique avec les bons modèles Pydantic
            history_list = json.loads(history_json)
            reconstructed_history: List[Dict[str, Any]] = []
            for msg in history_list:
                candidate = msg
                if not isinstance(candidate, dict):
                    if hasattr(candidate, "model_dump"):
                        try:
                            candidate = candidate.model_dump(mode="json")  # type: ignore[attr-defined]
                        except Exception:
                            candidate = {}
                    elif hasattr(candidate, "dict"):
                        try:
                            candidate = candidate.dict()  # type: ignore[attr-defined]
                        except Exception:
                            candidate = {}
                    elif isinstance(candidate, str):
                        try:
                            candidate = json.loads(candidate)
                        except Exception:
                            candidate = {"raw": candidate}
                    elif hasattr(candidate, "items"):
                        try:
                            candidate = dict(candidate)
                        except Exception:
                            candidate = {}
                    else:
                        candidate = {}
                if not isinstance(candidate, dict):
                    reconstructed_history.append(candidate)
                    continue
                try:
                    role = str(candidate.get("role") or "").lower()
                    model: ChatMessage | AgentMessage
                    if role == "assistant":
                        model = AgentMessage(**candidate)
                    else:
                        model = ChatMessage(**candidate)
                    payload = model.model_dump(mode="json")
                    if "message" in payload and "content" not in payload:
                        payload["content"] = payload.get("message")
                    reconstructed_history.append(payload)
                except Exception:
                    reconstructed_history.append(candidate)

            session = Session(
                id=session_dict['id'],
                user_id=session_dict['user_id'],
                start_time=datetime.fromisoformat(session_dict['created_at']),
                end_time=datetime.fromisoformat(session_dict['updated_at']),
                history=reconstructed_history,
            )
            session.metadata = {
                "summary": session_dict.get('summary'),
                "concepts": json.loads(session_dict.get('extracted_concepts', '[]') or '[]'),
                "entities": json.loads(session_dict.get('extracted_entities', '[]') or '[]')
            }

            self.active_sessions[session_id] = session  # On la met en cache actif
            if session.user_id:
                uid = str(session.user_id)
                self._session_user_cache[session_id] = uid
                self._session_users[session_id] = uid
            logger.info(f"Session {session_id} chargée et reconstruite depuis la BDD.")
            return session
        except Exception as e:
            logger.error(f"Erreur lors de la reconstruction de la session {session_id} depuis la BDD: {e}", exc_info=True)
            return None

    async def _hydrate_session_from_thread(self, session_id: str, thread_id: str, limit: int = 200) -> None:
        thread_id = (thread_id or "").strip()
        if not thread_id:
            return

        try:
            thread_row = await queries.get_thread_any(self.db_manager, thread_id, session_id)
            if not thread_row:
                logger.warning(f"Thread {thread_id} introuvable pour l'hydratation de la session {session_id}.")
            else:
                session_meta = self.active_sessions[session_id].metadata
                if not isinstance(session_meta, dict):
                    session_meta = {}
                    self.active_sessions[session_id].metadata = session_meta
                try:
                    raw_meta = thread_row.get("meta")
                    meta_dict = json.loads(raw_meta) if isinstance(raw_meta, str) else (raw_meta or {})
                except Exception:
                    meta_dict = {}
                session_meta.setdefault("thread", thread_row)
                if meta_dict:
                    session_meta.setdefault("thread_meta", meta_dict)

            messages = await queries.get_messages(self.db_manager, thread_id, session_id=session_id, limit=limit)
            history: List[Dict[str, Any]] = []
            for item in messages or []:
                try:
                    payload = dict(item)
                except Exception:
                    payload = item
                msg_role = str(payload.get("role") or Role.USER).lower()
                role = Role.ASSISTANT if msg_role == Role.ASSISTANT.value else Role.USER
                content = payload.get("content")
                if not isinstance(content, str):
                    try:
                        content = json.dumps(content or "")
                    except Exception:
                        content = str(content or "")
                agent_id = payload.get("agent_id") or ("user" if role == Role.USER else "assistant")
                timestamp = payload.get("created_at") or payload.get("timestamp") or datetime.now(timezone.utc).isoformat()
                message_id = str(payload.get("id") or uuid4())
                meta = payload.get("meta")
                if isinstance(meta, str):
                    try:
                        meta = json.loads(meta)
                    except Exception:
                        meta = {"raw": meta}

                history.append({
                    "id": message_id,
                    "session_id": session_id,
                    "role": role.value,
                    "agent": agent_id,
                    "content": content,
                    "timestamp": timestamp,
                    "meta": meta,
                    "source": "thread_persisted"
                })

            if history:
                self.active_sessions[session_id].history = history
                logger.info(f"Session {session_id} hydratée depuis le thread {thread_id} ({len(history)} messages).")
        except Exception as e:
            logger.error(f"Hydratation session {session_id} depuis thread {thread_id} échouée: {e}", exc_info=True)

    async def add_message_to_session(self, session_id: str, message: ChatMessage | AgentMessage):
        session_id = self.resolve_session_id(session_id)
        session = self.get_session(session_id)
        if session:
            payload = message.model_dump(mode='json')
            if "message" in payload and "content" not in payload:
                payload["content"] = payload.pop("message")
            payload.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
            session.history.append(payload)

            await self._persist_message(session_id, payload)
        else:
            logger.error(f"Impossible d'ajouter un message : session {session_id} non trouvée.")

    def get_full_history(self, session_id: str) -> List[Dict[str, Any]]:
        session = self.get_session(session_id)
        if not session:
            return []
        normalized: List[Dict[str, Any]] = []
        for item in getattr(session, "history", []) or []:
            if isinstance(item, dict):
                normalized.append(item)
                continue
            try:
                if hasattr(item, "model_dump"):
                    normalized.append(item.model_dump(mode="json"))  # type: ignore[attr-defined]
                elif hasattr(item, "dict"):
                    normalized.append(item.dict())  # type: ignore[attr-defined]
                elif hasattr(item, "items"):
                    normalized.append(dict(item))
                elif isinstance(item, str):
                    normalized.append(json.loads(item))
                else:
                    normalized.append({})
            except Exception:
                normalized.append({})
        return normalized

    def export_history_for_transport(self, session_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Retourne l'historique hydraté, normalisé pour transport (agent_id, created_at, meta dict)."""
        session_id = self.resolve_session_id(session_id)
        history = self.get_full_history(session_id)
        if not history:
            return []
        if isinstance(limit, int) and limit > 0:
            history = history[-limit:]
        exported: List[Dict[str, Any]] = []
        for item in history:
            data: Dict[str, Any]
            if isinstance(item, dict):
                data = item
            else:
                try:
                    if hasattr(item, 'model_dump'):
                        data = item.model_dump(mode='json')  # type: ignore[attr-defined]
                    elif hasattr(item, 'dict'):
                        data = item.dict()  # type: ignore[attr-defined]
                    else:
                        data = dict(item)  # type: ignore[arg-type]
                except Exception:
                    data = {}
            if not isinstance(data, dict):
                continue
            role_raw = str(data.get('role') or '').strip().lower()
            if role_raw in {Role.USER.value, 'user'}:
                role_value = Role.USER.value
            elif role_raw in {Role.ASSISTANT.value, 'assistant'}:
                role_value = Role.ASSISTANT.value
            elif role_raw in {Role.SYSTEM.value, 'system'}:
                role_value = Role.SYSTEM.value
            else:
                role_value = Role.USER.value if role_raw.startswith('user') else Role.ASSISTANT.value
            content = data.get('content')
            if content is None:
                content = data.get('message') or ''
            if not isinstance(content, str):
                try:
                    content = json.dumps(content)
                except Exception:
                    content = str(content)
            agent_id = data.get('agent_id') or data.get('agent')
            if not agent_id:
                agent_id = 'user' if role_value == Role.USER.value else 'assistant'
            created_at = data.get('created_at') or data.get('timestamp')
            if not created_at:
                created_at = datetime.now(timezone.utc).isoformat()
            meta = data.get('meta')
            if isinstance(meta, str):
                try:
                    meta = json.loads(meta)
                except Exception:
                    meta = {'raw': meta}
            if meta is None:
                meta = {}
            if not isinstance(meta, dict):
                meta = {'value': meta}
            doc_ids = data.get('doc_ids')
            if isinstance(doc_ids, (set, tuple)):
                doc_ids = list(doc_ids)
            elif doc_ids is None:
                doc_ids = []
            elif not isinstance(doc_ids, list):
                doc_ids = [doc_ids]
            exported.append({
                'id': data.get('id') or str(uuid4()),
                'role': role_value,
                'content': content,
                'agent_id': str(agent_id),
                'created_at': created_at,
                'meta': meta,
                'doc_ids': doc_ids,
                'use_rag': bool(data.get('use_rag')),
            })
        return exported

    async def _persist_message(self, session_id: str, payload: Dict[str, Any]):
        session_id = self.resolve_session_id(session_id)
        thread_id = self._session_threads.get(session_id)
        if not thread_id:
            return

        role = str(payload.get("role") or Role.USER.value).lower()
        content = payload.get("content") or payload.get("message") or ""
        if not isinstance(content, str):
            try:
                content = json.dumps(content or "")
            except Exception:
                content = str(content or "")
        agent_id = payload.get("agent") or payload.get("agent_id")
        tokens = payload.get("tokens")
        if isinstance(tokens, dict):
            tokens_value = tokens.get("total") or tokens.get("output") or tokens.get("count")
        elif isinstance(tokens, (int, float)):
            tokens_value = int(tokens)
        else:
            cost_info = payload.get("cost_info") or {}
            tokens_value = cost_info.get("output_tokens") or cost_info.get("total_tokens")

        meta = payload.get("meta")
        if meta is None:
            meta = {}
        if isinstance(meta, str):
            try:
                meta = json.loads(meta)
            except Exception:
                meta = {"raw": meta}
        if not isinstance(meta, dict):
            meta = {"value": meta}

        meta.setdefault("persisted_by", "backend")
        meta.setdefault("persisted_via", "ws")
        meta.setdefault("session_id", session_id)
        payload["meta"] = meta
        payload["session_id"] = session_id

        try:
            result = await queries.add_message(
                self.db_manager,
                thread_id,
                session_id,
                role=role,
                content=content,
                agent_id=agent_id,
                tokens=tokens_value,
                meta=meta,
            )
            await self.publish_event(session_id, "ws:message_persisted", {
                "message_id": payload.get("id"),
                "thread_id": thread_id,
                "role": role,
                "created_at": result.get("created_at"),
                "id": result.get("message_id") or result.get("id"),
                "persisted": True,
                "agent_id": agent_id,
                "session_id": session_id,
            })
        except Exception as e:
            logger.error(f"Persistance du message pour la session {session_id} a échoué: {e}", exc_info=True)
    async def finalize_session(self, session_id: str):
        session_id = self.resolve_session_id(session_id)
        session = self.active_sessions.pop(session_id, None)
        if session:
            if getattr(session, 'user_id', None):
                self._session_user_cache.setdefault(session_id, str(session.user_id))
            session.end_time = datetime.now(timezone.utc)
            duration = (session.end_time - session.start_time).total_seconds()
            logger.info(f"Finalisation de la session {session_id}. Durée: {duration:.2f}s.")
            
            # On utilise la méthode robuste du DatabaseManager pour sauvegarder
            await self.db_manager.save_session(session)

            # Lancement de l'analyse sémantique post-session
            if self.memory_analyzer:
                await self.memory_analyzer.analyze_session_for_concepts(session_id, session.history)
            else:
                logger.warning("MemoryAnalyzer non disponible, l'analyse post-session est sautée.")
        else:
            logger.warning(f"Tentative de finalisation d'une session inexistante ou déjà finalisée: {session_id}")

        self._session_threads.pop(session_id, None)
        self._session_users.pop(session_id, None)
        # Nettoyer cache d'hydratation
        keys_to_remove = [key for key in self._hydrated_threads if key[0] == session_id]
        for key in keys_to_remove:
            self._hydrated_threads.pop(key, None)
        self._cleanup_session_aliases(session_id)

    async def handle_session_revocation(
        self,
        session_id: str,
        *,
        reason: str = "session_revoked",
        close_connections: bool = True,
        close_code: int = 4401,
    ) -> bool:
        """Finalize a revoked session and close related WebSocket connections."""
        session_id = self.resolve_session_id(session_id)
        had_session = session_id in self.active_sessions
        if close_connections:
            conn = getattr(self, "connection_manager", None)
            if conn:
                try:
                    await conn.close_session(session_id, code=close_code, reason=reason)
                except Exception as exc:
                    logger.debug(
                        "Fermeture WS pour %s impossible: %s",
                        session_id,
                        exc,
                    )
        if had_session:
            await self.finalize_session(session_id)
        else:
            self._session_threads.pop(session_id, None)
            self._session_users.pop(session_id, None)
            keys_to_remove = [key for key in self._hydrated_threads if key[0] == session_id]
            for key in keys_to_remove:
                self._hydrated_threads.pop(key, None)
            self._cleanup_session_aliases(session_id)
        return had_session

    async def update_and_save_session(self, session_id: str, update_data: Dict[str, Any]):
        """Met à jour une session active et la sauvegarde."""
        session_id = self.resolve_session_id(session_id)
        session = self.get_session(session_id)
        if not session:
            logger.error(f"Impossible de mettre à jour la session {session_id} : non trouvée.")
            return

        try:
            if not isinstance(session.metadata, dict):
                session.metadata = {}
            
            session.metadata.update(update_data.get("metadata", {}))
            logger.info(f"Session {session_id} mise à jour avec les données du débat.")
            
            await self.db_manager.save_session(session)
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour et sauvegarde de la session {session_id}: {e}", exc_info=True)

    # --- Helper WS facultatif ---
    async def publish_event(self, session_id: str, type_: str, payload: Dict[str, Any]):
        session_id = self.resolve_session_id(session_id)
        cm = getattr(self, "connection_manager", None)
        if cm:
            await cm.send_personal_message({"type": type_, "payload": payload}, session_id)
        else:
            logger.warning("Aucun ConnectionManager attaché au SessionManager (publish_event ignoré).")

    def get_thread_id_for_session(self, session_id: str) -> Optional[str]:
        session_id = self.resolve_session_id(session_id)
        return self._session_threads.get(session_id)
