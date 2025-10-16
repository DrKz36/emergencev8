# 🎉 Système d'Orchestration Automatique - Installation Terminée

## ✅ Ce qui a été installé

### 1. Scripts d'orchestration automatique

| Script | Fonction |
|--------|----------|
| [auto_orchestrator.py](scripts/auto_orchestrator.py) | Orchestrateur principal exécutant tous les agents automatiquement |
| [auto_update_docs.py](scripts/auto_update_docs.py) | Agent de mise à jour automatique de la documentation |
| [scheduler.py](scripts/scheduler.py) | Planificateur pour exécution périodique |

### 2. Hook Git modifié

**Fichier:** `.git/hooks/post-commit`

**Ajout:**
- Support pour `AUTO_UPDATE_DOCS=1` (active la vérification post-commit)
- Support pour `AUTO_APPLY=1` (applique automatiquement les mises à jour)
- Création automatique de commits pour les mises à jour de documentation

### 3. Commande slash Claude

**Fichier:** `.claude/commands/auto_sync.md`

**Usage:** `/auto_sync` pour lancer l'orchestration automatique complète depuis Claude

### 4. Documentation

| Document | Description |
|----------|-------------|
| [AUTO_ORCHESTRATION.md](AUTO_ORCHESTRATION.md) | Documentation complète du système |
| [QUICKSTART_AUTO.md](QUICKSTART_AUTO.md) | Guide de démarrage rapide |
| [SUMMARY_AUTO_SETUP.md](SUMMARY_AUTO_SETUP.md) | Ce fichier - résumé de l'installation |

---

## 🚀 Démarrage rapide

### Option 1: Test manuel (recommandé pour débuter)

```bash
python claude-plugins/integrity-docs-guardian/scripts/auto_orchestrator.py
```

**Résultat:** Exécute tous les agents, génère les rapports, **mais ne modifie pas la documentation**.

### Option 2: Mode automatique complet

```bash
AUTO_APPLY=1 python claude-plugins/integrity-docs-guardian/scripts/auto_orchestrator.py
```

**Résultat:** Exécute tous les agents ET applique automatiquement les mises à jour de documentation.

### Option 3: Activation du hook post-commit

```bash
# Ajouter à votre .bashrc/.zshrc (Linux/Mac) ou profil PowerShell (Windows)
export AUTO_UPDATE_DOCS=1  # Active la vérification après commit
export AUTO_APPLY=0        # Mode analyse seulement (mettre à 1 pour mode auto)

# Puis faire un commit
git commit -m "test: vérifier le hook automatique"
```

### Option 4: Planification périodique

```bash
# Exécution continue toutes les heures
python claude-plugins/integrity-docs-guardian/scripts/scheduler.py

# Ou exécution unique (pour cron/Task Scheduler)
RUN_ONCE=1 python claude-plugins/integrity-docs-guardian/scripts/scheduler.py
```

---

## 📊 Workflow automatique

