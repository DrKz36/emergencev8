# src/backend/api.py
# V1.2 – Allowlist: dépendance appliquée aux sous-routeurs, /api/health public
from fastapi import APIRouter, Depends

from backend.shared.dependencies import enforce_allowlist

# Import des routeurs de chaque feature (ARBO-LOCK)
from backend.features.chat.router import router as chat_router
from backend.features.documents.router import router as documents_router
from backend.features.memory.router import router as memory_router
from backend.features.voice.router import router as voice_router
from backend.features.dashboard.router import router as dashboard_router

# Préfixe "/api" est posé dans main.py ; ici, on applique juste la dépendance d'allowlist
api_router = APIRouter()

# Sous-routeurs protégés par allowlist
api_router.include_router(chat_router,     prefix="/chat",     tags=["Chat"],      dependencies=[Depends(enforce_allowlist)])
api_router.include_router(documents_router,prefix="/documents",tags=["Documents"], dependencies=[Depends(enforce_allowlist)])
api_router.include_router(memory_router,   prefix="/memory",   tags=["Memory"],    dependencies=[Depends(enforce_allowlist)])
api_router.include_router(voice_router,    prefix="/voice",    tags=["Voice"],     dependencies=[Depends(enforce_allowlist)])
api_router.include_router(dashboard_router,prefix="/dashboard",tags=["Dashboard"], dependencies=[Depends(enforce_allowlist)])

# /api/health reste accessible publiquement (utilisé par Cloud Run)
@api_router.get("/health", tags=["System"])
async def health_check():
    return {"status": "ok"}
