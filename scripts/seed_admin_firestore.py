"""
Script pour créer un compte admin directement dans Firestore.
Usage: python scripts/seed_admin_firestore.py
"""
import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add src to path
repo_root = Path(__file__).resolve().parent.parent
src_dir = repo_root / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

import bcrypt  # type: ignore
from google.cloud import firestore  # type: ignore

DEFAULT_EMAIL = "gonzalefernando@gmail.com"
DEFAULT_PASSWORD = "WinipegMad2015"
DEFAULT_ROLE = "admin"


def hash_password(password: str) -> str:
    """Hash password using bcrypt (match backend logic)."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


async def seed_admin_firestore():
    """Create admin account in Firestore."""
    email = os.getenv("EMERGENCE_ADMIN_EMAIL", DEFAULT_EMAIL).strip().lower()
    password = os.getenv("EMERGENCE_ADMIN_PASSWORD", DEFAULT_PASSWORD).strip()
    role = os.getenv("EMERGENCE_ADMIN_ROLE", DEFAULT_ROLE).strip().lower()

    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters")

    # Initialize Firestore client
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "emergence-469005")
    db = firestore.AsyncClient(project=project_id)

    print(f"[seed-admin-firestore] Connecting to Firestore project: {project_id}")

    # Hash password
    password_hash = hash_password(password)

    # Create user document
    user_doc = {
        "email": email,
        "password_hash": password_hash,
        "role": role,
        "approved": True,
        "active": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "note": "seed-admin-firestore",
    }

    # Write to Firestore (collection: auth_allowlist)
    doc_ref = db.collection("auth_allowlist").document(email)
    await doc_ref.set(user_doc, merge=True)

    print(f"[seed-admin-firestore] Admin account created/updated:")
    print(f"  - Email: {email}")
    print(f"  - Role: {role}")
    print(f"  - Password hash: {password_hash[:16]}...")
    print(f"[seed-admin-firestore] You can now login at https://emergence-app-486095406755.europe-west1.run.app/")


if __name__ == "__main__":
    asyncio.run(seed_admin_firestore())
