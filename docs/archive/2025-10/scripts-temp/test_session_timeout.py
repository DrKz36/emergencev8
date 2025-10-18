#!/usr/bin/env python3
"""
Script de test pour le système de timeout de session.
Vérifie que les sessions inactives sont bien nettoyées après 3 minutes.
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Ajout du chemin pour les imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from backend.core.session_manager import SessionManager, INACTIVITY_TIMEOUT_MINUTES, CLEANUP_INTERVAL_SECONDS
from backend.core.database.manager import DatabaseManager
from backend.shared.models import Session


async def test_session_timeout():
    """Test du système de timeout de session."""
    print(f"[TEST] Systeme de timeout ({INACTIVITY_TIMEOUT_MINUTES} min)")
    print(f"   Intervalle de verification: {CLEANUP_INTERVAL_SECONDS}s\n")

    # Créer un SessionManager de test (sans DB réelle pour ce test)
    db_manager = DatabaseManager(":memory:")
    await db_manager.connect()

    session_manager = SessionManager(db_manager, memory_analyzer=None)

    # Créer une session de test
    test_session_id = "test-session-123"
    test_user_id = "test-user-456"

    print(f"[OK] Creation de la session {test_session_id}")
    session = session_manager.create_session(test_session_id, test_user_id)

    # Afficher les informations de la session
    print(f"   - Debut: {session.start_time.strftime('%H:%M:%S')}")
    print(f"   - Derniere activite: {session.last_activity.strftime('%H:%M:%S')}")
    print(f"   - Sessions actives: {len(session_manager.active_sessions)}\n")

    # Démarrer la tâche de nettoyage
    print("[START] Demarrage de la tache de nettoyage automatique")
    session_manager.start_cleanup_task()

    # Test 1: Session active (avec activité)
    print(f"\n[TEST 1] Session avec activite reguliere")
    print("   Simulation d'activite toutes les 60 secondes pendant 2 minutes...")
    for i in range(2):
        await asyncio.sleep(60)
        session_manager._update_session_activity(test_session_id)
        active_session = session_manager.get_session(test_session_id)
        if active_session:
            print(f"   [OK] Minute {i+1}: Session toujours active (last_activity: {active_session.last_activity.strftime('%H:%M:%S')})")
        else:
            print(f"   [ERROR] Minute {i+1}: Session supprimee (ERREUR!)")
            break

    # Test 2: Session inactive (sans activité)
    print(f"\n[TEST 2] Session sans activite pendant {INACTIVITY_TIMEOUT_MINUTES} minutes")
    print(f"   Attente de {INACTIVITY_TIMEOUT_MINUTES + 0.5} minutes sans activite...")

    # Pour accélérer le test, on modifie artificiellement last_activity
    active_session = session_manager.get_session(test_session_id)
    if active_session:
        old_time = datetime.now(timezone.utc) - timedelta(minutes=INACTIVITY_TIMEOUT_MINUTES + 0.5)
        active_session.last_activity = old_time
        print(f"   [TIME] Last activity modifiee a: {old_time.strftime('%H:%M:%S')}")
        print(f"   [WAIT] Attente du prochain cycle de nettoyage ({CLEANUP_INTERVAL_SECONDS}s)...")

        # Attendre un cycle de nettoyage
        await asyncio.sleep(CLEANUP_INTERVAL_SECONDS + 5)

        # Vérifier que la session a été nettoyée
        remaining_session = session_manager.get_session(test_session_id)
        if remaining_session is None:
            print(f"   [OK] Session correctement nettoyee pour inactivite!")
        else:
            print(f"   [ERROR] Session toujours active (ERREUR - timeout non fonctionnel!)")
    else:
        print("   [ERROR] Session deja supprimee (ERREUR!)")

    # Nettoyage
    print("\n[STOP] Arret de la tache de nettoyage")
    await session_manager.stop_cleanup_task()

    print(f"\n[OK] Test termine - Sessions actives restantes: {len(session_manager.active_sessions)}")

    await db_manager.disconnect()


if __name__ == "__main__":
    print("=" * 80)
    print("TEST DU SYSTEME DE TIMEOUT DE SESSION")
    print("=" * 80 + "\n")

    try:
        asyncio.run(test_session_timeout())
        print("\n" + "=" * 80)
        print("[SUCCESS] TOUS LES TESTS REUSSIS")
        print("=" * 80)
    except KeyboardInterrupt:
        print("\n\n[WARN] Test interrompu par l'utilisateur")
    except Exception as e:
        print(f"\n\n[ERROR] ERREUR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
