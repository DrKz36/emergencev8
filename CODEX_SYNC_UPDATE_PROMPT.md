# Prompt pour Codex : Mise à Jour Documentation Post-Merge

## 🎯 Contexte et Problème Identifié

### Situation Actuelle
Le repo `DrKz36/emergencev8` utilise un workflow de PR avec **squash merge**, ce qui a causé une confusion lors de la synchronisation post-merge.

**Ce qui s'est passé** :
1. Session 2025-10-05 : Travail sur branche `fix/debate-chat-ws-events-20250915-1808`
   - 3 commits créés : `86358ec`, `bed7c79`, `b2353eb`
   - Commits pushés sur `origin/fix/debate-chat-ws-events-20250915-1808`
   - PR créée manuellement via GitHub UI

2. Merge PR via GitHub :
   - **Squash merge** effectué → tous les commits fusionnés en 1 seul commit `b8fb37b`
   - Titre commit : "fix: align websocket session alias handling (#4)"
   - La branche distante `origin/fix/debate-chat-ws-events-20250915-1808` **reste présente** après merge

3. Synchronisation locale :
   - `git checkout main` + `git pull` → OK
   - Les fichiers de notre session sont bien présents dans `main`
   - MAIS les commits individuels (`86358ec`, `bed7c79`, `b2353eb`) n'apparaissent pas dans `git log main`
   - Ils sont "écrasés" dans le squash merge `b8fb37b`

### Le Piège du Squash Merge

```bash
# Avant merge (branche feature)
* b2353eb docs: add detailed session handoff notes
* bed7c79 docs: add review/passation notes for branch
* 86358ec docs: add ws:error matrix and integration tests
* 9119e0a fix: tighten opinion dedupe flow

# Après squash merge (main)
* b8fb37b fix: align websocket session alias handling (#4)  ← contient TOUS les commits précédents
* 198c524 Merge pull request #3
```

**Résultat** :
- ✅ Les **fichiers** sont bien dans `main`
- ❌ Les **commits individuels** disparaissent de l'historique `main`
- ⚠️ La branche feature reste sur remote (pollution potentielle)

## 📋 Problèmes à Documenter

### 1. Workflow Git Non Documenté
**Localisation** : `docs/workflow-sync.md` (existe déjà, mais incomplet)

**Manque** :
- Aucune mention du squash merge
- Pas de procédure post-merge (nettoyage branche, vérification sync)
- Pas d'explication sur la disparition des commits individuels

### 2. Procédure Sync Workdir Incomplète
**Localisation** : `scripts/sync-workdir.ps1` + documentation associée

**Manque** :
- Ne gère pas le cas "branche mergée en squash"
- Pas de détection automatique si une branche locale correspond à une PR mergée
- Pas de nettoyage des branches obsolètes

### 3. Instructions PR Manquantes
**Localisation** : `.github/pull_request_template.md` (existe)

**Manque** :
- Aucune instruction sur le type de merge (squash vs merge commit vs rebase)
- Pas de checklist post-merge
- Pas d'instructions pour nettoyer la branche après merge

### 4. Onboarding Dev Incomplet
**Localisation** : `README.md` ou `CONTRIBUTING.md` (à vérifier/créer)

**Manque** :
- Workflow Git complet du projet
- Bonnes pratiques PR (commits, merge, cleanup)
- Gestion des branches (naming, lifecycle, deletion)

## 🔧 Actions Requises

### Action 1 : Mettre à Jour `docs/workflow-sync.md`

**Ajouter une section** : "Post-Merge Workflow (Squash)"

```markdown
## Post-Merge Workflow (Squash Merge)

### Comprendre le Squash Merge

Ce projet utilise le **squash merge** pour les PRs. Cela signifie que :
- Tous vos commits de branche sont fusionnés en **1 seul commit** dans `main`
- Les commits individuels **disparaissent** de l'historique `main`
- Vos fichiers sont bien présents, mais sous un nouveau commit SHA

**Exemple** :
```bash
# Votre branche
* abc123 docs: add feature X
* def456 tests: add test for X
* ghi789 fix: typo in X

