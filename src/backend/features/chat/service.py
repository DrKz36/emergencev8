# src/backend/features/chat/service.py
# V31.4 — + meta.sources (RAG) dans ws:chat_stream_end  |  + logs inchangés
# Cf. V31.3: mémoire agent-aware, frames WS stables (model_info/fallback/memory_banner/rag_status)

import os, re, asyncio, logging, glob, json
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

from backend.features.memory.gardener import MemoryGardener

logger = logging.getLogger(__name__)

MODEL_PRICING = {
    "gpt-4o-mini": {"input": 0.15 / 1_000_000, "output": 0.60 / 1_000_000},
    "gpt-4o": {"input": 5.00 / 1_000_000, "output": 15.00 / 1_000_000},
    "gemini-1.5-flash": {"input": 0.35 / 1_000_000, "output": 0.70 / 1_000_000},
    "claude-3-haiku-20240307": {"input": 0.25 / 1_000_000, "output": 1.25 / 1_000_000},
    "claude-3-sonnet-20240229": {"input": 3.00 / 1_000_000, "output": 15.00 / 1_000_000},
    "claude-3-opus-20240229": {"input": 15.00 / 1_000_000, "output": 75.00 / 1_000_000},
}

def _normalize_provider(p: Optional[str]) -> str:
    if not p: return ""
    p = p.strip().lower()
    if p in ("gemini", "google", "googleai", "vertex"): return "google"
    if p in ("openai", "oai"): return "openai"
    if p in ("anthropic", "claude"): return "anthropic"
    return p

