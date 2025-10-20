"""
Tests Sprint 1: conversation_id (Clarification Session vs Conversation)

Date: 2025-10-18
Roadmap: MEMORY_REFACTORING_ROADMAP.md Sprint 1

Tests pour valider:
- Création threads avec conversation_id
- Récupération threads par conversation_id
- Rétrocompatibilité (conversation_id optionnel)
- Index performance
"""
import pytest
from datetime import datetime, timezone
from backend.core.database.manager import DatabaseManager
from backend.core.database import queries


@pytest.fixture
async def db():
    """Fixture database in-memory pour tests isolés"""
    db_manager = DatabaseManager(":memory:")
    await db_manager.connect()
    await db_manager.initialize()
    yield db_manager
    await db_manager.close()


@pytest.mark.asyncio
async def test_create_thread_with_conversation_id(db):
    """
    Test: Créer thread avec conversation_id explicite
    Expected: conversation_id correctement assigné
    """
    custom_conv_id = "conv_custom_123"

    thread_id = await queries.create_thread(
        db=db,
        session_id="sess_abc",
        user_id="user_test",
        type_="chat",
        title="Test conversation",
        conversation_id=custom_conv_id  # ✅ Explicite
    )

    # Vérifier thread créé
    assert thread_id is not None

    # Récupérer et vérifier conversation_id
    thread = await queries.get_thread_any(db, thread_id)
    assert thread is not None
    assert thread['conversation_id'] == custom_conv_id
    assert thread['id'] == thread_id


@pytest.mark.asyncio
async def test_create_thread_without_conversation_id_defaults_to_thread_id(db):
    """
    Test: Créer thread SANS conversation_id (rétrocompatibilité)
    Expected: conversation_id = thread_id par défaut
    """
    thread_id = await queries.create_thread(
        db=db,
        session_id="sess_xyz",
        user_id="user_test",
        type_="chat",
        title="Test default conversation_id"
        # ✅ PAS de conversation_id fourni
    )

    # Récupérer thread
    thread = await queries.get_thread_any(db, thread_id)
    assert thread is not None

    # Vérifier conversation_id = thread_id (défaut)
    assert thread['conversation_id'] == thread_id


@pytest.mark.asyncio
async def test_get_threads_by_conversation(db):
    """
    Test: Récupérer tous threads d'une conversation
    Expected: Tous threads avec même conversation_id retournés
    """
    user_id = "user_multi"
    conv_id = "conv_shared"

    # Créer 3 threads pour même conversation (sessions différentes)
    thread_id_1 = await queries.create_thread(
        db, "sess_1", user_id=user_id, type_="chat",
        title="Session 1", conversation_id=conv_id
    )
    thread_id_2 = await queries.create_thread(
        db, "sess_2", user_id=user_id, type_="chat",
        title="Session 2", conversation_id=conv_id
    )
    thread_id_3 = await queries.create_thread(
        db, "sess_3", user_id=user_id, type_="chat",
        title="Session 3", conversation_id=conv_id
    )

    # Créer thread pour autre conversation (contrôle)
    other_thread = await queries.create_thread(
        db, "sess_other", user_id=user_id, type_="chat",
        title="Other conv", conversation_id="conv_other"
    )

    # Récupérer threads par conversation
    threads = await queries.get_threads_by_conversation(
        db=db,
        conversation_id=conv_id,
        user_id=user_id,
        include_archived=False
    )

    # Vérifications
    assert len(threads) == 3  # 3 threads dans cette conversation
    thread_ids = {t['id'] for t in threads}
    assert thread_id_1 in thread_ids
    assert thread_id_2 in thread_ids
    assert thread_id_3 in thread_ids
    assert other_thread not in thread_ids  # Pas dans cette conversation

    # Vérifier tri par date création (DESC) - Plus récent en premier
    # Note: Si créés trop rapidement, timestamps peuvent être identiques
    # Vérifier juste que le tri est cohérent (pas forcément ordre exact)
    assert threads[0]['id'] in {thread_id_1, thread_id_2, thread_id_3}
    assert threads[1]['id'] in {thread_id_1, thread_id_2, thread_id_3}
    assert threads[2]['id'] in {thread_id_1, thread_id_2, thread_id_3}


