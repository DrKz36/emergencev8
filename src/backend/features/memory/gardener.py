# src/backend/features/memory/gardener.py
# V3.1 - Consolidation mémoire (SQL + Chroma) + injection dans la collection documents pour RAG
import logging
import uuid
import json
from typing import Dict, Any, List
from datetime import datetime, timezone

from backend.core.database.manager import DatabaseManager
from backend.core.database import queries as dbq
from backend.features.memory.vector_service import VectorService
from backend.features.memory.analyzer import MemoryAnalyzer
from backend.core import config

logger = logging.getLogger(__name__)

class MemoryGardener:
    """Consolide la connaissance issue des sessions:
    - Récolte les sessions non consolidées (sessions.is_consolidated = 0)
    - Analyse -> concepts / entités (via MemoryAnalyzer + LLM)
    - Plante les concepts:
        * en SQL (knowledge_concepts)
        * dans le VectorStore (collection 'emergence_knowledge')
        * et également dans la collection DOCUMENTS pour qu'ils soient pris en compte par le RAG existant.
    - Marque les sessions comme consolidées.
    """
    KNOWLEDGE_COLLECTION_NAME = "emergence_knowledge"

    def __init__(self, db_manager: DatabaseManager, vector_service: VectorService, memory_analyzer: MemoryAnalyzer):
        self.db = db_manager
        self.vector_service = vector_service
        self.analyzer = memory_analyzer
        self.knowledge_collection = self.vector_service.get_or_create_collection(self.KNOWLEDGE_COLLECTION_NAME)
        self.document_collection = self.vector_service.get_or_create_collection(
            getattr(config, "DOCUMENT_COLLECTION_NAME", "emergence_documents")
        )
        logger.info("MemoryGardener initialisé.")

    async def tend_the_garden(self, consolidation_limit: int = 10) -> Dict[str, Any]:
        logger.info("Ronde du jardinier: début.")
        try:
            sessions_to_process = await dbq.get_unconsolidated_sessions(self.db, limit=consolidation_limit)
            if not sessions_to_process:
                logger.info("Aucune session à consolider.")
                await self._decay_knowledge()
                return {"status": "success", "message": "Aucune session à traiter.", "consolidated_sessions": 0, "new_concepts": 0}

            total_concepts = 0
            consolidated_ids: List[str] = []

            for s in sessions_to_process:
                sid = s['id']
                try:
                    # Préparer l'historique
                    history: List[Dict[str, Any]] = []
                    raw = s.get('session_data')
                    if raw:
                        try:
                            history = json.loads(raw) if isinstance(raw, str) else raw
                        except Exception:
                            logger.warning(f"Session {sid}: 'session_data' non JSON.")

                    # Analyse sémantique (écrit summary / concepts / entities dans la table sessions)
                    await self.analyzer.analyze_session_for_concepts(sid, history)

                    # Relire les concepts extraits depuis la BDD
                    row = await dbq.get_session_by_id(self.db, sid)
                    concepts = []
                    if row:
                        try:
                            concepts = json.loads(row.get('extracted_concepts') or '[]') if isinstance(row, dict) else []
                        except Exception:
                            logger.warning(f"Session {sid}: 'extracted_concepts' illisible.")
                    if concepts:
                        await self._plant_concepts(concepts, sid)
                        total_concepts += len(concepts)
                        consolidated_ids.append(sid)
                    else:
                        logger.info(f"Session {sid}: aucun concept détecté.")
                except Exception as e:
                    logger.error(f"Erreur pendant consolidation de {sid}: {e}", exc_info=True)

            if consolidated_ids:
                await dbq.mark_sessions_as_consolidated(self.db, consolidated_ids)

            await self._decay_knowledge()

            return {
                "status": "success",
                "message": "Ronde terminée.",
                "consolidated_sessions": len(consolidated_ids),
                "new_concepts": total_concepts
            }
        except Exception as e:
            logger.critical(f"Échec critique de la ronde du jardinier: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    async def _plant_concepts(self, concepts: List[str], source_session_id: str):
        items = []
        for concept_text in concepts:
            cid = str(uuid.uuid4())
            # 1) SQL (index sémantique)
            await dbq.upsert_knowledge_concept(self.db, {
                "id": cid,
                "concept": concept_text,
                "description": f"Concept extrait de la session {source_session_id}",
                "categories": [],
                "vector_id": cid
            })
            # 2) Vector items (connaissances)
            meta = {
                "source_session_id": source_session_id,
                "kind": "memory",
                "concept_text": concept_text,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            items.append({"id": cid, "text": concept_text, "metadata": meta})

        if not items:
            return

        # Ajout dans la collection "mémoire"
        self.vector_service.add_items(self.knowledge_collection, items)
        # Ajout également dans la collection documents (pour RAG existant)
        self.vector_service.add_items(self.document_collection, items)
        logger.info(f"{len(items)} concept(s) vectorisés (knowledge + documents).")

    async def _decay_knowledge(self):
        # Stratégie future (décroissance). No-op pour l'instant.
        logger.debug("Décroissance: noop.")
