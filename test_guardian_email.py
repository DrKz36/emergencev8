#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script pour envoyer un email Guardian avec rapport enrichi
"""

import asyncio
import sys
from pathlib import Path

# Ajouter le backend au path
backend_path = Path(__file__).parent / "src" / "backend"
sys.path.insert(0, str(backend_path))

from features.guardian.email_report import GuardianEmailService


async def main():
    """Test sending Guardian email with enriched prod_report.json"""

    print("=" * 70)
    print("TEST GUARDIAN EMAIL - Rapport Enrichi")
    print("=" * 70)
    print()

    # Créer le service (il va charger depuis reports/ du repo)
    service = GuardianEmailService()

    print("📧 Envoi du rapport à gonzalefernando@gmail.com...")
    print()

    # Envoyer l'email
    success = await service.send_report(
        to_email="gonzalefernando@gmail.com",
        base_url="https://emergence-app-486095406755.europe-west1.run.app"
    )

    print()
    print("=" * 70)
    if success:
        print("✅ Email envoyé avec succès!")
        print()
        print("📊 Le rapport devrait contenir:")
        print("   - ❌ Erreurs détaillées avec stack traces")
        print("   - 🔍 Analyse de patterns (endpoint/fichier/type)")
        print("   - 💻 Code snippets suspects")
        print("   - 🔀 Commits récents (coupables potentiels)")
        print()
        print("👀 Vérifie ta boîte mail: gonzalefernando@gmail.com")
    else:
        print("❌ Échec de l'envoi de l'email")
        print()
        print("⚠️  Vérifie que les variables d'environnement sont configurées:")
        print("   - EMAIL_ENABLED=1")
        print("   - SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD")
    print("=" * 70)

    return success


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
