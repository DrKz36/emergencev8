# 📊 USAGE TRACKING SYSTEM - Phase 2 Guardian Cloud

**Version:** 1.0.0
**Date:** 2025-10-19
**Status:** ✅ IMPLÉMENTÉ

---

## 🎯 OBJECTIF

Système de tracking automatique de l'activité utilisateurs dans ÉMERGENCE V8 pour :
- Monitorer l'usage des features
- Détecter les erreurs rencontrées par les utilisateurs
- Générer des rapports d'activité pour dashboard admin
- **Privacy-compliant** : Aucun contenu sensible capturé

---

## 🏗️ ARCHITECTURE

### Composants créés

```
src/backend/
├── features/usage/
│   ├── __init__.py
│   ├── models.py           # Pydantic models (UserSession, FeatureUsage, UserError)
│   ├── repository.py       # UsageRepository (SQLite CRUD)
│   ├── guardian.py         # UsageGuardian (agrège stats)
│   └── router.py           # API endpoints (/api/usage/*)
├── middleware/
│   ├── __init__.py
│   └── usage_tracking.py   # UsageTrackingMiddleware (capture automatique)
```

### Tables SQLite

**`user_sessions`**
```sql
CREATE TABLE user_sessions (
    id TEXT PRIMARY KEY,
    user_email TEXT NOT NULL,
    session_start TEXT NOT NULL,
    session_end TEXT,
    duration_seconds INTEGER,
    ip_address TEXT,
    user_agent TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
)
```

**`feature_usage`**
```sql
CREATE TABLE feature_usage (
    id TEXT PRIMARY KEY,
    user_email TEXT NOT NULL,
    feature_name TEXT NOT NULL,        -- Ex: "chat_message", "document_upload"
    endpoint TEXT NOT NULL,            -- Ex: "/api/chat/message"
    method TEXT NOT NULL DEFAULT 'GET',
    timestamp TEXT NOT NULL,
    success BOOLEAN NOT NULL DEFAULT 1,
    error_message TEXT,
    duration_ms INTEGER,
    status_code INTEGER NOT NULL DEFAULT 200,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
)
```

**`user_errors`**
```sql
CREATE TABLE user_errors (
    id TEXT PRIMARY KEY,
    user_email TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    method TEXT NOT NULL,
    error_type TEXT NOT NULL,
    error_code INTEGER NOT NULL,
    error_message TEXT NOT NULL,
    stack_trace TEXT,
    timestamp TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
)
```

---

## 🔐 PRIVACY COMPLIANCE

### ✅ Ce qui EST capturé

- Endpoint appelé (ex: `/api/chat/message`)
- Méthode HTTP (GET, POST, etc.)
- User email (depuis JWT)
- Timestamp
- Succès/Échec (status code)
- Durée de la requête (ms)
- Message d'erreur (si erreur)

### ❌ Ce qui N'EST PAS capturé

- **Contenu des messages chat** (`/api/chat/message` body)
- **Contenu des fichiers uploadés**
- **Mots de passe**
- **Tokens JWT complets**
- **Données sensibles dans query params**

Le middleware utilise `fire-and-forget` pour logger sans bloquer les requêtes.

---

## 🚀 UTILISATION

### Middleware (Automatique)

Le middleware `UsageTrackingMiddleware` est activé automatiquement dans `main.py` :

```python
from backend.middleware.usage_tracking import UsageTrackingMiddleware

app.add_middleware(UsageTrackingMiddleware)
```

**Il capture automatiquement TOUTES les requêtes API** (sauf health/metrics).

### Endpoint Admin: `/api/usage/summary`

**GET** `/api/usage/summary?hours=2`

**Accès:** Admin only (`require_admin_claims`)

**Paramètres:**
- `hours` (int, default=2) : Nombre d'heures à analyser (1-720)

