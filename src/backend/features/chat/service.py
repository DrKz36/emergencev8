# src/backend/features/chat/service.py
# V30.2 — MEMORY M1: policy=agent_local (stateful), analyse avant close (avec history), mute chroma telemetry
# + Anti-dup in-flight: supprime les 2e streams pour le même (session, agent, dernier message)
import os, re, asyncio, logging, glob, json, inspect
from uuid import uuid4
from typing import Dict, Any, List, Tuple, Optional, AsyncGenerator
from pathlib import Path
from datetime import datetime, timezone, timedelta

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

# Auto-consolidation mémoire
from backend.features.memory.gardener import MemoryGardener

logger = logging.getLogger(__name__)

# --- Mute chroma telemetry (P1.5) -------------------------------------------
try:
    logging.getLogger("chromadb.telemetry").setLevel(logging.CRITICAL)
    logging.getLogger("chromadb.telemetry.product.posthog").setLevel(logging.CRITICAL)
except Exception:
    pass

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

        # Policy par défaut = agent_local (stateful)
        self.off_history_policy = os.getenv("EMERGENCE_RAG_OFF_POLICY", "agent_local").strip().lower()
        if self.off_history_policy not in ("stateless", "agent_local"):
            self.off_history_policy = "agent_local"
        logger.info(f"ChatService OFF policy: {self.off_history_policy}")

        try:
            self.openai_client = AsyncOpenAI(api_key=self.settings.openai_api_key)
            genai.configure(api_key=self.settings.google_api_key)
            self.anthropic_client = AsyncAnthropic(api_key=self.settings.anthropic_api_key)
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation des clients API: {e}", exc_info=True)
            raise

        self.prompts = self._load_prompts(self.settings.paths.prompts)
        logger.info(f"ChatService V30.2 initialisé. Prompts chargés: {len(self.prompts)}")

        # Garde anti-dup in-flight: (session_id, agent_id) -> {"text": str, "since": datetime}
        self._inflight: Dict[str, Dict[str, Any]] = {}

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

    # ---------- utils mémoire ----------
    def _extract_sensitive_tokens(self, text: str) -> List[str]:
        return re.findall(r"\b[A-Z]{3,}-\d{3,}\b", text or "")

    def _try_get_user_id(self, session_id: str) -> Optional[str]:
        for attr in ("get_user_id_for_session", "get_user", "get_owner", "get_session_owner"):
            try:
                fn = getattr(self.session_manager, attr, None)
                if callable(fn):
                    uid = fn(session_id)
                    if uid: return str(uid)
            except Exception:
                pass
        for attr in ("current_user_id", "user_id"):
            try:
                uid = getattr(self.session_manager, attr, None)
                if uid: return str(uid)
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
            if not ids: return None
        docs = got.get("documents", []) or []
        if not docs: return None
        line = docs[0] or ""
        if ":" in line:
            try: return line.split(":", 1)[1].strip()
            except Exception: pass
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
                if isinstance(s, str) and s.strip(): return s.strip()
        except Exception:
            pass
        return ""

    def _count_bullets(self, text: str) -> int:
        return sum(1 for line in (text or "").splitlines() if line.strip().startswith("- "))

    async def _build_memory_context(self, session_id: str, last_user_message: str, top_k: int = 5) -> str:
        try:
            if not last_user_message: return ""
            knowledge_name = os.getenv("EMERGENCE_KNOWLEDGE_COLLECTION", "emergence_knowledge")
            knowledge_col = self.vector_service.get_or_create_collection(knowledge_name)

            where_filter = None
            uid = self._try_get_user_id(session_id)
            if uid: where_filter = {"user_id": uid}

            results = self.vector_service.query(
                collection=knowledge_col,
                query_text=last_user_message,
                n_results=top_k,
                where_filter=where_filter
            )
            if not results: return ""
            lines = []
            for r in results:
                t = (r.get("text") or "").strip()
                if t: lines.append(f"- {t}")
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
            if not text: continue
            if provider == "google":
                normalized.append({"role": "user" if role in (Role.USER, "user") else "model", "parts": [text]})
            else:
                normalized.append({"role": "user" if role in (Role.USER, "user") else "assistant", "content": text})
        return normalized

    # ---------- stream providers ----------
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
                    if text: yield text
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
                    if text: yield text
                except Exception:
                    pass
            cost_info_container.setdefault("input_tokens", 0)
            cost_info_container.setdefault("output_tokens", 0)
            cost_info_container.setdefault("total_cost", 0.0)
        except Exception as e:
            logger.error(f"Gemini stream error: {e}", exc_info=True)

    async def _get_anthropic_stream(self, model: str, system_prompt: str, history: List[Dict], cost_info_container: Dict) -> AsyncGenerator[str, None]:
        try:
            async with self.anthropic_client.messages.stream(
                model=model, max_tokens=1500, temperature=0.4,
                system=system_prompt, messages=history
            ) as stream:
                async for event in stream:
                    try:
                        if getattr(event, "type", "") == "content_block_delta":
                            delta = getattr(event, "delta", None)
                            if delta:
                                text = getattr(delta, "text", "") or ""
                                if text: yield text
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

    # ---------- structured JSON ----------
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
                if t: text += t
            try:
                return json.loads(text)
            except Exception:
                m = re.search(r"\{.*\}", text, re.S)
                return json.loads(m.group(0)) if m else {}
        return {}

    # ---------- analyse & notifications ---------------------------------------
    async def _run_analysis_and_notify(self, session_id: str, agent_id: str, connection_manager: ConnectionManager) -> None:
        """Exécute l'analyse post-session et notifie le client (completed/error) sur la même WS."""
        try:
            analyzer = getattr(self.session_manager, "memory_analyzer", None)
            history = self.session_manager.get_full_history(session_id) or []
            if analyzer and hasattr(analyzer, "analyze_session_for_concepts"):
                try:
                    sig = inspect.signature(analyzer.analyze_session_for_concepts)
                    if "history" in sig.parameters:
                        await analyzer.analyze_session_for_concepts(session_id, history)
                    else:
                        await analyzer.analyze_session_for_concepts(session_id)
                except TypeError:
                    # rétro-compat si signature ancienne
                    await analyzer.analyze_session_for_concepts(session_id)
                # (patch) Analyzer will emit its own ws:analysis_status events; skip duplicated "completed".

            else:
                try:
                    await connection_manager.send_personal_message(
                        {"type": "ws:analysis_status",
                         "payload": {"status": "skipped", "reason": "analyzer_unavailable", "agent_id": agent_id}},
                        session_id
                    )
                except Exception:
                    pass
        except Exception as e:
            logger.warning(f"Memory analysis error: {e}")
            try:
                await connection_manager.send_personal_message(
                    {"type": "ws:analysis_status",
                     "payload": {"status": "error", "agent_id": agent_id, "error": str(e)}},
                    session_id
                )
            except Exception:
                pass

    # ---------- flux chat (stream) ----------
    async def _process_agent_response_stream(self, session_id: str, agent_id: str, use_rag: bool,
                                             connection_manager: ConnectionManager):
        temp_message_id = str(uuid4())
        full_response_text = ""
        cost_info_container: Dict[str, Any] = {}
        model_used = ""

        # Anti-dup in-flight: clé session/agent
        inflight_key = f"{session_id}::{agent_id}"
        last_user_message = ""

        try:
            # Start du stream côté client
            await connection_manager.send_personal_message(
                {"type": "ws:chat_stream_start", "payload": {"agent_id": agent_id, "id": temp_message_id}},
                session_id
            )

            # Historique & dernier message user
            history = self.session_manager.get_full_history(session_id)
            last_user_message_obj = next((m for m in reversed(history) if m.get("role") == Role.USER), None)
            last_user_message = last_user_message_obj.get("content", "") if last_user_message_obj else ""

            # Garde anti-dup: si un stream est déjà parti pour ce même texte tout de suite avant → on abandonne
            try:
                info = self._inflight.get(inflight_key)
                if info and info.get("text", "") == (last_user_message or ""):
                    since = info.get("since")
                    if isinstance(since, datetime) and (datetime.now(timezone.utc) - since) < timedelta(seconds=3):
                        logger.warning(f"[dedupe] Stream doublon ignoré pour agent={agent_id} (texte identique dans fenêtre courte).")
                        return
            except Exception:
                pass
            # On enregistre ce stream comme actif
            self._inflight[inflight_key] = {"text": last_user_message or "", "since": datetime.now(timezone.utc)}

            # Court-circuit "mot-code"
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
                    if "message" in payload: payload["content"] = payload.pop("message")

                    try:
                        await connection_manager.send_personal_message(
                            {"type": "ws:analysis_status", "payload": {"status": "started", "agent_id": agent_id, "session_id": session_id}},
                            session_id
                        )
                        asyncio.create_task(self._run_analysis_and_notify(session_id, agent_id, connection_manager))
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
                    return

            stm = self._try_get_session_summary(session_id)
            ltm_block = await self._build_memory_context(session_id, last_user_message, top_k=5) if last_user_message else ""

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
                doc_block = "\n\n".join([f"- {h['text']}" for h in doc_hits]) if doc_hits else ""
                mem_block = await self._build_memory_context(session_id, last_user_message)
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
            model_used = model
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

            response_generator = self._get_llm_response_stream(provider, model, system_prompt,
                                                               normalized_history, cost_info_container)
            async for chunk in response_generator:
                if chunk:
                    full_response_text += chunk
                    await connection_manager.send_personal_message(
                        {"type": "ws:chat_stream_chunk",
                         "payload": {"agent_id": agent_id, "id": temp_message_id, "chunk": chunk}},
                        session_id
                    )
            # (patch) Provider fallback on empty response / rate-limit
            try:
                if not full_response_text and cost_info_container.get("__error__") in ("rate_limit","provider_error"):
                    # default retry-after info for UI
                    retry_after = cost_info_container.get("__retry_after__")
                    # Fallback only for Gemini -> Claude Haiku on 'neo'
                    if agent_id == "neo":
                        try:
                            await connection_manager.send_personal_message(
                                {"type": "ws:debug_context",
                                 "payload": {"phase": "model_fallback", "from": model_used, "to": "claude-3-haiku-20240307"}},
                                session_id
                            )
                        except Exception:
                            pass
                        # Reuse same history/system prompt
                        fallback_cost: Dict[str, Any] = {}
                        alt_stream = self._get_llm_response_stream("anthropic", "claude-3-haiku-20240307", system_prompt, normalized_history, fallback_cost)
                        async for chunk in alt_stream:
                            if chunk:
                                full_response_text += chunk
                                await connection_manager.send_personal_message(
                                    {"type": "ws:chat_stream_chunk",
                                     "payload": {"agent_id": agent_id, "id": temp_message_id, "chunk": chunk}},
                                    session_id
                                )
                        # Merge cost info
                        try:
                            for k,v in fallback_cost.items():
                                if isinstance(v, (int,float)) and isinstance(cost_info_container.get(k), (int,float)):
                                    cost_info_container[k] += v
                                else:
                                    cost_info_container[k] = v
                        except Exception:
                            pass
                    # If still nothing, notify error and abort gracefully
                    if not full_response_text:
                        try:
                            await connection_manager.send_personal_message(
                                {"type": "ws:error",
                                 "payload": {"message": "rate_limited", "agent_id": agent_id, "retry_after": retry_after}},
                                session_id
                            )
                        except Exception:
                            pass
                        return
            except Exception:
                pass



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
            if "message" in payload: payload["content"] = payload.pop("message")

            try:
                await connection_manager.send_personal_message(
                    {"type": "ws:analysis_status", "payload": {"status": "started", "agent_id": agent_id, "session_id": session_id}},
                    session_id
                )
                asyncio.create_task(self._run_analysis_and_notify(session_id, agent_id, connection_manager))
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
        finally:
            # Libère le lock in-flight si on l'avait posé
            try:
                info = self._inflight.get(inflight_key)
                if info and info.get("text", "") == (last_user_message or ""):
                    self._inflight.pop(inflight_key, None)
            except Exception:
                pass

    # ---------- débat (inchangé) ----------
    async def get_llm_response_for_debate(
        self,
        agent_id: str,
        prompt: Optional[str] = None,
        *,
        rag_context: str = "",
        use_rag: bool = False,
        temperature: float = 0.3,
        max_tokens: int = 1500,
        **kwargs
    ) -> Tuple[str, Dict[str, Any]]:
        if prompt is None or (isinstance(prompt, str) and not prompt.strip()):
            for key in ("text", "content", "message", "prompt_text", "input", "summary",
                        "synthesis", "instruction", "instructions"):
                val = kwargs.get(key)
                if isinstance(val, str) and val.strip():
                    prompt = val
                    break

        if prompt is None or not str(prompt).strip():
            transcript = kwargs.get("transcript") or kwargs.get("context") or ""
            topic = kwargs.get("topic") or ""
            lines = [
                "Tu es 'Nexus', chargé de CONCLURE un débat.",
                f"Synthétise en 5 points clairs (faits, convergences, désaccords, angles aveugles, pistes) le débat sur : {topic or '—'}.",
            ]
            if isinstance(transcript, str) and transcript.strip():
                lines.append("Transcript ci-dessous:")
                lines.append(transcript)
            prompt = "\n".join(lines)

        prompt = str(prompt or "").strip()
        provider, model, system_prompt = self._get_agent_config(agent_id)
        base_cost: Dict[str, Any] = {"input_tokens": 0, "output_tokens": 0, "total_cost": 0.0}

        async def _openai_call(p: str) -> Tuple[str, Dict[str, Any]]:
            resp = await self.openai_client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": p}],
                temperature=temperature, max_tokens=max_tokens
            )
            text = (resp.choices[0].message.content or "").strip()
            usage = getattr(resp, "usage", None)
            if usage:
                pricing = MODEL_PRICING.get(model, {"input": 0, "output": 0})
                cost = (usage.prompt_tokens * pricing["input"]) + (usage.completion_tokens * pricing["output"])
                return text, {"input_tokens": usage.prompt_tokens, "output_tokens": usage.completion_tokens, "total_cost": cost}
            return text, dict(base_cost)

        try:
            if provider == "openai":
                return await _openai_call(prompt)

            elif provider == "google":
                model_instance = genai.GenerativeModel(model_name=model, system_instruction=system_prompt)
                parts = []
                if use_rag and rag_context:
                    parts.append({"role": "user", "parts": [f"[RAG_CONTEXT]\n{rag_context}"]})
                parts.append({"role": "user", "parts": [prompt]})
                resp = await model_instance.generate_content_async(parts, generation_config={"temperature": temperature})
                text = getattr(resp, "text", "") or ""
                usage = getattr(resp, "usage_metadata", None)
                if usage:
                    pricing = MODEL_PRICING.get(model, {"input": 0, "output": 0})
                    cost = (getattr(usage, "prompt_token_count", 0) * pricing["input"]) + (getattr(usage, "candidates_token_count", 0) * pricing["output"])
                    return text, {
                        "input_tokens": getattr(usage, "prompt_token_count", 0),
                        "output_tokens": getattr(usage, "candidates_token_count", 0),
                        "total_cost": cost
                    }
                return text, dict(base_cost)

            elif provider == "anthropic":
                content_text = f"[RAG_CONTEXT]\n{rag_context}\n\n{prompt}" if use_rag and rag_context else prompt
                try:
                    resp = await self.anthropic_client.messages.create(
                        model=model, max_tokens=max_tokens, temperature=temperature,
                        system=system_prompt, messages=[{"role": "user", "content": content_text}]
                    )
                    text = ""
                    for block in getattr(resp, "content", []) or []:
                        t = getattr(block, "text", "") or ""
                        if t: text += t
                    usage = getattr(resp, "usage", None)
                    if usage:
                        pricing = MODEL_PRICING.get(model, {"input": 0, "output": 0})
                        in_tok = getattr(usage, "input_tokens", 0); out_tok = getattr(usage, "output_tokens", 0)
                        cost = (in_tok * pricing["input"]) + (out_tok * pricing["output"])
                        cost_info = {"input_tokens": in_tok, "output_tokens": out_tok, "total_cost": cost}
                    else:
                        cost_info = dict(base_cost)
                    if not text.strip():
                        logger.warning("[DEBATE] Anthropic a renvoyé un texte vide — fallback OpenAI.")
                        return await _openai_call(prompt)
                    return text.strip(), cost_info
                except Exception as e:
                    logger.error(f"[DEBATE] Anthropic erreur, fallback OpenAI (agent={agent_id}): {e}")
                    return await _openai_call(prompt)

            else:
                raise ValueError(f"Fournisseur non supporté: {provider}")

        except Exception as e:
            logger.error(f"[DEBATE] get_llm_response_for_debate erreur (agent={agent_id}): {e}", exc_info=True)
            return "", {**base_cost, "note": f"error: {e}"}

    # ---------- entrée router ----------
    def process_user_message_for_agents(self, session_id: str, chat_request: Any, connection_manager: ConnectionManager) -> None:
        get = (lambda k: (chat_request.get(k) if isinstance(chat_request, dict) else getattr(chat_request, k, None)))
        agent_id = (get("agent_id") or "").strip().lower()
        use_rag  = bool(get("use_rag"))
        if not agent_id:
            logger.error("process_user_message_for_agents: agent_id manquant")
            return
        asyncio.create_task(self._process_agent_response_stream(session_id, agent_id, use_rag, connection_manager))
