# V1.1 — Outils mémoire/RAG (STM/LTM) + cache in-memory préférences (P2.1)
from __future__ import annotations
import os
import re
import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from backend.shared.models import Role

logger = logging.getLogger(__name__)

# Prometheus metrics (P2.1)
try:
    from prometheus_client import Counter
    PROMETHEUS_AVAILABLE = True

    memory_cache_operations = Counter(
        "memory_cache_operations_total",
        "Memory cache operations (hit/miss)",
        ["operation", "type"]
    )
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.debug("[MemoryContextBuilder] Prometheus client non disponible")


class MemoryContextBuilder:
    def __init__(self, session_manager, vector_service):
        self.session_manager = session_manager
        self.vector_service = vector_service

        # Cache in-memory préférences (P2.1)
        self._prefs_cache: Dict[str, Tuple[str, datetime]] = {}
        self._cache_ttl = timedelta(minutes=5)  # TTL 5 min
        logger.info("[MemoryContextBuilder] Initialized with in-memory preference cache (TTL=5min)")

    def try_get_session_summary(self, session_id: str) -> str:
        try:
            sess = self.session_manager.get_session(session_id)
            meta = getattr(sess, "metadata", None)
            if isinstance(meta, dict):
                s = meta.get("summary")
                if isinstance(s, str) and s.strip():
                    return s.strip()
        except Exception:
            pass
        return ""

    def try_get_user_id(self, session_id: str) -> Optional[str]:
        for attr in (
            "get_user_id_for_session",
            "get_user",
            "get_owner",
            "get_session_owner",
        ):
            try:
                fn = getattr(self.session_manager, attr, None)
                if callable(fn):
                    uid = fn(session_id)
                    if uid:
                        return str(uid)
            except Exception:
                pass
        for attr in ("current_user_id", "user_id"):
            try:
                uid = getattr(self.session_manager, attr, None)
                if uid:
                    return str(uid)
            except Exception:
                pass
        return None

    async def build_memory_context(
        self, session_id: str, last_user_message: str, top_k: int = 5
    ) -> str:
        try:
            if not last_user_message:
                return ""
            knowledge_name = os.getenv(
                "EMERGENCE_KNOWLEDGE_COLLECTION", "emergence_knowledge"
            )
            knowledge_col = self.vector_service.get_or_create_collection(knowledge_name)
            uid = self.try_get_user_id(session_id)

            # Build memory context with 3 components:
            # 1. Active preferences (high confidence, always injected)
            # 2. Vector search results (concepts/facts related to query)
            # 3. Temporal weighting (boost recent items)

            sections = []

            # 1. Fetch and inject active preferences (with cache P2.1)
            if uid:
                prefs = self._fetch_active_preferences_cached(knowledge_col, uid)
                if prefs:
                    sections.append(("Préférences actives", prefs))

            # 2. Vector search for concepts/facts
            where_filter = {"user_id": uid} if uid else None
            results = self.vector_service.query(
                collection=knowledge_col,
                query_text=last_user_message,
                n_results=top_k,
                where_filter=where_filter,
            )

            if results:
                # 3. Apply temporal weighting (boost recent items)
                weighted_results = self._apply_temporal_weighting(results)

                lines = []
                for r in weighted_results[:top_k]:
                    t = (r.get("text") or "").strip()
                    if t:
                        # Enrichir avec métadonnées temporelles si disponibles
                        temporal_hint = self._format_temporal_hint(r.get("metadata", {}))
                        lines.append(f"- {t}{temporal_hint}")

                if lines:
                    sections.append(("Connaissances pertinentes", "\n".join(lines)))

            # Merge all sections
            if not sections:
                return ""

            return self.merge_blocks(sections)

        except Exception as e:
            logger.warning(f"build_memory_context: {e}")
            return ""

    def _fetch_active_preferences_cached(self, collection, user_id: str) -> str:
        """
        Fetch active preferences with in-memory cache (TTL=5min).

        Phase P2.1 optimization:
        - Cache hit: ~2ms (80% des cas après warmup)
        - Cache miss: ~35ms (query ChromaDB)
        - Expected hit rate: >80% (5min TTL couvre ~8-10 messages)
        """
        now = datetime.now()

        # Check cache
        if user_id in self._prefs_cache:
            prefs, cached_at = self._prefs_cache[user_id]
            if now - cached_at < self._cache_ttl:
                logger.debug(f"[Cache HIT] Preferences for user {user_id[:8]}... (age={int((now - cached_at).total_seconds())}s)")
                if PROMETHEUS_AVAILABLE:
                    memory_cache_operations.labels(operation="hit", type="preferences").inc()
                return prefs

        # Cache miss → fetch ChromaDB
        logger.debug(f"[Cache MISS] Fetching preferences for user {user_id[:8]}...")
        if PROMETHEUS_AVAILABLE:
            memory_cache_operations.labels(operation="miss", type="preferences").inc()

        prefs = self._fetch_active_preferences(collection, user_id)

        # Update cache
        self._prefs_cache[user_id] = (prefs, now)

        # Cleanup old entries (garbage collection)
        self._cleanup_expired_cache()

        return prefs

    def _fetch_active_preferences(self, collection, user_id: str) -> str:
        """Fetch active preferences with high confidence (>0.6) for immediate injection."""
        try:
            where = {
                "$and": [
                    {"user_id": user_id},
                    {"type": "preference"},
                    {"confidence": {"$gte": 0.6}},
                ]
            }
            got = collection.get(where=where, include=["documents", "metadatas"])
            docs = got.get("documents", []) or []

            if not docs:
                return ""

            prefs = []
            for doc in docs[:5]:  # Limit to top 5 preferences
                if doc and doc.strip():
                    # Extract preference text (format: "topic: preference")
                    prefs.append(f"- {doc.strip()}")

            return "\n".join(prefs) if prefs else ""

        except Exception as e:
            logger.debug(f"_fetch_active_preferences: {e}")
            return ""

    def _cleanup_expired_cache(self) -> None:
        """Remove expired entries from cache (garbage collection)."""
        now = datetime.now()
        expired_keys = [
            key for key, (_, cached_at) in self._prefs_cache.items()
            if now - cached_at >= self._cache_ttl
        ]

        for key in expired_keys:
            del self._prefs_cache[key]

        if expired_keys:
            logger.debug(f"[Cache GC] Removed {len(expired_keys)} expired entries")

    def invalidate_preferences_cache(self, user_id: str) -> None:
        """Invalide le cache préférences pour un utilisateur donné.

        Appelée après mise à jour des préférences (analyse mémoire ou jardinage)
        pour forcer le rechargement depuis ChromaDB au prochain accès.

        Args:
            user_id: Identifiant de l'utilisateur
        """
        if user_id in self._prefs_cache:
            del self._prefs_cache[user_id]
            logger.info(f"[MemoryContext] Cache préférences invalidé pour user {user_id[:8]}...")

    def _apply_temporal_weighting(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply temporal weighting to boost recent and frequently used items."""
        import datetime

        now = datetime.datetime.now(datetime.timezone.utc)
        weighted = []

        for r in results:
            meta = r.get("metadata", {}) or {}
            created_at = meta.get("created_at")
            usage_count = meta.get("usage_count", 0)

            # Calculate freshness boost (1.0 to 1.3 based on age)
            freshness_boost = 1.0
            if created_at:
                try:
                    created_dt = datetime.datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                    age_days = (now - created_dt).days
                    if age_days < 7:
                        freshness_boost = 1.3  # Recent items (< 7 days)
                    elif age_days < 30:
                        freshness_boost = 1.15  # Medium recent (< 30 days)
                except Exception:
                    pass

            # Calculate usage boost (1.0 to 1.2 based on usage count)
            usage_boost = 1.0 + min(0.2, usage_count * 0.02)

            # Apply combined boost to score
            original_score = r.get("score", 1.0)
            boosted_score = original_score * freshness_boost * usage_boost

            r["boosted_score"] = boosted_score
            weighted.append(r)

        # Sort by boosted score (descending)
        weighted.sort(key=lambda x: x.get("boosted_score", 0), reverse=True)

        return weighted

    def normalize_history_for_llm(
        self,
        provider: str,
        history: List[Dict[str, Any]],
        *,
        rag_context: str = "",
        use_rag: bool = False,
        agent_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        normalized: List[Dict[str, Any]] = []
        if use_rag and rag_context:
            if provider == "google":
                normalized.append(
                    {"role": "user", "parts": [f"[RAG_CONTEXT]\n{rag_context}"]}
                )
            else:
                normalized.append(
                    {"role": "user", "content": f"[RAG_CONTEXT]\n{rag_context}"}
                )
        for m in history:
            role = m.get("role")
            text = m.get("content") or m.get("message") or ""
            if not text:
                continue
            if provider == "google":
                normalized.append(
                    {
                        "role": "user" if role in (Role.USER, "user") else "model",
                        "parts": [text],
                    }
                )
            else:
                normalized.append(
                    {
                        "role": "user" if role in (Role.USER, "user") else "assistant",
                        "content": text,
                    }
                )
        return normalized

    def merge_blocks(self, blocks: List[Tuple[str, str]]) -> str:
        parts = []
        for title, body in blocks:
            if body and str(body).strip():
                parts.append(f"### {title}\n{str(body).strip()}")
        return "\n\n".join(parts)

    _MOT_CODE_RE = re.compile(r"\b(mot-?code|code)\b", re.IGNORECASE)

    def is_mot_code_query(self, text: str) -> bool:
        return bool(self._MOT_CODE_RE.search(text or ""))

    def fetch_mot_code_for_agent(
        self, agent_id: str, user_id: Optional[str]
    ) -> Optional[str]:
        knowledge_name = os.getenv(
            "EMERGENCE_KNOWLEDGE_COLLECTION", "emergence_knowledge"
        )
        col = self.vector_service.get_or_create_collection(knowledge_name)
        clauses = [
            {"type": "fact"},
            {"key": "mot-code"},
            {"agent": (agent_id or "").lower()},
        ]
        if user_id:
            clauses.append({"user_id": user_id})
        where = {"$and": clauses}
        got = col.get(where=where, include=["documents", "metadatas"])
        ids = got.get("ids", []) or []
        if not ids:
            got = col.get(
                where={
                    "$and": [
                        {"type": "fact"},
                        {"key": "mot-code"},
                        {"agent": (agent_id or "").lower()},
                    ]
                },
                include=["documents", "metadatas"],
            )
            ids = got.get("ids", []) or []
            if not ids:
                return None
        docs = got.get("documents", []) or []
        if not docs:
            return None
        line = docs[0] or ""
        if ":" in line:
            try:
                return line.split(":", 1)[1].strip()
            except Exception:
                pass
        metas = got.get("metadatas", []) or []
        if metas and isinstance(metas[0], dict) and metas[0].get("value"):
            return str(metas[0]["value"]).strip()
        return None

    def count_bullets(self, text: str) -> int:
        return sum(
            1 for line in (text or "").splitlines() if line.strip().startswith("- ")
        )

    def extract_sensitive_tokens(self, text: str) -> List[str]:
        return re.findall(r"\b[A-Z]{3,}-\d{3,}\b", text or "")

    def _format_temporal_hint(self, metadata: Dict[str, Any]) -> str:
        """
        Format temporal metadata for RAG context enrichment.

        Returns hints like:
        - " (1ère mention: 5 oct, 3 fois)"
        - " (abordé le 8 oct à 14h32)"
        - "" (empty if no temporal data)
        """
        if not isinstance(metadata, dict):
            return ""

        first_mentioned = metadata.get("first_mentioned_at") or metadata.get("created_at")
        mention_count = metadata.get("mention_count", 1)

        if not first_mentioned:
            return ""

        try:
            # Parse ISO 8601 timestamp
            from datetime import datetime
            dt = datetime.fromisoformat(first_mentioned.replace("Z", "+00:00"))

            # Format français naturel : "5 oct" ou "5 oct à 14h32"
            day = dt.day
            months = ["", "janv", "fév", "mars", "avr", "mai", "juin",
                      "juil", "août", "sept", "oct", "nov", "déc"]
            month = months[dt.month] if 1 <= dt.month <= 12 else str(dt.month)

            date_str = f"{day} {month}"

            # Ajouter heure si pertinent (pas minuit pile)
            if dt.hour != 0 or dt.minute != 0:
                date_str += f" à {dt.hour}h{dt.minute:02d}"

            # Construire hint
            if isinstance(mention_count, int) and mention_count > 1:
                return f" (1ère mention: {date_str}, {mention_count} fois)"
            else:
                return f" (abordé le {date_str})"

        except Exception as e:
            logger.debug(f"[_format_temporal_hint] Parse error: {e}")
            return ""
