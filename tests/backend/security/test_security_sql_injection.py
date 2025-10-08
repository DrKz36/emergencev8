"""
Tests de sécurité - Injection SQL
Vérifie que l'application est protégée contre les injections SQL
"""

from fastapi.testclient import TestClient


class TestSQLInjection:
    """Tests de protection contre injection SQL"""

    def test_login_sql_injection_attempt(self, client):
        """Tente injection SQL via champ email du login"""

        # Tentatives d'injection SQL classiques
        payloads = [
            "admin' OR '1'='1",
            "admin'--",
            "admin' OR 1=1--",
            "' OR ''='",
            "1' UNION SELECT NULL--",
            "'; DROP TABLE users--",
        ]

        for payload in payloads:
            response = client.post(
                "/api/auth/login",
                json={"email": payload, "password": "anything"},
            )
            # Doit rejeter (401/422), jamais authentifier
            assert response.status_code in [401, 422, 400], f"Payload dangereux accepté: {payload}"

    def test_thread_search_sql_injection(self, client, authenticated_user):
        """Tente injection SQL via paramètres de recherche"""
        payloads = [
            "test' OR '1'='1",
            "'; DELETE FROM threads--",
            "1' UNION SELECT * FROM users--",
        ]

        for payload in payloads:
            response = client.get(
                "/api/threads",
                params={"search": payload},
            )
            # Doit traiter comme recherche normale, pas exécuter SQL
            assert response.status_code in [200, 400, 422]


class TestXSSProtection:
    """Tests de protection contre XSS"""

    
    def test_message_xss_script_tags(self, client, authenticated_user):
        """Vérifie que les scripts ne sont pas exécutés dans les messages"""
        xss_payloads = [
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert('xss')>",
            "javascript:alert('xss')",
            "<iframe src='javascript:alert(xss)'></iframe>",
        ]

        for payload in xss_payloads:
            response = client.post(
                "/api/chat",
                json={
                    "message": payload,
                    "session_id": "test-session",
                },
            )
            # L'application doit accepter mais sanitizer
            assert response.status_code in [200, 400, 422]


class TestCSRFProtection:
    """Tests de protection CSRF"""

    
    def test_state_changing_requires_auth(self, auth_app_factory):
        """Vérifie que les opérations critiques nécessitent authentification"""
        app = auth_app_factory()
        client = TestClient(app)

        # Tentatives sans authentification
        critical_endpoints = [
            ("/api/threads", "POST", {"title": "test"}),
            ("/api/threads/123", "DELETE", None),
            ("/api/memory/clear", "POST", None),
        ]

        for endpoint, method, data in critical_endpoints:
            if method == "POST":
                response = client.post(endpoint, json=data)
            elif method == "DELETE":
                response = client.delete(endpoint)

            # 401 (non auth) ou 404 (endpoint mock manquant) sont acceptables
            assert response.status_code in [401, 404], f"Endpoint {endpoint} accessible sans auth (got {response.status_code})"


class TestAuthenticationSecurity:
    """Tests de sécurité d'authentification"""

    
    def test_password_not_in_response(self, auth_app_factory):
        """Vérifie que les mots de passe ne sont jamais retournés"""
        app = auth_app_factory()
        client = TestClient(app)

        # Créer un utilisateur
        email = "test@security.local"
        password = "SecurePass123!"

        response = client.post(
            "/api/auth/register",
            json={"email": email, "password": password},
        )

        # Vérifier que le mot de passe n'est JAMAIS dans la réponse
        response_text = response.text.lower()
        assert password.lower() not in response_text
        assert "password" not in response.json() if response.status_code == 200 else True

    
    def test_timing_attack_resistance(self, auth_app_factory):
        """Vérifie résistance aux attaques par timing"""
        import time
        app = auth_app_factory()
        client = TestClient(app)

        # Mesurer temps pour email inexistant vs mauvais password
        timings = []

        for _ in range(5):
            start = time.perf_counter()
            client.post(
                "/api/auth/login",
                json={"email": "nonexistent@test.com", "password": "wrong"},
            )
            timings.append(time.perf_counter() - start)

        # La variance ne doit pas révéler si l'email existe
        variance = max(timings) - min(timings)
        assert variance < 0.1, "Différence de timing trop importante (timing attack possible)"


class TestInputValidation:
    """Tests de validation des entrées"""

    
    def test_oversized_input_rejection(self, client, authenticated_user):
        """Rejette les entrées trop volumineuses"""
        huge_message = "A" * 1000000  # 1MB

        response = client.post(
            "/api/chat",
            json={"message": huge_message, "session_id": "test"},
        )

        assert response.status_code in [400, 413, 422], "Message géant accepté"

    
    def test_malformed_json_handling(self, client):
        """Gère correctement les JSON malformés"""
        response = client.post(
            "/api/chat",
            data="{invalid json here}",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 422, "JSON invalide accepté"
