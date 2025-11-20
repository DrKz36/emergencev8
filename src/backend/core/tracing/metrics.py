# src/backend/core/tracing/metrics.py
# V1.0 - Prometheus metrics pour spans de tracing distribué
#
# Expose:
# - chat_trace_spans_total (Counter): Nombre total de spans par type/agent/status
# - chat_trace_span_duration_seconds (Histogram): Durée des spans (p50, p95, p99)

import logging
from prometheus_client import Counter, Histogram

logger = logging.getLogger(__name__)

# Counter: Nombre total de spans générés
chat_trace_spans_total = Counter(
    "chat_trace_spans_total",
    "Nombre total de spans générés par le système de tracing",
    ["span_name", "agent", "status"],
)

# Histogram: Durée des spans (buckets optimisés pour latences LLM/RAG)
chat_trace_span_duration_seconds = Histogram(
    "chat_trace_span_duration_seconds",
    "Durée des spans en secondes",
    ["span_name", "agent"],
    buckets=[
        0.01,  # 10ms (cache hit rapide)
        0.05,  # 50ms (RAG local)
        0.1,  # 100ms
        0.25,  # 250ms (retrieval typique)
        0.5,  # 500ms
        1.0,  # 1s (LLM génération début)
        2.5,  # 2.5s
        5.0,  # 5s (LLM génération moyenne)
        10.0,  # 10s (LLM génération lente)
        30.0,  # 30s (timeout boundary)
    ],
)


def record_span(span_name: str, agent: str, status: str, duration: float) -> None:
    """
    Enregistre un span dans Prometheus (counter + histogram).

    Args:
        span_name: Nom du span (retrieval, llm_generate, memory_update, tool_call)
        agent: ID de l'agent (anima, neo, nexus, unknown)
        status: État final (OK, ERROR, TIMEOUT)
        duration: Durée en secondes
    """
    try:
        # Increment counter
        chat_trace_spans_total.labels(
            span_name=span_name,
            agent=agent,
            status=status,
        ).inc()

        # Record duration (si status=OK uniquement, pour stats fiables)
        if status == "OK":
            chat_trace_span_duration_seconds.labels(
                span_name=span_name,
                agent=agent,
            ).observe(duration)

        logger.debug(
            f"[TracingMetrics] Recorded span: {span_name} (agent={agent}, status={status}, duration={duration:.3f}s)"
        )
    except Exception as e:
        logger.warning(f"[TracingMetrics] Failed to record span metrics: {e}")
