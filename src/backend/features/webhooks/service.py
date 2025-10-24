"""
Webhooks service - CRUD operations for webhook subscriptions
"""
from __future__ import annotations

import json
import logging
import secrets
import uuid
from datetime import datetime
from typing import Any

from ...core.database import DatabaseManager
from .models import (
    WebhookCreatePayload,
    WebhookDeliveryListResponse,
    WebhookDeliveryResponse,
    WebhookListResponse,
    WebhookResponse,
    WebhookStatsResponse,
    WebhookUpdatePayload,
)

logger = logging.getLogger(__name__)


class WebhookService:
    """
    Service for managing webhook subscriptions

    Features:
    - Create, read, update, delete webhooks
    - List webhooks per user
    - Get webhook delivery logs
    - Get webhook statistics
    """

    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    async def create_webhook(
        self,
        user_id: str,
        payload: WebhookCreatePayload
    ) -> WebhookResponse:
        """Create a new webhook subscription"""
        webhook_id = str(uuid.uuid4())
        secret = self._generate_secret()
        now = datetime.utcnow()

        events_json = json.dumps([str(event) for event in payload.events])

        query = """
            INSERT INTO webhooks
            (id, user_id, url, secret, events, active, description, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        await self.db.execute(
            query,
            (
                webhook_id,
                user_id,
                str(payload.url),
                secret,
                events_json,
                payload.active,
                payload.description,
                now,
                now
            ),
            commit=True
        )

        logger.info(f"Created webhook {webhook_id} for user {user_id}")

        # Return created webhook
        return await self.get_webhook(webhook_id, user_id)

    async def get_webhook(self, webhook_id: str, user_id: str) -> WebhookResponse:
        """Get a single webhook by ID"""
        query = """
            SELECT *
            FROM webhooks
            WHERE id = ? AND user_id = ?
        """
        row = await self.db.fetch_one(query, (webhook_id, user_id))

        if not row:
            raise ValueError(f"Webhook {webhook_id} not found")

        return self._webhook_from_row(row)

    async def list_webhooks(self, user_id: str) -> WebhookListResponse:
        """List all webhooks for a user"""
        query = """
            SELECT *
            FROM webhooks
            WHERE user_id = ?
            ORDER BY created_at DESC
        """
        rows = await self.db.fetch_all(query, (user_id,))

        webhooks = [self._webhook_from_row(row) for row in rows]

        return WebhookListResponse(
            items=webhooks,
            total=len(webhooks)
        )

    async def update_webhook(
        self,
        webhook_id: str,
        user_id: str,
        payload: WebhookUpdatePayload
    ) -> WebhookResponse:
        """Update an existing webhook"""
        # Check webhook exists
        await self.get_webhook(webhook_id, user_id)

        # Build update query dynamically
        updates: list[str] = []
        params: list[Any] = []

        if payload.url is not None:
            updates.append("url = ?")
            params.append(str(payload.url))

        if payload.events is not None:
            updates.append("events = ?")
            params.append(json.dumps([str(event) for event in payload.events]))

        if payload.description is not None:
            updates.append("description = ?")
            params.append(payload.description)

        if payload.active is not None:
            updates.append("active = ?")
            params.append(payload.active)

        if not updates:
            # No updates, return current webhook
            return await self.get_webhook(webhook_id, user_id)

        updates.append("updated_at = ?")
        params.append(datetime.utcnow())

        params.extend([webhook_id, user_id])

        query = f"""
            UPDATE webhooks
            SET {', '.join(updates)}
            WHERE id = ? AND user_id = ?
        """
        await self.db.execute(query, tuple(params), commit=True)

        logger.info(f"Updated webhook {webhook_id}")

        return await self.get_webhook(webhook_id, user_id)

    async def delete_webhook(self, webhook_id: str, user_id: str) -> None:
        """Delete a webhook (cascades to delivery logs)"""
        # Check webhook exists
        await self.get_webhook(webhook_id, user_id)

        query = """
            DELETE FROM webhooks
            WHERE id = ? AND user_id = ?
        """
        await self.db.execute(query, (webhook_id, user_id), commit=True)

        logger.info(f"Deleted webhook {webhook_id}")

    async def get_webhook_deliveries(
        self,
        webhook_id: str,
        user_id: str,
        limit: int = 50
    ) -> WebhookDeliveryListResponse:
        """Get delivery logs for a webhook"""
        # Check webhook exists
        await self.get_webhook(webhook_id, user_id)

        query = """
            SELECT *
            FROM webhook_deliveries
            WHERE webhook_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """
        rows = await self.db.fetch_all(query, (webhook_id, limit))

        deliveries = [self._delivery_from_row(row) for row in rows]

        return WebhookDeliveryListResponse(
            items=deliveries,
            total=len(deliveries)
        )

    async def get_webhook_stats(self, webhook_id: str, user_id: str) -> WebhookStatsResponse:
        """Get statistics for a webhook"""
        webhook = await self.get_webhook(webhook_id, user_id)

        success_rate = 0.0
        if webhook.total_deliveries > 0:
            success_rate = round(
                (webhook.successful_deliveries / webhook.total_deliveries) * 100,
                2
            )

        return WebhookStatsResponse(
            webhook_id=webhook_id,
            total_deliveries=webhook.total_deliveries,
            successful_deliveries=webhook.successful_deliveries,
            failed_deliveries=webhook.failed_deliveries,
            success_rate=success_rate,
            last_triggered_at=webhook.last_triggered_at
        )

    def _generate_secret(self) -> str:
        """Generate a secure random secret for HMAC signing"""
        return secrets.token_urlsafe(32)

    def _webhook_from_row(self, row: dict[str, Any]) -> WebhookResponse:
        """Convert database row to WebhookResponse"""
        return WebhookResponse(
            id=row["id"],
            user_id=row["user_id"],
            url=row["url"],
            events=json.loads(row["events"]),
            active=bool(row["active"]),
            description=row.get("description"),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            last_triggered_at=row.get("last_triggered_at"),
            total_deliveries=row.get("total_deliveries", 0),
            successful_deliveries=row.get("successful_deliveries", 0),
            failed_deliveries=row.get("failed_deliveries", 0)
        )

    def _delivery_from_row(self, row: dict[str, Any]) -> WebhookDeliveryResponse:
        """Convert database row to WebhookDeliveryResponse"""
        return WebhookDeliveryResponse(
            id=row["id"],
            webhook_id=row["webhook_id"],
            event_type=row["event_type"],
            status=row["status"],
            response_body=row.get("response_body"),
            error=row.get("error"),
            attempt=row["attempt"],
            created_at=row["created_at"]
        )
