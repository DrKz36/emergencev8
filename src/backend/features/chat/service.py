# src/backend/features/chat/service.py
# V31.2 “Citadelle+fallbacks-fixed” — re-normalisation cross-provider (chat stream) + double fallback
import os, re, asyncio, logging, glob, json
from uuid import uuid4
from typing import Dict, Any, List, Tuple, Optional, AsyncGenerator
from pathlib import Path
from datetime import datetime, timezone, timedelta

import google.generativeai as genai
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
try:
    import anthropic as _anth_pkg
    _AnthropicRateLimit = getattr(_anth_pkg, "RateLimitError", Exception)
except Exception:  # pragma: no cover
    _AnthropicRateLimit = Exception

from backend.core.session_manager import SessionManager
from backend.core.cost_tracker import CostTracker
from backend.core.websocket import ConnectionManager
from backend.shared.models import AgentMessage, Role, ChatMessage
from backend.features.memory.vector_service import VectorService
from backend.shared.config import Settings
from backend.core import config
from backend.features.memory.gardener import MemoryGardener

# ⬇️ Modules délégués
from .pricing import MODEL_PRICING
from .llm_stream import LLMStreamer
from .memory_ctx import MemoryContextBuilder
from .post_session import run_analysis_and_notify

logger = logging.getLogger(__name__)

try:
    logging.getLogger("chromadb.telemetry").setLevel(logging.CRITICAL)
    logging.getLogger("chromadb.telemetry.product.posthog").setLevel(logging.CRITICAL)
