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
        session_id = 'sess-owner-1'
        doc_id = await queries.insert_document(
            db,
            filename='spec.pdf',
            filepath='spec.pdf',
            status='ready',
            uploaded_at='2025-09-24T00:00:00Z',
            session_id=session_id,
            user_id=user_id,
        )

        thread_id = await queries.create_thread(
            db,
            session_id=session_id,
            user_id=user_id,
            type_='chat',
            title='Conversation to delete',
        )
        await queries.add_message(
            db,
            thread_id=thread_id,
            session_id=session_id,
            user_id=user_id,
            role='user',
            content='Hello world',
            agent_id=None,
            tokens=None,
            meta=None,
        )
        await queries.set_thread_docs(
            db, thread_id, session_id, [doc_id], user_id=user_id
        )

        removed = await queries.delete_thread(db, thread_id, session_id, user_id=user_id)
        assert removed is True

        assert await queries.get_thread(
            db, thread_id, session_id, user_id=user_id
        ) is None
        assert await db.fetch_one(
            'SELECT id FROM messages WHERE thread_id = ? AND session_id = ? AND user_id = ?',
            (thread_id, session_id, user_id),
        ) is None
        assert await db.fetch_one(
            'SELECT thread_id FROM thread_docs WHERE thread_id = ? AND session_id = ? AND user_id = ?',
            (thread_id, session_id, user_id),
        ) is None

        await db.disconnect()

    asyncio.run(scenario())


def test_delete_thread_requires_owner(tmp_path):
    async def scenario():
        db_path = tmp_path / 'threads-delete-owner.db'
        db = DatabaseManager(str(db_path))
        await schema.create_tables(db)

        owner_id = 'owner-2'
        owner_session = 'sess-owner-2'
        intruder_session = 'intruder-sess'
        thread_id = await queries.create_thread(
            db,
            session_id=owner_session,
            user_id=owner_id,
            type_='chat',
            title='Owned thread',
        )

        removed = await queries.delete_thread(
            db, thread_id, intruder_session, user_id='intruder'
        )
        assert removed is False

        still_there = await queries.get_thread(
            db, thread_id, owner_session, user_id=owner_id
        )
        assert still_there is not None

        await db.disconnect()

    asyncio.run(scenario())


def test_delete_thread_owner_cross_session_scope(tmp_path):
    async def scenario():
        db_path = tmp_path / 'threads-delete-cross-session.db'
        db = DatabaseManager(str(db_path))
        await schema.create_tables(db)

        user_id = 'owner-cross'
        session_primary = 'sess-owner-cross'
        session_secondary = 'sess-owner-secondary'

        doc_primary = await queries.insert_document(
            db,
            filename='primary.pdf',
            filepath='primary.pdf',
            status='ready',
            uploaded_at='2025-09-24T00:00:00Z',
            session_id=session_primary,
            user_id=user_id,
        )
        doc_secondary = await queries.insert_document(
            db,
            filename='secondary.pdf',
            filepath='secondary.pdf',
            status='ready',
            uploaded_at='2025-09-24T00:00:00Z',
            session_id=session_secondary,
            user_id=user_id,
        )

        thread_primary = await queries.create_thread(
            db,
            session_id=session_primary,
            user_id=user_id,
            type_='chat',
            title='Primary thread',
        )
        thread_secondary = await queries.create_thread(
            db,
            session_id=session_secondary,
            user_id=user_id,
            type_='chat',
            title='Secondary thread',
        )

        await queries.add_message(
            db,
            thread_id=thread_primary,
            session_id=session_primary,
            user_id=user_id,
            role='user',
            content='Keep me scoped',
            agent_id=None,
            tokens=None,
            meta=None,
        )
        await queries.add_message(
            db,
            thread_id=thread_secondary,
            session_id=session_secondary,
            user_id=user_id,
            role='assistant',
            content='Second thread message',
            agent_id='neo',
            tokens=None,
            meta=None,
        )
        await queries.set_thread_docs(
            db,
            thread_primary,
            session_primary,
            [doc_primary],
            user_id=user_id,
        )
        await queries.set_thread_docs(
            db,
            thread_secondary,
            session_secondary,
            [doc_secondary],
            user_id=user_id,
        )

        removed = await queries.delete_thread(
            db,
            thread_primary,
            session_secondary,
            user_id=user_id,
        )
        assert removed is True

        assert await queries.get_thread(
            db,
            thread_primary,
            session_primary,
            user_id=user_id,
        ) is None
        assert await db.fetch_one(
            'SELECT id FROM messages WHERE thread_id = ? AND session_id = ?',
            (thread_primary, session_primary),
        ) is None
        assert await db.fetch_one(
            'SELECT doc_id FROM thread_docs WHERE thread_id = ? AND session_id = ?',
            (thread_primary, session_primary),
        ) is None

        remaining_thread = await queries.get_thread(
            db,
            thread_secondary,
            session_secondary,
            user_id=user_id,
        )
        assert remaining_thread is not None
        assert await db.fetch_one(
            'SELECT id FROM messages WHERE thread_id = ? AND session_id = ?',
            (thread_secondary, session_secondary),
        ) is not None
        assert await db.fetch_one(
            'SELECT doc_id FROM thread_docs WHERE thread_id = ? AND session_id = ?',
            (thread_secondary, session_secondary),
        ) is not None

        await db.disconnect()

    asyncio.run(scenario())


def test_delete_thread_session_scope_requires_match(tmp_path):
    async def scenario():
        db_path = tmp_path / 'threads-delete-session-scope.db'
        db = DatabaseManager(str(db_path))
        await schema.create_tables(db)

        user_id = 'owner-session'
        session_id = 'sess-owner-session'
        thread_id = await queries.create_thread(
            db,
            session_id=session_id,
            user_id=user_id,
            type_='chat',
            title='Scoped thread',
        )
        await queries.add_message(
            db,
            thread_id=thread_id,
            session_id=session_id,
            user_id=user_id,
            role='user',
            content='Message to remove',
            agent_id=None,
            tokens=None,
            meta=None,
        )

        removed_wrong_scope = await queries.delete_thread(
            db,
            thread_id,
            'intruder-session',
            user_id=None,
        )
        assert removed_wrong_scope is False
        assert await queries.get_thread(
            db,
            thread_id,
            session_id,
            user_id=user_id,
        ) is not None

        removed_correct_scope = await queries.delete_thread(
            db,
            thread_id,
            session_id,
            user_id=None,
        )
        assert removed_correct_scope is True
        assert await queries.get_thread(
            db,
            thread_id,
            session_id,
            user_id=user_id,
        ) is None
        assert await db.fetch_one(
            'SELECT id FROM messages WHERE thread_id = ? AND session_id = ?',
            (thread_id, session_id),
        ) is None

        await db.disconnect()

    asyncio.run(scenario())


