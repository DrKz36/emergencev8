# src/backend/features/chat/service.py
# V29.7 – Gemini 'model_name' ok, Anthropic guard (no key => disabled),
# dynamic fallbacks, RAG sources WS, coûts unifiés. UTF-8 (CRLF conseillé sous Windows).

import os
import re
import glob
import json
import asyncio
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple
from uuid import uuid4
from pathlib import Path
from datetime import datetime, timezone

import google.generativeai as genai
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic

from backend.core.session_manager import SessionManager
from backend.core.cost_tracker import CostTracker
from backend.core.websocket import ConnectionManager
from backend.shared.models import AgentMessage, Role, ChatMessage
from backend.features.memory.vector_service import VectorService
from backend.shared.config import Settings
from backend.core import config

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Tarification unifiée (par token)
# ──────────────────────────────────────────────────────────────────────────────
MODEL_PRICING: Dict[str, Dict[str, float]] = {
    # OpenAI
    "gpt-4o-mini": {"input": 0.15 / 1_000_000, "output": 0.60 / 1_000_000},
    "gpt-4o": {"input": 5.00 / 1_000_000, "output": 15.00 / 1_000_000},
    # Google
    "gemini-1.5-flash": {"input": 0.35 / 1_000_000, "output": 0.70 / 1_000_000},
    # Anthropic
    "claude-3-haiku-20240307": {"input": 0.25 / 1_000_000, "output": 1.25 / 1_000_000},
    "claude-3-sonnet-20240229": {"input": 3.00 / 1_000_000, "output": 15.00 / 1_000_000},
    "claude-3-opus-20240229": {"input": 15.00 / 1_000_000, "output": 75.00 / 1_000_000},
}

SAFE_DEFAULTS: Dict[str, str] = {
    "openai": "gpt-4o-mini",
    "anthropic": "claude-3-haiku-20240307",
    "google": "gemini-1.5-flash",
}


