# src/backend/core/tracing/trace_manager.py
# V1.0 - Distributed tracing for ÉMERGENCE V8
#
# Lightweight OpenTelemetry-style tracing without external dependencies.
# Tracks spans (retrieval, llm_generate, memory_update, tool_call) with:
# - trace_id: correlates all spans in a conversation
# - span_id: unique identifier per span
# - parent_id: parent span for nested traces
# - duration: computed from start/end timestamps
# - status: OK, ERROR, TIMEOUT
#
# Export to Prometheus metrics (counters, histograms) for Grafana visualization.

import asyncio
import logging
import time
import uuid
from contextvars import ContextVar
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, TypeVar, cast

# Import metrics recorder (lazy import pour éviter circular dependency)
try:
    from .metrics import record_span

    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False
    record_span = None  # type: ignore

logger = logging.getLogger(__name__)

# Context var pour propager trace_id/span_id à travers async calls
_current_trace_id: ContextVar[Optional[str]] = ContextVar("trace_id", default=None)
_current_span_id: ContextVar[Optional[str]] = ContextVar("span_id", default=None)


class SpanStatus(str, Enum):
    """Status d'un span (OK, ERROR, TIMEOUT)."""

    OK = "OK"
    ERROR = "ERROR"
    TIMEOUT = "TIMEOUT"


class Span:
    """
    Représente un span de trace (une opération trackée).

    Attributes:
        span_id: Identifiant unique du span
        name: Nom du span (ex: "retrieval", "llm_generate")
        trace_id: ID de la trace parente (corrélation)
        parent_id: ID du span parent (si nested)
        start_time: Timestamp de début (seconds since epoch)
        end_time: Timestamp de fin (seconds since epoch)
        duration: Durée en secondes (end_time - start_time)
        status: État final (OK, ERROR, TIMEOUT)
        attributes: Métadonnées additionnelles (agent, model, tokens, etc.)
    """

    def __init__(
        self,
        name: str,
        trace_id: str,
        parent_id: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ):
        self.span_id = str(uuid.uuid4())
        self.name = name
        self.trace_id = trace_id
        self.parent_id = parent_id
        self.start_time = time.time()
        self.end_time: Optional[float] = None
        self.duration: Optional[float] = None
        self.status = SpanStatus.OK
        self.attributes = attributes or {}

    def end(self, status: SpanStatus = SpanStatus.OK) -> None:
        """Termine le span et calcule la durée."""
        if self.end_time is None:
            self.end_time = time.time()
            self.duration = self.end_time - self.start_time
            self.status = status

    def to_dict(self) -> Dict[str, Any]:
        """Export le span en dict pour logs structurés / export."""
        return {
            "span_id": self.span_id,
            "name": self.name,
            "trace_id": self.trace_id,
            "parent_id": self.parent_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "status": self.status.value,
            "attributes": self.attributes,
        }