class ChatService:
    def __init__(self, session_manager: SessionManager, cost_tracker: CostTracker,
                 vector_service: VectorService, settings: Settings):
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
        logger.info(f"ChatService V31.4 initialisé. Prompts chargés: {len(self.prompts)}")

    # ---------- prompts ----------
    def _load_prompts(self, prompts_dir: str) -> Dict[str, str]:
        def weight(name: str) -> int:
            name = name.lower(); w = 0
            if "lite" in name: w = max(w, 1)
            if "v2"   in name: w = max(w, 2)
            if "v3"   in name: w = max(w, 3)
            return w
        chosen: Dict[str, Dict[str, Any]] = {}
        for file_path in glob.glob(os.path.join(prompts_dir, "*.md")):
            p = Path(file_path)
            agent_id = p.stem.replace("_system","").replace("_v2","").replace("_v3","").replace("_lite","")
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
        provider_raw = agent_configs.get(clean_agent_id, {}).get("provider")
        model = agent_configs.get(clean_agent_id, {}).get("model")
        provider = _normalize_provider(provider_raw)

        if clean_agent_id == 'anima':
            model = 'gpt-4o-mini'
            logger.info("Remplacement du modèle pour 'anima' -> 'gpt-4o-mini' (coûts).")

        system_prompt = self.prompts.get(agent_id, self.prompts.get(clean_agent_id, ""))

        if not provider or not model or system_prompt is None:
            raise ValueError(f"Configuration incomplète pour l'agent '{agent_id}' "
                             f"(provider='{provider_raw}', normalisé='{provider}', model='{model}').")

        return provider, model, system_prompt

    def _extract_sensitive_tokens(self, text: str) -> List[str]:
        return re.findall(r"\b[A-Z]{3,}-\d{3,}\b", text or "")

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
        knowledge_name = os.getenv("EMERGENCE_KNOWLEDGE_COLLECTION", "emergence_knowledge")
        col = self.vector_service.get_or_create_collection(knowledge_name)
        clauses = [{"type": "fact"}, {"key": "mot-code"}, {"agent": (agent_id or "").lower()}]
        if user_id:
            clauses.append({"user_id": user_id})
        where = {"$and": clauses}
        got = col.get(where=where, include=["documents", "metadatas"])
        ids = got.get("ids", []) or []
        if not ids:
            got = col.get(where={"$and": [{"type": "fact"}, {"key": "mot-code"}, {"agent": (agent_id or "").lower()}]},
                         include=["documents", "metadatas"])
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

    async def _build_memory_context(self, session_id: str, last_user_message: str,
                                    top_k: int = 5, agent_id: Optional[str] = None) -> str:
        try:
            if not last_user_message:
                return ""
            knowledge_name = os.getenv("EMERGENCE_KNOWLEDGE_COLLECTION", "emergence_knowledge")
            knowledge_col = self.vector_service.get_or_create_collection(knowledge_name)

            where_filter = None
            uid = self._try_get_user_id(session_id)
            clauses: List[Dict[str, Any]] = []
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
                where_filter=where_filter
            )

            if (not results) and ag and uid:
                try:
                    results = self.vector_service.query(
                        collection=knowledge_col,
                        query_text=last_user_message,
                        n_results=top_k,
                        where_filter={"user_id": uid}
                    )
                except Exception:
                    pass

            if not results:
                return ""
            lines = []
            for r in results:
                t = (r.get("text") or "").strip()
                if t:
                    lines.append(f"- {t}")
            return "\n".join(lines[:top_k])
        except Exception as e:
            logger.warning(f"build_memory_context: {e}")
            return ""

    def _normalize_history_for_llm(self, provider: str, history: List[Dict],
                                   rag_context: str = "", use_rag: bool = False,
                                   agent_id: Optional[str] = None) -> List[Dict]:
        normalized: List[Dict[str, Any]] = []
        if use_rag and rag_context:
            if provider == "google":
                normalized.append({"role": "user", "parts": [f"[RAG_CONTEXT]\n{rag_context}"]})
            else:
                normalized.append({"role": "user", "content": f"[RAG_CONTEXT]\n{rag_context}"})
        for m in history:
            role = m.get("role"); text = m.get("content") or m.get("message") or ""
            if not text:
                continue
            if provider == "google":
                normalized.append({"role": "user" if role in (Role.USER, "user") else "model", "parts": [text]})
            else:
                normalized.append({"role": "user" if role in (Role.USER, "user") else "assistant", "content": text})
        return normalized

    async def _get_llm_response_stream(self, provider: str, model: str, system_prompt: str,
                                       history: List[Dict], cost_info_container: Dict) -> AsyncGenerator[str, None]:
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

    async def _get_openai_stream(self, model: str, system_prompt: str, history: List[Dict], cost_info_container: Dict) -> AsyncGenerator[str, None]:
        messages = [{"role": "system", "content": system_prompt}] + history
        usage_seen = False
        try:
            stream = await self.openai_client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.4,
                stream=True,
                stream_options={"include_usage": True}
            )
            async for event in stream:
                try:
                    delta = event.choices[0].delta
                    text = getattr(delta, "content", None)
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
                    cost_info_container.update({
                        "input_tokens": in_tok,
                        "output_tokens": out_tok,
                        "total_cost": (in_tok * pricing["input"]) + (out_tok * pricing["output"])
                    })
        except Exception as e:
            logger.error(f"OpenAI stream error: {e}", exc_info=True)
            raise

    async def _get_gemini_stream(self, model: str, system_prompt: str, history: List[Dict], cost_info_container: Dict) -> AsyncGenerator[str, None]:
        try:
            model_instance = genai.GenerativeModel(model_name=model, system_instruction=system_prompt)
            resp = await model_instance.generate_content_async(history, stream=True, generation_config={"temperature": 0.4})
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
            cost_info_container.setdefault("input_tokens", 0)
            cost_info_container.setdefault("output_tokens", 0)
            cost_info_container.setdefault("total_cost", 0.0)
        except Exception as e:
            logger.error(f"Gemini stream error: {e}", exc_info=True)
            raise

    async def _get_anthropic_stream(self, model: str, system_prompt: str, history: List[Dict], cost_info_container: Dict) -> AsyncGenerator[str, None]:
        try:
            async with self.anthropic_client.messages.stream(
                model=model,
                max_tokens=1500,
                temperature=0.4,
                system=system_prompt,
                messages=history
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
                    final = await stream.get_final_response()
                    usage = getattr(final, "usage", None)
                    if usage:
                        pricing = MODEL_PRICING.get(model, {"input": 0, "output": 0})
                        in_tok = getattr(usage, "input_tokens", 0)
                        out_tok = getattr(usage, "output_tokens", 0)
                        cost_info_container.update({
                            "input_tokens": in_tok,
                            "output_tokens": out_tok,
                            "total_cost": (in_tok * pricing["input"]) + (out_tok * pricing["output"])
                        })
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"Anthropic stream error: {e}", exc_info=True)
            raise

    async def get_structured_llm_response(self, agent_id: str, prompt: str, json_schema: Dict[str, Any]) -> Dict[str, Any]:
        provider, model, system_prompt = self._get_agent_config(agent_id)
        if provider == "google":
            model_instance = genai.GenerativeModel(model_name=model, system_instruction=system_prompt)
            schema_hint = json.dumps(json_schema, ensure_ascii=False)
            full_prompt = f"{prompt}\n\nIMPORTANT: Réponds EXCLUSIVEMENT en JSON valide correspondant strictement à ce SCHÉMA : {schema_hint}"
            resp = await model_instance.generate_content_async([{"role": "user", "parts": [full_prompt]}])
            text = getattr(resp, "text", "") or ""
            try:
                return json.loads(text) if text else {}
            except Exception:
                m = re.search(r"\{.*\}", text, re.S)
                return json.loads(m.group(0)) if m else {}
        elif provider == "openai":
            resp = await self.openai_client.chat.completions.create(
                model=model, temperature=0, response_format={"type": "json_object"},
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}]
            )
            content = (resp.choices[0].message.content or "").strip()
            return json.loads(content) if content else {}
        elif provider == "anthropic":
            resp = await self.anthropic_client.messages.create(
                model=model, max_tokens=1500, temperature=0, system=system_prompt + "\n\nRéponds strictement en JSON valide.",
                messages=[{"role": "user", "content": prompt}]
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

    async def _process_agent_response_stream(self, session_id: str, agent_id: str, use_rag: bool,
                                             connection_manager: ConnectionManager):
        temp_message_id = str(uuid4())
        full_response_text = ""
        cost_info_container: Dict[str, Any] = {}
        model_used = ""
        # ---- NEW: capturer les sources RAG pour meta ----
        rag_sources: List[Dict[str, Any]] = []

        try:
            await connection_manager.send_personal_message(
                {"type": "ws:chat_stream_start", "payload": {"agent_id": agent_id, "id": temp_message_id}},
                session_id
            )

            history = self.session_manager.get_full_history(session_id)
            last_user_message_obj = next((m for m in reversed(history) if m.get("role") == Role.USER), None)
            last_user_message = last_user_message_obj.get("content", "") if last_user_message_obj else ""

            if self._is_mot_code_query(last_user_message):
                uid = self._try_get_user_id(session_id)
                mot = self._fetch_mot_code_for_agent(agent_id, uid)
                try:
                    stm_here = self._try_get_session_summary(session_id)
                    await connection_manager.send_personal_message(
                        {"type": "ws:memory_banner",
                         "payload": {"agent_id": agent_id, "has_stm": bool(stm_here),
                                     "ltm_items": 0, "injected_into_prompt": False}},
                        session_id
                    )
                except Exception:
                    pass

                if mot:
                    final_agent_message = AgentMessage(
                        id=temp_message_id, session_id=session_id, role=Role.ASSISTANT, agent=agent_id,
                        message=mot, timestamp=datetime.now(timezone.utc).isoformat(), cost_info={}
                    )
                    await self.session_manager.add_message_to_session(session_id, final_agent_message)
                    payload = final_agent_message.model_dump(mode="json")
                    if "message" in payload:
                        payload["content"] = payload.pop("message")
                    payload.setdefault("meta", {"provider": "memory", "model": "mot-code", "fallback": False})
                    await connection_manager.send_personal_message(
                        {"type": "ws:chat_stream_end", "payload": payload}, session_id
                    )
                    if os.getenv("EMERGENCE_AUTO_TEND", "1") != "0":
                        try:
                            gardener = MemoryGardener(
                                db_manager=getattr(self.session_manager, "db_manager", None),
                                vector_service=self.vector_service,
                                memory_analyzer=getattr(self.session_manager, "memory_analyzer", None),
                            )
                            asyncio.create_task(gardener.tend_the_garden(consolidation_limit=3))
                        except Exception:
                            pass
                    return

            stm = self._try_get_session_summary(session_id)
            ltm_block = await self._build_memory_context(session_id, last_user_message, top_k=5, agent_id=agent_id) if last_user_message else ""

            if use_rag:
                memory_context = self._merge_blocks([("Résumé de session", stm)]) if stm else ""
                ltm_count_for_banner = self._count_bullets(ltm_block)
            else:
                memory_context = self._merge_blocks([("Résumé de session", stm), ("Faits & souvenirs", ltm_block)])
                ltm_count_for_banner = self._count_bullets(ltm_block)

            injected = bool(memory_context and memory_context.strip())
            if injected:
                history = [{"role": Role.USER, "content": f"[MEMORY_CONTEXT]\n{memory_context}"}] + history

            try:
                await connection_manager.send_personal_message(
                    {"type": "ws:memory_banner",
                     "payload": {"agent_id": agent_id, "has_stm": bool(stm),
                                 "ltm_items": int(ltm_count_for_banner), "injected_into_prompt": bool(injected)}},
                    session_id
                )
            except Exception:
                pass

            rag_context = ""
            if use_rag and last_user_message:
                await connection_manager.send_personal_message(
                    {"type": "ws:rag_status", "payload": {"status": "searching", "agent_id": agent_id}},
                    session_id
                )
                document_collection = self.vector_service.get_or_create_collection(config.DOCUMENT_COLLECTION_NAME)
                doc_hits = self.vector_service.query(collection=document_collection, query_text=last_user_message)

                # ---- NEW: préparer sources pour meta ----
                rag_sources = []
                for h in (doc_hits or []):
                    md = h.get("metadata") or {}
                    excerpt = (h.get("text") or "").strip()
                    if excerpt:
                        excerpt = excerpt[:220].rstrip()
                    rag_sources.append({
                        "document_id": md.get("document_id"),
                        "filename": md.get("filename"),
                        "page": md.get("page"),  # peut être None si non géré au parsing
                        "excerpt": excerpt
                    })

                doc_block = "\n\n".join([f"- {h['text']}" for h in (doc_hits or []) if h.get("text")]) if doc_hits else ""
                mem_block = await self._build_memory_context(session_id, last_user_message, agent_id=agent_id)
                rag_context = self._merge_blocks([("Mémoire (concepts clés)", mem_block),
                                                  ("Documents pertinents", doc_block)])
                await connection_manager.send_personal_message(
                    {"type": "ws:rag_status", "payload": {"status": "found", "agent_id": agent_id}}, session_id
                )

            raw_concat = "\n".join([(m.get("content") or m.get("message", "")) for m in history])
            raw_tokens = self._extract_sensitive_tokens(raw_concat)
            await connection_manager.send_personal_message(
                {"type": "ws:debug_context",
                 "payload": {"phase": "before_normalize", "agent_id": agent_id, "use_rag": use_rag,
                             "history_total": len(history), "rag_context_chars": len(rag_context),
                             "off_policy": self.off_history_policy,
                             "sensitive_tokens_in_history": list(set(raw_tokens))}},
                session_id
            )

            provider, model, system_prompt = self._get_agent_config(agent_id)
            primary_provider, primary_model = provider, model
            model_used = primary_model

            try:
                await connection_manager.send_personal_message(
                    {"type": "ws:model_info",
                     "payload": {"agent_id": agent_id, "id": temp_message_id,
                                 "provider": primary_provider, "model": primary_model}},
                    session_id
                )
            except Exception:
                pass
            logger.info(json.dumps({
                "event": "model_info",
                "agent_id": agent_id,
                "session_id": session_id,
                "provider": primary_provider,
                "model": primary_model
            }))

            normalized_history = self._normalize_history_for_llm(provider, history, rag_context, use_rag, agent_id)

            norm_concat = "\n".join(["".join(p.get("parts", [])) if provider == "google" else p.get("content", "")
                                     for p in normalized_history])
            norm_tokens = self._extract_sensitive_tokens(norm_concat)
            await connection_manager.send_personal_message(
                {"type": "ws:debug_context",
                 "payload": {"phase": "after_normalize", "agent_id": agent_id, "use_rag": use_rag,
                             "history_filtered": len(normalized_history), "rag_context_chars": len(rag_context),
                             "off_policy": self.off_history_policy,
                             "sensitive_tokens_in_prompt": list(set(norm_tokens))}},
                session_id
            )

            async def _stream_with(provider_name, model_name, hist):
                return self._get_llm_response_stream(provider_name, model_name, system_prompt, hist, cost_info_container)

            success = False
            try:
                async for chunk in (await _stream_with(primary_provider, primary_model, normalized_history)):
                    if chunk:
                        full_response_text += chunk
                        await connection_manager.send_personal_message(
                            {"type": "ws:chat_stream_chunk",
                             "payload": {"agent_id": agent_id, "id": temp_message_id, "chunk": chunk}},
                            session_id
                        )
                model_used = primary_model
                success = True
            except Exception as e_primary:
                fallbacks = []
                if primary_provider == "google":
                    fallbacks = [("anthropic", "claude-3-haiku-20240307"), ("openai", "gpt-4o-mini")]
                elif primary_provider == "anthropic":
                    fallbacks = [("openai", "gpt-4o-mini")]
                elif primary_provider == "openai":
                    fallbacks = [("anthropic", "claude-3-haiku-20240307")]

                last_error = e_primary
                for prov2, model2 in fallbacks:
                    try:
                        await connection_manager.send_personal_message(
                            {"type": "ws:model_fallback",
                             "payload": {"agent_id": agent_id, "id": temp_message_id,
                                         "from_provider": primary_provider, "from_model": primary_model,
                                         "to_provider": prov2, "to_model": model2,
                                         "reason": str(e_primary)}},
                            session_id
                        )
                    except Exception:
                        pass
                    logger.warning(json.dumps({
                        "event": "model_fallback",
                        "agent_id": agent_id,
                        "session_id": session_id,
                        "from_provider": primary_provider,
                        "from_model": primary_model,
                        "to_provider": prov2,
                        "to_model": model2,
                        "reason": str(e_primary)
                    }))

                    norm2 = self._normalize_history_for_llm(prov2, history, rag_context, use_rag, agent_id)
                    try:
                        async for chunk in (await _stream_with(prov2, model2, norm2)):
                            if chunk:
                                full_response_text += chunk
                                await connection_manager.send_personal_message(
                                    {"type": "ws:chat_stream_chunk",
                                     "payload": {"agent_id": agent_id, "id": temp_message_id, "chunk": chunk}},
                                    session_id
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

            final_agent_message = AgentMessage(
                id=temp_message_id, session_id=session_id, role=Role.ASSISTANT, agent=agent_id,
                message=full_response_text, timestamp=datetime.now(timezone.utc).isoformat(),
                cost_info=cost_info_container
            )
            await self.session_manager.add_message_to_session(session_id, final_agent_message)
            await self.cost_tracker.record_cost(
                agent=agent_id, model=model_used,
                input_tokens=cost_info_container.get("input_tokens", 0),
                output_tokens=cost_info_container.get("output_tokens", 0),
                total_cost=cost_info_container.get("total_cost", 0.0),
                feature="chat",
            )
            payload = final_agent_message.model_dump(mode="json")
            if "message" in payload:
                payload["content"] = payload.pop("message")
            payload["meta"] = {
                "provider": provider,
                "model": model_used,
                "fallback": bool(provider != primary_provider)
            }
            # ---- NEW: injecter les sources RAG si dispo ----
            try:
                if use_rag and rag_sources:
                    payload["meta"]["sources"] = rag_sources
            except Exception:
                pass

            await connection_manager.send_personal_message(
                {"type": "ws:chat_stream_end", "payload": payload}, session_id
            )

            if os.getenv("EMERGENCE_AUTO_TEND", "1") != "0":
                try:
                    gardener = MemoryGardener(
                        db_manager=getattr(self.session_manager, "db_manager", None),
                        vector_service=self.vector_service,
                        memory_analyzer=getattr(self.session_manager, "memory_analyzer", None),
                    )
                    asyncio.create_task(gardener.tend_the_garden(consolidation_limit=3))
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
                logger.error(f"Impossible d'envoyer l'erreur au client (session {session_id}): {send_error}", exc_info=True)

    def get_llm_response_for_debate(self, *a, **k):  # unchanged below
        return super().get_llm_response_for_debate(*a, **k)  # type: ignore[misc]

    def process_user_message_for_agents(self, session_id: str, chat_request: Any, connection_manager: ConnectionManager) -> None:
        get = (lambda k: (chat_request.get(k) if isinstance(chat_request, dict) else getattr(chat_request, k, None)))
        agent_id = (get("agent_id") or "").strip().lower()
        use_rag  = bool(get("use_rag"))
        if not agent_id:
            logger.error("process_user_message_for_agents: agent_id manquant")
            return
        asyncio.create_task(self._process_agent_response_stream(session_id, agent_id, use_rag, connection_manager))

    def _count_bullets(self, text: str) -> int:
        return sum(1 for line in (text or "").splitlines() if line.strip().startswith("- "))
