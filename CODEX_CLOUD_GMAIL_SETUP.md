# 📧 Configuration Gmail pour Codex Cloud - Guide Rapide

**Date:** 2025-10-20
**Status:** ✅ Tout est déjà configuré côté backend !

---

## 🎯 Résumé

Codex Cloud peut accéder aux emails Guardian via l'API Cloud Run déjà déployée en production. Pas besoin de config Gmail directe côté Codex, tout passe par l'API sécurisée.

**Ce qui est déjà fait :**
- ✅ Gmail API OAuth2 configurée (backend)
- ✅ Endpoint Codex API déployé en production
- ✅ Secrets GCP configurés
- ✅ Cloud Run 100% opérationnel

**Ce qu'il te reste à faire :**
1. Autoriser Gmail OAuth (one-time, 2 min) ← **TOI, EN TANT QU'ADMIN**
2. Donner les credentials à Codex Cloud ← **TOI, CONFIG CODEX**
3. Tester l'accès depuis Codex ← **CODEX**

---

## 📋 Prérequis pour Codex Cloud

### 1. Credentials à fournir à Codex

**Codex Cloud a besoin de ces 2 infos uniquement :**

```bash
# API Endpoint (production)
API_URL=https://emergence-app-486095406755.europe-west1.run.app/api/gmail/read-reports

# API Key (authentication)
CODEX_API_KEY=77bc68b9d3c0a2ebed19c0cdf73281b44d9b6736c21eae367766f4184d9951cb
```

**Où les mettre dans Codex Cloud :**
- Si Codex utilise `.env` → Ajouter ces 2 lignes dans son `.env`
- Si Codex utilise variables d'environnement → Les configurer dans son cloud (GCP Secret Manager, AWS Secrets, etc.)
- Si Codex utilise config JSON → Ajouter dans son fichier de config

**⚠️ Important :** Ces credentials doivent être **sécurisés** (jamais en clair dans le code, toujours dans secrets management).

---

## 🚀 Étape 1: Autoriser Gmail OAuth (TOI - One-Time)

**Objectif :** Permettre à l'app backend de lire tes emails Guardian.

**Action :**

1. Ouvre ce lien dans ton navigateur (connecté avec gonzalefernando@gmail.com) :
   ```
   https://emergence-app-486095406755.europe-west1.run.app/auth/gmail
   ```

2. Tu seras redirigé vers Google consent screen :
   - ✅ Vérifie que c'est bien ton projet GCP "emergence-469005"
   - ✅ Scope demandé : **"Lecture seule de tes emails"** (gmail.readonly)
   - ✅ Clique sur **"Autoriser"**

3. Après autorisation :
   - Tu seras redirigé vers `/auth/callback/gmail`
   - Page de confirmation affichée
   - **Tokens OAuth stockés automatiquement dans Firestore**

**Résultat attendu :**
```
✅ OAuth tokens stockés dans Firestore (collection: gmail_oauth_tokens)
✅ Backend peut maintenant lire tes emails Guardian
```

**Durée :** 2 minutes max
**Fréquence :** **UNE SEULE FOIS** (tokens persistent, refresh automatique)

---

## 🔧 Étape 2: Configurer Codex Cloud

**Objectif :** Donner les credentials Codex à ton agent Codex Cloud.

### Option A: Variables d'environnement (recommandé)

Si Codex Cloud utilise des variables d'environnement (GCP Cloud Run, AWS Lambda, etc.) :

```bash
# Ajouter dans la configuration cloud de Codex
EMERGENCE_API_URL=https://emergence-app-486095406755.europe-west1.run.app/api/gmail/read-reports
EMERGENCE_CODEX_API_KEY=77bc68b9d3c0a2ebed19c0cdf73281b44d9b6736c21eae367766f4184d9951cb
```

### Option B: Fichier .env local

Si Codex Cloud tourne en local ou avec `.env` :

Créer/modifier `.env` dans le dépôt Codex :

```env
# Émergence Guardian API
EMERGENCE_API_URL=https://emergence-app-486095406755.europe-west1.run.app/api/gmail/read-reports
EMERGENCE_CODEX_API_KEY=77bc68b9d3c0a2ebed19c0cdf73281b44d9b6736c21eae367766f4184d9951cb
```

### Option C: Config JSON

Si Codex Cloud utilise un fichier de config JSON :

```json
{
  "emergence": {
    "api_url": "https://emergence-app-486095406755.europe-west1.run.app/api/gmail/read-reports",
    "codex_api_key": "77bc68b9d3c0a2ebed19c0cdf73281b44d9b6736c21eae367766f4184d9951cb"
  }
}
```

---

## 🧪 Étape 3: Test d'Accès depuis Codex

**Objectif :** Vérifier que Codex Cloud peut lire les emails Guardian.

### Test manuel (curl)

Depuis n'importe quelle machine (ou depuis Codex Cloud) :

