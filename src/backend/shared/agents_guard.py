# src/backend/shared/agents_guard.py
"""
P2.3 - Garde-fous coût/risque agents

Fournit 3 classes pour protéger le système contre les dérives:
1. RoutePolicy - Redirige vers SLM local sauf si escalade nécessaire
2. BudgetGuard - Limite les tokens/jour par agent
3. ToolCircuitBreaker - Timeout et backoff exponentiel sur les tools
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Callable, Dict, List, Optional, TypeVar, Awaitable
from enum import Enum

logger = logging.getLogger(__name__)

T = TypeVar("T")


# ============================================================
# 1️⃣ RoutePolicy - Redirection SLM/LLM intelligente
# ============================================================

class ModelTier(str, Enum):
    """Tiers de modèles disponibles"""
    SLM = "slm"          # Small Language Model (local ou léger)
    LLM_LIGHT = "llm_light"  # LLM léger (GPT-3.5, Claude Haiku)
    LLM_HEAVY = "llm_heavy"  # LLM lourd (GPT-4, Claude Sonnet/Opus)


@dataclass
class RoutingDecision:
    """Décision de routing pour une requête agent"""
    tier: ModelTier
    reason: str
    confidence: Optional[float] = None
    tools_missing: bool = False


class RoutePolicy:
    """
    Politique de routing intelligente pour les agents.

    Stratégie par défaut:
    - SLM local si confidence >= 0.65 ET tools disponibles
    - Escalade vers LLM si:
      * Confidence < 0.65 (requête complexe)
      * Tools manquants (SLM ne peut pas gérer)
      * Override explicite

    Exemple config YAML:
        routing:
          default: slm
          escalate_on:
            - confidence_below: 0.65
            - tool_missing: true
    """

    def __init__(
        self,
        default_tier: ModelTier = ModelTier.SLM,
        confidence_threshold: float = 0.65,
        enable_tool_check: bool = True,
    ):
        self.default_tier = default_tier
        self.confidence_threshold = confidence_threshold
        self.enable_tool_check = enable_tool_check

    def decide(
        self,
        query: str,
        confidence: Optional[float] = None,
        required_tools: Optional[List[str]] = None,
        available_tools: Optional[List[str]] = None,
    ) -> RoutingDecision:
        """
        Décide du tier de modèle à utiliser.

        Args:
            query: Requête utilisateur
            confidence: Score de confidence (0-1) si disponible
            required_tools: Outils requis par la requête
            available_tools: Outils disponibles dans le contexte actuel

        Returns:
            RoutingDecision avec tier + raison
        """
        # Check 1: Tools manquants?
        if self.enable_tool_check and required_tools and available_tools is not None:
            missing = set(required_tools) - set(available_tools)
            if missing:
                return RoutingDecision(
                    tier=ModelTier.LLM_LIGHT,
                    reason=f"Tools manquants: {missing}",
                    tools_missing=True,
                )

        # Check 2: Confidence trop basse?
        if confidence is not None and confidence < self.confidence_threshold:
            return RoutingDecision(
                tier=ModelTier.LLM_LIGHT,
                reason=f"Confidence faible ({confidence:.2f} < {self.confidence_threshold})",
                confidence=confidence,
            )

        # Check 3: Requête très longue → probablement complexe
        if len(query) > 500:  # > 500 chars
            return RoutingDecision(
                tier=ModelTier.LLM_LIGHT,
                reason=f"Requête longue ({len(query)} chars)",
            )

        # Default: SLM local
        return RoutingDecision(
            tier=self.default_tier,
            reason="Conditions standard (confidence OK, tools OK)",
            confidence=confidence,
        )


# ============================================================
# 2️⃣ BudgetGuard - Limite tokens/jour par agent
# ============================================================

@dataclass
class AgentBudget:
    """Budget quotidien pour un agent"""
    agent_id: str
    max_tokens_per_day: int
    used_tokens_today: int = 0
    reset_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def reset_if_needed(self):
        """Reset le compteur si on a dépassé minuit UTC"""
        now = datetime.now(timezone.utc)
        if now.date() > self.reset_at.date():
            self.used_tokens_today = 0
            self.reset_at = now
            logger.info(f"[BudgetGuard] Reset budget quotidien pour {self.agent_id}")

    @property
    def remaining_tokens(self) -> int:
        """Tokens restants aujourd'hui"""
        self.reset_if_needed()
        return max(0, self.max_tokens_per_day - self.used_tokens_today)

    @property
    def is_exhausted(self) -> bool:
        """Budget épuisé?"""
        return self.remaining_tokens == 0


