# Guide d'activation du commit automatique pour les agents Guardian

Ce guide explique comment activer le commit automatique pour les agents Guardian du système ÉMERGENCE.

## Qu'est-ce que le commit automatique ?

Lorsque le commit automatique est activé (`AUTO_COMMIT=1`), les agents Guardian peuvent automatiquement committer les changements détectés sans demander confirmation à l'utilisateur. Cela est particulièrement utile pour :

- Les exécutions planifiées (Task Scheduler)
- L'automatisation complète du workflow
- Les mises à jour de documentation automatiques
- La synchronisation continue

## ⚠️ Avertissement

Le commit automatique doit être utilisé avec précaution car il modifie automatiquement le dépôt Git sans intervention manuelle. Assurez-vous de :

- Avoir une bonne sauvegarde de votre code
- Comprendre les changements que les agents peuvent effectuer
- Vérifier régulièrement l'historique Git

## Méthodes d'activation

### Méthode 1 : Activation ponctuelle (recommandé pour tester)

Pour une exécution unique avec commit automatique :

```powershell
# PowerShell
$env:AUTO_COMMIT = "1"
.\claude-plugins\integrity-docs-guardian\scripts\unified_guardian_scheduler.ps1
```

```bash
# Bash (Git Bash, WSL)
AUTO_COMMIT=1 bash claude-plugins/integrity-docs-guardian/scripts/sync_all.sh
```

### Méthode 2 : Configuration permanente au niveau utilisateur

Exécuter le script de configuration :

```powershell
# Activer pour l'utilisateur courant
powershell -ExecutionPolicy Bypass -File .\claude-plugins\integrity-docs-guardian\scripts\enable_auto_commit.ps1 -UserLevel

# Puis, pour cette session actuelle
$env:AUTO_COMMIT = "1"
```

### Méthode 3 : Configuration permanente au niveau système (nécessite admin)

```powershell
# Activer pour tous les utilisateurs (nécessite PowerShell en admin)
powershell -ExecutionPolicy Bypass -File .\claude-plugins\integrity-docs-guardian\scripts\enable_auto_commit.ps1

# Puis, pour cette session actuelle
$env:AUTO_COMMIT = "1"
```

### Méthode 4 : Configuration dans le Task Scheduler

Pour configurer une tâche planifiée avec AUTO_COMMIT :

1. Ouvrir le **Task Scheduler** Windows
2. Trouver la tâche **"ÉMERGENCE - Unified Guardian Scheduler"**
3. Faire un clic droit → **Propriétés**
4. Aller dans l'onglet **Actions**
5. Modifier l'action existante
6. Dans **Programme/script**, cliquer sur **Ajouter** pour créer un wrapper

Ou utiliser le script de configuration :

```powershell
# Re-créer la tâche planifiée avec AUTO_COMMIT activé
cd claude-plugins\integrity-docs-guardian\scripts

# Éditer setup_unified_scheduler.ps1 pour ajouter AUTO_COMMIT=1
# Puis exécuter :
.\setup_unified_scheduler.ps1
```

## Vérification de l'état

Pour vérifier si AUTO_COMMIT est activé :

```powershell
# Dans PowerShell
Write-Host "AUTO_COMMIT (User):    $([Environment]::GetEnvironmentVariable('AUTO_COMMIT', 'User'))"
Write-Host "AUTO_COMMIT (Machine): $([Environment]::GetEnvironmentVariable('AUTO_COMMIT', 'Machine'))"
Write-Host "AUTO_COMMIT (Process): $env:AUTO_COMMIT"
```

```bash
# Dans Bash
echo "AUTO_COMMIT: $AUTO_COMMIT"
```

## Désactivation

### Temporaire (session actuelle)

```powershell
# PowerShell
Remove-Item Env:\AUTO_COMMIT
```

```bash
# Bash
unset AUTO_COMMIT
```

### Permanente

```powershell
# Désactiver au niveau utilisateur
powershell -ExecutionPolicy Bypass -File .\claude-plugins\integrity-docs-guardian\scripts\enable_auto_commit.ps1 -UserLevel -Disable

# Désactiver au niveau système (nécessite admin)
powershell -ExecutionPolicy Bypass -File .\claude-plugins\integrity-docs-guardian\scripts\enable_auto_commit.ps1 -Disable
```

## Comportement des agents avec AUTO_COMMIT=1

Lorsque `AUTO_COMMIT=1` est défini, le script [sync_all.sh](scripts/sync_all.sh) :

