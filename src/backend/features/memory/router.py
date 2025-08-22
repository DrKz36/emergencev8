# src/backend/features/memory/router.py
# V3.0 - + GET /context ; + POST /episodes/rebuild ; garde Bearer ; compat Cloud Run.
import os
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Header, Request, Response

# Garde & DI existants
from backend.shared.dependencies import (
    get_memory_gardener,
    get_vector_service,
    require_bearer_or_401,
)

from backend.features.memory.gardener import MemoryGardener
from backend.features.memory.episodes_store import EpisodesStore
from backend.features.memory.vector_service import VectorService

# Threads (lecture messages / dernier user text)
from backend.features.threads.service import ThreadsService  # type: ignore

# Auth Google ID token -> user_id (sub)
from google.oauth2 import id_token as google_id_token  # type: ignore
from google.auth.transport import requests as google_requests  # type: ignore

router = APIRouter(tags=["Memory"])
logger = logging.getLogger(__name__)

# ---------- util: user_id depuis Authorization: Bearer <IDTOKEN> ----------
async def _user_id_from_bearer(request: Request, authorization: Optional[str]) -> str:
    # 1) middleware/app (si déjà peuplé)
    user = getattr(request.state, "user", None)
    uid = getattr(user, "id", None) if user else None
    if uid:
        return str(uid)
    # 2) ID Token GIS
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        aud = os.getenv("GOOGLE_OAUTH_CLIENT_ID") or os.getenv("EMERGENCE_GOOGLE_CLIENT_ID")
        try:
            req = google_requests.Request()
            info = google_id_token.verify_oauth2_token(token, req, audience=aud)
            sub = info.get("sub")
            if sub:
                return str(sub)
        except Exception:
            pass
    raise HTTPException(status_code=401, detail="Unauthorized")

# ---------- Endpoints existants ----------
@router.get("/tend-garden")
@router.post("/tend-garden")
async def tend_garden(
    gardener: MemoryGardener = Depends(get_memory_gardener),
    _token: str = Depends(require_bearer_or_401),
) -> Dict[str, Any]:
    """
    Déclenche la consolidation des sessions -> summary/concepts -> vecteurs.
    """
    logger.info("Endpoint /api/memory/tend-garden déclenché.")
    try:
        report = await gardener.tend_the_garden()
        if report.get("status") == "error":
            raise HTTPException(status_code=500, detail=report.get("message", "Erreur inconnue."))
        return report
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Échec serveur dans tend_garden.")
        raise HTTPException(status_code=500, detail=str(e))

# ---------- NOUVEAU: GET /context ----------
@router.get("/context")
async def get_memory_context(
    request: Request,
    thread_id: str = Query(..., min_length=1),
    k: int = Query(3, ge=1, le=10),
    q: Optional[str] = Query(None, description="Texte de requête. Si omis, on prend le dernier message utilisateur du thread."),
    vector_service: VectorService = Depends(get_vector_service),
    authorization: Optional[str] = Header(None),
    _token: str = Depends(require_bearer_or_401),
) -> Dict[str, Any]:
    """
    Retourne k extraits pertinents depuis la collection mémoire (knowledge) pour alimenter le bandeau “Mémoire chargée”.
    Stratégie:
      - si q est vide, on lit le dernier message 'user' du thread et on l'utilise pour requêter.
      - on interroge la collection mémoire via VectorService et on assemble un payload compact.
    """
    user_id = await _user_id_from_bearer(request, authorization)

    # 1) Résoudre le texte de requête
    query_text = (q or "").strip()
    if not query_text:
        try:
            tid = thread_id
            ts = ThreadsService()
            msgs = await ts.list_messages(user_id=user_id, thread_id=tid, limit=200)
            # dernier message 'user' si dispo
            for m in reversed(msgs):
                if (getattr(m, "role", None) or "").lower() == "user":
                    query_text = (m.content or "").strip()
                    if query_text:
                        break
        except Exception as e:
            logger.warning("Lecture dernier message utilisateur échouée (thread=%s): %s", thread_id, e)

    if not query_text:
        return {"thread_id": thread_id, "items": [], "k": k, "query_text": "", "note": "empty_query"}

    # 2) Interroger la collection mémoire
    items: List[Dict[str, Any]] = []
    try:
        collection = vector_service.get_or_create_collection(os.getenv("KNOWLEDGE_COLLECTION_NAME") or "emergence_knowledge")
        results = vector_service.query(collection=collection, query_text=query_text) or []
        for r in results:
            meta = (r.get("metadata") or {}) if isinstance(r, dict) else {}
            text = meta.get("text") or meta.get("chunk") or ""
            if not text:
                continue
            items.append({
                "preview": text if len(text) <= 180 else (text[:179] + "…"),
                "score": r.get("score") if isinstance(r, dict) else None,
                "source_session_id": meta.get("source_session_id"),
                "source_role": meta.get("role"),
            })
            if len(items) >= k:
                break
    except Exception as e:
        logger.error("Erreur VectorService.query: %s", e, exc_info=True)
        return {"thread_id": thread_id, "items": [], "k": k, "query_text": query_text, "status": "error"}

    return {"thread_id": thread_id, "items": items, "k": k, "query_text": query_text, "status": "ok"}

