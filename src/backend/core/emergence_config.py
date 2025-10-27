# src/backend/core/config.py
# Configuration centrale ÉMERGENCE — modèles & constantes.

import os
import json

from typing import Optional

DEFAULT_GOOGLE_MODEL = "models/gemini-2.5-flash"
_GOOGLE_MODEL_ALIASES = {
    "gemini-2.5-flash": DEFAULT_GOOGLE_MODEL,
    "models/gemini-2.5-flash": DEFAULT_GOOGLE_MODEL,
    "gemini-2.0-flash": DEFAULT_GOOGLE_MODEL,
    "models/gemini-2.0-flash": DEFAULT_GOOGLE_MODEL,
    "gemini-1.5-flash": DEFAULT_GOOGLE_MODEL,
    "models/gemini-1.5-flash": DEFAULT_GOOGLE_MODEL,
    "models/gemini-1.5-flash-latest": DEFAULT_GOOGLE_MODEL,
    DEFAULT_GOOGLE_MODEL: DEFAULT_GOOGLE_MODEL,
}


def _normalize_google_model(value: Optional[str]) -> str:
    if not value:
        return DEFAULT_GOOGLE_MODEL
    cleaned = value.strip()
    if not cleaned:
        return DEFAULT_GOOGLE_MODEL
    return _GOOGLE_MODEL_ALIASES.get(cleaned, cleaned)


# --- Fallback global (héritage) ---
# Utilisé si un agent ne trouve ni son provider ni son model.
DEFAULT_MODEL = _normalize_google_model(os.getenv("DEFAULT_MODEL", DEFAULT_GOOGLE_MODEL))

# --- Mapping par agent (provider + model) ---
# Valeurs par défaut validées pour ÉMERGENCE (Q/P):
#   - anima  -> OpenAI    : gpt-4o-mini
#   - neo    -> Google    : models/gemini-2.5-flash
#   - nexus  -> Anthropic : claude-3-haiku
AGENT_PROVIDERS = {
    "anima": {
        "provider": os.getenv("ANIMA_PROVIDER", "openai"),
        "model": os.getenv("ANIMA_MODEL", "gpt-4o-mini"),
    },
    "neo": {
        "provider": os.getenv("NEO_PROVIDER", "google"),
        "model": _normalize_google_model(os.getenv("NEO_MODEL", DEFAULT_GOOGLE_MODEL)),
    },
    "nexus": {
        "provider": os.getenv("NEXUS_PROVIDER", "anthropic"),
        "model": os.getenv("NEXUS_MODEL", "claude-3-haiku"),
    },
}


def get_agent_config(agent_id: str) -> tuple[Optional[str], str]:
    """
    Retourne (provider, model) pour un agent donné.
    Si non trouvé, renvoie (None, DEFAULT_MODEL) afin de préserver l’ancien comportement.
    """
    spec = AGENT_PROVIDERS.get(agent_id)
    if not spec:
        return (None, DEFAULT_MODEL)
    return (spec.get("provider") or None, spec.get("model") or DEFAULT_MODEL)


# --- Noms des Features pour le Suivi des Coûts ---
FEATURE_CHAT = "chat"  # chat simple
FEATURE_CHAT_RAG = "chat"  # aligné BDD (ne pas renommer)
FEATURE_DOCUMENT_PROCESSING = "document_processing"

# --- Configuration du Traitement des Documents ---
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150
DOCUMENT_COLLECTION_NAME = "emergence_documents"

# --- Sécurité HTTP : Deny-list simple (404 early) ---
# Activable par env: DENYLIST_ENABLED=1|true|on
DENYLIST_ENABLED = str(os.getenv("DENYLIST_ENABLED", "1")).lower() in {
    "1",
    "true",
    "yes",
    "on",
}

# Liste de patterns (regex) — surcharge possible via env DENYLIST_PATTERNS (JSON array)
_DEFAULT_DENYLIST = [
    r"/(wp-admin|wp-login|wp-content|wp-includes)(/|$)",
    r"\.php(\?.*)?$",
    r"^/pearcmd",
    r"^/vendor/.*",
    r"^/\.git",
    r"^/\.env",
    r"^/server-status$",
    r"^/owa(/|$)",
    r"^/phpmyadmin(/|$)",
]


def _load_env_patterns() -> list[str]:
    raw = os.getenv("DENYLIST_PATTERNS")
    if not raw:
        return _DEFAULT_DENYLIST
    try:
        data = json.loads(raw)
        if isinstance(data, list) and all(isinstance(x, str) for x in data):
            return data
    except Exception:
        pass
    return _DEFAULT_DENYLIST


DENYLIST_PATTERNS: list[str] = _load_env_patterns()

