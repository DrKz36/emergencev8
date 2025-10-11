# src/backend/features/memory/rag_metrics.py
# Prometheus metrics for RAG hybrid system

"""
Prometheus metrics tracking for RAG hybrid retrieval system.

Métriques exposées :
- rag_queries_hybrid_total : Compteur de requêtes hybrides (BM25 + vectoriel)
- rag_queries_vector_only_total : Compteur de requêtes vectorielles pures
- rag_queries_bm25_only_total : Compteur de requêtes BM25 pures
- rag_avg_score : Gauge du score moyen de pertinence
- rag_results_filtered_total : Compteur de résultats filtrés par seuil
- rag_query_duration_seconds : Histogramme de la durée des requêtes
"""

import logging
from prometheus_client import Counter, Gauge, Histogram
from typing import Optional

logger = logging.getLogger(__name__)

# ============================================================
# Métriques Prometheus
# ============================================================

# Compteurs de requêtes par type
rag_queries_hybrid_total = Counter(
    'rag_queries_hybrid_total',
    'Total number of hybrid RAG queries (BM25 + vector)',
    ['collection', 'status']  # Labels: collection name, status (success/error)
)

rag_queries_vector_only_total = Counter(
    'rag_queries_vector_only_total',
    'Total number of vector-only RAG queries',
    ['collection', 'status']
)

rag_queries_bm25_only_total = Counter(
    'rag_queries_bm25_only_total',
    'Total number of BM25-only queries',
    ['collection', 'status']
)

# Score moyen de pertinence
rag_avg_score = Gauge(
    'rag_avg_score',
    'Average relevance score of RAG results',
    ['collection', 'query_type']  # Labels: collection, query_type (hybrid/vector/bm25)
)

# Résultats filtrés par seuil
rag_results_filtered_total = Counter(
    'rag_results_filtered_total',
    'Total number of results filtered by score threshold',
    ['collection', 'reason']  # Labels: collection, reason (below_threshold/empty_result)
)

# Durée des requêtes
rag_query_duration_seconds = Histogram(
    'rag_query_duration_seconds',
    'Duration of RAG query execution in seconds',
    ['collection', 'query_type'],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5]
)

# Nombre de résultats retournés
rag_results_count = Histogram(
    'rag_results_count',
    'Number of results returned by RAG query',
    ['collection', 'query_type'],
    buckets=[0, 1, 2, 5, 10, 20, 50, 100]
)

# Score BM25 vs Vector
rag_score_component = Gauge(
    'rag_score_component',
    'Component scores (BM25 and vector) for hybrid queries',
    ['collection', 'component']  # component: bm25 or vector
)


# ============================================================
# Helpers pour tracking des métriques
# ============================================================

