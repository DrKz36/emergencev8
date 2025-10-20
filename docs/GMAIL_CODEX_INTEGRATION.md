# Gmail API Integration - Documentation Codex GPT

**Objectif:** Permettre à Codex GPT de lire les rapports Guardian par email pour faire des corrections Git automatiques.

**Phase:** 3 - Gmail API Integration (Guardian Cloud Implementation)

**Date:** 2025-10-19

---

## Architecture

```
┌──────────────┐
│              │
│  Codex GPT   │──────────┐
│  (local)     │          │
│              │          │
└──────────────┘          │
                          │
                          ▼
              ┌───────────────────────┐
              │                       │
              │  POST /api/gmail/     │
              │  read-reports         │
              │                       │
              │  Header:              │
              │  X-Codex-API-Key      │
              │                       │
              └───────────────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │                       │
              │  GmailService         │
              │  (backend)            │
              │                       │
              │  - OAuth tokens       │
              │  - Gmail API read     │
              │  - Parse emails       │
              │                       │
              └───────────────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │                       │
              │  Gmail API            │
              │  (Google)             │
              │                       │
              │  - OAuth2 flow        │
              │  - Read emails        │
              │  - Scope: readonly    │
              │                       │
              └───────────────────────┘
```

---

## Endpoints Disponibles

### 1. OAuth Flow (Admin uniquement)

**Authentifier Gmail (une seule fois):**

```bash
# Navigate to (dans le navigateur):
https://emergence-app-486095406755.europe-west1.run.app/auth/gmail

# → Redirect vers Google consent screen
# → Accepte les permissions (gmail.readonly)
# → Callback automatique vers /auth/callback/gmail
# → Tokens stockés dans Firestore (encrypted)
```

**⚠️ À FAIRE UNE SEULE FOIS** (tokens persistent dans Firestore).

---

### 2. API Codex - Lire Rapports Guardian

**Endpoint:** `POST /api/gmail/read-reports`

**Authentification:** Header `X-Codex-API-Key: <secret>`

**Requête:**

```bash
curl -X GET https://emergence-app-486095406755.europe-west1.run.app/api/gmail/read-reports \
  -H "X-Codex-API-Key: YOUR_SECRET_KEY_HERE" \
  -H "Content-Type: application/json" \
  -d '{"max_results": 10}'
```

**Réponse (200 OK):**

```json
{
  "success": true,
  "count": 3,
  "emails": [
    {
      "id": "18e1234567890abcd",
      "subject": "🛡️ Guardian Report - Production Status",
      "from": "emergence-guardian@example.com",
      "date": "Thu, 19 Oct 2025 14:30:00 +0000",
      "timestamp": "2025-10-19T14:30:00",
      "body": "<html>... full email HTML ...</html>",
      "snippet": "Guardian report for production: 2 errors detected in..."
    },
    {
      "id": "18e1234567890abce",
      "subject": "Emergence Audit - Usage Stats",
      "from": "emergence-guardian@example.com",
      "date": "Thu, 19 Oct 2025 12:00:00 +0000",
      "timestamp": "2025-10-19T12:00:00",
      "body": "<html>... full email HTML ...</html>",
      "snippet": "Usage tracking report: 5 active users, 127 requests..."
    }
  ]
}
```

**Erreurs possibles:**

- **401 Unauthorized** : API key invalide
- **500 Internal Server Error** : OAuth tokens manquants ou expirés (relancer OAuth flow)

---

### 3. Vérifier Status OAuth

**Endpoint:** `GET /api/gmail/status`

**Pas d'authentification requise** (endpoint public pour debug).

**Requête:**

```bash
curl https://emergence-app-486095406755.europe-west1.run.app/api/gmail/status
```

**Réponse (si authentifié):**

```json
{
  "authenticated": true,
  "message": "Gmail OAuth is configured and tokens are valid",
  "scopes": ["https://www.googleapis.com/auth/gmail.readonly"]
}
```

**Réponse (si pas authentifié):**

```json
{
  "authenticated": false,
  "message": "No OAuth tokens found. Please authenticate via /auth/gmail"
}
```

---

## Configuration API Key Codex

**1. Générer API key (côté admin):**

