# 🛡️ GUARDIAN CLOUD - PLAN D'IMPLÉMENTATION COMPLET

**Date:** 2025-10-19
**Version:** 2.0.0 (Extended avec tracking users + Gmail integration)
**Durée estimée:** 12-15 jours

---

## 📋 RÉCAPITULATIF DES DEMANDES

### 1. **Unifier système email** (double système actuel)
- Actuellement: 2 types de mails différents envoyés
- **Solution:** Créer un seul système de reporting email unifié

### 2. **Rapports email détaillés (toutes les 2h)**
- Email riche avec erreurs détaillées
- Format clair pour devs (toi + Claude + Codex)
- Permettre corrections rapides

### 3. **Tracking utilisateurs** (nouveau Guardian)
- Email utilisé
- Temps passé sur l'app
- Fonctionnalités testées
- Erreurs rencontrées
- **PAS** le contenu des messages (privacy)

### 4. **Intégration Gmail API pour Codex**
- Codex lit les rapports Guardian par email
- Peut faire corrections Git depuis cloud
- Accès indirect (pas Gmail perso direct)
- OAuth2 sécurisé

### 5. **Trigger audit Guardian depuis Admin UI**
- Bouton "Lancer Audit Guardian" dans module admin
- Déclenche audit cloud à la demande
- Affiche résultats en temps réel

---

## 🏗️ ARCHITECTURE GLOBALE

```
┌─────────────────────────────────────────────────────────────────────┐
│                      EMERGENCE BACKEND (Cloud Run)                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ GUARDIAN CLOUD SERVICE                                          │ │
│  ├────────────────────────────────────────────────────────────────┤ │
│  │ Agents:                                                         │ │
│  │  • ProdGuardian (logs Cloud Run)                                │ │
│  │  • Nexus (agrégation rapports)                                  │ │
│  │  • Argus Cloud (Cloud Logging analysis)                         │ │
│  │  • UsageGuardian (NEW - tracking users)                         │ │
│  │                                                                  │ │
│  │ Endpoints:                                                       │ │
│  │  • POST /api/guardian/run-audit (trigger manuel depuis Admin)   │ │
│  │  • GET  /api/guardian/reports (liste rapports)                  │ │
│  │  • GET  /api/guardian/reports/{id} (détail rapport)             │ │
│  │  • GET  /api/guardian/status (état global)                      │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ GMAIL INTEGRATION SERVICE (NEW)                                 │ │
│  ├────────────────────────────────────────────────────────────────┤ │
│  │ • OAuth2 Flow (user consent)                                    │ │
│  │ • Token storage (Firestore encrypted)                           │ │
│  │ • Read emails (subject: emergence|guardian|audit)               │ │
│  │ • Expose API pour Codex                                         │ │
│  │                                                                  │ │
│  │ Endpoints:                                                       │ │
│  │  • GET  /auth/gmail (initiate OAuth)                            │ │
│  │  • GET  /auth/callback/gmail (OAuth callback)                   │ │
│  │  • POST /api/gmail/read-reports (Codex reads reports)           │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ USAGE TRACKING SERVICE (NEW)                                    │ │
│  ├────────────────────────────────────────────────────────────────┤ │
│  │ • Track user sessions (login/logout)                            │ │
│  │ • Track feature usage (endpoints called)                        │ │
│  │ • Track errors per user                                         │ │
│  │ • Middleware pour capture automatique                           │ │
│  │                                                                  │ │
│  │ Endpoints:                                                       │ │
│  │  • GET /api/usage/summary (dashboard admin)                     │ │
│  │  • GET /api/usage/users (liste users + metrics)                 │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ EMAIL UNIFIED SERVICE (REFACTOR)                                │ │
│  ├────────────────────────────────────────────────────────────────┤ │
│  │ • Consolidation email_service.py existant                       │ │
│  │ • Template Guardian Report (HTML riche)                         │ │
│  │ • Envoi auto toutes les 2h (Cloud Scheduler)                    │ │
│  │ • Inclut: prod errors + usage stats + recommendations           │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
                    ┌────────────────────────┐
                    │ CLOUD SCHEDULER (2h)   │
                    │ Trigger Guardian Audit │
                    └────────────────────────┘
                                 │
                                 ▼
                    ┌────────────────────────┐
                    │ EMAIL (Gmail SMTP)     │
                    │ → gonzalefernando@...  │
                    └────────────────────────┘
                                 │
                                 ▼
                    ┌────────────────────────┐
                    │ CODEX (via Gmail API)  │
                    │ Lit rapports → Git fix │
                    └────────────────────────┘
```

