# 🤖 ÉMERGENCE Guardian - État du Système

**Date de dernière mise à jour :** 2025-10-17
**Version :** Phase 3 - Automatisation Complète Activée

---

## ✅ État Actuel : OPÉRATIONNEL

Le système Guardian est **entièrement opérationnel** avec automatisation complète.

---

## 📊 Composants du Système

### 🎯 Agents Actifs

| Agent | Nom | Fonction | Statut |
|-------|-----|----------|--------|
| 📚 Anima | DocKeeper | Détection des gaps de documentation | ✅ ACTIF |
| 🔐 Neo | IntegrityWatcher | Vérification de l'intégrité backend/frontend | ✅ ACTIF |
| 🏭 ProdGuardian | Production Monitor | Surveillance des logs de production | ✅ ACTIF |
| 💰 Theia | CostWatcher | Optimisation des coûts modèles IA | ✅ ACTIF |
| 🎯 Nexus | Coordinator | Génération de rapports unifiés | ✅ ACTIF |

### 🪝 Hooks Git Automatiques

| Hook | Déclenché | Fonction | Statut |
|------|-----------|----------|--------|
| `pre-commit` | Avant chaque commit | Vérifications Anima + Neo, bloque si critique | ✅ ACTIF |
| `post-commit` | Après chaque commit | Génère rapports + feedback détaillé | ✅ ACTIF |
| `pre-push` | Avant chaque push | Vérifie production, bloque si critique | ✅ ACTIF |

### 📋 Scripts Disponibles

| Script | Fonction | Emplacement |
|--------|----------|-------------|
| `scan_docs.py` | Anima - Scan documentation | `scripts/` |
| `check_integrity.py` | Neo - Check intégrité | `scripts/` |
| `check_prod_logs.py` | ProdGuardian - Logs prod | `scripts/` |
| `analyze_ai_costs.py` | Theia - Analyse coûts IA | `scripts/` |
| `generate_report.py` | Nexus - Rapport unifié | `scripts/` |
| `auto_orchestrator.py` | Orchestrateur automatique | `scripts/` |
| `scheduler.py` | Planificateur continu | `scripts/` |
| `setup_automation.py` | Configuration initiale | `scripts/` |

---

## 🔄 Modes de Fonctionnement

### Mode 1 : Automatisation Git (Activé ✅)

**Description :** Les hooks Git s'exécutent automatiquement lors des commits/push.

**Configuration :**
- ✅ Hooks installés : `pre-commit`, `post-commit`, `pre-push`
- ✅ Python détecté : Système ou venv
- ✅ Tous les agents disponibles

**Utilisation :**
```bash
# Commit normal → hooks s'exécutent automatiquement
git add .
git commit -m "feat: nouvelle fonctionnalité"

# Push normal → vérification production
git push
```

### Mode 2 : Monitoring Continu (Optionnel ⚙️)

**Description :** Le scheduler vérifie automatiquement toutes les heures en arrière-plan.

**Configuration :**
```bash
# Option A : Windows Task Scheduler (recommandé)
# Voir GUIDE_TASK_SCHEDULER.md

# Option B : Exécution manuelle
python claude-plugins/integrity-docs-guardian/scripts/scheduler.py
```

**Variables d'environnement :**
- `AGENT_CHECK_INTERVAL` : Intervalle en minutes (défaut: 60)
- `RUN_ONCE` : 1 pour une seule exécution, 0 pour continu
- `CHECK_GIT_STATUS` : 1 pour vérifier git status, 0 pour skip

### Mode 3 : Mise à Jour Auto de Documentation (Optionnel ⚙️)

**Description :** Met à jour automatiquement la documentation après chaque commit.

**Configuration :**
```powershell
# Windows PowerShell
$env:AUTO_UPDATE_DOCS='1'
$env:AUTO_APPLY='1'

# Linux/Mac
export AUTO_UPDATE_DOCS=1
export AUTO_APPLY=1
```

**Comportement :**
- Si `AUTO_UPDATE_DOCS=1` : Analyse et propose des mises à jour
- Si `AUTO_APPLY=1` : Applique ET commit automatiquement les mises à jour

---

## 📈 Workflow Standard

