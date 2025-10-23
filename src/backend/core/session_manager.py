# src/backend/core/session_manager.py
# V13.3 - FIX: Ajout du système de timeout d'inactivité (3 minutes)
import logging
import json
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple, Set
from uuid import uuid4

# Imports corrigés pour refléter la structure réelle
from backend.shared.models import Session, ChatMessage, AgentMessage, Role
from backend.core.database.manager import DatabaseManager
from backend.core.database import queries  # Import du module queries
from backend.features.memory.analyzer import MemoryAnalyzer

logger = logging.getLogger(__name__)

# Configuration du timeout d'inactivité
import os  # noqa: E402

INACTIVITY_TIMEOUT_MINUTES = int(os.getenv("SESSION_INACTIVITY_TIMEOUT_MINUTES", "30"))
CLEANUP_INTERVAL_SECONDS = int(os.getenv("SESSION_CLEANUP_INTERVAL_SECONDS", "60"))
WARNING_BEFORE_TIMEOUT_SECONDS = int(os.getenv("SESSION_WARNING_BEFORE_TIMEOUT_SECONDS", "120"))

# Métriques Prometheus pour le monitoring des sessions
try:
    from prometheus_client import Counter, Gauge, Histogram

    SESSIONS_TIMEOUT_TOTAL = Counter(
        'sessions_timeout_total',
        'Total number of sessions closed due to inactivity timeout'
    )
    SESSIONS_WARNING_SENT_TOTAL = Counter(
        'sessions_warning_sent_total',
        'Total number of inactivity warnings sent to users'
    )
    SESSIONS_ACTIVE_GAUGE = Gauge(
        'sessions_active_current',
        'Current number of active sessions in memory'
    )
    SESSION_INACTIVITY_DURATION = Histogram(
        'session_inactivity_duration_seconds',
        'Duration of session inactivity before timeout',
        buckets=[60, 120, 180, 240, 300, 600]
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.warning("Prometheus client non disponible, métriques de session désactivées")

class SessionManager:
    """
    Gère les sessions de chat actives en mémoire et leur persistance.
    V13.3: Ajout du système de timeout d'inactivité automatique.
    """

    def __init__(self, db_manager: DatabaseManager, memory_analyzer: Optional[MemoryAnalyzer] = None, vector_service: Any = None):
        self.db_manager = db_manager
        self.memory_analyzer = memory_analyzer
        self.vector_service = vector_service  # 🆕 Phase Agent Memory: Needed for HandshakeHandler
        self.active_sessions: Dict[str, Session] = {}
        self._session_user_cache: Dict[str, str] = {}
        # ConnectionManager sera injecté dynamiquement par websocket.ConnectionManager
        self.connection_manager = None
        self._session_threads: Dict[str, str] = {}
        self._session_users: Dict[str, str] = {}
        self._hydrated_threads: Dict[Tuple[str, str], bool] = {}
        self._session_alias_to_canonical: Dict[str, str] = {}
        self._session_canonical_to_aliases: Dict[str, Set[str]] = {}

        # Tâche de nettoyage périodique
        self._cleanup_task: Optional[asyncio.Task[None]] = None
        self._is_running = False

        is_ready = self.memory_analyzer is not None
        logger.info(f"SessionManager V13.3 initialisé avec timeout d'inactivité de {INACTIVITY_TIMEOUT_MINUTES}min. MemoryAnalyzer prêt : {is_ready}")

    def _ensure_analyzer_ready(self):
        """Vérifie que le service dépendant est bien injecté avant utilisation."""
        if not self.memory_analyzer:
            logger.error("Dépendance 'memory_analyzer' non injectée dans SessionManager.")
            raise ReferenceError("SessionManager: memory_analyzer manquant.")

    def start_cleanup_task(self):
        """Démarre la tâche de nettoyage automatique des sessions inactives."""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._is_running = True
            self._cleanup_task = asyncio.create_task(self._cleanup_inactive_sessions_loop())
            logger.info("Tâche de nettoyage des sessions inactives démarrée.")

    async def stop_cleanup_task(self):
        """Arrête la tâche de nettoyage automatique."""
        self._is_running = False
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            logger.info("Tâche de nettoyage des sessions inactives arrêtée.")

    async def _cleanup_inactive_sessions_loop(self):
        """Boucle de nettoyage périodique des sessions inactives."""
        logger.info(f"Démarrage de la boucle de nettoyage (intervalle: {CLEANUP_INTERVAL_SECONDS}s)")
        while self._is_running:
            try:
                await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)
                await self._cleanup_inactive_sessions()
            except asyncio.CancelledError:
                logger.info("Boucle de nettoyage annulée.")
                break
            except Exception as e:
                logger.error(f"Erreur dans la boucle de nettoyage: {e}", exc_info=True)

    async def _cleanup_inactive_sessions(self):
        """Nettoie les sessions inactives depuis plus de INACTIVITY_TIMEOUT_MINUTES minutes."""
        now = datetime.now(timezone.utc)
        timeout_threshold = timedelta(minutes=INACTIVITY_TIMEOUT_MINUTES)
        warning_threshold = timedelta(minutes=INACTIVITY_TIMEOUT_MINUTES, seconds=-WARNING_BEFORE_TIMEOUT_SECONDS)
        sessions_to_cleanup = []
        sessions_to_warn = []

        # Debug: Log du nombre de sessions actives
        active_count = len(self.active_sessions)
        if active_count > 0:
            logger.debug(f"[Inactivity Check] {active_count} session(s) active(s) à vérifier")

        for session_id, session in list(self.active_sessions.items()):
            try:
                last_activity = getattr(session, 'last_activity', None)
                if last_activity is None:
                    # Si pas de last_activity, utiliser start_time
                    last_activity = session.start_time

                inactivity_duration = now - last_activity

                # Debug: Log de l'état de chaque session
                logger.debug(
                    f"[Inactivity Check] Session {session_id[:8]}... inactive depuis {inactivity_duration.total_seconds():.0f}s "
                    f"(seuil avertissement: {warning_threshold.total_seconds():.0f}s, seuil timeout: {timeout_threshold.total_seconds():.0f}s)"
                )

                # Vérifier si un avertissement a déjà été envoyé
                warning_sent = getattr(session, '_warning_sent', False)

                # Vérifier si la session doit être nettoyée (UNIQUEMENT si avertissement déjà envoyé)
                if inactivity_duration > timeout_threshold and warning_sent:
                    sessions_to_cleanup.append((session_id, inactivity_duration))
                    logger.debug(f"[Inactivity Check] Session {session_id[:8]}... marquée pour nettoyage (avertissement déjà envoyé)")
                # Vérifier si un avertissement doit être envoyé (session au-delà du seuil mais pas encore avertie)
                elif inactivity_duration > warning_threshold and not warning_sent:
                    sessions_to_warn.append((session_id, inactivity_duration))
                    logger.debug(f"[Inactivity Check] Session {session_id[:8]}... marquée pour avertissement")
            except Exception as e:
                logger.error(f"Erreur lors de la vérification d'inactivité pour session {session_id}: {e}")

        # Envoyer des avertissements
        for session_id, duration in sessions_to_warn:
            try:
                remaining_seconds = int((timeout_threshold - duration).total_seconds())
                logger.info(f"Envoi d'avertissement à la session {session_id} (déconnexion dans {remaining_seconds}s)")

                # Marquer l'avertissement comme envoyé
                session = self.active_sessions.get(session_id)
                if session:
                    setattr(session, '_warning_sent', True)

                # Envoyer l'avertissement via WebSocket
                if self.connection_manager:
                    notification_payload = {
                        "notification_type": "inactivity_warning",
                        "message": f"Votre session sera déconnectée dans {remaining_seconds} secondes en raison d'inactivité.",
                        "remaining_seconds": remaining_seconds,
                        "duration": 5000  # Durée d'affichage en ms
                    }
                    logger.info(f"[Notification] Envoi notification inactivité à {session_id[:8]}... payload: {notification_payload}")
                    await self.connection_manager.send_system_message(session_id, notification_payload)
                    logger.info(f"[Notification] Notification inactivité envoyée avec succès à {session_id[:8]}...")
                else:
                    logger.warning(f"[Notification] ConnectionManager non disponible pour session {session_id[:8]}...")

                # Métrique Prometheus
                if PROMETHEUS_AVAILABLE:
                    SESSIONS_WARNING_SENT_TOTAL.inc()

            except Exception as e:
                logger.error(f"Erreur lors de l'envoi d'avertissement pour session {session_id}: {e}", exc_info=True)

        # Nettoyer les sessions inactives
        for session_id, duration in sessions_to_cleanup:
            try:
                logger.info(f"Session {session_id} inactive depuis {duration.total_seconds():.0f}s, nettoyage...")
                await self.handle_session_revocation(
                    session_id,
                    reason="inactivity_timeout",
                    close_connections=True,
                    close_code=4408,  # Code personnalisé pour timeout d'inactivité
                )

                # Métriques Prometheus
                if PROMETHEUS_AVAILABLE:
                    SESSIONS_TIMEOUT_TOTAL.inc()
                    SESSION_INACTIVITY_DURATION.observe(duration.total_seconds())

            except Exception as e:
                logger.error(f"Erreur lors du nettoyage de la session {session_id}: {e}", exc_info=True)

        # Mettre à jour la métrique du nombre de sessions actives
        if PROMETHEUS_AVAILABLE:
            SESSIONS_ACTIVE_GAUGE.set(len(self.active_sessions))

        if sessions_to_cleanup:
            logger.info(f"{len(sessions_to_cleanup)} session(s) nettoyée(s) pour inactivité.")
        if sessions_to_warn:
            logger.info(f"{len(sessions_to_warn)} avertissement(s) d'inactivité envoyé(s).")

    def _update_session_activity(self, session_id: str) -> None:
        """Met à jour le timestamp de dernière activité d'une session."""
        session_id = self.resolve_session_id(session_id)
        session = self.active_sessions.get(session_id)
        if session:
            session.last_activity = datetime.now(timezone.utc)
            # Réinitialiser le flag d'avertissement lors d'une nouvelle activité
            if hasattr(session, '_warning_sent'):
                session._warning_sent = False

    async def ensure_session(self, session_id: str, user_id: str, *, thread_id: Optional[str] = None,
                             history_limit: int = 200) -> Session:
        """Garantit qu'une session est active en mémoire et hydratée depuis les persistances disponibles."""
        session_id = self.resolve_session_id(session_id)
        session = self.active_sessions.get(session_id)

        if not session:
            session = await self.load_session_from_db(session_id)
            if not session:
                now = datetime.now(timezone.utc)
                session = Session(
                    id=session_id,
                    user_id=user_id,
                    start_time=now,
                    end_time=None,
                    last_activity=now,
                    history=[],
                )
                if thread_id:
                    session.metadata["thread_id"] = thread_id
                self.active_sessions[session_id] = session
                logger.info(f"Session active créée : {session_id} pour l'utilisateur {user_id}")
            else:
                logger.info(f"Session {session_id} rechargée depuis la BDD")

        # Mettre à jour l'activité à chaque accès
        self._update_session_activity(session_id)

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

    def create_session(self, session_id: str, user_id: str) -> Session:
        """Crée une session et la garde active en mémoire (compatibilité synchrone)."""
        session_id = self.resolve_session_id(session_id)
        if session_id in self.active_sessions:
            logger.warning(f"Tentative de création d'une session déjà existante: {session_id}")
            # Mettre à jour l'activité même si elle existe déjà
            self._update_session_activity(session_id)
            return self.active_sessions[session_id]

        now = datetime.now(timezone.utc)
        session = Session(
            id=session_id,
            user_id=user_id,
            start_time=now,
            end_time=None,
            last_activity=now,
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

            now = datetime.now(timezone.utc)
            session = Session(
                id=session_dict['id'],
                user_id=session_dict['user_id'],
                start_time=datetime.fromisoformat(session_dict['created_at']),
                end_time=datetime.fromisoformat(session_dict['updated_at']),
                last_activity=now,  # Initialiser avec maintenant lors du chargement
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
            user_scope = (
                self._session_users.get(session_id)
                or self._session_user_cache.get(session_id)
                or getattr(self.active_sessions.get(session_id), 'user_id', None)
            )
            thread_row = await queries.get_thread_any(
                self.db_manager,
                thread_id,
                session_id,
                user_id=user_scope,
            )
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

            messages = await queries.get_messages(
                self.db_manager,
                thread_id,
                session_id=session_id,
                user_id=user_scope,
                limit=limit,
            )
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

    async def add_message_to_session(self, session_id: str, message: ChatMessage | AgentMessage) -> None:
        session_id = self.resolve_session_id(session_id)
        session = self.get_session(session_id)
        if session:
            # Mettre à jour l'activité
            self._update_session_activity(session_id)

            payload = message.model_dump(mode='json')
            if "message" in payload and "content" not in payload:
                payload["content"] = payload.pop("message")
            extra_meta = getattr(message, 'meta', None)
            if isinstance(extra_meta, dict) and extra_meta:
                payload['meta'] = extra_meta
            payload.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
            session.history.append(payload)

            await self._persist_message(session_id, payload)
        else:
            logger.error(f"Impossible d'ajouter un message : session {session_id} non trouvée.")

    def get_message_by_id(self, session_id: str, message_id: str) -> Optional[Dict[str, Any]]:
        session_id = self.resolve_session_id(session_id)
        history = self.get_full_history(session_id)
        if not history:
            return None
        for item in history:
            try:
                if item and str(item.get('id')) == str(message_id):
                    return item
            except Exception:
                continue
        return None

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

    async def _persist_message(self, session_id: str, payload: Dict[str, Any]) -> None:
        session_id = self.resolve_session_id(session_id)
        raw_thread_id = (
            self._session_threads.get(session_id)
            or payload.get("thread_id")
            or (payload.get("meta") or {}).get("thread_id")
        )
        thread_id = str(raw_thread_id).strip() if raw_thread_id else ""

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

        def _sanitize_candidate(value: Optional[Any]) -> str:
            if value is None:
                return ""
            try:
                candidate = str(value).strip()
            except Exception:
                candidate = ""
            return candidate

        thread_id = _sanitize_candidate(thread_id)

        user_scope = (
            self._session_users.get(session_id)
            or self._session_user_cache.get(session_id)
            or getattr(self.active_sessions.get(session_id), 'user_id', None)
        )

        async def _resolve_latest_thread_id() -> Optional[str]:
            try:
                threads = await queries.get_threads(
                    self.db_manager,
                    session_id,
                    user_id=user_scope,
                    type_="chat",
                    limit=1,
                )
            except Exception as fetch_err:
                logger.warning(
                    "Unable to fetch fallback thread for session %s: %s",
                    session_id,
                    fetch_err,
                )
                return None
            for item in threads or []:
                candidate = _sanitize_candidate(item.get("id"))
                if candidate:
                    return candidate
            return None

        if not thread_id:
            fallback_thread_id = await _resolve_latest_thread_id()
            if not fallback_thread_id:
                logger.warning(
                    "Skip message persistence: no thread available for session %s.",
                    session_id,
                )
                return
            thread_id = fallback_thread_id
            self._session_threads[session_id] = thread_id

        try:
            thread_row = await queries.get_thread_any(
                self.db_manager,
                thread_id,
                session_id,
                user_id=user_scope,
            )
        except Exception as thread_err:
            logger.debug(
                "get_thread_any failed for session=%s thread=%s: %s",
                session_id,
                thread_id,
                thread_err,
            )
            thread_row = None

        if not thread_row:
            fallback_thread_id = await _resolve_latest_thread_id()
            if fallback_thread_id:
                if fallback_thread_id != thread_id:
                    logger.warning(
                        "Thread %s not found for session %s. Using fallback %s.",
                        thread_id,
                        session_id,
                        fallback_thread_id,
                    )
                thread_id = fallback_thread_id
                self._session_threads[session_id] = thread_id
            else:
                logger.warning(
                    "Skip message persistence: unable to resolve thread for session %s.",
                    session_id,
                )
                return

        meta.setdefault("thread_id", thread_id)
        payload["thread_id"] = thread_id

        original_message_id = str(payload.get("id") or "").strip()
        try:
            result = await queries.add_message(
                self.db_manager,
                thread_id,
                session_id,
                user_id=user_scope,
                role=role,
                content=content,
                agent_id=agent_id,
                tokens=tokens_value,
                meta=meta,
                message_id=payload.get("id"),
            )
            persisted_id = str(result.get("message_id") or result.get("id") or "").strip()
            if not persisted_id:
                persisted_id = original_message_id
            if persisted_id:
                payload["id"] = persisted_id
            client_message_id = original_message_id or persisted_id
            await self.publish_event(session_id, "ws:message_persisted", {
                "message_id": client_message_id,
                "thread_id": thread_id,
                "role": role,
                "created_at": result.get("created_at"),
                "id": persisted_id,
                "persisted": True,
                "agent_id": agent_id,
                "session_id": session_id,
            })
        except Exception as e:
            logger.error(f"Persistance du message pour la session {session_id} a echoue: {e}", exc_info=True)

    async def finalize_session(self, session_id: str) -> None:
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

    async def update_and_save_session(self, session_id: str, update_data: Dict[str, Any]) -> None:
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
    async def publish_event(self, session_id: str, type_: str, payload: Dict[str, Any]) -> None:
        session_id = self.resolve_session_id(session_id)
        cm = getattr(self, "connection_manager", None)
        if cm:
            await cm.send_personal_message({"type": type_, "payload": payload}, session_id)
        else:
            logger.warning("Aucun ConnectionManager attaché au SessionManager (publish_event ignoré).")

    def get_thread_id_for_session(self, session_id: str) -> Optional[str]:
        session_id = self.resolve_session_id(session_id)
        return self._session_threads.get(session_id)

