# ruff: noqa: E402
import asyncio
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT_DIR = Path(__file__).resolve().parents[3]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from backend.core.database.manager import DatabaseManager
from backend.core.database import schema, queries
from backend.core.session_manager import SessionManager
from backend.features.chat.service import ChatService


class DummyAsyncClient:
    def __init__(self, *args, **kwargs):
        pass


class DummySyncClient:
    def __init__(self, *args, **kwargs):
        pass


class FakeCostTracker:
    def __init__(self):
        self.last = None

    async def record_cost(self, **kwargs):
        self.last = kwargs


class FakeVectorService:
    def __init__(self, allowed_doc_id, blocked_doc_id):
        self.allowed_doc_id = allowed_doc_id
        self.blocked_doc_id = blocked_doc_id
        self.collection = None
        self.last_where_filter = None

    def get_or_create_collection(self, name):
        self.collection = name
        return name

    def query(self, collection, query_text, where_filter=None):
        self.last_where_filter = where_filter
        return [
            {
                "text": "Allowed excerpt",
                "metadata": {
                    "document_id": self.allowed_doc_id,
                    "filename": "allowed.pdf",
                    "page": 1,
                },
            },
            {
                "text": "Blocked excerpt",
                "metadata": {
                    "document_id": self.blocked_doc_id,
                    "filename": "blocked.pdf",
                    "page": 2,
                },
            },
        ]

    def hybrid_query(
        self,
        collection,
        query_text,
        n_results=5,
        where_filter=None,
        alpha=0.5,
        score_threshold=0.0,
    ):
        """Hybrid query method for compatibility with ChatService RAG"""
        self.last_where_filter = where_filter
        return [
            {
                "text": "Allowed excerpt",
                "metadata": {
                    "document_id": self.allowed_doc_id,
                    "filename": "allowed.pdf",
                    "page": 1,
                },
            },
            {
                "text": "Blocked excerpt",
                "metadata": {
                    "document_id": self.blocked_doc_id,
                    "filename": "blocked.pdf",
                    "page": 2,
                },
            },
        ]


class FakeConnectionManager:
    def __init__(self):
        self.messages = []

    async def send_personal_message(self, message, session_id):
        self.messages.append((message, session_id))


class PatchedChatService(ChatService):
    async def _get_llm_response_stream(
        self,
        provider_name,
        model_name,
        system_prompt,
        history,
        cost_info_container,
        agent_id: str = "unknown",
    ):
        async def generator():
            yield "Stub response"

        return generator()

    async def _build_memory_context(self, *args, **kwargs):
        return ""

    def _merge_blocks(self, blocks):
        return ""

    def _try_get_session_summary(self, session_id):
        return ""


def test_thread_doc_filter(tmp_path):
    async def scenario():
        os.environ["EMERGENCE_AUTO_TEND"] = "0"

        db_path = tmp_path / "chat-docs.db"
        db = DatabaseManager(str(db_path))
        await schema.create_tables(db)

        session_id = "sess-thread-docs"
        user_id = "user-test"
        doc1 = await queries.insert_document(
            db,
            filename="doc1.pdf",
            filepath="doc1.pdf",
            status="ready",
            uploaded_at="2025-09-20T00:00:00Z",
            session_id=session_id,
            user_id=user_id,
        )
        thread_id = await queries.create_thread(
            db,
            session_id=session_id,
            user_id=user_id,
            type_="chat",
            title="Test Thread",
        )
        await queries.set_thread_docs(
            db, thread_id, session_id, [doc1], user_id=user_id
        )

        session_manager = SessionManager(db, memory_analyzer=None)
        await session_manager.ensure_session(
            session_id=session_id,
            user_id=user_id,
            thread_id=thread_id,
            history_limit=50,
        )

        cost_tracker = FakeCostTracker()
        vector_service = FakeVectorService(allowed_doc_id=doc1, blocked_doc_id=999)
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir(exist_ok=True)
        settings = SimpleNamespace(
            openai_api_key="test-key",
            google_api_key="test-key",
            anthropic_api_key="test-key",
            paths=SimpleNamespace(prompts=str(prompts_dir)),
        )

        fake_cm = FakeConnectionManager()

        with (
            patch("backend.features.chat.service.AsyncOpenAI", DummyAsyncClient),
            patch("backend.features.chat.service.AsyncAnthropic", DummyAsyncClient),
            patch("backend.features.chat.service.Anthropic", DummySyncClient),
            patch("backend.features.chat.service.OpenAI", DummySyncClient),
            patch(
                "backend.features.chat.service.genai.configure", lambda api_key: None
            ),
        ):
            service = PatchedChatService(
                session_manager, cost_tracker, vector_service, settings
            )
            await service._process_agent_response_stream(
                session_id=session_id,
                agent_id="anima",
                use_rag=True,
                connection_manager=fake_cm,
                doc_ids=[999],
                origin_agent_id=None,
            )

        end_frames = [
            frame
            for frame, _ in fake_cm.messages
            if frame.get("type") == "ws:chat_stream_end"
        ]
        assert end_frames, "No ws:chat_stream_end frame captured"
        payload = end_frames[0]["payload"]
        meta = payload.get("meta", {})

        selected_ids = meta.get("selected_doc_ids", [])
        assert 999 not in selected_ids
        assert doc1 in selected_ids

        sources = meta.get("sources", [])
        for source in sources:
            doc_id = source.get("document_id")
            if doc_id is not None:
                assert int(doc_id) == doc1

        assert vector_service.last_where_filter == {
            "$and": [
                {"session_id": session_id},
                {"user_id": user_id},
                {"document_id": doc1},
            ]
        }

        await db.disconnect()
        os.environ.pop("EMERGENCE_AUTO_TEND", None)

    asyncio.run(scenario())
