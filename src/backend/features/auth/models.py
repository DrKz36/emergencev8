from __future__ import annotations

from datetime import datetime
from typing import Optional, Sequence

from pydantic import BaseModel, Field


class AuthConfig(BaseModel):
    secret: str
    issuer: str
    audience: str
    token_ttl_seconds: int = Field(default=7 * 24 * 60 * 60)
    admin_emails: set[str] = Field(default_factory=set)
    dev_mode: bool = False

    model_config = {
        "frozen": True,
    }


class LoginRequest(BaseModel):
    email: str


class LoginResponse(BaseModel):
    token: str
    expires_at: datetime
    role: str
    session_id: str


class SessionStatusResponse(BaseModel):
    email: str
    role: str
    expires_at: datetime
    issued_at: datetime
    session_id: str
    source: Optional[str] = None


class SessionInfo(BaseModel):
    id: str
    email: str
    role: str
    issued_at: datetime
    expires_at: datetime
    ip_address: Optional[str] = None
    revoked_at: Optional[datetime] = None
    revoked_by: Optional[str] = None


class AllowlistEntry(BaseModel):
    email: str
    role: str = "member"
    note: Optional[str] = None
    created_at: datetime
    created_by: Optional[str] = None
    revoked_at: Optional[datetime] = None
    revoked_by: Optional[str] = None


class AllowlistCreatePayload(BaseModel):
    email: str
    role: str = "member"
    note: Optional[str] = None


class AllowlistListResponse(BaseModel):
    items: Sequence[AllowlistEntry]


class SessionsListResponse(BaseModel):
    items: Sequence[SessionInfo]


class SessionRevokePayload(BaseModel):
    session_id: str


class SessionRevokeResult(BaseModel):
    updated: int


class LogoutPayload(BaseModel):
    session_id: Optional[str] = None


class AuditEvent(BaseModel):
    event_type: str
    email: Optional[str] = None
    actor: Optional[str] = None
    metadata: dict = Field(default_factory=dict)
    created_at: datetime