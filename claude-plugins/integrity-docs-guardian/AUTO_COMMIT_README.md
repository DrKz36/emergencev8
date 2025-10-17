# Auto-Commit pour les Agents Guardian

Documentation complète pour l'activation et la gestion du commit automatique dans le système Guardian ÉMERGENCE.

## 📚 Table des Matières

1. [Vue d'ensemble](#vue-densemble)
2. [Installation rapide](#installation-rapide)
3. [Méthodes d'activation](#méthodes-dactivation)
4. [Documentation](#documentation)
5. [Scripts disponibles](#scripts-disponibles)
6. [Dépannage](#dépannage)

---

## Vue d'ensemble

Le **commit automatique** (`AUTO_COMMIT=1`) permet aux agents Guardian d'automatiquement committer les changements détectés sans interaction manuelle. Cette fonctionnalité est essentielle pour :

- ✅ L'automatisation complète du workflow Guardian
- ✅ Les exécutions planifiées via Task Scheduler
- ✅ La synchronisation continue de la documentation
- ✅ Les mises à jour automatiques de rapports

### Agents concernés

- **Anima (DocKeeper)** - Documentation
- **Neo (IntegrityWatcher)** - Vérification d'intégrité
- **ProdGuardian** - Surveillance production
- **Nexus (Coordinator)** - Coordination et rapports

---

## Installation Rapide

### Option 1 : Script d'activation en un clic (Recommandé)

```powershell
# Ouvrir PowerShell en tant qu'administrateur
cd C:\dev\emergenceV8\claude-plugins\integrity-docs-guardian\scripts

# Exécuter le script d'activation rapide
.\quick_enable_auto_commit.ps1
```

Ce script :
- ✅ Vérifie les privilèges
- ✅ Reconfigure la tâche planifiée avec AUTO_COMMIT
- ✅ Propose un test immédiat
- ✅ Affiche les commandes utiles

### Option 2 : Configuration manuelle

```powershell
# Reconfigurer la tâche planifiée avec AUTO_COMMIT
.\setup_unified_scheduler.ps1 -Force -EnableAutoCommit
```

---

## Méthodes d'Activation

### 1. Via Task Scheduler (Production)

**Pour l'automatisation complète :**

```powershell
cd scripts
.\setup_unified_scheduler.ps1 -Force -EnableAutoCommit
```

**Personnaliser l'intervalle :**

```powershell
# Exécuter toutes les 30 minutes
.\setup_unified_scheduler.ps1 -Force -EnableAutoCommit -IntervalMinutes 30
```

### 2. Variable d'environnement système

**Activation permanente (tous les utilisateurs) :**

```powershell
# Nécessite PowerShell en admin
.\enable_auto_commit.ps1
```

**Activation pour l'utilisateur courant uniquement :**

```powershell
# Pas besoin de droits admin
.\enable_auto_commit.ps1 -UserLevel
```

### 3. Exécution ponctuelle

**PowerShell :**

```powershell
$env:AUTO_COMMIT = "1"
.\unified_guardian_scheduler.ps1
```

**Bash (Git Bash / WSL) :**

```bash
AUTO_COMMIT=1 bash sync_all.sh
```

---

## Documentation

### Guides disponibles

| Document | Description |
|----------|-------------|
| [AUTO_COMMIT_GUIDE.md](AUTO_COMMIT_GUIDE.md) | Guide détaillé complet avec exemples et meilleures pratiques |
| [AUTO_COMMIT_ACTIVATION.md](AUTO_COMMIT_ACTIVATION.md) | Guide d'activation rapide avec commandes essentielles |
| [AUTO_COMMIT_README.md](AUTO_COMMIT_README.md) | Ce fichier - Vue d'ensemble et index |

### Scripts disponibles

| Script | Description |
|--------|-------------|
| [quick_enable_auto_commit.ps1](scripts/quick_enable_auto_commit.ps1) | Activation en un clic avec interface guidée |
| [enable_auto_commit.ps1](scripts/enable_auto_commit.ps1) | Configuration de la variable d'environnement système |
| [setup_unified_scheduler.ps1](scripts/setup_unified_scheduler.ps1) | Configuration de la tâche planifiée avec option `-EnableAutoCommit` |

---

## Vérification de l'état

### Vérifier si AUTO_COMMIT est activé

```powershell
# Variables d'environnement
Write-Host "User:    $([Environment]::GetEnvironmentVariable('AUTO_COMMIT', 'User'))"
Write-Host "Machine: $([Environment]::GetEnvironmentVariable('AUTO_COMMIT', 'Machine'))"
Write-Host "Session: $env:AUTO_COMMIT"

# Tâche planifiée
Get-ScheduledTask -TaskName "EmergenceUnifiedGuardian" |
    Select-Object TaskName, State, Description |
    Format-List
```

### Vérifier les commits automatiques

```bash
# Voir tous les commits automatiques
git log --all --grep="chore(sync)" --oneline

# Voir le dernier commit auto avec détails
git log --grep="chore(sync)" -n 1 --stat
```

---

## Comportement avec AUTO_COMMIT

Lorsque `AUTO_COMMIT=1` est activé, le workflow devient :

```
1. Exécution des agents Guardian
   ↓
2. Détection des changements (git status)
   ↓
3. Commit automatique (sans confirmation)
   Message: "chore(sync): mise à jour automatique - agents ÉMERGENCE [timestamp]"
   ↓
4. Push vers GitHub (origin/main)
   ↓
5. Push vers Codex Cloud (codex/main) [si configuré]
   ↓
6. Génération du rapport final
```

### Fichiers committés

- ✅ Rapports générés par les agents
- ✅ Documentation mise à jour
- ✅ Fichiers de configuration modifiés
- ✅ Logs de synchronisation

### Fichiers exclus (jamais committés)

- ❌ `.env` - Variables d'environnement
- ❌ `credentials.json` - Identifiants
- ❌ `*.key` - Clés privées
- ❌ `secrets/*` - Tout le répertoire secrets

---

## Options Combinées

### AUTO_COMMIT + SKIP_PUSH

Committer localement sans pousser vers les dépôts distants :

```bash
AUTO_COMMIT=1 SKIP_PUSH=1 bash sync_all.sh
```

### AUTO_COMMIT + AUTO_APPLY

Activer à la fois le commit ET l'application automatique des correctifs :

```bash
AUTO_COMMIT=1 AUTO_APPLY=1 bash sync_all.sh
```

---

## Désactivation

### Désactiver temporairement

```powershell
# PowerShell
Remove-Item Env:\AUTO_COMMIT

# Bash
unset AUTO_COMMIT
```

### Désactiver définitivement

```powershell
# Variable d'environnement système
.\enable_auto_commit.ps1 -Disable

# Variable d'environnement utilisateur
.\enable_auto_commit.ps1 -UserLevel -Disable

# Reconfigurer la tâche planifiée SANS AUTO_COMMIT
.\setup_unified_scheduler.ps1 -Force
```

---

## Dépannage

### AUTO_COMMIT ne fonctionne pas

**1. Vérifier que la variable est définie :**

```powershell
echo $env:AUTO_COMMIT
# Doit afficher : 1
```

**2. Vérifier qu'il y a des changements :**

```bash
git status
# Doit montrer des fichiers modifiés
```

**3. Consulter les logs :**

```powershell
Get-Content logs\unified_scheduler_*.log -Tail 50
```

### Les commits ne sont pas poussés

**Vérifier SKIP_PUSH :**

```powershell
echo $env:SKIP_PUSH
# Si défini, le désactiver
Remove-Item Env:\SKIP_PUSH
```

**Vérifier la configuration Git :**

```bash
# Vérifier les remotes
git remote -v

# Tester la connexion
git fetch origin
```

### La tâche planifiée échoue

**1. Voir les détails de la tâche :**

```powershell
Get-ScheduledTaskInfo -TaskName "EmergenceUnifiedGuardian"
```

**2. Exécuter manuellement pour déboguer :**

```powershell
cd C:\dev\emergenceV8
$env:AUTO_COMMIT = "1"
.\claude-plugins\integrity-docs-guardian\scripts\unified_guardian_scheduler.ps1 -Verbose
```

**3. Vérifier l'historique d'exécution :**

```powershell
Get-WinEvent -FilterHashtable @{
    LogName='Microsoft-Windows-TaskScheduler/Operational'
    ID=102
} -MaxEvents 10 | Where-Object { $_.Message -like "*EmergenceUnifiedGuardian*" }
```

---

## Meilleures Pratiques

### ✅ À FAIRE

1. **Tester en mode manuel** avant d'activer AUTO_COMMIT
2. **Surveiller les premiers commits** pour valider le comportement
3. **Vérifier l'historique Git** régulièrement
4. **Garder une sauvegarde** avant activation complète
5. **Utiliser SKIP_PUSH=1** pour les tests initiaux

### ❌ À ÉVITER

1. **Activer sans tester** en environnement de production
2. **Ignorer les logs** et les alertes
3. **Désactiver les hooks Git** (pre-commit, post-commit)
4. **Committer du code non testé** automatiquement
5. **Oublier de vérifier** les rapports des agents

---

## Sécurité

### Protections intégrées

- 🔒 **Fichiers sensibles exclus** - `.env`, `credentials.json` jamais committés
- 🔒 **Hooks Git respectés** - pre-commit et post-commit toujours exécutés
- 🔒 **Traçabilité complète** - Tous les commits automatiques sont identifiés
- 🔒 **Rollback possible** - `git revert` fonctionne normalement
- 🔒 **Validation avant push** - Les agents vérifient l'intégrité avant de pousser

### Recommandations

1. **Configurer `.gitignore`** correctement
2. **Activer les hooks Git** de validation
3. **Surveiller les alertes** des agents
4. **Audit régulier** de l'historique Git
5. **Backup quotidien** du dépôt

---

## Monitoring

### Logs disponibles

```
claude-plugins/integrity-docs-guardian/
├── logs/
│   ├── unified_scheduler_2025-10.log
│   └── orchestrator.log
└── reports/
    ├── global_report.json
    ├── docs_report.json
    ├── integrity_report.json
    └── prod_report.json
```

### Commandes de monitoring

```powershell
# Logs du scheduler
Get-Content logs\unified_scheduler_*.log -Tail 100 -Wait

# Commits automatiques récents
git log --grep="chore(sync)" --since="1 day ago" --oneline

# État de la tâche planifiée
Get-ScheduledTask -TaskName "EmergenceUnifiedGuardian" |
    Get-ScheduledTaskInfo |
    Format-List
```

---

## Support et Documentation

### Liens utiles

- [AUTOMATION_GUIDE.md](AUTOMATION_GUIDE.md) - Guide d'automatisation global
- [GUARDIAN_SETUP_COMPLETE.md](../../GUARDIAN_SETUP_COMPLETE.md) - Configuration complète Guardian
- [QUICKSTART.md](QUICKSTART.md) - Démarrage rapide
- [AGENTS.md](../../AGENTS.md) - Documentation des agents

### Commandes slash disponibles

```bash
/sync_all          # Orchestration complète
/check_docs        # Anima uniquement
/check_integrity   # Neo uniquement
/check_prod        # ProdGuardian uniquement
/guardian_report   # Rapport unifié
/audit_agents      # Audit système complet
```

---

## Exemples d'usage

### Scénario 1 : Test initial

```powershell
# 1. Activer temporairement
$env:AUTO_COMMIT = "1"
$env:SKIP_PUSH = "1"

# 2. Tester
.\unified_guardian_scheduler.ps1 -Verbose

# 3. Vérifier le commit
git log -1

# 4. Si OK, push manuel
git push origin main
```

### Scénario 2 : Production complète

```powershell
# 1. Configurer la tâche planifiée avec AUTO_COMMIT
.\quick_enable_auto_commit.ps1

# 2. Vérifier immédiatement
Start-ScheduledTask -TaskName "EmergenceUnifiedGuardian"

# 3. Surveiller les logs
Get-Content ..\logs\unified_scheduler_*.log -Tail 50 -Wait
```

### Scénario 3 : Désactivation urgente

```powershell
# 1. Arrêter la tâche
Stop-ScheduledTask -TaskName "EmergenceUnifiedGuardian"

# 2. Désactiver la tâche
Disable-ScheduledTask -TaskName "EmergenceUnifiedGuardian"

# 3. Supprimer la variable
Remove-Item Env:\AUTO_COMMIT
.\enable_auto_commit.ps1 -Disable
```

---

## Changelog

### Version 1.0.0 (2025-10-17)

- ✨ Ajout du support AUTO_COMMIT dans unified_guardian_scheduler.ps1
- ✨ Création du script enable_auto_commit.ps1
- ✨ Création du script quick_enable_auto_commit.ps1
- ✨ Ajout de l'option -EnableAutoCommit dans setup_unified_scheduler.ps1
- 📚 Documentation complète (3 guides)
- ✅ Tests et validation

---

**Version :** 1.0.0
**Date :** 2025-10-17
**Maintenu par :** Équipe ÉMERGENCE

Pour toute question, consultez la documentation ou les logs du système.
