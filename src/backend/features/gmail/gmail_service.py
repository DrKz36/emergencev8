"""
Gmail Service - Lecture des emails Guardian pour Codex GPT.

Architecture:
- Lecture seule (scope gmail.readonly)
- Query emails par sujet (emergence, guardian, audit)
- Parse HTML/plaintext body
- Auto-refresh tokens
"""

from typing import List, Dict, Optional
from datetime import datetime
import base64

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import logging

from backend.features.gmail.oauth_service import GmailOAuthService

logger = logging.getLogger("emergence.gmail.service")


class GmailService:
    """Service pour lire les rapports Guardian par email."""

    def __init__(self):
        self.oauth_service = GmailOAuthService()

    async def read_guardian_reports(
        self,
        max_results: int = 10,
        user_email: str = "admin"
    ) -> List[Dict]:
        """
        Lit les derniers emails Guardian depuis Gmail.

        Args:
            max_results: Nombre max d'emails à récupérer
            user_email: Email utilisateur (pour récupérer tokens)

        Returns:
            List[Dict]: Liste emails avec subject, body, timestamp, from
        """
        try:
            # Récupérer credentials OAuth
            credentials = await self.oauth_service.get_credentials(user_email)
            if not credentials:
                logger.error(f"No OAuth credentials found for {user_email}")
                return []

            # Build Gmail API service
            service = build('gmail', 'v1', credentials=credentials)

            # Query emails (sujet contient emergence, guardian, ou audit)
            query = 'subject:(emergence OR guardian OR audit)'
            results = service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()

            messages = results.get('messages', [])
            if not messages:
                logger.info("No Guardian emails found")
                return []

            # Récupérer détails de chaque email
            emails = []
            for msg in messages:
                email_data = await self._get_email_details(service, msg['id'])
                if email_data:
                    emails.append(email_data)

            logger.info(f"Retrieved {len(emails)} Guardian emails")
            return emails

        except HttpError as e:
            logger.error(f"Gmail API error: {e}")
            return []
        except Exception as e:
            logger.error(f"Error reading Guardian emails: {e}")
            return []

    async def _get_email_details(self, service, message_id: str) -> Optional[Dict]:
        """
        Récupère les détails d'un email (subject, body, timestamp, from).

        Args:
            service: Gmail API service
            message_id: ID du message

        Returns:
            Dict: Détails email ou None si erreur
        """
        try:
            msg = service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()

            # Extract headers
            headers = msg['payload']['headers']
            subject = self._get_header(headers, 'Subject')
            from_email = self._get_header(headers, 'From')
            date_str = self._get_header(headers, 'Date')

            # Extract body (HTML ou plaintext)
            body = self._get_email_body(msg['payload'])

            # Parse timestamp
            timestamp = self._parse_timestamp(msg['internalDate'])

            return {
                'id': message_id,
                'subject': subject,
                'from': from_email,
                'date': date_str,
                'timestamp': timestamp,
                'body': body,
                'snippet': msg.get('snippet', '')
            }

        except Exception as e:
            logger.error(f"Error getting email details for {message_id}: {e}")
            return None

    def _get_header(self, headers: List[Dict], name: str) -> str:
        """Récupère la valeur d'un header."""
        for header in headers:
            if header['name'].lower() == name.lower():
                return header['value']
        return ''

    def _get_email_body(self, payload: Dict) -> str:
        """
        Extrait le body d'un email (HTML ou plaintext).

        Args:
            payload: Payload du message Gmail

        Returns:
            str: Body décodé
        """
        # Si le message a des parts (multipart)
        if 'parts' in payload:
            for part in payload['parts']:
                # Préférer HTML si disponible
                if part['mimeType'] == 'text/html':
                    return self._decode_body(part['body'].get('data', ''))
                elif part['mimeType'] == 'text/plain':
                    return self._decode_body(part['body'].get('data', ''))

                # Récursif pour nested parts
                if 'parts' in part:
                    body = self._get_email_body(part)
                    if body:
                        return body

        # Si le message est simple (pas multipart)
        if 'body' in payload and 'data' in payload['body']:
            return self._decode_body(payload['body']['data'])

        return ''

    def _decode_body(self, data: str) -> str:
        """Décode le body encodé en base64url."""
        if not data:
            return ''
        try:
            decoded = base64.urlsafe_b64decode(data).decode('utf-8')
            return decoded
        except Exception as e:
            logger.error(f"Error decoding email body: {e}")
            return ''

    def _parse_timestamp(self, internal_date: str) -> str:
        """
        Parse le timestamp Gmail (millisecondes depuis epoch).

        Args:
            internal_date: Timestamp Gmail (string)

        Returns:
            str: ISO format timestamp
        """
        try:
            timestamp_ms = int(internal_date)
            dt = datetime.fromtimestamp(timestamp_ms / 1000.0)
            return dt.isoformat()
        except Exception as e:
            logger.error(f"Error parsing timestamp: {e}")
            return ''

    async def search_emails_by_subject(
        self,
        subject_keywords: str,
        max_results: int = 10,
        user_email: str = "admin"
    ) -> List[Dict]:
        """
        Recherche emails par mots-clés dans le sujet.

        Args:
            subject_keywords: Mots-clés à chercher dans le sujet
            max_results: Nombre max de résultats
            user_email: Email utilisateur

        Returns:
            List[Dict]: Liste emails trouvés
        """
        try:
            credentials = await self.oauth_service.get_credentials(user_email)
            if not credentials:
                return []

            service = build('gmail', 'v1', credentials=credentials)

            query = f'subject:{subject_keywords}'
            results = service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()

            messages = results.get('messages', [])
            emails = []
            for msg in messages:
                email_data = await self._get_email_details(service, msg['id'])
                if email_data:
                    emails.append(email_data)

            return emails

        except Exception as e:
            logger.error(f"Error searching emails: {e}")
            return []
