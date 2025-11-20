# tests/backend/features/memory/test_weighted_retrieval.py
"""
Tests unitaires pour le système de retrieval pondéré par l'horodatage.

Couvre :
- compute_memory_score() avec différents paramètres
- MemoryConfig (chargement fichier + env)
- VectorService.query_weighted()
- Mise à jour automatique de last_used_at et use_count
"""

import os
import pytest
import tempfile
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

from backend.features.memory.vector_service import (
    compute_memory_score,
    MemoryConfig,
    VectorService,
)


class TestComputeMemoryScore:
    """Tests pour la fonction compute_memory_score()."""

    def test_recent_highly_used_memory(self):
        """Mémoire récente très utilisée → score élevé."""
        score = compute_memory_score(
            cosine_sim=0.85,
            delta_days=2.0,
            freq=10,
            lambda_=0.02,
            alpha=0.1,
        )
        # Attendu : ~1.615 (0.85 × 0.96 × 2.0)
        assert score > 1.5, f"Score devrait être > 1.5, got {score}"
        assert score < 2.0, f"Score devrait être < 2.0, got {score}"

    def test_old_rarely_used_memory(self):
        """Mémoire ancienne peu utilisée → score faible."""
        score = compute_memory_score(
            cosine_sim=0.85,
            delta_days=100.0,
            freq=1,
            lambda_=0.02,
            alpha=0.1,
        )
        # Attendu : ~0.115 (0.85 × 0.135 × 1.1)
        assert score < 0.2, f"Score devrait être < 0.2, got {score}"

    def test_old_but_frequently_used_memory(self):
        """Mémoire ancienne mais très utilisée → score moyen (renforcement compense)."""
        score = compute_memory_score(
            cosine_sim=0.85,
            delta_days=50.0,
            freq=20,
            lambda_=0.02,
            alpha=0.1,
        )
        # Attendu : ~0.864 (0.85 × 0.37 × 3.0)
        assert 0.7 < score < 1.2, f"Score devrait être entre 0.7 et 1.2, got {score}"

    def test_decay_rate_impact(self):
        """Plus λ est élevé, plus l'oubli est rapide."""
        # λ faible (0.01) → oubli lent
        score_slow = compute_memory_score(
            0.8, delta_days=50, freq=5, lambda_=0.01, alpha=0.1
        )

        # λ élevé (0.05) → oubli rapide
        score_fast = compute_memory_score(
            0.8, delta_days=50, freq=5, lambda_=0.05, alpha=0.1
        )

        assert score_slow > score_fast, (
            "λ=0.01 devrait donner un score plus élevé que λ=0.05"
        )

    def test_reinforcement_impact(self):
        """Plus α est élevé, plus la fréquence booste le score."""
        # α faible (0.05)
        score_low_alpha = compute_memory_score(
            0.8, delta_days=10, freq=10, lambda_=0.02, alpha=0.05
        )

        # α élevé (0.2)
        score_high_alpha = compute_memory_score(
            0.8, delta_days=10, freq=10, lambda_=0.02, alpha=0.2
        )

        assert score_high_alpha > score_low_alpha, (
            "α=0.2 devrait donner un score plus élevé que α=0.05"
        )

    def test_zero_frequency(self):
        """Fréquence 0 (jamais utilisé) → pas de boost."""
        score = compute_memory_score(
            cosine_sim=0.8,
            delta_days=10,
            freq=0,
            lambda_=0.02,
            alpha=0.1,
        )
        # Devrait être : 0.8 × exp(-0.02 × 10) × (1 + 0.1 × 0) = 0.8 × 0.819 × 1 = 0.655
        expected = 0.8 * 0.819 * 1.0
        assert abs(score - expected) < 0.05, (
            f"Score devrait être ~{expected}, got {score}"
        )

    def test_negative_delta_days_clamped(self):
        """Δt négatif (impossible) → clamped à 0."""
        score = compute_memory_score(
            cosine_sim=0.8,
            delta_days=-10.0,  # Impossible en pratique
            freq=5,
            lambda_=0.02,
            alpha=0.1,
        )
        # Devrait être traité comme delta_days=0
        score_zero = compute_memory_score(
            0.8, delta_days=0.0, freq=5, lambda_=0.02, alpha=0.1
        )
        assert abs(score - score_zero) < 0.001, "Δt négatif devrait être clamped à 0"

    def test_invalid_cosine_sim_clamped(self):
        """Cosine sim > 1 ou < 0 → clamped à [0, 1]."""
        # Cosine > 1 (impossible)
        score_high = compute_memory_score(
            1.5, delta_days=5, freq=3, lambda_=0.02, alpha=0.1
        )
        score_valid = compute_memory_score(
            1.0, delta_days=5, freq=3, lambda_=0.02, alpha=0.1
        )
        assert abs(score_high - score_valid) < 0.001, (
            "Cosine > 1 devrait être clamped à 1.0"
        )

        # Cosine < 0 (impossible)
        score_low = compute_memory_score(
            -0.5, delta_days=5, freq=3, lambda_=0.02, alpha=0.1
        )
        assert score_low == 0.0, "Cosine < 0 devrait être clamped à 0.0"