**Réponse:**
```json
{
  "period_start": "2025-10-19T14:00:00+00:00",
  "period_end": "2025-10-19T16:00:00+00:00",
  "active_users": 5,
  "total_requests": 1234,
  "total_errors": 12,
  "users": [
    {
      "email": "user@example.com",
      "total_time_minutes": 45,
      "features_used": ["chat_message", "documents_upload", "thread_create"],
      "requests_count": 234,
      "errors_count": 2,
      "errors": [
        {
          "endpoint": "/api/documents/upload",
          "error": "File too large",
          "timestamp": "2025-10-19T15:30:12+00:00",
          "code": 413
        }
      ]
    }
  ],
  "top_features": [
    {"name": "chat_message", "count": 567},
    {"name": "thread_create", "count": 123}
  ],
  "error_breakdown": {
    "400": 5,
    "500": 2,
    "503": 1
  }
}
```

### Endpoint: `/api/usage/generate-report`

**POST** `/api/usage/generate-report?hours=2`

**Accès:** Admin only

Génère rapport ET le sauvegarde dans `reports/usage_report.json`

**Réponse:**
```json
{
  "status": "success",
  "report_path": "reports/usage_report.json",
  "summary": {
    "active_users": 5,
    "total_requests": 1234,
    "total_errors": 12,
    "period": "2025-10-19T14:00:00+00:00 -> 2025-10-19T16:00:00+00:00"
  }
}
```

### Endpoint: `/api/usage/health`

**GET** `/api/usage/health`

**Accès:** Public

Health check du système usage tracking.

**Réponse:**
```json
{
  "status": "healthy",
  "service": "usage-tracking",
  "repository": "available"
}
```

---

## 🤖 USAGEGUARDIAN AGENT

### Méthodes principales

```python
from backend.features.usage.guardian import UsageGuardian
from backend.features.usage.repository import UsageRepository

# Initialiser
repository = UsageRepository(db_manager)
guardian = UsageGuardian(repository)

# Générer rapport (2h par défaut)
report = await guardian.generate_report(hours=2)

# Générer + sauvegarder fichier
report, path = await guardian.generate_and_save_report(hours=6)
# → Crée reports/usage_report.json
```

### Format rapport

```python
{
    "period_start": datetime,
    "period_end": datetime,
    "active_users": int,
    "total_requests": int,
    "total_errors": int,
    "users": [
        {
            "email": str,
            "total_time_minutes": int,
            "features_used": [str],
            "requests_count": int,
            "errors_count": int,
            "errors": [dict]
        }
    ],
    "top_features": [{"name": str, "count": int}],
    "error_breakdown": {"400": 5, "500": 2}
}
```

---

## 🔗 INTÉGRATION PHASE 5 (EMAIL GUARDIAN)

Le rapport usage sera intégré dans l'email Guardian (Phase 5).

Le template `guardian_report_email.html` a déjà une section `{% if usage_stats %}` prête :

```python
# Phase 5 appellera:
usage_report = load_report('usage_report.json')

await email_service.send_guardian_report(
    to_email="admin@example.com",
    reports={
        'prod_report.json': prod_data,
        'usage_stats': usage_report,  # ← Usage tracking ici
    }
)
```

---

## ⚡ PERFORMANCE

### Overhead middleware

- **Target:** < 10ms par requête
- **Implémentation:** Fire-and-forget (asyncio.create_task)
- **Pas de await bloquant** dans le middleware

### Optimisations

- Index SQLite sur `timestamp` et `user_email`
- Logging asynchrone
- Skip des endpoints health/metrics
- Batch writes possibles (future)

---

## 🧪 TESTS

### Test manuel du middleware

1. Lancer backend local :
   ```bash
   pwsh -File scripts/run-backend.ps1
   ```

2. Faire quelques requêtes API :
   ```bash
   curl http://localhost:8000/api/health
   curl -H "Authorization: Bearer <token>" http://localhost:8000/api/threads
   ```

