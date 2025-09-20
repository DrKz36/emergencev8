# src/backend/features/documents/router.py
# V2.2 - Safe resolver for get_document_service + alias sans slash
import logging
from pathlib import Path
from typing import Any, Dict, List, Awaitable, Callable, cast

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Request

from .service import DocumentService
from backend.shared import dependencies as deps  # <- module, pas l'attribut direct

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Documents"])


async def _get_document_service(request: Request) -> DocumentService:
    getter = getattr(deps, "get_document_service", None)
    if getter is None or not callable(getter):
        raise HTTPException(status_code=503, detail="Document service unavailable.")
    typed_getter = cast(Callable[[Request], Awaitable[DocumentService]], getter)
    service = await typed_getter(request)
    if not isinstance(service, DocumentService):
        raise HTTPException(status_code=503, detail="Invalid document service instance.")
    return service


@router.get("/", response_model=List[Dict[str, Any]])
async def list_documents(service: DocumentService = Depends(_get_document_service)):
    """Retourne la liste de tous les documents uploades."""
    return await service.get_all_documents()


@router.get("", response_model=List[Dict[str, Any]])
async def list_documents_alias(service: DocumentService = Depends(_get_document_service)):
    """Alias sans slash final pour eviter 404."""
    return await service.get_all_documents()


@router.post("/upload", status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    service: DocumentService = Depends(_get_document_service),
):
    supported_types = [".pdf", ".txt", ".docx"]
    filename = file.filename or ""
    if not filename:
        raise HTTPException(status_code=400, detail="Nom de fichier manquant.")
    file_extension = Path(filename).suffix.lower()
    if file_extension not in supported_types:
        raise HTTPException(
            status_code=400,
            detail=f"Type de fichier non supporte. Types acceptes : {supported_types}",
        )
    try:
        document_id = await service.process_uploaded_file(file)
        return {
            "message": "Fichier uploade et traite avec succes.",
            "document_id": document_id,
            "filename": filename,
        }
    except Exception as exc:
        logger.error(f"Erreur critique lors de l'upload: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Erreur interne lors du traitement du fichier.")


@router.delete("/{document_id}", status_code=200)
async def delete_document(
    document_id: int,
    service: DocumentService = Depends(_get_document_service),
):
    """Supprime un document, ses chunks et ses vecteurs."""
    success = await service.delete_document(document_id)
    if success:
        return {"message": "Document supprime avec succes."}
    # Le service leve HTTPException 404 si non trouve.
