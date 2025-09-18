from pathlib import Path
import sys
import asyncio

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

        text, cost_info = await debate_service._say_once(
            session_id="sess-1",
            agent_id="anima",
            prompt="Expose le sujet",
            use_rag=False,
        )

        assert text == "Salut"
        assert cost_info["output_tokens"] == 2
        assert cost_tracker.records == [
            {
                "agent": "anima",
                "model": "claude-3-haiku-20240307",
                "input_tokens": 7,
                "output_tokens": 2,
                "total_cost": 0.00042,
                "feature": "debate",
            }
        ]

    asyncio.run(_run())
