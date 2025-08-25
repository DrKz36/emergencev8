# src/backend/features/memory/gardener.py
# V2.4 - Ajoute user_id dans les métadonnées vectorisées + trace SQL enrichie
import logging
import uuid
import json
from typing import Dict, Any, List
from datetime import datetime, timezone

from backend.core.database.manager import DatabaseManager
from backend.features.memory.vector_service import VectorService
from backend.features.memory.analyzer import MemoryAnalyzer

logger = logging.getLogger(__name__)

class MemoryGardener:
    """
    MEMORY GARDENER V2.4
    - Analyse via MemoryAnalyzer.
    - Persistes summary/concepts/entities (fait par l'analyzer).
    - Vectorise les concepts dans 'emergence_knowledge' avec metadata { user_id, source_session_id, ... }.
    - Traçage simple dans 'monitoring'.
    """
    KNOWLEDGE_COLLECTION_NAME = "emergence_knowledge"

    def __init__(self, db_manager: DatabaseManager, vector_service: VectorService, memory_analyzer: MemoryAnalyzer):
        self.db = db_manager
        self.vector_service = vector_service
        self.analyzer = memory_analyzer
        self.knowledge_collection = self.vector_service.get_or_create_collection(self.KNOWLEDGE_COLLECTION_NAME)
        logger.info("MemoryGardener V2.4 initialisé.")

    async def tend_the_garden(self, consolidation_limit: int = 10) -> Dict[str, Any]:
        logger.info("Le jardinier commence sa ronde dans le jardin de la mémoire...")

        sessions_to_process = await self._fetch_unconsolidated_sessions(limit=consolidation_limit)
        if not sessions_to_process:
            logger.info("Aucune nouvelle session à consolider. Le jardin est en ordre.")
            await self._decay_knowledge()
            return {"status": "success", "message": "Aucune nouvelle session à traiter.", "consolidated_sessions": 0, "new_concepts": 0}

        logger.info(f"Récolte de {len(sessions_to_process)} sessions pour consolidation.")
        new_concepts_count = 0
        processed_ids: List[str] = []

        for session in sessions_to_process:
            sid = session["id"]
            try:
                # 1) History depuis session_data
                history = []
                try:
                    sd = session.get("session_data")
                    if sd:
                        parsed = json.loads(sd)
                        if isinstance(parsed, list):
                            history = parsed
                        elif isinstance(parsed, dict) and "history" in parsed:
                            history = parsed["history"]
                except Exception as e:
                    logger.warning(f"Parsing session_data KO pour {sid}: {e}")

                if not history:
                    logger.info(f"Session {sid}: history vide — skip analyse.")
                    continue

                # 2) Analyse sémantique (persistance DB par l'analyzer)
                await self.analyzer.analyze_session_for_concepts(session_id=sid, history=history)

                # 3) Relire concepts puis vectoriser + tracer
                row = await self.db.fetch_one("SELECT user_id, extracted_concepts FROM sessions WHERE id = ?", (sid,))
                concepts = []
                uid = None
                if row:
                    uid = row.get("user_id")
                    if row.get("extracted_concepts"):
                        try:
                            concepts = json.loads(row["extracted_concepts"]) or []
                        except Exception as e:
                            logger.warning(f"JSON concepts invalide pour {sid}: {e}")

                if concepts:
                    await self._record_concepts_in_sql(concepts, session, uid)
                    await self._vectorize_concepts(concepts, session, uid)
                    new_concepts_count += len(concepts)

                processed_ids.append(sid)

            except Exception as e:
                logger.error(f"Erreur lors de la consolidation pour la session {sid}: {e}", exc_info=True)

        # 4) Marquer consolidé
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

    async def _fetch_unconsolidated_sessions(self, limit: int) -> List[Dict[str, Any]]:
        query = """
            SELECT id, user_id, created_at, updated_at, session_data, summary, extracted_concepts, extracted_entities
            FROM sessions
            WHERE (summary IS NULL OR TRIM(summary) = '')
               OR (extracted_concepts IS NULL OR extracted_concepts = '[]')
            ORDER BY updated_at DESC
            LIMIT ?
        """
        rows = await self.db.fetch_all(query, (int(limit),))
        return [dict(r) for r in (rows or [])]

    async def _record_concepts_in_sql(self, concepts: List[str], session: Dict[str, Any], user_id: str | None):
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

    async def _vectorize_concepts(self, concepts: List[str], session: Dict[str, Any], user_id: str | None):
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