3. Vérifier tables SQLite :
   ```bash
   sqlite3 emergence_local.db "SELECT * FROM feature_usage ORDER BY timestamp DESC LIMIT 10"
   ```

### Test endpoint admin

```bash
# Login admin
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "xxx"}'

# Récupérer token JWT
export TOKEN="<jwt-token>"

# Appeler endpoint usage
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/usage/summary?hours=24"
```

### Test privacy compliance

**Vérifier que le body n'est PAS capturé :**

```bash
# Envoyer message chat
curl -X POST http://localhost:8000/api/chat/message \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "SECRET MESSAGE", "session_id": "xxx"}'

# Vérifier DB
sqlite3 emergence_local.db "SELECT * FROM feature_usage WHERE endpoint = '/api/chat/message'"

# ✅ DOIT afficher:
# - endpoint: /api/chat/message
# - user_email: xxx
# - success: 1
# ❌ NE DOIT PAS afficher:
# - "SECRET MESSAGE" nulle part
```

---

## 📊 DASHBOARD ADMIN (Future)

Le frontend intégrera un dashboard admin pour visualiser les rapports usage :

- Graphique utilisateurs actifs (timeline)
- Top features utilisées (bar chart)
- Breakdown erreurs (pie chart)
- Liste utilisateurs avec détails

**TODO Phase 3:** Créer `src/frontend/features/admin/usage-dashboard.js`

---

## 🚨 ALERTES (Future Phase 5)

Le système pourra déclencher alertes si :
- Taux d'erreurs > 10% sur dernière heure
- Feature critique (chat) down
- Utilisateur rencontre 5+ erreurs en 10 min

**Intégration:** Email Guardian + notifications Slack (Phase 5)

---

## 🔧 MAINTENANCE

### Nettoyer vieilles données

```python
# TODO: Ajouter endpoint /api/usage/cleanup
# Supprime feature_usage > 90 jours
# Supprime user_errors > 30 jours
# Garde user_sessions indéfiniment (ou 1 an)
```

### Migration Firestore (Phase 3+)

Actuellement SQLite, migration Firestore prévue pour :
- Scalabilité cloud
- Requêtes distribuées
- Backup automatique

**TODO:** `UsageRepository` sera adapté pour Firestore (interface identique).

---

## 📝 CHANGELOG

### v1.0.0 (2025-10-19) - Phase 2 Guardian Cloud

**Implémenté:**
- ✅ UsageTrackingMiddleware (capture automatique)
- ✅ UsageRepository (SQLite CRUD)
- ✅ UsageGuardian (génération rapports)
- ✅ Endpoint `/api/usage/summary` (admin only)
- ✅ Endpoint `/api/usage/generate-report` (admin only)
- ✅ Privacy compliance (pas de body capturé)
- ✅ Tables SQLite (user_sessions, feature_usage, user_errors)
- ✅ Documentation complète

**TODO Phase 3+:**
- [ ] Migration Firestore
- [ ] Dashboard admin frontend
- [ ] Alertes temps réel
- [ ] Cleanup automatique vieilles données
- [ ] Tests E2E

---

## 🤝 CONTRIBUTION AGENT

**Créé par:** Claude Code (Phase 2 Guardian Cloud)
**Date:** 2025-10-19
**Durée:** 1 session (2h)

**Fichiers créés:**
- `src/backend/features/usage/models.py` (96 lignes)
- `src/backend/features/usage/repository.py` (326 lignes)
- `src/backend/features/usage/guardian.py` (222 lignes)
- `src/backend/features/usage/router.py` (144 lignes)
- `src/backend/middleware/usage_tracking.py` (280 lignes)
- `docs/USAGE_TRACKING.md` (ce fichier)

**Total:** ~1068 lignes de code + documentation

---

**✅ Phase 2 terminée - Prêt pour Phase 3 (Gmail API Integration) 🚀**
