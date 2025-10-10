"""API endpoints pour la synchronisation automatique."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, Request

from ...shared.dependencies import get_user_id
from .auto_sync_service import get_auto_sync_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sync", tags=["sync"])


@router.get("/status")
async def get_sync_status(
    request: Request,
    _user_id: str = Depends(get_user_id),
) -> dict[str, Any]:
    """
    Retourne le statut actuel de la synchronisation automatique.

    Retourne :
    - running : Service actif ou non
    - pending_changes : Nombre de changements en attente
    - last_consolidation : Date/heure de la dernière consolidation
    - watched_files : Nombre de fichiers surveillés
    - checksums_tracked : Nombre de checksums trackés
    - consolidation_threshold : Seuil de déclenchement
    - check_interval_seconds : Intervalle de vérification
    """
    service = get_auto_sync_service()
    return service.get_status()


@router.post("/consolidate")
async def trigger_consolidation(
    request: Request,
    _user_id: str = Depends(get_user_id),
) -> dict[str, Any]:
    """
    Déclenche manuellement une consolidation.

    Force la consolidation de tous les changements en attente,
    même si le seuil n'est pas atteint.

    Retourne :
    - status : Résultat de l'opération
    - trigger : Détails du déclencheur
    - changes_consolidated : Nombre de changements consolidés
    """
    service = get_auto_sync_service()
    result = await service.trigger_manual_consolidation()

    logger.info(
        "Manual consolidation triggered by user %s: %d changes consolidated",
        _user_id,
        result.get("changes_consolidated", 0),
    )

    return result


@router.get("/pending-changes")
async def get_pending_changes(
    request: Request,
    _user_id: str = Depends(get_user_id),
) -> dict[str, Any]:
    """
    Retourne la liste des changements en attente de consolidation.

    Retourne :
    - count : Nombre de changements
    - changes : Liste des événements SyncEvent
    """
    service = get_auto_sync_service()

    changes = [
        {
            "file_path": event.file_path,
            "event_type": event.event_type,
            "timestamp": event.timestamp.isoformat(),
            "old_checksum": event.old_checksum,
            "new_checksum": event.new_checksum,
            "agent_owner": event.agent_owner,
        }
        for event in service.pending_changes
    ]

    return {"count": len(changes), "changes": changes}


@router.get("/checksums")
async def get_checksums(
    request: Request,
    _user_id: str = Depends(get_user_id),
) -> dict[str, Any]:
    """
    Retourne les checksums de tous les fichiers surveillés.

    Retourne :
    - count : Nombre de checksums trackés
    - checksums : Dict {file_path: checksum_info}
    """
    service = get_auto_sync_service()

    checksums = {
        path: {
            "checksum": cs.checksum,
            "last_modified": cs.last_modified.isoformat(),
            "agent_owner": cs.agent_owner,
        }
        for path, cs in service.checksums.items()
    }

    return {"count": len(checksums), "checksums": checksums}
