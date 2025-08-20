# src/backend/shared/config.py
# V1.3 - Defaults Cloud Run: bascule automatique sur /tmp pour DB & VectorStore & chemins d'écriture
import os
from pathlib import Path
from typing import Optional, Dict, Any

from pydantic_settings import BaseSettings
from pydantic import Field

# --- CHEMINS DE BASE ---
# src/backend/shared/config.py -> src/backend/shared -> src/backend -> src -> /
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
SRC_DIR = BASE_DIR / "src"
BACKEND_DIR = SRC_DIR / "backend"
DATA_DIR = BACKEND_DIR / "data"
PROMPTS_DIR = BASE_DIR / "prompts"

IS_CLOUD_RUN = bool(os.getenv("K_SERVICE") or os.getenv("CLOUD_RUN_SERVICE"))

def _db_file_default() -> str:
    # SQLite fichier: en Cloud Run on persiste en /tmp (FS RW éphémère)
    if IS_CLOUD_RUN:
        return "/tmp/emergence/db/emergence_v7.db"
    return str(DATA_DIR / "db/emergence_v7.db")

def _vector_store_default() -> str:
    # Priorité à l'ENV si présent
    env = os.getenv("DB__VECTOR_STORE_PATH")
    if env and env.strip():
        return env.strip()
    # Cloud Run → /tmp
    if IS_CLOUD_RUN:
        return "/tmp/emergence/vector_store"
    return str(DATA_DIR / "vector_store")

def _documents_default() -> str:
    env = os.getenv("EMERGENCE_UPLOADS_DIR")
    if env and env.strip():
        return env.strip()
    if IS_CLOUD_RUN:
        return "/tmp/emergence/uploads"
    return str(DATA_DIR / "uploads")

def _sessions_default() -> str:
    if IS_CLOUD_RUN:
        return "/tmp/emergence/sessions"
    return str(DATA_DIR / "sessions")

def _debates_default() -> str:
    if IS_CLOUD_RUN:
        return "/tmp/emergence/debates"
    return str(DATA_DIR / "debates")

class RagSettings(BaseSettings):
    ENABLED: bool = True
    N_RESULTS: int = 5
    EMBED_MODEL_NAME: str = "all-MiniLM-L6-v2"
    PROMPT_TEMPLATE: str = (
        "Contexte pertinent:\n---\n{context}\n---\nEn te basant UNIQUEMENT sur ce contexte, "
        "réponds à la question suivante: {question}"
    )

class DbSettings(BaseSettings):
    filepath: str = Field(default_factory=_db_file_default)
    vector_store_path: str = Field(default_factory=_vector_store_default)
    migrations_dir: str = str(DATA_DIR / "migrations")

class PathSettings(BaseSettings):
    documents: str = Field(default_factory=_documents_default)
    sessions: str = Field(default_factory=_sessions_default)
    debates: str = Field(default_factory=_debates_default)
    prompts: str = str(PROMPTS_DIR)

class Settings(BaseSettings):
    # Clés API et configurations diverses
    openai_api_key: str
    google_api_key: str
    anthropic_api_key: str
    gemini_api_key: Optional[str] = None
    elevenlabs_api_key: Optional[str] = None
    elevenlabs_voice_id: Optional[str] = None
    elevenlabs_model_id: Optional[str] = None
    dev_mode: bool = False

    # Configurations des agents
    agents: Dict[str, Any] = {
        "default": {"provider": "google", "model": "gemini-1.5-flash"},
        "neo": {"provider": "google", "model": "gemini-1.5-flash"},
        "nexus": {"provider": "anthropic", "model": "claude-3-haiku-20240307"},
        "anima": {"provider": "openai", "model": "gpt-4o"},
    }

    # Configurations imbriquées
    rag: RagSettings = RagSettings()
    db: DbSettings = DbSettings()
    paths: PathSettings = PathSettings()

    class Config:
        case_sensitive = False
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"
