#!/usr/bin/env python3
"""
Migration script: Enrich existing concept metadata in ChromaDB
Adds: first_mentioned_at, last_mentioned_at, mention_count, thread_ids, message_id

Usage:
    python scripts/migrate_concept_metadata.py
"""

import sys
import os
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

# Import après sys.path modification
from backend.features.memory.vector_service import VectorService  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

COLLECTION_NAME = "emergence_knowledge"


def migrate_concept_metadata():
    """
    Migrate existing concepts to add temporal tracking metadata.
    """
    logger.info(f"🔄 Starting metadata migration for collection: {COLLECTION_NAME}")

    # Configuration par défaut alignée avec le backend
    persist_directory = os.getenv("EMERGENCE_VECTOR_DIR", "./src/backend/data/vector_store")
    embed_model_name = os.getenv("EMBED_MODEL_NAME", "all-MiniLM-L6-v2")

    vector_service = VectorService(
        persist_directory=persist_directory,
        embed_model_name=embed_model_name
    )
    collection = vector_service.get_or_create_collection(COLLECTION_NAME)

    # Get all concepts
    try:
        result = collection.get(
            where={"type": "concept"},
            include=["metadatas"]
        )
    except Exception as e:
        logger.error(f"❌ Failed to fetch concepts: {e}")
        return

    if not result or not result.get("ids"):
        logger.warning("⚠️  No concepts found in collection.")
        return

    ids = result["ids"]
    metadatas = result["metadatas"]

    logger.info(f"📊 Found {len(ids)} concepts to migrate")

    migrated_count = 0
    skipped_count = 0
    error_count = 0

    for i, (vector_id, meta) in enumerate(zip(ids, metadatas)):
        try:
            # Skip if already migrated (has first_mentioned_at)
            if meta.get("first_mentioned_at"):
                skipped_count += 1
                if i % 100 == 0:
                    logger.info(f"⏭️  [{i}/{len(ids)}] Skipping already migrated concept: {vector_id}")
                continue

            # Enrich metadata
            updated_meta = dict(meta)
            created_at = meta.get("created_at")

            # Use created_at as fallback for temporal fields
            updated_meta["first_mentioned_at"] = created_at
            updated_meta["last_mentioned_at"] = created_at
            updated_meta["mention_count"] = 1
            updated_meta["thread_ids"] = []  # Cannot retroactively determine
            updated_meta["message_id"] = None
            updated_meta["thread_id"] = None

            # Update in ChromaDB
            collection.update(
                ids=[vector_id],
                metadatas=[updated_meta]
            )

            migrated_count += 1

            if (i + 1) % 100 == 0:
                logger.info(f"✅ [{i + 1}/{len(ids)}] Migrated {migrated_count} concepts")

        except Exception as e:
            error_count += 1
            logger.warning(f"⚠️  Failed to migrate concept {vector_id}: {e}")

    logger.info(f"""
    ✨ Migration complete!
    ─────────────────────────────
    Total concepts:     {len(ids)}
    Migrated:           {migrated_count}
    Skipped (existing): {skipped_count}
    Errors:             {error_count}
    """)


if __name__ == "__main__":
    try:
        migrate_concept_metadata()
    except KeyboardInterrupt:
        logger.warning("\n⚠️  Migration interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}", exc_info=True)
        sys.exit(1)
