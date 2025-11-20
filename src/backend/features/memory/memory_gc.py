# src/backend/features/memory/memory_gc.py
# V1.0 - Garbage Collector pour mémoire vectorielle
#
# Objectif: Archiver automatiquement les entrées inactives > gc_inactive_days
# pour éviter saturation de la mémoire vectorielle.
#
# Stratégie:
# - Déplace entrées inactives vers collection "emergence_knowledge_archived"
# - Garde métadonnées originales (pour éventuelle restauration)
# - Émission métriques Prometheus
#
# Date création: 2025-10-21

import logging
from typing import List, Dict, Any, Optional, cast
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

# Prometheus metrics
try:
    from prometheus_client import Counter, Gauge, REGISTRY

    def _get_gc_counter() -> Counter:
        try:
            return Counter(
                "memory_gc_entries_archived_total",
                "Nombre entrées archivées par GC",
                ["collection"],
                registry=REGISTRY,
            )
        except ValueError:
            existing = getattr(REGISTRY, "_names_to_collectors", {}).get(
                "memory_gc_entries_archived_total"
            )
            if existing is None:
                raise
            return cast(Counter, existing)

    def _get_gc_gauge() -> Gauge:
        try:
            return Gauge(
                "memory_gc_last_run_timestamp",
                "Timestamp dernière exécution GC",
                ["collection"],
                registry=REGISTRY,
            )
        except ValueError:
            existing = getattr(REGISTRY, "_names_to_collectors", {}).get(
                "memory_gc_last_run_timestamp"
            )
            if existing is None:
                raise
            return cast(Gauge, existing)

    MEMORY_GC_ARCHIVED = _get_gc_counter()
    MEMORY_GC_LAST_RUN = _get_gc_gauge()
    PROMETHEUS_AVAILABLE = True

except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.debug("[MemoryGC] Prometheus client non disponible")


