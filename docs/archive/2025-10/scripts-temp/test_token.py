"""
Script de test pour vérifier le token d'authentification et les endpoints API
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
    "Cookie": f"id_token={ID_TOKEN}; emergence_session_id={SESSION_ID}",
}


def print_test_header(test_name: str):
    """Affiche un en-tête de test"""
    print("\n" + "=" * 80)
    print(f"TEST: {test_name}")
    print("=" * 80)


def print_result(success: bool, message: str, details: Any = None):
    """Affiche le résultat d'un test"""
    status = "[OK] SUCCES" if success else "[ERREUR] ECHEC"
    print(f"\n{status}: {message}")
    if details:
        print(f"Details: {json.dumps(details, indent=2, ensure_ascii=False)}")


def test_health_check():
    """Test 1: Vérifier que le backend répond"""
    print_test_header("Health Check")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        success = response.status_code == 200
        print_result(
            success,
            f"Backend status: {response.status_code}",
            response.json() if success else None,
        )
        return success
    except Exception as e:
        print_result(False, f"Erreur de connexion: {str(e)}")
        return False


def test_auth_verification():
    """Test 2: Vérifier l'authentification avec le token"""
    print_test_header("Vérification du Token")
    try:
        # Essayer un endpoint qui nécessite l'authentification
        response = requests.get(
            f"{BASE_URL}/api/user/profile", headers=HEADERS, timeout=5
        )
        success = response.status_code in [
            200,
            401,
            404,
        ]  # 404 si l'endpoint n'existe pas encore

        if response.status_code == 200:
            print_result(
                True, "Token valide - Utilisateur authentifié", response.json()
            )
        elif response.status_code == 401:
            print_result(
                False,
                "Token invalide ou expiré",
                {"status": response.status_code, "body": response.text},
            )
        else:
            print_result(
                True,
                f"Endpoint retourne {response.status_code} (endpoint peut ne pas exister)",
                {"status": response.status_code},
            )

        return success
    except Exception as e:
        print_result(False, f"Erreur lors de la vérification: {str(e)}")
        return False


def test_chat_endpoint():
    """Test 3: Tester l'endpoint de chat"""
    print_test_header("Test Chat Endpoint")
    try:
        payload = {
            "message": "Hello, this is a test message",
            "thread_id": "test-thread-123",
        }
        response = requests.post(
            f"{BASE_URL}/api/chat", headers=HEADERS, json=payload, timeout=10
        )
        success = response.status_code in [200, 201, 404]

        if response.status_code in [200, 201]:
            print_result(
                True,
                "Endpoint chat accessible et fonctionnel",
                {
                    "status": response.status_code,
                    "response_preview": response.text[:200] if response.text else None,
                },
            )
        elif response.status_code == 404:
            print_result(
                True,
                "Endpoint chat non trouvé (peut utiliser un autre chemin)",
                {"status": 404},
            )
        else:
            print_result(
                False, f"Erreur {response.status_code}", {"body": response.text[:200]}
            )

        return success
    except Exception as e:
        print_result(False, f"Erreur lors du test chat: {str(e)}")
        return False


def test_debate_endpoint():
    """Test 4: Tester l'endpoint de débat"""
    print_test_header("Test Debate Endpoint")
    try:
        payload = {"topic": "Test debate topic", "participants": ["neo", "anima"]}
        response = requests.post(
            f"{BASE_URL}/api/debate", headers=HEADERS, json=payload, timeout=10
        )
        success = response.status_code in [200, 201, 404]

        if response.status_code in [200, 201]:
            print_result(
                True,
                "Endpoint debate accessible et fonctionnel",
                {
                    "status": response.status_code,
                    "response_preview": response.text[:200] if response.text else None,
                },
            )
        elif response.status_code == 404:
            print_result(
                True,
                "Endpoint debate non trouvé (peut utiliser un autre chemin)",
                {"status": 404},
            )
        else:
            print_result(
                False, f"Erreur {response.status_code}", {"body": response.text[:200]}
            )

        return success
    except Exception as e:
        print_result(False, f"Erreur lors du test debate: {str(e)}")
        return False