class BudgetGuard:
    """
    Garde-fou pour limiter les tokens par agent par jour.

    Exemple config YAML:
        agents:
          anima: {max_tokens_day: 120000}
          neo:   {max_tokens_day: 80000}
          nexus: {max_tokens_day: 60000}
    """

    def __init__(self, budgets: Dict[str, int]):
        """
        Args:
            budgets: Dict {agent_id: max_tokens_per_day}
        """
        self.budgets: Dict[str, AgentBudget] = {}
        for agent_id, max_tokens in budgets.items():
            self.budgets[agent_id] = AgentBudget(
                agent_id=agent_id,
                max_tokens_per_day=max_tokens,
            )

    def check(self, agent_id: str, estimated_tokens: int) -> bool:
        """
        Vérifie si l'agent peut consommer estimated_tokens.

        Args:
            agent_id: ID de l'agent (anima, neo, nexus)
            estimated_tokens: Nombre de tokens estimé pour cette requête

        Returns:
            True si budget OK, False si épuisé

        Raises:
            RuntimeError si budget épuisé
        """
        if agent_id not in self.budgets:
            # Pas de limite définie pour cet agent
            return True

        budget = self.budgets[agent_id]
        budget.reset_if_needed()

        if budget.is_exhausted:
            logger.error(
                f"[BudgetGuard] Budget épuisé pour {agent_id} "
                f"({budget.used_tokens_today}/{budget.max_tokens_per_day} tokens utilisés)"
            )
            raise RuntimeError(
                f"budget_exceeded:{agent_id}:{budget.used_tokens_today}/{budget.max_tokens_per_day}"
            )

        if budget.remaining_tokens < estimated_tokens:
            logger.warning(
                f"[BudgetGuard] Budget quasi-épuisé pour {agent_id} "
                f"({budget.remaining_tokens} tokens restants < {estimated_tokens} requis)"
            )
            # On autorise quand même mais on log
            return True

        return True

    def consume(self, agent_id: str, actual_tokens: int):
        """
        Enregistre la consommation réelle de tokens.

        Args:
            agent_id: ID de l'agent
            actual_tokens: Nombre de tokens réellement consommés
        """
        if agent_id not in self.budgets:
            return

        budget = self.budgets[agent_id]
        budget.reset_if_needed()
        budget.used_tokens_today += actual_tokens

        logger.info(
            f"[BudgetGuard] {agent_id} a consommé {actual_tokens} tokens "
            f"({budget.used_tokens_today}/{budget.max_tokens_per_day} utilisés, "
            f"{budget.remaining_tokens} restants)"
        )

    def get_status(self, agent_id: str) -> Dict[str, Any]:
        """Retourne le statut du budget pour un agent"""
        if agent_id not in self.budgets:
            return {"error": "No budget defined"}

        budget = self.budgets[agent_id]
        budget.reset_if_needed()

        return {
            "agent_id": agent_id,
            "max_tokens_per_day": budget.max_tokens_per_day,
            "used_tokens_today": budget.used_tokens_today,
            "remaining_tokens": budget.remaining_tokens,
            "percent_used": round(
                (budget.used_tokens_today / budget.max_tokens_per_day) * 100, 1
            ),
            "is_exhausted": budget.is_exhausted,
            "reset_at": budget.reset_at.isoformat(),
        }


# ============================================================
# 3️⃣ ToolCircuitBreaker - Timeout + Backoff exponentiel
# ============================================================

@dataclass
class CircuitState:
    """État du circuit breaker pour un outil"""
    tool_name: str
    failures: int = 0
    last_failure: Optional[datetime] = None
    backoff_until: Optional[datetime] = None
    total_calls: int = 0
    total_failures: int = 0

    @property
    def is_open(self) -> bool:
        """Circuit ouvert (outil temporairement désactivé)?"""
        if self.backoff_until is None:
            return False
        return datetime.now(timezone.utc) < self.backoff_until


