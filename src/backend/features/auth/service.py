from __future__ import annotations

import hashlib
import json
import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Sequence
from uuid import uuid4

import jwt

from backend.core.database.manager import DatabaseManager

from .models import AllowlistEntry, AuthConfig, LoginResponse, SessionInfo
from .rate_limiter import RateLimiterConfig, RateLimitExceeded, SlidingWindowRateLimiter

logger = logging.getLogger("emergence.auth")


class AuthError(Exception):
    def __init__(self, message: str, *, status_code: int = 400, payload: Optional[dict] = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload or {}


class AuthService:
    def __init__(
        self,
        db_manager: DatabaseManager,
        config: AuthConfig,
        rate_limiter: Optional[SlidingWindowRateLimiter] = None,
    ) -> None:
        self.db = db_manager
        self.config = config
        self.rate_limiter = rate_limiter or SlidingWindowRateLimiter(RateLimiterConfig())

    # ------------------------------------------------------------------
    async def bootstrap(self) -> None:
        for email in self.config.admin_emails:
            normalized = self._normalize_email(email)
            if not normalized:
                continue
            await self._upsert_allowlist(normalized, role="admin", note="seed", actor="bootstrap")

    async def login(self, email: str, ip_address: Optional[str], user_agent: Optional[str]) -> LoginResponse:
        normalized = self._normalize_email(email)
        if not normalized:
            raise AuthError("Email invalide ou vide.", status_code=400)

        try:
            await self.rate_limiter.check(normalized, ip_address)
        except RateLimitExceeded as exc:
            raise AuthError(
                "Trop de tentatives. Réessaie plus tard.",
                status_code=429,
                payload={"retry_after": exc.retry_after},
            ) from exc

        allow_row = await self._get_allowlist_row(normalized)
        if allow_row is None:
            raise AuthError("Email non autorisé.", status_code=401)
        if allow_row.get("revoked_at"):
            raise AuthError("Compte temporairement désactivé.", status_code=423)

        now = self._now()
        expires_at = now + timedelta(seconds=self.config.token_ttl_seconds)
        session_id = str(uuid4())
        role = allow_row.get("role") or "member"

        claims = {
            "iss": self.config.issuer,
            "aud": self.config.audience,
            "sub": self._hash_subject(normalized),
            "email": normalized,
            "role": role,
            "sid": session_id,
            "iat": int(now.timestamp()),
            "exp": int(expires_at.timestamp()),
        }
        token = jwt.encode(claims, self.config.secret, algorithm="HS256")

        metadata: dict[str, Any] = {}
        if user_agent:
            metadata["user_agent"] = user_agent

        await self.db.execute(
            """
            INSERT INTO auth_sessions (id, email, role, ip_address, user_agent, issued_at, expires_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                normalized,
                role,
                ip_address,
                user_agent,
                now.isoformat(),
                expires_at.isoformat(),
                json.dumps(metadata) if metadata else None,
            ),
        )
        await self._write_audit(
            "login",
            email=normalized,
            metadata={"session_id": session_id, "ip": ip_address},
        )
        await self.rate_limiter.reset(normalized, ip_address)
        return LoginResponse(token=token, expires_at=expires_at, role=role, session_id=session_id)

    async def logout(self, session_id: str, actor: Optional[str] = None) -> bool:
        session = await self._fetch_one_dict(
            "SELECT email, revoked_at FROM auth_sessions WHERE id = ?",
            (session_id,),
        )
        if not session:
            return False
        if session.get("revoked_at"):
            return False
        await self.db.execute(
            "UPDATE auth_sessions SET revoked_at = ?, revoked_by = ? WHERE id = ?",
            (self._now().isoformat(), actor, session_id),
        )
        await self._write_audit(
            "logout",
            email=session.get("email"),
            actor=actor,
            metadata={"session_id": session_id},
        )
        return True

    async def revoke_session(self, session_id: str, actor: Optional[str]) -> bool:
        session = await self._fetch_one_dict(
            "SELECT email, revoked_at FROM auth_sessions WHERE id = ?",
            (session_id,),
        )
        if not session or session.get("revoked_at"):
            return False
        await self.db.execute(
            "UPDATE auth_sessions SET revoked_at = ?, revoked_by = ? WHERE id = ?",
            (self._now().isoformat(), actor, session_id),
        )
        await self._write_audit(
            "session:revoke",
            email=session.get("email"),
            actor=actor,
            metadata={"session_id": session_id},
        )
        return True

    async def revoke_sessions_for_email(self, email: str, actor: Optional[str]) -> int:
        normalized = self._normalize_email(email)
        rows = await self._fetch_all_dicts(
            "SELECT id FROM auth_sessions WHERE email = ? AND revoked_at IS NULL",
            (normalized,),
        )
        if not rows:
            return 0
        await self.db.execute(
            "UPDATE auth_sessions SET revoked_at = ?, revoked_by = ? WHERE email = ? AND revoked_at IS NULL",
            (self._now().isoformat(), actor, normalized),
        )
        await self._write_audit("session:revoke_all", email=normalized, actor=actor)
        return len(rows)

    async def verify_token(self, token: str, allow_expired: bool = False, allow_revoked: bool = False) -> dict[str, Any]:
        try:
            claims = jwt.decode(
                token,
                self.config.secret,
                algorithms=["HS256"],
                audience=self.config.audience,
                issuer=self.config.issuer,
                options={"verify_exp": not allow_expired},
            )
        except jwt.ExpiredSignatureError as exc:
            raise AuthError("Token expir�.", status_code=401) from exc
        except jwt.InvalidTokenError as exc:
            raise AuthError("Token invalide.", status_code=401) from exc

        email = self._normalize_email(str(claims.get("email", "")))
        session_id = str(claims.get("sid", ""))
        if not email or not session_id:
            raise AuthError("Token incomplet.", status_code=401)

        allow_row = await self._get_allowlist_row(email)
        if not allow_row or allow_row.get("revoked_at"):
            raise AuthError("Compte non autoris�.", status_code=401)

        session = await self._fetch_one_dict(
            "SELECT expires_at, revoked_at FROM auth_sessions WHERE id = ?",
            (session_id,),
        )
        if not session:
            raise AuthError("Session inconnue.", status_code=401)

        revoked_at_raw = session.get("revoked_at")
        session_revoked = bool(revoked_at_raw)
        if session_revoked and not allow_revoked:
            raise AuthError("Session r�voqu�e.", status_code=401)

        expires_at = self._parse_dt(session.get("expires_at"))
        if expires_at < self._now() and not allow_expired:
            raise AuthError("Session expir�e.", status_code=401)

        revoked_at = self._parse_dt(revoked_at_raw) if revoked_at_raw else None
        role = claims.get("role") or allow_row.get("role") or "member"
        claims.update({
            "email": email,
            "role": role,
            "session_id": session_id,
            "expires_at": expires_at,
            "session_revoked": session_revoked,
        })
        if revoked_at:
            claims["revoked_at"] = revoked_at
        return claims
    async def list_allowlist(self, include_revoked: bool = False) -> list[AllowlistEntry]:
        if include_revoked:
            rows = await self._fetch_all_dicts(
                "SELECT email, role, note, created_at, created_by, revoked_at, revoked_by FROM auth_allowlist ORDER BY email ASC"
            )
        else:
            rows = await self._fetch_all_dicts(
                "SELECT email, role, note, created_at, created_by, revoked_at, revoked_by FROM auth_allowlist WHERE revoked_at IS NULL ORDER BY email ASC"
            )
        return [self._row_to_allowlist(r) for r in rows]

    async def upsert_allowlist(self, email: str, role: str, note: Optional[str], actor: Optional[str]) -> AllowlistEntry:
        normalized = self._normalize_email(email)
        if not normalized:
            raise AuthError("Email invalide.", status_code=400)
        await self._upsert_allowlist(normalized, role=role, note=note, actor=actor)
        await self._write_audit(
            "allowlist:add",
            email=normalized,
            actor=actor,
            metadata={"role": role, "note": note},
        )
        row = await self._get_allowlist_row(normalized)
        if not row:
            raise AuthError("Entrée allowlist introuvable après création.", status_code=500)
        return self._row_to_allowlist(row)

    async def remove_allowlist(self, email: str, actor: Optional[str]) -> None:
        normalized = self._normalize_email(email)
        await self.db.execute(
            "UPDATE auth_allowlist SET revoked_at = ?, revoked_by = ? WHERE email = ?",
            (self._now().isoformat(), actor, normalized),
        )
        await self.revoke_sessions_for_email(normalized, actor=actor)
        await self._write_audit("allowlist:remove", email=normalized, actor=actor)

    async def list_sessions(self, active_only: bool = False) -> list[SessionInfo]:
        if active_only:
            rows = await self._fetch_all_dicts(
                "SELECT id, email, role, ip_address, issued_at, expires_at, revoked_at, revoked_by FROM auth_sessions WHERE revoked_at IS NULL ORDER BY issued_at DESC"
            )
        else:
            rows = await self._fetch_all_dicts(
                "SELECT id, email, role, ip_address, issued_at, expires_at, revoked_at, revoked_by FROM auth_sessions ORDER BY issued_at DESC"
            )
        return [self._row_to_session(r) for r in rows]

    # ------------------------------------------------------------------
    async def _upsert_allowlist(self, email: str, role: str, note: Optional[str], actor: Optional[str]) -> None:
        now = self._now().isoformat()
        await self.db.execute(
            """
            INSERT INTO auth_allowlist (email, role, note, created_at, created_by, revoked_at, revoked_by)
            VALUES (?, ?, ?, ?, ?, NULL, NULL)
            ON CONFLICT(email) DO UPDATE SET
                role = excluded.role,
                note = excluded.note,
                revoked_at = NULL,
                revoked_by = NULL
            """,
            (email, role, note, now, actor),
        )

    async def _get_allowlist_row(self, email: str) -> Optional[dict[str, Any]]:
        return await self._fetch_one_dict(
            "SELECT email, role, note, created_at, created_by, revoked_at, revoked_by FROM auth_allowlist WHERE email = ?",
            (email,),
        )

    async def _write_audit(
        self,
        event_type: str,
        *,
        email: Optional[str],
        actor: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        try:
            await self.db.execute(
                "INSERT INTO auth_audit_log (event_type, email, actor, metadata, created_at) VALUES (?, ?, ?, ?, ?)",
                (
                    event_type,
                    email,
                    actor,
                    json.dumps(metadata) if metadata else None,
                    self._now().isoformat(),
                ),
            )
        except Exception as exc:
            logger.warning("Auth audit log failure: %s", exc)

    async def _fetch_one_dict(self, query: str, params: Sequence[Any] | tuple[Any, ...] | None = None) -> Optional[dict[str, Any]]:
        row = await self.db.fetch_one(query, params)
        return self._row_to_dict(row)

    async def _fetch_all_dicts(self, query: str, params: Sequence[Any] | tuple[Any, ...] | None = None) -> list[dict[str, Any]]:
        rows = await self.db.fetch_all(query, params)
        return [d for d in (self._row_to_dict(r) for r in rows or []) if d]

    def _row_to_dict(self, row) -> Optional[dict[str, Any]]:
        if row is None:
            return None
        if isinstance(row, dict):
            return row
        try:
            keys = row.keys()  # type: ignore[attr-defined]
            return {key: row[key] for key in keys}
        except Exception:
            try:
                return dict(row)  # type: ignore[arg-type]
            except Exception:
                return None

    def _row_to_allowlist(self, row: dict[str, Any]) -> AllowlistEntry:
        revoked_at = row.get("revoked_at")
        return AllowlistEntry(
            email=row["email"],
            role=row.get("role", "member"),
            note=row.get("note"),
            created_at=self._parse_dt(row.get("created_at")),
            created_by=row.get("created_by"),
            revoked_at=self._parse_dt(revoked_at) if revoked_at else None,
            revoked_by=row.get("revoked_by"),
        )

    def _row_to_session(self, row: dict[str, Any]) -> SessionInfo:
        revoked_at = row.get("revoked_at")
        return SessionInfo(
            id=row["id"],
            email=row["email"],
            role=row.get("role", "member"),
            issued_at=self._parse_dt(row.get("issued_at")),
            expires_at=self._parse_dt(row.get("expires_at")),
            ip_address=row.get("ip_address"),
            revoked_at=self._parse_dt(revoked_at) if revoked_at else None,
            revoked_by=row.get("revoked_by"),
        )

    def _hash_subject(self, email: str) -> str:
        return hashlib.sha256(email.encode("utf-8")).hexdigest()

    def _normalize_email(self, email: str) -> str:
        return (email or "").strip().lower()

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def _parse_dt(self, value: Optional[str]) -> datetime:
        if not value:
            return datetime.fromtimestamp(0, tz=timezone.utc)
        try:
            dt = datetime.fromisoformat(value)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            return datetime.fromtimestamp(0, tz=timezone.utc)


TRUTHY = {"1", "true", "yes", "on"}


def build_auth_config_from_env() -> AuthConfig:
    secret = os.getenv("AUTH_JWT_SECRET", "change-me")
    if not secret:
        secret = "change-me"
    issuer = os.getenv("AUTH_JWT_ISSUER", "emergence.local")
    audience = os.getenv("AUTH_JWT_AUDIENCE", "emergence-app")
    ttl_raw = os.getenv("AUTH_JWT_TTL_DAYS", "7")
    try:
        ttl_days = max(1, int(ttl_raw))
    except Exception:
        ttl_days = 7
    admin_raw = os.getenv("AUTH_ADMIN_EMAILS", "")
    admin_emails = {email.strip().lower() for email in admin_raw.split(',') if email.strip()}
    dev_mode = str(os.getenv("AUTH_DEV_MODE", "0")).strip().lower() in TRUTHY
    return AuthConfig(
        secret=secret,
        issuer=issuer,
        audience=audience,
        token_ttl_seconds=ttl_days * 24 * 60 * 60,
        admin_emails=admin_emails,
        dev_mode=dev_mode,
    )



