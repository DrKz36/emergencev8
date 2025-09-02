# src/backend/features/memory/router.py
# V2.5 — + support body {thread_id} pour tend-garden (consolidation ciblée d’un thread)
import os
import logging
from typing import Dict, Any, Optional, Tuple, List

from fastapi import APIRouter, HTTPException, Request, Body, Query

from backend.features.memory.gardener import MemoryGardener

router = APIRouter(tags=["Memory & Knowledge"])
logger = logging.getLogger(__name__)

_KNOWLEDGE_COLLECTION_ENV = "EMERGENCE_KNOWLEDGE_COLLECTION"
_DEFAULT_KNOWLEDGE_NAME = "emergence_knowledge"

def _get_container(request: Request):
    container = getattr(request.app.state, "service_container", None)
    if container is None:
        raise HTTPException(status_code=503, detail="Service container indisponible.")
    return container

def _get_gardener_from_request(request: Request) -> MemoryGardener:
    container = _get_container(request)
    return MemoryGardener(
        db_manager=container.db_manager(),
        vector_service=container.vector_service(),
        memory_analyzer=container.memory_analyzer(),
    )

def _resolve_session_id(request: Request, explicit_session_id: Optional[str] = None) -> str:
    if explicit_session_id and str(explicit_session_id).strip():
        return str(explicit_session_id).strip()
    for key in ("X-Session-Id", "x-session-id", "X-Session-ID"):
        sid = request.headers.get(key)
        if sid and str(sid).strip():
            return str(sid).strip()
    raise HTTPException(status_code=400, detail="Session ID manquant (header 'X-Session-Id' ou paramètre 'session_id').")

async def _purge_stm(db_manager, session_id: str) -> bool:
    try:
        await db_manager.execute(
            """
            UPDATE sessions
               SET summary = NULL,
                   extracted_concepts = NULL,
                   extracted_entities = NULL
             WHERE id = ?
            """,
            (session_id,),
        )
        return True
    except Exception as e:
        logger.error(f"[memory.clear] Échec purge STM pour session={session_id}: {e}", exc_info=True)
        return False

def _count_ids_from_get_result(got: Dict[str, Any]) -> int:
    ids = got.get("ids") or []
    if not isinstance(ids, list): return 0
    if ids and isinstance(ids[0], list): return sum(len(x or []) for x in ids)
    return len(ids)

def _build_where_filter(session_id: Optional[str], agent_id: Optional[str], user_id: Optional[str]) -> Dict[str, Any]:
    clauses: List[Dict[str, Any]] = []
    if session_id: clauses.append({"source_session_id": session_id})
    if agent_id:   clauses.append({"agent": agent_id})
    if user_id:    clauses.append({"user_id": user_id})
    if not clauses: raise HTTPException(status_code=400, detail="Aucun critère de purge LTM déterminé.")
    return clauses[0] if len(clauses) == 1 else {"$and": clauses}

def _purge_ltm(vector_service, where_filter: Dict[str, Any]) -> Tuple[int, int]:
    try:
        collection_name = os.getenv(_KNOWLEDGE_COLLECTION_ENV, _DEFAULT_KNOWLEDGE_NAME)
        col = vector_service.get_or_create_collection(collection_name)
        got_before = col.get(where=where_filter)
        n_before = _count_ids_from_get_result(got_before)
        try:
            vector_service.delete_vectors(col, where_filter)
        except Exception as de:
            logger.warning(f"[memory.clear] delete_vectors(...) a levé: {de}")
            try: col.delete(where=where_filter)
            except Exception as de2:
                logger.warning(f"[memory.clear] fallback col.delete(where=...) a levé: {de2}")
        got_after = col.get(where=where_filter)
        n_after = _count_ids_from_get_result(got_after)
        return n_before, max(0, n_before - n_after)
    except Exception as e:
        logger.error(f"[memory.clear] purge LTM erreur: {e}", exc_info=True)
        return 0, 0

