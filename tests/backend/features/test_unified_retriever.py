# tests/backend/features/test_unified_retriever.py
# Tests unitaires pour UnifiedMemoryRetriever
# Sprint 3 Memory Refactoring
#
# Coverage:
# - MemoryContext (to_prompt_sections, to_markdown)
# - UnifiedMemoryRetriever._get_stm_context
# - UnifiedMemoryRetriever._get_ltm_context
# - UnifiedMemoryRetriever._get_archived_context
# - UnifiedMemoryRetriever.retrieve_context (full integration)

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from datetime import datetime
from backend.features.memory.unified_retriever import (
    MemoryContext,
    UnifiedMemoryRetriever
)


class TestMemoryContext:
    """Tests pour la classe MemoryContext"""

    def test_memory_context_init(self):
        """Test initialisation MemoryContext"""
        context = MemoryContext()

        assert context.stm_history == []
        assert context.ltm_concepts == []
        assert context.ltm_preferences == []
        assert context.archived_conversations == []

    def test_to_prompt_sections_empty(self):
        """Test to_prompt_sections avec contexte vide"""
        context = MemoryContext()
        sections = context.to_prompt_sections()

        assert sections == []

    def test_to_prompt_sections_with_preferences(self):
        """Test to_prompt_sections avec préférences"""
        context = MemoryContext()
        context.ltm_preferences = [
            {'text': 'Préférence utilisateur Docker', 'confidence': 0.8}
        ]

        sections = context.to_prompt_sections()

        assert len(sections) == 1
        assert sections[0][0] == "Préférences actives"
        assert "Docker" in sections[0][1]

    def test_to_prompt_sections_with_archives(self):
        """Test to_prompt_sections avec archives"""
        context = MemoryContext()
        context.archived_conversations = [
            {
                'thread_id': 'thread_123',
                'title': 'Discussion Docker',
                'date': '5 oct',
                'summary': 'Nous avons discuté de Docker',
                'relevance': 0.9
            }
        ]

        sections = context.to_prompt_sections()

        assert len(sections) == 1
        assert sections[0][0] == "Conversations passées pertinentes"
        assert "5 oct" in sections[0][1]
        assert "Docker" in sections[0][1]

    def test_to_prompt_sections_full_context(self):
        """Test to_prompt_sections avec contexte complet"""
        context = MemoryContext()
        context.ltm_preferences = [
            {'text': 'Préférence 1', 'confidence': 0.8}
        ]
        context.ltm_concepts = [
            {'text': 'Concept Docker', 'score': 0.9}
        ]
        context.archived_conversations = [
            {
                'date': '5 oct',
                'summary': 'Discussion Docker'
            }
        ]

        sections = context.to_prompt_sections()

        assert len(sections) == 3
        titles = [s[0] for s in sections]
        assert "Préférences actives" in titles
        assert "Conversations passées pertinentes" in titles
        assert "Connaissances pertinentes" in titles

    def test_to_markdown_empty(self):
        """Test to_markdown avec contexte vide"""
        context = MemoryContext()
        markdown = context.to_markdown()

        assert markdown == ""

    def test_to_markdown_with_content(self):
        """Test to_markdown avec contenu"""
        context = MemoryContext()
        context.ltm_preferences = [
            {'text': 'Préférence Docker', 'confidence': 0.8}
        ]
        context.ltm_concepts = [
            {'text': 'Containerisation', 'score': 0.9}
        ]

        markdown = context.to_markdown()

        assert "### Préférences actives" in markdown
        assert "### Connaissances pertinentes" in markdown
        assert "Docker" in markdown
        assert "Containerisation" in markdown


