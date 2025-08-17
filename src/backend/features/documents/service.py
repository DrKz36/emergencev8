# src/backend/features/documents/service.py
# V8.4 – Cloud Run safe uploads dir:
#   - Résout le répertoire d’uploads à l’initialisation.
#   - Si le chemin demandé n’est pas inscriptible (FS read-only), fallback -> /tmp/emergence/uploads.
#   - Support optionnel d’un override via env EMERGENCE_UPLOADS_DIR.
#   - Le reste de la logique (DB, parsing, vectorisation) est inchangée.

import logging
import uuid
import os
import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Any
from pathlib import Path

from fastapi import UploadFile, HTTPException

from backend.core.database.manager import DatabaseManager
from backend.core.database import queries as db_queries
from backend.features.documents.parser import ParserFactory
from backend.features.memory.vector_service import VectorService
from backend.core import config

logger = logging.getLogger(__name__)

class DocumentService:
    def __init__(
        self,
        db_manager: DatabaseManager,
        parser_factory: ParserFactory,
        vector_service: VectorService,
        uploads_dir: str
    ):
        self.db_manager = db_manager
        self.parser_factory = parser_factory
        self.vector_service = vector_service
        self.document_collection = self.vector_service.get_or_create_collection(
            config.DOCUMENT_COLLECTION_NAME
        )

        # --- Résolution robuste du dossier d’upload ---
        # Ordre de priorité :
        #   1) EMERGENCE_UPLOADS_DIR (env)
        #   2) uploads_dir (DI existant)
        #   3) /tmp/emergence/uploads (fallback Cloud Run)
        env_override = os.getenv("EMERGENCE_UPLOADS_DIR", "").strip()
        requested = Path(env_override or uploads_dir or "/tmp/emergence/uploads")
        self.uploads_dir = self._ensure_writable_dir(requested)

        logger.info(
            "DocumentService (V8.4) initialisé. Collection='%s' uploads_dir='%s'",
            config.DOCUMENT_COLLECTION_NAME,
            self.uploads_dir
        )

    # --- Helpers internes ---

    def _ensure_writable_dir(self, path: Path) -> Path:
        """
        Tente de créer le dossier demandé et d’y écrire un fichier test.
        En cas d’échec (FS read-only, permissions, etc.), fallback vers /tmp/emergence/uploads.
        """
        # 1) Tentative sur le chemin demandé
        try:
            path.mkdir(parents=True, exist_ok=True)
            test_file = path / ".write_test"
            with open(test_file, "wb") as f:
                f.write(b"ok")
            # cleanup best-effort
            try:
                test_file.unlink()
            except Exception:
                pass
            return path
        except Exception as e:
            logger.warning(
                "Chemin d’uploads non inscriptible '%s' → fallback /tmp. Raison: %s",
                path, e
            )

        # 2) Fallback Cloud Run
        fallback = Path("/tmp/emergence/uploads")
        try:
            fallback.mkdir(parents=True, exist_ok=True)
            test_file = fallback / ".write_test"
            with open(test_file, "wb") as f:
                f.write(b"ok")
            try:
                test_file.unlink()
            except Exception:
                pass
            logger.info("Fallback uploads_dir = '%s'", fallback)
            return fallback
        except Exception as e2:
            # Si même /tmp échoue, on log et on laisse remonter (ça ne devrait pas arriver sur Cloud Run).
            logger.error("Impossible de créer le dossier d’uploads même dans /tmp: %s", e2, exc_info=True)
            raise

    def _chunk_text(self, text: str) -> List[str]:
        # Simple chunking (aligné config.CHUNK_SIZE)
        return [text[i:i + config.CHUNK_SIZE] for i in range(0, len(text), config.CHUNK_SIZE)]

    # --- API métier ---

    async def process_uploaded_file(self, file: UploadFile) -> int:
        filename = file.filename
        filepath = self.uploads_dir / f"{uuid.uuid4()}_{filename}"

        try:
            # Écriture du fichier source sur le FS (dossier garanti inscriptible)
            data = await file.read()
            with open(filepath, "wb") as buffer:
                buffer.write(data)

            # 1) Insert DB (statut 'pending') pour obtenir l’ID
            doc_id = await db_queries.insert_document(
                self.db_manager,
                filename=filename,
                filepath=str(filepath),
                status="pending",
                uploaded_at=datetime.now(timezone.utc).isoformat()
            )

            # 2) Parsing
            parser = self.parser_factory.get_parser(filepath.suffix)
            text_content = await asyncio.to_thread(parser.parse, filepath)

            # 3) Chunking
            chunks = self._chunk_text(text_content)

            # 4) Update DB (statut 'ready', counts)
            await db_queries.update_document_processing_info(
                self.db_manager,
                doc_id=doc_id,
                char_count=len(text_content),
                chunk_count=len(chunks),
                status="ready"
            )

            # 5) Vectorisation
            chunk_vectors = [
                {"id": f"{doc_id}_{i}", "text": chunk, "metadata": {"document_id": doc_id, "filename": filename}}
                for i, chunk in enumerate(chunks)
            ]
            self.vector_service.add_items(collection=self.document_collection, items=chunk_vectors)

            logger.info("Document '%s' (ID: %s) traité et vectorisé.", filename, doc_id)
            return doc_id

        except Exception as e:
            logger.error("Erreur lors du traitement du fichier '%s': %s", filename, e, exc_info=True)
            raise HTTPException(status_code=500, detail="Erreur lors du traitement du fichier.")

    async def get_all_documents(self) -> List[Dict[str, Any]]:
        """Liste les documents en base (via db_queries.get_all_documents)."""
        return await db_queries.get_all_documents(self.db_manager)

    async def delete_document(self, doc_id: int) -> bool:
        """
        Supprime un document :
          1) purge vecteurs (filtre metadata.document_id)
          2) suppression DB (document + chunks)
        """
        try:
            self.vector_service.delete_vectors(
                collection=self.document_collection,
                where_filter={"document_id": int(doc_id)}
            )
        except Exception as e:
            logger.warning("Echec purge vecteurs pour document %s: %s", doc_id, e)

        await db_queries.delete_document(self.db_manager, int(doc_id))
        return True
