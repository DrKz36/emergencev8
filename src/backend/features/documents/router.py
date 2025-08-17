# src/backend/features/documents/router.py
# V3.2 - Hotfix 500 serialization:
#        - Retire response_model (validation stricte) sur GET
#        - Normalise en liste + jsonable_encoder pour éviter erreurs de sérialisation
#        - Garde Google ID token (require_google_user) + try/except + compat sync/async

import logging
import inspect
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from fastapi.encoders import jsonable_encoder

from .service import DocumentService
from backend.shared import dependencies
from backend.shared.auth.google_oauth import require_google_user

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Documents"])


async def _maybe_await(value):
    """Si value est awaitable (coroutine/awaitable), on l'attend; sinon on le renvoie tel quel."""
    return await value if inspect.isawaitable(value) else value


def _to_list(value: Any) -> list:
    """Normalise la sortie en liste (générateurs/sets/tuples -> list; objet seul -> [obj])."""
    if isinstance(value, list):
        return value
    if isinstance(value, (tuple, set)):
        return list(value)
    # Iterable non string/bytes/dict → on tente list()
    try:
        if hasattr(value, "__iter__") and not isinstance(value, (str, bytes, dict)):
            return list(value)
    except Exception:
        pass
    return [value]


@router.get("/")  # ❌ pas de response_model pour éviter 500 côté validation
async def list_documents(
    user = Depends(require_google_user),
    service: DocumentService = Depends(dependencies.get_document_service),
):
    """Retourne la liste des documents (format libre côté service)."""
    try:
        result = service.get_all_documents()
        raw = await _maybe_await(result)
        items = _to_list(raw)
        payload = jsonable_encoder(items)  # BaseModel -> dict, Path -> str, etc.
        return payload
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur list_documents: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erreur interne lors de la récupération des documents.")


# ✅ Alias sans slash: /api/documents (en plus de /api/documents/)
@router.get("")  # idem: pas de response_model
async def list_documents_alias(
    user = Depends(require_google_user),
    service: DocumentService = Depends(dependencies.get_document_service),
):
    """Alias sans slash final pour éviter 404."""
    try:
        result = service.get_all_documents()
        raw = await _maybe_await(result)
        items = _to_list(raw)
        payload = jsonable_encoder(items)
        return payload
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur list_documents (alias): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erreur interne lors de la récupération des documents.")


@router.post("/upload", status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    user = Depends(require_google_user),
    service: DocumentService = Depends(dependencies.get_document_service),
):
    supported_types = [".pdf", ".txt", ".docx"]
    file_extension = Path(file.filename).suffix.lower()
    if file_extension not in supported_types:
        raise HTTPException(status_code=400, detail=f"Type de fichier non supporté. Types acceptés : {supported_types}")
    try:
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
    user = Depends(require_google_user),
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
