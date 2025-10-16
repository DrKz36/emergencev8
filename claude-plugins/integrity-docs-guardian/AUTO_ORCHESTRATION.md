# 🤖 Orchestration Automatique des Agents - ÉMERGENCE

Ce document explique comment configurer et utiliser le système d'orchestration automatique des agents de vérification avec mise à jour automatique de la documentation.

## 🎯 Vue d'ensemble

Le système d'orchestration automatique exécute tous les agents de vérification (Anima, Neo, ProdGuardian, Nexus) et met à jour automatiquement la documentation pertinente en fonction des rapports générés.

## 📁 Fichiers clés

### Scripts
- **`auto_orchestrator.py`** - Orchestrateur principal qui exécute tous les agents
- **`auto_update_docs.py`** - Agent de mise à jour automatique de la documentation
- **`scheduler.py`** - Planificateur pour exécution périodique

### Hooks Git
- **`.git/hooks/post-commit`** - Hook modifié pour support de l'orchestration automatique

### Commandes Slash
- **`/auto_sync`** - Lance l'orchestration automatique complète

### Rapports générés
- **`orchestration_report.json`** - Résumé de l'exécution de tous les agents
- **`auto_update_report.json`** - Détails des mises à jour de documentation

## 🚀 Modes d'exécution

### 1. Mode Manuel (Analyse uniquement)

Exécute tous les agents et identifie les mises à jour nécessaires sans modifier la documentation.

```bash
# Via Python directement
python claude-plugins/integrity-docs-guardian/scripts/auto_orchestrator.py

# Via commande slash Claude
/auto_sync
```

**Résultat:**
- Tous les agents sont exécutés
- Rapports générés dans `reports/`
- Liste des mises à jour recommandées
- **Aucune modification automatique**

### 2. Mode Automatique (Avec mise à jour)

Exécute tous les agents ET applique automatiquement les mises à jour de documentation.

```bash
# Avec application automatique des mises à jour
AUTO_APPLY=1 python claude-plugins/integrity-docs-guardian/scripts/auto_orchestrator.py
```

**Résultat:**
- Tous les agents sont exécutés
- Mises à jour appliquées automatiquement à la documentation
- Changements listés dans `auto_update_report.json`

### 3. Mode Hook Git (Post-commit)

Exécute automatiquement l'orchestration après chaque commit.

```bash
# Activer l'orchestration automatique après commit
export AUTO_UPDATE_DOCS=1

# Activer l'application automatique des mises à jour
export AUTO_APPLY=1

# Faire un commit (déclenche le hook)
git add .
git commit -m "votre message"

# Le hook post-commit se déclenche automatiquement et:
# 1. Exécute tous les agents
# 2. Met à jour la documentation si nécessaire
# 3. Crée un commit automatique des mises à jour doc (si AUTO_APPLY=1)
```

**Pour désactiver:**
```bash
unset AUTO_UPDATE_DOCS
unset AUTO_APPLY
```

### 4. Mode Planifié (Périodique)

Exécute l'orchestration à intervalles réguliers.

#### Option A: Une seule exécution
```bash
RUN_ONCE=1 python claude-plugins/integrity-docs-guardian/scripts/scheduler.py
```

#### Option B: Exécution continue
```bash
# Vérifie toutes les heures (par défaut)
python claude-plugins/integrity-docs-guardian/scripts/scheduler.py

# Vérifie toutes les 30 minutes
AGENT_CHECK_INTERVAL=30 python claude-plugins/integrity-docs-guardian/scripts/scheduler.py

# En arrière-plan (Linux/Mac)
nohup python claude-plugins/integrity-docs-guardian/scripts/scheduler.py > scheduler.log 2>&1 &
```

#### Option C: Via Cron (Linux/Mac)
```bash
# Éditer crontab
crontab -e

# Ajouter une ligne pour exécution toutes les heures
0 * * * * cd /path/to/emergenceV8 && RUN_ONCE=1 python claude-plugins/integrity-docs-guardian/scripts/scheduler.py
```

#### Option D: Via Task Scheduler (Windows)

1. Ouvrir "Task Scheduler"
2. Créer une tâche de base:
   - **Nom:** ÉMERGENCE Auto Orchestration
   - **Déclencheur:** Répéter toutes les heures
   - **Action:** Démarrer un programme
   - **Programme:** `python`
   - **Arguments:** `claude-plugins/integrity-docs-guardian/scripts/scheduler.py`
   - **Répertoire:** `C:\dev\emergenceV8`
   - **Variables d'environnement:**
     - `RUN_ONCE=1`
     - `AUTO_APPLY=0` (ou `1` pour mode automatique)

## ⚙️ Variables d'environnement

| Variable | Valeur | Description |
|----------|---------|-------------|
| `AUTO_UPDATE_DOCS` | `0` ou `1` | Active la vérification auto après commit |
| `AUTO_APPLY` | `0` ou `1` | Active l'application automatique des mises à jour doc |
| `AGENT_CHECK_INTERVAL` | Minutes (défaut: `60`) | Intervalle pour le planificateur |
| `RUN_ONCE` | `0` ou `1` | Mode une seule exécution pour le planificateur |
| `CHECK_GIT_STATUS` | `0` ou `1` | Vérifie l'état Git avant exécution (défaut: `1`) |

