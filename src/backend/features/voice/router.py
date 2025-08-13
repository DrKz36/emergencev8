# src/backend/features/voice/router.py
# V1.0 - Création initiale du routeur WebSocket pour la voix
import logging
import json
from typing import AsyncGenerator

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query

from backend.features.voice.service import VoiceService
from backend.shared import dependencies
from backend.shared.dependencies import WebSocketException

logger = logging.getLogger(__name__)

router = APIRouter()

async def audio_receiver(websocket: WebSocket) -> AsyncGenerator[bytes, None]:
    """
    Un générateur asynchrone qui écoute les messages entrants du WebSocket
    et les yield comme des chunks de bytes audio.
    """
    try:
        while True:
            data = await websocket.receive_bytes()
            yield data
    except WebSocketDisconnect:
        logger.info("Le client a fermé la connexion pendant la réception audio.")
        # Le générateur s'arrête simplement lorsque le client se déconnecte.
        pass
    except Exception as e:
        logger.error(f"Erreur inattendue pendant la réception audio: {e}", exc_info=True)


@router.websocket("/ws/{agent_name}")
async def voice_chat_ws(
    websocket: WebSocket,
    agent_name: str,
    session_id: str = Query(...),
    service: VoiceService = Depends(dependencies.get_voice_service),
    user_id: str = Depends(dependencies.get_user_id_from_websocket) # Sécurise et identifie
):
    """
    Endpoint WebSocket pour une interaction vocale bi-directionnelle.
    1. Accepte la connexion.
    2. Reçoit un flux de bytes audio du client.
    3. Passe le flux au VoiceService.
    4. Streame les réponses (texte puis audio) au client.
    """
    await websocket.accept()
    logger.info(f"WebSocket connecté pour l'agent '{agent_name}' (Session: {session_id}, User: {user_id})")

    try:
        audio_stream = audio_receiver(websocket)
        
        # Le service traite le flux et renvoie des dictionnaires structurés
        response_generator = service.process_voice_interaction(
            audio_stream=audio_stream,
            agent_name=agent_name,
            session_id=session_id
        )

        async for response_part in response_generator:
            # response_part est un dict: {'type': 'text'|'audio', 'data': ...}
            await websocket.send_json(response_part)

    except WebSocketException as e:
        # Géré par la dépendance, qui a déjà fermé le socket.
        logger.warning(f"Erreur de dépendance WebSocket: {e}")
    except WebSocketDisconnect:
        logger.info(f"Client déconnecté de l'agent '{agent_name}'. Session: {session_id}")
    except Exception as e:
        logger.error(f"Erreur critique dans le WebSocket pour l'agent '{agent_name}': {e}", exc_info=True)
        error_payload = {
            "type": "error",
            "data": "Une erreur interne est survenue sur le serveur."
        }
        try:
            await websocket.send_json(error_payload)
        except Exception:
            pass # Le client est peut-être déjà parti
    finally:
        if websocket.client_state != "DISCONNECTED":
            await websocket.close()
            logger.info(f"Connexion WebSocket proprement fermée pour la session {session_id}.")

