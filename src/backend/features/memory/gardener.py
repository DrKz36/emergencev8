# src/backend/features/memory/gardener.py
# V2.6.1 — FIX sqlite3.Row.get (→ dict(row)) + extraction texte robuste (text|content|message)
import logging
import uuid
import json
import re
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from backend.core.database.manager import DatabaseManager
from backend.features.memory.vector_service import VectorService
from backend.features.memory.analyzer import MemoryAnalyzer

logger = logging.getLogger(__name__)

_CODE_PATTERNS = [
    # “Pour Anima, mon mot-code est ‘nexus’.” / “Pour neo, mon mot code: vlad”
    r"(?:pour\s+(anima|neo|nexus)\s*,?\s*)?mon\s*mot[-\s]?code\s*(?:est|:)\s*[«\"'’]?\s*([A-Za-zÀ-ÖØ-öø-ÿ0-9_\-]+)\s*[»\"'’]?",
    # “Mon mot-code pour Anima est nexus”
    r"mon\s*mot[-\s]?code\s*pour\s+(anima|neo|nexus)\s*(?:est|:)\s*[«\"'’]?\s*([A-Za-zÀ-ÖØ-öø-ÿ0-9_\-]+)\s*[»\"'’]?"
]

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _unique(seq: List[str]) -> List[str]:
    seen = set()
    out = []
    for s in seq or []:
        key = s.strip().lower()
        if key and key not in seen:
            out.append(s.strip())
            seen.add(key)
    return out

def _agent_norm(name: Optional[str]) -> Optional[str]:
    if not name:
        return None
    n = name.strip().lower()
    if n in {"anima", "neo", "nexus"}:
        return n
    return None

