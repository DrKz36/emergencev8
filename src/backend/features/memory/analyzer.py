# src/backend/features/memory/analyzer.py
# V2.1 — MemoryAnalyzer (corrigé, sans imports circulaires)
# - DI:    MemoryAnalyzer(db_manager)  [containers.py]
# - Hook:  set_chat_service(chat_service)            [main.py]
# - API:   analyze_session_for_concepts(session_id, history)  -> écrit summary/concepts/entities en BDD
#          analyze_history(session_id|None, history)           -> renvoie un dict (read-only)
# - AUCUN import vers gardener/containers/chat.service au runtime (prévention cycles).
# - Typages 'forward' via TYPE_CHECKING pour ChatService.

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from backend.core.database.manager import DatabaseManager
from backend.core.database import queries  # doit fournir update_session_analysis_data(...)

if TYPE_CHECKING:
    # Import paresseux uniquement pour le typing (évite les cycles).
    from backend.features.chat.service import ChatService  # pragma: no cover

logger = logging.getLogger(__name__)

# ------------------------ utilitaires internes (légers) ------------------------

_VALUE_TRAIL_RE = re.compile(r"[\s\.\,\;\:\!\?]+$")
def _clean_value(v: str) -> str:
    v = (v or "").strip()
    v = _VALUE_TRAIL_RE.sub("", v)
    v = re.sub(r"\s{2,}", " ", v)
    return v

def _unique(seq: List[str]) -> List[str]:
    seen, out = set(), []
    for s in seq or []:
        k = (s or "").strip().lower()
        if k and k not in seen:
            out.append((s or "").strip())
            seen.add(k)
    return out

def _history_to_text(history: List[Dict[str, Any]], limit_chars: int = 2400) -> str:
    """Aplatis l'historique en texte simple (robuste aux contenus JSON)."""
    blocks: List[str] = []
    total = 0
    for m in history or []:
        role = (m.get("role") or "").strip().lower()
        raw = m.get("content")
        txt = raw if isinstance(raw, str) else json.dumps(raw or "", ensure_ascii=False)
        if not txt:
            continue
        prefix = "U:" if role in ("user", "system") else "A:"
        line = f"{prefix} {txt.strip()}"
        total += len(line)
        if total > limit_chars:
            # on termine proprement
            blocks.append(line[: max(0, limit_chars - (total - len(line)))])
            break
        blocks.append(line)
    return "\n".join(blocks)

def _summarize(history: List[Dict[str, Any]], max_len: int = 480) -> str:
    """Résumé heuristique bref (sans LLM) — robuste, déterministe, économique."""
    text = _history_to_text(history, limit_chars=2400)
    text = re.sub(r"\s+", " ", text).strip()
    return (text[:max_len] + "…") if len(text) > max_len else text

# Détection “mot-code” (expressions usuelles + variantes) — proche du Gardener pour cohérence.
_CODE_PATTERNS = [
    r"(?:pour\s+(?P<agent>anima|neo|nexus)\s*,?\s*)?(?:mon|ton|ce|le)\s*mot[-\s]?code\s*(?:est|:|=)\s*[«\"'’]?\s*(?P<value>[A-Za-zÀ-ÖØ-öø-ÿ0-9_\- ]+?)\s*[»\"'’]?(?:[.!?,;:\)]|$)",
    r"(?:mon|ton|ce|le)\s*mot[-\s]?code\s*pour\s+(?P<agent>anima|neo|nexus)\s*(?:est|:|=)\s*[«\"'’]?\s*(?P<value>[A-Za-zÀ-ÖØ-öø-ÿ0-9_\- ]+?)\s*[»\"'’]?(?:[.!?,;:\)]|$)",
    r"(?:pour\s+(?P<agent>anima|neo|nexus)\s*,?\s*)?mon\s*mot[-\s]?code\s*(?:est|:|=)\s*[«\"'’]?\s*(?P<value>[A-Za-zÀ-ÖØ-öø-ÿ0-9_\-]+)\s*[»\"'’]?",
    r"mot[-\s]?code\s*(?:est|:|=)\s*[«\"'’]?\s*(?P<value>[A-Za-zÀ-ÖØ-öø-ÿ0-9_\- ]+?)\s*[»\"'’]?(?:[.!?,;:\)]|$)",
]

