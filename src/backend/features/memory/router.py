# src/backend/features/memory/router.py
# V2.4 — Hotfix prod:
#   - Retire le prefix local (laisse main.py monter /api/memory) → supprime le double préfixe en prod
#   - Ajoute GET alias pour /tend-garden (compat front GET/POST)
#   - Contrats REST sinon inchangés (clear: DELETE & POST)

import os
import logging
from typing import Dict, Any, Optional, Tuple, List

from fastapi import APIRouter, HTTPException, Request, Body, Query

from backend.features.memory.gardener import MemoryGardener

# ❗️Pas de prefix ici : main.py inclut ce router avec prefix="/api/memory"
router = APIRouter(tags=["Memory & Knowledge"])
logger = logging.getLogger(__name__)

_KNOWLEDGE_COLLECTION_ENV = "EMERGENCE_KNOWLEDGE_COLLECTION"
_DEFAULT_KNOWLEDGE_NAME = "emergence_knowledge"


# ---------- Helpers DI ----------
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
    """
    Priorité au paramètre, puis aux headers X-Session-Id (casse tolérée).
    """
    if explicit_session_id and str(explicit_session_id).strip():
        return str(explicit_session_id).strip()
    for key in ("X-Session-Id", "x-session-id", "X-Session-ID"):
        sid = request.headers.get(key)
        if sid and str(sid).strip():
            return str(sid).strip()
    raise HTTPException(status_code=400, detail="Session ID manquant (header 'X-Session-Id' ou paramètre 'session_id').")


def _try_get_user_id_for_session(container, session_id: str) -> Optional[str]:
    """
    Récupère l'user_id depuis SessionManager, en essayant les méthodes connues (tolérant aux variantes).
    """
    try:
        sm = container.session_manager()
    except Exception:
        return None
    for name in ("get_user_id_for_session", "get_user", "get_owner", "get_session_owner"):
        fn = getattr(sm, name, None)
        try:
            if callable(fn):
                uid = fn(session_id)
                if uid:
                    return str(uid)
        except Exception:
            pass
    for name in ("current_user_id", "user_id"):
        try:
            val = getattr(sm, name, None)
            if val:
                return str(val)
        except Exception:
            pass
    return None


async def _purge_stm(db_manager, session_id: str) -> bool:
    """
    Efface le résumé et les entités extraites (STM) pour la session indiquée.
    """
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
    """
    Collection.get(...) renvoie 'ids' (liste plate ou liste de listes selon versions Chroma).
    """
    ids = got.get("ids") or []
    if not isinstance(ids, list):
        return 0
    if ids and isinstance(ids[0], list):
        return sum(len(x or []) for x in ids)
    return len(ids)


def _build_where_filter(session_id: Optional[str], agent_id: Optional[str], user_id: Optional[str]) -> Dict[str, Any]:
    """
    Construit un filtre 'where' robuste pour la suppression LTM.
    - 1 clause  -> dict simple
    - >=2       -> {"$and": [ ... ]}
    """
    clauses: List[Dict[str, Any]] = []
    if session_id:
        clauses.append({"source_session_id": session_id})
    if agent_id:
        clauses.append({"agent": agent_id})
    if user_id:
        clauses.append({"user_id": user_id})

    if not clauses:
        raise HTTPException(status_code=400, detail="Aucun critère de purge LTM déterminé.")
    if len(clauses) == 1:
        return clauses[0]
    return {"$and": clauses}


def _purge_ltm(vector_service, where_filter: Dict[str, Any]) -> Tuple[int, int]:
    """
    Purge LTM :
      - get(where=...) SANS include=["ids"] (non supporté) pour compter les IDs
      - suppression via VectorService.delete_vectors(...) (normalisation where + logs)
      - recomptage post-suppression
    """
    try:
        collection_name = os.getenv(_KNOWLEDGE_COLLECTION_ENV, _DEFAULT_KNOWLEDGE_NAME)
        col = vector_service.get_or_create_collection(collection_name)

        got_before = col.get(where=where_filter)  # ← retour par défaut contient 'ids'
        n_before = _count_ids_from_get_result(got_before)

        try:
            vector_service.delete_vectors(col, where_filter)
        except Exception as de:
            logger.warning(f"[memory.clear] delete_vectors(...) a levé: {de}")
            # fallback direct (dernier recours)
            try:
                col.delete(where=where_filter)
            except Exception as de2:
                logger.warning(f"[memory.clear] fallback col.delete(where=...) a levé: {de2}")

        got_after = col.get(where=where_filter)
        n_after = _count_ids_from_get_result(got_after)

        return n_before, max(0, n_before - n_after)
    except Exception as e:
        logger.error(f"[memory.clear] purge LTM erreur: {e}", exc_info=True)
        return 0, 0


# ---------- Endpoints ----------
@router.post(
    "/tend-garden",
    response_model=Dict[str, Any],
    summary="Déclenche la consolidation de la mémoire (gardener).",
    description="Lance manuellement le 'MemoryGardener' pour analyser/consolider les sessions récentes."
)
async def tend_garden_endpoint(request: Request) -> Dict[str, Any]:
    logger.info("Requête reçue sur /api/memory/tend-garden.")
    try:
        gardener = _get_gardener_from_request(request)
        report = await gardener.tend_the_garden()
        if report.get("status") == "error":
            raise HTTPException(status_code=500, detail=report.get("message", "Erreur interne"))
        return report
    except HTTPException:
        raise
    except Exception as e:
        logger.critical(f"Erreur non gérée dans tend_garden: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erreur interne critique.")


# Alias GET (compat) → même logique que POST
@router.get(
    "/tend-garden",
    response_model=Dict[str, Any],
    summary="(Alias) Déclenche la consolidation de la mémoire (gardener).",
    description="Alias GET pour compatibilité UI (équivalent au POST)."
)
async def tend_garden_get(request: Request) -> Dict[str, Any]:
    return await tend_garden_endpoint(request)


async def _handle_clear(request: Request, session_id: Optional[str], agent_id: Optional[str]) -> Dict[str, Any]:
    """
    Handler commun DELETE/POST /clear : purge STM + LTM
    - session_id : query|body|header X-Session-Id
    - agent_id   : optionnel, normalisé en lower()
    """
    container = _get_container(request)
    sid = _resolve_session_id(request, session_id)
    uid = _try_get_user_id_for_session(container, sid)
    ag = (agent_id or "").strip().lower() or None

    # Purge STM
    stm_ok = await _purge_stm(container.db_manager(), sid)

    # Purge LTM (where robuste)
    where_filter = _build_where_filter(sid, ag, uid)
    n_before, n_deleted = _purge_ltm(container.vector_service(), where_filter)

    payload = {
        "status": "success",
        "cleared": {
            "session_id": sid,
            "agent_id": ag,
            "stm": bool(stm_ok),
            "ltm_before": int(n_before),
            "ltm_deleted": int(n_deleted),
        }
    }
    logger.info(f"[memory.clear] {payload}")
    return payload


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
    return await _handle_clear(request, session_id, agent_id)


@router.post(
    "/clear",
    response_model=Dict[str, Any],
    summary="Efface la mémoire de la session (STM+LTM) — compat POST.",
    description="Équivalent DELETE avec body JSON."
)
async def clear_memory_post(
    request: Request,
    data: Dict[str, Any] = Body(default={})
) -> Dict[str, Any]:
    session_id = (data or {}).get("session_id")
    agent_id = (data or {}).get("agent_id")
    return await _handle_clear(request, session_id, agent_id)