class TraceManager:
    """
    Gestionnaire de traces distribué (léger, sans OpenTelemetry).

    Conserve les spans en mémoire (FIFO, max 1000 par défaut).
    Expose les spans pour export Prometheus ou logs structurés.

    Usage:
        trace_mgr = TraceManager()

        # Démarrer un span
        span_id = trace_mgr.start_span("retrieval", attrs={"agent": "AnimA"})

        # ... opération ...

        # Terminer le span
        trace_mgr.end_span(span_id, status="OK")

        # Export pour Prometheus
        spans = trace_mgr.export()
    """

    def __init__(self, max_spans: int = 1000):
        self._spans: Dict[str, Span] = {}
        self._completed_spans: List[Span] = []
        self._max_spans = max_spans

    def start_span(
        self,
        name: str,
        parent_id: Optional[str] = None,
        attrs: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Démarre un nouveau span.

        Args:
            name: Nom du span (ex: "retrieval", "llm_generate")
            parent_id: ID du span parent (si nested)
            attrs: Attributs supplémentaires (agent, model, tokens, etc.)

        Returns:
            span_id: Identifiant unique du span créé
        """
        # Récupère trace_id du contexte ou génère-en un nouveau
        trace_id = _current_trace_id.get()
        if trace_id is None:
            trace_id = str(uuid.uuid4())
            _current_trace_id.set(trace_id)

        # Si pas de parent_id fourni, utilise le span courant comme parent
        if parent_id is None:
            parent_id = _current_span_id.get()

        span = Span(name=name, trace_id=trace_id, parent_id=parent_id, attributes=attrs)
        self._spans[span.span_id] = span

        # Propage le span_id dans le contexte pour nested spans
        _current_span_id.set(span.span_id)

        logger.debug(
            f"[Trace] Started span: {name} (span_id={span.span_id}, trace_id={trace_id})"
        )

        return span.span_id

    def end_span(self, span_id: str, status: str = "OK") -> None:
        """
        Termine un span existant.

        Args:
            span_id: ID du span à terminer
            status: État final ("OK", "ERROR", "TIMEOUT")
        """
        span = self._spans.get(span_id)
        if span is None:
            logger.warning(f"[Trace] Attempted to end unknown span: {span_id}")
            return

        # Parse status
        try:
            span_status = SpanStatus(status.upper())
        except ValueError:
            logger.warning(f"[Trace] Invalid status '{status}', defaulting to OK")
            span_status = SpanStatus.OK

        span.end(status=span_status)

        # Déplace vers completed_spans
        self._completed_spans.append(span)
        del self._spans[span_id]

        # FIFO: limite le buffer
        if len(self._completed_spans) > self._max_spans:
            self._completed_spans.pop(0)

        logger.debug(
            f"[Trace] Ended span: {span.name} (duration={span.duration:.3f}s, status={status})"
        )

        # Export vers Prometheus metrics
        if METRICS_AVAILABLE and span.duration is not None:
            agent = span.attributes.get("agent", "unknown")
            record_span(
                span_name=span.name,
                agent=str(agent),
                status=span.status.value,
                duration=span.duration,
            )

        # Restaure le contexte parent (si nested)
        if span.parent_id:
            _current_span_id.set(span.parent_id)
        else:
            _current_span_id.set(None)

    def export(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Export les derniers spans complétés (pour Prometheus / logs structurés).

        Args:
            limit: Nombre max de spans à retourner (défaut 100)

        Returns:
            Liste de dicts représentant les spans (du plus récent au plus ancien)
        """
        # Retourne les `limit` derniers spans (reversed = plus récents d'abord)
        recent_spans = self._completed_spans[-limit:][::-1]
        return [span.to_dict() for span in recent_spans]

    def get_span(self, span_id: str) -> Optional[Span]:
        """Récupère un span actif par ID (pour debugging)."""
        return self._spans.get(span_id)

    def clear(self) -> None:
        """Nettoie tous les spans (utile pour tests)."""
        self._spans.clear()
        self._completed_spans.clear()


# Singleton global (accessible via get_trace_manager)
_global_trace_manager: Optional[TraceManager] = None


def get_trace_manager() -> TraceManager:
    """Retourne le TraceManager global (singleton)."""
    global _global_trace_manager
    if _global_trace_manager is None:
        _global_trace_manager = TraceManager()
    return _global_trace_manager


# Type var pour décorateur
F = TypeVar("F", bound=Callable[..., Any])


def trace_span(name: str, **attrs: Any) -> Callable[[F], F]:
    """
    Décorateur pour tracer automatiquement une fonction async.

    Usage:
        @trace_span("llm_generate", agent="AnimA")
        async def _generate_llm(self, prompt: str) -> str:
            ...

    Le span démarre au début de la fonction et se termine automatiquement
    (status=OK si succès, status=ERROR si exception).
    """

    def decorator(func: F) -> F:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            mgr = get_trace_manager()
            span_id = mgr.start_span(name, attrs=attrs)

            try:
                result = await func(*args, **kwargs)
                mgr.end_span(span_id, status="OK")
                return result
            except Exception as e:
                mgr.end_span(span_id, status="ERROR")
                logger.error(f"[Trace] Span {name} failed: {e}")
                raise

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            mgr = get_trace_manager()
            span_id = mgr.start_span(name, attrs=attrs)

            try:
                result = func(*args, **kwargs)
                mgr.end_span(span_id, status="OK")
                return result
            except Exception as e:
                mgr.end_span(span_id, status="ERROR")
                logger.error(f"[Trace] Span {name} failed: {e}")
                raise

        # Détecte si fonction async ou sync
        if asyncio.iscoroutinefunction(func):
            return cast(F, async_wrapper)
        else:
            return cast(F, sync_wrapper)

    return decorator