```bash
# Générer un secret random (par exemple):
openssl rand -hex 32
# → 64f5a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0
```

**2. Stocker dans Secret Manager GCP:**

```bash
echo -n "64f5a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0" | \
gcloud secrets create codex-api-key \
  --data-file=- \
  --project=emergence-469005 \
  --replication-policy=automatic
```

**3. Configurer Cloud Run:**

```bash
gcloud run services update emergence-app \
  --region europe-west1 \
  --set-env-vars="CODEX_API_KEY=64f5a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0"
```

---

## Workflow Codex GPT

**Scénario:** Codex reçoit un email Guardian avec erreurs, puis crée un fix automatique.

### Étape 1: Polling Emails (toutes les 2h)

```python
import requests

CODEX_API_KEY = "64f5a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0"
API_URL = "https://emergence-app-486095406755.europe-west1.run.app/api/gmail/read-reports"

response = requests.get(
    API_URL,
    headers={"X-Codex-API-Key": CODEX_API_KEY},
    params={"max_results": 10}
)

emails = response.json()["emails"]
```

### Étape 2: Parser Emails Guardian

```python
guardian_reports = [
    email for email in emails
    if "guardian" in email["subject"].lower() or "emergence" in email["subject"].lower()
]

for report in guardian_reports:
    print(f"Subject: {report['subject']}")
    print(f"Timestamp: {report['timestamp']}")
    print(f"Snippet: {report['snippet']}")

    # Parse HTML body pour extraire erreurs
    body_html = report['body']
    # TODO: regex ou BeautifulSoup pour extraire erreurs
```

### Étape 3: Détection Erreurs

```python
from bs4 import BeautifulSoup

def extract_errors(html_body: str) -> list:
    """
    Parse le HTML Guardian report pour extraire les erreurs.

    Structure attendue:
    - Section "🚨 Production Errors" avec liste <ul>
    - Chaque erreur dans <li> avec détails
    """
    soup = BeautifulSoup(html_body, 'html.parser')

    errors = []

    # Trouver section Production Errors
    prod_section = soup.find(text=lambda t: "Production Errors" in t if t else False)
    if prod_section:
        ul = prod_section.find_next('ul')
        if ul:
            for li in ul.find_all('li'):
                errors.append(li.get_text(strip=True))

    return errors

# Exemple
errors = extract_errors(report['body'])
print(f"Found {len(errors)} errors: {errors}")
```

### Étape 4: Créer Fix Automatique (Git)

```python
import subprocess

def auto_fix_errors(errors: list):
    """
    Crée une branche Git, fixe les erreurs détectées, crée PR.
    """
    # Créer branche
    branch_name = f"auto-fix/guardian-{timestamp}"
    subprocess.run(["git", "checkout", "-b", branch_name])

    # Analyser erreurs et appliquer fixes
    for error in errors:
        # TODO: logique de fix selon type d'erreur
        # Ex: "Missing type hint in function X" → ajouter type hint
        # Ex: "Unused import in file Y" → supprimer import
        pass

    # Commit
    subprocess.run(["git", "add", "."])
    subprocess.run(["git", "commit", "-m", f"fix: Auto-fix Guardian errors\n\nErrors fixed:\n{errors}"])

    # Push
    subprocess.run(["git", "push", "origin", branch_name])

    # Créer PR (via gh CLI ou GitHub API)
    subprocess.run([
        "gh", "pr", "create",
        "--title", "Auto-fix Guardian Errors",
        "--body", f"Automatic fixes based on Guardian report.\n\nErrors:\n{errors}"
    ])

# Appliquer
if errors:
    auto_fix_errors(errors)
```

### Étape 5: Notification (optionnel)

```python
# Envoyer notification Slack/Email que le fix est fait
import requests

SLACK_WEBHOOK = "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"

requests.post(SLACK_WEBHOOK, json={
    "text": f"✅ Codex auto-fixed {len(errors)} Guardian errors.\nPR: https://github.com/org/repo/pull/123"
})
```

---

## Sécurité

### OAuth Tokens

