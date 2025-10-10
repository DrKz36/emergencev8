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
        prefs_results = collection.get(
            where={"$and": [
                {"user_id": user_id},
                {"type": {"$in": ["preference", "intent", "constraint"]}}
            ]},
            include=["documents", "metadatas"]
        )

        prefs_docs = prefs_results.get("documents", [])
        prefs_meta = prefs_results.get("metadatas", [])

        # Parse preferences
        for doc, meta in zip(prefs_docs, prefs_meta):
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

        # Parse concepts
        for doc, meta in zip(concepts_docs, concepts_meta):
            concepts.append({
                "concept": meta.get("concept_text") or (doc if isinstance(doc, str) else str(doc)),
                "mentions": int(meta.get("mention_count", 1)),
                "last_mentioned": meta.get("last_mentioned_at") or meta.get("created_at")
            })

        # Sort by mentions (descending)
        concepts.sort(key=lambda x: x["mentions"], reverse=True)

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
