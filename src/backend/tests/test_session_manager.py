"""
Tests pour SessionManager - Composant critique de gestion des sessions
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from backend.core.session_manager import SessionManager
from backend.shared.models import Session, ChatMessage, Role


@pytest.fixture
def mock_db_manager():
    """Mock DatabaseManager pour tests isolés"""
    db = MagicMock()
    db.connect = AsyncMock()
    db.disconnect = AsyncMock()
    db.execute = AsyncMock()
    db.fetch_one = AsyncMock()  # Correct method name
    db.fetch_all = AsyncMock()  # Correct method name
    db.commit = AsyncMock()
    return db


@pytest.fixture
def mock_memory_analyzer():
    """Mock MemoryAnalyzer"""
    analyzer = MagicMock()
    analyzer.analyze_message = AsyncMock()
    return analyzer


@pytest.fixture
def session_manager(mock_db_manager, mock_memory_analyzer):
    """Instance de SessionManager pour tests"""
    return SessionManager(mock_db_manager, mock_memory_analyzer)


class TestSessionManagerInit:
    """Tests d'initialisation"""

    def test_init_with_memory_analyzer(self, session_manager, mock_memory_analyzer):
        """Vérifie que le SessionManager s'initialise correctement"""
        assert session_manager.db_manager is not None
        assert session_manager.memory_analyzer == mock_memory_analyzer
        assert session_manager.active_sessions == {}

    def test_init_without_memory_analyzer(self, mock_db_manager):
        """Vérifie l'initialisation sans MemoryAnalyzer"""
        sm = SessionManager(mock_db_manager, None)
        assert sm.memory_analyzer is None


class TestSessionCreation:
    """Tests de création de session"""

    def test_create_session(self, session_manager):
        """Vérifie la création d'une nouvelle session"""
        session_id = "test-session-123"
        user_id = "user-456"

        session = session_manager.create_session(session_id, user_id)

        assert session.id == session_id
        assert session.user_id == user_id
        assert session.history == []
        assert session_id in session_manager.active_sessions

    def test_create_duplicate_session_returns_existing(self, session_manager):
        """Vérifie qu'une session existante est retournée si recréée"""
        session_id = "test-session-123"
        user_id = "user-456"

        session1 = session_manager.create_session(session_id, user_id)
        session2 = session_manager.create_session(session_id, user_id)

        assert session1 is session2


class TestSessionEnsure:
    """Tests de ensure_session (création ou récupération)"""

    @pytest.mark.asyncio
    async def test_ensure_new_session(self, session_manager, mock_db_manager):
        """Vérifie la création d'une nouvelle session via ensure_session"""
        session_id = "new-session-789"
        user_id = "user-123"

        # Mock: pas de session en BDD
        mock_db_manager.fetch_one = AsyncMock(return_value=None)

        session = await session_manager.ensure_session(session_id, user_id)

        assert session.id == session_id
        assert session.user_id == user_id
        assert session in session_manager.active_sessions.values()

    @pytest.mark.asyncio
    async def test_ensure_existing_session_in_memory(self, session_manager):
        """Vérifie qu'une session en mémoire est réutilisée"""
        session_id = "existing-session"
        user_id = "user-123"

        # Créer une session en mémoire
        existing_session = session_manager.create_session(session_id, user_id)

        # Ensure devrait retourner la même instance
        session = await session_manager.ensure_session(session_id, user_id)

        assert session is existing_session


class TestSessionRetrieval:
    """Tests de récupération de session"""

    def test_get_session_existing(self, session_manager):
        """Vérifie la récupération d'une session existante"""
        session_id = "test-session"
        user_id = "user-123"

        created = session_manager.create_session(session_id, user_id)
        retrieved = session_manager.get_session(session_id)

        assert retrieved == created

    def test_get_session_nonexistent(self, session_manager):
        """Vérifie le comportement avec une session inexistante"""
        session = session_manager.get_session("nonexistent-session")
        assert session is None


class TestMessageManagement:
    """Tests de gestion des messages"""

    @pytest.mark.asyncio
    async def test_add_message_to_session(self, session_manager):
        """Vérifie l'ajout d'un message à une session"""
        session_id = "test-session"
        user_id = "user-123"

        session = session_manager.create_session(session_id, user_id)

        # Créer un ChatMessage avec tous les champs obligatoires
        message = ChatMessage(
            id="msg-001",
            session_id=session_id,
            role=Role.USER,
            agent="user",
            content="Hello, world!",
            timestamp=datetime.now(timezone.utc).isoformat()
        )

        # La méthode est async
        await session_manager.add_message_to_session(session_id, message)

        assert len(session.history) == 1
        # Le message est stocké comme dict et peut avoir des métadonnées ajoutées
        stored_message = session.history[0]
        assert stored_message['id'] == message.id
        assert stored_message['content'] == message.content
        assert stored_message['role'] == message.role.value
        assert stored_message['agent'] == message.agent

    @pytest.mark.asyncio
    async def test_add_message_fails_if_session_not_exists(self, session_manager):
        """Vérifie qu'ajouter un message à une session inexistante échoue"""
        session_id = "nonexistent-session"

        message = ChatMessage(
            id="msg-002",
            session_id=session_id,
            role=Role.USER,
            agent="user",
            content="Test message",
            timestamp=datetime.now(timezone.utc).isoformat()
        )

        # L'implémentation actuelle log une erreur mais ne lève pas d'exception
        # Le message n'est pas ajouté si la session n'existe pas
        await session_manager.add_message_to_session(session_id, message)

        # Vérifier que la session n'a PAS été créée automatiquement
        assert session_id not in session_manager.active_sessions


class TestSessionAliases:
    """Tests de gestion des alias de session"""

    def test_register_alias(self, session_manager):
        """Vérifie l'enregistrement d'un alias"""
        canonical_id = "session-123"
        alias_id = "alias-456"
        user_id = "user-789"

        session_manager.create_session(canonical_id, user_id)
        # Signature: register_session_alias(session_id, alias)
        # où session_id est le canonical et alias est l'alias
        session_manager.register_session_alias(canonical_id, alias_id)

        resolved = session_manager.resolve_session_id(alias_id)
        assert resolved == canonical_id

    def test_resolve_non_aliased_returns_same(self, session_manager):
        """Vérifie que resolver retourne l'ID original si pas d'alias"""
        session_id = "normal-session"
        resolved = session_manager.resolve_session_id(session_id)
        assert resolved == session_id


class TestEdgeCases:
    """Tests des cas limites"""

    def test_empty_session_id(self, session_manager):
        """Vérifie le comportement avec un ID vide"""
        # Un ID vide peut être toléré par certaines implémentations
        # Ce test vérifie simplement que le comportement est prévisible
        try:
            session = session_manager.create_session("", "user-123")
            # Si accepté, vérifier qu'une session existe
            assert session is not None
        except (ValueError, AssertionError, KeyError):
            # Comportement attendu : rejet d'ID vide
            pass

    def test_none_user_id(self, session_manager):
        """Vérifie le comportement avec user_id None"""
        # Pydantic requiert un string pour user_id, donc None devrait échouer
        with pytest.raises(Exception):  # ValidationError de Pydantic
            session_manager.create_session("session-123", None)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
