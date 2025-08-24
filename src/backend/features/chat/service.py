# src/backend/features/chat/service.py
# V29.3 - STREAM GUARD + STRUCTURED LLM RESPONSE
# - Guard robuste sur le stream OpenAI (boucle sur choices, skip deltas vides).
# - Ajout get_structured_llm_response() pour l'analyse JSON (MemoryAnalyzer).
# - Reste inchangé (coûts, normalisation historique, Gemini/Anthropic stream).

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

# --- CORRECTION V29.0: Grille tarifaire unifiée ---
MODEL_PRICING = {
    "gpt-4o-mini": {"input": 0.15 / 1_000_000, "output": 0.60 / 1_000_000},
    "gpt-4o": {"input": 5.00 / 1_000_000, "output": 15.00 / 1_000_000},
    "gemini-1.5-flash": {"input": 0.35 / 1_000_000, "output": 0.70 / 1_000_000},
    "claude-3-haiku-20240307": {"input": 0.25 / 1_000_000, "output": 1.25 / 1_000_000},
    "claude-3-sonnet-20240229": {"input": 3.00 / 1_000_000, "output": 15.00 / 1_000_000},
    "claude-3-opus-20240229": {"input": 15.00 / 1_000_000, "output": 75.00 / 1_000_000},
}

