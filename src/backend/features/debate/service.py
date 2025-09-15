# src/backend/features/debate/service.py
# V12.8 — DI+API compat + WS events par tour (started/turn_update/ended)

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any

from backend.core.websocket import ConnectionManager

logger = logging.getLogger(__name__)


@dataclass
class DebateConfig:
    topic: str
    rounds: int
    agent_order: List[str]  # [attacker, challenger, mediator]
    use_rag: bool = False


class DebateService:
    def __init__(
        self,
        chat_service,
        connection_manager: ConnectionManager,
        session_manager: Optional[object] = None,
        vector_service: Optional[object] = None,
        cost_tracker: Optional[object] = None,
        settings: Optional[object] = None,
    ):
        self.chat_service = chat_service
        self.connection_manager = connection_manager
        self.session_manager = session_manager
        self.vector_service = vector_service
        self.cost_tracker = cost_tracker
        self.settings = settings

    async def _status(self, session_id: str, status: str, topic: str = "") -> None:
        try:
            await self.connection_manager.send_personal_message(
                {"type": "ws:debate_status_update", "payload": {"status": status, "topic": topic}},
                session_id,
            )
        except Exception:
            logger.debug("Impossible d'envoyer ws:debate_status_update", exc_info=True)

    async def _emit(self, session_id: str, type_: str, payload: Dict) -> None:
        try:
            await self.connection_manager.send_personal_message({"type": type_, "payload": payload}, session_id)
        except Exception:
            logger.debug("Emission WS échouée (%s)", type_, exc_info=True)

    async def _say_once(
        self,
        session_id: str,
        agent_id: str,
        prompt: str,
        *,
        use_rag: bool,
    ) -> Tuple[str, Dict]:
        try:
            res: Dict = await asyncio.to_thread(
                self.chat_service.get_llm_response_for_debate,
                agent_id,
                prompt,
                system_override=None,
                use_rag=use_rag,
                session_id=session_id,
            )
        except Exception as e:
            logger.error(f"_say_once error (agent={agent_id}): {e}", exc_info=True)
            raise

        text = (res or {}).get("text", "") or ""
        cost_info = (res or {}).get("cost_info", {}) or {}
        return text, cost_info

    @staticmethod
    def _normalize_config(config: Optional[DebateConfig], kwargs: Dict[str, Any]) -> DebateConfig:
        if isinstance(config, DebateConfig):
            return config
        topic = (kwargs.get("topic") or "").strip()
        rounds = int(kwargs.get("rounds") or 1)
        agent_order = kwargs.get("agentOrder") or kwargs.get("agent_order") or []
        if not isinstance(agent_order, list):
            agent_order = []
        use_rag = bool(kwargs.get("useRag") if "useRag" in kwargs else kwargs.get("use_rag", False))
        return DebateConfig(topic=topic, rounds=rounds, agent_order=agent_order, use_rag=use_rag)

    async def run(self, session_id: str, config: Optional[DebateConfig] = None, **kwargs) -> Dict:
        cfg = self._normalize_config(config, kwargs)
        topic = (cfg.topic or "").strip()
        attacker, challenger, mediator = (cfg.agent_order + ["", "", ""])[:3]
        rounds = max(1, int(cfg.rounds or 1))
        use_rag = bool(cfg.use_rag)

        logger.info(
            json.dumps(
                {
                    "event": "debate_start",
                    "session_id": session_id,
                    "topic": topic,
                    "rounds": rounds,
                    "agent_order": [attacker, challenger, mediator],
                    "use_rag": use_rag,
                },
                ensure_ascii=False,
            )
        )

        # NEW: signal "started"
        await self._emit(
            session_id,
            "ws:debate_started",
            {
                "topic": topic,
                "config": {"rounds": rounds, "agentOrder": [attacker, challenger, mediator], "useRag": use_rag},
            },
        )
        await self._status(session_id, "starting", topic)

        turns: List[Dict] = []

        for r in range(1, rounds + 1):
            await self._status(session_id, f"round_{r}_attacker")
            prompt_attacker = self._build_turn_prompt(topic, turns, speaker="attacker", agent=attacker)
            text_a, _ = await self._say_once(session_id, attacker, prompt_attacker, use_rag=use_rag)
            turn_a = {"round": r, "agent": attacker, "text": text_a}
            turns.append(turn_a)
            # NEW: signal "turn_update"
            await self._emit(session_id, "ws:debate_turn_update", {**turn_a, "speaker": "attacker"})

            await self._status(session_id, f"round_{r}_challenger")
            prompt_challenger = self._build_turn_prompt(topic, turns, speaker="challenger", agent=challenger)
            text_c, _ = await self._say_once(session_id, challenger, prompt_challenger, use_rag=use_rag)
            turn_c = {"round": r, "agent": challenger, "text": text_c}
            turns.append(turn_c)
            # NEW: signal "turn_update"
            await self._emit(session_id, "ws:debate_turn_update", {**turn_c, "speaker": "challenger"})

        await self._status(session_id, "synthesis")
        synthesis_prompt = self._build_synthesis_prompt(topic, turns, mediator)
        synthesis_text, _ = await self._say_once(session_id, mediator, synthesis_prompt, use_rag=use_rag)

        payload = {
            "topic": topic,
            "turns": turns,
            "synthesis": synthesis_text,
            "config": {"topic": topic, "rounds": rounds, "agentOrder": [attacker, challenger, mediator], "useRag": use_rag},
            "status": "completed",
        }

        # Résultat global + "ended"
        await self._emit(session_id, "ws:debate_result", payload)
        await self._emit(session_id, "ws:debate_ended", {"topic": topic, "rounds": rounds})
        await self._status(session_id, "completed", topic)
        return payload

    def _build_turn_prompt(self, topic: str, turns: List[Dict], *, speaker: str, agent: str) -> str:
        assert speaker in ("attacker", "challenger")
        if not turns:
            return f"Sujet: {topic}\n\nTon rôle ({agent}) : ouvre le débat de manière concise et percutante en 4-6 phrases."
        last = turns[-1]
        last_agent = last.get("agent", "")
        last_text = last.get("text", "")
        return (
            f"Sujet: {topic}\n\n"
            f"Dernière intervention de l'adversaire ({last_agent}):\n{last_text}\n\n"
            f"Ton rôle ({agent}) : réponds précisément, 4-6 phrases, pas de résumé global."
        )

    def _build_synthesis_prompt(self, topic: str, turns: List[Dict], mediator: str) -> str:
        lines = [f"Sujet: {topic}", "Débat (chronologique):"]
        for t in turns:
            lines.append(f"- {t.get('agent','?')}: {t.get('text','').strip()}")
        lines.append(
            "\nConsigne (médiateur): fournis une synthèse neutre, structurée, 6-10 phrases maximum, "
            "pas de répétitions, pas de nouvelles idées, conclure par 1 phrase d'ouverture constructive."
        )
        return "\n".join(lines)
