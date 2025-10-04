# src/backend/features/metrics/router.py
# Prometheus metrics endpoint for Emergence V8

import os
import logging
from fastapi import APIRouter, Response
from prometheus_client import REGISTRY, generate_latest, CONTENT_TYPE_LATEST

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Metrics"])

METRICS_ENABLED = os.getenv("CONCEPT_RECALL_METRICS_ENABLED", "false").lower() == "true"


@router.get("/metrics")
async def prometheus_metrics():
    """
    Expose Prometheus-compatible metrics endpoint.

    Returns metrics in Prometheus text format for scraping.
    Disabled by default (requires CONCEPT_RECALL_METRICS_ENABLED=true).
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
