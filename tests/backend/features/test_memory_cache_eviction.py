# tests/backend/features/test_memory_cache_eviction.py
"""
Tests pour la correction du Bug #2 : Fuite mémoire dans le cache d'analyse.
Vérifie que l'éviction agressive fonctionne correctement.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

# Import du module à tester
from backend.features.memory.analyzer import (
    MemoryAnalyzer,
    _ANALYSIS_CACHE,
    EVICTION_THRESHOLD,
    MAX_CACHE_SIZE,
)


@pytest.fixture
def mock_db_manager():
    """Mock DatabaseManager pour les tests"""
    db = Mock()
    db.execute = AsyncMock()
    return db


@pytest.fixture
def mock_chat_service():
    """Mock ChatService pour les tests"""
    chat = Mock()
    chat.get_structured_llm_response = AsyncMock(
        return_value={
            "summary": "Test summary",
            "concepts": ["concept1", "concept2"],
            "entities": ["entity1"],
        }
    )
    chat.session_manager = Mock()
    chat.session_manager.get_session = Mock(return_value=None)
    chat.vector_service = None
    return chat


@pytest.fixture
def analyzer(mock_db_manager, mock_chat_service):
    """Fixture pour créer un MemoryAnalyzer configuré"""
    analyzer = MemoryAnalyzer(mock_db_manager)
    analyzer.set_chat_service(mock_chat_service)
    return analyzer


@pytest.fixture(autouse=True)
def clear_cache():
    """Nettoie le cache avant et après chaque test"""
    _ANALYSIS_CACHE.clear()
    yield
    _ANALYSIS_CACHE.clear()


class TestCacheEviction:
    """Tests pour l'éviction agressive du cache"""

    def test_cache_eviction_constants(self):
        """Vérifie que les constantes sont bien définies"""
        assert EVICTION_THRESHOLD == 80, "EVICTION_THRESHOLD doit être 80"
        assert MAX_CACHE_SIZE == 100, "MAX_CACHE_SIZE doit être 100"

    @pytest.mark.asyncio
    async def test_cache_eviction_aggressive(self, analyzer, mock_db_manager):
        """Test que l'éviction est agressive (supprime 50+ entrées)"""
        # Patch queries.update_session_analysis_data
        with patch(
            "backend.features.memory.analyzer.queries.update_session_analysis_data",
            new=AsyncMock(),
        ):
            # Simuler 100 entrées dans le cache avec des timestamps échelonnés
            base_time = datetime.now()
            for i in range(100):
                cache_key = f"memory_analysis:session_{i}:hash{i:08x}"
                _ANALYSIS_CACHE[cache_key] = (
                    {"summary": f"test_{i}", "concepts": [], "entities": []},
                    base_time
                    - timedelta(
                        minutes=100 - i
                    ),  # Les plus récents ont i proche de 100
                )

            assert len(_ANALYSIS_CACHE) == 100, "Cache devrait avoir 100 entrées"

            # Créer une nouvelle entrée pour déclencher l'éviction
            history = [{"role": "user", "content": "Test message 101"}]

            # Analyser une session pour déclencher l'éviction
            await analyzer.analyze_session_for_concepts(
                session_id="session_101",
                history=history,
                force=False,
                user_id="test_user",
            )

            # Vérifier que le cache a été réduit à ~50 entrées (tolérance ±5)
            cache_size = len(_ANALYSIS_CACHE)
            assert cache_size <= 55, (
                f"Cache devrait être réduit à ~50 entrées, actuel: {cache_size}"
            )
            assert cache_size >= 45, (
                f"Cache ne devrait pas être trop réduit, actuel: {cache_size}"
            )

    @pytest.mark.asyncio
    async def test_cache_keeps_most_recent(self, analyzer, mock_db_manager):
        """Test que l'éviction garde les entrées les plus récentes"""
        with patch(
            "backend.features.memory.analyzer.queries.update_session_analysis_data",
            new=AsyncMock(),
        ):
            base_time = datetime.now()
            old_keys = []
            recent_keys = []

            # Créer 60 anciennes entrées
            for i in range(60):
                key = f"memory_analysis:old_session_{i}:hash{i:08x}"
                _ANALYSIS_CACHE[key] = (
                    {"summary": "old", "concepts": [], "entities": []},
                    base_time - timedelta(hours=i + 10),  # Très anciennes
                )
                old_keys.append(key)

            # Créer 30 entrées récentes
            for i in range(30):
                key = f"memory_analysis:recent_session_{i}:hash{i + 60:08x}"
                _ANALYSIS_CACHE[key] = (
                    {"summary": "recent", "concepts": [], "entities": []},
                    base_time - timedelta(minutes=i),  # Très récentes
                )
                recent_keys.append(key)

            assert len(_ANALYSIS_CACHE) == 90, "Cache devrait avoir 90 entrées"

            # Déclencher éviction en ajoutant une entrée
            history = [{"role": "user", "content": "Trigger eviction"}]
            await analyzer.analyze_session_for_concepts(
                session_id="trigger_session",
                history=history,
                force=False,
                user_id="test_user",
            )

            # Vérifier que les récentes sont majoritairement gardées
            recent_count = sum(1 for key in recent_keys if key in _ANALYSIS_CACHE)
            old_count = sum(1 for key in old_keys if key in _ANALYSIS_CACHE)

            # Au moins 25 des 30 récentes devraient être gardées
            assert recent_count >= 25, (
                f"Devrait garder ~25+ entrées récentes, actuel: {recent_count}"
            )

            # La plupart des anciennes devraient être supprimées
            assert old_count < 30, (
                f"Devrait supprimer la plupart des anciennes, actuel: {old_count}"
            )

    @pytest.mark.asyncio
    async def test_no_eviction_below_threshold(self, analyzer, mock_db_manager):
        """Test qu'il n'y a pas d'éviction en dessous du seuil (80)"""
        with patch(
            "backend.features.memory.analyzer.queries.update_session_analysis_data",
            new=AsyncMock(),
        ):
            # Ajouter seulement 70 entrées (< EVICTION_THRESHOLD)
            base_time = datetime.now()
            for i in range(70):
                key = f"memory_analysis:session_{i}:hash{i:08x}"
                _ANALYSIS_CACHE[key] = (
                    {"summary": f"test_{i}", "concepts": [], "entities": []},
                    base_time - timedelta(minutes=i),
                )

            assert len(_ANALYSIS_CACHE) == 70

            # Ajouter une nouvelle entrée
            history = [{"role": "user", "content": "Test no eviction"}]
            await analyzer.analyze_session_for_concepts(
                session_id="test_session",
                history=history,
                force=False,
                user_id="test_user",
            )

            # Le cache devrait avoir 71 entrées (pas d'éviction)
            assert len(_ANALYSIS_CACHE) == 71, (
                f"Aucune éviction ne devrait se produire, actuel: {len(_ANALYSIS_CACHE)}"
            )

    @pytest.mark.asyncio
    async def test_eviction_at_threshold(self, analyzer, mock_db_manager):
        """Test que l'éviction se déclenche exactement au seuil (81 entrées)"""
        with patch(
            "backend.features.memory.analyzer.queries.update_session_analysis_data",
            new=AsyncMock(),
        ):
            # Ajouter exactement 81 entrées (EVICTION_THRESHOLD + 1)
            base_time = datetime.now()
            for i in range(81):
                key = f"memory_analysis:session_{i}:hash{i:08x}"
                _ANALYSIS_CACHE[key] = (
                    {"summary": f"test_{i}", "concepts": [], "entities": []},
                    base_time - timedelta(minutes=i),
                )

            assert len(_ANALYSIS_CACHE) == 81

            # Ajouter une nouvelle entrée pour déclencher l'éviction
            history = [{"role": "user", "content": "Trigger at threshold"}]
            await analyzer.analyze_session_for_concepts(
                session_id="threshold_session",
                history=history,
                force=False,
                user_id="test_user",
            )

            # Le cache devrait être réduit à ~50 entrées
            cache_size = len(_ANALYSIS_CACHE)
            assert cache_size <= 55, (
                f"Cache devrait être réduit à ~50, actuel: {cache_size}"
            )
            assert cache_size >= 45, (
                f"Cache ne devrait pas être sur-réduit, actuel: {cache_size}"
            )


