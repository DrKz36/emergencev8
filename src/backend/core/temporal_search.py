# src/backend/core/temporal_search.py
# V9.2 - Import corrigé + appel DatabaseManager.search_messages()
import logging
from typing import List, Dict, Any

from backend.core.database.manager import DatabaseManager
from backend.shared.exceptions import TemporalSearchException

logger = logging.getLogger(__name__)


class TemporalSearch:
    """
    TEMPORAL SEARCH V9.2 - Moteur d'exploration de la Mémoire Vive.
    Fournit une interface async pour interroger les messages archivés.
    """

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        logger.info("TemporalSearch V9.2 (Async) initialisé.")

    async def search_messages(
        self, query: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        if not query or not str(query).strip():
            logger.warning("Tentative de recherche avec une requête vide.")
            return []
        logger.info(f"Recherche temporelle asynchrone: '{query}' (limit={limit})")
        try:
            results = await self.db.search_messages(query=query, limit=limit)
            logger.info(f"{len(results)} résultats trouvés pour '{query}'.")
            return results
        except Exception as e:
            logger.error(f"Erreur durant la recherche: {e}", exc_info=True)
            raise TemporalSearchException(
                "An error occurred in the database during search."
            ) from e
