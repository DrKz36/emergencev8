# src/backend/core/config.py
# Configuration centrale ÉMERGENCE — modèles & constantes.

import os

# --- Fallback global (héritage) ---
# Utilisé si un agent ne trouve ni son provider ni son model.
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gemini-1.5-flash")

# --- Mapping par agent (provider + model) ---
# Valeurs par défaut validées pour ÉMERGENCE (Q/P):
#   - anima  -> OpenAI    : gpt-4o-mini
#   - neo    -> Google    : gemini-1.5-flash
#   - nexus  -> Anthropic : claude-3-haiku
AGENT_PROVIDERS = {
    "anima": {
        "provider": os.getenv("ANIMA_PROVIDER",  "openai"),
        "model":    os.getenv("ANIMA_MODEL",     "gpt-4o-mini"),
    },
    "neo": {
        "provider": os.getenv("NEO_PROVIDER",    "google"),
        "model":    os.getenv("NEO_MODEL",       "gemini-1.5-flash"),
    },
    "nexus": {
        "provider": os.getenv("NEXUS_PROVIDER",  "anthropic"),
        "model":    os.getenv("NEXUS_MODEL",     "claude-3-haiku"),
    },
}

def get_agent_config(agent_id: str) -> tuple[str, str]:
    """
    Retourne (provider, model) pour un agent donné.
    Si non trouvé, renvoie (None, DEFAULT_MODEL) afin de préserver l’ancien comportement.
    """
    spec = AGENT_PROVIDERS.get(agent_id)
    if not spec:
        return (None, DEFAULT_MODEL)
    return (spec.get("provider") or None, spec.get("model") or DEFAULT_MODEL)

# --- Noms des Features pour le Suivi des Coûts ---
FEATURE_CHAT = "chat"              # chat simple
FEATURE_CHAT_RAG = "chat"          # aligné BDD (ne pas renommer)
FEATURE_DOCUMENT_PROCESSING = "document_processing"

# --- Configuration du Traitement des Documents ---
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150
DOCUMENT_COLLECTION_NAME = "emergence_documents"
