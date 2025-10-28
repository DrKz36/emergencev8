"""
Initialize Firestore allowlist snapshot document.

This script creates the initial Firestore document for the allowlist snapshot
with the current admin email from the environment.
"""
import os
import asyncio
from datetime import datetime, timezone
from google.cloud import firestore  # type: ignore

async def init_firestore_snapshot():
    """Initialize the Firestore allowlist snapshot."""
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "emergence-469005")
    collection = os.getenv("AUTH_ALLOWLIST_SNAPSHOT_COLLECTION", "auth_config")
    document = os.getenv("AUTH_ALLOWLIST_SNAPSHOT_DOCUMENT", "allowlist")
    admin_email = os.getenv("AUTH_ADMIN_EMAILS", "gonzalefernando@gmail.com")

    print(f"Initializing Firestore snapshot:")
    print(f"  Project: {project_id}")
    print(f"  Collection: {collection}")
    print(f"  Document: {document}")
    print(f"  Admin email: {admin_email}")

    # Create Firestore client
    client = firestore.AsyncClient(project=project_id)

    # Check if document already exists
    doc_ref = client.collection(collection).document(document)
    snapshot = await doc_ref.get()

    if snapshot.exists:
        print("\n[OK] Document already exists!")
        data = snapshot.to_dict()
        print(f"  Active entries: {len(data.get('active_entries', []))}")
        print(f"  Revoked entries: {len(data.get('revoked_entries', []))}")
        print(f"  Last updated: {data.get('last_updated', 'N/A')}")
        return

    # Create initial document with admin email
    now = datetime.now(timezone.utc).isoformat()
    initial_data = {
        "active_entries": [
            {
                "email": admin_email.lower().strip(),
                "role": "admin",
                "created_at": now,
                "is_active": True,
                "password_hash": None,  # Will be set when user sets password
            }
        ],
        "revoked_entries": [],
        "last_updated": now,
        "version": 1,
    }

    await doc_ref.set(initial_data)
    print("\n[OK] Document created successfully!")
    print(f"  Collection: {collection}")
    print(f"  Document: {document}")
    print(f"  Admin email added: {admin_email}")

    # Close client
    await client.close()

if __name__ == "__main__":
    asyncio.run(init_firestore_snapshot())
