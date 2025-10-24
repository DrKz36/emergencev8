"""
Webhooks router - REST endpoints for webhook management
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status

from ...shared.dependencies import get_auth_claims
from .models import (
    WebhookCreatePayload,
    WebhookDeliveryListResponse,
    WebhookListResponse,
    WebhookResponse,
    WebhookStatsResponse,
    WebhookUpdatePayload,
)
from .service import WebhookService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webhooks", tags=["Webhooks"])


async def get_webhook_service(request: Request) -> WebhookService:
    """Dependency to get webhook service from container"""
    container = getattr(request.app.state, "service_container", None)
    if container is None:
        raise HTTPException(status_code=503, detail="Service container unavailable")

    db = container.db()
    return WebhookService(db)


@router.post("", response_model=WebhookResponse, status_code=status.HTTP_201_CREATED)
async def create_webhook(
    payload: WebhookCreatePayload,
    claims: dict[str, Any] = Depends(get_auth_claims),
    service: WebhookService = Depends(get_webhook_service)
) -> WebhookResponse:
    """
    Create a new webhook subscription

    **Events available:**
    - `thread.created` - Triggered when a new thread is created
    - `message.sent` - Triggered when a message is sent
    - `analysis.completed` - Triggered when memory analysis is completed
    - `debate.completed` - Triggered when a debate is finished
    - `document.uploaded` - Triggered when a document is uploaded

    **HMAC Signature:**
    - The webhook request will include `X-Webhook-Signature` header
    - Signature is HMAC SHA256 of the request body using the webhook secret
    - Verify signature: `HMAC-SHA256(body, secret) == X-Webhook-Signature`

    **Example verification (Python):**
    ```python
    import hmac
    import hashlib

    def verify_signature(body: str, signature: str, secret: str) -> bool:
        expected = hmac.new(
            secret.encode('utf-8'),
            body.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, signature)
    ```
    """
    user_id = claims["sub"]

    try:
        webhook = await service.create_webhook(user_id, payload)
        logger.info(f"Webhook {webhook.id} created by user {user_id}")
        return webhook
    except Exception as e:
        logger.error(f"Failed to create webhook: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create webhook"
        ) from e


@router.get("", response_model=WebhookListResponse)
async def list_webhooks(
    claims: dict[str, Any] = Depends(get_auth_claims),
    service: WebhookService = Depends(get_webhook_service)
) -> WebhookListResponse:
    """
    List all webhooks for the current user
    """
    user_id = claims["sub"]

    try:
        return await service.list_webhooks(user_id)
    except Exception as e:
        logger.error(f"Failed to list webhooks: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list webhooks"
        ) from e


@router.get("/{webhook_id}", response_model=WebhookResponse)
async def get_webhook(
    webhook_id: str,
    claims: dict[str, Any] = Depends(get_auth_claims),
    service: WebhookService = Depends(get_webhook_service)
) -> WebhookResponse:
    """
    Get a single webhook by ID
    """
    user_id = claims["sub"]

    try:
        return await service.get_webhook(webhook_id, user_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        ) from e
    except Exception as e:
        logger.error(f"Failed to get webhook {webhook_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get webhook"
        ) from e


@router.put("/{webhook_id}", response_model=WebhookResponse)
async def update_webhook(
    webhook_id: str,
    payload: WebhookUpdatePayload,
    claims: dict[str, Any] = Depends(get_auth_claims),
    service: WebhookService = Depends(get_webhook_service)
) -> WebhookResponse:
    """
    Update an existing webhook

    **Partial updates supported** - only provide fields you want to change
    """
    user_id = claims["sub"]

    try:
        webhook = await service.update_webhook(webhook_id, user_id, payload)
        logger.info(f"Webhook {webhook_id} updated by user {user_id}")
        return webhook
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        ) from e
    except Exception as e:
        logger.error(f"Failed to update webhook {webhook_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update webhook"
        ) from e


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook(
    webhook_id: str,
    claims: dict[str, Any] = Depends(get_auth_claims),
    service: WebhookService = Depends(get_webhook_service)
) -> None:
    """
    Delete a webhook

    **Warning:** This will also delete all delivery logs for this webhook
    """
    user_id = claims["sub"]

    try:
        await service.delete_webhook(webhook_id, user_id)
        logger.info(f"Webhook {webhook_id} deleted by user {user_id}")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        ) from e
    except Exception as e:
        logger.error(f"Failed to delete webhook {webhook_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete webhook"
        ) from e


@router.get("/{webhook_id}/deliveries", response_model=WebhookDeliveryListResponse)
async def get_webhook_deliveries(
    webhook_id: str,
    limit: int = 50,
    claims: dict[str, Any] = Depends(get_auth_claims),
    service: WebhookService = Depends(get_webhook_service)
) -> WebhookDeliveryListResponse:
    """
    Get delivery logs for a webhook

    Shows recent webhook delivery attempts with status codes, responses, and errors.
    """
    user_id = claims["sub"]

    if limit < 1 or limit > 200:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Limit must be between 1 and 200"
        )

    try:
        return await service.get_webhook_deliveries(webhook_id, user_id, limit)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        ) from e
    except Exception as e:
        logger.error(f"Failed to get deliveries for webhook {webhook_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get webhook deliveries"
        ) from e


@router.get("/{webhook_id}/stats", response_model=WebhookStatsResponse)
async def get_webhook_stats(
    webhook_id: str,
    claims: dict[str, Any] = Depends(get_auth_claims),
    service: WebhookService = Depends(get_webhook_service)
) -> WebhookStatsResponse:
    """
    Get statistics for a webhook

    Shows total deliveries, success rate, and last triggered timestamp.
    """
    user_id = claims["sub"]

    try:
        return await service.get_webhook_stats(webhook_id, user_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        ) from e
    except Exception as e:
        logger.error(f"Failed to get stats for webhook {webhook_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get webhook stats"
        ) from e
