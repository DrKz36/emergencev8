# src/backend/features/voice/service.py
# V1.1 - Correction du chemin d'importation
import httpx
import logging
from typing import AsyncGenerator, List, Dict, Any

from .models import VoiceServiceConfig
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
        logger.info("VoiceService initialise avec STT, TTS, et ChatService.")

    async def transcribe_audio(self, audio_stream: AsyncGenerator[bytes, None]) -> str:
        logger.info("Debut de la transcription audio avec l'API OpenAI...")
        audio_bytes_list: List[bytes] = [chunk async for chunk in audio_stream]
        audio_data = b"".join(audio_bytes_list)

        if not audio_data:
            logger.warning("Aucune donnee audio recue pour la transcription.")
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
            logger.info("Texte transcrit: '%s'", transcribed_text)
            from typing import cast
            return cast(str, transcribed_text)
        except httpx.HTTPStatusError as exc:
            error_body = await exc.response.aread()
            logger.error(
                "Erreur API Whisper: %s - %s",
                exc.response.status_code,
                error_body.decode(),
            )
            raise Exception("Erreur de transcription.")

    async def synthesize_speech(self, text: str, agent_id: str | None = None) -> AsyncGenerator[bytes, None]:
        logger.info(
            "Debut de la synthese vocale avec ElevenLabs pour le texte: '%s'... (agent=%s)",
            text[:30],
            agent_id,
        )

        # Choisir la voice_id en fonction de l'agent (ou fallback sur default)
        voice_id = self.config.tts_voice_id  # Fallback par défaut
        if agent_id and agent_id in self.config.agent_voices:
            voice_id = self.config.agent_voices[agent_id]
            logger.info(f"Voix spécifique pour agent '{agent_id}': {voice_id}")
        else:
            logger.info(f"Voix par défaut utilisée: {voice_id}")

        if (
            not voice_id
            or not isinstance(voice_id, str)
            or voice_id.startswith("sk_")
        ):
            logger.error(
                "ID de voix ElevenLabs invalide ou manquant. ID actuel : '%s'.",
                voice_id,
            )
            raise ValueError("ID de voix ElevenLabs non configure ou invalide.")

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"
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
                        "Erreur API ElevenLabs: %s - %s",
                        response.status_code,
                        error_body.decode(),
                    )
                    response.raise_for_status()

                logger.info("Streaming TTS audio...")
                async for chunk in response.aiter_bytes():
                    yield chunk
                logger.info("Fin du streaming TTS.")

        except httpx.HTTPStatusError as exc:
            raise Exception(
                f"Erreur de synthese vocale (HTTP {exc.response.status_code})."
            )
        except Exception as exc:
            logger.error("Erreur inattendue pendant la synthese vocale: %s", exc)
            raise

    async def process_voice_interaction(
        self,
        audio_stream: AsyncGenerator[bytes, None],
        agent_name: str,
        session_id: str,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Gere l'interaction vocale complete et renvoie des dictionnaires structures.
        - {'type': 'text', 'data': str} pour la reponse textuelle
        - {'type': 'audio', 'data': bytes} pour les chunks audio
        """
        try:
            user_text = await self.transcribe_audio(audio_stream)
            if not user_text:
                logger.warning("Transcription vide, interaction annulee.")
                yield {
                    "type": "text",
                    "data": "Je n'ai rien entendu. Peux-tu repeter ?",
                }
                async for chunk in self.synthesize_speech(
                    "Je n'ai rien entendu. Peux-tu repeter ?"
                ):
                    yield {"type": "audio", "data": chunk}
                return

            logger.info(
                "Envoi du texte transcrit '%s' a l'agent '%s'...",
                user_text,
                agent_name,
            )
            history_snapshot: List[Dict[str, Any]] = []
            try:
                history_snapshot = self.chat_service.session_manager.get_full_history(
                    session_id
                )
            except Exception:
                history_snapshot = []
            response_payload = await self.chat_service.get_llm_response_for_debate(
                agent_id=agent_name,
                prompt=user_text,
                session_id=session_id,
                use_rag=False,
                history=history_snapshot,
            )
            agent_response_text = str(response_payload.get("text") or "").strip()
            if not agent_response_text:
                agent_response_text = (
                    "Je suis desole, je n'ai pas de reponse pour le moment."
                )

            yield {"type": "text", "data": agent_response_text}

            async for audio_chunk in self.synthesize_speech(agent_response_text):
                yield {"type": "audio", "data": audio_chunk}

        except Exception as exc:
            logger.error(
                "Erreur majeure dans le cycle vocal: %s",
                exc,
                exc_info=True,
            )
            error_message = (
                "Desole, une erreur technique est survenue lors de la generation de la reponse vocale."
            )
            try:
                yield {"type": "text", "data": error_message}
                async for chunk in self.synthesize_speech(error_message):
                    yield {"type": "audio", "data": chunk}
            except Exception as synth_error:
                logger.error(
                    "Impossible de generer le message d'erreur vocal: %s",
                    synth_error,
                )
