# src/backend/features/chat/service.py
# V32.1 — Style prelude balisé + anti-vouvoiement (+ tonalités par agent) en priorité system,
#          ws:model_info expose prompt_file, logs enrichis ; prompts conservent texte+nom de fichier.
#
# Historique:
# - V31.5: Débat sync provider-agnostic + meta.sources RAG + style FR pour Nexus/Anthropic
# - V32.0: retire le forçage dur d'AnimA -> gpt-4o-mini (désormais pilotable par ENV),
#          étend le préambule de style FR aux 3 agents, petits nettoyages.
# - V32.1: STYLE_RULES balisés + anti-vouvoiement explicite, prompt_file exposé, _load_prompts -> bundles.

import asyncio
import inspect
import glob
import json
import logging
import os
import re
from uuid import uuid4
from typing import Dict, Any, List, Tuple, Optional, AsyncGenerator, AsyncIterator, cast
from pathlib import Path
from datetime import datetime, timezone

import google.generativeai as genai
from openai import AsyncOpenAI, OpenAI
from anthropic import AsyncAnthropic, Anthropic
from anthropic.types.message_param import MessageParam


from backend.core.session_manager import SessionManager
from backend.core.cost_tracker import CostTracker
from backend.core.websocket import ConnectionManager
from backend.shared.models import AgentMessage, Role, ChatMessage
from backend.features.memory.vector_service import VectorService
from backend.shared.config import Settings, DEFAULT_AGENT_CONFIGS
from backend.core import config
from backend.core.database import queries

from backend.features.memory.gardener import MemoryGardener

logger = logging.getLogger(__name__)

VITALITY_RECALL_THRESHOLD = getattr(MemoryGardener, "RECALL_THRESHOLD", 0.3)
VITALITY_MAX = getattr(MemoryGardener, "MAX_VITALITY", 1.0)
VITALITY_USAGE_BOOST = getattr(MemoryGardener, "USAGE_BOOST", 0.2)

# Prix indicatifs (USD / token) — à vérifier en session connectée.
MODEL_PRICING = {
    "gpt-4o-mini": {"input": 0.15 / 1_000_000, "output": 0.60 / 1_000_000},
    "gpt-4o": {"input": 5.00 / 1_000_000, "output": 15.00 / 1_000_000},
    "gemini-1.5-flash": {"input": 0.35 / 1_000_000, "output": 0.70 / 1_000_000},
    "claude-3-5-haiku-20241022": {"input": 0.25 / 1_000_000, "output": 1.25 / 1_000_000},
    "claude-3-sonnet-20240229": {"input": 3.00 / 1_000_000, "output": 15.00 / 1_000_000},
    "claude-3-opus-20240229": {"input": 15.00 / 1_000_000, "output": 75.00 / 1_000_000},
}

DEFAULT_TEMPERATURE = float(os.getenv("EMERGENCE_TEMP_DEFAULT", "0.4"))

CHAT_PROVIDER_FALLBACKS = {
    "google": [("anthropic", "claude-3-5-haiku-20241022"), ("openai", "gpt-4o-mini")],
    "anthropic": [("openai", "gpt-4o-mini"), ("google", "gemini-1.5-flash")],
    "openai": [("anthropic", "claude-3-5-haiku-20241022"), ("google", "gemini-1.5-flash")],
}


def _normalize_provider(p: Optional[str]) -> str:
    if not p:
        return ""
    p = p.strip().lower()
    if p in ("gemini", "google", "googleai", "vertex"):
        return "google"
    if p in ("openai", "oai"):
        return "openai"
    if p in ("anthropic", "claude"):
        return "anthropic"
    return p


