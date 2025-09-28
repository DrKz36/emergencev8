# ruff: noqa: E402
import asyncio
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[3]
SRC_DIR = ROOT_DIR / 'src'
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from backend.features.chat.service import ChatService


class StubSessionManager:
    def __init__(self, user_id: str):
        self._user_id = user_id

    def get_user_id_for_session(self, session_id: str):  # pragma: no cover - simple stub
        return self._user_id


class StubVectorService:
    def __init__(self, metadata):
        self._metadata = metadata
        self.queries = []
        self.updated = []
        self.collection_name = None

    def get_or_create_collection(self, name):
        self.collection_name = name
        return name

    def query(self, collection, query_text, n_results=5, where_filter=None):
        self.queries.append((collection, query_text, n_results, where_filter))
        return [
            {
                'id': 'vec-1',
                'text': 'User adore le café, préfère les grains costauds.',
                'metadata': dict(self._metadata),
            }
        ]

    def update_metadatas(self, collection, ids, metadatas):
        self.updated.append((collection, list(ids), [dict(m) for m in metadatas]))


async def _run_memory_context_scenario():
    session_id = 'sess-recall'
    user_id = 'user-42'

    # Metadata intentionally lacks `session_id` to simulate legacy vectors.
    stored_meta = {
        'source_session_id': session_id,
        'user_id': user_id,
        'agent': 'anima',
        'usage_count': 0,
        'vitality': 0.5,
    }

    vector_service = StubVectorService(stored_meta)
    session_manager = StubSessionManager(user_id)

    service = object.__new__(ChatService)
    service.vector_service = vector_service
    service.session_manager = session_manager
    service._knowledge_collection = None

    memory_block = await service._build_memory_context(
        session_id=session_id,
        last_user_message='Peux-tu me conseiller un café ? Je préfère les torréfactions corsées.',
        top_k=3,
        agent_id='Anima',
    )

    assert '- User adore le café, préfère les grains costauds.' in memory_block

    assert vector_service.queries, 'vector_service.query should have been called'
    _collection, _query_text, _n_results, where_filter = vector_service.queries[0]
    assert where_filter is not None and '$and' in where_filter
    clauses = where_filter['$and']
    session_clause = clauses[0]
    assert '$or' in session_clause
    assert {'session_id': session_id} in session_clause['$or']
    assert {'source_session_id': session_id} in session_clause['$or']
    assert {'user_id': user_id} in clauses

    assert vector_service.updated, 'Vector metadata should be updated on recall'
    _, ids, metadatas = vector_service.updated[0]
    assert ids == ['vec-1']
    meta = metadatas[0]
    assert meta['session_id'] == session_id
    assert meta['source_session_id'] == session_id


def test_memory_context_recalls_vector_with_legacy_metadata():
    asyncio.run(_run_memory_context_scenario())