class ChatService:
    """
    ChatService V29.7
    - Initialisation clients OpenAI / Anthropic / Google
    - Fallback dynamique (ignore provider non configuré)
    - Fallback single-shot si stream ne renvoie aucun chunk
    - Format Anthropic conforme (content blocks)
    - 'anima' forcé sur OpenAI gpt-4o-mini (stabilité/coût)
    - Emission des sources RAG (ws:chat_sources)
    """

    def __init__(
        self,
        session_manager: SessionManager,
        cost_tracker: CostTracker,
        vector_service: VectorService,
        settings: Settings,
    ) -> None:
        self.session_manager = session_manager
        self.cost_tracker = cost_tracker
        self.vector_service = vector_service
        self.settings = settings

        # Politique OFF quand RAG désactivé
        self.off_history_policy = os.getenv("EMERGENCE_RAG_OFF_POLICY", "stateless").strip().lower()
        if self.off_history_policy not in ("stateless", "agent_local"):
            self.off_history_policy = "stateless"
        logger.info("ChatService OFF policy: %s", self.off_history_policy)

        # Clients LLM
        try:
            self.openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

            anth_key = os.getenv("ANTHROPIC_API_KEY")
            if anth_key:
                self.anthropic_client = AsyncAnthropic(api_key=anth_key)
            else:
                self.anthropic_client = None
                logger.warning("ANTHROPIC_API_KEY manquant – Anthropic désactivé (aucun essai / fallback).")

            gkey = os.getenv("GOOGLE_API_KEY")
            if gkey:
                genai.configure(api_key=gkey)
            else:
                logger.warning("GOOGLE_API_KEY manquant – Gemini ne sera pas utilisable.")
        except Exception as e:
            logger.error("Erreur lors de l'initialisation des clients API: %s", e, exc_info=True)
            raise

        # Prompts (fichiers *.md dans settings.paths.prompts)
        self.prompts: Dict[str, str] = self._load_prompts(self.settings.paths.prompts)
        logger.info("ChatService initialisé. Prompts chargés: %d", len(self.prompts))

    # ──────────────────────────────────────────────────────────────────────
    # Chargement des prompts
    # ──────────────────────────────────────────────────────────────────────
    def _load_prompts(self, prompts_dir: str) -> Dict[str, str]:
        prompts: Dict[str, str] = {}
        if not prompts_dir:
            return prompts
        for file_path in glob.glob(os.path.join(prompts_dir, "*.md")):
            agent_id = Path(file_path).stem.replace("_system", "").replace("_v2", "").replace("_v3", "").replace("_lite", "")
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    prompts[agent_id] = f.read()
                    logger.info("Prompt chargé pour l'agent '%s' depuis %s.", agent_id, Path(file_path).name)
            except Exception as e:
                logger.error("Impossible de lire le prompt '%s': %s", file_path, e, exc_info=True)
        return prompts

    def _ensure_supported(self, provider: Optional[str], model: Optional[str]) -> Tuple[str, str]:
        """Garantit un couple (provider, model) exploitable."""
        if not provider:
            provider = "openai"
        if not model:
            model = SAFE_DEFAULTS[provider]
        if model not in MODEL_PRICING and provider in SAFE_DEFAULTS:
            logger.warning("Modèle '%s' non répertorié, fallback -> %s (%s).", model, SAFE_DEFAULTS[provider], provider)
            model = SAFE_DEFAULTS[provider]
        return provider, model

    def _get_agent_config(self, agent_id: str) -> Tuple[str, str, str]:
        clean_agent_id = agent_id.replace("_lite", "")
        agent_configs = getattr(self.settings, "agents", {})
        provider = agent_configs.get(clean_agent_id, {}).get("provider")
        model = agent_configs.get(clean_agent_id, {}).get("model")

        # Sécurisation 'anima' : impose OpenAI/gpt-4o-mini
        if clean_agent_id == "anima":
            provider, model = "openai", "gpt-4o-mini"
            logger.info("Remplacement modèle pour 'anima' -> openai/gpt-4o-mini.")

        provider, model = self._ensure_supported(provider, model)

        # Si Anthropic demandé mais pas de clé -> fallback immédiat OpenAI
        if provider == "anthropic" and self.anthropic_client is None:
            logger.warning("Agent '%s' configuré Anthropic sans clé – fallback -> openai/%s.", agent_id, SAFE_DEFAULTS["openai"])
            provider, model = "openai", SAFE_DEFAULTS["openai"]

        system_prompt = self.prompts.get(agent_id, self.prompts.get(clean_agent_id, ""))
        if not system_prompt:
            logger.warning("Prompt système non trouvé pour '%s' – utilisation d'un prompt vide.", agent_id)
        return provider, model, system_prompt

    # ──────────────────────────────────────────────────────────────────────
    # API publique – traitement d'un message user pour N agents
    # ──────────────────────────────────────────────────────────────────────
    async def process_user_message_for_agents(
        self, session_id: str, message: ChatMessage, connection_manager: ConnectionManager
    ) -> None:
        # Persiste le message utilisateur
        await self.session_manager.add_message_to_session(session_id, message)
        if not message.agents:
            logger.warning("Aucun agent spécifié dans le message.")
            return

        tasks = [
            self._process_agent_response_stream(session_id, agent_id, getattr(message, "use_rag", False), connection_manager)
            for agent_id in message.agents
        ]
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.error("Erreur lors du traitement du message (gather): %s", e, exc_info=True)

    # ──────────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────────
    def _extract_sensitive_tokens(self, text: str) -> List[str]:
        return re.findall(r"\b[A-Z]{3,}-\d{3,}\b", text or "")

    def _to_anthropic_messages(self, history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convertit un historique {role, content} -> Anthropic {role, content=[{type:text,text:...}]}"""
        out: List[Dict[str, Any]] = []
        for it in history:
            role = it.get("role")
            content = it.get("content", "")
            if not content:
                continue
            if out and out[-1]["role"] == role:
                out[-1]["content"][0]["text"] += f"\n\n{content}"
            else:
                out.append({"role": role, "content": [{"type": "text", "text": content}]})
        return out

    # ──────────────────────────────────────────────────────────────────────
    # Orchestration d'un agent (streaming + RAG + coûts)
    # ──────────────────────────────────────────────────────────────────────
    async def _process_agent_response_stream(
        self, session_id: str, agent_id: str, use_rag: bool, connection_manager: ConnectionManager
    ) -> None:
        provider, model, system_prompt = self._get_agent_config(agent_id)

        # Notifie UI : début du stream
        temp_message_id = str(uuid4())
        await connection_manager.send_personal_message(
            {"type": "ws:chat_stream_start", "payload": {"agent_id": agent_id, "id": temp_message_id}}, session_id
        )

        # Construit historique + option RAG
        history = self.session_manager.get_full_history(session_id)
        rag_context = ""
        sources_payload: List[Dict[str, Any]] = []

        if use_rag:
            # Dernier message user
            last_user_message_obj = next((m for m in reversed(history) if m.get("role") in (Role.USER, "user")), None)
            last_user_message = (last_user_message_obj or {}).get("content", "")

            await connection_manager.send_personal_message(
                {"type": "ws:rag_status", "payload": {"status": "searching", "agent_id": agent_id}}, session_id
            )
            try:
                document_collection = self.vector_service.get_or_create_collection(config.DOCUMENT_COLLECTION_NAME)
                search_results = self.vector_service.query(collection=document_collection, query_text=last_user_message)

                for r in (search_results or []):
                    meta = (r.get("metadata") or {}) if isinstance(r, dict) else {}
                    sources_payload.append(
                        {
                            "document_id": meta.get("document_id") or meta.get("doc_id"),
                            "filename": meta.get("filename") or meta.get("source") or "",
                            "score": r.get("score") if isinstance(r, dict) else None,
                        }
                    )
                    snippet = meta.get("text") or meta.get("chunk") or ""
                    if snippet:
                        rag_context += f"\n• {snippet}"

                await connection_manager.send_personal_message(
                    {"type": "ws:chat_sources", "payload": {"agent_id": agent_id, "sources": sources_payload}}, session_id
                )
                await connection_manager.send_personal_message(
                    {"type": "ws:rag_status", "payload": {"status": "found", "agent_id": agent_id}}, session_id
                )
            except Exception as e:
                logger.error("Erreur RAG: %s", e, exc_info=True)
                await connection_manager.send_personal_message(
                    {"type": "ws:rag_status", "payload": {"status": "error", "agent_id": agent_id}}, session_id
                )

        # Normalisation provider
        normalized_history = self._normalize_history_for_llm(
            provider=provider, history=history, rag_context=rag_context, use_rag=use_rag, agent_id=agent_id
        )
        # Debug prompt envoyé (sans le system)
        try:
            if provider == "google":
                norm_concat = "\n".join(
                    ["".join(x.get("parts", [])) if isinstance(x.get("parts"), list) else x.get("parts", "") for x in normalized_history]
                )
            elif provider == "anthropic":
                norm_concat = "\n".join([x["content"][0]["text"] for x in normalized_history if x.get("content")])
            else:
                norm_concat = "\n".join([x.get("content", "") for x in normalized_history])
            norm_tokens = list(set(self._extract_sensitive_tokens(norm_concat)))
        except Exception:
            norm_tokens = []

        await connection_manager.send_personal_message(
            {
                "type": "ws:chat_debug",
                "payload": {
                    "phase": "after_normalize",
                    "agent_id": agent_id,
                    "use_rag": use_rag,
                    "history_filtered": len(normalized_history),
                    "rag_context_chars": len(rag_context),
                    "off_policy": self.off_history_policy,
                    "sensitive_tokens_in_prompt": norm_tokens,
                },
            },
            session_id,
        )

        # Stream + fallback
        cost_info: Dict[str, Any] = {"input_tokens": 0, "output_tokens": 0, "total_cost": 0.0}
        full_text = ""
        try:
            gen = self._get_llm_response_stream(provider, model, system_prompt, normalized_history, cost_info)
            async for chunk in gen:
                if not chunk:
                    continue
                full_text += chunk
                await connection_manager.send_personal_message(
                    {"type": "ws:chat_stream_chunk", "payload": {"agent_id": agent_id, "id": temp_message_id, "chunk": chunk}},
                    session_id,
                )
        except Exception as primary_err:
            logger.error("[STREAM FAIL] provider=%s model=%s: %s", provider, model, primary_err, exc_info=True)

            # Fallback chain dynamique (ignore providers non configurés)
            fallback_candidates: List[str] = []
            if provider != "openai" and self.openai_client is not None:
                fallback_candidates.append("openai")
            if provider != "google" and os.getenv("GOOGLE_API_KEY"):
                fallback_candidates.append("google")
            if provider != "anthropic" and self.anthropic_client is not None:
                fallback_candidates.append("anthropic")

            for fb in fallback_candidates:
                try:
                    fb_model = SAFE_DEFAULTS[fb]
                    gen = self._get_llm_response_stream(fb, fb_model, system_prompt, normalized_history, cost_info)
                    async for chunk in gen:
                        if not chunk:
                            continue
                        full_text += chunk
                        await connection_manager.send_personal_message(
                            {
                                "type": "ws:chat_stream_chunk",
                                "payload": {"agent_id": agent_id, "id": temp_message_id, "chunk": chunk},
                            },
                            session_id,
                        )
                    provider, model = fb, fb_model
                    break
                except Exception as fb_err:
                    logger.error("[FALLBACK STREAM FAIL] %s/%s: %s", fb, fb_model, fb_err, exc_info=True)

        # Si toujours vide → single-shot
        if not full_text.strip():
            try:
                content, _cost = await self._get_llm_response_single(provider, model, system_prompt, normalized_history, False)
                full_text = content or ""
                if _cost:
                    cost_info.update(_cost)
                if full_text:
                    await connection_manager.send_personal_message(
                        {
                            "type": "ws:chat_stream_chunk",
                            "payload": {"agent_id": agent_id, "id": temp_message_id, "chunk": full_text},
                        },
                        session_id,
                    )
            except Exception as single_err:
                logger.error("[SINGLE-SHOT FAIL] %s/%s: %s", provider, model, single_err, exc_info=True)
                raise

        # Persistance + tracking coûts
        final_agent_message = AgentMessage(
            id=temp_message_id,
            session_id=session_id,
            role=Role.ASSISTANT,
            agent=agent_id,
            message=full_text,
            timestamp=datetime.now(timezone.utc).isoformat(),
            cost_info=cost_info,
        )
        await self.session_manager.add_message_to_session(session_id, final_agent_message)
        await self.cost_tracker.record_cost(
            agent=agent_id,
            model=model,
            input_tokens=cost_info.get("input_tokens", 0),
            output_tokens=cost_info.get("output_tokens", 0),
            total_cost=cost_info.get("total_cost", 0.0),
            feature="chat",
        )

        await connection_manager.send_personal_message(
            {
                "type": "ws:chat_stream_end",
                "payload": {"agent_id": agent_id, "id": temp_message_id, "model": model, "provider": provider, "cost": cost_info},
            },
            session_id,
        )

    # ──────────────────────────────────────────────────────────────────────
    # Normalisation des historiques par provider
    # ──────────────────────────────────────────────────────────────────────
    def _normalize_history_for_llm(
        self, *, provider: str, history: List[Dict[str, Any]], rag_context: str, use_rag: bool, agent_id: str
    ) -> List[Dict[str, Any]]:
        """Transforme l'historique interne -> format messages du provider."""
        # Copie "user/assistant" uniquement
        pairs: List[Tuple[Any, str]] = []
        for m in history:
            role = m.get("role")
            content = m.get("content") or m.get("message") or ""
            if role in (Role.USER, "user", Role.ASSISTANT, "assistant"):
                pairs.append((role, str(content)))

        # Injection RAG dans le dernier message user
        if use_rag and pairs:
            for i in range(len(pairs) - 1, -1, -1):
                r = pairs[i][0]
                if r == Role.USER or r == "user":
                    original = pairs[i][1]
                    ctx = rag_context.strip()
                    if ctx:
                        enriched = f"{original}\n\n[CONTEXT]\n{ctx}\n[/CONTEXT]"
                        pairs[i] = (r, enriched)
                    break

        # Conversion
        normalized: List[Dict[str, Any]] = []
        if provider == "google":
            for role, content in pairs:
                normalized.append({"role": "user" if (role == Role.USER or role == "user") else "model", "parts": [content]})
            return normalized

        if provider == "anthropic":
            for role, content in pairs:
                anth_role = "user" if (role == Role.USER or role == "user") else "assistant"
                if not normalized or normalized[-1]["role"] != anth_role:
                    normalized.append({"role": anth_role, "content": [{"type": "text", "text": content}]})
                else:
                    normalized[-1]["content"][0]["text"] += f"\n\n{content}"
            return normalized

        # OpenAI (default)
        for role, content in pairs:
            normalized.append({"role": "user" if (role == Role.USER or role == "user") else "assistant", "content": content})
        return normalized

    # ──────────────────────────────────────────────────────────────────────
    # Streaming provider-agnostic
    # ──────────────────────────────────────────────────────────────────────
    async def _get_llm_response_stream(
        self, provider: str, model: str, system_prompt: str, history: List[Dict[str, Any]], cost_info_container: Dict[str, Any]
    ) -> AsyncGenerator[str, None]:
        if provider == "openai":
            async for c in self._get_openai_stream(model, system_prompt, history, cost_info_container):
                yield c
        elif provider == "google":
            async for c in self._get_gemini_stream(model, system_prompt, history, cost_info_container):
                yield c
        elif provider == "anthropic":
            if self.anthropic_client is None:
                raise ValueError("Anthropic non configuré (clé absente).")
            hist = history
            if history and "content" in history[0] and not isinstance(history[0]["content"], list):
                hist = self._to_anthropic_messages(history)
            async for c in self._get_anthropic_stream(model, system_prompt, hist, cost_info_container):
                yield c
        else:
            raise ValueError(f"Fournisseur LLM non supporté pour le streaming: {provider}")

    async def _get_openai_stream(
        self, model: str, system_prompt: str, history: List[Dict[str, Any]], cost_info_container: Dict[str, Any]
    ) -> AsyncGenerator[str, None]:
        messages = [{"role": "system", "content": system_prompt}] + history
        stream = await self.openai_client.chat.completions.create(
            model=model, messages=messages, temperature=0.2, max_tokens=4000, stream=True
        )
        final_usage = None
        async for chunk in stream:
            try:
                delta = chunk.choices[0].delta
                content = getattr(delta, "content", None) or ""
            except Exception:
                content = ""
            if getattr(chunk, "usage", None):
                final_usage = chunk.usage
            if content:
                yield content
        if final_usage:
            pricing = MODEL_PRICING.get(model, {"input": 0.0, "output": 0.0})
            in_tok = getattr(final_usage, "prompt_tokens", 0)
            out_tok = getattr(final_usage, "completion_tokens", getattr(final_usage, "completed_tokens", 0))
            cost = (in_tok * pricing["input"]) + (out_tok * pricing["output"])
            cost_info_container.update({"input_tokens": in_tok, "output_tokens": out_tok, "total_cost": cost})

    async def _get_gemini_stream(
        self, model: str, system_prompt: str, history: List[Dict[str, Any]], cost_info_container: Dict[str, Any]
    ) -> AsyncGenerator[str, None]:
        model_instance = genai.GenerativeModel(model_name=model, system_instruction=system_prompt)
        response = await model_instance.generate_content_async(contents=history, stream=True)
        usage_metadata = None
        async for chunk in response:
            text = getattr(chunk, "text", None) or ""
            if text:
                yield text
            usage_metadata = getattr(chunk, "usage_metadata", usage_metadata)
        if usage_metadata:
            pricing = MODEL_PRICING.get(model, {"input": 0.0, "output": 0.0})
            in_tok = getattr(usage_metadata, "prompt_token_count", 0)
            out_tok = getattr(usage_metadata, "candidates_token_count", 0)
            cost = (in_tok * pricing["input"]) + (out_tok * pricing["output"])
            cost_info_container.update({"input_tokens": in_tok, "output_tokens": out_tok, "total_cost": cost})

    async def _get_anthropic_stream(
        self, model: str, system_prompt: str, history: List[Dict[str, Any]], cost_info_container: Dict[str, Any]
    ) -> AsyncGenerator[str, None]:
        if not history:
            raise ValueError("L'historique des messages pour Anthropic ne peut pas être vide.")
        async with self.anthropic_client.messages.stream(
            model=model, messages=history, system=system_prompt, temperature=0.2, max_tokens=4000
        ) as stream:
            async for text in stream.text_stream:
                if text:
                    yield text
            final_message = await stream.get_final_message()
        usage = getattr(final_message, "usage", None)
        if usage:
            pricing = MODEL_PRICING.get(model, {"input": 0.0, "output": 0.0})
            in_tok = getattr(usage, "input_tokens", 0)
            out_tok = getattr(usage, "output_tokens", 0)
            cost = (in_tok * pricing["input"]) + (out_tok * pricing["output"])
            cost_info_container.update({"input_tokens": in_tok, "output_tokens": out_tok, "total_cost": cost})

    # ──────────────────────────────────────────────────────────────────────
    # Single-shot (utilisé pour débats & outils)
    # ──────────────────────────────────────────────────────────────────────
    async def get_llm_response_for_debate(self, agent_id: str, history: List[Dict[str, Any]], session_id: str) -> Tuple[str, Dict]:
        provider, model, system_prompt = self._get_agent_config(agent_id)
        # Le prompt débat est le premier item user
        debate_prompt = ""
        for it in history:
            if it.get("role") in (Role.USER, "user"):
                debate_prompt = str(it.get("content", ""))
                break

        if provider == "google":
            normalized = [{"role": "user", "parts": [debate_prompt]}]
        elif provider == "anthropic":
            normalized = [{"role": "user", "content": [{"type": "text", "text": debate_prompt}]}]
        else:
            normalized = [{"role": "user", "content": debate_prompt}]

        content, cost = await self._get_llm_response_single(provider, model, system_prompt, normalized, json_mode=False)
        await self.cost_tracker.record_cost(
            agent=f"debate_{agent_id}",
            model=model,
            input_tokens=cost.get("input_tokens", 0),
            output_tokens=cost.get("output_tokens", 0),
            total_cost=cost.get("total_cost", 0.0),
            feature="debate",
        )
        return content, cost

    async def get_structured_llm_response(
        self, agent_id: str, prompt: str, session_id: str, json_schema_hint: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Demande une réponse JSON stricte au LLM et renvoie l'objet parsé."""
        provider, model, system_prompt = self._get_agent_config(agent_id)
        if json_schema_hint:
            prompt += f"\n\nRéponds UNIQUEMENT avec un objet JSON valide correspondant à ce schéma (indicatif) :\n{json_schema_hint}"
        if provider == "google":
            history = [{"role": "user", "parts": [prompt]}]
        elif provider == "anthropic":
            history = [{"role": "user", "content": [{"type": "text", "text": prompt}]}]
        else:
            history = [{"role": "user", "content": prompt}]

        text, cost = await self._get_llm_response_single(provider, model, system_prompt, history, json_mode=True)
        await self.cost_tracker.record_cost(
            agent=f"internal_analyzer_{agent_id}",
            model=model,
            input_tokens=cost.get("input_tokens", 0),
            output_tokens=cost.get("output_tokens", 0),
            total_cost=cost.get("total_cost", 0.0),
            feature="document_processing",
        )

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.error("Erreur de décodage JSON: %s – Réponse brute: %r", e, text, exc_info=True)
            return None

    async def _get_llm_response_single(
        self, provider: str, model: str, system_prompt: str, history: List[Dict[str, Any]], json_mode: bool = False
    ) -> Tuple[str, Dict[str, Any]]:
        if provider == "openai":
            return await self._get_openai_response_single(model, system_prompt, history, json_mode)
        elif provider == "google":
            return await self._get_gemini_response_single(model, system_prompt, history, json_mode)
        elif provider == "anthropic":
            if self.anthropic_client is None:
                raise ValueError("Anthropic non configuré (clé absente).")
            hist = history
            if history and "content" in history[0] and not isinstance(history[0]["content"], list):
                hist = self._to_anthropic_messages(history)
            return await self._get_anthropic_response_single(model, system_prompt, hist, json_mode)
        else:
            raise ValueError(f"Fournisseur LLM non supporté: {provider}")

    async def _get_openai_response_single(
        self, model: str, system_prompt: str, history: List[Dict[str, Any]], json_mode: bool = False
    ) -> Tuple[str, Dict[str, Any]]:
        messages = [{"role": "system", "content": system_prompt}] + history
        response_format = {"type": "json_object"} if json_mode else {"type": "text"}
        response = await self.openai_client.chat.completions.create(
            model=model, messages=messages, temperature=0.2, max_tokens=4000, stream=False, response_format=response_format
        )
        content = (response.choices[0].message.content or "").strip()
        usage = getattr(response, "usage", None)
        pricing = MODEL_PRICING.get(model, {"input": 0.0, "output": 0.0})
        in_tok = getattr(usage, "prompt_tokens", 0) if usage else 0
        out_tok = getattr(usage, "completion_tokens", 0) if usage else 0
        cost = (in_tok * pricing["input"]) + (out_tok * pricing["output"])
        return content, {"input_tokens": in_tok, "output_tokens": out_tok, "total_cost": cost}

    async def _get_gemini_response_single(
        self, model: str, system_prompt: str, history: List[Dict[str, Any]], json_mode: bool = False
    ) -> Tuple[str, Dict[str, Any]]:
        model_instance = genai.GenerativeModel(model_name=model, system_instruction=system_prompt)
        gen_cfg = {}
        if json_mode:
            gen_cfg["response_mime_type"] = "application/json"
        response = await model_instance.generate_content_async(contents=history, generation_config=gen_cfg or None)
        text = (getattr(response, "text", None) or "").strip()
        usage_metadata = getattr(response, "usage_metadata", None)
        pricing = MODEL_PRICING.get(model, {"input": 0.0, "output": 0.0})
        in_tok = getattr(usage_metadata, "prompt_token_count", 0) if usage_metadata else 0
        out_tok = getattr(usage_metadata, "candidates_token_count", 0) if usage_metadata else 0
        cost = (in_tok * pricing["input"]) + (out_tok * pricing["output"])
        return text, {"input_tokens": in_tok, "output_tokens": out_tok, "total_cost": cost}

    async def _get_anthropic_response_single(
        self, model: str, system_prompt: str, history: List[Dict[str, Any]], json_mode: bool = False
    ) -> Tuple[str, Dict[str, Any]]:
        if json_mode and history and isinstance(history[-1].get("content"), list):
            for blk in history[-1]["content"]:
                if blk.get("type") == "text":
                    blk["text"] += "\n\nRéponds uniquement avec un objet JSON valide."
                    break
        response = await self.anthropic_client.messages.create(
            model=model, messages=history, system=system_prompt, temperature=0.2, max_tokens=4000
        )
        content = (response.content[0].text or "").strip()
        usage = getattr(response, "usage", None)
        pricing = MODEL_PRICING.get(model, {"input": 0.0, "output": 0.0})
        in_tok = getattr(usage, "input_tokens", 0) if usage else 0
        out_tok = getattr(usage, "output_tokens", 0) if usage else 0
        cost = (in_tok * pricing["input"]) + (out_tok * pricing["output"])
        return content, {"input_tokens": in_tok, "output_tokens": out_tok, "total_cost": cost}
