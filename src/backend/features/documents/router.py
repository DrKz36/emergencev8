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
    try:
        service = await typed_getter(request)
    except HTTPException:
        raise
    except AttributeError as exc:
        logger.error("DocumentService provider unavailable: %s", exc)
        raise HTTPException(status_code=503, detail="Document service unavailable.") from exc
    except Exception as exc:
        logger.error("Failed to resolve DocumentService: %s", exc, exc_info=True)
        raise HTTPException(status_code=503, detail="Document service unavailable.") from exc
    if not isinstance(service, DocumentService):
        raise HTTPException(status_code=503, detail="Invalid document service instance.")
    return service


@router.get("/", response_model=List[Dict[str, Any]])
async def list_documents(
    session: deps.SessionContext = Depends(deps.get_session_context),
    service: DocumentService = Depends(_get_document_service),
) -> List[Dict[str, Any]]:
    """Retourne la liste de tous les documents uploades."""
    return await service.get_all_documents(session.session_id, user_id=session.user_id)


@router.get("", response_model=List[Dict[str, Any]])
async def list_documents_alias(
    session: deps.SessionContext = Depends(deps.get_session_context),
    service: DocumentService = Depends(_get_document_service),
) -> List[Dict[str, Any]]:
    """Alias sans slash final pour eviter 404."""
    return await service.get_all_documents(session.session_id, user_id=session.user_id)


@router.post("/upload", status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    session: deps.SessionContext = Depends(deps.get_session_context),
    service: DocumentService = Depends(_get_document_service),
) -> Dict[str, Any]:
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
        document_id = await service.process_uploaded_file(
            file, session_id=session.session_id, user_id=session.user_id
        )
        return {
            "message": "Fichier uploade et traite avec succes.",
            "document_id": document_id,
            "filename": filename,
        }
    except Exception as exc:
        logger.error(f"Erreur critique lors de l'upload: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Erreur interne lors du traitement du fichier.")


@router.get("/{document_id}")
async def get_document(
    document_id: int,
    session: deps.SessionContext = Depends(deps.get_session_context),
    service: DocumentService = Depends(_get_document_service),
) -> Dict[str, Any]:
    """Retourne les détails d'un document spécifique."""
    try:
        docs = await service.get_all_documents(session.session_id, user_id=session.user_id)
        document = next((doc for doc in docs if doc.get("id") == document_id), None)
        if document is None:
            raise HTTPException(status_code=404, detail="Document introuvable")
        return document
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Erreur lors de la récupération du document {document_id}: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erreur interne lors de la récupération du document")


@router.delete("/{document_id}", status_code=200)
async def delete_document(
    document_id: int,
    session: deps.SessionContext = Depends(deps.get_session_context),
    service: DocumentService = Depends(_get_document_service),
) -> Dict[str, str]:
    """Supprime un document, ses chunks et ses vecteurs."""
    success = await service.delete_document(document_id, session.session_id, user_id=session.user_id)
    if success:
        return {"message": "Document supprime avec succes."}
    raise HTTPException(status_code=404, detail="Document introuvable")


