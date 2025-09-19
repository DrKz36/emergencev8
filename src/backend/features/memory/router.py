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

def _normalize_history_for_analysis(history: Optional[List[Any]]) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for item in history or []:
        if isinstance(item, dict):
            normalized.append(item)
            continue
        try:
            if hasattr(item, 'model_dump'):
                normalized.append(item.model_dump(mode='json'))  # type: ignore[attr-defined]
            elif hasattr(item, 'dict'):
                normalized.append(item.dict())  # type: ignore[attr-defined]
            else:
                normalized.append(dict(item))  # type: ignore[arg-type]
        except Exception:
            normalized.append({})
    return normalized



def _normalize_session_id(candidate: Optional[Any]) -> Optional[str]:
    if candidate is None:
        return None
    try:
        value = str(candidate).strip()
    except Exception:
        return None
    return value or None



def _resolve_session_id(request: Request, provided: Optional[str]) -> str:
    for candidate in (
        provided,
        request.headers.get('x-session-id'),
        request.query_params.get('session_id'),
    ):
        normalized = _normalize_session_id(candidate)
        if normalized:
            return normalized

    try:
        state_sid = getattr(request.state, 'session_id', None)
        normalized = _normalize_session_id(state_sid)
        if normalized:
            return normalized
    except Exception:
        pass

    try:
        container = getattr(request.app.state, 'service_container', None)
        if container is not None:
            session_manager = container.session_manager()
            active_sessions = getattr(session_manager, 'active_sessions', {})
            if isinstance(active_sessions, dict) and len(active_sessions) == 1:
                only_session_id = next(iter(active_sessions.keys()))
                normalized = _normalize_session_id(only_session_id)
                if normalized:
                    return normalized
    except Exception as exc:
        logger.debug(f"[memory] Session ID fallback via session_manager failed: {exc}")

    raise HTTPException(status_code=400, detail='Session ID manquant ou invalide.')


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
    "/analyze",
    response_model=Dict[str, Any],
    summary="Analyse sémantique d'une session (STM)",
    description="Génère ou régénère le résumé/concepts d'une session en utilisant le MemoryAnalyzer."
)
async def analyze_session_endpoint(
    request: Request,
    payload: Dict[str, Any] = Body(default={})
) -> Dict[str, Any]:
    container = _get_container(request)
    analyzer = container.memory_analyzer()
    session_manager = container.session_manager()

    raw_session_id = (payload or {}).get('session_id')
    force = bool((payload or {}).get('force'))
    session_id = _resolve_session_id(request, raw_session_id)

    if not session_manager.get_session(session_id):
        await session_manager.load_session_from_db(session_id)
    if not session_manager.get_session(session_id):
        raise HTTPException(status_code=404, detail="Session introuvable")

    metadata = session_manager.get_session_metadata(session_id)
    if metadata.get('summary') and not force:
        return {
            'status': 'skipped',
            'reason': 'already_analyzed',
            'session_id': session_id,
            'metadata': metadata,
        }

    history = _normalize_history_for_analysis(session_manager.get_full_history(session_id))

    if not history:
        return {
            'status': 'skipped',
            'reason': 'no_history',
            'session_id': session_id,
            'metadata': metadata,
        }

    try:
        analysis = await analyzer.analyze_session_for_concepts(session_id, history, force=force)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"[memory.analyze] Échec analyse session={session_id}: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Analyse mémoire impossible pour cette session.")

    updated_meta = session_manager.get_session_metadata(session_id)
    has_summary = bool((analysis or {}).get('summary')) or bool(updated_meta.get('summary'))
    response: Dict[str, Any] = {
        'status': 'completed' if has_summary else 'skipped',
        'session_id': session_id,
        'force': force,
        'analysis': analysis or updated_meta,
        'metadata': updated_meta,
    }
    if response['status'] == 'skipped':
        response.setdefault('reason', 'no_changes')
    return response


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
