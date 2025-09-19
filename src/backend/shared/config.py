# src/backend/shared/config.py
# V1.2 - Correction du chemin de BASE_DIR pour localiser les prompts
import os
from pathlib import Path
from typing import Optional, List, Dict, Any

from pydantic_settings import BaseSettings
from pydantic import Field

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

class PathSettings(BaseSettings):
    documents: str = str(DATA_DIR / "uploads")
    sessions: str = str(DATA_DIR / "sessions")
    debates: str = str(DATA_DIR / "debates")
    prompts: str = str(PROMPTS_DIR)

class Settings(BaseSettings):
    # ClÃ©s API et configurations diverses
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
        "nexus": {"provider": "anthropic", "model": "claude-3-5-haiku-20241022"},
        "anima": {"provider": "openai", "model": "gpt-4o-mini"},
    }
    
    # Configurations imbriquÃ©es
    rag: RagSettings = RagSettings()
    db: DbSettings = DbSettings()
    paths: PathSettings = PathSettings()

    class Config:
        case_sensitive = False
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


