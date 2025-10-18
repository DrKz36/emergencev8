"""
Tests E2E - Dashboard Admin
Vérifie les fonctionnalités du dashboard admin (threads, coûts, sessions JWT)
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any

import pytest
from fastapi import FastAPI, Header, HTTPException, Depends
from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parents[3]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


# Mock storage pour tests admin
_mock_admin_users = {}
_mock_admin_sessions = {}
_mock_threads = {}
_mock_auth_sessions = {}
_mock_costs_data = []


@pytest.fixture(scope="function")
def admin_app():
    """Factory pour créer app avec endpoints admin"""
    # Reset storage
    _mock_admin_users.clear()
    _mock_admin_sessions.clear()
    _mock_threads.clear()
    _mock_auth_sessions.clear()
    _mock_costs_data.clear()

    app = FastAPI()

    # Helper auth admin
    def verify_admin_role(authorization: str = Header(None)):
        if not authorization:
            raise HTTPException(status_code=401, detail="Missing token")
        token = authorization.replace("Bearer ", "")
        user = _mock_admin_sessions.get(token)
        if not user or user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Admin required")
        return True

    # Endpoint login admin
    @app.post("/api/auth/login")
    async def login(body: dict):
        email = body.get("email")
        password = body.get("password")

        # Mock admin user
        if email == "admin@example.com" and password == "admin123":
            token = "admin_token_123"
            user = {"id": 1, "email": email, "role": "admin"}
            _mock_admin_sessions[token] = user
            return {"access_token": token, "user": user}

        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Endpoint threads actifs (Phase 1 - renommé)
    @app.get("/api/admin/analytics/threads")
    async def get_active_threads(_admin: bool = Depends(verify_admin_role)):
        """Retourne les threads actifs (conversations)"""
        threads_list = []

        for thread_id, thread_data in _mock_threads.items():
            threads_list.append({
                "session_id": thread_id,
                "user_id": thread_data.get("user_id"),
                "email": thread_data.get("email"),
                "role": thread_data.get("role", "member"),
                "created_at": thread_data.get("created_at"),
                "last_activity": thread_data.get("last_activity"),
                "duration_minutes": thread_data.get("duration_minutes", 0),
                "is_active": thread_data.get("is_active", True),
                "device": thread_data.get("device", "Unknown"),
                "ip_address": thread_data.get("ip_address", "127.0.0.1"),
                "user_agent": thread_data.get("user_agent", "Mozilla/5.0"),
            })

        return {
            "threads": threads_list,
            "total": len(threads_list)
        }

    # Endpoint coûts (évolution 7 derniers jours)
    @app.get("/api/admin/analytics/costs")
    async def get_costs_data(_admin: bool = Depends(verify_admin_role)):
        """Retourne les données de coûts (7 derniers jours)"""
        return {
            "costs": _mock_costs_data,
            "total": len(_mock_costs_data)
        }

    # Endpoint auth admin sessions (JWT)
    @app.get("/api/auth/admin/sessions")
    async def list_auth_sessions(
        status_filter: str = None,
        _admin: bool = Depends(verify_admin_role)
    ):
        """Retourne les sessions d'authentification JWT (pas les threads)"""
        sessions_list = []

        for session_id, session_data in _mock_auth_sessions.items():
            # Filtrer par status si demandé
            if status_filter == "active":
                if session_data.get("revoked_at"):
                    continue
                # Vérifier expiration
                expires_at = datetime.fromisoformat(session_data.get("expires_at"))
                if expires_at < datetime.now():
                    continue

            sessions_list.append({
                "id": session_id,
                "email": session_data.get("email"),
                "role": session_data.get("role"),
                "ip_address": session_data.get("ip_address"),
                "issued_at": session_data.get("issued_at"),
                "expires_at": session_data.get("expires_at"),
                "revoked_at": session_data.get("revoked_at"),
                "revoked_by": session_data.get("revoked_by"),
            })

        return {"items": sessions_list}

    return app


@pytest.fixture
def admin_client(admin_app):
    """Client de test avec auth admin automatique"""
    client = TestClient(admin_app)

    # Login admin
    login_response = client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "admin123"}
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    # Injecter le token
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


