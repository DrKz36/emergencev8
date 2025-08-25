# src/backend/features/memory/gardener.py
# V2.5 - FAST-PATH concepts existants + récolte élargie + dédoublonnage vector store
import logging
import uuid
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from backend.core.database.manager import DatabaseManager
from backend.features.memory.vector_service import VectorService
from backend.features.memory.analyzer import MemoryAnalyzer

logger = logging.getLogger(__name__)

class MemoryGardener:
    """
    MEMORY GARDENER V2.5
    - Si des 'extracted_concepts' existent déjà en BDD: vectorisation directe (FAST-PATH).
    - Sinon: on tente l'analyse sémantique si un 'history' est présent.
    - Récolte élargie: dernières sessions par updated_at (limite N), pas seulement "sans concepts".
    - Dédoublonnage: on évite de replanter si des vecteurs existent déjà pour la session.
    """
    KNOWLEDGE_COLLECTION_NAME = "emergence_knowledge"

    def __init__(self, db_manager: DatabaseManager, vector_service: VectorService, memory_analyzer: MemoryAnalyzer):
        self.db = db_manager
        self.vector_service = vector_service
        self.analyzer = memory_analyzer
        self.knowledge_collection = self.vector_service.get_or_create_collection(self.KNOWLEDGE_COLLECTION_NAME)
        logger.info("MemoryGardener V2.5 initialisé.")

    async def tend_the_garden(self, consolidation_limit: int = 10) -> Dict[str, Any]:
        logger.info("Le jardinier commence sa ronde dans le jardin de la mémoire...")

        sessions_to_process = await self._fetch_recent_sessions(limit=consolidation_limit)
        if not sessions_to_process:
            logger.info("Aucune session récente à traiter. Le jardin est en ordre.")
            await self._decay_knowledge()
            return {"status": "success", "message": "Aucune session à traiter.", "consolidated_sessions": 0, "new_concepts": 0}

        logger.info(f"Récolte de {len(sessions_to_process)} sessions pour consolidation.")
        new_concepts_count = 0
        processed_ids: List[str] = []

        for session in sessions_to_process:
            sid: str = session["id"]
            uid: Optional[str] = session.get("user_id")

            try:
                # 0) Dédup: si déjà vectorisé pour cette session -> skip
                if await self._already_vectorized_for_session(sid):
                    logger.info(f"Session {sid}: déjà vectorisée — skip.")
                    continue

                # 1) FAST-PATH: si des concepts existent déjà en BDD, vectoriser sans ré-analyser
                raw_concepts = session.get("extracted_concepts")
                concepts = self._parse_concepts(raw_concepts)
                if concepts:
                    await self._record_concepts_in_sql(concepts, session, uid)
                    await self._vectorize_concepts(concepts, session, uid)
                    new_concepts_count += len(concepts)
                    processed_ids.append(sid)
                    continue

                # 2) Sinon: tenter l'analyse sémantique si on trouve un history
                history = self._extract_history(session.get("session_data"))
                if not history:
                    logger.info(f"Session {sid}: pas d'history ni de concepts — skip.")
                    continue

                await self.analyzer.analyze_session_for_concepts(session_id=sid, history=history)

                # 3) Relire les concepts puis vectoriser
                row = await self.db.fetch_one("SELECT extracted_concepts, user_id FROM sessions WHERE id = ?", (sid,))
                concepts = self._parse_concepts(row.get("extracted_concepts") if row else None)
                if concepts:
                    await self._record_concepts_in_sql(concepts, session, uid or (row.get("user_id") if row else None))
                    await self._vectorize_concepts(concepts, session, uid or (row.get("user_id") if row else None))
                    new_concepts_count += len(concepts)

                processed_ids.append(sid)

            except Exception as e:
                logger.error(f"Erreur lors de la consolidation pour la session {sid}: {e}", exc_info=True)

        # 4) Marquer consolidé (trace temporelle simple)
        await self._mark_sessions_as_consolidated(processed_ids)

        # 5) Vieillissement
        await self._decay_knowledge()

        report = {
            "status": "success",
            "message": "La ronde du jardinier est terminée.",
            "consolidated_sessions": len(processed_ids),
            "new_concepts": new_concepts_count
        }
        logger.info(report)
        return report

    # ---------- Helpers ----------

    async def _fetch_recent_sessions(self, limit: int) -> List[Dict[str, Any]]:
        # On ne filtre plus sur "summary/concepts vides" pour ne pas exclure
        # les sessions déjà analysées mais pas encore vectorisées.
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

    async def _already_vectorized_for_session(self, session_id: str) -> bool:
        try:
            # On utilise un 'where' sur la metadata pour savoir si des vecteurs existent déjà
            res = self.vector_service.query(
                self.knowledge_collection,
                query_text=session_id,  # n'importe quel texte pour satisfaire l'API
                n_results=1,
                where_filter={"source_session_id": session_id}
            )
            return bool(res)
        except Exception:
            return False

    async def _record_concepts_in_sql(self, concepts: List[str], session: Dict[str, Any], user_id: Optional[str]):
        now = datetime.now(timezone.utc).isoformat()
        for concept_text in concepts:
            concept_id = uuid.uuid4().hex
            details = {
                "id": concept_id,
                "concept": concept_text,
                "source_session_id": session["id"],
                "user_id": user_id,
                "categories": session.get("themes", []),
                "vector_id": concept_id
            }
            try:
                await self.db.execute(
                    "INSERT INTO monitoring (event_type, event_details, timestamp) VALUES (?, ?, ?)",
                    ("knowledge_concept", json.dumps(details, ensure_ascii=False), now)
                )
            except Exception as e:
                logger.warning(f"Trace concept SQL échouée (session {session['id']}): {e}", exc_info=True)

    async def _vectorize_concepts(self, concepts: List[str], session: Dict[str, Any], user_id: Optional[str]):
        payload = []
        for concept_text in concepts:
            concept_id = uuid.uuid4().hex
            payload.append({
                "id": concept_id,
                "text": concept_text,
                "metadata": {
                    "user_id": user_id,
                    "source_session_id": session["id"],
                    "concept_text": concept_text,
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
            })
        if payload:
            self.vector_service.add_items(self.knowledge_collection, payload)
            logger.info(f"{len(payload)} concepts vectorisés et plantés.")

    async def _mark_sessions_as_consolidated(self, session_ids: List[str]):
        if not session_ids:
            return
        now = datetime.now(timezone.utc).isoformat()
        try:
            params = [(now, sid) for sid in session_ids]
            await self.db.executemany("UPDATE sessions SET updated_at = ? WHERE id = ?", params)
        except Exception as e:
            logger.warning(f"Impossible de marquer les sessions consolidées: {e}", exc_info=True)

    async def _decay_knowledge(self):
        now = datetime.now(timezone.utc).isoformat()
        try:
            await self.db.execute(
                "INSERT INTO monitoring (event_type, event_details, timestamp) VALUES (?, ?, ?)",
                ("knowledge_decay", json.dumps({"note": "decay applied"}, ensure_ascii=False), now)
            )
            logger.info("Vieillissement journalisé (monitoring.knowledge_decay).")
        except Exception as e:
            logger.warning(f"Échec vieillissement (trace): {e}", exc_info=True)
