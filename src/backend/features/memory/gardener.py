# src/backend/features/memory/gardener.py
# V2.9.0 - Vitality calibration + monitoring metrics
import logging
import os
import asyncio
import uuid
import json
import re
import hashlib
import unicodedata
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone

from math import isfinite, floor, ceil
from statistics import mean, median

from backend.core.database.manager import DatabaseManager
from backend.features.memory.vector_service import VectorService
from backend.features.memory.analyzer import MemoryAnalyzer
from backend.core.database import queries  # ← NEW: accès threads/messages

logger = logging.getLogger(__name__)

_CODE_PATTERNS = [
    r"(?:pour\s+(?P<agent>anima|neo|nexus)\s*,?\s*)?(?:mon|ton|ce|le)\s*mot[-\s]?code\s*(?:est|:|=)\s*[«\"'’]?\s*(?P<value>[A-Za-zÀ-ÖØ-öø-ÿ0-9_\- ]+?)\s*[»\"'’]?(?:[.!?,;:\)]|$)",
    r"(?:mon|ton|ce|le)\s*mot[-\s]?code\s*pour\s+(?P<agent>anima|neo|nexus)\s*(?:est|:|=)\s*[«\"'’]?\s*(?P<value>[A-Za-zÀ-ÖØ-öø-ÿ0-9_\- ]+?)\s*[»\"'’]?(?:[.!?,;:\)]|$)",
    r"(?:pour\s+(?P<agent>anima|neo|nexus)\s*,?\s*)?mon\s*mot[-\s]?code\s*(?:est|:)\s*[«\"'’]?\s*(?P<value>[A-Za-zÀ-ÖØ-öø-ÿ0-9_\-]+)\s*[»\"'’]?",
    r"mon\s*mot[-\s]?code\s*pour\s+(?P<agent>anima|neo|nexus)\s*(?:est|:)\s*[«\"'’]?\s*(?P<value>[A-Za-zÀ-ÖØ-öø-ÿ0-9_\-]+)\s*[»\"'’]?",
    r"mot[-\s]?code\s*(?:est|:|=)\s*[«\"'’]?\s*(?P<value>[A-Za-zÀ-ÖØ-öø-ÿ0-9_\- ]+?)\s*[»\"'’]?(?:[.!?,;:\)]|$)",
]


_PREFERENCE_REGEX_PATTERNS = [
    re.compile(
        r"\bje\s+(?:pr[eé]f[eè]re|souhaite|voudrais|veux|adore|aime|d[eé]teste|n(?:'|e)\s*(?:veux\s+pas|veux|aime|utiliser|utilise)|évite|refuse)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bje\s+(?:planifie|pr[eé]vois|compte|vais|dois|pense\s+faire)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bj'aimerais\s+(?:que|faire)|je\s+vais\s+(?:faire|prendre)|je\s+compte\s+sur\s+toi\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:i\s+prefer|my\s+preference\s+is|i\s+would\s+like|i\s+want|i\s+intend|i\s+plan\s+to|please\s+remember|please\s+avoid)\b",
        re.IGNORECASE,
    ),
]
_IMPERATIVE_STARTERS = (
    "merci de",
    "peux-tu",
    "pense à",
    "rappelle-moi",
    "n'oublie pas",
    "favorise",
    "privilégie",
    "cesse",
    "arrête",
    "évite",
    "garde",
    "utilise",
    "ne propose pas",
    "fait en sorte",
    "assure-toi",
    "do not",
    "please avoid",
    "please favour",
)
_MAX_PREFERENCE_CANDIDATES = 8
_PREFERENCE_CONFIDENCE_EVENT_THRESHOLD = 0.6

_PREFERENCE_CLASSIFICATION_SCHEMA = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "type": {
                        "type": "string",
                        "enum": ["preference", "intent", "constraint", "neutral"],
                    },
                    "topic": {"type": "string"},
                    "action": {"type": "string"},
                    "timeframe": {"type": "string"},
                    "sentiment": {"type": "string"},
                    "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                    "summary": {"type": "string"},
                },
                "required": ["id", "type", "confidence"],
            },
        }
    },
    "required": ["items"],
}


_CLASSIFICATION_KEY_ALIASES = {
    "items": {
        "items",
        "item",
        "elements",
        "element",
        "entries",
        "records",
        "liste",
        "list",
        "points",
        "resultats",
        "resultat",
        "reponses",
        "reponse",
    },
    "id": {"id", "identifier", "identifiant"},
    "type": {"type", "categorie", "categories", "category", "classe"},
    "topic": {"topic", "sujet", "theme", "themes", "thematique", "thematiques"},
    "action": {"action", "actions", "tache", "taches", "task", "tasks", "verbe"},
    "timeframe": {
        "timeframe",
        "delai",
        "delais",
        "echeance",
        "echeances",
        "periode",
        "periodes",
        "horizon",
        "date",
        "dates",
    },
    "sentiment": {
        "sentiment",
        "sentiments",
        "ton",
        "tonalite",
        "tonalites",
        "valence",
        "valences",
        "opinion",
    },
    "confidence": {
        "confidence",
        "confiance",
        "confiances",
        "score",
        "scores",
        "probabilite",
        "probabilites",
        "certitude",
        "certitudes",
    },
    "summary": {
        "summary",
        "resume",
        "resumes",
        "synthese",
        "syntheses",
        "description",
        "descriptions",
    },
}


def _sanitize_json_key(name: Any) -> str:
    text = str(name or "").strip()
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKD", text)
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    normalized = normalized.lower()
    return re.sub(r"[^a-z0-9]", "", normalized)


def _canonicalize_field_key(name: Any) -> Optional[str]:
    sanitized = _sanitize_json_key(name)
    if not sanitized:
        return None
    for canonical, aliases in _CLASSIFICATION_KEY_ALIASES.items():
        if sanitized in aliases:
            return canonical
    return None


def _normalize_classification_item(raw: Dict[str, Any]) -> Dict[str, Any]:
    normalized: Dict[str, Any] = {}
    for key, value in (raw or {}).items():
        canonical = _canonicalize_field_key(key)
        target_key = canonical or key
        normalized[target_key] = value
    conf_value = normalized.get("confidence")
    if isinstance(conf_value, str):
        cleaned = conf_value.strip().replace(" ", "")
        is_percent = cleaned.endswith("%")
        cleaned = cleaned.replace("%", "").replace(",", ".")
        try:
            conf_float = float(cleaned)
            if is_percent or conf_float > 1.0:
                conf_float = conf_float / 100.0
            normalized["confidence"] = conf_float
        except ValueError:
            pass
    return normalized


