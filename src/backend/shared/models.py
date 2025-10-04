# src/backend/shared/models.py
# V13.27 - FIX: Ajout du modèle manquant 'Session'.
"""
Module central pour les modèles de données partagés (Pydantic).
Assure la cohérence et la validation des structures de données à travers toute l'application.
"""
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from enum import Enum
from datetime import datetime

# --- Énumérations pour les valeurs contrôlées ---

class Role(str, Enum):
    """Définit les rôles possibles dans un échange."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class ChatMode(str, Enum):
    """Définit les modes d'interaction possibles."""
    DIALOGUE = "dialogue"
    DEBATE = "debate"
    DOCUMENT = "document"
    SINGLE = "single"

# --- MODÈLE POUR LA SESSION (AJOUTÉ) ---

class Session(BaseModel):
    """
    Représente une session de chat complète, de son début à sa fin.
    C'est l'objet principal géré par le SessionManager.
    """
    id: str = Field(..., description="ID unique de la session (généralement un UUID)")
    user_id: str = Field(..., description="ID de l'utilisateur associé à la session")
    start_time: datetime = Field(..., description="Horodatage du début de la session")
    end_time: Optional[datetime] = Field(None, description="Horodatage de la fin de la session")
    history: List[Dict[str, Any]] = Field(default_factory=list, description="Liste des messages (ChatMessage, AgentMessage) de la session")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata for the session (thread info, summaries).")
    
    class Config:
        extra = 'allow' # Permet d'ajouter des champs non définis (ex: summary, concepts) plus tard

# --- Modèles pour les messages ---

class ChatMessage(BaseModel):
    """

    Structure de base pour un message stocké dans l'historique de session.
    C'est le format interne unifié.
    """
    id: str = Field(..., description="ID unique du message")
    session_id: str = Field(..., description="ID de la session à laquelle le message appartient")
    role: Role = Field(..., description="Rôle de l'auteur du message (user ou assistant)")
    agent: str = Field(..., description="Agent concerné (ex: 'anima', 'neo', ou 'user')")
    content: str = Field(..., description="Contenu textuel du message")
    timestamp: str = Field(..., description="Horodatage ISO 8601 du message")
    cost: Optional[float] = Field(None, description="Coût associé à la génération de ce message (si assistant)")
    tokens: Optional[Dict[str, Any]] = Field(None, description="Détail des tokens utilisés (input, output)")
    agents: Optional[List[str]] = Field(None, description="Liste des agents cibles pour un nouveau message utilisateur.")
    use_rag: bool = Field(False, description="Indique si le RAG doit être utilisé pour ce message.")
    doc_ids: Optional[List[str]] = Field(
        default=None,
        description="Liste optionnelle d'identifiants de documents associés au RAG pour ce message.",
    )
    meta: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Métadonnées complémentaires (RAG, avis, diffusion WS, etc.).",
    )

    class Config:
        extra = 'ignore'


# --- Modèles pour les réponses API (contrats avec le frontend) ---

class AgentMessage(BaseModel):
    """
    Structure d'un message tel qu'envoyé au frontend.
    Plus léger que ChatMessage.
    """
    id: str
    session_id: str # Ajout pour la cohérence
    role: Role
    message: str 
    agent: str
    cost_info: Optional[Dict[str, Any]] = None
    timestamp: str
    meta: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    """
    Structure de la réponse pour une interaction de chat simple.
    """
    success: bool
    message: AgentMessage
    agent: str
    mode: ChatMode
    cost: Optional[Dict[str, Any]] = None
    processingTime: float
