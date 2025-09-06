# src/backend/features/memory/gardener.py
# V2.10.2 — fix awaitable: _tend_single_thread ne 'await' plus un dict (inspect.isawaitable)
from __future__ import annotations

import logging
import json
import re
import hashlib
import inspect
from typing import Dict, Any, List, Optional, Iterable

from backend.core.database.manager import DatabaseManager
from backend.features.memory.vector_service import VectorService
from backend.features.memory.analyzer import MemoryAnalyzer

logger = logging.getLogger(__name__)

# ---------------- Utilitaires légers ----------------
_VALUE_TRAIL_RE = re.compile(r"[\s\.\,\;\:\!\?]+$")
def _clean_value(v: str) -> str:
    v = (v or "").strip()
    v = _VALUE_TRAIL_RE.sub("", v)
    v = re.sub(r"\s{2,}", " ", v)
    return v

def _unique(seq: Iterable[str]) -> List[str]:
    seen, out = set(), []
    for s in seq or []:
        k = (s or "").strip().lower()
        if k and k not in seen:
            out.append((s or "").strip())
            seen.add(k)
    return out

def _hash_key(*parts: str) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update((p or "").encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()[:16]

def _row_get(row: Any, key: str, default: Any = None) -> Any:
    if row is None:
        return default
    if isinstance(row, dict):
        return row.get(key, default)
    try:
        return getattr(row, key, default)
    except Exception:
        return default

def _is_str_json(s: Any) -> bool:
    return isinstance(s, str) and s.strip().startswith(("{", "["))

# ---------------- MemoryGardener ----------------
class MemoryGardener:
    """
    Consolidation STM → LTM (concepts / entités / faits). Vectorisation Chroma.
    Compat signatures: MemoryGardener(db, vec, analyzer) OU kwargs (db_manager, vector_service, memory_analyzer|analyzer).
    """
    KNOWLEDGE = "emergence_knowledge"

    def __init__(self, *args, **kwargs):
        # Compat kwargs
        db_kw   = kwargs.get("db_manager")
        vec_kw  = kwargs.get("vector_service")
        ana_kw  = kwargs.get("memory_analyzer") or kwargs.get("analyzer")

        # Compat positionnel
        db_pos  = args[0] if len(args) > 0 else None
        vec_pos = args[1] if len(args) > 1 else None
        ana_pos = args[2] if len(args) > 2 else None

        self.db: DatabaseManager = db_kw or db_pos
        self.vector_service: VectorService = vec_kw or vec_pos
        self.analyzer: Optional[MemoryAnalyzer] = ana_kw or ana_pos

        if self.db is None or self.vector_service is None:
            raise ValueError("MemoryGardener: db_manager et vector_service requis.")

        self.knowledge_collection = self.vector_service.get_or_create_collection(self.KNOWLEDGE)
        logger.info("MemoryGardener V2.10.2 initialisé.")

    # --------- API publique ---------
    async def tend_the_garden(self, consolidation_limit: int = 10, thread_id: Optional[str] = None) -> Dict[str, Any]:
        if thread_id:
            return await self._tend_single_thread(thread_id)

        logger.info("Le jardinier commence sa ronde dans le jardin de la mémoire (mode sessions)…")
        sessions = await self._fetch_recent_sessions(limit=consolidation_limit)
        if not sessions:
            logger.info("Aucune session récente à traiter. Le jardin est en ordre.")
            await self._decay_knowledge()
            return {"status": "success", "message": "Aucune session à traiter.", "consolidated_sessions": 0, "new_concepts": 0}

        processed_ids: List[str] = []
        new_items_count = 0

        for s in sessions:
            sid: str = s.get("id")
            uid: Optional[str] = s.get("user_id")
            try:
                history = self._extract_history(s.get("session_data"))
                concepts = self._parse_concepts(s.get("extracted_concepts"))
                entities = self._parse_entities(s.get("extracted_entities"))
                all_concepts = _unique((concepts or []) + (entities or []))

                # Relance d’analyse si nécessaire
                if not all_concepts and history and self.analyzer:
                    await self.analyzer.analyze_session_for_concepts(session_id=sid, history=history)
                    row = await self.db.fetch_one(
                        "SELECT extracted_concepts, extracted_entities FROM sessions WHERE id = ?", (sid,)
                    )
                    conc = self._parse_concepts(_row_get(row, "extracted_concepts"))
                    ent  = self._parse_entities(_row_get(row, "extracted_entities"))
                    all_concepts = _unique((conc or []) + (ent or []))

                # Vectorisation concepts
                if all_concepts and not await self._any_vectors_for_session_type(sid, "concept"):
                    new_items_count += await self._vectorize_concepts(uid, sid, all_concepts)

            except Exception as e:
                logger.warning(f"Échec consolidation session {sid}: {e}", exc_info=True)
            finally:
                processed_ids.append(sid)

        await self._decay_knowledge()
        return {
            "status": "success",
            "message": "La ronde du jardinier est terminée.",
            "consolidated_sessions": len(processed_ids),
            "new_concepts": new_items_count,
        }

    async def _tend_single_thread(self, tid: str) -> Dict[str, Any]:
        rows = await self.db.fetch_all(
            "SELECT role, content, agent_id FROM messages WHERE thread_id = ? ORDER BY created_at ASC",
            (tid,)
        )
        history: List[Dict[str, Any]] = []
        for m in rows or []:
            role = _row_get(m, "role", "user")
            raw  = _row_get(m, "content")
            text = raw if isinstance(raw, str) else json.dumps(raw or "", ensure_ascii=False)
            history.append({"role": role, "content": text})

        # ⛑️ fix awaitable: ne pas 'await' un dict retourné par _fallback_analysis
        res = self.analyzer.analyze_history(tid, history) if (self.analyzer and history) else self._fallback_analysis(history)
        analysis = await res if inspect.isawaitable(res) else res

        all_concepts = _unique((analysis.get("concepts") or []) + (analysis.get("entities") or []))
        created = 0
        if all_concepts and not await self._any_vectors_for_session_type(tid, "concept"):
            created += await self._vectorize_concepts(None, tid, all_concepts)
        return {"status": "success", "message": "Thread consolidé", "thread_id": tid, "new_items": created}

    # --------- Helpers principaux ---------
    async def _fetch_recent_sessions(self, limit: int = 20) -> List[Dict[str, Any]]:
        rows = await self.db.fetch_all(
            """
            SELECT id, user_id, session_data, extracted_concepts, extracted_entities
            FROM sessions
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (limit,)
        )
        out: List[Dict[str, Any]] = []
        for r in rows or []:
            out.append({
                "id": _row_get(r, "id"),
                "user_id": _row_get(r, "user_id"),
                "session_data": _row_get(r, "session_data"),
                "extracted_concepts": _row_get(r, "extracted_concepts"),
                "extracted_entities": _row_get(r, "extracted_entities"),
            })
        return out

    def _extract_history(self, session_data: Any) -> List[Dict[str, Any]]:
        try:
            obj = json.loads(session_data) if _is_str_json(session_data) else (session_data or {})
            return obj.get("history") or []
        except Exception:
            return []

    def _parse_concepts(self, dumped: Any) -> List[str]:
        try:
            if isinstance(dumped, str):
                d = json.loads(dumped)
                if isinstance(d, dict): return d.get("concepts") or []
                if isinstance(d, list): return d
            if isinstance(dumped, dict): return dumped.get("concepts") or []
            if isinstance(dumped, list): return dumped
        except Exception:
            pass
        return []

    def _parse_entities(self, dumped: Any) -> List[str]:
        try:
            if isinstance(dumped, str):
                d = json.loads(dumped)
                if isinstance(d, dict): return d.get("entities") or []
                if isinstance(d, list): return d
            if isinstance(dumped, dict): return dumped.get("entities") or []
            if isinstance(dumped, list): return dumped
        except Exception:
            pass
        return []

    def _fallback_analysis(self, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        text = " ".join(_row.get("content","") for _row in (history or []))
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            return {"summary": "", "concepts": [], "entities": []}
        # 3–12 mots, 5 items max
        chunks = [c.strip() for c in re.split(r"[.;:\n]+", text) if c.strip()]
        concepts = []
        for c in chunks:
            wc = len(c.split())
            if 3 <= wc <= 12:
                concepts.append(c)
            if len(concepts) >= 5: break
        return {"summary": text[:480], "concepts": _unique(concepts), "entities": []}

    async def _any_vectors_for_session_type(self, session_id: str, type_: str) -> bool:
        where = {"$and": [
            {"session_id": {"$eq": session_id}},
            {"type": {"$eq": type_}},
        ]}
        got = self.knowledge_collection.get(where=where, limit=1)
        ids = got.get("ids") or []
        if ids and isinstance(ids, list) and len(ids) > 0 and isinstance(ids[0], list):
            ids = [x for sub in ids for x in (sub or [])]
        return bool(ids)

    async def _vectorize_concepts(self, user_id: Optional[str], session_id: str, items: List[str]) -> int:
        if not items:
            return 0
        ids = [f"c:{_hash_key(session_id, it)}" for it in items]
        metadatas = [{"session_id": session_id, "type": "concept", "user_id": user_id} for _ in items]
        embeddings = self.vector_service.embed_texts(items)
        self.knowledge_collection.add(ids=ids, metadatas=metadatas, embeddings=embeddings, documents=items)
        return len(items)

    async def _decay_knowledge(self) -> None:
        logger.info("Vieillissement journalisé (monitoring.knowledge_decay).")