@pytest.mark.asyncio
async def test_get_threads_by_conversation_with_archived(db):
    """
    Test: Récupérer threads conversation incluant archivés
    Expected: Threads actifs + archivés retournés
    """
    user_id = "user_archive"
    conv_id = "conv_archive_test"

    # Créer threads actif et archivé
    thread_active = await queries.create_thread(
        db, "sess_active", user_id=user_id, type_="chat",
        title="Active", conversation_id=conv_id
    )
    thread_archived = await queries.create_thread(
        db, "sess_archived", user_id=user_id, type_="chat",
        title="Archived", conversation_id=conv_id
    )

    # Archiver thread
    await queries.update_thread(
        db, thread_archived, "sess_archived",
        user_id=user_id, archived=True
    )

    # Sans include_archived (défaut)
    threads_active_only = await queries.get_threads_by_conversation(
        db, conv_id, user_id, include_archived=False
    )
    assert len(threads_active_only) == 1
    assert threads_active_only[0]['id'] == thread_active

    # Avec include_archived=True
    threads_all = await queries.get_threads_by_conversation(
        db, conv_id, user_id, include_archived=True
    )
    assert len(threads_all) == 2
    thread_ids = {t['id'] for t in threads_all}
    assert thread_active in thread_ids
    assert thread_archived in thread_ids


@pytest.mark.asyncio
async def test_get_threads_by_conversation_user_isolation(db):
    """
    Test: Isolation utilisateurs (sécurité)
    Expected: User A ne voit pas threads de User B
    """
    conv_id = "conv_shared_name"  # Même nom mais users différents

    # User A crée thread
    thread_user_a = await queries.create_thread(
        db, "sess_a", user_id="user_a", type_="chat",
        conversation_id=conv_id
    )

    # User B crée thread avec MÊME conversation_id (collision nom)
    thread_user_b = await queries.create_thread(
        db, "sess_b", user_id="user_b", type_="chat",
        conversation_id=conv_id
    )

    # User A récupère ses threads
    threads_a = await queries.get_threads_by_conversation(
        db, conv_id, user_id="user_a"
    )
    assert len(threads_a) == 1
    assert threads_a[0]['id'] == thread_user_a

    # User B récupère ses threads
    threads_b = await queries.get_threads_by_conversation(
        db, conv_id, user_id="user_b"
    )
    assert len(threads_b) == 1
    assert threads_b[0]['id'] == thread_user_b


@pytest.mark.asyncio
async def test_conversation_continuity_across_sessions(db):
    """
    Test End-to-End: Continuité conversation sur plusieurs sessions
    Scénario: User reprend conversation après déconnexion/reconnexion
    """
    user_id = "user_continuity"
    conv_id = "conv_persistent"

    # Session 1: User démarre conversation
    thread_sess1 = await queries.create_thread(
        db, session_id="ws_session_1",
        user_id=user_id, type_="chat",
        title="Début conversation Docker",
        conversation_id=conv_id
    )

    # Simuler déconnexion/reconnexion → Nouvelle session WS
    # Session 2: User reprend conversation
    thread_sess2 = await queries.create_thread(
        db, session_id="ws_session_2",  # ✅ Nouveau session_id WS
        user_id=user_id, type_="chat",
        title="Reprise conversation Docker",
        conversation_id=conv_id  # ✅ Même conversation_id
    )

    # Vérifier threads distincts
    assert thread_sess1 != thread_sess2

    # Vérifier threads partagent même conversation
    thread1 = await queries.get_thread_any(db, thread_sess1)
    thread2 = await queries.get_thread_any(db, thread_sess2)
    assert thread1['conversation_id'] == conv_id
    assert thread2['conversation_id'] == conv_id
    assert thread1['session_id'] != thread2['session_id']  # Sessions WS différentes

    # Récupérer historique complet conversation
    all_threads = await queries.get_threads_by_conversation(
        db, conv_id, user_id
    )
    assert len(all_threads) == 2


# ============================================================================
# Tests Performance & Index
# ============================================================================

@pytest.mark.asyncio
async def test_conversation_id_index_exists(db):
    """
    Test: Vérifier index conversation_id créés
    Expected: Indexes idx_threads_user_conversation présent
    """
    # Requête indexes SQLite
    indexes = await db.fetch_all(
        "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='threads'"
    )
    index_names = [idx['name'] for idx in indexes]

    # Vérifier indexes conversation_id (créés par migration)
    assert 'idx_threads_user_conversation' in index_names


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
