# tests/backend/core/test_trace_manager.py
# Tests unitaires pour TraceManager (Phase 3 Tracing)

import asyncio
import time
import pytest
from backend.core.tracing import TraceManager, SpanStatus, trace_span


class TestTraceManager:
    """Tests unitaires pour le TraceManager."""

    @pytest.fixture
    def trace_mgr(self):
        """Fixture: TraceManager propre pour chaque test."""
        mgr = TraceManager(max_spans=100)
        mgr.clear()
        return mgr

    def test_start_span_creates_valid_span(self, trace_mgr):
        """Test: start_span crée un span valide avec trace_id."""
        span_id = trace_mgr.start_span("test_operation", attrs={"agent": "test"})

        assert span_id is not None
        span = trace_mgr.get_span(span_id)
        assert span is not None
        assert span.name == "test_operation"
        assert span.trace_id is not None
        assert span.attributes["agent"] == "test"

    def test_end_span_calculates_duration(self, trace_mgr):
        """Test: end_span calcule la durée correctement."""
        span_id = trace_mgr.start_span("test_operation")
        time.sleep(0.01)  # 10ms minimum
        trace_mgr.end_span(span_id, status="OK")

        # Span déplacé vers completed_spans
        assert trace_mgr.get_span(span_id) is None
        exports = trace_mgr.export(limit=10)
        assert len(exports) == 1
        assert exports[0]["duration"] >= 0.01  # Au moins 10ms
        assert exports[0]["status"] == "OK"

    def test_end_span_handles_invalid_status(self, trace_mgr):
        """Test: end_span gère les statuts invalides (fallback OK)."""
        span_id = trace_mgr.start_span("test_operation")
        trace_mgr.end_span(span_id, status="INVALID_STATUS")

        exports = trace_mgr.export(limit=1)
        assert exports[0]["status"] == "OK"  # Fallback

    def test_end_span_unknown_id_doesnt_crash(self, trace_mgr):
        """Test: end_span avec span_id inconnu ne crash pas."""
        trace_mgr.end_span("unknown_span_id_12345", status="OK")
        # Ne devrait pas lever d'exception

    def test_export_returns_recent_spans(self, trace_mgr):
        """Test: export retourne les N derniers spans (LIFO)."""
        # Créer 5 spans
        for i in range(5):
            span_id = trace_mgr.start_span(f"op_{i}")
            time.sleep(0.001)
            trace_mgr.end_span(span_id)

        exports = trace_mgr.export(limit=3)
        assert len(exports) == 3
        # Plus récent d'abord (op_4, op_3, op_2)
        assert exports[0]["name"] == "op_4"
        assert exports[1]["name"] == "op_3"
        assert exports[2]["name"] == "op_2"

    def test_fifo_buffer_limit(self, trace_mgr):
        """Test: buffer FIFO limite à max_spans."""
        trace_mgr._max_spans = 3

        # Créer 5 spans (dépasse la limite)
        for i in range(5):
            span_id = trace_mgr.start_span(f"op_{i}")
            trace_mgr.end_span(span_id)

        exports = trace_mgr.export(limit=10)
        # Seulement les 3 derniers (op_2, op_3, op_4)
        assert len(exports) == 3
        assert exports[0]["name"] == "op_4"

    def test_nested_spans_parent_id(self, trace_mgr):
        """Test: spans imbriqués ont parent_id correct."""
        parent_id = trace_mgr.start_span("parent")
        child_id = trace_mgr.start_span("child")  # Auto-parent via contextvars

        parent = trace_mgr.get_span(parent_id)
        child = trace_mgr.get_span(child_id)

        assert child.parent_id == parent_id
        assert child.trace_id == parent.trace_id  # Même trace

    def test_clear_removes_all_spans(self, trace_mgr):
        """Test: clear supprime tous les spans."""
        trace_mgr.start_span("op1")
        trace_mgr.start_span("op2")
        trace_mgr.clear()

        exports = trace_mgr.export()
        assert len(exports) == 0


class TestTraceSpanDecorator:
    """Tests pour le décorateur @trace_span."""

    @pytest.fixture
    def trace_mgr(self):
        """Fixture: TraceManager propre."""
        from backend.core.tracing import get_trace_manager
        mgr = get_trace_manager()
        mgr.clear()
        return mgr

    @pytest.mark.asyncio
    async def test_async_function_traced(self, trace_mgr):
        """Test: décorateur @trace_span sur fonction async."""
        @trace_span("async_operation", agent="test")
        async def async_func():
            await asyncio.sleep(0.01)
            return "result"

        result = await async_func()
        assert result == "result"

        exports = trace_mgr.export(limit=1)
        assert len(exports) == 1
        assert exports[0]["name"] == "async_operation"
        assert exports[0]["status"] == "OK"
        assert exports[0]["attributes"]["agent"] == "test"

    @pytest.mark.asyncio
    async def test_async_function_error_traced(self, trace_mgr):
        """Test: décorateur @trace_span capture erreurs (status=ERROR)."""
        @trace_span("failing_operation")
        async def failing_func():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            await failing_func()

        exports = trace_mgr.export(limit=1)
        assert len(exports) == 1
        assert exports[0]["name"] == "failing_operation"
        assert exports[0]["status"] == "ERROR"

    def test_sync_function_traced(self, trace_mgr):
        """Test: décorateur @trace_span sur fonction sync."""
        @trace_span("sync_operation", agent="sync_test")
        def sync_func():
            time.sleep(0.01)
            return "sync_result"

        result = sync_func()
        assert result == "sync_result"

        exports = trace_mgr.export(limit=1)
        assert len(exports) == 1
        assert exports[0]["name"] == "sync_operation"
        assert exports[0]["status"] == "OK"


class TestSpanExport:
    """Tests pour l'export des spans (Prometheus-ready)."""

    @pytest.fixture
    def trace_mgr(self):
        mgr = TraceManager()
        mgr.clear()
        return mgr

    def test_export_format_matches_prometheus(self, trace_mgr):
        """Test: format export compatible avec Prometheus."""
        span_id = trace_mgr.start_span(
            "retrieval",
            attrs={"agent": "anima", "top_k": 5},
        )
        time.sleep(0.01)
        trace_mgr.end_span(span_id, status="OK")

        exports = trace_mgr.export(limit=1)
        span_dict = exports[0]

        # Vérifier structure attendue
        assert "span_id" in span_dict
        assert "name" in span_dict
        assert "trace_id" in span_dict
        assert "duration" in span_dict
        assert "status" in span_dict
        assert "attributes" in span_dict
        assert span_dict["attributes"]["agent"] == "anima"
        assert span_dict["attributes"]["top_k"] == 5
