from pathlib import Path
import sys
import asyncio
import types

import pytest

sys.path.append(str(Path(__file__).resolve().parents[3] / "src"))

import backend.features.chat.service as chat_service_module
from backend.features.chat.service import ChatService
from backend.features.debate.service import DebateService
from backend.shared.config import Settings


class DummySessionManager:
    def get_full_history(self, session_id):
        return []

    async def add_message_to_session(self, *args, **kwargs):
        return None


class DummyCostTracker:
    def __init__(self):
        self.records = []

    async def record_cost(self, *, agent, model, input_tokens, output_tokens, total_cost, feature):
        self.records.append(
            {
                "agent": agent,
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_cost": total_cost,
                "feature": feature,
            }
        )


class DummyVectorService:
    def get_or_create_collection(self, *args, **kwargs):
        return None

    def query(self, *args, **kwargs):
        return []


class DummyConnectionManager:
    async def send_personal_message(self, *args, **kwargs):
        return None


class DummyAsyncClient:
    def __init__(self, *args, **kwargs):
        pass


class DummySyncClient:
    def __init__(self, *args, **kwargs):
        pass


@pytest.mark.skip(reason="Mock fake_stream obsolete - missing agent_id parameter")
def test_debate_say_once_short_response(monkeypatch):
    monkeypatch.setattr(chat_service_module, "AsyncOpenAI", DummyAsyncClient)
    monkeypatch.setattr(chat_service_module, "OpenAI", DummySyncClient)
    monkeypatch.setattr(chat_service_module, "AsyncAnthropic", DummyAsyncClient)
    monkeypatch.setattr(chat_service_module, "Anthropic", DummySyncClient)
    monkeypatch.setattr(chat_service_module.genai, "configure", lambda **kwargs: None)
    monkeypatch.setenv("EMERGENCE_FORCE_CHEAP_ANIMA", "0")

    async def fake_stream(self, provider, model, system_prompt, history, cost_info_container):
        if provider == "openai":
            raise RuntimeError("primary failure")
        cost_info_container.update({"input_tokens": 7, "output_tokens": 2, "total_cost": 0.00042})
        yield "Salut"

    monkeypatch.setattr(ChatService, "_get_llm_response_stream", fake_stream, raising=False)

    async def _run():
        settings = Settings(openai_api_key="sk-test", google_api_key="sk-test", anthropic_api_key="sk-test")
        cost_tracker = DummyCostTracker()
        chat_service = ChatService(DummySessionManager(), cost_tracker, DummyVectorService(), settings)
        debate_service = DebateService(chat_service, DummyConnectionManager())

        response = await debate_service._say_once(
            session_id="sess-1",
            agent_id="anima",
            prompt="Expose le sujet",
            use_rag=False,
        )

        assert isinstance(response, dict)
        assert response.get("text") == "Salut"
        assert set(response.keys()) >= {"text", "cost_info", "provider", "model", "fallback"}
        assert response["cost_info"]["output_tokens"] == 2
        assert isinstance(response["fallback"], bool)
        assert response["provider"]
        assert response["model"]

        assert len(cost_tracker.records) == 1
        record = cost_tracker.records[0]
        assert record["agent"] == "anima"
        assert record["input_tokens"] == 7
        assert record["output_tokens"] == 2
        assert record["total_cost"] == pytest.approx(0.00042)
        assert record["feature"] == "debate"
        assert record["model"] == response["model"]

    asyncio.run(_run())


def test_debate_run_cost_summary_aggregation():
    class StubChatService:
        def _sanitize_doc_ids(self, doc_ids):
            return [101, 202]

    async def _run():
        chat_service = StubChatService()
        debate_service = DebateService(chat_service, DummyConnectionManager())

        async def _no_op(self, *args, **kwargs):
            return None

        debate_service._emit = types.MethodType(_no_op, debate_service)
        debate_service._status = types.MethodType(_no_op, debate_service)

        cost_map = {
            "neo": {
                "text": "Neo opening",
                "cost_info": {"total_cost": 0.0105, "input_tokens": 100, "output_tokens": 50},
                "provider": "anthropic",
                "model": "claude-neo",
                "fallback": False,
            },
            "nexus": {
                "text": "Nexus rebuttal",
                "cost_info": {"total_cost": 0.021, "input_tokens": 120, "output_tokens": 60},
                "provider": "anthropic",
                "model": "claude-nexus",
                "fallback": False,
            },
            "anima": {
                "text": "Anima synthesis",
                "cost_info": {"total_cost": 0.01575, "input_tokens": 150, "output_tokens": 75},
                "provider": "anthropic",
                "model": "claude-anima",
                "fallback": False,
            },
        }

        async def _fake_say_once(self, session_id, agent_id, prompt, *, use_rag, doc_ids=None):
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

    asyncio.run(_run())