1. **Exécute tous les agents** (Anima, Neo, ProdGuardian)
2. **Fusionne les rapports** et identifie les problèmes
3. **Détecte les modifications** dans le dépôt Git
4. **Committe automatiquement** avec un message descriptif :
   ```
   chore(sync): mise à jour automatique - agents ÉMERGENCE 2025-10-17_14:30:45
   ```
5. **Push vers GitHub** et Codex Cloud (sauf si `SKIP_PUSH=1`)

## Workflow recommandé

### Pour le développement

```bash
# Sans commit automatique (mode manuel)
bash claude-plugins/integrity-docs-guardian/scripts/sync_all.sh

# Examiner les changements proposés
git status
git diff

# Committer manuellement si souhaité
git add .
git commit -m "votre message personnalisé"
```

### Pour l'automatisation

```bash
# Avec commit automatique (pour tâches planifiées)
AUTO_COMMIT=1 bash claude-plugins/integrity-docs-guardian/scripts/sync_all.sh
```

## Combinaisons avec d'autres options

### AUTO_COMMIT avec SKIP_PUSH

Committer automatiquement mais ne pas pousser vers les dépôts distants :

```bash
AUTO_COMMIT=1 SKIP_PUSH=1 bash claude-plugins/integrity-docs-guardian/scripts/sync_all.sh
```

### AUTO_COMMIT avec AUTO_APPLY (AutoSync)

Activer à la fois le commit automatique ET l'application automatique des correctifs :

```bash
AUTO_COMMIT=1 AUTO_APPLY=1 bash claude-plugins/integrity-docs-guardian/scripts/sync_all.sh
```

## Dépannage

### Le commit automatique ne fonctionne pas

1. Vérifier que la variable est bien définie :
   ```powershell
   echo $env:AUTO_COMMIT  # PowerShell
   echo $AUTO_COMMIT      # Bash
   ```

2. Vérifier qu'il y a des changements à committer :
   ```bash
   git status
   ```

3. Vérifier les logs du scheduler :
   ```powershell
   Get-Content claude-plugins\integrity-docs-guardian\logs\unified_scheduler_*.log -Tail 50
   ```

### Les commits ne sont pas poussés vers GitHub

Vérifier que `SKIP_PUSH` n'est pas défini :
```bash
unset SKIP_PUSH        # Bash
Remove-Item Env:\SKIP_PUSH  # PowerShell
```

## Logs et audit

Tous les commits automatiques sont enregistrés dans :

- **Logs du scheduler** : `claude-plugins/integrity-docs-guardian/logs/unified_scheduler_*.log`
- **Rapports** : `claude-plugins/integrity-docs-guardian/reports/`
- **Historique Git** : `git log --all --oneline --graph`

Pour auditer les commits automatiques :

```bash
# Voir tous les commits automatiques
git log --all --grep="chore(sync)" --oneline

# Voir le dernier commit automatique
git log --grep="chore(sync)" -n 1 --stat
```

## Meilleures pratiques

1. **Tester d'abord en mode manuel** avant d'activer le commit automatique
2. **Surveiller les premiers commits automatiques** pour valider le comportement
3. **Vérifier régulièrement l'historique Git** pour détecter tout problème
4. **Utiliser des branches** pour les changements majeurs (les agents créent automatiquement des branches `fix/auto-*` pour les correctifs critiques)
5. **Garder une sauvegarde** avant d'activer l'automatisation complète

## Sécurité

- Les agents ne committent jamais de fichiers sensibles (`.env`, `credentials.json`, etc.)
- Les hooks Git (pre-commit, post-commit) sont toujours exécutés
- Tous les changements sont traçables via l'historique Git
- Les correctifs critiques nécessitent une validation manuelle (non inclus dans AUTO_COMMIT)

## Commandes rapides

```bash
# Activer pour cette session
export AUTO_COMMIT=1                    # Bash
$env:AUTO_COMMIT = "1"                  # PowerShell

# Exécuter avec auto-commit
AUTO_COMMIT=1 bash scripts/sync_all.sh  # Bash

# Désactiver pour cette session
unset AUTO_COMMIT                       # Bash
Remove-Item Env:\AUTO_COMMIT            # PowerShell

# Vérifier l'état
echo $AUTO_COMMIT                       # Bash
echo $env:AUTO_COMMIT                   # PowerShell
```

---

**Version :** 1.0.0
**Date :** 2025-10-17
**Maintenu par :** Équipe ÉMERGENCE
