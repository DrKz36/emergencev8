# src/backend/features/memory/gardener.py
# V2.9.3 — Fix Pylance: import sqlite3 ; robustesse Row/dict ; aucune logique supprimée

import logging
import uuid
import json
import re
import hashlib
import sqlite3
from typing import Dict, Any, List, Optional, Iterable, Union
from datetime import datetime, timezone

from backend.core.database.manager import DatabaseManager
from backend.features.memory.vector_service import VectorService
from backend.features.memory.analyzer import MemoryAnalyzer

logger = logging.getLogger(__name__)

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

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

def _sha1(s: str) -> str:
    return hashlib.sha1((s or "").encode("utf-8")).hexdigest()

def _agent_norm(name: Optional[str]) -> Optional[str]:
    if not name:
        return None
    n = name.strip().lower()
    return n if n in {"anima", "neo", "nexus"} else None

def _row_get(row: Union[dict, sqlite3.Row], key: str, default=None):
    """Tolérance dict/sqlite3.Row (pas de .get() natif sur Row)."""
    try:
        if row is None:
            return default
        return row[key]  # sqlite3.Row indexation par clé
    except Exception:
        try:
            return (row or {}).get(key, default)  # dict-like
        except Exception:
            return default

# Expressions pour les “mot-code”
_CODE_PATTERNS = [
    r"(?:pour\s+(?P<agent>anima|neo|nexus)\s*,?\s*)?(?:mon|ton|ce|le)\s*mot[-\s]?code\s*(?:est|:|=)\s*[«\"'’]?\s*(?P<value>[A-Za-zÀ-ÖØ-öø-ÿ0-9_\- ]+?)\s*[»\"'’]?(?:[.!?,;:\)]|$)",
    r"(?:mon|ton|ce|le)\s*mot[-\s]?code\s*pour\s+(?P<agent>anima|neo|nexus)\s*(?:est|:|=)\s*[«\"'’]?\s*(?P<value>[A-Za-zÀ-ÖØ-öø-ÿ0-9_\- ]+?)\s*[»\"'’]?(?:[.!?,;:\)]|$)",
    r"(?:pour\s+(?P<agent>anima|neo|nexus)\s*,?\s*)?mon\s*mot[-\s]?code\s*(?:est|:)\s*[«\"'’]?\s*(?P<value>[A-Za-zÀ-ÖØ-öø-ÿ0-9_\-]+)\s*[»\"'’]?",
    r"mon\s*mot[-\s]?code\s*pour\s+(?P<agent>anima|neo|nexus)\s*(?:est|:)\s*[«\"'’]?\s*(?P<value>[A-Za-zÀ-ÖØ-öø-ÿ0-9_\-]+)\s*[»\"'’]?",
    r"mot[-\s]?code\s*(?:est|:|=)\s*[«\"'’]?\s*(?P<value>[A-Za-zÀ-ÖØ-öø-ÿ0-9_\- ]+?)\s*[»\"'’]?(?:[.!?,;:\)]|$)"
]

def _concepts_from_summary(summary: str, max_items: int = 5) -> List[str]:
    """Fallback simple : 3–5 segments courts (3–12 mots), nettoyés et dédupliqués."""
    if not isinstance(summary, str) or not summary.strip():
        return []
    text = re.sub(r"\s+", " ", summary.strip())
    chunks = re.split(r"[.;:\n]+", text)
    out: List[str] = []
    for c in chunks:
        w = c.strip()
        if not w:
            continue
        wc = len(w.split())
        if 3 <= wc <= 12:
            out.append(w)
        if len(out) >= max_items:
            break
    return _unique(out)

