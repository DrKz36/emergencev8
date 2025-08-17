# src/backend/features/memory/analyzer.py
# V3.2 - Analyse sémantique robuste (sans dépendance WS) + fallback heuristique + MAJ BDD fiable.
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional, TYPE_CHECKING

# Typage retardé pour éviter les imports circulaires
if TYPE_CHECKING:
    from backend.features.chat.service import ChatService
    from backend.core.database.manager import DatabaseManager

from backend.core.database import queries as dbq

logger = logging.getLogger(__name__)


class MemoryAnalyzer:
    """
    Analyse les conversations pour en extraire les concepts clés et les entités.
    V3.2 : pas d'accès WebSocket ; écriture BDD directe ; heuristiques sûres si LLM indisponible.
    """

    def __init__(self, db_manager: "DatabaseManager", chat_service: Optional["ChatService"] = None) -> None:
        self.db_manager = db_manager
        self.chat_service = chat_service
        self.is_ready = self.chat_service is not None
        logger.info(f"MemoryAnalyzer V3.2 initialisé. Prêt : {self.is_ready}")

    def set_chat_service(self, chat_service: "ChatService") -> None:
        """Injection tardive possible (au startup)."""
        self.chat_service = chat_service
        self.is_ready = True
        logger.info("ChatService injecté dans MemoryAnalyzer. L'analyseur est prêt.")

    # --------------------------------------------------------------------- #
    # Public API
    # --------------------------------------------------------------------- #
    async def analyze_session_for_concepts(
        self,
        session_id: str,
        history: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Analyse une session et enregistre summary/concepts/entities dans la table sessions.
        - Aucun accès WebSocket ici (pas de connection_manager).
        - Écrit toujours dans la BDD (même vide) pour marquer le passage d'analyse.
        """
        if not history:
            logger.warning(f"Historique de la session {session_id} vide. Analyse annulée.")
            await dbq.update_session_analysis_data(self.db_manager, session_id, "", [], [])
            return {"summary": "", "concepts": [], "entities": []}

        # 1) Conversation textuelle simple (role: content)
        conversation_text = self._history_to_text(history)

        # 2) Tentative d'analyse via ChatService (si disponible)
        summary: str = ""
        concepts: List[str] = []
        entities: List[str] = []

        try:
            if self.chat_service and getattr(self.chat_service, "analyze_text_to_json", None):
                payload = await self.chat_service.analyze_text_to_json(
                    prompt=(
                        "Analyse cette conversation et fournis un JSON avec les clés "
                        "'summary' (2-3 phrases), 'concepts' (3-5 items), 'entities' (liste). "
                        "Réponds STRICTEMENT en JSON."
                    ),
                    text=conversation_text,
                )
                summary = (payload or {}).get("summary") or ""
                concepts = list(
                    dict.fromkeys([(c or "").strip() for c in (payload or {}).get("concepts", []) if c])
                )[:5]
                entities = list(
                    dict.fromkeys([(e or "").strip() for e in (payload or {}).get("entities", []) if e])
                )[:10]
            else:
                # 3) Fallback heuristique si pas d'analyse LLM dédiée
                summary = self._heuristic_summary(history)
                concepts = self._extract_concepts_heuristic(conversation_text)
                entities = self._extract_entities_heuristic(conversation_text)
        except Exception as e:
            logger.exception(f"Échec analyse LLM, fallback heuristique. session_id={session_id}: {e}")
            summary = self._heuristic_summary(history)
            concepts = self._extract_concepts_heuristic(conversation_text)
            entities = self._extract_entities_heuristic(conversation_text)

        # 4) Écriture en BDD (toujours)
        await dbq.update_session_analysis_data(self.db_manager, session_id, summary, concepts, entities)
        logger.info(
            "Analyse reçue pour la session %s: summary=%r, concepts=%s, entities=%s",
            session_id, summary[:80], concepts, entities,
        )
        return {"summary": summary, "concepts": concepts, "entities": entities}

    # --------------------------------------------------------------------- #
    # Helpers
    # --------------------------------------------------------------------- #
    def _history_to_text(self, history: List[Dict[str, Any]]) -> str:
        parts: List[str] = []
        for msg in history:
            role = (msg.get("role") or "").strip()
            content = (msg.get("content") or "").strip()
            if role and content:
                parts.append(f"{role}: {content}")
        return "\n".join(parts)

    def _heuristic_summary(self, history: List[Dict[str, Any]]) -> str:
        # Cherche la 1re question user + la dernière réponse assistant
        user_lines = [m.get("content", "") for m in history if m.get("role") == "user" and m.get("content")]
        asst_lines = [m.get("content", "") for m in history if m.get("role") in ("assistant", "system") and m.get("content")]
        first = user_lines[0] if user_lines else ""
        last = asst_lines[-1] if asst_lines else ""
        if first and last and first != last:
            return f"L'utilisateur a abordé: {first[:160]}. Réponse principale: {last[:160]}."
        if last:
            return f"Réponse principale: {last[:200]}."
        if first:
            return f"Demande/entrée principale: {first[:200]}."
        return "Conversation brève sans contenu exploitable."

    def _extract_concepts_heuristic(self, text: str) -> List[str]:
        # Mots fréquents non triviaux (FR): mini extraction very-light
        text_norm = re.sub(r"[^\wÀ-ÖØ-öø-ÿ'-]+", " ", text.lower())
        stop = {
            "le","la","les","un","une","des","du","de","d","et","ou","au","aux","avec","sans","sur","sous",
            "est","sont","je","tu","il","elle","on","nous","vous","ils","elles",
            "ai","as","a","avons","avez","ont","être","faire","avoir","pour","par","dans","qui","que","quoi",
            "quand","comment","où","aujourd'hui","hier","demain","the","a","an","to","of","in","is","it","this"
        }
        words = [w for w in text_norm.split() if len(w) > 2 and w not in stop]
        freq: Dict[str, int] = {}
        for w in words:
            freq[w] = freq.get(w, 0) + 1
        # Top 5 distinct
        ordered = sorted(freq.items(), key=lambda kv: (-kv[1], kv[0]))
        return [w for w, _ in ordered[:5]]

    def _extract_entities_heuristic(self, text: str) -> List[str]:
        # NER ultra-simple: mots en Majuscules significatives / sigles
        # (suffisant pour planter des entités de mémoire sans LLM)
        raw = set(re.findall(r"\b([A-ZÉÈÀÂÊÎÔÛÄËÏÖÜ][A-Za-zÉÈÀÂÊÎÔÛÄËÏÖÜà-ÿ0-9_-]{2,})\b", text))
        # Ajoute quelques sigles fréquents
        raw.update(re.findall(r"\b([A-Z]{2,6})\b", text))
        # Nettoyage
        cleaned = {e.strip(".,;:!?()[]{}") for e in raw if not e.isdigit()}
        # borne supérieure pour ne pas « polluer »
        out = list(dict.fromkeys(sorted(cleaned)))[:10]
        return out
