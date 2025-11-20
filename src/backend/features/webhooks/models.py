"""
Webhooks models - Pydantic schemas for webhook subscriptions
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, HttpUrl


class WebhookEvent(str, Enum):
    """Available webhook events"""

    THREAD_CREATED = "thread.created"
    MESSAGE_SENT = "message.sent"
    ANALYSIS_COMPLETED = "analysis.completed"
    DEBATE_COMPLETED = "debate.completed"
    DOCUMENT_UPLOADED = "document.uploaded"

    def __str__(self) -> str:
        return self.value


class WebhookCreatePayload(BaseModel):
    """Payload for creating a new webhook"""

    url: HttpUrl
    events: list[WebhookEvent]
    description: Optional[str] = None
    active: bool = True


class WebhookUpdatePayload(BaseModel):
    """Payload for updating an existing webhook"""

    url: Optional[HttpUrl] = None
    events: Optional[list[WebhookEvent]] = None
    description: Optional[str] = None
    active: Optional[bool] = None


class WebhookResponse(BaseModel):
    """Webhook object returned by API"""

    id: str
    user_id: str
    url: str
    events: list[str]
    active: bool
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    last_triggered_at: Optional[datetime] = None
    total_deliveries: int = 0
    successful_deliveries: int = 0
    failed_deliveries: int = 0

    model_config = {
        "from_attributes": True,
    }


class WebhookListResponse(BaseModel):
    """Response for listing webhooks"""

    items: list[WebhookResponse]
    total: int


class WebhookDeliveryStatus(str, Enum):
    """Delivery status for webhook deliveries"""

    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"

    def __str__(self) -> str:
        return self.value


class WebhookDeliveryResponse(BaseModel):
    """Webhook delivery log"""

    id: str
    webhook_id: str
    event_type: str
    status: int
    response_body: Optional[str] = None
    error: Optional[str] = None
    attempt: int
    created_at: datetime

    model_config = {
        "from_attributes": True,
    }


class WebhookDeliveryListResponse(BaseModel):
    """Response for listing webhook deliveries"""

    items: list[WebhookDeliveryResponse]
    total: int


class WebhookEventPayload(BaseModel):
    """Generic webhook event payload sent to external URLs"""

    event: str
    timestamp: datetime
    data: dict[str, Any]
    webhook_id: str

    model_config = {
        "json_encoders": {
            datetime: lambda v: v.isoformat(),
        }
    }


class WebhookStatsResponse(BaseModel):
    """Webhook statistics"""

    webhook_id: str
    total_deliveries: int
    successful_deliveries: int
    failed_deliveries: int
    success_rate: float
    last_triggered_at: Optional[datetime] = None
