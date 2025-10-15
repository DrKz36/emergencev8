#!/usr/bin/env python3
"""
Test rapide du système de timeout de session (sans attendre 3 minutes).
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.insert(0, str(Path(__file__).parent / "src"))

from backend.core.session_manager import SessionManager, INACTIVITY_TIMEOUT_MINUTES, CLEANUP_INTERVAL_SECONDS
from backend.core.database.manager import DatabaseManager


async def quick_test():
    """Test rapide du système de timeout."""
    print("=" * 80)
    print("TEST RAPIDE DU SYSTEME DE TIMEOUT DE SESSION")
    print("=" * 80 + "\n")

    print(f"Configuration:")
    print(f"  - Timeout d'inactivite: {INACTIVITY_TIMEOUT_MINUTES} min")
    print(f"  - Intervalle de verification: {CLEANUP_INTERVAL_SECONDS}s\n")

    # Créer un SessionManager de test
    db_manager = DatabaseManager(":memory:")
    await db_manager.connect()
    session_manager = SessionManager(db_manager, memory_analyzer=None)

    # Créer 3 sessions de test
    session_ids = ["session-1", "session-2", "session-3"]
    print("[SETUP] Creation de 3 sessions de test")
    for sid in session_ids:
        session_manager.create_session(sid, f"user-{sid}")
        print(f"  - {sid} creee")

    print(f"\n[INFO] Sessions actives: {len(session_manager.active_sessions)}")

    # Démarrer la tâche de nettoyage
    print("\n[START] Demarrage de la tache de nettoyage")
    session_manager.start_cleanup_task()

    # Test: Modifier artificiellement last_activity pour forcer le timeout
    print(f"\n[TEST] Modification artificielle de last_activity pour forcer le timeout")
    old_time = datetime.now(timezone.utc) - timedelta(minutes=INACTIVITY_TIMEOUT_MINUTES + 0.5)

    # Session 1 et 2: Inactives (timeout)
    for sid in session_ids[:2]:
        session = session_manager.get_session(sid)
        if session:
            session.last_activity = old_time
            print(f"  - {sid}: last_activity = {old_time.strftime('%H:%M:%S')} (INACTIVE)")

    # Session 3: Active (pas de timeout)
    session_manager._update_session_activity(session_ids[2])
    session3 = session_manager.get_session(session_ids[2])
    if session3:
        print(f"  - {session_ids[2]}: last_activity = {session3.last_activity.strftime('%H:%M:%S')} (ACTIVE)")

    # Attendre un cycle de nettoyage
    wait_time = CLEANUP_INTERVAL_SECONDS + 5
    print(f"\n[WAIT] Attente du prochain cycle de nettoyage ({wait_time}s)...")
    await asyncio.sleep(wait_time)

    # Vérifier les résultats
    print("\n[VERIFY] Verification des resultats:")
    remaining = []
    for sid in session_ids:
        session = session_manager.get_session(sid)
        if session:
            remaining.append(sid)
            print(f"  - {sid}: PRESENTE (last_activity: {session.last_activity.strftime('%H:%M:%S')})")
        else:
            print(f"  - {sid}: SUPPRIMEE (timeout)")

    # Arrêter la tâche de nettoyage
    print("\n[STOP] Arret de la tache de nettoyage")
    await session_manager.stop_cleanup_task()

    # Résultat final
    print(f"\n[RESULT] Sessions actives finales: {len(session_manager.active_sessions)}")

    # Validation
    success = len(remaining) == 1 and session_ids[2] in remaining
    if success:
        print("\n" + "=" * 80)
        print("[SUCCESS] TEST REUSSI!")
        print("  - Les sessions inactives ont ete correctement supprimees")
        print(f"  - La session active ({session_ids[2]}) est toujours presente")
        print("=" * 80)
    else:
        print("\n" + "=" * 80)
        print("[FAILURE] TEST ECHOUE!")
        print(f"  - Sessions attendues: [{session_ids[2]}]")
        print(f"  - Sessions presentes: {remaining}")
        print("=" * 80)
        sys.exit(1)

    await db_manager.disconnect()


if __name__ == "__main__":
    try:
        asyncio.run(quick_test())
    except KeyboardInterrupt:
        print("\n\n[WARN] Test interrompu")
    except Exception as e:
        print(f"\n\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