# Après squash merge dans main
* xyz000 feat: implement feature X (#42)  ← contient abc123 + def456 + ghi789
```

### Synchronisation Post-Merge

**Étape 1 : Vérifier que la PR est mergée**
```bash
# Sur GitHub, vérifier que la PR affiche "Merged" (violet)
# Noter le numéro de PR (ex: #42)
```

**Étape 2 : Passer sur main local**
```bash
git checkout main
git pull origin main
```

**Étape 3 : Vérifier la présence de vos fichiers**
```bash
# Chercher vos fichiers/commits dans l'historique
git log --all --oneline --grep="votre-feature" -i
git show HEAD --name-only | grep "votre-fichier"

# Vérifier que vos fichiers existent
ls -la path/to/your/new/file.md
```

**Étape 4 : Nettoyer la branche feature**
```bash
# Supprimer la branche locale
git branch -d fix/your-feature-branch

# Supprimer la branche distante (importante!)
git push origin --delete fix/your-feature-branch
```

**Étape 5 : Vérifier l'état propre**
```bash
git status  # Doit afficher "working tree clean"
git branch -a | grep fix/  # Ne doit plus lister votre branche
```

### ⚠️ Pièges Courants

**1. "Mes commits ont disparu !"**
- Normal avec squash merge
- Vérifiez que vos **fichiers** sont présents, pas les commits individuels
- Cherchez le commit de merge avec `git log --grep="PR-title"`

**2. "La branche distante existe encore"**
- Le squash merge ne supprime PAS automatiquement la branche
- Supprimez-la manuellement : `git push origin --delete branch-name`

**3. "Git dit que je suis en avance/retard"**
- Si vous êtes sur l'ancienne branche feature, normal
- Passez sur `main` : `git checkout main && git pull`
```

### Action 2 : Créer `docs/git-workflow.md`

**Nouveau fichier** complet sur le workflow Git du projet :

```markdown
# Git Workflow - Émergence V8

## Vue d'Ensemble

Ce projet utilise un workflow **feature branch + squash merge** :
1. Créer une branche feature depuis `main`
2. Développer + commits atomiques
3. Push + créer PR sur GitHub
4. Review + merge squash dans `main`
5. Nettoyer la branche feature

## 1. Créer une Feature Branch

```bash
# Toujours partir de main à jour
git checkout main
git pull origin main

# Créer et basculer sur la nouvelle branche
git checkout -b fix/descriptive-name-YYYYMMDD-HHMM
# Exemple: fix/debate-chat-ws-events-20250915-1808
```

**Convention de nommage** :
- `fix/` : corrections de bugs
- `feat/` : nouvelles fonctionnalités
- `docs/` : documentation uniquement
- `chore/` : maintenance, refactoring

## 2. Développer et Commiter

```bash
# Commits atomiques et descriptifs
git add path/to/file.py
git commit -m "fix: correct websocket error handling

- Add error code to ws:error payload
- Route opinion_already_exists to toast
- Add integration tests for duplicate detection"

# Convention commits:
# type: short description (50 chars max)
#
# - Bullet points for details
# - Explain WHY, not just WHAT
```

**Types de commits** :
- `fix:` - correction de bug
- `feat:` - nouvelle feature
- `docs:` - documentation
- `test:` - ajout/modification tests
- `refactor:` - refactoring sans changement fonctionnel
- `chore:` - tâches maintenance

## 3. Push et Créer PR

```bash
# Premier push (créer la branche remote)
git push -u origin fix/your-branch-name

# Pushs suivants
git push
```

**Créer la PR** :
1. Aller sur GitHub → Compare & Pull Request
2. Base : `main` ← Head : `fix/your-branch`
3. Titre explicite (reprendre le commit principal)
4. Description détaillée (utiliser template `.github/pull_request_template.md`)
5. Assigner reviewers si nécessaire

## 4. Review et Merge

**Pendant la review** :
```bash
# Commits de correction suite à review
git add .
git commit -m "fix: address review comments"
git push
```

**Merge (maintainer uniquement)** :
- Sur GitHub : bouton "Squash and merge"
- Le titre du squash commit = titre de la PR
- Tous vos commits → 1 seul commit dans `main`

## 5. Post-Merge : Synchronisation

**Immédiatement après merge** :

```bash
# 1. Passer sur main
git checkout main

# 2. Récupérer le squash commit
git pull origin main

# 3. Vérifier que vos fichiers sont présents
ls -la path/to/your/files
git log -1 --stat  # Voir le dernier commit (squash merge)

# 4. Supprimer la branche locale
git branch -d fix/your-branch-name

# 5. Supprimer la branche distante
git push origin --delete fix/your-branch-name

# 6. Vérifier l'état propre
git status  # "working tree clean"
git branch -a  # Votre branche ne doit plus apparaître
```

## 6. Troubleshooting

### "Mes commits ont disparu de main"
**Normal avec squash merge !**
- Vos commits individuels sont fusionnés en 1 seul
- Vérifiez la présence de vos **fichiers**, pas des commits
- Cherchez le commit de merge : `git log --grep="PR-title"`

### "La branche distante existe encore après merge"
**Squash merge ne supprime pas auto la branche**
```bash
git push origin --delete fix/branch-name
```

### "Working tree not clean après sync"
**Vérifier les fichiers non suivis** :
```bash
git status
# Si modifications cosmétiques (EOL), ignorer ou :
git restore path/to/file
# Si nouveaux fichiers utiles :
git add . && git commit -m "..."
```

### "Conflit lors du pull"
```bash
# Stasher vos changements locaux
git stash push -m "local changes before pull"
git pull origin main
git stash pop  # Résoudre conflits si nécessaire
```

## 7. Bonnes Pratiques

✅ **À FAIRE** :
- Toujours partir de `main` à jour
- Commits atomiques et descriptifs
- Tests verts avant PR
- Review du diff avant merge
- Nettoyer les branches après merge
- Documenter les changements complexes

❌ **À ÉVITER** :
- Commits "WIP" ou "fix" sans contexte
- Push force sur `main`
- Merge sans review (sauf hotfix critique)
- Laisser des branches mortes sur remote
- Oublier de pull `main` avant nouvelle branche

## 8. Cas Spécial : Hotfix Production

```bash
# Partir de main
git checkout main && git pull

# Branche hotfix
git checkout -b hotfix/critical-bug-description

# Fix + commit + push
git add . && git commit -m "hotfix: fix critical bug X"
git push -u origin hotfix/critical-bug-description

# PR immédiate + review rapide + merge
# Puis nettoyage standard
```

## Références

- [Convention Commits](https://www.conventionalcommits.org/)
- [GitHub Flow](https://guides.github.com/introduction/flow/)
- [Pull Request Template](.github/pull_request_template.md)
- [Sync Workflow](docs/workflow-sync.md)
```

### Action 3 : Mettre à Jour `.github/pull_request_template.md`

**Ajouter une section** "Post-Merge Checklist" :

```markdown
---

## 📦 Post-Merge Checklist (Auteur)

**À faire IMMÉDIATEMENT après merge** :

- [ ] Vérifier que GitHub affiche "Merged" (étiquette violette)
- [ ] Synchroniser `main` local : `git checkout main && git pull`
- [ ] Vérifier présence des fichiers : `ls -la <nouveaux-fichiers>`
- [ ] Supprimer branche locale : `git branch -d <branch-name>`
- [ ] Supprimer branche distante : `git push origin --delete <branch-name>`
- [ ] Vérifier état propre : `git status` (working tree clean)
- [ ] Vérifier absence branche : `git branch -a | grep <branch>`

**Note** : Ce projet utilise **squash merge**. Vos commits individuels seront fusionnés en 1 seul commit dans `main`. C'est normal si vous ne voyez plus vos commits originaux dans `git log main`.

**Documentation** : [Git Workflow](docs/git-workflow.md) | [Sync Workflow](docs/workflow-sync.md)
```

### Action 4 : Améliorer `scripts/sync-workdir.ps1`

**Ajouter une fonction** de détection de branches mergées :

```powershell
function Test-BranchMerged {
    param(
        [string]$BranchName,
        [string]$BaseBranch = "main"
    )

    # Vérifier si la branche existe sur remote
    $remoteBranches = git branch -r | Select-String "origin/$BranchName"
    if (-not $remoteBranches) {
        Write-Host "✓ Branche $BranchName n'existe pas sur remote" -ForegroundColor Green
        return $true
    }

    # Vérifier si les commits de la branche sont dans main (via diff)
    git fetch origin --quiet
    $diff = git rev-list "origin/$BaseBranch..origin/$BranchName" 2>$null

    if (-not $diff) {
        Write-Warning "⚠ Branche $BranchName semble mergée mais existe encore sur remote"
        Write-Host "Supprimer avec: git push origin --delete $BranchName" -ForegroundColor Yellow
        return $true
    }

    return $false
}

# Utilisation dans le script principal
Write-Host "`n🔍 Vérification des branches mergées..." -ForegroundColor Cyan

$currentBranch = git branch --show-current
if ($currentBranch -ne "main") {
    if (Test-BranchMerged -BranchName $currentBranch) {
        Write-Warning "La branche courante '$currentBranch' semble mergée dans main"
        $switch = Read-Host "Basculer sur main et nettoyer? (y/N)"
        if ($switch -eq "y") {
            git checkout main
            git pull origin main
            git branch -d $currentBranch
            git push origin --delete $currentBranch 2>$null
            Write-Host "✓ Branche nettoyée" -ForegroundColor Green
        }
    }
}
```

### Action 5 : Créer `CONTRIBUTING.md` (si n'existe pas)

**Nouveau fichier** avec section Git :

```markdown
# Guide de Contribution - Émergence V8

## Workflow Git

Ce projet utilise un workflow **feature branch + squash merge** :

1. **Créer une branche** depuis `main` à jour
2. **Développer** avec commits atomiques
3. **Push** et créer une Pull Request
4. **Review** par les mainteneurs
5. **Merge squash** dans `main` (1 seul commit)
6. **Nettoyer** la branche feature (local + remote)

**Documentation complète** : [Git Workflow](docs/git-workflow.md)

### Quick Start

```bash
# Nouvelle feature
git checkout main && git pull
git checkout -b feat/my-feature-$(date +%Y%m%d-%H%M)

# Développer + commit
git add . && git commit -m "feat: add feature X"
git push -u origin feat/my-feature-*

# Créer PR sur GitHub
# Après merge:
git checkout main && git pull
git branch -d feat/my-feature-*
git push origin --delete feat/my-feature-*
```

### ⚠️ Important : Squash Merge

**Vos commits individuels disparaîtront de `main`**. C'est normal ! Le squash merge fusionne tous vos commits en un seul. Vérifiez la présence de vos **fichiers**, pas des commits.

**Exemple** :
- Votre branche : 3 commits (`abc`, `def`, `ghi`)
- Après merge : 1 commit dans `main` (`xyz`) qui contient tout

Voir [Git Workflow - Squash Merge](docs/git-workflow.md#comprendre-le-squash-merge)

## Autres Sections...
(tests, style code, etc.)
```

### Action 6 : Ajouter Note dans `README.md`

**Dans la section "Development" ou "Contributing"** :

```markdown
## 🔄 Workflow Git

Ce projet utilise **squash merge** pour les PRs. Points importants :

- ✅ Créer une branche feature depuis `main`
- ✅ Développer avec commits atomiques
- ✅ PR → Review → Squash merge
- ⚠️ Vos commits individuels sont fusionnés en 1 seul dans `main`
- 🧹 Nettoyer la branche après merge (local + remote)

**Documentation** : [Git Workflow](docs/git-workflow.md) | [Contributing](CONTRIBUTING.md)

### Quick Reference

```bash
# Post-merge cleanup
git checkout main && git pull
git branch -d feat/my-branch
git push origin --delete feat/my-branch
```
```

## 🎯 Ta Mission (Codex)

### Étapes à Suivre

1. **Lire les fichiers existants** pour éviter les doublons :
   - `docs/workflow-sync.md`
   - `.github/pull_request_template.md`
   - `README.md`
   - `scripts/sync-workdir.ps1`
   - Vérifier si `CONTRIBUTING.md` existe

2. **Créer/Mettre à jour les fichiers** selon les actions ci-dessus :
   - Mettre à jour `docs/workflow-sync.md` (ajouter section squash merge)
   - Créer `docs/git-workflow.md` (nouveau fichier complet)
   - Mettre à jour `.github/pull_request_template.md` (ajouter checklist post-merge)
   - Améliorer `scripts/sync-workdir.ps1` (ajouter fonction `Test-BranchMerged`)
   - Créer `CONTRIBUTING.md` si absent (ou mettre à jour si existe)
   - Ajouter note dans `README.md` (section Development/Contributing)

3. **Éviter les erreurs futures** :
   - Documenter clairement que **squash merge = commits individuels écrasés**
   - Expliquer que **vérifier les fichiers, pas les commits**
   - Ajouter checklist post-merge systématique
   - Automatiser la détection de branches mergées

4. **Créer un commit** avec les changements :
   ```bash
   git add docs/ .github/ scripts/ README.md CONTRIBUTING.md
   git commit -m "docs: document squash merge workflow and post-merge cleanup

   - Add comprehensive Git workflow documentation (docs/git-workflow.md)
   - Update workflow-sync.md with squash merge explanations
   - Add post-merge checklist to PR template
   - Enhance sync-workdir.ps1 with merged branch detection
   - Add Git workflow quick reference to README
   - Create/update CONTRIBUTING.md with squash merge notes

   Prevents confusion when commits disappear after squash merge.
   Establishes clear post-merge cleanup procedures.

   🤖 Generated with [Claude Code](https://claude.com/claude-code)

   Co-Authored-By: Claude <noreply@anthropic.com>"
   ```

## 📋 Checklist de Validation

Avant de créer le commit, vérifie :

- [ ] `docs/git-workflow.md` créé avec toutes les sections (workflow complet, squash merge, troubleshooting)
- [ ] `docs/workflow-sync.md` mis à jour avec section "Post-Merge Workflow (Squash)"
- [ ] `.github/pull_request_template.md` contient "Post-Merge Checklist"
- [ ] `scripts/sync-workdir.ps1` a la fonction `Test-BranchMerged`
- [ ] `CONTRIBUTING.md` créé/mis à jour avec section Git
- [ ] `README.md` a une note sur le workflow squash merge
- [ ] Tous les fichiers mentionnent que **squash merge écrase les commits individuels**
- [ ] Toutes les docs pointent vers `docs/git-workflow.md` pour référence complète
- [ ] Checklist post-merge présente dans au moins 2 endroits (PR template + git-workflow.md)

## 🔗 Références

**Contexte session** :
- Session 2025-10-05 : Travail opinion flow + tests intégration
- PR #4 (squash merge) : commit `b8fb37b`
- Commits originaux : `86358ec`, `bed7c79`, `b2353eb` (écrasés dans squash)
- Rapport sync : [SYNC_REPORT.md](SYNC_REPORT.md)

**Fichiers existants à vérifier** :
- `docs/workflow-sync.md` - workflow actuel (incomplet)
- `.github/pull_request_template.md` - template PR (manque post-merge)
- `scripts/sync-workdir.ps1` - script sync (ne détecte pas branches mergées)
- `README.md` - docs principales (manque section Git workflow)

**Nouveaux fichiers à créer** :
- `docs/git-workflow.md` - documentation complète Git
- `CONTRIBUTING.md` - guide contribution (si absent)

---

**Prompt créé** : 2025-10-05
**Contexte** : Post-merge confusion (squash commits disparus)
**Objectif** : Documenter le workflow pour éviter erreurs futures
**Outil** : Claude Code

Merci de mettre à jour toute la documentation ! 🚀
