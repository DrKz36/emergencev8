#!/usr/bin/env python3
"""
Script de migration pour activer la persistance cross-device.

Ce script:
1. Ajoute la colonne user_id si manquante
2. Backfill les user_id depuis email (hash)
3. Crée les index nécessaires

Usage:
    python scripts/migrate_cross_device.py [--dry-run]

Options:
    --dry-run    Afficher les changements sans les appliquer
"""

import asyncio
import sys
import hashlib
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.core.database.manager import DatabaseManager


def hash_email(email: str) -> str:
    """Hash un email pour générer un user_id constant."""
    return hashlib.sha256(email.lower().encode("utf-8")).hexdigest()


async def migrate_auth_sessions(db: DatabaseManager, dry_run: bool = False):
    """Migrer la table auth_sessions."""
    print("📊 Migration auth_sessions...")

    # Vérifier si colonne user_id existe
    rows = await db.fetch_all("PRAGMA table_info(auth_sessions)")
    columns = [dict(row)["name"] for row in rows]

    if "user_id" not in columns:
        print("   ➕ Ajout colonne user_id...")
        if not dry_run:
            await db.execute(
                "ALTER TABLE auth_sessions ADD COLUMN user_id TEXT", commit=True
            )
        print("   ✅ Colonne user_id ajoutée")
    else:
        print("   ✅ Colonne user_id déjà présente")

    # Backfill user_id depuis email
    count_row = await db.fetch_one(
        "SELECT COUNT(*) as count FROM auth_sessions WHERE (user_id IS NULL OR user_id = '') AND email IS NOT NULL"
    )
    count = dict(count_row)["count"] if count_row else 0

    if count > 0:
        print(f"   🔄 Backfill {count} sessions...")
        if not dry_run:
            # Récupérer toutes les sessions sans user_id
            rows = await db.fetch_all(
                "SELECT id, email FROM auth_sessions WHERE (user_id IS NULL OR user_id = '') AND email IS NOT NULL"
            )
            for row in rows:
                session = dict(row)
                session_id = session["id"]
                email = session["email"]
                user_id = hash_email(email)
                await db.execute(
                    "UPDATE auth_sessions SET user_id = ? WHERE id = ?",
                    (user_id, session_id),
                    commit=True,
                )
        print(f"   ✅ {count} sessions backfillées")
    else:
        print("   ✅ Toutes les sessions ont déjà un user_id")

    # Créer index
    if not dry_run:
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_auth_sessions_user_id ON auth_sessions(user_id)",
            commit=True,
        )
    print("   ✅ Index créé")


async def migrate_threads(db: DatabaseManager, dry_run: bool = False):
    """Migrer la table threads."""
    print("📊 Migration threads...")

    # Vérifier si colonne user_id existe
    rows = await db.fetch_all("PRAGMA table_info(threads)")
    columns = [dict(row)["name"] for row in rows]

    if "user_id" not in columns:
        print("   ➕ Ajout colonne user_id...")
        if not dry_run:
            await db.execute("ALTER TABLE threads ADD COLUMN user_id TEXT", commit=True)
        print("   ✅ Colonne user_id ajoutée")
    else:
        print("   ✅ Colonne user_id déjà présente")

    # Backfill user_id depuis auth_sessions
    count_row = await db.fetch_one(
        """
        SELECT COUNT(*) as count
        FROM threads
        WHERE (user_id IS NULL OR user_id = '')
        AND session_id IS NOT NULL
        AND EXISTS (SELECT 1 FROM auth_sessions WHERE auth_sessions.id = threads.session_id)
        """
    )
    count = dict(count_row)["count"] if count_row else 0

    if count > 0:
        print(f"   🔄 Backfill {count} threads depuis auth_sessions...")
        if not dry_run:
            await db.execute(
                """
                UPDATE threads
                SET user_id = (
                    SELECT user_id FROM auth_sessions WHERE auth_sessions.id = threads.session_id
                )
                WHERE (user_id IS NULL OR user_id = '')
                AND session_id IS NOT NULL
                AND EXISTS (SELECT 1 FROM auth_sessions WHERE auth_sessions.id = threads.session_id)
                """,
                commit=True,
            )
        print(f"   ✅ {count} threads backfillés")
    else:
        print("   ✅ Tous les threads ont déjà un user_id")

    # Créer index
    if not dry_run:
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_threads_user_id ON threads(user_id)",
            commit=True,
        )
    print("   ✅ Index créé")


