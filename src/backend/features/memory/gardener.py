# src/backend/features/memory/gardener.py
# V2.0 - FINAL: Réécriture complète en asynchrone avec logique de consolidation.
import logging
import uuid
from typing import Dict, Any, List
from datetime import datetime, timezone

from backend.core.database_backup import DatabaseManager
from backend.features.memory.vector_service import VectorService
from backend.features.memory.analyzer import MemoryAnalyzer

logger = logging.getLogger(__name__)

class MemoryGardener:
    """
    MEMORY GARDENER V2.0 - Le jardinier de la mémoire, asynchrone et intelligent.
    Responsabilité : Consolider la connaissance des sessions terminées dans une
    base de connaissance durable (SQL + Vectorielle) et gérer son cycle de vie.
    """
    KNOWLEDGE_COLLECTION_NAME = "emergence_knowledge"

    def __init__(self, db_manager: DatabaseManager, vector_service: VectorService, memory_analyzer: MemoryAnalyzer):
        self.db = db_manager
        self.vector_service = vector_service
        self.analyzer = memory_analyzer
        self.knowledge_collection = self.vector_service.get_or_create_collection(self.KNOWLEDGE_COLLECTION_NAME)
        logger.info("MemoryGardener V2.0 (Async) initialisé.")

    async def tend_the_garden(self, consolidation_limit: int = 10) -> Dict[str, Any]:
        """
        Tâche principale du jardinier, à exécuter manuellement ou périodiquement.
        1. Récolte les sessions non consolidées.
        2. Analyse, extrait et consolide les concepts dans le KnowledgeGraph.
        3. Fait vieillir la connaissance existante.
        """
        logger.info("Le jardinier commence sa ronde dans le jardin de la mémoire...")
        
        try:
            # 1. Récolte
            sessions_to_process = await self.db.get_unconsolidated_sessions(limit=consolidation_limit)
            if not sessions_to_process:
                logger.info("Aucune nouvelle session à consolider. Le jardin est en ordre.")
                await self._decay_knowledge()
                return {"status": "success", "message": "Aucune nouvelle session à traiter.", "consolidated_sessions": 0, "new_concepts": 0}

            logger.info(f"Récolte de {len(sessions_to_process)} sessions pour consolidation.")
            
            # 2. Consolidation
            new_concepts_count = 0
            for session in sessions_to_process:
                try:
                    # L'analyseur est synchrone, on l'exécute tel quel.
                    analysis = self.analyzer.analyze_session(session)
                    concepts = analysis.get("concepts", [])
                    
                    if concepts:
                        logger.info(f"Session {session['id']}: {len(concepts)} concepts extraits -> {concepts}")
                        await self._plant_concepts(concepts, session)
                        new_concepts_count += len(concepts)
                    else:
                        logger.info(f"Session {session['id']}: Aucun concept majeur détecté.")

                except Exception as e:
                    logger.error(f"Erreur lors de l'analyse de la session {session['id']}: {e}", exc_info=True)
            
            # 3. Marquer comme traité
            session_ids = [s['id'] for s in sessions_to_process]
            await self.db.mark_sessions_as_consolidated(session_ids)

            # 4. Entretien (vieillissement)
            await self._decay_knowledge()
            
            report = {
                "status": "success",
                "message": "La ronde du jardinier est terminée.",
                "consolidated_sessions": len(sessions_to_process),
                "new_concepts": new_concepts_count
            }
            logger.info(report)
            return report

        except Exception as e:
            logger.critical(f"Échec critique de la ronde du jardinier: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    async def _plant_concepts(self, concepts: List[str], session: Dict[str, Any]):
        """Sauvegarde les concepts dans la DB et le Vector Store."""
        
        concepts_to_vectorize = []
        for concept_text in concepts:
            concept_id = str(uuid.uuid4())
            concept_db_entry = {
                "id": concept_id,
                "concept": concept_text,
                "description": f"Concept extrait de la session {session['id']}",
                "categories": session.get("themes", []),
                "vector_id": concept_id # Utiliser le même ID pour la jointure logique
            }
            # Sauvegarde en BDD SQL
            await self.db.upsert_knowledge_concept(concept_db_entry)

            # Préparation pour la vectorisation
            concepts_to_vectorize.append({
                "id": concept_id,
                "text": concept_text,
                "metadata": {
                    "source_session_id": session['id'],
                    "concept_text": concept_text,
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
            })
        
        # Ajout en batch au Vector Store
        if concepts_to_vectorize:
            self.vector_service.add_items(self.knowledge_collection, concepts_to_vectorize)
            logger.info(f"{len(concepts_to_vectorize)} concepts vectorisés et plantés.")

    async def _decay_knowledge(self):
        """Applique le vieillissement à tous les concepts du Knowledge Graph."""
        logger.info("Application du vieillissement sur le Knowledge Graph...")
        await self.db.decay_knowledge_vivacity()
        logger.info("La vivacité des souvenirs a été mise à jour.")