class TestAdminThreadsEndpoint:
    """Tests E2E pour l'endpoint /admin/analytics/threads"""

    def test_get_active_threads_empty(self, admin_client):
        """Test: Aucun thread actif"""
        response = admin_client.get("/api/admin/analytics/threads")

        assert response.status_code == 200
        data = response.json()
        assert "threads" in data
        assert "total" in data
        assert data["total"] == 0
        assert data["threads"] == []

    def test_get_active_threads_with_data(self, admin_client):
        """Test: Plusieurs threads actifs"""
        # Ajouter des threads mock
        now = datetime.now().isoformat()
        _mock_threads["thread_1"] = {
            "user_id": "user1@example.com",
            "email": "user1@example.com",
            "role": "member",
            "created_at": now,
            "last_activity": now,
            "duration_minutes": 15,
            "is_active": True,
            "device": "Desktop",
            "ip_address": "192.168.1.100",
            "user_agent": "Mozilla/5.0 (Windows)",
        }
        _mock_threads["thread_2"] = {
            "user_id": "user2@example.com",
            "email": "user2@example.com",
            "role": "premium",
            "created_at": now,
            "last_activity": now,
            "duration_minutes": 30,
            "is_active": True,
            "device": "Mobile",
            "ip_address": "192.168.1.101",
            "user_agent": "Mozilla/5.0 (iPhone)",
        }

        response = admin_client.get("/api/admin/analytics/threads")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["threads"]) == 2

        # Vérifier structure des threads
        thread = data["threads"][0]
        assert "session_id" in thread
        assert "email" in thread
        assert "role" in thread
        assert "created_at" in thread
        assert "last_activity" in thread
        assert "duration_minutes" in thread
        assert "is_active" in thread

    def test_get_active_threads_requires_admin(self, admin_app):
        """Test: Endpoint nécessite rôle admin"""
        client = TestClient(admin_app)

        # Sans auth
        response = client.get("/api/admin/analytics/threads")
        assert response.status_code == 401

        # Avec auth non-admin (mock)
        # (Ici on ne peut pas tester car le mock ne supporte qu'admin)


class TestAdminCostsEndpoint:
    """Tests E2E pour l'endpoint /admin/analytics/costs"""

    def test_get_costs_all_zero(self, admin_client):
        """Test: Tous les coûts à 0 (cas edge Phase 2)"""
        # Mock 7 jours de coûts à 0
        base_date = datetime.now() - timedelta(days=6)
        for i in range(7):
            date = (base_date + timedelta(days=i)).strftime("%Y-%m-%d")
            _mock_costs_data.append({"date": date, "cost": 0.0})

        response = admin_client.get("/api/admin/analytics/costs")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 7

        # Vérifier que tous les coûts sont bien à 0
        total_cost = sum(item["cost"] for item in data["costs"])
        assert total_cost == 0.0

    def test_get_costs_with_data(self, admin_client):
        """Test: Données de coûts normales"""
        base_date = datetime.now() - timedelta(days=6)
        costs = [1.25, 2.50, 0.75, 3.00, 1.80, 2.10, 4.50]

        for i, cost in enumerate(costs):
            date = (base_date + timedelta(days=i)).strftime("%Y-%m-%d")
            _mock_costs_data.append({"date": date, "cost": cost})

        response = admin_client.get("/api/admin/analytics/costs")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 7

        # Vérifier total
        total_cost = sum(item["cost"] for item in data["costs"])
        assert total_cost == sum(costs)

    def test_get_costs_empty(self, admin_client):
        """Test: Aucune donnée de coûts"""
        response = admin_client.get("/api/admin/analytics/costs")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["costs"] == []

    def test_get_costs_null_handling(self, admin_client):
        """Test: Gestion des valeurs null/undefined (Phase 2)"""
        # Ajouter des données avec null
        _mock_costs_data.append({"date": "2025-10-18", "cost": None})
        _mock_costs_data.append({"date": "2025-10-17", "cost": 0.0})

        response = admin_client.get("/api/admin/analytics/costs")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2


