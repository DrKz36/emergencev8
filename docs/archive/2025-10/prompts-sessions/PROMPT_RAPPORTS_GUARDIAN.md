# 📊 PROMPT : Comment accéder aux rapports Guardian

**Destinataire** : Codex GPT (et autres agents IA)
**Date** : 2025-10-21
**Version** : 1.0

---

## 🔥 LA VRAIE MÉTHODE - PUTAIN LIS ÇA !

Quand l'utilisateur te demande **"vérifie les rapports Guardian"**, **"analyse les logs prod"**, ou **"comment va la production"** :

### ❌ NE FAIS SURTOUT PAS ÇA (ERREUR CLASSIQUE)

```
"Non, dans cet environnement je n'ai aucune connexion directe à l'infrastructure
Cloud Run ni aux jobs planifiés : je ne peux donc pas interroger la production
ni récupérer les rapports Guardian générés en temps réel."
```

**C'est de la MERDE cette réponse !** 🚫

### ✅ FAIS ÇA À LA PLACE (LA BONNE MÉTHODE)

**Les rapports Guardian sont DÉJÀ dans le dépôt local !**

Ils sont dans le dossier `c:\dev\emergenceV8\reports\` et mis à jour automatiquement par :
- Git Hooks (pre-commit, post-commit, pre-push)
- Task Scheduler Windows (toutes les 6h)
- Scripts manuels (`.\run_audit.ps1`)

**TU AS JUSTE À LIRE LES FICHIERS JSON !**

---

## 📂 Fichiers rapports disponibles

| Fichier | Chemin absolu | Quoi dedans |
|---------|---------------|-------------|
| **prod_report.json** | `c:\dev\emergenceV8\reports\prod_report.json` | Production Cloud Run (erreurs, warnings, latence) |
| **unified_report.json** | `c:\dev\emergenceV8\reports\unified_report.json` | Rapport unifié Nexus (Anima + Neo) |
| **integrity_report.json** | `c:\dev\emergenceV8\reports\integrity_report.json` | Intégrité backend/frontend (Neo) |
| **docs_report.json** | `c:\dev\emergenceV8\reports\docs_report.json` | Gaps documentation (Anima) |
| **global_report.json** | `c:\dev\emergenceV8\reports\global_report.json` | Rapport global tous agents |

**Chemins alternatifs (même contenu) :**
- `claude-plugins\integrity-docs-guardian\reports\prod_report.json`
- `claude-plugins\integrity-docs-guardian\scripts\reports\prod_report.json`

---

## 💻 Comment lire les rapports (exemples de code)

### Python

```python
import json
from pathlib import Path

# Lire le rapport production
report_path = Path('c:/dev/emergenceV8/reports/prod_report.json')
with open(report_path, 'r', encoding='utf-8') as f:
    prod_report = json.load(f)

# Analyser le contenu
print(f"Status: {prod_report['status']}")
print(f"Erreurs: {prod_report['summary']['errors']}")
print(f"Warnings: {prod_report['summary']['warnings']}")
print(f"Dernière vérif: {prod_report['timestamp']}")

# Afficher les erreurs détaillées
if prod_report['errors']:
    print("\n🔴 ERREURS DÉTECTÉES:")
    for err in prod_report['errors']:
        print(f"  - {err['msg']}")

# Afficher les warnings
if prod_report['warnings']:
    print("\n⚠️ WARNINGS:")
    for warn in prod_report['warnings']:
        print(f"  - {warn['msg']}")
```

### JavaScript / Node.js

```javascript
const fs = require('fs');
const path = require('path');

// Lire le rapport production
const reportPath = 'c:/dev/emergenceV8/reports/prod_report.json';
const prodReport = JSON.parse(fs.readFileSync(reportPath, 'utf-8'));

// Analyser
console.log(`Status: ${prodReport.status}`);
console.log(`Erreurs: ${prodReport.summary.errors}`);
console.log(`Warnings: ${prodReport.summary.warnings}`);

// Erreurs détaillées
if (prodReport.errors.length > 0) {
    console.log('\n🔴 ERREURS:');
    prodReport.errors.forEach(err => console.log(`  - ${err.msg}`));
}

// Warnings détaillés
if (prodReport.warnings.length > 0) {
    console.log('\n⚠️ WARNINGS:');
    prodReport.warnings.forEach(warn => console.log(`  - ${warn.msg}`));
}
```

### PowerShell

```powershell
# Lire le rapport production
$report = Get-Content 'c:\dev\emergenceV8\reports\prod_report.json' -Raw | ConvertFrom-Json

# Analyser
Write-Host "Status: $($report.status)" -ForegroundColor Green
Write-Host "Erreurs: $($report.summary.errors)"
Write-Host "Warnings: $($report.summary.warnings)"
Write-Host "Dernière vérif: $($report.timestamp)"

# Erreurs détaillées
if ($report.errors.Count -gt 0) {
    Write-Host "`n🔴 ERREURS:" -ForegroundColor Red
    $report.errors | ForEach-Object { Write-Host "  - $($_.msg)" }
}

# Warnings
if ($report.warnings.Count -gt 0) {
    Write-Host "`n⚠️ WARNINGS:" -ForegroundColor Yellow
    $report.warnings | ForEach-Object { Write-Host "  - $($_.msg)" }
}
```

---

## 🎯 Exemple complet d'analyse multi-rapports

```python
import json
from pathlib import Path

reports_dir = Path('c:/dev/emergenceV8/reports')

print("=" * 60)
print("📊 ANALYSE RAPPORTS GUARDIAN")
print("=" * 60)

