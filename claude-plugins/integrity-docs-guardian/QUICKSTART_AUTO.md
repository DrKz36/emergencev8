# 🚀 Guide de Démarrage Rapide - Orchestration Automatique

Ce guide vous permet de mettre en place rapidement l'orchestration automatique des agents avec mise à jour automatique de la documentation.

## ✅ Prérequis

- Python 3.8+
- Git
- Accès au projet ÉMERGENCE

## 🎯 Scénarios d'utilisation

### Scénario 1: Test manuel (recommandé pour débuter)

**Objectif:** Tester le système sans modifier automatiquement la documentation.

```bash
# Exécuter l'orchestration manuelle
python claude-plugins/integrity-docs-guardian/scripts/auto_orchestrator.py
```

**Ce qui se passe:**
- ✅ Tous les agents s'exécutent (Anima, Neo, ProdGuardian, Nexus)
- ✅ Rapports générés dans `reports/`
- ✅ Identification des mises à jour de documentation nécessaires
- ❌ **Aucune modification automatique**

**Vérifier les résultats:**
```bash
# Voir le rapport d'orchestration
cat claude-plugins/integrity-docs-guardian/reports/orchestration_report.json

# Voir les mises à jour de documentation recommandées
cat claude-plugins/integrity-docs-guardian/reports/auto_update_report.json
```

---

### Scénario 2: Mode automatique complet

**Objectif:** Exécuter l'orchestration ET appliquer automatiquement les mises à jour de documentation.

```bash
# Exécuter avec application automatique
AUTO_APPLY=1 python claude-plugins/integrity-docs-guardian/scripts/auto_orchestrator.py
```

**Ce qui se passe:**
- ✅ Tous les agents s'exécutent
- ✅ Mises à jour de documentation appliquées automatiquement
- ✅ Changements tracés dans les rapports

**Vérifier les changements:**
```bash
# Voir les fichiers modifiés
git status

# Voir les différences
git diff docs/ AGENT_SYNC.md
```

---

### Scénario 3: Activation du hook Git (automatique post-commit)

**Objectif:** Exécuter automatiquement les vérifications après chaque commit.

#### Étape 1: Activer le hook (mode analyse uniquement)

```bash
# Ajouter à votre .bashrc, .zshrc ou équivalent (Linux/Mac)
export AUTO_UPDATE_DOCS=1
export AUTO_APPLY=0  # Mode analyse seulement

# Pour Windows (PowerShell), ajouter à votre profil
$env:AUTO_UPDATE_DOCS=1
$env:AUTO_APPLY=0
```

#### Étape 2: Tester

```bash
# Faire un commit
git add .
git commit -m "test: vérifier le hook automatique"

# Le hook se déclenche automatiquement après le commit
# Vous verrez:
# 🔍 ÉMERGENCE Guardian d'Intégrité: Vérification Post-Commit
# [...]
# ✅ Vérification Guardian d'Intégrité terminée!
```

#### Étape 3: Mode automatique complet (optionnel)

```bash
# Pour appliquer automatiquement les mises à jour de documentation
export AUTO_APPLY=1

# Faire un commit
git add .
git commit -m "feat: nouvelle fonctionnalité"

# Le hook:
# 1. Exécute tous les agents
# 2. Applique les mises à jour de documentation
# 3. Crée un commit automatique avec les mises à jour (si nécessaire)
```

---

### Scénario 4: Planification périodique (monitoring continu)

**Objectif:** Exécuter les vérifications toutes les heures automatiquement.

#### Option A: Exécution unique programmée

```bash
# Exécuter une fois (utile pour cron)
RUN_ONCE=1 python claude-plugins/integrity-docs-guardian/scripts/scheduler.py
```

#### Option B: Exécution continue

```bash
# Exécuter en continu toutes les heures (par défaut)
python claude-plugins/integrity-docs-guardian/scripts/scheduler.py

# Personnaliser l'intervalle (en minutes)
AGENT_CHECK_INTERVAL=30 python claude-plugins/integrity-docs-guardian/scripts/scheduler.py
```

#### Option C: Configuration avec Cron (Linux/Mac)

```bash
# Éditer crontab
crontab -e

# Ajouter cette ligne pour exécution toutes les heures
0 * * * * cd /path/to/emergenceV8 && RUN_ONCE=1 AUTO_APPLY=0 /usr/bin/python3 claude-plugins/integrity-docs-guardian/scripts/scheduler.py >> /tmp/emergence-scheduler.log 2>&1
```

#### Option D: Task Scheduler (Windows)

1. Ouvrir "Planificateur de tâches" (Task Scheduler)
2. Créer une tâche de base:
   - **Nom:** ÉMERGENCE Auto Check
   - **Déclencheur:** Répéter toutes les 1 heures
   - **Action:** Démarrer un programme
     - Programme: `python`
     - Arguments: `claude-plugins\integrity-docs-guardian\scripts\scheduler.py`
     - Répertoire: `C:\dev\emergenceV8`
3. Variables d'environnement (dans "Modifier la tâche" → "Actions" → "Modifier"):
   - Ajouter: `RUN_ONCE=1`

---

## 📊 Comprendre les rapports

### orchestration_report.json

Résumé de l'exécution de tous les agents:

```json
{
  "timestamp": "2025-10-16T17:03:53",
  "agents": [
    {
      "agent": "Anima (DocKeeper)",
      "status": "OK",
      "timestamp": "..."
    },
    ...
  ],
  "global_status": "OK",
  "summary": {
    "total_agents": 6,
    "successful": 6,
    "failed": 0,
    "success_rate": "100.0%"
  }
}
```

