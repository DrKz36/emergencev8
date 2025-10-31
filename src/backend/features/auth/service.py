from __future__ import annotations

import asyncio
import hashlib
import inspect
import json
import logging
import os
import secrets
import base64
import io
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, Optional, Sequence
from uuid import uuid4

import bcrypt
import jwt
import pyotp
import qrcode

from backend.core.database.manager import DatabaseManager

from .models import (
    AllowlistEntry,
    AuthConfig,
    LoginResponse,
    SessionInfo,
    User,
    UserRole,
)
from .rate_limiter import RateLimiterConfig, RateLimitExceeded, SlidingWindowRateLimiter

logger = logging.getLogger("emergence.auth")


class AuthError(Exception):
    def __init__(self, message: str, *, status_code: int = 400, payload: Optional[dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload or {}


class AuthService:
    def __init__(
        self,
        db_manager: DatabaseManager,
        config: Optional[AuthConfig | Mapping[str, Any]] = None,
        rate_limiter: Optional[SlidingWindowRateLimiter] = None,
    ) -> None:
        self.db = db_manager
        resolved_config = self._resolve_config(config)
        self.config = resolved_config
        self.jwt_algorithm = resolved_config.algorithm or "HS256"
        self.access_token_expire_minutes = max(1, resolved_config.token_ttl_seconds // 60)
        self.rate_limiter = rate_limiter or SlidingWindowRateLimiter(RateLimiterConfig())
        self._auth_sessions_has_user_id: Optional[bool] = None
        snapshot_backend = (resolved_config.allowlist_snapshot_backend or "").strip().lower() if resolved_config.allowlist_snapshot_backend else None
        self._allowlist_snapshot_backend: Optional[str] = snapshot_backend or None
        self._allowlist_snapshot_project: Optional[str] = resolved_config.allowlist_snapshot_project
        self._allowlist_snapshot_collection: str = (resolved_config.allowlist_snapshot_collection or "auth_config").strip() or "auth_config"
        self._allowlist_snapshot_document: str = (resolved_config.allowlist_snapshot_document or "allowlist").strip() or "allowlist"
        self._allowlist_snapshot_client: Optional[Any] = None
        self._allowlist_snapshot_lock = asyncio.Lock()
        self._allowlist_snapshot_columns: Optional[set[str]] = None

    def _resolve_config(self, config: Optional[AuthConfig | Mapping[str, Any]]) -> AuthConfig:
        payload: AuthConfig | Mapping[str, Any] | None = config
        if payload is None:
            payload = build_auth_config_from_env()
        if isinstance(payload, AuthConfig):
            return payload
        if isinstance(payload, Mapping):
            return self._config_from_mapping(payload)
        raise TypeError("Unsupported auth configuration payload.")

    @staticmethod
    def _config_from_mapping(payload: Mapping[str, Any]) -> AuthConfig:
        secret = payload.get("jwt_secret") or payload.get("secret") or payload.get("secret_key") or "change-me"
        issuer = payload.get("jwt_issuer") or payload.get("issuer") or "emergence.local"
        audience = payload.get("jwt_audience") or payload.get("audience") or "emergence-app"
        algorithm = payload.get("jwt_algorithm") or payload.get("algorithm") or "HS256"
        ttl_minutes = payload.get("access_token_expire_minutes")
        if ttl_minutes is None:
            ttl_seconds = int(payload.get("token_ttl_seconds", 7 * 24 * 60 * 60))
        else:
            ttl_seconds = max(60, int(ttl_minutes) * 60)
        admin_emails_raw = payload.get("admin_emails") or payload.get("allowlist", [])
        if isinstance(admin_emails_raw, str):
            admin_emails_iter = [email.strip() for email in admin_emails_raw.split(",")]
        else:
            admin_emails_iter = list(admin_emails_raw)
        admin_emails = {str(email).strip().lower() for email in admin_emails_iter if str(email).strip()}
        dev_mode = bool(payload.get("dev_mode") or payload.get("enable_dev_mode"))
        dev_default_email_raw = payload.get("dev_default_email") or payload.get("dev_email")
        dev_default_email = str(dev_default_email_raw).strip().lower() or None if dev_default_email_raw else None
        snapshot_backend_raw = payload.get("allowlist_snapshot_backend") or payload.get("allowlist_sync_backend")
        snapshot_backend = str(snapshot_backend_raw).strip().lower() if snapshot_backend_raw else None
        snapshot_project_raw = payload.get("allowlist_snapshot_project") or payload.get("allowlist_firestore_project")
        snapshot_project = str(snapshot_project_raw).strip() if snapshot_project_raw else None
        snapshot_collection_raw = payload.get("allowlist_snapshot_collection") or payload.get("allowlist_collection")
        snapshot_document_raw = payload.get("allowlist_snapshot_document") or payload.get("allowlist_document")
        snapshot_collection = (str(snapshot_collection_raw).strip() if snapshot_collection_raw else "auth_config") or "auth_config"
        snapshot_document = (str(snapshot_document_raw).strip() if snapshot_document_raw else "allowlist") or "allowlist"
        return AuthConfig(
            secret=secret,
            issuer=issuer,
            audience=audience,
            token_ttl_seconds=ttl_seconds,
            algorithm=algorithm,
            admin_emails=admin_emails,
            dev_mode=dev_mode,
            dev_default_email=dev_default_email,
            allowlist_snapshot_backend=snapshot_backend,
            allowlist_snapshot_project=snapshot_project,
            allowlist_snapshot_collection=snapshot_collection,
            allowlist_snapshot_document=snapshot_document,
        )

    def _load_allowlist_seed_entries(self) -> list[dict[str, Any]]:
        """Load allowlist seed entries from environment configuration."""
        raw_payload: Optional[str] = os.getenv("AUTH_ALLOWLIST_SEED")
        seed_path = os.getenv("AUTH_ALLOWLIST_SEED_PATH") or os.getenv("AUTH_ALLOWLIST_SEED_FILE")

        if not raw_payload and seed_path:
            try:
                with open(seed_path, "r", encoding="utf-8") as handle:
                    raw_payload = handle.read()
            except FileNotFoundError:
                logger.warning("Allowlist seed file not found at %s", seed_path)
            except Exception as exc:
                logger.warning("Unable to read allowlist seed file %s: %s", seed_path, exc)

        if not raw_payload:
            return []

        try:
            parsed = json.loads(raw_payload)
        except json.JSONDecodeError as exc:
            logger.warning("AUTH_ALLOWLIST_SEED contains invalid JSON: %s", exc)
            return []
        except Exception as exc:
            logger.warning("Unexpected error while parsing AUTH_ALLOWLIST_SEED: %s", exc)
            return []

        if isinstance(parsed, dict):
            parsed = [parsed]

        if not isinstance(parsed, list):
            logger.warning("AUTH_ALLOWLIST_SEED must be a list or object. Received: %s", type(parsed).__name__)
            return []

        entries: list[dict[str, Any]] = []
        for item in parsed:
            if not isinstance(item, dict):
                logger.warning("Skipping allowlist seed entry because it is not an object: %r", item)
                continue
            entries.append(item)
        return entries

    async def _seed_allowlist_from_env(self) -> None:
        entries = self._load_allowlist_seed_entries()
        if not entries:
            return

        for entry in entries:
            email_raw = entry.get("email")
            email = self._normalize_email(email_raw)
            if not email:
                logger.warning("Skipping allowlist seed entry with invalid email: %r", email_raw)
                continue

            password = entry.get("password")
            role = entry.get("role")
            note = entry.get("note")
            password_generated = bool(entry.get("password_generated"))

            actor = entry.get("actor") or "bootstrap:env"
            try:
                await self.upsert_allowlist(
                    email=email,
                    role=role,
                    note=note,
                    actor=actor,
                    password=password,
                    password_generated=password_generated,
                    sync_snapshot=False,
                )
                if password:
                    logger.info("Allowlist seed applied for %s (role=%s)", email, role or "member")
                else:
                    logger.info("Allowlist seed ensured for %s (role=%s, password unchanged)", email, role or "member")
            except AuthError as exc:
                logger.warning("Failed to seed allowlist entry for %s: %s", email, exc)
            except Exception as exc:
                logger.error("Unexpected error while seeding allowlist entry for %s: %s", email, exc, exc_info=True)

        # NOTE: Sync removed here - will be done once at the end of bootstrap()
        # This prevents overwriting Firestore snapshot before restore is called
    def _allowlist_snapshot_enabled(self) -> bool:
        return self._allowlist_snapshot_backend == "firestore"

    async def _get_allowlist_snapshot_client(self) -> Optional[Any]:
        if not self._allowlist_snapshot_enabled():
            return None
        if self._allowlist_snapshot_client is not None:
            return self._allowlist_snapshot_client

        try:
            from google.cloud import firestore  # type: ignore[attr-defined]
        except Exception as exc:  # pragma: no cover - optional dependency missing
            logger.warning("Allowlist snapshot disabled (firestore import failed): %s", exc)
            self._allowlist_snapshot_backend = None
            return None

        project_id = self._allowlist_snapshot_project or os.getenv("AUTH_ALLOWLIST_SNAPSHOT_PROJECT") or os.getenv("GOOGLE_CLOUD_PROJECT")
        try:
            client = firestore.AsyncClient(project=project_id)
        except AttributeError:
            logger.warning("Allowlist snapshot disabled (AsyncClient not available in google-cloud-firestore).")
            self._allowlist_snapshot_backend = None
            return None
        except Exception as exc:  # pragma: no cover - Firestore init failure
            logger.warning("Allowlist snapshot disabled (Firestore client init failed): %s", exc)
            self._allowlist_snapshot_backend = None
            return None

        self._allowlist_snapshot_client = client
        return client

    async def _get_allowlist_columns(self) -> set[str]:
        if self._allowlist_snapshot_columns is not None:
            return self._allowlist_snapshot_columns
        try:
            rows = await self.db.fetch_all("PRAGMA table_info(auth_allowlist)")
        except Exception as exc:
            logger.warning("Allowlist snapshot: unable to inspect auth_allowlist schema: %s", exc)
            self._allowlist_snapshot_columns = set()
            return set()

        columns: set[str] = set()
        for row in rows or []:
            info = self._row_to_dict(row)
            if not info:
                continue
            name = info.get("name")
            if isinstance(name, str) and name:
                columns.add(name)
        self._allowlist_snapshot_columns = columns
        return columns

    async def _fetch_allowlist_snapshot_rows(self) -> list[dict[str, Any]]:
        columns = await self._get_allowlist_columns()
        if not columns:
            return []

        base_columns = [
            "email",
            "role",
            "note",
            "created_at",
            "created_by",
            "revoked_at",
            "revoked_by",
            "password_hash",
            "password_updated_at",
            "password_must_reset",
        ]
        optional_columns = [
            "totp_secret",
            "totp_enabled_at",
            "backup_codes",
            "oauth_sub",
        ]
        selected = [col for col in base_columns if col in columns]
        selected.extend(col for col in optional_columns if col in columns and col not in selected)
        if not selected:
            return []

        query = f"SELECT {', '.join(selected)} FROM auth_allowlist"
        rows = await self._fetch_all_dicts(query)
        resolved: list[dict[str, Any]] = []
        for row in rows:
            payload = {key: row.get(key) for key in selected}
            resolved.append(payload)
        return resolved

    async def _persist_allowlist_snapshot(self) -> None:
        client = await self._get_allowlist_snapshot_client()
        if client is None:
            return

        rows = await self._fetch_allowlist_snapshot_rows()
        collection = self._allowlist_snapshot_collection or "auth_config"
        document = self._allowlist_snapshot_document or "allowlist"

        active: list[dict[str, Any]] = []
        revoked: list[dict[str, Any]] = []
        for row in rows:
            # Ensure only JSON-serializable values
            payload = {key: row.get(key) for key in row.keys()}
            if payload.get("revoked_at"):
                revoked.append(payload)
            else:
                active.append(payload)

        doc_ref = client.collection(collection).document(document)
        data = {
            "version": 1,
            "updated_at": self._now().isoformat(),
            "entries": active,
        }
        if revoked:
            data["revoked_entries"] = revoked
        await doc_ref.set(data, merge=False)

    async def _load_allowlist_snapshot(self) -> Optional[dict[str, Any]]:
        client = await self._get_allowlist_snapshot_client()
        if client is None:
            return None
        collection = self._allowlist_snapshot_collection or "auth_config"
        document = self._allowlist_snapshot_document or "allowlist"
        doc_ref = client.collection(collection).document(document)
        snapshot = await doc_ref.get()
        if not snapshot.exists:
            return None
        data = snapshot.to_dict() or {}
        if not isinstance(data, dict):
            return None
        return data

    async def _apply_allowlist_snapshot_entry(
        self,
        entry: dict[str, Any],
        columns: set[str],
        *,
        revoked: bool,
    ) -> bool:
        email = self._normalize_email(entry.get("email"))
        if not email:
            return False

        role = entry.get("role") or "member"
        note = entry.get("note")
        password_hash = entry.get("password_hash")
        password_updated_at = entry.get("password_updated_at")
        try:
            await self._upsert_allowlist(
                email,
                role=role,
                note=note,
                actor="bootstrap:snapshot",
                password_hash=password_hash,
                password_updated_at=password_updated_at,
            )
        except Exception as exc:
            logger.warning("Allowlist snapshot: unable to upsert %s from snapshot: %s", email, exc)
            return False

        update_fields: list[str] = []
        params: list[Any] = []
        mutable_columns = (
            "created_at",
            "created_by",
            "password_must_reset",
            "totp_secret",
            "totp_enabled_at",
            "backup_codes",
            "oauth_sub",
        )
        for column in mutable_columns:
            if column in columns and column in entry:
                value = entry.get(column)
                if column == "password_must_reset" and value is not None:
                    value = int(bool(value))
                update_fields.append(f"{column} = ?")
                params.append(value)

        if revoked and "revoked_at" in columns and "revoked_at" in entry:
            update_fields.append("revoked_at = ?")
            params.append(entry.get("revoked_at"))
        if revoked and "revoked_by" in columns and "revoked_by" in entry:
            update_fields.append("revoked_by = ?")
            params.append(entry.get("revoked_by"))
        if not revoked and "revoked_at" in columns:
            update_fields.append("revoked_at = NULL")
        if not revoked and "revoked_by" in columns:
            update_fields.append("revoked_by = NULL")

        if update_fields:
            params.append(email)
            assignments = ", ".join(update_fields)
            await self.db.execute(
                f"UPDATE auth_allowlist SET {assignments} WHERE email = ?",
                tuple(params),
                commit=True,
            )
        return True

    async def _restore_allowlist_from_snapshot(self) -> None:
        if not self._allowlist_snapshot_enabled():
            return
        snapshot = await self._load_allowlist_snapshot()
        if not snapshot:
            return

        entries = snapshot.get("entries") or []
        revoked_entries = snapshot.get("revoked_entries") or []
        if not isinstance(entries, list):
            entries = []
        if not isinstance(revoked_entries, list):
            revoked_entries = []

        columns = await self._get_allowlist_columns()
        restored = 0
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            if await self._apply_allowlist_snapshot_entry(entry, columns, revoked=False):
                restored += 1
        for entry in revoked_entries:
            if not isinstance(entry, dict):
                continue
            await self._apply_allowlist_snapshot_entry(entry, columns, revoked=True)
        if restored:
            logger.info("Allowlist snapshot restored %d entrie(s) from Firestore.", restored)

    async def _sync_allowlist_snapshot(self, *, reason: str) -> None:
        if not self._allowlist_snapshot_enabled():
            return
        async with self._allowlist_snapshot_lock:
            try:
                await self._persist_allowlist_snapshot()
            except Exception as exc:  # pragma: no cover - external service failure
                logger.warning("Allowlist snapshot sync failed (%s): %s", reason, exc)

    async def _auth_sessions_supports_user_id(self) -> bool:
        if self._auth_sessions_has_user_id is not None:
            return self._auth_sessions_has_user_id

        try:
            rows = await self.db.fetch_all("PRAGMA table_info(auth_sessions)")
        except Exception as exc:
            logger.warning("Unable to inspect auth_sessions schema: %s", exc)
            self._auth_sessions_has_user_id = False
            return False

        has_column = False
        for row in rows or []:
            name: Optional[str] = None
            try:
                # Row peut être dict-like ou avoir un attribut name
                if hasattr(row, "keys"):
                    name = dict(row).get("name")
                else:
                    name = getattr(row, "name", None)
            except Exception:
                name = getattr(row, "name", None)

            if isinstance(name, str) and name.lower() == "user_id":
                has_column = True
                break

        self._auth_sessions_has_user_id = has_column
        return has_column

    async def _backfill_auth_session_user_ids(self) -> None:
        if not await self._auth_sessions_supports_user_id():
            return

        rows = await self._fetch_all_dicts(
            "SELECT id, email, user_id FROM auth_sessions WHERE user_id IS NULL OR TRIM(user_id) = ''"
        )
        if not rows:
            return

        updates: list[tuple[str, str]] = []
        for row in rows:
            session_id = str(row.get("id") or "").strip()
            email = self._normalize_email(str(row.get("email") or ""))
            if not session_id or not email:
                continue
            updates.append((self._hash_subject(email), session_id))

        if not updates:
            return

        await self.db.executemany(
            "UPDATE auth_sessions SET user_id = ? WHERE id = ?",
            updates,
            commit=True,
        )
        logger.info("Backfilled user_id for %d auth session(s)", len(updates))

    # ------------------------------------------------------------------
    async def bootstrap(self) -> None:
        for email in self.config.admin_emails:
            normalized = self._normalize_email(email)
            if not normalized:
                continue
            await self._upsert_allowlist(normalized, role="admin", note="seed", actor="bootstrap")

        # Ensure all existing admins have password_must_reset set to 0
        await self.db.execute(
            "UPDATE auth_allowlist SET password_must_reset = 0 WHERE role = 'admin' AND password_must_reset != 0",
            commit=True,
        )

        # FIX: Restore snapshot BEFORE seeding to preserve manually added accounts
        # Order matters: restore from Firestore first, then seed missing entries, then sync back
        await self._restore_allowlist_from_snapshot()
        await self._seed_allowlist_from_env()
        await self._sync_allowlist_snapshot(reason="bootstrap")
        self._auth_sessions_has_user_id = None
        await self._backfill_auth_session_user_ids()

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

    def hash_password(self, password: str) -> str:
        try:
            self._validate_password_strength(password)
        except AuthError as exc:
            raise ValueError(str(exc)) from exc
        return self._hash_password(password)

    def verify_password(self, password: str, password_hash: str) -> bool:
        return self._verify_password(password, password_hash)

    def create_access_token(self, user_id: str, role: UserRole | str, expires_minutes: Optional[int] = None) -> str:
        if not user_id:
            raise ValueError("user_id must not be empty.")
        role_value = self._coerce_role(role).value
        minutes = self.access_token_expire_minutes if expires_minutes is None else max(1, int(expires_minutes))
        issued_at = self._now()
        expires_at = issued_at + timedelta(minutes=minutes)
        payload = {
            "iss": self.config.issuer,
            "aud": self.config.audience,
            "sub": user_id,
            "role": role_value,
            "iat": int(issued_at.timestamp()),
            "exp": int(expires_at.timestamp()),
        }
        token = jwt.encode(payload, self.config.secret, algorithm=self.jwt_algorithm)
        # Modern PyJWT always returns str, not bytes
        return str(token)

    def decode_token(self, token: str) -> Optional[dict[str, Any]]:
        if not token or not isinstance(token, str):
            return None
        try:
            from typing import cast
            return cast(dict[str, Any], jwt.decode(
                token,
                self.config.secret,
                algorithms=[self.jwt_algorithm],
                audience=self.config.audience,
                options={"verify_aud": bool(self.config.audience)},
            ))
        except jwt.PyJWTError:
            return None

    async def register_user(
        self,
        username: str,
        email: str,
        password: str,
        role: Optional[UserRole | str] = None,
    ) -> User:
        normalized_username = (username or "").strip()
        if not normalized_username:
            raise ValueError("username must not be empty.")
        normalized_email = self._normalize_email(email)
        if not normalized_email:
            raise ValueError("email must not be empty.")
        try:
            self._validate_password_strength(password)
        except AuthError as exc:
            raise ValueError(str(exc)) from exc

        existing_user = await self._fetch_user_by_username(normalized_username)
        if existing_user:
            raise ValueError("Username already exists.")

        existing_email = await self._fetch_user_by_email(normalized_email)
        if existing_email:
            raise ValueError("Email already registered.")

        hashed_password = self._hash_password(password)
        user_id = str(uuid4())
        now_dt = self._now()
        role_enum = self._coerce_role(role)

        try:
            await self.db.execute(
                """
                INSERT INTO auth_users (id, username, email, password_hash, role, is_active, created_at)
                VALUES (?, ?, ?, ?, ?, 1, ?)
                """,
                (
                    user_id,
                    normalized_username,
                    normalized_email,
                    hashed_password,
                    role_enum.value,
                    now_dt.isoformat(),
                ),
                commit=True,
            )
        except Exception as exc:
            logger.debug("auth_users insert skipped or failed (non blocking): %s", exc, exc_info=True)

        try:
            await self._upsert_allowlist(
                normalized_email,
                role_enum.value,
                note="register",
                actor="auth-service",
                password_hash=hashed_password,
                password_updated_at=now_dt.isoformat(),
            )
        except Exception as exc:
            logger.warning("Allowlist upsert failed during register_user: %s", exc)

        return User(
            id=user_id,
            username=normalized_username,
            email=normalized_email,
            role=role_enum,
            is_active=True,
            created_at=now_dt,
        )

    async def authenticate(self, username_or_email: str, password: str) -> Optional[User]:
        candidate = (username_or_email or "").strip()
        if not candidate or not password:
            return None

        user_row = await self._fetch_user_by_username(candidate)
        if not user_row:
            user_row = await self._fetch_user_by_email(candidate)

        if user_row:
            hashed = user_row.get("password_hash") or user_row.get("password")
            if hashed and self._verify_password(password, str(hashed)):
                return self._row_to_user(user_row)
            return None

        normalized_email = self._normalize_email(candidate)
        allow_row = await self._get_allowlist_row(normalized_email)
        if allow_row and allow_row.get("password_hash"):
            if self._verify_password(password, allow_row["password_hash"]):
                return User(
                    id=self._hash_subject(normalized_email),
                    username=normalized_email,
                    email=normalized_email,
                    role=self._coerce_role(allow_row.get("role")),
                    is_active=allow_row.get("revoked_at") is None,
                    created_at=self._parse_dt(allow_row.get("created_at")),
                )
        return None

    def has_permission(self, role: UserRole | str, resource: str) -> bool:
        normalized_role = self._coerce_role(role)
        if normalized_role is UserRole.ADMIN:
            return True
        resource_key = (resource or "").strip().lower()
        role_permissions: dict[str, set[str]] = {
            UserRole.MEMBER.value: {"chat", "cockpit", "memory", "documents"},
            UserRole.TESTER.value: {"chat", "cockpit", "memory", "experiments"},
            UserRole.GUEST.value: {"memory"},
        }
        allowed = role_permissions.get(normalized_role.value, set())
        return resource_key in allowed

    def _coerce_role(self, role: Optional[UserRole | str]) -> UserRole:
        if isinstance(role, UserRole):
            return role
        if not role:
            return UserRole.MEMBER
        candidate = str(role).strip().lower()
        for enum_role in UserRole:
            if enum_role.value == candidate or enum_role.name.lower() == candidate:
                return enum_role
        return UserRole.MEMBER

    async def _fetch_user_by_username(self, username: str) -> Optional[dict[str, Any]]:
        if not username:
            return None
        try:
            return await self._fetch_one_dict(
                """
                SELECT id, username, email, password_hash, role, is_active, created_at
                FROM auth_users
                WHERE LOWER(username) = LOWER(?)
                """,
                (username,),
            )
        except Exception as exc:
            logger.debug("auth_users lookup by username failed: %s", exc, exc_info=True)
            return None

    async def _fetch_user_by_email(self, email: str) -> Optional[dict[str, Any]]:
        normalized = self._normalize_email(email)
        if not normalized:
            return None
        try:
            return await self._fetch_one_dict(
                """
                SELECT id, username, email, password_hash, role, is_active, created_at
                FROM auth_users
                WHERE LOWER(email) = ?
                """,
                (normalized,),
            )
        except Exception as exc:
            logger.debug("auth_users lookup by email failed: %s", exc, exc_info=True)
            return None

    def _row_to_user(self, row: Mapping[str, Any]) -> User:
        email = self._normalize_email(str(row.get("email") or ""))
        username = str(row.get("username") or email or "user")
        user_id = str(row.get("id") or self._hash_subject(email or username))
        created_raw = row.get("created_at")
        created_at = self._parse_dt(created_raw) if created_raw else None
        is_active_raw = row.get("is_active")
        is_active = bool(is_active_raw) if is_active_raw is not None else True
        role_value = row.get("role")
        return User(
            id=user_id,
            username=username,
            email=email or username,
            role=self._coerce_role(role_value),
            is_active=is_active,
            created_at=created_at,
        )

    async def _restore_session_from_claims(
        self,
        email: str,
        session_id: str,
        role: str,
        claims: dict[str, Any],
    ) -> Optional[dict[str, Any]]:
        issued_at_ts = claims.get("iat")
        expires_at_ts = claims.get("exp")

        try:
            issued_at = datetime.fromtimestamp(int(issued_at_ts or 0), tz=timezone.utc)
        except Exception:
            issued_at = self._now()

        try:
            expires_at = datetime.fromtimestamp(int(expires_at_ts or 0), tz=timezone.utc)
        except Exception:
            expires_at = issued_at + timedelta(seconds=self.config.token_ttl_seconds)

        user_id = str((claims.get("sub") or claims.get("user_id") or "").strip())
        if not user_id:
            user_id = self._hash_subject(email)

        metadata = {
            "restored_from_claims": True,
            "restored_at": self._now().isoformat(),
        }

        metadata_json = json.dumps(metadata)
        supports_user_id = await self._auth_sessions_supports_user_id()
        insert_with_user_id = """
            INSERT OR IGNORE INTO auth_sessions (id, email, role, ip_address, user_id, user_agent, issued_at, expires_at, metadata)
            VALUES (?, ?, ?, NULL, ?, NULL, ?, ?, ?)
        """
        insert_without_user_id = """
            INSERT OR IGNORE INTO auth_sessions (id, email, role, ip_address, user_agent, issued_at, expires_at, metadata)
            VALUES (?, ?, ?, NULL, NULL, ?, ?, ?)
        """

        try:
            if supports_user_id:
                await self.db.execute(
                    insert_with_user_id,
                    (
                        session_id,
                        email,
                        role,
                        user_id or None,
                        issued_at.isoformat(),
                        expires_at.isoformat(),
                        metadata_json,
                    ),
                    commit=True,
                )
            else:
                await self.db.execute(
                    insert_without_user_id,
                    (
                        session_id,
                        email,
                        role,
                        issued_at.isoformat(),
                        expires_at.isoformat(),
                        metadata_json,
                    ),
                    commit=True,
                )
        except Exception as exc:
            if supports_user_id and "user_id" in str(exc).lower():
                logger.warning(
                    "auth_sessions.user_id column missing during restore, falling back to legacy schema: %s",
                    exc,
                )
                self._auth_sessions_has_user_id = False
                await self.db.execute(
                    insert_without_user_id,
                    (
                        session_id,
                        email,
                        role,
                        issued_at.isoformat(),
                        expires_at.isoformat(),
                        metadata_json,
                    ),
                    commit=True,
                )
            else:
                logger.warning(
                    "Unable to restore missing auth session %s for %s: %s",
                    session_id,
                    email,
                    exc,
                )
                return None

        select_columns = "expires_at, revoked_at, user_id"
        if not await self._auth_sessions_supports_user_id():
            select_columns = "expires_at, revoked_at"

        row = await self._fetch_one_dict(
            f"SELECT {select_columns} FROM auth_sessions WHERE id = ?",
            (session_id,),
        )
        if row is None:
            return None
        row.setdefault("user_id", None)
        return row

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

        # CRITICAL WRITE: Utilise execute_critical_write() pour sérialiser les écritures auth_sessions
        # Évite "database is locked" sur connexions concurrentes multiples
        supports_user_id = await self._auth_sessions_supports_user_id()
        metadata_payload = json.dumps(session_meta) if session_meta else None
        insert_with_user_id = """
            INSERT INTO auth_sessions (id, email, role, ip_address, user_id, user_agent, issued_at, expires_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        insert_without_user_id = """
            INSERT INTO auth_sessions (id, email, role, ip_address, user_agent, issued_at, expires_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """

        try:
            if supports_user_id:
                await self.db.execute_critical_write(
                    insert_with_user_id,
                    (
                        session_id,
                        email,
                        role,
                        ip_address,
                        claims.get("sub"),
                        user_agent,
                        now.isoformat(),
                        expires_at.isoformat(),
                        metadata_payload,
                    ),
                    commit=True,
                )
            else:
                await self.db.execute_critical_write(
                    insert_without_user_id,
                    (
                        session_id,
                        email,
                        role,
                        ip_address,
                        user_agent,
                        now.isoformat(),
                        expires_at.isoformat(),
                        metadata_payload,
                    ),
                    commit=True,
                )
        except Exception as exc:
            if supports_user_id and "user_id" in str(exc).lower():
                logger.warning(
                    "auth_sessions.user_id column missing during insert, falling back to legacy schema: %s",
                    exc,
                )
                self._auth_sessions_has_user_id = False
                await self.db.execute_critical_write(
                    insert_without_user_id,
                    (
                        session_id,
                        email,
                        role,
                        ip_address,
                        user_agent,
                        now.isoformat(),
                        expires_at.isoformat(),
                        metadata_payload,
                    ),
                    commit=True,
                )
            else:
                raise

        audit_meta: dict[str, Any] = {"session_id": session_id}
        if ip_address:
            audit_meta["ip"] = ip_address
        if audit_metadata:
            audit_meta.update({k: v for k, v in audit_metadata.items() if v is not None})

        user_claim = str(claims.get("sub") or "")
        # Audit log asynchrone pour login (non-bloquant) - réduit latence login de ~50-100ms
        await self._write_audit(event_type, email=email, metadata=audit_meta, _async=True)

        # Get password_must_reset status
        allow_row = await self._get_allowlist_row(email)
        password_must_reset = bool(allow_row.get("password_must_reset", False)) if allow_row else False

        return LoginResponse(
            token=token,
            expires_at=expires_at,
            role=role,
            session_id=session_id,
            user_id=user_claim,
            email=email,
            password_must_reset=password_must_reset,
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
            commit=True,
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
            commit=True,
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
            commit=True,
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

        role_value = allow_row.get("role") or claims.get("role") or "member"
        role = str(role_value).strip() or "member"

        select_columns = "expires_at, revoked_at, user_id"
        if not await self._auth_sessions_supports_user_id():
            select_columns = "expires_at, revoked_at"
        session = await self._fetch_one_dict(
            f"SELECT {select_columns} FROM auth_sessions WHERE id = ?",
            (session_id,),
        )
        if session and "user_id" not in session:
            session["user_id"] = None
        if not session:
            session = await self._restore_session_from_claims(
                email=email,
                session_id=session_id,
                role=role,
                claims=claims,
            )
            if session:
                logger.warning(
                    "Auth session %s restored from token claims (email=%s)",
                    session_id,
                    email,
                )
                session.setdefault("user_id", None)
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
        claims.update({
            "email": email,
            "role": role,
            "session_id": session_id,
            "expires_at": expires_at,
            "session_revoked": session_revoked,
        })
        if revoked_at:
            claims["revoked_at"] = revoked_at
        from typing import cast
        return cast(dict[str, Any], claims)

    async def get_user_id_for_session(self, session_id: str) -> Optional[str]:
        normalized = (session_id or "").strip()
        if not normalized:
            return None
        if not await self._auth_sessions_supports_user_id():
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
            SELECT email, role, note, created_at, created_by, revoked_at, revoked_by, password_updated_at, password_must_reset
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
        sync_snapshot: bool = True,
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
            # Defensive cast (password is Optional[str], narrowed to str here)
            cleaned_password = str(password).strip()
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
        if sync_snapshot:
            await self._sync_allowlist_snapshot(reason="upsert")
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

        # Password has been set - clear the must_reset flag
        await self.db.execute(
            "UPDATE auth_allowlist SET password_must_reset = 0 WHERE email = ?",
            (normalized,),
            commit=True,
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
        await self._sync_allowlist_snapshot(reason="set_password")
        return self._row_to_allowlist(updated_row)

    async def change_own_password(
        self,
        email: str,
        current_password: str,
        new_password: str,
    ) -> bool:
        """Change password for the authenticated user."""
        normalized = self._normalize_email(email)
        if not normalized:
            raise AuthError("Email invalide.", status_code=400)

        # Verify current password
        allow_row = await self._get_allowlist_row(normalized)
        if not allow_row:
            raise AuthError("Email non autorise.", status_code=401)

        if allow_row.get("revoked_at"):
            raise AuthError("Compte temporairement desactive.", status_code=423)

        password_hash = allow_row.get("password_hash")
        if not password_hash or not self._verify_password(current_password, password_hash):
            raise AuthError("Mot de passe actuel incorrect.", status_code=401)

        # Validate and set new password
        self._validate_password_strength(new_password)
        new_password_hash = self._hash_password(new_password)
        updated_at = self._now().isoformat()

        await self._upsert_allowlist(
            normalized,
            role=allow_row.get("role") or "member",
            note=allow_row.get("note"),
            actor=normalized,
            password_hash=new_password_hash,
            password_updated_at=updated_at,
        )

        # Ensure password_must_reset is set to 0 after self-service password change
        await self.db.execute(
            "UPDATE auth_allowlist SET password_must_reset = 0 WHERE email = ?",
            (normalized,),
            commit=True,
        )

        await self._write_audit(
            "password:changed",
            email=normalized,
            actor=normalized,
            metadata={"password_updated_at": updated_at, "source": "self_service"},
        )

        await self._sync_allowlist_snapshot(reason="change_password")
        return True

    async def remove_allowlist(self, email: str, actor: Optional[str]) -> None:
        normalized = self._normalize_email(email)
        await self.db.execute(
            "UPDATE auth_allowlist SET revoked_at = ?, revoked_by = ? WHERE email = ?",
            (self._now().isoformat(), actor, normalized),
            commit=True,
        )
        await self.revoke_sessions_for_email(normalized, actor=actor)
        await self._write_audit("allowlist:remove", email=normalized, actor=actor)
        await self._sync_allowlist_snapshot(reason="remove")

    async def create_password_reset_token(self, email: str) -> str:
        """
        Create a password reset token for the given email.
        Token is valid for 1 hour.

        Returns:
            The reset token
        """
        normalized = self._normalize_email(email)
        if not normalized:
            raise AuthError("Email invalide.", status_code=400)

        # Check if user exists in allowlist
        allow_row = await self._get_allowlist_row(normalized)
        if not allow_row:
            raise AuthError("Email non autorise.", status_code=404)

        if allow_row.get("revoked_at"):
            raise AuthError("Compte temporairement desactive.", status_code=423)

        # Generate secure token
        token = secrets.token_urlsafe(32)
        now = self._now()
        expires_at = now + timedelta(hours=1)

        # Store token in database
        await self.db.execute(
            """
            INSERT INTO password_reset_tokens (token, email, expires_at, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (token, normalized, expires_at.isoformat(), now.isoformat()),
            commit=True,
        )

        # Audit log
        await self._write_audit(
            "password:reset_requested",
            email=normalized,
            actor=normalized,
            metadata={"expires_at": expires_at.isoformat()},
        )

        return token

    async def verify_password_reset_token(self, token: str) -> Optional[str]:
        """
        Verify a password reset token and return the associated email if valid.

        Returns:
            The email associated with the token, or None if invalid/expired
        """
        if not token:
            return None

        row = await self._fetch_one_dict(
            """
            SELECT email, expires_at, used_at
            FROM password_reset_tokens
            WHERE token = ?
            """,
            (token,),
        )

        if not row:
            return None

        # Check if already used
        if row.get("used_at"):
            return None

        # Check if expired
        expires_at = self._parse_dt(row.get("expires_at"))
        if expires_at < self._now():
            return None

        return row.get("email")

    async def reset_password_with_token(self, token: str, new_password: str) -> bool:
        """
        Reset password using a valid token.

        Returns:
            True if password was reset successfully
        """
        email = await self.verify_password_reset_token(token)
        if not email:
            raise AuthError("Token invalide ou expire.", status_code=400)

        # Validate new password
        self._validate_password_strength(new_password)

        # Get allowlist entry
        allow_row = await self._get_allowlist_row(email)
        if not allow_row:
            raise AuthError("Email non autorise.", status_code=404)

        # Hash new password
        password_hash = self._hash_password(new_password)
        updated_at = self._now().isoformat()

        # Update password in allowlist and set password_must_reset to False
        await self._upsert_allowlist(
            email,
            role=allow_row.get("role") or "member",
            note=allow_row.get("note"),
            actor=email,
            password_hash=password_hash,
            password_updated_at=updated_at,
        )

        # Set password_must_reset to False
        await self.db.execute(
            "UPDATE auth_allowlist SET password_must_reset = 0 WHERE email = ?",
            (email,),
            commit=True,
        )

        # Mark token as used
        await self.db.execute(
            """
            UPDATE password_reset_tokens
            SET used_at = ?
            WHERE token = ?
            """,
            (self._now().isoformat(), token),
            commit=True,
        )

        # Audit log
        await self._write_audit(
            "password:reset_completed",
            email=email,
            actor=email,
            metadata={"password_updated_at": updated_at, "source": "reset_token"},
        )

        # Revoke all existing sessions for security
        await self.revoke_sessions_for_email(email, actor=email)

        return True

    async def list_sessions(self, active_only: bool = False) -> list[SessionInfo]:
        columns = "id, email, role, ip_address, issued_at, expires_at, revoked_at, revoked_by"
        if await self._auth_sessions_supports_user_id():
            columns = columns + ", user_id"
        if active_only:
            rows = await self._fetch_all_dicts(
                f"SELECT {columns} FROM auth_sessions WHERE revoked_at IS NULL ORDER BY issued_at DESC"
            )
        else:
            rows = await self._fetch_all_dicts(
                f"SELECT {columns} FROM auth_sessions ORDER BY issued_at DESC"
            )
        normalized_rows: list[dict[str, Any]] = []
        for payload in rows:
            if "user_id" not in payload:
                payload["user_id"] = None
            normalized_rows.append(payload)
        return [self._row_to_session(r) for r in normalized_rows]

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
        # Admin users should never be forced to reset password
        # For new entries: members must reset (1), admins don't (0)
        password_must_reset = 0 if role == "admin" else 1

        await self.db.execute(
            """
            INSERT INTO auth_allowlist (email, role, note, created_at, created_by, revoked_at, revoked_by, password_hash, password_updated_at, password_must_reset)
            VALUES (?, ?, ?, ?, ?, NULL, NULL, ?, ?, ?)
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
                END,
                password_must_reset = CASE
                    WHEN excluded.role = 'admin' THEN 0
                    WHEN excluded.password_hash IS NOT NULL THEN 0
                    ELSE auth_allowlist.password_must_reset
                END
            """,
            (email, role, note, now, actor, password_hash, password_updated_at, password_must_reset),
            commit=True,
        )

    async def _get_allowlist_row(self, email: str) -> Optional[dict[str, Any]]:
        return await self._fetch_one_dict(
            "SELECT email, role, note, created_at, created_by, revoked_at, revoked_by, password_hash, password_updated_at, password_must_reset FROM auth_allowlist WHERE email = ?",
            (email,),
        )

    async def _write_audit(
        self,
        event_type: str,
        *,
        email: Optional[str],
        actor: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
        _async: bool = False,
    ) -> None:
        """
        Écrit un événement d'audit dans auth_audit_log.

        Args:
            _async: Si True, exécute en arrière-plan (non-bloquant).
                   Recommandé pour événements non-critiques (login success, etc.)
        """
        try:
            if _async:
                # Audit asynchrone non-bloquant (fire-and-forget)
                # Utilisé pour login success, logout, etc.
                import asyncio
                asyncio.create_task(
                    self.db.execute(
                        "INSERT INTO auth_audit_log (event_type, email, actor, metadata, created_at) VALUES (?, ?, ?, ?, ?)",
                        (
                            event_type,
                            email,
                            actor,
                            json.dumps(metadata) if metadata else None,
                            self._now().isoformat(),
                        ),
                        commit=True,
                    )
                )
            else:
                # Audit synchrone bloquant pour événements critiques
                # (allowlist changes, password changes, etc.)
                await self.db.execute(
                    "INSERT INTO auth_audit_log (event_type, email, actor, metadata, created_at) VALUES (?, ?, ?, ?, ?)",
                    (
                        event_type,
                        email,
                        actor,
                        json.dumps(metadata) if metadata else None,
                        self._now().isoformat(),
                    ),
                    commit=True,
                )
        except Exception as exc:
            logger.warning("Auth audit log failure (%s): %s", event_type, exc)

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
            return (params,)

    async def _db_fetchone(self, query: str, params: Sequence[Any] | None = None) -> Optional[Any]:
        tuple_params = self._prepare_params(params)
        fetch_one = getattr(self.db, "fetch_one", None)
        if callable(fetch_one):
            return await fetch_one(query, tuple_params)
        fetchone = getattr(self.db, "fetchone", None)
        if callable(fetchone):
            result = fetchone(query, tuple_params)
            if inspect.isawaitable(result):
                return await result
            return result
        return None

    async def _db_fetchall(self, query: str, params: Sequence[Any] | None = None) -> list[Any]:
        tuple_params = self._prepare_params(params)
        fetch_all = getattr(self.db, "fetch_all", None)
        if callable(fetch_all):
            rows = await fetch_all(query, tuple_params)
            return list(rows or [])
        fetchall = getattr(self.db, "fetchall", None)
        if callable(fetchall):
            result = fetchall(query, tuple_params)
            if inspect.isawaitable(result):
                result = await result
            return list(result or [])
        return []

    async def _fetch_one_dict(self, query: str, params: Sequence[Any] | None = None) -> Optional[dict[str, Any]]:
        row = await self._db_fetchone(query, params)
        return self._row_to_dict(row)

    async def _fetch_all_dicts(self, query: str, params: Sequence[Any] | None = None) -> list[dict[str, Any]]:
        rows = await self._db_fetchall(query, params)
        return [d for d in (self._row_to_dict(r) for r in rows or []) if d]

    def _row_to_dict(self, row: Any) -> Optional[dict[str, Any]]:
        if row is None:
            return None
        if isinstance(row, dict):
            return row
        try:
            keys = row.keys()
            return {key: row[key] for key in keys}
        except Exception:
            try:
                return dict(row)
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
            password_must_reset=bool(row.get("password_must_reset", True)),
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
            user_id=str(row.get("user_id") or "").strip() or None,
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

    def _normalize_email(self, email: str | None) -> str:
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

    # =========================================================================
    # 2FA / TOTP METHODS (Phase P2 - Feature 9)
    # =========================================================================

    async def enable_2fa(self, email: str) -> dict[str, Any]:
        """
        Enable 2FA for a user by generating a TOTP secret and backup codes.

        Returns:
            dict with:
                - secret: TOTP secret (base32 encoded)
                - qr_code: QR code image data (base64 encoded PNG)
                - backup_codes: list of 10 backup codes
                - provisioning_uri: otpauth:// URI for manual entry
        """
        normalized = email.strip().lower()

        # Get user from allowlist
        allow_row = await self._fetch_one_dict(
            "SELECT email, role FROM auth_allowlist WHERE email = ? AND revoked_at IS NULL",
            (normalized,)
        )

        if not allow_row:
            raise AuthError("User not found", status_code=404)

        # Generate TOTP secret (16 bytes = 128 bits)
        secret = pyotp.random_base32()

        # Generate backup codes (10 codes, 8 characters each)
        backup_codes = [secrets.token_hex(4).upper() for _ in range(10)]

        # Create provisioning URI for QR code
        totp = pyotp.TOTP(secret)
        issuer_name = "Emergence V8"
        provisioning_uri = totp.provisioning_uri(
            name=normalized,
            issuer_name=issuer_name
        )

        # Generate QR code image
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        qr_code_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

        # Store in database (not enabled yet, will be enabled after verification)
        await self.db.execute(
            """
            UPDATE auth_allowlist
            SET totp_secret = ?, backup_codes = ?
            WHERE email = ?
            """,
            (secret, json.dumps(backup_codes), normalized),
            commit=True
        )

        # Audit log
        await self._write_audit(
            "2fa:setup_initiated",
            email=normalized,
            actor=normalized,
            metadata={"backup_codes_count": len(backup_codes)}
        )

        await self._sync_allowlist_snapshot(reason="enable_2fa")
        return {
            "secret": secret,
            "qr_code": qr_code_base64,
            "backup_codes": backup_codes,
            "provisioning_uri": provisioning_uri
        }

    async def verify_and_enable_2fa(self, email: str, totp_code: str) -> bool:
        """
        Verify TOTP code and enable 2FA if valid.

        Args:
            email: User email
            totp_code: 6-digit TOTP code from authenticator app

        Returns:
            True if verification successful and 2FA enabled
        """
        normalized = email.strip().lower()

        # Get user with totp_secret
        allow_row = await self._fetch_one_dict(
            "SELECT email, totp_secret, totp_enabled_at FROM auth_allowlist WHERE email = ? AND revoked_at IS NULL",
            (normalized,)
        )

        if not allow_row:
            raise AuthError("User not found", status_code=404)

        secret = allow_row.get("totp_secret")
        if not secret:
            raise AuthError("2FA not initiated. Call enable_2fa first.", status_code=400)

        # Verify TOTP code
        totp = pyotp.TOTP(secret)
        if not totp.verify(totp_code, valid_window=1):  # Allow 1 window tolerance (30s before/after)
            await self._write_audit(
                "2fa:verification_failed",
                email=normalized,
                actor=normalized,
                metadata={}
            )
            return False

        # Enable 2FA
        now = self._now()
        await self.db.execute(
            """
            UPDATE auth_allowlist
            SET totp_enabled_at = ?
            WHERE email = ?
            """,
            (now.isoformat(), normalized),
            commit=True
        )

        # Audit log
        await self._write_audit(
            "2fa:enabled",
            email=normalized,
            actor=normalized,
            metadata={"enabled_at": now.isoformat()}
        )

        await self._sync_allowlist_snapshot(reason="verify_enable_2fa")
        return True

    async def verify_2fa_code(self, email: str, code: str) -> bool:
        """
        Verify a 2FA TOTP code or backup code.

        Args:
            email: User email
            code: 6-digit TOTP code OR 8-character backup code

        Returns:
            True if code is valid
        """
        normalized = email.strip().lower()

        # Get user
        allow_row = await self._fetch_one_dict(
            "SELECT email, totp_secret, totp_enabled_at, backup_codes FROM auth_allowlist WHERE email = ? AND revoked_at IS NULL",
            (normalized,)
        )

        if not allow_row:
            raise AuthError("User not found", status_code=404)

        totp_enabled_at = allow_row.get("totp_enabled_at")
        if not totp_enabled_at:
            raise AuthError("2FA not enabled for this user", status_code=400)

        secret = allow_row.get("totp_secret")
        backup_codes_json = allow_row.get("backup_codes")

        # Try TOTP code first (6 digits)
        if len(code) == 6 and code.isdigit():
            if not secret or not isinstance(secret, str):
                raise AuthError("Invalid TOTP secret", status_code=500)
            totp = pyotp.TOTP(secret)
            if totp.verify(code, valid_window=1):
                await self._write_audit(
                    "2fa:verified",
                    email=normalized,
                    actor=normalized,
                    metadata={"method": "totp"}
                )
                return True

        # Try backup code (8 characters hex)
        if len(code) == 8 and backup_codes_json:
            backup_codes = json.loads(backup_codes_json)
            code_upper = code.upper()

            if code_upper in backup_codes:
                # Remove used backup code
                backup_codes.remove(code_upper)
                await self.db.execute(
                    "UPDATE auth_allowlist SET backup_codes = ? WHERE email = ?",
                    (json.dumps(backup_codes), normalized),
                    commit=True
                )

                await self._write_audit(
                    "2fa:backup_code_used",
                    email=normalized,
                    actor=normalized,
                    metadata={"remaining_codes": len(backup_codes)}
                )

                await self._sync_allowlist_snapshot(reason="backup_code_used")
                return True

        # Verification failed
        await self._write_audit(
            "2fa:verification_failed",
            email=normalized,
            actor=normalized,
            metadata={"code_length": len(code)}
        )

        return False

    async def disable_2fa(self, email: str, password: str) -> bool:
        """
        Disable 2FA for a user (requires password confirmation).

        Args:
            email: User email
            password: User's password for confirmation

        Returns:
            True if 2FA disabled successfully
        """
        normalized = email.strip().lower()

        # Verify password first
        allow_row = await self._fetch_one_dict(
            "SELECT email, password_hash, totp_enabled_at FROM auth_allowlist WHERE email = ? AND revoked_at IS NULL",
            (normalized,)
        )

        if not allow_row:
            raise AuthError("User not found", status_code=404)

        password_hash = allow_row.get("password_hash")
        if not password_hash or not self._verify_password(password, password_hash):
            raise AuthError("Invalid password", status_code=401)

        totp_enabled_at = allow_row.get("totp_enabled_at")
        if not totp_enabled_at:
            raise AuthError("2FA not enabled", status_code=400)

        # Disable 2FA
        await self.db.execute(
            """
            UPDATE auth_allowlist
            SET totp_secret = NULL, backup_codes = NULL, totp_enabled_at = NULL
            WHERE email = ?
            """,
            (normalized,),
            commit=True
        )

        # Audit log
        await self._write_audit(
            "2fa:disabled",
            email=normalized,
            actor=normalized,
            metadata={}
        )

        await self._sync_allowlist_snapshot(reason="disable_2fa")
        return True

    async def get_2fa_status(self, email: str) -> dict[str, Any]:
        """
        Get 2FA status for a user.

        Returns:
            dict with:
                - enabled: bool
                - enabled_at: ISO timestamp or None
                - backup_codes_remaining: int
        """
        normalized = email.strip().lower()

        allow_row = await self._fetch_one_dict(
            "SELECT totp_enabled_at, backup_codes FROM auth_allowlist WHERE email = ? AND revoked_at IS NULL",
            (normalized,)
        )

        if not allow_row:
            raise AuthError("User not found", status_code=404)

        totp_enabled_at = allow_row.get("totp_enabled_at")
        backup_codes_json = allow_row.get("backup_codes")

        backup_codes_remaining = 0
        if backup_codes_json:
            try:
                backup_codes = json.loads(backup_codes_json)
                backup_codes_remaining = len(backup_codes)
            except (json.JSONDecodeError, TypeError):
                pass

        return {
            "enabled": bool(totp_enabled_at),
            "enabled_at": totp_enabled_at,
            "backup_codes_remaining": backup_codes_remaining
        }


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
    algorithm = os.getenv("AUTH_JWT_ALGORITHM", "HS256") or "HS256"
    snapshot_backend_raw = os.getenv("AUTH_ALLOWLIST_SNAPSHOT_BACKEND", "")
    snapshot_backend = snapshot_backend_raw.strip().lower() or None
    snapshot_collection = os.getenv("AUTH_ALLOWLIST_SNAPSHOT_COLLECTION", "auth_config") or "auth_config"
    snapshot_document = os.getenv("AUTH_ALLOWLIST_SNAPSHOT_DOCUMENT", "allowlist") or "allowlist"
    snapshot_project_raw = os.getenv("AUTH_ALLOWLIST_SNAPSHOT_PROJECT", "")
    snapshot_project = snapshot_project_raw.strip() or None
    return AuthConfig(
        secret=secret,
        issuer=issuer,
        audience=audience,
        token_ttl_seconds=ttl_days * 24 * 60 * 60,
        algorithm=algorithm,
        admin_emails=admin_emails,
        dev_mode=dev_mode,
        dev_default_email=dev_default_email,
        allowlist_snapshot_backend=snapshot_backend,
        allowlist_snapshot_collection=snapshot_collection.strip() or "auth_config",
        allowlist_snapshot_document=snapshot_document.strip() or "allowlist",
        allowlist_snapshot_project=snapshot_project,
    )