# ---------- NOUVEAU: POST /episodes/rebuild ----------
@router.post("/episodes/rebuild")
async def rebuild_episodes_for_thread(
    request: Request,
    thread_id: str = Query(..., min_length=1),
    authorization: Optional[str] = Header(None),
    _token: str = Depends(require_bearer_or_401),
    gardener: MemoryGardener = Depends(get_memory_gardener),
) -> Dict[str, Any]:
    """
    Reconstruit 1 'episode' LTM (Firestore) pour un thread donné:
      - lit tout le thread (jusqu'à 1000 messages),
      - génère un résumé court + mots-clés (utilise MemoryAnalyzer si dispo, sinon heuristique simple),
      - upsert dans Firestore: users/{user_id}/episodes/{episode_id}
    """
    user_id = await _user_id_from_bearer(request, authorization)

    # 1) Lire les messages du thread
    ts = ThreadsService()
    try:
        msgs = await ts.list_messages(user_id=user_id, thread_id=thread_id, limit=1000)
    except KeyError:
        raise HTTPException(status_code=404, detail="thread_not_found")
    except Exception as e:
        logger.error("Erreur lecture messages thread=%s: %s", thread_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail="thread_read_error")

    # 2) Construire un texte brut (simple concat)
    parts: List[str] = []
    for m in msgs:
        role = (getattr(m, "role", "") or "").lower()
        who = "USER" if role == "user" else "ASSISTANT"
        text = (getattr(m, "content", "") or "").strip()
        if text:
            parts.append(f"[{who}] {text}")
    raw_text = "\n".join(parts).strip()

    if not raw_text:
        raise HTTPException(status_code=400, detail="empty_thread")

    # 3) Résumer — essayer MemoryAnalyzer (via gardener), sinon heuristique
    summary: str = ""
    keywords: List[str] = []
    try:
        analyzer = getattr(gardener, "memory_analyzer", None) or getattr(gardener, "analyzer", None)
        if analyzer is not None and hasattr(analyzer, "analyze_text_to_json"):
            data = analyzer.analyze_text_to_json(raw_text)  # type: ignore
            summary = (data.get("summary") or "").strip()
            kw = data.get("keywords") or data.get("concepts") or []
            if isinstance(kw, list):
                keywords = [str(x) for x in kw][:20]
        if not summary:
            # Fallback heuristique court
            summary = (raw_text[:600] + "…") if len(raw_text) > 600 else raw_text
            # keywords naïfs: 10 tokens les plus longs distincts
            tokens = [t.strip(".,;:!?()[]{}\"'").lower() for t in raw_text.split()]
            tokens = [t for t in tokens if len(t) >= 6]
            seen = set()
            for t in tokens:
                if t not in seen:
                    keywords.append(t); seen.add(t)
                if len(keywords) >= 10:
                    break
    except Exception as e:
        logger.warning("Analyse mémoire (LLM) non disponible, fallback heuristique: %s", e)
        summary = (raw_text[:600] + "…") if len(raw_text) > 600 else raw_text
        keywords = []

    # 4) Upsert Firestore
    try:
        store = EpisodesStore(project=os.getenv("GOOGLE_CLOUD_PROJECT"))
        eid = store.upsert_episode(
            user_id=user_id,
            episode_id=None,
            thread_id=thread_id,
            title=None,
            summary=summary,
            keywords=keywords,
            quality_score=None,
        )
        existed = store.list_for_thread(user_id=user_id, thread_id=thread_id, limit=3)
        return {"status": "ok", "episode_id": eid, "thread_id": thread_id, "count_recent": len(existed)}
    except Exception as e:
        logger.error("Erreur Firestore upsert episode: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="firestore_error")