```bash
curl -X POST \
  "https://emergence-app-486095406755.europe-west1.run.app/api/gmail/read-reports?max_results=5" \
  -H "X-Codex-API-Key: 77bc68b9d3c0a2ebed19c0cdf73281b44d9b6736c21eae367766f4184d9951cb" \
  -H "Content-Type: application/json"
```

**Résultat attendu (200 OK) :**

```json
{
  "success": true,
  "count": 3,
  "emails": [
    {
      "id": "abc123def456",
      "subject": "🛡️ Guardian Report - ÉMERGENCE V8",
      "from": "gonzalefernando@gmail.com",
      "date": "2025-10-20T06:05:00Z",
      "body_text": "Status: OK\nErrors: 0\nWarnings: 0...",
      "body_html": "<html>...rapport complet...</html>",
      "snippet": "Status: OK - Production healthy...",
      "timestamp": "2025-10-20T06:05:00Z"
    },
    ...
  ]
}
```

**Si erreur :**
- ❌ `401 Unauthorized` → Vérifier API key (header `X-Codex-API-Key`)
- ❌ `403 Forbidden` → Refaire OAuth flow (Étape 1)
- ❌ `500 Internal Error` → Checker logs Cloud Run

### Test depuis Codex Cloud (Python)

Ajouter ce code dans Codex Cloud :

```python
import requests
import os

# Config (depuis .env ou variables d'environnement)
API_URL = os.getenv("EMERGENCE_API_URL")
CODEX_API_KEY = os.getenv("EMERGENCE_CODEX_API_KEY")

def fetch_guardian_emails(max_results=10):
    """Fetch Guardian emails from Emergence API"""
    try:
        response = requests.get(
            API_URL,
            headers={"X-Codex-API-Key": CODEX_API_KEY},
            params={"max_results": max_results},
            timeout=30
        )
        response.raise_for_status()
        data = response.json()

        print(f"✅ Fetched {data['count']} emails from Guardian")
        return data['emails']

    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP Error: {e.response.status_code} - {e.response.text}")
        raise
    except Exception as e:
        print(f"❌ Error: {e}")
        raise

# Test
if __name__ == "__main__":
    emails = fetch_guardian_emails(max_results=5)
    for email in emails:
        print(f"  - {email['subject']} ({email['date']})")
```

**Durée du test :** 1 minute

---

## 📊 Utilisation Avancée (Codex Auto-Fix)

Une fois les tests OK, Codex Cloud peut implémenter un workflow d'auto-fix :

### Workflow recommandé

```python
"""
Codex Guardian Auto-Fix Workflow
"""
import requests
import time
import re
from typing import List, Dict

# Config
API_URL = os.getenv("EMERGENCE_API_URL")
CODEX_API_KEY = os.getenv("EMERGENCE_CODEX_API_KEY")
POLLING_INTERVAL = 1800  # 30 minutes

def extract_errors(email_body: str) -> List[Dict]:
    """Parse email body to extract errors"""
    errors = []

    # Extract CRITICAL errors
    if "CRITICAL" in email_body or "🚨" in email_body:
        errors.append({
            "severity": "CRITICAL",
            "type": "production",
            "raw": email_body
        })

    # Extract ERROR logs
    if "ERROR" in email_body or "❌" in email_body:
        errors.append({
            "severity": "ERROR",
            "type": "backend",
            "raw": email_body
        })

    return errors

def guardian_polling_loop():
    """Main polling loop - run continuously"""
    print("[Codex Guardian] Starting polling loop...")

    while True:
        try:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Fetching Guardian emails...")

            # 1. Fetch emails
            response = requests.get(
                API_URL,
                headers={"X-Codex-API-Key": CODEX_API_KEY},
                params={"max_results": 5},
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            emails = data.get('emails', [])

            print(f"  → Found {len(emails)} emails")

            # 2. Parse emails for errors
            all_errors = []
            for email in emails:
                body = email.get('body_text', '')
                errors = extract_errors(body)
                if errors:
                    print(f"  → Email '{email['subject']}' has {len(errors)} errors")
                    all_errors.extend(errors)

            # 3. If errors found, trigger auto-fix
            if all_errors:
                print(f"  → Total errors to fix: {len(all_errors)}")
                # TODO: Implement auto-fix logic here
                # - Create Git branch
                # - Apply fixes
                # - Run tests
                # - Create PR
            else:
                print("  → No errors found, all good ✅")

        except Exception as e:
            print(f"[ERROR] Polling loop error: {e}")

        # Sleep until next poll
        print(f"  → Sleeping for {POLLING_INTERVAL}s...")
        time.sleep(POLLING_INTERVAL)

# Main entry point
if __name__ == "__main__":
    guardian_polling_loop()
```

**Déploiement recommandé :**
- **Option 1:** Cloud Function (GCP/AWS) avec trigger Cloud Scheduler (toutes les 30 min)
- **Option 2:** Service/Daemon continu qui tourne en background
- **Option 3:** Cron job (si Codex tourne sur serveur local)

