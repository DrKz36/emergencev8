from __future__ import annotations

import hashlib
import json
import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Sequence
from uuid import uuid4

import jwt
import bcrypt

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

    async def login(self, email: str, password: str, ip_address: Optional[str], user_agent: Optional[str]) -> LoginResponse:
        normalized = self._normalize_email(email)
        if not normalized:
            raise AuthError("Email invalide ou vide.", status_code=400)

        candidate_password = (password or "").strip()
        if not candidate_password:
            raise AuthError("Mot de passe requis.", status_code=400)

        try:
            await self.rate_limiter.check(normalized, ip_address)
        except RateLimitExceeded as exc:
            raise AuthError(
                "Trop de tentatives. Reessaie plus tard.",
                status_code=429,
                payload={"retry_after": exc.retry_after},
            ) from exc

        allow_row = await self._get_allowlist_row(normalized)
        if allow_row is None:
            raise AuthError("Email non autorise.", status_code=401)
        if allow_row.get("revoked_at"):
            raise AuthError("Compte temporairement desactive.", status_code=423)

        password_hash = allow_row.get("password_hash")
        if not password_hash or not self._verify_password(candidate_password, password_hash):
            raise AuthError("Identifiants invalides.", status_code=401)

        role = allow_row.get("role") or "member"

        session_response = await self._issue_session(
            normalized,
            role,
            ip_address,
            user_agent,
            event_type="login",
            audit_metadata={"source": "password"},
            session_metadata={"source": "password"},
        )
        await self.rate_limiter.reset(normalized, ip_address)
        return session_response

    async def _issue_session(
        self,
        email: str,
        role: str,
        ip_address: Optional[str],
        user_agent: Optional[str],
        *,
        event_type: str,
        audit_metadata: Optional[dict[str, Any]] = None,
        session_metadata: Optional[dict[str, Any]] = None,
        claims_extra: Optional[dict[str, Any]] = None,
    ) -> LoginResponse:
        now = self._now()
        expires_at = now + timedelta(seconds=self.config.token_ttl_seconds)
        session_id = str(uuid4())
        claims = {
            "iss": self.config.issuer,
            "aud": self.config.audience,
            "sub": self._hash_subject(email),
            "email": email,
            "role": role,
            "sid": session_id,
            "iat": int(now.timestamp()),
            "exp": int(expires_at.timestamp()),
        }
        if claims_extra:
            for key, value in claims_extra.items():
                if value is not None:
                    claims[key] = value
        token = jwt.encode(claims, self.config.secret, algorithm="HS256")

        session_meta: dict[str, Any] = {}
        if session_metadata:
            session_meta.update({k: v for k, v in session_metadata.items() if v is not None})
        if user_agent:
            session_meta.setdefault("user_agent", user_agent)

        await self.db.execute(
            """
            INSERT INTO auth_sessions (id, email, role, ip_address, user_id, user_agent, issued_at, expires_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                email,
                role,
                ip_address,
                claims.get("sub"),
                user_agent,
                now.isoformat(),
                expires_at.isoformat(),
                json.dumps(session_meta) if session_meta else None,
            ),
        )

        audit_meta: dict[str, Any] = {"session_id": session_id}
        if ip_address:
            audit_meta["ip"] = ip_address
        if audit_metadata:
            audit_meta.update({k: v for k, v in audit_metadata.items() if v is not None})

        user_claim = str(claims.get("sub") or "")
        await self._write_audit(event_type, email=email, metadata=audit_meta)
        return LoginResponse(
            token=token,
            expires_at=expires_at,
            role=role,
            session_id=session_id,
            user_id=user_claim,
            email=email,
        )

    async def dev_login(self, email: Optional[str], ip_address: Optional[str], user_agent: Optional[str]) -> LoginResponse:
        if not self.config.dev_mode:
            raise AuthError("Mode dev desactive.", status_code=403)

        candidate = self._normalize_email(email or "")
        env_email = self._normalize_email(self.config.dev_default_email or "")
        if not candidate and env_email:
            candidate = env_email
        if not candidate and self.config.admin_emails:
            candidate = next(iter(sorted(self.config.admin_emails)))
        if not candidate:
            candidate = "dev@local"
        candidate = self._normalize_email(candidate)

        existing = await self._get_allowlist_row(candidate)
        desired_role = "admin"
        note = existing.get("note") if existing and existing.get("note") else "dev:auto"

        await self._upsert_allowlist(
            candidate,
            role=desired_role,
            note=note,
            actor="dev-login",
        )

        refreshed = await self._get_allowlist_row(candidate)
        if refreshed:
            refreshed_role = refreshed.get("role")
            if isinstance(refreshed_role, str) and refreshed_role.strip():
                desired_role = refreshed_role.strip()

        return await self._issue_session(
            candidate,
            desired_role or "admin",
            ip_address,
            user_agent,
            event_type="login:dev",
            audit_metadata={"mode": "dev", "source": "auto"},
            session_metadata={"source": "dev"},
        )

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
            "SELECT expires_at, revoked_at, user_id FROM auth_sessions WHERE id = ?",
            (session_id,),
        )
        if not session:
            raise AuthError("Session inconnue.", status_code=401)

        stored_user_id = str((session.get("user_id") or "").strip())
        claim_user_id = str((claims.get("sub") or claims.get("user_id") or "").strip())
        effective_user_id = claim_user_id or stored_user_id
        if effective_user_id:
            claims["sub"] = effective_user_id
            claims["user_id"] = effective_user_id

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

    async def get_user_id_for_session(self, session_id: str) -> Optional[str]:
        normalized = (session_id or "").strip()
        if not normalized:
            return None
        row = await self._fetch_one_dict(
            "SELECT user_id FROM auth_sessions WHERE id = ?",
            (normalized,),
        )
        if not row:
            return None
        value = row.get('user_id')
        if value is None:
            return None
        normalized_value = str(value).strip()
        return normalized_value or None

    async def list_allowlist(
        self,
        *,
        status: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[AllowlistEntry], int]:
        try:
            limit = int(limit)
        except (TypeError, ValueError):
            limit = 20
        limit = max(1, min(limit, 100))

        try:
            offset = int(offset)
        except (TypeError, ValueError):
            offset = 0
        offset = max(0, offset)

        status_normalized = (status or "").strip().lower()
        if status_normalized not in {"active", "revoked", "all"}:
            status_normalized = "active"

        filters: list[str] = []
        params: list[Any] = []

        if status_normalized == "active":
            filters.append("revoked_at IS NULL")
        elif status_normalized == "revoked":
            filters.append("revoked_at IS NOT NULL")

        search_value = (search or "").strip()
        if search_value:
            like = f"%{search_value.lower()}%"
            filters.append("(LOWER(email) LIKE ? OR LOWER(COALESCE(note, '')) LIKE ?)")
            params.extend([like, like])

        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""

        total_row = await self._fetch_one_dict(
            f"SELECT COUNT(*) AS count FROM auth_allowlist {where_clause}",
            tuple(params) if params else None,
        )
        total = int(total_row.get('count', 0) if total_row else 0)

        query_params: list[Any] = list(params)
        query_params.extend([limit, offset])

        rows = await self._fetch_all_dicts(
            f"""
            SELECT email, role, note, created_at, created_by, revoked_at, revoked_by, password_updated_at
            FROM auth_allowlist
            {where_clause}
            ORDER BY (revoked_at IS NULL) DESC, LOWER(email) ASC
            LIMIT ? OFFSET ?
            """,
            tuple(query_params),
        )
        return [self._row_to_allowlist(r) for r in rows], total

    async def upsert_allowlist(
        self,
        email: str,
        role: Optional[str],
        note: Optional[str],
        actor: Optional[str],
        password: Optional[str] = None,
        *,
        password_generated: bool = False,
    ) -> AllowlistEntry:
        normalized = self._normalize_email(email)
        if not normalized:
            raise AuthError("Email invalide.", status_code=400)

        existing = await self._get_allowlist_row(normalized)

        effective_role_raw = role if role is not None else (existing.get("role") if existing else None)
        effective_role = (effective_role_raw or "member").strip().lower()
        if effective_role not in {"member", "admin"}:
            raise AuthError("Role invalide. Utiliser 'member' ou 'admin'.", status_code=400)

        effective_note: Optional[str] = None
        if note is not None:
            effective_note = note.strip() if isinstance(note, str) else str(note)
        else:
            existing_note = existing.get("note") if existing else None
            effective_note = existing_note if isinstance(existing_note, str) else None
        password_hash: Optional[str] = None
        password_updated_at: Optional[str] = None
        password_length: Optional[int] = None
        if password is not None:
            if not isinstance(password, str):
                password = str(password)
            cleaned_password = password.strip()
            self._validate_password_strength(cleaned_password)
            password_hash = self._hash_password(cleaned_password)
            password_updated_at = self._now().isoformat()
            password_length = len(cleaned_password)

        await self._upsert_allowlist(
            normalized,
            role=effective_role,
            note=effective_note,
            actor=actor,
            password_hash=password_hash,
            password_updated_at=password_updated_at,
        )

        was_existing = existing is not None
        was_revoked = bool(existing and existing.get("revoked_at"))
        role_changed = bool(existing and (existing.get("role") or "member").lower() != effective_role)
        note_changed = bool(existing and (existing.get("note") or "") != (effective_note or ""))

        metadata: dict[str, Any] = {
            "role": effective_role,
            "password_updated": bool(password_hash),
            "password_generated": bool(password_hash and password_generated),
            "was_existing": was_existing,
        }
        if effective_note is not None:
            metadata["note"] = effective_note
        if was_revoked:
            metadata["reactivated"] = True
        if role_changed:
            metadata["role_changed"] = True
        if note_changed:
            metadata["note_changed"] = True

        event_type = "allowlist:add" if not was_existing else "allowlist:update"
        await self._write_audit(event_type, email=normalized, actor=actor, metadata=metadata)

        if password_hash and password_generated:
            generated_meta: dict[str, Any] = {"password_length": password_length or 0}
            if was_existing:
                generated_meta["was_existing"] = True
            if was_revoked:
                generated_meta["reactivated"] = True
            await self._write_audit(
                "allowlist:password_generated",
                email=normalized,
                actor=actor,
                metadata=generated_meta,
            )

        row = await self._get_allowlist_row(normalized)
        if not row:
            raise AuthError("Entree allowlist introuvable apres creation.", status_code=500)
        return self._row_to_allowlist(row)

    async def set_allowlist_password(self, email: str, password: str, actor: Optional[str] = None) -> AllowlistEntry:
        normalized = self._normalize_email(email)
        if not normalized:
            raise AuthError("Email invalide.", status_code=400)

        row = await self._get_allowlist_row(normalized)
        if not row:
            raise AuthError("Email non autorise.", status_code=404)

        self._validate_password_strength(password)
        password_hash = self._hash_password(password)
        updated_at = self._now().isoformat()

        await self._upsert_allowlist(
            normalized,
            role=row.get("role") or "member",
            note=row.get("note"),
            actor=actor,
            password_hash=password_hash,
            password_updated_at=updated_at,
        )
        await self._write_audit(
            "allowlist:password_set",
            email=normalized,
            actor=actor,
            metadata={"password_updated_at": updated_at},
        )
        updated_row = await self._get_allowlist_row(normalized)
        if not updated_row:
            raise AuthError("Entree allowlist introuvable apres mise a jour.", status_code=500)
        return self._row_to_allowlist(updated_row)

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
    async def _upsert_allowlist(
        self,
        email: str,
        role: str,
        note: Optional[str],
        actor: Optional[str],
        *,
        password_hash: Optional[str] = None,
        password_updated_at: Optional[str] = None,
    ) -> None:
        now = self._now().isoformat()
        await self.db.execute(
            """
            INSERT INTO auth_allowlist (email, role, note, created_at, created_by, revoked_at, revoked_by, password_hash, password_updated_at)
            VALUES (?, ?, ?, ?, ?, NULL, NULL, ?, ?)
            ON CONFLICT(email) DO UPDATE SET
                role = excluded.role,
                note = excluded.note,
                revoked_at = NULL,
                revoked_by = NULL,
                password_hash = CASE
                    WHEN excluded.password_hash IS NOT NULL THEN excluded.password_hash
                    ELSE auth_allowlist.password_hash
                END,
                password_updated_at = CASE
                    WHEN excluded.password_hash IS NOT NULL THEN excluded.password_updated_at
                    ELSE auth_allowlist.password_updated_at
                END
            """,
            (email, role, note, now, actor, password_hash, password_updated_at),
        )

    async def _get_allowlist_row(self, email: str) -> Optional[dict[str, Any]]:
        return await self._fetch_one_dict(
            "SELECT email, role, note, created_at, created_by, revoked_at, revoked_by, password_hash, password_updated_at FROM auth_allowlist WHERE email = ?",
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

    def _prepare_params(self, params: Sequence[Any] | None) -> tuple[Any, ...] | None:
        if params is None:
            return None
        if isinstance(params, tuple):
            return params
        if isinstance(params, (str, bytes, bytearray)):
            return (params,)
        try:
            return tuple(params)
        except TypeError:
            return (params,)  # type: ignore[arg-type]

    async def _fetch_one_dict(self, query: str, params: Sequence[Any] | None = None) -> Optional[dict[str, Any]]:
        tuple_params = self._prepare_params(params)
        row = await self.db.fetch_one(query, tuple_params)
        return self._row_to_dict(row)

    async def _fetch_all_dicts(self, query: str, params: Sequence[Any] | None = None) -> list[dict[str, Any]]:
        tuple_params = self._prepare_params(params)
        rows = await self.db.fetch_all(query, tuple_params)
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
        pwd_updated = row.get("password_updated_at")
        return AllowlistEntry(
            email=row["email"],
            role=row.get("role", "member"),
            note=row.get("note"),
            created_at=self._parse_dt(row.get("created_at")),
            created_by=row.get("created_by"),
            password_updated_at=self._parse_dt(pwd_updated) if pwd_updated else None,
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

    def _hash_password(self, password: str) -> str:
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def _verify_password(self, password: str, password_hash: str) -> bool:
        try:
            return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
        except (ValueError, TypeError):
            return False

    def _validate_password_strength(self, password: str) -> None:
        if len(password) < 8:
            raise AuthError('Mot de passe trop court (8 caracteres minimum).', status_code=400)

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
    dev_default_email_raw = os.getenv("AUTH_DEV_DEFAULT_EMAIL", "") or ""
    dev_default_email = dev_default_email_raw.strip().lower() or None
    return AuthConfig(
        secret=secret,
        issuer=issuer,
        audience=audience,
        token_ttl_seconds=ttl_days * 24 * 60 * 60,
        admin_emails=admin_emails,
        dev_mode=dev_mode,
        dev_default_email=dev_default_email,
    )

