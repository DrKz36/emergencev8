"""
Webhooks feature module - External integrations via HTTP webhooks

Features:
- Subscribe to events (thread.created, message.sent, analysis.completed, etc.)
- Automatic HTTP POST delivery with HMAC signature
- Retry logic (3 attempts with exponential backoff)
- Delivery logs and statistics
"""

from .delivery import WebhookDeliveryService
from .events import WebhookEventDispatcher, get_webhook_dispatcher
from .models import (
    WebhookCreatePayload,
    WebhookDeliveryListResponse,
    WebhookDeliveryResponse,
    WebhookEvent,
    WebhookEventPayload,
    WebhookListResponse,
    WebhookResponse,
    WebhookStatsResponse,
    WebhookUpdatePayload,
)
from .router import router as webhooks_router
from .service import WebhookService

__all__ = [
    # Router
    "webhooks_router",
    # Services
    "WebhookService",
    "WebhookDeliveryService",
    "WebhookEventDispatcher",
    "get_webhook_dispatcher",
    # Models
    "WebhookEvent",
    "WebhookCreatePayload",
    "WebhookUpdatePayload",
    "WebhookResponse",
    "WebhookListResponse",
    "WebhookDeliveryResponse",
    "WebhookDeliveryListResponse",
    "WebhookStatsResponse",
    "WebhookEventPayload",
]
