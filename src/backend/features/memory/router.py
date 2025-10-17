# src/backend/features/memory/router.py
# V2.5 â€” + support body {thread_id} pour tend-garden (consolidation ciblÃ©e dâ€™un thread)
import os
import logging
import inspect
from typing import Dict, Any, Optional, Tuple, List

from fastapi import APIRouter, HTTPException, Request, Body, Query

from backend.features.memory.gardener import MemoryGardener
from backend.core.database import queries
from backend.shared import dependencies as shared_dependencies

router = APIRouter(tags=["Memory & Knowledge"])
logger = logging.getLogger(__name__)

_KNOWLEDGE_COLLECTION_ENV = "EMERGENCE_KNOWLEDGE_COLLECTION"
_DEFAULT_KNOWLEDGE_NAME = "emergence_knowledge"




def _supports_kwarg(func, name: str) -> bool:
    try:
        signature = inspect.signature(func)
    except (ValueError, TypeError):
        return False
    for param in signature.parameters.values():
        if param.name == name and param.kind in (inspect.Parameter.KEYWORD_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD):
            return True
    return False
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


def _normalize_history_for_analysis(
    history: Optional[List[Any]],
) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for item in history or []:
        if isinstance(item, dict):
            normalized.append(item)
            continue
        try:
            if hasattr(item, "model_dump"):
                normalized.append(item.model_dump(mode="json"))  # type: ignore[attr-defined]
            elif hasattr(item, "dict"):
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
        request.headers.get("x-session-id"),
        request.query_params.get("session_id"),
    ):
        normalized = _normalize_session_id(candidate)
        if normalized:
            return normalized

    try:
        state_sid = getattr(request.state, "session_id", None)
        normalized = _normalize_session_id(state_sid)
        if normalized:
            return normalized
    except Exception:
        pass

    try:
        container = getattr(request.app.state, "service_container", None)
        if container is not None:
            session_manager = container.session_manager()
            active_sessions = getattr(session_manager, "active_sessions", {})
            if isinstance(active_sessions, dict) and len(active_sessions) == 1:
                only_session_id = next(iter(active_sessions.keys()))
                normalized = _normalize_session_id(only_session_id)
                if normalized:
                    return normalized
    except Exception as exc:
        logger.debug(f"[memory] Session ID fallback via session_manager failed: {exc}")

    raise HTTPException(status_code=400, detail="Session ID manquant ou invalide.")


@router.post(
    "/sync-stm",
    response_model=Dict[str, Any],
    summary="Hydrate le SessionManager avec l'historique persistant.",
    description="Recharge la STM depuis la base pour un couple session/thread et renvoie les messages normalisÃ©s.",
)
async def sync_short_term_memory(
    request: Request, data: Dict[str, Any] = Body(default={})
) -> Dict[str, Any]:
    container = _get_container(request)
    session_manager = container.session_manager()
    try:
        user_id = await shared_dependencies.get_user_id(request)
    except HTTPException:
        raise

    payload = data or {}
    raw_thread_id = (
        payload.get("thread_id")
        or request.query_params.get("thread_id")
        or request.headers.get("x-thread-id")
    )
    thread_id = _normalize_session_id(raw_thread_id)

    raw_session_id = (
        payload.get("session_id")
        or request.headers.get("x-session-id")
        or raw_thread_id
    )
    session_id = _normalize_session_id(raw_session_id)
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id requis (ou thread_id).")

    limit_value = payload.get("limit") or request.query_params.get("limit")
    history_limit = 200
    if limit_value is not None:
        try:
            history_limit = int(str(limit_value).strip())
            if history_limit <= 0:
                history_limit = 200
        except (TypeError, ValueError):
            history_limit = 200

    await session_manager.ensure_session(
        session_id=session_id,
        user_id=user_id,
        thread_id=thread_id,
        history_limit=history_limit,
    )

    resolved_thread_id = (
        session_manager.get_thread_id_for_session(session_id) or thread_id
    )
    export = session_manager.export_history_for_transport(
        session_id, limit=history_limit
    )
    metadata = session_manager.get_session_metadata(session_id)
    meta_payload = {
        k: metadata.get(k)
        for k in ("summary", "concepts", "entities")
        if metadata.get(k)
    }

    response: Dict[str, Any] = {
        "status": "ok",
        "session_id": session_id,
        "thread_id": resolved_thread_id,
        "history_count": len(export),
        "messages": export,
        "metadata": meta_payload,
        "hydrated": bool(export),
    }

    owner = session_manager.get_user_id_for_session(session_id)
    if owner:
        response["user_id"] = owner

    return response


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
            commit=True,
        )
        return True
    except Exception as e:
        logger.error(
            f"[memory.clear] Ã‰chec purge STM pour session={session_id}: {e}",
            exc_info=True,
        )
        return False


def _count_ids_from_get_result(got: Dict[str, Any]) -> int:
    ids = got.get("ids") or []
    if not isinstance(ids, list):
        return 0
    if ids and isinstance(ids[0], list):
        return sum(len(x or []) for x in ids)
    return len(ids)



def _session_vector_clause(session_id: str) -> Dict[str, Any]:
    return {"$or": [{"session_id": session_id}, {"source_session_id": session_id}]}

def _build_where_filter(
    session_id: Optional[str], agent_id: Optional[str], user_id: Optional[str]
) -> Dict[str, Any]:
    clauses: List[Dict[str, Any]] = []
    if session_id:
        clauses.append(_session_vector_clause(session_id))
    if agent_id:
        clauses.append({"agent": agent_id})
    if user_id:
        clauses.append({"user_id": user_id})
    if not clauses:
        raise HTTPException(
            status_code=400, detail="Aucun critÃ¨re de purge LTM dÃ©terminÃ©."
        )
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
            logger.warning(f"[memory.clear] delete_vectors(...) a levÃ©: {de}")
            try:
                col.delete(where=where_filter)
            except Exception as de2:
                logger.warning(
                    f"[memory.clear] fallback col.delete(where=...) a levÃ©: {de2}"
                )
        got_after = col.get(where=where_filter)
        n_after = _count_ids_from_get_result(got_after)
        return n_before, max(0, n_before - n_after)
    except Exception as e:
        logger.error(f"[memory.clear] purge LTM erreur: {e}", exc_info=True)
        return 0, 0


@router.post(
    "/analyze",
    response_model=Dict[str, Any],
    summary="Analyse sÃ©mantique d'une session (STM)",
    description="GÃ©nÃ¨re ou rÃ©gÃ©nÃ¨re le rÃ©sumÃ©/concepts d'une session en utilisant le MemoryAnalyzer.",
)
async def analyze_session_endpoint(
    request: Request, payload: Dict[str, Any] = Body(default={})
) -> Dict[str, Any]:
    container = _get_container(request)
    analyzer = container.memory_analyzer()
    session_manager = container.session_manager()

    raw_session_id = (payload or {}).get("session_id")
    force = bool((payload or {}).get("force"))
    session_id = _resolve_session_id(request, raw_session_id)

    if not session_manager.get_session(session_id):
        await session_manager.load_session_from_db(session_id)
    if not session_manager.get_session(session_id):
        raise HTTPException(status_code=404, detail="Session introuvable")

    metadata = session_manager.get_session_metadata(session_id)
    if metadata.get("summary") and not force:
        return {
            "status": "skipped",
            "reason": "already_analyzed",
            "session_id": session_id,
            "metadata": metadata,
        }

    history = _normalize_history_for_analysis(
        session_manager.get_full_history(session_id)
    )

    if not history:
        return {
            "status": "skipped",
            "reason": "no_history",
            "session_id": session_id,
            "metadata": metadata,
        }

    # ✅ FIX CRITIQUE P2 Sprint 3: Récupérer user_id depuis request auth
    user_id: Optional[str] = None
    try:
        user_id = await shared_dependencies.get_user_id(request)
    except HTTPException:
        # Si pas d'auth, essayer de récupérer depuis session
        if hasattr(session_manager, "get_user_id_for_session"):
            user_id = session_manager.get_user_id_for_session(session_id)

    try:
        analysis = await analyzer.analyze_session_for_concepts(
            session_id, history, force=force, user_id=user_id
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            f"[memory.analyze] Ã‰chec analyse session={session_id}: {exc}", exc_info=True
        )
        raise HTTPException(
            status_code=500, detail="Analyse mÃ©moire impossible pour cette session."
        )

    # Invalider cache préférences après extraction (Bug #5 P1)
    if user_id:
        memory_ctx = getattr(request.app.state, "memory_context", None)
        if memory_ctx and hasattr(memory_ctx, "invalidate_preferences_cache"):
            memory_ctx.invalidate_preferences_cache(user_id)

    updated_meta = session_manager.get_session_metadata(session_id)
    has_summary = bool((analysis or {}).get("summary")) or bool(
        updated_meta.get("summary")
    )
    response: Dict[str, Any] = {
        "status": "completed" if has_summary else "skipped",
        "session_id": session_id,
        "force": force,
        "analysis": analysis or updated_meta,
        "metadata": updated_meta,
    }
    if response["status"] == "skipped":
        response.setdefault("reason", "no_changes")
    return response


