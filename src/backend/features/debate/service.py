# src/backend/features/debate/service.py
# V15.0 - DEBUG CONTEXT + OFF ISOLATION + STRICT ROLE ISOLATION + P1.5-b (persistance synthèse)

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

# 🔗 Threads
from backend.features.threads.service import ThreadsService
from backend.features.threads.schemas import MessageCreate

logger = logging.getLogger(__name__)

class DebateService:
    """
    DebateService V15.0
    - DEBUG: ws:debug_context (scope='debate')
    - OFF ISOLATION: EMERGENCE_DEBATE_OFF_POLICY (full_transcript / round_local / stateless)
    - RAG: si use_rag=True, policy forcée à 'full_transcript'
    - ✅ P1.5-b: persistance de la synthèse finale dans un thread lié à la session
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

        self._threads = ThreadsService()

        logger.info(f"DebateService V15.0 initialisé. OFF policy={self.off_policy}, round_local_n={self.round_local_n}")

    def _normalize_llm_result(self, result):
        try:
            if isinstance(result, tuple) and len(result) == 2:
                text, meta = result
                return (text or "", meta or {})
            if isinstance(result, dict):
                text = result.get("text") or result.get("content") or result.get("message") or result.get("output") or result.get("response") or ""
                return (text, result)
            if isinstance(result, str):
                return (result, {})
        except Exception:
            pass
        return (str(result), {})

    async def _call_llm(self, *, agent_id: str, history: list, session_id: str):
        try:
            method = getattr(self.chat_service, "get_llm_response_for_debate")
            result = await method(agent_id=agent_id, history=history, session_id=session_id)
            return self._normalize_llm_result(result)
        except AttributeError:
            pass
        try:
            method = getattr(self.chat_service, "get_llm_response")
            try:
                result = await method(agent_id=agent_id, history=history, session_id=session_id, mode="debate")
            except TypeError:
                result = await method(agent_id=agent_id, history=history, session_id=session_id)
            return self._normalize_llm_result(result)
        except AttributeError:
            pass
        for alt in ("chat", "generate_response", "generate", "ask"):
            try:
                method = getattr(self.chat_service, alt)
            except AttributeError:
                continue
            result = await method(agent_id=agent_id, history=history, session_id=session_id)
            return self._normalize_llm_result(result)
        raise AttributeError("ChatService: aucune méthode compatible trouvée (get_llm_response_for_debate / get_llm_response / chat / generate_response / generate / ask).")

    # ---------- utilitaires ----------
    def _extract_sensitive_tokens(self, text: str) -> List[str]:
        return re.findall(r"\b[A-Z]{3,}-\d{3,}\b", text or "")

    def _sanitize_agent_output(self, agent_id: str, text: str, synthesizer_id: str) -> str:
        if not text:
            return text
        known = {"anima", "neo", "nexus"}
        agent_id_l = (agent_id or "").lower()
        other_agents = [a for a in known if a != agent_id_l]

        cleaned = text
        for other in other_agents:
            cleaned = re.sub(
                rf"(?mis)(^|\n)\s*\*\*\s*{other}\s+a dit\s*:?\s*\*\*\s*\n(?:\s*>.*\n?)+",
                "\n",
                cleaned
            )
            cleaned = re.sub(
                rf"(?mis)^\s*#{1,6}\s*Intervention\s+de\s+{other}\s*\n.*?(?=^\s*#{1,6}\s|\Z)",
                "",
                cleaned
            )
            cleaned = re.sub(rf"(?mi)^\s*{other}\s*:\s*", "", cleaned)

        if agent_id_l != (synthesizer_id or "").lower():
            cleaned = re.sub(r"(?mi)^\s*#{1,6}\s*Synth[èe]se.*(?:\n.*)*", "", cleaned)
        return cleaned.strip()

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

    def _resolve_synthesizer(self, session: DebateSession) -> str:
        proposed = (session.config.agent_order[-1] or "").lower()
        if proposed != "nexus":
            return proposed
        gemini_key = (os.getenv("GEMINI_API_KEY", "") or "").strip().lower()
        if gemini_key and gemini_key not in {"dummy", "test", "placeholder", "xxx"}:
            return "nexus"
        participants = [a.lower() for a in session.config.agent_order[:-1]]
        fallback = "neo" if "neo" not in participants else "anima"
        logger.warning(f"[Debate] GEMINI_API_KEY absente/invalide. Fallback synthèse: {fallback} au lieu de 'nexus'.")
        return fallback

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
                f"apporte ta contribution au débat. Sois pertinent, concis et fais avancer la discussion.\n\n"
                f"RÈGLES D'ISOLATION (OBLIGATOIRES) :\n"
                f"- Tu parles uniquement au nom de {agent_id}. N'invente JAMAIS de répliques attribuées à d'autres agents.\n"
                f"- Référence aux autres en style indirect uniquement.\n"
                f"- Pas d'en-têtes \"Intervention de ...\" ni de section \"Synthèse\".\n"
                f"- Ne préfixe PAS ta sortie par ton nom/role. Réponds en un seul bloc de texte."
            )
            structured_history = [{"role": "user", "content": prompt_for_agent}]

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

            try:
                response_text, _ = await self._call_llm(agent_id=agent_id, history=structured_history, session_id=session.session_id)
            except Exception as e:
                logger.error(f"[Debate] Tour {round_number} — échec appel LLM pour {agent_id}: {e}", exc_info=True)
                response_text = "_(Réponse non disponible pour des raisons techniques.)_"

            response_text = self._sanitize_agent_output(agent_id, response_text, session.config.agent_order[-1])
            current_turn.agent_responses[agent_id] = response_text

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

        synthesizer_id = self._resolve_synthesizer(session)
        final_transcript = self._build_full_transcript(session, with_header=False, policy="full_transcript")

        prompt_content = (
            f"Le débat sur le sujet \"{session.config.topic}\" est terminé. Voici le transcript complet des échanges:\n\n"
            f"--- DÉBUT DU TRANSCRIPT ---\n{final_transcript}\n--- FIN DU TRANSCRIPT ---\n\n"
            f"## Ta Mission de Synthèse ({synthesizer_id}):\n"
            "1. **Points de Convergence**\n2. **Points de Divergence**\n3. **Idée Émergente**\n4. **Conclusion**\n"
            "Structure ta réponse avec ces quatre points. Sois analytique, profond et concis."
        )
        structured_history = [{"role": "user", "content": prompt_content}]
        
        try:
            response_text, _ = await self._call_llm(agent_id=synthesizer_id, history=structured_history, session_id=session.session_id)
            session.synthesis = response_text
            logger.info(f"Synthèse générée par {synthesizer_id}.")
        except Exception as e:
            logger.error(f"[Debate] Échec synthèse via {synthesizer_id}: {e}", exc_info=True)
            session.synthesis = "_Synthèse indisponible pour raisons techniques._"

        # ✅ Nouveau — Persistance de la synthèse dans un thread lié à la session
        try:
            # user_id via SessionManager (mêmes patterns que côté chat)
            user_id = None
            try:
                if hasattr(self.session_manager, "get_session"):
                    s = self.session_manager.get_session(session.session_id)  # type: ignore[attr-defined]
                elif hasattr(self.session_manager, "get"):
                    s = self.session_manager.get(session.session_id)  # type: ignore[attr-defined]
                else:
                    s = None
                if s:
                    if isinstance(s, dict):
                        user_id = s.get("user_id") or (s.get("user") or {}).get("id")
                    else:
                        user_id = getattr(s, "user_id", None) or getattr(getattr(s, "user", None), "id", None)
            except Exception:
                pass

            if not user_id:
                for fn in ("get_user_id", "get_session_user_id"):
                    try:
                        if hasattr(self.session_manager, fn):
                            user_id = getattr(self.session_manager, fn)(session.session_id)  # type: ignore[misc]
                            if user_id:
                                break
                    except Exception:
                        continue

            if user_id:
                threads = ThreadsService()
                tid = await threads.ensure_session_thread(
                    user_id=user_id, session_id=session.session_id, title=f"Débat: {session.config.topic}"
                )
                msg = MessageCreate(role="assistant", content=session.synthesis or "", agent=synthesizer_id, model=None, rag_sources=None)
                await threads.add_message(user_id=user_id, thread_id=tid, msg=msg)
            else:
                logger.warning("[Debate/Threads] user_id introuvable pour session %s — persistance synthèse sautée.", session.session_id)
        except Exception as e:
            logger.warning("[Debate/Threads] Persistance synthèse sautée: %s", e)
