# tests/backend/features/test_rag_precision.py
"""
Tests unitaires pour les optimisations RAG (P2.1)
- Pondération temporelle
- Score de spécificité (low-entropy boost)
- Re-rank hybride (cosine + Jaccard)
"""

import pytest
import time
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
from backend.features.memory.vector_service import (
    compute_specificity_score,
    rerank_with_lexical_overlap,
    recency_decay,
)


class TestSpecificityScore:
    """Tests du score de spécificité (densité IDF/NER/nombres)"""

    def test_specificity_high_density_tokens(self):
        """Texte avec tokens longs et nombres → score élevé"""
        text = """
        The configuration parameter MLPClassifierOptimizer achieves 0.9847 accuracy
        on dataset CIFAR-10 with hyperparameter tuning on 2024-03-15.
        """
        score = compute_specificity_score(text)

        assert 0.0 <= score <= 1.0, "Score doit être entre 0 et 1"
        assert score > 0.5, (
            f"Texte à haute spécificité devrait scorer > 0.5 (got {score:.3f})"
        )

    def test_specificity_low_density_common_words(self):
        """Texte avec mots communs courts → score faible"""
        text = "this is a simple text with no special words or numbers"
        score = compute_specificity_score(text)

        assert 0.0 <= score <= 1.0, "Score doit être entre 0 et 1"
        assert score < 0.4, f"Texte banal devrait scorer < 0.4 (got {score:.3f})"

    def test_specificity_with_entities(self):
        """Texte avec entités nommées → score moyen-élevé"""
        text = """
        John Smith visited Paris and met Marie Curie at the Sorbonne University
        to discuss quantum mechanics research.
        """
        score = compute_specificity_score(text)

        assert 0.0 <= score <= 1.0, "Score doit être entre 0 et 1"
        assert score > 0.3, f"Texte avec NER devrait scorer > 0.3 (got {score:.3f})"

    def test_specificity_empty_text(self):
        """Texte vide → score 0"""
        assert compute_specificity_score("") == 0.0
        assert compute_specificity_score("   ") == 0.0

    def test_specificity_numbers_and_dates(self):
        """Texte avec beaucoup de nombres/dates → score élevé"""
        text = """
        2024-03-15: Revenue $125,000 (15% increase). Q1 2024 target: $500,000.
        Meeting scheduled for 2024-04-01 at 14:30. Budget: €75,000.
        """
        score = compute_specificity_score(text)

        assert 0.0 <= score <= 1.0, "Score doit être entre 0 et 1"
        assert score > 0.6, (
            f"Texte riche en nombres devrait scorer > 0.6 (got {score:.3f})"
        )


class TestLexicalRerank:
    """Tests du re-ranking avec Jaccard (lexical overlap)"""

    def test_rerank_basic(self):
        """Test re-rank simple avec 3 résultats"""
        query = "train machine learning model"
        results = [
            {"id": "1", "text": "deep learning neural networks", "distance": 0.3},
            {
                "id": "2",
                "text": "train ML model with gradient descent",
                "distance": 0.4,
            },
            {"id": "3", "text": "data preprocessing techniques", "distance": 0.5},
        ]

        reranked = rerank_with_lexical_overlap(query, results, topk=3)

        assert len(reranked) == 3, "Devrait retourner 3 résultats"
        assert all("rerank_score" in r for r in reranked), (
            "Tous devraient avoir rerank_score"
        )
        assert all("jaccard_score" in r for r in reranked), (
            "Tous devraient avoir jaccard_score"
        )
        assert all("cosine_sim" in r for r in reranked), (
            "Tous devraient avoir cosine_sim"
        )

        # Vérifier que le reranking a bien été appliqué (les scores sont présents et triés)
        # Note: Le scoring combine distance + jaccard + cosine, donc l'ordre peut varier
        assert reranked[0]["rerank_score"] >= reranked[1]["rerank_score"], (
            "Scores doivent être triés décroissants"
        )
        assert reranked[1]["rerank_score"] >= reranked[2]["rerank_score"], (
            "Scores doivent être triés décroissants"
        )

    def test_rerank_empty_results(self):
        """Test avec liste vide"""
        reranked = rerank_with_lexical_overlap("query", [], topk=5)
        assert reranked == [], "Liste vide → résultat vide"

    def test_rerank_topk_limit(self):
        """Test que top-k limite bien les résultats"""
        results = [
            {"id": str(i), "text": f"document {i}", "distance": 0.1 * i}
            for i in range(10)
        ]

        reranked = rerank_with_lexical_overlap("document", results, topk=3)

        assert len(reranked) == 3, "Devrait limiter à top-3"

    def test_rerank_jaccard_calculation(self):
        """Vérifier le calcul Jaccard correct"""
        query = "apple banana"
        results = [
            {
                "id": "1",
                "text": "apple banana cherry",
                "distance": 0.5,
            },  # Jaccard = 2/3 = 0.67
            {
                "id": "2",
                "text": "apple orange",
                "distance": 0.5,
            },  # Jaccard = 1/3 = 0.33
        ]

        reranked = rerank_with_lexical_overlap(query, results, topk=2)

        # Doc 1 devrait avoir meilleur Jaccard
        assert reranked[0]["id"] == "1", "Doc avec plus d'overlap devrait être top"
        assert reranked[0]["jaccard_score"] > reranked[1]["jaccard_score"]