```
┌─────────────────────────────────────────────────────────────┐
│                   DÉCLENCHEUR                                │
│  • Commit Git (hook post-commit)                            │
│  • Commande manuelle (/auto_sync)                           │
│  • Planificateur (toutes les N minutes)                     │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│             PHASE 1: Exécution des agents                    │
│  ✅ Anima (DocKeeper) → scan_docs.py                        │
│  ✅ Neo (IntegrityWatcher) → check_integrity.py             │
│  ✅ ProdGuardian → check_prod_logs.py                       │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│             PHASE 2: Coordination                            │
│  ✅ Nexus (Coordinator) → generate_report.py                │
│  ✅ Merge Reports → merge_reports.py                        │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│       PHASE 3: Mise à jour automatique de la doc             │
│  ✅ Auto Documentation Updater → auto_update_docs.py        │
│                                                              │
│  SI AUTO_APPLY=0 (mode manuel):                             │
│    → Génère auto_update_report.json                         │
│    → Liste les mises à jour recommandées                    │
│    → Aucune modification                                    │
│                                                              │
│  SI AUTO_APPLY=1 (mode automatique):                        │
│    → Applique les mises à jour à la documentation           │
│    → Trace dans auto_update_report.json                     │
│    → Crée un commit automatique (si hook Git)               │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                 RAPPORTS GÉNÉRÉS                             │
│  📄 orchestration_report.json                               │
│  📄 auto_update_report.json                                 │
│  📄 docs_report.json                                        │
│  📄 integrity_report.json                                   │
│  📄 prod_report.json                                        │
│  📄 unified_report.json                                     │
│  📄 global_report.json                                      │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 Modes d'exécution

### Mode 1: Analyse uniquement (par défaut)

**Variables:** `AUTO_APPLY=0` (ou non défini)

**Comportement:**
- ✅ Tous les agents s'exécutent
- ✅ Rapports générés
- ✅ Liste des mises à jour recommandées dans `auto_update_report.json`
- ❌ **Aucune modification automatique de la documentation**

**Usage:**
```bash
python claude-plugins/integrity-docs-guardian/scripts/auto_orchestrator.py
```

### Mode 2: Automatique complet

**Variables:** `AUTO_APPLY=1`

**Comportement:**
- ✅ Tous les agents s'exécutent
- ✅ Mises à jour de documentation appliquées automatiquement
- ✅ Changements tracés dans les rapports
- ✅ Commit automatique si déclenché par hook Git

**Usage:**
```bash
AUTO_APPLY=1 python claude-plugins/integrity-docs-guardian/scripts/auto_orchestrator.py
```

### Mode 3: Hook Git (post-commit)

**Variables:** `AUTO_UPDATE_DOCS=1` + `AUTO_APPLY=0|1`

**Comportement:**
- ✅ Se déclenche automatiquement après chaque commit
- ✅ Exécute tous les agents
- ✅ Applique ou recommande les mises à jour selon `AUTO_APPLY`
- ✅ Crée un commit automatique si `AUTO_APPLY=1` et modifications nécessaires

**Configuration:**
```bash
export AUTO_UPDATE_DOCS=1
export AUTO_APPLY=0  # ou 1 pour mode automatique
```

### Mode 4: Planificateur périodique

**Variables:** `AGENT_CHECK_INTERVAL=60` (minutes) + `RUN_ONCE=0|1`

**Comportement:**
- ✅ Exécution à intervalles réguliers
- ✅ Vérifie l'état Git avant exécution (optionnel)
- ✅ Logs dans `claude-plugins/integrity-docs-guardian/logs/scheduler.log`

**Usage:**
```bash
# Continu (toutes les heures)
python claude-plugins/integrity-docs-guardian/scripts/scheduler.py

# Une seule fois (pour cron)
RUN_ONCE=1 python claude-plugins/integrity-docs-guardian/scripts/scheduler.py
```

---

## 📋 Rapports générés

### orchestration_report.json
Statut de tous les agents exécutés

### auto_update_report.json
Liste des mises à jour de documentation (appliquées ou recommandées)

### Autres rapports
Voir [AUTO_ORCHESTRATION.md](AUTO_ORCHESTRATION.md) pour la description complète

---

## 🔐 Sécurité et garanties

1. **Pas de modifications sans rapport**: Aucune modification n'est effectuée sans qu'un rapport préalable soit généré
2. **Traçabilité complète**: Tous les changements sont tracés dans les rapports JSON et commits Git
3. **Commits marqués**: Les commits automatiques sont identifiés avec 🤖 et `--no-verify`
4. **Mode manuel par défaut**: Sans configuration explicite (`AUTO_APPLY=1`), le système analyse mais ne modifie rien
5. **Vérification Git**: Le planificateur vérifie qu'il n'y a pas de changements non commités avant d'exécuter

---

## ⚙️ Configuration recommandée par environnement

### Développement local (solo)

```bash
export AUTO_UPDATE_DOCS=1
export AUTO_APPLY=0
```

**Résultat:** Analyse après chaque commit, revue manuelle des mises à jour

### Intégration continue (CI/CD)

```yaml
# Dans votre pipeline CI/CD
- name: Auto orchestration
  run: |
    AUTO_APPLY=1 python claude-plugins/integrity-docs-guardian/scripts/auto_orchestrator.py
    git add docs/ AGENT_SYNC.md
    git commit -m "docs: auto-update from CI" --no-verify || true
    git push
