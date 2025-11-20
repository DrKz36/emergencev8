from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict

import pytest
from starlette.datastructures import UploadFile

from backend.core.database.manager import DatabaseManager
from backend.features.documents.parser import ParserFactory
from backend.features.documents.service import DocumentService
from backend.core.database import queries as db_queries


class ReadOnlyVectorService:
    """Stub vector service that mimics a read-only backend."""

    def __init__(self) -> None:
        self.collection_requested = 0
        self.add_called = False

    def get_or_create_collection(self, name: str):  # pragma: no cover - simple stub
        self.collection_requested += 1
        raise RuntimeError("VectorService en mode READ-ONLY (écritures bloquées).")

    def is_vector_store_reachable(self) -> bool:
        return False

    def get_last_init_error(self) -> str:
        return "VectorService en mode READ-ONLY (écritures bloquées)."

    # The service should never call add/delete when the store is unreachable
    def add_items(self, *args, **kwargs):  # pragma: no cover - defensive guard
        self.add_called = True
        raise AssertionError("add_items ne doit pas être appelé en mode READ-ONLY")

    def delete_vectors(self, *args, **kwargs):  # pragma: no cover - defensive guard
        raise AssertionError("delete_vectors ne doit pas être appelé en mode READ-ONLY")


class RecordingVectorService:
    """Stub vector service that records batch sizes for assertions."""

    def __init__(self) -> None:
        self.collection = SimpleNamespace(name="documents")
        self.add_calls: list[list[dict[str, Any]]] = []
        self.deleted_filters: list[Dict[str, Any]] = []

    def get_or_create_collection(self, name: str):
        self.collection.name = name
        return self.collection

    def is_vector_store_reachable(self) -> bool:
        return True

    def get_last_init_error(self) -> str | None:  # pragma: no cover - compatibility
        return None

    def add_items(self, *, collection, items):
        assert collection is self.collection
        self.add_calls.append(list(items))

    def delete_vectors(
        self, *, collection, where_filter
    ):  # pragma: no cover - not used here
        self.deleted_filters.append(dict(where_filter))


@pytest.mark.asyncio
async def test_process_upload_when_vector_store_unavailable(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    uploads_dir = tmp_path / "uploads"

    manager = DatabaseManager(str(db_path))
    await manager.connect()
    await manager.initialize()

    parser_factory = ParserFactory()
    vector_service = ReadOnlyVectorService()

    service = DocumentService(
        db_manager=manager,
        parser_factory=parser_factory,
        vector_service=vector_service,
        uploads_dir=str(uploads_dir),
    )

    upload = UploadFile(filename="notes.txt", file=BytesIO(b"Ligne 1\nLigne 2\n"))
    result = await service.process_uploaded_file(
        upload,
        session_id="sess-1",
        user_id="user-1",
    )

    assert result["vectorized"] is False
    assert result["status"] == "error"
    assert "Vector" in (result["warning"] or "")

    documents = await db_queries.get_all_documents(
        manager,
        session_id="sess-1",
        user_id="user-1",
    )
    assert documents
    assert documents[0]["status"] == "error"
    assert "Vector" in (documents[0].get("error_message") or "")

    await manager.disconnect()


@pytest.mark.asyncio
async def test_process_upload_with_chunk_limit(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    uploads_dir = tmp_path / "uploads"

    manager = DatabaseManager(str(db_path))
    await manager.connect()
    await manager.initialize()

    parser_factory = ParserFactory()
    vector_service = RecordingVectorService()

    service = DocumentService(
        db_manager=manager,
        parser_factory=parser_factory,
        vector_service=vector_service,
        uploads_dir=str(uploads_dir),
    )
    service.max_vector_chunks = 5
    service.vector_batch_size = 2

    paragraphs = [f"Paragraphe {i}\nLigne {i}" for i in range(12)]
    payload = "\n\n".join(paragraphs)
    upload = UploadFile(filename="many.txt", file=BytesIO(payload.encode("utf-8")))

    result = await service.process_uploaded_file(
        upload,
        session_id="sess-limit",
        user_id="user-limit",
    )

    assert result["vectorized"] is True
    assert result["indexed_chunks"] == 5
    assert result["total_chunks"] >= 5
    assert result["warning"]
    assert "limitée" in result["warning"].lower()

    # Ensure batching respected the configured size (ceil(5/2) == 3 calls)
    assert len(vector_service.add_calls) == 3
    assert sum(len(batch) for batch in vector_service.add_calls) == 5

    documents = await db_queries.get_all_documents(
        manager,
        session_id="sess-limit",
        user_id="user-limit",
    )
    assert documents
    assert documents[0]["status"] == "ready"

    await manager.disconnect()


@pytest.mark.asyncio
async def test_process_upload_with_massive_line_count(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    uploads_dir = tmp_path / "uploads"

    manager = DatabaseManager(str(db_path))
    await manager.connect()
    await manager.initialize()

    parser_factory = ParserFactory()
    vector_service = RecordingVectorService()

    service = DocumentService(
        db_manager=manager,
        parser_factory=parser_factory,
        vector_service=vector_service,
        uploads_dir=str(uploads_dir),
    )

    # Crée un document artificiel avec > 10 000 paragraphes très courts
    paragraphs = [f"Paragraphe {i}" for i in range(12_500)]
    payload = "\n\n".join(paragraphs)
    upload = UploadFile(filename="huge.txt", file=BytesIO(payload.encode("utf-8")))

    result = await service.process_uploaded_file(
        upload,
        session_id="sess-huge",
        user_id="user-huge",
    )

    assert result["vectorized"] is True
    assert result["total_chunks"] <= service.MAX_TOTAL_CHUNKS_ALLOWED
    assert result["indexed_chunks"] == result["total_chunks"]
    assert (
        sum(len(batch) for batch in vector_service.add_calls)
        == result["indexed_chunks"]
    )

    documents = await db_queries.get_all_documents(
        manager,
        session_id="sess-huge",
        user_id="user-huge",
    )
    assert documents
    assert documents[0]["status"] == "ready"
    assert documents[0]["chunk_count"] == result["total_chunks"]

    await manager.disconnect()
