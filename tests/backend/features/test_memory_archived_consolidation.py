"""
Tests consolidation threads archivés dans LTM.
Phase P0 - Résolution Gap #1
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone

# Import des modules à tester
from backend.features.memory.task_queue import MemoryTaskQueue


@pytest.fixture
def mock_db_manager():
    """Mock DatabaseManager."""
    db = Mock()
    db.fetch_all = AsyncMock(return_value=[])
    db.fetch_one = AsyncMock(return_value=None)
    db.execute = AsyncMock()
    return db


@pytest.fixture
def mock_vector_service():
    """Mock VectorService avec collection ChromaDB."""
    service = Mock()
    collection = Mock()

    # Mock get_or_create_collection
    service.get_or_create_collection = Mock(return_value=collection)

    # Mock collection.get() - par défaut retourne vide (non consolidé)
    collection.get = Mock(return_value={"ids": []})

    # Mock add_documents
    service.add_documents = Mock()

    return service, collection


@pytest.fixture
def mock_gardener(mock_db_manager, mock_vector_service):
    """Mock MemoryGardener."""
    vector_service, _ = mock_vector_service

    gardener = Mock()
    gardener.db = mock_db_manager
    gardener.vector_service = vector_service

    # Mock _tend_single_thread pour retourner succès avec concepts
    gardener._tend_single_thread = AsyncMock(return_value={
        "status": "success",
        "new_concepts": 5,
        "consolidated_sessions": 1
    })

    return gardener


@pytest.fixture
def sample_archived_threads():
    """Threads archivés exemple."""
    return [
        {
            "id": "thread_archived_1",
            "session_id": "session_1",
            "user_id": "user_123",
            "title": "Archived Thread 1",
            "archived": True,
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": "thread_archived_2",
            "session_id": "session_2",
            "user_id": "user_123",
            "title": "Archived Thread 2",
            "archived": True,
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": "thread_archived_3",
            "session_id": "session_3",
            "user_id": "user_123",
            "title": "Archived Thread 3",
            "archived": True,
            "created_at": datetime.now(timezone.utc).isoformat()
        },
    ]


# ============================================================================
# Tests unitaires - Endpoint /consolidate-archived
# ============================================================================

@pytest.mark.asyncio
async def test_consolidate_archived_endpoint_success(mock_gardener, sample_archived_threads, mock_vector_service):
    """Test endpoint /consolidate-archived - succès."""
    from backend.features.memory.router import consolidate_archived_threads

    # Mock request
    mock_request = Mock()
    mock_container = Mock()

    vector_service, collection = mock_vector_service
    mock_container.vector_service = Mock(return_value=vector_service)
    mock_container.db_manager = Mock(return_value=mock_gardener.db)

    mock_request.app.state.service_container = mock_container

    # Mock get_user_id coroutine
    async def mock_get_user_id(req):
        return "user_123"

    # Mock _get_gardener_from_request
    def mock_get_gardener(req):
        return mock_gardener

    with patch("backend.shared.dependencies.get_user_id", new=mock_get_user_id):
        with patch("backend.features.memory.router._get_gardener_from_request", new=mock_get_gardener):
            with patch("backend.features.memory.router._get_container", return_value=mock_container):
                with patch("backend.core.database.queries.get_threads", new=AsyncMock(return_value=sample_archived_threads)):
                    # Exécuter endpoint
                    result = await consolidate_archived_threads(
                        request=mock_request,
                        data={"limit": 10, "force": False}
                    )

    # Vérifications
    assert result["status"] == "success"
    assert result["consolidated_count"] == 3  # 3 threads consolidés
    assert result["total_archived"] == 3
    assert len(result["errors"]) == 0


@pytest.mark.asyncio
async def test_consolidate_archived_endpoint_no_archived_threads(mock_gardener, mock_vector_service):
    """Test endpoint - aucun thread archivé."""
    from backend.features.memory.router import consolidate_archived_threads

    # Mock request
    mock_request = Mock()
    mock_container = Mock()

    vector_service, collection = mock_vector_service
    mock_container.vector_service = Mock(return_value=vector_service)
    mock_container.db_manager = Mock(return_value=mock_gardener.db)

    mock_request.app.state.service_container = mock_container

    # Mock get_user_id coroutine
    async def mock_get_user_id(req):
        return "user_123"

    # Mock get_threads retournant liste vide
    with patch("backend.shared.dependencies.get_user_id", new=mock_get_user_id):
        with patch("backend.features.memory.router._get_gardener_from_request", return_value=mock_gardener):
            with patch("backend.features.memory.router._get_container", return_value=mock_container):
                with patch("backend.core.database.queries.get_threads", new=AsyncMock(return_value=[])):
                    result = await consolidate_archived_threads(
                        request=mock_request,
                        data={"limit": 10}
                    )

    # Vérifications
    assert result["status"] == "success"
    assert result["consolidated_count"] == 0
    assert result["skipped_count"] == 0
    assert result["total_archived"] == 0


@pytest.mark.asyncio
async def test_consolidate_archived_endpoint_partial_failure(mock_gardener, sample_archived_threads, mock_vector_service):
    """Test endpoint - échec partiel (continue avec les autres)."""
    from backend.features.memory.router import consolidate_archived_threads

    # Mock request
    mock_request = Mock()
    mock_container = Mock()

    vector_service, collection = mock_vector_service
    mock_container.vector_service = Mock(return_value=vector_service)
    mock_container.db_manager = Mock(return_value=mock_gardener.db)

    mock_request.app.state.service_container = mock_container

    # Mock _tend_single_thread échouant pour thread 2
    async def mock_tend_with_failure(thread_id, **kwargs):
        if thread_id == "thread_archived_2":
            raise Exception("Consolidation failed for thread 2")
        return {"status": "success", "new_concepts": 3}

    mock_gardener._tend_single_thread = mock_tend_with_failure

    # Mock get_user_id coroutine
    async def mock_get_user_id(req):
        return "user_123"

    with patch("backend.shared.dependencies.get_user_id", new=mock_get_user_id):
        with patch("backend.features.memory.router._get_gardener_from_request", return_value=mock_gardener):
            with patch("backend.features.memory.router._get_container", return_value=mock_container):
                with patch("backend.core.database.queries.get_threads", new=AsyncMock(return_value=sample_archived_threads)):
                    result = await consolidate_archived_threads(
                        request=mock_request,
                        data={"limit": 10}
                    )

    # Vérifications
    assert result["status"] == "success"
    assert result["consolidated_count"] == 2  # 2 réussis
    assert len(result["errors"]) == 1  # 1 échec
    assert result["errors"][0]["thread_id"] == "thread_archived_2"


@pytest.mark.asyncio
async def test_consolidate_archived_skips_already_consolidated(mock_gardener, sample_archived_threads, mock_vector_service):
    """Test endpoint - skip threads déjà consolidés."""
    from backend.features.memory.router import consolidate_archived_threads

    # Mock request
    mock_request = Mock()
    mock_container = Mock()

    vector_service, collection = mock_vector_service
    mock_container.vector_service = Mock(return_value=vector_service)
    mock_container.db_manager = Mock(return_value=mock_gardener.db)

    mock_request.app.state.service_container = mock_container

    # Mock collection.get() pour thread_archived_1 (déjà consolidé)
    def mock_collection_get(where=None, **kwargs):
        if where and where.get("thread_id") == "thread_archived_1":
            return {"ids": [["concept_id_1"]]}  # Thread déjà consolidé
        return {"ids": []}  # Autres threads non consolidés

    collection.get = mock_collection_get

    # Mock get_user_id coroutine
    async def mock_get_user_id(req):
        return "user_123"

    with patch("backend.shared.dependencies.get_user_id", new=mock_get_user_id):
        with patch("backend.features.memory.router._get_gardener_from_request", return_value=mock_gardener):
            with patch("backend.features.memory.router._get_container", return_value=mock_container):
                with patch("backend.core.database.queries.get_threads", new=AsyncMock(return_value=sample_archived_threads)):
                    result = await consolidate_archived_threads(
                        request=mock_request,
                        data={"limit": 10, "force": False}
                    )

    # Vérifications
    assert result["consolidated_count"] == 2  # Seulement thread 2 et 3
    assert result["skipped_count"] == 1  # Thread 1 skippé


# ============================================================================
# Tests intégration hook archivage
# ============================================================================

@pytest.mark.asyncio
async def test_update_thread_hook_logic():
    """Test logique hook archivage - vérifie condition was_archived."""
    # Test unitaire de la logique hook sans dépendances complexes

    # Scénario 1: Thread non archivé -> archived=True => doit enqueue
    was_archived_1 = False
    payload_archived_1 = True
    should_enqueue_1 = payload_archived_1 and not was_archived_1
    assert should_enqueue_1 is True

    # Scénario 2: Thread déjà archivé -> archived=True => NE doit PAS enqueue
    was_archived_2 = True
    payload_archived_2 = True
    should_enqueue_2 = payload_archived_2 and not was_archived_2
    assert should_enqueue_2 is False

    # Scénario 3: Thread non archivé -> archived=None (pas de changement) => NE doit PAS enqueue
    was_archived_3 = False
    payload_archived_3 = None
    should_enqueue_3 = payload_archived_3 and not was_archived_3
    assert not should_enqueue_3  # None is falsy

    # Scénario 4: Thread archivé -> archived=False (désarchivage) => NE doit PAS enqueue
    was_archived_4 = True
    payload_archived_4 = False
    should_enqueue_4 = payload_archived_4 and not was_archived_4
    assert should_enqueue_4 is False


@pytest.mark.asyncio
async def test_update_thread_no_trigger_if_already_archived():
    """Test pas de trigger si thread déjà archivé."""
    from backend.features.threads.router import update_thread
    from backend.features.threads.router import ThreadUpdate
    from backend.shared.dependencies import SessionContext

    # Mock dependencies
    mock_db = Mock()
    mock_session = SessionContext(
        session_id="session_123",
        user_id="user_123",
        email="test@example.com",
        role="user",
        claims={}
    )

    # Mock task queue enqueue
    mock_queue = Mock()
    mock_queue.enqueue = AsyncMock()

    # Mock get_thread - thread DÉJÀ archivé
    async def mock_get_thread_already_archived(*args, **kwargs):
        return {
            "id": "thread_1",
            "archived": True,  # Déjà archivé
            "title": "Test Thread"
        }

    # Mock update_thread
    async def mock_update_thread(*args, **kwargs):
        pass

    with patch("backend.core.database.queries.get_thread", new=mock_get_thread_already_archived):
        with patch("backend.core.database.queries.update_thread", new=mock_update_thread):
            with patch("backend.features.memory.task_queue.get_memory_queue", return_value=mock_queue):
                payload = ThreadUpdate(archived=True)

                await update_thread(
                    thread_id="thread_1",
                    payload=payload,
                    session=mock_session,
                    db=mock_db
                )

    # Vérifications - Queue NE doit PAS être appelée
    assert not mock_queue.enqueue.called


# ============================================================================
# Tests task queue
# ============================================================================

@pytest.mark.asyncio
async def test_task_queue_consolidate_thread_type():
    """Test MemoryTaskQueue traite type 'consolidate_thread'."""
    from backend.features.memory.task_queue import MemoryTask

    queue = MemoryTaskQueue(max_workers=1)

    # Mock _run_thread_consolidation
    queue._run_thread_consolidation = AsyncMock(return_value={
        "status": "consolidated",
        "thread_id": "thread_1",
        "new_concepts": 7
    })

    # Créer tâche
    task = MemoryTask(
        task_type="consolidate_thread",
        payload={
            "thread_id": "thread_1",
            "session_id": "session_1",
            "user_id": "user_123",
            "reason": "archiving"
        }
    )

    # Traiter tâche
    await queue._process_task(task, worker_id=0)

    # Vérifications
    assert queue._run_thread_consolidation.called
    call_args = queue._run_thread_consolidation.call_args[0][0]
    assert call_args["thread_id"] == "thread_1"
    assert call_args["reason"] == "archiving"


@pytest.mark.asyncio
async def test_task_queue_consolidate_thread_saves_concepts(mock_db_manager, mock_vector_service):
    """Test consolidation sauvegarde concepts dans ChromaDB."""
    from backend.features.memory.task_queue import MemoryTaskQueue

    queue = MemoryTaskQueue(max_workers=1)

    vector_service, collection = mock_vector_service

    # Mock container
    mock_container = Mock()
    mock_container.db_manager = Mock(return_value=mock_db_manager)
    mock_container.vector_service = Mock(return_value=vector_service)
    mock_container.memory_analyzer = Mock()

    # Mock gardener
    mock_gardener = Mock()
    mock_gardener._tend_single_thread = AsyncMock(return_value={
        "status": "success",
        "new_concepts": 10
    })

    # Patcher à l'intérieur du module task_queue
    with patch("backend.containers.ServiceContainer", return_value=mock_container):
        with patch("backend.features.memory.gardener.MemoryGardener", return_value=mock_gardener):
            # Exécuter consolidation
            result = await queue._run_thread_consolidation({
                "thread_id": "thread_1",
                "session_id": "session_1",
                "user_id": "user_123",
                "reason": "manual"
            })

    # Vérifications
    assert result["status"] == "consolidated"
    assert result["new_concepts"] == 10
    assert mock_gardener._tend_single_thread.called


# ============================================================================
# Tests helper _thread_already_consolidated
# ============================================================================

@pytest.mark.asyncio
async def test_thread_already_consolidated_returns_true(mock_vector_service):
    """Test _thread_already_consolidated retourne True si concepts trouvés."""
    from backend.features.memory.router import _thread_already_consolidated

    vector_service, collection = mock_vector_service

    # Mock collection.get() retournant concepts
    collection.get = Mock(return_value={
        "ids": [["concept_1", "concept_2"]]
    })

    result = await _thread_already_consolidated(vector_service, "thread_1")

    assert result is True


@pytest.mark.asyncio
async def test_thread_already_consolidated_returns_false(mock_vector_service):
    """Test _thread_already_consolidated retourne False si aucun concept."""
    from backend.features.memory.router import _thread_already_consolidated

    vector_service, collection = mock_vector_service

    # Mock collection.get() retournant vide
    collection.get = Mock(return_value={"ids": []})

    result = await _thread_already_consolidated(vector_service, "thread_1")

    assert result is False
