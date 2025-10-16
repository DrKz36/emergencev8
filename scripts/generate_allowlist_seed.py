"""
Utility to export the current auth_allowlist entries to a bootstrap JSON payload
and optionally publish it to Google Secret Manager.

Usage examples:
    python scripts/generate_allowlist_seed.py --output allowlist_seed.json
    python scripts/generate_allowlist_seed.py --push AUTH_ALLOWLIST_SEED
"""

from __future__ import annotations

import argparse
import json
import secrets
import sqlite3
import string
import subprocess
import sys
from pathlib import Path
from typing import Iterable, List, Optional

DEFAULT_DB_PATHS: tuple[Path, ...] = (
    Path("src/backend/data/db/emergence_v7.db"),
    Path("data/emergence.db"),
)

PASSWORD_ALPHABET = string.ascii_letters + string.digits + "!@#$%_-+"


def generate_password(length: int = 16) -> str:
    if length < 8:
        length = 8
    while True:
        candidate = "".join(secrets.choice(PASSWORD_ALPHABET) for _ in range(length))
        if (
            any(c.islower() for c in candidate)
            and any(c.isupper() for c in candidate)
            and any(c.isdigit() for c in candidate)
            and any(c in "!@#$%_-+" for c in candidate)
        ):
            return candidate


def load_allowlist_entries(
    db_paths: Iterable[Path],
    *,
    include_revoked: bool = False,
) -> List[dict]:
    entries: List[dict] = []
    for db_path in db_paths:
        if not db_path.exists():
            continue
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.cursor()
            query = """
                SELECT email, role, note, revoked_at
                FROM auth_allowlist
                ORDER BY lower(email)
            """
            for row in cursor.execute(query):
                email = (row["email"] or "").strip().lower()
                if not email:
                    continue
                revoked_at = row["revoked_at"]
                if revoked_at and not include_revoked:
                    continue
                role = (row["role"] or "member").strip().lower()
                note = (row["note"] or "").strip() or None
                entries.append(
                    {
                        "email": email,
                        "role": role if role in {"admin", "member"} else "member",
                        "note": note,
                    }
                )
        finally:
            conn.close()
    # Deduplicate by email (keep first occurrence)
    seen = set()
    deduped: List[dict] = []
    for entry in entries:
        if entry["email"] in seen:
            continue
        seen.add(entry["email"])
        deduped.append(entry)
    return deduped


def build_seed_payload(entries: List[dict], password_length: int) -> List[dict]:
    payload: List[dict] = []
    for entry in entries:
        payload.append(
            {
                "email": entry["email"],
                "role": entry["role"],
                "note": entry.get("note"),
                "password": generate_password(password_length),
            }
        )
    return payload


def push_to_secret_manager(
    payload_json: str,
    secret_name: str,
    *,
    project: str,
    create_if_missing: bool,
) -> None:
    if create_if_missing:
        try:
            subprocess.run(
                [
                    "gcloud",
                    "secrets",
                    "describe",
                    secret_name,
                    f"--project={project}",
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except subprocess.CalledProcessError:
            subprocess.run(
                [
                    "gcloud",
                    "secrets",
                    "create",
                    secret_name,
                    "--replication-policy=automatic",
                    f"--project={project}",
                ],
                check=True,
            )
    subprocess.run(
        [
            "gcloud",
            "secrets",
            "versions",
            "add",
            secret_name,
            "--data-file=-",
            f"--project={project}",
        ],
        input=payload_json.encode("utf-8"),
        check=True,
    )


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Generate AUTH_ALLOWLIST_SEED payload.")
    parser.add_argument(
        "--db",
        action="append",
        dest="db_paths",
        help="Path(s) to SQLite database(s) containing auth_allowlist (default: emergence_v7.db).",
    )
    parser.add_argument(
        "--include-revoked",
        action="store_true",
        help="Include revoked accounts in the export.",
    )
    parser.add_argument(
        "--password-length",
        type=int,
        default=16,
        help="Generated password length (default: 16).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Write payload JSON to this file.",
    )
    parser.add_argument(
        "--push",
        metavar="SECRET_NAME",
        help="Push the payload as a new Secret Manager version (gcloud CLI required).",
    )
    parser.add_argument(
        "--project",
        default="emergence-469005",
        help="GCP project when using --push (default: emergence-469005).",
    )
    parser.add_argument(
        "--create-secret",
        action="store_true",
        help="Create the secret if it does not exist (used with --push).",
    )

    args = parser.parse_args(argv)

    db_paths = (
        [Path(p) for p in args.db_paths] if args.db_paths else list(DEFAULT_DB_PATHS)
    )
    entries = load_allowlist_entries(
        db_paths,
        include_revoked=args.include_revoked,
    )
    if not entries:
        print("❌ No allowlist entries found. Specify --db to point to a valid database file.", file=sys.stderr)
        return 1

    payload = build_seed_payload(entries, args.password_length)
    payload_json = json.dumps(payload, indent=2, ensure_ascii=False)

    if args.output:
        args.output.write_text(payload_json, encoding="utf-8")
        print(f"✅ Wrote seed payload to {args.output}")
    else:
        print(payload_json)

    if args.push:
        push_to_secret_manager(
            payload_json,
            args.push,
            project=args.project,
            create_if_missing=args.create_secret,
        )
        print(f"✅ Secret version added to {args.push} (project {args.project})")

    print("\n[INFO] Remember to redeploy Cloud Run so the new allowlist seed is applied.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
