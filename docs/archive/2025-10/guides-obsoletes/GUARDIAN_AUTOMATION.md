# 🛡️ Guardian Automation - ÉMERGENCE V8

**Système d'audit automatisé 3x/jour avec rapports par email**

---

## 📋 Table des matières

1. [Vue d'ensemble](#vue-densemble)
2. [Solution A - Cloud Run (Recommandé - 24/7)](#solution-a---cloud-run-recommandé---247)
3. [Solution B - Windows Task Scheduler](#solution-b---windows-task-scheduler)
4. [Dashboard Admin - Historique des Audits](#dashboard-admin---historique-des-audits)
5. [Tests & Vérification](#tests--vérification)
6. [Troubleshooting](#troubleshooting)

---

## 🎯 Vue d'ensemble

### Fonctionnalités

✅ **Audit automatisé 3x/jour** (08:00, 14:00, 20:00 CET)
✅ **Email HTML stylisé** envoyé à `gonzalefernando@gmail.com`
✅ **Dashboard admin** avec historique des audits
✅ **2 solutions** : Cloud Run (24/7) ou Windows (PC allumé)
✅ **Vérifications complètes** :
- Health endpoints production (`/api/health`, `/health/liveness`, `/health/readiness`)
- Métriques Cloud Run (status, conditions, génération)
- Logs récents (erreurs des 15 dernières minutes)
- Intégrité backend/frontend (7 fichiers critiques)
- Endpoints API (5 routers)
- Documentation (6 docs critiques)

---

## 🚀 Solution A - Cloud Run (Recommandé - 24/7)

### Avantages

✅ **Fonctionne 24/7** - pas besoin que ton PC soit allumé
✅ **Gratuit** - dans les limites du free tier GCP
✅ **Fiable** - infrastructure Google Cloud
✅ **Scalable** - se lance uniquement quand nécessaire

### Architecture

```
Cloud Scheduler (3 jobs)
    ↓ (08:00, 14:00, 20:00 CET)
Cloud Run Job (cloud-audit-job)
    ↓
Vérification Production
    ↓
Envoi Email (SMTP Gmail)
```

### Déploiement

#### 1. Prérequis

- Project GCP : `emergence-app-prod`
- Artifact Registry configuré
- Service Account avec permissions:
  - `roles/run.admin`
  - `roles/logging.viewer`
  - `roles/cloudscheduler.admin`
- Secrets Manager:
  - `smtp-password` (mot de passe app Gmail)
  - `openai-api-key` (pour compatibilité)

#### 2. Lancer le déploiement

```powershell
# Depuis le répertoire racine du projet
cd c:\dev\emergenceV8

# Lancer le script de déploiement
pwsh -File scripts/deploy-cloud-audit.ps1
```

Le script va :
1. ✅ Build de l'image Docker (`Dockerfile.audit`)
2. ✅ Push vers Artifact Registry
3. ✅ Déployer le Cloud Run Job
4. ✅ Créer 3 Cloud Scheduler jobs (08:00, 14:00, 20:00)
5. ✅ Proposer un test manuel

#### 3. Vérifier le déploiement

**Console GCP:**
- Cloud Run Jobs: https://console.cloud.google.com/run/jobs?project=emergence-app-prod
- Cloud Scheduler: https://console.cloud.google.com/cloudscheduler?project=emergence-app-prod
- Logs: https://console.cloud.google.com/logs/query?project=emergence-app-prod

**CLI:**
```bash
# Vérifier le job
gcloud run jobs describe cloud-audit-job --region=europe-west1

# Vérifier les schedulers
gcloud scheduler jobs list --location=europe-west1

# Lancer manuellement un test
gcloud run jobs execute cloud-audit-job --region=europe-west1 --wait
```

#### 4. Emails automatiques

**Format HTML stylisé:**
- Dark mode élégant
- Emojis et badges colorés
- Score de santé global
- Détails par catégorie (health, metrics, logs)
- Fallback texte brut

**Destinataire:** `gonzalefernando@gmail.com`

**Horaires (Europe/Zurich):**
- 🌅 **Matin:** 08:00
- 🌞 **Après-midi:** 14:00
- 🌙 **Soir:** 20:00

---

## 💻 Solution B - Windows Task Scheduler

### Avantages

✅ **Facile à configurer** - script PowerShell automatique
✅ **Pas de dépendance cloud** - tourne en local
✅ **Contrôle total** - modification simple des horaires

### Inconvénients

⚠️ **PC doit être allumé** - sinon les tâches ne s'exécutent pas
⚠️ **Pas de monitoring** si le PC est en veille
⚠️ **Pas adapté pour 24/7** - préférer Cloud Run

### Installation

#### 1. Ouvrir PowerShell en administrateur

```powershell
# Clic droit sur PowerShell > Exécuter en tant qu'administrateur
```

#### 2. Lancer le script de configuration

```powershell
cd c:\dev\emergenceV8

# Lancer le setup
pwsh -File scripts/setup-windows-scheduler.ps1
```

Le script va :
1. ✅ Vérifier que Python est disponible
2. ✅ Créer 3 tâches planifiées (08:00, 14:00, 20:00)
3. ✅ Configurer l'exécution automatique
4. ✅ Proposer un test manuel

#### 3. Vérifier les tâches

**Via GUI:**
- Ouvrir : `taskschd.msc`
- Chercher : "Emergence-Audit-*"
- Vérifier : Prochaine exécution

**Via PowerShell:**
```powershell
Get-ScheduledTask -TaskName "Emergence-Audit-*" | Get-ScheduledTaskInfo
```

#### 4. Modifier les horaires

**Via GUI:**
1. Ouvrir `taskschd.msc`
2. Clic droit sur la tâche > Propriétés
3. Onglet "Déclencheurs" > Modifier

**Via PowerShell:**
```powershell
$Trigger = New-ScheduledTaskTrigger -Daily -At "09:00"
Set-ScheduledTask -TaskName "Emergence-Audit-Morning" -Trigger $Trigger
```

---

## 📊 Dashboard Admin - Historique des Audits

### Fonctionnalités

✅ **Historique complet** des 10 derniers audits
✅ **Stats en temps réel** (OK, Warnings, Critical)
✅ **Score moyen d'intégrité**
✅ **Détails par audit** (modal avec infos complètes)
✅ **Auto-refresh** toutes les 5 minutes

### Intégration

#### 1. Backend API

**Endpoint ajouté:**
```
GET /api/admin/dashboard/audits?limit=10
```

**Réponse:**
```json
{
  "audits": [
    {
      "timestamp": "2025-10-19T04:47:39+00:00",
      "revision": "emergence-app-00501-zon",
      "status": "OK",
      "integrity_score": "83%",
      "checks": {
        "total": 24,
        "passed": 20,
        "failed": 4
      },
      "summary": {
        "backend_integrity": "OK",
        "frontend_integrity": "OK",
        "ws_health": "OK",
        "prod_status": "OK"
      },
      "issues": []
    }
  ],
  "count": 1,
  "stats": {
    "ok": 1,
    "warning": 0,
    "critical": 0,
    "average_score": "83%"
  },
  "latest": { ... }
}
```

#### 2. Frontend Widget

**Fichiers ajoutés:**
- `src/frontend/features/admin/audit-history.js` - Widget JavaScript
- `src/frontend/features/admin/audit-history.css` - Styling

**Intégration dans le dashboard admin:**

```html
<!-- Dans admin-dashboard.html -->
<link rel="stylesheet" href="/frontend/features/admin/audit-history.css">

<div id="audit-history-container"></div>

<script type="module">
import { AuditHistoryWidget } from '/frontend/features/admin/audit-history.js';
import { APIClient } from '/frontend/core/api-client.js';

const apiClient = new APIClient();
const auditWidget = new AuditHistoryWidget(apiClient);
await auditWidget.init('audit-history-container');

// Exposer globalement pour les boutons onclick
window.auditHistoryWidget = auditWidget;
</script>
```

#### 3. Fonctionnalités UI

**Stats Cards:**
- ✅ OK (nombre d'audits réussis)
- ⚠️ Warnings (nombre d'avertissements)
- 🚨 Critical (nombre de critiques)
- 📈 Score moyen d'intégrité

**Dernier Audit:**
- Timestamp
- Révision Cloud Run
- Statut (badge coloré)
- Score d'intégrité
- Checks passés/totaux
- Liste des problèmes détectés

**Historique Tableau:**
- Colonnes : Date/Heure, Révision, Statut, Score, Checks, Détails
- Bouton "👁️ Voir" pour ouvrir modal détails
- Tri par timestamp décroissant

**Modal Détails:**
- Informations générales
- Résumé des vérifications
- Liste des problèmes

---

## 🧪 Tests & Vérification

### Test manuel local

```bash
# Test sans email
python scripts/run_audit.py --no-email

# Test complet avec email
python scripts/run_audit.py --target emergence-app-00501-zon --mode full
```

### Test Cloud Run Job

```bash
# Via gcloud CLI
gcloud run jobs execute cloud-audit-job --region=europe-west1 --wait

# Via console GCP
# https://console.cloud.google.com/run/jobs/details/europe-west1/cloud-audit-job?project=emergence-app-prod
# Cliquer sur "EXECUTE"
```

### Vérifier les emails

1. Check boîte mail `gonzalefernando@gmail.com`
2. Rechercher sujet : "☁️ Audit Cloud ÉMERGENCE"
3. Vérifier format HTML (badges colorés, dark mode)
4. Vérifier fallback texte brut (si HTML désactivé)

### Vérifier logs Cloud Run

```bash
# Via gcloud
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=cloud-audit-job" --limit=50 --format=json

# Via console
# https://console.cloud.google.com/logs/query?project=emergence-app-prod
# Filtre: resource.type="cloud_run_job" resource.labels.job_name="cloud-audit-job"
```

---

## 🐛 Troubleshooting

### Email non reçu

**Vérifier SMTP config:**
```bash
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('EMAIL_ENABLED:', os.getenv('EMAIL_ENABLED')); print('SMTP_HOST:', os.getenv('SMTP_HOST')); print('SMTP_USER:', os.getenv('SMTP_USER'))"
```

**Résultat attendu:**
```
EMAIL_ENABLED: 1
SMTP_HOST: smtp.gmail.com
SMTP_USER: gonzalefernando@gmail.com
```

**Si manquant:**
- Vérifier fichier `.env` à la racine
- Vérifier Secret Manager dans GCP pour `smtp-password`

### Cloud Run Job échoue

**Vérifier les logs:**
```bash
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=cloud-audit-job AND severity>=ERROR" --limit=10
```

**Erreurs communes:**
- `ImportError: google-cloud-run` → Vérifier Dockerfile.audit (ligne 18-21)
- `401 Unauthorized` → Vérifier Service Account permissions
- `SMTP authentication failed` → Vérifier smtp-password dans Secret Manager

### Task Scheduler ne se lance pas

**Vérifier état tâche:**
```powershell
Get-ScheduledTask -TaskName "Emergence-Audit-Morning" | Get-ScheduledTaskInfo
```

**Vérifier LastTaskResult:**
- `0` = Succès
- `1` = Erreur générale
- `0x1` = Permission denied

**Si erreur permission:**
1. Ouvrir `taskschd.msc`
2. Clic droit sur tâche > Propriétés
3. Onglet "Général" > Vérifier "Exécuter avec les privilèges les plus élevés"

### Dashboard admin ne charge pas les audits

**Vérifier endpoint backend:**
```bash
# Depuis VSCode / navigateur dev tools
fetch('/api/admin/dashboard/audits?limit=10', {
    headers: {
        'Authorization': 'Bearer YOUR_JWT_TOKEN'
    }
})
.then(r => r.json())
.then(console.log)
```

**Vérifier fichiers rapports:**
```bash
ls reports/guardian_verification_report*.json
```

**Si vide:**
- Lancer un audit manuel : `python scripts/run_audit.py`
- Vérifier permissions lecture fichiers

---

## 📚 Références

### Scripts créés

| Fichier | Description |
|---------|-------------|
| `scripts/run_audit.py` | Script d'audit local (PC) |
| `scripts/cloud_audit_job.py` | Script d'audit cloud (Cloud Run) |
| `scripts/deploy-cloud-audit.ps1` | Déploiement Cloud Run + Scheduler |
| `scripts/setup-windows-scheduler.ps1` | Configuration Task Scheduler Windows |

### Fichiers infrastructure

| Fichier | Description |
|---------|-------------|
| `Dockerfile.audit` | Dockerfile pour Cloud Run Job |
| `src/backend/features/dashboard/admin_router.py` | Endpoint API `/admin/dashboard/audits` |
| `src/backend/features/dashboard/admin_service.py` | Service `get_audit_history()` |
| `src/frontend/features/admin/audit-history.js` | Widget UI dashboard |
| `src/frontend/features/admin/audit-history.css` | Styling widget |

### Rapports générés

| Fichier | Description |
|---------|-------------|
| `reports/guardian_verification_report.json` | Rapport principal audit local |
| `reports/global_report.json` | Rapport global Guardian |
| `reports/integrity_report.json` | Rapport intégrité (Neo) |
| `reports/docs_report.json` | Rapport documentation (Anima) |
| `reports/unified_report.json` | Rapport unifié (Nexus) |
| `reports/prod_report.json` | Rapport production Cloud Run |

---

## ✅ Recommandation Finale

**Pour un monitoring 24/7 fiable :**

👉 **Utilise la Solution A (Cloud Run)** 👈

**Avantages :**
- ✅ Fonctionne même si ton PC est éteint
- ✅ Gratuit (free tier GCP)
- ✅ Fiable et scalable
- ✅ Logs centralisés dans GCP
- ✅ Facile à monitorer (console GCP)

**Déploiement :**
```bash
pwsh -File scripts/deploy-cloud-audit.ps1
```

**Vérification :**
- Email reçu dans les 2 minutes
- Logs visibles dans GCP
- Dashboard admin affiche l'historique

---

**🎉 Ton système Guardian surveille maintenant ÉMERGENCE 24/7 ! 🛡️**

