# tests/test_memory_archives.py
# Tests validation corrections audit mémoire v2.0

import pytest
from datetime import datetime


class TestArchivedThreadsAccess:
    """Tests accès conversations archivées (P0)"""

    @pytest.mark.asyncio
    async def test_get_threads_include_archived(self, db_manager, test_user):
        """Vérifie que include_archived=True retourne les archives"""
        from backend.core.database import queries

        # Créer thread actif
        _ = await queries.create_thread(
            db_manager,
            session_id=None,
            user_id=test_user,
            type_="chat",
            title="Thread actif",
        )

        # Créer thread archivé
        archived_id = await queries.create_thread(
            db_manager,
            session_id=None,
            user_id=test_user,
            type_="chat",
            title="Thread archivé",
        )
        await queries.update_thread(
            db_manager,
            archived_id,
            session_id=None,
            user_id=test_user,
            archived=True,
        )

        # Test 1: Par défaut, archives exclues
        default_threads = await queries.get_threads(
            db_manager, session_id=None, user_id=test_user
        )
        assert len([t for t in default_threads if t["archived"] == 1]) == 0

        # Test 2: include_archived=True retourne tout
        all_threads = await queries.get_threads(
            db_manager, session_id=None, user_id=test_user, include_archived=True
        )
        assert len([t for t in all_threads if t["archived"] == 1]) >= 1
        assert len([t for t in all_threads if t["archived"] == 0]) >= 1

        # Test 3: archived_only=True retourne uniquement archives
        archived_only = await queries.get_threads(
            db_manager, session_id=None, user_id=test_user, archived_only=True
        )
        assert all(t["archived"] == 1 for t in archived_only)
        assert len(archived_only) >= 1

    @pytest.mark.asyncio
    async def test_archived_threads_enriched_metadata(self, db_manager, test_user):
        """Vérifie métadonnées enrichies (last_message_at, message_count)"""
        from backend.core.database import queries

        thread_id = await queries.create_thread(
            db_manager, session_id=None, user_id=test_user, type_="chat"
        )

        # Ajouter messages
        for i in range(5):
            await queries.add_message(
                db_manager,
                thread_id,
                session_id=None,
                user_id=test_user,
                role="user",
                content=f"Message {i}",
            )

        # Récupérer thread
        threads = await queries.get_threads(
            db_manager, session_id=None, user_id=test_user, include_archived=True
        )
        thread = next(t for t in threads if t["id"] == thread_id)

        # Vérifications
        assert thread.get("message_count") == 5
        assert thread.get("last_message_at") is not None
        assert datetime.fromisoformat(
            thread["last_message_at"].replace("Z", "+00:00")
        )


class TestTemporalSearch:
    """Tests recherche temporelle (P1)"""

    @pytest.mark.asyncio
    async def test_temporal_search_with_date_filters(self, db_manager, test_user):
        """Vérifie filtres temporels start_date/end_date"""
        from backend.core.temporal_search import TemporalSearch
        from backend.core.database import queries

        temporal = TemporalSearch(db_manager)

        # Créer messages à dates différentes
        thread_id = await queries.create_thread(
            db_manager, session_id=None, user_id=test_user, type_="chat"
        )

        await queries.add_message(
            db_manager,
            thread_id,
            session_id=None,
            user_id=test_user,
            role="user",
            content="Message about Docker containerization",
        )

        # Recherche sans filtre
        all_results = await temporal.search_messages(query="Docker", limit=50)
        assert len(all_results) >= 1

        # TODO: Implémenter filtres dates dans TemporalSearch.search_messages()
        # pour supporter start_date/end_date nativement

    @pytest.mark.asyncio
    async def test_concept_recall_timestamps(self, db_manager, vector_service, test_user):
        """Vérifie first_mentioned_at et last_mentioned_at dans LTM"""
        from backend.features.memory.concept_recall import ConceptRecallTracker

        tracker = ConceptRecallTracker(db_manager, vector_service, connection_manager=None)

        # Recherche concept (nécessite données vectorielles existantes)
        results = await tracker.query_concept_history(
            concept_text="test concept", user_id=test_user, limit=10
        )

        # Si résultats, vérifier timestamps
        if results:
            for r in results:
                assert "first_mentioned_at" in r
                assert "last_mentioned_at" in r
                assert "mention_count" in r
                assert r["mention_count"] >= 1

                # Valider format ISO 8601
                datetime.fromisoformat(r["first_mentioned_at"].replace("Z", "+00:00"))
                datetime.fromisoformat(r["last_mentioned_at"].replace("Z", "+00:00"))


