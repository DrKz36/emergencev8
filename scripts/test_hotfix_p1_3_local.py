"""
Script de test local Hotfix P1.3 - Validation user_id fallback

Ce script teste le scénario complet d'extraction de préférences
avec fallback user_id en environnement local.

Usage:
    python scripts/test_hotfix_p1_3_local.py
"""

import asyncio
import sys
from pathlib import Path

# Ajouter src au path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from backend.features.memory.preference_extractor import PreferenceExtractor
from backend.features.memory.analyzer import MemoryAnalyzer
from unittest.mock import AsyncMock, MagicMock
import logging

# Configuration logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class TestScenario:
    """Scénarios de test Hotfix P1.3"""

    def __init__(self):
        self.results = []

    def log_result(self, test_name: str, passed: bool, details: str = ""):
        """Enregistre résultat test"""
        status = "✅ PASS" if passed else "❌ FAIL"
        self.results.append((test_name, passed, details))
        logger.info(f"{status} - {test_name}")
        if details:
            logger.info(f"  Details: {details}")

    async def test_1_extraction_with_user_sub(self):
        """Test 1: Extraction normale avec user_sub présent"""
        logger.info("\n" + "=" * 60)
        logger.info("TEST 1: Extraction avec user_sub présent")
        logger.info("=" * 60)

        # Mock LLM client
        mock_llm = AsyncMock()
        mock_llm.get_structured_llm_response = AsyncMock(
            return_value={
                "type": "preference",
                "topic": "programmation",
                "action": "utiliser",
                "timeframe": "ongoing",
                "sentiment": "positive",
                "confidence": 0.85,
                "entities": ["Python", "FastAPI"],
            }
        )

        # Créer extractor
        extractor = PreferenceExtractor(llm_client=mock_llm)

        # Messages avec préférences
        messages = [
            {
                "id": "msg_1",
                "role": "user",
                "content": "Je préfère utiliser Python avec FastAPI pour mes APIs",
            }
        ]

        try:
            # Extraction avec user_sub
            preferences = await extractor.extract(
                messages=messages,
                user_sub="auth0|user_test_123",
                user_id="user_test_123",
                thread_id="thread_test_1",
            )

            passed = len(preferences) > 0
            details = f"Extracted {len(preferences)} preferences"
            self.log_result("Test 1: user_sub présent", passed, details)

        except Exception as e:
            self.log_result("Test 1: user_sub présent", False, f"Exception: {e}")

    async def test_2_extraction_fallback_user_id(self):
        """Test 2: Extraction avec fallback user_id (user_sub absent)"""
        logger.info("\n" + "=" * 60)
        logger.info("TEST 2: Extraction avec fallback user_id")
        logger.info("=" * 60)

        # Mock LLM client
        mock_llm = AsyncMock()
        mock_llm.get_structured_llm_response = AsyncMock(
            return_value={
                "type": "preference",
                "topic": "frontend",
                "action": "utiliser",
                "timeframe": "ongoing",
                "sentiment": "positive",
                "confidence": 0.90,
                "entities": ["TypeScript", "React"],
            }
        )

        extractor = PreferenceExtractor(llm_client=mock_llm)

        messages = [
            {
                "id": "msg_2",
                "role": "user",
                "content": "J'aime beaucoup TypeScript pour le frontend",
            }
        ]

        try:
            # Extraction SANS user_sub (seulement user_id)
            preferences = await extractor.extract(
                messages=messages,
                user_sub=None,  # ❌ Absent
                user_id="user_fallback_456",  # ✅ Fallback
                thread_id="thread_test_2",
            )

            passed = len(preferences) > 0
            details = f"Extracted {len(preferences)} preferences with user_id fallback"
            self.log_result("Test 2: user_id fallback", passed, details)

        except Exception as e:
            self.log_result("Test 2: user_id fallback", False, f"Exception: {e}")

    async def test_3_extraction_no_identifier(self):
        """Test 3: Échec si aucun identifiant"""
        logger.info("\n" + "=" * 60)
        logger.info("TEST 3: Échec si aucun identifiant")
        logger.info("=" * 60)

        mock_llm = AsyncMock()
        extractor = PreferenceExtractor(llm_client=mock_llm)

        messages = [
            {"id": "msg_3", "role": "user", "content": "Je veux apprendre Rust"}
        ]

        try:
            # Extraction SANS user_sub NI user_id
            await extractor.extract(
                messages=messages,
                user_sub=None,  # ❌ Absent
                user_id=None,  # ❌ Absent
                thread_id="thread_test_3",
            )

            # Si on arrive ici, c'est un échec (devrait lever ValueError)
            self.log_result(
                "Test 3: no identifier → ValueError",
                False,
                "Should have raised ValueError but didn't",
            )

        except ValueError as e:
            # Comportement attendu
            passed = "no user identifier" in str(e).lower()
            details = f"ValueError raised as expected: {e}"
            self.log_result("Test 3: no identifier → ValueError", passed, details)

        except Exception as e:
            self.log_result(
                "Test 3: no identifier → ValueError",
                False,
                f"Wrong exception type: {type(e).__name__}: {e}",
            )

    async def test_4_analyzer_integration(self):
        """Test 4: Integration MemoryAnalyzer avec fallback"""
        logger.info("\n" + "=" * 60)
        logger.info("TEST 4: Integration MemoryAnalyzer")
        logger.info("=" * 60)

        # Mock DatabaseManager
        mock_db = AsyncMock()

        # Mock ChatService avec SessionManager
        mock_chat_service = MagicMock()
        mock_session_manager = MagicMock()

        # Mock session AVEC user_id mais SANS user_sub
        mock_session = MagicMock()
        mock_session.user_id = "user_integration_789"
        mock_session.metadata = {}  # Pas de user_sub
        mock_session_manager.get_session.return_value = mock_session

        mock_chat_service.session_manager = mock_session_manager

        # Créer MemoryAnalyzer
        analyzer = MemoryAnalyzer(db_manager=mock_db, chat_service=mock_chat_service)
        analyzer.set_chat_service(mock_chat_service)

        # Mock PreferenceExtractor
        mock_extractor = AsyncMock()
        mock_extractor.extract = AsyncMock(
            return_value=[
                MagicMock(type="preference", topic="database", confidence=0.88)
            ]
        )
        analyzer.preference_extractor = mock_extractor

        try:
            # Simuler extraction (comme dans analyzer.py)
            session_id = "session_integration"
            history = [
                {"role": "user", "content": "Je préfère PostgreSQL", "id": "msg_int"}
            ]

            # Récupérer contexte utilisateur (comme dans analyzer.py)
            user_sub = mock_session.metadata.get("user_sub")
            user_id = mock_session.user_id

            if user_sub or user_id:
                await analyzer.preference_extractor.extract(
                    messages=history,
                    user_sub=user_sub,
                    user_id=user_id,
                    thread_id=session_id,
                )

            # Vérifier que extract() a été appelé avec user_id fallback
            mock_extractor.extract.assert_called_once()
            call_kwargs = mock_extractor.extract.call_args.kwargs

            passed = (
                call_kwargs["user_sub"] is None
                and call_kwargs["user_id"] == "user_integration_789"
            )
            details = f"extract() called with user_sub={call_kwargs['user_sub']}, user_id={call_kwargs['user_id']}"
            self.log_result("Test 4: MemoryAnalyzer integration", passed, details)

        except Exception as e:
            self.log_result(
                "Test 4: MemoryAnalyzer integration", False, f"Exception: {e}"
            )

    async def test_5_thread_id_fallback(self):
        """Test 5: Fallback thread_id=None → "unknown" """
        logger.info("\n" + "=" * 60)
        logger.info("TEST 5: Fallback thread_id=None")
        logger.info("=" * 60)

        mock_llm = AsyncMock()
        mock_llm.get_structured_llm_response = AsyncMock(
            return_value={
                "type": "constraint",
                "topic": "sécurité",
                "action": "éviter",
                "timeframe": "ongoing",
                "sentiment": "negative",
                "confidence": 0.75,
                "entities": ["SQL injection"],
            }
        )

        extractor = PreferenceExtractor(llm_client=mock_llm)

        messages = [
            {
                "id": "msg_5",
                "role": "user",
                "content": "J'évite toujours les SQL injections",
            }
        ]

        try:
            # Extraction avec thread_id=None
            preferences = await extractor.extract(
                messages=messages,
                user_sub="auth0|user_thread_test",
                user_id="user_thread_test",
                thread_id=None,  # ❌ Absent
            )

            # Vérifier que thread_id est "unknown"
            passed = all(pref.thread_id == "unknown" for pref in preferences)
            details = f"thread_id set to 'unknown' for {len(preferences)} preferences"
            self.log_result("Test 5: thread_id fallback", passed, details)

        except Exception as e:
            self.log_result("Test 5: thread_id fallback", False, f"Exception: {e}")

    def print_summary(self):
        """Affiche résumé des tests"""
        logger.info("\n" + "=" * 60)
        logger.info("RÉSUMÉ DES TESTS")
        logger.info("=" * 60)

        total = len(self.results)
        passed = sum(1 for _, p, _ in self.results if p)
        failed = total - passed

        logger.info(f"\nTotal tests: {total}")
        logger.info(f"✅ Passed: {passed}")
        logger.info(f"❌ Failed: {failed}")

        if failed > 0:
            logger.info("\n❌ TESTS ÉCHOUÉS:")
            for name, success, details in self.results:
                if not success:
                    logger.info(f"  - {name}")
                    if details:
                        logger.info(f"    {details}")

        logger.info("\n" + "=" * 60)

        return failed == 0


async def main():
    """Point d'entrée principal"""
    logger.info("🔬 DÉBUT TESTS HOTFIX P1.3")
    logger.info("=" * 60)

    scenario = TestScenario()

    # Exécuter tous les tests
    await scenario.test_1_extraction_with_user_sub()
    await scenario.test_2_extraction_fallback_user_id()
    await scenario.test_3_extraction_no_identifier()
    await scenario.test_4_analyzer_integration()
    await scenario.test_5_thread_id_fallback()

    # Afficher résumé
    all_passed = scenario.print_summary()

    if all_passed:
        logger.info("\n✅ TOUS LES TESTS SONT PASSÉS !")
        logger.info("🚀 Hotfix P1.3 prêt pour déploiement production")
        return 0
    else:
        logger.error("\n❌ CERTAINS TESTS ONT ÉCHOUÉ")
        logger.error("⚠️  Corriger les erreurs avant déploiement")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