class ChatService:
    """
    ChatService V29.3
    - Guard stream OpenAI + méthode d'analyse structurée.
    - Grille tarifaire/cost tracking et normalisation historiques inchangées.
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

        self.off_history_policy = os.getenv("EMERGENCE_RAG_OFF_POLICY", "stateless").strip().lower()
        if self.off_history_policy not in ("stateless", "agent_local"):
            self.off_history_policy = "stateless"
        logger.info(f"ChatService OFF policy: {self.off_history_policy}")

        try:
            self.openai_client = AsyncOpenAI(api_key=self.settings.openai_api_key)
            genai.configure(api_key=self.settings.google_api_key)
            self.anthropic_client = AsyncAnthropic(api_key=self.settings.anthropic_api_key)
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation des clients API: {e}", exc_info=True)
            raise

        self.prompts = self._load_prompts(self.settings.paths.prompts)
        logger.info(f"ChatService V29.3 initialisé. Prompts chargés: {len(self.prompts)}")

    def _load_prompts(self, prompts_dir: str) -> Dict[str, str]:
        def weight(name: str) -> int:
            name = name.lower()
            w = 0
            if "lite" in name: w = max(w, 1)
            if "v2" in name:   w = max(w, 2)
            if "v3" in name:   w = max(w, 3)
            return w

        chosen: Dict[str, Dict[str, Any]] = {}
        for file_path in glob.glob(os.path.join(prompts_dir, "*.md")):
            p = Path(file_path)
            agent_id = p.stem.replace("_system", "").replace("_v2", "").replace("_v3", "").replace("_lite", "")
            w = weight(p.name)
            if agent_id not in chosen or w > chosen[agent_id]["w"]:
                with open(file_path, 'r', encoding='utf-8') as f:
                    chosen[agent_id] = {"w": w, "text": f.read(), "file": p.name}
        for aid, meta in chosen.items():
            logger.info(f"Prompt retenu pour l'agent '{aid}': {meta['file']}")
        return {aid: meta["text"] for aid, meta in chosen.items()}

    def _get_agent_config(self, agent_id: str) -> Tuple[str, str, str]:
        clean_agent_id = agent_id.replace('_lite', '')
        agent_configs = self.settings.agents
        provider = agent_configs.get(clean_agent_id, {}).get("provider")
        model = agent_configs.get(clean_agent_id, {}).get("model")

        if clean_agent_id == 'anima':
            model = 'gpt-4o-mini'
            logger.info("Remplacement du modèle pour 'anima' -> 'gpt-4o-mini' pour optimiser les coûts.")

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

    async def _process_agent_response_stream(self, session_id: str, agent_id: str, use_rag: bool, connection_manager: ConnectionManager):
        temp_message_id = str(uuid4())
        full_response_text = ""
        cost_info_container = {} 
        model_used = ""

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

            norm_concat = ""
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

            response_generator = self._get_llm_response_stream(provider, model, system_prompt, normalized_history, cost_info_container)

            async for chunk in response_generator:
                full_response_text += chunk
                await connection_manager.send_personal_message({
                    "type": "ws:chat_stream_chunk",
                    "payload": {"agent_id": agent_id, "id": temp_message_id, "chunk": chunk}
                }, session_id)
            
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

    def _normalize_history_for_llm(
        self,
        provider: str,
        history: List[Dict],
        rag_context: str = "",
        use_rag: bool = False,
        agent_id: Optional[str] = None
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
                if role == Role.USER or role == "user":
                    normalized.append({"role": "user", "parts": [text]})
                elif role == Role.ASSISTANT or role == "assistant":
                    normalized.append({"role": "model", "parts": [text]})
                else:
                    normalized.append({"role": "user", "parts": [text]})
            else:
                if role == Role.USER or role == "user":
                    normalized.append({"role": "user", "content": text})
                elif role == Role.ASSISTANT or role == "assistant":
                    normalized.append({"role": "assistant", "content": text})
                else:
                    normalized.append({"role": "user", "content": text})

        return normalized

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
            raise ValueError(f"Fournisseur LLM non supporté pour le streaming: {provider}")

        async for chunk in streamer:
            yield chunk

    # ---------- NOUVEAU : réponse structurée (JSON) ----------
    async def get_structured_llm_response(self, agent_id: str, prompt: str, json_schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Appel non-stream pour obtenir un JSON structuré (utilisé par MemoryAnalyzer).
        Implémentation simple et robuste, avec fallback de parsing JSON.
        """
        provider, model, system_prompt = self._get_agent_config(agent_id)

        if provider == "google":
            model_instance = genai.GenerativeModel(model_name=model, system_instruction=system_prompt)
            schema_hint = json.dumps(json_schema, ensure_ascii=False)
            full_prompt = (
                f"{prompt}\n\n"
                f"IMPORTANT: Réponds EXCLUSIVEMENT en JSON valide correspondant strictement à ce SCHÉMA "
                f"(clés exactes, types conformes) : {schema_hint}"
            )
            resp = await model_instance.generate_content_async([{"role": "user", "parts": [full_prompt]}])
            text = getattr(resp, "text", "") or ""
            try:
                return json.loads(text) if text else {}
            except Exception:
                m = re.search(r"\{.*\}", text, re.S)
                return json.loads(m.group(0)) if m else {}

        elif provider == "openai":
            resp = await self.openai_client.chat.completions.create(
                model=model,
                temperature=0,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
            )
            content = (resp.choices[0].message.content or "").strip()
            return json.loads(content) if content else {}

        elif provider == "anthropic":
            resp = await self.anthropic_client.messages.create(
                model=model,
                max_tokens=1500,
                temperature=0,
                system=system_prompt + "\n\nRéponds strictement en JSON valide.",
                messages=[{"role": "user", "content": prompt}],
            )
            text = ""
            for block in getattr(resp, "content", []) or []:
                t = getattr(block, "text", "") or ""
                if t:
                    text += t
            try:
                return json.loads(text)
            except Exception:
                m = re.search(r"\{.*\}", text, re.S)
                return json.loads(m.group(0)) if m else {}

        return {}

    async def _get_openai_stream(self, model: str, system_prompt: str, history: List[Dict], cost_info_container: Dict) -> AsyncGenerator[str, None]:
        messages = [{"role": "system", "content": system_prompt}] + history
        stream = await self.openai_client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.2,
            max_tokens=4000,
            stream=True,
            stream_options={"include_usage": True}
        )
        final_chunk = None
        async for chunk in stream:
            # --- GUARD ROBUSTE SUR CHOICES ---
            choices = getattr(chunk, "choices", None) or []
            if not choices:
                if getattr(chunk, "usage", None):
                    final_chunk = chunk
                continue

            yielded = False
            for ch in choices:
                delta = getattr(ch, "delta", None)
                piece = getattr(delta, "content", "") or ""
                if piece:
                    yielded = True
                    yield piece

            if getattr(chunk, "usage", None):
                final_chunk = chunk
            if not yielded:
                # rien à émettre sur ce chunk (ex: tool/role/safety), on continue
                pass

        if final_chunk and getattr(final_chunk, "usage", None):
            usage = final_chunk.usage
            pricing = MODEL_PRICING.get(model, {"input": 0, "output": 0})
            cost = (usage.prompt_tokens * pricing["input"]) + (usage.completion_tokens * pricing["output"])
            cost_info_container.update({
                "input_tokens": usage.prompt_tokens,
                "output_tokens": usage.completion_tokens,
                "total_cost": cost
            })
        else:
            logger.warning(f"Impossible de récupérer les informations de coût pour le stream OpenAI (modèle: {model}). Coûts non enregistrés.")
            cost_info_container.update({"input_tokens": 0, "output_tokens": 0, "total_cost": 0.0, "note": "Cost not available for OpenAI streams"})

    async def _get_gemini_stream(self, model: str, system_prompt: str, history: List[Dict], cost_info_container: Dict) -> AsyncGenerator[str, None]:
        model_instance = genai.GenerativeModel(model_name=model, system_instruction=system_prompt)
        response = await model_instance.generate_content_async(history, stream=True)

        async for chunk in response:
            try:
                yield getattr(chunk, "text", "") or ""
            except Exception:
                continue

        try:
            await response.resolve()
        except Exception:
            pass

        usage = getattr(response, "usage_metadata", None)
        if usage:
            pricing = MODEL_PRICING.get(model, {"input": 0, "output": 0})
            cost = (getattr(usage, "prompt_token_count", 0) * pricing["input"]) + \
                   (getattr(usage, "candidates_token_count", 0) * pricing["output"])
            cost_info_container.update({
                "input_tokens": getattr(usage, "prompt_token_count", 0),
                "output_tokens": getattr(usage, "candidates_token_count", 0),
                "total_cost": cost
            })
        else:
            cost_info_container.update({"input_tokens": 0, "output_tokens": 0, "total_cost": 0.0, "note": "No usage metadata from Gemini"})

    async def _get_anthropic_stream(self, model: str, system_prompt: str, history: List[Dict], cost_info_container: Dict) -> AsyncGenerator[str, None]:
        try:
            messages = history
            resp = await self.anthropic_client.messages.create(
                model=model,
                max_tokens=4000,
                system=system_prompt,
                messages=messages,
                temperature=0.2,
            )
            text = ""
            try:
                for block in getattr(resp, "content", []) or []:
                    t = getattr(block, "text", "") or ""
                    if t:
                        text += t
            except Exception:
                pass

            yield text

            usage = getattr(resp, "usage", None)
            if usage:
                pricing = MODEL_PRICING.get(model, {"input": 0, "output": 0})
                in_tok = getattr(usage, "input_tokens", 0)
                out_tok = getattr(usage, "output_tokens", 0)
                cost = (in_tok * pricing["input"]) + (out_tok * pricing["output"])
                cost_info_container.update({
                    "input_tokens": in_tok,
                    "output_tokens": out_tok,
                    "total_cost": cost
                })
            else:
                cost_info_container.update({"input_tokens": 0, "output_tokens": 0, "total_cost": 0.0, "note": "No usage from Anthropic"})

        except Exception as e:
            logger.error(f"Erreur Anthropic (fallback non-stream): {e}", exc_info=True)
            yield ""
            cost_info_container.update({"input_tokens": 0, "output_tokens": 0, "total_cost": 0.0, "note": "Anthropic error"})
