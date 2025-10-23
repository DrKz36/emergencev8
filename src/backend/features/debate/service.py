# src/backend/features/debate/service.py
# V12.8 — DI+API compat + WS events par tour (started/turn_update/ended)

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, cast

from backend.core.websocket import ConnectionManager

logger = logging.getLogger(__name__)


@dataclass
class DebateConfig:
    topic: str
    rounds: int
    agent_order: List[str]  # [attacker, challenger, mediator]
    use_rag: bool = False
    doc_ids: Optional[List[str]] = None


class DebateService:
    def __init__(
        self,
        chat_service: Any,
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

    async def _status(
        self,
        session_id: str,
        status: str,
        topic: str = "",
        *,
        round_number: Optional[int] = None,
        agent_id: Optional[str] = None,
        role: Optional[str] = None,
        status_label: Optional[str] = None,
        message: Optional[str] = None,
    ) -> None:
        payload: Dict[str, Any] = {"stage": status, "status": status_label or status}
        if topic:
            payload["topic"] = topic
        if round_number is not None:
            payload["round"] = round_number
        if agent_id:
            payload["agent"] = agent_id
        if role:
            payload["role"] = role
        payload["message"] = message or self._format_status_message(
            stage=status, round_number=round_number, agent_id=agent_id, role=role
        )
        try:
            await self.connection_manager.send_personal_message(
                {"type": "ws:debate_status_update", "payload": payload},
                session_id,
            )
        except Exception:
            logger.debug("Impossible d'envoyer ws:debate_status_update", exc_info=True)

    def _format_status_message(
        self,
        *,
        stage: str,
        round_number: Optional[int] = None,
        agent_id: Optional[str] = None,
        role: Optional[str] = None,
    ) -> str:
        stage_norm = (stage or "").strip().lower()
        if stage_norm in {"", "idle"}:
            return "Pret a commencer."
        if stage_norm in {"starting", "start"}:
            return "Initialisation du debat..."
        if stage_norm in {"completed", "done", "finished"}:
            return "Debat termine."
        if stage_norm in {"synthesis", "synthesizing"}:
            target = agent_id or role or "mediateur"
            return f"Synthese en cours ({target})."
        if stage_norm.startswith("round"):
            round_txt = f"Tour {round_number}" if round_number is not None else ""
            agent_txt = agent_id or role or "intervenant"
            prefix = f"{round_txt} - " if round_txt else ""
            return f"{prefix}{agent_txt} intervient."
        return stage.replace("_", " " ).capitalize() or "Progression en cours."

    async def _emit(self, session_id: str, type_: str, payload: Dict[str, Any]) -> None:
        try:
            await self.connection_manager.send_personal_message(
                {"type": type_, "payload": payload}, session_id
            )
        except Exception:
            logger.debug("Emission WS echouee (%s)", type_, exc_info=True)

    async def _say_once(
        self,
        session_id: str,
        agent_id: str,
        prompt: str,
        *,
        use_rag: bool,
        doc_ids: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        try:
            res: Dict[str, Any] = await self.chat_service.get_llm_response_for_debate(
                agent_id,
                prompt,
                system_override=None,
                use_rag=use_rag,
                session_id=session_id,
                doc_ids=doc_ids,
            )
        except Exception as exc:
            agent_label = (agent_id or "inconnu").strip() or "inconnu"
            logger.error(
                "_say_once error (agent=%s): %s",
                agent_label,
                exc,
                exc_info=True,
            )
            raw_message = str(exc).replace("\n", " ").strip()
            if len(raw_message) > 200:
                raw_message = raw_message[:197] + "..."
            fallback_message = (
                f"⚠️ Agent {agent_label} indisponible — contribution ignorée."
            )
            if raw_message:
                fallback_message = f"{fallback_message} (erreur: {raw_message})"

            return {
                "text": fallback_message,
                "cost_info": {"input_tokens": 0, "output_tokens": 0, "total_cost": 0.0},
                "provider": None,
                "model": None,
                "fallback": True,
                "error": {
                    "type": exc.__class__.__name__,
                    "message": raw_message,
                },
            }

        text = (res or {}).get("text", "") or ""
        cost_info = (res or {}).get("cost_info", {}) or {}
        provider = (res or {}).get("provider")
        model = (res or {}).get("model")
        fallback = bool((res or {}).get("fallback"))
        payload: Dict[str, Any] = {
            "text": text,
            "cost_info": cost_info,
            "provider": provider,
            "model": model,
            "fallback": fallback,
        }
        error_info = (res or {}).get("error")
        if error_info:
            payload["error"] = error_info
        return payload

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
        raw_doc_ids = kwargs.get("doc_ids") if "doc_ids" in kwargs else kwargs.get("docIds")
        if isinstance(raw_doc_ids, (set, tuple)):
            raw_doc_ids = list(raw_doc_ids)
        elif isinstance(raw_doc_ids, str):
            raw_doc_ids = [raw_doc_ids]
        doc_ids: Optional[List[str]] = None
        if isinstance(raw_doc_ids, list):
            doc_ids = []
            for item in raw_doc_ids:
                if item in (None, ""):
                    continue
                try:
                    doc_ids.append(str(int(str(item).strip())))
                except (ValueError, TypeError):
                    text = str(item).strip()
                    if text:
                        doc_ids.append(text)
            if not doc_ids:
                doc_ids = None
        return DebateConfig(topic=topic, rounds=rounds, agent_order=agent_order, use_rag=use_rag, doc_ids=doc_ids)

    async def run(self, session_id: str, config: Optional[DebateConfig] = None, **kwargs: Any) -> Dict[str, Any]:
        cfg = self._normalize_config(config, kwargs)
        topic = (cfg.topic or "").strip()
        attacker, challenger, mediator = (cfg.agent_order + ["", "", ""])[:3]
        rounds = max(1, int(cfg.rounds or 1))
        use_rag = bool(cfg.use_rag)
        selected_doc_ids: List[int] = []
        try:
            if self.chat_service:
                selected_doc_ids = self.chat_service._sanitize_doc_ids(cfg.doc_ids)
        except Exception:
            selected_doc_ids = []

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

        cost_summary: Dict[str, Any] = {
            "total_usd": 0.0,
            "tokens": {"input": 0, "output": 0},
            "by_agent": {},
        }

        def accumulate_cost(agent: str, info: Optional[Dict[str, Any]]) -> None:
            if not info:
                return
            total_cost = float(info.get("total_cost") or 0.0)
            input_tokens = int(info.get("input_tokens") or 0)
            output_tokens = int(info.get("output_tokens") or 0)
            if agent:
                agent_entry = cost_summary["by_agent"].setdefault(
                    agent, {"usd": 0.0, "input_tokens": 0, "output_tokens": 0}
                )
                agent_entry["usd"] += total_cost
                agent_entry["input_tokens"] += input_tokens
                agent_entry["output_tokens"] += output_tokens
            cost_summary["total_usd"] += total_cost
            cost_summary["tokens"]["input"] += input_tokens
            cost_summary["tokens"]["output"] += output_tokens

        await self._emit(
            session_id,
            "ws:debate_started",
            {
                "topic": topic,
                "config": {"rounds": rounds, "agentOrder": [attacker, challenger, mediator], "useRag": use_rag},
            },
        )
        await self._status(
            session_id,
            "starting",
            topic,
            status_label="starting",
            message="Initialisation du debat...",
        )

        turns: List[Dict[str, Any]] = []

        for r in range(1, rounds + 1):
            # ⚡ Optimisation Phase 2: Round 1 en parallèle (attacker + challenger indépendants)
            if r == 1:
                # Round 1: les deux agents parlent simultanément du même topic
                await self._status(
                    session_id,
                    "round_attacker",
                    topic,
                    round_number=r,
                    agent_id=attacker,
                    role="attacker",
                    status_label="speaking",
                )
                await self._status(
                    session_id,
                    "round_challenger",
                    topic,
                    round_number=r,
                    agent_id=challenger,
                    role="challenger",
                    status_label="speaking",
                )

                prompt_attacker = self._build_turn_prompt(topic, turns, speaker="attacker", agent=attacker)
                prompt_challenger = self._build_turn_prompt(topic, turns, speaker="challenger", agent=challenger)

                # Appels parallèles avec asyncio.gather
                import asyncio
                results = await asyncio.gather(
                    self._say_once(session_id, attacker, prompt_attacker, use_rag=use_rag, doc_ids=selected_doc_ids),
                    self._say_once(session_id, challenger, prompt_challenger, use_rag=use_rag, doc_ids=selected_doc_ids),
                    return_exceptions=True
                )
                attacker_response_raw, challenger_response_raw = results

                # Gérer les erreurs individuelles
                if isinstance(attacker_response_raw, Exception):
                    logger.error(f"Erreur attacker round {r}: {attacker_response_raw}", exc_info=attacker_response_raw)
                    raise attacker_response_raw
                if isinstance(challenger_response_raw, Exception):
                    logger.error(f"Erreur challenger round {r}: {challenger_response_raw}", exc_info=challenger_response_raw)
                    raise challenger_response_raw

                # Type narrowing après vérification des exceptions (cast pour mypy)
                attacker_response: Dict[str, Any] = cast(Dict[str, Any], attacker_response_raw)
                challenger_response: Dict[str, Any] = cast(Dict[str, Any], challenger_response_raw)

                turn_a = {
                    "round": r,
                    "agent": attacker,
                    "text": attacker_response.get("text", ""),
                    "meta": {
                        "role": "attacker",
                        "provider": attacker_response.get("provider"),
                        "model": attacker_response.get("model"),
                        "fallback": attacker_response.get("fallback"),
                        "cost": attacker_response.get("cost_info"),
                        "error": attacker_response.get("error"),
                    },
                }
                turns.append(turn_a)
                accumulate_cost(attacker, attacker_response.get("cost_info"))
                await self._emit(session_id, "ws:debate_turn_update", {**turn_a, "speaker": "attacker"})

                turn_c = {
                    "round": r,
                    "agent": challenger,
                    "text": challenger_response.get("text", ""),
                    "meta": {
                        "role": "challenger",
                        "provider": challenger_response.get("provider"),
                        "model": challenger_response.get("model"),
                        "fallback": challenger_response.get("fallback"),
                        "cost": challenger_response.get("cost_info"),
                        "error": challenger_response.get("error"),
                    },
                }
                turns.append(turn_c)
                accumulate_cost(challenger, challenger_response.get("cost_info"))
                await self._emit(session_id, "ws:debate_turn_update", {**turn_c, "speaker": "challenger"})

            else:
                # Rounds suivants: séquentiel (challenger répond à attacker)
                await self._status(
                    session_id,
                    "round_attacker",
                    topic,
                    round_number=r,
                    agent_id=attacker,
                    role="attacker",
                    status_label="speaking",
                )
                prompt_attacker = self._build_turn_prompt(topic, turns, speaker="attacker", agent=attacker)
                attacker_response = await self._say_once(
                    session_id,
                    attacker,
                    prompt_attacker,
                    use_rag=use_rag,
                    doc_ids=selected_doc_ids,
                )
                turn_a = {
                    "round": r,
                    "agent": attacker,
                    "text": attacker_response.get("text", ""),
                    "meta": {
                        "role": "attacker",
                        "provider": attacker_response.get("provider"),
                        "model": attacker_response.get("model"),
                        "fallback": attacker_response.get("fallback"),
                        "cost": attacker_response.get("cost_info"),
                        "error": attacker_response.get("error"),
                    },
                }
                turns.append(turn_a)
                accumulate_cost(attacker, attacker_response.get("cost_info"))
                await self._emit(session_id, "ws:debate_turn_update", {**turn_a, "speaker": "attacker"})

                await self._status(
                    session_id,
                    "round_challenger",
                    topic,
                    round_number=r,
                    agent_id=challenger,
                    role="challenger",
                    status_label="speaking",
                )
                prompt_challenger = self._build_turn_prompt(topic, turns, speaker="challenger", agent=challenger)
                challenger_response = await self._say_once(
                    session_id,
                    challenger,
                    prompt_challenger,
                    use_rag=use_rag,
                    doc_ids=selected_doc_ids,
                )
                turn_c = {
                    "round": r,
                    "agent": challenger,
                    "text": challenger_response.get("text", ""),
                    "meta": {
                        "role": "challenger",
                        "provider": challenger_response.get("provider"),
                        "model": challenger_response.get("model"),
                        "fallback": challenger_response.get("fallback"),
                        "cost": challenger_response.get("cost_info"),
                        "error": challenger_response.get("error"),
                    },
                }
                turns.append(turn_c)
                accumulate_cost(challenger, challenger_response.get("cost_info"))
                await self._emit(session_id, "ws:debate_turn_update", {**turn_c, "speaker": "challenger"})

        await self._status(
            session_id,
            "synthesis",
            topic,
            agent_id=mediator,
            role="mediator",
            status_label="synthesizing",
        )
        synthesis_prompt = self._build_synthesis_prompt(topic, turns, mediator)
        synthesis_response = await self._say_once(
            session_id,
            mediator,
            synthesis_prompt,
            use_rag=use_rag,
            doc_ids=selected_doc_ids,
        )
        synthesis_text = synthesis_response.get("text", "")
        synthesis_meta = {
            "role": "mediator",
            "provider": synthesis_response.get("provider"),
            "model": synthesis_response.get("model"),
            "fallback": synthesis_response.get("fallback"),
            "cost": synthesis_response.get("cost_info"),
            "error": synthesis_response.get("error"),
        }
        accumulate_cost(mediator, synthesis_response.get("cost_info"))

        cost_payload = {
            "total_usd": round(cost_summary["total_usd"], 6),
            "tokens": {
                "input": int(cost_summary["tokens"].get("input", 0)),
                "output": int(cost_summary["tokens"].get("output", 0)),
            },
            "by_agent": {
                agent: {
                    "usd": round(values.get("usd", 0.0), 6),
                    "input_tokens": int(values.get("input_tokens", 0)),
                    "output_tokens": int(values.get("output_tokens", 0)),
                }
                for agent, values in cost_summary["by_agent"].items()
            },
        }

        payload = {
            "topic": topic,
            "turns": turns,
            "synthesis": synthesis_text,
            "synthesis_meta": synthesis_meta,
            "config": {
                "topic": topic,
                "rounds": rounds,
                "agentOrder": [attacker, challenger, mediator],
                "useRag": use_rag,
                "docIds": selected_doc_ids,
            },
            "status": "completed",
            "stage": "completed",
            "cost": cost_payload,
        }

        await self._emit(session_id, "ws:debate_result", payload)
        await self._emit(session_id, "ws:debate_ended", {"topic": topic, "rounds": rounds})
        await self._status(
            session_id,
            "completed",
            topic,
            status_label="completed",
            message="Debat termine.",
        )
        return payload

    def _build_turn_prompt(self, topic: str, turns: List[Dict[str, Any]], *, speaker: str, agent: str) -> str:
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

    def _build_synthesis_prompt(self, topic: str, turns: List[Dict[str, Any]], mediator: str) -> str:
        lines = [f"Sujet: {topic}", "Débat (chronologique):"]
        for t in turns:
            lines.append(f"- {t.get('agent','?')}: {t.get('text','').strip()}")
        lines.append(
            "\nConsigne (médiateur): fournis une synthèse neutre, structurée, 6-10 phrases maximum, "
            "pas de répétitions, pas de nouvelles idées, conclure par 1 phrase d'ouverture constructive."
        )
        return "\n".join(lines)


