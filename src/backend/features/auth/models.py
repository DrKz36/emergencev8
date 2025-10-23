from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Optional, Sequence

from pydantic import BaseModel, Field


class UserRole(str, Enum):
    ADMIN = "admin"
    MEMBER = "member"
    GUEST = "guest"
    TESTER = "tester"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class User:
    id: str
    username: str
    email: str
    role: UserRole = UserRole.MEMBER
    is_active: bool = True
    created_at: Optional[datetime] = None


class AuthConfig(BaseModel):
    secret: str
    issuer: str
    audience: str
    token_ttl_seconds: int = Field(default=7 * 24 * 60 * 60)
    algorithm: str = "HS256"
    admin_emails: set[str] = Field(default_factory=set)
    dev_mode: bool = False
    dev_default_email: Optional[str] = None

    model_config = {
        "frozen": True,
    }


class LoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=8)
    meta: Optional[dict[str, Any]] = None


class LoginResponse(BaseModel):
    token: str
    expires_at: datetime
    role: str
    session_id: str
    user_id: str
    email: str
    password_must_reset: bool = False


class DevLoginRequest(BaseModel):
    email: Optional[str] = None


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
    password_updated_at: Optional[datetime] = None
    password_must_reset: bool = True
    revoked_at: Optional[datetime] = None
    revoked_by: Optional[str] = None


class AllowlistCreatePayload(BaseModel):
    email: str
    role: Optional[str] = Field(default=None)
    note: Optional[str] = None
    password: Optional[str] = Field(default=None, min_length=8)
    generate_password: bool = False


class AllowlistMutationResponse(BaseModel):
    entry: AllowlistEntry
    clear_password: Optional[str] = None
    generated: bool = False


class AllowlistListResponse(BaseModel):
    items: Sequence[AllowlistEntry]
    total: int
    page: int
    page_size: int
    has_more: bool
    status: str = "active"
    query: Optional[str] = None


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
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=8)
    new_password: str = Field(min_length=8)


class ChangePasswordResponse(BaseModel):
    success: bool
    message: str


class RequestPasswordResetRequest(BaseModel):
    email: str


class RequestPasswordResetResponse(BaseModel):
    success: bool
    message: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8)


class ResetPasswordResponse(BaseModel):
    success: bool
    message: str
