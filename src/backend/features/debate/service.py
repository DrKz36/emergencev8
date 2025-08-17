# src/backend/features/debate/service.py
# V14.0 - DEBUG CONTEXT + OFF ISOLATION (full_transcript | round_local | stateless) + STRICT ROLE ISOLATION
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
    DebateService V13.0
    - DEBUG: envoie 'ws:debug_context' (scope='debate') avant/après chaque appel agent.
    - OFF ISOLATION: contrôle du transcript quand use_rag=False via EMERGENCE_DEBATE_OFF_POLICY.
        * full_transcript (défaut) : historique complet (comportement précédent).
        * round_local : uniquement le round courant (+ N rounds précédents optionnels).
        * stateless : aucun transcript (isolation maximale).
    - RAG: si use_rag=True, rag_context est injecté et la policy est forcée à 'full_transcript'.
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

        # Politique d'historique OFF (quand use_rag=False)
        policy = os.getenv("EMERGENCE_DEBATE_OFF_POLICY", "full_transcript").strip().lower()
        if policy not in ("full_transcript", "round_local", "stateless"):
            policy = "full_transcript"
        self.off_policy = policy

        # Pour round_local: nombre de rounds complets précédents à inclure
        try:
            self.round_local_n = max(0, int(os.getenv("EMERGENCE_DEBATE_ROUND_LOCAL_N", "0")))
        except ValueError:
            self.round_local_n = 0

        logger.info(f"DebateService V13.0 initialisé. OFF policy={self.off_policy}, round_local_n={self.round_local_n}")

    # ---------- utilitaires ----------
    def _extract_sensitive_tokens(self, text: str) -> List[str]:
        """Détecte des patterns de type AZUR-8152 / ONYX-4472."""
        return re.findall(r"\b[A-Z]{3,}-\d{3,}\b", text or "")

    def _sanitize_agent_output(self, agent_id: str, text: str, synthesizer_id: str) -> str:
        """
        STRICT ROLE ISOLATION:
        - Empêche un agent d'écrire au nom d'un autre (ex: "**neo a dit :** ...").
        - Supprime les en-têtes "Intervention de <agent>" dans les tours.
        - Empêche la production d'une "Synthèse" par un agent qui n'est pas le médiateur.
        """
        if not text:
            return text

        known = {"anima", "neo", "nexus"}
        agent_id_l = (agent_id or "").lower()
        other_agents = [a for a in known if a != agent_id_l]
        cleaned = text

        for other in other_agents:
            # Bloc du type: **neo a dit :** + blockquotes suivants
            cleaned = re.sub(
                rf"(?mis)(^|\n)\s*\*\*\s*{other}\s+a dit\s*:?\s*\*\*\s*\n(?:\s*>.*\n?)+",
                "\n",
                cleaned
            )
            # En-tête 'Intervention de other' + paragraphe/blockquote suivant
            cleaned = re.sub(
                rf"(?mis)^\s*#{1,6}\s*Intervention\s+de\s+{other}\s*\n.*?(?=^\s*#{1,6}\s|\Z)",
                "",
                cleaned
            )
            # Préfixe 'other:' en début de ligne
            cleaned = re.sub(
                rf"(?mi)^\s*{other}\s*:\s*",
                "",
                cleaned
            )

        # Empêcher la "Synthèse" côté non-synthétiseur
        if agent_id_l != (synthesizer_id or "").lower():
            cleaned = re.sub(r"(?mi)^\s*#{1,6}\s*Synth[èe]se.*(?:\n.*)*", "", cleaned)

        return cleaned.strip()

    def _policy_for_session(self, session: DebateSession) -> str:
        """Si RAG ON, on garde le transcript complet pour la cohérence du débat."""
        return "full_transcript" if session.config.use_rag else self.off_policy

    def _build_full_transcript(
        self,
        session: DebateSession,
        with_header: bool = True,
        policy: Optional[str] = None
    ) -> str:
        """
        Construit le transcript selon la policy.
        - full_transcript : comportement historique (tous les tours).
        - round_local : réponses déjà données dans le round en cours + N rounds complets précédents.
        - stateless : aucun contenu d'historique.
        """
        policy = policy or self._policy_for_session(session)
        parts: List[str] = []

        if with_header:
            parts.append(f"Le sujet du débat est : \"{session.config.topic}\"")
            if session.rag_context:
                parts.append(f"\n--- CONTEXTE DOCUMENTAIRE ---\n{session.rag_context}\n---------------------------\n")

        # STATLESS: pas d'historique
        if policy == "stateless":
            return "\n".join(parts)

        history = session.history

        # FULL TRANSCRIPT: tout l'historique
        if policy == "full_transcript":
            for turn in history:
                parts.append(f"\n### TOUR DE TABLE N°{turn.round_number} ###")
                for agent_name, response in turn.agent_responses.items():
                    parts.append(f"\n**{agent_name} a dit :**\n> {response}")
            return "\n".join(parts)

        # ROUND LOCAL: round courant + N rounds précédents
        if not history:
            return "\n".join(parts)

        # rounds précédents (complets), en conservant l'ordre
        if self.round_local_n > 0:
            prev_completed = [t for t in history if len(t.agent_responses) > 0][:-1]
            for t in prev_completed[-self.round_local_n:]:
                parts.append(f"\n### TOUR DE TABLE N°{t.round_number} (récap) ###")
                for agent_name, response in t.agent_responses.items():
                    parts.append(f"\n**{agent_name} a dit :**\n> {response}")

        # round en cours (réponses déjà données)
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
                f"C'est à ton tour de parler. En te basant sur l'intégralité des éléments ci-dessus (selon policy={policy}), "
                f"apporte ta contribution au débat. Sois pertinent, concis et fais avancer la discussion.\n\n"
                f"RÈGLES D'ISOLATION (OBLIGATOIRES) :\n"
                f"- Tu parles uniquement au nom de {agent_id}. N'invente JAMAIS de répliques attribuées à d'autres agents (ex: \"**neo a dit :**\").\n"
                f"- Tu peux faire référence aux idées DES AUTRES uniquement en style indirect (ex: \"Comme Neo le suggère...\").\n"
                f"- N'écris pas d'en-têtes comme \"Intervention de ...\" ni de section \"Synthèse\".\n"
                f"- Ne préfixe PAS ta sortie par ton nom/role. Réponds en un seul bloc de texte."
            )
            structured_history = [{"role": "user", "content": prompt_for_agent}]

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

            response_text, _ = await self.chat_service.get_llm_response_for_debate(
                agent_id=agent_id,
                history=structured_history,
                session_id=session.session_id
            )
            
            response_text = self._sanitize_agent_output(agent_id, response_text, session.config.agent_order[-1])
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
        # Pour la synthèse, on garde toujours le transcript complet.
        final_transcript = self._build_full_transcript(session, with_header=False, policy="full_transcript")

        prompt_content = (
            f"Le débat sur le sujet \"{session.config.topic}\" est terminé. Voici le transcript complet des échanges:\n\n"
            f"--- DÉBUT DU TRANSCRIPT ---\n{final_transcript}\n--- FIN DU TRANSCRIPT ---\n\n"
            f"## Ta Mission de Synthèse ({synthesizer_id}):\n"
            "1. **Points de Convergence**\n2. **Points de Divergence**\n3. **Idée Émergente**\n4. **Conclusion**\n"
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