class ToolCircuitBreaker:
    """
    Circuit breaker avec timeout et backoff exponentiel pour les tools.

    Stratégie:
    - Timeout par défaut: 30s
    - Backoff exponentiel: 0.5s, 1s, 2s, 4s, 8s (max 8s)
    - Reset après 1 minute sans échec

    Exemple config YAML:
        tools:
          circuit_breaker:
            timeout_s: 30
            backoff: "exp:0.5..8s"
            max_failures: 3
    """

    def __init__(
        self,
        timeout_seconds: float = 30.0,
        backoff_base: float = 0.5,
        backoff_max: float = 8.0,
        max_consecutive_failures: int = 3,
        reset_after_seconds: float = 60.0,
    ):
        self.timeout_seconds = timeout_seconds
        self.backoff_base = backoff_base
        self.backoff_max = backoff_max
        self.max_consecutive_failures = max_consecutive_failures
        self.reset_after_seconds = reset_after_seconds

        self.circuits: Dict[str, CircuitState] = {}

    def _get_circuit(self, tool_name: str) -> CircuitState:
        """Récupère ou crée l'état du circuit pour un outil"""
        if tool_name not in self.circuits:
            self.circuits[tool_name] = CircuitState(tool_name=tool_name)
        return self.circuits[tool_name]

    def _calculate_backoff(self, failures: int) -> float:
        """Calcule le délai de backoff exponentiel"""
        delay = self.backoff_base * (2 ** failures)
        return min(delay, self.backoff_max)

    async def execute(
        self,
        tool_name: str,
        func: Callable[..., Awaitable[T]],
        *args,
        **kwargs,
    ) -> T:
        """
        Exécute une fonction tool avec timeout et circuit breaker.

        Args:
            tool_name: Nom de l'outil (pour tracking)
            func: Fonction async à exécuter
            *args, **kwargs: Arguments de la fonction

        Returns:
            Résultat de la fonction

        Raises:
            TimeoutError si timeout dépassé
            RuntimeError si circuit ouvert
        """
        circuit = self._get_circuit(tool_name)

        # Check 1: Circuit ouvert?
        if circuit.is_open:
            assert circuit.backoff_until is not None  # Garanti par is_open()
            wait_seconds = (circuit.backoff_until - datetime.now(timezone.utc)).total_seconds()
            logger.warning(
                f"[ToolCircuitBreaker] Circuit OUVERT pour {tool_name} "
                f"(attend {wait_seconds:.1f}s avant retry)"
            )
            raise RuntimeError(
                f"circuit_open:{tool_name}:wait_{wait_seconds:.1f}s"
            )

        # Check 2: Reset si pas d'échec récent
        if circuit.last_failure:
            time_since_failure = (
                datetime.now(timezone.utc) - circuit.last_failure
            ).total_seconds()
            if time_since_failure > self.reset_after_seconds:
                logger.info(
                    f"[ToolCircuitBreaker] Reset circuit pour {tool_name} "
                    f"({time_since_failure:.1f}s sans échec)"
                )
                circuit.failures = 0
                circuit.backoff_until = None

        # Exécution avec timeout
        circuit.total_calls += 1
        try:
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=self.timeout_seconds,
            )

            # Succès: reset failures
            if circuit.failures > 0:
                logger.info(
                    f"[ToolCircuitBreaker] {tool_name} réussi après {circuit.failures} échecs"
                )
                circuit.failures = 0
                circuit.backoff_until = None

            return result

        except asyncio.TimeoutError:
            # Timeout dépassé
            circuit.failures += 1
            circuit.total_failures += 1
            circuit.last_failure = datetime.now(timezone.utc)

            logger.error(
                f"[ToolCircuitBreaker] Timeout {tool_name} après {self.timeout_seconds}s "
                f"({circuit.failures} échecs consécutifs)"
            )

            # Ouvrir le circuit si trop d'échecs
            if circuit.failures >= self.max_consecutive_failures:
                backoff = self._calculate_backoff(circuit.failures)
                circuit.backoff_until = datetime.now(timezone.utc) + timedelta(
                    seconds=backoff
                )
                logger.error(
                    f"[ToolCircuitBreaker] Circuit OUVERT pour {tool_name} "
                    f"(backoff {backoff}s)"
                )

            raise TimeoutError(
                f"{tool_name} timeout après {self.timeout_seconds}s"
            )

        except Exception as e:
            # Autre erreur
            circuit.failures += 1
            circuit.total_failures += 1
            circuit.last_failure = datetime.now(timezone.utc)

            logger.error(
                f"[ToolCircuitBreaker] Erreur {tool_name}: {e} "
                f"({circuit.failures} échecs consécutifs)"
            )

            # Ouvrir le circuit si trop d'échecs
            if circuit.failures >= self.max_consecutive_failures:
                backoff = self._calculate_backoff(circuit.failures)
                circuit.backoff_until = datetime.now(timezone.utc) + timedelta(
                    seconds=backoff
                )
                logger.error(
                    f"[ToolCircuitBreaker] Circuit OUVERT pour {tool_name} "
                    f"(backoff {backoff}s)"
                )

            raise

    def get_status(self, tool_name: str) -> Dict[str, Any]:
        """Retourne le statut du circuit breaker pour un outil"""
        if tool_name not in self.circuits:
            return {"error": "No circuit defined"}

        circuit = self.circuits[tool_name]
        now = datetime.now(timezone.utc)

        status = {
            "tool_name": tool_name,
            "is_open": circuit.is_open,
            "failures": circuit.failures,
            "total_calls": circuit.total_calls,
            "total_failures": circuit.total_failures,
            "success_rate": round(
                ((circuit.total_calls - circuit.total_failures) / circuit.total_calls) * 100, 1
            ) if circuit.total_calls > 0 else 100.0,
        }

        if circuit.last_failure:
            status["last_failure"] = circuit.last_failure.isoformat()
            status["time_since_failure"] = round(
                (now - circuit.last_failure).total_seconds(), 1
            )

        if circuit.backoff_until:
            status["backoff_until"] = circuit.backoff_until.isoformat()
            status["wait_seconds"] = max(
                0, round((circuit.backoff_until - now).total_seconds(), 1)
            )

        return status
