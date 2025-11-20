#!/usr/bin/env python3
"""
Script manuel pour consolider les threads archivés dans ChromaDB
"""

import asyncio
import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent / "src"
sys.path.insert(0, str(SRC_DIR))

from backend.core.database.manager import DatabaseManager
from backend.features.memory.vector_service import VectorService
from backend.features.memory.analyzer import MemoryAnalyzer
from backend.features.memory.gardener import MemoryGardener


async def main():
    print("=" * 70)
    print("CONSOLIDATION MANUELLE DES THREADS ARCHIVES")
    print("=" * 70)
    print()

    # Init services
    db_manager = DatabaseManager("backend/data/db/emergence_v7.db")
    await db_manager.connect()

    # Utiliser le même chemin que le backend (depuis src/)
    vector_service = VectorService(
        persist_directory="./data/vector_store", embed_model_name="all-MiniLM-L6-v2"
    )

    # Activer le mode offline pour permettre l'analyse sans ChatService
    # En mode offline, l'analyse sera heuristique mais fonctionnera
    memory_analyzer = MemoryAnalyzer(db_manager=db_manager, enable_offline_mode=True)

    gardener = MemoryGardener(
        db_manager=db_manager,
        vector_service=vector_service,
        memory_analyzer=memory_analyzer,
    )

    # Récupérer les threads archivés
    threads = await db_manager.fetch_all("""
        SELECT id, user_id, session_id, title, message_count
        FROM threads
        WHERE archived = 1
        ORDER BY archived_at DESC
    """)

    print(f"Trouve {len(threads)} threads archives a consolider\n")

    # Consolider chaque thread
    for i, thread in enumerate(threads, 1):
        thread_id = thread[0]
        user_id = thread[1]
        session_id = thread[2]
        title = thread[3] or "Sans titre"
        msg_count = thread[4]

        print(f"[{i}/{len(threads)}] Consolidation: '{title[:40]}' ({msg_count} msgs)")
        print(f"            Thread: {thread_id[:12]}...")

        try:
            # Consolider le thread
            await gardener._tend_single_thread(
                thread_id=thread_id, session_id=session_id, user_id=user_id
            )
            print("            [OK] Consolide!")

        except Exception as e:
            print(f"            [ERREUR] {e}")

        print()

    print("=" * 70)
    print("CONSOLIDATION TERMINEE")
    print("=" * 70)
    print()

    # Vérifier combien de concepts ont été créés
    collection = vector_service.get_or_create_collection("emergence_knowledge")
    concept_count = collection.count()
    print(f"Total concepts dans ChromaDB: {concept_count}")
    print()

    await db_manager.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
