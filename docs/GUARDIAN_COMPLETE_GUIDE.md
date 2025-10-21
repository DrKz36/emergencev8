# 🛡️ GUARDIAN SYSTEM - GUIDE COMPLET

**Système de monitoring automatique multi-agents pour garantir la qualité, l'intégrité et la stabilité d'Émergence V8.**

**Version:** 3.1.0 (Documentation consolidée)
**Dernière mise à jour:** 2025-10-21

---

## 📖 Table des Matières

1. [Vue d'Ensemble](#-vue-densemble)
2. [Agents Guardian](#-agents-guardian-détaillés)
3. [Installation & Activation](#-installation--activation)
4. [Workflows Automatiques](#-workflows-automatiques)
5. [Rapports](#-rapports-générés)
6. [Commandes Utiles](#-commandes-utiles)
7. [Troubleshooting](#-troubleshooting)
8. [Plans Cloud (Futur)](#-plans-cloud-futur)
9. [FAQ](#-faq)

---

## 📋 Vue d'Ensemble

### Système Multi-Agents

Le système Guardian est composé de **6 agents spécialisés** qui surveillent différents aspects du projet :

| Agent | Rôle | Trigger | Rapport |
|-------|------|---------|---------|
| **ANIMA** (DocKeeper) | Vérifie gaps documentation, sync versioning | Pre-commit, Manuel | `docs_report.json` |
| **NEO** (IntegrityWatcher) | Vérifie cohérence backend/frontend, schemas | Pre-commit, Manuel | `integrity_report.json` |
| **NEXUS** (Coordinator) | Agrège Anima+Neo, priorise issues (P0-P4) | Post-commit, Manuel | `unified_report.json` |
| **PRODGUARDIAN** | Monitore Cloud Run logs, erreurs production | Pre-push, Scheduler (6h), Manuel | `prod_report.json` |
| **ARGUS** | Analyse dev logs temps réel, patterns erreurs | Manuel uniquement | `dev_logs_report.json` |
| **THEIA** | Analyse coûts AI (Claude, OpenAI) | Disabled (optionnel) | `cost_report.json` |

### Architecture Globale

```
┌─────────────────────────────────────────────────────────────┐
│                   ÉMERGENCE V8 PROJECT                       │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Git Hooks (Automatiques)                                    │
│  ┌────────────────┬────────────────┬─────────────────────┐  │
│  │ Pre-Commit     │ Post-Commit    │ Pre-Push            │  │
│  │ • Anima (Doc)  │ • Nexus (Sync) │ • ProdGuardian      │  │
│  │ • Neo (Integ)  │ • Auto-update  │ • Codex Summary     │  │
│  └────────────────┴────────────────┴─────────────────────┘  │
│                                                               │
│  Task Scheduler (Background - 6h)                            │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ EMERGENCE_Guardian_ProdMonitor                        │   │
│  │ • ProdGuardian → Check Cloud Run logs                │   │
│  │ • Génère reports/prod_report.json                     │   │
│  │ • (Optionnel) Email si CRITICAL                       │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
│  Rapports (reports/)                                         │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ • prod_report.json (Production)                       │   │
│  │ • docs_report.json (Documentation)                    │   │
│  │ • integrity_report.json (Intégrité)                   │   │
│  │ • unified_report.json (Vue unifiée)                   │   │
│  │ • global_report.json (Master Orchestrator)            │   │
│  │ • codex_summary.md (Résumé pour agents IA)            │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 🤖 Agents Guardian Détaillés

### 2.1 ANIMA (DocKeeper)

**Responsabilités:**
- Détecte gaps documentation (docstrings manquantes, README obsolètes)
- **Source de vérité versioning:** `src/version.js`
- Synchronise vers `package.json`, `CHANGELOG.md`, `ROADMAP_OFFICIELLE.md`
- Vérifie cohérence documentation architecture (C4 model)

**Fichier:** `scan_docs.py` (350 LOC)

**Commande manuelle:**
```bash
python claude-plugins/integrity-docs-guardian/scripts/scan_docs.py
```

**Exemple de détection:**
```json
{
  "gaps_found": 3,
  "high_priority": [
    {
      "file": "src/backend/features/chat/router.py",
      "issue": "API endpoint /chat/message non documenté",
      "recommendation": "Ajouter docstring avec exemple"
    }
  ]
}
```

---

### 2.2 NEO (IntegrityWatcher)

**Responsabilités:**
- Vérifie cohérence backend Python ↔ frontend JavaScript
- Valide schemas JSON (API contracts)
- Détecte breaking changes entre versions
- Analyse dépendances circulaires

**Fichier:** `check_integrity.py` (398 LOC)

**Commande manuelle:**
```bash
python claude-plugins/integrity-docs-guardian/scripts/check_integrity.py
```

**Vérifications:**
- Cohérence endpoints API backend ↔ frontend
- Validation schémas `openapi.json`
- Détection imports circulaires
- Vérification contrats API

---

### 2.3 NEXUS (Coordinator)

**Responsabilités:**
- Agrège rapports ANIMA + NEO
- Priorise issues (P0 critical → P4 nice-to-have)
- Génère executive summary
- Détecte conflits entre recommandations agents

**Fichier:** `generate_report.py` (332 LOC)

**Commande manuelle:**
```bash
python claude-plugins/integrity-docs-guardian/scripts/generate_report.py
```

**Priorités:**
- **P0:** CRITICAL - Bloque production
- **P1:** HIGH - Fix avant release
- **P2:** MEDIUM - Fix semaine en cours
- **P3:** LOW - Backlog
- **P4:** NICE_TO_HAVE - Optionnel

---

### 2.4 PRODGUARDIAN

**Responsabilités:**
- Monitore logs Cloud Run (emergence-app)
- Détecte erreurs 500, 400, OOMKilled, timeout
- Analyse patterns d'erreurs (spikes, fréquence)
- Génère alertes si état CRITICAL

**Fichier:** `check_prod_logs.py` (357 LOC)

**Commande manuelle:**
```bash
python claude-plugins/integrity-docs-guardian/scripts/check_prod_logs.py
```

**Status Levels:**

#### 🟢 OK (Code: 0)
- Aucune erreur détectée dans la dernière heure
- Latence normale
- Aucune révision unhealthy
- Utilisation mémoire < 70%

**Exemple:**
```
🟢 Production Status: OK

📊 Summary:
   - Logs analyzed: 80
   - Errors: 0
   - Warnings: 0
   - Critical signals: 0
   - Latency issues: 0

💡 Recommendations:
   🟢 [LOW] No immediate action required
      Production is healthy
```

#### 🟡 DEGRADED (Code: 1)
- 1-5 erreurs détectées
- 3+ warnings présents
- Latence élevée (mais < 3s)
- Utilisation mémoire 70-90%

**Actions:** Surveiller de près, investiguer dans les 1-2 heures

#### 🔴 CRITICAL (Code: 2)
- 5+ erreurs détectées
- OOMKilled ou container crashes
- Révisions unhealthy
- Health check failures
- Latence sévère (> 3s)

**Actions:** Action immédiate requise !

**Exemple:**
```
🔴 Production Status: CRITICAL

📊 Summary:
   - Errors: 12
   - Critical signals: 2

❌ Critical Issues:
   [2025-10-21T15:47:23Z] OOM
      Container exceeded memory limit (OOMKilled)

💡 Recommendations:
   🔴 [HIGH] Increase memory limit
      Command: gcloud run services update emergence-app --memory=2Gi --region=europe-west1
```

---

### 2.5 ARGUS (DevLogs Analyzer)

**Responsabilités:**
- Analyse logs dev backend (`logs/backend_*.log`)
- Détecte patterns d'erreurs récurrents
- Track performance dégradée
- Suggestions optimisation

**Fichier:** `argus_analyzer.py` (495 LOC)

**Commande manuelle:**
```bash
python claude-plugins/integrity-docs-guardian/scripts/argus_analyzer.py
```

**Note:** Manuel uniquement (pas de hook auto)

---

### 2.6 THEIA (AI Cost Analyzer)

**Responsabilités:**
- Analyse coûts API Claude/OpenAI
- Track tokens utilisés par feature
- Suggère optimisations cost
- Projections budget mensuel

**Fichier:** `analyze_ai_costs.py` (720 LOC)

**Status:** **DISABLED** (trop de données à traiter)

**Réactivation:**
```json
// claude-plugins/integrity-docs-guardian/config/guardian_config.json
{
  "agents": {
    "theia": {
      "enabled": true
    }
  }
}
```

---

## 🚀 Installation & Activation

### 3.1 Installation Rapide (Recommandée)

```powershell
cd c:\dev\emergenceV8\claude-plugins\integrity-docs-guardian\scripts
.\setup_guardian.ps1
```

**Ce que fait ce script:**
- ✅ Configure les **Git Hooks** (pre-commit, post-commit, pre-push)
- ✅ Active **Auto-update documentation** après chaque commit
- ✅ Crée **Task Scheduler** pour monitoring prod toutes les 6h
- ✅ Teste que tous les agents fonctionnent

### 3.2 Configuration Avancée

```powershell
# Monitoring prod toutes les 2h au lieu de 6h
.\setup_guardian.ps1 -IntervalHours 2

# Avec email des rapports
.\setup_guardian.ps1 -EmailTo "admin@example.com"

# Désactiver complètement Guardian
.\setup_guardian.ps1 -Disable
```

### 3.3 Vérification Installation

**1. Vérifier les hooks Git:**
```bash
ls -la .git/hooks/
# Doit afficher: pre-commit, post-commit, pre-push
```

**2. Vérifier la tâche planifiée:**
```powershell
Get-ScheduledTask -TaskName "EMERGENCE_Guardian_ProdMonitor"
```

**3. Test manuel:**
```powershell
cd claude-plugins/integrity-docs-guardian/scripts
.\run_audit.ps1
```

---

## 🔄 Workflows Automatiques

### 4.1 Pre-Commit Hook (BLOQUANT)

**Déclenché:** Avant chaque commit

**Agents exécutés:**
1. **ANIMA** - Documentation gaps, versioning sync
2. **NEO** - Intégrité backend/frontend, schemas cohérents

**Comportement:**
- ✅ **Commit autorisé** si aucun problème critique
- ⚠️ **Warnings affichés** mais commit autorisé
- 🚨 **Commit BLOQUÉ** si erreurs critiques d'intégrité

**Bypass (urgence uniquement):**
```bash
git commit --no-verify -m "fix urgent"
```

**Exemple de feedback:**
```
🛡️  Guardian Pre-Commit Check...
📚 Anima (DocKeeper)...
✅ Report generated: reports/docs_report.json
📊 Summary: 0 documentation gap(s) found

🔍 Neo (IntegrityWatcher)...
✅ Report generated: reports/integrity_report.json
📊 Summary: No changes detected

✅ Guardian: Pre-commit OK
```

---

### 4.2 Post-Commit Hook (Non-bloquant)

**Déclenché:** Après chaque commit

**Actions:**
1. **NEXUS** - Génère rapport unifié Anima + Neo
2. **Auto-update docs** - Met à jour CHANGELOG.md, ROADMAP si besoin
3. **Codex Summary** - Génère `reports/codex_summary.md`

**Variables d'environnement:**

**`AUTO_UPDATE_DOCS`** (optionnel)
```bash
# Active l'analyse et proposition de mises à jour de documentation
export AUTO_UPDATE_DOCS=1
```

**`AUTO_APPLY`** (optionnel, nécessite AUTO_UPDATE_DOCS=1)
```bash
# Applique ET commit automatiquement les mises à jour de docs
export AUTO_APPLY=1
```

**⚠️ Attention:** En mode `AUTO_APPLY=1`, un commit peut générer un commit automatique de documentation.

**Exemple de feedback:**
```
🛡️  Guardian Post-Commit...
📊 Nexus (Coordinator)...
✅ Unified report generated: reports/unified_report.json

📊 Executive Summary:
   Status: OK
   ✅ All checks passed - no issues detected

📝 Codex Summary...
✅ Résumé généré: reports/codex_summary.md

📝 Auto-update docs...
✅ Aucune mise à jour de documentation nécessaire

✅ Guardian: Post-commit OK
```

---

### 4.3 Pre-Push Hook (BLOQUANT Production)

**Déclenché:** Avant chaque push vers `main`

**Actions:**
1. **PRODGUARDIAN** - Vérifie état production Cloud Run
2. **Si status CRITICAL → Push BLOQUÉ** ❌

**Comportement:**
- ✅ **Push autorisé** si production OK
- ⚠️ **Warnings affichés** si production dégradée mais push autorisé
- 🚨 **Push BLOQUÉ** si production en état CRITICAL

**Bypass (déconseillé):**
```bash
git push --no-verify
```

**Exemple de feedback:**
```
🛡️  Guardian Pre-Push Check...
☁️  ProdGuardian...

🟢 Production Status: OK

📊 Summary:
   - Logs analyzed: 80
   - Errors: 0
   - Warnings: 0
   - Critical signals: 0

✅ Guardian: Pre-push OK
```

---

### 4.4 Task Scheduler (Background)

**⚠️ IMPORTANT (2025-10-21): Tâche unique !**

**Tâche active:** `EMERGENCE_Guardian_ProdMonitor`

**Configuration:**
- **Fréquence:** Toutes les 6h
- **Agents:** PRODGUARDIAN uniquement
- **Rapports:** `reports/prod_report.json`
- **Email:** (Optionnel) Si erreurs critiques

**Tâches redondantes supprimées:**
- ~~`Guardian-ProdCheck`~~
- ~~`Guardian_EmailReports`~~
- ~~`ProdGuardian_AutoMonitor`~~

**Gestion:**

```powershell
# Consulter le statut
Get-ScheduledTask -TaskName "EMERGENCE_Guardian_ProdMonitor" | Get-ScheduledTaskInfo

# Exécuter manuellement
Start-ScheduledTask -TaskName "EMERGENCE_Guardian_ProdMonitor"

# Désactiver temporairement
Disable-ScheduledTask -TaskName "EMERGENCE_Guardian_ProdMonitor"

# Réactiver
Enable-ScheduledTask -TaskName "EMERGENCE_Guardian_ProdMonitor"

# Modifier la fréquence (exemple: 2h)
$Trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Hours 2)
Set-ScheduledTask -TaskName "EMERGENCE_Guardian_ProdMonitor" -Trigger $Trigger
```

---

## 📊 Rapports Générés

### 5.1 Emplacements (IMPORTANT!)

**⚠️ POUR LES AGENTS IA (Claude Code, Codex GPT): LISEZ CETTE SECTION !**

**Les rapports Guardian sont LOCAUX dans le dépôt Git, PAS dans le cloud !**

Quand on vous demande "vérifie les rapports Guardian", vous devez **juste lire les fichiers JSON locaux** - pas besoin de se connecter à Cloud Run ou aux jobs planifiés.

**Tous les rapports sont maintenant dans `reports/` (racine du projet):**

| Fichier | Agent | Contenu |
|---------|-------|---------|
| `prod_report.json` | PRODGUARDIAN | État production (erreurs, warnings, latence) |
| `docs_report.json` | ANIMA | Gaps documentation, versioning |
| `integrity_report.json` | NEO | Intégrité backend/frontend |
| `unified_report.json` | NEXUS | Vue unifiée Anima + Neo, priorisation issues |
| `global_report.json` | Master Orchestrator | Rapport global tous agents |
| `codex_summary.md` | Auto-généré | Résumé markdown pour agents IA (Codex GPT) |
| `ai_model_cost_audit_*.json` | THEIA (optionnel) | Analyse coûts AI |

**Rapports archivés:** `reports/archive/` (rapports obsolètes/historiques)

**Ancien emplacement supprimé:** ~~`claude-plugins/integrity-docs-guardian/reports/`~~ (plus de duplication!)

---

### 5.2 Comment Accéder aux Rapports (Agents IA)

**❌ NE PAS FAIRE:**
```
"Je n'ai pas accès à Cloud Run ni aux jobs planifiés..."
"Je ne peux pas récupérer les rapports Guardian en temps réel..."
```

**✅ FAIRE:**

#### Option 1: Résumé Markdown (RECOMMANDÉ)

```python
# Résumé narratif exploitable pour LLM
with open('c:/dev/emergenceV8/reports/codex_summary.md', 'r', encoding='utf-8') as f:
    summary = f.read()

print(summary)
```

**Ce fichier contient:**
- ✅ Vue d'ensemble tous les Guardians (Production, Docs, Intégrité)
- ✅ Insights actionnables avec contexte
- ✅ Code snippets des fichiers avec erreurs
- ✅ Patterns d'erreurs (endpoints, types, fichiers)
- ✅ Recommandations prioritaires avec commandes gcloud
- ✅ Commits récents (contexte pour identifier coupables)
- ✅ Actions prioritaires ("Que faire maintenant ?")

#### Option 2: Rapports JSON Bruts (Détails)

```python
# Python
import json
with open('c:/dev/emergenceV8/reports/prod_report.json', 'r', encoding='utf-8') as f:
    prod = json.load(f)

with open('c:/dev/emergenceV8/reports/docs_report.json', 'r', encoding='utf-8') as f:
    docs = json.load(f)

with open('c:/dev/emergenceV8/reports/integrity_report.json', 'r', encoding='utf-8') as f:
    integrity = json.load(f)

with open('c:/dev/emergenceV8/reports/unified_report.json', 'r', encoding='utf-8') as f:
    unified = json.load(f)
```

```javascript
// JavaScript/Node.js
const fs = require('fs');
const prod = JSON.parse(fs.readFileSync('c:/dev/emergenceV8/reports/prod_report.json', 'utf-8'));
```

```powershell
# PowerShell
$prod = Get-Content 'c:\dev\emergenceV8\reports\prod_report.json' -Raw | ConvertFrom-Json
```

**Ces fichiers sont mis à jour automatiquement par:**
- Git Hooks (pre-commit, post-commit, pre-push)
- Task Scheduler Windows (toutes les 6h)
- Scripts manuels (`.\run_audit.ps1`)

**Donc: PAS BESOIN d'aller chercher dans le cloud - tout est local et à jour ! 🔥**

---

### 5.3 Structure des Rapports

**Rapport Typique (JSON):**
```json
{
  "metadata": {
    "timestamp": "2025-10-21T14:30:00",
    "agent": "prodguardian",
    "version": "3.1.0"
  },
  "summary": {
    "status": "OK",
    "total_issues": 0,
    "critical": 0,
    "warnings": 0,
    "errors": 0
  },
  "errors_detailed": [],
  "recommendations": [
    {
      "priority": "LOW",
      "action": "No immediate action required",
      "details": "Production is healthy"
    }
  ]
}
```

**Champs Utiles dans prod_report.json:**
- `errors_detailed`: Liste erreurs avec full context (endpoint, file, line, stack trace)
- `error_patterns.by_endpoint`: Endpoints les plus affectés
- `error_patterns.by_file`: Fichiers les plus affectés
- `code_snippets`: Code source avec numéros de ligne
- `recent_commits`: 5 derniers commits (potentiels coupables)
- `recommendations`: Actions prioritaires avec commandes gcloud

---

### 5.4 Génération du Résumé Codex

Le résumé `codex_summary.md` est généré par:

```bash
python scripts/generate_codex_summary.py
```

**Mise à jour automatique:**
- ✅ Hooks Git (post-commit, pre-push)
- ✅ Task Scheduler (toutes les 6h)

**Mise à jour manuelle:**
```bash
cd c:/dev/emergenceV8
python scripts/generate_codex_summary.py
```

---

## 🔧 Commandes Utiles

### 6.1 Audit Manuel Global

Pour lancer un audit complet de l'application (tous les agents):

```powershell
cd c:\dev\emergenceV8\claude-plugins\integrity-docs-guardian\scripts
.\run_audit.ps1
```

**Agents exécutés (dans l'ordre):**
1. ANIMA (DocKeeper)
2. NEO (IntegrityWatcher)
3. PRODGUARDIAN (Cloud Run)
4. ARGUS (DevLogs) - si disponible
5. NEXUS (Coordinator)
6. Master Orchestrator (Global)

**Avec email du rapport:**
```powershell
.\run_audit.ps1 -EmailReport -EmailTo "admin@example.com"
```

---

### 6.2 Tests Individuels Agents

```bash
# Anima (DocKeeper)
python claude-plugins/integrity-docs-guardian/scripts/scan_docs.py

# Neo (IntegrityWatcher)
python claude-plugins/integrity-docs-guardian/scripts/check_integrity.py

# Nexus (Coordinator)
python claude-plugins/integrity-docs-guardian/scripts/generate_report.py

# ProdGuardian
python claude-plugins/integrity-docs-guardian/scripts/check_prod_logs.py

# Argus (DevLogs)
python claude-plugins/integrity-docs-guardian/scripts/argus_analyzer.py
```

---

### 6.3 Régénérer Codex Summary

```bash
python scripts/generate_codex_summary.py
```

---

### 6.4 Gestion Task Scheduler

```powershell
# Consulter le statut
Get-ScheduledTask -TaskName "EMERGENCE_Guardian_ProdMonitor" | Get-ScheduledTaskInfo

# Exécuter manuellement
Start-ScheduledTask -TaskName "EMERGENCE_Guardian_ProdMonitor"

# Désactiver temporairement
Disable-ScheduledTask -TaskName "EMERGENCE_Guardian_ProdMonitor"

# Réactiver
Enable-ScheduledTask -TaskName "EMERGENCE_Guardian_ProdMonitor"

# Modifier la fréquence (exemple: 2h)
$Trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Hours 2)
Set-ScheduledTask -TaskName "EMERGENCE_Guardian_ProdMonitor" -Trigger $Trigger

# Supprimer la tâche
Unregister-ScheduledTask -TaskName "EMERGENCE_Guardian_ProdMonitor" -Confirm:$false
```

---

## 🐛 Troubleshooting

### 7.1 Hooks Git ne se Déclenchent Pas

**Vérifier permissions (Unix/Mac/Linux):**
```bash
ls -la .git/hooks/
# Les hooks doivent être exécutables
chmod +x .git/hooks/pre-commit
chmod +x .git/hooks/post-commit
chmod +x .git/hooks/pre-push
```

**Sur Windows:** Git Bash gère les permissions automatiquement.

**Vérifier contenu des hooks:**
```bash
cat .git/hooks/pre-commit
# Doit appeler les scripts Guardian
```

---

### 7.2 "Lock Acquisition Timeout"

**Cause:** Un autre agent Guardian tourne déjà

**Solution:**
```bash
# Supprimer le lock manuellement (si agent crashé)
rm claude-plugins/integrity-docs-guardian/.guardian_lock
```

---

### 7.3 ProdGuardian Échoue avec "gcloud not found"

**Solutions:**
1. **Installer Google Cloud SDK:**
   - Windows: https://cloud.google.com/sdk/docs/install
   - macOS: `brew install --cask google-cloud-sdk`
   - Linux: `curl https://sdk.cloud.google.com | bash`

2. **Authentifier:**
   ```bash
   gcloud auth login
   gcloud config set project emergence-469005
   ```

3. **Tester accès:**
   ```bash
   gcloud run services describe emergence-app --region=europe-west1
   ```

4. **Ou désactiver vérif prod en skippant pre-push:**
   ```bash
   git push --no-verify
   ```

---

### 7.4 Rapports Pas Générés

**Vérifier permissions écriture:**
```bash
# Vérifier que reports/ est accessible en écriture
touch reports/test.txt && rm reports/test.txt
```

**Vérifier encoding (Windows):**
```powershell
# Définir encoding UTF-8
$env:PYTHONIOENCODING="utf-8"
```

**Exécuter agent en mode verbose:**
```bash
python claude-plugins/integrity-docs-guardian/scripts/check_prod_logs.py --verbose
```

---

### 7.5 Task Scheduler Ne S'Exécute Pas

**Cause:** Droits admin requis sur certaines versions Windows

**Solution:**
```powershell
# Exécuter PowerShell en admin
.\setup_guardian.ps1 -IntervalHours 6
```

**Vérifier la tâche:**
```powershell
Get-ScheduledTask -TaskName "EMERGENCE_Guardian_ProdMonitor"
```

**Consulter l'historique:**
```powershell
Get-ScheduledTaskInfo -TaskName "EMERGENCE_Guardian_ProdMonitor"
```

**Ouvrir le Planificateur de tâches:**
```powershell
taskschd.msc
```

---

### 7.6 Erreur "Python not found" dans les Hooks

**Solution:**
Les hooks cherchent Python dans le venv. Assure-toi que:
- `.venv/Scripts/python.exe` existe (Windows)
- `.venv/bin/python` existe (Unix)

**Vérifier:**
```bash
.venv/Scripts/python.exe --version  # Windows
.venv/bin/python --version          # Unix
```

---

### 7.7 Trop de Rapports Générés

**Nettoyage automatique:**
Les anciens rapports (> 30 jours) sont automatiquement archivés dans `reports/archive/`

**Nettoyage manuel:**
```bash
# Supprimer rapports anciens
rm reports/archive/*
```

---

## 📚 Plans Cloud (Futur)

**Objectif:** Dupliquer le système Guardian local sur Cloud Run pour monitoring production 24/7

### Architecture Cible

```
Cloud Run Guardian (Nouveau service)
├── Endpoints:
│   ├── /health (liveness/readiness)
│   ├── /api/guardian/run-audit (trigger manuel)
│   └── /api/guardian/reports (consultation rapports)
│
├── Cloud Scheduler (toutes les 2h):
│   └── Trigger PRODGUARDIAN + NEXUS
│
├── Rapports stockés:
│   ├── Cloud Storage (bucket: emergence-guardian-reports)
│   └── Firestore (metadata, alertes)
│
└── Alerting:
    ├── Email (SendGrid) si CRITICAL
    └── Slack webhook (optionnel)
```

### Agents Cloud vs Local

| Agent | Local | Cloud Run |
|-------|-------|-----------|
| ANIMA | Pre-commit (dev) | ❌ N/A (code source local) |
| NEO | Pre-commit (dev) | ❌ N/A (code source local) |
| NEXUS | Post-commit | ✅ Cloud Scheduler (2h) |
| PRODGUARDIAN | Pre-push + 6h | ✅ Cloud Scheduler (2h) + Endpoint |
| ARGUS | Manuel | ✅ Cloud Logs analysis |
| THEIA | Disabled | ✅ BigQuery cost analysis |

**Fonctionnalités Prévues:**
- Service Cloud Run `emergence-guardian-service`
- Monitoring 24/7 (toutes les 2h)
- Cloud Storage pour rapports
- Gmail API pour Codex
- Usage Tracking
- Trigger manuel depuis Admin UI

**Status:** 📋 PLANIFICATION (pas encore implémenté)

**Documents de Référence:**
- [GUARDIAN_CLOUD_IMPLEMENTATION_PLAN.md](../GUARDIAN_CLOUD_IMPLEMENTATION_PLAN.md) (v2.0.0)
- [GUARDIAN_CLOUD_MIGRATION.md](../GUARDIAN_CLOUD_MIGRATION.md) (v1.0.0)

**Timeline:** Phase 3 (après consolidation documentation + CI/CD)

---

## ❓ FAQ

### 9.1 Pourquoi il y avait plusieurs emplacements de rapports ?

**Avant (Phase 1):**
- `reports/` (racine)
- `claude-plugins/integrity-docs-guardian/reports/` (doublons!)

**Maintenant (Phase 1 ✅):**
- `reports/` (racine) - **UNIQUE**

**Résultat:** Plus de confusion, une seule source de vérité.

---

### 9.2 Comment Codex GPT accède aux rapports ?

**Réponse:** Codex lit `reports/codex_summary.md` localement via Python:

```python
with open('c:/dev/emergenceV8/reports/codex_summary.md', 'r', encoding='utf-8') as f:
    print(f.read())
```

**PAS besoin de Cloud Run, Gmail API, ou jobs planifiés.**

---

### 9.3 Puis-je Désactiver Guardian ?

**Oui:**
```powershell
.\setup_guardian.ps1 -Disable
```

**Cela va:**
- Désactiver tous les hooks Git
- Supprimer la tâche planifiée

**Pour réactiver:**
```powershell
.\setup_guardian.ps1
```

---

### 9.4 Quelle est la Différence entre les Agents ?

| Critère | ANIMA | NEO | NEXUS | PRODGUARDIAN | ARGUS | THEIA |
|---------|-------|-----|-------|--------------|-------|-------|
| **Focus** | Documentation | Intégrité | Coordination | Production | Dev Logs | Coûts AI |
| **Trigger** | Pre-commit | Pre-commit | Post-commit | Pre-push + 6h | Manuel | Disabled |
| **Bloquant** | ✅ Oui | ✅ Oui | ❌ Non | ✅ Oui (Pre-push) | ❌ Non | ❌ Non |
| **Rapport** | docs_report.json | integrity_report.json | unified_report.json | prod_report.json | dev_logs_report.json | cost_report.json |
| **Cible** | Code local | Code local | Rapports | Cloud Run | Logs locaux | BigQuery |

---

### 9.5 Comment Modifier la Fréquence du Monitoring Prod ?

**Modifier la tâche Task Scheduler:**

```powershell
# Changer pour 2 heures
$Trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Hours 2)
Set-ScheduledTask -TaskName "EMERGENCE_Guardian_ProdMonitor" -Trigger $Trigger

# Changer pour 1 heure
$Trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Hours 1)
Set-ScheduledTask -TaskName "EMERGENCE_Guardian_ProdMonitor" -Trigger $Trigger

# Changer pour 15 minutes
$Trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 15)
Set-ScheduledTask -TaskName "EMERGENCE_Guardian_ProdMonitor" -Trigger $Trigger
```

---

### 9.6 Les Hooks Bloquent Mon Commit, Que Faire ?

**Option 1 (Recommandée): Corriger les Erreurs**
- Consulter les rapports détaillés
- Corriger les issues détectées
- Re-committer

**Option 2 (Urgence): Bypass**
```bash
git commit --no-verify -m "fix urgent"
```

**⚠️ Attention:** Ne pas abuser du bypass, les erreurs peuvent causer des problèmes en production.

---

### 9.7 Comment Activer les Emails Automatiques ?

**1. Ajouter credentials dans `.env`:**
```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password  # App password, pas mot de passe compte
```

**2. Activer dans config:**
```json
// claude-plugins/integrity-docs-guardian/config/guardian_config.json
{
  "email_notifications": {
    "enabled": true,
    "recipients": ["admin@example.com"],
    "on_critical_only": true  // Seulement si status CRITICAL
  }
}
```

**3. Test manuel:**
```bash
python claude-plugins/integrity-docs-guardian/scripts/send_guardian_reports_email.py
```

---

### 9.8 Guardian Consomme Trop de Ressources

**Solutions:**

**1. Augmenter l'intervalle Task Scheduler:**
```powershell
# Passer de 6h à 12h
$Trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Hours 12)
Set-ScheduledTask -TaskName "EMERGENCE_Guardian_ProdMonitor" -Trigger $Trigger
```

**2. Désactiver agents inutilisés:**
```json
// guardian_config.json
{
  "agents": {
    "argus": {
      "enabled": false  // Désactiver Argus
    },
    "theia": {
      "enabled": false  // Déjà désactivé
    }
  }
}
```

**3. Réduire fenêtre de logs ProdGuardian:**
```python
# Éditer check_prod_logs.py
FRESHNESS = "30m"  # Au lieu de "1h"
LIMIT = 50         # Au lieu de 80
```

---

## 📞 Support

**Documentation:**
- [CLAUDE.md](../../CLAUDE.md) - Configuration Claude Code
- [AGENTS.md](../../AGENTS.md) - Consignes générales agents
- [CODEV_PROTOCOL.md](../../CODEV_PROTOCOL.md) - Protocole multi-agents
- [docs/architecture/](../architecture/) - Architecture C4

**Logs:**
- `claude-plugins/integrity-docs-guardian/reports/orchestrator.log`
- `claude-plugins/integrity-docs-guardian/logs/scheduler.log` (si Task Scheduler)

**Contact:**
- Architecte: Fernando Gonzales (gonzalefernando@gmail.com)

---

## 🎉 Résumé

**Guardian System 3.1.0 = Clean, Simple, Puissant**

- ✅ **18 scripts PowerShell → 2 scripts** (`setup_guardian.ps1`, `run_audit.ps1`)
- ✅ **3 orchestrateurs Python → 1 seul** (`master_orchestrator.py`)
- ✅ **6 agents spécialisés** (Anima, Neo, Nexus, ProdGuardian, Argus, Theia)
- ✅ **Git Hooks automatiques** (pre-commit, post-commit, pre-push)
- ✅ **Monitoring production 24/7** (Task Scheduler 6h)
- ✅ **Email notifications** (optionnel)
- ✅ **Rapports JSON structurés** (consultation facile)
- ✅ **Documentation consolidée** (ce guide unique)

**Commandes Essentielles:**
```powershell
# Installation/Activation
.\setup_guardian.ps1

# Audit manuel complet
.\run_audit.ps1

# Désactivation
.\setup_guardian.ps1 -Disable
```

**C'est tout ! Le système tourne en arrière-plan et te prévient s'il y a des problèmes.** 🚀

---

**Dernière mise à jour:** 2025-10-21
**Version:** 3.1.0 (Documentation consolidée)
**Auteur:** Claude Code Agent