@router.post(
    "/tend-garden",
    response_model=Dict[str, Any],
    summary="Déclenche la consolidation de la mémoire (gardener).",
    description="Lance le 'MemoryGardener' pour analyser/consolider les sessions récentes ou un thread précis si 'thread_id' est fourni."
)
async def tend_garden_endpoint(request: Request, data: Dict[str, Any] = Body(default={}))-> Dict[str, Any]:
    logger.info("Requête reçue sur /api/memory/tend-garden.")
    try:
        gardener = _get_gardener_from_request(request)
        thread_id = None
        try:
            t = (data or {}).get("thread_id")
            if isinstance(t, str) and t.strip():
                thread_id = t.strip()
        except Exception:
            thread_id = None
        report = await gardener.tend_the_garden(thread_id=thread_id)
        if report.get("status") == "error":
            raise HTTPException(status_code=500, detail=report.get("message", "Erreur interne"))
        return report
    except HTTPException:
        raise
    except Exception as e:
        logger.critical(f"Erreur non gérée dans tend_garden: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erreur interne critique.")

@router.get(
    "/tend-garden",
    response_model=Dict[str, Any],
    summary="(Alias) Déclenche la consolidation de la mémoire (gardener).",
    description="Alias GET pour compatibilité UI (équivalent au POST)."
)
async def tend_garden_get(request: Request) -> Dict[str, Any]:
    return await tend_garden_endpoint(request)

@router.delete(
    "/clear",
    response_model=Dict[str, Any],
    summary="Efface la mémoire de la session (STM+LTM).",
    description="Supprime le résumé et les entités extraites de la session (STM) et purge les embeddings associés (LTM)."
)
async def clear_memory_delete(
    request: Request,
    session_id: Optional[str] = Query(default=None),
    agent_id: Optional[str] = Query(default=None),
) -> Dict[str, Any]:
    container = _get_container(request)
    sid = _resolve_session_id(request, session_id)
    uid = None
    try:
        sm = container.session_manager()
        for name in ("get_user_id_for_session","get_user","get_owner","get_session_owner"):
            fn = getattr(sm, name, None)
            if callable(fn):
                uid = fn(sid) or None
                if uid: break
    except Exception:
        uid = None
    where_filter = _build_where_filter(sid, (agent_id or "").strip().lower() or None, uid)
    stm_ok = await _purge_stm(container.db_manager(), sid)
    n_before, n_deleted = _purge_ltm(container.vector_service(), where_filter)
    payload = {"status":"success","cleared":{"session_id":sid,"agent_id":(agent_id or "").strip().lower() or None,"stm":bool(stm_ok),"ltm_before":int(n_before),"ltm_deleted":int(n_deleted)}}
    logger.info(f"[memory.clear] {payload}"); return payload

@router.post(
    "/clear",
    response_model=Dict[str, Any],
    summary="Efface la mémoire de la session (STM+LTM) — compat POST.",
    description="Équivalent DELETE avec body JSON."
)
async def clear_memory_post(request: Request, data: Dict[str, Any] = Body(default={})) -> Dict[str, Any]:
    session_id = (data or {}).get("session_id")
    agent_id = (data or {}).get("agent_id")
    container = _get_container(request)
    sid = _resolve_session_id(request, session_id)
    uid = None
    try:
        sm = container.session_manager()
        for name in ("get_user_id_for_session","get_user","get_owner","get_session_owner"):
            fn = getattr(sm, name, None)
            if callable(fn):
                uid = fn(sid) or None
                if uid: break
    except Exception:
        uid = None
    where_filter = _build_where_filter(sid, (agent_id or "").strip().lower() or None, uid)
    stm_ok = await _purge_stm(container.db_manager(), sid)
    n_before, n_deleted = _purge_ltm(container.vector_service(), where_filter)
    payload = {"status":"success","cleared":{"session_id":sid,"agent_id":(agent_id or "").strip().lower() or None,"stm":bool(stm_ok),"ltm_before":int(n_before),"ltm_deleted":int(n_deleted)}}
    logger.info(f"[memory.clear] {payload}"); return payload
