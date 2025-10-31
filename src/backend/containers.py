# src/backend/containers.py
# V5.8 — DI alignée :
#    - DocumentService(db_manager, parser_factory, vector_service, uploads_dir) ✅
#    - Plus d’injection 'cost_tracker' dans DocumentService ❌
#    - VectorService(persist_directory, embed_model_name) ✅
#    - Helpers robustes _get_db_path/_get_vector_dir/_get_embed_model_name/_get_uploads_dir ✅
#    - DebateService présent (déjà utilisé par WS) ✅
#    - Alias ServiceContainer ✅

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional, Any

from dependency_injector import containers, providers
import httpx

from backend.shared.app_settings import Settings
from backend.core.database.manager import DatabaseManager
from backend.core.cost_tracker import CostTracker
from backend.core.session_manager import SessionManager
from backend.core.websocket import ConnectionManager
from backend.features.auth.service import AuthService, build_auth_config_from_env
from backend.features.auth.rate_limiter import SlidingWindowRateLimiter
from backend.features.memory.vector_service import VectorService
from backend.features.memory.analyzer import MemoryAnalyzer
from backend.features.chat.service import ChatService

logger = logging.getLogger(__name__)

# --- Features optionnelles (tolérance à l'absence) ---
try:
    from backend.features.dashboard.service import DashboardService
    from backend.features.dashboard.admin_service import AdminDashboardService
except Exception:  # pragma: no cover
    DashboardService = None  # type: ignore[assignment,misc]
    AdminDashboardService = None  # type: ignore[assignment,misc]

try:
    from backend.features.documents.service import DocumentService
    from backend.features.documents.parser import ParserFactory  # requis par DocumentService
except Exception:  # pragma: no cover
    DocumentService = None  # type: ignore[assignment,misc]
    ParserFactory = None  # type: ignore[assignment,misc]

try:
    from backend.features.debate.service import DebateService
except Exception:  # pragma: no cover
    DebateService = None  # type: ignore[assignment,misc]

try:
    from backend.features.benchmarks.service import BenchmarksService
    from backend.benchmarks.persistence import (
        BenchmarksRepository,
        build_firestore_client,
    )
except Exception:  # pragma: no cover
    BenchmarksService = None  # type: ignore[assignment,misc]
    BenchmarksRepository = None  # type: ignore[assignment,misc]
    build_firestore_client = None  # type: ignore[assignment]

try:
    from backend.features.voice.service import VoiceService
    from backend.features.voice.models import VoiceServiceConfig
except Exception:  # pragma: no cover
    VoiceService = None  # type: ignore[assignment,misc]
    VoiceServiceConfig = None  # type: ignore[assignment,misc]

_VOICE_STT_MODEL_DEFAULT = "whisper-1"
_VOICE_TTS_MODEL_DEFAULT = "eleven_multilingual_v2"
_VOICE_TTS_VOICE_DEFAULT = "ohItIVrXTBI80RrUECOD"



# ----------------------------
# Helpers chemins / options
# ----------------------------
def _get_db_path(settings: Settings) -> str:
    """
    Préfère settings.db.filepath/path, tolère db.PATH/URL/url, sinon EMERGENCE_DB_PATH, défaut ./data/emergence.db
    Retour absolu.
    """
    cand: Optional[str] = None
    try:
        db = getattr(settings, "db", None)
        keys = ("filepath", "file_path", "path", "PATH", "url", "URL")
        if db is not None:
            if isinstance(db, dict):
                for key in keys:
                    val = db.get(key)
                    if isinstance(val, Path):
                        cand = str(val)
                        break
                    if isinstance(val, str) and val.strip():
                        cand = val.strip()
                        break
            else:
                for key in keys:
                    val = getattr(db, key, None)
                    if isinstance(val, Path):
                        cand = str(val)
                        break
                    if isinstance(val, str) and val.strip():
                        cand = val.strip()
                        break
    except Exception:
        cand = None
    if not cand:
        env_val = os.getenv("EMERGENCE_DB_PATH")
        if isinstance(env_val, str) and env_val.strip():
            cand = env_val.strip()
    if not cand:
        cand = "./data/emergence.db"
    return str(Path(cand).resolve())

