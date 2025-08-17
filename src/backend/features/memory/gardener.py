# src/backend/features/memory/gardener.py
# V3.5 - Ajout user_id dans metadata vector store + robustesse lecture BDD + consolidation inconditionnelle + dédup inter-collections.
import logging
import uuid
import json
from typing import Dict, Any, List, Optional, Set
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
    - Marque les sessions consolidées (même si aucun concept/summary).
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
                return {
                    "status": "success",
                    "message": "Aucune session à traiter.",
                    "consolidated_sessions": 0,
                    "new_concepts": 0
                }

            total_concepts = 0
            consolidated_ids: List[str] = []

            for s in sessions_to_process:
                sid = s["id"]
                try:
                    # 0) Lecture "vérité BDD" (user_id + éventuel fallback des champs)
                    row = await dbq.get_session_by_id(self.db, sid)
                    row_dict = row if isinstance(row, dict) else (dict(row) if row else {})
                    user_id: Optional[str] = row_dict.get("user_id")

                    # 1) Historique
                    history: List[Dict[str, Any]] = []
                    raw = s.get("session_data") or row_dict.get("session_data")
                    if raw:
                        try:
                            history = json.loads(raw) if isinstance(raw, str) else raw
                        except Exception:
                            logger.warning("Session %s: 'session_data' non JSON.", sid)

                    # 2) Analyse sémantique (écrit summary/concepts/entities en BDD)
                    analysis = await self.analyzer.analyze_session_for_concepts(sid, history)
                    concepts: List[str] = list(dict.fromkeys((analysis or {}).get("concepts", []) or []))
                    summary: str = (analysis or {}).get("summary") or ""

                    # 3) Relecture “vérité BDD” si nécessaire (concepts éventuellement stockés)
                    if not concepts:
                        try:
                            raw_concepts = row_dict.get("extracted_concepts")
                            if isinstance(raw_concepts, str):
                                concepts = json.loads(raw_concepts or "[]")
                            elif isinstance(raw_concepts, list):
                                concepts = raw_concepts
                        except Exception:
                            logger.warning("Session %s: 'extracted_concepts' illisible.", sid)

                    # 4) Étend avec le résumé (utile au RAG même si concepts maigres)
                    extended_concepts = list(
                        dict.fromkeys([c for c in concepts if c] + ([summary] if summary else []))
                    )

                    # 5) Plante si contenu
                    if extended_concepts:
                        await self._plant_concepts(
                            concepts=extended_concepts,
                            source_session_id=sid,
                            summary_text=(summary if summary else None),
                            user_id=user_id,
                        )
                        total_concepts += len(extended_concepts)
                        logger.info("Session %s: %d concept(s)/résumé(s) plantés.", sid, len(extended_concepts))
                    else:
                        logger.info("Session %s: aucun concept/résumé détecté (rien de planté).", sid)

                    # 6) IMPORTANT: on consolide la session dans tous les cas
                    consolidated_ids.append(sid)

                except Exception as e:
                    logger.error("Erreur pendant consolidation de %s: %s", sid, e, exc_info=True)

            if consolidated_ids:
                await dbq.mark_sessions_as_consolidated(self.db, consolidated_ids)
                logger.info("Sessions consolidées: %s", consolidated_ids)

            await self._decay_knowledge()

            return {
                "status": "success",
                "message": "Ronde terminée.",
                "consolidated_sessions": len(consolidated_ids),
                "new_concepts": total_concepts
            }
        except Exception as e:
            logger.critical("Échec critique de la ronde du jardinier: %s", e, exc_info=True)
            return {"status": "error", "message": str(e)}

    # ------------------------------------------------------------------ #
    # Implémentation
    # ------------------------------------------------------------------ #
    def _collection_existing_texts(self, collection) -> Set[str]:
        """
        Récupère l'ensemble des 'documents' déjà présents dans une collection Chroma.
        On tolère les structures [List[str]] ou [str] selon l'implémentation.
        """
        try:
            data = collection.get(include=["documents"])
            docs = data.get("documents") or []
            # Flatten soft
            flat: List[str] = []
            for d in docs:
                if isinstance(d, list):
                    flat.extend([x for x in d if isinstance(x, str)])
                elif isinstance(d, str):
                    flat.append(d)
            return set(flat)
        except Exception as e:
            logger.warning("Impossible de lister les documents existants (dedup) : %s", e)
            return set()

    async def _plant_concepts(
        self,
        concepts: List[str],
        source_session_id: str,
        summary_text: Optional[str] = None,
        user_id: Optional[str] = None,
    ):
        # Dédup inter-collections (knowledge + documents)
        existing_texts = self._collection_existing_texts(self.knowledge_collection)
        existing_texts |= self._collection_existing_texts(self.document_collection)

        seen_local: Set[str] = set()
        items: List[Dict[str, Any]] = []
        sql_payloads: List[Dict[str, Any]] = []

        for concept_text in concepts:
            concept_text = (concept_text or "").strip()
            if not concept_text:
                continue
            if concept_text in seen_local:
                continue
            if concept_text in existing_texts:
                # déjà présent dans au moins une collection, on saute
                continue

            seen_local.add(concept_text)

            cid = str(uuid.uuid4())
            role = "summary" if (summary_text and concept_text == summary_text) else "concept"

            # 1) SQL (index sémantique)
            sql_payloads.append({
                "id": cid,
                "concept": concept_text,
                "description": f"Concept extrait de la session {source_session_id}",
                "categories": [],
                "vector_id": cid
            })

            # 2) Vector items (connaissances + documents)
            meta = {
                "source_session_id": source_session_id,
                "user_id": user_id,
                "kind": "memory",
                "role": role,  # utile pour le RAG si besoin
                "concept_text": concept_text,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            items.append({"id": cid, "text": concept_text, "metadata": meta})

        if not items:
            logger.info("Aucun nouvel item à vectoriser (tout était déjà présent).")
            return

        # Upsert SQL d'abord (pour garder une trace indexée)
        for payload in sql_payloads:
            await dbq.upsert_knowledge_concept(self.db, payload)

        # Ajout dans la collection "mémoire" puis "documents"
        self.vector_service.add_items(self.knowledge_collection, items)
        self.vector_service.add_items(self.document_collection, items)
        logger.info("%d concept(s)/résumé(s) vectorisés (knowledge + documents).", len(items))

    async def _decay_knowledge(self):
        # Stratégie future (décroissance). No-op pour l'instant.
        logger.debug("Décroissance: noop.")
