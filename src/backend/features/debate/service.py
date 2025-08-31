# src/backend/features/debate/service.py
# V16.0 — History agrégée par tour + frames statutées + résultat final renvoyé (WS final émis par le chat.router)
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("backend.features.debate.service")

class DebateService:
    def __init__(
        self,
        settings: Any,
        chat_service: Any,
        session_manager: Any,
        vector_service: Optional[Any] = None,
        connection_manager: Optional[Any] = None,
        cost_tracker: Optional[Any] = None,
    ) -> None:
        self.settings = settings
        self.chat_service = chat_service
        self.session_manager = session_manager
        self.vector_service = vector_service
        self.connection_manager = connection_manager
        self.cost_tracker = cost_tracker

    async def run(
        self,
        *,
        session_id: str,
        topic: str,
        agent_order: List[str],
        rounds: int,
        use_rag: bool = False,
    ) -> Dict[str, Any]:
        """Appelée par WS (features/chat/router.py). Renvoie un dict 'riche' prêt à être envoyé au client."""
        agent_order = [str(a).strip().lower() for a in (agent_order or []) if a]
        rounds = max(1, int(rounds) if isinstance(rounds, int) else 1)

        # Config normalisée (compatible front)
        config = {"topic": topic, "rounds": rounds, "agentOrder": agent_order, "useRag": use_rag}

        # Ping UI (préparation)
        await self._send_ws(session_id, "ws:debate_started", {
            "status": "pending",
            "topic": topic,
            "rounds": rounds,
            "agent_order": agent_order,
            "use_rag": use_rag,
            "config": config,
            "history": [],
        })

        # Agrégation par tours
        turns_maps: List[Dict[str, str]] = []  # ex: [{ "anima": "...", "neo": "..." }, { ... }, ...]
        total_cost = 0.0

        for r in range(rounds):
            round_map: Dict[str, str] = {}
            for agent_id in agent_order:
                # Prompt contextuel (dernier état connu)
                if turns_maps or round_map:
                    tail = []
                    for i, tmap in enumerate(turns_maps + [round_map]):
                        for a, txt in (tmap or {}).items():
                            tail.append(f"{a.upper()}: {txt}")
                    prompt = f"Sujet: {topic}\n\nDéroulé précédent:\n" + "\n".join(tail[-6:])
                else:
                    prompt = f"Sujet: {topic}"

                text, cost_info = await self.chat_service.get_llm_response_for_debate(
                    agent_id=agent_id, prompt=prompt, use_rag=use_rag
                )
                cost = float(cost_info.get("total_cost", 0.0)) if isinstance(cost_info, dict) else 0.0
                total_cost += cost
                round_map[agent_id] = text or ""

                # État agrégé courant (tours complets + tour en cours)
                partial_turns = turns_maps + [round_map]
                history_payload = self._format_turns_history(partial_turns)

                await self._send_ws(session_id, "ws:debate_turn_update", {
                    "status": "in_progress",
                    "round": r + 1,
                    "agent": agent_id,
                    "text": text or "",
                    "cost": cost,
                    "config": config,
                    "history": history_payload,
                })

            turns_maps.append(round_map)

        # Synthèse finale par 'anima' par défaut
        summarizer = self._pick_summarizer(agent_order)
        transcript = "\n\n".join(
            f"{a.upper()}: {txt}"
            for tmap in turns_maps for a, txt in (tmap or {}).items()
        )
        synth_prompt = (
            "Synthétise le débat en 5–8 phrases (faits, convergences, divergences, angles aveugles, pistes). "
            "Ne pas inventer de faits nouveaux."
        )
        synthesis, synth_cost_info = await self.chat_service.get_llm_response_for_debate(
            agent_id=summarizer, prompt=f"{synth_prompt}\n\nSujet: {topic}\n\n{transcript}", use_rag=use_rag
        )
        total_cost += float(synth_cost_info.get("total_cost", 0.0)) if isinstance(synth_cost_info, dict) else 0.0

        # Résultat final (le WS final sera envoyé par chat.router)
        result = {
            "status": "completed",
            "config": config,
            "history": self._format_turns_history(turns_maps),
            "synthesis": synthesis,
            "cost": total_cost,
        }
        return result

    def _pick_summarizer(self, order: List[str]) -> str:
        return "anima" if "anima" in (order or []) else (order[0] if order else "anima")

    def _format_turns_history(self, turns_maps: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """Convertit [{agent->text}, ...] -> [{round, agent_responses}, ...] (compat front)."""
        out: List[Dict[str, Any]] = []
        for idx, amap in enumerate(turns_maps):
            out.append({"round": idx + 1, "agent_responses": dict(amap or {})})
        return out

    async def _send_ws(self, session_id: str, event: str, payload: Dict[str, Any]) -> None:
        if not self.connection_manager:
            return
        try:
            await self.connection_manager.send_personal_message(
                {"type": event, "payload": payload}, session_id
            )
        except Exception as e:
            logger.warning(f"[debate.ws] envoi ws échoué (session={session_id}): {e}")