def _get_vector_dir(settings: Settings) -> str:
    """
    Préfère settings.vector.persist_directory, sinon EMERGENCE_VECTOR_DIR, défaut ./data/vector_store
    """
    cand: Optional[str] = None
    try:
        vec = getattr(settings, "vector", None)
        keys = ("persist_directory", "persist_dir", "dir", "path")
        if vec is not None:
            if isinstance(vec, dict):
                for key in keys:
                    val = vec.get(key)
                    if isinstance(val, Path):
                        cand = str(val)
                        break
                    if isinstance(val, str) and val.strip():
                        cand = val.strip()
                        break
            else:
                for key in keys:
                    val = getattr(vec, key, None)
                    if isinstance(val, Path):
                        cand = str(val)
                        break
                    if isinstance(val, str) and val.strip():
                        cand = val.strip()
                        break
    except Exception:
        cand = None
    if not cand:
        env_val = os.getenv("EMERGENCE_VECTOR_DIR")
        if isinstance(env_val, str) and env_val.strip():
            cand = env_val.strip()
    if not cand:
        cand = "./data/vector_store"
    return str(Path(cand).resolve())

def _get_vector_backend(settings: Settings) -> str:
    try:
        vec = getattr(settings, "vector", None)
        backend = getattr(vec, "backend", None) if vec is not None else None
        if isinstance(backend, str) and backend.strip():
            return backend.strip()
    except Exception:
        pass
    env = os.getenv("VECTOR_BACKEND")
    return (env or "auto").strip()

def _get_qdrant_url(settings: Settings) -> Optional[str]:
    try:
        vec = getattr(settings, "vector", None)
        url = getattr(vec, "qdrant_url", None) if vec is not None else None
        if isinstance(url, str) and url.strip():
            return url.strip()
    except Exception:
        pass
    env = os.getenv("QDRANT_URL") or os.getenv("QDRANT_HOST")
    return env.strip() if isinstance(env, str) and env.strip() else None

def _get_qdrant_api_key(settings: Settings) -> Optional[str]:
    try:
        vec = getattr(settings, "vector", None)
        key = getattr(vec, "qdrant_api_key", None) if vec is not None else None
        if isinstance(key, str) and key.strip():
            return key.strip()
    except Exception:
        pass
    env = os.getenv("QDRANT_API_KEY")
    return env.strip() if isinstance(env, str) and env.strip() else None

def _get_embed_model_name(settings: Settings) -> str:
    """
    Modèle d'embedding SentenceTransformer.
    Préfère settings.vector.embed_model_name, sinon EMBED_MODEL_NAME, défaut all-MiniLM-L6-v2
    """
    try:
        vec = getattr(settings, "vector", None)
        name = getattr(vec, "embed_model_name", None)
        if isinstance(name, str) and name.strip():
            return name.strip()
    except Exception:
        pass
    return (os.getenv("EMBED_MODEL_NAME") or "all-MiniLM-L6-v2").strip()

def _get_uploads_dir(settings: Settings) -> str:
    """
    Répertoire de dépôt des fichiers uploadés (Documents).
    Préfère settings.paths.uploads, sinon EMERGENCE_UPLOADS_DIR, défaut ./data/uploads
    """
    try:
        paths = getattr(settings, "paths", None)
        up = getattr(paths, "uploads", None) if paths is not None else None
        if isinstance(up, str) and up.strip():
            return str(Path(up).resolve())
    except Exception:
        pass
    env = os.getenv("EMERGENCE_UPLOADS_DIR")
    if env and env.strip():
        return str(Path(env).resolve())
    return str(Path("./data/uploads").resolve())


