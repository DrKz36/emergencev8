# Workflow de Synchronisation Cloud ↔ Local ↔ GitHub

## 🎯 Objectif
Permettre à GPT Codex (cloud) de travailler efficacement sans accès direct à GitHub, en utilisant l'agent local comme pont de synchronisation.

## 🔍 État Actuel

### Configuration Locale (✅ OK)
- **Machine** : `c:\dev\emergenceV8`
- **Branche** : `main`
- **Remotes configurés** :
  - `origin` (HTTPS) : `https://github.com/DrKz36/emergencev8.git`
  - `codex` (SSH) : `git@github.com:DrKz36/emergencev8.git`
- **État** : Up to date with origin/main

### Environnement Cloud GPT (⚠️ LIMITATIONS)
- **Chemin** : `/workspace/emergencev8`
- **Problèmes** :
  - ❌ Aucun remote Git configuré (`git remote -v` vide)
  - ❌ Pas d'accès réseau sortant (impossible de contacter GitHub)
  - ❌ Impossible d'ajouter un remote depuis le cloud
- **Conséquence** : Modifications restent isolées dans le cloud

## 🔄 Workflow de Synchronisation (3 Méthodes)

### Méthode 1 : Export/Import Manuel (RECOMMANDÉE - Simple)

#### Étape 1 : GPT Codex Cloud génère un patch
```bash
# Dans l'environnement cloud
git diff > /workspace/changes.patch
# OU pour tous les commits non pushés
git format-patch origin/main --stdout > /workspace/changes.patch
```

#### Étape 2 : Développeur transfère le patch localement
- Télécharger `changes.patch` depuis l'environnement cloud
- Copier dans `C:\dev\emergenceV8\`

#### Étape 3 : Agent local applique le patch
```bash
# Sur la machine locale
cd C:\dev\emergenceV8
git apply changes.patch
# OU
git am changes.patch  # Si créé avec format-patch
```

#### Étape 4 : Commit et push vers GitHub
```bash
git add -A
git commit -m "sync: intégration modifications GPT Codex cloud"
git push origin main
```

---

### Méthode 2 : Export Fichiers Modifiés (RAPIDE pour petits changements)

#### Étape 1 : GPT Codex Cloud liste les fichiers modifiés
```bash
# Dans l'environnement cloud
git status --short > /workspace/modified_files.txt
```

#### Étape 2 : Développeur copie manuellement les fichiers
- Identifier les fichiers depuis `modified_files.txt`
- Copier-coller le contenu depuis cloud → local
- OU utiliser un partage de fichiers (si disponible)

#### Étape 3 : Agent local commit et push
```bash
cd C:\dev\emergenceV8
git add <fichiers_modifiés>
git commit -m "sync: modifications depuis GPT Codex cloud"
git push origin main
```

---

### Méthode 3 : Workflow Automatisé avec Bundle (AVANCÉE)

#### Étape 1 : GPT Codex Cloud crée un bundle Git
```bash
# Dans l'environnement cloud
git bundle create /workspace/changes.bundle main
```

#### Étape 2 : Développeur transfère le bundle
- Télécharger `changes.bundle`
- Copier dans `C:\dev\emergenceV8\`

#### Étape 3 : Agent local importe et synchronise
```bash
cd C:\dev\emergenceV8
git fetch changes.bundle main:cloud-changes
git merge cloud-changes
git push origin main
git branch -d cloud-changes  # Nettoyer la branche temporaire
```

---

## 📋 Procédure Standard Recommandée

### Pour GPT Codex Cloud (Sans accès GitHub)

1. **Avant de commencer à coder** :
   ```bash
   # Vérifier l'état actuel
   git status
   git log --oneline -5
   ```

2. **Pendant le développement** :
   - Travailler normalement
   - Faire des commits locaux
   - Documenter dans `AGENT_SYNC.md` et `docs/passation.md`

3. **À la fin de la session** :
   ```bash
   # Générer un patch avec TOUS les changements
   git diff origin/main > /workspace/sync_$(date +%Y%m%d_%H%M%S).patch

   # OU si commits faits
   git format-patch origin/main --stdout > /workspace/sync_$(date +%Y%m%d_%H%M%S).patch

   # Lister les fichiers modifiés pour référence
   git status --short > /workspace/files_changed.txt
   ```

4. **Informer le développeur** :
   - Indiquer le nom du fichier patch généré
   - Résumer les modifications dans `AGENT_SYNC.md`
   - Préciser les fichiers critiques modifiés

### Pour Agent Local Claude Code (Avec accès GitHub)

1. **Réception du patch** :
   ```bash
   cd C:\dev\emergenceV8

   # Vérifier l'état avant application
   git status
   git fetch origin
   ```

2. **Application des modifications** :
   ```bash
   # Appliquer le patch
   git apply --check sync_*.patch  # Vérifier d'abord
   git apply sync_*.patch

   # OU si format-patch
   git am sync_*.patch
   ```

3. **Validation et synchronisation** :
   ```bash
   # Vérifier les modifications
   git status
   git diff

   # Tests (si applicable)
   npm run build
   pytest

   # Commit si apply (pas nécessaire si am)
   git add -A
   git commit -m "sync: intégration modifications GPT Codex cloud - [description]"

   # Push vers GitHub
   git push origin main
   ```

4. **Confirmation** :
   ```bash
   # Vérifier la synchronisation
   git log --oneline -3
   git status
   ```

---

## 🚨 Gestion des Conflits

### Si le patch ne s'applique pas
```bash
# Identifier les conflits
git apply --reject sync_*.patch

