"""
Webhooks event dispatcher - Emits events to registered webhooks
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any, Optional

from .models import WebhookEvent, WebhookEventPayload

logger = logging.getLogger(__name__)


class WebhookEventDispatcher:
    """
    Event dispatcher for webhooks

    Emits events to registered webhook subscribers via delivery service.
    """

    def __init__(self) -> None:
        self._delivery_service: Optional[Any] = None  # WebhookDeliveryService (circular import)
        self._enabled: bool = True

    def set_delivery_service(self, delivery_service: Any) -> None:
        """Set delivery service (called during DI initialization)"""
        self._delivery_service = delivery_service

    def disable(self) -> None:
        """Disable event dispatching (for testing)"""
        self._enabled = False

    def enable(self) -> None:
        """Enable event dispatching"""
        self._enabled = True

    async def emit_thread_created(
        self,
        thread_id: str,
        user_id: str,
        thread_data: dict[str, Any]
    ) -> None:
        """Emit thread.created event"""
        await self._emit_event(
            event_type=WebhookEvent.THREAD_CREATED,
            user_id=user_id,
            data={
                "thread_id": thread_id,
                "type": thread_data.get("type", "chat"),
                "created_at": thread_data.get("created_at"),
                **thread_data
            }
        )

    async def emit_message_sent(
        self,
        message_id: str,
        thread_id: str,
        user_id: str,
        agent: str,
        content: str,
        metadata: Optional[dict[str, Any]] = None
    ) -> None:
        """Emit message.sent event"""
        await self._emit_event(
            event_type=WebhookEvent.MESSAGE_SENT,
            user_id=user_id,
            data={
                "message_id": message_id,
                "thread_id": thread_id,
                "agent": agent,
                "content": content[:500],  # Truncate long messages
                "metadata": metadata or {},
            }
        )

    async def emit_analysis_completed(
        self,
        thread_id: str,
        user_id: str,
        summary_id: str,
        facts_count: int,
        ltm_count: int
    ) -> None:
        """Emit analysis.completed event"""
        await self._emit_event(
            event_type=WebhookEvent.ANALYSIS_COMPLETED,
            user_id=user_id,
            data={
                "thread_id": thread_id,
                "summary_id": summary_id,
                "facts_count": facts_count,
                "ltm_count": ltm_count,
            }
        )

    async def emit_debate_completed(
        self,
        debate_id: str,
        user_id: str,
        topic: str,
        turns_count: int,
        synthesis: str
    ) -> None:
        """Emit debate.completed event"""
        await self._emit_event(
            event_type=WebhookEvent.DEBATE_COMPLETED,
            user_id=user_id,
            data={
                "debate_id": debate_id,
                "topic": topic,
                "turns_count": turns_count,
                "synthesis": synthesis[:500],  # Truncate long synthesis
            }
        )

    async def emit_document_uploaded(
        self,
        document_id: str,
        user_id: str,
        filename: str,
        size: int,
        chunks_count: int
    ) -> None:
        """Emit document.uploaded event"""
        await self._emit_event(
            event_type=WebhookEvent.DOCUMENT_UPLOADED,
            user_id=user_id,
            data={
                "document_id": document_id,
                "filename": filename,
                "size": size,
                "chunks_count": chunks_count,
            }
        )

    async def _emit_event(
        self,
        event_type: WebhookEvent,
        user_id: str,
        data: dict[str, Any]
    ) -> None:
        """Internal method to emit event to delivery service"""
        if not self._enabled:
            logger.debug(f"Webhook events disabled, skipping {event_type}")
            return

        if not self._delivery_service:
            logger.warning(f"Webhook delivery service not initialized, skipping {event_type}")
            return

        try:
            # Create event payload
            payload = WebhookEventPayload(
                event=str(event_type),
                timestamp=datetime.utcnow(),
                data=data,
                webhook_id=""  # Will be filled by delivery service
            )

            # Dispatch to delivery service asynchronously (fire and forget)
            asyncio.create_task(
                self._delivery_service.deliver_event(
                    event_type=str(event_type),
                    user_id=user_id,
                    payload=payload
                )
            )

            logger.debug(f"Dispatched webhook event: {event_type} for user {user_id}")

        except Exception as e:
            logger.error(f"Failed to dispatch webhook event {event_type}: {e}", exc_info=True)


# Global singleton dispatcher
_dispatcher: Optional[WebhookEventDispatcher] = None


def get_webhook_dispatcher() -> WebhookEventDispatcher:
    """Get global webhook event dispatcher"""
    global _dispatcher
    if _dispatcher is None:
        _dispatcher = WebhookEventDispatcher()
    return _dispatcher
