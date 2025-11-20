# src/backend/features/documents/models.py
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from enum import Enum


class DocumentStatus(str, Enum):
    """
    Énumération pour les statuts possibles d'un document.
    Rend le code plus lisible et évite les erreurs de frappe.
    """

    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    ERROR = "error"


class Document(BaseModel):
    """
    Modèle Pydantic représentant un document dans notre système.
    Utilisé pour la validation et la sérialisation des données.
    """

    id: str
    filename: str
    file_type: str
    status: DocumentStatus
    chunk_count: int
    uploaded_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UploadResponse(BaseModel):
    """
    Modèle pour la réponse JSON de l'endpoint d'upload.
    """

    message: str
    document_id: str
