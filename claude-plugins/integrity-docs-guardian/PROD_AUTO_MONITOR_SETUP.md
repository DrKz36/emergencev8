# 🔍 ProdGuardian - Configuration de la Surveillance Automatique

## ✅ Vue d'ensemble

Ce guide explique comment configurer la surveillance automatique de la production sur Google Cloud toutes les 30 minutes.

---

## 🎯 Objectif

Exécuter automatiquement `check_prod_logs.py` toutes les 30 minutes pour surveiller l'application **emergence-app** sur Cloud Run (région: europe-west1) et détecter les anomalies en temps réel.

---

## 📦 Ce qui a été créé

### 1. **Script de Surveillance Automatique**
- ✅ [scripts/prod_guardian_scheduler.ps1](scripts/prod_guardian_scheduler.ps1)
  - Exécute `check_prod_logs.py` automatiquement
  - Génère des rapports d'exécution horodatés
  - Nettoie les anciens rapports (> 7 jours)
  - Configure automatiquement le Task Scheduler Windows
  - Gère les alertes selon le statut (OK/DEGRADED/CRITICAL)

### 2. **Rapports Générés**
- `reports/prod_report.json` - Rapport de surveillance production
- `reports/prodguardian_execution_YYYYMMDD_HHmmss.json` - Historique des exécutions
- `logs/prodguardian_scheduler_YYYY-MM.log` - Logs mensuels du scheduler

---

## 🚀 Installation Rapide

### Option 1: Configuration Automatique (Recommandée)

```powershell
# Exécuter en tant qu'administrateur
cd C:\dev\emergenceV8
.\claude-plugins\integrity-docs-guardian\scripts\prod_guardian_scheduler.ps1 -SetupScheduler
```

Cette commande va:
1. ✅ Créer une tâche Windows nommée "ProdGuardian_AutoMonitor"
2. ✅ Configurer l'exécution toutes les 30 minutes
3. ✅ Utiliser votre compte utilisateur actuel
4. ✅ Démarrer automatiquement même si l'ordinateur est sur batterie

### Option 2: Configuration Manuelle

1. **Ouvrir le Planificateur de tâches**
   ```
   Touche Windows + R → taskschd.msc → Entrée
   ```

2. **Créer une nouvelle tâche**
   - Clic droit sur "Bibliothèque du Planificateur de tâches"
   - Créer un dossier "ÉMERGENCE"
   - Créer une tâche → "Créer une tâche de base..."

3. **Configuration de la tâche**

   **Général:**
   - Nom: `ProdGuardian_AutoMonitor`
   - Description: `Surveillance automatique de la production ÉMERGENCE sur Google Cloud toutes les 30 minutes`
   - Exécuter même si l'utilisateur n'est pas connecté: ❌ (décoché)
   - Exécuter avec les autorisations maximales: ❌ (décoché)

   **Déclencheur:**
   - Type: Quotidien
   - Tous les: 1 jour
   - Répéter la tâche toutes les: **30 minutes**
   - Pendant: Indéfiniment
   - Activé: ✅

   **Action:**
   - Action: Démarrer un programme
   - Programme: `PowerShell.exe`
   - Ajouter des arguments:
     ```
     -NoProfile -ExecutionPolicy Bypass -File "C:\dev\emergenceV8\claude-plugins\integrity-docs-guardian\scripts\prod_guardian_scheduler.ps1"
     ```

   **Conditions:**
   - Démarrer la tâche uniquement si l'ordinateur est connecté au réseau: ✅
   - Démarrer uniquement si l'ordinateur est branché: ❌

   **Paramètres:**
   - Autoriser le démarrage de la tâche à la demande: ✅
   - Arrêter la tâche si elle s'exécute plus de: 1 heure
   - Si la tâche échoue, la redémarrer toutes les: 10 minutes

---

## 📋 Prérequis

### 1. **Python 3.11+**
```powershell
python --version
# Doit afficher Python 3.11 ou supérieur
```

### 2. **gcloud CLI Installé et Authentifié**

**Installation:**
```powershell
# Télécharger depuis: https://cloud.google.com/sdk/docs/install
# Ou avec Chocolatey:
choco install gcloudsdk
```

