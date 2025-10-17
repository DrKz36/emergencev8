#!/usr/bin/env python3
"""
CLI Script: Consolidate Archived Threads to LTM

This script consolidates all archived threads that haven't been consolidated yet
into Long-Term Memory (LTM). It's designed to be run:
1. As a one-time migration for existing archived threads
2. Periodically as a maintenance task
3. Manually when needed

Usage:
    python -m backend.cli.consolidate_archived_threads [OPTIONS]

Options:
    --user-id TEXT          Consolidate only for specific user (optional)
    --limit INTEGER         Max number of threads to process (default: no limit)
    --force                 Reconsolidate even if already consolidated
    --dry-run               Show what would be done without actually doing it
    --verbose              Show detailed progress

Examples:
    # Consolidate all unconsolidated archived threads
    python -m backend.cli.consolidate_archived_threads

    # Consolidate for specific user with verbose output
    python -m backend.cli.consolidate_archived_threads --user-id user123 --verbose

    # Dry run to see what would happen
    python -m backend.cli.consolidate_archived_threads --dry-run --verbose

    # Force reconsolidation of all archived threads (use with caution)
    python -m backend.cli.consolidate_archived_threads --force --limit 10
"""

import asyncio
import logging
import sys
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

import click

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def get_unconsolidated_archived_threads(
    db_manager,
    user_id: Optional[str] = None,
    limit: Optional[int] = None,
    force: bool = False
) -> List[Dict[str, Any]]:
    """
    Fetch archived threads that haven't been consolidated yet.

    Args:
        db_manager: Database manager instance
        user_id: Optional user ID to filter threads
        limit: Optional limit on number of threads
        force: If True, include already consolidated threads

    Returns:
        List of thread dictionaries
    """
    # Build query
    query = """
        SELECT id, session_id, user_id, type, title, archived_at, consolidated_at, message_count
        FROM threads
        WHERE archived = 1
    """

    params = []

    if not force:
        query += " AND consolidated_at IS NULL"

    if user_id:
        query += " AND user_id = ?"
        params.append(user_id)

    query += " ORDER BY archived_at DESC"

    if limit:
        query += " LIMIT ?"
        params.append(limit)

    rows = await db_manager.fetch_all(query, tuple(params) if params else ())
    return [dict(row) for row in rows]


async def consolidate_thread(
    gardener,
    thread: Dict[str, Any],
    verbose: bool = False
) -> Dict[str, Any]:
    """
    Consolidate a single thread using the MemoryGardener.

    Args:
        gardener: MemoryGardener instance
        thread: Thread dictionary
        verbose: Whether to show detailed output

    Returns:
        Result dictionary with status and stats
    """
    thread_id = thread['id']
    session_id = thread['session_id']
    user_id = thread['user_id']

    if verbose:
        logger.info(f"  Processing thread: {thread_id[:8]}... (messages: {thread.get('message_count', 0)})")

    try:
        result = await gardener._tend_single_thread(
            thread_id=thread_id,
            session_id=session_id,
            user_id=user_id
        )

        if verbose and result.get('status') == 'success':
            new_concepts = result.get('new_concepts', 0)
            logger.info(f"    ✓ Success: {new_concepts} concepts/items added to LTM")

        return result

    except Exception as e:
        logger.error(f"    ✗ Error consolidating thread {thread_id[:8]}...: {e}")
        return {
            'status': 'error',
            'message': str(e),
            'consolidated_sessions': 0,
            'new_concepts': 0
        }


