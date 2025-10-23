# src/backend/core/ws/handlers/handshake.py
"""
WebSocket Handshake Handler - Agent context synchronization protocol

Gère le protocole HELLO/ACK/SYNC entre agents et clients WebSocket.
Assure la cohérence du contexte mémoire agent-spécifique.

Flux du protocole:
1. Agent → Client: HELLO (annonce contexte)
2. Client → Agent: ACK (confirmation)
3. Agent → Client: SYNC (synchronisation si nécessaire)
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class HandshakeHandler:
    """
    Gestionnaire du protocole de handshake agent↔client.

    Assure que le client frontend et l'agent backend sont synchronisés
    sur le même contexte mémoire.
    """

    def __init__(self, memory_sync_manager):
        """
        Args:
            memory_sync_manager: Instance de MemorySyncManager
        """
        self.memory_sync = memory_sync_manager

    async def send_hello(
        self,
        connection_manager: Any,
        session_id: str,
        agent_id: str,
        model: str,
        provider: str,
        user_id: str
    ) -> None:
        """
        Envoie un message HELLO au client pour annoncer le contexte agent.

        Args:
            connection_manager: Gestionnaire de connexions WS
            session_id: ID de session WebSocket
            agent_id: ID de l'agent (anima, neo, nexus)
            model: Modèle LLM utilisé
            provider: Provider (google, openai, anthropic)
            user_id: ID utilisateur
        """
        try:
            # Créer ou récupérer le contexte agent
            context = self.memory_sync.create_agent_context(
                agent_id=agent_id,
                user_id=user_id,
                session_id=session_id
            )

            # Construire le payload HELLO
            hello_payload = self.memory_sync.build_hello_payload(
                context=context,
                model=model,
                provider=provider
            )

            # Envoyer via WebSocket
            await connection_manager.send_to_session(
                session_id=session_id,
                message={
                    "type": "ws:handshake_hello",
                    "payload": hello_payload
                }
            )

            logger.debug(
                f"[Handshake] HELLO sent → {agent_id} "
                f"({context.context_id}/{context.context_rev})"
            )

        except Exception as e:
            logger.error(f"[Handshake] Error sending HELLO: {e}", exc_info=True)

    async def handle_ack(
        self,
        session_id: str,
        payload: Dict[str, Any]
    ) -> Optional[str]:
        """
        Traite un message ACK du client.

        Args:
            session_id: ID session
            payload: Payload ACK du client

        Returns:
            Status de synchronisation ("ok", "desync", "stale")
        """
        try:
            agent_id = payload.get("agent_id", "").lower()
            client_rev = payload.get("context_rev", "")
            user_id = payload.get("user_id", "")

            if not agent_id or not user_id:
                logger.warning("[Handshake] ACK missing agent_id or user_id")
                return "error"

            # Récupérer le contexte serveur
            server_context = self.memory_sync.get_agent_context(agent_id, user_id)

            if not server_context:
                logger.warning(f"[Handshake] No server context for {agent_id}")
                return "stale"

            # Vérifier la révision
            if client_rev != server_context.context_rev:
                logger.info(
                    f"[Handshake] Context desync detected: "
                    f"client={client_rev}, server={server_context.context_rev}"
                )
                return "desync"

            logger.debug(f"[Handshake] ACK received from {agent_id} → sync OK")
            return "ok"

        except Exception as e:
            logger.error(f"[Handshake] Error handling ACK: {e}", exc_info=True)
            return "error"

    async def send_sync_if_needed(
        self,
        connection_manager: Any,
        session_id: str,
        agent_id: str,
        user_id: str,
        sync_status: str
    ) -> None:
        """
        Envoie un message SYNC si le client est désynchronisé.

        Args:
            connection_manager: Gestionnaire connexions WS
            session_id: ID session
            agent_id: ID agent
            user_id: ID utilisateur
            sync_status: Résultat du ACK ("ok", "desync", "stale")
        """
        if sync_status == "ok":
            return

        try:
            context = self.memory_sync.get_agent_context(agent_id, user_id)

            if not context:
                logger.warning(f"[Handshake] No context for SYNC: {agent_id}")
                return

            # TODO: Récupérer les items STM/LTM depuis ChromaDB
            # Pour l'instant, on envoie juste les compteurs
            sync_payload = {
                "type": "SYNC",
                "agent_id": context.agent_id,
                "context_id": context.context_id,
                "context_rev": context.context_rev,
                "memory_stats": {
                    "stm": context.stm_count,
                    "ltm": context.ltm_count
                },
                "status": sync_status,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

            await connection_manager.send_to_session(
                session_id=session_id,
                message={
                    "type": "ws:handshake_sync",
                    "payload": sync_payload
                }
            )

            logger.info(
                f"[Handshake] SYNC sent → {agent_id} "
                f"(status: {sync_status}, rev: {context.context_rev})"
            )

        except Exception as e:
            logger.error(f"[Handshake] Error sending SYNC: {e}", exc_info=True)

    async def handle_client_hello(
        self,
        connection_manager: Any,
        session_id: str,
        payload: Dict[str, Any]
    ) -> None:
        """
        Traite un HELLO venant du client (rare, mais possible).

        Args:
            connection_manager: Gestionnaire WS
            session_id: ID session
            payload: Payload HELLO du client
        """
        try:
            agent_id = payload.get("agent_id", "").lower()
            user_id = payload.get("user_id", "")

            if not agent_id or not user_id:
                logger.warning("[Handshake] Client HELLO missing required fields")
                return

            # Récupérer le contexte serveur
            context = self.memory_sync.get_agent_context(agent_id, user_id)

            if not context:
                # Créer un nouveau contexte
                context = self.memory_sync.create_agent_context(
                    agent_id=agent_id,
                    user_id=user_id,
                    session_id=session_id
                )

            # Envoyer ACK
            ack_payload = self.memory_sync.build_ack_payload(
                context=context,
                sync_status="ok"
            )

            await connection_manager.send_to_session(
                session_id=session_id,
                message={
                    "type": "ws:handshake_ack",
                    "payload": ack_payload
                }
            )

            logger.debug(f"[Handshake] ACK sent in response to client HELLO: {agent_id}")

        except Exception as e:
            logger.error(f"[Handshake] Error handling client HELLO: {e}", exc_info=True)
