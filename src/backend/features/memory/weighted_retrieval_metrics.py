# src/backend/features/memory/weighted_retrieval_metrics.py
# V1.0 - Métriques Prometheus pour retrieval pondéré
#
# Objectif: Monitoring détaillé du système de mémoire pondérée
# - Latence scoring
# - Distribution des scores
# - Taux de cache hit/miss
# - Fréquence GC
#
# Date création: 2025-10-21

import logging
from typing import Any, Optional, cast

logger = logging.getLogger(__name__)

# Prometheus metrics
try:
    from prometheus_client import Counter, Histogram, Gauge, REGISTRY

    def _get_or_create_counter(name: str, doc: str, labels: list[str]) -> Counter:
        try:
            return Counter(name, doc, labels, registry=REGISTRY)
        except ValueError:
            existing = getattr(REGISTRY, "_names_to_collectors", {}).get(name)
            if existing is None:
                raise
            return cast(Counter, existing)

    def _get_or_create_histogram(
        name: str,
        doc: str,
        labels: list[str],
        buckets: Optional[tuple[float, ...]] = None,
    ) -> Histogram:
        try:
            kwargs: dict[str, Any] = {"registry": REGISTRY}
            if buckets:
                kwargs["buckets"] = buckets
            return Histogram(name, doc, labels, **kwargs)
        except ValueError:
            existing = getattr(REGISTRY, "_names_to_collectors", {}).get(name)
            if existing is None:
                raise
            return cast(Histogram, existing)

    def _get_or_create_gauge(
        name: str, doc: str, labels: Optional[list[str]] = None
    ) -> Gauge:
        try:
            if labels:
                return Gauge(name, doc, labels, registry=REGISTRY)
            else:
                return Gauge(name, doc, registry=REGISTRY)
        except ValueError:
            existing = getattr(REGISTRY, "_names_to_collectors", {}).get(name)
            if existing is None:
                raise
            return cast(Gauge, existing)

    # Métriques latence scoring
    WEIGHTED_SCORING_DURATION = _get_or_create_histogram(
        "weighted_scoring_duration_seconds",
        "Durée calcul score pondéré par entrée",
        ["collection"],
        buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0),
    )

    # Distribution des scores
    WEIGHTED_SCORE_DISTRIBUTION = _get_or_create_histogram(
        "weighted_score_distribution",
        "Distribution des scores pondérés",
        ["collection"],
        buckets=(0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0),
    )

    # Métriques requêtes
    WEIGHTED_QUERY_TOTAL = _get_or_create_counter(
        "weighted_query_requests_total",
        "Nombre requêtes query_weighted",
        ["collection", "status"],  # status: success/error
    )

    WEIGHTED_QUERY_RESULTS = _get_or_create_histogram(
        "weighted_query_results_count",
        "Nombre résultats par requête",
        ["collection"],
        buckets=(0, 1, 5, 10, 20, 50, 100),
    )

    # Métriques métadonnées update
    METADATA_UPDATE_TOTAL = _get_or_create_counter(
        "memory_metadata_updates_total",
        "Nombre updates métadonnées (last_used_at, use_count)",
        ["collection"],
    )

    METADATA_UPDATE_DURATION = _get_or_create_histogram(
        "memory_metadata_update_duration_seconds",
        "Durée update métadonnées",
        ["collection"],
        buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 5.0),
    )

    # Métriques temporelles
    MEMORY_AGE_DISTRIBUTION = _get_or_create_histogram(
        "memory_entry_age_days",
        "Distribution âge entrées (jours depuis last_used_at)",
        ["collection"],
        buckets=(1, 7, 14, 30, 60, 90, 180, 365),
    )

    USE_COUNT_DISTRIBUTION = _get_or_create_histogram(
        "memory_use_count_distribution",
        "Distribution use_count des entrées",
        ["collection"],
        buckets=(1, 2, 5, 10, 20, 50, 100, 500),
    )

    # Gauge pour stats globales
    ACTIVE_MEMORIES_COUNT = _get_or_create_gauge(
        "memory_active_entries_total",
        "Nombre entrées actives par collection",
        ["collection"],
    )

    PROMETHEUS_AVAILABLE = True
    logger.info("[WeightedRetrievalMetrics] Métriques Prometheus initialisées")

except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.debug("[WeightedRetrievalMetrics] Prometheus client non disponible")


class WeightedRetrievalMetrics:
    """
    Classe utilitaire pour enregistrer métriques retrieval pondéré.
    """

    @staticmethod
    def record_query(
        collection: str, status: str, results_count: int, duration_seconds: float
    ) -> None:
        """
        Enregistre métrique requête query_weighted.

        Args:
            collection: Nom de la collection
            status: 'success' ou 'error'
            results_count: Nombre de résultats retournés
            duration_seconds: Durée de la requête
        """
        if not PROMETHEUS_AVAILABLE:
            return

        WEIGHTED_QUERY_TOTAL.labels(collection=collection, status=status).inc()
        WEIGHTED_QUERY_RESULTS.labels(collection=collection).observe(results_count)

    @staticmethod
    def record_score(collection: str, score: float, duration_seconds: float) -> None:
        """
        Enregistre métrique calcul score.

        Args:
            collection: Nom de la collection
            score: Score pondéré calculé
            duration_seconds: Durée calcul du score
        """
        if not PROMETHEUS_AVAILABLE:
            return

        WEIGHTED_SCORING_DURATION.labels(collection=collection).observe(
            duration_seconds
        )
        WEIGHTED_SCORE_DISTRIBUTION.labels(collection=collection).observe(score)

    @staticmethod
    def record_metadata_update(collection: str, duration_seconds: float) -> None:
        """
        Enregistre métrique update métadonnées.

        Args:
            collection: Nom de la collection
            duration_seconds: Durée update
        """
        if not PROMETHEUS_AVAILABLE:
            return

        METADATA_UPDATE_TOTAL.labels(collection=collection).inc()
        METADATA_UPDATE_DURATION.labels(collection=collection).observe(duration_seconds)

    @staticmethod
    def record_entry_age(collection: str, age_days: float) -> None:
        """
        Enregistre métrique âge entrée.

        Args:
            collection: Nom de la collection
            age_days: Âge en jours depuis last_used_at
        """
        if not PROMETHEUS_AVAILABLE:
            return

        MEMORY_AGE_DISTRIBUTION.labels(collection=collection).observe(age_days)

    @staticmethod
    def record_use_count(collection: str, use_count: int) -> None:
        """
        Enregistre métrique use_count.

        Args:
            collection: Nom de la collection
            use_count: Nombre d'utilisations
        """
        if not PROMETHEUS_AVAILABLE:
            return

        USE_COUNT_DISTRIBUTION.labels(collection=collection).observe(use_count)

    @staticmethod
    def set_active_count(collection: str, count: int) -> None:
        """
        Met à jour gauge nombre entrées actives.

        Args:
            collection: Nom de la collection
            count: Nombre d'entrées actives
        """
        if not PROMETHEUS_AVAILABLE:
            return

        ACTIVE_MEMORIES_COUNT.labels(collection=collection).set(count)
