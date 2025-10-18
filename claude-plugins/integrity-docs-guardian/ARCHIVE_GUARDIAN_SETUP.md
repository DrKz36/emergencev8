# Archive Guardian - Automated Repository Cleanup

**Version:** 1.0.0
**Date:** 2025-10-18
**Agent:** ANIMA (DocKeeper)

---

## Vue d'Ensemble

**Archive Guardian** est un système automatisé qui maintient la racine du dépôt propre en archivant automatiquement les fichiers obsolètes chaque semaine.

### Fonctionnalités

- **Scan automatique** de la racine du dépôt
- **Détection intelligente** des fichiers obsolètes (basée sur patterns et âge)
- **Archivage structuré** dans `docs/archive/YYYY-MM/`
- **Whitelist configurable** pour protéger les fichiers essentiels
- **Rapports détaillés** de chaque nettoyage
- **Exécution hebdomadaire** automatique (dimanche 3h00)

---

## Installation

### Prérequis

- Python 3.11+ avec virtualenv activé
- PowerShell (pour configuration scheduler Windows)
- Permissions administrateur (pour créer tâche planifiée)

### Configuration Scheduler Hebdomadaire

```powershell
# Créer la tâche planifiée
cd claude-plugins/integrity-docs-guardian/scripts
.\setup_archive_scheduler.ps1

# Vérifier le statut
.\setup_archive_scheduler.ps1 -Status

# Supprimer la tâche (si nécessaire)
.\setup_archive_scheduler.ps1 -Remove
```

---

## Utilisation

### Exécution Manuelle

```bash
# Dry-run (voir ce qui serait fait sans modifier)
python claude-plugins/integrity-docs-guardian/scripts/archive_guardian.py --dry-run

# Mode interactif (demande confirmation)
python claude-plugins/integrity-docs-guardian/scripts/archive_guardian.py

# Mode automatique (utilisé par le scheduler)
python claude-plugins/integrity-docs-guardian/scripts/archive_guardian.py --auto
```

### Vérifier le Scheduler

```powershell
# Voir le statut de la tâche planifiée
.\setup_archive_scheduler.ps1 -Status

# Exécuter manuellement la tâche planifiée
schtasks /run /tn "EmergenceArchiveGuardian"
```

---

## Règles de Détection

### Fichiers Markdown (.md)

**Archivés automatiquement** :
- `PROMPT_*.md`, `HANDOFF_*.md`, `NEXT_SESSION_*.md` > 7 jours
- `PHASE*_*.md` (toutes phases sauf actives)
- `*_FIX_*.md`, `*_AUDIT_*.md`, `CORRECTIONS_*.md` > 14 jours
- `DEPLOYMENT_*.md` (sauf `DEPLOYMENT_SUCCESS.md`, `CANARY_DEPLOYMENT.md`)
- Fichiers datés (pattern `YYYY-MM-DD`) > 30 jours
- `*_IMPLEMENTATION.md`, `*_SUMMARY.md`, `*_STATE_*.md`
- `(UPGRADE|CHANGELOG)_*.md` (sauf `CHANGELOG.md`)

**JAMAIS archivés (whitelist)** :
- `README.md`, `CLAUDE.md`, `AGENT_SYNC.md`, `AGENTS.md`
- `CODEV_PROTOCOL.md`, `CHANGELOG.md`, `CONTRIBUTING.md`
- `ROADMAP_*.md`, `MEMORY_REFACTORING_ROADMAP.md`
- `DEPLOYMENT_SUCCESS.md`, `FIX_PRODUCTION_DEPLOYMENT.md`, `CANARY_DEPLOYMENT.md`
- `CLAUDE_CODE_GUIDE.md`, `CODEX_GPT_GUIDE.md`, `GUIDE_INTERFACE_BETA.md`
- `GUARDIAN_SETUP_COMPLETE.md`

### Scripts Python (.py)

**Archivés automatiquement** :
- `test_*.py` dans la racine (sauf tests validation)
- Scripts obsolètes > 7 jours :
  - `check_db*.py`, `fix_*.py`, `fetch_*.py`, `send_*.py`
  - `consolidate_*.py`, `qa_*.py`, `inject_*.py`, `generate_*.py`
  - `deploy_*.py`, `cleanup*.py`, `revoke_*.py`, `disable_*.py`

**Gardés** :
- `apply_migration_*.py` récents (≤ 7 jours)
- `check_db_status.py` (utilitaire actif)
- Scripts dans `/scripts`, `/tests`, `/src`

