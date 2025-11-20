# src/backend/features/usage/models.py
"""
Phase 2 Guardian Cloud - Pydantic models pour Usage Tracking
Privacy-compliant: NO message content, NO file content, NO passwords
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional, Any
from pydantic import BaseModel, Field


class UserSession(BaseModel):
    """Session utilisateur (login -> logout)"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_email: str
    session_start: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    session_end: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

    class Config:
        json_encoders = {datetime: lambda dt: dt.isoformat() if dt else None}


class FeatureUsage(BaseModel):
    """Utilisation d'une feature (endpoint appelé)"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_email: str | None
    feature_name: str  # Ex: "chat_message", "document_upload", "thread_create"
    endpoint: str  # Ex: "/api/chat/message"
    method: str = "GET"  # GET, POST, PUT, DELETE, etc.
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    success: bool = True
    error_message: Optional[str] = None
    duration_ms: Optional[int] = None
    status_code: int = 200

    class Config:
        json_encoders = {datetime: lambda dt: dt.isoformat() if dt else None}


class UserError(BaseModel):
    """Erreur rencontrée par un utilisateur"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_email: str | None
    endpoint: str
    method: str  # GET, POST, etc.
    error_type: str  # "ValidationError", "HTTPException", "ServerError", etc.
    error_code: int  # 400, 500, 503, etc.
    error_message: str
    stack_trace: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        json_encoders = {datetime: lambda dt: dt.isoformat() if dt else None}


class UsageReportUser(BaseModel):
    """Stats d'un utilisateur pour le rapport"""

    email: str
    total_time_minutes: int
    features_used: list[str]
    requests_count: int
    errors_count: int
    errors: list[dict[str, Any]]  # Liste des erreurs avec détails


class UsageReport(BaseModel):
    """Rapport d'usage global (toutes les N heures)"""

    period_start: datetime
    period_end: datetime
    active_users: int
    total_requests: int
    total_errors: int
    users: list[UsageReportUser]
    top_features: list[dict[str, Any]]  # [{"name": "chat_message", "count": 567}, ...]
    error_breakdown: dict[str, int]  # {"400": 5, "500": 2}

    class Config:
        json_encoders = {datetime: lambda dt: dt.isoformat() if dt else None}
