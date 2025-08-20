# src/backend/features/chat/service.py
# V31.0 – P1.5-b: Persistance auto (Threads) des messages user + réponses agents
# UTF-8 (CRLF conseillé sous Windows).

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

# 🔗 Threads (nouveau)
from backend.features.threads.service import ThreadsService
from backend.features.threads.schemas import MessageCreate

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

# Collection mémoire (fallback si non défini en config)
KNOWLEDGE_COLLECTION_NAME: str = getattr(config, "KNOWLEDGE_COLLECTION_NAME", "emergence_knowledge")


class ChatService:
    """
    ChatService V31.0
    - Initialisation clients OpenAI / Anthropic / Google
    - Fallback dynamique
    - RAG inchangé (sources WS)
    - Mémoire P2 (bandeau & injection dans le chat)
    - API non-stream pour Débat: get_llm_response_for_debate(...)
    - ✅ P1.5-b: Persistance auto (Threads) des messages user + réponses agents
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

        # Politique OFF quand RAG désactivé (inchangé)
        self.off_history_policy = os.getenv("EMERGENCE_RAG_OFF_POLICY", "stateless").strip().lower()
        if self.off_history_policy not in ("stateless", "agent_local"):
            self.off_history_policy = "stateless"
        logger.info("ChatService OFF policy: %s", self.off_history_policy)

        # Clients LLM (inchangé)
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

        # Prompts
        self.prompts: Dict[str, str] = self._load_prompts(self.settings.paths.prompts)
        logger.info("ChatService initialisé. Prompts chargés: %d", len(self.prompts))

        # Threads service (persistance P1.5-b)
        self._threads = ThreadsService()

    # ──────────────────────────────────────────────────────────────────────
    # Chargement des prompts (inchangé)
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

        # 'anima' forcé OpenAI/gpt-4o-mini
        if clean_agent_id == "anima":
            provider, model = "openai", "gpt-4o-mini"
            logger.info("Remplacement modèle pour 'anima' -> openai/gpt-4o-mini.")

        provider, model = self._ensure_supported(provider, model)

        # Anthropic sans clé -> fallback OpenAI
        if provider == "anthropic" and self.anthropic_client is None:
            logger.warning("Agent '%s' configuré Anthropic sans clé – fallback -> openai/%s.", agent_id, SAFE_DEFAULTS["openai"])
            provider, model = "openai", SAFE_DEFAULTS["openai"]

        system_prompt = self.prompts.get(agent_id, self.prompts.get(clean_agent_id, ""))
        if not system_prompt:
            logger.warning("Prompt système non trouvé pour '%s' – utilisation d'un prompt vide.", agent_id)
        return provider, model, system_prompt

    # ──────────────────────────────────────────────────────────────────────
    # Helpers persistance Threads (P1.5-b)
    # ──────────────────────────────────────────────────────────────────────
    def _safe_get_user_text(self, message: ChatMessage) -> str:
        for k in ("content", "message", "text"):
            v = getattr(message, k, None)
            if v:
                return str(v)
        try:
            return str(message)
        except Exception:
            return ""

    def _resolve_user_id_from_session(self, session_id: str) -> Optional[str]:
        """
        Essaie plusieurs patterns de SessionManager pour obtenir user_id.
        Tolérant aux différences de versions.
        """
        try:
            # pattern get_session() -> dict/obj
            if hasattr(self.session_manager, "get_session"):
                s = self.session_manager.get_session(session_id)  # type: ignore[attr-defined]
            elif hasattr(self.session_manager, "get"):
                s = self.session_manager.get(session_id)  # type: ignore[attr-defined]
            else:
                s = None
            if s:
                if isinstance(s, dict):
                    return s.get("user_id") or (s.get("user") or {}).get("id")
                # obj
                return getattr(s, "user_id", None) or getattr(getattr(s, "user", None), "id", None)
        except Exception:
            pass
        # autres helpers potentiels
        for fn in ("get_user_id", "get_session_user_id"):
            try:
                if hasattr(self.session_manager, fn):
                    return getattr(self.session_manager, fn)(session_id)  # type: ignore[misc]
            except Exception:
                continue
        return None

    async def _persist_to_threads(
        self,
        *,
        session_id: str,
        role: str,
        content: str,
        agent: Optional[str] = None,
        model: Optional[str] = None,
        rag_sources: Optional[List[Dict[str, Any]]] = None,
        thread_title_if_new: Optional[str] = None,
    ) -> None:
        if not (content or "").strip():
            return
        try:
            user_id = self._resolve_user_id_from_session(session_id)
            if not user_id:
                logger.warning("[Threads] user_id introuvable pour session %s — persistance sautée.", session_id)
                return
            tid = await self._threads.ensure_session_thread(user_id=user_id, session_id=session_id, title=thread_title_if_new)
            msg = MessageCreate(role=role, content=content, agent=agent, model=model, rag_sources=rag_sources)
            await self._threads.add_message(user_id=user_id, thread_id=tid, msg=msg)
        except Exception as e:
            logger.warning("[Threads] Persistance sautée (session=%s, role=%s): %s", session_id, role, e)

    # ──────────────────────────────────────────────────────────────────────
    # API publique – traitement d'un message user pour N agents (chat streaming)
    # ──────────────────────────────────────────────────────────────────────
    async def process_user_message_for_agents(
        self, session_id: str, message: ChatMessage, connection_manager: ConnectionManager
    ) -> None:
        # Persiste le message utilisateur (session)
        await self.session_manager.add_message_to_session(session_id, message)

        # ✅ Nouveau — persistance Threads du message user
        try:
            user_text = self._safe_get_user_text(message)
            await self._persist_to_threads(
                session_id=session_id,
                role="user",
                content=user_text,
                thread_title_if_new="Chat"
            )
        except Exception as e:
            logger.warning("[Threads] Persistance message user échouée: %s", e)

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
    # Mémoire — build context snippets + payload WS
    # ──────────────────────────────────────────────────────────────────────
    def _dedup_preserve(self, items: List[str]) -> List[str]:
        seen = set()
        out = []
        for s in items:
            if s and s not in seen:
                out.append(s); seen.add(s)
        return out

    def _safe_preview(self, s: str, max_len: int = 140) -> str:
        s = (s or "").strip()
        return s if len(s) <= max_len else (s[:max_len - 1] + "…")

    def _build_memory_context(self, query_text: str, max_items: int = 5) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Retourne (context_en_bullets, sources_payload) depuis la collection mémoire.
        """
        if not (query_text or "").strip():
            return "", []

        try:
            knowledge_collection = self.vector_service.get_or_create_collection(KNOWLEDGE_COLLECTION_NAME)
        except Exception as e:
            logger.error("Impossible d'ouvrir la collection mémoire '%s': %s", KNOWLEDGE_COLLECTION_NAME, e, exc_info=True)
            return "", []

        try:
            results = self.vector_service.query(collection=knowledge_collection, query_text=query_text) or []
        except Exception as e:
            logger.error("Erreur requête mémoire: %s", e, exc_info=True)
            return "", []

        snippets: List[str] = []
        payload: List[Dict[str, Any]] = []
        for r in results:
            meta = (r.get("metadata") or {}) if isinstance(r, dict) else {}
            text = meta.get("text") or meta.get("chunk") or ""
            if not text:
                continue
            snippets.append(text)
            payload.append({
                "source_session_id": meta.get("source_session_id"),
                "role": meta.get("role"),
                "score": r.get("score") if isinstance(r, dict) else None,
                "preview": self._safe_preview(text),
            })
            if len(snippets) >= max_items:
                break

        snippets = self._dedup_preserve(snippets)[:max_items]
        if not snippets:
            return "", []

        bullets = "\n".join([f"• {s}" for s in snippets])
        return bullets, payload

    # ──────────────────────────────────────────────────────────────────────
    # Orchestration d'un agent (streaming + RAG + Mémoire + coûts)
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

        # Construit historique + récupère dernier message user
        history = self.session_manager.get_full_history(session_id)
        last_user_message_obj = next((m for m in reversed(history) if m.get("role") in (Role.USER, "user")), None)
        last_user_message = (last_user_message_obj or {}).get("content", "")

        # RAG : inchangé (documents)
        rag_context = ""
        sources_payload: List[Dict[str, Any]] = []

        if use_rag:
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

        # NOUVEAU — Mémoire : build + WS status
        memory_context = ""
        memory_sources: List[Dict[str, Any]] = []
        try:
            await connection_manager.send_personal_message(
                {"type": "ws:memory_status", "payload": {"status": "searching", "agent_id": agent_id}}, session_id
            )
            memory_context, memory_sources = self._build_memory_context(last_user_message, max_items=5)
            await connection_manager.send_personal_message(
                {"type": "ws:memory_sources", "payload": {"agent_id": agent_id, "sources": memory_sources}}, session_id
            )
            await connection_manager.send_personal_message(
                {"type": "ws:memory_status", "payload": {"status": ("found" if memory_context else "empty"), "agent_id": agent_id}},
                session_id,
            )
        except Exception as e:
            logger.error("Erreur Mémoire: %s", e, exc_info=True)
            await connection_manager.send_personal_message(
                {"type": "ws:memory_status", "payload": {"status": "error", "agent_id": agent_id}}, session_id
            )

        # Normalisation provider + injection RAG/MEMORY
        normalized_history = self._normalize_history_for_llm(
            provider=provider,
            history=history,
            rag_context=rag_context,
            memory_context=memory_context,
            use_rag=use_rag,
            agent_id=agent_id,
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
                    "memory_context_chars": len(memory_context),
                    "memory_snippets": len(memory_sources),
                    "off_policy": self.off_history_policy,
                    "sensitive_tokens_in_prompt": norm_tokens,
                },
            },
            session_id,
        )

        # Stream + fallback (inchangé)
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

            # Fallback chain
            fallback_candidates: List[str] = []
            if provider != "openai" and self.openai_client is not None:
                fallback_candidates.append("openai")
            if provider != "google" and os.getenv("GOOGLE_API_KEY"):
                fallback_candidates.append("google")
            if provider != "anthropic" and self.anthropic_client is not None:
                fallback_candidates.append("anthropic")

        # Single-shot si nécessaire (inchangé)
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

        # Persistance session + coûts (inchangé)
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

        # ✅ Nouveau — persistance Threads de la réponse agent
        try:
            await self._persist_to_threads(
                session_id=session_id,
                role="assistant",
                content=full_text,
                agent=agent_id,
                model=model,
                rag_sources=sources_payload,
            )
        except Exception as e:
            logger.warning("[Threads] Persistance message agent échouée: %s", e)

        await connection_manager.send_personal_message(
            {
                "type": "ws:chat_stream_end",
                "payload": {"agent_id": agent_id, "id": temp_message_id, "model": model, "provider": provider, "cost": cost_info},
            },
            session_id,
        )

    # ──────────────────────────────────────────────────────────────────────
    # Normalisation des historiques + injection RAG/MEMORY (inchangé)
    # ──────────────────────────────────────────────────────────────────────
    def _normalize_history_for_llm(
        self,
        *,
        provider: str,
        history: List[Dict[str, Any]],
        rag_context: str,
        memory_context: str,
        use_rag: bool,
        agent_id: str,
    ) -> List[Dict[str, Any]]:

        pairs: List[Tuple[Any, str]] = []
        for m in history:
            role = m.get("role")
            content = m.get("content") or m.get("message") or ""
            if role in (Role.USER, "user", Role.ASSISTANT, "assistant"):
                pairs.append((role, str(content)))

        if pairs:
            for i in range(len(pairs) - 1, -1, -1):
                r = pairs[i][0]
                if r == Role.USER or r == "user":
                    original = pairs[i][1]
                    enriched = original
                    ctx = (rag_context or "").strip()
                    mem = (memory_context or "").strip()
                    if use_rag and ctx:
                        enriched = f"{enriched}\n\n[CONTEXT]\n{ctx}\n[/CONTEXT]"
                    if mem:
                        enriched = f"{enriched}\n\n[MEMORY]\n{mem}\n[/MEMORY]"
                    pairs[i] = (r, enriched)
                    break

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

        for role, content in pairs:
            normalized.append({"role": "user" if (role == Role.USER or role == "user") else "assistant", "content": content})
        return normalized

    # ──────────────────────────────────────────────────────────────────────
    # Streaming, Single-shot, API débat (inchangé sauf version header)
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
        response_format = {"type": "json_object"} if json_mode else {"type": "text"}
        messages = [{"role": "system", "content": system_prompt}] + history
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

    # ──────────────────────────────────────────────────────────────────────
    # ✅ API non-stream pour le module Débat (inchangé)
    # ──────────────────────────────────────────────────────────────────────
    async def get_llm_response_for_debate(
        self,
        *,
        agent_id: str,
        history: List[Dict[str, Any]],
        session_id: str
    ) -> Tuple[str, Dict[str, Any]]:
        provider, model, system_prompt = self._get_agent_config(agent_id)

        def _ensure_openai_style(msgs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            out: List[Dict[str, Any]] = []
            for m in msgs or []:
                role = m.get("role", "user")
                if "content" in m and isinstance(m["content"], str):
                    out.append({"role": role, "content": m["content"]})
                elif "parts" in m:
                    parts = m.get("parts") or []
                    text = "".join(parts) if isinstance(parts, list) else str(parts or "")
                    out.append({"role": role if role in ("user","assistant") else ("assistant" if role=="model" else "user"), "content": text})
                else:
                    out.append({"role": role, "content": str(m.get("content") or "")})
            return out or [{"role": "user", "content": ""}]

        async def _single(provider_name: str, model_name: str) -> Tuple[str, Dict[str, Any]]:
            if provider_name == "openai":
                norm = _ensure_openai_style(history)
                return await self._get_openai_response_single(model_name, system_prompt, norm, False)
            if provider_name == "google":
                base = _ensure_openai_style(history)
                gem = [{"role": ("user" if m["role"] == "user" else "model"), "parts": [m["content"]]} for m in base]
                return await self._get_gemini_response_single(model_name, system_prompt, gem, False)
            if provider_name == "anthropic":
                base = _ensure_openai_style(history)
                ant = self._to_anthropic_messages(base)
                return await self._get_anthropic_response_single(model_name, system_prompt, ant, False)
            raise ValueError(f"Provider non supporté: {provider_name}")

        try:
            text, cost = await _single(provider, model)
            await self.cost_tracker.record_cost(
                agent=agent_id,
                model=model,
                input_tokens=cost.get("input_tokens", 0),
                output_tokens=cost.get("output_tokens", 0),
                total_cost=cost.get("total_cost", 0.0),
                feature="debate",
            )
            return text, cost
        except Exception as e:
            logger.error("[DEBATE SINGLE FAIL] %s/%s: %s", provider, model, e, exc_info=True)

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
                text, cost = await _single(fb, fb_model)
                await self.cost_tracker.record_cost(
                    agent=agent_id,
                    model=fb_model,
                    input_tokens=cost.get("input_tokens", 0),
                    output_tokens=cost.get("output_tokens", 0),
                    total_cost=cost.get("total_cost", 0.0),
                    feature="debate",
                )
                return text, cost
            except Exception as fb_err:
                logger.error("[DEBATE FALLBACK FAIL] %s: %s", fb, fb_err, exc_info=True)

        return "", {}