### auto_update_report.json

Détails des mises à jour de documentation:

```json
{
  "timestamp": "2025-10-16T17:03:56",
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

---

## 🛠️ Variables d'environnement

| Variable | Valeurs | Description |
|----------|---------|-------------|
| `AUTO_UPDATE_DOCS` | `0` / `1` | Active la vérification post-commit |
| `AUTO_APPLY` | `0` / `1` | Active l'application automatique des mises à jour |
| `AGENT_CHECK_INTERVAL` | Minutes | Intervalle pour le planificateur (défaut: 60) |
| `RUN_ONCE` | `0` / `1` | Exécution unique pour le planificateur |
| `CHECK_GIT_STATUS` | `0` / `1` | Vérifie Git avant exécution (défaut: 1) |

---

## 🎓 Commandes utiles

### Via Python directement

```bash
# Orchestration manuelle
python claude-plugins/integrity-docs-guardian/scripts/auto_orchestrator.py

# Orchestration avec mise à jour automatique
AUTO_APPLY=1 python claude-plugins/integrity-docs-guardian/scripts/auto_orchestrator.py

# Planificateur (une fois)
RUN_ONCE=1 python claude-plugins/integrity-docs-guardian/scripts/scheduler.py

# Planificateur (continu, toutes les 30 min)
AGENT_CHECK_INTERVAL=30 python claude-plugins/integrity-docs-guardian/scripts/scheduler.py
```

### Via commandes slash Claude

```bash
# Orchestration automatique
/auto_sync
```

---

## 🚨 Dépannage

### "Le hook ne se déclenche pas après commit"

**Vérifier:**
```bash
# Variable d'environnement définie ?
echo $AUTO_UPDATE_DOCS  # Devrait afficher 1

# Hook exécutable ?
chmod +x .git/hooks/post-commit
```

### "Les mises à jour ne sont pas appliquées"

**Vérifier:**
```bash
# AUTO_APPLY activé ?
echo $AUTO_APPLY  # Devrait afficher 1

# Exécuter manuellement pour déboguer
AUTO_APPLY=1 python claude-plugins/integrity-docs-guardian/scripts/auto_update_docs.py
```

### "Erreurs d'encodage (Windows)"

✅ **Les scripts incluent maintenant un fix automatique complet pour Windows** (v2.0.0+).

Si vous utilisez une version antérieure ou voyez encore des warnings d'encodage, assurez-vous que:

```bash
# PowerShell
$env:PYTHONIOENCODING="utf-8"

# CMD
set PYTHONIOENCODING=utf-8

# Puis réexécuter
python claude-plugins/integrity-docs-guardian/scripts/auto_orchestrator.py
```

**Note:** Les versions récentes (v2.0.0+) gèrent automatiquement l'encodage UTF-8, même avec des emojis dans les rapports.

---

## 📚 Documentation complète

Pour plus de détails, consultez:

- [AUTO_ORCHESTRATION.md](AUTO_ORCHESTRATION.md) - Documentation complète du système
- [AGENTS.md](../../AGENTS.md) - Documentation des agents
- [CODEV_PROTOCOL.md](../../CODEV_PROTOCOL.md) - Protocole multi-agents

---

## 🎯 Recommandations par cas d'usage

### Développeur solo en phase active

```bash
# Mode manuel avec hook post-commit
export AUTO_UPDATE_DOCS=1
export AUTO_APPLY=0

# Revue manuelle des mises à jour après chaque commit
```

### Équipe avec CI/CD

```bash
# Dans le pipeline CI/CD, ajouter:
AUTO_APPLY=1 python claude-plugins/integrity-docs-guardian/scripts/auto_orchestrator.py
git add docs/ AGENT_SYNC.md
git commit -m "docs: auto-update from CI" --no-verify || true
```

### Production avec monitoring 24/7

```bash
# Planificateur continu toutes les heures
nohup python claude-plugins/integrity-docs-guardian/scripts/scheduler.py > scheduler.log 2>&1 &

# Ou via cron
0 * * * * cd /path/to/emergenceV8 && RUN_ONCE=1 AUTO_APPLY=1 python3 scheduler.py
```

---

## ✅ Checklist de mise en place

### Étape 0: Vérifier l'installation

```bash
# Lancer le test d'installation complet
python claude-plugins/integrity-docs-guardian/scripts/test_installation.py
```

**Ce script vérifie:**
- ✅ Présence de tous les scripts (orchestrateur, agents, planificateur)
- ✅ Hooks Git configurés
- ✅ Commandes slash disponibles
- ✅ Documentation complète
- ✅ Dossiers nécessaires créés

**Résultat attendu:** `100.0%` de réussite

---

### Étapes suivantes:

- [ ] ✅ **Vérifier l'installation:** `python test_installation.py`
- [ ] Tester l'orchestration manuelle: `python auto_orchestrator.py`
- [ ] Vérifier les rapports générés dans `reports/`
- [ ] Tester le mode automatique: `AUTO_APPLY=1 python auto_orchestrator.py`
- [ ] Configurer les variables d'environnement pour le hook Git
- [ ] Faire un commit de test pour vérifier le hook
- [ ] (Optionnel) Configurer le planificateur pour monitoring continu

---

**Vous êtes prêt !** 🎉

Le système d'orchestration automatique est maintenant configuré et prêt à maintenir votre documentation synchronisée avec votre code.