class TestCacheCorrectness:
    """Tests pour la correction et la cohérence du cache"""

    @pytest.mark.asyncio
    async def test_cache_ttl_expiration(self, analyzer, mock_db_manager):
        """Test que les entrées expirées sont détectées et ignorées"""
        with patch(
            "backend.features.memory.analyzer.queries.update_session_analysis_data",
            new=AsyncMock(),
        ):
            # Ajouter une entrée expirée (> 1h)
            expired_time = datetime.now() - timedelta(hours=2)
            valid_key = "memory_analysis:expired_session:12345678"
            _ANALYSIS_CACHE[valid_key] = (
                {"summary": "expired", "concepts": [], "entities": []},
                expired_time,  # Expirée depuis 2h
            )

            # Analyser avec même hash (devrait ignorer le cache expiré et re-calculer)
            history = [{"role": "user", "content": "Test"}]

            with patch("hashlib.md5") as mock_hash:
                mock_hash.return_value.hexdigest.return_value = "12345678"

                await analyzer.analyze_session_for_concepts(
                    session_id="expired_session",
                    history=history,
                    force=False,
                    user_id="test_user",
                )

            # Le LLM devrait être appelé car cache expiré
            assert analyzer.chat_service.get_structured_llm_response.call_count == 1, (
                "Le LLM devrait être appelé car cache expiré"
            )

            # Vérifier que le cache contient maintenant la nouvelle valeur (pas l'ancienne)
            if valid_key in _ANALYSIS_CACHE:
                cached_data, cached_time = _ANALYSIS_CACHE[valid_key]
                # Le nouveau timestamp doit être récent (pas l'ancien de -2h)
                assert cached_time > expired_time, (
                    "Le cache devrait contenir la nouvelle valeur"
                )

    @pytest.mark.asyncio
    async def test_cache_hit_valid_entry(self, analyzer, mock_db_manager):
        """Test qu'une entrée valide dans le cache est réutilisée"""
        with patch(
            "backend.features.memory.analyzer.queries.update_session_analysis_data",
            new=AsyncMock(),
        ):
            # Ajouter une entrée valide dans le cache
            valid_key = "memory_analysis:test_session:12345678"
            cached_result = {
                "summary": "Cached summary",
                "concepts": ["cached_concept"],
                "entities": ["cached_entity"],
            }
            _ANALYSIS_CACHE[valid_key] = (cached_result, datetime.now())

            # Simuler analyse avec même hash
            history = [{"role": "user", "content": "Test message"}]

            with patch("hashlib.md5") as mock_hash:
                mock_hash.return_value.hexdigest.return_value = "12345678"

                await analyzer.analyze_session_for_concepts(
                    session_id="test_session",
                    history=history,
                    force=False,
                    user_id="test_user",
                )

            # Le LLM ne devrait PAS être appelé (cache hit)
            # Note: result sera vide car le cache hit retourne tôt
            # L'important est que get_structured_llm_response n'ait pas été appelé
            assert analyzer.chat_service.get_structured_llm_response.call_count == 0, (
                "Le LLM ne devrait pas être appelé en cas de cache hit"
            )