# Les rejets seront dans des fichiers *.rej
# Résoudre manuellement en comparant :
# - Fichier original
# - Fichier *.rej (modifications rejetées)
# - Contexte du patch

# Après résolution manuelle
git add <fichiers_résolus>
git commit -m "sync: résolution conflits patch cloud"
```

### Si divergence entre cloud et local
```bash
# Sur la machine locale
git log --oneline -10 > local_history.txt

# Envoyer local_history.txt à GPT Codex cloud
# GPT Codex peut rebaser ses changements si nécessaire
```

---

## 📊 Compatibilité et Désynchronisation

### Prévention de la Désynchronisation

1. **Avant chaque session GPT Codex** :
   - Agent local doit confirmer que `origin/main` est à jour
   - Partager le dernier `git log` avec GPT Codex
   - GPT Codex doit lire `AGENT_SYNC.md` et `docs/passation.md`

2. **Pendant la session GPT Codex** :
   - ❌ Ne PAS travailler simultanément (agent local + cloud)
   - ✅ Une seule session active à la fois
   - ✅ Documenter toutes les modifications dans `AGENT_SYNC.md`

3. **Après synchronisation** :
   - Agent local met à jour `AGENT_SYNC.md` avec nouveau SHA commit
   - Confirmer que GitHub et local sont alignés
   - Notifier que GPT Codex peut reprendre (si besoin)

### Vérification de Compatibilité

```bash
# Sur la machine locale (avant sync)
git log --oneline origin/main..HEAD  # Commits locaux non pushés
git log --oneline HEAD..origin/main  # Commits distants non pullés

# Après sync
git diff origin/main  # Doit être vide si sync OK
```

---

## 🛠️ Scripts d'Automatisation

### Script pour GPT Codex Cloud
**Fichier** : `/workspace/scripts/export-changes.sh`
```bash
#!/bin/bash
# Export automatique des modifications pour synchronisation

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_DIR="/workspace/sync_export"
mkdir -p "$OUTPUT_DIR"

# Générer patch
git format-patch origin/main --stdout > "$OUTPUT_DIR/changes_$TIMESTAMP.patch"

# Liste des fichiers
git status --short > "$OUTPUT_DIR/files_$TIMESTAMP.txt"

# Résumé des commits
git log origin/main..HEAD --oneline > "$OUTPUT_DIR/commits_$TIMESTAMP.txt"