class RAGMetricsTracker:
    """
    Helper class pour tracker facilement les métriques RAG.

    Usage:
        with RAGMetricsTracker("concepts", "hybrid") as tracker:
            results = hybrid_query(...)
            tracker.record_results(results, avg_score=0.85)
    """

    def __init__(self, collection: str, query_type: str = "hybrid"):
        """
        Args:
            collection: Nom de la collection (ex: "concepts", "memories")
            query_type: Type de requête ("hybrid", "vector", "bm25")
        """
        self.collection = collection
        self.query_type = query_type
        self.timer = None
        self.status = "success"

    def __enter__(self):
        """Démarre le timer de durée"""
        self.timer = rag_query_duration_seconds.labels(
            collection=self.collection,
            query_type=self.query_type
        ).time()
        self.timer.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Arrête le timer et enregistre le statut"""
        if exc_type is not None:
            self.status = "error"

        # Incrémenter le compteur approprié
        if self.query_type == "hybrid":
            rag_queries_hybrid_total.labels(
                collection=self.collection,
                status=self.status
            ).inc()
        elif self.query_type == "vector":
            rag_queries_vector_only_total.labels(
                collection=self.collection,
                status=self.status
            ).inc()
        elif self.query_type == "bm25":
            rag_queries_bm25_only_total.labels(
                collection=self.collection,
                status=self.status
            ).inc()

        # Arrêter le timer
        if self.timer:
            self.timer.__exit__(exc_type, exc_val, exc_tb)

    def record_results(self, results: list, avg_score: Optional[float] = None):
        """
        Enregistre les résultats de la requête.

        Args:
            results: Liste des résultats retournés
            avg_score: Score moyen de pertinence (calculé si non fourni)
        """
        # Nombre de résultats
        rag_results_count.labels(
            collection=self.collection,
            query_type=self.query_type
        ).observe(len(results))

        # Score moyen
        if avg_score is None and results:
            scores = [r.get("score", 0) for r in results if isinstance(r, dict)]
            avg_score = sum(scores) / len(scores) if scores else 0.0

        if avg_score is not None:
            rag_avg_score.labels(
                collection=self.collection,
                query_type=self.query_type
            ).set(avg_score)

        # Scores composants pour requêtes hybrides
        if self.query_type == "hybrid" and results:
            bm25_scores = [r.get("bm25_score", 0) for r in results if isinstance(r, dict)]
            vector_scores = [r.get("vector_score", 0) for r in results if isinstance(r, dict)]

            if bm25_scores:
                avg_bm25 = sum(bm25_scores) / len(bm25_scores)
                rag_score_component.labels(
                    collection=self.collection,
                    component="bm25"
                ).set(avg_bm25)

            if vector_scores:
                avg_vector = sum(vector_scores) / len(vector_scores)
                rag_score_component.labels(
                    collection=self.collection,
                    component="vector"
                ).set(avg_vector)

    def record_filtered(self, count: int, reason: str = "below_threshold"):
        """
        Enregistre le nombre de résultats filtrés.

        Args:
            count: Nombre de résultats filtrés
            reason: Raison du filtrage
        """
        rag_results_filtered_total.labels(
            collection=self.collection,
            reason=reason
        ).inc(count)


# ============================================================
# Fonctions utilitaires
# ============================================================

def track_hybrid_query(
    collection: str,
    results: list,
    avg_score: Optional[float] = None,
    filtered_count: int = 0
):
    """
    Shortcut pour tracker une requête hybride sans context manager.

    Args:
        collection: Nom de la collection
        results: Résultats retournés
        avg_score: Score moyen (calculé si non fourni)
        filtered_count: Nombre de résultats filtrés
    """
    # Compter la requête
    rag_queries_hybrid_total.labels(
        collection=collection,
        status="success"
    ).inc()

    # Résultats
    rag_results_count.labels(
        collection=collection,
        query_type="hybrid"
    ).observe(len(results))

    # Score moyen
    if avg_score is None and results:
        scores = [r.get("score", 0) for r in results if isinstance(r, dict)]
        avg_score = sum(scores) / len(scores) if scores else 0.0

    if avg_score is not None:
        rag_avg_score.labels(
            collection=collection,
            query_type="hybrid"
        ).set(avg_score)

    # Résultats filtrés
    if filtered_count > 0:
        rag_results_filtered_total.labels(
            collection=collection,
            reason="below_threshold"
        ).inc(filtered_count)

    logger.debug(
        f"RAG metrics tracked: collection={collection}, "
        f"results={len(results)}, avg_score={avg_score:.3f if avg_score else 0}, "
        f"filtered={filtered_count}"
    )


def get_rag_metrics_summary(collection: Optional[str] = None) -> dict:
    """
    Récupère un résumé des métriques RAG actuelles.

    Args:
        collection: Filtrer par collection (optionnel)

    Returns:
        Dict avec le résumé des métriques
    """
    # Note: Cette fonction nécessite l'accès au registre Prometheus
    # Pour une implémentation complète, utiliser prometheus_client.REGISTRY
    # Ici on retourne un placeholder pour l'API

    return {
        "hybrid_queries_total": 0,  # À implémenter avec REGISTRY.get_sample_value()
        "avg_score": 0.0,
        "filtered_results": 0,
        "success_rate": 1.0,
    }


# ============================================================
# Export
# ============================================================

__all__ = [
    "RAGMetricsTracker",
    "track_hybrid_query",
    "get_rag_metrics_summary",
    "rag_queries_hybrid_total",
    "rag_queries_vector_only_total",
    "rag_queries_bm25_only_total",
    "rag_avg_score",
    "rag_results_filtered_total",
    "rag_query_duration_seconds",
    "rag_results_count",
    "rag_score_component",
]