class TestMemoryConfig:
    """Tests pour la classe MemoryConfig."""

    def test_default_values(self):
        """Config par défaut si aucun fichier."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "nonexistent.json")
            config = MemoryConfig(config_path=config_path)

            assert config.decay_lambda == 0.02
            assert config.reinforcement_alpha == 0.1
            assert config.top_k == 8
            assert config.score_threshold == 0.2
            assert config.enable_trace_logging is False
            assert config.gc_inactive_days == 180

    def test_load_from_json(self):
        """Chargement depuis fichier JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "memory_config.json")
            config_data = {
                "default": {
                    "decay_lambda": 0.05,
                    "reinforcement_alpha": 0.2,
                    "top_k": 10,
                    "score_threshold": 0.3,
                    "enable_trace_logging": True,
                    "gc_inactive_days": 90,
                }
            }

            with open(config_path, "w") as f:
                json.dump(config_data, f)

            config = MemoryConfig(config_path=config_path)

            assert config.decay_lambda == 0.05
            assert config.reinforcement_alpha == 0.2
            assert config.top_k == 10
            assert config.score_threshold == 0.3
            assert config.enable_trace_logging is True
            assert config.gc_inactive_days == 90

    def test_load_from_env_variables(self):
        """Override depuis variables d'environnement."""
        with patch.dict(
            os.environ,
            {
                "MEMORY_DECAY_LAMBDA": "0.03",
                "MEMORY_REINFORCEMENT_ALPHA": "0.15",
                "MEMORY_TOP_K": "12",
                "MEMORY_TRACE_LOGGING": "1",
            },
        ):
            config = MemoryConfig.from_env()

            assert config.decay_lambda == 0.03
            assert config.reinforcement_alpha == 0.15
            assert config.top_k == 12
            assert config.enable_trace_logging is True

    def test_invalid_json_fallback_to_defaults(self):
        """JSON invalide → fallback sur valeurs par défaut."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "invalid.json")

            with open(config_path, "w") as f:
                f.write("{ invalid json }")

            config = MemoryConfig(config_path=config_path)

            # Devrait fallback sur defaults
            assert config.decay_lambda == 0.02
            assert config.top_k == 8


class TestVectorServiceWeightedRetrieval:
    """Tests d'intégration pour VectorService.query_weighted()."""

    @pytest.fixture
    def mock_vector_service(self):
        """Crée un VectorService mocké pour tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = VectorService(
                persist_directory=tmpdir,
                embed_model_name="sentence-transformers/all-MiniLM-L6-v2",
            )
            # Mock lazy init pour éviter de charger le modèle réel
            service.model = Mock()
            service.client = Mock()
            service._inited = True

            yield service

    def test_query_weighted_basic(self, mock_vector_service):
        """Test basique de query_weighted()."""
        # Mock collection
        mock_collection = Mock()
        mock_collection.name = "test_collection"

        # Mock query standard pour retourner des résultats
        now = datetime.now(timezone.utc)
        past_used = (now - timedelta(days=10)).isoformat()

        mock_results = [
            {
                "id": "entry_1",
                "text": "CI/CD pipeline",
                "metadata": {
                    "last_used_at": past_used,
                    "use_count": 5,
                    "user_id": "user123",
                },
                "distance": 0.3,  # cosine_sim = 1 - 0.3/2 = 0.85
            },
            {
                "id": "entry_2",
                "text": "Docker containers",
                "metadata": {
                    "last_used_at": None,  # Jamais utilisé
                    "use_count": 0,
                    "user_id": "user123",
                },
                "distance": 0.4,  # cosine_sim = 0.8
            },
        ]

        mock_vector_service.query = Mock(return_value=mock_results)
        mock_vector_service._update_retrieval_metadata = Mock()

        # Appel (désactiver score_threshold pour ce test)
        results = mock_vector_service.query_weighted(
            collection=mock_collection,
            query_text="pipeline deployment",
            n_results=2,
            score_threshold=0.0,  # Pas de filtrage par score pour ce test
        )

        # Vérifications
        assert len(results) == 2
        assert all("weighted_score" in r for r in results)
        assert all("cosine_sim" in r for r in results)

        # Le premier résultat devrait avoir un meilleur score (récent + utilisé)
        assert results[0]["id"] == "entry_1", (
            "Entry 1 devrait être premier (plus utilisé)"
        )
        assert results[0]["weighted_score"] > results[1]["weighted_score"]

        # Vérifier que update_metadata a été appelé
        mock_vector_service._update_retrieval_metadata.assert_called_once()

    def test_query_weighted_with_trace(self, mock_vector_service):
        """Test du mode trace activé."""
        mock_collection = Mock()
        mock_collection.name = "test_collection"

        now = datetime.now(timezone.utc)
        mock_results = [
            {
                "id": "entry_1",
                "text": "Test",
                "metadata": {
                    "last_used_at": (now - timedelta(days=5)).isoformat(),
                    "use_count": 3,
                },
                "distance": 0.2,
            }
        ]

        mock_vector_service.query = Mock(return_value=mock_results)
        mock_vector_service._update_retrieval_metadata = Mock()

        # Activer trace
        results = mock_vector_service.query_weighted(
            collection=mock_collection,
            query_text="test query",
            enable_trace=True,
        )

        assert len(results) > 0
        assert "trace_info" in results[0]
        trace = results[0]["trace_info"]
        assert "cosine_sim" in trace
        assert "delta_days" in trace
        assert "use_count" in trace
        assert "weighted_score" in trace

    def test_query_weighted_score_threshold(self, mock_vector_service):
        """Test du seuil de score minimum."""
        mock_collection = Mock()
        mock_collection.name = "test_collection"

        # Résultats avec scores très faibles
        mock_results = [
            {
                "id": "entry_1",
                "text": "Low score",
                "metadata": {
                    "last_used_at": None,  # Jamais utilisé
                    "use_count": 0,
                },
                "distance": 1.8,  # cosine_sim = 1 - 1.8/2 = 0.1 (très faible)
            }
        ]

        mock_vector_service.query = Mock(return_value=mock_results)
        mock_vector_service._update_retrieval_metadata = Mock()

        # Seuil élevé (0.5)
        results = mock_vector_service.query_weighted(
            collection=mock_collection,
            query_text="test",
            score_threshold=0.5,
        )

        # Aucun résultat ne devrait passer le seuil
        assert len(results) == 0

    def test_update_retrieval_metadata(self, mock_vector_service):
        """Test de _update_retrieval_metadata()."""
        mock_collection = Mock()
        mock_collection.name = "test_collection"

        results = [
            {
                "id": "entry_1",
                "metadata": {
                    "user_id": "user123",
                    "use_count": 5,
                },
            },
            {
                "id": "entry_2",
                "metadata": {
                    "user_id": "user123",
                    "use_count": 0,
                },
            },
        ]

        mock_vector_service.update_metadatas = Mock()

        # Appel
        mock_vector_service._update_retrieval_metadata(
            collection=mock_collection,
            results=results,
        )

        # Vérifier que update_metadatas a été appelé
        mock_vector_service.update_metadatas.assert_called_once()

        # Vérifier les arguments
        call_args = mock_vector_service.update_metadatas.call_args
        ids = call_args.kwargs["ids"]
        metadatas = call_args.kwargs["metadatas"]

        assert len(ids) == 2
        assert ids == ["entry_1", "entry_2"]

        # Vérifier que use_count a été incrémenté
        assert metadatas[0]["use_count"] == 6  # 5 + 1
        assert metadatas[1]["use_count"] == 1  # 0 + 1

        # Vérifier que last_used_at a été mis à jour
        assert "last_used_at" in metadatas[0]
        assert "last_used_at" in metadatas[1]

        # Vérifier format ISO
        datetime.fromisoformat(metadatas[0]["last_used_at"])  # Should not raise


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
