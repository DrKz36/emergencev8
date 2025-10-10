"""
Extracteur de préférences, intentions et contraintes utilisateur.
Pipeline hybride : filtrage lexical + classification LLM + normalisation.

Version P1.2 - Module autonome pour extraction enrichie au-delà des "mot-code"
"""

import logging
import hashlib
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

logger = logging.getLogger(__name__)

# ⚡ Métriques Prometheus (P1.3)
try:
    from prometheus_client import Counter, Histogram

    PREFERENCES_EXTRACTED_TOTAL = Counter(
        "memory_preferences_extracted_total",
        "Total préférences/intentions extraites",
        ["type"],  # preference, intent, constraint
    )

    PREFERENCES_CONFIDENCE = Histogram(
        "memory_preferences_confidence",
        "Distribution scores de confiance",
        buckets=[0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
    )

    PREFERENCES_EXTRACTION_DURATION = Histogram(
        "memory_preferences_extraction_duration_seconds",
        "Durée extraction préférences",
        buckets=[0.1, 0.5, 1.0, 2.0, 5.0],
    )

    PREFERENCES_LEXICAL_FILTERED = Counter(
        "memory_preferences_lexical_filtered_total",
        "Total messages filtrés par le filtre lexical",
    )

    PREFERENCES_LLM_CALLS = Counter(
        "memory_preferences_llm_calls_total",
        "Total d'appels LLM pour classification",
    )

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

if not PROMETHEUS_AVAILABLE:
    logger.warning("Prometheus client non disponible - métriques préférences désactivées")

# Verbes cibles pour filtrage lexical (patterns souples)
PREFERENCE_VERBS = {
    "fr": ["préfèr", "préfér", "prefere", "aim", "aime", "déteste", "adore", "appréci", "favoris"],
    "en": ["prefer", "like", "love", "hate", "enjoy", "favorite"],
}

INTENT_VERBS = {
    "fr": ["vouloir", "veux", "vais", "souhaite", "planifie", "prévoi", "décide", "compte"],
    "en": ["want", "wish", "plan", "intend", "decide", "will", "going to"],
}

CONSTRAINT_VERBS = {
    "fr": ["évite", "evite", "refuse", "jamais", "interdit", "ne pas", "impossible"],
    "en": ["avoid", "refuse", "never", "forbidden", "don't", "cannot"],
}


@dataclass
class PreferenceRecord:
    """Enregistrement préférence/intention/contrainte"""

    id: str  # Hash MD5 court
    type: str  # "preference" | "intent" | "constraint" | "neutral"
    topic: str  # Sujet normalisé
    action: str  # Verbe infinitif
    text: str  # Texte original
    timeframe: str  # ISO 8601 ou "ongoing"
    sentiment: str  # "positive" | "negative" | "neutral"
    confidence: float  # 0.0-1.0
    entities: List[str]  # Personnes, outils, lieux
    source_message_id: str
    thread_id: str
    captured_at: str  # ISO timestamp

    @staticmethod
    def generate_id(user_sub: str, topic: str, type_: str) -> str:
        """Génère ID unique basé sur (user_sub, topic, type)"""
        key = f"{user_sub}:{topic}:{type_}"
        return hashlib.md5(key.encode()).hexdigest()[:12]

    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire"""
        return asdict(self)


class PreferenceExtractor:
    """
    Extracteur de préférences/intentions/contraintes.

    Usage:
        extractor = PreferenceExtractor(llm_client)
        records = await extractor.extract(messages, user_sub="user123", thread_id="thread1")
    """

    def __init__(self, llm_client):
        self.llm = llm_client
        self.stats = {"extracted": 0, "filtered": 0, "classified": 0}

    async def extract(
        self, messages: List[Dict], user_sub: Optional[str] = None, thread_id: Optional[str] = None, user_id: Optional[str] = None
    ) -> List[PreferenceRecord]:
        """
        Extrait préférences/intentions depuis messages.

        Args:
            messages: Liste messages (role, content, id)
            user_sub: ID utilisateur (prioritaire)
            user_id: ID utilisateur (fallback si user_sub absent)
            thread_id: ID thread

        Returns:
            Liste PreferenceRecord avec confidence > 0.6

        Raises:
            ValueError: Si ni user_sub ni user_id fournis
        """
        # 🆕 HOTFIX P1.3: Fallback user_sub → user_id
        user_identifier = user_sub or user_id
        if not user_identifier:
            raise ValueError(
                "Cannot extract preferences: no user identifier (user_sub or user_id) provided"
            )

        # 🆕 LOG warning si fallback utilisé
        if not user_sub and user_id:
            logger.warning(
                f"[PreferenceExtractor] user_sub missing, using user_id={user_id} as fallback "
                f"(thread_id={thread_id})"
            )

        start_time = datetime.utcnow()
        records = []

        # Filtrer messages utilisateur
        user_messages = [m for m in messages if m.get("role") == "user"]

        for msg in user_messages:
            content = msg.get("content", "")
            msg_id = msg.get("id", "unknown")

            # Étape 1 : Filtrage lexical
            if not self._contains_target_verbs(content):
                self.stats["filtered"] += 1
                # 📊 Métrique filtrage lexical
                if PROMETHEUS_AVAILABLE:
                    PREFERENCES_LEXICAL_FILTERED.inc()
                continue

            # Étape 2 : Classification LLM
            classification = await self._classify_llm(content)
            self.stats["classified"] += 1
            # 📊 Métrique appels LLM
            if PROMETHEUS_AVAILABLE:
                PREFERENCES_LLM_CALLS.inc()

            if classification["type"] == "neutral":
                continue

            if classification["confidence"] < 0.6:
                logger.debug(
                    f"Low confidence {classification['confidence']:.2f}: {content[:50]}"
                )
                continue

            # Étape 3 : Normalisation
            record = PreferenceRecord(
                id=PreferenceRecord.generate_id(
                    user_identifier, classification["topic"], classification["type"]
                ),
                type=classification["type"],
                topic=classification["topic"],
                action=classification["action"],
                text=content,
                timeframe=classification.get("timeframe", "ongoing"),
                sentiment=classification.get("sentiment", "neutral"),
                confidence=classification["confidence"],
                entities=classification.get("entities", []),
                source_message_id=msg_id,
                thread_id=thread_id or "unknown",
                captured_at=datetime.utcnow().isoformat(),
            )

            records.append(record)
            self.stats["extracted"] += 1

            # 📊 Métriques par préférence extraite
            if PROMETHEUS_AVAILABLE:
                PREFERENCES_EXTRACTED_TOTAL.labels(type=record.type).inc()
                PREFERENCES_CONFIDENCE.observe(record.confidence)

        # 📊 Métrique durée totale
        if PROMETHEUS_AVAILABLE:
            duration = (datetime.utcnow() - start_time).total_seconds()
            PREFERENCES_EXTRACTION_DURATION.observe(duration)

        logger.info(
            f"Extracted {len(records)} preferences/intents (filtered: {self.stats['filtered']}, classified: {self.stats['classified']})"
        )
        return records

    def _contains_target_verbs(self, text: str) -> bool:
        """Filtre lexical : contient verbes cibles ?"""
        text_lower = text.lower()

        all_verbs = (
            PREFERENCE_VERBS["fr"]
            + PREFERENCE_VERBS["en"]
            + INTENT_VERBS["fr"]
            + INTENT_VERBS["en"]
            + CONSTRAINT_VERBS["fr"]
            + CONSTRAINT_VERBS["en"]
        )

        return any(verb in text_lower for verb in all_verbs)

    async def _classify_llm(self, text: str) -> Dict[str, Any]:
        """
        Classification LLM (gpt-4o-mini ou claude-3-haiku).

        Returns:
            {
                "type": "preference" | "intent" | "constraint" | "neutral",
                "topic": "programmation",
                "action": "apprendre",
                "timeframe": "ongoing",
                "sentiment": "positive",
                "confidence": 0.85,
                "entities": ["Python", "FastAPI"]
            }
        """
        prompt = f"""Tu es un extracteur de préférences utilisateur.

Analyse ce message et extrait :
- **type** : "preference" (goût, habitude), "intent" (action future), "constraint" (limite), ou "neutral"
- **topic** : Sujet principal (1-3 mots)
- **action** : Verbe principal (infinitif)
- **timeframe** : Date ISO 8601 si mentionnée, sinon "ongoing"
- **sentiment** : "positive", "negative", "neutral"
- **confidence** : Score 0.0-1.0 (certitude extraction)
- **entities** : Noms propres, outils, lieux (liste)

Message : "{text}"

Réponds UNIQUEMENT en JSON valide :
{{"type": "...", "topic": "...", "action": "...", "timeframe": "...", "sentiment": "...", "confidence": 0.0, "entities": []}}"""

        try:
            # Appel LLM (utilise ChatService si disponible)
            if hasattr(self.llm, "get_structured_llm_response"):
                # Via ChatService
                schema = {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string"},
                        "topic": {"type": "string"},
                        "action": {"type": "string"},
                        "timeframe": {"type": "string"},
                        "sentiment": {"type": "string"},
                        "confidence": {"type": "number"},
                        "entities": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": [
                        "type",
                        "topic",
                        "action",
                        "timeframe",
                        "sentiment",
                        "confidence",
                        "entities",
                    ],
                }
                result = await self.llm.get_structured_llm_response(
                    agent_id="neo_analysis", prompt=prompt, json_schema=schema
                )
            else:
                # Fallback : appel direct (mock ou autre client)
                import json

                response = await self.llm.generate(
                    prompt=prompt,
                    model="gpt-4o-mini",
                    temperature=0.1,
                    response_format="json",
                )
                result = json.loads(response)

            # Normalisation clés (prévention localisation)
            return {
                "type": result.get("type", "neutral"),
                "topic": result.get("topic", "unknown"),
                "action": result.get("action", ""),
                "timeframe": result.get("timeframe", "ongoing"),
                "sentiment": result.get("sentiment", "neutral"),
                "confidence": float(result.get("confidence", 0.5)),
                "entities": result.get("entities", []),
            }

        except Exception as e:
            logger.error(f"LLM classification failed: {e}", exc_info=True)
            return {
                "type": "neutral",
                "topic": "unknown",
                "action": "",
                "timeframe": "ongoing",
                "sentiment": "neutral",
                "confidence": 0.0,
                "entities": [],
            }
