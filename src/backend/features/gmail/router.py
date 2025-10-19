"""
Gmail API Router - Endpoints OAuth2 + Codex API.

Endpoints:
- GET /auth/gmail - Initie OAuth flow
- GET /auth/callback/gmail - Callback OAuth
- POST /api/gmail/read-reports - API Codex (lecture rapports)
"""

import os
from typing import Optional

from fastapi import APIRouter, Request, Header, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
import logging

from backend.features.gmail.oauth_service import GmailOAuthService
from backend.features.gmail.gmail_service import GmailService

logger = logging.getLogger("emergence.gmail.router")


router = APIRouter()

gmail_oauth_service = GmailOAuthService()
gmail_service = GmailService()


@router.get("/auth/gmail")
async def gmail_auth_init(request: Request):
    """
    Initie le flow OAuth2 Gmail.

    Redirige l'utilisateur vers le consent screen Google.

    Returns:
        RedirectResponse: Redirect vers Google OAuth
    """
    try:
        # Build redirect URI dynamique (prod ou local)
        base_url = str(request.base_url).rstrip('/')
        redirect_uri = f"{base_url}/auth/callback/gmail"

        # Générer URL de consentement Google
        authorization_url = gmail_oauth_service.initiate_oauth(redirect_uri)

        logger.info(f"Redirecting to Google OAuth: {authorization_url}")
        return RedirectResponse(url=authorization_url)

    except Exception as e:
        logger.error(f"Failed to initiate OAuth: {e}")
        raise HTTPException(status_code=500, detail=f"OAuth init failed: {str(e)}")


@router.get("/auth/callback/gmail")
async def gmail_auth_callback(
    request: Request,
    code: Optional[str] = None,
    error: Optional[str] = None
):
    """
    Callback OAuth2 Gmail après consentement utilisateur.

    Args:
        code: Code d'autorisation de Google
        error: Erreur de Google (si l'utilisateur refuse)

    Returns:
        JSONResponse: Résultat OAuth
    """
    if error:
        logger.warning(f"OAuth callback error: {error}")
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": f"OAuth error: {error}"}
        )

    if not code:
        logger.error("No authorization code in callback")
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": "No authorization code provided"}
        )

    try:
        # Build redirect URI (doit matcher initiate_oauth)
        base_url = str(request.base_url).rstrip('/')
        redirect_uri = f"{base_url}/auth/callback/gmail"

        # Échanger code contre tokens
        result = await gmail_oauth_service.handle_callback(
            code=code,
            redirect_uri=redirect_uri,
            user_email="admin"  # Admin par défaut (pas d'auth multi-user)
        )

        if result['success']:
            logger.info("OAuth callback successful")
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "message": "Gmail OAuth authentication successful! You can now use the Gmail API.",
                    "next_step": "Codex can now call POST /api/gmail/read-reports with API key"
                }
            )
        else:
            return JSONResponse(
                status_code=400,
                content=result
            )

    except Exception as e:
        logger.error(f"OAuth callback failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"OAuth callback failed: {str(e)}"}
        )


@router.post("/api/gmail/read-reports")
async def read_gmail_reports(
    x_codex_api_key: str = Header(..., alias="X-Codex-API-Key"),
    max_results: int = 10
):
    """
    API Codex - Lit les rapports Guardian par email.

    Authentification: Header X-Codex-API-Key

    Args:
        x_codex_api_key: API key Codex (depuis Secret Manager)
        max_results: Nombre max d'emails à récupérer

    Returns:
        JSONResponse: Liste emails Guardian
    """
    try:
        # Vérifier API key Codex
        expected_api_key = os.getenv('CODEX_API_KEY')
        if not expected_api_key:
            logger.error("CODEX_API_KEY not configured in environment")
            raise HTTPException(
                status_code=500,
                detail="Codex API key not configured on server"
            )

        if x_codex_api_key != expected_api_key:
            logger.warning(f"Invalid Codex API key: {x_codex_api_key[:10]}...")
            raise HTTPException(
                status_code=401,
                detail="Invalid Codex API key"
            )

        # Lire emails Guardian
        emails = await gmail_service.read_guardian_reports(
            max_results=max_results,
            user_email="admin"
        )

        logger.info(f"Codex API: returned {len(emails)} Guardian emails")

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "count": len(emails),
                "emails": emails
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reading Gmail reports for Codex: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to read Gmail reports: {str(e)}"
        )


@router.get("/api/gmail/status")
async def gmail_oauth_status():
    """
    Vérifie le status de l'OAuth Gmail (tokens valides ou non).

    Returns:
        JSONResponse: Status OAuth
    """
    try:
        credentials = await gmail_oauth_service.get_credentials("admin")

        if not credentials:
            return JSONResponse(
                status_code=200,
                content={
                    "authenticated": False,
                    "message": "No OAuth tokens found. Please authenticate via /auth/gmail"
                }
            )

        return JSONResponse(
            status_code=200,
            content={
                "authenticated": True,
                "message": "Gmail OAuth is configured and tokens are valid",
                "scopes": credentials.scopes
            }
        )

    except Exception as e:
        logger.error(f"Error checking OAuth status: {e}")
        return JSONResponse(
            status_code=500,
            content={"authenticated": False, "error": str(e)}
        )
