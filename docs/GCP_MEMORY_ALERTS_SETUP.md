# Configuration Alertes Mémoire GCP Cloud Run

**Objectif** : Recevoir une alerte email quand l'utilisation mémoire > 80% de 2Gi.

**Date** : 2025-10-21 (post-résolution OOM)

---

## 📊 Contexte

Après résolution OOM en production (upgrade 1Gi → 2Gi), configuration alertes proactives pour surveiller utilisation mémoire et éviter futurs crashs.

**Seuil configuré** : 80% de 2Gi = 1.6Gi
**Durée déclenchement** : 5 minutes consécutives
**Notification** : Email + Dashboard GCP

---

## 🔧 Configuration Manuelle (GCP Console)

### 1. Accéder à Cloud Monitoring

1. Ouvrir [Google Cloud Console](https://console.cloud.google.com/)
2. Projet : `emergence-469005`
3. Menu Navigation → **Monitoring** → **Alerting**

### 2. Créer Canal de Notification

1. **Alerting** → **Notification Channels**
2. **Add New** → **Email**
3. Paramètres :
   - **Display Name** : `Emergence Admin - Memory Alerts`
   - **Email Address** : `gonzalefernando@gmail.com`
   - **Enabled** : ✅
4. **Save**

### 3. Créer Politique d'Alerte Mémoire

1. **Alerting** → **Create Policy**
2. **Add Condition** :

**Condition Details :**
- **Target** :
  - Resource type : `Cloud Run Revision`
  - Metric : `Memory utilization` (`run.googleapis.com/container/memory/utilizations`)
  - Filter :
    ```
    resource.service_name = "emergence-app"
    resource.location = "europe-west1"
    ```

- **Configuration** :
  - Condition type : `Threshold`
  - Aggregation : `Mean`
  - Condition : `Above threshold`
  - Threshold value : `0.80` (80%)
  - For : `5 minutes` (durée)

3. **Notifications** :
   - Select notification channel : `Emergence Admin - Memory Alerts`
   - Auto-close duration : `7 days`
   - Notification rate limit : `1 hour` (max 1 email/heure)

4. **Documentation** :
   ```markdown
   # Alerte Mémoire Cloud Run - Emergence

   **Service:** emergence-app
   **Région:** europe-west1
   **Seuil:** 80% de 2Gi (1.6Gi)

   ## Actions Recommandées

   1. **Vérifier les métriques détaillées:**
      ```bash
      gcloud run services describe emergence-app --region=europe-west1 --format=json
      ```

   2. **Consulter les logs récents:**
      ```bash
      python claude-plugins/integrity-docs-guardian/scripts/check_prod_logs.py
      ```

   3. **Analyser les rapports Guardian:**
      - Rapport prod: `reports/prod_report.json`
      - Résumé: `reports/codex_summary.md`

   4. **Si utilisation > 90% persistante:**
      ```bash
      # Augmenter à 4Gi
      gcloud run services update emergence-app --memory=4Gi --region=europe-west1
      ```

   ## Contexte

   Alerte configurée le 2025-10-21 après résolution OOM.
   Limite actuelle: 2Gi (upgrade depuis 1Gi après crashs).
   ```

5. **Alert name** : `Emergence Cloud Run - Memory > 80%`

6. **Save Policy**

---

## 🧪 Test de l'Alerte

### Option 1: Simulation via Dashboard

1. Monitoring → Alerting → Policies
2. Sélectionner `Emergence Cloud Run - Memory > 80%`
3. **Test** → Envoyer notification test

### Option 2: Monitoring Réel

1. Surveiller métriques actuelles :
   ```bash
   gcloud run services describe emergence-app \
     --region=europe-west1 \
     --format="value(status.traffic[0].latestRevision,status.traffic[0].revisionName)"
   ```

2. Consulter métriques mémoire :
   - Console GCP → Cloud Run → emergence-app → **Metrics**
   - Graph : `Memory utilization`
   - Vérifier si proche de 80% (1.6Gi)

---

## 📈 Métriques à Surveiller (24h post-upgrade)

### Commandes de Monitoring

```bash
# Statut service
gcloud run services describe emergence-app --region=europe-west1

# Logs récents (erreurs mémoire)
gcloud logging read \
  'resource.type="cloud_run_revision" AND resource.labels.service_name="emergence-app" AND textPayload:"memory"' \
  --limit=50 \
  --format=json

# Rapport Guardian prod
python claude-plugins/integrity-docs-guardian/scripts/check_prod_logs.py
```

### Métriques Clés (via GCP Console)

1. **Memory Utilization** :
   - Normal : 40-60% (0.8-1.2Gi)
   - Warning : 60-80% (1.2-1.6Gi)
   - Critical : >80% (>1.6Gi)

2. **Container Instance Count** :
   - Stable : 1-2 instances
   - Spike : >5 instances (possibleOOM recovery)

3. **Request Count & Latency** :
   - Vérifier corrélation avec memory spikes

4. **Error Rate** :
   - Must stay 0% (post-OOM fix)

---

## 🔴 Procédure d'Urgence (si alerte déclenchée)

### 1. Investigation Immédiate (< 5 min)

```bash
# Check état actuel
python claude-plugins/integrity-docs-guardian/scripts/check_prod_logs.py

# Vérifier métriques live
gcloud run services describe emergence-app --region=europe-west1

# Logs crashs
gcloud logging read \
  'resource.type="cloud_run_revision" AND severity="ERROR"' \
  --limit=20 \
  --freshness=1h
```

### 2. Décision (basée sur investigation)

**Scenario A : Memory > 80% mais < 90% (WARNING)**
- ✅ Continuer monitoring (pas d'action)
- ✅ Analyser patterns (heure de la journée, requêtes spécifiques)
- ✅ Planifier upgrade si tendance haussière

**Scenario B : Memory > 90% ou crashs (CRITICAL)**
- 🚨 Upgrade immédiat à 4Gi :
  ```bash
  gcloud run services update emergence-app --memory=4Gi --region=europe-west1
  ```
- 🚨 Vérifier santé post-upgrade :
  ```bash
  curl https://emergence-app-486095406755.europe-west1.run.app/api/health
  ```
- 🚨 Notifier équipe + documenter incident

### 3. Post-Incident

1. **Analyse Root Cause** :
   - Logs détaillés période incident
   - Patterns requêtes (endpoints memory-intensive)
   - Code profiling si récurrence

2. **Mise à jour Config** :
   - `stable-service.yaml` ligne 149
   - `canary-service.yaml` ligne 75
   - Documentation AGENT_SYNC.md

3. **Tests Charge** :
   - Valider nouvelle limite
   - Tester scénarios worst-case

---

## 📊 Dashboard Monitoring 24h

**Checklist quotidienne (1 fois/jour pendant 7 jours) :**

- [ ] Memory utilization max : `_____%` (objectif: <70%)
- [ ] Nombre crashs : `_____` (objectif: 0)
- [ ] Nombre alertes email : `_____` (objectif: 0)
- [ ] Latence P95 : `_____ms` (objectif: <500ms)
- [ ] Error rate : `_____%` (objectif: 0%)

**Log Monitoring :**
```bash
# Jour 1 (2025-10-21)
python claude-plugins/integrity-docs-guardian/scripts/check_prod_logs.py
# → Résultat: OK (0 errors, 0 warnings)

# Jour 2 (2025-10-22)
# TODO: Compléter

# Jour 3 (2025-10-23)
# TODO: Compléter
```

---

## 🔗 Ressources

**Documentation GCP :**
- [Cloud Run Memory Limits](https://cloud.google.com/run/docs/configuring/memory-limits)
- [Cloud Monitoring Alerting](https://cloud.google.com/monitoring/alerts)
- [Cloud Run Metrics](https://cloud.google.com/run/docs/monitoring)

**Docs Projet :**
- [AGENT_SYNC.md](../AGENT_SYNC.md) - Session 2025-10-21 07:50
- [docs/passation.md](passation.md) - Détails fix OOM

**Scripts :**
- [check_prod_logs.py](../claude-plugins/integrity-docs-guardian/scripts/check_prod_logs.py)
- [run_audit.py](../scripts/run_audit.py)

---

**Dernière mise à jour** : 2025-10-21 08:00 CET (Claude Code)