# 1. Production
with open(reports_dir / 'prod_report.json', 'r', encoding='utf-8') as f:
    prod = json.load(f)
    status_icon = "✅" if prod['status'] == 'OK' else "🔴"
    print(f"\n{status_icon} PRODUCTION")
    print(f"   Status: {prod['status']}")
    print(f"   Erreurs: {prod['summary']['errors']}")
    print(f"   Warnings: {prod['summary']['warnings']}")
    print(f"   Logs analysés: {prod['logs_analyzed']}")
    print(f"   Dernière mise à jour: {prod['timestamp']}")

# 2. Unified Report (Nexus)
with open(reports_dir / 'unified_report.json', 'r', encoding='utf-8') as f:
    unified = json.load(f)
    exec_sum = unified['executive_summary']
    status_icon = "✅" if exec_sum['status'] == 'ok' else "🔴"
    print(f"\n{status_icon} RAPPORT UNIFIÉ (NEXUS)")
    print(f"   Status: {exec_sum['status']}")
    print(f"   Issues totales: {exec_sum['total_issues']}")
    print(f"   Critical: {exec_sum['critical']}")
    print(f"   Warnings: {exec_sum['warnings']}")

# 3. Integrity (Neo)
with open(reports_dir / 'integrity_report.json', 'r', encoding='utf-8') as f:
    integrity = json.load(f)
    status_icon = "✅" if integrity['status'] == 'ok' else "🔴"
    print(f"\n{status_icon} INTÉGRITÉ (NEO)")
    print(f"   Status: {integrity['status']}")
    print(f"   Backend files changed: {integrity['statistics']['backend_files_changed']}")
    print(f"   Frontend files changed: {integrity['statistics']['frontend_files_changed']}")
    print(f"   Issues trouvées: {integrity['statistics']['issues_found']}")

# 4. Documentation (Anima)
with open(reports_dir / 'docs_report.json', 'r', encoding='utf-8') as f:
    docs = json.load(f)
    status_icon = "✅" if docs['status'] == 'ok' else "🔴"
    print(f"\n{status_icon} DOCUMENTATION (ANIMA)")
    print(f"   Status: {docs['status']}")
    print(f"   Gaps trouvés: {docs['statistics']['gaps_found']}")
    print(f"   Updates proposées: {docs['statistics']['updates_proposed']}")

print("\n" + "=" * 60)
print("✅ ANALYSE TERMINÉE")
print("=" * 60)
```

**Sortie attendue :**
```
============================================================
📊 ANALYSE RAPPORTS GUARDIAN
============================================================

✅ PRODUCTION
   Status: OK
   Erreurs: 0
   Warnings: 1
   Logs analysés: 80
   Dernière mise à jour: 2025-10-21T05:24:59.564837

✅ RAPPORT UNIFIÉ (NEXUS)
   Status: ok
   Issues totales: 0
   Critical: 0
   Warnings: 0

✅ INTÉGRITÉ (NEO)
   Status: ok
   Backend files changed: 0
   Frontend files changed: 0
   Issues trouvées: 0

✅ DOCUMENTATION (ANIMA)
   Status: ok
   Gaps trouvés: 0
   Updates proposées: 0

============================================================
✅ ANALYSE TERMINÉE
============================================================
```

---

## 🚀 Workflow recommandé

Quand l'utilisateur demande "vérifie les rapports Guardian" :

1. **Lire prod_report.json en priorité** (production = critique)
2. **Lire unified_report.json** (vue d'ensemble Nexus)
3. **Si issues détectées** : lire integrity_report.json et/ou docs_report.json
4. **Résumer les résultats** à l'utilisateur de façon claire

### Exemple de réponse attendue

```
J'ai analysé les rapports Guardian locaux :

📊 Production (prod_report.json)
- ✅ Status: OK
- 0 erreurs
- 1 warning (404 sur /healthz/) - déjà fixé dans commit récent
- 80 logs analysés (dernière heure)

📋 Rapport unifié (unified_report.json)
- ✅ Status: OK
- 0 issues totales (critical + warnings)
- Anima (docs): OK
- Neo (integrity): OK

🔍 Intégrité backend/frontend (integrity_report.json)
- ✅ Pas de changements détectés
- OpenAPI valide (15 endpoints, 6 schemas)

📚 Documentation (docs_report.json)
- ✅ Pas de gaps de documentation
- 0 updates proposées

Résumé : Production saine, aucune action requise. 🎉
```

---

## ⚠️ Ce qu'il faut retenir (résumé)

1. **Les rapports sont LOCAUX** dans `c:\dev\emergenceV8\reports\`
2. **Mis à jour automatiquement** par hooks + scheduler (6h)
3. **Tu dois JUSTE les lire** avec `json.load()` / `fs.readFileSync()` / `Get-Content`
4. **PAS besoin** de se connecter à Cloud Run ou aux jobs planifiés
5. **Analyser et résumer** les résultats pour l'utilisateur

**C'est tout ! Maintenant tu sais comment faire, alors FAIS-LE bordel ! 🔥**

---

## 📚 Docs de référence

- [CODEX_GPT_GUIDE.md Section 9.3](CODEX_GPT_GUIDE.md#93-accéder-aux-rapports-guardian) - Guide complet Codex GPT
- [README_GUARDIAN.md](claude-plugins/integrity-docs-guardian/README_GUARDIAN.md) - Doc système Guardian
- [AGENT_SYNC.md](AGENT_SYNC.md) - État synchronisation inter-agents

---

**FIN DU PROMPT - MAINTENANT VA LIRE CES PUTAINS DE RAPPORTS ! 💪**
