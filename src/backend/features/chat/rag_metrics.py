# src/backend/features/chat/rag_metrics.py
# Phase 3 RAG: Métriques Prometheus pour monitoring avancé du système RAG
#
# Exposition des métriques:
# - Latences (query, merge, scoring)
# - Taux de cache (hits/misses)
# - Qualité résultats (nb chunks, ratio fusion)
# - Usage par agent

import logging
from typing import Optional, List, Iterator
from contextlib import contextmanager
from time import time

try:
    from prometheus_client import Counter, Histogram, Gauge, Info
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logging.warning("[RAG Metrics] prometheus_client not available, metrics disabled")

logger = logging.getLogger(__name__)


# ==========================================
# Compteurs - Événements cumulatifs
# ==========================================

if PROMETHEUS_AVAILABLE:
    # Nombre total de requêtes RAG par agent
    rag_queries_total = Counter(
        'rag_queries_total',
        'Total number of RAG queries processed',
        ['agent_id', 'has_intent']
    )

    # Cache hits/misses
    rag_cache_hits_total = Counter(
        'rag_cache_hits_total',
        'Number of RAG cache hits'
    )

    rag_cache_misses_total = Counter(
        'rag_cache_misses_total',
        'Number of RAG cache misses'
    )

    # Chunks fusionnés
    rag_chunks_merged_total = Counter(
        'rag_chunks_merged_total',
        'Total number of adjacent chunks merged'
    )

    # Requêtes par type de contenu
    rag_queries_by_content_type = Counter(
        'rag_queries_by_content_type_total',
        'RAG queries by detected content type',
        ['content_type']
    )


    # ==========================================
    # Histogrammes - Distribution des latences
    # ==========================================

    # Latence query vectorielle (Phase 3)
    rag_query_phase3_duration_seconds = Histogram(
        'rag_query_phase3_duration_seconds',
        'Time spent in Phase 3 document search query',
        buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0]
    )

    # Latence fusion de chunks
    rag_merge_duration_seconds = Histogram(
        'rag_merge_duration_seconds',
        'Time spent merging adjacent chunks',
        buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.25, 0.5]
    )

    # Latence scoring sémantique
    rag_scoring_duration_seconds = Histogram(
        'rag_scoring_duration_seconds',
        'Time spent in semantic scoring',
        buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.25, 0.5]
    )

    # Latence totale end-to-end
    rag_total_duration_seconds = Histogram(
        'rag_total_duration_seconds',
        'Total RAG pipeline duration (query + merge + score)',
        buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
    )


    # ==========================================
    # Gauges - Valeurs instantanées/moyennes
    # ==========================================

    # Nombre moyen de chunks retournés
    rag_avg_chunks_returned = Gauge(
        'rag_avg_chunks_returned',
        'Average number of chunks returned per query'
    )

    # Ratio de fusion moyen (chunks fusionnés / chunks bruts)
    rag_avg_merge_ratio = Gauge(
        'rag_avg_merge_ratio',
        'Average merge ratio (merged_blocks / raw_chunks)'
    )

    # Score moyen de pertinence
    rag_avg_relevance_score = Gauge(
        'rag_avg_relevance_score',
        'Average relevance score of top result'
    )

    # Diversité des sources (nombre de documents uniques dans top-10)
    rag_avg_source_diversity = Gauge(
        'rag_avg_source_diversity',
        'Average number of unique documents in top results'
    )


    # ==========================================
    # Info - Métadonnées de configuration
    # ==========================================

    rag_config_info = Info(
        'rag_config',
        'RAG system configuration parameters'
    )

    # ==========================================
    # Phase 3 - Métriques Mémoire Temporelle
    # ==========================================

    # Compteur questions temporelles détectées
    memory_temporal_queries_total = Counter(
        'memory_temporal_queries_total',
        'Total temporal queries detected',
        ['detected']  # "true" ou "false"
    )

    # Compteur concepts consolidés trouvés
    memory_temporal_concepts_found_total = Counter(
        'memory_temporal_concepts_found_total',
        'Total consolidated concepts found in temporal queries',
        ['count_range']  # "0", "1-2", "3-5", "5+"
    )

    # Histogram durée recherche ChromaDB pour mémoire consolidée
    memory_temporal_search_duration_seconds = Histogram(
        'memory_temporal_search_duration_seconds',
        'Time spent searching ChromaDB for consolidated concepts',
        buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0]
    )

    # Histogram taille contexte enrichi
    memory_temporal_context_size_bytes = Histogram(
        'memory_temporal_context_size_bytes',
        'Size of enriched temporal context in bytes',
        buckets=[100, 500, 1000, 2000, 5000, 10000]
    )

    # Gauge cache hit rate (calculé périodiquement)
    memory_temporal_cache_hit_rate = Gauge(
        'memory_temporal_cache_hit_rate',
        'Cache hit rate for temporal queries (percentage)'
    )


