# src/backend/features/dashboard/service.py
# V11.0 - Refonte complète pour servir de DTO au frontend.
import logging
from typing import Dict, Any

from backend.core.database.manager import DatabaseManager
from backend.core.database import queries as db_queries
from backend.core.cost_tracker import CostTracker

logger = logging.getLogger(__name__)

class DashboardService:
    """
    Fournit les données agrégées pour le cockpit de pilotage.
    Cette version agit comme un adaptateur (DTO pattern), formatant les données
    exactement comme le frontend en a besoin.
    """
    def __init__(self, db_manager: DatabaseManager, cost_tracker: CostTracker):
        """
        Initialise le service avec le gestionnaire de BDD et le CostTracker.
        Le CostTracker est nécessaire pour récupérer les seuils d'alerte.
        """
        self.db = db_manager
        self.cost_tracker = cost_tracker
        logger.info("DashboardService V11.0 (DTO Refactor) initialisé.")

    async def get_dashboard_data(self) -> Dict[str, Any]:
        """
        Récupère, agrège et formate toutes les données pour le cockpit.
        La structure de l'objet retourné correspond exactement à ce que
        le composant dashboard-ui.js attend.
        """
        try:
            # 1. Récupération des données brutes depuis la base de données
            costs_raw = await db_queries.get_costs_summary(self.db)
            documents_raw = await db_queries.get_all_documents(self.db)
            sessions_raw = await db_queries.get_all_sessions_overview(self.db)
            # La requête get_monitoring_summary n'est pas utilisée car nous
            # préférons des chiffres plus fiables basés sur les tables principales.

            # 2. Transformation et formatage des données pour le frontend
            
            # Formatage des coûts pour correspondre aux attentes de l'UI
            costs_formatted = {
                "total_cost": costs_raw.get("total", 0.0),
                "today_cost": costs_raw.get("today", 0.0),
                "current_week_cost": costs_raw.get("this_week", 0.0),
                "current_month_cost": costs_raw.get("this_month", 0.0),
            }

            # Formatage des données de monitoring
            monitoring_formatted = {
                "total_documents": len(documents_raw),
                "total_sessions": len(sessions_raw),
            }

            # Récupération des seuils depuis l'instance de CostTracker
            thresholds_formatted = {
                "daily_threshold": self.cost_tracker.DAILY_LIMIT,
                "weekly_threshold": self.cost_tracker.WEEKLY_LIMIT,
                "monthly_threshold": self.cost_tracker.MONTHLY_LIMIT,
            }

            # 3. Assemblage du payload final
            return {
                "costs": costs_formatted,
                "monitoring": monitoring_formatted,
                "thresholds": thresholds_formatted,
                 # On garde ces données pour une éventuelle vue détaillée future
                "raw_data": {
                    "documents": documents_raw,
                    "sessions": sessions_raw
                }
            }
            
        except Exception as e:
            logger.error(f"Erreur critique lors de la récupération et du formatage des données du dashboard: {e}", exc_info=True)
            # En cas d'erreur, retourner une structure vide mais valide pour éviter un crash du frontend
            return {
                "costs": {"total_cost": 0, "today_cost": 0, "current_week_cost": 0, "current_month_cost": 0},
                "monitoring": {"total_documents": 0, "total_sessions": 0},
                "thresholds": {"daily_threshold": 1, "weekly_threshold": 1, "monthly_threshold": 1},
                "raw_data": {"documents": [], "sessions": []}
            }