---

## 📅 PLAN PAR PHASES (15 JOURS)

### **PHASE 1 : Audit & Unification Email** (2 jours)

**Objectifs:**
- Identifier les 2 systèmes d'email actuels (doublons)
- Unifier en un seul service
- Créer template email Guardian complet

**Tâches:**
1. Auditer code email actuel
   - [ ] Grep tous les `send_email` / `EmailService`
   - [ ] Identifier les 2 chemins d'envoi différents
   - [ ] Lister différences (templates, triggers, config)

2. Unifier EmailService
   - [ ] Consolider dans `email_service.py`
   - [ ] Supprimer doublons
   - [ ] Créer méthode `send_guardian_report()`

3. Créer template HTML Guardian
   - [ ] Section: Executive Summary (status global)
   - [ ] Section: Production Errors (détails stack traces)
   - [ ] Section: Usage Stats (users actifs, features utilisées)
   - [ ] Section: Recommendations (actions prioritaires)
   - [ ] Section: Links (rapports Cloud Storage, Admin UI)

**Livrables:**
- `src/backend/features/auth/email_service.py` (unifié)
- `src/backend/templates/guardian_report_email.html`
- Doc: `docs/EMAIL_UNIFICATION.md`

---

### **PHASE 2 : Usage Tracking System** (3 jours)

**Objectifs:**
- Tracker activité utilisateurs (sessions, features, erreurs)
- **Privacy-compliant** (pas de lecture messages)
- Dashboard admin pour consultation

**Tâches:**

#### 2.1 - Base de données (1j)
- [ ] Créer table `user_sessions` (Firestore/PostgreSQL)
  ```sql
  - user_email
  - session_start
  - session_end
  - duration_seconds
  - ip_address (optionnel)
  ```

- [ ] Créer table `feature_usage` (Firestore/PostgreSQL)
  ```sql
  - user_email
  - feature_name (ex: "chat_message", "document_upload")
  - timestamp
  - success (bool)
  - error_message (if failed)
  ```

- [ ] Créer table `user_errors` (Firestore/PostgreSQL)
  ```sql
  - user_email
  - endpoint
  - error_type (500, 400, etc.)
  - error_message
  - stack_trace
  - timestamp
  ```

#### 2.2 - Middleware tracking (1j)
- [ ] Créer `usage_tracking_middleware.py`
  - Capture toutes les requêtes API
  - Extract user email depuis JWT token
  - Log feature usage (endpoint appelé)
  - Log erreurs (si status >= 400)
  - **Exclure:** `/api/chat/message` content (privacy)

- [ ] Intégrer middleware dans `main.py`
  ```python
  app.add_middleware(UsageTrackingMiddleware)
  ```

#### 2.3 - UsageGuardian Agent (1j)
- [ ] Créer `usage_guardian.py`
  - Agrège stats dernières 2h
  - Génère rapport `usage_report.json`:
    ```json
    {
      "period": "2025-10-19 14:00 - 16:00",
      "active_users": 5,
      "users": [
        {
          "email": "user@example.com",
          "total_time_minutes": 45,
          "features_used": ["chat", "documents", "voice"],
          "errors_count": 2,
          "errors": [
            {
              "endpoint": "/api/documents/upload",
              "error": "File too large",
              "timestamp": "..."
            }
          ]
        }
      ]
    }
    ```

- [ ] Endpoint `/api/usage/summary`
  - Retourne rapport usage pour Admin UI

**Livrables:**
- `src/backend/middleware/usage_tracking.py`
- `src/backend/features/usage/guardian.py`
- `src/backend/features/usage/router.py`
- Rapports: `usage_report.json`

---

### **PHASE 3 : Gmail API Integration pour Codex** (4 jours)

**Objectifs:**
- Codex peut lire rapports Guardian par email
- OAuth2 sécurisé (consent utilisateur)
- Pas d'accès direct Gmail perso

