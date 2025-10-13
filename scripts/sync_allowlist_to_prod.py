#!/usr/bin/env python3
"""
Script pour synchroniser l'allowlist locale vers la production
Usage: python scripts/sync_allowlist_to_prod.py
"""
import sqlite3
import requests
import sys
import os
from pathlib import Path

# Configuration
LOCAL_DB_PATH = "src/backend/data/db/emergence_v7.db"
PROD_API_URL = "https://emergence-app-486095406755.europe-west1.run.app"
ADMIN_EMAIL = "gonzalefernando@gmail.com"

def get_local_allowlist():
    """Récupère l'allowlist de la base locale"""
    db_path = Path(__file__).parent.parent / LOCAL_DB_PATH
    if not db_path.exists():
        print(f"[ERREUR] Base de donnees locale introuvable: {db_path}")
        sys.exit(1)

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute('''
        SELECT email, role, note, password_must_reset
        FROM auth_allowlist
        WHERE revoked_at IS NULL
        ORDER BY email
    ''')
    users = cursor.fetchall()
    conn.close()

    return [
        {
            "email": row[0],
            "role": row[1],
            "note": row[2] or "",
            "password_must_reset": bool(row[3])
        }
        for row in users
    ]

def get_prod_token(password):
    """Obtient un token admin de production"""
    response = requests.post(
        f"{PROD_API_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": password},
        timeout=10
    )

    if response.status_code != 200:
        print(f"[ERREUR] Echec de connexion admin: {response.status_code}")
        print(response.text)
        sys.exit(1)

    return response.json()["token"]

def get_prod_allowlist(token):
    """Récupère l'allowlist de production"""
    response = requests.get(
        f"{PROD_API_URL}/api/auth/admin/allowlist?page=1&page_size=100",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10
    )

    if response.status_code != 200:
        print(f"[ERREUR] Echec de recuperation allowlist prod: {response.status_code}")
        print(response.text)
        sys.exit(1)

    data = response.json()
    # La clé peut être "users" ou "entries"
    users = data.get("users") or data.get("entries") or []
    return {user["email"]: user for user in users}

def add_user_to_prod(token, user):
    """Ajoute un utilisateur à l'allowlist de production"""
    response = requests.post(
        f"{PROD_API_URL}/api/auth/admin/allowlist",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "email": user["email"],
            "role": user["role"],
            "note": user["note"]
        },
        timeout=10
    )

    return response.status_code in [200, 201]

def main():
    print("=== Synchronisation de l'allowlist vers la production ===\n")

    # Demander le mot de passe admin
    password = input(f"Mot de passe admin pour {ADMIN_EMAIL} en production: ")
    if not password:
        print("[ERREUR] Mot de passe requis")
        sys.exit(1)

    # Obtenir token admin
    print("[INFO] Authentification...")
    token = get_prod_token(password)
    print("[OK] Authentifie\n")

    # Récupérer les allowlists
    print("[INFO] Recuperation des allowlists...")
    local_users = get_local_allowlist()
    prod_users_dict = get_prod_allowlist(token)
    print(f"   Local: {len(local_users)} utilisateurs")
    print(f"   Prod:  {len(prod_users_dict)} utilisateurs\n")

    # Trouver les différences
    to_add = []
    for user in local_users:
        if user["email"] not in prod_users_dict:
            to_add.append(user)

    if not to_add:
        print("[OK] Aucune difference trouvee - allowlists synchronisees")
        return

    print(f"[INFO] Utilisateurs a ajouter en production ({len(to_add)}):")
    for user in to_add:
        print(f"   - {user['email']} ({user['role']})")

    # Confirmer
    confirm = input("\n[WARNING] Confirmer l'ajout en production? (y/N): ")
    if confirm.lower() != 'y':
        print("[ANNULE]")
        sys.exit(0)

    # Ajouter les utilisateurs
    print("\n[INFO] Ajout des utilisateurs...")
    success_count = 0
    for user in to_add:
        if add_user_to_prod(token, user):
            print(f"   [OK] {user['email']}")
            success_count += 1
        else:
            print(f"   [ERREUR] {user['email']} (echec)")

    print(f"\n[OK] Synchronisation terminee: {success_count}/{len(to_add)} utilisateurs ajoutes")

if __name__ == "__main__":
    main()
