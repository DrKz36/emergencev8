"""
Tests unitaires pour consolidation automatique des threads archivés (Sprint 2).

Teste que :
1. L'archivage d'un thread déclenche automatiquement la consolidation LTM
2. Le timestamp consolidated_at est correctement enregistré
3. Les concepts sont créés dans ChromaDB
4. Le système fonctionne sans gardener (rétrocompatibilité)
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from backend.core.database.manager import DatabaseManager
from backend.core.database import queries


@pytest.fixture
async def db():
    """Base de données en mémoire pour tests."""
    db_manager = DatabaseManager(":memory:")
    await db_manager.connect()

    # Créer schema avec table threads (incluant consolidated_at)
    await db_manager.execute(
        """
        CREATE TABLE IF NOT EXISTS threads (
            id TEXT PRIMARY KEY,
            conversation_id TEXT,
            session_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('chat','debate')),
            title TEXT,
            agent_id TEXT,
            meta TEXT,
            archived INTEGER NOT NULL DEFAULT 0,
            archival_reason TEXT,
            archived_at TEXT,
            consolidated_at TEXT,
            last_message_at TEXT,
            message_count INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """,
        commit=True,
    )

    # Index
    await db_manager.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_threads_user_conversation
        ON threads(user_id, conversation_id)
    """,
        commit=True,
    )

    await db_manager.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_threads_archived_not_consolidated
        ON threads(archived, consolidated_at)
        WHERE archived = 1 AND consolidated_at IS NULL
    """,
        commit=True,
    )

    # Table messages pour tests complets
    await db_manager.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            thread_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            user_id TEXT NOT NULL
        )
    """,
        commit=True,
    )

    yield db_manager
    await db_manager.close()


@pytest.fixture
def mock_gardener():
    """Mock MemoryGardener pour tester hook consolidation."""
    gardener = MagicMock()
    gardener._tend_single_thread = AsyncMock(return_value={"new_concepts": 5})
    return gardener


@pytest.mark.asyncio
async def test_archive_without_gardener_backwards_compat(db):
    """
    Test rétrocompatibilité: archivage sans gardener doit fonctionner.

    Vérifie que l'archivage fonctionne normalement si gardener non fourni
    (comportement legacy).
    """
    # Créer thread
    thread_id = await queries.create_thread(
        db,
        session_id="sess_test",
        user_id="user_test",
        type_="chat",
        title="Thread test rétrocompat",
    )

    # Archiver SANS gardener (comportement legacy)
    await queries.update_thread(
        db,
        thread_id=thread_id,
        session_id="sess_test",
        user_id="user_test",
        archived=True,
        # PAS de gardener fourni
    )

    # Vérifier thread archivé
    thread = await queries.get_thread_any(
        db, thread_id, session_id=None, user_id="user_test"
    )
    assert thread is not None
    assert thread["archived"] == 1
    assert thread["archived_at"] is not None
    assert thread["archival_reason"] == "manual_archive"  # Défaut

    # consolidated_at doit être NULL (pas de consolidation sans gardener)
    assert thread["consolidated_at"] is None


@pytest.mark.asyncio
async def test_archive_triggers_consolidation(db, mock_gardener):
    """
    Test consolidation automatique lors archivage avec gardener.

    Vérifie que:
    1. L'archivage déclenche _tend_single_thread du gardener
    2. consolidated_at est rempli après consolidation
    3. Les métadonnées archival_reason et archived_at sont correctes
    """
    # Créer thread
    thread_id = await queries.create_thread(
        db,
        session_id="sess_test",
        user_id="user_123",
        type_="chat",
        title="Thread à consolider",
    )

    # Ajouter message pour contexte (optionnel pour ce test)
    await db.execute(
        """
        INSERT INTO messages (id, thread_id, role, content, created_at, user_id)
        VALUES (?, ?, ?, ?, ?, ?)
    """,
        (
            "msg_1",
            thread_id,
            "user",
            "Message test pour consolidation",
            datetime.now(timezone.utc).isoformat(),
            "user_123",
        ),
        commit=True,
    )

    # Archiver AVEC gardener (doit déclencher consolidation)
    await queries.update_thread(
        db,
        thread_id=thread_id,
        session_id="sess_test",
        user_id="user_123",
        archived=True,
        meta={"archival_reason": "test_auto_consolidation"},
        gardener=mock_gardener,  # ✅ Injection gardener
    )

    # Vérifier que gardener._tend_single_thread a été appelé
    mock_gardener._tend_single_thread.assert_called_once_with(
        thread_id=thread_id, session_id="sess_test", user_id="user_123"
    )

    # Vérifier thread archivé ET consolidé
    thread = await queries.get_thread_any(
        db, thread_id, session_id=None, user_id="user_123"
    )
    assert thread is not None
    assert thread["archived"] == 1
    assert thread["archived_at"] is not None
    assert thread["archival_reason"] == "test_auto_consolidation"

    # ✅ CRITIQUE: consolidated_at doit être rempli
    assert thread["consolidated_at"] is not None

    # Vérifier format timestamp ISO8601
    consolidated_dt = datetime.fromisoformat(
        thread["consolidated_at"].replace("Z", "+00:00")
    )
    assert consolidated_dt.tzinfo is not None  # Timezone-aware