**Tâches:**

#### 3.1 - Setup GCP OAuth2 (1j)
- [ ] Console GCP → `emergence-440016`
- [ ] APIs & Services → Enable Gmail API
- [ ] Create OAuth2 Credentials (Web Application)
  - Redirect URIs: `https://emergence-app-HASH.a.run.app/auth/callback/gmail`
  - Scopes: `gmail.readonly` (lecture seule)
- [ ] Download `client_secret.json`
- [ ] Store dans Secret Manager

#### 3.2 - OAuth Flow Backend (1j)
- [ ] Créer `src/backend/features/gmail/oauth_service.py`
  - Méthode `initiate_oauth()` → redirect Google consent
  - Méthode `handle_callback(code)` → échange code → tokens
  - Méthode `store_tokens(user_email, tokens)` → Firestore encrypted

- [ ] Créer endpoints OAuth
  ```python
  @router.get("/auth/gmail")
  async def gmail_auth_init():
      # Redirect vers Google OAuth consent screen

  @router.get("/auth/callback/gmail")
  async def gmail_auth_callback(code: str):
      # Échange code → tokens
      # Store tokens Firestore
      # Redirect admin UI success page
  ```

#### 3.3 - Gmail Read Service (1j)
- [ ] Créer `src/backend/features/gmail/gmail_service.py`
  - Méthode `read_guardian_reports(max_results=10)`
    - Query: `subject:(emergence OR guardian OR audit)`
    - Retourne: liste emails avec subject, body, timestamp
  - Méthode `refresh_tokens_if_needed()`
    - Auto-refresh tokens expirés

- [ ] Endpoint pour Codex
  ```python
  @router.post("/api/gmail/read-reports")
  async def read_gmail_reports(api_key: str = Header(...)):
      # Vérifier API key Codex
      # Appeler gmail_service.read_guardian_reports()
      # Retourner JSON parseable par Codex
  ```

#### 3.4 - Codex Integration (1j)
- [ ] Créer API key Codex (Secret Manager)
- [ ] Documenter API pour Codex:
  ```bash
  curl -X POST https://emergence-app.../api/gmail/read-reports \
    -H "X-Codex-API-Key: SECRET_KEY" \
    -H "Content-Type: application/json"
  ```

- [ ] Codex workflow:
  1. Appelle `/api/gmail/read-reports` toutes les 2h
  2. Parse rapports Guardian
  3. Si erreurs détectées → crée branche Git
  4. Fait corrections auto
  5. Crée PR GitHub
  6. Notifie via Slack/Email

**Livrables:**
- `src/backend/features/gmail/oauth_service.py`
- `src/backend/features/gmail/gmail_service.py`
- `src/backend/features/gmail/router.py`
- Doc: `docs/GMAIL_CODEX_INTEGRATION.md`

---

### **PHASE 4 : Admin UI - Trigger Audit Guardian** (2 jours)

**Objectifs:**
- Bouton "Lancer Audit Guardian" dans Admin UI
- Déclenche audit cloud manuel
- Affiche résultats en temps réel (websocket ou polling)

**Tâches:**

#### 4.1 - Backend Endpoint (1j)
- [ ] Endpoint `/api/guardian/run-audit` (déjà existe dans router.py)
  - Améliorer pour exec cloud agents:
    - ProdGuardian
    - Nexus
    - Argus Cloud
    - UsageGuardian (nouveau)
  - Upload rapports → Cloud Storage
  - Retourne status + rapport summary

- [ ] Endpoint `/api/guardian/audit-status/{audit_id}`
  - Poll status audit en cours
  - Retourne progress % + logs

#### 4.2 - Frontend Admin UI (1j)
- [ ] Créer `admin-guardian.js` module
  - Bouton "🛡️ Lancer Audit Guardian"
  - Modal progress avec logs temps réel
  - Affichage rapport summary:
    - Prod status (OK / WARNING / CRITICAL)
    - Usage stats (users actifs, features populaires)
    - Errors count + détails
    - Recommendations prioritaires

- [ ] Intégrer dans `admin-dashboard.js`
  - Section "Guardian Cloud Monitoring"
  - Historical audits (derniers 10)
  - Graphe status over time

