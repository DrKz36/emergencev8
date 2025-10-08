from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import statistics
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional, Sequence, cast

from .agentarch_runner import BenchmarkMatrixResult, BenchmarkRunResult, BenchmarkResultSink
from ..core.database.manager import DatabaseManager

logger = logging.getLogger(__name__)


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _json_loads(value: Optional[str]) -> Any:
    if not value:
        return None
    try:
        return json.loads(value)
    except Exception:
        return None


def _run_identifier(matrix_id: str, config_slug: str) -> str:
    payload = f"{matrix_id}:{config_slug}".encode("utf-8", "ignore")
    return hashlib.sha1(payload).hexdigest()


class BenchmarksRepository:
    """Low-level persistence helper backed by SQLite."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        self._db = db_manager

    async def ensure_matrix_placeholder(
        self, *, matrix_id: str, scenario_id: str
    ) -> None:
        query = """
            INSERT OR IGNORE INTO benchmark_matrices (
                id, scenario_id, started_at, completed_at, edge_mode_enabled,
                context, runs_count, success_count, failure_count, average_cost,
                median_latency_ms, created_at
            ) VALUES (?, ?, ?, ?, 0, NULL, 0, 0, 0, 0, 0, ?)
        """
        now = _iso_now()
        await self._db.execute(query, (matrix_id, scenario_id, now, now, now))

    async def insert_run(
        self,
        *,
        run_id: str,
        matrix_id: str,
        scenario_id: str,
        run: BenchmarkRunResult,
    ) -> None:
        config = run.config
        metadata_json = _json_dumps(config.metadata or {}) if config.metadata else None
        executor_details = _json_dumps(run.executor_details) if run.executor_details else None
        query = """
            INSERT OR REPLACE INTO benchmark_runs (
                id, matrix_id, scenario_id, slug,
                agent_topology, orchestration_mode, memory_mode,
                success, retries, cost, latency_ms,
                started_at, completed_at, error_message,
                executor_details, config_metadata, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            run_id,
            matrix_id,
            scenario_id,
            config.slug,
            config.agent_topology.value,
            config.orchestration_mode.value,
            config.memory_mode.value,
            int(run.success),
            int(run.retries),
            float(run.cost),
            float(run.latency_ms),
            run.started_at.isoformat(),
            run.completed_at.isoformat(),
            run.error_message,
            executor_details,
            metadata_json,
            _iso_now(),
        )
        await self._db.execute(query, params)

    async def insert_matrix(
        self,
        *,
        matrix_id: str,
        matrix: BenchmarkMatrixResult,
    ) -> None:
        runs = matrix.results
        run_count = len(runs)
        success_count = sum(1 for item in runs if item.success)
        failure_count = run_count - success_count
        average_cost = (
            sum(item.cost for item in runs) / run_count if run_count else 0.0
        )
        median_latency = (
            statistics.median(item.latency_ms for item in runs)
            if run_count
            else 0.0
        )
        context_json = _json_dumps(matrix.context or {}) if matrix.context else None
        query = """
            INSERT INTO benchmark_matrices (
                id, scenario_id, started_at, completed_at,
                edge_mode_enabled, context, runs_count, success_count,
                failure_count, average_cost, median_latency_ms,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                scenario_id = excluded.scenario_id,
                started_at = excluded.started_at,
                completed_at = excluded.completed_at,
                edge_mode_enabled = excluded.edge_mode_enabled,
                context = excluded.context,
                runs_count = excluded.runs_count,
                success_count = excluded.success_count,
                failure_count = excluded.failure_count,
                average_cost = excluded.average_cost,
                median_latency_ms = excluded.median_latency_ms,
                created_at = excluded.created_at
        """
        params = (
            matrix_id,
            matrix.scenario_id,
            matrix.started_at.isoformat(),
            matrix.completed_at.isoformat(),
            int(matrix.edge_mode_enabled),
            context_json,
            run_count,
            success_count,
            failure_count,
            round(average_cost, 6),
            round(median_latency, 3),
            _iso_now(),
        )
        await self._db.execute(query, params)

    async def fetch_recent_results(
        self,
        *,
        scenario_id: Optional[str] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        clauses: List[str] = []
        params: List[Any] = []
        if scenario_id:
            clauses.append("scenario_id = ?")
            params.append(scenario_id)
        sql = "SELECT * FROM benchmark_matrices"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY datetime(completed_at) DESC LIMIT ?"
        params.append(int(limit))
        matrices = await self._db.fetch_all(sql, tuple(params))
        results: List[Dict[str, Any]] = []
        for row in matrices:
            matrix_id = row["id"]
            runs = await self._db.fetch_all(
                "SELECT * FROM benchmark_runs WHERE matrix_id = ? ORDER BY slug ASC",
                (matrix_id,),
            )
            results.append(
                {
                    "id": matrix_id,
                    "scenario_id": row["scenario_id"],
                    "started_at": row["started_at"],
                    "completed_at": row["completed_at"],
                    "edge_mode_enabled": bool(row["edge_mode_enabled"]),
                    "context": _json_loads(row["context"]) or {},
                    "summary": {
                        "runs_count": row["runs_count"],
                        "success_count": row["success_count"],
                        "failure_count": row["failure_count"],
                        "average_cost": row["average_cost"],
                        "median_latency_ms": row["median_latency_ms"],
                        "success_rate": (
                            row["success_count"] / row["runs_count"]
                            if row["runs_count"]
                            else 0.0
                        ),
                    },
                    "runs": [self._serialize_run(cast(Mapping[str, Any], run)) for run in runs],
                }
            )
        return results

    def _serialize_run(self, row: Mapping[str, Any]) -> Dict[str, Any]:
        return {
            "id": row["id"],
            "slug": row["slug"],
            "config": {
                "agent_topology": row["agent_topology"],
                "orchestration_mode": row["orchestration_mode"],
                "memory_mode": row["memory_mode"],
                "metadata": _json_loads(row["config_metadata"]) or {}
                if "config_metadata" in row.keys() else {},
            },
            "success": bool(row["success"]),
            "retries": row["retries"],
            "cost": row["cost"],
            "latency_ms": row["latency_ms"],
            "started_at": row["started_at"],
            "completed_at": row["completed_at"],
            "error_message": row["error_message"],
            "executor_details": _json_loads(row["executor_details"]) or {}
            if "executor_details" in row.keys() else {},
        }


class SQLiteBenchmarkResultSink(BenchmarkResultSink):
    """SQLite-backed materialisation of benchmark results."""

    def __init__(
        self,
        repository: BenchmarksRepository,
        *,
        matrix_id: str,
        scenario_id: str,
    ) -> None:
        self._repository = repository
        self._matrix_id = matrix_id
        self._scenario_id = scenario_id
        self._lock = asyncio.Lock()
        self._initialized = False

    async def persist_run(self, result: BenchmarkRunResult) -> None:
        async with self._lock:
            if not self._initialized:
                await self._repository.ensure_matrix_placeholder(
                    matrix_id=self._matrix_id,
                    scenario_id=self._scenario_id,
                )
                self._initialized = True
            run_id = _run_identifier(self._matrix_id, result.config.slug)
            await self._repository.insert_run(
                run_id=run_id,
                matrix_id=self._matrix_id,
                scenario_id=self._scenario_id,
                run=result,
            )

    async def persist_matrix(self, matrix: BenchmarkMatrixResult) -> None:
        await self._repository.insert_matrix(matrix_id=self._matrix_id, matrix=matrix)


class FirestoreBenchmarkResultSink(BenchmarkResultSink):
    """Optional Firestore materialisation. No-op if the client is missing."""

    def __init__(
        self,
        client: Any,
        *,
        matrix_id: str,
        scenario_id: str,
        run_collection: str = "benchmark_runs",
        matrix_collection: str = "benchmark_matrices",
    ) -> None:
        self._client = client
        self._matrix_id = matrix_id
        self._scenario_id = scenario_id
        self._run_collection = run_collection
        self._matrix_collection = matrix_collection

    async def persist_run(self, result: BenchmarkRunResult) -> None:
        if self._client is None:
            return
        data = result.to_dict()
        data.update(
            {
                "id": _run_identifier(self._matrix_id, result.config.slug),
                "matrix_id": self._matrix_id,
                "scenario_id": self._scenario_id,
            }
        )
        await asyncio.to_thread(self._store_run, data)

    async def persist_matrix(self, matrix: BenchmarkMatrixResult) -> None:
        if self._client is None:
            return
        runs_count = len(matrix.results)
        success_count = sum(1 for item in matrix.results if item.success)
        payload = matrix.to_dict()
        payload.update(
            {
                "id": self._matrix_id,
                "runs_count": runs_count,
                "success_count": success_count,
                "failure_count": runs_count - success_count,
            }
        )
        await asyncio.to_thread(self._store_matrix, payload)

    def _store_run(self, data: Dict[str, Any]) -> None:
        try:
            self._client.collection(self._run_collection).document(data["id"]).set(data)
        except Exception:  # pragma: no cover - logging only
            logger.exception("Failed to persist benchmark run to Firestore.")

    def _store_matrix(self, data: Dict[str, Any]) -> None:
        try:
            self._client.collection(self._matrix_collection).document(data["id"]).set(data)
        except Exception:  # pragma: no cover - logging only
            logger.exception("Failed to persist benchmark matrix to Firestore.")


class CompositeBenchmarkResultSink(BenchmarkResultSink):
    """Fan-out sink forwarding data to multiple child sinks."""

    def __init__(self, sinks: Sequence[BenchmarkResultSink]) -> None:
        self._sinks = [sink for sink in sinks if sink is not None]

    async def persist_run(self, result: BenchmarkRunResult) -> None:
        for sink in self._sinks:
            try:
                await sink.persist_run(result)
            except Exception:  # pragma: no cover - logging only
                logger.exception("Benchmark sink failed while persisting run.")

    async def persist_matrix(self, matrix: BenchmarkMatrixResult) -> None:
        for sink in self._sinks:
            try:
                await sink.persist_matrix(matrix)
            except Exception:  # pragma: no cover - logging only
                logger.exception("Benchmark sink failed while persisting matrix.")


def build_firestore_client(*, project_id: Optional[str] = None) -> Optional[Any]:
    if os.getenv("EDGE_MODE", "0").strip().lower() in {"1", "true", "yes", "on"}:
        return None
    try:
        from google.cloud import firestore  # type: ignore
    except Exception:  # pragma: no cover - optional dependency
        logger.debug("google-cloud-firestore not available; skipping Firestore client init.")
        return None

    if project_id:
        try:
            return firestore.Client(project=project_id)
        except Exception:  # pragma: no cover - logging only
            logger.exception("Unable to build Firestore client with provided project id.")
            return None

    try:
        return firestore.Client()
    except Exception:  # pragma: no cover - logging only
        logger.exception("Unable to build Firestore client; default credentials missing.")
        return None


__all__ = [
    "BenchmarksRepository",
    "SQLiteBenchmarkResultSink",
    "FirestoreBenchmarkResultSink",
    "CompositeBenchmarkResultSink",
    "build_firestore_client",
]
