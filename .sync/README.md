# 🔄 Système de Synchronisation Multi-Agent

Infrastructure complète pour synchroniser le code entre **GPT Codex Cloud**, **GPT Codex Local** et **Claude Code (Agent Local)** via Git patches.

---

## 🎯 Vue d'Ensemble

Ce système permet aux trois agents de collaborer efficacement malgré les limitations réseau de l'environnement cloud:

```
GPT Codex Cloud (sans accès GitHub)
    ↓ [export patch]
Développeur (transfert manuel)
    ↓ [patch + métadonnées]
Claude Code Local (avec accès GitHub)
    ↓ [import + test + push]
GitHub Repository
    ↓ [pull]
GPT Codex Local (avec accès GitHub)
```

---

## 📁 Structure

```
.sync/
├── patches/          # Patches Git générés
├── logs/             # Logs d'export/import
├── scripts/          # Scripts d'automatisation
│   ├── cloud-export.sh         # Export depuis Cloud (Bash)
│   ├── cloud-export.py         # Export depuis Cloud (Python)
│   ├── local-import.sh         # Import sur Local (Bash)
│   ├── local-import.py         # Import sur Local (Python)
│   ├── sync-tracker.py         # Historique & traçabilité
│   └── validate-before-sync.py # Validation avant sync
├── templates/        # Templates de documentation
│   ├── sync-session-summary.md
│   ├── agent-handoff.md
│   └── checklist-pre-sync.md
├── sync_history.db   # Base de données SQLite (historique)
└── README.md         # Ce fichier
```

---

## 🚀 Guide Rapide

### Pour GPT Codex Cloud (Export)

**Objectif**: Générer un patch de vos modifications pour le transférer vers l'agent local.

#### Option 1: Script Bash

```bash
cd /workspace/emergencev8
bash .sync/scripts/cloud-export.sh
```

#### Option 2: Script Python (recommandé)

```bash
cd /workspace/emergencev8
python .sync/scripts/cloud-export.py
```

**Sortie**:
- Patch: `.sync/patches/sync_cloud_YYYYMMDD_HHMMSS.patch`
- Métadonnées: `.sync/patches/sync_cloud_YYYYMMDD_HHMMSS.json`
- Instructions: `.sync/patches/INSTRUCTIONS_YYYYMMDD_HHMMSS.txt`

**Prochaine étape**: Transférer le patch et les métadonnées vers la machine locale.

---

### Pour Claude Code Local (Import)

**Objectif**: Recevoir et appliquer un patch depuis l'environnement cloud, puis pusher vers GitHub.

#### Option 1: Script Bash

```bash
cd C:\dev\emergenceV8
bash .sync/scripts/local-import.sh sync_cloud_20251010_123456.patch
```

#### Option 2: Script Python (recommandé - Windows compatible)

```bash
cd C:\dev\emergenceV8
python .sync/scripts/local-import.py sync_cloud_20251010_123456.patch
```

**Le script va**:
1. ✅ Vérifier prérequis (patch, métadonnées, dépôt Git)
2. ✅ Créer une branche de backup
3. ✅ Appliquer le patch (avec 3 méthodes de fallback)
4. ✅ Proposer validation (build, tests)
5. ✅ Proposer commit et push vers GitHub

---

### Pour GPT Codex Local (Pull depuis GitHub)

**Objectif**: Récupérer les dernières modifications depuis GitHub après qu'elles ont été pushées par l'agent local.

```bash
cd /workspace/emergencev8
git fetch origin
git pull origin main
```

Lire ensuite:
- `AGENT_SYNC.md` pour l'état actuel
- `docs/passation.md` pour les dernières sessions

---

## 🔧 Scripts Disponibles

### 1. Export Cloud (`cloud-export.sh` / `cloud-export.py`)

Génère un patch Git complet avec métadonnées.

**Usage**:
```bash
python .sync/scripts/cloud-export.py
```

**Options Bash**:
```bash
SYNC_DIR=.sync bash .sync/scripts/cloud-export.sh
```

**Génère**:
- Patch Git (diff ou format-patch)
- Métadonnées JSON (agent, timestamp, branche, statistiques)
- Liste des fichiers modifiés
- Instructions pour l'agent local
- Log d'export complet

---

### 2. Import Local (`local-import.sh` / `local-import.py`)

Applique un patch reçu de l'environnement cloud.