**Authentication:**
```powershell
# Se connecter à Google Cloud
gcloud auth login

# Configurer le projet par défaut (optionnel)
gcloud config set project YOUR_PROJECT_ID

# Vérifier l'accès aux logs
gcloud logging read 'resource.type="cloud_run_revision"' --limit=1
```

### 3. **Accès au Service Cloud Run**

Vérifier que vous avez les droits de lecture sur le service:
```powershell
gcloud run services describe emergence-app --region=europe-west1
```

Si vous obtenez une erreur de permission, demandez les droits suivants:
- `roles/logging.viewer` - Pour lire les logs
- `roles/run.viewer` - Pour voir le service Cloud Run

---

## 🧪 Test de la Configuration

### Test 1: Exécution Manuelle du Script

```powershell
cd C:\dev\emergenceV8
.\claude-plugins\integrity-docs-guardian\scripts\prod_guardian_scheduler.ps1 -Verbose
```

**Résultat attendu:**
```
[2025-10-17 10:30:00] [INFO] ================================================================
[2025-10-17 10:30:00] [INFO] 🔍 PROD GUARDIAN SCHEDULER - Surveillance Production Automatique
[2025-10-17 10:30:00] [INFO] ================================================================
...
[2025-10-17 10:30:15] [SUCCESS] ✅ Production Status: OK - Aucune anomalie détectée
...
[2025-10-17 10:30:20] [INFO] Fin de l'exécution (code: 0)
```

### Test 2: Vérifier les Rapports Générés

```powershell
# Rapport de production (mis à jour à chaque exécution)
cat .\claude-plugins\integrity-docs-guardian\reports\prod_report.json

# Dernier rapport d'exécution
Get-ChildItem .\claude-plugins\integrity-docs-guardian\reports\prodguardian_execution_*.json | Sort-Object LastWriteTime -Descending | Select-Object -First 1 | Get-Content
```

### Test 3: Vérifier la Tâche Planifiée

```powershell
# Lister la tâche
Get-ScheduledTask -TaskName "ProdGuardian_AutoMonitor" -TaskPath "\ÉMERGENCE\"

# Voir les détails
Get-ScheduledTaskInfo -TaskName "ProdGuardian_AutoMonitor" -TaskPath "\ÉMERGENCE\"

# Exécuter manuellement
Start-ScheduledTask -TaskName "ProdGuardian_AutoMonitor" -TaskPath "\ÉMERGENCE\"
```

### Test 4: Surveiller les Logs

```powershell
# Voir les logs du mois en cours
Get-Content .\claude-plugins\integrity-docs-guardian\logs\prodguardian_scheduler_$(Get-Date -Format 'yyyy-MM').log -Tail 50 -Wait
```

---

## 📊 Interprétation des Résultats

### Statut: OK (Code de sortie: 0)
```
🟢 Production Status: OK

📊 Summary:
   - Logs analyzed: 78
   - Errors: 0
   - Warnings: 0
   - Critical signals: 0
   - Latency issues: 0

💡 Recommendations:
   🟢 [LOW] No immediate action required
      Production is healthy
```
**Action:** Aucune - Tout va bien!

### Statut: DEGRADED (Code de sortie: 1)
```
🟡 Production Status: DEGRADED

📊 Summary:
   - Logs analyzed: 80
   - Errors: 2
   - Warnings: 4
   - Critical signals: 0
   - Latency issues: 1

💡 Recommendations:
   🟡 [MEDIUM] Monitor closely and investigate warnings
      4 warnings detected
```
**Action:** Surveiller de près, investiguer les warnings dans les prochaines 1-2 heures

### Statut: CRITICAL (Code de sortie: 2)
```
🔴 Production Status: CRITICAL

📊 Summary:
   - Errors: 12
   - Critical signals: 2

❌ Critical Issues:
   [2025-10-17T15:47:23Z] OOM
      Container exceeded memory limit (OOMKilled)

💡 Recommendations:
   🔴 [HIGH] Increase memory limit
      Command: gcloud run services update emergence-app --memory=2Gi --region=europe-west1
```
**Action:** Action immédiate requise! Consulter le rapport détaillé et appliquer les recommandations

---

## 🔧 Configuration Avancée