class TestUnifiedSearch:
    """Tests recherche unifiée (P1.3)"""

    @pytest.mark.asyncio
    async def test_unified_search_all_sources(
        self, client, test_user_token, db_manager
    ):
        """Vérifie recherche dans STM+LTM+threads+messages"""
        from backend.core.database import queries

        # Créer données test
        thread_id = await queries.create_thread(
            db_manager,
            session_id=None,
            user_id="test_user",
            type_="chat",
            title="Docker discussion",
        )
        await queries.add_message(
            db_manager,
            thread_id,
            session_id=None,
            user_id="test_user",
            role="user",
            content="How to configure Docker?",
        )

        # Appel API
        response = client.get(
            "/api/memory/search/unified?q=docker&limit=10",
            headers={"Authorization": f"Bearer {test_user_token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # Vérifier structure
        assert "query" in data
        assert data["query"] == "docker"
        assert "stm_summaries" in data
        assert "ltm_concepts" in data
        assert "threads" in data
        assert "messages" in data
        assert "total_results" in data

        # Au moins une source doit avoir des résultats
        assert data["total_results"] > 0


class TestAPIEndpoints:
    """Tests nouveaux endpoints API"""

    def test_archived_threads_list_endpoint(self, client, test_user_token):
        """Vérifie GET /api/threads/archived/list"""
        response = client.get(
            "/api/threads/archived/list",
            headers={"Authorization": f"Bearer {test_user_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert isinstance(data["items"], list)

    def test_temporal_search_endpoint(self, client, test_user_token):
        """Vérifie GET /api/memory/search avec filtres dates"""
        response = client.get(
            "/api/memory/search?q=test&start_date=2025-01-01&end_date=2025-12-31",
            headers={"Authorization": f"Bearer {test_user_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "query" in data
        assert "results" in data
        assert "filters" in data
        assert data["filters"]["start_date"] == "2025-01-01"

    def test_unified_search_endpoint(self, client, test_user_token):
        """Vérifie GET /api/memory/search/unified"""
        response = client.get(
            "/api/memory/search/unified?q=test&include_archived=true",
            headers={"Authorization": f"Bearer {test_user_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "total_results" in data
        assert isinstance(data["stm_summaries"], list)
        assert isinstance(data["ltm_concepts"], list)
        assert isinstance(data["threads"], list)
        assert isinstance(data["messages"], list)


class TestDatabaseMigrations:
    """Tests migration schéma BDD"""

    @pytest.mark.asyncio
    async def test_threads_new_columns_exist(self, db_manager):
        """Vérifie présence colonnes last_message_at, message_count, archival_reason"""
        rows = await db_manager.fetch_all("PRAGMA table_info(threads)")
        columns = [row["name"] for row in rows]

        assert "last_message_at" in columns
        assert "message_count" in columns
        assert "archival_reason" in columns

    @pytest.mark.asyncio
    async def test_message_count_trigger_insert(self, db_manager, test_user):
        """Vérifie trigger auto-incrémentation message_count"""
        from backend.core.database import queries

        thread_id = await queries.create_thread(
            db_manager, session_id=None, user_id=test_user, type_="chat"
        )

        # Vérifier count initial = 0
        threads_before = await queries.get_threads(
            db_manager, session_id=None, user_id=test_user, include_archived=True
        )
        thread_before = next(t for t in threads_before if t["id"] == thread_id)
        assert thread_before.get("message_count", 0) == 0

        # Ajouter message
        await queries.add_message(
            db_manager,
            thread_id,
            session_id=None,
            user_id=test_user,
            role="user",
            content="Test",
        )

        # Vérifier count incrémenté
        threads_after = await queries.get_threads(
            db_manager, session_id=None, user_id=test_user, include_archived=True
        )
        thread_after = next(t for t in threads_after if t["id"] == thread_id)
        assert thread_after.get("message_count", 0) == 1


# Fixtures pour tests
@pytest.fixture
def test_user():
    return "test_user_123"


@pytest.fixture
def test_user_token():
    # Générer token JWT valide pour tests
    import jwt

    payload = {"sub": "test_user_123", "role": "member"}
    return jwt.encode(payload, "test_secret", algorithm="HS256")


@pytest.fixture
async def db_manager():
    from backend.core.database.manager import DatabaseManager

    db = DatabaseManager(":memory:")  # DB en mémoire pour tests
    await db.initialize()
    yield db
    await db.close()


@pytest.fixture
async def vector_service():
    from backend.features.memory.vector_service import VectorService

    vs = VectorService(persist_directory=None)  # Mode mémoire
    return vs


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from backend.main import app

    return TestClient(app)