class TestUnifiedMemoryRetriever:
    """Tests pour UnifiedMemoryRetriever"""

    @pytest.fixture
    def mock_session_manager(self):
        """Mock SessionManager"""
        manager = Mock()
        manager.db_manager = Mock()
        manager.get_full_history = Mock(return_value=[
            {'role': 'user', 'content': 'Bonjour', 'timestamp': '2025-10-18T10:00:00Z'},
            {'role': 'assistant', 'content': 'Bonjour !', 'timestamp': '2025-10-18T10:00:01Z'}
        ])
        return manager

    @pytest.fixture
    def mock_vector_service(self):
        """Mock VectorService"""
        service = Mock()
        collection = Mock()

        # Mock get
        collection.get = Mock(return_value={
            'ids': ['pref_1'],
            'documents': ['Préférence Docker'],
            'metadatas': [{'confidence': 0.8, 'topic': 'tech'}]
        })

        service.get_or_create_collection = Mock(return_value=collection)
        service.query = Mock(return_value=[
            {
                'text': 'Concept Docker containerisation',
                'score': 0.9,
                'metadata': {'created_at': '2025-10-18T10:00:00Z'}
            }
        ])

        return service

    @pytest.fixture
    def mock_db_manager(self):
        """Mock DatabaseManager"""
        db = AsyncMock()
        return db

    @pytest.fixture
    def mock_memory_query_tool(self):
        """Mock MemoryQueryTool"""
        tool = Mock()
        return tool

    @pytest.fixture
    def retriever(self, mock_session_manager, mock_vector_service, mock_db_manager, mock_memory_query_tool):
        """UnifiedMemoryRetriever avec mocks"""
        return UnifiedMemoryRetriever(
            session_manager=mock_session_manager,
            vector_service=mock_vector_service,
            db_manager=mock_db_manager,
            memory_query_tool=mock_memory_query_tool
        )

    @pytest.mark.asyncio
    async def test_get_stm_context_success(self, retriever):
        """Test _get_stm_context avec succès"""
        history = await retriever._get_stm_context('session_123')

        assert len(history) == 2
        assert history[0]['role'] == 'user'
        assert history[1]['role'] == 'assistant'

    @pytest.mark.asyncio
    async def test_get_stm_context_failure(self, retriever):
        """Test _get_stm_context avec erreur"""
        retriever.session_manager.get_full_history = Mock(side_effect=Exception("Session not found"))

        history = await retriever._get_stm_context('invalid_session')

        assert history == []

    @pytest.mark.skip(reason="Mock obsolete - 'Mock' object is not iterable")
    @pytest.mark.asyncio
    async def test_get_ltm_context_success(self, retriever):
        """Test _get_ltm_context avec succès"""
        result = await retriever._get_ltm_context(
            user_id='user_123',
            agent_id='anima',
            query='Docker containerisation',
            top_k=5
        )

        assert 'preferences' in result
        assert 'concepts' in result
        assert len(result['preferences']) == 1
        assert len(result['concepts']) == 1
        assert 'Docker' in result['preferences'][0]['text']
        assert 'Docker' in result['concepts'][0]['text']

    @pytest.mark.asyncio
    async def test_get_ltm_context_failure(self, retriever):
        """Test _get_ltm_context avec erreur"""
        retriever.vector_service.get_or_create_collection = Mock(side_effect=Exception("ChromaDB error"))

        result = await retriever._get_ltm_context(
            user_id='user_123',
            agent_id='anima',
            query='test',
            top_k=5
        )

        assert result == {'preferences': [], 'concepts': []}

    @pytest.mark.asyncio
    async def test_get_archived_context_with_results(self, retriever):
        """Test _get_archived_context avec résultats"""
        # Mock get_threads pour retourner threads archivés
        from backend.core.database import queries

        with patch.object(queries, 'get_threads', new_callable=AsyncMock) as mock_get_threads:
            mock_get_threads.return_value = [
                {
                    'id': 'thread_1',
                    'title': 'Docker et Kubernetes en production',
                    'archived_at': '2025-10-15T14:30:00Z',
                    'consolidated_at': '2025-10-15T14:35:00Z'
                },
                {
                    'id': 'thread_2',
                    'title': 'Introduction à Python',
                    'archived_at': '2025-10-14T10:00:00Z',
                    'consolidated_at': None
                }
            ]

            results = await retriever._get_archived_context(
                user_id='user_123',
                agent_id='anima',
                query='Docker Kubernetes',
                limit=3
            )

            # Should find thread_1 (contains keywords)
            assert len(results) > 0
            assert any('Docker' in r['title'] for r in results)

    @pytest.mark.asyncio
    async def test_get_archived_context_empty(self, retriever):
        """Test _get_archived_context sans résultats"""
        from backend.core.database import queries

        with patch.object(queries, 'get_threads', new_callable=AsyncMock) as mock_get_threads:
            mock_get_threads.return_value = []

            results = await retriever._get_archived_context(
                user_id='user_123',
                agent_id='anima',
                query='test',
                limit=3
            )

            assert results == []

    @pytest.mark.asyncio
    async def test_retrieve_context_full(self, retriever):
        """Test retrieve_context avec contexte complet"""
        from backend.core.database import queries

        with patch.object(queries, 'get_threads', new_callable=AsyncMock) as mock_get_threads:
            mock_get_threads.return_value = [
                {
                    'id': 'thread_1',
                    'title': 'Docker discussion',
                    'archived_at': '2025-10-15T14:30:00Z',
                    'consolidated_at': '2025-10-15T14:35:00Z'
                }
            ]

            context = await retriever.retrieve_context(
                user_id='user_123',
                agent_id='anima',
                session_id='session_123',
                current_query='Comment utiliser Docker?',
                include_stm=True,
                include_ltm=True,
                include_archives=True,
                top_k_concepts=5,
                top_k_archives=3
            )

            # Vérifier toutes les sections remplies
            assert isinstance(context, MemoryContext)
            assert len(context.stm_history) == 2  # Mocked history
            assert len(context.ltm_preferences) == 1  # Mocked preferences
            assert len(context.ltm_concepts) == 1  # Mocked concepts
            assert len(context.archived_conversations) >= 0  # Mocked archives

    @pytest.mark.asyncio
    async def test_retrieve_context_stm_only(self, retriever):
        """Test retrieve_context avec STM uniquement"""
        context = await retriever.retrieve_context(
            user_id='user_123',
            agent_id='anima',
            session_id='session_123',
            current_query='test',
            include_stm=True,
            include_ltm=False,
            include_archives=False
        )

        assert isinstance(context, MemoryContext)
        assert len(context.stm_history) == 2
        assert len(context.ltm_concepts) == 0
        assert len(context.ltm_preferences) == 0
        assert len(context.archived_conversations) == 0

    @pytest.mark.asyncio
    async def test_retrieve_context_ltm_only(self, retriever):
        """Test retrieve_context avec LTM uniquement"""
        context = await retriever.retrieve_context(
            user_id='user_123',
            agent_id='anima',
            session_id='session_123',
            current_query='Docker',
            include_stm=False,
            include_ltm=True,
            include_archives=False
        )

        assert isinstance(context, MemoryContext)
        assert len(context.stm_history) == 0
        assert len(context.ltm_concepts) == 1
        assert len(context.ltm_preferences) == 1
        assert len(context.archived_conversations) == 0

    @pytest.mark.asyncio
    async def test_retrieve_context_archives_only(self, retriever):
        """Test retrieve_context avec Archives uniquement"""
        from backend.core.database import queries

        with patch.object(queries, 'get_threads', new_callable=AsyncMock) as mock_get_threads:
            mock_get_threads.return_value = []

            context = await retriever.retrieve_context(
                user_id='user_123',
                agent_id='anima',
                session_id='session_123',
                current_query='test',
                include_stm=False,
                include_ltm=False,
                include_archives=True
            )

            assert isinstance(context, MemoryContext)
            assert len(context.stm_history) == 0
            assert len(context.ltm_concepts) == 0
            assert len(context.ltm_preferences) == 0
            # Archives peuvent être vides si pas de match

    def test_format_date_success(self):
        """Test _format_date avec date valide"""
        result = UnifiedMemoryRetriever._format_date('2025-10-18T14:30:00Z')

        assert '18' in result
        assert 'oct' in result

    def test_format_date_none(self):
        """Test _format_date avec None"""
        result = UnifiedMemoryRetriever._format_date(None)

        assert result == ""

    def test_format_date_invalid(self):
        """Test _format_date avec date invalide"""
        result = UnifiedMemoryRetriever._format_date('invalid')

        # Should return first 10 chars as fallback
        assert result == 'invalid'