### Changer la Fréquence d'Exécution

**Pour 15 minutes:**
```powershell
# Modifier le déclencheur dans le Task Scheduler
$TaskName = "ProdGuardian_AutoMonitor"
$Trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 15) -RepetitionDuration ([TimeSpan]::MaxValue)

Set-ScheduledTask -TaskName $TaskName -TaskPath "\ÉMERGENCE\" -Trigger $Trigger
```

**Pour 1 heure:**
```powershell
$Trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Hours 1) -RepetitionDuration ([TimeSpan]::MaxValue)

Set-ScheduledTask -TaskName $TaskName -TaskPath "\ÉMERGENCE\" -Trigger $Trigger
```

### Modifier les Seuils de Détection

Éditer [scripts/check_prod_logs.py](scripts/check_prod_logs.py):

```python
# Ligne 22-24: Ajuster les seuils
ERROR_THRESHOLD_DEGRADED = 1    # Nombre d'erreurs pour status DEGRADED
ERROR_THRESHOLD_CRITICAL = 5    # Nombre d'erreurs pour status CRITICAL
WARNING_THRESHOLD = 3           # Nombre de warnings pour status DEGRADED
```

### Modifier la Fenêtre de Temps des Logs

Éditer [scripts/check_prod_logs.py](scripts/check_prod_logs.py):

```python
# Ligne 19: Ajuster la fenêtre de temps
FRESHNESS = "1h"    # Options: "30m", "1h", "2h", "6h", "12h", "1d"
```

### Ajouter des Notifications (TODO - Extension Future)

Le script peut être étendu pour envoyer des notifications:
- Email (via SMTP)
- Slack (via Webhook)
- Microsoft Teams
- Discord

---

## 🛠️ Dépannage

### Problème: La tâche ne s'exécute pas

**Solution 1: Vérifier que la tâche est activée**
```powershell
Get-ScheduledTask -TaskName "ProdGuardian_AutoMonitor" | Select-Object State
# Doit afficher: State = Ready
```

**Solution 2: Vérifier l'historique de la tâche**
```
1. Ouvrir le Planificateur de tâches (taskschd.msc)
2. Naviguer vers ÉMERGENCE > ProdGuardian_AutoMonitor
3. Onglet "Historique" → Activer l'historique si désactivé
4. Consulter les erreurs récentes
```

**Solution 3: Exécuter manuellement pour voir les erreurs**
```powershell
.\claude-plugins\integrity-docs-guardian\scripts\prod_guardian_scheduler.ps1 -Verbose
```

### Problème: "gcloud: command not found"

**Solution:**
```powershell
# Réinstaller gcloud CLI
choco install gcloudsdk

# Ou télécharger manuellement depuis:
# https://cloud.google.com/sdk/docs/install

# Redémarrer PowerShell après installation
```

### Problème: "Permission denied" lors de la lecture des logs

**Solution:**
```powershell
# Re-authentifier
gcloud auth login

# Vérifier le projet actif
gcloud config get-value project

# Demander les droits de logging viewer si nécessaire
```

### Problème: Aucun log retourné

**Causes possibles:**
1. Service name incorrect → Vérifier avec `gcloud run services list`
2. Région incorrecte → Doit être `europe-west1`
3. Pas de logs dans la dernière heure → Augmenter `FRESHNESS` dans le script
4. Service non déployé ou inactif

**Debug:**
```powershell
# Vérifier que le service existe
gcloud run services describe emergence-app --region=europe-west1

# Tester la lecture des logs manuellement
gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="emergence-app"' --limit=5 --freshness=1h
```

---

## 📁 Structure des Fichiers

```
claude-plugins/integrity-docs-guardian/
├── scripts/
│   ├── check_prod_logs.py                      # Script de surveillance (existant)
│   └── prod_guardian_scheduler.ps1             # ✅ NOUVEAU: Scheduler automatique
│
├── reports/
│   ├── prod_report.json                        # Rapport de prod (mis à jour toutes les 30min)
│   └── prodguardian_execution_*.json           # Historique des exécutions
│
├── logs/
│   └── prodguardian_scheduler_YYYY-MM.log      # Logs mensuels du scheduler
│
├── PRODGUARDIAN_SETUP.md                       # Guide du script check_prod_logs.py
└── PROD_AUTO_MONITOR_SETUP.md                  # ✅ NOUVEAU: Ce guide
```