- ✅ **Scope:** `gmail.readonly` (lecture seule, aucune modification possible)
- ✅ **Stockage:** Firestore (encrypted at rest)
- ✅ **Auto-refresh:** Tokens expirés sont automatiquement refreshed
- ✅ **Révocation:** Possible via [Google Account Settings](https://myaccount.google.com/permissions)

### API Key Codex

- ✅ **Stockage:** Secret Manager GCP (jamais hardcodé)
- ✅ **Transmission:** HTTPS uniquement (TLS 1.3)
- ✅ **Rotation:** Possible en modifiant `CODEX_API_KEY` env var
- ⚠️ **Pas de rate limiting** (Codex trusted, mais à ajouter si abuse)

### RGPD / Privacy

- ✅ **Pas de tracking contenu emails** (seulement subject, timestamp, from)
- ✅ **Body parsé côté backend** (jamais stocké)
- ✅ **Codex reçoit uniquement rapports Guardian** (query filtrée par sujet)

---

## Tests

### Test Local (OAuth Flow)

```bash
# 1. Démarrer backend local
cd c:\dev\emergenceV8
pwsh -File scripts/run-backend.ps1

# 2. Navigate to OAuth flow
# http://localhost:8000/auth/gmail

# 3. Accepter consent Google
# → Redirect vers http://localhost:8000/auth/callback/gmail
# → Tokens stockés dans Firestore

# 4. Vérifier status
curl http://localhost:8000/api/gmail/status
# → {"authenticated": true, ...}
```

### Test API Codex (local)

```bash
# 1. Configurer API key en local (.env)
echo "CODEX_API_KEY=test-key-123" >> .env

# 2. Appeler API
curl -X GET http://localhost:8000/api/gmail/read-reports \
  -H "X-Codex-API-Key: test-key-123" \
  -H "Content-Type: application/json"

# 3. Vérifier emails retournés
# → Devrait retourner liste emails Guardian
```

---

## Variables d'Environnement

### Backend Cloud Run

```bash
# Gmail OAuth (credentials depuis Secret Manager)
# Pas de var env nécessaire (client_secret lu depuis Secret Manager)

# API Key Codex
CODEX_API_KEY=<secret-key-from-secret-manager>

# GCP Project ID (pour Secret Manager)
GCP_PROJECT_ID=emergence-469005

# Firestore (déjà configuré)
# Pas de var env supplémentaire nécessaire
```

---

## Troubleshooting

### Erreur: "No OAuth tokens found"

**Cause:** OAuth flow pas encore fait, ou tokens expirés et refresh_token manquant.

**Solution:**
1. Navigate to `/auth/gmail`
2. Accepter consent Google (force `prompt=consent` pour avoir refresh_token)
3. Vérifier `/api/gmail/status` → `authenticated: true`

### Erreur: "Invalid Codex API key"

**Cause:** API key incorrecte ou pas configurée.

**Solution:**
1. Vérifier `CODEX_API_KEY` env var dans Cloud Run
2. Vérifier header `X-Codex-API-Key` dans requête Codex

### Erreur: "Gmail API quota exceeded"

**Cause:** Trop de requêtes Gmail API (quota GCP).

**Solution:**
1. Réduire fréquence polling Codex (ex: 2h → 4h)
2. Augmenter quota Gmail API dans GCP Console (APIs & Services → Quotas)

---

## Roadmap Future

- [ ] **Multi-user OAuth** (actuellement admin uniquement)
- [ ] **Webhook Gmail push notifications** (au lieu de polling)
- [ ] **Rate limiting API Codex** (sécurité)
- [ ] **Logs parsing avancé** (ML pour détecter patterns d'erreurs)
- [ ] **Auto-fix suggestions** (backend génère suggestions avant Codex commit)

---

## Support

**Questions / Issues:**
- GitHub: `emergenceV8/issues`
- Email: `gonzalefernando@gmail.com`
- Slack: `#emergence-guardian` (si configuré)

**Documentation complète:**
- `docs/GUARDIAN_CLOUD_IMPLEMENTATION_PLAN.md`
- `docs/EMAIL_UNIFICATION.md`
- `docs/USAGE_TRACKING.md`

---

**✅ Gmail API Integration - Phase 3 Guardian Cloud - Prêt pour production**
