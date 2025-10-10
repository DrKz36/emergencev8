"""
Script de validation des préférences dans ChromaDB.
Hotfix P1.3 - Vérification post-déploiement

Usage:
    python scripts/validate_preferences.py
    python scripts/validate_preferences.py --limit 20
    python scripts/validate_preferences.py --user-id user_123
"""

import sys
import argparse
from pathlib import Path

# Ajouter src au path pour imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    import chromadb
    from chromadb.config import Settings
except ImportError:
    print("❌ chromadb non installé. Installer avec: pip install chromadb")
    sys.exit(1)


def validate_preferences(persist_directory: str = "./chroma_data", limit: int = 10, user_id: str = None):
    """
    Valide que préférences sont bien dans ChromaDB.

    Args:
        persist_directory: Chemin vers données ChromaDB
        limit: Nombre max de préférences à afficher
        user_id: Filtrer par user_id (optionnel)
    """
    print(f"🔍 Validation ChromaDB - Collection 'memory_preferences'")
    print(f"📂 Répertoire: {persist_directory}")
    print("-" * 60)

    # Connexion ChromaDB
    try:
        client = chromadb.Client(Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=persist_directory
        ))
        print("✅ Connexion ChromaDB établie")
    except Exception as e:
        print(f"❌ Erreur connexion ChromaDB: {e}")
        return False

    # Récupérer collection
    try:
        collection = client.get_collection("memory_preferences")
        print(f"✅ Collection 'memory_preferences' trouvée")
    except Exception as e:
        print(f"❌ Collection 'memory_preferences' non trouvée: {e}")
        print("💡 Cela signifie probablement qu'aucune préférence n'a été extraite encore.")
        return False

    # Compter documents
    try:
        count = collection.count()
        print(f"📊 Total préférences: {count}")

        if count == 0:
            print("⚠️  Aucune préférence dans ChromaDB")
            print("💡 Causes possibles:")
            print("   - Aucune session finalisée avec préférences")
            print("   - Bug extraction (vérifier logs backend)")
            print("   - user_sub/user_id manquant (hotfix P1.3)")
            return False

    except Exception as e:
        print(f"❌ Erreur count: {e}")
        return False

    # Récupérer préférences
    try:
        # Filtrer par user_id si fourni
        where_filter = {"user_id": user_id} if user_id else None

        results = collection.get(
            limit=limit,
            include=["metadatas", "documents"],
            where=where_filter
        )

        print(f"\n📋 Affichage de {min(len(results['documents']), limit)} préférences:")
        print("-" * 60)

        for i, (doc, meta) in enumerate(zip(results["documents"], results["metadatas"])):
            print(f"\n🔹 Préférence {i+1}/{min(count, limit)}")
            print(f"   User: {meta.get('user_sub') or meta.get('user_id', 'N/A')}")
            print(f"   Type: {meta.get('type', 'N/A')}")
            print(f"   Topic: {meta.get('topic', 'N/A')}")
            print(f"   Action: {meta.get('action', 'N/A')}")
            print(f"   Sentiment: {meta.get('sentiment', 'N/A')}")
            print(f"   Confidence: {meta.get('confidence', 'N/A')}")
            print(f"   Session: {meta.get('session_id', 'N/A')}")
            print(f"   Thread: {meta.get('thread_id', 'N/A')}")
            print(f"   Captured: {meta.get('captured_at', 'N/A')}")
            print(f"   Text: {doc[:100]}..." if len(doc) > 100 else f"   Text: {doc}")

        print("\n" + "=" * 60)
        print("✅ Validation terminée avec succès")
        return True

    except Exception as e:
        print(f"❌ Erreur récupération préférences: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Valide les préférences dans ChromaDB (Hotfix P1.3)"
    )
    parser.add_argument(
        "--persist-dir",
        type=str,
        default="./chroma_data",
        help="Chemin vers données ChromaDB (défaut: ./chroma_data)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Nombre max de préférences à afficher (défaut: 10)"
    )
    parser.add_argument(
        "--user-id",
        type=str,
        default=None,
        help="Filtrer par user_id (optionnel)"
    )

    args = parser.parse_args()

    success = validate_preferences(
        persist_directory=args.persist_dir,
        limit=args.limit,
        user_id=args.user_id
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