---

## 🔄 Intégration avec le Unified Guardian Scheduler

Le script `prod_guardian_scheduler.ps1` peut également être intégré dans le [unified_guardian_scheduler.ps1](scripts/unified_guardian_scheduler.ps1) existant pour orchestrer:

1. **Guardian d'intégrité** (vérification docs)
2. **ProdGuardian** (surveillance production) ← Ce script
3. **Génération de rapports consolidés**
4. **AutoSync** (mises à jour automatiques)

Pour cela, le `unified_guardian_scheduler.ps1` appelle déjà ProdGuardian, mais uniquement dans le cadre d'une orchestration complète. Le script `prod_guardian_scheduler.ps1` est spécifiquement dédié à la surveillance production autonome toutes les 30 minutes.

---

## ✅ Checklist de Vérification

- [x] Script de surveillance créé (`prod_guardian_scheduler.ps1`)
- [x] Documentation de setup complète (ce fichier)
- [ ] **gcloud CLI installé et authentifié** ← **ACTION REQUISE**
- [ ] **Tâche planifiée créée** ← **ACTION REQUISE**
- [ ] **Test d'exécution manuelle réussi** ← **ACTION REQUISE**
- [ ] **Premier rapport de production généré** ← **ACTION REQUISE**
- [ ] **Logs de surveillance vérifiés** ← **ACTION REQUISE**

---

## 🎯 Prochaines Étapes

### Actions Immédiates

1. **Installer et configurer gcloud CLI** (si ce n'est pas déjà fait)
   ```powershell
   choco install gcloudsdk
   gcloud auth login
   ```

2. **Configurer la tâche planifiée**
   ```powershell
   # Exécuter en tant qu'administrateur
   .\claude-plugins\integrity-docs-guardian\scripts\prod_guardian_scheduler.ps1 -SetupScheduler
   ```

3. **Tester l'exécution**
   ```powershell
   # Test manuel
   .\claude-plugins\integrity-docs-guardian\scripts\prod_guardian_scheduler.ps1 -Verbose

   # Test via Task Scheduler
   Start-ScheduledTask -TaskName "ProdGuardian_AutoMonitor" -TaskPath "\ÉMERGENCE\"
   ```

4. **Vérifier les rapports**
   ```powershell
   # Rapport de production
   cat .\claude-plugins\integrity-docs-guardian\reports\prod_report.json

   # Logs du scheduler
   cat .\claude-plugins\integrity-docs-guardian\logs\prodguardian_scheduler_$(Get-Date -Format 'yyyy-MM').log
   ```

### Extensions Futures

- [ ] Notifications par email/Slack en cas de statut CRITICAL
- [ ] Dashboard de visualisation des métriques historiques
- [ ] Alertes intelligentes basées sur des tendances
- [ ] Auto-remediation pour problèmes courants (avec validation)
- [ ] Intégration avec le système de monitoring Cloud (Stackdriver)

---

## 📚 Ressources Supplémentaires

- [ProdGuardian User Guide](PRODGUARDIAN_README.md) - Guide d'utilisation manuel
- [check_prod_logs.py Setup](PRODGUARDIAN_SETUP.md) - Configuration du script de base
- [Agent Prompt Template](agents/prodguardian.md) - Template pour Claude Code
- [Slash Command](/check_prod) - Utilisation via Claude Code
- [Google Cloud Run Logging](https://cloud.google.com/run/docs/logging) - Documentation officielle

---

## 🤝 Support

En cas de problème:

1. Consulter les logs: `logs/prodguardian_scheduler_YYYY-MM.log`
2. Exécuter en mode verbose: `.\prod_guardian_scheduler.ps1 -Verbose`
3. Vérifier les prérequis (Python, gcloud, droits d'accès)
4. Consulter la documentation Google Cloud

---

**Status:** ✅ Configuration Prête - En Attente d'Activation

**Dernière Mise à Jour:** 2025-10-17
**Version:** 1.0.0
**Auteur:** Claude Code Agent