@pytest.mark.asyncio
async def test_consolidation_failure_does_not_block_archiving(db, mock_gardener):
    """
    Test robustesse: échec consolidation ne doit PAS bloquer archivage.

    Si gardener._tend_single_thread échoue, le thread doit quand même
    être archivé (consolidated_at reste NULL).
    """
    # Créer thread
    thread_id = await queries.create_thread(
        db,
        session_id="sess_test",
        user_id="user_fail",
        type_="chat",
        title="Thread avec échec consolidation",
    )

    # Configurer gardener pour échouer
    mock_gardener._tend_single_thread = AsyncMock(
        side_effect=Exception("ChromaDB indisponible")
    )

    # Archiver (consolidation va échouer mais archivage doit réussir)
    await queries.update_thread(
        db,
        thread_id=thread_id,
        session_id="sess_test",
        user_id="user_fail",
        archived=True,
        gardener=mock_gardener,
    )

    # Vérifier thread archivé (malgré échec consolidation)
    thread = await queries.get_thread_any(
        db, thread_id, session_id=None, user_id="user_fail"
    )
    assert thread is not None
    assert thread["archived"] == 1
    assert thread["archived_at"] is not None

    # consolidated_at doit être NULL (consolidation a échoué)
    assert thread["consolidated_at"] is None


@pytest.mark.asyncio
async def test_unarchive_does_not_trigger_consolidation(db, mock_gardener):
    """
    Test que le désarchivage ne déclenche PAS la consolidation.

    Seul archived=True doit trigger consolidation.
    """
    # Créer thread archivé
    thread_id = await queries.create_thread(
        db,
        session_id="sess_test",
        user_id="user_unarchive",
        type_="chat",
        title="Thread à désarchiver",
    )

    # Archiver d'abord
    await queries.update_thread(
        db,
        thread_id,
        "sess_test",
        user_id="user_unarchive",
        archived=True,
        gardener=mock_gardener,
    )

    # Reset mock call count
    mock_gardener._tend_single_thread.reset_mock()

    # Désarchiver (archived=False)
    await queries.update_thread(
        db,
        thread_id,
        "sess_test",
        user_id="user_unarchive",
        archived=False,
        gardener=mock_gardener,
    )

    # Vérifier que consolidation n'a PAS été appelée pour désarchivage
    mock_gardener._tend_single_thread.assert_not_called()

    # Vérifier thread désarchivé
    thread = await queries.get_thread_any(
        db, thread_id, session_id=None, user_id="user_unarchive"
    )
    assert thread["archived"] == 0


@pytest.mark.asyncio
async def test_index_archived_not_consolidated_exists(db):
    """
    Test que l'index idx_threads_archived_not_consolidated est créé.

    Cet index améliore les performances des requêtes
    "WHERE archived=1 AND consolidated_at IS NULL".
    """
    indexes = await db.fetch_all("PRAGMA index_list(threads)")
    index_names = [idx["name"] for idx in indexes]

    assert "idx_threads_archived_not_consolidated" in index_names, (
        "Index idx_threads_archived_not_consolidated manquant"
    )


# ===== Tests à ajouter dans le futur =====
# - Test consolidation batch (script consolidate_all_archives.py)
# - Test vérification ChromaDB (concepts créés)
# - Test performance consolidation (latence < 2s par thread)
# - Test isolation utilisateurs (user_id)
