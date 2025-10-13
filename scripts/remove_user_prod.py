#!/usr/bin/env python3
"""Script pour supprimer un utilisateur de l'allowlist de production"""
import requests
import sys

PROD_API_URL = "https://emergence-app-486095406755.europe-west1.run.app"
ADMIN_EMAIL = "gonzalefernando@gmail.com"
ADMIN_PASSWORD = "Claude1936"
USER_TO_REMOVE = "test@example.com"

def main():
    print(f"[INFO] Suppression de {USER_TO_REMOVE} de la production...")

    # 1. Login
    print("[INFO] Authentification...")
    response = requests.post(
        f"{PROD_API_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=10
    )

    if response.status_code != 200:
        print(f"[ERREUR] Echec de connexion: {response.status_code}")
        print(response.text)
        sys.exit(1)

    token = response.json()["token"]
    print("[OK] Authentifie\n")

    # 2. Supprimer (révoquer) l'utilisateur
    print(f"[INFO] Revocation de {USER_TO_REMOVE}...")
    response = requests.delete(
        f"{PROD_API_URL}/api/auth/admin/allowlist/{USER_TO_REMOVE}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10
    )

    if response.status_code in [200, 204]:
        print(f"[OK] {USER_TO_REMOVE} a ete supprime de la production")
    else:
        print(f"[ERREUR] Echec de suppression: {response.status_code}")
        print(response.text)
        sys.exit(1)

if __name__ == "__main__":
    main()
