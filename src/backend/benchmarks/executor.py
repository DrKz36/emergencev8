from __future__ import annotations

import os
from typing import Any, Dict, Mapping, Optional

from .agentarch_runner import (
    AgentArchExecutor,
    AgentExecutionOutcome,
    AgentTopology,
    BenchmarkRunConfig,
    MemoryMode,
    OrchestrationMode,
)
from .scenarios import SCENARIO_DEFINITIONS, ScenarioDefinition


_EDGE_ENV_VALUES = {"1", "true", "yes", "on"}


def _detect_edge_mode_flag() -> bool:
    raw = os.getenv("EDGE_MODE", "0")
    if raw is None:
        return False  # type: ignore[unreachable]
    return raw.strip().lower() in _EDGE_ENV_VALUES


def _pick_context_snapshot(context: Optional[Mapping[str, Any]], *, limit: int = 6) -> Dict[str, Any]:
    if not context:
        return {}
    out: Dict[str, Any] = {}
    for idx, (key, value) in enumerate(context.items()):
        if idx >= limit:
            break
        out[str(key)] = value
    return out


class AgentArchScenarioExecutor(AgentArchExecutor):
    """Concrete executor leveraging static scenario metadata.

    The executor does not call external LLM providers. Instead it simulates
    the expected behaviour of the orchestration pipeline by combining the
    scenario difficulties with heuristics derived from the selected
    configuration (topology/orchestration/memory). This keeps the benchmarks
    reproducible, fast and offline-friendly while still providing meaningful
    differentials between configurations.
    """

    def __init__(
        self,
        *,
        scenarios: Optional[Mapping[str, ScenarioDefinition]] = None,
        edge_mode: Optional[bool] = None,
    ) -> None:
        self._scenarios = dict(scenarios or SCENARIO_DEFINITIONS)
        self._edge_mode = _detect_edge_mode_flag() if edge_mode is None else bool(edge_mode)

    async def execute(
        self,
        config: BenchmarkRunConfig,
        *,
        context: Optional[Dict[str, Any]] = None,
        attempt: int,
    ) -> AgentExecutionOutcome:
        scenario = self._resolve_scenario(config.scenario_id)
        capacity = self._compute_capacity(config, scenario, context or {})
        tasks_total = max(1, len(scenario.tasks))
        solved = sum(1 for task in scenario.tasks if capacity >= task.difficulty)
        score = solved / tasks_total
        threshold = scenario.success_threshold
        success = score >= threshold

        cost, cost_multiplier = self._estimate_cost(config, scenario, solved)
        latency_ms, latency_multiplier = self._estimate_latency(config, scenario, solved)

        details = {
            "score": round(score, 4),
            "tasks_total": tasks_total,
            "tasks_solved": solved,
            "threshold": round(threshold, 4),
            "capacity_index": round(capacity, 4),
            "edge_mode": self._edge_mode,
            "attempt": attempt,
            "cost_multiplier": round(cost_multiplier, 4),
            "latency_multiplier": round(latency_multiplier, 4),
            "context_snapshot": _pick_context_snapshot(context),
        }

        error_message = None
        if not success:
            error_message = (
                f"score {score:.2f} below threshold {threshold:.2f} for scenario {scenario.id}"
            )

        return AgentExecutionOutcome(
            success=success,
            cost=round(cost, 6),
            latency_ms=round(latency_ms, 3),
            error_message=error_message,
            retryable=False,
            details=details,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _resolve_scenario(self, scenario_id: str) -> ScenarioDefinition:
        try:
            return self._scenarios[scenario_id]
        except KeyError as exc:  # pragma: no cover - defensive
            raise ValueError(f"Unknown benchmark scenario: {scenario_id}") from exc

    def _compute_capacity(
        self,
        config: BenchmarkRunConfig,
        scenario: ScenarioDefinition,
        context: Dict[str, Any],
    ) -> float:
        base = 0.52
        if config.agent_topology == AgentTopology.MULTI_AGENT:
            base += 0.09
        else:
            base += 0.04

        if config.orchestration_mode == OrchestrationMode.FUNCTION_CALLING:
            base += 0.11
        else:
            base += 0.06

        if config.memory_mode == MemoryMode.FULL:
            base += 0.08
        else:
            base -= 0.015

        # Scenario-specific adjustments
        topology_bias = (scenario.metadata.get("topology_bias") or {}).get(
            config.agent_topology.value, 0.0
        )
        memory_adjustment = (scenario.metadata.get("memory_adjustment") or {}).get(
            config.memory_mode.value, 0.0
        )
        orchestration_bonus = (scenario.metadata.get("orchestration_bonus") or {}).get(
            config.orchestration_mode.value, 0.0
        )

        base += float(topology_bias)
        base += float(memory_adjustment)
        base += float(orchestration_bonus)

        if self._edge_mode:
            base -= 0.05

        if context:
            base += float(context.get("capacity_boost", 0.0))
            base -= float(context.get("capacity_penalty", 0.0))

        return max(0.25, min(0.97, base))

    def _estimate_cost(
        self,
        config: BenchmarkRunConfig,
        scenario: ScenarioDefinition,
        solved: int,
    ) -> tuple[float, float]:
        multiplier = 1.0
        if config.agent_topology == AgentTopology.MULTI_AGENT:
            multiplier += 0.33
        else:
            multiplier += 0.08

        if config.orchestration_mode == OrchestrationMode.FUNCTION_CALLING:
            multiplier += 0.2
        else:
            multiplier += 0.05

        if config.memory_mode == MemoryMode.FULL:
            multiplier += 0.14
        else:
            multiplier -= 0.04

        if self._edge_mode:
            multiplier -= 0.08

        cost = scenario.base_cost * multiplier
        cost += solved * 0.00035
        return max(cost, scenario.base_cost * 0.45), multiplier

    def _estimate_latency(
        self,
        config: BenchmarkRunConfig,
        scenario: ScenarioDefinition,
        solved: int,
    ) -> tuple[float, float]:
        multiplier = 1.0
        if config.agent_topology == AgentTopology.MULTI_AGENT:
            multiplier += 0.26
        else:
            multiplier -= 0.04

        if config.orchestration_mode == OrchestrationMode.FUNCTION_CALLING:
            multiplier += 0.12
        else:
            multiplier -= 0.02

        if config.memory_mode == MemoryMode.FULL:
            multiplier += 0.08
        else:
            multiplier -= 0.03

        if self._edge_mode:
            multiplier *= 0.92

        latency = scenario.base_latency_ms * multiplier
        latency += solved * 21.5
        return max(latency, scenario.base_latency_ms * 0.6), multiplier


__all__ = ["AgentArchScenarioExecutor"]
