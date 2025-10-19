# 🛡️ GUARDIAN CLOUD MIGRATION PLAN

**Objectif :** Dupliquer le système Guardian local sur Cloud Run pour monitoring production 24/7

**Version :** 1.0.0
**Date :** 2025-10-19
**Status :** 📋 PLANIFICATION

---

## 🎯 OBJECTIFS

### Vision

Avoir un **Guardian Cloud Run Service** qui :
- ✅ Monitore production **24/7** (toutes les 2h au lieu de 6h local)
- ✅ Track toutes les erreurs Cloud Run (emergence-beta, emergence-stable)
- ✅ Génère rapports automatiques stockés dans Cloud Storage
- ✅ Envoie emails **automatiquement** si erreurs critiques
- ✅ Expose API pour consultation rapports depuis admin UI

### Bénéfices

| Aspect | Local (actuel) | Cloud (cible) |
|--------|----------------|---------------|
| **Fréquence monitoring** | 6h (Task Scheduler) | **2h** (Cloud Scheduler) |
| **Disponibilité** | Si PC éteint = pas de monitoring | **24/7** garanti |
| **Rapports** | JSON local uniquement | Cloud Storage + Firestore + API |
| **Alerting** | Email manuel | **Email auto** + Slack (optionnel) |
| **Agents actifs** | 3/6 (Anima, Neo, Nexus, ProdGuardian) | **3/6** (Nexus, ProdGuardian, Argus Cloud Logs) |
| **Scalabilité** | 1 instance | Auto-scale selon charge |

---

## 📐 ARCHITECTURE CIBLE

### Service Cloud Run : `emergence-guardian-service`

```
emergence-guardian-service (Cloud Run)
├── Container: Python 3.11
├── CPU: 1 vCPU (min), 2 vCPU (max)
├── Memory: 512 Mi (min), 1 Gi (max)
├── Instances: 0 (min), 2 (max)
├── Timeout: 300s (5 min max par agent)
└── Environment:
    ├── GUARDIAN_MODE=cloud
    ├── GCP_PROJECT_ID=emergence-440016
    ├── SMTP_* (pour emails)
    └── SLACK_WEBHOOK_URL (optionnel)
```

### Endpoints API

| Endpoint | Méthode | Description | Auth |
|----------|---------|-------------|------|
| `/health` | GET | Liveness/readiness probe | Public |
| `/api/guardian/run-audit` | POST | Trigger audit manuel (tous agents) | API Key |
| `/api/guardian/run-agent/{agent_name}` | POST | Trigger agent spécifique | API Key |
| `/api/guardian/reports` | GET | Liste rapports disponibles | API Key |
| `/api/guardian/reports/{report_id}` | GET | Télécharger rapport JSON | API Key |
| `/api/guardian/status` | GET | Status global (dernière exec) | API Key |

### Storage

**Cloud Storage Bucket :** `emergence-guardian-reports`

```
emergence-guardian-reports/
├── prod_reports/
│   ├── 2025-10-19_14-30_prod_report.json
│   ├── 2025-10-19_16-30_prod_report.json
│   └── ...
├── unified_reports/
│   ├── 2025-10-19_14-30_unified_report.json
│   └── ...
├── argus_reports/
│   └── 2025-10-19_14-30_cloud_logs_report.json
└── archives/
    └── (rapports > 30 jours)
```

**Firestore Collection :** `guardian_status`

```javascript
{
  "id": "exec-2025-10-19-14-30",
  "timestamp": "2025-10-19T14:30:00Z",
  "agents_executed": ["prodguardian", "nexus", "argus"],
  "global_status": "WARNING",  // OK, WARNING, CRITICAL
  "critical_count": 2,
  "warning_count": 5,
  "execution_time_seconds": 45,
  "reports": {
    "prod_report": "gs://emergence-guardian-reports/prod_reports/2025-10-19_14-30_prod_report.json",
    "unified_report": "gs://emergence-guardian-reports/unified_reports/2025-10-19_14-30_unified_report.json"
  },
  "email_sent": true,
  "alert_sent": false
}
```

### Cloud Scheduler

**Tâche :** `guardian-scheduled-audit`

```yaml
Schedule: "0 */2 * * *"  # Toutes les 2h
Timezone: "Europe/Zurich"
Target:
  Type: HTTP
  URL: https://emergence-guardian-service-HASH-ew.a.run.app/api/guardian/run-audit
  Method: POST
  Headers:
    - X-API-Key: [SECRET_GUARDIAN_API_KEY]
  Body: |
    {
      "agents": ["prodguardian", "nexus", "argus"],
      "email_on_critical": true,
      "email_recipients": ["gonzalefernando@gmail.com"]
    }
Retry:
  MaxRetries: 3
  MinBackoff: 10s
  MaxBackoff: 60s
```

