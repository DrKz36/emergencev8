# V3.3 - Dev bypass Auth (AUTH_DEV_MODE=1) + robustesse
#        - En dev: routes accessibles sans ID token (utilisateur factice)
#        - En prod: inchangé -> Google ID token requis
#        - Garde la sérialisation "jsonable_encoder" + alias sans slash

import logging
import inspect
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from fastapi.encoders import jsonable_encoder

from .service import DocumentService
from backend.shared import dependencies
from backend.shared.auth.google_oauth import require_google_user

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Documents"])

# --- Auth selector: dev bypass si AUTH_DEV_MODE=1 --------------------------------
def _dev_user():
    # Utilisateur factice minimal pour dev local
    return {
        "sub": "dev_user_local",
        "email": "dev@local",
        "email_verified": True,
        "hd": None,
        "iss": "dev",
        "aud": "dev",
    }

AUTH_DEV_MODE = os.getenv("AUTH_DEV_MODE", "0") == "1"

def current_user_dependency():
    """
    Retourne la dépendance FastAPI à utiliser selon l'environnement.
    - Prod (default): require_google_user (ID token obligatoire)
    - Dev (AUTH_DEV_MODE=1): utilisateur factice
    """
    if AUTH_DEV_MODE:
        async def _dep():
            return _dev_user()
        return _dep
    else:
        return require_google_user

async def _maybe_await(value):
    """Si value est awaitable (coroutine/awaitable), on l'attend; sinon on le renvoie tel quel."""
    return await value if inspect.isawaitable(value) else value

def _to_list(value: Any) -> list:
    """Normalise la sortie en liste (générateurs/sets/tuples -> list; objet seul -> [obj])."""
    if isinstance(value, list):
        return value
    if isinstance(value, (tuple, set)):
        return list(value)
    try:
        if hasattr(value, "__iter__") and not isinstance(value, (str, bytes, dict)):
            return list(value)
    except Exception:
        pass
    return [value]

# ------------------------------------------------------------------------------

@router.get("/")  # pas de response_model pour éviter 500 de validation côté FastAPI
async def list_documents(
    user = Depends(current_user_dependency()),
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
    user = Depends(current_user_dependency()),
    service: DocumentService = Depends(dependencies.get_document_service),
):
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
    user = Depends(current_user_dependency()),
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
    user = Depends(current_user_dependency()),
    service: DocumentService = Depends(dependencies.get_document_service),
):
    """Supprime un document, ses chunks et ses vecteurs."""
    try:
        result = service.delete_document(document_id)
        success = await _maybe_await(result)
        if success:
            return {"message": "Document supprimé avec succès."}
        return {"message": "Aucun document supprimé."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur delete_document({document_id}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erreur interne lors de la suppression du document.")