**Livrables:**
- `src/backend/features/guardian/router.py` (updated)
- `src/frontend/features/admin/admin-guardian.js`
- UI mockup: `docs/ADMIN_GUARDIAN_UI.md`

---

### **PHASE 5 : Unified Email Reporting** (2 jours)

**Objectifs:**
- Email Guardian toutes les 2h (Cloud Scheduler)
- Template HTML riche et détaillé
- Inclut: prod errors + usage + recommendations

**Tâches:**

#### 5.1 - Template HTML Email (1j)
- [ ] Créer `guardian_report_email.html` (Jinja2 template)

**Structure template:**
```html
<!DOCTYPE html>
<html>
<head>
    <style>
        /* Modern email-safe CSS */
    </style>
</head>
<body>
    <h1>🛡️ Guardian Report - {{ period }}</h1>

    <!-- Executive Summary -->
    <section class="summary">
        <h2>📊 Executive Summary</h2>
        <div class="status status-{{ global_status }}">
            Status: {{ global_status }}
        </div>
        <ul>
            <li>Critical issues: {{ critical_count }}</li>
            <li>Warnings: {{ warning_count }}</li>
            <li>Active users: {{ active_users }}</li>
        </ul>
    </section>

    <!-- Production Errors -->
    <section class="errors">
        <h2>🚨 Production Errors (Last 2h)</h2>
        {% if prod_errors %}
            {% for error in prod_errors %}
            <div class="error-card">
                <h3>{{ error.type }}</h3>
                <p><strong>Count:</strong> {{ error.count }}</p>
                <p><strong>Endpoint:</strong> {{ error.endpoint }}</p>
                <pre>{{ error.stack_trace }}</pre>
                <p><strong>First seen:</strong> {{ error.first_seen }}</p>
            </div>
            {% endfor %}
        {% else %}
            <p style="color: green;">✅ No errors detected</p>
        {% endif %}
    </section>

    <!-- Usage Stats -->
    <section class="usage">
        <h2>👥 Usage Statistics</h2>
        <table>
            <thead>
                <tr>
                    <th>User</th>
                    <th>Time</th>
                    <th>Features Used</th>
                    <th>Errors</th>
                </tr>
            </thead>
            <tbody>
                {% for user in users %}
                <tr>
                    <td>{{ user.email }}</td>
                    <td>{{ user.total_time_minutes }} min</td>
                    <td>{{ user.features_used | join(', ') }}</td>
                    <td>{{ user.errors_count }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </section>

    <!-- Recommendations -->
    <section class="recommendations">
        <h2>⚡ Recommended Actions</h2>
        <ul>
            {% for rec in recommendations %}
            <li class="priority-{{ rec.priority }}">
                [{{ rec.priority }}] {{ rec.action }}
            </li>
            {% endfor %}
        </ul>
    </section>

    <!-- Links -->
    <section class="links">
        <h2>🔗 Quick Links</h2>
        <ul>
            <li><a href="{{ admin_ui_url }}">Admin Dashboard</a></li>
            <li><a href="{{ cloud_storage_url }}">Full Reports (Cloud Storage)</a></li>
            <li><a href="{{ cloud_logging_url }}">Cloud Logging</a></li>
        </ul>
    </section>

    <footer>
        <p style="color: gray;">
            Generated by Guardian Cloud Service<br>
            {{ timestamp }}
        </p>
    </footer>
</body>
</html>
```

#### 5.2 - Email Send Logic (1j)
- [ ] Créer `send_guardian_email_report()`
  - Load tous les rapports (prod, usage, nexus)
  - Render template HTML
  - Send via EmailService
  - Log envoi (Firestore)

- [ ] Cloud Scheduler config
  ```yaml
  Schedule: "0 */2 * * *"  # Toutes les 2h
  Target: /api/guardian/scheduled-report
  Method: POST
  Headers:
    X-Guardian-Scheduler-Token: SECRET_TOKEN
  ```

- [ ] Endpoint `/api/guardian/scheduled-report`
  - Vérifie token scheduler
  - Lance audit complet
  - Génère + envoie email
  - Retourne 200 OK

**Livrables:**
- `src/backend/templates/guardian_report_email.html`
- `src/backend/features/guardian/email_report.py`
- Cloud Scheduler config: `infrastructure/guardian-scheduler.yaml`