---

## 🤖 AGENTS CLOUD vs LOCAL

### Agents ACTIFS sur Cloud Run

| Agent | Local | Cloud | Raison |
|-------|-------|-------|--------|
| **PRODGUARDIAN** | ✅ Pre-push + 6h | ✅ Cloud Scheduler 2h | Monitoring logs Cloud Run (emergence-beta, emergence-stable) |
| **NEXUS** | ✅ Post-commit | ✅ Cloud Scheduler 2h | Agrégation rapports ProdGuardian + Argus Cloud |
| **ARGUS Cloud** | ❌ Local dev logs only | ✅ Cloud Scheduler 2h | Analyse Cloud Logging (backend errors, slow queries) |

### Agents INACTIFS sur Cloud Run

| Agent | Local | Cloud | Raison |
|-------|-------|-------|--------|
| **ANIMA** | ✅ Pre-commit | ❌ N/A | Code source local uniquement (GitHub Actions pourrait faire ça) |
| **NEO** | ✅ Pre-commit | ❌ N/A | Code source local uniquement |
| **THEIA** | ⏸️ Disabled | ⏸️ Optionnel | BigQuery cost analysis (future) |

### Nouveau Agent : ARGUS Cloud

**Responsabilités :**
- Analyse **Cloud Logging** (pas dev logs locaux)
- Track erreurs backend production (500, 400, exceptions)
- Détecte slow queries (> 1s)
- Analyse patterns erreurs (spikes, fréquence)

**Queries Cloud Logging :**
```python
# Erreurs backend (1h)
resource.type="cloud_run_revision"
resource.labels.service_name=("emergence-beta-service" OR "emergence-stable-service")
severity >= ERROR
timestamp >= "2025-10-19T13:00:00Z"

# Slow requests (> 2s)
resource.type="cloud_run_revision"
httpRequest.latency > "2s"

# Exceptions Python
jsonPayload.message =~ "Traceback|Exception"
```

---

## 📧 EMAIL NOTIFICATIONS

### Configuration SMTP

**Variables d'environnement Cloud Run :**
```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=gonzalefernando@gmail.com
SMTP_PASSWORD=[SECRET_GMAIL_APP_PASSWORD]  # Google Cloud Secret Manager
```

### Template Email

**Sujet :**
```
🛡️ [CRITICAL] Guardian Alert - Production Issues Detected
```

**Corps :**
```html
<h2>🚨 Guardian Production Alert</h2>

<p><strong>Timestamp:</strong> 2025-10-19 14:30:00 UTC</p>
<p><strong>Status:</strong> CRITICAL</p>

<h3>Summary</h3>
<ul>
  <li>Critical issues: 2</li>
  <li>Warnings: 5</li>
  <li>Services affected: emergence-beta-service</li>
</ul>

<h3>Critical Issues</h3>
<ol>
  <li><strong>[ProdGuardian]</strong> 50 errors in last hour (spike detected)</li>
  <li><strong>[Argus Cloud]</strong> Database connection timeout (5 occurrences)</li>
</ol>

<h3>Detailed Reports</h3>
<ul>
  <li><a href="https://console.cloud.google.com/storage/browser/emergence-guardian-reports/prod_reports/2025-10-19_14-30_prod_report.json">Production Report</a></li>
  <li><a href="https://console.cloud.google.com/storage/browser/emergence-guardian-reports/unified_reports/2025-10-19_14-30_unified_report.json">Unified Report</a></li>
</ul>

<p><em>Automated email sent by Guardian Cloud Service</em></p>
```

### Règles d'envoi

**Email envoyé SI :**
- `global_status == "CRITICAL"`
- **OU** `critical_count > 0`
- **OU** erreurs production > 50 en 1h

**Email PAS envoyé SI :**
- `global_status == "OK"`
- Warnings uniquement (sauf config `email_on_warnings=true`)

---

## 🔧 IMPLÉMENTATION

### Phase 1 : Setup Infrastructure (1 jour)

**Tâches :**
- [ ] Créer Cloud Storage bucket `emergence-guardian-reports`
- [ ] Créer Firestore collection `guardian_status`
- [ ] Configurer Secret Manager pour `SMTP_PASSWORD`, `GUARDIAN_API_KEY`
- [ ] Setup IAM roles (Service Account pour Guardian)

**Service Account Permissions :**
```yaml
roles/logging.viewer           # Lire Cloud Logging
roles/storage.objectAdmin      # Écrire dans bucket rapports
roles/datastore.user          # Écrire dans Firestore
roles/secretmanager.secretAccessor  # Lire secrets
```

### Phase 2 : Adapter Agents Python (2 jours)

**Modifications :**

