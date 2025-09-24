# ruff: noqa: E402
import asyncio
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[3]
SRC_DIR = ROOT_DIR / 'src'
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from backend.core.database.manager import DatabaseManager
from backend.core.database import schema, queries


def test_delete_thread_removes_related_records(tmp_path):
    async def scenario():
        db_path = tmp_path / 'threads-delete.db'
        db = DatabaseManager(str(db_path))
        await schema.create_tables(db)

        user_id = 'owner-1'
        doc_id = await queries.insert_document(
            db,
            filename='spec.pdf',
            filepath='spec.pdf',
            status='ready',
            uploaded_at='2025-09-24T00:00:00Z',
        )

        thread_id = await queries.create_thread(
            db,
            user_id=user_id,
            type_='chat',
            title='Conversation to delete',
        )
        await queries.add_message(
            db,
            thread_id=thread_id,
            role='user',
            content='Hello world',
            agent_id=None,
            tokens=None,
            meta=None,
        )
        await queries.set_thread_docs(db, thread_id, [doc_id])

        removed = await queries.delete_thread(db, thread_id, user_id)
        assert removed is True

        assert await queries.get_thread(db, thread_id, user_id) is None
        assert await db.fetch_one('SELECT id FROM messages WHERE thread_id = ?', (thread_id,)) is None
        assert await db.fetch_one('SELECT thread_id FROM thread_docs WHERE thread_id = ?', (thread_id,)) is None

        await db.disconnect()

    asyncio.run(scenario())


def test_delete_thread_requires_owner(tmp_path):
    async def scenario():
        db_path = tmp_path / 'threads-delete-owner.db'
        db = DatabaseManager(str(db_path))
        await schema.create_tables(db)

        owner_id = 'owner-2'
        intruder_id = 'intruder'
        thread_id = await queries.create_thread(
            db,
            user_id=owner_id,
            type_='chat',
            title='Owned thread',
        )

        removed = await queries.delete_thread(db, thread_id, intruder_id)
        assert removed is False

        still_there = await queries.get_thread(db, thread_id, owner_id)
        assert still_there is not None

        await db.disconnect()

    asyncio.run(scenario())

