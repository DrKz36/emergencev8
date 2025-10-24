"""
Webhook delivery service - HTTP POST with HMAC signature and retry logic
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import uuid
from datetime import datetime
from typing import Any, Optional

import httpx

from ...core.database import DatabaseManager
from .models import WebhookEventPayload

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAYS = [5, 15, 60]  # seconds: 5s, 15s, 60s
DELIVERY_TIMEOUT = 10  # seconds


class WebhookDeliveryService:
    """
    Service for delivering webhook events via HTTP POST

    Features:
    - HMAC signature for verification
    - Automatic retry (3 attempts with exponential backoff)
    - Delivery logging in database
    """

    def __init__(self, db: DatabaseManager) -> None:
        self.db = db
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=DELIVERY_TIMEOUT,
                follow_redirects=False,
            )
        return self._client

    async def close(self) -> None:
        """Close HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _generate_signature(self, payload: str, secret: str) -> str:
        """Generate HMAC SHA256 signature for webhook payload"""
        return hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

    async def deliver_event(
        self,
        event_type: str,
        user_id: str,
        payload: WebhookEventPayload
    ) -> None:
        """
        Deliver event to all subscribed webhooks for this user

        This is called asynchronously by WebhookEventDispatcher (fire and forget).
        """
        try:
            # Find all active webhooks subscribed to this event
            webhooks = await self._get_subscribed_webhooks(user_id, event_type)

            if not webhooks:
                logger.debug(f"No active webhooks for event {event_type} (user {user_id})")
                return

            logger.info(f"Delivering {event_type} to {len(webhooks)} webhook(s) for user {user_id}")

            # Deliver to each webhook
            for webhook in webhooks:
                asyncio.create_task(
                    self._deliver_to_webhook(webhook, payload)
                )

        except Exception as e:
            logger.error(f"Failed to deliver webhook event {event_type}: {e}", exc_info=True)

    async def _get_subscribed_webhooks(self, user_id: str, event_type: str) -> list[dict[str, Any]]:
        """Get all active webhooks subscribed to this event type"""
        query = """
            SELECT id, url, secret, events, total_deliveries, successful_deliveries, failed_deliveries
            FROM webhooks
            WHERE user_id = ? AND active = 1
        """
        rows = await self.db.fetch_all(query, (user_id,))

        webhooks = []
        for row in rows:
            events = json.loads(row["events"])
            if event_type in events:
                webhooks.append(dict(row))

        return webhooks

    async def _deliver_to_webhook(
        self,
        webhook: dict[str, Any],
        payload: WebhookEventPayload
    ) -> None:
        """
        Deliver payload to a single webhook with retry logic

        Retries:
        - Attempt 1: Immediate
        - Attempt 2: After 5s delay
        - Attempt 3: After 15s delay
        - Attempt 4: After 60s delay (final)
        """
        webhook_id = webhook["id"]
        url = webhook["url"]
        secret = webhook["secret"]

        # Update webhook_id in payload
        payload.webhook_id = webhook_id

        # Serialize payload
        payload_json = payload.model_dump_json()

        # Generate HMAC signature
        signature = self._generate_signature(payload_json, secret)

        # Try delivery with retries
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                # Wait before retry (except first attempt)
                if attempt > 1:
                    delay = RETRY_DELAYS[attempt - 2]
                    logger.info(f"Retrying webhook {webhook_id} in {delay}s (attempt {attempt}/{MAX_RETRIES})")
                    await asyncio.sleep(delay)

                # Attempt delivery
                client = await self._get_client()
                response = await client.post(
                    url,
                    content=payload_json,
                    headers={
                        "Content-Type": "application/json",
                        "X-Webhook-Signature": signature,
                        "X-Webhook-Event": payload.event,
                        "X-Webhook-ID": webhook_id,
                        "User-Agent": "Emergence-Webhooks/1.0"
                    }
                )

                # Log delivery
                await self._log_delivery(
                    webhook_id=webhook_id,
                    event_type=payload.event,
                    payload_json=payload_json,
                    status=response.status_code,
                    response_body=response.text[:1000],  # Truncate long responses
                    error=None,
                    attempt=attempt
                )

                # Check if successful
                if 200 <= response.status_code < 300:
                    await self._update_webhook_stats(webhook_id, success=True)
                    logger.info(f"Webhook {webhook_id} delivered successfully (status {response.status_code})")
                    return  # Success, stop retrying

                # Server error (5xx) - retry
                if response.status_code >= 500:
                    logger.warning(
                        f"Webhook {webhook_id} failed with server error {response.status_code} "
                        f"(attempt {attempt}/{MAX_RETRIES})"
                    )
                    continue  # Retry

                # Client error (4xx) - don't retry
                logger.error(f"Webhook {webhook_id} failed with client error {response.status_code} (no retry)")
                await self._update_webhook_stats(webhook_id, success=False)
                return

            except httpx.TimeoutException:
                logger.warning(f"Webhook {webhook_id} timed out (attempt {attempt}/{MAX_RETRIES})")
                await self._log_delivery(
                    webhook_id=webhook_id,
                    event_type=payload.event,
                    payload_json=payload_json,
                    status=0,
                    response_body=None,
                    error="Request timeout",
                    attempt=attempt
                )
                continue  # Retry

            except Exception as e:
                logger.error(f"Webhook {webhook_id} failed with exception: {e} (attempt {attempt}/{MAX_RETRIES})")
                await self._log_delivery(
                    webhook_id=webhook_id,
                    event_type=payload.event,
                    payload_json=payload_json,
                    status=0,
                    response_body=None,
                    error=str(e),
                    attempt=attempt
                )
                continue  # Retry

        # All retries exhausted
        await self._update_webhook_stats(webhook_id, success=False)
        logger.error(f"Webhook {webhook_id} failed after {MAX_RETRIES} attempts")

    async def _log_delivery(
        self,
        webhook_id: str,
        event_type: str,
        payload_json: str,
        status: int,
        response_body: Optional[str],
        error: Optional[str],
        attempt: int
    ) -> None:
        """Log webhook delivery attempt"""
        try:
            delivery_id = str(uuid.uuid4())
            query = """
                INSERT INTO webhook_deliveries
                (id, webhook_id, event_type, payload, status, response_body, error, attempt, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            await self.db.execute(
                query,
                (
                    delivery_id,
                    webhook_id,
                    event_type,
                    payload_json,
                    status,
                    response_body,
                    error,
                    attempt,
                    datetime.utcnow()
                ),
                commit=True
            )
        except Exception as e:
            logger.error(f"Failed to log webhook delivery: {e}")

    async def _update_webhook_stats(self, webhook_id: str, success: bool) -> None:
        """Update webhook delivery statistics"""
        try:
            if success:
                query = """
                    UPDATE webhooks
                    SET total_deliveries = total_deliveries + 1,
                        successful_deliveries = successful_deliveries + 1,
                        last_triggered_at = ?
                    WHERE id = ?
                """
            else:
                query = """
                    UPDATE webhooks
                    SET total_deliveries = total_deliveries + 1,
                        failed_deliveries = failed_deliveries + 1,
                        last_triggered_at = ?
                    WHERE id = ?
                """
            await self.db.execute(query, (datetime.utcnow(), webhook_id), commit=True)
        except Exception as e:
            logger.error(f"Failed to update webhook stats: {e}")
