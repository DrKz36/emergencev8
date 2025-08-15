# src/backend/features/chat/service.py
# V29.2 - STREAM ROBUST + FALLBACK + ANTHROPIC FORMAT + SAFE MODEL FOR 'ANIMA'
import os
import re
import asyncio
import logging
import glob
import json
from uuid import uuid4
from typing import Dict, Any, List, Tuple, Optional, AsyncGenerator

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

# --- Grille tarifaire unifiée (inchangée) ---
MODEL_PRICING = {
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

# --- Modèles stables par provider (fallback chain) ---
SAFE_DEFAULTS = {
    "openai": "gpt-4o-mini",
    "anthropic": "claude-3-haiku-20240307",
    "google": "gemini-1.5-flash",
}


class ChatService:
    """
    ChatService V29.2
    - Timeouts/retries SDK.
    - Fallback provider chain (openai -> anthropic -> google) en cas d'échec stream.
    - Fallback single-shot si stream ne produit aucun chunk.
    - Format Anthropic messages conforme (content blocks).
    - 'anima' forcé sur OpenAI/gpt-4o-mini pour cohérence.
    """
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

        # Politique OFF
        self.off_history_policy = os.getenv("EMERGENCE_RAG_OFF_POLICY", "stateless").strip().lower()
        if self.off_history_policy not in ("stateless", "agent_local"):
            self.off_history_policy = "stateless"
        logger.info(f"ChatService OFF policy: {self.off_history_policy}")

        try:
            # Timeouts/retries côté SDK
            self.openai_client = AsyncOpenAI(
                api_key=self.settings.openai_api_key,
                timeout=30.0,
                max_retries=2,
            )
            genai.configure(api_key=self.settings.google_api_key)
            self.anthropic_client = AsyncAnthropic(
                api_key=self.settings.anthropic_api_key,
                max_retries=2,
                timeout=30.0,  # accepté dans SDK récent ; si non supporté, ignoré sans casse
            )
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation des clients API: {e}", exc_info=True)
            raise

        self.prompts = self._load_prompts(self.settings.paths.prompts)
        logger.info(f"ChatService V29.2 initialisé. Prompts chargés: {len(self.prompts)}")

    def _load_prompts(self, prompts_dir: str) -> Dict[str, str]:
        prompts = {}
        prompt_files = glob.glob(os.path.join(prompts_dir, "*.md"))
        for file_path in prompt_files:
            agent_id = Path(file_path).stem.replace("_system", "").replace("_v2", "").replace("_v3", "").replace("_lite", "")
            with open(file_path, 'r', encoding='utf-8') as f:
                prompts[agent_id] = f.read()
                logger.info(f"Prompt chargé pour l'agent '{agent_id}' depuis {Path(file_path).name}.")
        return prompts

    def _ensure_supported(self, provider: Optional[str], model: Optional[str]) -> Tuple[str, str]:
        """Garantit un couple (provider, model) exploitable."""
        if not provider:
            provider = "openai"
        if not model:
            model = SAFE_DEFAULTS[provider]
        # Si modèle inconnu de la grille: on bascule sur le safe default du provider
        if model not in MODEL_PRICING and provider in SAFE_DEFAULTS:
            logger.warning(f"Modèle '{model}' non répertorié, fallback -> {SAFE_DEFAULTS[provider]} ({provider}).")
            model = SAFE_DEFAULTS[provider]
        return provider, model

    def _get_agent_config(self, agent_id: str) -> Tuple[str, str, str]:
        clean_agent_id = agent_id.replace('_lite', '')
        agent_configs = self.settings.agents
        provider = agent_configs.get(clean_agent_id, {}).get("provider")
        model = agent_configs.get(clean_agent_id, {}).get("model")

        # Sécurisation 'anima' : impose OpenAI/gpt-4o-mini
        if clean_agent_id == 'anima':
            provider, model = "openai", "gpt-4o-mini"
            logger.info("Remplacement du modèle pour 'anima' -> provider=openai, model=gpt-4o-mini (coût & stabilité).")

        provider, model = self._ensure_supported(provider, model)

        system_prompt = self.prompts.get(agent_id, self.prompts.get(clean_agent_id, ""))
        if not all([provider, model, system_prompt]):
            raise ValueError(f"Configuration incomplète pour l'agent '{agent_id}'.")
        return provider, model, system_prompt

    async def process_user_message_for_agents(self, session_id: str, message: ChatMessage, connection_manager: ConnectionManager):
        await self.session_manager.add_message_to_session(session_id, message)
        if not message.agents:
            logger.warning("Aucun agent spécifié dans le message. Le traitement est terminé.")
            return
        
        tasks = [
            self._process_agent_response_stream(session_id, agent_id, message.use_rag, connection_manager)
            for agent_id in message.agents
        ]
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.error(f"Erreur lors du traitement du message de chat (gather): {e}", exc_info=True)

    # --- Helpers DEBUG ---
    def _extract_sensitive_tokens(self, text: str) -> List[str]:
        return re.findall(r"\b[A-Z]{3,}-\d{3,}\b", text or "")

    def _to_anthropic_messages(self, history: List[Dict]) -> List[Dict]:
        """Anthropic v1: content = list[{'type':'text','text':...}]"""
        fixed = []
        for m in history:
            role = m.get("role")
            content = m.get("content") or ""
            fixed.append({
                "role": role,
                "content": [{"type": "text", "text": content}],
            })
        return fixed

    async def _process_agent_response_stream(self, session_id: str, agent_id: str, use_rag: bool, connection_manager: ConnectionManager):
        temp_message_id = str(uuid4())
        full_response_text = ""
        cost_info_container = {} 
        model_used = ""
        chunk_count = 0

        try:
            await connection_manager.send_personal_message({
                "type": "ws:chat_stream_start",
                "payload": {"agent_id": agent_id, "id": temp_message_id}
            }, session_id)

            history = self.session_manager.get_full_history(session_id)
            rag_context = ""
            if use_rag:
                last_user_message_obj = next((msg for msg in reversed(history) if msg.get('role') == Role.USER), None)
                if last_user_message_obj:
                    last_user_message = last_user_message_obj.get('content', '')
                    await connection_manager.send_personal_message({"type": "ws:rag_status", "payload": {"status": "searching", "agent_id": agent_id}}, session_id)
                    document_collection = self.vector_service.get_or_create_collection(config.DOCUMENT_COLLECTION_NAME)
                    search_results = self.vector_service.query(collection=document_collection, query_text=last_user_message)
                    rag_context = "\n".join([result['text'] for result in search_results])
                    await connection_manager.send_personal_message({"type": "ws:rag_status", "payload": {"status": "found", "agent_id": agent_id}}, session_id)

            # DEBUG pré-normalisation
            raw_concat = "\n".join([(m.get('content') or m.get('message', '')) for m in history])
            raw_tokens = self._extract_sensitive_tokens(raw_concat)
            await connection_manager.send_personal_message({
                "type": "ws:debug_context",
                "payload": {
                    "phase": "before_normalize",
                    "agent_id": agent_id,
                    "use_rag": use_rag,
                    "history_total": len(history),
                    "rag_context_chars": len(rag_context),
                    "off_policy": self.off_history_policy,
                    "sensitive_tokens_in_history": list(set(raw_tokens))
                }
            }, session_id)

            provider, model, system_prompt = self._get_agent_config(agent_id)
            model_used = model
            normalized_history = self._normalize_history_for_llm(
                provider=provider,
                history=history,
                rag_context=rag_context,
                use_rag=use_rag,
                agent_id=agent_id
            )

            # DEBUG post-normalisation
            if provider == "google":
                norm_concat = "\n".join(["".join(p.get("parts", [])) if isinstance(p.get("parts"), list) else p.get("parts", "") for p in normalized_history])
            else:
                norm_concat = "\n".join([p.get("content", "") for p in normalized_history])
            norm_tokens = self._extract_sensitive_tokens(norm_concat)

            await connection_manager.send_personal_message({
                "type": "ws:debug_context",
                "payload": {
                    "phase": "after_normalize",
                    "agent_id": agent_id,
                    "use_rag": use_rag,
                    "history_filtered": len(normalized_history),
                    "rag_context_chars": len(rag_context),
                    "off_policy": self.off_history_policy,
                    "sensitive_tokens_in_prompt": list(set(norm_tokens))
                }
            }, session_id)

            # --- Streaming principal avec fallback provider si échec ---
            response_generator = None
            try:
                response_generator = self._get_llm_response_stream(provider, model, system_prompt, normalized_history, cost_info_container)
                async for chunk in response_generator:
                    if chunk:
                        chunk_count += 1
                        full_response_text += chunk
                        await connection_manager.send_personal_message({
                            "type": "ws:chat_stream_chunk",
                            "payload": {"agent_id": agent_id, "id": temp_message_id, "chunk": chunk}
                        }, session_id)
            except Exception as primary_err:
                logger.error(f"[STREAM FAIL] provider={provider}, model={model}: {primary_err}", exc_info=True)
                # Fallback chain
                chain = ["openai", "anthropic", "google"]
                if provider in chain:
                    chain.remove(provider)
                for fb in chain:
                    fb_model = SAFE_DEFAULTS[fb]
                    try:
                        await connection_manager.send_personal_message({
                            "type": "ws:debug_context",
                            "payload": {"phase": "fallback", "agent_id": agent_id, "fallback_provider": fb, "fallback_model": fb_model}
                        }, session_id)
                        alt_history = normalized_history
                        if fb == "anthropic":
                            alt_history = self._to_anthropic_messages(normalized_history)
                        async for chunk in self._get_llm_response_stream(fb, fb_model, system_prompt, alt_history, cost_info_container):
                            if chunk:
                                chunk_count += 1
                                full_response_text += chunk
                                await connection_manager.send_personal_message({
                                    "type": "ws:chat_stream_chunk",
                                    "payload": {"agent_id": agent_id, "id": temp_message_id, "chunk": chunk}
                                }, session_id)
                        if chunk_count > 0:
                            provider, model = fb, fb_model
                            break
                    except Exception as fb_err:
                        logger.error(f"[FALLBACK FAIL] provider={fb}, model={fb_model}: {fb_err}", exc_info=True)
                        continue

            # --- Fallback single-shot si aucun chunk n'a été produit ---
            if chunk_count == 0:
                try:
                    single_history = normalized_history
                    p = provider
                    m = model
                    if p == "anthropic":
                        single_history = self._to_anthropic_messages(normalized_history)
                    content, _cost = await self._get_llm_response_single(p, m, system_prompt, single_history, json_mode=False)
                    if content:
                        full_response_text = content
                        cost_info_container.update(_cost)
                        await connection_manager.send_personal_message({
                            "type": "ws:chat_stream_chunk",
                            "payload": {"agent_id": agent_id, "id": temp_message_id, "chunk": content}
                        }, session_id)
                except Exception as single_err:
                    logger.error(f"[SINGLE-SHOT FAIL] provider={provider}, model={model}: {single_err}", exc_info=True)
                    raise single_err

            # --- Persist & coût ---
            final_agent_message = AgentMessage(
                id=temp_message_id,
                session_id=session_id,
                role=Role.ASSISTANT,
                agent=agent_id,
                message=full_response_text,
                timestamp=datetime.now(timezone.utc).isoformat(),
                cost_info=cost_info_container
            )

            await self.session_manager.add_message_to_session(session_id, final_agent_message)
            
            await self.cost_tracker.record_cost(
                agent=agent_id,
                model=model_used,
                input_tokens=cost_info_container.get("input_tokens", 0),
                output_tokens=cost_info_container.get("output_tokens", 0),
                total_cost=cost_info_container.get("total_cost", 0.0),
                feature="chat"
            )

            payload_to_send = final_agent_message.model_dump(mode='json')
            if 'message' in payload_to_send:
                payload_to_send['content'] = payload_to_send.pop('message')

            await connection_manager.send_personal_message({
                "type": "ws:chat_stream_end",
                "payload": payload_to_send
            }, session_id)

        except Exception as e:
            logger.error(f"Erreur lors du streaming pour l'agent {agent_id}: {e}", exc_info=True)
            try:
                await connection_manager.send_personal_message({
                    "type": "ws:error",
                    "payload": {"message": f"Erreur interne pour l'agent {agent_id}: {str(e)}"}
                }, session_id)
            except Exception as send_error:
                logger.error(f"Impossible d'envoyer le message d'erreur au client pour la session {session_id}: {send_error}", exc_info=True)

    def _normalize_history_for_llm(self, provider: str, history: List[Dict], rag_context: str = "", use_rag: bool = False, agent_id: Optional[str] = None) -> List[Dict]:
        # 1) Construire une copie de l'historique selon la politique
        if use_rag:
            history_copy = list(history)
        else:
            if self.off_history_policy == "agent_local" and agent_id:
                filtered = []
                for m in reversed(history):
                    r = m.get('role')
                    a = m.get('agent')
                    if r == Role.USER or (r == Role.ASSISTANT and a == agent_id):
                        filtered.append(m)
                    if len(filtered) >= 6:
                        break
                history_copy = list(reversed(filtered)) if filtered else []
            else:
                last_user_message_obj = next((msg for msg in reversed(history) if msg.get('role') == Role.USER), None)
                history_copy = [last_user_message_obj] if last_user_message_obj else []

        # 2) Injection du contexte RAG (si présent)
        if rag_context and history_copy:
            rag_prompt = f"Contexte pertinent issu de documents:\n---\n{rag_context}\n---\nEn te basant sur ce contexte, réponds à la question suivante:"
            if history_copy[-1].get('role') == Role.USER:
                history_copy[-1] = dict(history_copy[-1])
                history_copy[-1]['content'] = f"{rag_prompt}\n{history_copy[-1].get('content', '')}"

        # 3) Normalisation selon le provider
        normalized = []
        for msg in history_copy:
            msg_role = msg.get('role')
            content = None
            if msg_role == Role.USER:
                role, content = "user", msg.get('content')
            elif msg_role == Role.ASSISTANT:
                role, content = ("model" if provider == "google" else "assistant"), msg.get('message')
            else:
                continue
            if not content:
                continue
            if provider == "google":
                normalized.append({"role": role, "parts": [content]})
            elif provider == "anthropic" and normalized and normalized[-1]["role"] == role:
                normalized[-1]["content"] += f"\n\n{content}"
            else:
                normalized.append({"role": role, "content": content})
        return normalized

    async def _get_llm_response_stream(
        self, provider: str, model: str, system_prompt: str, history: List[Dict], cost_info_container: Dict
    ) -> AsyncGenerator[str, None]:
        if provider == "openai":
            async for c in self._get_openai_stream(model, system_prompt, history, cost_info_container):
                yield c
        elif provider == "google":
            async for c in self._get_gemini_stream(model, system_prompt, history, cost_info_container):
                yield c
        elif provider == "anthropic":
            # convertit au format Anthropic si besoin (sécurité)
            hist = history
            if history and "content" in history[0] and not isinstance(history[0]["content"], list):
                hist = self._to_anthropic_messages(history)
            async for c in self._get_anthropic_stream(model, system_prompt, hist, cost_info_container):
                yield c
        else:
            raise ValueError(f"Fournisseur LLM non supporté pour le streaming: {provider}")

    async def _get_openai_stream(self, model: str, system_prompt: str, history: List[Dict], cost_info_container: Dict) -> AsyncGenerator[str, None]:
        messages = [{"role": "system", "content": system_prompt}] + history
        stream = await self.openai_client.chat.completions.create(
            model=model, messages=messages, temperature=0.2, max_tokens=4000, stream=True
        )
        final_chunk = None
        async for chunk in stream:
            try:
                content = (chunk.choices[0].delta.content or "")
            except Exception:
                content = ""
            if hasattr(chunk, "usage") and chunk.usage:
                final_chunk = chunk
            if content:
                yield content
        if final_chunk and getattr(final_chunk, "usage", None):
            usage = final_chunk.usage
            pricing = MODEL_PRICING.get(model, {"input": 0, "output": 0})
            cost = (usage.prompt_tokens * pricing["input"]) + (usage.completion_tokens * pricing["output"])
            cost_info_container.update({
                "input_tokens": usage.prompt_tokens,
                "output_tokens": getattr(usage, "completed_tokens", usage.completion_tokens),
                "total_cost": cost
            })
        else:
            cost_info_container.update({"input_tokens": 0, "output_tokens": 0, "total_cost": 0.0, "note": "Cost not available for OpenAI streams"})

    async def _get_gemini_stream(self, model: str, system_prompt: str, history: List[Dict], cost_info_container: Dict) -> AsyncGenerator[str, None]:
        model_instance = genai.GenerativeModel(model_name=model, system_instruction=system_prompt)
        response = await model_instance.generate_content_async(history, stream=True)
        async for chunk in response:
            if getattr(chunk, "text", None):
                yield chunk.text
        usage_metadata = getattr(response, "usage_metadata", None)
        if usage_metadata:
            pricing = MODEL_PRICING.get(model, {"input": 0, "output": 0})
            cost = (usage_metadata.prompt_token_count * pricing["input"]) + (usage_metadata.candidates_token_count * pricing["output"])
            cost_info_container.update({
                "input_tokens": usage_metadata.prompt_token_count,
                "output_tokens": usage_metadata.candidates_token_count,
                "total_cost": cost,
            })

    async def _get_anthropic_stream(self, model: str, system_prompt: str, history: List[Dict], cost_info_container: Dict) -> AsyncGenerator[str, None]:
        if not history:
            raise ValueError("L'historique des messages pour Anthropic ne peut pas être vide.")
        async with self.anthropic_client.messages.stream(
            model=model, messages=history, system=system_prompt, temperature=0.2, max_tokens=4000
        ) as stream:
            async for text in stream.text_stream:
                if text:
                    yield text
            final_message = await stream.get_final_message()
        usage = final_message.usage
        pricing = MODEL_PRICING.get(model, {"input": 0, "output": 0})
        cost = (usage.input_tokens * pricing["input"]) + (usage.output_tokens * pricing["output"])
        cost_info_container.update({
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
            "total_cost": cost
        })

    async def get_llm_response_for_debate(self, agent_id: str, history: List[Dict], session_id: str) -> Tuple[str, Dict]:
        try:
            provider, model, system_prompt = self._get_agent_config(agent_id)
            debate_prompt = history[0]['content']
            if provider == 'google':
                normalized_history = [{'role': 'user', 'parts': [debate_prompt]}]
            elif provider == 'anthropic':
                normalized_history = [{'role': 'user', 'content': [{"type": "text", "text": debate_prompt}]}]
            else:
                normalized_history = [{'role': 'user', 'content': debate_prompt}]
            
            response_text, cost_info = await self._get_llm_response_single(provider, model, system_prompt, normalized_history)

            await self.cost_tracker.record_cost(
                agent=agent_id,
                model=model,
                input_tokens=cost_info.get("input_tokens", 0),
                output_tokens=cost_info.get("output_tokens", 0),
                total_cost=cost_info.get("total_cost", 0.0),
                feature="debate"
            )
            return response_text, cost_info
        except Exception as e:
            logger.error(f"Erreur dans get_llm_response_for_debate pour {agent_id}: {e}", exc_info=True)
            raise

    async def get_structured_llm_response(self, agent_id: str, prompt: str, json_schema: Dict) -> Optional[Dict]:
        try:
            provider, model, _ = self._get_agent_config(agent_id)
            if provider == 'google':
                history = [{'role': 'user', 'parts': [prompt]}]
            elif provider == 'anthropic':
                history = [{'role': 'user', 'content': [{"type": "text", "text": prompt}]}]
            else:
                history = [{'role': 'user', 'content': prompt}]
            system_prompt = "Tu es un assistant expert en traitement de données. Tu ne réponds qu'au format JSON."
            
            response_str, cost = await self._get_llm_response_single(provider, model, system_prompt, history, json_mode=True)

            await self.cost_tracker.record_cost(
                agent=f"internal_analyzer_{agent_id}", model=model,
                input_tokens=cost.get("input_tokens", 0),
                output_tokens=cost.get("output_tokens", 0),
                total_cost=cost.get("total_cost", 0.0),
                feature="document_processing"
            )
            return json.loads(response_str)
        except json.JSONDecodeError as e:
            logger.error(f"Erreur de décodage JSON de la part du LLM: {e}. Réponse reçue: {response_str}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"Erreur dans get_structured_llm_response pour {agent_id}: {e}", exc_info=True)
            return None

    async def _get_llm_response_single(self, provider: str, model: str, system_prompt: str, history: List[Dict], json_mode: bool = False) -> Tuple[str, Dict]:
        if provider == "openai":
            return await self._get_openai_response_single(model, system_prompt, history, json_mode)
        elif provider == "google":
            return await self._get_gemini_response_single(model, system_prompt, history, json_mode)
        elif provider == "anthropic":
            # sécurité format
            if history and "content" in history[0] and not isinstance(history[0]["content"], list):
                history = self._to_anthropic_messages(history)
            return await self._get_anthropic_response_single(model, system_prompt, history, json_mode)
        else:
            raise ValueError(f"Fournisseur LLM non supporté: {provider}")

    async def _get_openai_response_single(self, model: str, system_prompt: str, history: List[Dict], json_mode: bool = False) -> Tuple[str, Dict]:
        messages = [{"role": "system", "content": system_prompt}] + history
        response_format = {"type": "json_object"} if json_mode else {"type": "text"}
        response = await self.openai_client.chat.completions.create(
            model=model, messages=messages, temperature=0.2, max_tokens=4000, response_format=response_format
        )
        content = response.choices[0].message.content or ""
        cost_info = {"input_tokens": 0, "output_tokens": 0, "total_cost": 0.0}
        if response.usage:
            usage = response.usage
            pricing = MODEL_PRICING.get(model, {"input": 0, "output": 0})
            cost = (usage.prompt_tokens * pricing["input"]) + (usage.completion_tokens * pricing["output"])
            cost_info.update({
                "input_tokens": usage.prompt_tokens,
                "output_tokens": getattr(usage, "completed_tokens", usage.completion_tokens),
                "total_cost": cost
            })
        return content, cost_info

    async def _get_gemini_response_single(self, model: str, system_prompt: str, history: List[Dict], json_mode: bool = False) -> Tuple[str, Dict]:
        model_instance = genai.GenerativeModel(model_name=model, system_instruction=system_prompt)
        generation_config = genai.types.GenerationConfig(response_mime_type="application/json") if json_mode else None
        response = await model_instance.generate_content_async(history, generation_config=generation_config)
        content = response.text or ""
        cost_info = {"input_tokens": 0, "output_tokens": 0, "total_cost": 0.0}
        if response.usage_metadata:
            usage = response.usage_metadata
            pricing = MODEL_PRICING.get(model, {"input": 0, "output": 0})
            cost = (usage.prompt_token_count * pricing["input"]) + (usage.candidates_token_count * pricing["output"])
            cost_info.update({
                "input_tokens": usage.prompt_token_count,
                "output_tokens": usage.candidates_token_count,
                "total_cost": cost
            })
        return content, cost_info

    async def _get_anthropic_response_single(self, model: str, system_prompt: str, history: List[Dict], json_mode: bool = False) -> Tuple[str, Dict]:
        if not history:
            raise ValueError("L'historique des messages pour Anthropic ne peut pas être vide.")
        if json_mode and history and isinstance(history[-1].get('content'), list):
            # Ajoute une consigne JSON dans le dernier bloc user
            for blk in history[-1]['content']:
                if blk.get("type") == "text":
                    blk["text"] += "\n\nRéponds uniquement avec un objet JSON valide."
                    break
        response = await self.anthropic_client.messages.create(
            model=model, messages=history, system=system_prompt, temperature=0.2, max_tokens=4000
        )
        content = response.content[0].text or ""
        usage = response.usage
        pricing = MODEL_PRICING.get(model, {"input": 0, "output": 0})
        cost = (usage.input_tokens * pricing["input"]) + (usage.output_tokens * pricing["output"])
        cost_info = {"input_tokens": usage.input_tokens, "output_tokens": usage.output_tokens, "total_cost": cost}
        return content, cost_info
