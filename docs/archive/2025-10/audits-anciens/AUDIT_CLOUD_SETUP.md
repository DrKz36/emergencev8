# Audit Cloud ÉMERGENCE V8 - Configuration Toutes les 2h

**Status:** ✅ Scripts prêts | ⏳ Déploiement cloud en attente (permissions GCP)

---

## 🎯 Vue d'ensemble

Système d'audit automatisé de la production Cloud Run qui envoie des rapports par email **toutes les 2 heures** (12x/jour).

### Fonctionnalités

✅ **Email HTML stylisé dark mode**
- Score de santé global
- Vérification health endpoints
- Métriques Cloud Run via API Google
- Analyse logs récents (15 min)
- Design moderne avec badges colorés

✅ **12 exécutions quotidiennes**
- Toutes les 2h: 00:00, 02:00, 04:00, 06:00, 08:00, 10:00, 12:00, 14:00, 16:00, 18:00, 20:00, 22:00
- Timezone: Europe/Zurich
- Email automatique à: gonzalefernando@gmail.com

---

## 📧 Test Email Réussi

**Date:** 19 octobre 2025, 07:35
**Résultat:** ✅ Email envoyé et reçu avec succès

L'email de test contient :
- Badge statut vert "OK"
- Score santé 100%
- Design dark mode avec dégradé bleu
- Métriques production stylisées

---

## 🚀 Utilisation Locale (Mode Test)

### Test immédiat (un seul email)

```powershell
python scripts/test_audit_email.py
```

**Prérequis:** `.env` doit contenir `SMTP_PASSWORD=dfshbvvsmyqrfkja`

### Boucle toutes les 2h (simulation cloud)

```powershell
pwsh -File scripts/run_local_audit_2h.ps1
```

**Options:**
```powershell
# Durée personnalisée (par défaut 24h)
pwsh -File scripts/run_local_audit_2h.ps1 -DurationHours 48
```

---

## ☁️ Déploiement Cloud Run (Option Recommandée)

### Prérequis

**Permissions GCP nécessaires:**
- `artifactregistry.repositories.create` - Créer repository Docker
- `artifactregistry.repositories.uploadArtifacts` - Push images
- `run.jobs.create` - Déployer Cloud Run Jobs
- `cloudscheduler.jobs.create` - Créer schedulers

**Secrets GCP à configurer:**
```bash
# Créer les secrets (une seule fois)
echo -n "dfshbvvsmyqrfkja" | gcloud secrets create smtp-password --data-file=-
echo -n "sk-proj-aQfB..." | gcloud secrets create openai-api-key --data-file=-
```

### Déploiement

```powershell
pwsh -File scripts/deploy-cloud-audit.ps1
```

**Le script effectue automatiquement:**
1. ✅ Build Docker image (`Dockerfile.audit`)
2. ✅ Push vers Artifact Registry (`europe-west1-docker.pkg.dev`)
3. ✅ Déploie Cloud Run Job (`cloud-audit-job`)
4. ✅ Crée 12 Cloud Schedulers (toutes les 2h)
5. ✅ Test manuel optionnel

---

## 📁 Fichiers Clés

### Scripts d'audit
- `scripts/cloud_audit_job.py` - Job audit cloud (SMTP direct)
- `scripts/test_audit_email.py` - Test local immédiat
- `scripts/run_local_audit_2h.ps1` - Boucle test 2h

### Déploiement
- `scripts/deploy-cloud-audit.ps1` - Déploiement automatisé
- `Dockerfile.audit` - Image Docker Cloud Run

### Documentation
- `GUARDIAN_AUTOMATION.md` - Guide complet automatisation
- `AUDIT_CLOUD_SETUP.md` - Ce fichier

---

## 🔍 Vérifications Effectuées

### 1. Health Endpoints (Production)
```
✅ /api/health
✅ /health/liveness
✅ /health/readiness
```

### 2. Métriques Cloud Run
- Service status
- Conditions (Ready, etc.)
- Génération observée

### 3. Logs Récents
- Erreurs des 15 dernières minutes
- Niveau CRITICAL et ERROR
- Échantillon dans l'email

