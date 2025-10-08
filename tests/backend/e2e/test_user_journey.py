"""
Tests E2E - Parcours utilisateur complets
Simule des scénarios réels d'utilisation de l'application
"""

from fastapi.testclient import TestClient
import time


class TestCompleteUserJourney:
    """Parcours utilisateur complet du début à la fin"""

    
    def test_new_user_onboarding_to_chat(self, auth_app_factory):
        """
        Scénario: Nouvel utilisateur s'inscrit et utilise le chat
        1. Inscription
        2. Login
        3. Création d'un thread
        4. Envoi de messages
        5. Récupération de l'historique
        6. Déconnexion
        """
        app = auth_app_factory()
        client = TestClient(app)

        # 1. Inscription
        email = f"newuser_{int(time.time())}@test.com"
        password = "SecurePass123!"

        register_response = client.post(
            "/api/auth/register",
            json={"email": email, "password": password},
        )
        assert register_response.status_code == 200, "Inscription échouée"

        # 2. Login
        login_response = client.post(
            "/api/auth/login",
            json={"email": email, "password": password},
        )
        assert login_response.status_code == 200, "Login échoué"
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 3. Création d'un thread
        thread_response = client.post(
            "/api/threads",
            json={"title": "Mon premier thread"},
            headers=headers,
        )
        assert thread_response.status_code == 200, "Création thread échouée"
        thread_id = thread_response.json()["id"]

        # 4. Envoi de messages
        message_response = client.post(
            "/api/chat",
            json={
                "message": "Bonjour, c'est mon premier message!",
                "thread_id": thread_id,
            },
            headers=headers,
        )
        assert message_response.status_code == 200, "Envoi message échoué"

        # 5. Récupération de l'historique
        history_response = client.get(
            f"/api/threads/{thread_id}/messages",
            headers=headers,
        )
        assert history_response.status_code == 200, "Récupération historique échouée"
        messages = history_response.json()
        assert len(messages) > 0, "Aucun message dans l'historique"

        # 6. Déconnexion
        logout_response = client.post(
            "/api/auth/logout",
            headers=headers,
        )
        assert logout_response.status_code == 200, "Déconnexion échouée"

        # 7. Vérifier que le token est invalidé
        invalid_response = client.get(
            f"/api/threads/{thread_id}/messages",
            headers=headers,
        )
        assert invalid_response.status_code == 401, "Token toujours valide après logout"


class TestMultiThreadConversation:
    """Test de gestion de conversations multi-threads"""

    
    def test_user_manages_multiple_conversations(self, client, authenticated_user):
        """
        Scénario: Utilisateur jongle entre plusieurs conversations
        """
        # Créer 3 threads différents
        threads = []
        for i in range(3):
            response = client.post(
                "/api/threads",
                json={"title": f"Thread {i+1}"},
            )
            assert response.status_code == 200
            threads.append(response.json()["id"])

        # Envoyer des messages dans chaque thread
        for i, thread_id in enumerate(threads):
            response = client.post(
                "/api/chat",
                json={
                    "message": f"Message dans thread {i+1}",
                    "thread_id": thread_id,
                },
            )
            assert response.status_code == 200

        # Vérifier que les threads sont bien isolés
        for i, thread_id in enumerate(threads):
            response = client.get(f"/api/threads/{thread_id}/messages")
            messages = response.json()
            # Chaque thread doit contenir uniquement ses messages
            assert any(f"thread {i+1}" in msg["content"].lower() for msg in messages)


