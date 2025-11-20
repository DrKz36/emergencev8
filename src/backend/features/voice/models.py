# src/backend/features/voice/models.py

from typing import Dict
from pydantic import BaseModel, Field


class VoiceServiceConfig(BaseModel):
    """
    Configuration pour le VoiceService, validée par Pydantic.
    Permet de centraliser les clés API et autres paramètres
    pour les services de Speech-to-Text et Text-to-Speech.
    """

    stt_provider: str = Field(
        default="whisper", description="Fournisseur du service Speech-to-Text."
    )
    stt_api_key: str = Field(..., description="Clé API pour le service STT.")
    stt_model: str = Field(
        default="whisper-1", description="Modèle utilisé pour le STT."
    )

    tts_provider: str = Field(
        default="elevenlabs", description="Fournisseur du service Text-to-Speech."
    )
    tts_api_key: str = Field(..., description="Clé API pour le service TTS.")
    tts_model_id: str = Field(
        default="a_model_id_here", description="ID du modèle de voix pour le TTS."
    )
    tts_voice_id: str = Field(
        default="a_voice_id_here",
        description="ID de la voix spécifique pour le TTS (fallback).",
    )

    # Mapping agent_id → voice_id pour voix différentes par agent
    agent_voices: Dict[str, str] = Field(
        default_factory=dict,
        description="Mapping agent_id → voice_id ElevenLabs pour personnaliser la voix par agent.",
    )