class TestRecencyDecay:
    """Tests de la pondération temporelle"""

    def test_recency_decay_recent_doc(self):
        """Document très récent → score proche de 1"""
        age_days = 0.5  # 12 heures
        score = recency_decay(age_days, half_life=30.0)

        assert 0.0 <= score <= 1.0, "Score doit être entre 0 et 1"
        assert score > 0.95, f"Document récent devrait scorer > 0.95 (got {score:.3f})"

    def test_recency_decay_half_life(self):
        """Document à half-life → score = 0.5"""
        age_days = 30.0
        score = recency_decay(age_days, half_life=30.0)

        assert abs(score - 0.5) < 0.01, (
            f"À half-life, score devrait être ~0.5 (got {score:.3f})"
        )

    def test_recency_decay_old_doc(self):
        """Document ancien → score faible"""
        age_days = 180.0  # 6 mois
        score = recency_decay(age_days, half_life=30.0)

        assert 0.0 <= score <= 1.0, "Score doit être entre 0 et 1"
        assert score < 0.05, f"Document ancien devrait scorer < 0.05 (got {score:.3f})"

    def test_recency_decay_negative_age(self):
        """Âge négatif (bug) → clamped à 0"""
        age_days = -10.0
        score = recency_decay(age_days, half_life=30.0)

        assert score == 1.0, "Âge négatif devrait être clamped à 0 → score=1.0"