except Exception:
    pass


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
    def __init__(self, session_manager: SessionManager, cost_tracker: CostTracker,
                 vector_service: VectorService, settings: Settings):
        self.session_manager = session_manager
        self.cost_tracker = cost_tracker
        self.vector_service = vector_service
        self.settings = settings

        self.off_history_policy = os.getenv("EMERGENCE_RAG_OFF_POLICY", "agent_local").strip().lower()
        if self.off_history_policy not in ("stateless", "agent_local"):
            self.off_history_policy = "agent_local"
        logger.info(f"ChatService OFF policy: {self.off_history_policy}")

        try:
            self.openai_client = AsyncOpenAI(api_key=self.settings.openai_api_key)
            genai.configure(api_key=self.settings.google_api_key)
            self.anthropic_client = AsyncAnthropic(api_key=self.settings.anthropic_api_key)
        except Exception as e:
            logger.error(f"Erreur init clients API: {e}", exc_info=True)
            raise

        self.prompts = self._load_prompts(self.settings.paths.prompts)
        logger.info(f"ChatService V31.2 initialisé. Prompts: {len(self.prompts)}")

        self._inflight: Dict[str, Dict[str, Any]] = {}

        self.enable_analysis = os.getenv("EMERGENCE_ANALYSIS_ENABLED", "0") != "0"
        self.send_debug_ctx = os.getenv("EMERGENCE_SEND_DEBUG_CONTEXT", "0") != "0"
        self.stream_max_history = int(os.getenv("EMERGENCE_STREAM_MAX_HISTORY", "40"))
        self._rate_max_retries = int(os.getenv("EMERGENCE_RATE_LIMIT_MAX_RETRIES", "2"))
        self._rate_base_delay = float(os.getenv("EMERGENCE_RATE_LIMIT_BASE_DELAY", "2.0"))

        self._rl = {
            "openai": asyncio.Semaphore(int(os.getenv("EMERGENCE_CONCURRENCY_OPENAI", "3"))),
            "google": asyncio.Semaphore(int(os.getenv("EMERGENCE_CONCURRENCY_GOOGLE", "3"))),
            "anthropic": asyncio.Semaphore(int(os.getenv("EMERGENCE_CONCURRENCY_ANTHROPIC", "1"))),
        }

        self.streamer = LLMStreamer(
            self.openai_client, self.anthropic_client, self._rl,
            base_delay=self._rate_base_delay, max_retries=self._rate_max_retries
        )
        self.memory = MemoryContextBuilder(self.session_manager, self.vector_service)

    # ---------- Prompts ----------
    def _load_prompts(self, prompts_dir: str) -> Dict[str, str]:
        def weight(name: str) -> int:
            name = name.lower()
            w = 0
            if "lite" in name: w = max(w, 1)
            if "v2"  in name: w = max(w, 2)
            if "v3"  in name: w = max(w, 3)
            return w

        chosen: Dict[str, Dict[str, Any]] = {}
        for file_path in glob.glob(os.path.join(prompts_dir, "*.md")):
            p = Path(file_path)
            agent_id = p.stem.replace("_system", "").replace("_v2", "").replace("_v3", "").replace("_lite", "")
            w = weight(p.name)
            if agent_id not in chosen or w > chosen[agent_id]["w"]:
                with open(file_path, "r", encoding="utf-8") as f:
                    chosen[agent_id] = {"w": w, "text": f.read(), "file": p.name}
        for aid, meta in chosen.items():
            logger.info(f"Prompt retenu pour l'agent '{aid}': {meta['file']}")
        return {aid: meta["text"] for aid, meta in chosen.items()}

    def _get_agent_config(self, agent_id: str) -> Tuple[str, str, str]:
        clean_agent_id = agent_id.replace("_lite", "")
        agent_configs = self.settings.agents
        provider_raw = agent_configs.get(clean_agent_id, {}).get("provider")
        model = agent_configs.get(clean_agent_id, {}).get("model")
        provider = _normalize_provider(provider_raw)

        if clean_agent_id == "anima":
            model = "gpt-4o-mini"
            logger.info("Remplacement du modèle pour 'anima' -> 'gpt-4o-mini' (coûts).")

        system_prompt = self.prompts.get(agent_id, self.prompts.get(clean_agent_id, ""))
        if not provider or not model or system_prompt is None:
            raise ValueError(
                f"Configuration incomplète pour l'agent '{agent_id}' "
                f"(provider='{provider_raw}', normalisé='{provider}', model='{model}')."
            )
        return provider, model, system_prompt

    # ---------- Entrée routeur ----------
    def process_user_message_for_agents(
        self, session_id: str, chat_request: Any, connection_manager: ConnectionManager
    ) -> None:
        get = lambda k: (chat_request.get(k) if isinstance(chat_request, dict) else getattr(chat_request, k, None))
        agent_id = (get("agent_id") or "").strip().lower()
        use_rag = bool(get("use_rag"))
        if not agent_id:
            logger.error("process_user_message_for_agents: agent_id manquant")
            return
        asyncio.create_task(
            self._process_agent_response_stream(session_id, agent_id, use_rag, connection_manager)
        )

    # ---------- Flux chat (stream) ----------
    async def _process_agent_response_stream(
        self, session_id: str, agent_id: str, use_rag: bool, connection_manager: ConnectionManager
    ):
        temp_message_id = str(uuid4())
        full_response_text = ""
        cost_info_container: Dict[str, Any] = {}
        model_used = ""

        inflight_key = f"{session_id}::{agent_id}"
        last_user_message = ""

        try:
            # Historique & dernier message user
            history = self.session_manager.get_full_history(session_id) or []
            if self.stream_max_history and len(history) > self.stream_max_history:
                history = history[-self.stream_max_history:]
            last_user_message_obj = next((m for m in reversed(history) if m.get("role") == Role.USER), None)
            last_user_message = last_user_message_obj.get("content", "") if last_user_message_obj else ""

            # Anti-dup court (3s)
            try:
                info = self._inflight.get(inflight_key)
                if info and info.get("text", "") == (last_user_message or ""):
                    since = info.get("since")
                    if isinstance(since, datetime) and (datetime.now(timezone.utc) - since) < timedelta(seconds=3):
                        logger.warning(f"[dedupe] Stream doublon ignoré pour agent={agent_id} (texte identique < 3s).")
                        return
            except Exception:
                pass

            # Lock + START
            self._inflight[inflight_key] = {"text": last_user_message or "", "since": datetime.now(timezone.utc)}
            await connection_manager.send_personal_message(
                {"type": "ws:chat_stream_start", "payload": {"agent_id": agent_id, "id": temp_message_id}}, session_id
            )

            # Court-circuit "mot-code"
            if self.memory.is_mot_code_query(last_user_message):
                uid = self.memory.try_get_user_id(session_id)
                mot = self.memory.fetch_mot_code_for_agent(agent_id, uid)
                try:
                    stm_here = self.memory.try_get_session_summary(session_id)
                    await connection_manager.send_personal_message(
                        {"type": "ws:memory_banner", "payload": {
                            "agent_id": agent_id, "has_stm": bool(stm_here),
                            "ltm_items": 0, "injected_into_prompt": False
                        }}, session_id
                    )
                except Exception:
                    pass
                if mot:
                    final_agent_message = AgentMessage(
                        id=temp_message_id, session_id=session_id, role=Role.ASSISTANT,
                        agent=agent_id, message=mot, timestamp=datetime.now(timezone.utc).isoformat(), cost_info={}
                    )
                    await self.session_manager.add_message_to_session(session_id, final_agent_message)
                    payload = final_agent_message.model_dump(mode="json")
                    if "message" in payload: payload["content"] = payload.pop("message")
                    if self.enable_analysis:
                        try:
                            await connection_manager.send_personal_message(
                                {"type": "ws:analysis_status",
                                 "payload": {"status": "started", "agent_id": agent_id, "session_id": session_id}},
                                session_id
                            )
                            asyncio.create_task(
                                run_analysis_and_notify(self.session_manager, connection_manager,
                                                        session_id, agent_id, self.enable_analysis)
                            )
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

            # Mémoire (STM/LTM) — bannière + injection
            stm = self.memory.try_get_session_summary(session_id)
            ltm_block = (await self.memory.build_memory_context(session_id, last_user_message, top_k=5)
                         if last_user_message else "")
            if use_rag:
                memory_context = self.memory.merge_blocks([("Résumé de session", stm)]) if stm else ""
                ltm_count_for_banner = self.memory.count_bullets(ltm_block)
            else:
                memory_context = self.memory.merge_blocks([("Résumé de session", stm), ("Faits & souvenirs", ltm_block)])
                ltm_count_for_banner = self.memory.count_bullets(ltm_block)
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

            # RAG (documents + mémoire locale)
            rag_context = ""
            if use_rag and last_user_message:
                try:
                    await connection_manager.send_personal_message(
                        {"type": "ws:rag_status", "payload": {"status": "searching", "agent_id": agent_id}}, session_id
                    )
                except Exception:
                    pass
                document_collection = self.vector_service.get_or_create_collection(config.DOCUMENT_COLLECTION_NAME)
                doc_hits = self.vector_service.query(collection=document_collection, query_text=last_user_message)
                doc_block = "\n\n".join([f"- {h['text']}" for h in doc_hits]) if doc_hits else ""
                mem_block = await self.memory.build_memory_context(session_id, last_user_message)
                rag_context = self.memory.merge_blocks([("Mémoire (concepts clés)", mem_block),
                                                        ("Documents pertinents", doc_block)])
                try:
                    await connection_manager.send_personal_message(
                        {"type": "ws:rag_status", "payload": {"status": "found", "agent_id": agent_id}}, session_id
                    )
                except Exception:
                    pass

            # Debug (avant normalisation)
            raw_concat = "\n".join([(m.get("content") or m.get("message", "")) for m in history])
            raw_tokens = self.memory.extract_sensitive_tokens(raw_concat)
            if self.send_debug_ctx:
                try:
                    await connection_manager.send_personal_message(
                        {"type": "ws:debug_context",
                         "payload": {"phase": "before_normalize", "agent_id": agent_id, "use_rag": use_rag,
                                     "history_total": len(history), "rag_context_chars": len(rag_context),
                                     "off_policy": self.off_history_policy,
                                     "sensitive_tokens_in_history": list(set(raw_tokens))}},
                        session_id
                    )
                except Exception:
                    pass

            # Config agent + normalisation provider-spécifique
            provider, model, system_prompt = self._get_agent_config(agent_id)
            model_used = model
            normalized_history = self.memory.normalize_history_for_llm(
                provider, history, rag_context=rag_context, use_rag=use_rag, agent_id=agent_id
            )

            # Debug (après normalisation)
            if provider == "google":
                norm_concat = "\n".join(["".join(p.get("parts", [])) for p in normalized_history])
            else:
                norm_concat = "\n".join([p.get("content", "") for p in normalized_history])
            norm_tokens = self.memory.extract_sensitive_tokens(norm_concat)
            if self.send_debug_ctx:
                try:
                    await connection_manager.send_personal_message(
                        {"type": "ws:debug_context",
                         "payload": {"phase": "after_normalize", "agent_id": agent_id, "use_rag": use_rag,
                                     "history_filtered": len(normalized_history),
                                     "rag_context_chars": len(rag_context),
                                     "off_policy": self.off_history_policy,
                                     "sensitive_tokens_in_prompt": list(set(norm_tokens))}},
                        session_id
                    )
                except Exception:
                    pass

            # Stream principal
            response_generator = self.streamer.get_llm_response_stream(
                provider, model, system_prompt, normalized_history, cost_info_container
            )
            async for chunk in response_generator:
                if chunk:
                    full_response_text += chunk
                    await connection_manager.send_personal_message(
                        {"type": "ws:chat_stream_chunk",
                         "payload": {"agent_id": agent_id, "id": temp_message_id, "chunk": chunk}},
                        session_id
                    )

            # ✅ Fallback (rate_limit/provider_error) — **re-normalisation cross-provider**
            try:
                if not full_response_text and cost_info_container.get("__error__") in ("rate_limit", "provider_error"):
                    # 1) Anthropic d'abord pour Neo (style + coûts)
                    try:
                        await connection_manager.send_personal_message(
                            {"type": "ws:debug_context",
                             "payload": {"phase": "model_fallback", "from": model_used, "to": "claude-3-haiku-20240307"}},
                            session_id
                        )
                    except Exception:
                        pass

                    # 🔁 Re-normalise l’historique POUR le provider de fallback
                    hist_for_anthropic = self.memory.normalize_history_for_llm(
                        "anthropic", history, rag_context=rag_context, use_rag=use_rag, agent_id=agent_id
                    )
                    fb_cost_1: Dict[str, Any] = {}
                    alt_stream = self.streamer.get_llm_response_stream(
                        "anthropic", "claude-3-haiku-20240307", system_prompt, hist_for_anthropic, fb_cost_1
                    )
                    async for chunk in alt_stream:
                        if chunk:
                            full_response_text += chunk
                            await connection_manager.send_personal_message(
                                {"type": "ws:chat_stream_chunk",
                                 "payload": {"agent_id": agent_id, "id": temp_message_id, "chunk": chunk}},
                                session_id
                            )

                    # 2) Si encore vide → second fallback OpenAI (modèle sûr)
                    if not full_response_text:
                        hist_for_openai = self.memory.normalize_history_for_llm(
                            "openai", history, rag_context=rag_context, use_rag=use_rag, agent_id=agent_id
                        )
                        fb_cost_2: Dict[str, Any] = {}
                        alt2_stream = self.streamer.get_llm_response_stream(
                            "openai", "gpt-4o-mini", system_prompt, hist_for_openai, fb_cost_2
                        )
                        async for chunk in alt2_stream:
                            if chunk:
                                full_response_text += chunk
                                await connection_manager.send_personal_message(
                                    {"type": "ws:chat_stream_chunk",
                                     "payload": {"agent_id": agent_id, "id": temp_message_id, "chunk": chunk}},
                                    session_id
                                )

                    # Merge coûts fallback
                    try:
                        for k, v in {**locals().get("fb_cost_1", {}), **locals().get("fb_cost_2", {})}.items():
                            if isinstance(v, (int, float)) and isinstance(cost_info_container.get(k), (int, float)):
                                cost_info_container[k] += v
                            else:
                                cost_info_container[k] = v
                    except Exception:
                        pass

                    # Si toujours vide → notifie rate-limit
                    if not full_response_text:
                        try:
                            await connection_manager.send_personal_message(
                                {"type": "ws:error", "payload": {"message": "rate_limited", "agent_id": agent_id}},
                                session_id
                            )
                        except Exception:
                            pass
                        return
            except Exception:
                pass

            # Persist + coût + fin + analyse
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

            if self.enable_analysis:
                try:
                    await connection_manager.send_personal_message(
                        {"type": "ws:analysis_status",
                         "payload": {"status": "started", "agent_id": agent_id, "session_id": session_id}},
                        session_id
                    )
                    asyncio.create_task(
                        run_analysis_and_notify(self.session_manager, connection_manager,
                                                session_id, agent_id, self.enable_analysis)
                    )
                except Exception:
                    pass
            else:
                try:
                    await connection_manager.send_personal_message(
                        {"type": "ws:analysis_status",
                         "payload": {"status": "skipped", "reason": "disabled", "agent_id": agent_id}},
                        session_id
                    )
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
                    session_id
                )
            except Exception as send_error:
                logger.error(f"Impossible d'envoyer l'erreur au client (session {session_id}): {send_error}", exc_info=True)
        finally:
            try:
                info = self._inflight.get(inflight_key)
                if info and info.get("text", "") == (last_user_message or ""):
                    self._inflight.pop(inflight_key, None)
            except Exception:
                pass

    # ---------- Réponse JSON structurée ----------
    async def get_structured_llm_response(
        self, agent_id: str, prompt: str, json_schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        provider, model, system_prompt = self._get_agent_config(agent_id)

        async def _anthropic_call() -> Dict[str, Any]:
            resp = await self.anthropic_client.messages.create(
                model=model, max_tokens=1500, temperature=0,
                system=system_prompt + "\n\nRéponds strictement en JSON valide.",
                messages=[{"role": "user", "content": prompt}],
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

        async def _openai_call() -> Dict[str, Any]:
            resp = await self.openai_client.chat.completions.create(
                model=model, temperature=0, response_format={"type": "json_object"},
                messages=[{"role": "system", "content": system_prompt},
                          {"role": "user", "content": prompt}],
            )
            content = (resp.choices[0].message.content or "").strip()
            return json.loads(content) if content else {}

        async def _openai_call_forced() -> Dict[str, Any]:
            resp = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini", temperature=0, response_format={"type": "json_object"},
                messages=[{"role": "system", "content": system_prompt},
                          {"role": "user", "content": prompt}],
            )
            content = (resp.choices[0].message.content or "").strip()
            return json.loads(content) if content else {}

        async def _google_call() -> Dict[str, Any]:
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

        try:
            if provider == "anthropic":
                try:
                    return await self.streamer.with_rate_limit_retries("anthropic", _anthropic_call)
                except Exception as e:
                    if isinstance(e, _AnthropicRateLimit) or "429" in str(e):
                        logger.warning("[structured] Anthropic 429 — fallback OpenAI.")
                        return await self.streamer.with_rate_limit_retries("openai", _openai_call)
                    logger.error(f"[structured] Anthropic error, fallback Google: {e}")
                    return await self.streamer.with_rate_limit_retries("google", _google_call)
            elif provider == "openai":
                try:
                    return await self.streamer.with_rate_limit_retries("openai", _openai_call)
                except Exception as e:
                    logger.error(f"[structured] OpenAI error, fallback Google: {e}")
                    return await self.streamer.with_rate_limit_retries("google", _google_call)
            elif provider == "google":
                try:
                    return await self.streamer.with_rate_limit_retries("google", _google_call)
                except Exception as e:
                    logger.error(f"[structured] Google error, fallback OpenAI: {e}")
                    return await self.streamer.with_rate_limit_retries("openai", _openai_call_forced)
            else:
                raise ValueError(f"Fournisseur LLM non supporté: {provider}")
        except Exception as e:
            logger.error(f"[structured] All providers failed: {e}", exc_info=True)
            return {}

    # ---------- Débat / synthèse ----------
    async def get_llm_response_for_debate(
        self, agent_id: str, prompt: Optional[str] = None, *,
        rag_context: str = "", use_rag: bool = False,
        temperature: float = 0.3, max_tokens: int = 1500, **kwargs,
    ) -> Tuple[str, Dict[str, Any]]:
        if prompt is None or (isinstance(prompt, str) and not prompt.strip()):
            for key in ("text","content","message","prompt_text","input","summary","synthesis","instruction","instructions"):
                val = kwargs.get(key)
                if isinstance(val, str) and val.strip():
                    prompt = val; break
        if prompt is None or not str(prompt).strip():
            transcript = kwargs.get("transcript") or kwargs.get("context") or ""
            topic = kwargs.get("topic") or ""
            lines = [
                "Tu es 'Nexus', chargé de CONCLURE un débat.",
                f"Synthétise en 5 points clairs (faits, convergences, désaccords, angles aveugles, pistes) le débat sur : {topic or '—'}.",
            ]
            if isinstance(transcript, str) and transcript.strip():
                lines.append("Transcript ci-dessous:"); lines.append(transcript)
            prompt = "\n".join(lines)

        prompt = str(prompt or "").strip()
        provider, model, system_prompt = self._get_agent_config(agent_id)
        base_cost: Dict[str, Any] = {"input_tokens": 0, "output_tokens": 0, "total_cost": 0.0}

        async def _openai_call(p: str, forced_model: Optional[str] = None) -> Tuple[str, Dict[str, Any]]:
            mdl = forced_model or model
            resp = await self.openai_client.chat.completions.create(
                model=mdl, temperature=temperature,
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": p}],
            )
            content = (resp.choices[0].message.content or "").strip()
            usage = getattr(resp, "usage", None)
            if usage:
                pricing = MODEL_PRICING.get(mdl, {"input": 0, "output": 0})
                in_tok = getattr(usage, "prompt_tokens", 0)
                out_tok = getattr(usage, "completion_tokens", 0)
                cost = (in_tok * pricing["input"]) + (out_tok * pricing["output"])
                return content, {"input_tokens": in_tok, "output_tokens": out_tok, "total_cost": cost}
            return content, dict(base_cost)

        if provider == "openai":
            return await _openai_call(prompt)

        elif provider == "google":
            try:
                model_instance = genai.GenerativeModel(model_name=model, system_instruction=system_prompt)
                parts = []
                if use_rag and rag_context:
                    parts.append({"role": "user", "parts": [f"[RAG_CONTEXT]\n{rag_context}"]})
                parts.append({"role": "user", "parts": [prompt]})
                resp = await self.streamer.with_rate_limit_retries(
                    "google",
                    lambda: model_instance.generate_content_async(parts, generation_config={"temperature": temperature}),
                )
                text = getattr(resp, "text", "") or ""
                usage = getattr(resp, "usage_metadata", None)
                if usage:
                    pricing = MODEL_PRICING.get(model, {"input": 0, "output": 0})
                    cost = (getattr(usage, "prompt_token_count", 0) * pricing["input"]) + (
                        getattr(usage, "candidates_token_count", 0) * pricing["output"]
                    )
                    return text, {
                        "input_tokens": getattr(usage, "prompt_token_count", 0),
                        "output_tokens": getattr(usage, "candidates_token_count", 0),
                        "total_cost": cost,
                    }
                return text, dict(base_cost)
            except Exception as e:
                logger.error(f"[DEBATE] Google erreur/quota, fallback OpenAI (agent={agent_id}): {e}")
                return await _openai_call(prompt, forced_model="gpt-4o-mini")

        elif provider == "anthropic":
            content_text = f"[RAG_CONTEXT]\n{rag_context}\n\n{prompt}" if use_rag and rag_context else prompt
            try:
                resp = await self.anthropic_client.messages.create(
                    model=model, max_tokens=max_tokens, temperature=temperature,
                    system=system_prompt, messages=[{"role": "user", "content": content_text}],
                )
                text = ""
                for block in getattr(resp, "content", []) or []:
                    t = getattr(block, "text", "") or ""
                    if t: text += t
                usage = getattr(resp, "usage", None)
                if usage:
                    pricing = MODEL_PRICING.get(model, {"input": 0, "output": 0})
                    in_tok = getattr(usage, "input_tokens", 0)
                    out_tok = getattr(usage, "output_tokens", 0)
                    cost = (in_tok * pricing["input"]) + (out_tok * pricing["output"])
                    cost_info = {"input_tokens": in_tok, "output_tokens": out_tok, "total_cost": cost}
                else:
                    cost_info = dict(base_cost)
                if not text.strip():
                    logger.warning("[DEBATE] Anthropic a renvoyé un texte vide — fallback OpenAI.")
                    return await _openai_call(prompt, forced_model="gpt-4o-mini")
                return text.strip(), cost_info
            except Exception as e:
                logger.error(f"[DEBATE] Anthropic erreur, fallback OpenAI (agent={agent_id}): {e}")
                return await _openai_call(prompt, forced_model="gpt-4o-mini")

        else:
            raise ValueError(f"Fournisseur non supporté: {provider}")
