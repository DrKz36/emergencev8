# src/backend/features/metrics/router.py
# Prometheus metrics endpoint for Emergence V8

import os
import logging
from fastapi import APIRouter, Response
from prometheus_client import REGISTRY, generate_latest, CONTENT_TYPE_LATEST
from typing import Dict, Any, Union

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Metrics"])

METRICS_ENABLED = os.getenv("CONCEPT_RECALL_METRICS_ENABLED", "true").lower() == "true"


@router.get("/metrics")
async def prometheus_metrics():
    """
    Expose Prometheus-compatible metrics endpoint.

    Returns metrics in Prometheus text format for scraping.
    Enabled by default for Prometheus monitoring.
    """
    if not METRICS_ENABLED:
        return Response(
            content="# Metrics disabled. Set CONCEPT_RECALL_METRICS_ENABLED=true to enable.\n",
            media_type=CONTENT_TYPE_LATEST,
            status_code=200
        )

    try:
        # Generate Prometheus format metrics
        metrics_output = generate_latest(REGISTRY)

        return Response(
            content=metrics_output,
            media_type=CONTENT_TYPE_LATEST,
            status_code=200
        )
    except Exception as e:
        logger.error(f"[Metrics] Failed to generate metrics: {e}", exc_info=True)
        return Response(
            content=f"# Error generating metrics: {str(e)}\n",
            media_type=CONTENT_TYPE_LATEST,
            status_code=500
        )


@router.get("/health")
async def health_check():
    """
    Simple health check endpoint.
    """
    return {
        "status": "healthy",
        "metrics_enabled": METRICS_ENABLED
    }


@router.get("/rag")
async def get_rag_metrics() -> Dict[str, Any]:
    """
    Get RAG-specific metrics summary.

    Returns structured JSON with current RAG metrics for dashboard display.
    """
    try:
        # Extract RAG metrics from Prometheus registry
        metrics_data: Dict[str, Union[int, float]] = {}

        for metric in REGISTRY.collect():
            # RAG hybrid queries
            if metric.name == "rag_queries_hybrid_total":
                total = 0.0
                for sample in metric.samples:
                    if sample.labels.get("status") == "success":
                        total += sample.value
                metrics_data["hybrid_queries_total"] = int(total)

            # RAG average score
            elif metric.name == "rag_avg_score":
                # Get the latest value (sum across all labels)
                scores = [sample.value for sample in metric.samples]
                metrics_data["avg_score"] = max(scores) if scores else 0.0

            # Filtered results
            elif metric.name == "rag_results_filtered_total":
                total = 0.0
                for sample in metric.samples:
                    total += sample.value
                metrics_data["filtered_results"] = int(total)

            # Results count histogram
            elif metric.name == "rag_results_count":
                # Calculate average from histogram
                count_sum = 0.0
                count_total = 0.0
                for sample in metric.samples:
                    if sample.name.endswith("_sum"):
                        count_sum = sample.value
                    elif sample.name.endswith("_count"):
                        count_total = sample.value

                if count_total > 0:
                    metrics_data["avg_results_per_query"] = count_sum / count_total

        # Calculate success rate
        total_queries = int(metrics_data.get("hybrid_queries_total", 0))
        if total_queries > 0:
            # Assume success if not filtered
            filtered = int(metrics_data.get("filtered_results", 0))
            successful = max(0, total_queries - filtered)
            metrics_data["successful_queries"] = successful
            metrics_data["success_rate"] = successful / total_queries if total_queries else 1.0
        else:
            metrics_data["successful_queries"] = 0
            metrics_data["success_rate"] = 1.0

        # Fill defaults for missing metrics
        metrics_data.setdefault("hybrid_queries_total", 0)
        metrics_data.setdefault("avg_score", 0.0)
        metrics_data.setdefault("filtered_results", 0)
        metrics_data.setdefault("avg_results_per_query", 0.0)

        return metrics_data

    except Exception as e:
        logger.error(f"Failed to get RAG metrics: {e}", exc_info=True)
        # Return safe defaults on error
        return {
            "hybrid_queries_total": 0,
            "avg_score": 0.0,
            "filtered_results": 0,
            "successful_queries": 0,
            "success_rate": 1.0,
            "avg_results_per_query": 0.0,
            "error": str(e)
        }