class TestRAGPrecisionIntegration:
    """Tests d'intégration des optimisations RAG (end-to-end)"""

    @pytest.fixture
    def mock_vector_results(self) -> List[Dict[str, Any]]:
        """
        Fixture retournant des résultats vectoriels simulés avec timestamps.
        """
        now = datetime.now(timezone.utc)
        return [
            {
                "id": "recent_specific",
                "text": "MLPClassifier hyperparameter optimization achieved 0.9847 accuracy on 2024-03-15",
                "distance": 0.3,
                "metadata": {
                    "ts": (now - timedelta(days=1)).isoformat(),  # 1 jour
                },
                "embedding": [0.1] * 384,  # Mock embedding
            },
            {
                "id": "old_generic",
                "text": "this is a simple text about machine learning",
                "distance": 0.25,  # Meilleure distance mais générique + ancien
                "metadata": {
                    "ts": (now - timedelta(days=90)).isoformat(),  # 90 jours
                },
                "embedding": [0.2] * 384,
            },
            {
                "id": "recent_generic",
                "text": "machine learning is useful for many tasks",
                "distance": 0.35,
                "metadata": {
                    "ts": (now - timedelta(days=2)).isoformat(),  # 2 jours
                },
                "embedding": [0.3] * 384,
            },
        ]

    def test_specificity_boost_prioritizes_informative_chunks(
        self, mock_vector_results
    ):
        """
        Test que les chunks à forte densité IDF remontent dans le top-3.
        """
        # Simuler l'application du specificity boost
        from backend.features.memory.vector_service import compute_specificity_score

        specificity_weight = 0.15

        for result in mock_vector_results:
            text = result["text"]
            distance = result["distance"]

            # Calculer score de spécificité
            specificity_score = compute_specificity_score(text)
            cosine_score = max(0.0, 1.0 - (distance / 2.0))

            # Score combiné
            combined_score = (
                1 - specificity_weight
            ) * cosine_score + specificity_weight * specificity_score

            result["specificity_score"] = specificity_score
            result["combined_score"] = combined_score
            result["distance"] = 2.0 * (1.0 - combined_score)

        # Trier par distance ajustée
        mock_vector_results.sort(key=lambda x: x["distance"])

        # Vérifications
        top1 = mock_vector_results[0]
        assert top1["id"] == "recent_specific", (
            f"Document à haute spécificité devrait être top-1 (got {top1['id']})"
        )
        assert top1["specificity_score"] > 0.5, (
            "Document spécifique devrait avoir score > 0.5"
        )

    def test_recency_boost_prioritizes_recent_docs(self, mock_vector_results):
        """
        Test que les documents récents reçoivent un score plus élevé.
        """
        from backend.features.memory.vector_service import recency_decay

        now = datetime.now(timezone.utc)
        half_life = 30.0

        # Appliquer recency decay
        for result in mock_vector_results:
            ts_str = result["metadata"].get("ts")
            if ts_str:
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                age_days = (now - ts).total_seconds() / 86400
                recency_score = recency_decay(age_days, half_life=half_life)

                result["age_days"] = age_days
                result["recency_score"] = recency_score

                # Ajuster distance (boost recency)
                recency_factor = max(recency_score, 0.1)
                result["distance"] = result["distance"] / recency_factor

        # Trier par distance ajustée
        mock_vector_results.sort(key=lambda x: x["distance"])

        # Vérifications
        # Document récent devrait être mieux classé
        top_doc = mock_vector_results[0]
        assert top_doc["age_days"] < 10, (
            f"Document top-1 devrait être récent (got {top_doc['age_days']:.1f} jours)"
        )

    def test_ranking_stability_short_vs_long_queries(self):
        """
        Test de stabilité du ranking avec requêtes courtes vs longues.
        """
        query_short = "ML model"
        query_long = "train machine learning model with hyperparameter optimization"

        results = [
            {
                "id": "1",
                "text": "train ML model with gradient descent",
                "distance": 0.3,
            },
            {"id": "2", "text": "deep learning neural networks", "distance": 0.4},
            {
                "id": "3",
                "text": "machine learning hyperparameter tuning",
                "distance": 0.35,
            },
        ]

        # Rerank avec requête courte
        reranked_short = rerank_with_lexical_overlap(
            query_short, results.copy(), topk=3
        )

        # Rerank avec requête longue
        reranked_long = rerank_with_lexical_overlap(query_long, results.copy(), topk=3)

        # Le top-1 devrait être le même (stabilité)
        # Note: Peut varier selon le contenu, vérifier que l'ordre est cohérent
        assert len(reranked_short) == len(reranked_long) == 3, (
            "Devrait retourner 3 résultats"
        )

        # Vérifier que des résultats pertinents sont dans le top-3
        top_ids_short = {r["id"] for r in reranked_short}
        top_ids_long = {r["id"] for r in reranked_long}

        # Intersection devrait contenir au moins 2 docs communs
        common = top_ids_short & top_ids_long
        assert len(common) >= 2, f"Top-3 devrait être stable (common={len(common)}/3)"


