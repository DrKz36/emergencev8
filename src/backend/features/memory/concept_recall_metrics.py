# src/backend/features/memory/concept_recall_metrics.py
# V1.0 - Prometheus metrics for Concept Recall feature

"""
Concept Recall Metrics Module

Provides Prometheus-compatible metrics for monitoring:
- Detection rate and quality
- Performance (latency, vector search duration)
- User interactions (dismiss, view history)
- Cross-thread detection patterns
"""

import os
import logging
from typing import Optional
from prometheus_client import Counter, Histogram, Gauge, Info

logger = logging.getLogger(__name__)

# Feature flag: opt-in metrics collection
METRICS_ENABLED = os.getenv("CONCEPT_RECALL_METRICS_ENABLED", "false").lower() == "true"


# ============================================================================
# 1. DETECTION METRICS
# ============================================================================

DETECTIONS_TOTAL = Counter(
    'concept_recall_detections_total',
    'Total number of concept recall detections',
    ['user_id_hash', 'similarity_range']
)

EVENTS_EMITTED_TOTAL = Counter(
    'concept_recall_events_emitted_total',
    'Total WebSocket concept_recall events emitted',
    ['user_id_hash']
)

SIMILARITY_SCORE = Histogram(
    'concept_recall_similarity_score',
    'Distribution of similarity scores for detected concepts',
    buckets=[0.5, 0.75, 0.8, 0.9, 1.0]
)

DETECTION_LATENCY = Histogram(
    'concept_recall_detection_latency_seconds',
    'Time to detect recurring concepts (vector search + filtering)',
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0]
)


# ============================================================================
# 2. QUALITY METRICS
# ============================================================================

FALSE_POSITIVES_TOTAL = Counter(
    'concept_recall_false_positives_total',
    'Detections dismissed by user (Ignorer button)',
    ['user_id_hash']
)

INTERACTIONS_TOTAL = Counter(
    'concept_recall_interactions_total',
    'User interactions with concept recall banners',
    ['user_id_hash', 'action']  # action: view_history, dismiss, auto_hide
)


# ============================================================================
# 3. PERFORMANCE METRICS
# ============================================================================

VECTOR_SEARCH_DURATION = Histogram(
    'concept_recall_vector_search_duration_seconds',
    'Duration of ChromaDB vector search',
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.5, 1.0]
)

METADATA_UPDATE_DURATION = Histogram(
    'concept_recall_metadata_update_duration_seconds',
    'Duration to update vector metadata (mention_count, thread_ids)',
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0]
)


# ============================================================================
# 4. BUSINESS METRICS
# ============================================================================

CROSS_THREAD_DETECTIONS = Counter(
    'concept_recall_cross_thread_detections_total',
    'Cross-thread detections by thread count range',
    ['thread_count_range']  # 2, 3-5, 6-10, 10+
)

CONCEPT_REUSE_TOTAL = Counter(
    'concept_recall_concept_reuse_total',
    'Concepts reused across conversations (mention_count > 1)',
    ['user_id_hash']
)

CONCEPTS_TOTAL = Gauge(
    'concept_recall_concepts_total',
    'Total concepts in vector store',
    ['user_id_hash']
)


# ============================================================================
# 5. SYSTEM INFO
# ============================================================================

SYSTEM_INFO = Info(
    'concept_recall_system',
    'Concept recall system information'
)

# Set system info on module load
if METRICS_ENABLED:
    SYSTEM_INFO.info({
        'version': '1.0',
        'similarity_threshold': '0.75',
        'max_recalls_per_message': '3',
        'collection_name': 'emergence_knowledge',
    })


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _hash_user_id(user_id: str) -> str:
    """
    Hash user_id for privacy in Prometheus labels.
    Returns first 8 chars of SHA256 hash.
    """
    import hashlib
    return hashlib.sha256(user_id.encode()).hexdigest()[:8]


def _get_similarity_range(score: float) -> str:
    """
    Categorize similarity score into range bucket.
    """
    if score >= 0.9:
        return "0.9-1.0"
    elif score >= 0.8:
        return "0.8-0.9"
    elif score >= 0.75:
        return "0.75-0.8"
    else:
        return "0.5-0.75"


def _get_thread_count_range(count: int) -> str:
    """
    Categorize thread count into range bucket.
    """
    if count >= 10:
        return "10+"
    elif count >= 6:
        return "6-10"
    elif count >= 3:
        return "3-5"
    else:
        return "2"


# ============================================================================
# INSTRUMENTATION API
# ============================================================================

class ConceptRecallMetrics:
    """
    High-level API for instrumenting concept recall operations.
    Safe to use even when metrics are disabled (no-op).
    """

    def __init__(self, enabled: Optional[bool] = None):
        self.enabled = enabled if enabled is not None else METRICS_ENABLED
        if self.enabled:
            logger.info("[ConceptRecallMetrics] Metrics collection enabled")

    def record_detection(
        self,
        user_id: str,
        similarity_score: float,
        thread_count: int,
        duration_seconds: float
    ):
        """Record a successful concept recall detection."""
        if not self.enabled:
            return

        user_hash = _hash_user_id(user_id)
        similarity_range = _get_similarity_range(similarity_score)
        thread_range = _get_thread_count_range(thread_count)

        DETECTIONS_TOTAL.labels(
            user_id_hash=user_hash,
            similarity_range=similarity_range
        ).inc()

        SIMILARITY_SCORE.observe(similarity_score)
        DETECTION_LATENCY.observe(duration_seconds)

        CROSS_THREAD_DETECTIONS.labels(
            thread_count_range=thread_range
        ).inc()

    def record_event_emitted(self, user_id: str, recall_count: int):
        """Record WebSocket event emission."""
        if not self.enabled:
            return

        user_hash = _hash_user_id(user_id)
        EVENTS_EMITTED_TOTAL.labels(user_id_hash=user_hash).inc()

    def record_vector_search(self, duration_seconds: float):
        """Record vector search duration."""
        if not self.enabled:
            return

        VECTOR_SEARCH_DURATION.observe(duration_seconds)

    def record_metadata_update(self, duration_seconds: float):
        """Record metadata update duration."""
        if not self.enabled:
            return

        METADATA_UPDATE_DURATION.observe(duration_seconds)

    def record_interaction(self, user_id: str, action: str):
        """
        Record user interaction with banner.

        Args:
            user_id: User identifier
            action: One of 'view_history', 'dismiss', 'auto_hide'
        """
        if not self.enabled:
            return

        user_hash = _hash_user_id(user_id)
        INTERACTIONS_TOTAL.labels(
            user_id_hash=user_hash,
            action=action
        ).inc()

        # Track false positives (dismissals)
        if action == 'dismiss':
            FALSE_POSITIVES_TOTAL.labels(user_id_hash=user_hash).inc()

    def record_concept_reuse(self, user_id: str, mention_count: int):
        """Record concept being reused (mention_count > 1)."""
        if not self.enabled:
            return

        if mention_count > 1:
            user_hash = _hash_user_id(user_id)
            CONCEPT_REUSE_TOTAL.labels(user_id_hash=user_hash).inc()

    def update_concepts_total(self, user_id: str, count: int):
        """Update total concepts gauge for user."""
        if not self.enabled:
            return

        user_hash = _hash_user_id(user_id)
        CONCEPTS_TOTAL.labels(user_id_hash=user_hash).set(count)


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

# Export singleton instance for easy import
concept_recall_metrics = ConceptRecallMetrics()