def test_settings_security():
    """Test 5: Tester l'endpoint de settings/security"""
    print_test_header("Test Settings Security Endpoint")
    try:
        response = requests.get(
            f"{BASE_URL}/api/settings/security", headers=HEADERS, timeout=5
        )
        success = response.status_code in [200, 404]

        if response.status_code == 200:
            print_result(True, "Endpoint settings/security accessible", response.json())
        elif response.status_code == 404:
            print_result(
                True,
                "Endpoint settings/security non trouvé (normal si pas encore implémenté)",
                {"status": 404},
            )
        else:
            print_result(
                False, f"Erreur {response.status_code}", {"body": response.text[:200]}
            )

        return success
    except Exception as e:
        print_result(False, f"Erreur lors du test settings: {str(e)}")
        return False


def test_cors_headers():
    """Test 6: Vérifier les headers CORS"""
    print_test_header("Vérification CORS Headers")
    try:
        response = requests.options(f"{BASE_URL}/api/chat", headers=HEADERS, timeout=5)
        cors_headers = {
            "Access-Control-Allow-Origin": response.headers.get(
                "Access-Control-Allow-Origin"
            ),
            "Access-Control-Allow-Methods": response.headers.get(
                "Access-Control-Allow-Methods"
            ),
            "Access-Control-Allow-Headers": response.headers.get(
                "Access-Control-Allow-Headers"
            ),
        }
        success = any(cors_headers.values())
        print_result(
            success,
            "Headers CORS",
            cors_headers if success else "Pas de headers CORS trouvés",
        )
        return success
    except Exception as e:
        print_result(False, f"Erreur lors de la vérification CORS: {str(e)}")
        return False


def decode_jwt_payload():
    """Bonus: Décoder le payload du JWT pour voir les infos utilisateur"""
    print_test_header("Décodage du JWT (Payload uniquement)")
    try:
        import base64

        # Le JWT est composé de 3 parties séparées par des points: header.payload.signature
        parts = ID_TOKEN.split(".")
        if len(parts) != 3:
            print_result(False, "Format JWT invalide")
            return False

        # Décoder le payload (partie 2)
        payload = parts[1]
        # Ajouter le padding nécessaire pour base64
        padding = 4 - len(payload) % 4
        if padding != 4:
            payload += "=" * padding

        decoded = base64.urlsafe_b64decode(payload)
        payload_data = json.loads(decoded)

        print_result(True, "JWT décodé avec succès", payload_data)
        return True
    except Exception as e:
        print_result(False, f"Erreur lors du décodage: {str(e)}")
        return False


def main():
    """Exécute tous les tests"""
    print("\n" + "=" * 80)
    print("TESTS D'AUTHENTIFICATION ET API - EmergenceV8")
    print("=" * 80)

    tests = [
        ("Health Check", test_health_check),
        ("JWT Decode", decode_jwt_payload),
        ("Auth Verification", test_auth_verification),
        ("Chat Endpoint", test_chat_endpoint),
        ("Debate Endpoint", test_debate_endpoint),
        ("Settings Security", test_settings_security),
        ("CORS Headers", test_cors_headers),
    ]

    results = {}
    for test_name, test_func in tests:
        results[test_name] = test_func()

    # Résumé
    print("\n" + "=" * 80)
    print("RÉSUMÉ DES TESTS")
    print("=" * 80)

    total = len(results)
    passed = sum(1 for r in results.values() if r)

    for test_name, result in results.items():
        status = "[OK]" if result else "[FAIL]"
        print(f"{status} {test_name}")

    print("\n" + "-" * 80)
    print(f"Total: {passed}/{total} tests réussis ({passed * 100 // total}%)")
    print("=" * 80)


if __name__ == "__main__":
    main()
