#!/usr/bin/env python3
"""Simple test: create thread, add user message directly to DB via API, then consolidate."""

import asyncio
import json
import sys
from pathlib import Path

import httpx

# Load credentials
env_file = Path(__file__).parent / ".env.qa"
if env_file.exists():
    import os
    for line in env_file.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())

import os
BASE_URL = "https://emergence-app-47nct44nma-ew.a.run.app"
EMAIL = os.environ.get("EMERGENCE_SMOKE_EMAIL", "")
PASSWORD = os.environ.get("EMERGENCE_SMOKE_PASSWORD", "")

async def main():
    print(f"[P1 Simple Test]")
    print(f"Base URL: {BASE_URL}")
    print(f"Email: {EMAIL}\n")

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=120.0) as client:
        # 1. Login
        print("[1/4] Logging in...")
        response = await client.post("/api/auth/login", json={"email": EMAIL, "password": PASSWORD})
        response.raise_for_status()
        data = response.json()
        token = data["token"]
        user_id = data["user_id"]
        print(f"[OK] Token: {token[:40]}...")
        print(f"[OK] User ID: {user_id}\n")

        # 2. Create thread
        print("[2/4] Creating thread...")
        response = await client.post(
            "/api/threads",
            json={"title": "P1 Simple Preference Test", "type": "chat"},
            headers={"Authorization": f"Bearer {token}"}
        )
        response.raise_for_status()
        thread_id = response.json()["id"]
        print(f"[OK] Thread ID: {thread_id}\n")

        # 3. Add messages directly via /api/threads/{id}/messages
        print("[3/4] Adding messages...")
        messages = [
            "Je préfère utiliser Python pour mes projets backend",
            "Réponse agent: Python est un excellent choix pour le backend.",
            "Je vais apprendre FastAPI la semaine prochaine",
            "Réponse agent: FastAPI est très performant et moderne.",
        ]

        for i, msg in enumerate(messages):
            role = "user" if i % 2 == 0 else "assistant"
            print(f"  [{role}] {msg[:60]}...")
            response = await client.post(
                f"/api/threads/{thread_id}/messages",
                json={"content": msg, "role": role, "agent": "anima" if role == "assistant" else None},
                headers={"Authorization": f"Bearer {token}"}
            )
            response.raise_for_status()

        print("[OK] Messages added\n")

        # 4. Trigger consolidation
        print("[4/4] Triggering consolidation...")
        response = await client.post(
            "/api/memory/tend-garden",
            json={"thread_id": thread_id, "user_sub": user_id},
            headers={"Authorization": f"Bearer {token}"}
        )
        response.raise_for_status()
        result = response.json()
        print(f"[OK] Result: {json.dumps(result, indent=2)}\n")

        print("[SUCCESS] Check metrics now:")
        print(f"  curl {BASE_URL}/api/metrics | grep memory_preferences")
        print(f"\n[SUCCESS] Check logs:")
        print(f"  gcloud logging read 'textPayload:PreferenceExtractor' --limit 20")

if __name__ == "__main__":
    asyncio.run(main())
