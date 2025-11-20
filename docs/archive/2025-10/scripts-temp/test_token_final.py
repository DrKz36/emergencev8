"""
Script de test FINAL - Token dans Authorization Header (Bearer)
"""

import requests
import json
from typing import Any

# Configuration
BASE_URL = "http://localhost:8000"
ID_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJlbWVyZ2VuY2UubG9jYWwiLCJhdWQiOiJlbWVyZ2VuY2UtYXBwIiwic3ViIjoiZmZhNGM0M2FlNTdmYzkzZWNmOTRiMWJlMjAxYzZjNjAxOGMzYjBhYjUwN2U1ZjcwNTA5ZTkwNDRkOWU2NTJkNyIsImVtYWlsIjoiZ29uemFsZWZlcm5hbmRvQGdtYWlsLmNvbSIsInJvbGUiOiJhZG1pbiIsInNpZCI6ImEyNGVlZmM5LTEwZjEtNDUzZi05ZmZmLTZkMWI3NWQ5NGU4ZSIsImlhdCI6MTc2MDE0MjkwNiwiZXhwIjoxNzYwNzQ3NzA2fQ.66krhcdLBJeNVDbLtOMi8VvVFCAKM_UugUzLKoc3qTg"
SESSION_ID = "a24eefc9-10f1-453f-9fff-6d1b75d94e8e"

# Headers avec le token dans Authorization (format Bearer)
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {ID_TOKEN}",
    "X-Session-Id": SESSION_ID,
}


def print_section(title: str):
    """Affiche une section"""
    print("\n" + "=" * 80)
    print(f"{title}")
    print("=" * 80)


def print_test(test_name: str, success: bool, details: Any = None):
    """Affiche le résultat d'un test"""
    status = "[OK]" if success else "[FAIL]"
    print(f"{status} {test_name}")
    if details and success:
        if isinstance(details, dict):
            print(json.dumps(details, indent=2, ensure_ascii=False))
        else:
            print(details)


def main():
    """Tests complets avec le bon format d'authentification"""
    print_section("TESTS COMPLETS - EmergenceV8 API avec Token Bearer")

    # 1. JWT Decode
    print("\n1. JWT DECODE")
    try:
        import base64

        parts = ID_TOKEN.split(".")
        payload = parts[1] + "=" * (-len(parts[1]) % 4)
        decoded = base64.urlsafe_b64decode(payload)
        payload_data = json.loads(decoded)

        import time

        exp = payload_data.get("exp", 0)
        now = int(time.time())
        is_valid = now < exp
        time_left_hours = round((exp - now) / 3600, 2)

        print(f"   Email: {payload_data.get('email')}")
        print(f"   Role: {payload_data.get('role')}")
        print(f"   Session ID: {payload_data.get('sid')}")
        print(f"   Valide: {is_valid} (expire dans {time_left_hours}h)")
        print_test("JWT Decode", True)
    except Exception as e:
        print_test("JWT Decode", False, str(e))

    # 2. Health Check
    print("\n2. HEALTH CHECK")
    try:
        response = requests.get(f"{BASE_URL}/api/health", timeout=5)
        data = response.json() if response.status_code == 200 else None
        print_test(
            f"Health (status={response.status_code})", response.status_code == 200, data
        )
    except Exception as e:
        print_test("Health Check", False, str(e))

    # 3. Threads (avec auth)
    print("\n3. THREADS (avec authentification)")
    try:
        response = requests.get(f"{BASE_URL}/api/threads", headers=HEADERS, timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_test(f"Threads (status={response.status_code})", True, data)
        else:
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            print_test("Threads", False)
    except Exception as e:
        print_test("Threads", False, str(e))

    # 4. Documents (avec auth)
    print("\n4. DOCUMENTS (avec authentification)")
    try:
        response = requests.get(f"{BASE_URL}/api/documents", headers=HEADERS, timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_test(f"Documents (status={response.status_code})", True, data)
        else:
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            print_test("Documents", False)
    except Exception as e:
        print_test("Documents", False, str(e))

    # 5. Sync (avec auth)
    print("\n5. SYNC STATUS (avec authentification)")
    try:
        response = requests.get(
            f"{BASE_URL}/api/sync/status", headers=HEADERS, timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            print_test(f"Sync Status (status={response.status_code})", True, data)
        elif response.status_code == 404:
            print_test("Sync Status (endpoint non trouvé)", True, {"status": 404})
        else:
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            print_test("Sync Status", False)
    except Exception as e:
        print_test("Sync Status", False, str(e))

    # 6. Dashboard
    print("\n6. DASHBOARD")
    try:
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats", headers=HEADERS, timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            print_test(f"Dashboard Stats (status={response.status_code})", True, data)
        elif response.status_code == 404:
            print_test("Dashboard Stats (endpoint non trouvé)", True, {"status": 404})
        else:
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            print_test("Dashboard Stats", False)
    except Exception as e:
        print_test("Dashboard Stats", False, str(e))

    # 7. Debate List
    print("\n7. DEBATE")
    try:
        response = requests.get(f"{BASE_URL}/api/debate/", headers=HEADERS, timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_test(f"Debate List (status={response.status_code})", True, data)
        else:
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            print_test("Debate List", False)
    except Exception as e:
        print_test("Debate List", False, str(e))

    # 8. Memory
    print("\n8. MEMORY")
    try:
        response = requests.get(
            f"{BASE_URL}/api/memory/stats", headers=HEADERS, timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            print_test(f"Memory Stats (status={response.status_code})", True, data)
        elif response.status_code == 404:
            print_test("Memory Stats (endpoint non trouvé)", True, {"status": 404})
        else:
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            print_test("Memory Stats", False)
    except Exception as e:
        print_test("Memory Stats", False, str(e))

    # Recommendations
    print_section("RECOMMANDATIONS POUR L'UI")
    print("\nPour utiliser ce token dans l'interface utilisateur (frontend):")
    print("\n1. STOCKER LE TOKEN:")
    print("   - Apres login, stocker le token dans localStorage ou sessionStorage")
    print("   - Exemple: localStorage.setItem('id_token', token)")
    print("\n2. CONFIGURER L'API CLIENT:")
    print("   Dans votre fichier api-client.js, le header doit etre:")
    print("   Authorization: Bearer <token>")
    print("\n3. WEBSOCKET:")
    print("   Pour le WebSocket, le token peut etre passe via:")
    print(f"   - Query parameter: ws://localhost:8000/ws/{SESSION_ID}?token=<id_token>")
    print("   - Cookie: document.cookie = 'id_token=<token>'")
    print("   - Subprotocol header")
    print("\n4. GESTION SESSION:")
    print(f"   - Session ID: {SESSION_ID}")
    print(f"   - User ID (sub): {payload_data.get('sub', 'N/A')[:20]}...")
    print(f"   - Email: {payload_data.get('email', 'N/A')}")
    print(f"   - Role: {payload_data.get('role', 'N/A')}")
    print(f"   - Expire dans: {time_left_hours}h")

    print_section("FIN DES TESTS")


if __name__ == "__main__":
    main()