@router.post(
    "/tend-garden",
    response_model=Dict[str, Any],
    summary="DÃ©clenche la consolidation de la mÃ©moire (gardener).",
    description="Lance le 'MemoryGardener' pour analyser/consolider les sessions rÃ©centes ou un thread prÃ©cis si 'thread_id' est fourni.",
)
async def tend_garden_endpoint(
    request: Request, data: Dict[str, Any] = Body(default={})
) -> Dict[str, Any]:
    logger.info("RequÃªte reÃ§ue sur /api/memory/tend-garden.")

    try:
        user_id = await shared_dependencies.get_user_id(request)
        gardener = _get_gardener_from_request(request)
        thread_id = None
        try:
            t = (data or {}).get("thread_id")
            if isinstance(t, str) and t.strip():
                thread_id = t.strip()
        except Exception:
            thread_id = None

        agent_id = None
        try:
            raw_agent = (data or {}).get("agent_id") or (data or {}).get("agentId")
            if isinstance(raw_agent, str) and raw_agent.strip():
                agent_id = raw_agent.strip()
        except Exception:
            agent_id = None

        resolved_session_id = None
        try:
            candidate_session = (data or {}).get("session_id")
        except Exception:
            candidate_session = None
        if not candidate_session:
            candidate_session = (
                request.headers.get("x-session-id")
                or request.query_params.get("session_id")
            )
        if candidate_session:
            resolved_session_id = _resolve_session_id(request, candidate_session)

        if not resolved_session_id and thread_id:
            try:
                container = _get_container(request)
                db = container.db_manager()
                thread_row = await queries.get_thread_any(db, thread_id)
                inferred_session = _normalize_session_id((thread_row or {}).get("session_id"))
                if inferred_session:
                    resolved_session_id = inferred_session
            except HTTPException:
                pass
            except Exception as exc:  # pragma: no cover - diagnostic path
                logger.debug("[memory] unable to infer session from thread %s: %s", thread_id, exc)

        call_kwargs: dict[str, Any] = {
            'thread_id': thread_id,
            'session_id': resolved_session_id,
            'agent_id': agent_id,
        }
        if _supports_kwarg(gardener.tend_the_garden, 'user_id'):
            call_kwargs['user_id'] = user_id
        report = await gardener.tend_the_garden(**call_kwargs)  # type: ignore[arg-type]

        # Invalider cache préférences après jardinage (Bug #5 P1)
        memory_ctx = getattr(request.app.state, "memory_context", None)
        if memory_ctx and hasattr(memory_ctx, "invalidate_preferences_cache") and user_id:
            memory_ctx.invalidate_preferences_cache(user_id)

        if report.get("status") == "error":
            raise HTTPException(
                status_code=500, detail=report.get("message", "Erreur interne")
            )
        return report
    except HTTPException:
        raise
    except Exception as e:
        logger.critical(f"Erreur non gÃ©rÃ©e dans tend_garden: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erreur interne critique.")


@router.get(
    "/tend-garden",
    response_model=Dict[str, Any],
    summary="Retourne l'état de consolidation mémoire.",
    description="Renvoie l'historique des consolidations (STM/LTM) et des métriques associées.",
)
async def tend_garden_get(
    request: Request, limit: Optional[int] = Query(default=None, ge=1, le=50)
) -> Dict[str, Any]:
    user_id = await shared_dependencies.get_user_id(request)
    use_fallback = False
    try:
        container = _get_container(request)
    except HTTPException as exc:
        if exc.status_code == 503:
            use_fallback = True
        else:
            raise

    if use_fallback:
        gardener = _get_gardener_from_request(request)
        call_kwargs: dict[str, Any] = {}
        if _supports_kwarg(gardener.tend_the_garden, 'user_id'):
            call_kwargs['user_id'] = user_id
        report = await gardener.tend_the_garden(**call_kwargs)  # type: ignore[arg-type]
        return {
            "status": report.get("status", "success"),
            "summaries": [],
            "facts": [],
            "ltm_count": int(report.get("new_concepts") or 0),
            "total": int(report.get("consolidated_sessions") or 0),
            "legacy_report": report,
        }

    db = container.db_manager()

    try:
        rows = await queries.get_all_sessions_overview(db, user_id=user_id)
    except Exception as exc:
        logger.error("[memory.tend_garden] Impossible de récupérer l'historique: %s", exc, exc_info=True)
        rows = []

    if limit is not None and limit >= 1:
        rows = rows[: int(limit)]

    summaries: List[Dict[str, Any]] = []
    for row in rows:
        summaries.append(
            {
                "session_id": row.get("id"),
                "updated_at": row.get("updated_at"),
                "summary": row.get("summary"),
                "concept_count": int(row.get("concept_count") or 0),
                "entity_count": int(row.get("entity_count") or 0),
            }
        )

    ltm_count: Optional[int] = None
    try:
        vector_service = container.vector_service()
        collection_name = os.getenv(_KNOWLEDGE_COLLECTION_ENV, _DEFAULT_KNOWLEDGE_NAME)
        collection = vector_service.get_or_create_collection(collection_name)
        if hasattr(collection, "count"):
            try:
                ltm_count = int(collection.count() or 0)
            except Exception as exc:  # pragma: no cover - dépend backend
                logger.debug("[memory.tend_garden] count() indisponible: %s", exc)
                ltm_count = None
    except Exception as exc:
        logger.debug("[memory.tend_garden] Impossible de déterminer ltm_count: %s", exc)
        ltm_count = None

    return {
        "status": "ok",
        "summaries": summaries,
        "facts": [],
        "ltm_count": ltm_count if ltm_count is not None else 0,
        "total": len(summaries),
    }


@router.delete(
    "/clear",
    response_model=Dict[str, Any],
    summary="Efface la mÃ©moire de la session (STM+LTM).",
    description="Supprime le rÃ©sumÃ© et les entitÃ©s extraites de la session (STM) et purge les embeddings associÃ©s (LTM).",
)
async def clear_memory_delete(
    request: Request,
    session_id: Optional[str] = Query(default=None),
    agent_id: Optional[str] = Query(default=None),
) -> Dict[str, Any]:
    requester_id = await shared_dependencies.get_user_id(request)
    container = _get_container(request)
    sid = _resolve_session_id(request, session_id)
    uid = requester_id
    try:
        sm = container.session_manager()
        for name in (
            "get_user_id_for_session",
            "get_user",
            "get_owner",
            "get_session_owner",
        ):
            fn = getattr(sm, name, None)
            if callable(fn):
                resolved = fn(sid) or None
                if resolved:
                    uid = resolved
                    break
    except Exception:
        uid = requester_id

    where_filter = _build_where_filter(
        sid, (agent_id or "").strip().lower() or None, uid
    )
    stm_ok = await _purge_stm(container.db_manager(), sid)
    n_before, n_deleted = _purge_ltm(container.vector_service(), where_filter)
    payload = {
        "status": "success",
        "cleared": {
            "session_id": sid,
            "agent_id": (agent_id or "").strip().lower() or None,
            "stm": bool(stm_ok),
            "ltm_before": int(n_before),
            "ltm_deleted": int(n_deleted),
        },
    }
    logger.info(f"[memory.clear] {payload}")
    return payload


