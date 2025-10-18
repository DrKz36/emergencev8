#!/usr/bin/env python3
"""
Script ponctuel: Appliquer migration conversation_id sur DB locale

Usage: python apply_migration_conversation_id.py
"""
import asyncio
import sys
from pathlib import Path

# Ajouter src au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent))

from src.backend.core.database.manager import DatabaseManager


async def apply_migration():
    """Applique migration 20251018_add_conversation_id.sql"""

    # Lire migration SQL
    migration_file = Path(__file__).parent / "migrations" / "20251018_add_conversation_id.sql"

    if not migration_file.exists():
        print(f"❌ Migration file not found: {migration_file}")
        return 1

    migration_sql = migration_file.read_text(encoding='utf-8')
    print(f"[INFO] Migration SQL loaded ({len(migration_sql)} chars)\n")

    # Connexion DB
    db = DatabaseManager("emergence.db")
    await db.connect()

    try:
        # Parser SQL: Retirer commentaires et extraire statements
        lines = migration_sql.split('\n')
        clean_lines = []

        for line in lines:
            # Skip lignes commentaires
            if line.strip().startswith('--'):
                continue
            # Garder ligne si contient du SQL
            if line.strip():
                clean_lines.append(line)

        # Rejoindre et découper par ;
        clean_sql = '\n'.join(clean_lines)
        statements = [
            stmt.strip()
            for stmt in clean_sql.split(';')
            if stmt.strip() and any(kw in stmt.upper() for kw in ['ALTER', 'CREATE', 'UPDATE', 'INSERT'])
        ]

        print(f"[INFO] Executing {len(statements)} SQL statements...\n")

        for i, stmt in enumerate(statements, 1):
            print(f"  [{i}/{len(statements)}] {stmt[:70].replace(chr(10), ' ')}...")
            await db.execute(stmt, commit=True)
            print(f"  [OK]")

        # Validation post-migration
        print("\n[INFO] Validation post-migration...")

        # Vérifier colonne conversation_id existe
        result = await db.fetch_all("PRAGMA table_info(threads)")
        columns = [row['name'] for row in result]

        if 'conversation_id' in columns:
            print(f"  [OK] Colonne conversation_id ajoutee")
        else:
            print(f"  [FAIL] Colonne conversation_id MANQUANTE")
            return 1

        # Vérifier threads existants ont conversation_id
        null_count = await db.fetch_one(
            "SELECT COUNT(*) as count FROM threads WHERE conversation_id IS NULL"
        )
        total_count = await db.fetch_one("SELECT COUNT(*) as count FROM threads")

        print(f"  [INFO] Total threads: {total_count['count']}")
        print(f"  [INFO] Threads sans conversation_id: {null_count['count']}")

        if null_count['count'] == 0:
            print(f"  [OK] Tous threads ont conversation_id")
        else:
            print(f"  [WARN] {null_count['count']} threads sans conversation_id (attendu si DB vide)")

        # Vérifier index créés
        indexes = await db.fetch_all(
            "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='threads'"
        )
        index_names = [idx['name'] for idx in indexes]

        expected_indexes = ['idx_threads_user_conversation', 'idx_threads_user_type_conversation']
        for idx_name in expected_indexes:
            if idx_name in index_names:
                print(f"  [OK] Index {idx_name} cree")
            else:
                print(f"  [FAIL] Index {idx_name} MANQUANT")

        print("\n[SUCCESS] Migration appliquee avec succes!")
        return 0

    except Exception as e:
        print(f"\n[ERROR] Erreur lors de l'application de la migration:")
        print(f"   {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        await db.close()


if __name__ == '__main__':
    exit(asyncio.run(apply_migration()))
