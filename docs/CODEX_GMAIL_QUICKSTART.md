# 🚀 Guide Rapide - Brancher Codex GPT aux Emails Guardian

**Date:** 2025-10-19
**Status:** Phase 3 Guardian Cloud READY ✅

---

## 📋 Résumé Ultra-Rapide

**Ce qui est déjà fait:**
- ✅ Gmail API intégrée au backend (OAuth2 + email reading)
- ✅ Endpoint Codex API créé et déployé en production
- ✅ Secrets GCP configurés (OAuth client secret + Codex API key)
- ✅ Cloud Run déployé et 100% fonctionnel

**Ce qui reste à faire (10 min max):**
1. **OAuth Gmail flow** (autorisation Google one-time, 2 min)
2. **Test API Codex** (vérifier que ça lit les emails, 1 min)
3. **Push commits vers GitHub** (optionnel, déjà committés localement)

---

## 🔥 ÉTAPE 1: OAuth Gmail (Admin - One-Time)

**Objectif:** Autoriser l'app à lire tes emails Guardian.

**Action:**

1. Ouvre ce URL dans ton browser:
   ```
   https://emergence-app-486095406755.europe-west1.run.app/auth/gmail
   ```

2. Tu seras redirigé vers Google consent screen:
   - ✅ Vérifie que c'est bien ton projet GCP "emergence-469005"
   - ✅ Scope demandé: **"Lecture seule de tes emails"** (gmail.readonly)
   - ✅ Clique sur **"Autoriser"**

3. Après autorisation:
   - Tu seras redirigé vers `/auth/callback/gmail`
   - Page de confirmation affichée
   - Tokens OAuth stockés automatiquement dans Firestore

**Durée:** 2 minutes max

**Résultat attendu:**
```
✅ OAuth tokens stockés dans Firestore (collection: gmail_oauth_tokens)
✅ Backend peut maintenant lire tes emails Guardian
```

---

## 🔥 ÉTAPE 2: Test API Codex

**Objectif:** Vérifier que Codex peut lire les emails.

**Action:**

Exécute cette commande curl (ou équivalent dans Codex):

```bash
curl -X POST \
  "https://emergence-app-486095406755.europe-west1.run.app/api/gmail/read-reports?max_results=5" \
  -H "X-Codex-API-Key: 77bc68b9d3c0a2ebed19c0cdf73281b44d9b6736c21eae367766f4184d9951cb"
```

**Résultat attendu:**

```json
[
  {
    "subject": "🛡️ Guardian Report - Émergence V8",
    "from": "emergence@example.com",
    "date": "2025-10-19T16:00:00Z",
    "body": "<html>...rapport Guardian complet...</html>",
    "timestamp": "2025-10-19T16:00:00Z"
  },
  ...
]
```

**Si ça marche:**
- ✅ Codex peut lire les emails Guardian
- ✅ Prêt à implémenter le workflow auto-fix

**Si erreur:**
- ❌ `401 Unauthorized` → Vérifier API key
- ❌ `403 Forbidden` → Refaire OAuth flow (Étape 1)
- ❌ `500 Internal Error` → Checker logs Cloud Run

**Durée:** 1 minute

---

## 🔥 ÉTAPE 3: Workflow Codex (Auto-Fix)

**Objectif:** Implémenter polling + auto-fix dans Codex GPT.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Codex GPT (Local ou Cloud)                                  │
│                                                              │
│  ┌──────────────────────────────────────────────┐           │
│  │ Polling Loop (toutes les 30 min)            │           │
│  └──────────────────────────────────────────────┘           │
│                        │                                     │
│                        ▼                                     │
│  ┌──────────────────────────────────────────────┐           │
│  │ Call API: POST /api/gmail/read-reports      │           │
│  │ Header: X-Codex-API-Key                     │           │
│  └──────────────────────────────────────────────┘           │
│                        │                                     │
│                        ▼                                     │
│  ┌──────────────────────────────────────────────┐           │
│  │ Parse emails body (HTML/text)                │           │
│  │ Extract errors: CRITICAL, ERROR, WARNING     │           │
│  └──────────────────────────────────────────────┘           │
│                        │                                     │
│                        ▼                                     │
│  ┌──────────────────────────────────────────────┐           │
│  │ IF errors found:                             │           │
│  │   1. Create Git branch (fix-guardian-XXX)   │           │
│  │   2. Apply automated fixes                   │           │
│  │   3. Run tests                               │           │
│  │   4. Create Pull Request                     │           │
│  └──────────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ Cloud Run Backend                                            │
│  → OAuth2 → Gmail API → Return emails JSON                  │
└─────────────────────────────────────────────────────────────┘
```

### Pseudo-Code Python (Codex)

```python
"""
Codex Guardian Auto-Fix Workflow
À intégrer dans le système de Codex GPT
"""
import requests
import time
import re
from typing import List, Dict