@router.post(
    "/clear",
    response_model=Dict[str, Any],
    summary="Efface la mÃ©moire de la session (STM+LTM) â€” compat POST.",
    description="Ã‰quivalent DELETE avec body JSON.",
)
async def clear_memory_post(
    request: Request, data: Dict[str, Any] = Body(default={})
) -> Dict[str, Any]:
    session_id = (data or {}).get("session_id")
    agent_id = (data or {}).get("agent_id")
    requester_id = await shared_dependencies.get_user_id(request)
    container = _get_container(request)
    sid = _resolve_session_id(request, session_id)
    uid = requester_id
    try:
        sm = container.session_manager()
        for name in (
            "get_user_id_for_session",
            "get_user",
            "get_owner",
            "get_session_owner",
        ):
            fn = getattr(sm, name, None)
            if callable(fn):
                resolved = fn(sid) or None
                if resolved:
                    uid = resolved
                    break
    except Exception:
        uid = requester_id

    where_filter = _build_where_filter(
        sid, (agent_id or "").strip().lower() or None, uid
    )
    stm_ok = await _purge_stm(container.db_manager(), sid)
    n_before, n_deleted = _purge_ltm(container.vector_service(), where_filter)
    payload = {
        "status": "success",
        "cleared": {
            "session_id": sid,
            "agent_id": (agent_id or "").strip().lower() or None,
            "stm": bool(stm_ok),
            "ltm_before": int(n_before),
            "ltm_deleted": int(n_deleted),
        },
    }
    logger.info(f"[memory.clear] {payload}")
    return payload




# ========== Concept Recall API (Phase 4) ==========

@router.get("/search")
async def search_memory(
    request: Request,
    q: str = Query(..., min_length=3, description="Requête de recherche"),
    limit: int = Query(10, ge=1, le=50, description="Nombre max de résultats"),
    start_date: Optional[str] = Query(None, description="Date de début (ISO 8601)"),
    end_date: Optional[str] = Query(None, description="Date de fin (ISO 8601)"),
):
    """
    Recherche temporelle dans l'historique des messages.

    Usage: GET /api/memory/search?q=containerization&limit=10&start_date=2025-01-01

    Returns list of matching messages with timestamps and metadata.
    """
    container = _get_container(request)

    # Get user_id from auth
    try:
        _user_id = await shared_dependencies.get_user_id(request)  # noqa: F841
    except HTTPException:
        raise HTTPException(status_code=401, detail="Authentication required")

    # Initialize TemporalSearch
    try:
        from backend.core.temporal_search import TemporalSearch

        temporal_search = TemporalSearch(db_manager=container.db_manager())
    except Exception as e:
        logger.error(f"[memory/search] Failed to initialize TemporalSearch: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal error initializing search")

    # Execute search
    try:
        results = await temporal_search.search_messages(query=q, limit=limit)

        # Filter by date range if provided
        if start_date or end_date:
            from datetime import datetime
            filtered = []
            for r in results:
                created_at = r.get("created_at") or r.get("timestamp")
                if not created_at:
                    continue
                try:
                    msg_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                    if start_date:
                        start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
                        if msg_dt < start_dt:
                            continue
                    if end_date:
                        end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                        if msg_dt > end_dt:
                            continue
                    filtered.append(r)
                except Exception:
                    continue
            results = filtered

    except Exception as e:
        logger.error(f"[memory/search] Query failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Search failed: {e}")

    return {
        "query": q,
        "results": results,
        "count": len(results),
        "filters": {
            "start_date": start_date,
            "end_date": end_date,
        },
    }


@router.get("/search/unified")
async def unified_memory_search(
    request: Request,
    q: str = Query(..., min_length=3, description="Requête de recherche"),
    limit: int = Query(10, ge=1, le=50, description="Nombre max de résultats par catégorie"),
    include_archived: bool = Query(True, description="Inclure threads archivés"),
    start_date: Optional[str] = Query(None, description="Date de début (ISO 8601)"),
    end_date: Optional[str] = Query(None, description="Date de fin (ISO 8601)"),
):
    """
    Recherche unifiée dans STM + LTM + threads + messages archivés.

    Usage: GET /api/memory/search/unified?q=docker&limit=10

    Returns:
    {
        "query": "docker",
        "stm_summaries": [...],      # Résumés de sessions (STM)
        "ltm_concepts": [...],        # Concepts vectoriels (LTM)
        "threads": [...],             # Threads correspondants
        "messages": [...],            # Messages archivés
        "total_results": 42
    }
    """
    container = _get_container(request)

    # Get user_id from auth
    try:
        user_id = await shared_dependencies.get_user_id(request)
    except HTTPException:
        raise HTTPException(status_code=401, detail="Authentication required")

    results: dict[str, Any] = {
        "query": q,
        "stm_summaries": [],
        "ltm_concepts": [],
        "threads": [],
        "messages": [],
        "total_results": 0,
    }

    # 1. Search STM (sessions with summaries)
    try:
        sessions = await queries.get_all_sessions_overview(
            container.db_manager(), user_id=user_id
        )
        for sess in sessions:
            summary = sess.get("summary") or ""
            if q.lower() in summary.lower():
                results["stm_summaries"].append({
                    "session_id": sess.get("id"),
                    "summary": summary,
                    "created_at": sess.get("created_at"),
                    "updated_at": sess.get("updated_at"),
                    "concept_count": sess.get("concept_count", 0),
                })
                if len(results["stm_summaries"]) >= limit:
                    break
    except Exception as e:
        logger.warning(f"[unified_search] STM search failed: {e}")

    # 2. Search LTM (vector concepts)
    try:
        from backend.features.memory.concept_recall import ConceptRecallTracker

        tracker = ConceptRecallTracker(
            db_manager=container.db_manager(),
            vector_service=container.vector_service(),
            connection_manager=None,
        )
        ltm_results = await tracker.query_concept_history(
            concept_text=q, user_id=user_id, limit=limit
        )
        results["ltm_concepts"] = ltm_results
    except Exception as e:
        logger.warning(f"[unified_search] LTM search failed: {e}")

    # 3. Search threads (titles + metadata)
    try:
        from backend.core.database import queries as db_queries

        all_threads = await db_queries.get_threads(
            container.db_manager(),
            session_id=None,
            user_id=user_id,
            include_archived=include_archived,
            limit=100,  # Pre-fetch more for filtering
        )
        for thread in all_threads:
            title = thread.get("title") or ""
            meta = thread.get("meta") or {}
            meta_str = str(meta) if isinstance(meta, dict) else ""
            if q.lower() in title.lower() or q.lower() in meta_str.lower():
                results["threads"].append({
                    "thread_id": thread.get("id"),
                    "title": title,
                    "type": thread.get("type"),
                    "archived": thread.get("archived"),
                    "last_message_at": thread.get("last_message_at"),
                    "message_count": thread.get("message_count"),
                    "created_at": thread.get("created_at"),
                })
                if len(results["threads"]) >= limit:
                    break
    except Exception as e:
        logger.warning(f"[unified_search] Threads search failed: {e}")

    # 4. Search messages (TemporalSearch)
    try:
        from backend.core.temporal_search import TemporalSearch

        temporal = TemporalSearch(db_manager=container.db_manager())
        messages = await temporal.search_messages(query=q, limit=limit)

        # Filter by date range if provided
        if start_date or end_date:
            from datetime import datetime

            filtered = []
            for msg in messages:
                created_at = msg.get("created_at") or msg.get("timestamp")
                if not created_at:
                    continue
                try:
                    msg_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                    if start_date:
                        start_dt = datetime.fromisoformat(
                            start_date.replace("Z", "+00:00")
                        )
                        if msg_dt < start_dt:
                            continue
                    if end_date:
                        end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                        if msg_dt > end_dt:
                            continue
                    filtered.append(msg)
                except Exception:
                    continue
            messages = filtered

        results["messages"] = messages
    except Exception as e:
        logger.warning(f"[unified_search] Messages search failed: {e}")

    # Calculate total
    results["total_results"] = (
        len(results["stm_summaries"])
        + len(results["ltm_concepts"])
        + len(results["threads"])
        + len(results["messages"])
    )

    return results


