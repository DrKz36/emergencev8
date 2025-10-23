"""
Tests pour RAG Startup-Safe V13.2
- Mode READ-ONLY fallback si ChromaDB indisponible
- Endpoint /health/ready avec diagnostics vector store
"""

import pytest
import tempfile
import shutil
import os
from unittest.mock import patch, MagicMock

from backend.features.memory.vector_service import VectorService


class TestRAGStartupSafe:
    """Tests pour mode READ-ONLY fallback V13.2"""

    def test_normal_boot_readwrite_mode(self):
        """Test boot normal: ChromaDB OK → mode readwrite"""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = VectorService(
                persist_directory=tmpdir,
                embed_model_name="sentence-transformers/all-MiniLM-L6-v2",
                auto_reset_on_schema_error=True,
            )

            # Force init
            service._ensure_inited()

            # Vérifications
            assert service.get_vector_mode() == "readwrite"
            assert service.is_vector_store_reachable() is True
            assert service.get_last_init_error() is None
            assert service.client is not None

    def test_chromadb_failure_readonly_fallback(self):
        """Test boot KO: ChromaDB fail → mode readonly"""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = VectorService(
                persist_directory=tmpdir,
                embed_model_name="sentence-transformers/all-MiniLM-L6-v2",
                auto_reset_on_schema_error=False,  # Pas d'auto-reset
            )

            # Mock ChromaDB pour simuler échec init
            with patch("chromadb.PersistentClient") as mock_client:
                mock_client.side_effect = Exception("ChromaDB connection failed")

                # Force init (ne doit PAS raise, doit passer en readonly)
                service._ensure_inited()

                # Vérifications
                assert service.get_vector_mode() == "readonly"
                assert service.is_vector_store_reachable() is False
                assert service.get_last_init_error() is not None
                assert "ChromaDB init failed" in service.get_last_init_error()
                assert service.client is None

    def test_write_operations_blocked_in_readonly_mode(self):
        """Test refus d'écriture en mode readonly"""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = VectorService(
                persist_directory=tmpdir,
                embed_model_name="sentence-transformers/all-MiniLM-L6-v2",
                auto_reset_on_schema_error=False,
            )

            # Forcer mode readonly sans init ChromaDB
            service._vector_mode = "readonly"
            service._last_init_error = "Simulated failure"
            service._inited = True
            service.model = MagicMock()  # Mock SBERT

            # Mock collection
            mock_collection = MagicMock()
            mock_collection.name = "test_collection"

            # Test add_items bloqué
            with pytest.raises(RuntimeError, match="mode READ-ONLY"):
                service.add_items(
                    mock_collection,
                    [{"id": "1", "text": "test", "metadata": {}}],
                )

            # Test update_metadatas bloqué
            with pytest.raises(RuntimeError, match="mode READ-ONLY"):
                service.update_metadatas(
                    mock_collection,
                    ["1"],
                    [{"key": "value"}],
                )

            # Test delete_vectors bloqué
            with pytest.raises(RuntimeError, match="mode READ-ONLY"):
                service.delete_vectors(
                    mock_collection,
                    {"user_id": "123"},
                )

    def test_read_operations_allowed_in_readonly_mode(self):
        """Test que les opérations de lecture fonctionnent en readonly"""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = VectorService(
                persist_directory=tmpdir,
                embed_model_name="sentence-transformers/all-MiniLM-L6-v2",
            )

            # Force mode readonly
            service._vector_mode = "readonly"
            service._inited = True
            service.model = MagicMock()  # Mock SBERT

            # Les getters publics doivent fonctionner
            assert service.get_vector_mode() == "readonly"
            assert service.is_vector_store_reachable() is False


class TestHealthReadyEndpoint:
    """Tests pour endpoint /health/ready V13.2"""

    @pytest.mark.asyncio
    async def test_health_ready_ok_status(self):
        """Test /health/ready retourne OK si tout est up"""
        from fastapi.testclient import TestClient
        from fastapi import FastAPI, Request
        from backend.features.monitoring.router import router as monitoring_router

        app = FastAPI()
        app.include_router(monitoring_router)

        # Mock service container
        mock_vector = MagicMock()
        mock_vector._ensure_inited = MagicMock()
        mock_vector.get_vector_mode.return_value = "readwrite"
        mock_vector.is_vector_store_reachable.return_value = True
        mock_vector.get_last_init_error.return_value = None
        mock_vector.backend = "chroma"

        mock_container = MagicMock()
        mock_container.vector_service.return_value = mock_vector

        app.state.service_container = mock_container

        # Mock _check_database pour retourner up
        with patch("backend.features.monitoring.router._check_database") as mock_db:
            mock_db.return_value = {"status": "up"}

            client = TestClient(app)
            response = client.get("/api/monitoring/health/ready")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert data["database"]["reachable"] is True
            assert data["vector_store"]["reachable"] is True
            assert data["vector_store"]["mode"] == "readwrite"
            assert data["vector_store"]["backend"] == "chroma"

    @pytest.mark.asyncio
    async def test_health_ready_degraded_readonly(self):
        """Test /health/ready retourne degraded si vector readonly"""
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from backend.features.monitoring.router import router as monitoring_router

        app = FastAPI()
        app.include_router(monitoring_router)

        # Mock vector service en readonly
        mock_vector = MagicMock()
        mock_vector._ensure_inited = MagicMock()
        mock_vector.get_vector_mode.return_value = "readonly"
        mock_vector.is_vector_store_reachable.return_value = False
        mock_vector.get_last_init_error.return_value = "ChromaDB init failed"
        mock_vector.backend = "chroma"

        mock_container = MagicMock()
        mock_container.vector_service.return_value = mock_vector

        app.state.service_container = mock_container

        with patch("backend.features.monitoring.router._check_database") as mock_db:
            mock_db.return_value = {"status": "up"}

            client = TestClient(app)
            response = client.get("/api/monitoring/health/ready")

            # Status degraded mais HTTP 200 (accepté)
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "degraded"
            assert data["vector_store"]["mode"] == "readonly"
            assert data["vector_store"]["last_error"] == "ChromaDB init failed"

    @pytest.mark.asyncio
    async def test_health_ready_down_db_failure(self):
        """Test /health/ready retourne down si DB KO"""
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from backend.features.monitoring.router import router as monitoring_router

        app = FastAPI()
        app.include_router(monitoring_router)

        mock_vector = MagicMock()
        mock_vector._ensure_inited = MagicMock()
        mock_vector.get_vector_mode.return_value = "readwrite"
        mock_vector.is_vector_store_reachable.return_value = True
        mock_vector.get_last_init_error.return_value = None
        mock_vector.backend = "chroma"

        mock_container = MagicMock()
        mock_container.vector_service.return_value = mock_vector

        app.state.service_container = mock_container

        # Mock DB down
        with patch("backend.features.monitoring.router._check_database") as mock_db:
            mock_db.return_value = {"status": "down", "error": "DB connection failed"}

            client = TestClient(app)
            response = client.get("/api/monitoring/health/ready")

            # Status down avec HTTP 503
            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "down"