# Config
CODEX_API_KEY = "77bc68b9d3c0a2ebed19c0cdf73281b44d9b6736c21eae367766f4184d9951cb"
API_URL = "https://emergence-app-486095406755.europe-west1.run.app/api/gmail/read-reports"
POLLING_INTERVAL = 1800  # 30 minutes (en secondes)

def fetch_guardian_emails(max_results: int = 10) -> List[Dict]:
    """Fetch Guardian emails from Cloud Run API"""
    response = requests.get(
        API_URL,
        headers={"X-Codex-API-Key": CODEX_API_KEY},
        params={"max_results": max_results},
        timeout=30
    )
    response.raise_for_status()
    return response.json()

def extract_errors(email_body: str) -> List[Dict]:
    """Parse email body to extract errors and recommendations"""
    errors = []

    # Extract CRITICAL errors
    critical_pattern = r'CRITICAL.*?(?=\n\n|\Z)'
    criticals = re.findall(critical_pattern, email_body, re.DOTALL)
    for crit in criticals:
        errors.append({
            "severity": "CRITICAL",
            "message": crit.strip(),
            "type": "production"
        })

    # Extract ERROR logs
    error_pattern = r'ERROR.*?(?=\n\n|\Z)'
    errs = re.findall(error_pattern, email_body, re.DOTALL)
    for err in errs:
        errors.append({
            "severity": "ERROR",
            "message": err.strip(),
            "type": "backend"
        })

    # Extract recommendations (si présentes dans le rapport)
    rec_pattern = r'Recommandation:.*?(?=\n\n|\Z)'
    recs = re.findall(rec_pattern, email_body, re.DOTALL)
    for rec in recs:
        errors.append({
            "severity": "WARNING",
            "message": rec.strip(),
            "type": "recommendation"
        })

    return errors

def create_fix_branch(errors: List[Dict]) -> str:
    """Create Git branch for fixes"""
    timestamp = int(time.time())
    branch_name = f"fix/guardian-auto-{timestamp}"

    # Execute git commands
    subprocess.run(["git", "checkout", "-b", branch_name])
    return branch_name

def apply_fixes(errors: List[Dict]) -> Dict:
    """Apply automated fixes based on error types"""
    fixes_applied = []

    for error in errors:
        if error["type"] == "production":
            # Production errors: restart service, scale up, etc.
            fix = handle_production_error(error)
            fixes_applied.append(fix)

        elif error["type"] == "backend":
            # Backend errors: fix imports, update code, etc.
            fix = handle_backend_error(error)
            fixes_applied.append(fix)

        elif error["type"] == "recommendation":
            # Recommendations: apply suggested changes
            fix = apply_recommendation(error)
            fixes_applied.append(fix)

    return {
        "total_errors": len(errors),
        "fixes_applied": len(fixes_applied),
        "details": fixes_applied
    }

def create_pull_request(branch_name: str, fixes: Dict) -> str:
    """Create PR with fixes"""
    title = f"fix(guardian): Auto-fix from Guardian report"
    body = f"""
# Guardian Auto-Fix

**Errors detected:** {fixes['total_errors']}
**Fixes applied:** {fixes['fixes_applied']}

## Details

{format_fixes_details(fixes['details'])}

---
🤖 Auto-generated by Codex GPT from Guardian email report
"""

    # Use gh CLI to create PR
    result = subprocess.run(
        ["gh", "pr", "create", "--title", title, "--body", body],
        capture_output=True,
        text=True
    )

    return result.stdout.strip()

def guardian_polling_loop():
    """Main polling loop - run continuously"""
    print("[Codex Guardian] Starting polling loop...")

    while True:
        try:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Fetching Guardian emails...")

            # 1. Fetch emails
            emails = fetch_guardian_emails(max_results=5)
            print(f"  → Found {len(emails)} emails")

            # 2. Parse emails for errors
            all_errors = []
            for email in emails:
                body = email.get('body', '')
                errors = extract_errors(body)
                if errors:
                    print(f"  → Email '{email['subject']}' has {len(errors)} errors")
                    all_errors.extend(errors)

            # 3. If errors found, apply fixes
            if all_errors:
                print(f"  → Total errors to fix: {len(all_errors)}")

                # Create branch
                branch = create_fix_branch(all_errors)
                print(f"  → Created branch: {branch}")

                # Apply fixes
                fixes = apply_fixes(all_errors)
                print(f"  → Applied {fixes['fixes_applied']} fixes")

                # Run tests
                tests_ok = run_tests()
                if tests_ok:
                    # Create PR
                    pr_url = create_pull_request(branch, fixes)
                    print(f"  → PR created: {pr_url}")
                else:
                    print(f"  → Tests failed, aborting PR creation")
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

