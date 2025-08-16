# src/backend/features/documents/router.py
# V3.1 - Robustesse sync/async:
#        - Supporte DocumentService.get_all_documents() qu'il soit sync ou async
#        - Garde Bearer stricte + try/except conservés
import logging
import inspect
from pathlib import Path
from typing import List, Dict, Any

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException

from .service import DocumentService
from backend.shared import dependencies

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Documents"])


async def _maybe_await(value):
    """Si value est awaitable (coroutine/awaitable), on l'attend; sinon on le renvoie tel quel."""
    return await value if inspect.isawaitable(value) else value


@router.get("/", response_model=List[Dict[str, Any]])
async def list_documents(
    _token: str = Depends(dependencies.require_bearer_or_401),
    service: DocumentService = Depends(dependencies.get_document_service),
):
    """Retourne la liste de tous les documents uploadés."""
    try:
        result = service.get_all_documents()
        return await _maybe_await(result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur list_documents: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erreur interne lors de la récupération des documents.")


# ✅ Alias sans slash: /api/documents (en plus de /api/documents/)
@router.get("", response_model=List[Dict[str, Any]])
async def list_documents_alias(
    _token: str = Depends(dependencies.require_bearer_or_401),
    service: DocumentService = Depends(dependencies.get_document_service),
):
    """Alias sans slash final pour éviter 404."""
    try:
        result = service.get_all_documents()
        return await _maybe_await(result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur list_documents (alias): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erreur interne lors de la récupération des documents.")


@router.post("/upload", status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    service: DocumentService = Depends(dependencies.get_document_service),
):
    supported_types = [".pdf", ".txt", ".docx"]
    file_extension = Path(file.filename).suffix.lower()
    if file_extension not in supported_types:
        raise HTTPException(status_code=400, detail=f"Type de fichier non supporté. Types acceptés : {supported_types}")
    try:
        # Support sync/async sur process_uploaded_file aussi, par cohérence
        result = service.process_uploaded_file(file)
        document_id = await _maybe_await(result)
        return {
            "message": "Fichier uploadé et traité avec succès.",
            "document_id": document_id,
            "filename": file.filename
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur critique lors de l'upload: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erreur interne lors du traitement du fichier.")


@router.delete("/{document_id}", status_code=200)
async def delete_document(
    document_id: str,
    service: DocumentService = Depends(dependencies.get_document_service),
):
    """Supprime un document, ses chunks et ses vecteurs."""
    try:
        result = service.delete_document(document_id)
        success = await _maybe_await(result)
        if success:
            return {"message": "Document supprimé avec succès."}
        # Le service peut lever HTTPException 404 si non trouvé.
        return {"message": "Aucun document supprimé."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur delete_document({document_id}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erreur interne lors de la suppression du document.")
