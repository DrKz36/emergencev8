# Scripts de Test - Système d'Emails Membres

Ce dossier contient des scripts de test pour le système d'envoi d'emails aux membres.

## Scripts disponibles

### `test_member_emails_system.py`
**Script principal de test du système d'emails**

- Teste le service d'email backend
- Affiche les templates disponibles
- Permet d'envoyer un email de test
- Affiche la documentation des endpoints API

**Usage :**
```bash
python scripts/test/test_member_emails_system.py
```

### `preview_auth_issue_email.py`
Prévisualisation du template d'email "problème d'authentification" (HTML + texte)

### `send_auth_email_confirmed.py`
Script d'envoi d'emails aux utilisateurs confirmés

### `send_auth_email_to_selected.py`
Script d'envoi d'emails à une sélection d'utilisateurs

### `send_test_auth_email.py`
Script de test rapide pour envoyer un email d'authentification

## Configuration requise

Assurez-vous que les variables d'environnement SMTP sont configurées :

```env
EMAIL_ENABLED=1
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=your-email@gmail.com
SMTP_FROM_NAME=ÉMERGENCE
SMTP_USE_TLS=1
```

## Documentation complète

Voir [docs/MEMBER_EMAILS_SYSTEM.md](../../docs/MEMBER_EMAILS_SYSTEM.md) pour la documentation complète du système d'emails membres.

## Phase

Ces scripts ont été créés durant le développement du système d'emails membres (2025-10-16).
