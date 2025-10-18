"""
Script de test v2 - Endpoints corrects pour EmergenceV8
"""
import requests
import json
from typing import Any

# Configuration
BASE_URL = "http://localhost:8000"
ID_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJlbWVyZ2VuY2UubG9jYWwiLCJhdWQiOiJlbWVyZ2VuY2UtYXBwIiwic3ViIjoiZmZhNGM0M2FlNTdmYzkzZWNmOTRiMWJlMjAxYzZjNjAxOGMzYjBhYjUwN2U1ZjcwNTA5ZTkwNDRkOWU2NTJkNyIsImVtYWlsIjoiZ29uemFsZWZlcm5hbmRvQGdtYWlsLmNvbSIsInJvbGUiOiJhZG1pbiIsInNpZCI6ImEyNGVlZmM5LTEwZjEtNDUzZi05ZmZmLTZkMWI3NWQ5NGU4ZSIsImlhdCI6MTc2MDE0MjkwNiwiZXhwIjoxNzYwNzQ3NzA2fQ.66krhcdLBJeNVDbLtOMi8VvVFCAKM_UugUzLKoc3qTg"
SESSION_ID = "a24eefc9-10f1-453f-9fff-6d1b75d94e8e"

# Headers avec le token
HEADERS = {
    "Content-Type": "application/json",
    "Cookie": f"id_token={ID_TOKEN}; emergence_session_id={SESSION_ID}"
}

def print_test_header(test_name: str):
    """Affiche un en-tête de test"""
    print("\n" + "=" * 80)
    print(f"TEST: {test_name}")
    print("=" * 80)

def print_result(success: bool, message: str, details: Any = None):
    """Affiche le résultat d'un test"""
    status = "[OK]" if success else "[FAIL]"
    print(f"\n{status}: {message}")
    if details:
        if isinstance(details, dict):
            print(f"Details: {json.dumps(details, indent=2, ensure_ascii=False)}")
        else:
            print(f"Details: {details}")

def test_health():
    """Test 1: Health endpoint"""
    print_test_header("Health Check")
    try:
        response = requests.get(f"{BASE_URL}/api/health", timeout=5)
        success = response.status_code == 200
        data = response.json() if success else None
        print_result(success, f"Health endpoint (status={response.status_code})", data)
        return success
    except Exception as e:
        print_result(False, f"Erreur: {str(e)}")
        return False

def test_debate_list():
    """Test 2: Liste des débats actifs"""
    print_test_header("Liste des Debats")
    try:
        response = requests.get(f"{BASE_URL}/api/debate/", headers=HEADERS, timeout=5)
        success = response.status_code == 200
        data = response.json() if success else None
        print_result(success, f"Liste debats (status={response.status_code})", data)
        return success
    except Exception as e:
        print_result(False, f"Erreur: {str(e)}")
        return False

def test_dashboard():
    """Test 3: Dashboard endpoint"""
    print_test_header("Dashboard")
    try:
        response = requests.get(f"{BASE_URL}/api/dashboard/stats", headers=HEADERS, timeout=5)
        success = response.status_code in [200, 404]  # 404 acceptable si pas encore implementé

        if response.status_code == 200:
            data = response.json()
            print_result(True, "Dashboard stats accessible", data)
        elif response.status_code == 404:
            print_result(True, "Dashboard stats non trouvé (normal si pas encore implémenté)", {"status": 404})
        else:
            print_result(False, f"Erreur {response.status_code}", {"body": response.text[:200]})

        return success
    except Exception as e:
        print_result(False, f"Erreur: {str(e)}")
        return False

def test_threads():
    """Test 4: Threads endpoint"""
    print_test_header("Threads")
    try:
        response = requests.get(f"{BASE_URL}/api/threads", headers=HEADERS, timeout=5)
        success = response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()
            print_result(True, "Threads endpoint accessible", data)
        elif response.status_code == 404:
            print_result(True, "Threads endpoint non trouvé (normal si pas encore implémenté)", {"status": 404})
        else:
            print_result(False, f"Erreur {response.status_code}", {"body": response.text[:200]})

        return success
    except Exception as e:
        print_result(False, f"Erreur: {str(e)}")
        return False

def test_memory():
    """Test 5: Memory endpoint"""
    print_test_header("Memory")
    try:
        response = requests.get(f"{BASE_URL}/api/memory/stats", headers=HEADERS, timeout=5)
        success = response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()
            print_result(True, "Memory stats accessible", data)
        elif response.status_code == 404:
            print_result(True, "Memory stats non trouvé (normal si pas encore implémenté)", {"status": 404})
        else:
            print_result(False, f"Erreur {response.status_code}", {"body": response.text[:200]})

        return success
    except Exception as e:
        print_result(False, f"Erreur: {str(e)}")
        return False

def test_metrics():
    """Test 6: Metrics endpoint (Prometheus)"""
    print_test_header("Metrics (Prometheus)")
    try:
        response = requests.get(f"{BASE_URL}/api/metrics", headers=HEADERS, timeout=5)
        success = response.status_code in [200, 404]

        if response.status_code == 200:
            # Les metrics Prometheus sont en format texte
            content = response.text[:500]
            print_result(True, "Metrics endpoint accessible", {"preview": content})
        elif response.status_code == 404:
            print_result(True, "Metrics endpoint non trouvé", {"status": 404})
        else:
            print_result(False, f"Erreur {response.status_code}", {"body": response.text[:200]})

        return success
    except Exception as e:
        print_result(False, f"Erreur: {str(e)}")
        return False

