#!/usr/bin/env python3
# src/backend/cli/backfill_agent_ids.py
# Sprint 4 Memory Refactoring - Backfill agent_id pour concepts legacy
#
# Objectif: Ajouter agent_id aux concepts ChromaDB qui n'en ont pas
# Stratégie: Inférence depuis thread_id source
#
# Usage:
#   python src/backend/cli/backfill_agent_ids.py --dry-run
#   python src/backend/cli/backfill_agent_ids.py --user-id <user_id>
#   python src/backend/cli/backfill_agent_ids.py --all

import asyncio
import logging
import argparse
from typing import Optional

from backend.features.memory.vector_service import VectorService
from backend.core.database.manager import DatabaseManager
from backend.core.database import queries

logger = logging.getLogger(__name__)


async def infer_agent_from_thread(db: DatabaseManager, thread_id: str) -> Optional[str]:
    """
    Infère agent_id depuis thread source.

    Args:
        db: DatabaseManager instance
        thread_id: ID du thread source

    Returns:
        agent_id inféré (anima par défaut)
    """
    try:
        thread = await queries.get_thread_any(db, thread_id, session_id=None, user_id=None)
        if thread:
            agent_id = thread.get('agent_id')
            if agent_id:
                return agent_id.lower()
        return 'anima'  # Défaut si pas d'agent_id dans thread
    except Exception as e:
        logger.warning(f"Failed to infer agent from thread {thread_id}: {e}")
        return 'anima'


async def backfill_missing_agent_ids(
    vector_service: VectorService,
    db: DatabaseManager,
    *,
    user_id: Optional[str] = None,
    dry_run: bool = False
) -> dict:
    """
    Backfill agent_id pour concepts sans agent_id.

    Args:
        vector_service: VectorService instance
        db: DatabaseManager instance
        user_id: User ID à traiter (None = tous)
        dry_run: Si True, simule sans modifier

    Returns:
        Dict avec statistiques (total, updated, skipped, errors)
    """
    collection = vector_service.get_or_create_collection("emergence_knowledge")

    # Récupérer tous concepts (on filtrera après)
    where = {"type": "concept"}
    if user_id:
        where = {"$and": [where, {"user_id": user_id}]}

    results = collection.get(
        where=where,
        include=["metadatas"]
    )

    concept_ids = results.get('ids', [])
    metadatas = results.get('metadatas', [])

    logger.info(f"Trouvé {len(concept_ids)} concepts à analyser")

    updated = 0
    skipped = 0
    errors = []

    for concept_id, meta in zip(concept_ids, metadatas):
        try:
            # Skip si agent_id déjà présent
            if meta.get('agent_id'):
                skipped += 1
                continue

            # Inférer depuis thread_ids
            thread_ids = meta.get('thread_ids', [])
            if not thread_ids:
                logger.debug(f"Concept {concept_id[:8]}... sans thread_ids, skip")
                skipped += 1
                continue

            # Prendre premier thread_id
            inferred_agent = await infer_agent_from_thread(db, thread_ids[0])

            logger.info(
                f"Concept {concept_id[:8]}... → agent_id inféré: {inferred_agent}"
            )

            if not dry_run:
                # Mettre à jour
                updated_meta = {**meta, 'agent_id': inferred_agent}
                collection.update(
                    ids=[concept_id],
                    metadatas=[updated_meta]
                )
                updated += 1
            else:
                logger.info(f"  [DRY-RUN] Aurait mis à jour avec agent_id={inferred_agent}")
                updated += 1

        except Exception as e:
            logger.error(f"Erreur traitement concept {concept_id[:8]}...: {e}", exc_info=True)
            errors.append({
                'concept_id': concept_id,
                'error': str(e)
            })

    # Rapport final
    logger.info(f"""
    ╔═══════════════════════════════════════╗
    ║  BACKFILL AGENT_ID TERMINÉ            ║
    ╠═══════════════════════════════════════╣
    ║  Total concepts: {len(concept_ids):4d}              ║
    ║  Updated:        {updated:4d}              ║
    ║  Skipped:        {skipped:4d}              ║
    ║  Errors:         {len(errors):4d}              ║
    ║  Dry-run:        {str(dry_run):5s}             ║
    ╚═══════════════════════════════════════╝
    """)

    if errors:
        logger.error(f"Erreurs détaillées:\n{errors}")

    return {
        'total': len(concept_ids),
        'updated': updated,
        'skipped': skipped,
        'errors': errors
    }


async def main():
    parser = argparse.ArgumentParser(
        description="Backfill agent_id pour concepts legacy"
    )
    parser.add_argument('--user-id', help="User ID à traiter")
    parser.add_argument('--all', action='store_true', help="Tous utilisateurs")
    parser.add_argument('--dry-run', action='store_true', help="Simulation sans modification")
    parser.add_argument('--db', default='emergence.db', help="Chemin DB SQLite")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Setup
    db = DatabaseManager(args.db)
    await db.connect()

    vector_service = VectorService()

    # Validation args
    user_id = None if args.all else args.user_id
    if not user_id and not args.all:
        logger.error("--user-id ou --all requis")
        await db.close()
        return 1

    # Exécution
    await backfill_missing_agent_ids(
        vector_service, db,
        user_id=user_id,
        dry_run=args.dry_run
    )

    await db.close()
    return 0


if __name__ == '__main__':
    exit(asyncio.run(main()))