class ChatService:
    def __init__(
        self,
        session_manager: SessionManager,
        cost_tracker: CostTracker,
        vector_service: VectorService,
        settings: Settings,
    ):
        self.session_manager = session_manager
        self.cost_tracker = cost_tracker
        self.vector_service = vector_service
        self.settings = settings

        # Politique hors historique (quand RAG OFF)
        self.off_history_policy = os.getenv("EMERGENCE_RAG_OFF_POLICY", "stateless").strip().lower()
        if self.off_history_policy not in ("stateless", "agent_local"):
            self.off_history_policy = "stateless"
        logger.info(f"ChatService OFF policy: {self.off_history_policy}")

        try:
            # Clients async (chat streaming)
            self.openai_client = AsyncOpenAI(api_key=self.settings.openai_api_key)
            genai.configure(api_key=self.settings.google_api_key)
            self.anthropic_client = AsyncAnthropic(api_key=self.settings.anthropic_api_key)
            # Clients sync (débat — non stream)
            self.openai_sync = OpenAI(api_key=self.settings.openai_api_key)
            self.anthropic_sync = Anthropic(api_key=self.settings.anthropic_api_key)
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation des clients API: {e}", exc_info=True)
            raise

        # Cache paresseux des collections
        self._doc_collection = None
        self._knowledge_collection = None

        self.prompts = self._load_prompts(self.settings.paths.prompts)
        self.broadcast_agents = self._compute_broadcast_agents()
        if not self.broadcast_agents:
            self.broadcast_agents = ['anima', 'neo', 'nexus']
        logger.info(f"ChatService V32.1 initialisé. Prompts chargés: {len(self.prompts)}")

    # ---------- prompts ----------
    def _load_prompts(self, prompts_dir: str) -> Dict[str, Dict[str, str]]:
        """
        Retourne un mapping agent_id -> {"text": <prompt>, "file": <nom_fichier>} en choisissant
        la variante de poids maximum (v3 > v2 > lite par nom).
        """
        def weight(name: str) -> int:
            name = name.lower()
            w = 0
            if "lite" in name:
                w = max(w, 1)
            if "v2" in name:
                w = max(w, 2)
            if "v3" in name:
                w = max(w, 3)
            return w

        chosen: Dict[str, Dict[str, Any]] = {}
        for file_path in glob.glob(os.path.join(prompts_dir, "*.md")):
            p = Path(file_path)
            agent_id = (
                p.stem.replace("_system", "")
                .replace("_v2", "")
                .replace("_v3", "")
                .replace("_lite", "")
            )
            w = weight(p.name)
            if agent_id not in chosen or w > chosen[agent_id]["w"]:
                with open(file_path, "r", encoding="utf-8") as f:
                    chosen[agent_id] = {"w": w, "text": f.read(), "file": p.name}
        for aid, meta in chosen.items():
            logger.info(f"Prompt retenu pour l'agent '{aid}': {meta['file']}")
        # Conserver texte + nom de fichier pour l'UI / debug
        return {aid: {"text": meta["text"], "file": meta["file"]} for aid, meta in chosen.items()}


    def _resolve_agent_configs(self) -> Dict[str, Dict[str, Any]]:
        base = {name: dict(cfg) for name, cfg in DEFAULT_AGENT_CONFIGS.items()}
        raw_configs = getattr(self.settings, "agents", None)
        if isinstance(raw_configs, dict):
            for name, cfg in raw_configs.items():
                if not isinstance(cfg, dict):
                    continue
                merged = dict(base.get(name, {}))
                for key, value in cfg.items():
                    if value is None:
                        continue
                    merged[key] = value
                base[name] = merged
        return base


    def _compute_broadcast_agents(self) -> List[str]:
        agents_cfg = self._resolve_agent_configs()
        candidates = [aid for aid in agents_cfg.keys() if aid not in {"default", "global"}]

        ordered: List[str] = []
        for preferred in ("anima", "neo", "nexus"):
            if preferred in candidates and preferred not in ordered:
                ordered.append(preferred)

        for aid in candidates:
            if aid not in ordered:
                ordered.append(aid)

        prompt_ids = [p.replace('_lite', '') for p in self.prompts.keys()]
        for prompt_id in prompt_ids:
            if prompt_id not in ordered and prompt_id not in {"default", "global"}:
                ordered.append(prompt_id)

        return ordered

    # ---------- config agent / system prompt ----------
    def _get_agent_config(self, agent_id: str) -> Tuple[str, str, str]:
        """
        Retourne (provider, model, system_prompt) en respectant settings.agents.
        Possibilité d'override économique pour AnimA via ENV:
          - EMERGENCE_FORCE_CHEAP_ANIMA=1  -> force openai:gpt-4o-mini
        """
        clean_agent_id = (agent_id or "").replace("_lite", "")
        agent_configs = self._resolve_agent_configs()

        provider_raw = agent_configs.get(clean_agent_id, {}).get("provider")
        model = agent_configs.get(clean_agent_id, {}).get("model")
        provider = _normalize_provider(provider_raw)

        # ENV toggle pour protéger les coûts quand souhaité.
        if clean_agent_id == "anima" and os.getenv("EMERGENCE_FORCE_CHEAP_ANIMA", "0").strip() == "1":
            provider = "openai"
            model = "gpt-4o-mini"
            logger.info("Override coût activé (ENV): anima → openai:gpt-4o-mini")

        fallback_order = []
        if clean_agent_id in agent_configs:
            fallback_order.append(clean_agent_id)
        if "default" in agent_configs and "default" not in fallback_order:
            fallback_order.append("default")
        if "anima" in agent_configs and "anima" not in fallback_order:
            fallback_order.append("anima")
        fallback_order.extend([k for k in agent_configs.keys() if k not in fallback_order])

        resolved_id = None
        for candidate in fallback_order:
            cfg = agent_configs.get(candidate, {})
            cand_provider = provider if candidate == clean_agent_id else _normalize_provider(cfg.get("provider"))
            cand_model = model if candidate == clean_agent_id else cfg.get("model")
            if not cand_provider or not cand_model:
                continue
            resolved_id = candidate
            provider = cand_provider
            model = cand_model
            if candidate != clean_agent_id:
                logger.warning("Agent '%s' non configuré, fallback sur '%s'", agent_id, candidate)
            break

        bundle = (
            self.prompts.get(agent_id)
            or self.prompts.get(clean_agent_id)
            or (self.prompts.get(resolved_id) if resolved_id else None)
            or self.prompts.get("anima")
            or {"text": ""}
        )
        system_prompt = bundle.get("text", "")

        if not provider or not model or system_prompt is None:
            raise ValueError(
                f"Configuration incomplète pour l'agent '{agent_id}' "
                f"(provider='{provider}', agent_effectif='{resolved_id or clean_agent_id}', model='{model}')."
            )

        return provider, model, system_prompt
    def _ensure_fr_tutoiement(self, agent_id: str, provider: str, system_prompt: str) -> str:
        """
        Préambule de style prioritaire, cross-provider.
        - Tutoiement OBLIGATOIRE, auto-correction si 'vous' utilisé.
        - Tonalité par agent plus saillante.
        - Balises [STYLE_RULES] pour surpondération attentionnelle.
        """
        aid = (agent_id or "").strip().lower()

        persona = {
            "anima": (
                "Tonalité: créative, imagée, sensible mais précise. "
                "Tu peux employer des métaphores courtes, jamais de pathos."
            ),
            "neo": (
                "Tonalité: analytique, mordante, factuelle, anti-bullshit. "
                "Tu privilégies la concision et les listes."
            ),
            "nexus": (
                "Tonalité: médiatrice, calme, structurée, synthétique. "
                "Tu fais émerger les points d'accord et les divergences."
            ),
        }.get(aid, "")

        style_rules = (
            "[STYLE_RULES]\n"
            "1) Tu tutoies l'utilisateur, sans exception. Si tu écris 'vous', "
            "   corrige-toi immédiatement et reformule en 'tu'.\n"
            "2) Tu réponds en français, clair, direct, phrases courtes.\n"
            f"3) {persona}\n"
            "4) Pas de précautions inutiles ni de disclaimers hors sujet.\n"
            "[/STYLE_RULES]\n"
        )

        # On place les règles AVANT le prompt agent pour maximiser l'effet.
        return f"""{style_rules}
{system_prompt}""".strip()

    # ---------- utilitaires mémoire / RAG ----------
    def _extract_sensitive_tokens(self, text: str) -> List[str]:
        return re.findall(r"\b[A-Z]{3,}-\d{3,}\b", text or "")

    @staticmethod
    def _normalize_role_value(role: Any) -> str:
        if isinstance(role, Role):
            return role.value
        if isinstance(role, str):
            return role.strip().lower()
        try:
            value = getattr(role, "value", None)
            if isinstance(value, str):
                return value.strip().lower()
        except Exception:
            pass
        return ""

    def _is_user_role(self, role: Any) -> bool:
        return self._normalize_role_value(role) == Role.USER.value

    def _message_to_dict(self, message: Any) -> Dict[str, Any]:
        if isinstance(message, dict):
            payload = dict(message)
        else:
            payload = {}
            for attr in ("model_dump", "dict"):
                if hasattr(message, attr):
                    try:
                        dump = getattr(message, attr)
                        payload = dump(mode="json") if attr == "model_dump" else dump()
                        if isinstance(payload, dict):
                            break
                        payload = {}
                    except TypeError:
                        try:
                            payload = getattr(message, attr)()
                            if isinstance(payload, dict):
                                break
                            payload = {}
                        except Exception:
                            payload = {}
                    except Exception:
                        payload = {}
            if not payload:
                for key in ("id", "session_id", "role", "content", "message", "agent", "agent_id",
                            "timestamp", "cost_info", "meta"):
                    if hasattr(message, key):
                        payload[key] = getattr(message, key)

        role_value = self._normalize_role_value(payload.get("role"))
        if role_value:
            payload["role"] = role_value
        return payload

    def _try_get_user_id(self, session_id: str) -> Optional[str]:
        for attr in ("get_user_id_for_session", "get_user", "get_owner", "get_session_owner"):
            try:
                fn = getattr(self.session_manager, attr, None)
                if callable(fn):
                    uid = fn(session_id)
                    if uid:
                        return str(uid)
            except Exception:
                pass
        for attr in ("current_user_id", "user_id"):
            try:
                uid = getattr(self.session_manager, attr, None)
                if uid:
                    return str(uid)
            except Exception:
                pass
        return None

    def _merge_blocks(self, blocks: List[Tuple[str, str]]) -> str:
        parts = []
        for title, body in blocks:
            if body and str(body).strip():
                parts.append(f"### {title}\n{str(body).strip()}")
        return "\n\n".join(parts)

    _MOT_CODE_RE = re.compile(r"\b(mot-?code|code)\b", re.IGNORECASE)

    def _is_mot_code_query(self, text: str) -> bool:
        return bool(self._MOT_CODE_RE.search(text or ""))

    def _fetch_mot_code_for_agent(self, agent_id: str, user_id: Optional[str]) -> Optional[str]:
        if self._knowledge_collection is None:
            knowledge_name = os.getenv("EMERGENCE_KNOWLEDGE_COLLECTION", "emergence_knowledge")
            self._knowledge_collection = self.vector_service.get_or_create_collection(knowledge_name)

        collection = self._knowledge_collection
        if collection is None:
            return None

        clauses = [{"type": "fact"}, {"key": "mot-code"}, {"agent": (agent_id or "").lower()}]
        if user_id:
            clauses.append({"user_id": user_id})
        where = {"$and": clauses}
        got = collection.get(where=where, include=["documents", "metadatas"])
        ids = got.get("ids", []) or []
        if not ids:
            got = collection.get(
                where={"$and": [{"type": "fact"}, {"key": "mot-code"}, {"agent": (agent_id or "").lower()}]},
                include=["documents", "metadatas"],
            )
            ids = got.get("ids", []) or []
            if not ids:
                return None
        docs = got.get("documents", []) or []
        if not docs:
            return None
        line = docs[0] or ""
        if ":" in line:
            try:
                return line.split(":", 1)[1].strip()
            except Exception:
                pass
        metas = got.get("metadatas", []) or []
        if metas and isinstance(metas[0], dict) and metas[0].get("value"):
            return str(metas[0]["value"]).strip()
        return None

    def _try_get_session_summary(self, session_id: str) -> str:
        try:
            sess = self.session_manager.get_session(session_id)
            meta = getattr(sess, "metadata", None)
            if isinstance(meta, dict):
                s = meta.get("summary")
                if isinstance(s, str) and s.strip():
                    return s.strip()
        except Exception:
            pass
        return ""

    async def _build_memory_context(
        self, session_id: str, last_user_message: str, top_k: int = 5, agent_id: Optional[str] = None
    ) -> str:
        try:
            if not last_user_message:
                return ""
            if self._knowledge_collection is None:
                knowledge_name = os.getenv("EMERGENCE_KNOWLEDGE_COLLECTION", "emergence_knowledge")
                self._knowledge_collection = self.vector_service.get_or_create_collection(knowledge_name)

            knowledge_col = self._knowledge_collection
            if knowledge_col is None:
                return ""
            where_filter = None
            uid = self._try_get_user_id(session_id)

            session_clause: Dict[str, Any] = {
                "$or": [
                    {"session_id": session_id},
                    {"source_session_id": session_id},
                ]
            }
            clauses: List[Dict[str, Any]] = [session_clause]
            if uid:
                clauses.append({"user_id": uid})
            ag = (agent_id or "").strip().lower() if agent_id else ""
            if ag:
                clauses.append({"agent": ag})
            if len(clauses) == 1:
                where_filter = clauses[0]
            elif len(clauses) >= 2:
                where_filter = {"$and": clauses}

            results = self.vector_service.query(
                collection=knowledge_col,
                query_text=last_user_message,
                n_results=top_k,
                where_filter=where_filter,
            )

            if (not results) and ag and uid:
                try:
                    results = self.vector_service.query(
                        collection=knowledge_col,
                        query_text=last_user_message,
                        n_results=top_k,
                        where_filter={
                            "$and": [
                                {"session_id": session_id},
                                {"user_id": uid},
                                {"vitality": {"$gte": VITALITY_RECALL_THRESHOLD}},
                            ]
                        },
                    )
                except Exception:
                    pass

            if not results:
                return ""
            lines: List[str] = []
            touched_ids: List[str] = []
            touched_metas: List[Dict[str, Any]] = []
            touch_ts = datetime.now(timezone.utc).isoformat()

            for r in results:
                t = (r.get("text") or "").strip()
                if t:
                    lines.append(f"- {t}")
                vec_id = r.get("id")
                meta = r.get("metadata")
                if not vec_id or not isinstance(meta, dict):
                    continue
                updated_meta = dict(meta)
                prev_usage = updated_meta.get("usage_count", 0)
                try:
                    updated_meta["usage_count"] = int(prev_usage) + 1
                except Exception:
                    updated_meta["usage_count"] = 1
                prev_vitality = updated_meta.get("vitality", VITALITY_MAX)
                try:
                    prev_vitality = float(prev_vitality)
                except (TypeError, ValueError):
                    prev_vitality = VITALITY_MAX
                updated_meta["vitality"] = min(
                    VITALITY_MAX, round(prev_vitality + VITALITY_USAGE_BOOST, 4)
                )
                updated_meta["last_access_at"] = touch_ts
                if not updated_meta.get("session_id"):
                    updated_meta["session_id"] = session_id
                if not updated_meta.get("source_session_id"):
                    updated_meta["source_session_id"] = session_id
                if uid and not updated_meta.get("user_id"):
                    updated_meta["user_id"] = uid
                touched_ids.append(str(vec_id))
                touched_metas.append(updated_meta)
            if touched_ids and knowledge_col is not None:
                try:
                    self.vector_service.update_metadatas(knowledge_col, touched_ids, touched_metas)
                except Exception as err:
                    logger.warning(f"Impossible de mettre à jour la vitalité mémoire: {err}")
            return "\n".join(lines[:top_k])
        except Exception as e:
            logger.warning(f"build_memory_context: {e}")
            return ""

    # ---------- normalisation historique ----------
    def _normalize_history_for_llm(
        self,
        provider: str,
        history: List[Dict],
        rag_context: str = "",
        use_rag: bool = False,
        agent_id: Optional[str] = None,
    ) -> List[Dict]:
        normalized: List[Dict[str, Any]] = []
        if use_rag and rag_context:
            if provider == "google":
                normalized.append({"role": "user", "parts": [f"[RAG_CONTEXT]\n{rag_context}"]})
            else:
                normalized.append({"role": "user", "content": f"[RAG_CONTEXT]\n{rag_context}"})
        for m in history:
            role = m.get("role")
            text = m.get("content") or m.get("message") or ""
            if not text:
                continue
            if provider == "google":
                normalized.append({"role": "user" if role in (Role.USER, "user") else "model", "parts": [text]})
            else:
                normalized.append({"role": "user" if role in (Role.USER, "user") else "assistant", "content": text})
        return normalized

    @staticmethod
    def _normalize_openai_delta_content(raw: Any) -> str:
        """Return normalized text from OpenAI delta content."""
        if raw is None:
            return ""
        if isinstance(raw, str):
            return raw
        if isinstance(raw, list):
            parts: List[str] = []
            for item in raw:
                try:
                    if hasattr(item, 'text'):
                        text_value = getattr(item, 'text')
                    elif isinstance(item, dict):
                        text_value = item.get('text')
                    else:
                        text_value = None
                    if text_value:
                        parts.append(str(text_value))
                except Exception:
                    continue
            return ''.join(parts)
        try:
            return str(raw)
        except Exception:
            return ""

    async def _ensure_async_stream(
        self,
        stream_candidate: Any,
    ) -> AsyncIterator[str]:
        if inspect.isawaitable(stream_candidate):
            stream_candidate = await stream_candidate
        if hasattr(stream_candidate, "__aiter__"):
            return stream_candidate
        raise TypeError("LLM stream must be an awaitable or async iterable")

    # ---------- providers (stream) ----------
    async def _get_llm_response_stream(
        self, provider: str, model: str, system_prompt: str, history: List[Dict], cost_info_container: Dict
    ) -> AsyncGenerator[str, None]:
        if provider == "openai":
            streamer = self._get_openai_stream(model, system_prompt, history, cost_info_container)
        elif provider == "google":
            streamer = self._get_gemini_stream(model, system_prompt, history, cost_info_container)
        elif provider == "anthropic":
            streamer = self._get_anthropic_stream(model, system_prompt, history, cost_info_container)
        else:
            raise ValueError(f"Fournisseur LLM non supporté: {provider}")
        async for chunk in streamer:
            yield chunk

    async def _get_openai_stream(
        self, model: str, system_prompt: str, history: List[Dict[str, Any]], cost_info_container: Dict[str, Any]
    ) -> AsyncGenerator[str, None]:
        messages = [{"role": "system", "content": system_prompt}] + history
        usage_seen = False
        try:
            stream = await self.openai_client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=DEFAULT_TEMPERATURE,
                stream=True,
                stream_options={"include_usage": True},
            )
            async for event in stream:
                try:
                    delta = event.choices[0].delta
                    raw_content = getattr(delta, "content", None)
                    text = self._normalize_openai_delta_content(raw_content)
                    if text:
                        yield text
                except Exception:
                    pass
                usage = getattr(event, "usage", None)
                if usage and not usage_seen:
                    usage_seen = True
                    pricing = MODEL_PRICING.get(model, {"input": 0, "output": 0})
                    in_tok = getattr(usage, "prompt_tokens", 0)
                    out_tok = getattr(usage, "completion_tokens", 0)
                    cost_info_container.update(
                        {
                            "input_tokens": in_tok,
                            "output_tokens": out_tok,
                            "total_cost": (in_tok * pricing["input"]) + (out_tok * pricing["output"]),
                        }
                    )
        except Exception as e:
            logger.error(f"OpenAI stream error: {e}", exc_info=True)
            raise

    async def _get_gemini_stream(
        self, model: str, system_prompt: str, history: List[Dict[str, Any]], cost_info_container: Dict[str, Any]
    ) -> AsyncGenerator[str, None]:
        try:
            model_instance = genai.GenerativeModel(model_name=model, system_instruction=system_prompt)
            resp = await model_instance.generate_content_async(
                history, stream=True, generation_config={"temperature": DEFAULT_TEMPERATURE}
            )
            async for chunk in resp:
                try:
                    text = getattr(chunk, "text", None)
                    if not text and getattr(chunk, "candidates", None):
                        cand = chunk.candidates[0]
                        if getattr(cand, "content", None) and getattr(cand.content, "parts", None):
                            text = "".join([getattr(p, "text", "") or str(p) for p in cand.content.parts if p])
                    if text:
                        yield text
                except Exception:
                    pass
            # Gemini: coût non renvoyé en stream ? placeholders
            cost_info_container.setdefault("input_tokens", 0)
            cost_info_container.setdefault("output_tokens", 0)
            cost_info_container.setdefault("total_cost", 0.0)
        except Exception as e:
            logger.error(f"Gemini stream error: {e}", exc_info=True)
            raise

    async def _get_anthropic_stream(
        self, model: str, system_prompt: str, history: List[Dict[str, Any]], cost_info_container: Dict[str, Any]
    ) -> AsyncGenerator[str, None]:
        try:
            history_params = cast(List[MessageParam], history)
            async with self.anthropic_client.messages.stream(
                model=model,
                max_tokens=1500,
                temperature=DEFAULT_TEMPERATURE,
                system=system_prompt,
                messages=history_params,
            ) as stream:
                async for event in stream:
                    try:
                        if getattr(event, "type", "") == "content_block_delta":
                            delta = getattr(event, "delta", None)
                            if delta:
                                text = getattr(delta, "text", "") or ""
                                if text:
                                    yield text
                    except Exception:
                        pass
                try:
                    final = await stream.get_final_message()
                    usage = getattr(final, "usage", None)
                    if usage:
                        pricing = MODEL_PRICING.get(model, {"input": 0, "output": 0})
                        in_tok = getattr(usage, "input_tokens", 0)
                        out_tok = getattr(usage, "output_tokens", 0)
                        cost_info_container.update(
                            {
                                "input_tokens": in_tok,
                                "output_tokens": out_tok,
                                "total_cost": (in_tok * pricing["input"]) + (out_tok * pricing["output"]),
                            }
                        )
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"Anthropic stream error: {e}", exc_info=True)
            raise

    # ---------- réponses structurées ----------
    async def get_structured_llm_response(self, agent_id: str, prompt: str, json_schema: Dict[str, Any]) -> Dict[str, Any]:
        provider, model, system_prompt = self._get_agent_config(agent_id)
        system_prompt = self._ensure_fr_tutoiement(agent_id, provider, system_prompt)
        if provider == "google":
            model_instance = genai.GenerativeModel(model_name=model, system_instruction=system_prompt)
            schema_hint = json.dumps(json_schema, ensure_ascii=False)
            full_prompt = (
                f"{prompt}\n\nIMPORTANT: Réponds EXCLUSIVEMENT en JSON valide correspondant strictement à ce SCHÉMA : {schema_hint}"
            )
            google_resp = await model_instance.generate_content_async([{"role": "user", "parts": [full_prompt]}])
            text = getattr(google_resp, "text", "") or ""
            try:
                return json.loads(text) if text else {}
            except Exception:
                m = re.search(r"\{.*\}", text, re.S)
                return json.loads(m.group(0)) if m else {}
        elif provider == "openai":
            openai_resp = await self.openai_client.chat.completions.create(
                model=model,
                temperature=0,
                response_format={"type": "json_object"},
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}],
            )
            content = (openai_resp.choices[0].message.content or "").strip()
            return json.loads(content) if content else {}
        elif provider == "anthropic":
            anthropic_resp = await self.anthropic_client.messages.create(
                model=model,
                max_tokens=1500,
                temperature=0,
                system=system_prompt + "\n\nRéponds strictement en JSON valide.",
                messages=[{"role": "user", "content": prompt}],
            )
            text = ""
            for block in getattr(anthropic_resp, "content", []) or []:
                t = getattr(block, "text", "") or ""
                if t:
                    text += t
            try:
                return json.loads(text)
            except Exception:
                m = re.search(r"\{.*\}", text, re.S)
                return json.loads(m.group(0)) if m else {}
        return {}

    # ---------- pipeline chat (stream) ----------
    async def _process_agent_response_stream(
        self,
        session_id: str,
        agent_id: str,
        use_rag: bool,
        connection_manager: ConnectionManager,
        doc_ids: Optional[List[int]] = None,
        origin_agent_id: Optional[str] = None,
        opinion_request: Optional[Dict[str, Any]] = None,
    ):
        temp_message_id = str(uuid4())
        full_response_text = ""
        cost_info_container: Dict[str, Any] = {}
        model_used = ""
        rag_sources: List[Dict[str, Any]] = []
        uid = self._try_get_user_id(session_id)

        origin = (origin_agent_id or "").strip().lower()
        is_broadcast = origin == "global"

        try:
            start_payload = {"agent_id": agent_id, "id": temp_message_id}
            if opinion_request:
                opinion_meta = dict(opinion_request.get("opinion_meta") or {})
                if opinion_request.get("source_agent_id") is not None:
                    opinion_meta.setdefault("source_agent_id", opinion_request.get("source_agent_id"))
                if opinion_request.get("target_message_id") is not None:
                    opinion_meta.setdefault("target_message_id", opinion_request.get("target_message_id"))
                if opinion_request.get("request_note_id"):
                    opinion_meta.setdefault("request_note_id", opinion_request.get("request_note_id"))
                if opinion_meta.get("request_id") and not opinion_meta.get("request_note_id"):
                    opinion_meta.setdefault("request_note_id", opinion_meta.get("request_id"))
                opinion_meta.setdefault("reviewer_agent_id", agent_id)
                opinion_meta.setdefault("agent_id", agent_id)
                start_payload["meta"] = {"opinion": opinion_meta}
            if is_broadcast:
                start_payload["broadcast_origin"] = origin
            await connection_manager.send_personal_message(
                {"type": "ws:chat_stream_start", "payload": start_payload}, session_id
            )

            raw_history = self.session_manager.get_full_history(session_id) or []
            history = [self._message_to_dict(m) for m in raw_history if m is not None]

            if opinion_request:
                instruction_text = (opinion_request.get("instruction") or "").strip()
                if instruction_text:
                    history.append({"role": Role.USER.value, "content": instruction_text})

            last_user_message_obj = next(
                (m for m in reversed(history) if self._is_user_role(m.get("role"))),
                None,
            )
            last_user_message = ""
            if last_user_message_obj:
                last_user_message = (
                    str(last_user_message_obj.get("content") or last_user_message_obj.get("message") or "")
                ).strip()

            selected_doc_ids = self._sanitize_doc_ids(doc_ids)
            if not selected_doc_ids and isinstance(last_user_message_obj, dict):
                selected_doc_ids = self._sanitize_doc_ids(last_user_message_obj.get("doc_ids"))

            thread_id = None
            try:
                thread_id = self.session_manager.get_thread_id_for_session(session_id)
            except Exception:
                thread_id = None

            uid = self._try_get_user_id(session_id)

            allowed_doc_ids: List[int] = []
            if thread_id:
                try:
                    rows = await queries.get_thread_docs(
                        self.session_manager.db_manager,
                        thread_id,
                        session_id,
                        user_id=uid,
                    )
                    for row in rows:
                        raw = row.get("doc_id")
                        if raw is None:
                            continue
                        try:
                            value = int(raw)
                        except (TypeError, ValueError):
                            continue
                        if value not in allowed_doc_ids:
                            allowed_doc_ids.append(value)
                except Exception as fetch_err:
                    logger.warning(
                        "Unable to fetch thread docs for %s: %s",
                        thread_id,
                        fetch_err,
                    )

            if allowed_doc_ids:
                filtered_doc_ids = [doc_id for doc_id in selected_doc_ids if doc_id in allowed_doc_ids]
                if selected_doc_ids and not filtered_doc_ids:
                    logger.info(
                        "Selected doc IDs are outside thread scope (session=%s thread=%s ids=%s)",
                        session_id,
                        thread_id,
                        selected_doc_ids,
                    )
                if not filtered_doc_ids:
                    filtered_doc_ids = allowed_doc_ids
                selected_doc_ids = filtered_doc_ids

            # Mot-code court-circuit
            if self._is_mot_code_query(last_user_message):
                mot_uid = uid or self._try_get_user_id(session_id)
                mot = self._fetch_mot_code_for_agent(agent_id, mot_uid)
                try:
                    stm_here = self._try_get_session_summary(session_id)
                    await connection_manager.send_personal_message(
                        {
                            "type": "ws:memory_banner",
                            "payload": {
                                "agent_id": agent_id,
                                "has_stm": bool(stm_here),
                                "ltm_items": 0,
                                "injected_into_prompt": False,
                            },
                        },
                        session_id,
                    )
                except Exception:
                    pass

                if mot:
                    final_agent_message = AgentMessage(
                        id=temp_message_id,
                        session_id=session_id,
                        role=Role.ASSISTANT,
                        agent=agent_id,
                        message=mot,
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        cost_info={},
                    )
                    await self.session_manager.add_message_to_session(session_id, final_agent_message)
                    payload = final_agent_message.model_dump(mode="json")
                    payload["agent_id"] = agent_id
                    if "message" in payload:
                        payload["content"] = payload.pop("message")
                    payload.setdefault("meta", {"provider": "memory", "model": "mot-code", "fallback": False})
                    await connection_manager.send_personal_message(
                        {"type": "ws:chat_stream_end", "payload": payload}, session_id
                    )
                    if os.getenv("EMERGENCE_AUTO_TEND", "1") != "0":
                        try:
                            db_manager = getattr(self.session_manager, "db_manager", None)
                            analyzer = getattr(self.session_manager, "memory_analyzer", None)
                            if db_manager and analyzer:
                                gardener = MemoryGardener(
                                    db_manager=db_manager,
                                    vector_service=self.vector_service,
                                    memory_analyzer=analyzer,
                                )
                                asyncio.create_task(
                                    gardener.tend_the_garden(
                                        consolidation_limit=3,
                                        session_id=session_id,
                                        user_id=mot_uid,
                                    )
                                )
                        except Exception:
                            pass
                    return

            # Mémoire (STM/LTM)
            stm = self._try_get_session_summary(session_id)
            ltm_block = (
                await self._build_memory_context(session_id, last_user_message, top_k=5, agent_id=agent_id)
                if last_user_message
                else ""
            )

            if use_rag:
                memory_context = self._merge_blocks([("Résumé de session", stm)]) if stm else ""
                ltm_count_for_banner = self._count_bullets(ltm_block)
            else:
                memory_context = self._merge_blocks([("Résumé de session", stm), ("Faits & souvenirs", ltm_block)])
                ltm_count_for_banner = self._count_bullets(ltm_block)

            injected = bool(memory_context and memory_context.strip())
            if injected:
                history = [{"role": Role.USER.value, "content": f"[MEMORY_CONTEXT]\n{memory_context}"}] + history

            try:
                await connection_manager.send_personal_message(
                    {
                        "type": "ws:memory_banner",
                        "payload": {
                            "agent_id": agent_id,
                            "has_stm": bool(stm),
                            "ltm_items": int(ltm_count_for_banner),
                            "injected_into_prompt": bool(injected),
                        },
                    },
                    session_id,
                )
            except Exception:
                pass

            # RAG documents
            rag_context = ""
            should_search_docs = bool(use_rag and (last_user_message or selected_doc_ids))
            if should_search_docs:
                await connection_manager.send_personal_message(
                    {"type": "ws:rag_status", "payload": {"status": "searching", "agent_id": agent_id}}, session_id
                )
                if self._doc_collection is None:
                    self._doc_collection = self.vector_service.get_or_create_collection(config.DOCUMENT_COLLECTION_NAME)

                base_clauses: List[Dict[str, Any]] = [{"session_id": session_id}]
                if uid:
                    base_clauses.append({"user_id": uid})

                where_clauses: List[Dict[str, Any]] = list(base_clauses)
                if selected_doc_ids:
                    if len(selected_doc_ids) == 1:
                        doc_filter: Dict[str, Any] = {"document_id": selected_doc_ids[0]}
                    else:
                        doc_filter = {"$or": [{"document_id": did} for did in selected_doc_ids]}
                    where_clauses.append(doc_filter)

                if not where_clauses:
                    where_filter: Optional[Dict[str, Any]] = None
                elif len(where_clauses) == 1:
                    where_filter = where_clauses[0]
                else:
                    where_filter = {"$and": where_clauses}

                query_text = (last_user_message or "").strip()
                if not query_text and selected_doc_ids:
                    query_text = " ".join(f"document:{doc_id}" for doc_id in selected_doc_ids) or "selected documents"

                doc_hits = self.vector_service.query(
                    collection=self._doc_collection,
                    query_text=query_text or " ",
                    where_filter=where_filter,
                )

                rag_sources = []
                for h in (doc_hits or []):
                    md = h.get("metadata") or {}
                    excerpt = (h.get("text") or "").strip()
                    if excerpt:
                        excerpt = excerpt[:220].rstrip()
                    rag_sources.append(
                        {
                            "document_id": md.get("document_id"),
                            "filename": md.get("filename"),
                            "page": md.get("page"),
                            "excerpt": excerpt,
                        }
                    )

                if allowed_doc_ids:
                    filtered_sources: List[Dict[str, Any]] = []
                    for source in rag_sources:
                        raw_doc_id = source.get("document_id")
                        if isinstance(raw_doc_id, (str, int)):
                            try:
                                doc_id_int = int(raw_doc_id)
                            except (TypeError, ValueError):
                                doc_id_int = None
                        else:
                            doc_id_int = None
                        if doc_id_int is None or doc_id_int in allowed_doc_ids:
                            filtered_sources.append(source)
                    rag_sources = filtered_sources

                doc_block = (
                    "\n\n".join([f"- {h['text']}" for h in (doc_hits or []) if h.get("text")]) if doc_hits else ""
                )
                mem_block = await self._build_memory_context(session_id, last_user_message, agent_id=agent_id)
                rag_context = self._merge_blocks(
                    [("Mémoire (concepts clés)", mem_block), ("Documents pertinents", doc_block)]
                )
                await connection_manager.send_personal_message(
                    {"type": "ws:rag_status", "payload": {"status": "found", "agent_id": agent_id}}, session_id
                )

            raw_concat = "\n".join([(m.get("content") or m.get("message", "")) for m in history])
            raw_tokens = self._extract_sensitive_tokens(raw_concat)
            await connection_manager.send_personal_message(
                {
                    "type": "ws:debug_context",
                    "payload": {
                        "phase": "before_normalize",
                        "agent_id": agent_id,
                        "use_rag": use_rag,
                        "history_total": len(history),
                        "rag_context_chars": len(rag_context),
                        "off_policy": self.off_history_policy,
                        "sensitive_tokens_in_history": list(set(raw_tokens)),
                    },
                },
                session_id,
            )

            provider, model, system_prompt = self._get_agent_config(agent_id)
            primary_provider, primary_model = provider, model
            system_prompt = self._ensure_fr_tutoiement(agent_id, provider, system_prompt)
            model_used = primary_model

            # Récupération du nom de fichier du prompt pour debug UI
            bundle = self.prompts.get(agent_id) or self.prompts.get(agent_id.replace("_lite", "")) or {}
            prompt_file = bundle.get("file", "")

            try:
                await connection_manager.send_personal_message(
                    {
                        "type": "ws:model_info",
                        "payload": {
                            "agent_id": agent_id,
                            "id": temp_message_id,
                            "provider": primary_provider,
                            "model": primary_model,
                            "prompt_file": prompt_file,
                        },
                    },
                    session_id,
                )
            except Exception:
                pass
            logger.info(
                json.dumps(
                    {
                        "event": "model_info",
                        "agent_id": agent_id,
                        "session_id": session_id,
                        "provider": primary_provider,
                        "model": primary_model,
                        "prompt_file": prompt_file,
                    }
                )
            )

            normalized_history = self._normalize_history_for_llm(
                provider, history, rag_context, use_rag, agent_id
            )

            norm_concat = "\n".join(
                ["".join(p.get("parts", [])) if provider == "google" else p.get("content", "") for p in normalized_history]
            )
            norm_tokens = self._extract_sensitive_tokens(norm_concat)
            await connection_manager.send_personal_message(
                {
                    "type": "ws:debug_context",
                    "payload": {
                        "phase": "after_normalize",
                        "agent_id": agent_id,
                        "use_rag": use_rag,
                        "history_filtered": len(normalized_history),
                        "rag_context_chars": len(rag_context),
                        "off_policy": self.off_history_policy,
                        "sensitive_tokens_in_prompt": list(set(norm_tokens)),
                    },
                },
                session_id,
            )

            async def _stream_with(provider_name, model_name, hist):
                return await self._ensure_async_stream(
                    self._get_llm_response_stream(
                        provider_name, model_name, system_prompt, hist, cost_info_container
                    )
                )
            success = False
            try:
                async for chunk in (await _stream_with(primary_provider, primary_model, normalized_history)):
                    if not chunk:
                        continue
                    new_total, delta = self._compute_chunk_delta(full_response_text, chunk)
                    full_response_text = new_total
                    if not delta:
                        continue
                    try:
                        logger.info("chunk_debug primary raw=%r delta=%r", chunk, delta)
                    except Exception:
                        pass
                    chunk_payload = {"agent_id": agent_id, "id": temp_message_id, "chunk": delta}
                    if is_broadcast:
                        chunk_payload["broadcast_origin"] = origin
                    await connection_manager.send_personal_message(
                        {"type": "ws:chat_stream_chunk", "payload": chunk_payload},
                        session_id,
                    )
                model_used = primary_model
                success = True
            except Exception as e_primary:
                fallback_sequence = CHAT_PROVIDER_FALLBACKS.get(primary_provider, [])
                last_error = e_primary
                for prov2, model2 in fallback_sequence:
                    if prov2 == primary_provider:
                        continue
                    try:
                        await connection_manager.send_personal_message(
                            {
                                "type": "ws:model_fallback",
                                "payload": {
                                    "agent_id": agent_id,
                                    "id": temp_message_id,
                                    "from_provider": primary_provider,
                                    "from_model": primary_model,
                                    "to_provider": prov2,
                                    "to_model": model2,
                                    "reason": str(e_primary),
                                },
                            },
                            session_id,
                        )
                    except Exception:
                        pass
                    logger.warning(
                        json.dumps(
                            {
                                "event": "model_fallback",
                                "agent_id": agent_id,
                                "session_id": session_id,
                                "from_provider": primary_provider,
                                "from_model": primary_model,
                                "to_provider": prov2,
                                "to_model": model2,
                                "reason": str(e_primary),
                            }
                        )
                    )

                    norm2 = self._normalize_history_for_llm(prov2, history, rag_context, use_rag, agent_id)
                    try:
                        async for chunk in (await _stream_with(prov2, model2, norm2)):
                            if not chunk:
                                continue
                            new_total, delta = self._compute_chunk_delta(full_response_text, chunk)
                            full_response_text = new_total
                            if not delta:
                                continue
                            try:
                                logger.info("chunk_debug fallback raw=%r delta=%r", chunk, delta)
                            except Exception:
                                pass
                            chunk_payload = {"agent_id": agent_id, "id": temp_message_id, "chunk": delta}
                            if is_broadcast:
                                chunk_payload["broadcast_origin"] = origin
                            await connection_manager.send_personal_message(
                                {
                                    "type": "ws:chat_stream_chunk",
                                    "payload": chunk_payload,
                                },
                                session_id,
                            )
                        provider = prov2
                        model_used = model2
                        success = True
                        break
                    except Exception as e2:
                        last_error = e2
                        continue

                if not success:
                    raise last_error

            thread_id = None
            try:
                thread_id = self.session_manager.get_thread_id_for_session(session_id)
            except Exception:
                thread_id = None

            final_agent_message = AgentMessage(
                id=temp_message_id,
                session_id=session_id,
                role=Role.ASSISTANT,
                agent=agent_id,
                message=full_response_text,
                timestamp=datetime.now(timezone.utc).isoformat(),
                cost_info=cost_info_container,
            )
            message_meta = {
                "provider": provider,
                "model": model_used,
                "fallback": bool(provider != primary_provider),
                "persisted_by": "backend",
                "persisted_via": "ws",
                "thread_id": thread_id,
            }
            if opinion_request:
                opinion_meta = dict(opinion_request.get("opinion_meta") or {})
                if opinion_request.get("source_agent_id") is not None:
                    opinion_meta.setdefault("source_agent_id", opinion_request.get("source_agent_id"))
                if opinion_request.get("target_message_id") is not None:
                    opinion_meta.setdefault("target_message_id", opinion_request.get("target_message_id"))
                if opinion_request.get("request_note_id"):
                    opinion_meta.setdefault("request_note_id", opinion_request.get("request_note_id"))
                if opinion_meta.get("request_id") and not opinion_meta.get("request_note_id"):
                    opinion_meta.setdefault("request_note_id", opinion_meta.get("request_id"))
                opinion_meta.setdefault("reviewer_agent_id", agent_id)
                opinion_meta.setdefault("agent_id", agent_id)
                message_meta["opinion"] = opinion_meta
            if is_broadcast:
                message_meta["broadcast_origin"] = origin
                message_meta["source_agent"] = agent_id
            if selected_doc_ids:
                try:
                    message_meta["selected_doc_ids"] = selected_doc_ids
                except Exception:
                    pass
            if use_rag and rag_sources:
                try:
                    message_meta["sources"] = rag_sources
                except Exception:
                    pass
            final_agent_message.meta = message_meta
            await self.session_manager.add_message_to_session(session_id, final_agent_message)
            await self.cost_tracker.record_cost(
                agent=agent_id,
                model=model_used,
                input_tokens=cost_info_container.get("input_tokens", 0),
                output_tokens=cost_info_container.get("output_tokens", 0),
                total_cost=cost_info_container.get("total_cost", 0.0),
                feature="chat",
                session_id=session_id,
                user_id=uid,
            )
            payload = final_agent_message.model_dump(mode="json")
            payload["agent_id"] = agent_id
            if "message" in payload:
                payload["content"] = payload.pop("message")
            payload["meta"] = dict(message_meta)
            if is_broadcast:
                payload["meta"]["broadcast_origin"] = origin
                payload["meta"]["source_agent"] = agent_id
            if selected_doc_ids:
                try:
                    payload["meta"]["selected_doc_ids"] = selected_doc_ids
                except Exception:
                    pass
            try:
                if use_rag and rag_sources:
                    payload["meta"]["sources"] = rag_sources
            except Exception:
                pass

            if is_broadcast:
                payload["broadcast_origin"] = origin
            await connection_manager.send_personal_message(
                {"type": "ws:chat_stream_end", "payload": payload}, session_id
            )

            if os.getenv("EMERGENCE_AUTO_TEND", "1") != "0":
                db_manager = getattr(self.session_manager, "db_manager", None)
                analyzer = getattr(self.session_manager, "memory_analyzer", None)
                if db_manager and analyzer:
                    try:
                        gardener = MemoryGardener(
                            db_manager=db_manager,
                            vector_service=self.vector_service,
                            memory_analyzer=analyzer,
                        )
                        asyncio.create_task(
                            gardener.tend_the_garden(
                                consolidation_limit=3,
                                thread_id=thread_id,
                                session_id=session_id,
                                user_id=uid or self._try_get_user_id(session_id),
                            )
                        )
                    except Exception:
                        pass

        except Exception as e:
            logger.error(f"Erreur streaming {agent_id}: {e}", exc_info=True)
            try:
                await connection_manager.send_personal_message(
                    {"type": "ws:error", "payload": {"message": f"Erreur interne pour l'agent {agent_id}: {e}"}},
                    session_id,
                )
            except Exception as send_error:
                logger.error(
                    f"Impossible d'envoyer l'erreur au client (session {session_id}): {send_error}", exc_info=True
                )

    # ===========================
    # Débat (non-stream, async)
    # ===========================
    async def get_llm_response_for_debate(
        self,
        agent_id: str,
        prompt: str,
        *,
        system_override: Optional[str] = None,
        use_rag: bool = False,
        session_id: Optional[str] = None,
        history: Optional[List[Any]] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        doc_ids: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """
        Réponse unique pour le pipeline Débat (non-stream).
        Retourne: {"text": str, "provider": str, "model": str, "fallback": bool, "cost_info": {...}}
        """
        provider, model, system_prompt = self._get_agent_config(agent_id)
        system_prompt = self._ensure_fr_tutoiement(agent_id, provider, system_override or system_prompt)

        rag_context = ""
        base_prompt = prompt or ""
        selected_doc_ids = self._sanitize_doc_ids(doc_ids)

        if use_rag and session_id and base_prompt:
            try:
                if self._doc_collection is None:
                    self._doc_collection = self.vector_service.get_or_create_collection(
                        config.DOCUMENT_COLLECTION_NAME
                    )
                base_clauses: List[Dict[str, Any]] = [{"session_id": session_id}]
                uid = self._try_get_user_id(session_id)
                if uid:
                    base_clauses.append({"user_id": uid})

                where_clauses: List[Dict[str, Any]] = list(base_clauses)
                if selected_doc_ids:
                    if len(selected_doc_ids) == 1:
                        doc_filter: Dict[str, Any] = {"document_id": selected_doc_ids[0]}
                    else:
                        doc_filter = {"$or": [{"document_id": did} for did in selected_doc_ids]}
                    where_clauses.append(doc_filter)

                if not where_clauses:
                    where_filter: Optional[Dict[str, Any]] = None
                elif len(where_clauses) == 1:
                    where_filter = where_clauses[0]
                else:
                    where_filter = {"$and": where_clauses}

                doc_hits = self.vector_service.query(
                    collection=self._doc_collection,
                    query_text=base_prompt,
                    where_filter=where_filter,
                )
                doc_block = "\n".join(
                    [f"- {h.get('text', '').strip()}" for h in (doc_hits or []) if h.get("text")]
                )
                if doc_block.strip():
                    rag_context = self._merge_blocks([("Documents pertinents", doc_block)])
            except Exception:
                pass

        raw_history: List[Dict[str, Any]] = []
        if history:
            for item in history:
                try:
                    if isinstance(item, ChatMessage):
                        raw_history.append({"role": item.role, "content": item.content})
                    elif isinstance(item, dict):
                        role = item.get("role")
                        content = item.get("content") or item.get("message")
                        if role and content:
                            raw_history.append({"role": role, "content": content})
                except Exception:
                    continue
        raw_history.append({"role": Role.USER, "content": base_prompt})

        async def run_once(provider_name: str, model_name: str) -> Tuple[str, Dict[str, Any]]:
            normalized = self._normalize_history_for_llm(
                provider_name,
                raw_history,
                rag_context,
                use_rag,
                agent_id,
            )
            local_cost: Dict[str, Any] = {}
            chunks: List[str] = []
            stream_iter = await self._ensure_async_stream(
                self._get_llm_response_stream(
                    provider_name,
                    model_name,
                    system_prompt,
                    normalized,
                    local_cost,
                )
            )
            async for chunk in stream_iter:
                if chunk:
                    chunks.append(chunk)
            return "".join(chunks), local_cost

        primary_provider, primary_model = provider, model
        provider_used = primary_provider
        model_used = primary_model
        fallback_used = False
        text = ""
        cost_info: Dict[str, Any] = {}

        try:
            text, cost_info = await run_once(primary_provider, primary_model)
        except Exception as e_primary:
            fallback_sequence = CHAT_PROVIDER_FALLBACKS.get(primary_provider, [])
            last_error: Exception = e_primary
            for prov2, model2 in fallback_sequence:
                if prov2 == primary_provider:
                    continue
                try:
                    text, cost_info = await run_once(prov2, model2)
                    provider_used = prov2
                    model_used = model2
                    fallback_used = True
                    logger.warning(
                        json.dumps(
                            {
                                "event": "model_fallback",
                                "agent_id": agent_id,
                                "session_id": session_id,
                                "from_provider": primary_provider,
                                "from_model": primary_model,
                                "to_provider": prov2,
                                "to_model": model2,
                                "reason": str(e_primary),
                            }
                        )
                    )
                    break
                except Exception as e2:
                    last_error = e2
                    continue
            else:
                logger.error(
                    f"get_llm_response_for_debate error (agent={agent_id}, provider={primary_provider}): {last_error}",
                    exc_info=True,
                )
                raise last_error

        if not isinstance(cost_info, dict):
            cost_info = {}
        cost_info.setdefault("input_tokens", 0)
        cost_info.setdefault("output_tokens", 0)
        cost_info.setdefault("total_cost", 0.0)

        try:
            if self.cost_tracker:
                await self.cost_tracker.record_cost(
                    agent=agent_id,
                    model=model_used,
                    input_tokens=int(cost_info.get("input_tokens", 0) or 0),
                    output_tokens=int(cost_info.get("output_tokens", 0) or 0),
                    total_cost=float(cost_info.get("total_cost", 0.0) or 0.0),
                    feature="debate",
                )
        except Exception:
            logger.debug("Impossible d'enregistrer le coût du débat", exc_info=True)

        return {
            "text": text.strip(),
            "provider": provider_used,
            "model": model_used,
            "fallback": fallback_used,
            "cost_info": cost_info,
        }


    # ---------- entrypoint WS ----------
    def process_user_message_for_agents(
        self,
        session_id: str,
        chat_request: Any,
        connection_manager: Optional[ConnectionManager] = None,
    ) -> None:
        def _get_value(key: str):
            if isinstance(chat_request, dict):
                return chat_request.get(key)
            return getattr(chat_request, key, None)

        agent_id = (_get_value('agent_id') or '').strip().lower()
        use_rag = bool(_get_value('use_rag'))
        doc_ids = self._sanitize_doc_ids(_get_value('doc_ids'))
        cm = connection_manager or getattr(self.session_manager, 'connection_manager', None)

        if not agent_id:
            logger.error('process_user_message_for_agents: agent_id manquant')
            return
        if cm is None:
            logger.error('process_user_message_for_agents: connection_manager manquant')
            return

        if agent_id == 'global':
            targets = [aid for aid in dict.fromkeys(self.broadcast_agents) if aid and aid != 'global']
            if not targets:
                targets = ['anima', 'neo', 'nexus']
            origin_marker = 'global'
        else:
            targets = [agent_id]
            origin_marker = None

        for target_agent in targets:
            asyncio.create_task(
                self._process_agent_response_stream(
                    session_id,
                    target_agent,
                    use_rag,
                    cm,
                    doc_ids=list(doc_ids or []),
                    origin_agent_id=origin_marker,
                    opinion_request=None,
                )
            )



    def _build_opinion_instruction(
        self,
        *,
        target_agent_id: str,
        source_agent_id: Optional[str],
        message_text: str,
        user_prompt: Optional[str],
    ) -> str:
        target = (target_agent_id or "").strip().lower() or "anima"
        source = (source_agent_id or "").strip().lower()
        source_display = f"l'agent {source}" if source else "l'autre agent"
        answer = (message_text or "").strip()
        prompt = (user_prompt or "").strip()

        instruction_parts = [
            f"Tu es l'agent {target} d'Émergence. On sollicite ton avis expert sur la réponse ci-dessous fournie par {source_display}.",
            "Analyse la réponse pour vérifier sa justesse, sa pertinence et les éléments manquants. Rédige ton avis en français, dans le style propre à ton agent.",
            "Structure ta réponse en trois sections courtes :",
            "1. Lecture rapide : une phrase qui résume ton jugement global.",
            "2. Points solides : liste de points exacts ou utiles.",
            "3. Points à corriger : liste de corrections, risques ou compléments nécessaires.",
            "Termine par une recommandation actionnable (1 phrase).",
        ]

        if prompt:
            instruction_parts.extend(
                [
                    "Question utilisateur initiale :",
                    "<<<QUESTION>>>",
                    prompt,
                    "<<<FIN_QUESTION>>>",
                ]
            )

        if answer:
            instruction_parts.extend(
                [
                    "Réponse analysée :",
                    "<<<REPONSE>>>",
                    answer,
                    "<<<FIN_REPONSE>>>",
                ]
            )
        else:
            instruction_parts.append("Réponse analysée : (contenu vide)")

        if source:
            instruction_parts.append(
                f"Indique clairement si tu n'es pas d'accord avec {source} et propose une alternative concrète."
            )

        return "\n".join(part for part in instruction_parts if part)



    async def request_opinion(
        self,
        session_id: str,
        target_agent_id: str,
        source_agent_id: Optional[str],
        message_id: Optional[str],
        message_text: Optional[str],
        connection_manager: ConnectionManager,
        request_id: Optional[str] = None,
    ) -> None:
        target = (target_agent_id or '').strip().lower()
        if not target:
            logger.error('request_opinion: target agent missing')
            return
        if target == 'global':
            logger.warning('request_opinion: target agent "global" invalid, fallback anima')
            target = 'anima'
        if target not in self.broadcast_agents and target not in {'anima', 'neo', 'nexus'}:
            await connection_manager.send_personal_message(
                {
                    'type': 'ws:error',
                    'payload': {'message': f"Agent {target_agent_id!r} indisponible pour un avis."},
                },
                session_id,
            )
            return

        clean_source = (source_agent_id or '').strip().lower() or None

        original_message = None
        if message_id:
            try:
                original_message = self.session_manager.get_message_by_id(session_id, message_id)
            except Exception:
                original_message = None

        content = (message_text or '').strip()
        if not content and isinstance(original_message, dict):
            content = str(
                original_message.get('content')
                or original_message.get('message')
                or ''
            ).strip()

        if not content:
            await connection_manager.send_personal_message(
                {
                    'type': 'ws:error',
                    'payload': {'message': "Impossible de récupérer la réponse à analyser."},
                },
                session_id,
            )
            return

        user_prompt = None
        try:
            history = self.session_manager.get_full_history(session_id) or []
            if message_id and history:
                for idx, item in enumerate(history):
                    if not item:
                        continue
                    try:
                        if str(item.get('id')) == str(message_id):
                            for previous in reversed(history[:idx]):
                                if previous and str(previous.get('role') or '').lower().endswith('user'):
                                    user_prompt = (
                                        str(previous.get('content') or previous.get('message') or '')
                                    ).strip()
                                    if user_prompt:
                                        break
                            break
                    except Exception:
                        continue
        except Exception:
            user_prompt = None

        candidate_note_id = request_id or ""
        if isinstance(candidate_note_id, bytes):
            candidate_note_id = candidate_note_id.decode("utf-8", "ignore")
        note_id = str(candidate_note_id).strip() if candidate_note_id else ""
        if len(note_id) > 256:
            note_id = note_id[:256]
        note_id = note_id or str(uuid4())

        request_display = f"Avis demandé à {target} sur la réponse de {clean_source or 'cet agent'}."
        user_note = ChatMessage(
            id=note_id,
            session_id=session_id,
            role=Role.USER,
            agent=target,
            content=request_display,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        user_note.meta = {
            "opinion_request": {
                "target_agent": target,
                "source_agent": clean_source,
                "requested_message_id": message_id,
                "request_id": note_id,
            }
        }
        try:
            await self.session_manager.add_message_to_session(session_id, user_note)
        except Exception:
            logger.warning('request_opinion: unable to persist user note for request', exc_info=True)

        instruction = self._build_opinion_instruction(
            target_agent_id=target,
            source_agent_id=clean_source,
            message_text=content,
            user_prompt=user_prompt,
        )

        opinion_meta = {
            'of_message_id': message_id,
            'source_agent_id': clean_source,
            'requested_at': datetime.now(timezone.utc).isoformat(),
            'request_note_id': note_id,
            'request_id': note_id,
            'reviewer_agent_id': target,
        }

        await self._process_agent_response_stream(
            session_id=session_id,
            agent_id=target,
            use_rag=False,
            connection_manager=connection_manager,
            doc_ids=[],
            origin_agent_id=None,
            opinion_request={
                "instruction": instruction,
                "opinion_meta": opinion_meta,
                "source_agent_id": clean_source,
                "target_message_id": message_id,
                "request_note_id": note_id,
            },
        )

    @staticmethod
    def _sanitize_doc_ids(raw_doc_ids: Any) -> List[int]:
        if raw_doc_ids is None:
            return []
        if isinstance(raw_doc_ids, (set, tuple)):
            raw_doc_ids = list(raw_doc_ids)
        elif not isinstance(raw_doc_ids, list):
            raw_doc_ids = [raw_doc_ids]

        sanitized: List[int] = []
        for item in raw_doc_ids:
            if item in (None, ""):
                continue
            try:
                value = int(str(item).strip())
            except (ValueError, TypeError):
                continue
            sanitized.append(value)

        unique: List[int] = []
        seen = set()
        for value in sanitized:
            if value in seen:
                continue
            seen.add(value)
            unique.append(value)
        return unique

    @staticmethod
    def _compute_chunk_delta(previous_text: str, raw_chunk: Optional[str]) -> Tuple[str, str]:
        if raw_chunk is None:
            return previous_text, ""
        try:
            chunk = str(raw_chunk)
        except Exception:
            chunk = ""
        if not chunk:
            return previous_text, ""
        if not previous_text:
            return chunk, chunk
        if chunk == previous_text:
            return previous_text, ""
        if chunk.startswith(previous_text):
            return chunk, chunk[len(previous_text):]
        if previous_text.startswith(chunk):
            return previous_text, ""
        if previous_text.endswith(chunk):
            return previous_text, ""

        max_overlap = min(len(chunk), len(previous_text))
        overlap = 0
        for size in range(max_overlap, 0, -1):
            if previous_text.endswith(chunk[:size]):
                overlap = size
                break
        if overlap:
            delta = chunk[overlap:]
            if not delta:
                return previous_text, ""
            return previous_text + delta, delta

        return previous_text + chunk, chunk

    # ---------- diverses ----------
    def _count_bullets(self, text: str) -> int:
        return sum(1 for line in (text or "").splitlines() if line.strip().startswith("- "))

