# src/backend/features/voice/service.py
# V1.1 - Correction du chemin d'importation
import httpx
import logging
from typing import AsyncGenerator, List, Dict, Any
from .models import VoiceServiceConfig

# ✅ CORRECTION : Chemin d'importation standardisé
from backend.features.chat.service import ChatService

logger = logging.getLogger(__name__)


class VoiceService:
    def __init__(
        self,
        config: VoiceServiceConfig,
        http_client: httpx.AsyncClient,
        chat_service: ChatService,
    ):
        self.config = config
        self.http_client = http_client
        self.chat_service = chat_service
        logger.info("VoiceService initialisé avec STT, TTS, et ChatService.")

    async def transcribe_audio(self, audio_stream: AsyncGenerator[bytes, None]) -> str:
        logger.info("Début de la transcription audio avec l'API OpenAI...")
        audio_bytes_list: List[bytes] = [chunk async for chunk in audio_stream]
        audio_data = b"".join(audio_bytes_list)

        if not audio_data:
            logger.warning("Aucune donnée audio reçue pour la transcription.")
            return ""

        files = {"file": ("audio.webm", audio_data, "audio/webm")}
        data = {"model": self.config.stt_model}
        headers = {"Authorization": f"Bearer {self.config.stt_api_key}"}
        url = "https://api.openai.com/v1/audio/transcriptions"

        try:
            response = await self.http_client.post(
                url, headers=headers, data=data, files=files, timeout=60.0
            )
            response.raise_for_status()
            result = response.json()
            transcribed_text = result.get("text", "").strip()
            logger.info(f"Texte transcrit: '{transcribed_text}'")
            return transcribed_text
        except httpx.HTTPStatusError as e:
            error_body = await e.response.aread()
            logger.error(
                f"Erreur API Whisper: {e.response.status_code} - {error_body.decode()}"
            )
            raise Exception("Erreur de transcription.")

    async def synthesize_speech(self, text: str) -> AsyncGenerator[bytes, None]:
        logger.info(
            f"Début de la synthèse vocale avec ElevenLabs pour le texte: '{text[:30]}...'"
        )

        if (
            not self.config.tts_voice_id
            or not isinstance(self.config.tts_voice_id, str)
            or self.config.tts_voice_id.startswith("sk_")
        ):
            logger.error(
                f"ID de voix ElevenLabs invalide ou manquant. ID actuel : '{self.config.tts_voice_id}'. Vérifie la configuration."
            )
            raise ValueError("ID de voix ElevenLabs non configuré ou invalide.")

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.config.tts_voice_id}/stream"
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.config.tts_api_key,
        }
        payload = {"text": text, "model_id": self.config.tts_model_id}

        try:
            async with self.http_client.stream(
                "POST", url, headers=headers, json=payload, timeout=60.0
            ) as response:
                if not response.is_success:
                    error_body = await response.aread()
                    logger.error(
                        f"Erreur API ElevenLabs: {response.status_code} - {error_body.decode()}"
                    )
                    response.raise_for_status()

                logger.info("Streaming TTS audio...")
                async for chunk in response.aiter_bytes():
                    yield chunk
                logger.info("Fin du streaming TTS.")

        except httpx.HTTPStatusError as e:
            raise Exception(
                f"Erreur de synthèse vocale (HTTP {e.response.status_code})."
            )
        except Exception as e:
            logger.error(f"Erreur inattendue pendant la synthèse vocale: {e}")
            raise

    async def process_voice_interaction(
        self,
        audio_stream: AsyncGenerator[bytes, None],
        agent_name: str,
        session_id: str,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Gère l'interaction vocale complète et renvoie des dictionnaires structurés.
        - {'type': 'text', 'data': str} pour la réponse textuelle
        - {'type': 'audio', 'data': bytes} pour les chunks audio
        """
        try:
            user_text = await self.transcribe_audio(audio_stream)
            if not user_text:
                logger.warning("Transcription vide, interaction annulée.")
                yield {
                    "type": "text",
                    "data": "Je n'ai rien entendu. Peux-tu répéter ?",
                }
                async for chunk in self.synthesize_speech(
                    "Je n'ai rien entendu. Peux-tu répéter ?"
                ):
                    yield {"type": "audio", "data": chunk}
                return

            logger.info(
                f"Envoi du texte transcrit '{user_text}' à l'agent '{agent_name}'..."
            )
            chat_response = await self.chat_service.process_message(
                agent_id=agent_name, message_content=user_text, session_id=session_id
            )
            agent_response_text = chat_response.message.content

            yield {"type": "text", "data": agent_response_text}

            async for audio_chunk in self.synthesize_speech(agent_response_text):
                yield {"type": "audio", "data": audio_chunk}

        except Exception as e:
            logger.error(f"Erreur majeure dans le cycle vocal: {e}", exc_info=True)
            error_message = "Désolé, une erreur technique est survenue lors de la génération de la réponse vocale."
            try:
                yield {"type": "text", "data": error_message}
                async for chunk in self.synthesize_speech(error_message):
                    yield {"type": "audio", "data": chunk}
            except Exception as synth_error:
                logger.error(
                    f"Impossible de générer le message d'erreur vocal: {synth_error}"
                )
