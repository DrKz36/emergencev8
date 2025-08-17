# src/backend/features/dev_auth/router.py
# ---------------------------------------------------------
# Sert le fichier frontend "src/frontend/dev-auth.html"
# via l'URL publique GET /dev-auth.html
#
# Usage:
#   - Inclure ce router dans ton app FastAPI:
#       from backend.features.dev_auth.router import router as dev_auth_router
#       app.include_router(dev_auth_router, include_in_schema=False)
#
# Notes ARBO:
#   - Le chemin vers "src/frontend/dev-auth.html" est résolu
#     relativement à ce fichier pour éviter les soucis de CWD.
# ---------------------------------------------------------

from __future__ import annotations

from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter()

def _resolve_dev_auth_html() -> Path:
    # Ce fichier est …/src/backend/features/dev_auth/router.py
    # On remonte jusqu'à …/src puis on pointe sur frontend/dev-auth.html
    here = Path(__file__).resolve()
    src_dir = here.parents[3]  # …/src
    dev_auth = src_dir / "frontend" / "dev-auth.html"
    return dev_auth

@router.get("/dev-auth.html", include_in_schema=False)
def serve_dev_auth_html():
    dev_auth = _resolve_dev_auth_html()
    if not dev_auth.exists():
        # 404 explicite si le fichier n'est pas présent dans l'image
        raise HTTPException(status_code=404, detail="dev-auth.html not found in build image.")
    # FileResponse se charge des bons en-têtes (text/html; charset=utf-8)
    return FileResponse(dev_auth, media_type="text/html")