async def run_consolidation(
    user_id: Optional[str] = None,
    limit: Optional[int] = None,
    force: bool = False,
    dry_run: bool = False,
    verbose: bool = False
):
    """
    Main consolidation logic.

    Args:
        user_id: Optional user ID filter
        limit: Optional limit on threads to process
        force: Whether to reconsolidate already consolidated threads
        dry_run: If True, don't actually consolidate
        verbose: Show detailed output
    """
    # Import here to avoid circular dependencies
    from backend.core.database.manager import DatabaseManager
    from backend.features.memory.gardener import MemoryGardener
    from backend.features.memory.vector_service import VectorService
    from backend.features.memory.analyzer import MemoryAnalyzer

    # Initialize services
    logger.info("Initializing services...")
    db_manager = DatabaseManager("emergence.db")
    await db_manager.connect()

    vector_service = VectorService()
    memory_analyzer = MemoryAnalyzer(db_manager=db_manager)

    gardener = MemoryGardener(
        db_manager=db_manager,
        vector_service=vector_service,
        memory_analyzer=memory_analyzer
    )

    # Fetch threads to consolidate
    logger.info("Fetching archived threads...")
    threads = await get_unconsolidated_archived_threads(
        db_manager,
        user_id=user_id,
        limit=limit,
        force=force
    )

    if not threads:
        logger.info("✓ No archived threads found that need consolidation")
        return

    logger.info(f"Found {len(threads)} archived thread(s) to consolidate")

    if dry_run:
        logger.info("\n=== DRY RUN MODE - No changes will be made ===\n")
        for i, thread in enumerate(threads, 1):
            logger.info(f"{i}. Thread {thread['id'][:8]}... ({thread.get('message_count', 0)} messages)")
            logger.info(f"   User: {thread.get('user_id', 'unknown')}")
            logger.info(f"   Archived: {thread.get('archived_at', 'unknown')}")
            if thread.get('consolidated_at'):
                logger.info(f"   Previously consolidated: {thread['consolidated_at']}")
        return

    # Consolidate threads
    logger.info(f"\nStarting consolidation of {len(threads)} thread(s)...\n")

    stats = {
        'total': len(threads),
        'success': 0,
        'skipped': 0,
        'errors': 0,
        'total_concepts': 0
    }

    start_time = datetime.now(timezone.utc)

    for i, thread in enumerate(threads, 1):
        logger.info(f"[{i}/{len(threads)}] Thread: {thread['id'][:8]}...")

        result = await consolidate_thread(gardener, thread, verbose=verbose)

        if result.get('status') == 'success':
            new_concepts = result.get('new_concepts', 0)
            if new_concepts > 0:
                stats['success'] += 1
                stats['total_concepts'] += new_concepts
            else:
                stats['skipped'] += 1
        else:
            stats['errors'] += 1

    end_time = datetime.now(timezone.utc)
    duration = (end_time - start_time).total_seconds()

    # Print summary
    logger.info("\n" + "=" * 60)
    logger.info("CONSOLIDATION SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total threads processed:    {stats['total']}")
    logger.info(f"Successfully consolidated:  {stats['success']}")
    logger.info(f"Skipped (no new items):     {stats['skipped']}")
    logger.info(f"Errors:                     {stats['errors']}")
    logger.info(f"Total concepts/items added: {stats['total_concepts']}")
    logger.info(f"Duration:                   {duration:.2f} seconds")
    logger.info("=" * 60)

    if stats['errors'] > 0:
        logger.warning(f"\n⚠️  {stats['errors']} thread(s) failed to consolidate. Check logs for details.")
    else:
        logger.info("\n✓ All threads consolidated successfully!")

    await db_manager.disconnect()


@click.command()
@click.option('--user-id', type=str, default=None, help='Consolidate only for specific user')
@click.option('--limit', type=int, default=None, help='Max number of threads to process')
@click.option('--force', is_flag=True, help='Reconsolidate even if already consolidated')
@click.option('--dry-run', is_flag=True, help='Show what would be done without actually doing it')
@click.option('--verbose', '-v', is_flag=True, help='Show detailed progress')
def main(user_id, limit, force, dry_run, verbose):
    """
    Consolidate archived threads to Long-Term Memory.

    This script processes archived conversation threads and extracts their concepts,
    preferences, and facts into the LTM for cross-session memory access.
    """
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        asyncio.run(run_consolidation(
            user_id=user_id,
            limit=limit,
            force=force,
            dry_run=dry_run,
            verbose=verbose
        ))
    except KeyboardInterrupt:
        logger.info("\n\nConsolidation interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n\nFatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