# ==========================================
# Helper functions pour instrumentation
# ==========================================

@contextmanager
def track_duration(histogram: Optional['Histogram']) -> Iterator[None]:
    """Context manager pour mesurer durée d'exécution."""
    if not PROMETHEUS_AVAILABLE or histogram is None:
        yield
        return

    start = time()
    try:
        yield
    finally:
        duration = time() - start
        histogram.observe(duration)


def record_query(agent_id: str, has_intent: bool = False) -> None:
    """Enregistre une requête RAG."""
    if PROMETHEUS_AVAILABLE:
        rag_queries_total.labels(agent_id=agent_id, has_intent=str(has_intent)).inc()


def record_cache_hit() -> None:
    """Enregistre un cache hit."""
    if PROMETHEUS_AVAILABLE:
        rag_cache_hits_total.inc()


def record_cache_miss() -> None:
    """Enregistre un cache miss."""
    if PROMETHEUS_AVAILABLE:
        rag_cache_misses_total.inc()


def record_chunks_merged(count: int) -> None:
    """Enregistre le nombre de chunks fusionnés."""
    if PROMETHEUS_AVAILABLE:
        rag_chunks_merged_total.inc(count)


def record_content_type_query(content_type: str) -> None:
    """Enregistre une requête par type de contenu."""
    if PROMETHEUS_AVAILABLE and content_type:
        rag_queries_by_content_type.labels(content_type=content_type).inc()


def update_avg_chunks_returned(avg: float) -> None:
    """Met à jour la moyenne de chunks retournés."""
    if PROMETHEUS_AVAILABLE:
        rag_avg_chunks_returned.set(avg)


def update_avg_merge_ratio(ratio: float) -> None:
    """Met à jour le ratio de fusion moyen."""
    if PROMETHEUS_AVAILABLE:
        rag_avg_merge_ratio.set(ratio)


def update_avg_relevance_score(score: float) -> None:
    """Met à jour le score de pertinence moyen."""
    if PROMETHEUS_AVAILABLE:
        rag_avg_relevance_score.set(score)


def update_source_diversity(diversity: float) -> None:
    """Met à jour la diversité des sources."""
    if PROMETHEUS_AVAILABLE:
        rag_avg_source_diversity.set(diversity)


def set_rag_config(
    n_results: int,
    max_blocks: int,
    chunk_tolerance: int,
    cache_enabled: bool,
    cache_ttl: int
) -> None:
    """Configure les métadonnées de configuration RAG."""
    if PROMETHEUS_AVAILABLE:
        rag_config_info.info({
            'n_results': str(n_results),
            'max_blocks': str(max_blocks),
            'chunk_tolerance': str(chunk_tolerance),
            'cache_enabled': str(cache_enabled),
            'cache_ttl_seconds': str(cache_ttl),
        })


# ==========================================
# Classe wrapper pour statistiques rolling
# ==========================================