### Développement Normal

```
1. Développer → git add .
                    ↓
2. Pre-Commit Hook ← Anima vérifie la documentation
                  ← Neo vérifie l'intégrité
                  ← Bloque si erreur critique
                    ↓
3. git commit -m "..." → Commit créé
                    ↓
4. Post-Commit Hook ← Nexus génère rapport unifié
                   ← Affiche feedback détaillé
                   ← (Optionnel) Met à jour la doc
                    ↓
5. git push → Pre-Push Hook vérifie la production
                    ↓
6. Push vers remote
```

### Résultat Visible

**Après un commit, tu verras :**
```
🔍 ÉMERGENCE Guardian: Vérification Pre-Commit
====================================================

📝 Fichiers staged:
   - src/backend/features/auth/auth_service.py
   - docs/backend/authentication.md

🧪 [1/4] Vérif de la couverture de tests...
   ✅ Check de couverture de tests terminé

🔌 [2/4] Vérif de la doc des endpoints API...
   ✅ Check de doc API terminé

📚 [3/4] Lancement d'Anima (DocKeeper)...
   ✅ Anima terminé - aucun gap de documentation détecté

🔐 [4/4] Lancement de Neo (IntegrityWatcher)...
   ✅ Neo terminé - intégrité OK

====================================================
✅ Validation pre-commit passée sans problème!

[main abc1234] feat: add JWT authentication
 2 files changed, 45 insertions(+), 2 deletions(-)

🎯 ÉMERGENCE Guardian: Feedback Post-Commit
=============================================================

📝 Commit: abc1234
   Message: feat: add JWT authentication

🎯 Génération du rapport unifié (Nexus Coordinator)...
   ✅ Rapport Nexus généré

📊 RÉSUMÉ DES VÉRIFICATIONS
-------------------------------------------------------------
📚 Anima (DocKeeper) - Documentation:
   ✅ Status: OK - Aucun gap de documentation

🔐 Neo (IntegrityWatcher) - Intégrité:
   ✅ Status: OK - Intégrité vérifiée

🎯 Nexus (Coordinator) - Rapport Unifié:
   📋 All systems operational - no issues detected
   📄 Rapport complet: .../unified_report.json

=============================================================
✅ Guardian Post-Commit terminé!

📋 Rapports disponibles:
   - Anima:  .../docs_report.json
   - Neo:    .../integrity_report.json
   - Nexus:  .../unified_report.json
```

---

## 📊 Rapports Générés

### Emplacement
```
claude-plugins/integrity-docs-guardian/reports/
├── docs_report.json           # Anima - Gaps de documentation
├── integrity_report.json      # Neo - Intégrité backend/frontend
├── prod_report.json           # ProdGuardian - État production
├── unified_report.json        # Nexus - Rapport consolidé
└── orchestration_report.json  # Orchestrateur - Stats d'exécution
```

### Rapports Consolidés (Scheduler)
```
claude-plugins/integrity-docs-guardian/reports/
└── consolidated_report_YYYYMMDD_HHMMSS.json  # Rapports historiques
```

### Logs
```
claude-plugins/integrity-docs-guardian/logs/
├── scheduler.log                    # Logs du scheduler
└── unified_scheduler_YYYY-MM.log   # Logs mensuels détaillés
```

---

## 🛠️ Commandes Utiles

### Vérification Manuelle

```bash
# Tester Anima (Documentation)
python claude-plugins/integrity-docs-guardian/scripts/scan_docs.py

# Tester Neo (Intégrité)
python claude-plugins/integrity-docs-guardian/scripts/check_integrity.py

# Tester ProdGuardian (Production)
python claude-plugins/integrity-docs-guardian/scripts/check_prod_logs.py

# Tester Theia (Coûts IA)
python claude-plugins/integrity-docs-guardian/scripts/analyze_ai_costs.py

# Générer rapport unifié
python claude-plugins/integrity-docs-guardian/scripts/generate_report.py

# Lancer orchestrateur complet
python claude-plugins/integrity-docs-guardian/scripts/auto_orchestrator.py

# Configuration et test
python claude-plugins/integrity-docs-guardian/scripts/setup_automation.py
```

### Bypass des Hooks (Déconseillé)

