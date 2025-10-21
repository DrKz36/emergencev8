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

## 2️⃣ Résume les résultats

```
📊 Production (prod_report.json)
- Status: {prod['status']}
- Erreurs: {prod['summary']['errors']}
- Warnings: {prod['summary']['warnings']}

📋 Vue d'ensemble (unified_report.json)
- Status: {unified['executive_summary']['status']}
- Issues: {unified['executive_summary']['total_issues']}
```

## 3️⃣ C'est tout !

**Les rapports sont mis à jour automatiquement (hooks Git + Task Scheduler 6h).**

**PAS BESOIN de se connecter à Cloud Run !** 🚫

---

**Doc complète :** [CODEX_GPT_GUIDE.md Section 9.3](CODEX_GPT_GUIDE.md#93-accéder-aux-rapports-guardian)