class RAGMetricsAggregator:
    """
    Agrégateur de métriques pour calcul de moyennes rolling.
    Utilisé pour mettre à jour les Gauges Prometheus.
    """

    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self.chunks_returned_history: List[int] = []
        self.merge_ratio_history: List[float] = []
        self.relevance_score_history: List[float] = []
        self.source_diversity_history: List[int] = []

    def add_result(
        self,
        chunks_returned: int,
        raw_chunks: int,
        merged_blocks: int,
        top_score: float,
        unique_docs: int
    ) -> None:
        """Ajoute un résultat et met à jour les métriques."""
        # Ajouter aux historiques
        self.chunks_returned_history.append(chunks_returned)
        if raw_chunks > 0:
            self.merge_ratio_history.append(merged_blocks / raw_chunks)
        else:
            self.merge_ratio_history.append(0.0)
        self.relevance_score_history.append(top_score)
        self.source_diversity_history.append(unique_docs)

        # Limiter la taille des fenêtres
        if len(self.chunks_returned_history) > self.window_size:
            self.chunks_returned_history.pop(0)
            self.merge_ratio_history.pop(0)
            self.relevance_score_history.pop(0)
            self.source_diversity_history.pop(0)

        # Mettre à jour les Gauges Prometheus
        if self.chunks_returned_history:
            update_avg_chunks_returned(
                sum(self.chunks_returned_history) / len(self.chunks_returned_history)
            )

        if self.merge_ratio_history:
            update_avg_merge_ratio(
                sum(self.merge_ratio_history) / len(self.merge_ratio_history)
            )

        if self.relevance_score_history:
            update_avg_relevance_score(
                sum(self.relevance_score_history) / len(self.relevance_score_history)
            )

        if self.source_diversity_history:
            update_source_diversity(
                sum(self.source_diversity_history) / len(self.source_diversity_history)
            )


# Instance globale de l'agrégateur (initialisée dans service.py)
_global_aggregator: Optional[RAGMetricsAggregator] = None


def get_aggregator() -> RAGMetricsAggregator:
    """Récupère ou crée l'agrégateur global."""
    global _global_aggregator
    if _global_aggregator is None:
        _global_aggregator = RAGMetricsAggregator()
    return _global_aggregator


# ==========================================
# Phase 3 - Helper functions Mémoire Temporelle
# ==========================================

def record_temporal_query(is_temporal: bool) -> None:
    """Enregistre une question temporelle (détectée ou non)."""
    if PROMETHEUS_AVAILABLE:
        memory_temporal_queries_total.labels(detected=str(is_temporal).lower()).inc()


def record_temporal_concepts_found(count: int) -> None:
    """Enregistre le nombre de concepts consolidés trouvés."""
    if PROMETHEUS_AVAILABLE:
        # Classifier par range
        if count == 0:
            range_label = "0"
        elif count <= 2:
            range_label = "1-2"
        elif count <= 5:
            range_label = "3-5"
        else:
            range_label = "5+"

        memory_temporal_concepts_found_total.labels(count_range=range_label).inc()


def record_temporal_search_duration(duration_seconds: float) -> None:
    """Enregistre la durée d'une recherche ChromaDB pour mémoire consolidée."""
    if PROMETHEUS_AVAILABLE:
        memory_temporal_search_duration_seconds.observe(duration_seconds)


def record_temporal_context_size(size_bytes: int) -> None:
    """Enregistre la taille du contexte temporel enrichi."""
    if PROMETHEUS_AVAILABLE:
        memory_temporal_context_size_bytes.observe(size_bytes)


def update_temporal_cache_hit_rate(hit_rate_percentage: float) -> None:
    """Met à jour le hit rate du cache temporel."""
    if PROMETHEUS_AVAILABLE:
        memory_temporal_cache_hit_rate.set(hit_rate_percentage)


logger.info(f"[RAG Metrics] Module initialized (Prometheus available: {PROMETHEUS_AVAILABLE})")
