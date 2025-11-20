import asyncio
import sys
import types
from pathlib import Path
from typing import Any

import pytest

sys.path.append(str(Path(__file__).resolve().parents[3] / "src"))

from backend.features.debate.service import DebateService


class RecorderConnectionManager:
    def __init__(self):
        self.messages: list[tuple[str, dict[str, Any]]] = []

    async def send_personal_message(
        self, payload: dict[str, Any], session_id: str
    ) -> None:
        self.messages.append((session_id, payload))


def run_async(coro):
    return asyncio.run(coro)


def test_debate_say_once_handles_chat_failure():
    class FailingChatService:
        async def get_llm_response_for_debate(self, *args, **kwargs):
            raise RuntimeError("anthropic timeout")

    debate_service = DebateService(FailingChatService(), RecorderConnectionManager())

    response = run_async(
        debate_service._say_once(
            session_id="sess-err",
            agent_id="neo",
            prompt="Expose le sujet",
            use_rag=False,
        )
    )

    assert response["fallback"] is True
    assert response["provider"] is None
    assert response["model"] is None
    assert response["cost_info"] == {
        "input_tokens": 0,
        "output_tokens": 0,
        "total_cost": 0.0,
    }
    assert "indisponible" in response["text"]
    assert "anthropic timeout" in response["text"]
    assert response["error"]["type"] == "RuntimeError"


def test_debate_run_continues_when_agent_fails():
    class MixedChatService:
        def __init__(self):
            self.calls: list[str] = []

        def _sanitize_doc_ids(self, doc_ids):
            return []

        async def get_llm_response_for_debate(self, agent_id, prompt, **kwargs):
            self.calls.append(agent_id)
            if agent_id == "nexus":
                raise RuntimeError("upstream 500")
            return {
                "text": f"{agent_id} reply",
                "cost_info": {
                    "total_cost": 0.01,
                    "input_tokens": 10,
                    "output_tokens": 5,
                },
                "provider": "stub",
                "model": "stub-model",
                "fallback": False,
            }

    conn = RecorderConnectionManager()
    chat_service = MixedChatService()
    debate_service = DebateService(chat_service, conn)

    result = run_async(
        debate_service.run(
            session_id="sess-fallback",
            topic="Test",
            agentOrder=["neo", "nexus", "anima"],
            rounds=1,
            use_rag=False,
        )
    )

    assert chat_service.calls.count("neo") == 1
    assert chat_service.calls.count("nexus") == 1
    assert chat_service.calls.count("anima") == 1

    turns = {turn["agent"]: turn for turn in result["turns"]}
    assert "neo" in turns and "nexus" in turns
    assert turns["nexus"]["meta"]["fallback"] is True
    assert turns["nexus"]["meta"]["error"]["type"] == "RuntimeError"
    assert turns["nexus"]["text"].startswith("⚠️ Agent nexus indisponible")

    cost = result["cost"]
    assert cost["by_agent"]["nexus"]["usd"] == pytest.approx(0.0)
    assert cost["by_agent"]["neo"]["usd"] == pytest.approx(0.01)
    assert cost["by_agent"]["anima"]["usd"] == pytest.approx(0.01)

    message_types = {payload["type"] for _, payload in conn.messages}
    assert "ws:debate_turn_update" in message_types
    assert "ws:debate_result" in message_types


def test_debate_run_cost_summary_aggregation():
    class StubChatService:
        def _sanitize_doc_ids(self, doc_ids):
            return [101, 202]

    async def _run():
        chat_service = StubChatService()
        debate_service = DebateService(chat_service, RecorderConnectionManager())

        async def _no_op(self, *args, **kwargs):
            return None

        debate_service._emit = types.MethodType(_no_op, debate_service)
        debate_service._status = types.MethodType(_no_op, debate_service)

        cost_map = {
            "neo": {
                "text": "Neo opening",
                "cost_info": {
                    "total_cost": 0.0105,
                    "input_tokens": 100,
                    "output_tokens": 50,
                },
                "provider": "anthropic",
                "model": "claude-neo",
                "fallback": False,
            },
            "nexus": {
                "text": "Nexus rebuttal",
                "cost_info": {
                    "total_cost": 0.021,
                    "input_tokens": 120,
                    "output_tokens": 60,
                },
                "provider": "anthropic",
                "model": "claude-nexus",
                "fallback": False,
            },
            "anima": {
                "text": "Anima synthesis",
                "cost_info": {
                    "total_cost": 0.01575,
                    "input_tokens": 150,
                    "output_tokens": 75,
                },
                "provider": "anthropic",
                "model": "claude-anima",
                "fallback": False,
            },
        }

        async def _fake_say_once(
            self, session_id, agent_id, prompt, *, use_rag, doc_ids=None
        ):
            data = cost_map[agent_id]
            return {
                "text": data["text"],
                "cost_info": data["cost_info"].copy(),
                "provider": data["provider"],
                "model": data["model"],
                "fallback": data["fallback"],
            }

        debate_service._say_once = types.MethodType(_fake_say_once, debate_service)

        result = await debate_service.run(
            session_id="sess-agg",
            topic="Test aggregation",
            agentOrder=["neo", "nexus", "anima"],
            rounds=1,
        )

        cost = result["cost"]
        assert cost["total_usd"] == pytest.approx(0.04725, rel=1e-9)
        assert cost["tokens"]["input"] == 370
        assert cost["tokens"]["output"] == 185

        by_agent = cost["by_agent"]
        assert by_agent["neo"]["usd"] == pytest.approx(0.0105, rel=1e-9)
        assert by_agent["neo"]["input_tokens"] == 100
        assert by_agent["neo"]["output_tokens"] == 50

        assert by_agent["nexus"]["usd"] == pytest.approx(0.021, rel=1e-9)
        assert by_agent["nexus"]["input_tokens"] == 120
        assert by_agent["nexus"]["output_tokens"] == 60

        assert by_agent["anima"]["usd"] == pytest.approx(0.01575, rel=1e-9)
        assert by_agent["anima"]["input_tokens"] == 150
        assert by_agent["anima"]["output_tokens"] == 75

        assert result["config"]["docIds"] == [101, 202]

    run_async(_run())
