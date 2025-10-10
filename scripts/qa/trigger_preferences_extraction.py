#!/usr/bin/env python3
"""
Script QA P1: Trigger preference extraction in production
Creates a conversation with explicit preferences, then triggers memory consolidation.
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import httpx
import websockets

# Try to load .env.qa if exists
env_file = Path(__file__).parent / ".env.qa"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())

# Configuration
BASE_URL = os.environ.get(
    "EMERGENCE_QA_BASE_URL", "https://emergence-app-47nct44nma-ew.a.run.app"
)
LOGIN_EMAIL = os.environ.get("EMERGENCE_SMOKE_EMAIL", "")
LOGIN_PASSWORD = os.environ.get("EMERGENCE_SMOKE_PASSWORD", "")

# Test messages with explicit preferences
PREFERENCE_MESSAGES = [
    "Je préfère utiliser Python pour mes projets backend",
    "Je vais apprendre FastAPI la semaine prochaine",
    "J'évite d'utiliser jQuery dans mes applications",
    "J'aime beaucoup travailler avec Claude pour coder",
    "Je planifie de migrer vers TypeScript d'ici fin du mois",
]


async def login(email: str, password: str) -> tuple[str, str]:
    """Login and return (token, user_sub)."""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        response = await client.post(
            "/api/auth/login", json={"email": email, "password": password}
        )
        response.raise_for_status()
        data = response.json()
        # Response format: {"token": "...", "user_id": "...", ...}
        return data["token"], data["user_id"]


async def create_thread(token: str, title: str) -> str:
    """Create a new thread and return thread_id."""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        response = await client.post(
            "/api/threads",
            json={"title": title, "type": "chat"},
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        data = response.json()
        return data["id"]


async def send_messages_ws(
    token: str, thread_id: str, messages: list[str]
) -> None:
    """Send messages via WebSocket."""
    parsed = httpx.URL(BASE_URL)
    ws_scheme = "wss" if parsed.scheme == "https" else "ws"
    ws_url = f"{ws_scheme}://{parsed.host}/ws"

    print(f"\nConnecting to WebSocket: {ws_url}")

    async with websockets.connect(
        ws_url, additional_headers={"Authorization": f"Bearer {token}"}
    ) as ws:
        print("[OK] WebSocket connected")

        for i, msg in enumerate(messages, 1):
            payload = {
                "type": "chat.message",
                "thread_id": thread_id,
                "content": msg,
                "agent": "anima",
            }
            print(f"\n[MSG {i}/{len(messages)}] Sending: {msg[:60]}...")
            await ws.send(json.dumps(payload))

            # Collect response
            response_content = ""
            while True:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=30.0)
                    event = json.loads(raw)

                    if event.get("type") == "chat.delta":
                        response_content += event.get("content", "")
                    elif event.get("type") == "chat.done":
                        print(f"[OK] Response received ({len(response_content)} chars)")
                        break
                    elif event.get("type") == "error":
                        print(f"[ERROR] {event.get('message')}")
                        break
                except asyncio.TimeoutError:
                    print("[TIMEOUT] Waiting for response")
                    break

            # Small delay between messages
            await asyncio.sleep(1.0)


async def trigger_memory_consolidation(
    token: str, thread_id: str, user_sub: str
) -> Dict[str, Any]:
    """Trigger memory consolidation (tend-garden)."""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=120.0) as client:
        response = await client.post(
            "/api/memory/tend-garden",
            json={"thread_id": thread_id, "user_sub": user_sub},
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        return response.json()


async def main() -> int:
    """Main QA flow."""
    print("[P1 QA] Preference Extraction")
    print(f"Base URL: {BASE_URL}")
    print(f"Email: {LOGIN_EMAIL}")

    if not LOGIN_EMAIL or not LOGIN_PASSWORD:
        print("[ERROR] Missing EMERGENCE_SMOKE_EMAIL or EMERGENCE_SMOKE_PASSWORD")
        return 1

    try:
        # 1. Login
        print("\n[1/4] Logging in...")
        token, user_sub = await login(LOGIN_EMAIL, LOGIN_PASSWORD)
        print(f"[OK] Logged in as {user_sub}")

        # 2. Create thread
        title = f"P1 QA Preferences Test {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        print(f"\n[2/4] Creating thread: {title}")
        thread_id = await create_thread(token, title)
        print(f"[OK] Thread created: {thread_id}")

        # 3. Send preference messages
        print(f"\n[3/4] Sending {len(PREFERENCE_MESSAGES)} preference messages...")
        await send_messages_ws(token, thread_id, PREFERENCE_MESSAGES)
        print("[OK] All messages sent")

        # 4. Trigger consolidation
        print("\n[4/4] Triggering memory consolidation...")
        result = await trigger_memory_consolidation(token, thread_id, user_sub)
        print("[OK] Consolidation triggered")
        print(f"Result: {json.dumps(result, indent=2)}")

        print("\n[SUCCESS] QA P1 completed successfully!")
        print("\nNext steps:")
        print(
            f"   1. Check metrics: curl {BASE_URL}/api/metrics | grep memory_preferences"
        )
        print(
            "   2. Check logs: gcloud logging read 'textPayload:PreferenceExtractor' --limit 20"
        )
        print(f"   3. Thread ID for verification: {thread_id}")

        return 0

    except httpx.HTTPStatusError as e:
        print(f"\n[ERROR] HTTP {e.response.status_code}: {e.response.text}")
        return 1
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
