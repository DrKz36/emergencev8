#!/usr/bin/env python3
"""
Script de test pour vérifier l'isolation des données utilisateurs.
"""

import asyncio
import sys
from pathlib import Path

# Ajouter le chemin du backend
sys.path.insert(0, str(Path(__file__).parent / "src" / "backend"))

from core.database.manager import DatabaseManager
from core.database import queries as db_queries


async def test_data_isolation():
    """Teste l'isolation des données entre utilisateurs."""
    print("Test d'isolation des donnees utilisateurs\n")

    # Initialiser le gestionnaire de base de données
    db_path = Path(__file__).parent / "data" / "emergence.db"
    db_manager = DatabaseManager(str(db_path))
    await db_manager.connect()

    try:
        # Test 1: get_all_documents sans user_id devrait échouer
        print("Test 1: get_all_documents sans user_id")
        try:
            docs = await db_queries.get_all_documents(db_manager)
            print("ECHEC: get_all_documents a retourne des resultats sans user_id")
            return False
        except ValueError as e:
            print(f"OK: {e}\n")

        # Test 2: get_document_by_id sans user_id devrait echouer
        print("Test 2: get_document_by_id sans user_id")
        try:
            doc = await db_queries.get_document_by_id(db_manager, 1)
            print("ECHEC: get_document_by_id a retourne un resultat sans user_id")
            return False
        except ValueError as e:
            print(f"OK: {e}\n")

        # Test 3: get_threads sans user_id devrait echouer
        print("Test 3: get_threads sans user_id")
        try:
            threads = await db_queries.get_threads(db_manager, session_id="test")
            print("ECHEC: get_threads a retourne des resultats sans user_id")
            return False
        except ValueError as e:
            print(f"OK: {e}\n")

        # Test 4: get_thread sans user_id devrait echouer
        print("Test 4: get_thread sans user_id")
        try:
            thread = await db_queries.get_thread(db_manager, "test_id", "test_session")
            print("ECHEC: get_thread a retourne un resultat sans user_id")
            return False
        except ValueError as e:
            print(f"OK: {e}\n")

        # Test 5: get_messages sans user_id devrait echouer
        print("Test 5: get_messages sans user_id")
        try:
            messages = await db_queries.get_messages(db_manager, "test_thread")
            print("ECHEC: get_messages a retourne des resultats sans user_id")
            return False
        except ValueError as e:
            print(f"OK: {e}\n")

        # Test 6: get_thread_docs sans user_id devrait echouer
        print("Test 6: get_thread_docs sans user_id")
        try:
            docs = await db_queries.get_thread_docs(db_manager, "test_thread")
            print("ECHEC: get_thread_docs a retourne des resultats sans user_id")
            return False
        except ValueError as e:
            print(f"OK: {e}\n")

        # Test 7: get_costs_summary sans user_id devrait echouer
        print("Test 7: get_costs_summary sans user_id")
        try:
            costs = await db_queries.get_costs_summary(db_manager)
            print("ECHEC: get_costs_summary a retourne des resultats sans user_id")
            return False
        except ValueError as e:
            print(f"OK: {e}\n")

        # Test 8: get_messages_by_period sans user_id devrait echouer
        print("Test 8: get_messages_by_period sans user_id")
        try:
            messages = await db_queries.get_messages_by_period(db_manager)
            print("ECHEC: get_messages_by_period a retourne des resultats sans user_id")
            return False
        except ValueError as e:
            print(f"OK: {e}\n")

        print("=" * 60)
        print("TOUS LES TESTS SONT PASSES!")
        print("=" * 60)
        print("\nL'isolation des donnees est maintenant correctement implementee.")
        print("Tous les modules exigent maintenant user_id pour acceder aux donnees.")
        return True

    finally:
        await db_manager.disconnect()


if __name__ == "__main__":
    result = asyncio.run(test_data_isolation())
    sys.exit(0 if result else 1)