echo "✅ Export créé dans $OUTPUT_DIR/"
echo "   - changes_$TIMESTAMP.patch"
echo "   - files_$TIMESTAMP.txt"
echo "   - commits_$TIMESTAMP.txt"
```

### Script pour Agent Local
**Fichier** : `C:\dev\emergenceV8\scripts\import-cloud-changes.ps1`
```powershell
# Import automatique des modifications depuis GPT Codex cloud

param(
    [Parameter(Mandatory=$true)]
    [string]$PatchFile
)

$ErrorActionPreference = "Stop"

Write-Host "🔄 Import des modifications cloud..." -ForegroundColor Cyan

# Vérifier l'état Git
Write-Host "`n📊 État actuel :" -ForegroundColor Yellow
git status

# Vérifier si working tree propre
$status = git status --porcelain
if ($status) {
    Write-Host "⚠️  Working tree non propre. Commit ou stash d'abord." -ForegroundColor Red
    exit 1
}

# Appliquer le patch
Write-Host "`n🔧 Application du patch..." -ForegroundColor Yellow
git apply --check $PatchFile
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Patch invalide. Vérifiez les conflits." -ForegroundColor Red
    exit 1
}

git apply $PatchFile
Write-Host "✅ Patch appliqué avec succès" -ForegroundColor Green

# Afficher les modifications
Write-Host "`n📝 Fichiers modifiés :" -ForegroundColor Yellow
git status --short

# Proposer le commit
Write-Host "`n💾 Prêt pour commit et push :" -ForegroundColor Cyan
Write-Host "   git add -A"
Write-Host "   git commit -m 'sync: modifications GPT Codex cloud'"
Write-Host "   git push origin main"
```

---

## 📚 Documentation de Référence

- **AGENT_SYNC.md** : État actuel du dépôt et des sessions
- **docs/passation.md** : Journal des modifications par session
- **CODEV_PROTOCOL.md** : Protocole de collaboration multi-agents

---

## ✅ Checklist de Synchronisation

### Avant Session GPT Codex
- [ ] Agent local confirme `git status` propre
- [ ] Agent local confirme `git pull origin main` à jour
- [ ] Partager dernier `git log -5` avec GPT Codex
- [ ] GPT Codex lit `AGENT_SYNC.md` et `docs/passation.md`

### Pendant Session GPT Codex
- [ ] GPT Codex documente modifications dans `AGENT_SYNC.md`
- [ ] GPT Codex ajoute entrée dans `docs/passation.md`
- [ ] Aucune session locale simultanée

### Après Session GPT Codex
- [ ] GPT Codex génère patch (`git format-patch`)
- [ ] GPT Codex liste fichiers modifiés
- [ ] Développeur télécharge patch
- [ ] Agent local applique patch (`git apply`)
- [ ] Agent local teste (build, tests)
- [ ] Agent local commit et push vers GitHub
- [ ] Agent local met à jour `AGENT_SYNC.md` (nouveau SHA)
- [ ] Confirmation synchronisation complète

---

## 🎯 Résumé : Qui Fait Quoi ?

| Agent | Responsabilités | Limitations |
|-------|----------------|-------------|
| **GPT Codex Cloud** | - Développement code<br>- Commits locaux<br>- Génération patches<br>- Documentation AGENT_SYNC.md | ❌ Pas d'accès GitHub<br>❌ Pas de remote Git<br>❌ Pas de réseau sortant |
| **Agent Local (Claude Code)** | - Application patches<br>- Tests et validation<br>- Push vers GitHub<br>- Synchronisation finale | ✅ Accès GitHub complet<br>✅ Remotes configurés<br>✅ Peut tester localement |
| **Développeur Humain** | - Transfert patches cloud→local<br>- Arbitrage conflits<br>- Validation finale | 🔧 Pont entre cloud et local |

---

**Dernière mise à jour** : 2025-10-10
**Validé par** : Claude Code (Agent Local)
