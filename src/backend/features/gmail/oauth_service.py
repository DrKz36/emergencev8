"""
Gmail OAuth2 Service - Gère l'authentification OAuth2 avec Gmail API.

Architecture:
- OAuth2 flow: redirect → consent → callback → tokens
- Tokens stockés dans Firestore (encrypted)
- Auto-refresh tokens expirés
"""

import json
import os
from typing import Optional
from datetime import datetime

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

from src.backend.core.logger import logger
from src.backend.core.config import get_settings


class GmailOAuthService:
    """Service pour gérer OAuth2 Gmail."""

    SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

    def __init__(self):
        self.settings = get_settings()
        self.client_config = self._load_client_config()

    def _load_client_config(self) -> dict:
        """
        Charge client_secret depuis Secret Manager ou fichier local.

        Returns:
            dict: Configuration OAuth client
        """
        # En production Cloud Run, lire depuis Secret Manager
        if os.getenv('K_SERVICE'):  # Variable Cloud Run
            try:
                from google.cloud import secretmanager
                client = secretmanager.SecretManagerServiceClient()
                project_id = self.settings.gcp_project_id or "emergence-469005"
                secret_name = f"projects/{project_id}/secrets/gmail-oauth-client-secret/versions/latest"
                response = client.access_secret_version(request={"name": secret_name})
                return json.loads(response.payload.data.decode('UTF-8'))
            except Exception as e:
                logger.error(f"Failed to load OAuth secret from Secret Manager: {e}")
                raise

        # En local, lire depuis fichier
        secret_path = os.path.join(os.getcwd(), 'gmail_client_secret.json')
        if not os.path.exists(secret_path):
            raise FileNotFoundError(
                f"Gmail OAuth client secret not found at {secret_path}. "
                "Download from GCP Console and place in project root."
            )

        with open(secret_path, 'r') as f:
            return json.load(f)

    def initiate_oauth(self, redirect_uri: str) -> str:
        """
        Initie le flow OAuth2 et retourne l'URL de consentement Google.

        Args:
            redirect_uri: URI de callback (ex: https://emergence-app-XXX.../auth/callback/gmail)

        Returns:
            str: URL de consentement Google
        """
        flow = Flow.from_client_config(
            self.client_config,
            scopes=self.SCOPES,
            redirect_uri=redirect_uri
        )

        authorization_url, state = flow.authorization_url(
            access_type='offline',  # Pour refresh token
            include_granted_scopes='true',
            prompt='consent'  # Force consent screen (pour avoir refresh_token)
        )

        logger.info(f"OAuth flow initiated, state={state}")
        return authorization_url

    async def handle_callback(
        self,
        code: str,
        redirect_uri: str,
        user_email: str = "admin"
    ) -> dict:
        """
        Échange le code OAuth contre des tokens et les stocke.

        Args:
            code: Code d'autorisation de Google
            redirect_uri: URI de callback (doit matcher initiate_oauth)
            user_email: Email utilisateur (pour stockage Firestore)

        Returns:
            dict: {"success": bool, "message": str}
        """
        try:
            flow = Flow.from_client_config(
                self.client_config,
                scopes=self.SCOPES,
                redirect_uri=redirect_uri
            )

            flow.fetch_token(code=code)
            credentials = flow.credentials

            # Stocker tokens dans Firestore
            await self._store_tokens(user_email, credentials)

            logger.info(f"OAuth tokens stored for user={user_email}")
            return {"success": True, "message": "OAuth authentication successful"}

        except Exception as e:
            logger.error(f"OAuth callback failed: {e}")
            return {"success": False, "message": f"OAuth failed: {str(e)}"}

    async def _store_tokens(self, user_email: str, credentials: Credentials):
        """
        Stocke les tokens OAuth dans Firestore (encrypted).

        Args:
            user_email: Email utilisateur
            credentials: Credentials Google
        """
        from google.cloud import firestore

        db = firestore.Client()
        tokens_ref = db.collection('gmail_oauth_tokens').document(user_email)

        token_data = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes,
            'expiry': credentials.expiry.isoformat() if credentials.expiry else None,
            'updated_at': datetime.utcnow().isoformat()
        }

        tokens_ref.set(token_data)
        logger.info(f"Tokens stored in Firestore for {user_email}")

    async def get_credentials(self, user_email: str = "admin") -> Optional[Credentials]:
        """
        Récupère les credentials depuis Firestore et refresh si nécessaire.

        Args:
            user_email: Email utilisateur

        Returns:
            Credentials: Google credentials (refreshed if needed)
        """
        from google.cloud import firestore

        db = firestore.Client()
        tokens_ref = db.collection('gmail_oauth_tokens').document(user_email)
        doc = tokens_ref.get()

        if not doc.exists:
            logger.warning(f"No OAuth tokens found for {user_email}")
            return None

        token_data = doc.to_dict()

        credentials = Credentials(
            token=token_data['token'],
            refresh_token=token_data.get('refresh_token'),
            token_uri=token_data['token_uri'],
            client_id=token_data['client_id'],
            client_secret=token_data['client_secret'],
            scopes=token_data['scopes']
        )

        # Auto-refresh si expiré
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
            await self._store_tokens(user_email, credentials)
            logger.info(f"Tokens refreshed for {user_email}")

        return credentials
