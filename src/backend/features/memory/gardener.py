# src/backend/features/memory/gardener.py
# V3.3 - Plante aussi le résumé en vecteur (en plus des concepts) + déduplication.
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
    - Récolte les sessions non consolidées (is_consolidated = 0)
    - Analyse -> summary/concepts/entities
    - Plante:
        * SQL (knowledge_concepts)
        * VectorStore ('emergence_knowledge')
        * Recopie aussi dans 'emergence_documents' pour le RAG existant.
    - Marque les sessions consolidées.
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
                    # 1) Historique
                    history: List[Dict[str, Any]] = []
                    raw = s.get('session_data')
                    if raw:
                        try:
                            history = json.loads(raw) if isinstance(raw, str) else raw
                        except Exception:
                            logger.warning(f"Session {sid}: 'session_data' non JSON.")

                    # 2) Analyse sémantique (écrit summary/concepts/entities en BDD)
                    analysis = await self.analyzer.analyze_session_for_concepts(sid, history)
                    concepts: List[str] = list(dict.fromkeys((analysis or {}).get("concepts", []) or []))
                    summary: str = (analysis or {}).get("summary") or ""

                    # 3) Relecture “vérité BDD” des concepts si nécessaire
                    if not concepts:
                        row = await dbq.get_session_by_id(self.db, sid)
                        if row:
                            try:
                                row_dict = row if isinstance(row, dict) else dict(row)
                                raw_concepts = row_dict.get('extracted_concepts')
                                if isinstance(raw_concepts, str):
                                    concepts = json.loads(raw_concepts or "[]")
                                elif isinstance(raw_concepts, list):
                                    concepts = raw_concepts
                            except Exception:
                                logger.warning(f"Session {sid}: 'extracted_concepts' illisible.")

                    # 4) Étend le set avec le résumé (utile au RAG même si concepts maigres)
                    extended_concepts = list(dict.fromkeys([c for c in concepts if c] + ([summary] if summary else [])))

                    if extended_concepts:
                        await self._plant_concepts(extended_concepts, sid)
                        total_concepts += len(extended_concepts)
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
        seen = set()
        items = []
        for concept_text in concepts:
            concept_text = (concept_text or "").strip()
            if not concept_text or concept_text in seen:
                continue
            seen.add(concept_text)

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
        logger.info(f"{len(items)} concept(s)/résumé(s) vectorisés (knowledge + documents).")

    async def _decay_knowledge(self):
        # Stratégie future (décroissance). No-op pour l'instant.
        logger.debug("Décroissance: noop.")