### Démarrage du workflow Codex

**Option 1: Daemon/Service (recommandé)**
```bash
# Run as systemd service or supervisor
python codex_guardian_poller.py
```

**Option 2: Cron job**
```bash
# Run every 30 minutes
*/30 * * * * /usr/bin/python /path/to/codex_guardian_poller.py
```

**Option 3: Cloud Function (si Codex cloud)**
- Trigger: Cloud Scheduler (toutes les 30 min)
- Runtime: Python 3.11
- Entry point: `guardian_polling_loop`

---

## 📊 Surveillance & Monitoring

### Check OAuth status

```bash
curl https://emergence-app-486095406755.europe-west1.run.app/api/gmail/status
```

**Résultat attendu:**
```json
{
  "authenticated": true,
  "user_email": "admin"
}
```

### Logs Cloud Run

```bash
# Logs Gmail API
gcloud logging read "resource.type=cloud_run_revision AND textPayload=~'gmail'" --limit 20

# Logs Guardian
gcloud logging read "resource.type=cloud_run_revision AND textPayload=~'guardian'" --limit 20
```

### Métriques

**Gmail API quotas:**
- Quota: 1 billion requests/day
- Codex polling 30 min: 48 requests/day (largement OK)

**Performance attendue:**
- `/api/gmail/read-reports` response time: ~500-1000ms
- Email parsing: < 100ms per email

---

## 🔐 Sécurité

**Secrets à protéger:**
```bash
# Codex API Key (dans .env Codex, JAMAIS en dur)
CODEX_API_KEY=77bc68b9d3c0a2ebed19c0cdf73281b44d9b6736c21eae367766f4184d9951cb

# OAuth tokens (stockés dans Firestore, encrypted at rest)
# Pas besoin de les manipuler côté Codex
```

**Permissions:**
- ✅ OAuth scope: `gmail.readonly` (lecture seule, pas de delete/modify)
- ✅ API key Codex: auth header uniquement
- ✅ HTTPS only (Cloud Run)

---

## 🐛 Troubleshooting

### Erreur 401 Unauthorized

**Cause:** API key invalide ou manquante

**Solution:**
```bash
# Vérifier header
-H "X-Codex-API-Key: 77bc68b9d3c0a2ebed19c0cdf73281b44d9b6736c21eae367766f4184d9951cb"
```

### Erreur 403 Forbidden

**Cause:** OAuth tokens expirés ou non configurés

**Solution:**
1. Refaire OAuth flow: https://emergence-app-486095406755.europe-west1.run.app/auth/gmail
2. Vérifier Firestore: `gmail_oauth_tokens` collection existe

### Pas d'emails retournés

**Cause:** Aucun email Guardian dans boîte mail ou query trop restrictive

**Solution:**
1. Vérifier que Guardian emails sont envoyés (Cloud Scheduler actif?)
2. Test manuel: Envoyer email test avec subject contenant "Guardian"
3. Query élargie: `max_results=20`

### Timeout 504

**Cause:** Gmail API lent ou quota dépassé

**Solution:**
1. Augmenter timeout Codex: `timeout=60`
2. Vérifier quotas GCP: https://console.cloud.google.com/apis/api/gmail.googleapis.com/quotas

---

## 📚 Documentation Complète

**Pour plus de détails:**
- [docs/GMAIL_CODEX_INTEGRATION.md](./GMAIL_CODEX_INTEGRATION.md) - Guide complet (453 lignes)
- [docs/PHASE_6_DEPLOYMENT_GUIDE.md](./PHASE_6_DEPLOYMENT_GUIDE.md) - Déploiement Cloud
- [AGENT_SYNC.md](../AGENT_SYNC.md) - État actuel du projet

---

## ✅ Checklist Finale

**Avant de dire "Codex est branché":**

- [ ] OAuth Gmail flow complété (Étape 1)
- [ ] Test API Codex réussi (Étape 2)
- [ ] Workflow polling implémenté dans Codex
- [ ] Tests E2E: Email Guardian → Codex détecte → PR créée
- [ ] Commits pushés vers GitHub
- [ ] Cloud Scheduler configuré (emails 2h automatiques)

---

**🎉 Une fois tout validé, Guardian Cloud est 100% opérationnel !**

**Contact:** Voir `docs/passation.md` pour historique complet des changements.
