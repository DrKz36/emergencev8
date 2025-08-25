# src/backend/features/debate/service.py
# V13.1 - PROMPT WIRING + 5-POINTS SYNTH + RAG PASSTHROUGH
import os
import re
import asyncio
import logging
from typing import Dict, Any, List, Optional
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
    DebateService V13.1
    - DEBUG: envoie 'ws:debug_context' (scope='debate') avant/après chaque appel agent.
    - OFF ISOLATION: contrôle du transcript quand use_rag=False via EMERGENCE_DEBATE_OFF_POLICY.
        * full_transcript (défaut) : historique complet.
        * round_local : round courant (+ N précédents optionnels).
        * stateless : aucun transcript.
    - RAG: si use_rag=True, rag_context est injecté et la policy est forcée à 'full_transcript'.
    - FIX: passage explicite du 'prompt' au ChatService (au lieu de 'history').
    - FIX: synthèse en 5 points (Faits, Convergences, Désaccords, Angles morts, Pistes) alignée avec l’UI.
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

        policy = os.getenv("EMERGENCE_DEBATE_OFF_POLICY", "full_transcript").strip().lower()
        if policy not in ("full_transcript", "round_local", "stateless"):
            policy = "full_transcript"
        self.off_policy = policy

        try:
            self.round_local_n = max(0, int(os.getenv("EMERGENCE_DEBATE_ROUND_LOCAL_N", "0")))
        except ValueError:
            self.round_local_n = 0

        logger.info(f"DebateService V13.1 initialisé. OFF policy={self.off_policy}, round_local_n={self.round_local_n}")

    # ---------- utilitaires ----------
    def _extract_sensitive_tokens(self, text: str) -> List[str]:
        return re.findall(r"\b[A-Z]{3,}-\d{3,}\b", text or "")

    def _policy_for_session(self, session: DebateSession) -> str:
        return "full_transcript" if session.config.use_rag else self.off_policy

    def _build_full_transcript(
        self,
        session: DebateSession,
        with_header: bool = True,
        policy: Optional[str] = None
    ) -> str:
        policy = policy or self._policy_for_session(session)
        parts: List[str] = []

        if with_header:
            parts.append(f"Le sujet du débat est : \"{session.config.topic}\"")
            if session.rag_context:
                parts.append(f"\n--- CONTEXTE DOCUMENTAIRE ---\n{session.rag_context}\n---------------------------\n")

        if policy == "stateless":
            return "\n".join(parts)

        history = session.history

        if policy == "full_transcript":
            for turn in history:
                parts.append(f"\n### TOUR DE TABLE N°{turn.round_number} ###")
                for agent_name, response in turn.agent_responses.items():
                    parts.append(f"\n**{agent_name} a dit :**\n> {response}")
            return "\n".join(parts)

        if not history:
            return "\n".join(parts)

        if self.round_local_n > 0:
            prev_completed = [t for t in history if len(t.agent_responses) > 0][:-1]
            for t in prev_completed[-self.round_local_n:]:
                parts.append(f"\n### TOUR DE TABLE N°{t.round_number} (récap) ###")
                for agent_name, response in t.agent_responses.items():
                    parts.append(f"\n**{agent_name} a dit :**\n> {response}")

        current = history[-1]
        if current.agent_responses:
            parts.append(f"\n### TOUR DE TABLE N°{current.round_number} (en cours) ###")
            for agent_name, response in current.agent_responses.items():
                parts.append(f"\n**{agent_name} a dit :**\n> {response}")

        return "\n".join(parts)

    # ---------- flux principal ----------
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

    async def _run_debate_flow(self, debate_id: str):
        session = self.active_debates.get(debate_id)
        if not session:
            logger.error(f"Tentative de lancement d'un débat inexistant: {debate_id}")
            return

        try:
            session.status = DebateStatus.IN_PROGRESS
            await self.connection_manager.send_personal_message(
                {"type": "ws:debate_started", "payload": session.model_dump(mode='json')},
                session.session_id
            )

            if session.config.use_rag:
                logger.info(f"Débat {debate_id}: Recherche RAG en cours pour le sujet.")
                await self.connection_manager.send_personal_message(
                    {"type": "ws:debate_status_update", "payload": {"debate_id": debate_id, "status": "Recherche RAG..."}},
                    session.session_id
                )
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
        await self.connection_manager.send_personal_message(
            {"type": "ws:debate_status_update", "payload": {"debate_id": session.debate_id, "status": f"Tour {round_number} en cours..."}},
            session.session_id
        )

        current_turn = DebateTurn(round_number=round_number)
        session.history.append(current_turn)

        agents_in_round = session.config.agent_order[:-1]
        policy = self._policy_for_session(session)

        for agent_id in agents_in_round:
            logger.info(f"Tour {round_number}: Au tour de {agent_id} (policy={policy}).")

            transcript = self._build_full_transcript(session, with_header=True, policy=policy)
            prompt_for_agent = (
                f"{transcript}\n\n---\n"
                f"**INSTRUCTION POUR {agent_id.upper()} :**\n"
                f"C'est à ton tour de parler. En te basant sur l'intégralité des éléments ci-dessus (policy={policy}), "
                f"apporte ta contribution au débat. Sois pertinent, concis et fais avancer la discussion."
            )

            # DEBUG (avant appel)
            sens_in_prompt = list(set(self._extract_sensitive_tokens(prompt_for_agent)))
            await self.connection_manager.send_personal_message({
                "type": "ws:debug_context",
                "payload": {
                    "scope": "debate",
                    "phase": "before_agent_call",
                    "debate_id": session.debate_id,
                    "round_number": round_number,
                    "agent_id": agent_id,
                    "use_rag": session.config.use_rag,
                    "policy": policy,
                    "transcript_chars": len(transcript),
                    "rag_context_chars": len(session.rag_context or ""),
                    "sensitive_tokens_in_prompt": sens_in_prompt,
                }
            }, session.session_id)

            # ✅ FIX: passage explicite du prompt + RAG passthrough
            response_text, _ = await self.chat_service.get_llm_response_for_debate(
                agent_id=agent_id,
                prompt=prompt_for_agent,
                rag_context=session.rag_context or "",
                use_rag=session.config.use_rag,
                session_id=session.session_id,
            )

            current_turn.agent_responses[agent_id] = response_text

            # DEBUG (après appel)
            sens_in_resp = list(set(self._extract_sensitive_tokens(response_text)))
            await self.connection_manager.send_personal_message({
                "type": "ws:debug_context",
                "payload": {
                    "scope": "debate",
                    "phase": "after_agent_call",
                    "debate_id": session.debate_id,
                    "round_number": round_number,
                    "agent_id": agent_id,
                    "use_rag": session.config.use_rag,
                    "policy": policy,
                    "response_chars": len(response_text or ""),
                    "sensitive_tokens_in_response": sens_in_resp,
                }
            }, session.session_id)

            await self.connection_manager.send_personal_message(
                {"type": "ws:debate_turn_update", "payload": session.model_dump(mode='json')},
                session.session_id
            )
            await asyncio.sleep(1)

    async def _generate_synthesis(self, session: DebateSession):
        logger.info(f"Génération de la synthèse pour le débat {session.debate_id}...")
        await self.connection_manager.send_personal_message(
            {"type": "ws:debate_status_update", "payload": {"debate_id": session.debate_id, "status": "Génération de la synthèse..."}},
            session.session_id
        )

        synthesizer_id = session.config.agent_order[-1]
        # Transcript complet pour la synthèse
        final_transcript = self._build_full_transcript(session, with_header=False, policy="full_transcript")

        # ✅ Alignement 5 points (Faits/Convergences/Désaccords/Angles morts/Pistes)
        prompt_content = (
            f"Le débat sur \"{session.config.topic}\" est terminé. Transcript complet ci-dessous :\n\n"
            f"--- DÉBUT DU TRANSCRIPT ---\n{final_transcript}\n--- FIN DU TRANSCRIPT ---\n\n"
            f"## Mission ({synthesizer_id}) — Synthèse en 5 points :\n"
            f"1) Faits clés documentés\n2) Convergences\n3) Désaccords\n4) Angles morts\n5) Pistes à explorer\n\n"
            "Réponds de manière directe et compacte, en français, sans méta-commentaires."
        )

        response_text, _ = await self.chat_service.get_llm_response_for_debate(
            agent_id=synthesizer_id,
            prompt=prompt_content,                 # ✅ FIX: prompt explicite
            rag_context=session.rag_context or "", # ✅ RAG passthrough
            use_rag=session.config.use_rag,
            session_id=session.session_id,
        )
        session.synthesis = response_text
        logger.info(f"Synthèse générée par {synthesizer_id}.")
