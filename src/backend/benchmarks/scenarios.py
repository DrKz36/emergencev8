from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class ScenarioTask:
    """Represents a single evaluation task used inside a scenario."""

    id: str
    difficulty: float
    domain: str
    weight: float = 1.0


@dataclass(frozen=True)
class ScenarioDefinition:
    """Describes a benchmark scenario and its evaluation metadata."""

    id: str
    name: str
    description: str
    success_threshold: float
    base_cost: float
    base_latency_ms: float
    tasks: List[ScenarioTask] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


#: Static catalogue describing the supported benchmark scenarios.
SCENARIO_DEFINITIONS: Dict[str, ScenarioDefinition] = {
    "ARE": ScenarioDefinition(
        id="ARE",
        name="Agent Reasoning Evaluation",
        description=(
            "Corpus ciblant la résolution d'énigmes, la planification et les \n"
            "contre-arguments courts. Les difficultés sont équilibrées pour \n"
            "tester la qualité de raisonnement séquentiel et la consolidation \n"
            "mémoire sur des contextes compacts."
        ),
        success_threshold=0.74,
        base_cost=0.0045,
        base_latency_ms=820.0,
        tasks=[
            ScenarioTask(id="are-logic-bridge", difficulty=0.54, domain="logic"),
            ScenarioTask(id="are-math-apply", difficulty=0.61, domain="math"),
            ScenarioTask(id="are-plan", difficulty=0.69, domain="planning"),
            ScenarioTask(id="are-critique", difficulty=0.76, domain="critique"),
            ScenarioTask(id="are-counterfactual", difficulty=0.82, domain="analysis"),
        ],
        metadata={
            "source": "ARE v2.1",
            "tasks_total": 5,
            "license": "CC-BY-NC",
            "topology_bias": {"mono-agent": 0.03, "multi-agent": -0.02},
            "memory_adjustment": {"full-memory": 0.05, "summary-memory": -0.01},
            "orchestration_bonus": {"react": 0.04, "function-calling": 0.07},
        },
    ),
    "Gaia2": ScenarioDefinition(
        id="Gaia2",
        name="Gaia-II Knowledge & Strategy",
        description=(
            "Dataset hybride combinant questions de culture générale, analyses \n"
            "prospectives et scénarios de négociation. Les tâches favorisent la \n"
            "coopération multi-agent et la consolidation mémoire longue."
        ),
        success_threshold=0.77,
        base_cost=0.0058,
        base_latency_ms=910.0,
        tasks=[
            ScenarioTask(id="gaia2-historical", difficulty=0.58, domain="history"),
            ScenarioTask(id="gaia2-science", difficulty=0.71, domain="science"),
            ScenarioTask(id="gaia2-statistics", difficulty=0.77, domain="analysis"),
            ScenarioTask(id="gaia2-debate", difficulty=0.83, domain="debate"),
            ScenarioTask(id="gaia2-policy", difficulty=0.87, domain="policy"),
        ],
        metadata={
            "source": "Gaia-II mini-set",
            "tasks_total": 5,
            "license": "Gaia Research Commons",
            "topology_bias": {"mono-agent": -0.01, "multi-agent": 0.06},
            "memory_adjustment": {"full-memory": 0.06, "summary-memory": -0.02},
            "orchestration_bonus": {"react": 0.03, "function-calling": 0.08},
        },
    ),
}


def list_supported_scenarios() -> List[str]:
    """Returns the list of scenario identifiers supported by default."""

    return list(SCENARIO_DEFINITIONS.keys())


__all__ = [
    "ScenarioTask",
    "ScenarioDefinition",
    "SCENARIO_DEFINITIONS",
    "list_supported_scenarios",
]