### Fichiers HTML

**Archivés automatiquement** :
- Tous les `.html` dans la racine (sauf `index.html`)
- Exemples : `beta_invitations.html`, `check_jwt_token.html`, `onboarding.html`

### Scripts Batch/Shell (.bat, .sh)

**Archivés automatiquement** :
- Tous les `.bat` et `.sh` dans la racine (aucune whitelist)
- Exemples : `envoyer_invitations_beta.bat`, `run_memory_validation.bat`, `cleanup.sh`

### Fichiers Temporaires (SUPPRIMÉS, pas archivés)

**Supprimés directement** :
- `tmp_*`, `temp_*`, `*.tmp`
- `downloaded-logs-*.json`
- `*_report.json` (sauf dans `/reports`)
- `build_tag.txt`, `BUILDSTAMP.txt`
- `*.log` dans la racine

---

## Structure d'Archivage

```
docs/archive/
├── 2025-10/                      ← Dossier mensuel
│   ├── obsolete-docs/            ← Fichiers .md obsolètes
│   │   ├── PROMPT_NEXT_SESSION_P1_FIXES.md
│   │   ├── PHASE3_RAG_CHANGELOG.md
│   │   └── ...
│   ├── temp-scripts/             ← Scripts temporaires
│   │   ├── test_beta_invitations.py
│   │   ├── check_db_simple.py
│   │   └── ...
│   ├── test-files/               ← Fichiers HTML de test
│   │   ├── beta_invitations.html
│   │   ├── check_jwt_token.html
│   │   └── ...
│   └── README.md                 ← Index automatique (à créer)
├── 2025-11/                      ← Prochain mois
│   └── ...
└── README.md                     ← Documentation archives
```

---

## Rapports

### Rapport JSON

Chaque exécution génère un rapport : **`reports/archive_cleanup_report.json`**

```json
{
  "timestamp": "2025-10-18T17:30:00",
  "archive_month": "2025-10",
  "scan_results": {
    "to_archive": 5,
    "to_delete": 3,
    "whitelisted": 25,
    "kept": 33
  },
  "actions_taken": {
    "archived": 5,
    "deleted": 3,
    "errors": 0
  },
  "files": {
    "to_archive": [
      {
        "file": "PROMPT_NEXT_SESSION_P1_FIXES.md",
        "type": "markdown",
        "reason": "obsolete pattern (prompt), 15 days old",
        "age_days": 15
      },
      ...
    ],
    "to_delete": [
      {
        "file": "downloaded-logs-20251001-120000.json",
        "reason": "temporary file (logs)",
        "age_days": 17
      },
      ...
    ]
  },
  "summary": "5 fichiers archivés, 3 fichiers supprimés"
}
```

### Logs

Consulter les logs d'exécution :

```powershell
# Voir les dernières exécutions planifiées
Get-ScheduledTask -TaskName "EmergenceArchiveGuardian" | Get-ScheduledTaskInfo

# Voir les événements Windows (Event Viewer)
Get-WinEvent -LogName "Microsoft-Windows-TaskScheduler/Operational" | Where-Object {$_.Message -like "*EmergenceArchiveGuardian*"} | Select-Object -First 10
```

---

## Exemples d'Usage

### Scénario 1: Nettoyage Manuel Avant Commit

```bash
# Voir ce qui serait nettoyé
python claude-plugins/integrity-docs-guardian/scripts/archive_guardian.py --dry-run

# Si OK, exécuter le nettoyage
python claude-plugins/integrity-docs-guardian/scripts/archive_guardian.py

# Vérifier git status
git status

# Commit si nécessaire
git add .
git commit -m "chore: manual archive cleanup before release"
```

### Scénario 2: Vérifier Après Nettoyage Hebdomadaire

```bash
# Consulter le rapport
cat reports/archive_cleanup_report.json | python -m json.tool

# Vérifier l'archive
ls docs/archive/2025-10/

# Vérifier la racine est propre
ls *.md
```

### Scénario 3: Récupérer un Fichier Archivé

```bash
# Trouver le fichier archivé
find docs/archive -name "PROMPT_NEXT_SESSION_*.md"

# Copier vers la racine (si nécessaire)
cp docs/archive/2025-10/obsolete-docs/PROMPT_NEXT_SESSION_P1_FIXES.md ./
```

---

## Configuration Avancée

