#!/usr/bin/env python3
"""
Test rapide: Vérifie que le contexte mémoire vide est bien passé au LLM
"""

import asyncio
import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent / "src"
sys.path.insert(0, str(SRC_DIR))

from backend.features.memory.memory_query_tool import MemoryQueryTool
from backend.features.memory.vector_service import VectorService


async def main():
    print("=" * 70)
    print("TEST: Verification fonction list_discussed_topics")
    print("=" * 70)
    print()

    # Init services
    vector_service = VectorService(
        persist_directory="./data/vector_store", embed_model_name="all-MiniLM-L6-v2"
    )

    memory_tool = MemoryQueryTool(vector_service)

    # Simuler une requete pour un user sans historique
    user_id = "test_user_123"
    agent_id = "anima"

    print(f"Test pour user: {user_id}")
    print(f"Agent: {agent_id}")
    print()

    # Appeler list_discussed_topics
    topics = await memory_tool.list_discussed_topics(
        user_id=user_id, timeframe="all", agent_id=agent_id
    )

    print("-" * 70)
    print("RESULTATS:")
    print("-" * 70)
    print(f"Nombre de topics: {len(topics)}")
    print()

    if len(topics) == 0:
        print("[OK] Aucun topic trouve (attendu car base vide)")
        print()
        print("Ce resultat DEVRAIT declencher le message d'alerte:")
        print('  "⚠️ CONTEXTE VIDE: Aucune conversation passee..."')
        print()
        print("Et Anima DEVRAIT repondre:")
        print('  "Je n\'ai pas acces a nos conversations passees..."')
        print()
        print("Si elle invente des dates/sujets, c'est un probleme de prompt LLM!")
    else:
        print(f"[INFO] {len(topics)} topics trouves:")
        for topic in topics:
            print(f"  - {topic.format_natural_fr()}")

    print()
    print("-" * 70)


if __name__ == "__main__":
    asyncio.run(main())