@router.get("/concepts/search")
async def search_concepts(
    request: Request,
    q: str = Query(..., min_length=3, description="Search query for concepts"),
    limit: int = Query(10, ge=1, le=50, description="Max number of results"),
):
    """
    Search for concepts in user's memory history.

    Usage: GET /api/memory/concepts/search?q=containerization&limit=10

    Returns list of matching concepts with metadata (first/last mentioned, thread IDs, etc.)
    """
    container = _get_container(request)

    # Get user_id from auth
    try:
        user_id = await shared_dependencies.get_user_id(request)
    except HTTPException:
        raise HTTPException(status_code=401, detail="Authentication required")

    # Get ConceptRecallTracker from container
    try:
        from backend.features.memory.concept_recall import ConceptRecallTracker

        tracker = ConceptRecallTracker(
            db_manager=container.db_manager(),
            vector_service=container.vector_service(),
            connection_manager=None,  # No WebSocket emission for REST API
        )
    except Exception as e:
        logger.error(f"[concepts/search] Failed to initialize tracker: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal error initializing concept search")

    # Query concept history
    try:
        results = await tracker.query_concept_history(
            concept_text=q,
            user_id=user_id,
            limit=limit,
        )
    except Exception as e:
        logger.error(f"[concepts/search] Query failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Concept search failed: {e}")

    return {
        "query": q,
        "results": results,
        "count": len(results),
    }


async def _thread_already_consolidated(vector_service, thread_id: str) -> bool:
    """
    Vérifie si thread déjà consolidé en cherchant concepts dans ChromaDB.

    Returns:
        True si au moins 1 concept du thread existe dans ChromaDB
    """
    try:
        collection_name = os.getenv(_KNOWLEDGE_COLLECTION_ENV, _DEFAULT_KNOWLEDGE_NAME)
        collection = vector_service.get_or_create_collection(collection_name)

        # Chercher concepts avec thread_id dans metadata
        result = collection.get(
            where={"thread_id": thread_id},
            limit=1
        )

        # Si au moins 1 concept trouvé, thread déjà consolidé
        ids = result.get("ids") or []
        if isinstance(ids, list) and len(ids) > 0:
            if isinstance(ids[0], list):
                return len(ids[0]) > 0
            return True
        return False

    except Exception as e:
        logger.warning(f"[consolidate_archived] Check failed for thread {thread_id}: {e}")
        return False  # En cas d'erreur, considérer non consolidé


@router.get(
    "/user/stats",
    response_model=Dict[str, Any],
    summary="Get user's memory statistics and top items",
    description="Returns user's memory stats: preferences, concepts, sessions analyzed, etc.",
)
async def get_user_memory_stats(
    request: Request
) -> Dict[str, Any]:
    """
    Get user's memory statistics and top items.

    Returns:
        {
          "preferences": {
            "total": 12,
            "top": [...],
            "by_type": {"preference": 8, "intent": 3, "constraint": 1}
          },
          "concepts": {
            "total": 47,
            "top": [...]
          },
          "stats": {
            "sessions_analyzed": 23,
            "threads_archived": 5,
            "ltm_size_mb": 2.4
          }
        }
    """
    try:
        user_id = await shared_dependencies.get_user_id(request)
    except HTTPException:
        raise HTTPException(status_code=401, detail="Authentication required")

    container = _get_container(request)
    vector_service = container.vector_service()
    db_manager = container.db_manager()

    collection_name = os.getenv(_KNOWLEDGE_COLLECTION_ENV, _DEFAULT_KNOWLEDGE_NAME)
    collection = vector_service.get_or_create_collection(collection_name)

    # Fetch user's preferences
    preferences = []
    type_counts = {"preference": 0, "intent": 0, "constraint": 0}

    try:
        # Phase 2 Fix: Utiliser OR au lieu de $in pour meilleure compatibilité ChromaDB
        prefs_results = collection.get(
            where={"$and": [
                {"user_id": user_id},
                {"$or": [
                    {"type": "preference"},
                    {"type": "intent"},
                    {"type": "constraint"}
                ]}
            ]},
            include=["documents", "metadatas"]
        )

        prefs_docs = prefs_results.get("documents", [])
        prefs_meta = prefs_results.get("metadatas", [])

        # Phase 2 Fix: Gérer les cas où documents/metadatas sont imbriqués dans des listes
        if prefs_docs and isinstance(prefs_docs, list) and len(prefs_docs) > 0:
            # Si first element is a list, flatten it
            if isinstance(prefs_docs[0], list):
                prefs_docs = [item for sublist in prefs_docs for item in sublist]

        if prefs_meta and isinstance(prefs_meta, list) and len(prefs_meta) > 0:
            if isinstance(prefs_meta[0], list):
                prefs_meta = [item for sublist in prefs_meta for item in sublist]

        # Parse preferences
        for doc, meta in zip(prefs_docs, prefs_meta):
            if not meta:  # Skip if metadata is None or empty
                continue

            pref_type = meta.get("type", "preference")
            type_counts[pref_type] = type_counts.get(pref_type, 0) + 1

            preferences.append({
                "topic": meta.get("topic", "Unknown"),
                "confidence": float(meta.get("confidence", 0.5)),
                "type": pref_type,
                "captured_at": meta.get("captured_at") or meta.get("created_at"),
                "text": doc if isinstance(doc, str) else str(doc)
            })

        # Sort by confidence (descending)
        preferences.sort(key=lambda x: x["confidence"], reverse=True)

        logger.info(f"[memory/user/stats] Retrieved {len(preferences)} preferences for user {user_id}")

    except Exception as e:
        logger.error(f"[memory/user/stats] Failed to fetch preferences: {e}", exc_info=True)
        # Continue with empty preferences

    # Fetch user's concepts
    concepts = []

    try:
        concepts_results = collection.get(
            where={"$and": [
                {"user_id": user_id},
                {"type": "concept"}
            ]},
            include=["documents", "metadatas"]
        )

        concepts_docs = concepts_results.get("documents", [])
        concepts_meta = concepts_results.get("metadatas", [])

        # Phase 2 Fix: Gérer les cas où documents/metadatas sont imbriqués dans des listes
        if concepts_docs and isinstance(concepts_docs, list) and len(concepts_docs) > 0:
            if isinstance(concepts_docs[0], list):
                concepts_docs = [item for sublist in concepts_docs for item in sublist]

        if concepts_meta and isinstance(concepts_meta, list) and len(concepts_meta) > 0:
            if isinstance(concepts_meta[0], list):
                concepts_meta = [item for sublist in concepts_meta for item in sublist]

        # Parse concepts
        for doc, meta in zip(concepts_docs, concepts_meta):
            if not meta:  # Skip if metadata is None or empty
                continue

            concepts.append({
                "concept": meta.get("concept_text") or (doc if isinstance(doc, str) else str(doc)),
                "mentions": int(meta.get("mention_count", 1)),
                "last_mentioned": meta.get("last_mentioned_at") or meta.get("created_at")
            })

        # Sort by mentions (descending)
        concepts.sort(key=lambda x: x["mentions"], reverse=True)

        logger.info(f"[memory/user/stats] Retrieved {len(concepts)} concepts for user {user_id}")

    except Exception as e:
        logger.error(f"[memory/user/stats] Failed to fetch concepts: {e}", exc_info=True)
        # Continue with empty concepts

    # Database stats
    sessions_count = 0
    archived_count = 0
    ltm_size_mb = 0.0

    try:
        # Count sessions analyzed (sessions with summary)
        sessions = await queries.get_all_sessions_overview(db_manager, user_id=user_id)
        sessions_count = len([s for s in sessions if s.get("summary")])

        # Count archived threads
        threads = await queries.get_threads(
            db_manager,
            session_id=None,
            user_id=user_id,
            archived_only=True,
            limit=1000
        )
        archived_count = len(threads)

        # Estimate LTM size (rough: ~1KB per item)
        ltm_size_mb = (len(prefs_docs) + len(concepts_docs)) * 0.001

    except Exception as e:
        logger.error(f"[memory/user/stats] Failed to fetch database stats: {e}", exc_info=True)
        # Continue with zero stats

    return {
        "preferences": {
            "total": len(preferences),
            "top": preferences[:10],
            "by_type": type_counts
        },
        "concepts": {
            "total": len(concepts),
            "top": concepts[:10]
        },
        "stats": {
            "sessions_analyzed": sessions_count,
            "threads_archived": archived_count,
            "ltm_size_mb": round(ltm_size_mb, 2)
        }
    }


