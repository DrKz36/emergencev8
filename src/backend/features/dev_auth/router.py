# src/backend/features/dev_auth/router.py
# Sert /dev-auth.html (outil de connexion locale). ARBO-LOCK: chemins stricts, aucune dérive.

from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

router = APIRouter()

# __file__ = src/backend/features/dev_auth/router.py
# parents[0]=…/dev_auth, [1]=…/features, [2]=…/backend, [3]=…/src  ← c’est celui qu’on veut
SRC_DIR = Path(__file__).resolve().parents[3]
DEV_AUTH_HTML = SRC_DIR / "frontend" / "dev-auth.html"


@router.get("/dev-auth.html", response_class=HTMLResponse)
def get_dev_auth_html() -> HTMLResponse:
    """
    Sert la page de debug pour récupérer un JWT local via email/mot de passe.
    """
    try:
        if DEV_AUTH_HTML.exists():
            html = DEV_AUTH_HTML.read_text(encoding="utf-8")
            return HTMLResponse(html)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Erreur lecture dev-auth.html: {e}"
        )

    # Fallback visible si le fichier statique manque (évite 404 silencieux)
    fallback = """
<!doctype html>
<meta charset="utf-8">
<title>dev-auth fallback</title>
<h1>/dev-auth.html indisponible</h1>
<p>Le fichier <code>src/frontend/dev-auth.html</code> est manquant OU le chemin de résolution est incorrect.</p>
<p>Vérifie le build context Docker (.dockerignore) et la présence du fichier dans l'image.</p>
"""
    return HTMLResponse(fallback, status_code=200)


# Mini diagnostic pour confirmer le chemin résolu dans le conteneur
@router.get("/api/_dev-auth-diag")
def dev_auth_diag():
    return JSONResponse(
        {
            "resolved_src_dir": str(SRC_DIR),
            "dev_auth_html_path": str(DEV_AUTH_HTML),
            "exists": DEV_AUTH_HTML.exists(),
        }
    )