**Usage**:
```bash
python .sync/scripts/local-import.py <patch_name>
```

**Lister patches disponibles**:
```bash
python .sync/scripts/local-import.py
```

**Fonctionnalités**:
- Application automatique du patch (3 méthodes: `git apply`, `git am`, `git apply --3way`)
- Création branche de backup
- Validation optionnelle (build, tests)
- Commit et push interactifs
- Log d'import complet

---

### 3. Tracker de Synchronisation (`sync-tracker.py`)

Enregistre et affiche l'historique de toutes les synchronisations.

**Commandes**:

```bash
# Lister les 10 dernières syncs
python .sync/scripts/sync-tracker.py list

# Lister les 50 dernières
python .sync/scripts/sync-tracker.py list 50

# Afficher les statistiques
python .sync/scripts/sync-tracker.py stats

# Trouver une sync par patch
python .sync/scripts/sync-tracker.py find sync_cloud_20251010_123456.patch

# Exporter l'historique en JSON
python .sync/scripts/sync-tracker.py export .sync/sync_history.json
```

**Base de données**: `.sync/sync_history.db` (SQLite)

---

### 4. Validation Avant Sync (`validate-before-sync.py`)

Valide la qualité du code avant de créer un patch.

**Niveaux de validation**:

#### Minimal (rapide)
```bash
python .sync/scripts/validate-before-sync.py --level minimal
```
Vérifie: Git status, syntaxe Python, build npm

#### Standard (recommandé)
```bash
python .sync/scripts/validate-before-sync.py --level standard
```
Vérifie: Minimal + tests pytest

#### Complete (rigoureux)
```bash
python .sync/scripts/validate-before-sync.py --level complete
```
Vérifie: Standard + linting (ruff) + type checking (mypy)

**Utilisation recommandée**: Exécuter avant chaque export cloud.

---

## 📋 Workflow Complet

### Scénario 1: Cloud → Local → GitHub

**GPT Codex Cloud**:
```bash
# 1. Valider le code
python .sync/scripts/validate-before-sync.py --level standard

# 2. Générer le patch
python .sync/scripts/cloud-export.py

# 3. Noter les fichiers générés
# - .sync/patches/sync_cloud_20251010_123456.patch
# - .sync/patches/sync_cloud_20251010_123456.json
```

**Développeur**:
```
# Transférer les 2 fichiers vers C:\dev\emergenceV8\.sync\patches\
```

**Claude Code Local**:
```bash
# 1. Importer le patch
python .sync/scripts/local-import.py sync_cloud_20251010_123456.patch

# 2. Le script propose automatiquement:
#    - Validation (build, tests)
#    - Commit
#    - Push vers GitHub

# 3. Vérifier l'historique
python .sync/scripts/sync-tracker.py list
```

**GPT Codex Local** (si différent de Cloud):
```bash
# Récupérer depuis GitHub
git pull origin main

# Lire la documentation mise à jour
cat AGENT_SYNC.md
cat docs/passation.md
```

---

### Scénario 2: Local → Cloud (moins fréquent)

**Claude Code Local** OU **GPT Codex Local**:
```bash
# 1. Pousser vers GitHub
git push origin main

# 2. Mettre à jour AGENT_SYNC.md
```

**GPT Codex Cloud**:
```bash
# Pull depuis GitHub (si remote configuré)
git pull origin main

# OU demander un patch au développeur
```

---

## 🎨 Templates de Documentation

### 1. Résumé de Session
Fichier: `.sync/templates/sync-session-summary.md`

Documenter chaque session de sync avec:
- Objectif
- Modifications apportées
- Tests effectués
- Métriques
- Problèmes rencontrés

### 2. Passation Agent
Fichier: `.sync/templates/agent-handoff.md`

Faciliter la passation entre agents avec:
- Contexte complet
- Tâches en cours/restantes
- Points d'attention
- Recommandations

### 3. Checklist Pré-Sync
Fichier: `.sync/templates/checklist-pre-sync.md`

Vérifications obligatoires avant chaque sync:
- État Git
- Tests et qualité
- Documentation
- Fichiers sensibles
- Dépendances

---

## 📊 Historique et Traçabilité

Toutes les synchronisations sont enregistrées dans `.sync/sync_history.db`.

**Informations trackées**:
- Timestamp
- Type (export/import)
- Agent (Cloud/Local)
- Patch name
- Branches (source/target)
- Nombre de commits
- Nombre de fichiers modifiés
- Taille du patch
- Status (success/failed/partial)
- Messages d'erreur
- Métadonnées complètes

