# 🛡️ GUARDIAN SYSTEM - ÉMERGENCE V8

**Système de monitoring automatique multi-agents pour garantir la qualité, l'intégrité et la stabilité du projet.**

Version: **3.0.0** (Nettoyé et optimisé - 2025-10-19)

---

## 📋 VUE D'ENSEMBLE

Le système Guardian est composé de **6 agents spécialisés** qui surveillent différents aspects du projet :

| Agent | Rôle | Trigger | Rapport |
|-------|------|---------|---------|
| **ANIMA** (DocKeeper) | Vérifie gaps documentation, sync versioning | Pre-commit, Manuel | `docs_report.json` |
| **NEO** (IntegrityWatcher) | Vérifie cohérence backend/frontend, schemas | Pre-commit, Manuel | `integrity_report.json` |
| **NEXUS** (Coordinator) | Agrège Anima+Neo, priorise issues (P0-P4) | Post-commit, Manuel | `unified_report.json` |
| **PRODGUARDIAN** | Monitore Cloud Run logs, erreurs production | Pre-push, Scheduler (6h), Manuel | `prod_report.json` |
| **ARGUS** | Analyse dev logs temps réel, patterns erreurs | Manuel uniquement | `dev_logs_report.json` |
| **THEIA** | Analyse coûts AI (Claude, OpenAI) | Disabled (optionnel) | `cost_report.json` |

---

## 🚀 INSTALLATION & ACTIVATION

### Installation Rapide (Recommandé)

```powershell
cd c:\dev\emergenceV8\claude-plugins\integrity-docs-guardian\scripts
.\setup_guardian.ps1
```

**Ce que fait ce script :**
- ✅ Configure les **Git Hooks** (pre-commit, post-commit, pre-push)
- ✅ Active **Auto-update documentation** après chaque commit
- ✅ Crée **Task Scheduler** pour monitoring prod toutes les 6h
- ✅ Teste que tous les agents fonctionnent

### Options Avancées

```powershell
# Monitoring prod toutes les 2h au lieu de 6h
.\setup_guardian.ps1 -IntervalHours 2

# Avec email des rapports
.\setup_guardian.ps1 -EmailTo "admin@example.com"

# Désactiver complètement Guardian
.\setup_guardian.ps1 -Disable
```

---

## 🎯 WORKFLOWS AUTOMATIQUES

### Pre-Commit Hook (Bloquant)

Avant chaque commit, Guardian vérifie :

1. **ANIMA** - Documentation à jour, versioning sync
2. **NEO** - Intégrité backend/frontend, schemas cohérents

**Si erreur critique détectée → Commit BLOQUÉ** ❌

```bash
# Bypass en cas d'urgence (déconseillé)
git commit --no-verify -m "fix urgent"
```

### Post-Commit Hook (Non-bloquant)

Après chaque commit :

1. **NEXUS** - Génère rapport unifié Anima + Neo
2. **Auto-update docs** - Met à jour CHANGELOG.md, ROADMAP si besoin

### Pre-Push Hook (Bloquant Production)

Avant chaque push vers `main` :

1. **PRODGUARDIAN** - Vérifie état production Cloud Run
2. **Si status CRITICAL → Push BLOQUÉ** ❌

### Task Scheduler (Background)

**⚠️ IMPORTANT (2025-10-21) : Tâche unique !**

**Tâche active :** `EMERGENCE_Guardian_ProdMonitor`

**PRODGUARDIAN** s'exécute automatiquement toutes les 6h pour :
- Analyser logs Cloud Run (erreurs, warnings, OOMKilled)
- Détecter anomalies de trafic
- Générer rapport `prod_report.json` dans `reports/`
- **(Optionnel)** Envoyer email si erreurs critiques

**Tâches redondantes supprimées :**
- ~~`Guardian-ProdCheck`~~
- ~~`Guardian_EmailReports`~~
- ~~`ProdGuardian_AutoMonitor`~~

---

## 🔍 AUDIT MANUEL GLOBAL

Pour lancer un audit complet de l'application (tous les agents) :

```powershell
cd c:\dev\emergenceV8\claude-plugins\integrity-docs-guardian\scripts
.\run_audit.ps1
```

