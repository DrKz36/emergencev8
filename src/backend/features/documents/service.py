# src/backend/features/documents/service.py
# V8.3 - Ajout de get_all_documents/delete_document + purge vecteurs par document_id
import logging
import uuid
import os
import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Any

from fastapi import UploadFile, HTTPException
from pathlib import Path

from backend.core.database.manager import DatabaseManager
from backend.core.database import queries as db_queries
from backend.features.documents.parser import ParserFactory
from backend.features.memory.vector_service import VectorService
from backend.core import config

logger = logging.getLogger(__name__)

class DocumentService:
    def __init__(self, db_manager: DatabaseManager, parser_factory: ParserFactory, vector_service: VectorService, uploads_dir: str):
        self.db_manager = db_manager
        self.parser_factory = parser_factory
        self.vector_service = vector_service
        self.document_collection = self.vector_service.get_or_create_collection(config.DOCUMENT_COLLECTION_NAME)
        self.uploads_dir = Path(uploads_dir)
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"DocumentService (V8.3) initialisé. Collection: '{config.DOCUMENT_COLLECTION_NAME}'")

    def _chunk_text(self, text: str) -> List[str]:
        # Simple chunking pour l’instant (aligné avec core/config.py si besoin)
        return [text[i:i + config.CHUNK_SIZE] for i in range(0, len(text), config.CHUNK_SIZE)]

    async def process_uploaded_file(self, file: UploadFile) -> int:
        filename = file.filename
        filepath = self.uploads_dir / f"{uuid.uuid4()}_{filename}"
        
        try:
            with open(filepath, "wb") as buffer:
                buffer.write(await file.read())
            
            # Étape 1: Insérer le document avec un statut 'pending' pour obtenir un ID
            doc_id = await db_queries.insert_document(
                self.db_manager,
                filename=filename,
                filepath=str(filepath),
                status='pending',
                uploaded_at=datetime.now(timezone.utc).isoformat()
            )

            # Étape 2: Traiter le fichier
            parser = self.parser_factory.get_parser(filepath.suffix)
            text_content = await asyncio.to_thread(parser.parse, filepath)
            
            chunks = self._chunk_text(text_content)
            
            # Étape 3: Mettre à jour le document avec les infos de traitement
            await db_queries.update_document_processing_info(
                self.db_manager,
                doc_id=doc_id,
                char_count=len(text_content),
                chunk_count=len(chunks),
                status='ready'  # <- PATCH: 'processed' -> 'ready'
            )
            
            # Étape 4: Vectoriser et stocker les chunks
            chunk_vectors = [
                {"id": f"{doc_id}_{i}", "text": chunk, "metadata": {"document_id": doc_id, "filename": filename}}
                for i, chunk in enumerate(chunks)
            ]
            
            # Envoi vers Chroma
            self.vector_service.add_items(collection=self.document_collection, items=chunk_vectors)
            
            logger.info(f"Document '{filename}' (ID: {doc_id}) traité et vectorisé avec succès.")
            return doc_id

        except Exception as e:
            logger.error(f"Erreur lors du traitement du fichier '{filename}': {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Erreur lors du traitement du fichier.")
        finally:
            # Pas de suppression du fichier upload ici (utile pour audit)
            pass

    # --- ✅ NOUVELLES MÉTHODES EXPOSÉES AU ROUTEUR ---

    async def get_all_documents(self) -> List[Dict[str, Any]]:
        """
        Retourne la liste des documents enregistrés en base (avec champs clés).
        S'appuie sur backend.core.database.queries.get_all_documents.
        """
        return await db_queries.get_all_documents(self.db_manager)

    async def delete_document(self, doc_id: int) -> bool:
        """
        Supprime un document:
         1) purge des vecteurs dans la collection (filtre metadata.document_id)
         2) suppression en base (document + chunks)
        """
        try:
            # 1) Purge vecteurs
            self.vector_service.delete_vectors(
                collection=self.document_collection,
                where_filter={"document_id": int(doc_id)}
            )
        except Exception as e:
            # On loggue mais on n'empêche pas la suppression DB
            logger.warning(f"Echec purge vecteurs pour document {doc_id}: {e}")

        # 2) Suppression DB
        await db_queries.delete_document(self.db_manager, int(doc_id))
        return True