1. **`check_prod_logs.py` (ProdGuardian)**
   - Déjà OK (utilise Cloud Logging API)
   - Ajouter upload rapport vers Cloud Storage
   - Ajouter write Firestore status

2. **Nouveau `argus_cloud.py` (Argus Cloud)**
   - Fork de `argus_analyzer.py`
   - Remplacer lecture fichiers logs par Cloud Logging API
   - Queries spécifiques production (errors, slow queries)

3. **`generate_report.py` (Nexus)**
   - Adapter pour agréger ProdGuardian + Argus Cloud
   - Upload rapport vers Cloud Storage

4. **Nouveau `cloud_orchestrator.py`**
   - Wrapper pour exécuter agents cloud
   - Gestion storage (upload rapports)
   - Gestion Firestore (status)
   - Trigger emails si CRITICAL

### Phase 3 : API Cloud Run (2 jours)

**Structure projet :**
```
src/guardian_service/
├── main.py              # FastAPI app
├── routers/
│   ├── health.py        # /health endpoints
│   ├── audit.py         # /api/guardian/run-audit
│   └── reports.py       # /api/guardian/reports
├── agents/
│   ├── __init__.py
│   ├── prodguardian.py  # Wrapped check_prod_logs.py
│   ├── argus_cloud.py   # Cloud Logging analyzer
│   ├── nexus.py         # Wrapped generate_report.py
│   └── orchestrator.py  # cloud_orchestrator.py
├── services/
│   ├── storage.py       # Cloud Storage upload/download
│   ├── firestore.py     # Firestore write/read
│   └── email.py         # Email sender (SMTP)
├── Dockerfile
├── requirements.txt
└── cloudbuild.yaml      # CI/CD
```

**Endpoints implémentés :**

```python
# main.py
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import APIKeyHeader

app = FastAPI(title="Guardian Service", version="1.0.0")

API_KEY_HEADER = APIKeyHeader(name="X-API-Key")

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/api/guardian/run-audit")
async def run_audit(
    request: AuditRequest,
    api_key: str = Depends(API_KEY_HEADER)
):
    """Trigger audit complet (tous agents)"""
    # Vérifier API key
    if api_key != os.getenv("GUARDIAN_API_KEY"):
        raise HTTPException(401, "Invalid API key")

    # Lancer orchestrator
    result = await orchestrator.run_full_audit(
        agents=request.agents,
        email_on_critical=request.email_on_critical,
        email_recipients=request.email_recipients
    )

    return result

@app.get("/api/guardian/reports")
async def list_reports(api_key: str = Depends(API_KEY_HEADER)):
    """Liste rapports disponibles (30 derniers jours)"""
    # ...

@app.get("/api/guardian/reports/{report_id}")
async def get_report(report_id: str, api_key: str = Depends(API_KEY_HEADER)):
    """Télécharge rapport JSON depuis Cloud Storage"""
    # ...
```

### Phase 4 : Cloud Scheduler + Secrets (1 jour)

**Secrets Manager :**
```bash
# Créer secrets
gcloud secrets create guardian-api-key --data-file=- <<< "RANDOM_SECURE_KEY_HERE"
gcloud secrets create smtp-password --data-file=- <<< "GMAIL_APP_PASSWORD_HERE"

# Donner accès au Service Account
gcloud secrets add-iam-policy-binding guardian-api-key \
  --member="serviceAccount:guardian-sa@emergence-440016.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

**Cloud Scheduler :**
```bash
gcloud scheduler jobs create http guardian-scheduled-audit \
  --location=europe-west1 \
  --schedule="0 */2 * * *" \
  --time-zone="Europe/Zurich" \
  --uri="https://emergence-guardian-service-HASH-ew.a.run.app/api/guardian/run-audit" \
  --http-method=POST \
  --headers="X-API-Key=SECRET_GUARDIAN_API_KEY,Content-Type=application/json" \
  --message-body='{"agents": ["prodguardian", "nexus", "argus"], "email_on_critical": true, "email_recipients": ["gonzalefernando@gmail.com"]}' \
  --max-retry-attempts=3 \
  --min-backoff=10s \
  --max-backoff=60s
```

### Phase 5 : Tests & Déploiement (1 jour)

**Tests :**
- [ ] Test local avec Docker
- [ ] Test Cloud Run staging
- [ ] Test Cloud Scheduler trigger manuel
- [ ] Test email notifications
- [ ] Test API endpoints avec Postman

**Déploiement :**
```bash
# Build & deploy
gcloud builds submit --config cloudbuild.yaml

# Vérifier deployment
gcloud run services describe emergence-guardian-service --region=europe-west1