**Consulter l'historique**:
```bash
# Vue liste
python .sync/scripts/sync-tracker.py list 20

# Vue statistiques
python .sync/scripts/sync-tracker.py stats

# Export JSON
python .sync/scripts/sync-tracker.py export backup.json
```

---

## ⚠️ Résolution de Problèmes

### Patch ne s'applique pas

**Symptômes**: `git apply` échoue

**Solutions**:
1. Le script essaie automatiquement 3 méthodes:
   - `git apply`
   - `git am`
   - `git apply --3way`

2. Si échec complet:
   ```bash
   # Restaurer backup
   git checkout backup/before-sync-YYYYMMDD_HHMMSS

   # Appliquer manuellement
   git apply --reject .sync/patches/sync_cloud_*.patch
   # Résoudre conflits dans *.rej files
   ```

### Working Tree Non Propre

**Symptômes**: Le script avertit de modifications non commitées

**Solutions**:
```bash
# Option 1: Stash temporaire
git stash
python .sync/scripts/local-import.py <patch>
git stash pop

# Option 2: Commit d'abord
git add -A
git commit -m "WIP: avant import patch"
python .sync/scripts/local-import.py <patch>
```

### Validation Échoue

**Symptômes**: `validate-before-sync.py` retourne des erreurs

**Solutions**:
1. Lire les erreurs affichées
2. Corriger le code
3. Re-valider
4. Si tests échouent temporairement, utiliser `--level minimal`

### Historique Corrompu

**Symptômes**: Erreurs SQLite

**Solutions**:
```bash
# Backup de l'historique
cp .sync/sync_history.db .sync/sync_history.db.backup

# Exporter en JSON
python .sync/scripts/sync-tracker.py export .sync/history_backup.json

# Supprimer et réinitialiser
rm .sync/sync_history.db
python .sync/scripts/sync-tracker.py list  # Recrée la DB
```

---

## 🔐 Sécurité

### Fichiers à NE JAMAIS Synchroniser

- ❌ Fichiers `.env` (secrets, credentials)
- ❌ `node_modules/`, `venv/`, `__pycache__/`
- ❌ Fichiers de configuration locale (`.vscode/`, `.idea/`)
- ❌ Logs contenant des données sensibles
- ❌ Bases de données de test avec données réelles

### Vérification Avant Export

Le script `cloud-export.py` **ne filtre pas automatiquement** les fichiers sensibles.

**Toujours vérifier** le contenu du patch avant transfert:
```bash
cat .sync/patches/sync_cloud_*.patch | head -100
```

### .gitignore Recommandé

Ajouter à `.gitignore`:
```
.sync/patches/*.patch
.sync/logs/*.log
.sync/sync_history.db
.sync/sync_history.json
```

**Raison**: Les patches peuvent contenir du code en cours de développement non destiné au repo.

---

## 📚 Documentation Complémentaire

- [CLOUD_LOCAL_SYNC_WORKFLOW.md](../docs/CLOUD_LOCAL_SYNC_WORKFLOW.md) - Guide détaillé workflow
- [GPT_CODEX_CLOUD_INSTRUCTIONS.md](../docs/GPT_CODEX_CLOUD_INSTRUCTIONS.md) - Instructions pour agent cloud
- [AGENT_SYNC.md](../AGENT_SYNC.md) - État de synchronisation du dépôt
- [CODEV_PROTOCOL.md](../CODEV_PROTOCOL.md) - Protocole multi-agents

---

## 🤝 Contribution

Ce système est maintenu par les agents suivants:
- **Claude Code (Local)** - Agent principal avec accès GitHub
- **GPT Codex Cloud** - Agent cloud sans accès réseau
- **GPT Codex Local** - Agent local avec accès GitHub

Toute amélioration doit être documentée et synchronisée via ce workflow.

---

## 📞 Support

En cas de problème:

1. Consulter les logs: `.sync/logs/`
2. Vérifier l'historique: `python .sync/scripts/sync-tracker.py list`
3. Lire la documentation: `docs/CLOUD_LOCAL_SYNC_WORKFLOW.md`
4. Restaurer backup: `git checkout backup/before-sync-*`

---

**Version**: 1.0.0
**Dernière mise à jour**: 2025-10-10
**Maintenu par**: Claude Code (Agent Local)