def _build_voice_config(settings: Settings) -> VoiceServiceConfig:
    if VoiceServiceConfig is None:
        raise RuntimeError("VoiceServiceConfig unavailable.")

    stt_api_key = getattr(settings, "openai_api_key", None)
    if not stt_api_key or not str(stt_api_key).strip():
        raise RuntimeError("VoiceService requires OPENAI_API_KEY.")

    tts_api_key = getattr(settings, "elevenlabs_api_key", None)
    if not tts_api_key or not str(tts_api_key).strip():
        raise RuntimeError("VoiceService requires ELEVENLABS_API_KEY.")

    stt_model = getattr(settings, "whisper_model", None)
    tts_model_id = getattr(settings, "elevenlabs_model_id", None)
    tts_voice_id = getattr(settings, "elevenlabs_voice_id", None)

    # Mapping des voix par agent (ElevenLabs voice IDs)
    # Voix publiques pré-configurées :
    # - Anima (féminine) : Rachel - 21m00Tcm4TlvDq8ikWAM
    # - Neo (masculin jeune) : Antoni - ErXwobaYiN019PkySvjV
    # - Nexus (masculin posé) : Josh - TxGEqnHWrfWFTfGW9XjX
    agent_voices = {
        "anima": "21m00Tcm4TlvDq8ikWAM",  # Rachel - Voix féminine claire
        "neo": "ErXwobaYiN019PkySvjV",    # Antoni - Voix masculine jeune
        "nexus": "TxGEqnHWrfWFTfGW9XjX",  # Josh - Voix masculine mûre
    }

    return VoiceServiceConfig(
        stt_api_key=str(stt_api_key).strip(),
        stt_model=str(stt_model).strip() if stt_model else _VOICE_STT_MODEL_DEFAULT,
        tts_api_key=str(tts_api_key).strip(),
        tts_model_id=str(tts_model_id).strip() if tts_model_id else _VOICE_TTS_MODEL_DEFAULT,
        tts_voice_id=str(tts_voice_id).strip() if tts_voice_id else _VOICE_TTS_VOICE_DEFAULT,
        agent_voices=agent_voices,
    )


def _build_benchmarks_firestore_client(settings: Settings) -> Any:
    if build_firestore_client is None:
        return None  # type: ignore[unreachable]
    project_id = None
    candidate = getattr(settings, 'benchmarks_firestore_project', None)
    if isinstance(candidate, str) and candidate.strip():
        project_id = candidate.strip()
    else:
        bench_cfg = getattr(settings, 'benchmarks', None)
        if bench_cfg is not None:
            if isinstance(bench_cfg, dict):
                for attr in ('firestore_project', 'project_id', 'project'):
                    value = bench_cfg.get(attr)
                    if isinstance(value, str) and value.strip():
                        project_id = value.strip()
                        break
            else:
                for attr in ('firestore_project', 'project_id', 'project'):
                    value = getattr(bench_cfg, attr, None)
                    if isinstance(value, str) and value.strip():
                        project_id = value.strip()
                        break
    if project_id is None:
        for key in (
            'EMERGENCE_FIRESTORE_PROJECT',
            'BENCHMARKS_FIRESTORE_PROJECT',
            'GOOGLE_CLOUD_PROJECT',
            'GCLOUD_PROJECT',
            'GOOGLE_PROJECT_ID',
        ):
            env_val = os.getenv(key)
            if isinstance(env_val, str) and env_val.strip():
                project_id = env_val.strip()
                break
    return build_firestore_client(project_id=project_id)

