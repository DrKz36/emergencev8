#!/usr/bin/env python3
"""
Script de diagnostic pour le problème de persistance cross-device.

Usage:
    python scripts/diagnose_cross_device.py

Ce script vérifie:
1. Schéma des tables (user_id présent ?)
2. Sessions sans user_id
3. Threads/documents sans user_id
4. Suggestions de fix
"""

import asyncio
import sys
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.core.database.manager import DatabaseManager
from backend.features.auth.service import AuthService


async def main():
    print("=" * 60)
    print("🔍 DIAGNOSTIC CROSS-DEVICE PERSISTENCE")
    print("=" * 60)
    print()

    # Init DB
    db_path = "emergence.db"
    db = DatabaseManager(db_path)
    await db.init()

    # Vérifier schéma auth_sessions
    print("1. Vérification schéma auth_sessions...")
    rows = await db.fetch_all("PRAGMA table_info(auth_sessions)")
    columns = [dict(row) for row in rows]
    has_user_id = any(col["name"] == "user_id" for col in columns)

    if has_user_id:
        print("   ✅ Colonne user_id présente dans auth_sessions")
    else:
        print("   ❌ Colonne user_id MANQUANTE dans auth_sessions")
        print("      → Les sessions ne peuvent pas résoudre le user_id !")
        print("      → CRITIQUE: Migration nécessaire")

    print()

    # Vérifier schéma threads
    print("2. Vérification schéma threads...")
    rows = await db.fetch_all("PRAGMA table_info(threads)")
    columns = [dict(row) for row in rows]
    has_user_id = any(col["name"] == "user_id" for col in columns)

    if has_user_id:
        print("   ✅ Colonne user_id présente dans threads")
    else:
        print("   ❌ Colonne user_id MANQUANTE dans threads")
        print("      → Les threads ne peuvent pas être partagés cross-device !")
        print("      → CRITIQUE: Migration nécessaire")

    print()

    # Vérifier schéma documents
    print("3. Vérification schéma documents...")
    rows = await db.fetch_all("PRAGMA table_info(documents)")
    columns = [dict(row) for row in rows]
    has_user_id = any(col["name"] == "user_id" for col in columns)

    if has_user_id:
        print("   ✅ Colonne user_id présente dans documents")
    else:
        print("   ❌ Colonne user_id MANQUANTE dans documents")
        print("      → Les documents ne peuvent pas être partagés cross-device !")
        print("      → CRITIQUE: Migration nécessaire")

    print()

    # Compter sessions sans user_id
    print("4. Vérification données auth_sessions...")
    try:
        count_row = await db.fetch_one(
            "SELECT COUNT(*) as count FROM auth_sessions WHERE user_id IS NULL OR user_id = ''"
        )
        count = dict(count_row)["count"] if count_row else 0
        total_row = await db.fetch_one("SELECT COUNT(*) as count FROM auth_sessions")
        total = dict(total_row)["count"] if total_row else 0

        if count > 0:
            print(f"   ⚠️  {count}/{total} sessions SANS user_id ({count*100//total if total else 0}%)")
            print("      → Ces sessions ne peuvent pas résoudre le user_id")
            print("      → FIX: Backfill nécessaire")
        else:
            print(f"   ✅ Toutes les sessions ont un user_id ({total} total)")
    except Exception as e:
        print(f"   ⚠️  Impossible de vérifier (colonne user_id manquante ?): {e}")

    print()

    # Compter threads sans user_id
    print("5. Vérification données threads...")
    try:
        count_row = await db.fetch_one(
            "SELECT COUNT(*) as count FROM threads WHERE user_id IS NULL OR user_id = ''"
        )
        count = dict(count_row)["count"] if count_row else 0
        total_row = await db.fetch_one("SELECT COUNT(*) as count FROM threads")
        total = dict(total_row)["count"] if total_row else 0

        if count > 0:
            print(f"   ⚠️  {count}/{total} threads SANS user_id ({count*100//total if total else 0}%)")
            print("      → Ces threads ne sont PAS partagés cross-device")
            print("      → FIX: Backfill nécessaire")
        else:
            print(f"   ✅ Tous les threads ont un user_id ({total} total)")
    except Exception as e:
        print(f"   ⚠️  Impossible de vérifier (colonne user_id manquante ?): {e}")

    print()

    # Compter documents sans user_id
    print("6. Vérification données documents...")
    try:
        count_row = await db.fetch_one(
            "SELECT COUNT(*) as count FROM documents WHERE user_id IS NULL OR user_id = ''"
        )
        count = dict(count_row)["count"] if count_row else 0
        total_row = await db.fetch_one("SELECT COUNT(*) as count FROM documents")
        total = dict(total_row)["count"] if total_row else 0

        if count > 0:
            print(f"   ⚠️  {count}/{total} documents SANS user_id ({count*100//total if total else 0}%)")
            print("      → Ces documents ne sont PAS partagés cross-device")
            print("      → FIX: Backfill nécessaire")
        else:
            print(f"   ✅ Tous les documents ont un user_id ({total} total)")
    except Exception as e:
        print(f"   ⚠️  Impossible de vérifier (colonne user_id manquante ?): {e}")

    print()

    # Vérifier correspondance email → user_id
    print("7. Vérification hash email → user_id...")
    try:
        # Prendre un exemple de session avec email
        session_row = await db.fetch_one(
            "SELECT email, user_id FROM auth_sessions WHERE email IS NOT NULL LIMIT 1"
        )
        if session_row:
            session = dict(session_row)
            email = session["email"]
            stored_user_id = session.get("user_id")

            # Calculer le hash attendu
            import hashlib
            expected_user_id = hashlib.sha256(email.lower().encode("utf-8")).hexdigest()

            if stored_user_id == expected_user_id:
                print(f"   ✅ Hash email → user_id CORRECT")
                print(f"      Email: {email}")
                print(f"      user_id: {stored_user_id[:16]}...")
            else:
                print(f"   ❌ Hash email → user_id INCORRECT !")
                print(f"      Email: {email}")
                print(f"      Attendu: {expected_user_id[:16]}...")
                print(f"      Trouvé: {stored_user_id[:16] if stored_user_id else 'NULL'}...")
                print("      → CRITIQUE: Le hash ne correspond pas !")
        else:
            print("   ⚠️  Aucune session trouvée pour tester")
    except Exception as e:
        print(f"   ⚠️  Impossible de vérifier: {e}")

    print()

    # Résumé et recommandations
    print("=" * 60)
    print("📋 RÉSUMÉ ET RECOMMANDATIONS")
    print("=" * 60)
    print()
    print("Si des problèmes ont été détectés:")
    print()
    print("1. URGENT: Lancer le script de migration")
    print("   python scripts/migrate_cross_device.py")
    print()
    print("2. Forcer re-login des utilisateurs pour nouveau JWT")
    print("   (JWT avec 'sub' correct)")
    print()
    print("3. Tester avec 2 devices (mobile + desktop)")
    print("   - Créer thread sur mobile")
    print("   - Vérifier qu'il apparaît sur desktop")
    print()

    await db.close()


if __name__ == "__main__":
    asyncio.run(main())