---

## 🎨 Format Email

### HTML Dark Mode
- Container : Dégradé #1a1a2e → #16213e
- Badges colorés : Vert (OK), Orange (WARNING), Rouge (CRITICAL)
- Métriques : Cards avec bordure bleue
- Police : -apple-system, BlinkMacSystemFont, 'Segoe UI'

### Texte Brut (Fallback)
Format simple avec :
- Timestamp
- Score global
- Résumé checks
- Contact admin

---

## ⚙️ Configuration Cloud Scheduler

**12 jobs créés automatiquement:**

| Nom | Cron | Heure (CET) |
|-----|------|-------------|
| `cloud-audit-00h` | `0 0 * * *` | 00:00 |
| `cloud-audit-02h` | `0 2 * * *` | 02:00 |
| `cloud-audit-04h` | `0 4 * * *` | 04:00 |
| `cloud-audit-06h` | `0 6 * * *` | 06:00 |
| `cloud-audit-08h` | `0 8 * * *` | 08:00 |
| `cloud-audit-10h` | `0 10 * * *` | 10:00 |
| `cloud-audit-12h` | `0 12 * * *` | 12:00 |
| `cloud-audit-14h` | `0 14 * * *` | 14:00 |
| `cloud-audit-16h` | `0 16 * * *` | 16:00 |
| `cloud-audit-18h` | `0 18 * * *` | 18:00 |
| `cloud-audit-20h` | `0 20 * * *` | 20:00 |
| `cloud-audit-22h` | `0 22 * * *` | 22:00 |

---

## 🐛 Troubleshooting

### Email non reçu

**Vérifier:**
1. `.env` contient `SMTP_PASSWORD=dfshbvvsmyqrfkja`
2. `EMAIL_ENABLED=1` dans `.env`
3. Pas de blocage Gmail (vérifier spam)

**Debug:**
```python
python scripts/test_audit_email.py
# Doit afficher: "Email envoyé avec succès à gonzalefernando@gmail.com!"
```

### Erreur déploiement Cloud Run

**Erreur:** `Permission denied on resource project emergence-app-prod`

**Solution:** Demander accès GCP à l'admin avec ces rôles:
- `roles/artifactregistry.admin`
- `roles/run.admin`
- `roles/cloudscheduler.admin`

### Build Docker échoue

**Vérifier:**
```powershell
docker build -f Dockerfile.audit -t test-audit .
```

Si erreur `COPY failed`, vérifier que `scripts/cloud_audit_job.py` existe.

---

## 📊 Monitoring

### Logs Cloud Run
```bash
gcloud run jobs logs read cloud-audit-job \
  --project=emergence-app-prod \
  --region=europe-west1 \
  --limit=50
```

### Vérifier Schedulers
```bash
gcloud scheduler jobs list \
  --project=emergence-app-prod \
  --location=europe-west1
```

### Test manuel Cloud Run Job
```bash
gcloud run jobs execute cloud-audit-job \
  --region=europe-west1 \
  --project=emergence-app-prod \
  --wait
```

---

## 🎯 Prochaines Étapes

### Immédiat (Local)
- [x] ✅ Test email envoyé et reçu
- [ ] Lancer boucle 2h pour vérifier stabilité (optionnel)

### Cloud (Nécessite permissions)
1. Demander accès GCP (Artifact Registry + Cloud Run + Scheduler)
2. Créer secrets GCP (`smtp-password`, `openai-api-key`)
3. Lancer `pwsh -File scripts/deploy-cloud-audit.ps1`
4. Tester manuellement le job
5. Attendre 2h pour vérifier premier email automatique

---

## 🤝 Support

**Contact:** gonzalefernando@gmail.com
**Projet:** emergence-app-prod
**Région:** europe-west1

**Documentation complète:** [GUARDIAN_AUTOMATION.md](./GUARDIAN_AUTOMATION.md)

---

**Dernière mise à jour:** 19 octobre 2025
**Version:** 1.0
**Status:** Prêt pour déploiement cloud ☁️
