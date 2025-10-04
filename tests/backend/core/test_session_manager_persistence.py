# ruff: noqa: E402
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timezone

ROOT_DIR = Path(__file__).resolve().parents[3]
SRC_DIR = ROOT_DIR / 'src'
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from backend.core.database.manager import DatabaseManager
from backend.core.database import schema, queries
from backend.core.session_manager import SessionManager
from backend.shared.models import ChatMessage, Role


def test_session_manager_hydrates_and_persists(tmp_path):
    async def scenario():
        db_path = tmp_path / 'session-tests.db'
        db = DatabaseManager(str(db_path))
        await schema.create_tables(db)

        user_id = 'user-test'
        session_id = 'sess-persist'
        thread_id = await queries.create_thread(
            db, session_id=session_id, user_id=user_id, type_='chat', title='Persist Test'
        )
        await queries.add_message(
            db,
            thread_id,
            session_id,
            user_id=user_id,
            role='user',
            content='Salut',
            agent_id='anima',
        )
        await queries.add_message(
            db,
            thread_id,
            session_id,
            user_id=user_id,
            role='assistant',
            content='Bonjour',
            agent_id='anima',
        )

        manager = SessionManager(db, memory_analyzer=None)
        await manager.ensure_session(
            session_id=session_id, user_id=user_id, thread_id=thread_id, history_limit=20
        )

        history = manager.get_full_history(session_id)
        assert len(history) == 2
        assert history[0]['role'] == Role.USER.value
        assert history[1]['role'] == Role.ASSISTANT.value

        exported = manager.export_history_for_transport(session_id)
        assert exported[-1]['content'] == 'Bonjour'
        assert exported[-1]['agent_id'] == 'anima'

        message = ChatMessage(
            id='user-extra',
            session_id=thread_id,
            role=Role.USER,
            agent='anima',
            content='Nouvelle question',
            timestamp=datetime.now(timezone.utc).isoformat(),
            use_rag=False,
            doc_ids=[],
        )
        await manager.add_message_to_session(session_id, message)

        stored = await queries.get_messages(
            db, thread_id, session_id=session_id, user_id=user_id, limit=10
        )
        assert any(row['content'] == 'Nouvelle question' for row in stored)

        await manager.finalize_session(session_id)

        reconnect_session = 'sess-reconnect'
        new_manager = SessionManager(db, memory_analyzer=None)
        await new_manager.ensure_session(
            session_id=reconnect_session,
            user_id=user_id,
            thread_id=thread_id,
            history_limit=20,
        )
        rehydrated = new_manager.get_full_history(reconnect_session)
        assert len(rehydrated) == 3
        assert rehydrated[-1]['content'] == 'Nouvelle question'

        await db.disconnect()

    asyncio.run(scenario())




def test_user_scope_indexes_created(tmp_path):
    async def scenario():
        db_path = tmp_path / 'index-scope.db'
        db = DatabaseManager(str(db_path))
        await schema.create_tables(db)

        expectations = {
            'documents': {'idx_documents_user_uploaded'},
            'document_chunks': {'idx_document_chunks_user'},
            'messages': {'idx_messages_user_created'},
            'thread_docs': {'idx_thread_docs_user'},
        }

        for table, expected in expectations.items():
            rows = await db.fetch_all(f"PRAGMA index_list('{table}')")
            names = {str(row['name']) for row in rows}
            for index_name in expected:
                assert index_name in names, f"Missing index {index_name} for table {table}"

        await db.disconnect()

    asyncio.run(scenario())
