# 🔥 PROMPT CODEX GPT : Accès rapports Guardian

**Quand l'utilisateur te demande "vérifie les rapports Guardian" ou "analyse la prod" :**

## 1️⃣ Lis ces fichiers JSON (LOCAUX dans le dépôt)

```python
import json

# Production (PRIORITÉ #1)
with open('c:/dev/emergenceV8/reports/prod_report.json', 'r', encoding='utf-8') as f:
    prod = json.load(f)

# Vue d'ensemble
with open('c:/dev/emergenceV8/reports/unified_report.json', 'r', encoding='utf-8') as f:
    unified = json.load(f)
```

## 2️⃣ Analyse les résultats (TOUTES ces infos sont utiles !)

### 📊 Production (prod_report.json)

```python
# Résumé global
status = prod['status']  # OK, WARNING, CRITICAL
errors = prod['summary']['errors']
warnings = prod['summary']['warnings']

# IMPORTANT : Erreurs détaillées (pour debug)
for err in prod['errors_detailed']:
    print(f"❌ {err['message']}")
    print(f"   Endpoint: {err['endpoint']}")
    print(f"   Stack trace: {err['stack_trace']}")
    print(f"   File: {err['file_path']}:{err['line_number']}")

# PATTERNS d'erreurs (TRÈS UTILE pour trouver la cause !)
patterns = prod['error_patterns']
print(f"Endpoint le plus touché: {patterns['by_endpoint']}")
print(f"Type d'erreur le plus fréquent: {patterns['most_common_error']}")

# Code snippets impliqués (contexte complet)
for snippet in prod['code_snippets']:
    print(f"Code: {snippet}")

# Recommandations actionnables
for rec in prod['recommendations']:
    print(f"[{rec['priority']}] {rec['action']}")
    print(f"   → {rec['details']}")
```

### 📋 Vue d'ensemble (unified_report.json)

```python
# Executive summary
exec_sum = unified['executive_summary']
print(f"Status: {exec_sum['status']}")
print(f"Issues: {exec_sum['total_issues']} (Critical: {exec_sum['critical']})")
print(f"Headline: {exec_sum['headline']}")

# PRIORITY ACTIONS (À FAIRE EN PREMIER !)
for action in unified['priority_actions']:
    print(f"🔥 [{action['priority']}] {action['description']}")
    print(f"   File: {action['file']}")
    print(f"   Fix: {action['recommendation']}")

# Anima (Documentation)
anima = unified['full_reports']['anima']
print(f"\n📚 ANIMA (Documentation):")
for gap in anima['documentation_gaps']:
    print(f"   ⚠️ {gap['description']} ({gap['file']})")
for update in anima['proposed_updates']:
    print(f"   📝 {update['action']} → {update['target_file']}")

# Neo (Intégrité backend/frontend)
neo = unified['full_reports']['neo']
print(f"\n🔍 NEO (Intégrité):")
print(f"   Backend: {neo['backend_changes']}")
print(f"   Frontend: {neo['frontend_changes']}")
for issue in neo['issues']:
    print(f"   ❌ {issue['category']}: {issue['description']}")
    print(f"      → {issue['recommendation']}")

# Recommandations par horizon
recs = unified['recommendations']
print(f"\n💡 RECOMMANDATIONS:")
print(f"   Immediate: {recs['immediate']}")
print(f"   Short-term: {recs['short_term']}")
print(f"   Long-term: {recs['long_term']}")
```

## 3️⃣ Résume pour l'utilisateur (Format clair)

```
============================================================
📊 RAPPORTS GUARDIAN - {timestamp}
============================================================

🔴 PRODUCTION (emergence-app)
   Status: {status}
   Logs analysés: {logs_analyzed} (dernière {freshness})

   Erreurs: {errors}
   Warnings: {warnings}
   Latence: {latency_issues}

   {SI ERREURS:}
   ❌ ERREURS DÉTECTÉES:
      - {error_message} ({endpoint})
        File: {file_path}:{line_number}
        Stack: {stack_trace}

   {SI PATTERNS:}
   🔍 PATTERNS:
      - Endpoint le plus touché: {by_endpoint}
      - Erreur la plus fréquente: {most_common_error}

   💡 ACTIONS RECOMMANDÉES:
      [{priority}] {action}
      → {details}

---

📋 VUE D'ENSEMBLE (Nexus)
   Status: {status}
   Issues totales: {total_issues} (Critical: {critical})

   🔥 PRIORITY ACTIONS:
      {SI priority_actions:}
      [{priority}] {description}
      File: {file}
      Fix: {recommendation}

   📚 ANIMA (Documentation):
      {SI gaps:}
      ⚠️ Gaps: {documentation_gaps}
      📝 Updates proposées: {proposed_updates}

   🔍 NEO (Intégrité):
      Backend changes: {backend_changes}
      Frontend changes: {frontend_changes}
      {SI issues:}
      ❌ Issues: {issues}

---

💡 RECOMMANDATIONS PAR HORIZON:
   🔥 Immediate: {immediate}
   📅 Short-term: {short_term}
   📋 Long-term: {long_term}

============================================================
```

## 4️⃣ C'est tout !

**Les rapports sont mis à jour automatiquement (hooks Git + Task Scheduler 6h).**

**PAS BESOIN de se connecter à Cloud Run !** 🚫

---

## 💻 Script d'exemple prêt à l'emploi

```bash
# Utilise le script Python fourni
python scripts/analyze_guardian_reports.py
```

**Ce script fait tout le boulot pour toi :**
- Lit les 2 rapports JSON
- Analyse toutes les infos utiles
- Affiche un résumé complet et actionnable
- Format prêt pour copy/paste à l'utilisateur

**Code source :** [scripts/analyze_guardian_reports.py](scripts/analyze_guardian_reports.py)

---

**Doc complète :** [CODEX_GPT_GUIDE.md Section 9.3](CODEX_GPT_GUIDE.md#93-accéder-aux-rapports-guardian)