**Agents exécutés (dans l'ordre) :**
1. ANIMA (DocKeeper)
2. NEO (IntegrityWatcher)
3. PRODGUARDIAN (Cloud Run)
4. ARGUS (DevLogs) - si disponible
5. NEXUS (Coordinator)
6. Master Orchestrator (Global)

**Avec email du rapport :**
```powershell
.\run_audit.ps1 -EmailReport -EmailTo "admin@example.com"
```

---

## 📊 RAPPORTS GÉNÉRÉS

**⚠️ POUR LES AGENTS IA (Claude Code, Codex GPT) : LISEZ CETTE SECTION !**

**Les rapports Guardian sont LOCAUX dans le dépôt Git, PAS dans le cloud !**

Quand on vous demande "vérifie les rapports Guardian", vous devez **juste lire les fichiers JSON locaux** - pas besoin de se connecter à Cloud Run ou aux jobs planifiés.

### Emplacements des rapports

**⚠️ IMPORTANT (2025-10-21) : Structure unifiée !**

**Tous les rapports sont maintenant dans `reports/` (racine du projet)** :

| Fichier | Agent | Contenu |
|---------|-------|---------|
| `prod_report.json` | PRODGUARDIAN | État production (erreurs, warnings, latence) |
| `docs_report.json` | ANIMA | Gaps documentation, versioning |
| `integrity_report.json` | NEO | Intégrité backend/frontend |
| `unified_report.json` | NEXUS | Vue unifiée Anima + Neo, priorisation issues |
| `global_report.json` | Master Orchestrator | Rapport global tous agents |
| `codex_summary.md` | Auto-généré | Résumé markdown pour agents IA (Codex GPT) |
| `ai_model_cost_audit_*.json` | THEIA (optionnel) | Analyse coûts AI |

**Rapports archivés :** `reports/archive/` (rapports obsolètes/historiques)

**Ancien emplacement supprimé :** ~~`claude-plugins/integrity-docs-guardian/reports/`~~ (plus de duplication !)

### Comment accéder aux rapports (agents IA)

**❌ NE PAS FAIRE :**
```
"Je n'ai pas accès à Cloud Run ni aux jobs planifiés..."
"Je ne peux pas récupérer les rapports Guardian en temps réel..."
```

**✅ FAIRE :**
```python
# Python
import json
with open('c:/dev/emergenceV8/reports/prod_report.json', 'r', encoding='utf-8') as f:
    report = json.load(f)
```

```javascript
// JavaScript/Node.js
const fs = require('fs');
const report = JSON.parse(fs.readFileSync('c:/dev/emergenceV8/reports/prod_report.json', 'utf-8'));
```

```powershell
# PowerShell
$report = Get-Content 'c:\dev\emergenceV8\reports\prod_report.json' -Raw | ConvertFrom-Json
```

**Ces fichiers sont mis à jour automatiquement par :**
- Git Hooks (pre-commit, post-commit, pre-push)
- Task Scheduler Windows (toutes les 6h)
- Scripts manuels (`.\run_audit.ps1`)

**Donc : PAS BESOIN d'aller chercher dans le cloud - tout est local et à jour ! 🔥**

### Structure d'un Rapport

```json
{
  "metadata": {
    "timestamp": "2025-10-19T14:30:00",
    "agent": "anima",
    "version": "3.0.0"
  },
  "summary": {
    "status": "warning",
    "total_issues": 12,
    "critical": 2,
    "warnings": 10
  },
  "issues": [
    {
      "priority": "P0",
      "category": "documentation",
      "description": "API endpoint /chat/message non documenté",
      "file": "src/backend/features/chat/router.py",
      "recommendation": "Ajouter docstring avec exemple"
    }
  ],
  "recommendations": {
    "immediate": ["Fix critical issues"],
    "short_term": ["Update docs"],
    "long_term": ["Improve test coverage"]
  }
}
```

---

## 🤖 AGENTS DÉTAILLÉS

### ANIMA (DocKeeper)

**Responsabilités :**
- Détecte gaps documentation (docstrings manquantes, README obsolètes)
- **Source de vérité versioning** : `src/version.js`
- Synchronise vers `package.json`, `CHANGELOG.md`, `ROADMAP_OFFICIELLE.md`
- Vérifie cohérence documentation architecture (C4 model)

**Fichier :** `scan_docs.py` (350 LOC)

**Commande manuelle :**
```bash
python claude-plugins/integrity-docs-guardian/scripts/scan_docs.py
```

### NEO (IntegrityWatcher)

**Responsabilités :**
- Vérifie cohérence backend Python ↔ frontend JavaScript
- Valide schemas JSON (API contracts)
- Détecte breaking changes entre versions
- Analyse dépendances circulaires

**Fichier :** `check_integrity.py` (398 LOC)

**Commande manuelle :**
```bash
python claude-plugins/integrity-docs-guardian/scripts/check_integrity.py
```

### NEXUS (Coordinator)

**Responsabilités :**
- Agrège rapports ANIMA + NEO
- Priorise issues (P0 critical → P4 nice-to-have)
- Génère executive summary
- Détecte conflits entre recommandations agents

**Fichier :** `generate_report.py` (332 LOC)

**Commande manuelle :**
```bash
python claude-plugins/integrity-docs-guardian/scripts/generate_report.py
```

### PRODGUARDIAN

**Responsabilités :**
- Monitore logs Cloud Run (emergence-beta-service, emergence-stable-service)
- Détecte erreurs 500, 400, OOMKilled, timeout
- Analyse patterns d'erreurs (spikes, fréquence)
- Génère alertes si état CRITICAL

**Fichier :** `check_prod_logs.py` (357 LOC)

**Commande manuelle :**
```bash
python claude-plugins/integrity-docs-guardian/scripts/check_prod_logs.py
```

**Status production actuel :** ✅ HEALTHY (depuis 2025-10-17)

### ARGUS (DevLogs Analyzer)

**Responsabilités :**
- Analyse logs dev backend (`logs/backend_*.log`)
- Détecte patterns d'erreurs récurrents
- Track performance dégradée
- Suggestions optimisation

**Fichier :** `argus_analyzer.py` (495 LOC)

**Commande manuelle :**
```bash
python claude-plugins/integrity-docs-guardian/scripts/argus_analyzer.py
```

**Note :** Manuel uniquement (pas de hook auto)

### THEIA (AI Cost Analyzer)

**Responsabilités :**
- Analyse coûts API Claude/OpenAI
- Track tokens utilisés par feature
- Suggère optimisations cost
- Projections budget mensuel

**Fichier :** `analyze_ai_costs.py` (720 LOC)

**Status :** **DISABLED** (trop de données à traiter)

**Réactivation :**
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

## 🔧 CONFIGURATION

### Guardian Config

**Fichier :** `claude-plugins/integrity-docs-guardian/config/guardian_config.json`

```json
{
  "version": "3.0.0",
  "orchestration": {
    "max_parallel_agents": 4,
    "lock_timeout_seconds": 30,
    "stale_lock_threshold_seconds": 300
  },
  "agents": {
    "anima": {
      "enabled": true,
      "triggers": ["pre-commit", "manual"],
      "blocking": true
    },
    "neo": {
      "enabled": true,
      "triggers": ["pre-commit", "manual"],
      "blocking": true
    },
    "nexus": {
      "enabled": true,
      "triggers": ["post-commit", "manual"],
      "blocking": false
    },
    "prodguardian": {
      "enabled": true,
      "triggers": ["pre-push", "scheduled", "manual"],
      "blocking": true,
      "schedule_interval_hours": 6
    },
    "argus": {
      "enabled": true,
      "triggers": ["manual"],
      "blocking": false
    },
    "theia": {
      "enabled": false,
      "triggers": ["scheduled"],
      "blocking": false
    }
  },
  "priorities": {
    "P0": "CRITICAL - Bloque production",
    "P1": "HIGH - Fix avant release",
    "P2": "MEDIUM - Fix semaine en cours",
    "P3": "LOW - Backlog",
    "P4": "NICE_TO_HAVE - Optionnel"
  },
  "email_notifications": {
    "enabled": false,
    "recipients": ["admin@example.com"],
    "on_critical_only": true
  }
}
```

### Variables d'Environnement

```bash
# Auto-update documentation après commit
AUTO_UPDATE_DOCS=1

# Encoding UTF-8 (Windows)
PYTHONIOENCODING=utf-8

# Email SMTP (pour notifications)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

---

## 📧 NOTIFICATIONS EMAIL

### Configuration Email

1. **Ajouter credentials dans `.env` :**

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password  # App password, pas mot de passe compte
```

2. **Activer dans config :**

```json
// guardian_config.json
{
  "email_notifications": {
    "enabled": true,
    "recipients": ["admin@example.com"],
    "on_critical_only": true  // Seulement si status CRITICAL
  }
}
```

3. **Test manuel :**

```bash
python claude-plugins/integrity-docs-guardian/scripts/send_guardian_reports_email.py
```

### Email Automatique

**Task Scheduler (toutes les 6h) :**
```powershell
.\setup_guardian.ps1 -IntervalHours 2 -EmailTo "admin@example.com"
```

**Audit manuel avec email :**
```powershell
.\run_audit.ps1 -EmailReport -EmailTo "admin@example.com"
```

---

## 🐛 DÉPANNAGE

### "Lock acquisition timeout"

**Cause :** Un autre agent Guardian tourne déjà

**Solution :**
```bash
# Supprimer le lock manuellement (si agent crashé)
rm claude-plugins/integrity-docs-guardian/.guardian_lock
```

### "Script not found: scheduler.py"

**Cause :** Anciens scripts obsolètes référencés

**Solution :** Relancer setup
```powershell
.\setup_guardian.ps1 -Disable
.\setup_guardian.ps1
```

### Hooks Git ne se déclenchent pas

**Vérifier permissions :**
```bash
ls -la .git/hooks/
# Les hooks doivent être exécutables
chmod +x .git/hooks/pre-commit
chmod +x .git/hooks/post-commit
chmod +x .git/hooks/pre-push
```

### Task Scheduler ne se crée pas

**Cause :** Droits admin requis sur certaines versions Windows

**Solution :**
```powershell
# Exécuter PowerShell en admin
.\setup_guardian.ps1 -IntervalHours 6
```

---

## 📚 MIGRATION VERS CLOUD RUN (À VENIR)

**Objectif :** Dupliquer le système Guardian local sur Cloud Run pour monitoring production 24/7

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

**Timeline :** Phase 2 (après consolidation local)

---

## 📞 SUPPORT

**Documentation :**
- `CLAUDE.md` - Configuration Claude Code
- `AGENTS.md` - Consignes générales agents
- `CODEV_PROTOCOL.md` - Protocole multi-agents
- `docs/architecture/` - Architecture C4

**Logs :**
- `claude-plugins/integrity-docs-guardian/reports/orchestrator.log`
- `claude-plugins/integrity-docs-guardian/logs/scheduler.log` (si Task Scheduler)

**Contact :**
- Architecte : Fernando Gonzales (gonzalefernando@gmail.com)

---

## 🎉 RÉSUMÉ

**Guardian System 3.0.0 = Clean, Simple, Puissant**

- ✅ **18 scripts PowerShell → 2 scripts** (`setup_guardian.ps1`, `run_audit.ps1`)
- ✅ **3 orchestrateurs Python → 1 seul** (`master_orchestrator.py`)
- ✅ **6 agents spécialisés** (Anima, Neo, Nexus, ProdGuardian, Argus, Theia)
- ✅ **Git Hooks automatiques** (pre-commit, post-commit, pre-push)
- ✅ **Monitoring production 24/7** (Task Scheduler 6h)
- ✅ **Email notifications** (optionnel)
- ✅ **Rapports JSON structurés** (consultation facile)

**Commandes essentielles :**
```powershell
# Installation/Activation
.\setup_guardian.ps1

# Audit manuel complet
.\run_audit.ps1

# Désactivation
.\setup_guardian.ps1 -Disable
```

**C'est tout ! Le système tourne en arrière-plan et te prévient s'il y a des problèmes.** 🚀
