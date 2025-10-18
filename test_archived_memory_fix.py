#!/usr/bin/env python3
"""
Script de validation du fix de récupération mémoire archivée.

Ce script teste que:
1. Les concepts legacy (sans agent_id) sont bien récupérés
2. Le filtrage permissif fonctionne correctement
3. Anima peut accéder aux souvenirs archivés
"""

import asyncio
import sys
import os
from pathlib import Path

# Ajouter src au path
SRC_DIR = Path(__file__).resolve().parent / "src"
sys.path.insert(0, str(SRC_DIR))

from backend.core.database.manager import DatabaseManager
from backend.features.memory.vector_service import VectorService
from backend.features.memory.memory_query_tool import MemoryQueryTool


async def main():
    print("=" * 70)
    print("TEST: Récupération souvenirs archivés - Fix validation")
    print("=" * 70)
    print()

    # 1. Initialiser les services
    print("[*] Initialisation des services...")
    db_manager = DatabaseManager("emergence.db")
    await db_manager.connect()

    persist_directory = os.getenv("EMERGENCE_VECTOR_DIR", "./data/vector_store")
    embed_model_name = os.getenv("EMBED_MODEL_NAME", "all-MiniLM-L6-v2")

    vector_service = VectorService(
        persist_directory=persist_directory,
        embed_model_name=embed_model_name
    )

    memory_tool = MemoryQueryTool(vector_service)
    print("[OK] Services initialises\n")

    # 2. Recuperer tous les utilisateurs qui ont des concepts
    print("[*] Recuperation des utilisateurs...")
    collection = vector_service.get_or_create_collection("emergence_knowledge")

    # Recuperer un echantillon de concepts pour voir les user_ids
    sample_results = collection.get(limit=100)

    if not sample_results or 'metadatas' not in sample_results or not sample_results['metadatas']:
        print("[!] Aucun concept trouve dans ChromaDB")
        print("    Il semble qu'il n'y ait pas encore de souvenirs consolides.")
        return

    user_ids = set()
    for meta in sample_results['metadatas']:
        if meta and 'user_id' in meta:
            user_ids.add(meta['user_id'])

    print(f"[OK] Trouve {len(user_ids)} utilisateur(s) avec des concepts\n")

    # 3. Tester pour chaque utilisateur
    for user_id in user_ids:
        print(f"[TEST] user_id: {user_id}")
        print("-" * 70)

        # Test avec agent Anima
        topics = await memory_tool.list_discussed_topics(
            user_id=user_id,
            timeframe="all",
            agent_id="anima"
        )

        if not topics:
            print(f"    [!] Aucun topic trouve pour cet utilisateur")
            continue

        # Analyser les resultats
        legacy_topics = [t for t in topics if not t.agent_id]
        anima_topics = [t for t in topics if t.agent_id and t.agent_id.lower() == "anima"]

        print(f"    Total topics recuperes: {len(topics)}")
        print(f"    Topics legacy (sans agent_id): {len(legacy_topics)}")
        print(f"    Topics Anima (avec agent_id='anima'): {len(anima_topics)}")
        print()

        # Afficher quelques exemples
        print("    Exemples de topics recuperes:")
        for i, topic in enumerate(topics[:5]):
            agent_label = topic.agent_id or "LEGACY"
            topic_label = getattr(topic, "topic", getattr(topic, "name", "???"))
            print(f"       {i+1}. {topic_label} (agent: {agent_label}, count: {topic.mention_count})")

        if len(topics) > 5:
            print(f"       ... et {len(topics) - 5} autres")

        print()

        # Validation du fix
        print("    Validation du fix:")
        if legacy_topics:
            print(f"       [OK] SUCCES: {len(legacy_topics)} concepts legacy recuperes")
            print("            Le filtrage PERMISSIF fonctionne!")
        else:
            print("       [!] Aucun concept legacy trouve")
            print("           Soit il n'y en a pas, soit le filtrage est trop strict")

        if anima_topics:
            print(f"       [OK] {len(anima_topics)} concepts Anima recuperes")

        print()

    # 4. Statistiques globales
    print("=" * 70)
    print("STATISTIQUES GLOBALES")
    print("=" * 70)

    total_concepts = collection.count()
    print(f"Total concepts dans ChromaDB: {total_concepts}")

    # Compter concepts par type d'agent_id
    all_results = collection.get(limit=total_concepts)
    agent_id_stats = {}

    for meta in all_results.get('metadatas', []):
        if meta:
            agent_id = meta.get('agent_id', 'LEGACY')
            agent_id_stats[agent_id] = agent_id_stats.get(agent_id, 0) + 1

    print("\nRépartition par agent_id:")
    for agent_id, count in sorted(agent_id_stats.items()):
        print(f"  - {agent_id}: {count} concepts")

    print()
    print("=" * 70)
    print("[OK] TEST TERMINE")
    print("=" * 70)

    await db_manager.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