class MemoryGardener:
    """
    MEMORY GARDENER V2.9.3
    - Fix sqlite3.Row (accès r["col"]), tolérance dict
    - Consolidation sessions + thread ciblé
    - Fallback “concepts depuis le résumé” si extraction vide
    - Vectorisation Chroma robuste (documents + metadatas + ids)
    """
    KNOWLEDGE_COLLECTION_NAME = "emergence_knowledge"

    def __init__(self, db_manager: DatabaseManager, vector_service: VectorService, memory_analyzer: MemoryAnalyzer):
        self.db = db_manager
        self.vector_service = vector_service
        self.analyzer = memory_analyzer
        self.knowledge_collection = self.vector_service.get_or_create_collection(self.KNOWLEDGE_COLLECTION_NAME)
        logger.info("MemoryGardener V2.9.3 initialisé.")

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
            sid: str = s["id"]; uid: Optional[str] = s.get("user_id")
            try:
                history = self._extract_history(s.get("session_data"))
                concepts = self._parse_concepts(s.get("extracted_concepts"))
                entities = self._parse_entities(s.get("extracted_entities"))
                all_concepts = _unique((concepts or []) + (entities or []))
                facts = self._extract_facts_from_history(history)

                # (A) Relance analyse si pas de concepts mais de l'historique
                if not all_concepts and history:
                    await self.analyzer.analyze_session_for_concepts(session_id=sid, history=history)
                    row = await self.db.fetch_one(
                        "SELECT summary, extracted_concepts, extracted_entities FROM sessions WHERE id = ?",
                        (sid,)
                    )
                    summary = _row_get(row, "summary", "")
                    concepts = self._parse_concepts(_row_get(row, "extracted_concepts"))
                    entities = self._parse_entities(_row_get(row, "extracted_entities"))
                    all_concepts = _unique((concepts or []) + (entities or []))
                    # (B) Fallback si toujours vide et résumé dispo
                    if (not all_concepts) and (summary or "").strip():
                        all_concepts = _unique(all_concepts + _concepts_from_summary(summary))

                added_any = False

                # Vectoriser facts (mot-code)
                facts_to_add = []
                for f in facts:
                    if not await self._fact_already_vectorized(sid, f["key"], f.get("agent")):
                        facts_to_add.append(f)
                if facts_to_add:
                    await self._record_facts_in_sql(facts_to_add, s, uid)  # no-op (safe)
                    await self._vectorize_facts(facts_to_add, s, uid)
                    new_items_count += len(facts_to_add); added_any = True

                # Vectoriser concepts (y compris fallback)
                if all_concepts and not await self._any_vectors_for_session_type(sid, "concept"):
                    await self._record_concepts_in_sql(all_concepts, s, uid)  # no-op (safe)
                    await self._vectorize_concepts(all_concepts, s, uid)
                    new_items_count += len(all_concepts); added_any = True

                if not added_any:
                    logger.info(f"Session {sid}: déjà vectorisée ou aucun nouvel item — skip.")
                processed_ids.append(sid)

            except Exception as e:
                logger.error(f"Erreur lors de la consolidation pour la session {sid}: {e}", exc_info=True)

        await self._mark_sessions_as_consolidated(processed_ids)
        await self._decay_knowledge()

        report = {
            "status": "success",
            "message": "La ronde du jardinier est terminée.",
            "consolidated_sessions": len(processed_ids),
            "new_concepts": new_items_count
        }
        logger.info(report)
        return report

    # --------- Thread ciblé ---------
    async def _tend_single_thread(self, thread_id: str) -> Dict[str, Any]:
        tid = (thread_id or "").strip()
        if not tid:
            return {"status": "success", "message": "thread_id vide.", "consolidated_sessions": 0, "new_concepts": 0}
        try:
            # Récupère messages du thread
            msgs = await self.db.fetch_all(
                "SELECT role, content, agent_id FROM messages WHERE thread_id = ? ORDER BY created_at ASC",
                (tid,)
            )
            history = []
            for m in msgs or []:
                role = _row_get(m, "role", "user")
                raw = _row_get(m, "content")
                agent_id = _row_get(m, "agent_id")
                text = raw if isinstance(raw, str) else json.dumps(raw or "")
                history.append({"role": role, "content": text, "agent_id": agent_id})

            facts = self._extract_facts_from_history(history)
            analysis = await self.analyzer.analyze_history(session_id=tid, history=history) if history else {}
            all_concepts = _unique((analysis.get("concepts") or []) + (analysis.get("entities") or []))
            if (not all_concepts) and (analysis.get("summary") or "").strip():
                all_concepts = _unique(_concepts_from_summary(analysis.get("summary")))

            new_items = 0; added_any = False
            if facts:
                facts_to_add = []
                for f in facts:
                    if not await self._fact_already_vectorized(tid, f["key"], f.get("agent")):
                        facts_to_add.append(f)
                if facts_to_add:
                    s_like = {"id": tid, "user_id": None, "themes": []}
                    await self._vectorize_facts(facts_to_add, s_like, None)
                    new_items += len(facts_to_add); added_any = True

            if all_concepts and not await self._any_vectors_for_session_type(tid, "concept"):
                s_like = {"id": tid, "user_id": None, "themes": []}
                await self._vectorize_concepts(all_concepts, s_like, None)
                new_items += len(all_concepts); added_any = True

            await self._decay_knowledge()
            msg = "Consolidation thread OK." if added_any else "Aucun nouvel item pour ce thread."
            return {"status": "success", "message": msg, "consolidated_sessions": 1 if added_any else 0, "new_concepts": new_items}
        except Exception as e:
            logger.error(f"Erreur consolidation thread {thread_id}: {e}", exc_info=True)
            return {"status": "error", "message": str(e), "consolidated_sessions": 0, "new_concepts": 0}

    # --------- Helpers DB / parsing / vectorisation ---------
    async def _fetch_recent_sessions(self, limit: int = 10) -> List[Dict[str, Any]]:
        rows = await self.db.fetch_all(
            "SELECT id, user_id, session_data, summary, extracted_concepts, extracted_entities "
            "FROM sessions ORDER BY updated_at DESC LIMIT ?",
            (int(limit or 10),)
        )
        out: List[Dict[str, Any]] = []
        for r in rows or []:
            out.append({
                "id": _row_get(r, "id"),
                "user_id": _row_get(r, "user_id"),
                "session_data": _row_get(r, "session_data"),
                "summary": _row_get(r, "summary"),
                "extracted_concepts": _row_get(r, "extracted_concepts"),
                "extracted_entities": _row_get(r, "extracted_entities"),
                "themes": []
            })
        return out

    def _extract_history(self, session_data: Any) -> List[Dict[str, Any]]:
        """Supporte session_data sous forme JSON (str) ou dict avec 'history'/'messages'."""
        history: List[Dict[str, Any]] = []
        if not session_data:
            return history
        try:
            obj = json.loads(session_data) if isinstance(session_data, str) else session_data
            msgs = (obj.get("history") or obj.get("messages") or []) if isinstance(obj, dict) else []
            for m in msgs:
                if not isinstance(m, dict):
                    continue
                role = m.get("role") or "user"
                text = m.get("content") or m.get("message") or ""
                if not isinstance(text, str):
                    try:
                        text = json.dumps(text or "")
                    except Exception:
                        text = str(text)
                history.append({"role": role, "content": text, "agent_id": m.get("agent_id")})
        except Exception:
            pass
        return history

    def _parse_concepts(self, raw: Any) -> List[str]:
        if not raw:
            return []
        if isinstance(raw, list):
            return [str(x) for x in raw if str(x).strip()]
        try:
            data = json.loads(raw) if isinstance(raw, str) else raw
            if isinstance(data, list):
                return [str(x) for x in data if str(x).strip()]
            if isinstance(data, dict) and "concepts" in data:
                return [str(x) for x in (data.get("concepts") or []) if str(x).strip()]
        except Exception:
            pass
        return []

    def _parse_entities(self, raw: Any) -> List[str]:
        if not raw:
            return []
        if isinstance(raw, list):
            return [str(x) for x in raw if str(x).strip()]
        try:
            data = json.loads(raw) if isinstance(raw, str) else raw
            if isinstance(data, list):
                return [str(x) for x in data if str(x).strip()]
            if isinstance(data, dict) and "entities" in data:
                return [str(x) for x in (data.get("entities") or []) if str(x).strip()]
        except Exception:
            pass
        return []

    def _extract_facts_from_history(self, history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        facts: List[Dict[str, Any]] = []
        for m in history or []:
            text = (m.get("content") or "").strip()
            if not text:
                continue
            for pat in _CODE_PATTERNS:
                for match in re.finditer(pat, text, re.IGNORECASE):
                    value = _clean_value(match.group("value") or "")
                    agent = _agent_norm(match.groupdict().get("agent"))
                    if value:
                        facts.append({"key": "mot-code", "value": value, "agent": agent})
        return facts

    async def _any_vectors_for_session_type(self, session_id: str, type_: str) -> bool:
        got = self.knowledge_collection.get(where={"session_id": session_id, "type": type_})
        ids = got.get("ids") or []
        if ids and isinstance(ids, list) and len(ids) > 0 and isinstance(ids[0], list):
            ids = [x for sub in ids for x in (sub or [])]
        return bool(ids)

    async def _fact_already_vectorized(self, session_id: str, key: str, agent: Optional[str]) -> bool:
        where = {"$and": [{"session_id": session_id}, {"type": "fact"}, {"key": key}]}
        if agent:
            where["$and"].append({"agent": agent})
        got = self.knowledge_collection.get(where=where)
        ids = got.get("ids") or []
        if ids and isinstance(ids, list) and len(ids) > 0 and isinstance(ids[0], list):
            ids = [x for sub in ids for x in (sub or [])]
        return bool(ids)

    async def _record_facts_in_sql(self, facts: List[Dict[str, Any]], session_row: Dict[str, Any], uid: Optional[str]):
        # Placeholder pour persistance SQL dédiée si tu crées une table knowledge_facts.
        return

    async def _vectorize_facts(self, facts: List[Dict[str, Any]], session_row: Dict[str, Any], uid: Optional[str]):
        docs: List[str] = []
        metas: List[Dict[str, Any]] = []
        ids: List[str] = []
        sid = session_row.get("id")
        for f in facts or []:
            agent = f.get("agent")
            text = f"Mot-code{f' ({agent})' if agent else ''}: {f['value']}"
            doc_id = _sha1(f"{sid}:fact:{f.get('key')}:{agent or 'global'}:{f['value']}")
            docs.append(text)
            metas.append({
                "type": "fact",
                "key": f.get("key"),
                "value": f.get("value"),
                "agent": agent,
                "session_id": sid,
                "user_id": uid,
                "created_at": _now_iso()
            })
            ids.append(doc_id)
        if docs:
            self.knowledge_collection.add(documents=docs, metadatas=metas, ids=ids)

    async def _record_concepts_in_sql(self, concepts: List[str], session_row: Dict[str, Any], uid: Optional[str]):
        # Placeholder pour persistance SQL dédiée si nécessaire.
        return

    async def _vectorize_concepts(self, concepts: List[str], session_row: Dict[str, Any], uid: Optional[str]):
        sid = session_row.get("id")
        docs = []
        metas = []
        ids = []
        for c in concepts or []:
            c_clean = _clean_value(str(c))
            if not c_clean:
                continue
            docs.append(c_clean)
            metas.append({
                "type": "concept",
                "session_id": sid,
                "user_id": uid,
                "created_at": _now_iso()
            })
            ids.append(_sha1(f"{sid}:concept:{c_clean.lower()}"))
        if docs:
            self.knowledge_collection.add(documents=docs, metadatas=metas, ids=ids)

    async def _mark_sessions_as_consolidated(self, ids: List[str]):
        if not ids:
            return
        # Rien à marquer pour l’instant (piloté par updated_at ailleurs).

    async def _decay_knowledge(self):
        logger.info("Vieillissement journalisé (monitoring.knowledge_decay).")