---

### **PHASE 6 : Cloud Run Deployment & Tests** (2 jours)

**Objectifs:**
- Déployer Guardian Cloud service
- Tester tous les workflows
- Valider email reports

**Tâches:**

#### 6.1 - Cloud Run Deploy (1j)
- [ ] Update `Dockerfile` (inclure Gmail API deps)
- [ ] Update `requirements.txt`
  ```
  google-auth
  google-auth-oauthlib
  google-api-python-client
  ```

- [ ] Deploy Cloud Run
  ```bash
  gcloud builds submit --config cloudbuild.yaml
  gcloud run deploy emergence-app \
    --region europe-west1 \
    --allow-unauthenticated
  ```

- [ ] Configure Cloud Scheduler (2h trigger)
  ```bash
  gcloud scheduler jobs create http guardian-scheduled-report \
    --location europe-west1 \
    --schedule="0 */2 * * *" \
    --uri="https://emergence-app-HASH.a.run.app/api/guardian/scheduled-report" \
    --http-method=POST \
    --headers="X-Guardian-Scheduler-Token=SECRET"
  ```

#### 6.2 - Tests End-to-End (1j)
- [ ] Test OAuth Gmail flow
  - Navigate `/auth/gmail`
  - Consent screen Google
  - Callback success
  - Tokens stored Firestore

- [ ] Test Gmail read (Codex API)
  ```bash
  curl -X POST https://emergence-app.../api/gmail/read-reports \
    -H "X-Codex-API-Key: KEY"
  # Devrait retourner derniers emails Guardian
  ```

- [ ] Test Usage Tracking
  - Login user beta
  - Utilise features (chat, docs)
  - Check `/api/usage/summary` → stats visible

- [ ] Test Audit manuel (Admin UI)
  - Click "Lancer Audit Guardian"
  - Vérifier progress
  - Vérifier rapport affiché

- [ ] Test Email scheduled (force trigger)
  ```bash
  curl -X POST https://emergence-app.../api/guardian/scheduled-report \
    -H "X-Guardian-Scheduler-Token: SECRET"
  # Email devrait arriver sous 1 min
  ```

- [ ] Valider email reçu
  - Format HTML correct
  - Toutes sections présentes
  - Links fonctionnels
  - Stats utilisateurs OK

**Livrables:**
- Service Cloud Run déployé
- Cloud Scheduler actif (2h)
- Tests report: `docs/GUARDIAN_CLOUD_TESTS.md`
- Premier email Guardian reçu ✅

---

## 📊 RÉCAPITULATIF TIMELINE

| Phase | Tâches | Durée | Dépendances |
|-------|--------|-------|-------------|
| **Phase 1** | Audit & Unification Email | 2j | - |
| **Phase 2** | Usage Tracking System | 3j | - |
| **Phase 3** | Gmail API Integration | 4j | Phase 1 |
| **Phase 4** | Admin UI Trigger Audit | 2j | Phase 2 |
| **Phase 5** | Unified Email Reporting | 2j | Phase 1, 2 |
| **Phase 6** | Cloud Deployment & Tests | 2j | Phase 1-5 |
| **TOTAL** | - | **15 jours** | - |

---

## 🎯 SUCCESS METRICS

### Email Reports
- [ ] Un seul type d'email Guardian (doublons supprimés)
- [ ] Email toutes les 2h (Cloud Scheduler fonctionne)
- [ ] Template HTML riche (toutes sections présentes)
- [ ] Erreurs production détaillées (stack traces visibles)
- [ ] Recommendations claires et actionnables

### Usage Tracking
- [ ] Toutes sessions users trackées
- [ ] Features utilisées identifiables
- [ ] Erreurs par user isolées
- [ ] Privacy respectée (pas de contenu messages)
- [ ] Dashboard admin fonctionnel

