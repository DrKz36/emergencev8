# src/backend/benchmarks/agentarch_runner.py
"""BenchmarksRunner V1.0 — matrice d'expérimentation agentique.

Ce module orchestre l'exécution d'une matrice de benchmarks couvrant
plusieurs topologies d'agents, stratégies d'orchestration et profils
mémoire. Les résultats produits sont prêts à être exposés côté API ou
persistés dans une base (Firestore, SQLite, ...).
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from itertools import product
from typing import Any, Dict, Iterable, List, Optional, Protocol

logger = logging.getLogger(__name__)


class AgentTopology(str, Enum):
    """Enumère les architectures agentiques supportées par la matrice."""

    MONO_AGENT = "mono-agent"
    MULTI_AGENT = "multi-agent"


class OrchestrationMode(str, Enum):
    """Enumère les stratégies d'orchestration disponibles."""

    REACT = "react"
    FUNCTION_CALLING = "function-calling"


class MemoryMode(str, Enum):
    """Enumère les profils mémoire à évaluer."""

    FULL = "full-memory"
    SUMMARIZED = "summary-memory"


@dataclass(frozen=True)
class BenchmarkRunConfig:
    """Décrit la configuration d'un run dans la matrice d'expérimentation."""

    agent_topology: AgentTopology
    orchestration_mode: OrchestrationMode
    memory_mode: MemoryMode
    scenario_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def slug(self) -> str:
        """Identifiant humain de la configuration (pour logs et reporting)."""

        return "::".join(
            (
                self.agent_topology.value,
                self.orchestration_mode.value,
                self.memory_mode.value,
                self.scenario_id,
            )
        )

    def to_dict(self) -> Dict[str, Any]:
        """Sérialise la configuration pour les API / stockages."""

        return {
            "agent_topology": self.agent_topology.value,
            "orchestration_mode": self.orchestration_mode.value,
            "memory_mode": self.memory_mode.value,
            "scenario_id": self.scenario_id,
            "metadata": dict(self.metadata),
            "slug": self.slug,
        }


@dataclass
class AgentExecutionOutcome:
    """Résultat retourné par l'exécuteur agentique pour un run donné."""

    success: bool
    cost: float
    latency_ms: Optional[float] = None
    error_message: Optional[str] = None
    retryable: bool = False
    details: Dict[str, Any] = field(default_factory=dict)


class AgentArchExecutor(Protocol):
    """Contrat minimal pour l'exécuteur de scénarios benchmark."""

    async def execute(
        self,
        config: BenchmarkRunConfig,
        *,
        context: Optional[Dict[str, Any]] = None,
        attempt: int,
    ) -> AgentExecutionOutcome:
        """Lance un run avec la configuration fournie et retourne son outcome."""


class BenchmarkResultSink(Protocol):
    """Abstraction de persistance pour enregistrer les résultats."""

    async def persist_run(self, result: "BenchmarkRunResult") -> None:
        """Persiste un run individuel (Firestore, SQLite, ...)."""

    async def persist_matrix(
        self,
        matrix: "BenchmarkMatrixResult",
    ) -> None:
        """Persiste la synthèse de la matrice complète."""


class NullBenchmarkResultSink:
    """Implémentation par défaut qui ignore la persistance."""

    async def persist_run(
        self, result: "BenchmarkRunResult"
    ) -> None:  # pragma: no cover - null sink
        return

    async def persist_matrix(
        self, matrix: "BenchmarkMatrixResult"
    ) -> None:  # pragma: no cover - null sink
        return


@dataclass
class BenchmarkRunResult:
    """Consolide les métriques d'un run de benchmark."""

    config: BenchmarkRunConfig
    success: bool
    retries: int
    cost: float
    latency_ms: float
    started_at: datetime
    completed_at: datetime
    error_message: Optional[str] = None
    executor_details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Sérialise le run en dictionnaire JSON-friendly."""

        return {
            "config": self.config.to_dict(),
            "success": self.success,
            "retries": self.retries,
            "cost": self.cost,
            "latency_ms": self.latency_ms,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat(),
            "error_message": self.error_message,
            "executor_details": dict(self.executor_details),
        }

    @property
    def status_label(self) -> str:
        """Retourne "success" ou "failure" pour simplifier l'usage frontend."""

        return "success" if self.success else "failure"


