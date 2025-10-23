# src/backend/features/voice/router.py
# V1.0 - Creation initiale du routeur WebSocket pour la voix
import logging
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect, HTTPException

from backend.features.voice.service import VoiceService
from backend.shared import dependencies

logger = logging.getLogger(__name__)

router = APIRouter()


def _ensure_voice_service(websocket: WebSocket) -> VoiceService:
    container = getattr(websocket.app.state, "service_container", None)
    if container is None:
        raise HTTPException(status_code=503, detail="Voice service unavailable.")
    provider = getattr(container, "voice_service", None)
    if provider is None:
        raise HTTPException(status_code=503, detail="Voice service unavailable.")
    try:
        service = provider()
    except Exception as exc:
        logger.error(f"Impossible de recuperer VoiceService: {exc}", exc_info=True)
        raise HTTPException(status_code=503, detail="Voice service indisponible.")
    if not isinstance(service, VoiceService):
        raise HTTPException(status_code=503, detail="Voice service invalide.")
    return service


async def audio_receiver(websocket: WebSocket) -> AsyncGenerator[bytes, None]:
    """Recoit un flux binaire via WebSocket et le renvoie chunk par chunk."""
    try:
        while True:
            data = await websocket.receive_bytes()
            yield data
    except WebSocketDisconnect:
        logger.info("Le client a ferme la connexion pendant la reception audio.")
    except Exception as exc:
        logger.error(f"Erreur inattendue pendant la reception audio: {exc}", exc_info=True)


@router.websocket("/ws/{agent_name}")
async def voice_chat_ws(
    websocket: WebSocket,
    agent_name: str,
    session_id: str = Query(...),
    service: VoiceService = Depends(_ensure_voice_service),
    user_id: str = Depends(dependencies.get_user_id_from_websocket),
) -> None:
    """Interaction vocale bi-directionnelle entre un utilisateur et un agent."""
    await websocket.accept()
    logger.info(
        "WebSocket connecte pour l'agent '%s' (Session: %s, User: %s)",
        agent_name,
        session_id,
        user_id,
    )

    try:
        audio_stream = audio_receiver(websocket)
        response_generator = service.process_voice_interaction(
            audio_stream=audio_stream,
            agent_name=agent_name,
            session_id=session_id,
        )

        async for response_part in response_generator:
            await websocket.send_json(response_part)

    except HTTPException as exc:
        logger.warning(f"Erreur de dependance WebSocket: {exc}")
        try:
            await websocket.close(code=4401)
        except Exception:
            pass
    except WebSocketDisconnect:
        logger.info("Client deconnecte de l'agent '%s' (Session: %s)", agent_name, session_id)
    except Exception as exc:
        logger.error(
            f"Erreur critique dans le WebSocket pour l'agent '{agent_name}': {exc}",
            exc_info=True,
        )
        error_payload = {"type": "error", "data": "Une erreur interne est survenue sur le serveur."}
        try:
            await websocket.send_json(error_payload)
        except Exception:
            pass
    finally:
        from fastapi.websockets import WebSocketState
        if websocket.client_state != WebSocketState.DISCONNECTED:
            await websocket.close()
            logger.info("Connexion WebSocket fermee pour la session %s.", session_id)
