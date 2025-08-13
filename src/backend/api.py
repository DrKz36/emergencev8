# src/backend/api.py
# V1.1 - FIX: Renommage en 'api_router' et suppression du préfixe pour compatibilité avec main.py

from fastapi import APIRouter

# Import des routeurs de chaque feature
from backend.features.chat.router import router as chat_router
from backend.features.documents.router import router as documents_router
from backend.features.memory.router import router as memory_router
from backend.features.voice.router import router as voice_router
from backend.features.dashboard.router import router as dashboard_router
# Note: Le service "debate" n'a pas de routeur HTTP, il fonctionne via WebSocket.

# ✅ CORRECTION APPLIQUÉE ICI : Renommage et suppression du préfixe
# Le préfixe "/api" est géré dans main.py pour plus de clarté.
api_router = APIRouter()

# Inclusion de tous les sous-routeurs
api_router.include_router(chat_router, prefix="/chat", tags=["Chat"])
api_router.include_router(documents_router, prefix="/documents", tags=["Documents"])
api_router.include_router(memory_router, prefix="/memory", tags=["Memory"])
api_router.include_router(voice_router, prefix="/voice", tags=["Voice"])
api_router.include_router(dashboard_router, prefix="/dashboard", tags=["Dashboard"])

@api_router.get("/health", tags=["System"])
async def health_check():
    """
    Endpoint simple pour vérifier que l'API est en ligne.
    """
    return {"status": "ok"}