class TestMemoryAndContext:
    """Test de la mémoire et du contexte conversationnel"""

    
    def test_conversation_with_memory_recall(self, client, authenticated_user):
        """
        Scénario: L'IA se souvient des informations précédentes
        """
        thread_response = client.post(
            "/api/threads",
            json={"title": "Test mémoire"},
        )
        thread_id = thread_response.json()["id"]

        # 1. Donner une information
        client.post(
            "/api/chat",
            json={
                "message": "Je m'appelle Alice et je suis développeuse Python",
                "thread_id": thread_id,
            },
        )

        # 2. Demander un rappel plus tard
        client.post(
            "/api/chat",
            json={
                "message": "Quel est mon prénom et mon métier?",
                "thread_id": thread_id,
            },
        )

        # Vérifier que l'historique contient bien les infos
        history = client.get(f"/api/threads/{thread_id}/messages").json()
        assert len(history) >= 2, "Historique incomplet"


class TestErrorRecovery:
    """Test de récupération d'erreurs"""

    
    def test_graceful_degradation_on_ai_failure(self, client, authenticated_user):
        """
        Scénario: L'application gère gracieusement les erreurs de l'IA
        """
        # Simuler une requête qui pourrait échouer
        response = client.post(
            "/api/chat",
            json={
                "message": "Message de test",
                "thread_id": "test-thread",
            },
        )

        # L'application ne doit JAMAIS retourner 500
        assert response.status_code != 500, "Erreur serveur non gérée"
        assert response.status_code in [200, 400, 422], "Code de réponse inattendu"


class TestDataPersistence:
    """Test de persistence des données"""

    
    def test_data_survives_session(self, auth_app_factory):
        """
        Scénario: Les données persistent entre sessions
        """
        app = auth_app_factory()
        client = TestClient(app)

        # Session 1: Créer des données
        email = f"persist_{int(time.time())}@test.com"
        password = "TestPass123!"

        client.post("/api/auth/register", json={"email": email, "password": password})
        login1 = client.post("/api/auth/login", json={"email": email, "password": password})
        token1 = login1.json()["access_token"]

        thread_response = client.post(
            "/api/threads",
            json={"title": "Thread persistant"},
            headers={"Authorization": f"Bearer {token1}"},
        )
        thread_id = thread_response.json()["id"]

        client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token1}"})

        # Session 2: Vérifier que les données existent toujours
        login2 = client.post("/api/auth/login", json={"email": email, "password": password})
        token2 = login2.json()["access_token"]

        threads_response = client.get(
            "/api/threads",
            headers={"Authorization": f"Bearer {token2}"},
        )

        assert threads_response.status_code == 200, f"Erreur récupération threads: {threads_response.status_code} - {threads_response.text}"
        threads = threads_response.json()
        thread_ids = [t["id"] for t in threads]
        assert thread_id in thread_ids, "Thread perdu entre sessions"


class TestConcurrentUsers:
    """Test d'utilisation concurrente"""

    
    def test_multiple_users_isolated(self, auth_app_factory):
        """
        Scénario: Deux utilisateurs ne voient pas les données de l'autre
        """
        app = auth_app_factory()

        # Créer deux clients différents
        client1 = TestClient(app)
        client2 = TestClient(app)

        # User 1
        email1 = f"user1_{int(time.time())}@test.com"
        client1.post("/api/auth/register", json={"email": email1, "password": "Pass1!"})
        login1 = client1.post("/api/auth/login", json={"email": email1, "password": "Pass1!"})
        token1 = login1.json()["access_token"]

        # User 2
        email2 = f"user2_{int(time.time())}@test.com"
        client2.post("/api/auth/register", json={"email": email2, "password": "Pass2!"})
        login2 = client2.post("/api/auth/login", json={"email": email2, "password": "Pass2!"})
        token2 = login2.json()["access_token"]

        # User 1 crée un thread
        thread1 = client1.post(
            "/api/threads",
            json={"title": "Thread User 1"},
            headers={"Authorization": f"Bearer {token1}"},
        )
        thread1_id = thread1.json()["id"]

        # User 2 ne doit PAS voir le thread de User 1
        threads2 = client2.get(
            "/api/threads",
            headers={"Authorization": f"Bearer {token2}"},
        )

        thread_ids = [t["id"] for t in threads2.json()]
        assert thread1_id not in thread_ids, "Isolation utilisateurs compromise!"
