# src/backend/shared/config.py
# V1.2 - Correction du chemin de BASE_DIR pour localiser les prompts
from pathlib import Path
from typing import Optional, Dict, Any

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# --- CHEMINS DE BASE ---
# MODIFIÉ V1.2: Correction du chemin. On remonte de 4 niveaux pour atteindre la racine du projet.
# src/backend/shared/config.py -> src/backend/shared -> src/backend -> src -> /
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
SRC_DIR = BASE_DIR / "src"
BACKEND_DIR = SRC_DIR / "backend"
DATA_DIR = BACKEND_DIR / "data"
PROMPTS_DIR = BASE_DIR / "prompts" 

class RagSettings(BaseSettings):
    ENABLED: bool = True
    N_RESULTS: int = 5
    EMBED_MODEL_NAME: str = "all-MiniLM-L6-v2" 
    PROMPT_TEMPLATE: str = (
        "Contexte pertinent:\n---\n{context}\n---\nEn te basant UNIQUEMENT sur ce contexte, "
        "rÃ©ponds Ã  la question suivante: {question}"
    )

class DbSettings(BaseSettings):
    filepath: str = str(DATA_DIR / "db/emergence_v7.db")
    vector_store_path: str = str(DATA_DIR / "vector_store")
    migrations_dir: str = str(DATA_DIR / "migrations")


class VectorSettings(BaseSettings):
    backend: str = "auto"  # auto → Qdrant si configuré, sinon Chroma local
    persist_directory: str = str(DATA_DIR / "vector_store")
    embed_model_name: str = "all-MiniLM-L6-v2"
    qdrant_url: Optional[str] = None
    qdrant_api_key: Optional[str] = None

class PathSettings(BaseSettings):
    documents: str = str(DATA_DIR / "uploads")
    sessions: str = str(DATA_DIR / "sessions")
    debates: str = str(DATA_DIR / "debates")
    prompts: str = str(PROMPTS_DIR)

class Settings(BaseSettings):
    # ClÃ©s API et configurations diverses
    openai_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    elevenlabs_api_key: Optional[str] = None
    elevenlabs_voice_id: Optional[str] = None
    elevenlabs_model_id: Optional[str] = None
    dev_mode: bool = False
    
    # Configurations des agents
    agents: Dict[str, Any] = {
        "default": {"provider": "google", "model": "gemini-1.5-flash"},
        "neo": {"provider": "google", "model": "gemini-1.5-flash"},
        "nexus": {"provider": "anthropic", "model": "claude-3-5-haiku-20241022"},
        "anima": {"provider": "openai", "model": "gpt-4o-mini"},
    }
    
    # Configurations imbriquÃ©es
    rag: RagSettings = RagSettings()
    db: DbSettings = DbSettings()
    vector: VectorSettings = VectorSettings()
    paths: PathSettings = PathSettings()

    @model_validator(mode="after")
    def _synchronize_provider_keys(self) -> "Settings":
        google_key = self.google_api_key or self.gemini_api_key
        if not google_key:
            raise ValueError("GOOGLE_API_KEY or GEMINI_API_KEY must be provided.")
        object.__setattr__(self, "google_api_key", google_key)
        if self.gemini_api_key is None:
            object.__setattr__(self, "gemini_api_key", google_key)

        missing = [name for name in ("openai_api_key", "anthropic_api_key") if not getattr(self, name)]
        if missing:
            missing_env = ", ".join(name.upper() for name in missing)
            raise ValueError(f"Missing required API keys: {missing_env}")
        return self

    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


