# src/backend/features/documents/router.py
# V3.0 - /api/documents GET protégés par require_bearer_or_401 + try/except (fiabilise 401 vs 500)
import logging
from pathlib import Path
from typing import List, Dict, Any

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException

from .service import DocumentService
from backend.shared import dependencies

logger = logging.getLogger(__name__)

# Remarque: on NE met PAS de garde globale ici pour coller au correctif minimal
# décrit dans le résumé : protection ciblée sur les endpoints GET seulement.
router = APIRouter(tags=["Documents"])

@router.get("/", response_model=List[Dict[str, Any]])
async def list_documents(
    _token: str = Depends(dependencies.require_bearer_or_401),
    service: DocumentService = Depends(dependencies.get_document_service),
):
    """Retourne la liste de tous les documents uploadés."""
    try:
        return await service.get_all_documents()
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
        return await service.get_all_documents()
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
        document_id = await service.process_uploaded_file(file)
        return {"message": "Fichier uploadé et traité avec succès.", "document_id": document_id, "filename": file.filename}
    except Exception as e:
        logger.error(f"Erreur critique lors de l'upload: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erreur interne lors du traitement du fichier.")

# ✅ URL standard REST: /api/documents/{document_id}
@router.delete("/{document_id}", status_code=200)
async def delete_document(
    document_id: str,
    service: DocumentService = Depends(dependencies.get_document_service),
):
    """Supprime un document, ses chunks et ses vecteurs."""
    success = await service.delete_document(document_id)
    if success:
        return {"message": "Document supprimé avec succès."}
    # Le service lève HTTPException 404 si non trouvé.