@router.get(
    "/concepts",
    response_model=Dict[str, Any],
    summary="List all concepts with pagination",
    description="Retrieve user's concepts with pagination, sorting and filtering",
)
async def get_concepts(
    request: Request,
    limit: int = Query(20, ge=1, le=100, description="Number of concepts per page"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    sort: str = Query("recent", regex="^(recent|frequent|alphabetical)$", description="Sort order"),
) -> Dict[str, Any]:
    """Get paginated list of user's concepts."""
    try:
        user_id = await shared_dependencies.get_user_id(request)
    except HTTPException:
        raise HTTPException(status_code=401, detail="Authentication required")

    container = _get_container(request)
    vector_service = container.vector_service()
    collection_name = os.getenv(_KNOWLEDGE_COLLECTION_ENV, _DEFAULT_KNOWLEDGE_NAME)
    collection = vector_service.get_or_create_collection(collection_name)

    try:
        # Get all user concepts
        results = collection.get(
            where={"$and": [
                {"user_id": user_id},
                {"type": "concept"}
            ]},
            include=["documents", "metadatas"]
        )

        concepts_docs = results.get("documents", [])
        concepts_meta = results.get("metadatas", [])
        concepts_ids = results.get("ids", [])

        # Build concept objects
        concepts = []
        for concept_id, doc, meta in zip(concepts_ids, concepts_docs, concepts_meta):
            concept = {
                "id": concept_id,
                "concept_id": concept_id,
                "concept_text": meta.get("concept_text") or (doc if isinstance(doc, str) else str(doc)),
                "description": meta.get("description", ""),
                "tags": meta.get("tags", []),
                "relations": meta.get("relations", []),
                "occurrence_count": int(meta.get("mention_count", 1)),
                "first_mentioned": meta.get("first_mentioned_at") or meta.get("created_at"),
                "last_mentioned": meta.get("last_mentioned_at") or meta.get("created_at"),
                "thread_ids": meta.get("thread_ids", []),
            }
            concepts.append(concept)

        # Sort concepts
        if sort == "frequent":
            concepts.sort(key=lambda x: x["occurrence_count"], reverse=True)
        elif sort == "alphabetical":
            concepts.sort(key=lambda x: x["concept_text"].lower())
        else:  # recent
            concepts.sort(key=lambda x: x["last_mentioned"] or "", reverse=True)

        # Apply pagination
        total = len(concepts)
        paginated = concepts[offset:offset + limit]

        return {
            "concepts": paginated,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    except Exception as e:
        logger.error(f"[concepts/get] Failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve concepts: {e}")


@router.get(
    "/concepts/{concept_id}",
    response_model=Dict[str, Any],
    summary="Get concept details by ID",
    description="Retrieve full details for a specific concept",
)
async def get_concept(
    request: Request,
    concept_id: str,
) -> Dict[str, Any]:
    """Get detailed information about a specific concept."""
    try:
        user_id = await shared_dependencies.get_user_id(request)
    except HTTPException:
        raise HTTPException(status_code=401, detail="Authentication required")

    container = _get_container(request)
    vector_service = container.vector_service()
    collection_name = os.getenv(_KNOWLEDGE_COLLECTION_ENV, _DEFAULT_KNOWLEDGE_NAME)
    collection = vector_service.get_or_create_collection(collection_name)

    try:
        # Get concept by ID
        results = collection.get(
            ids=[concept_id],
            include=["documents", "metadatas"]
        )

        if not results.get("ids") or len(results["ids"]) == 0:
            raise HTTPException(status_code=404, detail="Concept not found")

        doc = results["documents"][0]
        meta = results["metadatas"][0]

        # Verify ownership
        if meta.get("user_id") != user_id:
            raise HTTPException(status_code=403, detail="Access denied")

        return {
            "id": concept_id,
            "concept_id": concept_id,
            "concept_text": meta.get("concept_text") or (doc if isinstance(doc, str) else str(doc)),
            "description": meta.get("description", ""),
            "tags": meta.get("tags", []),
            "relations": meta.get("relations", []),
            "occurrence_count": int(meta.get("mention_count", 1)),
            "first_mentioned": meta.get("first_mentioned_at") or meta.get("created_at"),
            "last_mentioned": meta.get("last_mentioned_at") or meta.get("created_at"),
            "thread_ids": meta.get("thread_ids", []),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[concepts/get_one] Failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve concept: {e}")


@router.patch(
    "/concepts/{concept_id}",
    response_model=Dict[str, Any],
    summary="Update concept metadata",
    description="Update description, tags, or relations for a concept",
)
async def update_concept(
    request: Request,
    concept_id: str,
    data: Dict[str, Any] = Body(...),
) -> Dict[str, Any]:
    """Update concept metadata (description, tags, relations)."""
    try:
        user_id = await shared_dependencies.get_user_id(request)
    except HTTPException:
        raise HTTPException(status_code=401, detail="Authentication required")

    container = _get_container(request)
    vector_service = container.vector_service()
    collection_name = os.getenv(_KNOWLEDGE_COLLECTION_ENV, _DEFAULT_KNOWLEDGE_NAME)
    collection = vector_service.get_or_create_collection(collection_name)

    try:
        # Get existing concept
        results = collection.get(
            ids=[concept_id],
            include=["metadatas"]
        )

        if not results.get("ids") or len(results["ids"]) == 0:
            raise HTTPException(status_code=404, detail="Concept not found")

        meta = results["metadatas"][0]

        # Verify ownership
        if meta.get("user_id") != user_id:
            raise HTTPException(status_code=403, detail="Access denied")

        # Update metadata
        updated_meta = {**meta}
        if "description" in data:
            updated_meta["description"] = data["description"]
        if "tags" in data:
            updated_meta["tags"] = data["tags"]
        if "relations" in data:
            updated_meta["relations"] = data["relations"]

        # Update in ChromaDB
        collection.update(
            ids=[concept_id],
            metadatas=[updated_meta]
        )

        return {
            "status": "success",
            "concept_id": concept_id,
            "updated": True,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[concepts/update] Failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update concept: {e}")


@router.delete(
    "/concepts/{concept_id}",
    response_model=Dict[str, Any],
    summary="Delete a concept",
    description="Permanently delete a concept from memory",
)
async def delete_concept(
    request: Request,
    concept_id: str,
) -> Dict[str, Any]:
    """Delete a concept from user's memory."""
    try:
        user_id = await shared_dependencies.get_user_id(request)
    except HTTPException:
        raise HTTPException(status_code=401, detail="Authentication required")

    container = _get_container(request)
    vector_service = container.vector_service()
    collection_name = os.getenv(_KNOWLEDGE_COLLECTION_ENV, _DEFAULT_KNOWLEDGE_NAME)
    collection = vector_service.get_or_create_collection(collection_name)

    try:
        # Get concept to verify ownership
        results = collection.get(
            ids=[concept_id],
            include=["metadatas"]
        )

        if not results.get("ids") or len(results["ids"]) == 0:
            raise HTTPException(status_code=404, detail="Concept not found")

        meta = results["metadatas"][0]

        # Verify ownership
        if meta.get("user_id") != user_id:
            raise HTTPException(status_code=403, detail="Access denied")

        # Delete from ChromaDB
        collection.delete(ids=[concept_id])

        return {
            "status": "success",
            "concept_id": concept_id,
            "deleted": True,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[concepts/delete] Failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete concept: {e}")


@router.post(
    "/concepts/merge",
    response_model=Dict[str, Any],
    summary="Merge multiple concepts into one",
    description="Combine 2+ concepts into a single concept, preserving all metadata and history",
)
async def merge_concepts(
    request: Request,
    data: Dict[str, Any] = Body(...),
) -> Dict[str, Any]:
    """
    Merge multiple concepts into one.

    Body params:
    - source_ids: List[str] - IDs of concepts to merge
    - target_id: str - ID of the target concept (will receive merged data)
    - new_concept_text: Optional[str] - New text for merged concept (default: target's text)
    """
    try:
        user_id = await shared_dependencies.get_user_id(request)
    except HTTPException:
        raise HTTPException(status_code=401, detail="Authentication required")

    source_ids = data.get("source_ids", [])
    target_id = data.get("target_id")
    new_concept_text = data.get("new_concept_text")

    if not source_ids or len(source_ids) < 1:
        raise HTTPException(status_code=400, detail="source_ids required (at least 1 concept)")
    if not target_id:
        raise HTTPException(status_code=400, detail="target_id required")
    if target_id in source_ids:
        raise HTTPException(status_code=400, detail="target_id cannot be in source_ids")

    container = _get_container(request)
    vector_service = container.vector_service()
    collection_name = os.getenv(_KNOWLEDGE_COLLECTION_ENV, _DEFAULT_KNOWLEDGE_NAME)
    collection = vector_service.get_or_create_collection(collection_name)

    try:
        # Get all concepts
        all_ids = source_ids + [target_id]
        results = collection.get(
            ids=all_ids,
            include=["documents", "metadatas"]
        )

        if not results.get("ids") or len(results["ids"]) != len(all_ids):
            raise HTTPException(status_code=404, detail="One or more concepts not found")

        # Verify ownership for all concepts
        for meta in results["metadatas"]:
            if meta.get("user_id") != user_id:
                raise HTTPException(status_code=403, detail="Access denied to one or more concepts")

        # Find target metadata
        target_idx = results["ids"].index(target_id)
        target_meta = {**results["metadatas"][target_idx]}
        target_doc = results["documents"][target_idx]

        # Merge data from source concepts
        merged_tags = set(target_meta.get("tags", []))
        merged_relations = list(target_meta.get("relations", []))
        merged_thread_ids = set(target_meta.get("thread_ids", []))
        total_occurrences = int(target_meta.get("mention_count", 1))
        earliest_mentioned = target_meta.get("first_mentioned_at") or target_meta.get("created_at")
        latest_mentioned = target_meta.get("last_mentioned_at") or target_meta.get("created_at")

        for concept_id in source_ids:
            idx = results["ids"].index(concept_id)
            source_meta = results["metadatas"][idx]

            # Merge tags
            merged_tags.update(source_meta.get("tags", []))

            # Merge relations
            for rel in source_meta.get("relations", []):
                if rel not in merged_relations:
                    merged_relations.append(rel)

            # Merge thread IDs
            merged_thread_ids.update(source_meta.get("thread_ids", []))

            # Sum occurrences
            total_occurrences += int(source_meta.get("mention_count", 1))

            # Update timestamps
            source_first = source_meta.get("first_mentioned_at") or source_meta.get("created_at")
            source_last = source_meta.get("last_mentioned_at") or source_meta.get("created_at")

            if source_first and (not earliest_mentioned or source_first < earliest_mentioned):
                earliest_mentioned = source_first
            if source_last and (not latest_mentioned or source_last > latest_mentioned):
                latest_mentioned = source_last

        # Update target concept
        target_meta["tags"] = list(merged_tags)
        target_meta["relations"] = merged_relations
        target_meta["thread_ids"] = list(merged_thread_ids)
        target_meta["mention_count"] = total_occurrences
        target_meta["first_mentioned_at"] = earliest_mentioned
        target_meta["last_mentioned_at"] = latest_mentioned

        if new_concept_text:
            target_meta["concept_text"] = new_concept_text

        # Update target in ChromaDB
        collection.update(
            ids=[target_id],
            metadatas=[target_meta],
            documents=[new_concept_text] if new_concept_text else None
        )

        # Delete source concepts
        collection.delete(ids=source_ids)

        logger.info(f"[concepts/merge] Merged {len(source_ids)} concepts into {target_id} for user {user_id}")

        return {
            "status": "success",
            "target_id": target_id,
            "merged_count": len(source_ids),
            "merged_ids": source_ids,
            "new_concept_text": new_concept_text or target_meta.get("concept_text"),
            "total_occurrences": total_occurrences,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[concepts/merge] Failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to merge concepts: {e}")


@router.post(
    "/concepts/split",
    response_model=Dict[str, Any],
    summary="Split a concept into multiple concepts",
    description="Divide a concept into multiple separate concepts with distinct meanings",
)
async def split_concept(
    request: Request,
    data: Dict[str, Any] = Body(...),
) -> Dict[str, Any]:
    """
    Split a concept into multiple new concepts.

    Body params:
    - source_id: str - ID of concept to split
    - new_concepts: List[Dict] - New concepts to create, each with:
        - concept_text: str - Text for new concept
        - description: Optional[str]
        - tags: Optional[List[str]]
        - weight: Optional[float] - Proportion of occurrences (0-1, must sum to 1)
    """
    try:
        user_id = await shared_dependencies.get_user_id(request)
    except HTTPException:
        raise HTTPException(status_code=401, detail="Authentication required")

    source_id = data.get("source_id")
    new_concepts = data.get("new_concepts", [])

    if not source_id:
        raise HTTPException(status_code=400, detail="source_id required")
    if not new_concepts or len(new_concepts) < 2:
        raise HTTPException(status_code=400, detail="At least 2 new_concepts required")

    # Validate weights sum to 1.0 (within tolerance)
    weights = [c.get("weight", 1.0 / len(new_concepts)) for c in new_concepts]
    if abs(sum(weights) - 1.0) > 0.01:
        raise HTTPException(status_code=400, detail="Concept weights must sum to 1.0")

    container = _get_container(request)
    vector_service = container.vector_service()
    collection_name = os.getenv(_KNOWLEDGE_COLLECTION_ENV, _DEFAULT_KNOWLEDGE_NAME)
    collection = vector_service.get_or_create_collection(collection_name)

    try:
        # Get source concept
        results = collection.get(
            ids=[source_id],
            include=["documents", "metadatas", "embeddings"]
        )

        if not results.get("ids") or len(results["ids"]) == 0:
            raise HTTPException(status_code=404, detail="Source concept not found")

        source_meta = results["metadatas"][0]
        source_embedding = results["embeddings"][0] if results.get("embeddings") else None

        # Verify ownership
        if source_meta.get("user_id") != user_id:
            raise HTTPException(status_code=403, detail="Access denied")

        # Create new concepts
        new_ids = []
        total_occurrences = int(source_meta.get("mention_count", 1))

        for idx, new_concept in enumerate(new_concepts):
            concept_text = new_concept.get("concept_text")
            if not concept_text:
                raise HTTPException(status_code=400, detail=f"concept_text required for new_concept[{idx}]")

            # Generate new ID
            import uuid
            new_id = f"concept_{user_id}_{uuid.uuid4().hex[:8]}"

            # Create metadata
            new_meta = {
                "user_id": user_id,
                "type": "concept",
                "concept_text": concept_text,
                "description": new_concept.get("description", ""),
                "tags": new_concept.get("tags", []),
                "relations": [],
                "mention_count": int(total_occurrences * weights[idx]),
                "first_mentioned_at": source_meta.get("first_mentioned_at"),
                "last_mentioned_at": source_meta.get("last_mentioned_at"),
                "thread_ids": source_meta.get("thread_ids", []),
                "created_at": source_meta.get("created_at"),
                "split_from": source_id,
            }

            # Add to collection (reuse embedding if available, else will be generated)
            collection.add(
                ids=[new_id],
                documents=[concept_text],
                metadatas=[new_meta],
                embeddings=[source_embedding] if source_embedding else None
            )

            new_ids.append(new_id)

        # Delete source concept
        collection.delete(ids=[source_id])

        logger.info(f"[concepts/split] Split concept {source_id} into {len(new_ids)} concepts for user {user_id}")

        return {
            "status": "success",
            "source_id": source_id,
            "new_ids": new_ids,
            "split_count": len(new_ids),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[concepts/split] Failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to split concept: {e}")


@router.post(
    "/concepts/bulk-delete",
    response_model=Dict[str, Any],
    summary="Delete multiple concepts at once",
    description="Bulk delete operation for cleaning up multiple concepts",
)
async def bulk_delete_concepts(
    request: Request,
    data: Dict[str, Any] = Body(...),
) -> Dict[str, Any]:
    """
    Delete multiple concepts in one operation.

    Body params:
    - concept_ids: List[str] - IDs of concepts to delete
    """
    try:
        user_id = await shared_dependencies.get_user_id(request)
    except HTTPException:
        raise HTTPException(status_code=401, detail="Authentication required")

    concept_ids = data.get("concept_ids", [])

    if not concept_ids:
        raise HTTPException(status_code=400, detail="concept_ids required")

    container = _get_container(request)
    vector_service = container.vector_service()
    collection_name = os.getenv(_KNOWLEDGE_COLLECTION_ENV, _DEFAULT_KNOWLEDGE_NAME)
    collection = vector_service.get_or_create_collection(collection_name)

    try:
        # Get concepts to verify ownership
        results = collection.get(
            ids=concept_ids,
            include=["metadatas"]
        )

        found_ids = results.get("ids", [])
        if len(found_ids) != len(concept_ids):
            missing = set(concept_ids) - set(found_ids)
            raise HTTPException(status_code=404, detail=f"Concepts not found: {list(missing)}")

        # Verify ownership for all
        for meta in results["metadatas"]:
            if meta.get("user_id") != user_id:
                raise HTTPException(status_code=403, detail="Access denied to one or more concepts")

        # Delete all
        collection.delete(ids=concept_ids)

        logger.info(f"[concepts/bulk-delete] Deleted {len(concept_ids)} concepts for user {user_id}")

        return {
            "status": "success",
            "deleted_count": len(concept_ids),
            "deleted_ids": concept_ids,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[concepts/bulk-delete] Failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to bulk delete concepts: {e}")


@router.post(
    "/concepts/bulk-tag",
    response_model=Dict[str, Any],
    summary="Add tags to multiple concepts at once",
    description="Bulk tagging operation for categorizing multiple concepts",
)
async def bulk_tag_concepts(
    request: Request,
    data: Dict[str, Any] = Body(...),
) -> Dict[str, Any]:
    """
    Add tags to multiple concepts in one operation.

    Body params:
    - concept_ids: List[str] - IDs of concepts to tag
    - tags: List[str] - Tags to add
    - mode: "add" | "replace" - Whether to add or replace existing tags (default: "add")
    """
    try:
        user_id = await shared_dependencies.get_user_id(request)
    except HTTPException:
        raise HTTPException(status_code=401, detail="Authentication required")

    concept_ids = data.get("concept_ids", [])
    tags = data.get("tags", [])
    mode = data.get("mode", "add")

    if not concept_ids:
        raise HTTPException(status_code=400, detail="concept_ids required")
    if not tags:
        raise HTTPException(status_code=400, detail="tags required")
    if mode not in ["add", "replace"]:
        raise HTTPException(status_code=400, detail="mode must be 'add' or 'replace'")

    container = _get_container(request)
    vector_service = container.vector_service()
    collection_name = os.getenv(_KNOWLEDGE_COLLECTION_ENV, _DEFAULT_KNOWLEDGE_NAME)
    collection = vector_service.get_or_create_collection(collection_name)

    try:
        # Get concepts
        results = collection.get(
            ids=concept_ids,
            include=["metadatas"]
        )

        found_ids = results.get("ids", [])
        if len(found_ids) != len(concept_ids):
            missing = set(concept_ids) - set(found_ids)
            raise HTTPException(status_code=404, detail=f"Concepts not found: {list(missing)}")

        # Verify ownership and update tags
        updated_metas = []
        for meta in results["metadatas"]:
            if meta.get("user_id") != user_id:
                raise HTTPException(status_code=403, detail="Access denied to one or more concepts")

            updated_meta = {**meta}
            if mode == "replace":
                updated_meta["tags"] = tags
            else:  # add
                existing_tags = set(updated_meta.get("tags", []))
                existing_tags.update(tags)
                updated_meta["tags"] = list(existing_tags)

            updated_metas.append(updated_meta)

        # Update all concepts
        collection.update(
            ids=found_ids,
            metadatas=updated_metas
        )

        logger.info(f"[concepts/bulk-tag] Tagged {len(found_ids)} concepts for user {user_id}")

        return {
            "status": "success",
            "updated_count": len(found_ids),
            "updated_ids": found_ids,
            "tags": tags,
            "mode": mode,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[concepts/bulk-tag] Failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to bulk tag concepts: {e}")


@router.get(
    "/concepts/export",
    response_model=Dict[str, Any],
    summary="Export all user concepts",
    description="Export all concepts in JSON format for backup or transfer",
)
async def export_concepts(
    request: Request,
) -> Dict[str, Any]:
    """Export all user concepts."""
    try:
        user_id = await shared_dependencies.get_user_id(request)
    except HTTPException:
        raise HTTPException(status_code=401, detail="Authentication required")

    container = _get_container(request)
    vector_service = container.vector_service()
    collection_name = os.getenv(_KNOWLEDGE_COLLECTION_ENV, _DEFAULT_KNOWLEDGE_NAME)
    collection = vector_service.get_or_create_collection(collection_name)

    try:
        # Get all user concepts
        results = collection.get(
            where={"$and": [
                {"user_id": user_id},
                {"type": "concept"}
            ]},
            include=["documents", "metadatas"]
        )

        concepts = []
        for concept_id, doc, meta in zip(results["ids"], results["documents"], results["metadatas"]):
            concepts.append({
                "id": concept_id,
                "concept_text": meta.get("concept_text") or (doc if isinstance(doc, str) else str(doc)),
                "description": meta.get("description", ""),
                "tags": meta.get("tags", []),
                "relations": meta.get("relations", []),
                "occurrence_count": int(meta.get("mention_count", 1)),
                "first_mentioned": meta.get("first_mentioned_at"),
                "last_mentioned": meta.get("last_mentioned_at"),
                "thread_ids": meta.get("thread_ids", []),
            })

        return {
            "concepts": concepts,
            "total": len(concepts),
            "exported_at": __import__("datetime").datetime.utcnow().isoformat(),
            "user_id": user_id,
        }

    except Exception as e:
        logger.error(f"[concepts/export] Failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to export concepts: {e}")


@router.post(
    "/concepts/import",
    response_model=Dict[str, Any],
    summary="Import concepts from backup",
    description="Import concepts from JSON export (merge with existing)",
)
async def import_concepts(
    request: Request,
    data: Dict[str, Any] = Body(...),
) -> Dict[str, Any]:
    """
    Import concepts from export file.

    Body params:
    - concepts: List[Dict] - Concepts to import
    - mode: "merge" | "replace" - Merge with existing or replace all (default: "merge")
    """
    try:
        user_id = await shared_dependencies.get_user_id(request)
    except HTTPException:
        raise HTTPException(status_code=401, detail="Authentication required")

    concepts = data.get("concepts", [])
    mode = data.get("mode", "merge")

    if not concepts:
        raise HTTPException(status_code=400, detail="concepts required")
    if mode not in ["merge", "replace"]:
        raise HTTPException(status_code=400, detail="mode must be 'merge' or 'replace'")

    container = _get_container(request)
    vector_service = container.vector_service()
    collection_name = os.getenv(_KNOWLEDGE_COLLECTION_ENV, _DEFAULT_KNOWLEDGE_NAME)
    collection = vector_service.get_or_create_collection(collection_name)

    try:
        imported_count = 0

        # If replace mode, delete all existing concepts
        if mode == "replace":
            existing = collection.get(
                where={"$and": [{"user_id": user_id}, {"type": "concept"}]},
                include=["metadatas"]
            )
            if existing.get("ids"):
                collection.delete(ids=existing["ids"])
                logger.info(f"[concepts/import] Deleted {len(existing['ids'])} existing concepts (replace mode)")

        # Import concepts
        for concept in concepts:
            concept_text = concept.get("concept_text")
            if not concept_text:
                continue

            # Generate new ID
            import uuid
            new_id = f"concept_{user_id}_{uuid.uuid4().hex[:8]}"

            meta = {
                "user_id": user_id,
                "type": "concept",
                "concept_text": concept_text,
                "description": concept.get("description", ""),
                "tags": concept.get("tags", []),
                "relations": concept.get("relations", []),
                "mention_count": int(concept.get("occurrence_count", 1)),
                "first_mentioned_at": concept.get("first_mentioned"),
                "last_mentioned_at": concept.get("last_mentioned"),
                "thread_ids": concept.get("thread_ids", []),
                "created_at": __import__("datetime").datetime.utcnow().isoformat(),
            }

            collection.add(
                ids=[new_id],
                documents=[concept_text],
                metadatas=[meta]
            )

            imported_count += 1

        logger.info(f"[concepts/import] Imported {imported_count} concepts for user {user_id}")

        return {
            "status": "success",
            "imported": imported_count,
            "mode": mode,
        }

    except Exception as e:
        logger.error(f"[concepts/import] Failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to import concepts: {e}")


@router.get(
    "/concepts/graph",
    response_model=Dict[str, Any],
    summary="Get concept graph data for visualization",
    description="Returns concepts and their relationships for graph visualization",
)
async def get_concepts_graph(
    request: Request,
    limit: int = Query(100, ge=1, le=500, description="Max concepts to include"),
) -> Dict[str, Any]:
    """
    Get concept graph data for visualization.

    Returns:
        {
            "concepts": [...],  # List of concepts with metadata
            "relations": [...], # List of relationships between concepts
        }
    """
    try:
        user_id = await shared_dependencies.get_user_id(request)
    except HTTPException:
        raise HTTPException(status_code=401, detail="Authentication required")

    container = _get_container(request)
    vector_service = container.vector_service()
    collection_name = os.getenv(_KNOWLEDGE_COLLECTION_ENV, _DEFAULT_KNOWLEDGE_NAME)
    collection = vector_service.get_or_create_collection(collection_name)

    try:
        # Get user's concepts
        results = collection.get(
            where={"$and": [
                {"user_id": user_id},
                {"type": "concept"}
            ]},
            include=["documents", "metadatas"],
            limit=limit
        )

        concepts_docs = results.get("documents", [])
        concepts_meta = results.get("metadatas", [])
        concepts_ids = results.get("ids", [])

        # Build concepts list
        concepts = []
        relations = []

        for concept_id, doc, meta in zip(concepts_ids, concepts_docs, concepts_meta):
            if not meta:
                continue

            concept = {
                "id": concept_id,
                "concept_id": concept_id,
                "concept_text": meta.get("concept_text") or (doc if isinstance(doc, str) else str(doc)),
                "label": meta.get("concept_text") or (doc if isinstance(doc, str) else str(doc)),
                "occurrence_count": int(meta.get("mention_count", 1)),
                "created_at": meta.get("first_mentioned_at") or meta.get("created_at"),
                "last_mentioned": meta.get("last_mentioned_at"),
                "thread_ids": meta.get("thread_ids", []),
            }
            concepts.append(concept)

            # Extract relations from metadata
            concept_relations = meta.get("relations", [])
            for rel in concept_relations:
                if isinstance(rel, dict):
                    relations.append({
                        "source": concept_id,
                        "target": rel.get("target_id"),
                        "type": rel.get("type", "related"),
                        "strength": rel.get("strength", 1.0),
                    })

        logger.info(f"[concepts/graph] Retrieved {len(concepts)} concepts and {len(relations)} relations for user {user_id}")

        return {
            "concepts": concepts,
            "relations": relations,
            "total_concepts": len(concepts),
            "total_relations": len(relations),
        }

    except Exception as e:
        logger.error(f"[concepts/graph] Failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve concept graph: {e}")


@router.post(
    "/consolidate-archived",
    response_model=Dict[str, Any],
    summary="Consolide threads archivés dans LTM (batch)",
    description="Consolide tous threads archivés non encore traités. Utile pour migration ou rattrapage batch.",
)
async def consolidate_archived_threads(
    request: Request,
    data: Dict[str, Any] = Body(default={})
) -> Dict[str, Any]:
    """
    Consolide tous les threads archivés non encore traités.
    Utile pour migration ou rattrapage batch.

    Body params:
    - user_id (optional): Limiter à un utilisateur
    - limit (optional): Nombre max threads (défaut 100)
    - force (optional): Forcer reconsolidation même si déjà fait

    Returns:
    - status: "success" | "error"
    - consolidated_count: Nombre threads consolidés
    - skipped_count: Nombre threads déjà consolidés
    - errors: Liste erreurs éventuelles
    """
    user_id = await shared_dependencies.get_user_id(request)
    container = _get_container(request)
    gardener = _get_gardener_from_request(request)

    limit = data.get("limit", 100)
    force = data.get("force", False)

    # Récupérer tous threads archivés
    db = gardener.db
    try:
        threads = await queries.get_threads(
            db,
            session_id=None,  # Tous sessions
            user_id=user_id,
            archived_only=True,
            limit=limit
        )
    except Exception as e:
        logger.error(f"[consolidate_archived] Failed to fetch archived threads: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch archived threads: {e}")

    consolidated = 0
    skipped = 0
    errors = []

    logger.info(f"[consolidate_archived] Processing {len(threads)} archived threads (force={force})")

    for thread in threads:
        thread_id = thread.get("id")
        if not thread_id:
            continue

        try:
            # Vérifier si déjà consolidé (concepts dans ChromaDB)
            if not force and await _thread_already_consolidated(container.vector_service(), thread_id):
                skipped += 1
                logger.debug(f"[consolidate_archived] Thread {thread_id} already consolidated, skipping")
                continue

            # Consolider thread
            result = await gardener._tend_single_thread(
                thread_id=thread_id,
                session_id=thread.get("session_id"),
                user_id=thread.get("user_id")
            )

            new_concepts = result.get("new_concepts", 0)
            if new_concepts > 0:
                consolidated += 1
                logger.info(f"[consolidate_archived] Thread {thread_id} consolidated: {new_concepts} concepts")
            else:
                skipped += 1
                logger.debug(f"[consolidate_archived] Thread {thread_id} produced no concepts")

        except Exception as e:
            logger.error(f"[consolidate_archived] Error consolidating thread {thread_id}: {e}", exc_info=True)
            errors.append({
                "thread_id": thread_id,
                "error": str(e)
            })

    logger.info(
        f"[consolidate_archived] Batch completed: "
        f"{consolidated} consolidated, {skipped} skipped, {len(errors)} errors"
    )

    return {
        "status": "success",
        "consolidated_count": consolidated,
        "skipped_count": skipped,
        "total_archived": len(threads),
        "errors": errors
    }
