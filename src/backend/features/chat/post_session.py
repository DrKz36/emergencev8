# V1.0 — Analyse post-session & notifications WS
from __future__ import annotations
import inspect, logging
from backend.core.websocket import ConnectionManager
logger = logging.getLogger(__name__)

async def run_analysis_and_notify(session_manager, connection_manager: ConnectionManager,
                                  session_id: str, agent_id: str, enable_analysis: bool) -> None:
    if not enable_analysis:
        try:
            await connection_manager.send_personal_message(
                {"type": "ws:analysis_status","payload": {"status": "skipped","reason": "disabled","agent_id": agent_id}}, session_id)
        except Exception: pass
        return
    try:
        analyzer = getattr(session_manager, "memory_analyzer", None)
        history = session_manager.get_full_history(session_id) or []
        if analyzer and hasattr(analyzer, "analyze_session_for_concepts"):
            try:
                sig = inspect.signature(analyzer.analyze_session_for_concepts)
                if "history" in sig.parameters: await analyzer.analyze_session_for_concepts(session_id, history)
                else: await analyzer.analyze_session_for_concepts(session_id)
            except TypeError: await analyzer.analyze_session_for_concepts(session_id)
        else:
            try:
                await connection_manager.send_personal_message(
                    {"type": "ws:analysis_status","payload": {"status": "skipped","reason": "analyzer_unavailable","agent_id": agent_id}}, session_id)
            except Exception: pass
    except Exception as e:
        logger.warning(f"Memory analysis error: {e}")
        try:
            await connection_manager.send_personal_message(
                {"type": "ws:analysis_status","payload": {"status": "error","agent_id": agent_id,"error": str(e)}}, session_id)
        except Exception: pass