### Gmail Integration
- [ ] OAuth flow complet fonctionnel
- [ ] Codex peut lire emails Guardian
- [ ] Tokens sécurisés (encrypted Firestore)
- [ ] Auto-refresh tokens (pas d'expiration manuelle)
- [ ] Codex peut trigger corrections Git

### Admin UI
- [ ] Bouton "Lancer Audit" visible
- [ ] Audit s'exécute (backend appelé)
- [ ] Progress visible temps réel
- [ ] Rapport affiché clairement
- [ ] Historical audits consultables

### Cloud Run
- [ ] Service déployé et stable
- [ ] Monitoring 24/7 actif
- [ ] Coût < 15€/mois
- [ ] Latence < 5s par audit
- [ ] Uptime > 99%

---

## 💰 COÛTS ESTIMÉS

### Cloud Run (Guardian Service)
```
- Exécutions: 12/jour × 30j = 360 exec/mois
- Durée moyenne: 5 min/exec
- CPU: 1 vCPU × 30h/mois
- Memory: 512 Mi

Coût: ~8-12€/mois
```

### Gmail API
```
- Queries: 12/jour × 30j = 360 queries/mois
- Quota: 1M requests/day (gratuit)

Coût: Gratuit (dans quota)
```

### Cloud Storage (rapports)
```
- Storage: ~15 GB/mois (30j retention + 60j archives)
- Requêtes: ~1000 reads/mois

Coût: ~1-2€/mois
```

### Firestore (tokens, usage tracking)
```
- Documents: ~10K/mois (usage events)
- Reads: ~5K/mois
- Writes: ~10K/mois

Coût: ~2-3€/mois (Free tier: 50K reads, 20K writes)
```

### Cloud Scheduler
```
- Jobs: 1 job × 12 exec/jour

Coût: Gratuit (Free tier: 3 jobs)
```

**TOTAL ESTIMÉ: 11-17€/mois**

---

## 🚨 POINTS D'ATTENTION

### Privacy & Sécurité
- ⚠️ **Ne JAMAIS tracker le contenu des messages chat**
- ⚠️ Tokens Gmail encrypted au repos (Firestore)
- ⚠️ API key Codex dans Secret Manager (pas hardcodé)
- ⚠️ Limiter scope Gmail à `readonly` (pas write)

### Performance
- ⚠️ Usage tracking middleware → latence minimale (<10ms)
- ⚠️ Audit cloud → timeout 5 min max (sinon split agents)
- ⚠️ Emails HTML → taille <1 MB (sinon Gmail truncate)

### Maintenance
- ⚠️ Refresh tokens Gmail expirés (auto-refresh implemented)
- ⚠️ Rotation API keys Codex (tous les 6 mois)
- ⚠️ Cleanup rapports Cloud Storage (>30j → archive)

---

## 📚 DOCUMENTATION À CRÉER

- [ ] `EMAIL_UNIFICATION.md` - Système email unifié
- [ ] `USAGE_TRACKING.md` - Tracking utilisateurs
- [ ] `GMAIL_CODEX_INTEGRATION.md` - Intégration Gmail API
- [ ] `ADMIN_GUARDIAN_UI.md` - UI Admin trigger audit
- [ ] `GUARDIAN_CLOUD_TESTS.md` - Tests E2E
- [ ] `GUARDIAN_CLOUD_RUNBOOK.md` - Troubleshooting prod

---

## ✅ CHECKLIST FINALE

### Avant Go-Live
- [ ] Tous tests E2E passent
- [ ] Premier email Guardian reçu et validé
- [ ] Codex peut lire emails via API
- [ ] Admin UI trigger audit fonctionne
- [ ] Cloud Scheduler actif (2h)
- [ ] Monitoring alertes configurées
- [ ] Documentation complète
- [ ] Backup plan si Gmail API down

### Post Go-Live (Semaine 1)
- [ ] Monitor emails reçus (qualité, fréquence)
- [ ] Monitor coûts GCP (respect budget)
- [ ] Valider Codex Git fixes (qualité corrections)
- [ ] Collecter feedback utilisateurs beta (privacy OK?)
- [ ] Ajuster fréquence email si trop spam (2h → 4h?)

---

**🤖 Ce plan est vivant - sera mis à jour pendant implémentation**

**Questions ouvertes pour validation :**
1. Email 2h OK ou trop fréquent si beaucoup de warnings ?
2. Tracking users: quelles features exactement tracker ? (liste exhaustive)
3. Codex auto-fix: validation humaine requise avant merge PR ?
4. Admin UI: dashboard Guardian permanent ou modal popup ?
