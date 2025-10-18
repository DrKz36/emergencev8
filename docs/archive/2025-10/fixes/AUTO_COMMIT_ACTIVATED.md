# ✅ Commit Automatique - Configuration Disponible

Le système de **commit automatique** pour les agents Guardian est maintenant disponible et prêt à être activé.

## 🚀 Activation en 1 Minute

### Méthode rapide (recommandée)

Ouvrir PowerShell **en tant qu'administrateur** et exécuter :

```powershell
cd C:\dev\emergenceV8\claude-plugins\integrity-docs-guardian\scripts
.\quick_enable_auto_commit.ps1
```

Ce script guidé va :
1. ✅ Vérifier les privilèges
2. ✅ Reconfigurer la tâche planifiée Windows avec AUTO_COMMIT
3. ✅ Vous proposer un test immédiat
4. ✅ Afficher les commandes utiles pour surveiller

## 📖 Documentation Complète

Toute la documentation est disponible dans :

```
claude-plugins/integrity-docs-guardian/
├── AUTO_COMMIT_README.md          ← Vue d'ensemble et index
├── AUTO_COMMIT_GUIDE.md           ← Guide détaillé complet
├── AUTO_COMMIT_ACTIVATION.md      ← Guide d'activation rapide
└── scripts/
    ├── quick_enable_auto_commit.ps1       ← Script d'activation en 1 clic
    ├── enable_auto_commit.ps1             ← Configuration variable d'environnement
    └── setup_unified_scheduler.ps1        ← Configuration Task Scheduler
```

## 🔍 Qu'est-ce que AUTO_COMMIT ?

Lorsque `AUTO_COMMIT=1` est activé, les agents Guardian :

- ✅ **Exécutent** leurs vérifications automatiquement
- ✅ **Détectent** les changements nécessaires
- ✅ **Committent** automatiquement avec un message descriptif
- ✅ **Poussent** vers GitHub et Codex Cloud

**Sans AUTO_COMMIT** (comportement par défaut) :
- Les agents génèrent des rapports
- Vous devez confirmer manuellement chaque commit

## ⚙️ Options d'activation

### 1. Task Scheduler (Production) - Recommandé

Pour une automatisation complète :

```powershell
cd claude-plugins\integrity-docs-guardian\scripts
.\setup_unified_scheduler.ps1 -Force -EnableAutoCommit
```

### 2. Variable d'environnement système

Pour activer AUTO_COMMIT de manière permanente :

```powershell
# Niveau système (tous les utilisateurs) - nécessite admin
.\enable_auto_commit.ps1

# Niveau utilisateur (utilisateur courant uniquement)
.\enable_auto_commit.ps1 -UserLevel
```

### 3. Exécution ponctuelle

Pour un test ou une exécution unique :

```powershell
# PowerShell
$env:AUTO_COMMIT = "1"
.\unified_guardian_scheduler.ps1

# Bash (Git Bash / WSL)
AUTO_COMMIT=1 bash sync_all.sh
```

## 📊 Vérification

Pour vérifier si AUTO_COMMIT est activé :

```powershell
# Vérifier les variables d'environnement
echo $env:AUTO_COMMIT

# Vérifier la tâche planifiée
Get-ScheduledTask -TaskName "EmergenceUnifiedGuardian" | Format-List Description
```

## ⚠️ Important

### Avant d'activer

- ✅ Assurez-vous d'avoir une **sauvegarde** de votre code
- ✅ **Testez** d'abord en mode manuel pour comprendre le comportement
- ✅ Vérifiez que votre **`.gitignore`** est correctement configuré

### Sécurité garantie

- 🔒 Les fichiers sensibles (`.env`, `credentials.json`) ne sont **jamais** committés
- 🔒 Tous les **hooks Git** (pre-commit, post-commit) sont **toujours exécutés**
- 🔒 Tous les commits sont **traçables** et **réversibles** (git revert)

## 🔄 Workflow avec AUTO_COMMIT

```
┌─────────────────────────────────────────┐
│  1. Task Scheduler démarre le script   │
│     (toutes les 60 minutes)             │
└─────────────────┬───────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│  2. Exécution des 3 agents Guardian     │
│     • Anima (DocKeeper)                 │
│     • Neo (IntegrityWatcher)            │
│     • ProdGuardian                      │
└─────────────────┬───────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│  3. Fusion des rapports                 │
│     → global_report.json                │
└─────────────────┬───────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│  4. Détection des changements           │
│     git status                          │
└─────────────────┬───────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│  5. Commit automatique (AUTO_COMMIT=1)  │
│     Message: "chore(sync): mise à       │
│     jour automatique - agents           │
│     ÉMERGENCE [timestamp]"              │
└─────────────────┬───────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│  6. Push vers GitHub + Codex Cloud      │
│     (sauf si SKIP_PUSH=1)               │
└─────────────────────────────────────────┘
```

## 🛑 Désactivation

Si vous souhaitez désactiver AUTO_COMMIT :

```powershell
# Désactiver la variable d'environnement
.\enable_auto_commit.ps1 -Disable

# Reconfigurer la tâche planifiée SANS AUTO_COMMIT
.\setup_unified_scheduler.ps1 -Force
```

## 📞 Besoin d'aide ?

Consultez la documentation complète :

```powershell
# Ouvrir le guide complet
code claude-plugins\integrity-docs-guardian\AUTO_COMMIT_README.md

# Ouvrir le guide détaillé
code claude-plugins\integrity-docs-guardian\AUTO_COMMIT_GUIDE.md

# Ouvrir le guide rapide
code claude-plugins\integrity-docs-guardian\AUTO_COMMIT_ACTIVATION.md
```

## 🎯 Prochaines étapes

1. **Lire** la documentation (au moins AUTO_COMMIT_ACTIVATION.md)
2. **Tester** en mode manuel avec `$env:AUTO_COMMIT = "1"`
3. **Activer** via le script `quick_enable_auto_commit.ps1`
4. **Surveiller** les premiers commits dans `git log`
5. **Vérifier** les rapports dans `claude-plugins/integrity-docs-guardian/reports/`

---

## 📦 Fichiers créés/modifiés

### Nouveaux fichiers

- ✨ `claude-plugins/integrity-docs-guardian/AUTO_COMMIT_README.md`
- ✨ `claude-plugins/integrity-docs-guardian/AUTO_COMMIT_GUIDE.md`
- ✨ `claude-plugins/integrity-docs-guardian/AUTO_COMMIT_ACTIVATION.md`
- ✨ `claude-plugins/integrity-docs-guardian/scripts/enable_auto_commit.ps1`
- ✨ `claude-plugins/integrity-docs-guardian/scripts/quick_enable_auto_commit.ps1`
- ✨ `AUTO_COMMIT_ACTIVATED.md` (ce fichier)

### Fichiers modifiés

- 🔧 `claude-plugins/integrity-docs-guardian/scripts/setup_unified_scheduler.ps1`
  - Ajout du paramètre `-EnableAutoCommit`
  - Support de la variable AUTO_COMMIT dans la tâche planifiée

- 🔧 `claude-plugins/integrity-docs-guardian/scripts/unified_guardian_scheduler.ps1`
  - Ajout de logs pour AUTO_COMMIT

---

**Date de création :** 2025-10-17
**Version :** 1.0.0
**Statut :** ✅ Prêt à l'emploi

Pour activer maintenant, exécutez :
```powershell
.\claude-plugins\integrity-docs-guardian\scripts\quick_enable_auto_commit.ps1
```