_CAP_ENTITY_RE = re.compile(r"\b([A-Z][a-zA-ZÀ-ÖØ-öø-ÿ]{2,})\b")

def _extract_basic_entities(text: str, limit: int = 8) -> List[str]:
    if not text:
        return []
    ents = _unique(_CAP_ENTITY_RE.findall(text))
    return ents[:limit]

def _extract_concepts_entities(summary: str, history: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    """Heuristiques légères : concepts (incl. mot-code) + entités capitalisées."""
    # 1) mot-code dans l'historique (prioritaire)
    found_codes: List[str] = []
    for m in history or []:
        raw = m.get("content")
        txt = raw if isinstance(raw, str) else json.dumps(raw or "", ensure_ascii=False)
        if not txt:
            continue
        for pat in _CODE_PATTERNS:
            for match in re.finditer(pat, txt, re.IGNORECASE):
                value = _clean_value((match.group("value") or ""))
                if value:
                    found_codes.append(value)

    # 2) concepts depuis le résumé (3–12 mots, 3–5 items)
    def _concepts_from_summary(summary_text: str, max_items: int = 5) -> List[str]:
        if not isinstance(summary_text, str) or not summary_text.strip():
            return []
        text2 = re.sub(r"\s+", " ", summary_text.strip())
        chunks = re.split(r"[.;:\n]+", text2)
        out: List[str] = []
        for c in chunks:
            w = c.strip()
            if not w:
                continue
            wc = len(w.split())
            if 3 <= wc <= 12:
                out.append(w)
            if len(out) >= max_items:
                break
        return _unique(out)

    concepts = _unique((found_codes or []) + _concepts_from_summary(summary))
    entities = _extract_basic_entities(summary)
    return {"concepts": concepts, "entities": entities}

# ------------------------------- implémentation -------------------------------

class MemoryAnalyzer:
    """
    Service d’analyse mémoire *stateless*.
    - Met à jour la table 'sessions' (summary/extracted_concepts/extracted_entities) via queries.update_session_analysis_data.
    - Fournit une variante read-only pour consommation par le Gardener ou la SessionManager.
    """
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self._chat_service: Optional["ChatService"] = None
        logger.info("MemoryAnalyzer initialisé.")

    # Hook optionnel (main.py)
    def set_chat_service(self, chat_service: "ChatService") -> None:
        self._chat_service = chat_service
        logger.info("MemoryAnalyzer: ChatService attaché.")

    async def analyze_session_for_concepts(self, session_id: str, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calcule un résumé court + concepts/entités et les persiste pour la session.
        Renvoie la structure calculée (utile au call-site).
        """
        try:
            summary = _summarize(history)
            extracted = _extract_concepts_entities(summary, history)
            await queries.update_session_analysis_data(
                self.db,
                session_id=session_id,
                summary=summary,
                concepts=extracted["concepts"],
                entities=extracted["entities"],
            )
            result = {"session_id": session_id, "summary": summary, **extracted}
            logger.debug(f"[Analyzer] session={session_id} concepts={len(extracted['concepts'])} entities={len(extracted['entities'])}")
            return result
        except Exception as e:
            logger.error(f"[Analyzer] analyze_session_for_concepts KO (session={session_id}): {e}", exc_info=True)
            return {"session_id": session_id, "summary": "", "concepts": [], "entities": []}

    async def analyze_history(self, session_id: Optional[str], history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Variante 'read-only' : ne touche pas la BDD, renvoie uniquement le calcul.
        """
        try:
            summary = _summarize(history)
            extracted = _extract_concepts_entities(summary, history)
            return {"session_id": session_id, "summary": summary, **extracted}
        except Exception as e:
            logger.error(f"[Analyzer] analyze_history KO (session={session_id}): {e}", exc_info=True)
            return {"session_id": session_id, "summary": "", "concepts": [], "entities": []}