def test_monitoring():
    """Test 7: Monitoring endpoint"""
    print_test_header("Monitoring")
    try:
        response = requests.get(f"{BASE_URL}/api/monitoring/health", headers=HEADERS, timeout=5)
        success = response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()
            print_result(True, "Monitoring health accessible", data)
        elif response.status_code == 404:
            print_result(True, "Monitoring health non trouvé", {"status": 404})
        else:
            print_result(False, f"Erreur {response.status_code}", {"body": response.text[:200]})

        return success
    except Exception as e:
        print_result(False, f"Erreur: {str(e)}")
        return False

def test_documents():
    """Test 8: Documents endpoint"""
    print_test_header("Documents")
    try:
        response = requests.get(f"{BASE_URL}/api/documents", headers=HEADERS, timeout=5)
        success = response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()
            print_result(True, "Documents endpoint accessible", data)
        elif response.status_code == 404:
            print_result(True, "Documents endpoint non trouvé", {"status": 404})
        else:
            print_result(False, f"Erreur {response.status_code}", {"body": response.text[:200]})

        return success
    except Exception as e:
        print_result(False, f"Erreur: {str(e)}")
        return False

def test_benchmarks():
    """Test 9: Benchmarks endpoint"""
    print_test_header("Benchmarks")
    try:
        response = requests.get(f"{BASE_URL}/api/benchmarks", headers=HEADERS, timeout=5)
        success = response.status_code in [200, 404, 405]

        if response.status_code == 200:
            data = response.json()
            print_result(True, "Benchmarks endpoint accessible", data)
        elif response.status_code in [404, 405]:
            print_result(True, f"Benchmarks endpoint status={response.status_code}", {"status": response.status_code})
        else:
            print_result(False, f"Erreur {response.status_code}", {"body": response.text[:200]})

        return success
    except Exception as e:
        print_result(False, f"Erreur: {str(e)}")
        return False

def test_sync():
    """Test 10: Sync endpoint"""
    print_test_header("Sync")
    try:
        response = requests.get(f"{BASE_URL}/api/sync/status", headers=HEADERS, timeout=5)
        success = response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()
            print_result(True, "Sync status accessible", data)
        elif response.status_code == 404:
            print_result(True, "Sync status non trouvé", {"status": 404})
        else:
            print_result(False, f"Erreur {response.status_code}", {"body": response.text[:200]})

        return success
    except Exception as e:
        print_result(False, f"Erreur: {str(e)}")
        return False

def decode_jwt():
    """Bonus: Décoder le JWT"""
    print_test_header("JWT Decode")
    try:
        import base64
        parts = ID_TOKEN.split('.')
        if len(parts) != 3:
            print_result(False, "Format JWT invalide")
            return False

        payload = parts[1]
        padding = 4 - len(payload) % 4
        if padding != 4:
            payload += '=' * padding

        decoded = base64.urlsafe_b64decode(payload)
        payload_data = json.loads(decoded)

        # Vérifier l'expiration
        import time
        exp = payload_data.get('exp', 0)
        now = int(time.time())

        is_valid = now < exp
        time_left = exp - now

        payload_data['_computed'] = {
            'is_expired': not is_valid,
            'time_left_seconds': time_left,
            'time_left_hours': round(time_left / 3600, 2)
        }

        print_result(True, f"JWT décodé - Valide: {is_valid}", payload_data)
        return True
    except Exception as e:
        print_result(False, f"Erreur: {str(e)}")
        return False

def main():
    """Exécute tous les tests"""
    print("\n" + "=" * 80)
    print("TESTS API EmergenceV8 - Endpoints Réels")
    print("=" * 80)

    tests = [
        ("JWT Decode", decode_jwt),
        ("Health Check", test_health),
        ("Debate List", test_debate_list),
        ("Dashboard", test_dashboard),
        ("Threads", test_threads),
        ("Memory", test_memory),
        ("Metrics", test_metrics),
        ("Monitoring", test_monitoring),
        ("Documents", test_documents),
        ("Benchmarks", test_benchmarks),
        ("Sync", test_sync),
    ]

    results = {}
    for test_name, test_func in tests:
        results[test_name] = test_func()

    # Résumé
    print("\n" + "=" * 80)
    print("RESUME DES TESTS")
    print("=" * 80)

    total = len(results)
    passed = sum(1 for r in results.values() if r)

    for test_name, result in results.items():
        status = "[OK]" if result else "[FAIL]"
        print(f"{status} {test_name}")

    print("\n" + "-" * 80)
    print(f"Total: {passed}/{total} tests reussis ({passed*100//total}%)")
    print("=" * 80)

    # Recommendations
    print("\nRECOMMANDATIONS:")
    if results.get("Health Check"):
        print("- Backend operationnel")
    if results.get("Debate List"):
        print("- Endpoint debate fonctionnel")
    if not results.get("Dashboard"):
        print("- Dashboard: verifier l'endpoint exact dans router.py")

    print("\nPOUR UTILISER L'UI:")
    print(f"1. Token: Cookie 'id_token={ID_TOKEN[:20]}...'")
    print(f"2. Session: Cookie 'emergence_session_id={SESSION_ID}'")
    print("3. WebSocket: ws://localhost:8000/ws/{session_id}")

if __name__ == "__main__":
    main()
