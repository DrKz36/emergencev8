#!/usr/bin/env python3
"""
Script de migration ponctuel: Consolide tous threads archivés non traités (Sprint 2).

Ce script parcourt tous les threads archivés et les consolide en LTM (ChromaDB)
via le MemoryGardener. Il marque ensuite chaque thread avec consolidated_at.

Usage:
    python src/backend/cli/consolidate_all_archives.py --user-id <user_id>
    python src/backend/cli/consolidate_all_archives.py --all  # Admin only
    python src/backend/cli/consolidate_all_archives.py --all --force  # Reconsolider tout
"""
import asyncio
import argparse
import logging
from datetime import datetime, timezone
from typing import Optional, Any

import sys
from pathlib import Path

# Ajouter racine projet au sys.path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.core.database.manager import DatabaseManager  # noqa: E402
from backend.features.memory.gardener import MemoryGardener  # noqa: E402
from backend.features.memory.vector_service import VectorService  # noqa: E402
from backend.features.memory.analyzer import MemoryAnalyzer  # noqa: E402

logger = logging.getLogger(__name__)


async def is_already_consolidated(vector_service, thread_id: str) -> bool:
    """
    Vérifie si thread déjà consolidé en cherchant concepts dans ChromaDB.

    Args:
        vector_service: Service vectoriel ChromaDB
        thread_id: ID du thread à vérifier

    Returns:
        True si au moins un concept existe pour ce thread
    """
    try:
        collection = vector_service.get_or_create_collection("emergence_knowledge")
        result = collection.get(
            where={"thread_id": thread_id},
            limit=1
        )
        ids = result.get("ids") or []
        if isinstance(ids, list) and len(ids) > 0:
            if isinstance(ids[0], list):
                return len(ids[0]) > 0
            return True
        return False
    except Exception as e:
        logger.warning(f"Check consolidation failed for {thread_id}: {e}")
        return False


async def consolidate_all_archives(
    db: DatabaseManager,
    gardener: MemoryGardener,
    vector_service: VectorService,
    *,
    user_id: Optional[str] = None,
    limit: int = 1000,
    force: bool = False
):
    """
    Consolide tous threads archivés non traités.

    Args:
        db: DatabaseManager
        gardener: MemoryGardener pour consolidation
        vector_service: VectorService pour vérifier consolidation
        user_id: Filtrer par utilisateur (None = tous)
        limit: Limite de threads à traiter
        force: Forcer reconsolidation même si déjà fait
    """

    # Récupérer threads archivés
    logger.info(f"Récupération threads archivés (user_id={user_id}, limit={limit})...")

    # Requête SQL pour threads archivés
    where_clauses = ["archived = 1"]
    params: list[Any] = []

    if user_id:
        where_clauses.append("user_id = ?")
        params.append(user_id)

    query = f"""
        SELECT * FROM threads
        WHERE {' AND '.join(where_clauses)}
        ORDER BY created_at DESC
        LIMIT ?
    """
    params.append(limit)

    threads_raw = await db.fetch_all(query, tuple(params))
    threads: list[dict[str, Any]] = [dict(t) for t in threads_raw]

    logger.info(f"Trouvé {len(threads)} thread(s) archivé(s)")

    consolidated = 0
    skipped = 0
    errors = []

    for i, thread in enumerate(threads, 1):
        thread_id = thread.get('id')
        if not thread_id:
            continue

        logger.info(f"[{i}/{len(threads)}] Processing thread {thread_id[:8]}...")

        try:
            # Vérifier si déjà consolidé
            if not force and await is_already_consolidated(vector_service, thread_id):
                logger.info("  -> Déjà consolidé, skip")
                skipped += 1
                continue

            # Consolider
            result = await gardener._tend_single_thread(
                thread_id=thread_id,
                session_id=thread.get('session_id'),
                user_id=thread.get('user_id')
            )

            new_concepts = result.get('new_concepts', 0)
            if new_concepts > 0:
                logger.info(f"  -> Consolidé: {new_concepts} concepts")
                consolidated += 1

                # Marquer comme consolidé
                await db.execute(
                    "UPDATE threads SET consolidated_at = ? WHERE id = ?",
                    (datetime.now(timezone.utc).isoformat(), thread_id),
                    commit=True
                )
            else:
                logger.info("  -> Aucun concept extrait")
                skipped += 1

        except Exception as e:
            logger.error(f"  -> ERREUR: {e}", exc_info=True)
            errors.append({
                'thread_id': thread_id,
                'error': str(e)
            })

    # Rapport final
    logger.info(f"""
    ╔═══════════════════════════════════════╗
    ║  CONSOLIDATION BATCH TERMINÉE         ║
    ╠═══════════════════════════════════════╣
    ║  Total threads: {len(threads):4d}               ║
    ║  Consolidés:    {consolidated:4d}               ║
    ║  Skipped:       {skipped:4d}               ║
    ║  Erreurs:       {len(errors):4d}               ║
    ╚═══════════════════════════════════════╝
    """)

    if errors:
        logger.error(f"Erreurs détaillées:\n{errors}")

    return {
        'total': len(threads),
        'consolidated': consolidated,
        'skipped': skipped,
        'errors': errors
    }


async def main():
    parser = argparse.ArgumentParser(description="Consolide threads archivés en LTM")
    parser.add_argument('--user-id', help="User ID à traiter (optionnel)")
    parser.add_argument('--all', action='store_true', help="Tous utilisateurs (admin)")
    parser.add_argument('--limit', type=int, default=1000, help="Limite threads (défaut: 1000)")
    parser.add_argument('--force', action='store_true', help="Forcer reconsolidation")
    parser.add_argument('--db', default='emergence.db', help="Chemin DB (défaut: emergence.db)")
    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    # Setup database
    db = DatabaseManager(args.db)
    await db.connect()
    logger.info(f"Connected to {args.db}")

    # Setup vector service + analyzer + gardener
    vector_service = VectorService()
    analyzer = MemoryAnalyzer(db, enable_offline_mode=True)
    gardener = MemoryGardener(db, vector_service, analyzer)

    # Exécution
    user_id = None if args.all else args.user_id
    if not user_id and not args.all:
        logger.error("❌ --user-id ou --all requis")
        return 1

    await consolidate_all_archives(
        db, gardener, vector_service,
        user_id=user_id,
        limit=args.limit,
        force=args.force
    )

    await db.close()
    logger.info("Database connection closed")
    return 0


if __name__ == '__main__':
    exit(asyncio.run(main()))