```

### Production monitoring

```bash
# Via cron (toutes les heures)
0 * * * * cd /path/to/emergenceV8 && RUN_ONCE=1 AUTO_APPLY=1 python3 scheduler.py
```

---

## 🛠️ Variables d'environnement

| Variable | Valeurs | Description | Défaut |
|----------|---------|-------------|--------|
| `AUTO_UPDATE_DOCS` | `0` / `1` | Active la vérification post-commit | `0` |
| `AUTO_APPLY` | `0` / `1` | Active l'application automatique des mises à jour | `0` |
| `AGENT_CHECK_INTERVAL` | Minutes | Intervalle pour le planificateur | `60` |
| `RUN_ONCE` | `0` / `1` | Exécution unique pour le planificateur | `0` |
| `CHECK_GIT_STATUS` | `0` / `1` | Vérifie Git avant exécution | `1` |

---

## 📚 Documentation

| Document | Usage |
|----------|-------|
| [QUICKSTART_AUTO.md](QUICKSTART_AUTO.md) | Guide de démarrage rapide avec exemples |
| [AUTO_ORCHESTRATION.md](AUTO_ORCHESTRATION.md) | Documentation complète du système |
| [AGENTS.md](../../AGENTS.md) | Documentation des agents individuels |
| [CODEV_PROTOCOL.md](../../CODEV_PROTOCOL.md) | Protocole multi-agents |

---

## ✅ Prochaines étapes

1. **Tester le système:**
   ```bash
   python claude-plugins/integrity-docs-guardian/scripts/auto_orchestrator.py
   ```

2. **Vérifier les rapports:**
   ```bash
   cat claude-plugins/integrity-docs-guardian/reports/orchestration_report.json
   cat claude-plugins/integrity-docs-guardian/reports/auto_update_report.json
   ```

3. **Activer le hook Git (optionnel):**
   ```bash
   export AUTO_UPDATE_DOCS=1
   export AUTO_APPLY=0  # Mode analyse seulement
   ```

4. **Configurer le planificateur (optionnel):**
   - Via cron (Linux/Mac)
   - Via Task Scheduler (Windows)
   - Voir [QUICKSTART_AUTO.md](QUICKSTART_AUTO.md) pour les détails

---

## 🎓 Commandes utiles

```bash
# Test manuel
python claude-plugins/integrity-docs-guardian/scripts/auto_orchestrator.py

# Test avec application automatique
AUTO_APPLY=1 python claude-plugins/integrity-docs-guardian/scripts/auto_orchestrator.py

# Via Claude
/auto_sync

# Planificateur (une fois)
RUN_ONCE=1 python claude-plugins/integrity-docs-guardian/scripts/scheduler.py

# Planificateur (continu)
python claude-plugins/integrity-docs-guardian/scripts/scheduler.py
```

---

## 🎉 Félicitations !

Votre système d'orchestration automatique est maintenant opérationnel. Tous vos agents de vérification s'exécutent automatiquement et peuvent maintenir votre documentation synchronisée avec votre code.

**Pour toute question, consultez:**
- [QUICKSTART_AUTO.md](QUICKSTART_AUTO.md) - Guide de démarrage
- [AUTO_ORCHESTRATION.md](AUTO_ORCHESTRATION.md) - Documentation complète