### Modifier le Scheduler

Pour changer la fréquence (par défaut: dimanche 3h00) :

```powershell
# Supprimer la tâche existante
.\setup_archive_scheduler.ps1 -Remove

# Modifier setup_archive_scheduler.ps1 ligne 103-106
# Exemple: Tous les jours à 2h00
$trigger = New-ScheduledTaskTrigger `
    -Daily `
    -At 2:00AM

# Recréer la tâche
.\setup_archive_scheduler.ps1
```

### Modifier la Whitelist

Éditer **`archive_guardian.py`** ligne 37-55 (variable `WHITELIST`) :

```python
WHITELIST = {
    # Ajouter vos fichiers protégés ici
    "MY_IMPORTANT_FILE.md",
    "CUSTOM_SCRIPT.py",
    ...
}
```

### Ajouter des Patterns de Détection

Éditer **`archive_guardian.py`** ligne 58-79 (variable `OBSOLETE_PATTERNS`) :

```python
OBSOLETE_PATTERNS = {
    # Ajouter vos patterns regex ici
    "custom_pattern": r"CUSTOM_.*\.md",
    ...
}
```

---

## Troubleshooting

### La tâche planifiée ne s'exécute pas

**Vérifier** :
```powershell
# Statut de la tâche
.\setup_archive_scheduler.ps1 -Status

# Logs Windows
eventvwr.msc
# → Applications and Services Logs → Microsoft → Windows → Task Scheduler → Operational
```

**Solutions** :
1. Vérifier que le virtualenv Python est activé
2. Vérifier les permissions (exécuter PowerShell en admin)
3. Tester manuellement : `schtasks /run /tn "EmergenceArchiveGuardian"`

### Fichiers archivés par erreur

**Récupération** :
```bash
# Fichier archivé ce mois
cp docs/archive/2025-10/obsolete-docs/MY_FILE.md ./

# Ajouter à la whitelist pour éviter réarchivage
# Éditer archive_guardian.py → WHITELIST
```

### Script Python ne trouve pas les modules

**Vérifier virtualenv** :
```bash
# Activer virtualenv
.venv\Scripts\activate

# Vérifier Python path
python -c "import sys; print(sys.executable)"

# Doit pointer vers .venv\Scripts\python.exe
```

---

## Intégration Git

Le scheduler ne commit PAS automatiquement par défaut.

**Pour commit automatique** (optionnel), ajouter dans `setup_archive_scheduler.ps1` :

```powershell
# Après l'action principale
$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-File `"$RepoRoot\scripts\auto_commit_archives.ps1`""
```

Créer **`scripts/auto_commit_archives.ps1`** :
```powershell
cd $PSScriptRoot\..
git add docs/archive/
git commit -m "chore: automated archive cleanup $(Get-Date -Format 'yyyy-MM-dd')"
# Pas de push automatique pour sécurité
```

---

## Métriques & Monitoring

### Indicateurs Clés

- **Fichiers archivés/semaine** : Cible < 10 (racine bien maintenue)
- **Fichiers supprimés/semaine** : Cible < 5 (peu de fichiers temp créés)
- **Erreurs** : Cible = 0
- **Taille racine** : Cible < 100 fichiers

### Rapports Mensuels

Créer un script **`scripts/archive_stats.py`** :
```python
import json
from pathlib import Path

reports_dir = Path("reports")
monthly_reports = list(reports_dir.glob("archive_cleanup_report_*.json"))

total_archived = 0
total_deleted = 0

for report_file in monthly_reports:
    with open(report_file) as f:
        report = json.load(f)
        total_archived += report["actions_taken"]["archived"]
        total_deleted += report["actions_taken"]["deleted"]

print(f"Total archived this month: {total_archived}")
print(f"Total deleted this month: {total_deleted}")
```

---

## Références

- **Prompt Anima** : [claude-plugins/integrity-docs-guardian/agents/anima_dockeeper.md](../agents/anima_dockeeper.md)
- **Script Guardian** : [scripts/archive_guardian.py](scripts/archive_guardian.py)
- **Setup Scheduler** : [scripts/setup_archive_scheduler.ps1](scripts/setup_archive_scheduler.ps1)
- **Documentation Archives** : [docs/archive/README.md](../../../docs/archive/README.md)

---

**Maintenu par** : ANIMA (DocKeeper)
**Version** : 1.0.0
**Dernière mise à jour** : 2025-10-18