def _normalize_classification_payload(payload: Any) -> Dict[str, Any]:
    normalized_items: List[Dict[str, Any]] = []
    if isinstance(payload, dict):
        candidate_list: Optional[List[Any]] = None
        for key, value in payload.items():
            if _canonicalize_field_key(key) == "items" and isinstance(value, list):
                candidate_list = value
                break
        if candidate_list is None:
            for value in payload.values():
                if isinstance(value, list):
                    candidate_list = value
                    break
        if candidate_list:
            normalized_items = [
                _normalize_classification_item(item)
                for item in candidate_list
                if isinstance(item, dict)
            ]
    elif isinstance(payload, list):
        normalized_items = [
            _normalize_classification_item(item)
            for item in payload
            if isinstance(item, dict)
        ]
    return {"items": normalized_items}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_iso_ts(raw: Any) -> Optional[datetime]:
    """Best effort parser for ISO timestamps stored in metadata."""
    if not raw:
        return None
    if isinstance(raw, datetime):
        return raw if raw.tzinfo else raw.replace(tzinfo=timezone.utc)
    if isinstance(raw, (int, float)) and isfinite(raw):
        try:
            return datetime.fromtimestamp(float(raw), tz=timezone.utc)
        except Exception:
            return None
    if isinstance(raw, str):
        candidate = raw.strip()
        if not candidate:
            return None
        candidate = (
            candidate.replace("Z", "+00:00") if candidate.endswith("Z") else candidate
        )
        try:
            parsed = datetime.fromisoformat(candidate)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            try:
                return datetime.fromisoformat(candidate + "+00:00")
            except Exception:
                return None
    return None


def _unique(seq: List[str]) -> List[str]:
    seen, out = set(), []
    for s in seq or []:
        key = s.strip().lower()
        if key and key not in seen:
            out.append(s.strip())
            seen.add(key)
    return out


def _percentile(values: List[float], percentile: float) -> float:
    if not values:
        return 0.0
    if percentile <= 0:
        return min(values)
    if percentile >= 1:
        return max(values)
    ordered = sorted(values)
    k = (len(ordered) - 1) * percentile
    lower = floor(k)
    upper = ceil(k)
    if lower == upper:
        return ordered[int(k)]
    lower_val = ordered[lower]
    upper_val = ordered[upper]
    return lower_val + (upper_val - lower_val) * (k - lower)


def _agent_norm(name: Optional[str]) -> Optional[str]:
    if not name:
        return None
    n = name.strip().lower()
    return n if n in {"anima", "neo", "nexus"} else None


def _fact_id(session_id: str, key: str, agent: Optional[str], value: str) -> str:
    import hashlib

    base = f"{session_id}:{key}:{agent or 'global'}:{value}"
    return hashlib.sha1(base.encode("utf-8")).hexdigest()


_VALUE_TRAIL_RE = re.compile(r"[\s\.\,\;\:\!\?]+$")


def _clean_value(v: str) -> str:
    v = (v or "").strip()
    v = _VALUE_TRAIL_RE.sub("", v)
    v = re.sub(r"\s{2,}", " ", v)
    return v


def _normalize_for_scan(text: str) -> str:
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKD", text)
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return normalized.lower().strip()


def _looks_imperative(sentence: str) -> bool:
    normalized = _normalize_for_scan(sentence)
    if not normalized:
        return False
    for starter in _IMPERATIVE_STARTERS:
        if normalized.startswith(starter):
            return True
    return False


def _preference_record_id(
    user_identifier: Optional[str], pref_type: str, topic_key: str
) -> str:
    user_part = user_identifier or "anonymous"
    base = f"{user_part}:{pref_type}:{topic_key}"
    return hashlib.sha1(base.encode("utf-8")).hexdigest()


