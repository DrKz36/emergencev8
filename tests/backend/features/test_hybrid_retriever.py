# tests/backend/features/test_hybrid_retriever.py
# Tests unitaires pour HybridRetriever (BM25 + Vector)
"""
Tests du module de RAG hybride (P1.5 - Émergence V8)
"""

import pytest
from backend.features.memory.hybrid_retriever import BM25Scorer, HybridRetriever


class TestBM25Scorer:
    """Tests du scorer BM25 (Okapi BM25)"""

    def test_bm25_scorer_basic(self):
        """Test scoring BM25 simple"""
        corpus = [
            "Le chat mange des croquettes",
            "Le chien aime jouer au parc",
            "Les croquettes pour chat sont nutritives"
        ]

        scorer = BM25Scorer(corpus, k1=1.5, b=0.75)
        scores = scorer.get_scores("chat croquettes")

        # Vérifications
        assert len(scores) == 3, "Devrait retourner 3 scores"
        assert all(isinstance(s, float) for s in scores), "Tous les scores doivent être des floats"

        # Doc 0 et 2 devraient avoir des scores plus élevés (contiennent "chat" et "croquettes")
        assert scores[0] > 0, "Doc 0 devrait avoir un score > 0"
        assert scores[2] > 0, "Doc 2 devrait avoir un score > 0"
        assert scores[1] >= 0, "Doc 1 peut avoir score 0 ou faible"

    def test_bm25_scorer_empty_query(self):
        """Test avec requête vide"""
        corpus = ["texte un", "texte deux"]
        scorer = BM25Scorer(corpus)
        scores = scorer.get_scores("")

        assert scores == [0.0, 0.0], "Requête vide → scores nuls"

    def test_bm25_scorer_single_doc(self):
        """Test avec un seul document"""
        corpus = ["document unique"]
        scorer = BM25Scorer(corpus)
        scores = scorer.get_scores("document")

        assert len(scores) == 1
        assert scores[0] > 0, "Document devrait scorer"


class TestHybridRetriever:
    """Tests du retriever hybride BM25 + Vector"""

    def test_hybrid_retriever_alpha_extremes(self):
        """Test avec alpha=0 (full BM25) et alpha=1 (full vector)"""
        corpus = [
            "Le chat mange des croquettes",
            "Le chien aime jouer au parc",
        ]

        # Simuler des résultats vectoriels
        vector_results = [
            {"text": corpus[0], "metadata": {}, "distance": 0.2},  # Proche
            {"text": corpus[1], "metadata": {}, "distance": 0.8},  # Loin
        ]

        # Alpha=0 : Full BM25
        retriever_bm25 = HybridRetriever(alpha=0.0, top_k=2)
        results_bm25 = retriever_bm25.retrieve("chat croquettes", corpus, vector_results)

        assert len(results_bm25) <= 2
        assert all("score" in r for r in results_bm25)
        assert all("bm25_score" in r for r in results_bm25)
        assert all("vector_score" in r for r in results_bm25)

        # Alpha=1 : Full Vector
        retriever_vector = HybridRetriever(alpha=1.0, top_k=2)
        results_vector = retriever_vector.retrieve("chat croquettes", corpus, vector_results)

        assert len(results_vector) <= 2
        # Avec alpha=1, le score vectoriel domine
        if len(results_vector) == 2:
            # Doc 0 (distance=0.2) devrait scorer mieux que Doc 1 (distance=0.8)
            assert results_vector[0]["vector_score"] >= results_vector[1]["vector_score"]

    def test_hybrid_retriever_threshold(self):
        """Test du seuil de score (RAG strict)"""
        corpus = [
            "très pertinent",
            "peu pertinent"
        ]

        vector_results = [
            {"text": corpus[0], "metadata": {}, "distance": 0.1},
            {"text": corpus[1], "metadata": {}, "distance": 0.9},
        ]

        # Seuil élevé : ne retient que les meilleurs
        retriever = HybridRetriever(alpha=0.5, score_threshold=0.5, top_k=5)
        results = retriever.retrieve("pertinent", corpus, vector_results)

        # Tous les résultats doivent avoir score >= threshold
        for r in results:
            assert r["score"] >= 0.5, f"Score {r['score']} < threshold 0.5"

    def test_hybrid_retriever_empty_corpus(self):
        """Test avec corpus vide"""
        retriever = HybridRetriever()
        results = retriever.retrieve("query", [], [])

        assert results == [], "Corpus vide → aucun résultat"

    def test_hybrid_retriever_top_k(self):
        """Test limitation top_k"""
        corpus = [f"document {i}" for i in range(10)]
        vector_results = [
            {"text": text, "metadata": {}, "distance": 0.1 * i}
            for i, text in enumerate(corpus)
        ]

        retriever = HybridRetriever(top_k=3)
        results = retriever.retrieve("document", corpus, vector_results)

        assert len(results) <= 3, "top_k=3 → max 3 résultats"

    def test_hybrid_retriever_score_range(self):
        """Test que les scores sont normalisés dans [0, 1]"""
        corpus = ["texte A", "texte B"]
        vector_results = [
            {"text": corpus[0], "metadata": {}, "distance": 0.5},
            {"text": corpus[1], "metadata": {}, "distance": 0.5},
        ]

        retriever = HybridRetriever(alpha=0.5)
        results = retriever.retrieve("texte", corpus, vector_results)

        for r in results:
            assert 0.0 <= r["score"] <= 1.0, "Score doit être dans [0, 1]"
            assert 0.0 <= r["bm25_score"] <= 1.0, "BM25 score doit être dans [0, 1]"
            assert 0.0 <= r["vector_score"] <= 1.0, "Vector score doit être dans [0, 1]"


class TestHybridRetrieverIntegration:
    """Tests d'intégration (nécessitent VectorService)"""

    @pytest.mark.skipif(True, reason="Nécessite VectorService initialisé")
    def test_hybrid_query_with_vector_service(self):
        """Test intégration complète avec VectorService"""
        # Ce test nécessite un VectorService réel initialisé
        # À implémenter dans l'environnement de test E2E
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
