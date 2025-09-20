# src/backend/features/debate/models.py
"""
Modèles de données Pydantic pour le Débat.
Version V6.0 - Ajout de l'option RAG.
"""
from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Any, Optional
from enum import Enum

class DebateStatus(str, Enum):
    """Énumère les états possibles d'un débat."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class DebateConfig(BaseModel):
    """
    Configuration d'un débat, validée à la création.
    V6.0: Ajout du booléen use_rag.
    """
    topic: str = Field(..., min_length=10, description="Le sujet du débat.")
    rounds: int = Field(..., ge=1, le=5, description="Le nombre de tours du débat.")
    agent_order: List[str] = Field(..., min_length=3, max_length=3, description="L'ordre des agents participants.")
    use_rag: bool = Field(default=False, description="Indique si le débat doit utiliser le contexte RAG.")

    @field_validator('agent_order')
    @classmethod
    def check_unique_agents(cls, v: List[str]) -> List[str]:
        if len(set(v)) != len(v):
            raise ValueError('Les agents dans agent_order doivent être uniques.')
        return v

class DebateTurn(BaseModel):
    """Représente un round complet du débat."""
    round_number: int
    agent_responses: Dict[str, str] = Field(default_factory=dict, description="Réponses des agents pour ce tour.")

class DebateSession(BaseModel):
    """
    Représente l'état complet d'une session de débat.
    C'est l'objet qui sera sauvegardé à la fin.
    """
    debate_id: str
    session_id: str
    config: DebateConfig
    status: DebateStatus = DebateStatus.PENDING
    history: List[DebateTurn] = Field(default_factory=list)
    synthesis: Optional[str] = None
    # V6.0: Ajout d'un champ pour stocker le contexte RAG pour la traçabilité.
    rag_context: Optional[str] = Field(default=None, description="Contexte RAG utilisé pour le débat, s'il y a lieu.")
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def get_total_cost(self) -> float:
        """Calcule le coût total du débat. NOTE: Coûts non implémentés dans cette structure."""
        return 0.0
