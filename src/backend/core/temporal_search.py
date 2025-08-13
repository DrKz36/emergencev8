# src/backend/core/temporal_search.py
# V9.1 - Amélioration de la gestion d'erreurs
import logging
from typing import List, Dict, Any

from backend.core.database_backup import DatabaseManager
from backend.shared.exceptions import TemporalSearchException

logger = logging.getLogger(__name__)

class TemporalSearch:
    """
    TEMPORAL SEARCH V9.1 - Le moteur d'exploration de la Mémoire Vive.
    Fournit une interface de haut niveau asynchrone pour interroger les sessions archivées.
    """
    def __init__(self, db_manager: DatabaseManager):
        """
        Initialise le service de recherche temporelle.

        Args:
            db_manager: L'instance du gestionnaire de base de données asynchrone.
        """
        self.db = db_manager
        logger.info("TemporalSearch V9.1 (Async) initialisé.")

    async def search_messages(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Exécute une recherche FTS asynchrone pour des messages.

        Args:
            query: La chaîne de recherche (supporte la syntaxe FTS5).
            limit: Le nombre maximum de résultats à retourner.

        Returns:
            Une liste de dictionnaires représentant les messages trouvés.
        
        Raises:
            TemporalSearchException: Si une erreur de base de données se produit.
        """
        if not query or not query.strip():
            logger.warning("Tentative de recherche avec une requête vide.")
            return []
            
        logger.info(f"Recherche temporelle asynchrone lancée avec la requête: '{query}' et une limite de {limit}.")
        
        try:
            search_results = await self.db.search_messages(query=query, limit=limit)
            logger.info(f"{len(search_results)} résultats trouvés pour la requête '{query}'.")
            return search_results
        except Exception as e:
            logger.error(f"Erreur durant la recherche asynchrone de messages: {e}", exc_info=True)
            # Propager une exception spécifique pour que la couche API puisse la gérer.
            raise TemporalSearchException(f"An error occurred in the database during search.") from e
