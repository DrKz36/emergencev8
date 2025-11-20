# src/backend/features/tracing/router.py
# V1.0 - Tracing REST API for ÉMERGENCE V8
#
# Endpoints:
# - GET /api/traces/recent : Retourne les 100 derniers spans (debug/monitoring)
# - GET /api/traces/stats : Statistiques agrégées (count par span_name, avg duration)

import logging
from collections import defaultdict
from typing import Any, Dict, List

from fastapi import APIRouter, Query

from backend.core.tracing import get_trace_manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Tracing"], prefix="/traces")


@router.get("/recent")
async def get_recent_traces(
    limit: int = Query(default=100, ge=1, le=1000),
) -> List[Dict[str, Any]]:
    """
    Retourne les N derniers spans complétés (du plus récent au plus ancien).

    Args:
        limit: Nombre de spans à retourner (1-1000, défaut 100)

    Returns:
        Liste de spans avec leurs métadonnées (span_id, name, trace_id, duration, status, etc.)

    Example response:
        [
            {
                "span_id": "abc123",
                "name": "retrieval",
                "trace_id": "xyz789",
                "parent_id": null,
                "start_time": 1698765432.123,
                "end_time": 1698765432.456,
                "duration": 0.333,
                "status": "OK",
                "attributes": {"agent": "AnimA", "docs_count": 5}
            },
            ...
        ]
    """
    try:
        mgr = get_trace_manager()
        spans = mgr.export(limit=limit)
        logger.debug(f"[Tracing API] Exported {len(spans)} recent spans")
        return spans
    except Exception as e:
        logger.error(f"[Tracing API] Failed to export traces: {e}", exc_info=True)
        return []


@router.get("/stats")
async def get_trace_stats() -> Dict[str, Any]:
    """
    Retourne des statistiques agrégées sur les traces (100 derniers spans).

    Returns:
        - total_spans: Nombre total de spans
        - by_name: Count et durée moyenne par span_name
        - by_status: Count par status (OK, ERROR, TIMEOUT)
        - by_agent: Count par agent (si attribut "agent" présent)

    Example response:
        {
            "total_spans": 42,
            "by_name": {
                "retrieval": {"count": 10, "avg_duration": 0.345},
                "llm_generate": {"count": 10, "avg_duration": 1.234}
            },
            "by_status": {"OK": 40, "ERROR": 2},
            "by_agent": {"AnimA": 15, "Neo": 12, "Nexus": 15}
        }
    """
    try:
        mgr = get_trace_manager()
        spans = mgr.export(limit=100)

        # Stats par nom
        by_name: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"count": 0, "total_duration": 0.0}
        )
        by_status: Dict[str, int] = defaultdict(int)
        by_agent: Dict[str, int] = defaultdict(int)

        for span in spans:
            name = span["name"]
            status = span["status"]
            duration = span.get("duration", 0.0) or 0.0
            agent = span.get("attributes", {}).get("agent")

            # By name
            by_name[name]["count"] += 1
            by_name[name]["total_duration"] += duration

            # By status
            by_status[status] += 1

            # By agent
            if agent:
                by_agent[agent] += 1

        # Calcul avg_duration
        by_name_stats = {}
        for name, data in by_name.items():
            avg_duration = (
                data["total_duration"] / data["count"] if data["count"] > 0 else 0.0
            )
            by_name_stats[name] = {
                "count": data["count"],
                "avg_duration": round(avg_duration, 3),
            }

        stats = {
            "total_spans": len(spans),
            "by_name": by_name_stats,
            "by_status": dict(by_status),
            "by_agent": dict(by_agent),
        }

        logger.debug(f"[Tracing API] Generated stats for {len(spans)} spans")
        return stats

    except Exception as e:
        logger.error(f"[Tracing API] Failed to generate stats: {e}", exc_info=True)
        return {
            "total_spans": 0,
            "by_name": {},
            "by_status": {},
            "by_agent": {},
            "error": str(e),
        }
