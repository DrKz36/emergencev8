# V1.0 — Outils mémoire/RAG (STM/LTM), externalisés
from __future__ import annotations
import os, re, logging
from typing import Any, Dict, List, Optional, Tuple
from backend.shared.models import Role
logger = logging.getLogger(__name__)

class MemoryContextBuilder:
    def __init__(self, session_manager, vector_service):
        self.session_manager = session_manager
        self.vector_service = vector_service

    def try_get_session_summary(self, session_id: str) -> str:
        try:
            sess = self.session_manager.get_session(session_id)
            meta = getattr(sess, "metadata", None)
            if isinstance(meta, dict):
                s = meta.get("summary")
                if isinstance(s, str) and s.strip(): return s.strip()
        except Exception: pass
        return ""

    def try_get_user_id(self, session_id: str) -> Optional[str]:
        for attr in ("get_user_id_for_session", "get_user", "get_owner", "get_session_owner"):
            try:
                fn = getattr(self.session_manager, attr, None)
                if callable(fn):
                    uid = fn(session_id)
                    if uid: return str(uid)
            except Exception: pass
        for attr in ("current_user_id", "user_id"):
            try:
                uid = getattr(self.session_manager, attr, None)
                if uid: return str(uid)
            except Exception: pass
        return None

    async def build_memory_context(self, session_id: str, last_user_message: str, top_k: int = 5) -> str:
        try:
            if not last_user_message: return ""
            knowledge_name = os.getenv("EMERGENCE_KNOWLEDGE_COLLECTION", "emergence_knowledge")
            knowledge_col = self.vector_service.get_or_create_collection(knowledge_name)
            where_filter = None
            uid = self.try_get_user_id(session_id)
            if uid: where_filter = {"user_id": uid}
            results = self.vector_service.query(collection=knowledge_col, query_text=last_user_message,
                                                n_results=top_k, where_filter=where_filter)
            if not results: return ""
            lines = []
            for r in results:
                t = (r.get("text") or "").strip()
                if t: lines.append(f"- {t}")
            return "\n".join(lines[:top_k])
        except Exception as e:
            logger.warning(f"build_memory_context: {e}")
            return ""

    def normalize_history_for_llm(self, provider: str, history: List[Dict[str, Any]],
                                  *, rag_context: str = "", use_rag: bool = False,
                                  agent_id: Optional[str] = None) -> List[Dict[str, Any]]:
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

    def merge_blocks(self, blocks: List[Tuple[str, str]]) -> str:
        parts = []
        for title, body in blocks:
            if body and str(body).strip():
                parts.append(f"### {title}\n{str(body).strip()}")
        return "\n\n".join(parts)

    _MOT_CODE_RE = re.compile(r"\b(mot-?code|code)\b", re.IGNORECASE)
    def is_mot_code_query(self, text: str) -> bool:
        return bool(self._MOT_CODE_RE.search(text or ""))

    def fetch_mot_code_for_agent(self, agent_id: str, user_id: Optional[str]) -> Optional[str]:
        knowledge_name = os.getenv("EMERGENCE_KNOWLEDGE_COLLECTION", "emergence_knowledge")
        col = self.vector_service.get_or_create_collection(knowledge_name)
        clauses = [{"type": "fact"}, {"key": "mot-code"}, {"agent": (agent_id or "").lower()}]
        if user_id: clauses.append({"user_id": user_id})
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

    def count_bullets(self, text: str) -> int:
        return sum(1 for line in (text or "").splitlines() if line.strip().startswith("- "))

    def extract_sensitive_tokens(self, text: str) -> List[str]:
        return re.findall(r"\b[A-Z]{3,}-\d{3,}\b", text or "")