class MemoryGardener:
    """
    MEMORY GARDENER V2.9.0
    - Mode historique (sessions) inchange.
    - NEW: consolidation ciblee d'un THREAD via thread_id (analyse no-persist + vectorisation).
    - Calibration vitalite configurable + metriques monitoring.
    """

    KNOWLEDGE_COLLECTION_NAME = "emergence_knowledge"
    PREFERENCE_COLLECTION_NAME = "memory_preferences"
    BASE_DECAY = 0.03
    STALE_THRESHOLD_DAYS = 14
    STALE_DECAY = 0.07
    ARCHIVE_THRESHOLD_DAYS = 45
    ARCHIVE_DECAY = 0.2
    MIN_VITALITY = 0.12
    MAX_VITALITY = 1.0
    RECALL_THRESHOLD = 0.3
    USAGE_BOOST = 0.25

    def __init__(
        self,
        db_manager: DatabaseManager,
        vector_service: VectorService,
        memory_analyzer: MemoryAnalyzer,
    ):
        self.db = db_manager
        self.vector_service = vector_service
        self.analyzer = memory_analyzer

        self.base_decay = self._load_numeric_env(
            "MEMORY_DECAY_BASE", self.BASE_DECAY, min_value=0.0, max_value=1.0
        )
        self.stale_threshold_days = self._load_numeric_env(
            "MEMORY_DECAY_STALE_THRESHOLD_DAYS",
            self.STALE_THRESHOLD_DAYS,
            min_value=0,
            as_int=True,
        )
        self.stale_decay = self._load_numeric_env(
            "MEMORY_DECAY_STALE_DECAY", self.STALE_DECAY, min_value=0.0, max_value=1.0
        )
        self.archive_threshold_days = self._load_numeric_env(
            "MEMORY_DECAY_ARCHIVE_THRESHOLD_DAYS",
            self.ARCHIVE_THRESHOLD_DAYS,
            min_value=0,
            as_int=True,
        )
        self.archive_decay = self._load_numeric_env(
            "MEMORY_DECAY_ARCHIVE_DECAY",
            self.ARCHIVE_DECAY,
            min_value=0.0,
            max_value=1.0,
        )
        self.min_vitality = self._load_numeric_env(
            "MEMORY_DECAY_MIN_VITALITY", self.MIN_VITALITY, min_value=0.0, max_value=1.0
        )
        self.max_vitality = self._load_numeric_env(
            "MEMORY_DECAY_MAX_VITALITY", self.MAX_VITALITY, min_value=0.0, max_value=1.0
        )
        if self.min_vitality >= self.max_vitality:
            self.min_vitality = max(0.0, self.max_vitality - 0.05)
        self.recall_threshold = self._load_numeric_env(
            "MEMORY_RECALL_THRESHOLD",
            self.RECALL_THRESHOLD,
            min_value=0.0,
            max_value=1.0,
        )
        self.usage_boost = self._load_numeric_env(
            "MEMORY_USAGE_BOOST", self.USAGE_BOOST, min_value=0.0, max_value=1.0
        )

        self.knowledge_collection = self.vector_service.get_or_create_collection(
            self.KNOWLEDGE_COLLECTION_NAME
        )
        self.preference_collection = self.vector_service.get_or_create_collection(
            self.PREFERENCE_COLLECTION_NAME
        )

        logger.info(
            "MemoryGardener V2.9.0 configured (base_decay=%.3f | stale=%dd | archive=%dd | min_v=%.2f | max_v=%.2f)",
            self.base_decay,
            self.stale_threshold_days,
            self.archive_threshold_days,
            self.min_vitality,
            self.max_vitality,
        )

    def _load_numeric_env(
        self,
        env_name: str,
        default: float,
        *,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        as_int: bool = False,
    ):
        raw = os.getenv(env_name)
        if raw is None or str(raw).strip() == "":
            return int(default) if as_int else float(default)
        try:
            value = int(raw) if as_int else float(raw)
        except (TypeError, ValueError):
            logger.warning(
                "Invalid value '%s' for %s; falling back to default %s.",
                raw,
                env_name,
                default,
            )
            return int(default) if as_int else float(default)
        if min_value is not None and value < min_value:
            logger.warning(
                "Value %s for %s below minimum %s; clamping.",
                value,
                env_name,
                min_value,
            )
            value = min_value
        if max_value is not None and value > max_value:
            logger.warning(
                "Value %s for %s above maximum %s; clamping.",
                value,
                env_name,
                max_value,
            )
            value = max_value
        return int(value) if as_int else float(value)

    @staticmethod
    def _normalize_agent_id(agent_id: Optional[str]) -> Optional[str]:
        if agent_id is None:
            return None
        try:
            value = str(agent_id).strip().lower()
        except Exception:
            return None
        return value or None

    @staticmethod
    def _filter_history_for_agent(history: Optional[List[Dict[str, Any]]], agent_id: Optional[str]) -> List[Dict[str, Any]]:
        if not history:
            return []
        normalized = MemoryGardener._normalize_agent_id(agent_id)
        if not normalized:
            return list(history)
        filtered: List[Dict[str, Any]] = []
        for item in history:
            if not isinstance(item, dict):
                continue
            role = str(item.get("role") or "").strip().lower()
            if role == "assistant":
                agent_value = MemoryGardener._normalize_agent_id(item.get("agent_id") or item.get("agent"))
                if agent_value == normalized:
                    filtered.append(item)
            else:
                filtered.append(item)
        return filtered

    async def tend_the_garden(
        self,
        consolidation_limit: int = 10,
        thread_id: Optional[str] = None,
        session_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        normalized_agent = self._normalize_agent_id(agent_id)

        if thread_id:
            return await self._tend_single_thread(
                thread_id,
                session_id=session_id,
                agent_id=normalized_agent,
                user_id=user_id,
            )

        logger.info(
            "Le jardinier commence sa ronde dans le jardin de la mémoire (mode sessions)…"
        )
        if session_id:
            session_row = await self._fetch_session_by_id(session_id)
            if not session_row:
                logger.info(f"Session {session_id} introuvable pour la consolidation ciblée.")
                return {
                    "status": "success",
                    "message": "Aucune session à traiter.",
                    "consolidated_sessions": 0,
                    "new_concepts": 0,
                }
            sessions = [session_row]
            owner_uid = session_row.get("user_id") or None
            if user_id and owner_uid and owner_uid != user_id:
                logger.warning(
                    f"Session {session_id} ignorée pour l'utilisateur {user_id} (propriétaire: {owner_uid})."
                )
                return {
                    "status": "success",
                    "message": "Session non autorisée pour cet utilisateur.",
                    "consolidated_sessions": 0,
                    "new_concepts": 0,
                }
        else:
            sessions = await self._fetch_recent_sessions(
                limit=consolidation_limit, user_id=user_id
            )
            if not sessions:
                logger.info("Aucune session récente à traiter. Le jardin est en ordre.")
                await self._decay_knowledge()
                return {
                    "status": "success",
                    "message": "Aucune session à traiter.",
                    "consolidated_sessions": 0,
                    "new_concepts": 0,
                }

        processed_ids: List[str] = []
        new_items_count = 0
        for s in sessions:
            sid: str = s["id"]
            uid: Optional[str] = s.get("user_id")
            try:
                history = self._extract_history(s.get("session_data"))
                concepts = self._parse_concepts(s.get("extracted_concepts"))
                entities = self._parse_entities(s.get("extracted_entities"))
                all_concepts = _unique((concepts or []) + (entities or []))

                facts = self._extract_facts_from_history(history)

                if not concepts and history:
                    # ✅ FIX CRITIQUE P2 Sprint 3: Passer user_id pour extraction préférences
                    await self.analyzer.analyze_session_for_concepts(
                        session_id=sid, history=history, user_id=uid
                    )
                    db_row = await self.db.fetch_one(
                        "SELECT extracted_concepts, extracted_entities, user_id FROM sessions WHERE id = ?",
                        (sid,),
                    )
                    row_payload: Dict[str, Any] = (
                        dict(db_row) if db_row is not None else {}
                    )
                    concepts = self._parse_concepts(
                        row_payload.get("extracted_concepts")
                    )
                    entities = self._parse_entities(
                        row_payload.get("extracted_entities")
                    )
                    all_concepts = _unique((concepts or []) + (entities or []))

                added_any = False
                facts_to_add = []
                for fact in facts:
                    if not await self._fact_already_vectorized(
                        sid, fact["key"], fact.get("agent")
                    ):
                        facts_to_add.append(fact)
                if facts_to_add:
                    await self._record_facts_in_sql(facts_to_add, s, uid)
                    await self._vectorize_facts(facts_to_add, s, uid)
                    new_items_count += len(facts_to_add)
                    added_any = True

                pref_added = await self._process_preference_pipeline(history, sid, uid)
                if pref_added:
                    new_items_count += pref_added
                    added_any = True

                if all_concepts and not await self._any_vectors_for_session_type(
                    sid, "concept"
                ):
                    await self._record_concepts_in_sql(all_concepts, s, uid)
                    await self._vectorize_concepts(all_concepts, s, uid)
                    new_items_count += len(all_concepts)
                    added_any = True

                if not added_any:
                    logger.info(
                        f"Session {sid}: déjà vectorisée ou aucun nouvel item — skip."
                    )
                processed_ids.append(sid)

            except Exception as e:
                logger.error(
                    f"Erreur lors de la consolidation pour la session {sid}: {e}",
                    exc_info=True,
                )

        await self._mark_sessions_as_consolidated(processed_ids)
        await self._decay_knowledge()

        report = {
            "status": "success",
            "message": "La ronde du jardinier est terminée.",
            "consolidated_sessions": len(processed_ids),
            "new_concepts": new_items_count,
        }
        logger.info(report)
        return report

    # ---------- NEW: consolidation d’un thread ----------
    async def _tend_single_thread(
        self,
        thread_id: str,
        session_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        tid = (thread_id or "").strip()
        if not tid:
            return {
                "status": "success",
                "message": "thread_id vide.",
                "consolidated_sessions": 0,
                "new_concepts": 0,
            }

        normalized_agent = self._normalize_agent_id(agent_id)
        try:
            normalized_session = (session_id or "").strip() or None
            if normalized_session:
                thr = await queries.get_thread(self.db, tid, normalized_session)
            else:
                thr = await queries.get_thread_any(self.db, tid)
            if not thr:
                logger.warning(f"Thread {tid} introuvable.")
                return {
                    "status": "success",
                    "message": "Thread introuvable.",
                    "consolidated_sessions": 0,
                    "new_concepts": 0,
                }

            sid = thr.get("session_id") or normalized_session or tid
            if normalized_session and sid and normalized_session != sid:
                logger.warning(
                    f"Thread {tid} introuvable pour la session {normalized_session}."
                )
                return {
                    "status": "success",
                    "message": "Thread introuvable pour cette session.",
                    "consolidated_sessions": 0,
                    "new_concepts": 0,
                }

            uid = thr.get("user_id")
            if user_id and uid and uid != user_id:
                logger.warning(
                    f"Thread {tid} ignoré pour l'utilisateur {user_id} (propriétaire: {uid})."
                )
                return {
                    "status": "success",
                    "message": "Thread non autorisé pour cet utilisateur.",
                    "consolidated_sessions": 0,
                    "new_concepts": 0,
                }

            msgs = await queries.get_messages(
                self.db,
                tid,
                session_id=sid,
                user_id=uid,
                limit=1000,
            )
            history = []
            for m in msgs or []:
                history.append(
                    {
                        "role": m.get("role") or "user",
                        "content": m.get("content")
                        if isinstance(m.get("content"), str)
                        else json.dumps(m.get("content") or ""),
                        "agent_id": m.get("agent_id"),
                    }
                )

            history = self._filter_history_for_agent(history, normalized_agent)
            facts = self._extract_facts_from_history(history)

            # Analyse sémantique sans persistance en table sessions
            analysis = (
                await self.analyzer.analyze_history(session_id=sid, history=history)
                if history
                else {}
            )
            concepts = (
                self._parse_concepts(analysis.get("concepts")) if analysis else []
            )
            entities = (
                self._parse_entities(analysis.get("entities")) if analysis else []
            )
            all_concepts = _unique((concepts or []) + (entities or []))

            new_items_count = 0
            added_any = False

            if facts:
                facts_to_add = []
                for f in facts:
                    if not await self._fact_already_vectorized(
                        sid, f["key"], f.get("agent")
                    ):
                        facts_to_add.append(f)
                if facts_to_add:
                    session_stub: Dict[str, Any] = {"id": sid, "user_id": uid, "thread_id": tid, "themes": []}
                    await self._record_facts_in_sql(facts_to_add, session_stub, uid)
                    await self._vectorize_facts(facts_to_add, session_stub, uid)
                    new_items_count += len(facts_to_add)
                    added_any = True

            pref_added = await self._process_preference_pipeline(history, tid, uid)
            if pref_added:
                new_items_count += pref_added
                added_any = True

            if all_concepts and not await self._any_vectors_for_session_type(
                tid, "concept"
            ):
                concept_stub: Dict[str, Any] = {"id": tid, "user_id": uid, "themes": []}
                await self._record_concepts_in_sql(all_concepts, concept_stub, uid)
                await self._vectorize_concepts(all_concepts, concept_stub, uid)
                new_items_count += len(all_concepts)
                added_any = True

            await self._decay_knowledge()
            msg = (
                "Consolidation thread OK."
                if added_any
                else "Aucun nouvel item pour ce thread."
            )
            return {
                "status": "success",
                "message": msg,
                "consolidated_sessions": 1 if added_any else 0,
                "new_concepts": new_items_count,
            }

        except Exception as e:
            logger.error(f"Erreur consolidation thread {thread_id}: {e}", exc_info=True)
            return {
                "status": "error",
                "message": str(e),
                "consolidated_sessions": 0,
                "new_concepts": 0,
            }

    # ---------- Helpers SQL / parse / vectors (inchangés) ----------
    # … (le reste du fichier est inchangé par rapport à ta version V2.7.0) …

    # ---------- Helpers SQL ----------

    async def _fetch_session_by_id(self, session_id: str) -> Optional[Dict[str, Any]]:
        row = await self.db.fetch_one(
            """
            SELECT id, user_id, created_at, updated_at, session_data, summary, extracted_concepts, extracted_entities
            FROM sessions
            WHERE id = ?
            """,
            (session_id,),
        )
        return dict(row) if row else None

    async def _fetch_recent_sessions(self, limit: int, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        base_query = """
            SELECT id, user_id, created_at, updated_at, session_data, summary, extracted_concepts, extracted_entities
            FROM sessions
        """
        params: List[Any] = []
        if user_id:
            base_query += " WHERE user_id = ?"
            params.append(user_id)
        base_query += " ORDER BY updated_at DESC LIMIT ?"
        params.append(int(limit))
        rows = await self.db.fetch_all(base_query, tuple(params))
        return [dict(r) for r in (rows or [])]

    def _parse_concepts(self, raw: Any) -> List[str]:
        try:
            if raw is None:
                return []
            data = json.loads(raw) if isinstance(raw, str) else raw
            if isinstance(data, list):
                return [c for c in data if isinstance(c, str) and c.strip()]
            return []
        except Exception as e:
            logger.warning(f"JSON concepts invalide: {e}")
            return []

    def _parse_entities(self, raw: Any) -> List[str]:
        try:
            if raw is None:
                return []
            data = json.loads(raw) if isinstance(raw, str) else raw
            if isinstance(data, list):
                out = []
                for x in data:
                    if isinstance(x, str) and x.strip():
                        out.append(x.strip())
                return out
            return []
        except Exception as e:
            logger.warning(f"JSON entities invalide: {e}")
            return []

    async def _process_preference_pipeline(
        self, history: List[Dict[str, Any]], session_id: str, user_id: Optional[str]
    ) -> int:
        if not history:
            return 0
        candidates = self._collect_preference_candidates(history)
        if not candidates:
            return 0
        llm_results = await self._classify_preference_candidates(session_id, candidates)
        if not llm_results:
            return 0
        records = self._normalize_preference_records(
            llm_results, candidates, session_id, user_id
        )
        if not records:
            return 0
        return await self._store_preference_records(records, session_id, user_id)

    def _collect_preference_candidates(
        self, history: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        candidates: List[Dict[str, Any]] = []
        seen_keys = set()
        for msg in history or []:
            role = (msg.get("role") or "").lower()
            if role not in {"user", "client"}:
                continue
            raw_text = (
                msg.get("content") or msg.get("text") or msg.get("message") or ""
            ).strip()
            if not raw_text or len(raw_text) < 8:
                continue
            normalized_full = _normalize_for_scan(raw_text)
            matches_pattern = any(
                p.search(normalized_full) for p in _PREFERENCE_REGEX_PATTERNS
            )
            sentences = [
                s.strip() for s in re.split(r"(?<=[.!?])\s+", raw_text) if s.strip()
            ]
            if not sentences:
                sentences = [raw_text]
            for sent in sentences:
                if len(sent) < 6:
                    continue
                normalized_sentence = _normalize_for_scan(sent)
                if not normalized_sentence:
                    continue
                if (
                    not matches_pattern
                    and not any(
                        p.search(normalized_sentence)
                        for p in _PREFERENCE_REGEX_PATTERNS
                    )
                    and not _looks_imperative(sent)
                ):
                    continue
                key = normalized_sentence[:280]
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                candidates.append(
                    {
                        "id": uuid.uuid4().hex,
                        "text": sent,
                        "message_id": msg.get("id")
                        or msg.get("message_id")
                        or msg.get("uuid"),
                        "role": role,
                    }
                )
                if len(candidates) >= _MAX_PREFERENCE_CANDIDATES:
                    return candidates
        return candidates

    async def _classify_preference_candidates(
        self, session_id: str, candidates: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        chat_service = getattr(self.analyzer, "chat_service", None)
        if not chat_service:
            logger.debug(
                "[MemoryGardener] ChatService absent, impossible de classifier les préférences."
            )
            return []
        prompt_lines = [
            "Analyse les extraits suivants issus de messages utilisateur.",
            "Pour chacun, indique s'il s'agit d'une préférence, d'une intention, d'une contrainte ou de contenu neutre.",
            "Règles :",
            "- preference : goût, habitude, canal ou format que l'utilisateur apprécie ou rejette.",
            "- intent : action que l'utilisateur prévoit, décide ou demande explicitement.",
            "- constraint : interdiction, limite ou condition impérative.",
            "- neutral : tout ce qui ne rentre pas dans les trois catégories précédentes.",
            "Pour chaque extrait, fournis topic (sujet synthétique), action (verbe à l'infinitif si pertinent), timeframe (ISO 8601 si date explicite), sentiment (positive/negative/neutral) et confiance (0 à 1).",
            "Renvoie STRICTEMENT un JSON valide respectant le schéma fourni.",
            "Utilise EXACTEMENT les clés JSON suivantes sans traduction : items, id, type, topic, action, timeframe, sentiment, confidence, summary.",
            "N'ajoute aucun texte hors du JSON.",
            "---",
        ]
        limited = candidates[:_MAX_PREFERENCE_CANDIDATES]
        for cand in limited:
            prompt_lines.append(f"ID: {cand['id']}")
            prompt_lines.append("TEXTE:")
            prompt_lines.append(cand["text"])
            prompt_lines.append("---")
        prompt = "\n".join(prompt_lines)
        result: Dict[str, Any] = {}
        try:
            result = await chat_service.get_structured_llm_response(
                agent_id="anima",
                prompt=prompt,
                json_schema=_PREFERENCE_CLASSIFICATION_SCHEMA,
            )
        except Exception as exc:
            logger.warning(
                f"[MemoryGardener] Classification préférences (anima) échouée : {exc}",
                exc_info=True,
            )
        if not result:
            try:
                result = await chat_service.get_structured_llm_response(
                    agent_id="nexus",
                    prompt=prompt,
                    json_schema=_PREFERENCE_CLASSIFICATION_SCHEMA,
                )
            except Exception as exc:
                logger.error(
                    f"[MemoryGardener] Classification préférences fallback échouée : {exc}",
                    exc_info=True,
                )
                return []
        normalized_result = _normalize_classification_payload(result)
        items = (normalized_result or {}).get("items") or []
        filtered: List[Dict[str, Any]] = []
        for item in items:
            if isinstance(item, dict) and item.get("id"):
                filtered.append(item)
        return filtered

    def _normalize_preference_records(
        self,
        llm_results: List[Dict[str, Any]],
        candidates: List[Dict[str, Any]],
        session_id: str,
        user_id: Optional[str],
    ) -> List[Dict[str, Any]]:
        candidate_map = {c["id"]: c for c in candidates}
        records: List[Dict[str, Any]] = []
        user_identifier = (user_id or "").strip() or "anonymous"
        for item in llm_results:
            cid = str(item.get("id") or "").strip()
            if not cid or cid not in candidate_map:
                continue
            pref_type = str(item.get("type") or "").lower().strip()
            if pref_type not in {"preference", "intent", "constraint"}:
                continue
            raw_conf = item.get("confidence")
            confidence = 0.0
            if raw_conf is not None:
                try:
                    confidence = float(str(raw_conf))
                except (TypeError, ValueError):
                    confidence = 0.0
            confidence = max(0.0, min(1.0, confidence))
            candidate = candidate_map[cid]
            raw_topic = str(item.get("topic") or "").strip()
            topic_display = raw_topic or candidate["text"][:80]
            topic_key = (
                _normalize_for_scan(topic_display)[:120]
                or _normalize_for_scan(candidate["text"])[:120]
            )
            action = str(item.get("action") or "").strip()
            timeframe_raw = str(item.get("timeframe") or "").strip()
            timeframe = self._normalize_timeframe(timeframe_raw)
            sentiment = self._sanitize_sentiment(item.get("sentiment"))
            summary = str(item.get("summary") or "").strip()
            canonical_text = " | ".join(
                filter(
                    None,
                    [
                        pref_type,
                        topic_display,
                        action,
                        timeframe,
                        sentiment,
                        candidate["text"],
                    ],
                )
            )
            record_id = _preference_record_id(user_identifier, pref_type, topic_key)
            records.append(
                {
                    "id": record_id,
                    "type": pref_type,
                    "topic": topic_display,
                    "topic_normalized": topic_key,
                    "action": action,
                    "timeframe": timeframe,
                    "timeframe_raw": timeframe_raw,
                    "sentiment": sentiment,
                    "confidence": confidence,
                    "source_message_id": candidate.get("message_id"),
                    "source_text": candidate["text"],
                    "summary": summary,
                    "user_id": user_identifier,
                    "canonical_text": canonical_text,
                }
            )
        return records

    async def _store_preference_records(
        self, records: List[Dict[str, Any]], session_id: str, user_id: Optional[str]
    ) -> int:
        if not records:
            return 0
        inserted = 0
        vector_items: List[Dict[str, Any]] = []
        sql_payload: List[Dict[str, Any]] = []
        to_notify: List[Dict[str, Any]] = []
        for record in records:
            existing = await self._get_existing_preference_record(record["id"])
            existing_meta = (existing or {}).get("metadata") or {}
            prev_conf = float(existing_meta.get("confidence", 0.0) or 0.0)
            prev_occ = int(existing_meta.get("occurrences", 1) or 1)
            if prev_occ < 1:
                prev_occ = 1
            occurrences = prev_occ + 1 if existing else 1
            confidence_value = float(record.get("confidence", 0.0) or 0.0)
            if existing:
                confidence_value = (
                    (prev_conf * prev_occ) + confidence_value
                ) / occurrences
            record["confidence"] = round(confidence_value, 4)
            record["occurrences"] = occurrences
            if existing:
                if not record["topic"] and existing_meta.get("topic"):
                    record["topic"] = existing_meta.get("topic")
                if not record["action"] and existing_meta.get("action"):
                    record["action"] = existing_meta.get("action")
                if record["timeframe"] == "ongoing" and existing_meta.get("timeframe"):
                    record["timeframe"] = existing_meta.get("timeframe")
                if record["sentiment"] == "neutral" and existing_meta.get("sentiment"):
                    record["sentiment"] = existing_meta.get("sentiment")
            source_ids: List[str] = []
            prev_sources = existing_meta.get("source_message_ids") or existing_meta.get(
                "source_message_id"
            )
            if isinstance(prev_sources, list):
                source_ids.extend(str(s) for s in prev_sources if s)
            elif isinstance(prev_sources, str):
                source_ids.append(prev_sources)
            if record.get("source_message_id"):
                source_ids.append(str(record["source_message_id"]))
            record["source_message_ids"] = sorted({sid for sid in source_ids if sid})
            record["captured_at"] = _now_iso()
            embedding, embedding_model = await self._compute_preference_embedding(
                record["canonical_text"]
            )
            metadata = {
                "type": record["type"],
                "topic": record["topic"],
                "topic_normalized": record["topic_normalized"],
                "action": record["action"],
                "timeframe": record["timeframe"],
                "timeframe_raw": record.get("timeframe_raw"),
                "sentiment": record["sentiment"],
                "confidence": record["confidence"],
                "occurrences": record["occurrences"],
                "user_id": record["user_id"],
                "thread_id": session_id,
                "source_message_id": record.get("source_message_id"),
                "source_message_ids": record.get("source_message_ids"),
                "captured_at": record["captured_at"],
                "embedding_model": embedding_model
                or (
                    "text-embedding-3-large" if embedding else "vector_service_default"
                ),
                "summary": record.get("summary"),
            }
            item_payload = {
                "id": record["id"],
                "text": record["canonical_text"],
                "metadata": metadata,
            }
            if embedding:
                item_payload["embedding"] = list(embedding)
            vector_items.append(item_payload)
            sql_payload.append(
                {
                    "id": record["id"],
                    "type": record["type"],
                    "topic": record["topic"],
                    "confidence": record["confidence"],
                    "user_id": record["user_id"],
                    "thread_id": session_id,
                    "sentiment": record["sentiment"],
                    "timeframe": record["timeframe"],
                    "occurrences": record["occurrences"],
                    "source_message_id": record.get("source_message_id"),
                }
            )
            threshold_crossed = record[
                "confidence"
            ] >= _PREFERENCE_CONFIDENCE_EVENT_THRESHOLD and (
                not existing or prev_conf < _PREFERENCE_CONFIDENCE_EVENT_THRESHOLD
            )
            if threshold_crossed:
                to_notify.append(record)
            if not existing:
                inserted += 1
        if vector_items:
            try:
                await asyncio.to_thread(
                    self.vector_service.add_items,
                    self.preference_collection,
                    vector_items,
                )
                logger.info(f"{len(vector_items)} préférences/intentions vectorisées.")
            except Exception as exc:
                logger.error(
                    f"Vectorisation préférences impossible: {exc}", exc_info=True
                )
        if sql_payload:
            await self._record_preferences_in_sql(sql_payload, session_id, user_id)
        for record in to_notify:
            await self._emit_preference_banner(session_id, record)
        return inserted

    async def _get_existing_preference_record(
        self, record_id: str
    ) -> Optional[Dict[str, Any]]:
        try:
            result = await asyncio.to_thread(
                self.preference_collection.get, ids=[record_id]
            )
        except Exception:
            return None
        if not result:
            return None
        ids = result.get("ids") or []
        metadatas = result.get("metadatas") or []
        documents = result.get("documents") or []
        if ids and isinstance(ids[0], list):
            ids = ids[0]
        if metadatas and isinstance(metadatas[0], list):
            metadatas = metadatas[0]
        if documents and isinstance(documents[0], list):
            documents = documents[0]
        if ids:
            meta = metadatas[0] if metadatas else {}
            doc = documents[0] if documents else ""
            return {"id": ids[0], "metadata": meta, "document": doc}
        return None

    async def _compute_preference_embedding(
        self, text: str
    ) -> Tuple[Optional[List[float]], Optional[str]]:
        text = (text or "").strip()
        if not text:
            return None, None
        chat_service = getattr(self.analyzer, "chat_service", None)
        client = getattr(chat_service, "openai_client", None)
        if not client:
            return None, None
        for model_name in ("text-embedding-3-large", "text-embedding-004"):
            try:
                response = await client.embeddings.create(
                    model=model_name, input=[text]
                )
                data = getattr(response, "data", None) or []
                if data:
                    embedding = getattr(data[0], "embedding", None)
                    if embedding:
                        return list(embedding), model_name
            except Exception as exc:
                logger.debug(f"Embedding {model_name} échoué: {exc}", exc_info=True)
                continue
        return None, None

    async def _emit_preference_banner(
        self, session_id: str, record: Dict[str, Any]
    ) -> None:
        chat_service = getattr(self.analyzer, "chat_service", None)
        session_manager = (
            getattr(chat_service, "session_manager", None) if chat_service else None
        )
        connection_manager = (
            getattr(session_manager, "connection_manager", None)
            if session_manager
            else None
        )
        if not connection_manager:
            return
        payload = {
            "variant": "preference_captured",
            "topic": record.get("topic"),
            "type": record.get("type"),
            "confidence": record.get("confidence"),
            "timeframe": record.get("timeframe"),
            "sentiment": record.get("sentiment"),
            "source_message_id": record.get("source_message_id"),
        }
        try:
            await connection_manager.send_personal_message(
                {"type": "ws:memory_banner", "payload": payload}, session_id
            )
        except Exception:
            logger.debug(
                "[MemoryGardener] Impossible d'émettre ws:memory_banner preference_captured.",
                exc_info=True,
            )

    async def _record_preferences_in_sql(
        self, records: List[Dict[str, Any]], session_id: str, user_id: Optional[str]
    ) -> None:
        if not records:
            return
        now = _now_iso()
        for record in records:
            details = {
                "id": record.get("id"),
                "type": record.get("type"),
                "topic": record.get("topic"),
                "confidence": record.get("confidence"),
                "user_id": user_id,
                "thread_id": record.get("thread_id") or session_id,
                "sentiment": record.get("sentiment"),
                "timeframe": record.get("timeframe"),
                "occurrences": record.get("occurrences"),
                "source_message_id": record.get("source_message_id"),
            }
            try:
                await self.db.execute(
                    "INSERT INTO monitoring (event_type, event_details, timestamp) VALUES (?, ?, ?)",
                    ("memory_preference", json.dumps(details, ensure_ascii=False), now),
                    commit=True,
                )
            except Exception as exc:
                logger.warning(
                    f"Trace preference SQL échouée (session {session_id}): {exc}",
                    exc_info=True,
                )

    def _normalize_timeframe(self, value: Optional[str]) -> str:
        if not value:
            return "ongoing"
        candidate = str(value).strip()
        if not candidate:
            return "ongoing"
        try:
            normalized = candidate.replace("Z", "+00:00")
            parsed = datetime.fromisoformat(normalized)
            return parsed.isoformat()
        except Exception:
            pass
        match = re.search(r"(\d{4}-\d{2}-\d{2})", candidate)
        if match:
            return match.group(1)
        return "ongoing"

    def _sanitize_sentiment(self, value: Optional[str]) -> str:
        raw = str(value or "").strip().lower()
        if raw in {"positive", "positif", "positives"}:
            return "positive"
        if raw in {"negative", "negatif", "négatif", "neg"}:
            return "negative"
        if raw in {"neutral", "neutre"}:
            return "neutral"
        if raw in {"constraint", "constrained"}:
            return "neutral"
        return "neutral"

    # ---------- Helpers extraction ----------

    def _extract_history(self, session_data: Any) -> List[Dict[str, Any]]:
        try:
            if not session_data:
                return []
            parsed = (
                json.loads(session_data)
                if isinstance(session_data, str)
                else session_data
            )
            if isinstance(parsed, list):
                return parsed
            if isinstance(parsed, dict) and "history" in parsed:
                return parsed["history"]
        except Exception as e:
            logger.warning(f"Parsing session_data KO: {e}")
        return []

    def _extract_facts_from_history(
        self, history: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Cherche des motifs 'mot-code' dans l'history. Retourne des dicts avec text + metadata (type='fact')."""
        if not history:
            return []
        facts: List[Dict[str, Any]] = []
        for msg in history:
            # Robustesse: accepter 'text' | 'content' | 'message'
            text = (
                msg.get("text") or msg.get("content") or msg.get("message") or ""
            ).strip()
            agent_hint = _agent_norm(msg.get("agent_id") or msg.get("agent"))
            if not text:
                continue

            # recherche multi-patterns avec groupes nommés
            found = False
            for pat in _CODE_PATTERNS:
                m = re.search(pat, text, flags=re.IGNORECASE)
                if not m:
                    continue
                gd = m.groupdict() if m else {}
                agent = _agent_norm(gd.get("agent")) or agent_hint
                value = _clean_value(gd.get("value") or "")
                if value:
                    display_agent = agent or "global"
                    facts.append(
                        {
                            "key": "mot-code",
                            "agent": agent,
                            "value": value,
                            "text": f"Mot-code ({display_agent})={value}",
                        }
                    )
                    found = True
                    break  # éviter doublons sur le même message
            if found:
                continue

        # Unicité par (key, agent, value)
        seen = set()
        uniq: List[Dict[str, Any]] = []
        for f in facts:
            t = (f["key"], f.get("agent"), f["value"])
            if t not in seen:
                uniq.append(f)
                seen.add(t)
        return uniq

    # ---------- Helpers vecteurs ----------

    async def _any_vectors_for_session_type(
        self, session_id: str, type_name: str
    ) -> bool:
        """True s'il existe déjà AU MOINS 1 vecteur de ce type pour la session."""
        try:
            res = self.vector_service.query(
                self.knowledge_collection,
                query_text=session_id,
                n_results=1,
                where_filter={"source_session_id": session_id, "type": type_name},
            )
            return bool(res)
        except Exception:
            return False

    async def _fact_already_vectorized(
        self, session_id: str, key: str, agent: Optional[str]
    ) -> bool:
        try:
            where = {"source_session_id": session_id, "type": "fact", "key": key}
            if agent:
                where["agent"] = agent
            res = self.vector_service.query(
                self.knowledge_collection,
                query_text=key,
                n_results=1,
                where_filter=where,
            )
            return bool(res)
        except Exception:
            return False

    async def _record_concepts_in_sql(
        self, concepts: List[str], session: Dict[str, Any], user_id: Optional[str]
    ):
        now = _now_iso()
        for concept_text in concepts:
            concept_id = uuid.uuid4().hex
            details = {
                "id": concept_id,
                "concept": concept_text,
                "source_session_id": session["id"],
                "user_id": user_id,
                "categories": session.get("themes", []),
                "vector_id": concept_id,
                "kind": "concept",
            }
            try:
                await self.db.execute(
                    "INSERT INTO monitoring (event_type, event_details, timestamp) VALUES (?, ?, ?)",
                    ("knowledge_concept", json.dumps(details, ensure_ascii=False), now),
                    commit=True,
                )
            except Exception as e:
                logger.warning(
                    f"Trace concept SQL échouée (session {session['id']}): {e}",
                    exc_info=True,
                )

    async def _record_facts_in_sql(
        self,
        facts: List[Dict[str, Any]],
        session: Dict[str, Any],
        user_id: Optional[str],
    ):
        now = _now_iso()
        for fact in facts:
            rec = {
                "id": uuid.uuid4().hex,
                "key": fact["key"],
                "agent": fact.get("agent"),
                "value": fact["value"],
                "source_session_id": session["id"],
                "user_id": user_id,
                "vector_id": None,
                "kind": "fact",
                "text": fact["text"],
            }
            try:
                await self.db.execute(
                    "INSERT INTO monitoring (event_type, event_details, timestamp) VALUES (?, ?, ?)",
                    ("knowledge_fact", json.dumps(rec, ensure_ascii=False), now),
                    commit=True,
                )
            except Exception as e:
                logger.warning(
                    f"Trace fact SQL échouée (session {session['id']}): {e}",
                    exc_info=True,
                )

    async def _vectorize_concepts(
        self, concepts: List[str], session: Dict[str, Any], user_id: Optional[str]
    ):
        payload = []
        now_iso = _now_iso()

        # Récupérer thread_id et message_id depuis session stub
        thread_id = session.get("thread_id")
        message_id = session.get("message_id")

        for concept_text in concepts:
            vid = uuid.uuid4().hex
            payload.append(
                {
                    "id": vid,
                    "text": concept_text,
                    "metadata": {
                        "type": "concept",
                        "user_id": user_id,
                        "source_session_id": session["id"],
                        "concept_text": concept_text,
                        "created_at": now_iso,
                        "first_mentioned_at": now_iso,
                        "last_mentioned_at": now_iso,
                        "thread_id": thread_id or "",
                        "thread_ids_json": json.dumps([thread_id] if thread_id else []),
                        "message_id": message_id or "",
                        "mention_count": 1,
                        "last_access_at": now_iso,
                        "last_decay_at": now_iso,
                        "vitality": self.max_vitality,
                        "decay_runs": 0,
                        "usage_count": 0,
                    },
                }
            )
        if payload:
            try:
                await asyncio.to_thread(
                    self.vector_service.add_items, self.knowledge_collection, payload
                )
                logger.info(f"{len(payload)} concepts vectorisés avec métadonnées enrichies.")
            except Exception as exc:
                logger.error(
                    f"Vectorisation des concepts pour la session {session.get('id') if isinstance(session, dict) else session}: {exc}",
                    exc_info=True,
                )
                raise

    async def _vectorize_facts(
        self,
        facts: List[Dict[str, Any]],
        session: Dict[str, Any],
        user_id: Optional[str],
    ):
        payload = []
        now_iso = _now_iso()
        for f in facts:
            vid = _fact_id(
                session["id"], f["key"], f.get("agent"), f["value"]
            )  # ← ID déterministe (anti-doublon)
            payload.append(
                {
                    "id": vid,
                    "text": f["text"],
                    "metadata": {
                        "type": "fact",
                        "key": f["key"],
                        "agent": f.get("agent"),
                        "value": f["value"],
                        "user_id": user_id,
                        "source_session_id": session["id"],
                        "created_at": now_iso,
                        "last_access_at": now_iso,
                        "last_decay_at": now_iso,
                        "vitality": self.max_vitality,
                        "decay_runs": 0,
                        "usage_count": 0,
                    },
                }
            )
        if payload:
            try:
                await asyncio.to_thread(
                    self.vector_service.add_items, self.knowledge_collection, payload
                )
                logger.info(f"{len(payload)} faits vectorisés et plantés.")
            except Exception as exc:
                logger.error(
                    f"Vectorisation des faits pour la session {session.get('id') if isinstance(session, dict) else session}: {exc}",
                    exc_info=True,
                )
                raise

    async def _mark_sessions_as_consolidated(self, session_ids: List[str]):
        if not session_ids:
            return
        now = _now_iso()
        try:
            params = [(now, sid) for sid in session_ids]
            await self.db.executemany(
                "UPDATE sessions SET updated_at = ? WHERE id = ?", params, commit=True
            )
        except Exception as e:
            logger.warning(
                f"Impossible de marquer les sessions consolidées: {e}", exc_info=True
            )

    async def _decay_knowledge(self):
        now_dt = datetime.now(timezone.utc)
        now_iso = now_dt.isoformat()
        try:
            snapshot = self.knowledge_collection.get(include=["metadatas"])
        except Exception as e:
            logger.warning(f"[decay] collection read failed: {e}", exc_info=True)
            snapshot = {}

        raw_ids = snapshot.get("ids") if isinstance(snapshot, dict) else []
        raw_metas = snapshot.get("metadatas") if isinstance(snapshot, dict) else []

        ids: List[str] = []
        if isinstance(raw_ids, list):
            for chunk in raw_ids:
                if isinstance(chunk, list):
                    ids.extend([x for x in chunk if isinstance(x, str)])
                elif isinstance(chunk, str):
                    ids.append(chunk)

        metadatas: List[Dict[str, Any]] = []
        if isinstance(raw_metas, list):
            for chunk in raw_metas:
                if isinstance(chunk, list):
                    metadatas.extend([m if isinstance(m, dict) else {} for m in chunk])
                elif isinstance(chunk, dict):
                    metadatas.append(chunk)

        if not ids:
            try:
                await self.db.execute(
                    "INSERT INTO monitoring (event_type, event_details, timestamp) VALUES (?, ?, ?)",
                    (
                        "knowledge_decay",
                        json.dumps(
                            {"note": "decay skipped (no items)"}, ensure_ascii=False
                        ),
                        now_iso,
                    ),
                    commit=True,
                )
            except Exception as e:
                logger.warning(f"Trace vieillissement vide KO: {e}", exc_info=True)
            return

        updates_ids: List[str] = []
        updates_meta: List[Dict[str, Any]] = []
        delete_ids: List[str] = []
        vitality_values: List[float] = []
        new_vitality_values: List[float] = []
        age_days_values: List[float] = []
        unknown_age = 0

        bucket_counts = {"0-0.25": 0, "0.25-0.5": 0, "0.5-0.75": 0, "0.75-1.0": 0}

        def _bucketize(value: float) -> str:
            if value < 0.25:
                return "0-0.25"
            if value < 0.5:
                return "0.25-0.5"
            if value < 0.75:
                return "0.5-0.75"
            return "0.75-1.0"

        for idx, vec_id in enumerate(ids):
            meta = metadatas[idx] if idx < len(metadatas) else {}
            if not isinstance(meta, dict):
                meta = {}

            vitality_raw = meta.get("vitality", self.max_vitality)
            try:
                vitality = float(vitality_raw)
            except (TypeError, ValueError):
                vitality = self.max_vitality
            vitality = max(0.0, min(self.max_vitality, vitality))
            vitality_values.append(vitality)
            bucket_counts[_bucketize(vitality)] += 1

            last_touch = _parse_iso_ts(
                meta.get("last_access_at") or meta.get("created_at")
            )
            extra_decay = 0.0
            age_days = None
            if last_touch is not None:
                age_days = (now_dt - last_touch).total_seconds() / 86400.0
                if age_days >= 0:
                    age_days_values.append(age_days)
                    if age_days > self.stale_threshold_days:
                        extra_decay += self.stale_decay
                    if age_days > self.archive_threshold_days:
                        extra_decay += self.archive_decay
                else:
                    unknown_age += 1
            else:
                unknown_age += 1

            decay_amount = min(1.0, self.base_decay + extra_decay)
            new_vitality = max(0.0, vitality - decay_amount)

            if new_vitality <= self.min_vitality:
                delete_ids.append(vec_id)
                continue

            updated_meta = dict(meta)
            updated_meta["vitality"] = round(min(self.max_vitality, new_vitality), 4)
            updated_meta["last_decay_at"] = now_iso
            updated_meta["decay_runs"] = int(meta.get("decay_runs") or 0) + 1
            updates_ids.append(vec_id)
            updates_meta.append(updated_meta)
            new_vitality_values.append(new_vitality)

        if updates_ids:
            try:
                self.vector_service.update_metadatas(
                    self.knowledge_collection, updates_ids, updates_meta
                )
            except Exception as e:
                logger.warning(f"[decay] update vitality failed: {e}", exc_info=True)

        if delete_ids:
            try:
                self.knowledge_collection.delete(ids=delete_ids)
            except Exception as e:
                logger.warning(
                    f"[decay] delete expired items failed: {e}", exc_info=True
                )

        stats_payload = {
            "note": "decay applied",
            "processed": len(ids),
            "decayed": len(updates_ids),
            "deleted": len(delete_ids),
            "retained_ratio": round(len(updates_ids) / len(ids), 4) if ids else 0.0,
            "deleted_ratio": round(len(delete_ids) / len(ids), 4) if ids else 0.0,
            "base_decay": self.base_decay,
            "stale_threshold_days": self.stale_threshold_days,
            "stale_decay": self.stale_decay,
            "archive_threshold_days": self.archive_threshold_days,
            "archive_decay": self.archive_decay,
            "min_vitality": self.min_vitality,
            "max_vitality": self.max_vitality,
            "bucket_counts": bucket_counts,
            "unknown_age": unknown_age,
        }

        if vitality_values:
            stats_payload["vitality_before"] = {
                "count": len(vitality_values),
                "avg": round(mean(vitality_values), 4),
                "median": round(median(vitality_values), 4),
                "p90": round(_percentile(vitality_values, 0.9), 4),
                "p99": round(_percentile(vitality_values, 0.99), 4),
                "min": round(min(vitality_values), 4),
                "max": round(max(vitality_values), 4),
            }
        if new_vitality_values:
            stats_payload["vitality_after"] = {
                "count": len(new_vitality_values),
                "avg": round(mean(new_vitality_values), 4),
                "median": round(median(new_vitality_values), 4),
                "p90": round(_percentile(new_vitality_values, 0.9), 4),
                "p99": round(_percentile(new_vitality_values, 0.99), 4),
                "min": round(min(new_vitality_values), 4),
                "max": round(max(new_vitality_values), 4),
            }
        if age_days_values:
            recent = sum(
                1 for value in age_days_values if value <= self.stale_threshold_days
            )
            stats_payload["age_days"] = {
                "count": len(age_days_values),
                "avg": round(mean(age_days_values), 3),
                "median": round(median(age_days_values), 3),
                "p90": round(_percentile(age_days_values, 0.9), 3),
                "max": round(max(age_days_values), 3),
                "recent_ratio": round(recent / len(age_days_values), 4),
            }

        try:
            await self.db.execute(
                "INSERT INTO monitoring (event_type, event_details, timestamp) VALUES (?, ?, ?)",
                (
                    "knowledge_decay",
                    json.dumps(stats_payload, ensure_ascii=False),
                    now_iso,
                ),
                commit=True,
            )
            logger.info(
                f"Vieillissement applique: total={len(ids)} | decayed={len(updates_ids)} | deleted={len(delete_ids)} | base={self.base_decay:.3f}"
            )
        except Exception as e:
            logger.warning(f"[decay] monitoring insert failed: {e}", exc_info=True)
