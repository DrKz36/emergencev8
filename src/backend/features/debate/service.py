# src/backend/features/debate/service.py
# V12.0 - FIX: Utilisation de send_personal_message au lieu de broadcast.
import asyncio
import logging
from typing import Dict, Any, List
from uuid import uuid4
from pydantic import ValidationError

from backend.core.session_manager import SessionManager
from backend.core.websocket import ConnectionManager
from backend.features.chat.service import ChatService
from backend.features.memory.vector_service import VectorService
from backend.shared.config import Settings
from backend.core import config as core_config
from .models import DebateConfig, DebateSession, DebateTurn, DebateStatus

logger = logging.getLogger(__name__)

class DebateService:
    """
    DebateService V12.0
    - FIX: Appelle la méthode de communication WebSocket correcte.
    - CONTEXTE CUMULATIF: Les agents reçoivent désormais l'intégralité du transcript précédent.
    - INTÉGRATION RAG: Peut utiliser un contexte documentaire pour ancrer le débat.
    """
    def __init__(
        self,
        chat_service: ChatService,
        connection_manager: ConnectionManager,
        session_manager: SessionManager,
        vector_service: VectorService,
        settings: Settings
    ):
        self.active_debates: Dict[str, DebateSession] = {}
        self.chat_service = chat_service
        self.connection_manager = connection_manager
        self.session_manager = session_manager
        self.vector_service = vector_service
        self.settings = settings
        logger.info("DebateService V12.0 (FIX WebSocket) initialisé.")

    async def create_debate(self, config: Dict[str, Any], session_id: str):
        debate_id = f"debate_{uuid4().hex[:8]}"
        try:
            debate_config = DebateConfig(**config)
            debate_session = DebateSession(
                debate_id=debate_id, session_id=session_id,
                config=debate_config, status=DebateStatus.PENDING
            )
            self.active_debates[debate_id] = debate_session
            
            logger.info(f"Débat {debate_id} créé sur le sujet : '{debate_config.topic}'. RAG activé: {debate_config.use_rag}")
            
            asyncio.create_task(self._run_debate_flow(debate_id))

        except ValidationError as e:
            logger.error(f"Erreur de configuration du débat: {e}", exc_info=True)
            await self.connection_manager.send_personal_message({
                "type": "ws:error",
                "payload": {"message": f"Configuration du débat invalide: {e}"}
            }, session_id)
        except Exception as e:
            logger.error(f"Erreur inattendue lors de la création du débat {debate_id}: {e}", exc_info=True)
            if debate_id in self.active_debates:
                del self.active_debates[debate_id]
            await self.connection_manager.send_personal_message({
                "type": "ws:error",
                "payload": {"message": "Erreur serveur interne lors de la création du débat."}
            }, session_id)

    def _build_full_transcript(self, session: DebateSession, with_header: bool = True) -> str:
        transcript_parts = []
        
        if with_header:
            transcript_parts.append(f"Le sujet du débat est : \"{session.config.topic}\"")
            if session.rag_context:
                transcript_parts.append(f"\n--- CONTEXTE DOCUMENTAIRE ---\n{session.rag_context}\n---------------------------\n")

        for turn in session.history:
            transcript_parts.append(f"\n### TOUR DE TABLE N°{turn.round_number} ###")
            for agent_name, response in turn.agent_responses.items():
                transcript_parts.append(f"\n**{agent_name} a dit :**\n> {response}")
        
        return "\n".join(transcript_parts)

    async def _run_debate_flow(self, debate_id: str):
        session = self.active_debates.get(debate_id)
        if not session:
            logger.error(f"Tentative de lancement d'un débat inexistant: {debate_id}")
            return

        try:
            session.status = DebateStatus.IN_PROGRESS
            # FIX V12.0: Utilisation de send_personal_message avec le session_id.
            await self.connection_manager.send_personal_message(
                {"type": "ws:debate_started", "payload": session.model_dump(mode='json')},
                session.session_id
            )

            if session.config.use_rag:
                logger.info(f"Débat {debate_id}: Recherche RAG en cours pour le sujet.")
                await self.connection_manager.send_personal_message({"type": "ws:debate_status_update", "payload": {"debate_id": debate_id, "status": "Recherche RAG..."}}, session.session_id)
                document_collection = self.vector_service.get_or_create_collection(core_config.DOCUMENT_COLLECTION_NAME)
                search_results = self.vector_service.query(collection=document_collection, query_text=session.config.topic)
                session.rag_context = "\n\n".join([f"Source {i+1}:\n{result['text']}" for i, result in enumerate(search_results)])
                logger.info(f"Débat {debate_id}: {len(search_results)} fragments de contexte trouvés.")

            for i in range(session.config.rounds):
                round_number = i + 1
                await self._run_debate_round(session, round_number)

            await self._generate_synthesis(session)

            session.status = DebateStatus.COMPLETED
            logger.info(f"Débat {debate_id} terminé avec succès.")

        except Exception as e:
            session.status = DebateStatus.FAILED
            logger.error(f"Le déroulement du débat {debate_id} a échoué: {e}", exc_info=True)
            await self.connection_manager.send_personal_message({
                "type": "ws:error",
                "payload": {"message": f"Le débat '{session.config.topic}' a rencontré une erreur et a été interrompu."}
            }, session.session_id)
        finally:
            # FIX V12.0: Utilisation de send_personal_message avec le session_id.
            await self.connection_manager.send_personal_message(
                {"type": "ws:debate_ended", "payload": session.model_dump(mode='json')},
                session.session_id
            )
            
            update_data = {"metadata": {"debate": session.model_dump(mode='json')}}
            await self.session_manager.update_and_save_session(session.session_id, update_data)
            
            if debate_id in self.active_debates:
                del self.active_debates[debate_id]
            logger.info(f"Débat {debate_id} archivé et nettoyé de la mémoire active.")

    async def _run_debate_round(self, session: DebateSession, round_number: int):
        logger.info(f"Débat {session.debate_id}: Démarrage du Tour {round_number}.")
        await self.connection_manager.send_personal_message({"type": "ws:debate_status_update", "payload": {"debate_id": session.debate_id, "status": f"Tour {round_number} en cours..."}}, session.session_id)
        
        current_turn = DebateTurn(round_number=round_number)
        session.history.append(current_turn)

        agents_in_round = session.config.agent_order[:-1]

        for agent_id in agents_in_round:
            logger.info(f"Tour {round_number}: Au tour de {agent_id}.")
            
            transcript = self._build_full_transcript(session)
            
            prompt_for_agent = (
                f"{transcript}\n\n---\n"
                f"**INSTRUCTION POUR {agent_id.upper()} :**\n"
                f"C'est à ton tour de parler. En te basant sur l'intégralité des échanges ci-dessus, apporte ta contribution au débat. "
                f"Sois pertinent, concis et fais avancer la discussion."
            )
            
            structured_history = [{"role": "user", "content": prompt_for_agent}]
            
            response_text, _ = await self.chat_service.get_llm_response_for_debate(
                agent_id=agent_id,
                history=structured_history,
                session_id=session.session_id
            )
            
            current_turn.agent_responses[agent_id] = response_text
            # FIX V12.0: Utilisation de send_personal_message avec le session_id.
            await self.connection_manager.send_personal_message(
                {"type": "ws:debate_turn_update", "payload": session.model_dump(mode='json')},
                session.session_id
            )
            await asyncio.sleep(1)

    async def _generate_synthesis(self, session: DebateSession):
        logger.info(f"Génération de la synthèse pour le débat {session.debate_id}...")
        await self.connection_manager.send_personal_message({"type": "ws:debate_status_update", "payload": {"debate_id": session.debate_id, "status": "Génération de la synthèse..."}}, session.session_id)
        
        synthesizer_id = session.config.agent_order[-1] 
        
        final_transcript = self._build_full_transcript(session, with_header=False)

        prompt_content = (
            f"Le débat sur le sujet \"{session.config.topic}\" est terminé. Voici le transcript complet des échanges:\n\n"
            f"--- DÉBUT DU TRANSCRIPT ---\n{final_transcript}\n--- FIN DU TRANSCRIPT ---\n\n"
            f"## Ta Mission de Synthèse ({synthesizer_id}):\n"
            "Tu n'es pas un simple rapporteur. Ton rôle est d'analyser en profondeur la trajectoire de la discussion. Ta synthèse doit inclure :\n"
            "1.  **Points de Convergence :** Sur quels points les agents se sont-ils tacitement ou explicitement accordés ?\n"
            "2.  **Points de Divergence :** Quelle est la tension fondamentale ou le désaccord principal qui a émergé ?\n"
            "3.  **Idée Émergente :** Quelle est LA grande idée, la perspective nouvelle ou la question la plus intéressante qui a surgi de cette confrontation ?\n"
            "4.  **Conclusion :** Propose une conclusion percutante qui capture l'essence du débat.\n\n"
            "Structure ta réponse avec ces quatre points. Sois analytique, profond et concis."
        )

        structured_history = [{"role": "user", "content": prompt_content}]
        
        response_text, _ = await self.chat_service.get_llm_response_for_debate(
            agent_id=synthesizer_id,
            history=structured_history,
            session_id=session.session_id
        )

        session.synthesis = response_text
        logger.info(f"Synthèse générée par {synthesizer_id}.")