```bash
# Skip tous les hooks pour un commit
git commit --no-verify -m "message"

# Skip le pre-push hook
git push --no-verify
```

### Voir les Rapports

```bash
# Rapport complet avec jq (si installé)
jq . claude-plugins/integrity-docs-guardian/reports/unified_report.json

# Résumé rapide avec Python
python -c "import json; print(json.load(open('claude-plugins/integrity-docs-guardian/reports/unified_report.json'))['executive_summary']['headline'])"
```

---

## 🔧 Configuration Avancée

### Variables d'Environnement Disponibles

| Variable | Valeur | Description |
|----------|--------|-------------|
| `AUTO_UPDATE_DOCS` | 0/1 | Active la mise à jour auto de docs |
| `AUTO_APPLY` | 0/1 | Applique et commit auto les mises à jour |
| `CHECK_GIT_STATUS` | 0/1 | Vérifie changements non commités |
| `AGENT_CHECK_INTERVAL` | minutes | Intervalle du scheduler (défaut: 60) |
| `RUN_ONCE` | 0/1 | Mode one-shot du scheduler |
| `GCP_PROJECT_ID` | string | Projet GCP pour ProdGuardian |

### Personnalisation des Hooks

Les hooks sont dans `.git/hooks/` :
- `pre-commit` - Peut être modifié pour ajuster les vérifications
- `post-commit` - Peut être modifié pour personnaliser le feedback
- `pre-push` - Peut être modifié pour ajuster les seuils de blocage

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [AUTOMATION_GUIDE.md](AUTOMATION_GUIDE.md) | Guide complet d'automatisation |
| [QUICKSTART_PHASE3.md](QUICKSTART_PHASE3.md) | Démarrage rapide Phase 3 |
| [HIDDEN_MODE_GUIDE.md](HIDDEN_MODE_GUIDE.md) | Monitoring silencieux continu |
| [GUIDE_TASK_SCHEDULER.md](GUIDE_TASK_SCHEDULER.md) | Config Windows Task Scheduler |
| [AUTO_ORCHESTRATION.md](AUTO_ORCHESTRATION.md) | Détails orchestration auto |
| [README.md](README.md) | Documentation principale |

---

## 🚨 Troubleshooting

### Problème : Hooks ne s'exécutent pas

**Solution :**
```bash
# Vérifier présence
ls -la .git/hooks/

# Sur Linux/Mac, rendre exécutables
chmod +x .git/hooks/pre-commit
chmod +x .git/hooks/post-commit
chmod +x .git/hooks/pre-push

# Re-tester
python claude-plugins/integrity-docs-guardian/scripts/setup_automation.py
```

### Problème : ProdGuardian échoue

**Cause :** `gcloud` CLI non installé ou non authentifié

**Solution :**
```bash
# Installer Google Cloud SDK
# https://cloud.google.com/sdk/docs/install

# S'authentifier
gcloud auth login

# Tester
gcloud logging read --limit 1
```

### Problème : Scheduler skip toujours

**Cause :** Changements non commités détectés

**Solution :**
```bash
# Option 1 : Commit les changements
git add . && git commit -m "wip"

# Option 2 : Ignorer les changements
export CHECK_GIT_STATUS=0
python claude-plugins/integrity-docs-guardian/scripts/scheduler.py
```

---

## 📈 Prochaines Étapes

1. **Tester l'automatisation** avec un commit
2. **Consulter les rapports** générés
3. **Optionnel :** Activer `AUTO_UPDATE_DOCS=1`
4. **Optionnel :** Configurer le monitoring continu (Task Scheduler)
5. **Optionnel :** Intégrer dans CI/CD

---

## 🎉 Statut Final

✅ **Système Guardian Phase 3 : OPÉRATIONNEL**

- ✅ Hooks Git actifs et fonctionnels
- ✅ Tous les agents déployés et testés
- ✅ Rapports automatiques configurés
- ✅ Documentation complète disponible
- ✅ Prêt pour automatisation complète

**🚀 Prochain commit déclenchera automatiquement tous les agents !**

---

**Dernière vérification :** 2025-10-17
**Testé sur :** Windows 11, Python 3.11, Git Bash