class MemoryGardener:
    """
    MEMORY GARDENER V2.6.1
    - FIX: accès aux colonnes sur aiosqlite.Row (dict(row) avant .get).
    - Vectorise concepts/entities + FAITS (mot-code/agent) avec dédup fine.
    - Ne 'skip' pas si de nouveaux facts sont détectés.
    """
    KNOWLEDGE_COLLECTION_NAME = "emergence_knowledge"

    def __init__(self, db_manager: DatabaseManager, vector_service: VectorService, memory_analyzer: MemoryAnalyzer):
        self.db = db_manager
        self.vector_service = vector_service
        self.analyzer = memory_analyzer
        self.knowledge_collection = self.vector_service.get_or_create_collection(self.KNOWLEDGE_COLLECTION_NAME)
        logger.info("MemoryGardener V2.6.1 initialisé.")

    async def tend_the_garden(self, consolidation_limit: int = 10) -> Dict[str, Any]:
        logger.info("Le jardinier commence sa ronde dans le jardin de la mémoire...")

        sessions = await self._fetch_recent_sessions(limit=consolidation_limit)
        if not sessions:
            logger.info("Aucune session récente à traiter. Le jardin est en ordre.")
            await self._decay_knowledge()
            return {"status": "success", "message": "Aucune session à traiter.", "consolidated_sessions": 0, "new_concepts": 0}

        logger.info(f"Récolte de {len(sessions)} sessions pour consolidation.")
        processed_ids: List[str] = []
        new_items_count = 0

        for s in sessions:
            sid: str = s["id"]
            uid: Optional[str] = s.get("user_id")

            try:
                history = self._extract_history(s.get("session_data"))
                # 1) Préparer concepts/entités existants
                concepts = self._parse_concepts(s.get("extracted_concepts"))
                entities = self._parse_entities(s.get("extracted_entities"))
                all_concepts = _unique((concepts or []) + (entities or []))

                # 2) Extraire des FAITS (mot-code/agent) depuis l'history
                facts = self._extract_facts_from_history(history)

                # 3) Si pas de concepts mais un history: lancer analyse sémantique puis recharger
                if not concepts and history:
                    await self.analyzer.analyze_session_for_concepts(session_id=sid, history=history)
                    row = await self.db.fetch_one(
                        "SELECT extracted_concepts, extracted_entities, user_id FROM sessions WHERE id = ?",
                        (sid,)
                    )
                    row = dict(row) if row is not None else None
                    concepts = self._parse_concepts(row.get("extracted_concepts") if row else None)
                    entities = self._parse_entities(row.get("extracted_entities") if row else None)
                    all_concepts = _unique((concepts or []) + (entities or []))

                # 4) Dédup fine & vectorisation
                added_any = False

                # 4a) FAITS: ajoute uniquement les nouveaux (clé/agent)
                facts_to_add = []
                for fact in facts:
                    if not await self._fact_already_vectorized(sid, fact["key"], fact.get("agent")):
                        facts_to_add.append(fact)

                if facts_to_add:
                    await self._record_facts_in_sql(facts_to_add, s, uid)
                    await self._vectorize_facts(facts_to_add, s, uid)
                    new_items_count += len(facts_to_add)
                    added_any = True

                # 4b) CONCEPTS/ENTITIES: si aucun vecteur encore enregistré pour cette session
                if all_concepts and not await self._any_vectors_for_session(sid):
                    await self._record_concepts_in_sql(all_concepts, s, uid)
                    await self._vectorize_concepts(all_concepts, s, uid)
                    new_items_count += len(all_concepts)
                    added_any = True

                if not added_any:
                    logger.info(f"Session {sid}: déjà vectorisée ou aucun nouvel item — skip.")
                processed_ids.append(sid)

            except Exception as e:
                logger.error(f"Erreur lors de la consolidation pour la session {sid}: {e}", exc_info=True)

        # 5) Trace consolidation & 6) vieillissement
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

    # ---------- Helpers ----------

    async def _fetch_recent_sessions(self, limit: int) -> List[Dict[str, Any]]:
        query = """
            SELECT id, user_id, created_at, updated_at, session_data, summary, extracted_concepts, extracted_entities
            FROM sessions
            ORDER BY updated_at DESC
            LIMIT ?
        """
        rows = await self.db.fetch_all(query, (int(limit),))
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

    def _extract_history(self, session_data: Any) -> List[Dict[str, Any]]:
        try:
            if not session_data:
                return []
            parsed = json.loads(session_data) if isinstance(session_data, str) else session_data
            if isinstance(parsed, list):
                return parsed
            if isinstance(parsed, dict) and "history" in parsed:
                return parsed["history"]
        except Exception as e:
            logger.warning(f"Parsing session_data KO: {e}")
        return []

    def _extract_facts_from_history(self, history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Cherche des motifs 'mot-code' dans l'history. Retourne des dicts avec text + metadata (type='fact')."""
        if not history:
            return []
        facts: List[Dict[str, Any]] = []
        for msg in history:
            # Robustesse: accepter 'text' | 'content' | 'message'
            text = (msg.get("text") or msg.get("content") or msg.get("message") or "").strip()
            agent_hint = _agent_norm(msg.get("agent_id") or msg.get("agent"))
            if not text:
                continue

            for pat in _CODE_PATTERNS:
                m = re.search(pat, text, flags=re.IGNORECASE)
                if m:
                    g1, g2 = (m.group(1), m.group(2)) if m.lastindex and m.lastindex >= 2 else (None, None)
                    agent = _agent_norm(g1) or agent_hint
                    value = (g2 or "").strip()
                    if value:
                        display_agent = agent or "global"
                        facts.append({
                            "key": "mot-code",
                            "agent": agent,
                            "value": value,
                            "text": f"Mot-code ({display_agent})={value}"
                        })
                    break  # éviter doublons sur le même message

        # Unicité par (key, agent, value)
        seen = set()
        uniq: List[Dict[str, Any]] = []
        for f in facts:
            t = (f["key"], f.get("agent"), f["value"])
            if t not in seen:
                uniq.append(f)
                seen.add(t)
        return uniq

    async def _any_vectors_for_session(self, session_id: str) -> bool:
        try:
            res = self.vector_service.query(
                self.knowledge_collection,
                query_text=session_id,
                n_results=1,
                where_filter={"source_session_id": session_id}
            )
            return bool(res)
        except Exception:
            return False

    async def _fact_already_vectorized(self, session_id: str, key: str, agent: Optional[str]) -> bool:
        try:
            where = {"source_session_id": session_id, "type": "fact", "key": key}
            if agent:
                where["agent"] = agent
            res = self.vector_service.query(
                self.knowledge_collection,
                query_text=key,
                n_results=1,
                where_filter=where
            )
            return bool(res)
        except Exception:
            return False

    async def _record_concepts_in_sql(self, concepts: List[str], session: Dict[str, Any], user_id: Optional[str]):
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
                "kind": "concept"
            }
            try:
                await self.db.execute(
                    "INSERT INTO monitoring (event_type, event_details, timestamp) VALUES (?, ?, ?)",
                    ("knowledge_concept", json.dumps(details, ensure_ascii=False), now)
                )
            except Exception as e:
                logger.warning(f"Trace concept SQL échouée (session {session['id']}): {e}", exc_info=True)

    async def _record_facts_in_sql(self, facts: List[Dict[str, Any]], session: Dict[str, Any], user_id: Optional[str]):
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
                "text": fact["text"]
            }
            try:
                await self.db.execute(
                    "INSERT INTO monitoring (event_type, event_details, timestamp) VALUES (?, ?, ?)",
                    ("knowledge_fact", json.dumps(rec, ensure_ascii=False), now)
                )
            except Exception as e:
                logger.warning(f"Trace fact SQL échouée (session {session['id']}): {e}", exc_info=True)

    async def _vectorize_concepts(self, concepts: List[str], session: Dict[str, Any], user_id: Optional[str]):
        payload = []
        for concept_text in concepts:
            vid = uuid.uuid4().hex
            payload.append({
                "id": vid,
                "text": concept_text,
                "metadata": {
                    "type": "concept",
                    "user_id": user_id,
                    "source_session_id": session["id"],
                    "concept_text": concept_text,
                    "created_at": _now_iso()
                }
            })
        if payload:
            self.vector_service.add_items(self.knowledge_collection, payload)
            logger.info(f"{len(payload)} concepts vectorisés et plantés.")

    async def _vectorize_facts(self, facts: List[Dict[str, Any]], session: Dict[str, Any], user_id: Optional[str]):
        payload = []
        for f in facts:
            vid = uuid.uuid4().hex
            payload.append({
                "id": vid,
                "text": f["text"],
                "metadata": {
                    "type": "fact",
                    "key": f["key"],
                    "agent": f.get("agent"),
                    "value": f["value"],
                    "user_id": user_id,
                    "source_session_id": session["id"],
                    "created_at": _now_iso()
                }
            })
        if payload:
            self.vector_service.add_items(self.knowledge_collection, payload)
            logger.info(f"{len(payload)} faits vectorisés et plantés.")

    async def _mark_sessions_as_consolidated(self, session_ids: List[str]):
        if not session_ids:
            return
        now = _now_iso()
        try:
            params = [(now, sid) for sid in session_ids]
            await self.db.executemany("UPDATE sessions SET updated_at = ? WHERE id = ?", params)
        except Exception as e:
            logger.warning(f"Impossible de marquer les sessions consolidées: {e}", exc_info=True)

    async def _decay_knowledge(self):
        now = _now_iso()
        try:
            await self.db.execute(
                "INSERT INTO monitoring (event_type, event_details, timestamp) VALUES (?, ?, ?)",
                ("knowledge_decay", json.dumps({"note": "decay applied"}, ensure_ascii=False), now)
            )
            logger.info("Vieillissement journalisé (monitoring.knowledge_decay).")
        except Exception as e:
            logger.warning(f"Échec vieillissement (trace): {e}", exc_info=True)