class MemoryGarbageCollector:
    """
    Garbage collector pour mémoire vectorielle.

    Fonctionnalités:
    - Archive entrées inactives > gc_inactive_days
    - Déplace vers collection "_archived"
    - Garde métadonnées pour restauration
    - Métriques Prometheus
    """

    def __init__(self, vector_service: Any, gc_inactive_days: int = 180) -> None:
        """
        Initialize MemoryGarbageCollector.

        Args:
            vector_service: VectorService instance
            gc_inactive_days: Nombre de jours d'inactivité avant archivage (défaut: 180)
        """
        self.vector_service = vector_service
        self.gc_inactive_days = gc_inactive_days
        logger.info(f"[MemoryGC] Initialisé avec gc_inactive_days={gc_inactive_days}")

    async def run_gc(
        self, collection_name: str = "emergence_knowledge", dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Exécute garbage collection sur la collection.

        Args:
            collection_name: Nom de la collection à nettoyer
            dry_run: Si True, simule sans archiver (défaut: False)

        Returns:
            Statistiques GC:
            {
                "collection": "emergence_knowledge",
                "candidates_found": 42,
                "entries_archived": 38,
                "errors": 4,
                "cutoff_date": "2025-04-24T00:00:00+00:00",
                "dry_run": False
            }
        """
        start_time = datetime.now(timezone.utc)
        logger.info(
            f"[MemoryGC] Démarrage GC sur '{collection_name}' "
            f"(gc_inactive_days={self.gc_inactive_days}, dry_run={dry_run})"
        )

        collection = self.vector_service.get_or_create_collection(collection_name)
        if not collection:
            logger.error(f"[MemoryGC] Collection '{collection_name}' introuvable")
            return {
                "collection": collection_name,
                "candidates_found": 0,
                "entries_archived": 0,
                "errors": 1,
                "dry_run": dry_run,
            }

        # Calculer cutoff date
        cutoff_date = start_time - timedelta(days=self.gc_inactive_days)
        cutoff_iso = cutoff_date.isoformat()

        # Récupérer tous les documents de la collection
        # (ChromaDB ne supporte pas les filtres temporels complexes dans where)
        try:
            all_entries = collection.get(
                include=["documents", "metadatas", "embeddings"]
            )
        except Exception as e:
            logger.error(
                f"[MemoryGC] Erreur récupération collection: {e}", exc_info=True
            )
            return {
                "collection": collection_name,
                "candidates_found": 0,
                "entries_archived": 0,
                "errors": 1,
                "dry_run": dry_run,
            }

        if not all_entries or not all_entries.get("ids"):
            logger.info(f"[MemoryGC] Collection '{collection_name}' vide")
            return {
                "collection": collection_name,
                "candidates_found": 0,
                "entries_archived": 0,
                "errors": 0,
                "cutoff_date": cutoff_iso,
                "dry_run": dry_run,
            }

        # Filtrer entrées inactives
        candidates = self._find_inactive_entries(all_entries, cutoff_date)

        logger.info(
            f"[MemoryGC] {len(candidates)} candidats trouvés "
            f"(inactivité > {self.gc_inactive_days}j)"
        )

        if dry_run:
            logger.info("[MemoryGC] Mode dry_run activé - aucune archive")
            return {
                "collection": collection_name,
                "candidates_found": len(candidates),
                "entries_archived": 0,
                "errors": 0,
                "cutoff_date": cutoff_iso,
                "dry_run": True,
            }

        # Archiver candidats
        archived_count = 0
        error_count = 0

        for candidate in candidates:
            try:
                self._archive_entry(
                    collection_name=collection_name,
                    entry_id=candidate["id"],
                    document=candidate["document"],
                    metadata=candidate["metadata"],
                    embedding=candidate["embedding"],
                )
                archived_count += 1
            except Exception as e:
                logger.warning(f"[MemoryGC] Erreur archivage {candidate['id']}: {e}")
                error_count += 1

        # Métriques Prometheus
        if PROMETHEUS_AVAILABLE:
            MEMORY_GC_ARCHIVED.labels(collection=collection_name).inc(archived_count)
            MEMORY_GC_LAST_RUN.labels(collection=collection_name).set(
                datetime.now(timezone.utc).timestamp()
            )

        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        logger.info(
            f"[MemoryGC] Terminé en {duration:.2f}s : "
            f"{archived_count} archivés, {error_count} erreurs"
        )

        return {
            "collection": collection_name,
            "candidates_found": len(candidates),
            "entries_archived": archived_count,
            "errors": error_count,
            "cutoff_date": cutoff_iso,
            "dry_run": False,
            "duration_seconds": duration,
        }

    def _find_inactive_entries(
        self, all_entries: Dict[str, Any], cutoff_date: datetime
    ) -> List[Dict[str, Any]]:
        """
        Filtre entrées inactives depuis cutoff_date.

        Args:
            all_entries: Résultat collection.get()
            cutoff_date: Date seuil

        Returns:
            Liste candidats archivage
        """
        candidates = []

        ids = all_entries.get("ids", [])
        documents = all_entries.get("documents", [])
        metadatas = all_entries.get("metadatas", [])
        embeddings = all_entries.get("embeddings", [])

        for i, entry_id in enumerate(ids):
            try:
                meta = metadatas[i] if i < len(metadatas) else {}
                if not isinstance(meta, dict):
                    meta = {}

                # Récupérer last_used_at (prioritaire) ou created_at
                last_used_str = meta.get("last_used_at") or meta.get("created_at")
                if not last_used_str:
                    # Pas de date → considéré comme ancien
                    logger.debug(f"[MemoryGC] {entry_id}: pas de date → candidat")
                    candidates.append(
                        {
                            "id": entry_id,
                            "document": documents[i] if i < len(documents) else "",
                            "metadata": meta,
                            "embedding": embeddings[i] if i < len(embeddings) else None,
                        }
                    )
                    continue

                # Parser date
                try:
                    last_used = datetime.fromisoformat(
                        last_used_str.replace("Z", "+00:00")
                    )
                    if last_used.tzinfo is None:
                        last_used = last_used.replace(tzinfo=timezone.utc)
                except Exception:
                    logger.debug(
                        f"[MemoryGC] {entry_id}: date invalide '{last_used_str}' → candidat"
                    )
                    candidates.append(
                        {
                            "id": entry_id,
                            "document": documents[i] if i < len(documents) else "",
                            "metadata": meta,
                            "embedding": embeddings[i] if i < len(embeddings) else None,
                        }
                    )
                    continue

                # Vérifier inactivité
                if last_used < cutoff_date:
                    delta_days = (datetime.now(timezone.utc) - last_used).days
                    logger.debug(
                        f"[MemoryGC] {entry_id}: inactif depuis {delta_days}j → candidat"
                    )
                    candidates.append(
                        {
                            "id": entry_id,
                            "document": documents[i] if i < len(documents) else "",
                            "metadata": meta,
                            "embedding": embeddings[i] if i < len(embeddings) else None,
                        }
                    )

            except Exception as e:
                logger.warning(f"[MemoryGC] Erreur parsing {entry_id}: {e}")
                continue

        return candidates

    def _archive_entry(
        self,
        collection_name: str,
        entry_id: str,
        document: str,
        metadata: Dict[str, Any],
        embedding: Optional[List[float]],
    ) -> None:
        """
        Archive une entrée dans collection "_archived".

        Args:
            collection_name: Collection source
            entry_id: ID de l'entrée
            document: Texte du document
            metadata: Métadonnées
            embedding: Vecteur d'embedding
        """
        archived_collection_name = f"{collection_name}_archived"
        archived_collection = self.vector_service.get_or_create_collection(
            archived_collection_name
        )

        # Enrichir métadonnées avec info archivage
        archived_meta = dict(metadata)
        archived_meta["archived_at"] = datetime.now(timezone.utc).isoformat()
        archived_meta["original_collection"] = collection_name
        archived_meta["archived_by"] = "MemoryGarbageCollector"

        # Ajouter à collection archivée
        archived_collection.add(
            ids=[entry_id],
            documents=[document],
            metadatas=[archived_meta],
            embeddings=[embedding] if embedding else None,
        )

        # Supprimer de collection source
        source_collection = self.vector_service.get_or_create_collection(
            collection_name
        )
        source_collection.delete(ids=[entry_id])

        logger.debug(
            f"[MemoryGC] {entry_id} archivé : "
            f"{collection_name} → {archived_collection_name}"
        )

    async def restore_entry(
        self,
        entry_id: str,
        archived_collection_name: str = "emergence_knowledge_archived",
    ) -> bool:
        """
        Restaure une entrée archivée vers la collection originale.

        Args:
            entry_id: ID de l'entrée à restaurer
            archived_collection_name: Collection archivée source

        Returns:
            True si restauré, False sinon
        """
        try:
            archived_collection = self.vector_service.get_or_create_collection(
                archived_collection_name
            )

            # Récupérer entrée
            result = archived_collection.get(
                ids=[entry_id], include=["documents", "metadatas", "embeddings"]
            )

            if not result or not result.get("ids"):
                logger.warning(
                    f"[MemoryGC] Entrée {entry_id} introuvable dans archives"
                )
                return False

            document = result["documents"][0]
            metadata = result["metadatas"][0]
            embedding = result["embeddings"][0] if result.get("embeddings") else None

            # Récupérer collection originale
            original_collection_name = metadata.get(
                "original_collection", "emergence_knowledge"
            )
            original_collection = self.vector_service.get_or_create_collection(
                original_collection_name
            )

            # Nettoyer métadonnées archivage
            restored_meta = {
                k: v
                for k, v in metadata.items()
                if k not in ["archived_at", "original_collection", "archived_by"]
            }
            restored_meta["restored_at"] = datetime.now(timezone.utc).isoformat()

            # Ajouter à collection originale
            original_collection.add(
                ids=[entry_id],
                documents=[document],
                metadatas=[restored_meta],
                embeddings=[embedding] if embedding else None,
            )

            # Supprimer des archives
            archived_collection.delete(ids=[entry_id])

            logger.info(
                f"[MemoryGC] {entry_id} restauré : "
                f"{archived_collection_name} → {original_collection_name}"
            )
            return True

        except Exception as e:
            logger.error(
                f"[MemoryGC] Erreur restauration {entry_id}: {e}", exc_info=True
            )
            return False