## 📊 Rapports générés

### orchestration_report.json
```json
{
  "timestamp": "2025-10-16T17:00:00",
  "agents": [
    {
      "agent": "Anima (DocKeeper)",
      "status": "OK",
      "timestamp": "2025-10-16T17:00:01"
    },
    ...
  ],
  "global_status": "OK",
  "summary": {
    "total_agents": 5,
    "successful": 5,
    "failed": 0,
    "success_rate": "100.0%"
  }
}
```

### auto_update_report.json
```json
{
  "timestamp": "2025-10-16T17:00:05",
  "updates_found": 2,
  "updates": [
    {
      "file": "AGENT_SYNC.md",
      "section": "Production",
      "content": "...",
      "priority": "HIGH"
    }
  ],
  "priority_breakdown": {
    "CRITICAL": 0,
    "HIGH": 1,
    "MEDIUM": 1,
    "LOW": 0
  }
}
```

## 🔧 Configuration recommandée

### Pour développement actif

```bash
# Activer l'orchestration après chaque commit
export AUTO_UPDATE_DOCS=1

# Mode manuel (revue avant application)
export AUTO_APPLY=0
```

Après chaque commit, vous verrez les mises à jour recommandées dans `auto_update_report.json` et pouvez les appliquer manuellement.

### Pour intégration continue

```bash
# Activer l'orchestration et l'application automatique
export AUTO_UPDATE_DOCS=1
export AUTO_APPLY=1
```

Les mises à jour de documentation sont appliquées et commitées automatiquement.

### Pour monitoring production

```bash
# Planificateur toutes les heures
AGENT_CHECK_INTERVAL=60 python scheduler.py &

# Ou via cron
0 * * * * cd /path/to/emergenceV8 && RUN_ONCE=1 AUTO_APPLY=1 python claude-plugins/integrity-docs-guardian/scripts/scheduler.py
```

## 🛡️ Sécurité et garanties

1. **Pas de modifications sans rapport**: Aucune modification de documentation n'est effectuée sans qu'un rapport préalable soit généré.

2. **Traçabilité complète**: Tous les changements automatiques sont tracés dans les rapports JSON et les commits Git.

3. **Commits marqués**: Les commits automatiques sont clairement identifiés avec 🤖 et `--no-verify` pour éviter les boucles.

4. **Mode manuel par défaut**: Sans configuration explicite, le système analyse mais ne modifie rien.

5. **Vérification Git**: Le planificateur vérifie qu'il n'y a pas de changements non commités avant d'exécuter.

## 📝 Logs

Les logs du planificateur sont dans:
```
claude-plugins/integrity-docs-guardian/logs/scheduler.log
```

Exemple:
```
[2025-10-16 17:00:00] 🕐 PLANIFICATEUR D'ORCHESTRATION AUTOMATIQUE
[2025-10-16 17:00:00] Configuration:
[2025-10-16 17:00:00]   - Intervalle: 60 minutes
[2025-10-16 17:00:00]   - Mode: Continu
[2025-10-16 17:00:01] 🚀 Démarrage de l'orchestration automatique...
[2025-10-16 17:00:45] ✅ Orchestration terminée avec succès
```

## 🔍 Dépannage

### L'orchestration ne se déclenche pas après commit

Vérifiez que la variable est définie:
```bash
echo $AUTO_UPDATE_DOCS  # Devrait afficher 1
```

Vérifiez que le hook est exécutable:
```bash
chmod +x .git/hooks/post-commit
```

### Les mises à jour ne sont pas appliquées

Vérifiez que AUTO_APPLY est activé:
```bash
echo $AUTO_APPLY  # Devrait afficher 1
```

### Le planificateur ne s'exécute pas

Vérifiez les logs:
```bash
tail -f claude-plugins/integrity-docs-guardian/logs/scheduler.log
```

Vérifiez que Python est dans le PATH:
```bash
python --version
```

## 🎯 Cas d'usage

### Cas 1: Développeur solo en mode actif
```bash
export AUTO_UPDATE_DOCS=1
export AUTO_APPLY=0
# Revue manuelle des mises à jour après chaque commit
```

### Cas 2: Équipe avec CI/CD
```bash
# Dans le pipeline CI/CD
AUTO_APPLY=1 python auto_orchestrator.py
git add docs/ AGENT_SYNC.md
git commit -m "docs: auto-update from CI" --no-verify || true
git push
```

### Cas 3: Monitoring production 24/7
```bash
# Via systemd (Linux)
[Unit]
Description=ÉMERGENCE Auto Orchestration
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/emergenceV8
Environment="AGENT_CHECK_INTERVAL=60"
Environment="AUTO_APPLY=1"
ExecStart=/usr/bin/python3 claude-plugins/integrity-docs-guardian/scripts/scheduler.py
Restart=always

[Install]
WantedBy=multi-user.target
```

## 📚 Ressources

- [AGENTS.md](../../AGENTS.md) - Documentation générale des agents
- [CODEV_PROTOCOL.md](../../CODEV_PROTOCOL.md) - Protocole multi-agents
- [sync_all.md](.claude/commands/sync_all.md) - Orchestration manuelle complète
- [auto_sync.md](.claude/commands/auto_sync.md) - Commande slash d'orchestration automatique
