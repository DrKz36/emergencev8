#!/usr/bin/env python3
"""
Utility script to purge QA upload artefacts (ex: test_upload.txt) from Emergence.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import httpx

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import qa_metrics_validation as qa  # noqa: E402


def _default_pattern() -> str:
    return "test_upload"


def _select_name(entry: Dict[str, Any]) -> str:
    for key in ("filename", "original_filename", "display_name", "title", "name"):
        value = entry.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def _parse_datetime(raw: Any) -> Optional[datetime]:
    if not raw:
        return None
    if isinstance(raw, datetime):
        return raw
    if isinstance(raw, (int, float)):
        try:
            return datetime.fromtimestamp(float(raw), tz=timezone.utc)
        except (ValueError, OSError):
            return None
    if isinstance(raw, str):
        for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc)
            except ValueError:
                continue
    return None


def filter_documents(
    entries: Iterable[Dict[str, Any]], *, pattern: str, min_id: Optional[int]
) -> List[Dict[str, Any]]:
    matches: List[Dict[str, Any]] = []
    needle = pattern.casefold()
    for entry in entries or []:
        doc_id = entry.get("id")
        if isinstance(doc_id, str) and doc_id.isdigit():
            doc_id = int(doc_id)
        if min_id is not None and isinstance(doc_id, int) and doc_id < min_id:
            continue
        name = _select_name(entry)
        if needle in name.casefold():
            matches.append(entry)
    return matches


async def purge_documents(args: argparse.Namespace) -> int:
    base_url = qa._normalize_base_url(args.base_url)  # type: ignore[attr-defined]
    timeout = httpx.Timeout(args.http_timeout)
    async with httpx.AsyncClient(base_url=base_url, timeout=timeout) as client:
        auth = await qa.attempt_password_login(client, args.login_email, args.login_password)
        if auth is None and not args.no_dev_login:
            auth = await qa.attempt_dev_login(client)
    if auth is None:
        print("Authentication failed; aborting purge.", file=sys.stderr)
        return 1

    headers = {
        "Authorization": f"Bearer {auth.token}",
        "X-Session-Id": auth.session_id,
    }
    async with httpx.AsyncClient(base_url=base_url, timeout=timeout) as client:
        resp = await client.get("/api/documents", headers=headers, params={"limit": args.limit})
        resp.raise_for_status()
        payload = resp.json()
        if isinstance(payload, dict):
            entries = payload.get("items", [])
        elif isinstance(payload, list):
            entries = payload
        else:
            raise RuntimeError(f"Unexpected documents payload: {payload}")
        to_remove = filter_documents(entries, pattern=args.pattern, min_id=args.min_id)

        if not to_remove:
            print("No matching documents found.")
            return 0

        print(f"Matched {len(to_remove)} document(s) for deletion.")
        if args.dry_run:
            for entry in to_remove:
                doc_id = entry.get("id")
                name = _select_name(entry)
                created = _parse_datetime(entry.get("created_at"))
                print(f"[DRY-RUN] id={doc_id} name={name} created={created}")
            return 0

        deleted = 0
        for entry in to_remove:
            doc_id = entry.get("id")
            if not doc_id:
                continue
            resp = await client.delete(f"/api/documents/{doc_id}", headers=headers)
            if resp.status_code in (200, 204):
                deleted += 1
                name = _select_name(entry)
                print(f"Deleted document {doc_id} ({name})")
            else:
                print(f"Failed to delete {doc_id}: {resp.status_code} {resp.text[:120]}")
        print(f"Deleted {deleted} / {len(to_remove)} documents.")
        return 0 if deleted == len(to_remove) else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Purge les documents QA (test_upload, etc.) via l'API Emergence."
    )
    parser.add_argument("--base-url", default=qa.DEFAULT_BASE_URL, help="Base URL de l'API Emergence.")
    parser.add_argument("--login-email", default=qa.DEFAULT_LOGIN_EMAIL, help="Email pour /api/auth/login.")
    parser.add_argument("--login-password", default=qa.DEFAULT_LOGIN_PASSWORD, help="Mot de passe authentifié.")
    parser.add_argument("--pattern", default=_default_pattern(), help="Motif à rechercher dans les noms de documents.")
    parser.add_argument("--min-id", type=int, help="Supprime uniquement les documents avec un ID >= min-id.")
    parser.add_argument("--limit", type=int, default=200, help="Limite de documents récupérés (pagination simple).")
    parser.add_argument("--dry-run", action="store_true", help="Affiche les documents ciblés sans supprimer.")
    parser.add_argument(
        "--no-dev-login",
        action="store_true",
        help="N'utilise pas le fallback dev login lorsque l'auth standard échoue.",
    )
    parser.add_argument("--http-timeout", type=float, default=45.0, help="Timeout HTTP (s).")
    return parser


def main(argv: Optional[List[str]] = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    exit_code = asyncio.run(purge_documents(args))
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