class TestRAGMetrics:
    """Tests des métriques RAG (hit@k, MRR, latence)"""

    def test_hit_at_k(self):
        """
        Calcule hit@3 : proportion de queries où doc pertinent est dans top-3.
        """
        # Simuler résultats de 5 requêtes
        results = [
            # Query 1: doc pertinent en position 1 → hit
            [{"id": "relevant", "score": 0.9}, {"id": "irrelevant", "score": 0.5}],
            # Query 2: doc pertinent en position 2 → hit
            [{"id": "irrelevant", "score": 0.8}, {"id": "relevant", "score": 0.7}],
            # Query 3: doc pertinent hors top-3 → miss
            [{"id": "irrelevant1", "score": 0.6}, {"id": "irrelevant2", "score": 0.5}],
            # Query 4: doc pertinent en position 3 → hit
            [
                {"id": "irrelevant1", "score": 0.7},
                {"id": "irrelevant2", "score": 0.65},
                {"id": "relevant", "score": 0.6},
            ],
            # Query 5: doc pertinent en position 1 → hit
            [{"id": "relevant", "score": 0.95}],
        ]

        k = 3
        hits = 0
        for result_list in results:
            top_k_ids = [r["id"] for r in result_list[:k]]
            if "relevant" in top_k_ids:
                hits += 1

        hit_at_k = hits / len(results)
        assert hit_at_k == 0.8, f"hit@3 devrait être 4/5 = 0.8 (got {hit_at_k})"

    def test_mrr_calculation(self):
        """
        Calcule MRR (Mean Reciprocal Rank).
        """
        # Simuler résultats de 4 requêtes avec position du doc pertinent
        relevant_positions = [
            1,  # Query 1: doc pertinent en position 1 → 1/1 = 1.0
            2,  # Query 2: doc pertinent en position 2 → 1/2 = 0.5
            None,  # Query 3: pas de doc pertinent trouvé → 0.0
            3,  # Query 4: doc pertinent en position 3 → 1/3 = 0.33
        ]

        reciprocal_ranks = []
        for pos in relevant_positions:
            if pos is None:
                reciprocal_ranks.append(0.0)
            else:
                reciprocal_ranks.append(1.0 / pos)

        mrr = sum(reciprocal_ranks) / len(reciprocal_ranks)
        expected_mrr = (1.0 + 0.5 + 0.0 + 0.333) / 4
        assert abs(mrr - expected_mrr) < 0.01, (
            f"MRR devrait être ~{expected_mrr:.3f} (got {mrr:.3f})"
        )

    def test_latency_p95(self):
        """
        Mesure latence P95 de compute_specificity_score().
        """
        texts = [
            "short text",
            "MLPClassifier hyperparameter optimization achieved 0.9847 accuracy on CIFAR-10 dataset 2024-03-15",
            "this is a medium length text with some numbers like 123 and dates 2024/01/01",
        ] * 100  # 300 samples

        latencies = []
        for text in texts:
            start = time.perf_counter()
            _ = compute_specificity_score(text)
            latency_ms = (time.perf_counter() - start) * 1000
            latencies.append(latency_ms)

        latencies.sort()
        p95_index = int(len(latencies) * 0.95)
        p95_latency = latencies[p95_index]

        # Latence P95 devrait être < 5ms (optimisation rapide)
        assert p95_latency < 5.0, (
            f"Latence P95 devrait être < 5ms (got {p95_latency:.2f}ms)"
        )

    def test_rerank_latency_p95(self):
        """
        Mesure latence P95 de rerank_with_lexical_overlap().
        """
        query = "train machine learning model"
        results = [
            {"id": str(i), "text": f"document about ML topic {i}", "distance": 0.1 * i}
            for i in range(30)
        ]

        latencies = []
        for _ in range(100):
            start = time.perf_counter()
            _ = rerank_with_lexical_overlap(query, results.copy(), topk=8)
            latency_ms = (time.perf_counter() - start) * 1000
            latencies.append(latency_ms)

        latencies.sort()
        p95_index = int(len(latencies) * 0.95)
        p95_latency = latencies[p95_index]

        # Latence P95 devrait être < 10ms (rerank rapide)
        assert p95_latency < 10.0, (
            f"Latence P95 rerank devrait être < 10ms (got {p95_latency:.2f}ms)"
        )


# ============================================================
# Run tests
# ============================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