# ----------------------------
# Container
# ----------------------------
class AppContainer(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(
        modules=[
            "backend.features.chat.router",
            "backend.features.threads.router",
            "backend.features.chat.service",
            "backend.features.debate.router",
            "backend.features.benchmarks.router",
        ]
    )

    # Settings (pydantic BaseSettings)
    settings = providers.Singleton(Settings)

    # --- DB ---
    db_path = providers.Callable(_get_db_path, settings)
    db_manager = providers.Singleton(DatabaseManager, db_path)  # positionnel → robuste

    # --- Coûts ---
    cost_tracker = providers.Singleton(CostTracker, db_manager=db_manager)

    # --- Mémoire vectorielle ---
    vector_dir = providers.Callable(_get_vector_dir, settings)
    embed_model_name = providers.Callable(_get_embed_model_name, settings)
    vector_backend = providers.Callable(_get_vector_backend, settings)
    qdrant_url = providers.Callable(_get_qdrant_url, settings)
    qdrant_api_key = providers.Callable(_get_qdrant_api_key, settings)
    vector_service = providers.Singleton(
        VectorService,
        persist_directory=vector_dir,
        embed_model_name=embed_model_name,
        backend_preference=vector_backend,
        qdrant_url=qdrant_url,
        qdrant_api_key=qdrant_api_key,
    )

    # --- Analyse sémantique (STM) ---
    memory_analyzer = providers.Singleton(MemoryAnalyzer, db_manager=db_manager)

    # --- Sessions + WS ---
    session_manager = providers.Singleton(
        SessionManager,
        db_manager=db_manager,
        memory_analyzer=memory_analyzer,
        vector_service=vector_service,  # 🆕 Phase Agent Memory: For HandshakeHandler init
    )
    auth_config = providers.Callable(build_auth_config_from_env)
    auth_rate_limiter = providers.Singleton(SlidingWindowRateLimiter)
    auth_service = providers.Singleton(
        AuthService,
        db_manager=db_manager,
        config=auth_config,
        rate_limiter=auth_rate_limiter,
    )

    connection_manager = providers.Singleton(ConnectionManager, session_manager=session_manager)

    # --- Documents (doit être défini avant ChatService) ---
    if DocumentService is not None and ParserFactory is not None:
        parser_factory = providers.Singleton(ParserFactory)
        uploads_dir = providers.Callable(_get_uploads_dir, settings)
        document_service = providers.Singleton(
            DocumentService,
            db_manager=db_manager,
            parser_factory=parser_factory,
            vector_service=vector_service,
            uploads_dir=uploads_dir,
        )
    else:
        document_service = None  # type: ignore[unreachable]

    # --- Chat ---
    chat_service = providers.Singleton(
        ChatService,
        session_manager=session_manager,
        cost_tracker=cost_tracker,
        vector_service=vector_service,
        settings=settings,
        document_service=document_service,  # ✅ Phase 3 RAG
    )

    # --- Features optionnelles ---
    if DashboardService is not None:
        dashboard_service = providers.Singleton(
            DashboardService,
            db_manager=db_manager,
            cost_tracker=cost_tracker,
        )

    # TimelineService pour les graphiques dashboard
    try:
        from backend.features.dashboard.timeline_service import TimelineService
        timeline_service = providers.Singleton(
            TimelineService,
            db_manager=db_manager,
        )
    except Exception:  # pragma: no cover
        pass

    if AdminDashboardService is not None:
        admin_dashboard_service = providers.Singleton(
            AdminDashboardService,
            db_manager=db_manager,
            cost_tracker=cost_tracker,
        )

    # DocumentService déjà défini plus haut (avant ChatService)

    if BenchmarksService is not None and BenchmarksRepository is not None:
        benchmarks_repository = providers.Singleton(
            BenchmarksRepository,
            db_manager=db_manager,
        )
        benchmarks_firestore_client = providers.Callable(
            _build_benchmarks_firestore_client,
            settings,
        )
        benchmarks_service = providers.Singleton(
            BenchmarksService,
            repository=benchmarks_repository,
            firestore_client=benchmarks_firestore_client,
        )
    if DebateService is not None:
        debate_service = providers.Singleton(
            DebateService,
            settings=settings,
            chat_service=chat_service,
            session_manager=session_manager,
            vector_service=vector_service,
            connection_manager=connection_manager,
            cost_tracker=cost_tracker,
        )

    if VoiceService is not None and VoiceServiceConfig is not None:
        voice_http_client = providers.Singleton(
            httpx.AsyncClient,
            timeout=httpx.Timeout(60.0),
        )
        voice_service = providers.Singleton(
            VoiceService,
            config=providers.Callable(_build_voice_config, settings),
            http_client=voice_http_client,
            chat_service=chat_service,
        )

# Alias attendu par main.py & routers
ServiceContainer = AppContainer



