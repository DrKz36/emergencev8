from __future__ import annotations

import json
import logging
import os
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.benchmarks.agentarch_runner import BenchmarksRunner, BenchmarkMatrixResult
from backend.benchmarks.executor import AgentArchScenarioExecutor
from backend.benchmarks.persistence import (
    BenchmarksRepository,
    CompositeBenchmarkResultSink,
    FirestoreBenchmarkResultSink,
    SQLiteBenchmarkResultSink,
)
from backend.benchmarks.scenarios import (
    SCENARIO_DEFINITIONS,
    ScenarioDefinition,
    ScenarioTask,
)
from backend.features.benchmarks.metrics import ndcg_time_at_k

logger = logging.getLogger(__name__)
_EDGE_VALUES = {"1", "true", "yes", "on"}


def _is_edge_mode() -> bool:
    raw = os.getenv("EDGE_MODE", "0")
    return raw.strip().lower() in _EDGE_VALUES if raw else False


class BenchmarksService:
    """High-level facade bridging the runner, executor and persistence layers."""

    def __init__(
        self,
        repository: BenchmarksRepository,
        *,
        firestore_client: Any = None,
        default_concurrency: int = 3,
        max_retries: int = 1,
        scenario_index: Optional[str] = None,
    ) -> None:
        self._repository = repository
        self._firestore_client = firestore_client
        self._default_concurrency = max(1, int(default_concurrency))
        self._max_retries = max(0, int(max_retries))
        self._edge_mode = _is_edge_mode()
        self._scenarios = self._load_catalog(scenario_index)

    async def run_matrix(
        self,
        scenario_id: str,
        *,
        context: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> BenchmarkMatrixResult:
        scenario = self._require_scenario(scenario_id)
        matrix_id = uuid.uuid4().hex
        sqlite_sink = SQLiteBenchmarkResultSink(
            self._repository,
            matrix_id=matrix_id,
            scenario_id=scenario.id,
        )
        sinks: list[
            SQLiteBenchmarkResultSink | FirestoreBenchmarkResultSink
        ] = [sqlite_sink]
        if self._firestore_client is not None:
            sinks.append(
                FirestoreBenchmarkResultSink(
                    self._firestore_client,
                    matrix_id=matrix_id,
                    scenario_id=scenario.id,
                )
            )
        sink = sinks[0] if len(sinks) == 1 else CompositeBenchmarkResultSink(sinks)

        executor = AgentArchScenarioExecutor(
            scenarios=self._scenarios,
            edge_mode=self._edge_mode,
        )
        runner = BenchmarksRunner(
            executor,
            sink=sink,
            max_retries=self._max_retries,
            concurrency=self._default_concurrency,
        )
        scenario_context = {
            "scenario_id": scenario.id,
            "scenario_name": scenario.name,
            "tasks_total": len(scenario.tasks),
        }
        scenario_context.update(context or {})
        scenario_metadata = dict(metadata or {})
        scenario_metadata.setdefault("source", scenario.metadata.get("source"))
        matrix = await runner.run_matrix(
            scenario_id=scenario.id,
            context=scenario_context,
            metadata=scenario_metadata,
        )
        return matrix

    async def list_results(
        self,
        *,
        scenario_id: Optional[str] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        return await self._repository.fetch_recent_results(
            scenario_id=scenario_id,
            limit=limit,
        )

    def get_supported_scenarios(self) -> List[Dict[str, Any]]:
        catalogue: List[Dict[str, Any]] = []
        for item in self._scenarios.values():
            catalogue.append(
                {
                    "id": item.id,
                    "name": item.name,
                    "description": item.description,
                    "success_threshold": item.success_threshold,
                    "tasks_total": len(item.tasks),
                    "metadata": dict(item.metadata),
                }
            )
        return catalogue

    def calculate_temporal_ndcg(
        self,
        ranked_items: List[Dict[str, Any]],
        k: int = 10,
        **kwargs: Any,
    ) -> float:
        """
        Calcule la métrique nDCG@k temporelle sur une liste de résultats classés.

        Cette méthode expose la métrique `ndcg_time_at_k` pour mesurer la qualité
        d'un classement en intégrant la fraîcheur temporelle des documents.

        Args:
            ranked_items: Liste ordonnée d'items avec clés 'rel' (float)
                         et 'ts' (datetime)
            k: Nombre d'items considérés dans le top-k (défaut: 10)
            **kwargs: Arguments supplémentaires passés à ndcg_time_at_k
                     (now, T_days, lam)

        Returns:
            float: Score nDCG@k temporel entre 0 (pire) et 1 (parfait)

        Example:
            >>> from datetime import datetime, timedelta, timezone
            >>> now = datetime.now(timezone.utc)
            >>> items = [
            ...     {'rel': 3.0, 'ts': now - timedelta(days=1)},
            ...     {'rel': 2.0, 'ts': now - timedelta(days=30)},
            ... ]
            >>> service.calculate_temporal_ndcg(items, k=2)
            0.95
        """
        return ndcg_time_at_k(ranked_items, k=k, **kwargs)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _load_catalog(
        self, scenario_index: Optional[str]
    ) -> Dict[str, ScenarioDefinition]:
        if self._edge_mode:
            logger.info("EDGE_MODE enabled -> using static scenario catalogue.")
            return dict(SCENARIO_DEFINITIONS)

        path_hint = scenario_index or os.getenv("BENCHMARKS_SCENARIO_INDEX")
        if not path_hint:
            return dict(SCENARIO_DEFINITIONS)

        path = Path(path_hint)
        if not path.exists():
            logger.warning(
                "Scenario index path %s not found. "
                "Falling back to built-in catalogue.",
                path,
            )
            return dict(SCENARIO_DEFINITIONS)

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            scenarios: Dict[str, ScenarioDefinition] = {}
            for entry in data.get("scenarios", []):
                try:
                    scenarios[entry["id"]] = ScenarioDefinition(
                        id=entry["id"],
                        name=entry.get("name", entry["id"]),
                        description=entry.get("description", ""),
                        success_threshold=float(entry.get("success_threshold", 0.75)),
                        base_cost=float(entry.get("base_cost", 0.005)),
                        base_latency_ms=float(entry.get("base_latency_ms", 900.0)),
                        tasks=[
                            ScenarioTask(
                                id=task["id"],
                                difficulty=float(task.get("difficulty", 0.6)),
                                domain=task.get("domain", "generic"),
                                weight=float(task.get("weight", 1.0)),
                            )
                            for task in entry.get("tasks", [])
                        ],
                        metadata=dict(entry.get("metadata", {})),
                    )
                except Exception as exc:  # pragma: no cover - defensive fallback
                    logger.warning("Invalid scenario entry %s: %s", entry, exc)
            if not scenarios:
                logger.warning("Scenario index empty; using built-in defaults.")
                return dict(SCENARIO_DEFINITIONS)
            for default_id, default_def in SCENARIO_DEFINITIONS.items():
                scenarios.setdefault(default_id, default_def)
            return scenarios
        except Exception as exc:  # pragma: no cover - defensive fallback
            logger.exception("Unable to parse scenario index %s: %s", path, exc)
            return dict(SCENARIO_DEFINITIONS)

    def _require_scenario(self, scenario_id: str) -> ScenarioDefinition:
        try:
            return self._scenarios[scenario_id]
        except KeyError as exc:
            supported = ", ".join(sorted(self._scenarios.keys()))
            raise ValueError(
                f"Scenario '{scenario_id}' not supported. "
                f"Supported: {supported}"
            ) from exc


__all__ = ["BenchmarksService"]