---

## 🔐 Sécurité & Bonnes Pratiques

### Secrets à protéger

**API Key Codex :**
```bash
CODEX_API_KEY=77bc68b9d3c0a2ebed19c0cdf73281b44d9b6736c21eae367766f4184d9951cb
```

**⚠️ JAMAIS en dur dans le code !**
- ✅ Utiliser variables d'environnement
- ✅ Utiliser secrets management (GCP Secret Manager, AWS Secrets Manager)
- ✅ .env dans .gitignore
- ❌ Jamais dans le code source
- ❌ Jamais dans les logs

### Permissions

**OAuth Gmail :**
- ✅ Scope: `gmail.readonly` uniquement (lecture seule)
- ✅ Pas de delete, modify, send
- ✅ Tokens stockés encrypted dans Firestore

**API Codex :**
- ✅ Auth header uniquement (`X-Codex-API-Key`)
- ✅ HTTPS only (Cloud Run)
- ✅ Rate limiting configuré (100 req/min)

### Quotas Gmail API

**Limites Google :**
- Quota: 1 billion requests/day
- Codex polling 30 min: ~48 requests/day
- **Largement en dessous des limites** ✅

---

## 🐛 Troubleshooting

### Erreur 401 Unauthorized

**Cause :** API key invalide ou manquante

**Solution :**
```bash
# Vérifier que le header est bien présent et correct
curl -X POST "$API_URL" -H "X-Codex-API-Key: <VOTRE_CLE>"
```

### Erreur 403 Forbidden

**Cause :** OAuth tokens expirés ou non configurés

**Solution :**
1. Refaire OAuth flow : https://emergence-app-486095406755.europe-west1.run.app/auth/gmail
2. Vérifier Firestore : collection `gmail_oauth_tokens` existe et contient un document

### Pas d'emails retournés

**Cause :** Aucun email Guardian dans la boîte mail ou query trop restrictive

**Solution :**
1. Vérifier que Guardian envoie bien des emails (Task Scheduler actif ?)
2. Augmenter `max_results` : `?max_results=20`
3. Tester manuellement un envoi email Guardian

### Timeout 504

**Cause :** Gmail API lent ou quota dépassé

**Solution :**
1. Augmenter timeout Codex : `timeout=60`
2. Vérifier quotas GCP : https://console.cloud.google.com/apis/api/gmail.googleapis.com/quotas

---

## ✅ Checklist Complète

**Avant de dire "Codex Cloud est branché" :**

- [ ] **OAuth Gmail flow complété** (Étape 1 - TOI)
  - URL: https://emergence-app-486095406755.europe-west1.run.app/auth/gmail
  - Tokens stockés dans Firestore

- [ ] **Credentials fournis à Codex Cloud** (Étape 2 - TOI)
  - `EMERGENCE_API_URL` configuré
  - `EMERGENCE_CODEX_API_KEY` configuré
  - Secrets sécurisés (pas en dur dans code)

- [ ] **Test d'accès réussi** (Étape 3 - CODEX)
  - Curl test : 200 OK
  - Python test : emails fetched
  - Parsing email body : errors extracted

- [ ] **Workflow polling implémenté** (optionnel - CODEX)
  - Polling loop 30 min
  - Error extraction
  - Auto-fix logic

- [ ] **Monitoring configuré** (optionnel)
  - Logs Codex pour tracking
  - Alertes si API down

---

## 📚 Documentation Complète

**Docs détaillées :**
- [CODEX_GMAIL_QUICKSTART.md](docs/CODEX_GMAIL_QUICKSTART.md) - Guide rapide (460 lignes)
- [GMAIL_CODEX_INTEGRATION.md](docs/GMAIL_CODEX_INTEGRATION.md) - Guide complet (453 lignes)
- [TEST_EMAIL_REPORTS.md](claude-plugins/integrity-docs-guardian/TEST_EMAIL_REPORTS.md) - Tests email Guardian

**Backend Gmail Service :**
- [src/backend/features/gmail/gmail_service.py](src/backend/features/gmail/gmail_service.py) - Service Gmail OAuth2

---

## 🎉 Résumé Final

**Configuration côté backend :**
- ✅ Gmail API OAuth2 : Configuré
- ✅ Endpoint Codex API : Déployé en production
- ✅ Secrets GCP : Configurés
- ✅ Cloud Run : Opérationnel

**Ce que tu dois faire :**
1. **Autoriser Gmail OAuth** (2 min, one-time) → Ouvrir https://emergence-app-486095406755.europe-west1.run.app/auth/gmail
2. **Donner credentials à Codex Cloud** (1 min) → `EMERGENCE_API_URL` + `EMERGENCE_CODEX_API_KEY`
3. **Tester depuis Codex** (1 min) → curl ou Python test

**Total : 4 minutes pour brancher Codex Cloud aux emails Guardian ! 🚀**

---

**Contact :** Voir `docs/passation.md` pour historique complet.
