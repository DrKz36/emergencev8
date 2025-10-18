"""
Script d'application de la migration consolidated_at (Sprint 2).

Ajoute la colonne consolidated_at à la table threads pour tracker
la consolidation des threads archivés en LTM (ChromaDB).

Usage:
    python apply_migration_consolidated_at.py
"""
import asyncio
from pathlib import Path
from src.backend.core.database.manager import DatabaseManager


async def apply_migration():
    """Applique la migration consolidated_at sur emergence.db"""

    # Charger SQL migration
    migration_file = Path(__file__).parent / "migrations" / "20251018_add_consolidated_at.sql"

    if not migration_file.exists():
        print(f"[FAIL] Migration file not found: {migration_file}")
        return 1

    migration_sql = migration_file.read_text(encoding='utf-8')
    print(f"[INFO] Migration loaded: {migration_file.name}")

    # Connecter à la DB
    db = DatabaseManager("emergence.db")
    await db.connect()
    print("[INFO] Connected to emergence.db")

    try:
        # Parser statements SQL (ligne par ligne, filtrer commentaires et vides)
        lines = migration_sql.split('\n')
        clean_lines = [
            line for line in lines
            if line.strip() and not line.strip().startswith('--')
        ]
        clean_sql = '\n'.join(clean_lines)

        # Split par ';' et filtrer statements valides
        statements = [
            stmt.strip() for stmt in clean_sql.split(';')
            if stmt.strip() and any(
                kw in stmt.upper()
                for kw in ['ALTER', 'CREATE', 'UPDATE', 'INSERT', 'DELETE']
            )
        ]

        print(f"[INFO] Parsed {len(statements)} SQL statement(s)")

        # Exécuter chaque statement
        for i, stmt in enumerate(statements, 1):
            print(f"[INFO] Executing statement {i}/{len(statements)}...")
            print(f"       {stmt[:80]}..." if len(stmt) > 80 else f"       {stmt}")

            try:
                await db.execute(stmt, commit=True)
                print(f"[OK]   Statement {i} executed successfully")
            except Exception as e:
                # Ignorer si colonne existe déjà
                if "duplicate column name" in str(e).lower():
                    print(f"[WARN] Column already exists, skipping...")
                else:
                    raise

        # Vérifier que la colonne existe
        rows = await db.fetch_all("PRAGMA table_info(threads)")
        cols = [r["name"] for r in rows]

        if "consolidated_at" in cols:
            print("\n[OK]   Column 'consolidated_at' exists in table 'threads'")
        else:
            print("\n[FAIL] Column 'consolidated_at' NOT found!")
            return 1

        # Vérifier index créé
        indexes = await db.fetch_all("PRAGMA index_list(threads)")
        index_names = [idx["name"] for idx in indexes]

        if "idx_threads_archived_not_consolidated" in index_names:
            print("[OK]   Index 'idx_threads_archived_not_consolidated' created")
        else:
            print("[WARN] Index 'idx_threads_archived_not_consolidated' not found")

        # Stats threads
        stats = await db.fetch_one("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN archived=1 THEN 1 ELSE 0 END) as archived,
                SUM(CASE WHEN archived=1 AND consolidated_at IS NULL THEN 1 ELSE 0 END) as not_consolidated
            FROM threads
        """)

        print(f"\n[INFO] Database statistics:")
        print(f"       Total threads: {stats['total']}")
        print(f"       Archived threads: {stats['archived']}")
        print(f"       Not consolidated: {stats['not_consolidated']}")

        print("\n[OK]   Migration completed successfully!")
        return 0

    except Exception as e:
        print(f"\n[FAIL] Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        await db.close()
        print("[INFO] Database connection closed")


if __name__ == "__main__":
    exit_code = asyncio.run(apply_migration())
    exit(exit_code)