# Test manuel
curl -X POST \
  -H "X-API-Key: $GUARDIAN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"agents": ["prodguardian"], "email_on_critical": false}' \
  https://emergence-guardian-service-HASH-ew.a.run.app/api/guardian/run-audit
```

---

## 📊 COÛTS ESTIMÉS

### Cloud Run

```
Estimations (2h interval, 5 min/exec):
- Exécutions/mois: 12 (par jour) × 30 = 360 exécutions
- Durée moyenne: 5 min/exec
- Total CPU: 360 × 5 = 1800 min = 30h/mois
- Total Memory: 512 Mi × 30h

Coût: ~5-10€/mois (Free tier: 2M requests, 360K GB-seconds)
```

### Cloud Storage

```
- Storage: ~10 GB rapports (30 jours retention)
- Requêtes: 360 uploads/mois + consultations admin

Coût: ~0.50€/mois
```

### Cloud Scheduler

```
- 1 job × 12 execs/jour × 30 jours = 360 execs/mois

Coût: Gratuit (Free tier: 3 jobs)
```

### Cloud Logging API

```
- Queries: 360 queries/mois (1 par exec Argus Cloud)
- Logs lus: ~100 MB/query

Coût: Gratuit (Free tier: 50 GB/mois)
```

**Total estimé : ~6-11€/mois** (dans Free Tier probablement)

---

## 🎯 TIMELINE

| Phase | Durée | Dépendances | Responsable |
|-------|-------|-------------|-------------|
| **Phase 1** - Setup Infrastructure | 1 jour | - | Claude/FG |
| **Phase 2** - Adapter Agents Python | 2 jours | Phase 1 | Claude |
| **Phase 3** - API Cloud Run | 2 jours | Phase 2 | Claude |
| **Phase 4** - Cloud Scheduler + Secrets | 1 jour | Phase 3 | Claude/FG |
| **Phase 5** - Tests & Déploiement | 1 jour | Phase 4 | Claude/FG |
| **TOTAL** | **7 jours** | - | - |

**Démarrage recommandé :** Après consolidation Guardian local (✅ fait aujourd'hui)

---

## ✅ VALIDATION & SUCCESS METRICS

### Critères de Succès

- [ ] Guardian Cloud Run déployé et accessible
- [ ] Cloud Scheduler trigger toutes les 2h sans erreur
- [ ] Rapports uploadés dans Cloud Storage automatiquement
- [ ] Emails envoyés automatiquement si status CRITICAL
- [ ] API endpoints fonctionnels (avec API key auth)
- [ ] Monitoring 24/7 garanti (uptime > 99%)
- [ ] Latence exec < 5 min par audit complet
- [ ] Coûts < 15€/mois

### Monitoring du Guardian lui-même

**Métriques Cloud Monitoring :**
- Latence exécution agents (`guardian_agent_latency_seconds`)
- Taux succès exécutions (`guardian_execution_success_rate`)
- Nombre erreurs production détectées (`guardian_prod_errors_detected`)
- Emails envoyés (`guardian_emails_sent_total`)

**Alertes :**
- Si Guardian service down > 10 min → Alert Slack
- Si Cloud Scheduler fail 3× consécutives → Email admin

---

## 🚀 PROCHAINES ÉTAPES

**Immédiat (cette semaine) :**
1. ✅ Consolider Guardian local (FAIT)
2. 📋 Valider ce plan migration avec FG
3. 🔧 Phase 1 : Setup infrastructure GCP

**Court terme (semaine prochaine) :**
4. 🤖 Phase 2 : Adapter agents Python
5. 🌐 Phase 3 : API Cloud Run

**Moyen terme (2 semaines) :**
6. ⏰ Phase 4 : Cloud Scheduler
7. 🧪 Phase 5 : Tests & déploiement

**Long terme (optionnel) :**
- Intégration Slack webhooks (alertes temps réel)
- Dashboard Guardian dans Admin UI (consultation rapports)
- GitHub Actions Guardian (ANIMA + NEO sur PR)
- BigQuery cost analysis (THEIA Cloud)

---

## 📞 QUESTIONS OUVERTES

1. **Email frequency :** 2h c'est OK ou trop spam si warnings fréquents?
   - **Proposition :** Email seulement si CRITICAL, Slack pour warnings

2. **Retention rapports :** 30 jours suffisant ou plus long?
   - **Proposition :** 30j actifs, 90j archives (Cloud Storage Nearline)

3. **API publique :** Exposer `/api/guardian/reports` publiquement (readonly) pour transparence?
   - **Proposition :** Garder privé pour l'instant, peut-être plus tard

4. **Intégration Admin UI :** Dashboard Guardian dans admin interface beta?
   - **Proposition :** Phase 2 (après déploiement Cloud Guardian)

---

**📝 Document vivant - Sera mis à jour pendant l'implémentation**