async def migrate_documents(db: DatabaseManager, dry_run: bool = False):
    """Migrer la table documents."""
    print("📊 Migration documents...")

    # Vérifier si colonne user_id existe
    rows = await db.fetch_all("PRAGMA table_info(documents)")
    columns = [dict(row)["name"] for row in rows]

    if "user_id" not in columns:
        print("   ➕ Ajout colonne user_id...")
        if not dry_run:
            await db.execute(
                "ALTER TABLE documents ADD COLUMN user_id TEXT", commit=True
            )
        print("   ✅ Colonne user_id ajoutée")
    else:
        print("   ✅ Colonne user_id déjà présente")

    # Backfill user_id depuis auth_sessions
    count_row = await db.fetch_one(
        """
        SELECT COUNT(*) as count
        FROM documents
        WHERE (user_id IS NULL OR user_id = '')
        AND session_id IS NOT NULL
        AND EXISTS (SELECT 1 FROM auth_sessions WHERE auth_sessions.id = documents.session_id)
        """
    )
    count = dict(count_row)["count"] if count_row else 0

    if count > 0:
        print(f"   🔄 Backfill {count} documents depuis auth_sessions...")
        if not dry_run:
            await db.execute(
                """
                UPDATE documents
                SET user_id = (
                    SELECT user_id FROM auth_sessions WHERE auth_sessions.id = documents.session_id
                )
                WHERE (user_id IS NULL OR user_id = '')
                AND session_id IS NOT NULL
                AND EXISTS (SELECT 1 FROM auth_sessions WHERE auth_sessions.id = documents.session_id)
                """,
                commit=True,
            )
        print(f"   ✅ {count} documents backfillés")
    else:
        print("   ✅ Tous les documents ont déjà un user_id")

    # Créer index
    if not dry_run:
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_documents_user_id ON documents(user_id)",
            commit=True,
        )
    print("   ✅ Index créé")


async def main():
    dry_run = "--dry-run" in sys.argv

    if dry_run:
        print("=" * 60)
        print("🔍 MODE DRY-RUN (simulation sans changements)")
        print("=" * 60)
    else:
        print("=" * 60)
        print("🚀 MIGRATION CROSS-DEVICE PERSISTENCE")
        print("=" * 60)
        print()
        print("⚠️  ATTENTION: Cette migration va modifier la base de données.")
        print("   Assurez-vous d'avoir une sauvegarde avant de continuer !")
        print()
        response = input("Continuer ? [y/N] ")
        if response.lower() != "y":
            print("Migration annulée.")
            return

    print()

    # Init DB
    db_path = "emergence.db"
    db = DatabaseManager(db_path)
    await db.init()

    try:
        # Migration tables
        await migrate_auth_sessions(db, dry_run)
        print()
        await migrate_threads(db, dry_run)
        print()
        await migrate_documents(db, dry_run)
        print()

        print("=" * 60)
        print("✅ MIGRATION TERMINÉE")
        print("=" * 60)
        print()
        if not dry_run:
            print("Prochaines étapes:")
            print("1. Tester avec 2 devices (mobile + desktop)")
            print("2. Forcer re-login des utilisateurs (nouveau JWT avec sub)")
            print(
                "3. Vérifier que les threads/documents apparaissent sur les 2 devices"
            )
            print()
        else:
            print("Pour appliquer les changements, relancer sans --dry-run:")
            print("  python scripts/migrate_cross_device.py")
            print()

    except Exception as e:
        print()
        print("=" * 60)
        print("❌ ERREUR DURANT LA MIGRATION")
        print("=" * 60)
        print()
        print(f"Erreur: {e}")
        import traceback

        traceback.print_exc()
        print()
        print("La base de données n'a PAS été modifiée (rollback auto).")
        sys.exit(1)
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
