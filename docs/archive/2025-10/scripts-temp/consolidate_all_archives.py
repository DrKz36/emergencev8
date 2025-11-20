#!/usr/bin/env python3
"""
Script rapide pour consolider TOUS les threads archivés non consolidés.

Usage:
    python consolidate_all_archives.py

Ce script est un wrapper simplifié autour de backend.cli.consolidate_archived_threads
pour consolider rapidement tous les threads archivés qui n'ont pas encore été
consolidés dans la mémoire vectorielle (ChromaDB).

IMPORTANT: Ce script doit être lancé APRÈS les corrections du filtre agent_id
pour que les agents puissent récupérer les souvenirs des conversations archivées.
"""

import asyncio
import sys
from backend.cli.consolidate_archived_threads import run_consolidation


async def main():
    """Lance la consolidation de tous les threads archivés."""
    print("=" * 70)
    print("🔧 CONSOLIDATION DE TOUS LES THREADS ARCHIVÉS")
    print("=" * 70)
    print()
    print("Ce script va consolider tous les threads archivés non consolidés")
    print("dans la mémoire vectorielle (ChromaDB) pour que les agents puissent")
    print("se souvenir des conversations archivées.")
    print()
    print("Démarrage de la consolidation...")
    print()

    try:
        await run_consolidation(
            user_id=None,  # Tous les utilisateurs
            limit=None,  # Tous les threads
            force=False,  # Seulement ceux non consolidés
            dry_run=False,  # Vraie consolidation
            verbose=True,  # Mode verbose pour voir le progrès
        )
        print()
        print("✅ Consolidation terminée avec succès!")
        print()
        print("Les agents devraient maintenant pouvoir récupérer les souvenirs")
        print("des conversations archivées.")

    except KeyboardInterrupt:
        print("\n\n⚠️  Consolidation interrompue par l'utilisateur")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Erreur fatale: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