@dataclass
class BenchmarkMatrixResult:
    """Vue agrégée de la matrice d'expérimentation complète."""

    scenario_id: str
    results: List[BenchmarkRunResult]
    started_at: datetime
    completed_at: datetime
    edge_mode_enabled: bool
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Sérialise la matrice complète en dictionnaire JSON-friendly."""

        return {
            "scenario_id": self.scenario_id,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat(),
            "edge_mode_enabled": self.edge_mode_enabled,
            "context": dict(self.context),
            "results": [item.to_dict() for item in self.results],
        }


class BenchmarksRunner:
    """Orchestre l'exécution de la matrice d'expérimentation agentique."""

    VERSION = "BenchmarksRunner V1.0"

    def __init__(
        self,
        executor: AgentArchExecutor,
        *,
        sink: Optional[BenchmarkResultSink] = None,
        max_retries: int = 2,
        base_backoff_seconds: float = 0.75,
        concurrency: int = 2,
    ) -> None:
        self.executor = executor
        self.sink = sink or NullBenchmarkResultSink()
        self.max_retries = max(0, int(max_retries))
        self.base_backoff_seconds = max(0.1, float(base_backoff_seconds))
        self.concurrency = max(1, int(concurrency))
        self._edge_mode = self._detect_edge_mode()
        logger.info(
            "%s initialisé (edge_mode=%s, max_retries=%s, concurrency=%s)",
            self.VERSION,
            self._edge_mode,
            self.max_retries,
            self.concurrency,
        )

    async def run_matrix(
        self,
        *,
        scenario_id: str,
        context: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> BenchmarkMatrixResult:
        """Exécute la matrice complète et renvoie la synthèse des résultats."""

        started_at = datetime.now(timezone.utc)
        context_payload = dict(context or {})
        metadata_payload = dict(metadata or {})
        configs = list(
            self._iter_matrix(scenario_id=scenario_id, metadata=metadata_payload)
        )
        logger.info(
            "Démarrage matrice benchmarks (%s runs) pour scenario=%s",
            len(configs),
            scenario_id,
        )

        semaphore = asyncio.Semaphore(self.concurrency)
        run_results: List[BenchmarkRunResult] = []

        async def _run(config: BenchmarkRunConfig) -> None:
            async with semaphore:
                result = await self._execute_with_retries(
                    config=config, context=context_payload
                )
                await self.sink.persist_run(result)
                run_results.append(result)

        await asyncio.gather(*[asyncio.create_task(_run(cfg)) for cfg in configs])
        run_results.sort(key=lambda item: item.config.slug)

        completed_at = datetime.now(timezone.utc)
        matrix = BenchmarkMatrixResult(
            scenario_id=scenario_id,
            results=run_results,
            started_at=started_at,
            completed_at=completed_at,
            edge_mode_enabled=self._edge_mode,
            context={**context_payload, "metadata": metadata_payload},
        )
        await self.sink.persist_matrix(matrix)
        logger.info(
            "Matrice benchmarks terminée pour scenario=%s (succès=%s/%s)",
            scenario_id,
            sum(1 for item in run_results if item.success),
            len(run_results),
        )
        return matrix

    async def run_single(
        self,
        config: BenchmarkRunConfig,
        *,
        context: Optional[Dict[str, Any]] = None,
    ) -> BenchmarkRunResult:
        """Exécute une seule configuration (utile pour les tests ciblés)."""

        result = await self._execute_with_retries(
            config=config, context=dict(context or {})
        )
        await self.sink.persist_run(result)
        return result

    async def _execute_with_retries(
        self,
        *,
        config: BenchmarkRunConfig,
        context: Optional[Dict[str, Any]] = None,
    ) -> BenchmarkRunResult:
        """Encapsule la logique de retry + mesure des temps/coûts."""

        retries = 0
        run_started_at = datetime.now(timezone.utc)
        run_timer = time.perf_counter()
        context_payload = dict(context or {})
        last_error_message: Optional[str] = None
        executor_details: Dict[str, Any] = {}
        cost_accumulator = 0.0
        latency_ms = 0.0

        for attempt in range(1, self.max_retries + 2):
            attempt_timer = time.perf_counter()
            try:
                outcome = await self.executor.execute(
                    config,
                    context=context_payload,
                    attempt=attempt,
                )
            except Exception as exc:  # pylint: disable=broad-except
                last_error_message = self._format_exception(exc)
                executor_details = {"exception_type": exc.__class__.__name__}
                logger.warning(
                    "Benchmark run failed (config=%s, attempt=%s): %s",
                    config.slug,
                    attempt,
                    last_error_message,
                )
                outcome = AgentExecutionOutcome(
                    success=False,
                    cost=0.0,
                    latency_ms=(time.perf_counter() - attempt_timer) * 1000.0,
                    error_message=last_error_message,
                    retryable=True,
                    details={},
                )

            latency_ms = (
                outcome.latency_ms or (time.perf_counter() - attempt_timer) * 1000.0
            )
            cost_accumulator += max(0.0, float(outcome.cost))
            executor_details = {**executor_details, **outcome.details}

            if outcome.success:
                last_error_message = None
                break

            last_error_message = outcome.error_message or last_error_message
            if attempt > self.max_retries or not outcome.retryable:
                retries = attempt - 1
                break

            retries = attempt
            backoff = self._compute_backoff_seconds(attempt)
            logger.info(
                "Retrying benchmark (config=%s, attempt=%s/%s, backoff=%.2fs)",
                config.slug,
                attempt,
                self.max_retries + 1,
                backoff,
            )
            await asyncio.sleep(backoff)

        run_completed_at = datetime.now(timezone.utc)
        total_latency_ms = (time.perf_counter() - run_timer) * 1000.0
        aggregated_latency_ms = max(latency_ms, total_latency_ms)
        success = last_error_message is None

        result = BenchmarkRunResult(
            config=config,
            success=success,
            retries=retries,
            cost=round(cost_accumulator, 6),
            latency_ms=round(aggregated_latency_ms, 3),
            started_at=run_started_at,
            completed_at=run_completed_at,
            error_message=last_error_message,
            executor_details=executor_details,
        )
        status = "OK" if success else f"KO ({last_error_message})"
        logger.info("Run terminé (%s) -> %s", config.slug, status)
        return result

    def _iter_matrix(
        self,
        *,
        scenario_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Iterable[BenchmarkRunConfig]:
        """Génère la matrice complète de configurations à évaluer."""

        metadata_payload = dict(metadata or {})
        axes = (
            list(AgentTopology),
            list(OrchestrationMode),
            list(MemoryMode),
        )
        for agent_topology, orchestration_mode, memory_mode in product(*axes):
            yield BenchmarkRunConfig(
                agent_topology=agent_topology,
                orchestration_mode=orchestration_mode,
                memory_mode=memory_mode,
                scenario_id=scenario_id,
                metadata={
                    **metadata_payload,
                    "edge_mode": self._edge_mode,
                },
            )

    def _compute_backoff_seconds(self, attempt: int) -> float:
        """Calcule le délai de backoff exponentiel (avec plafonnement)."""
        from typing import cast

        capped_attempt = min(max(attempt, 1), 6)
        delay = self.base_backoff_seconds * (2 ** (capped_attempt - 1))
        return cast(float, round(delay, 3))

    @staticmethod
    def _format_exception(exc: BaseException) -> str:
        """Formate proprement une exception pour les logs / retours API."""

        return f"{exc.__class__.__name__}: {exc}".strip()

    @staticmethod
    def _detect_edge_mode() -> bool:
        """Détecte le mode edge via la variable d'environnement EDGE_MODE."""

        raw = os.getenv("EDGE_MODE", "0").strip().lower()
        return raw in {"1", "true", "yes", "on"}


__all__ = [
    "AgentTopology",
    "OrchestrationMode",
    "MemoryMode",
    "BenchmarkRunConfig",
    "AgentExecutionOutcome",
    "AgentArchExecutor",
    "BenchmarkResultSink",
    "BenchmarkRunResult",
    "BenchmarkMatrixResult",
    "BenchmarksRunner",
]
