# src/backend/features/dashboard/router.py
# V3.0 - FIX: Added the '/api/dashboard' prefix to align with frontend calls.
import logging
from fastapi import APIRouter, Depends
from typing import Dict, Any

from backend.features.dashboard.service import DashboardService
from backend.shared.dependencies import get_dashboard_service

# --- CORRECTION : Ajout du préfixe d'API ---
router = APIRouter(prefix="/api/dashboard")
logger = logging.getLogger(__name__)

@router.get(
    "/costs/summary",
    response_model=Dict[str, Any],
    tags=["Dashboard"],
    summary="Récupère le résumé complet des données du cockpit",
    description="Fournit un résumé des coûts, des métriques de monitoring et les seuils d'alerte."
)
async def get_dashboard_summary(
    dashboard_service: DashboardService = Depends(get_dashboard_service)
) -> Dict[str, Any]:
    """
    Endpoint V9.1 pour récupérer toutes les données du cockpit.
    L'URL est maintenant correctement préfixée par /api/dashboard.
    """
    logger.info("Récupération du résumé des données pour le dashboard...")
    
    summary_data = await dashboard_service.get_dashboard_data()
    
    logger.info("Résumé des données du cockpit envoyé.")
    return summary_data