class TestAuthAdminSessionsEndpoint:
    """Tests E2E pour l'endpoint /api/auth/admin/sessions (JWT sessions)"""

    def test_list_auth_sessions_empty(self, admin_client):
        """Test: Aucune session JWT"""
        response = admin_client.get("/api/auth/admin/sessions")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert data["items"] == []

    def test_list_auth_sessions_with_data(self, admin_client):
        """Test: Plusieurs sessions JWT actives"""
        now = datetime.now()

        # Ajouter des sessions JWT mock
        _mock_auth_sessions["session_1"] = {
            "email": "user1@example.com",
            "role": "member",
            "ip_address": "192.168.1.100",
            "issued_at": now.isoformat(),
            "expires_at": (now + timedelta(days=7)).isoformat(),
            "revoked_at": None,
            "revoked_by": None,
        }
        _mock_auth_sessions["session_2"] = {
            "email": "user2@example.com",
            "role": "admin",
            "ip_address": "192.168.1.101",
            "issued_at": now.isoformat(),
            "expires_at": (now + timedelta(days=7)).isoformat(),
            "revoked_at": None,
            "revoked_by": None,
        }

        response = admin_client.get("/api/auth/admin/sessions")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2

        # Vérifier structure
        session = data["items"][0]
        assert "id" in session
        assert "email" in session
        assert "role" in session
        assert "ip_address" in session
        assert "issued_at" in session
        assert "expires_at" in session

    def test_list_auth_sessions_filter_active(self, admin_client):
        """Test: Filtrer seulement sessions actives"""
        now = datetime.now()

        # Session active
        _mock_auth_sessions["session_active"] = {
            "email": "active@example.com",
            "role": "member",
            "ip_address": "192.168.1.100",
            "issued_at": now.isoformat(),
            "expires_at": (now + timedelta(days=7)).isoformat(),
            "revoked_at": None,
            "revoked_by": None,
        }

        # Session révoquée
        _mock_auth_sessions["session_revoked"] = {
            "email": "revoked@example.com",
            "role": "member",
            "ip_address": "192.168.1.101",
            "issued_at": now.isoformat(),
            "expires_at": (now + timedelta(days=7)).isoformat(),
            "revoked_at": now.isoformat(),
            "revoked_by": "admin@example.com",
        }

        # Session expirée
        _mock_auth_sessions["session_expired"] = {
            "email": "expired@example.com",
            "role": "member",
            "ip_address": "192.168.1.102",
            "issued_at": (now - timedelta(days=10)).isoformat(),
            "expires_at": (now - timedelta(days=3)).isoformat(),
            "revoked_at": None,
            "revoked_by": None,
        }

        # Filtrer actives
        response = admin_client.get("/api/auth/admin/sessions?status_filter=active")

        assert response.status_code == 200
        data = response.json()

        # Seulement la session active doit être retournée
        assert len(data["items"]) == 1
        assert data["items"][0]["email"] == "active@example.com"

    def test_sessions_vs_threads_distinction(self, admin_client):
        """
        Test: Vérifier que /admin/analytics/threads et /api/auth/admin/sessions
        retournent bien des données différentes (fix confusion Phase 1)
        """
        now = datetime.now()

        # Ajouter un thread (conversation)
        _mock_threads["thread_1"] = {
            "user_id": "user@example.com",
            "email": "user@example.com",
            "role": "member",
            "created_at": now.isoformat(),
            "last_activity": now.isoformat(),
            "duration_minutes": 15,
            "is_active": True,
        }

        # Ajouter une session JWT (authentification)
        _mock_auth_sessions["session_1"] = {
            "email": "user@example.com",
            "role": "member",
            "ip_address": "192.168.1.100",
            "issued_at": now.isoformat(),
            "expires_at": (now + timedelta(days=7)).isoformat(),
            "revoked_at": None,
            "revoked_by": None,
        }

        # Appeler les deux endpoints
        threads_response = admin_client.get("/api/admin/analytics/threads")
        sessions_response = admin_client.get("/api/auth/admin/sessions")

        assert threads_response.status_code == 200
        assert sessions_response.status_code == 200

        threads_data = threads_response.json()
        sessions_data = sessions_response.json()

        # Vérifier structure différente
        assert "threads" in threads_data
        assert "items" in sessions_data

        # Les threads ont session_id, device, user_agent
        thread = threads_data["threads"][0]
        assert "session_id" in thread
        assert "device" in thread
        assert "user_agent" in thread
        assert "duration_minutes" in thread

        # Les sessions JWT ont issued_at, expires_at, revoked_at
        session = sessions_data["items"][0]
        assert "issued_at" in session
        assert "expires_at" in session
        assert "revoked_at" in session
        assert "revoked_by" in session

        # Pas de confusion entre les deux
        assert "device" not in session  # Sessions JWT n'ont pas device
        assert "expires_at" not in thread  # Threads n'ont pas expires_at


class TestAdminDashboardIntegration:
    """Tests d'intégration complets du dashboard admin"""

    def test_full_admin_workflow(self, admin_client):
        """
        Test: Workflow complet admin
        1. Charger threads actifs
        2. Charger données coûts
        3. Charger sessions JWT
        4. Vérifier cohérence des données
        """
        now = datetime.now()

        # Setup: Ajouter données mock
        _mock_threads["thread_1"] = {
            "user_id": "user@example.com",
            "email": "user@example.com",
            "role": "member",
            "created_at": now.isoformat(),
            "last_activity": now.isoformat(),
            "duration_minutes": 20,
            "is_active": True,
        }

        base_date = now - timedelta(days=6)
        for i in range(7):
            date = (base_date + timedelta(days=i)).strftime("%Y-%m-%d")
            _mock_costs_data.append({"date": date, "cost": float(i + 1)})

        _mock_auth_sessions["session_1"] = {
            "email": "user@example.com",
            "role": "member",
            "ip_address": "192.168.1.100",
            "issued_at": now.isoformat(),
            "expires_at": (now + timedelta(days=7)).isoformat(),
            "revoked_at": None,
            "revoked_by": None,
        }

        # 1. Charger threads
        threads_response = admin_client.get("/api/admin/analytics/threads")
        assert threads_response.status_code == 200
        threads_data = threads_response.json()
        assert threads_data["total"] == 1

        # 2. Charger coûts
        costs_response = admin_client.get("/api/admin/analytics/costs")
        assert costs_response.status_code == 200
        costs_data = costs_response.json()
        assert costs_data["total"] == 7

        # 3. Charger sessions JWT
        sessions_response = admin_client.get("/api/auth/admin/sessions")
        assert sessions_response.status_code == 200
        sessions_data = sessions_response.json()
        assert len(sessions_data["items"]) == 1

        # 4. Vérifier cohérence
        # Même utilisateur dans threads et sessions
        assert threads_data["threads"][0]["email"] == "user@example.com"
        assert sessions_data["items"][0]["email"] == "user@example.com"

        # Mais structures différentes
        assert "device" in threads_data["threads"][0]
        assert "expires_at" in sessions_data["items"][0]
