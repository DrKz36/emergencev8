# 🔥 PROMPT CODEX GPT : Accès rapports Guardian

**Quand l'utilisateur te demande "vérifie les rapports Guardian" ou "analyse la prod" :**

## 🚀 NOUVELLE PROCÉDURE (2025-10-21)

### 1️⃣ Lis le résumé markdown enrichi (RECOMMANDÉ)

```python
# Résumé narratif exploitable pour LLM
with open('c:/dev/emergenceV8/reports/codex_summary.md', 'r', encoding='utf-8') as f:
    summary = f.read()

print(summary)
```

**Ce fichier contient :**
- ✅ Vue d'ensemble tous les Guardians (Production, Docs, Intégrité)
- ✅ Insights actionnables avec contexte
- ✅ Code snippets des fichiers avec erreurs
- ✅ Patterns d'erreurs (endpoints, types, fichiers)
- ✅ Recommandations prioritaires avec commandes gcloud
- ✅ Commits récents (contexte pour identifier coupables)
- ✅ Actions prioritaires ("Que faire maintenant ?")

**Avantage :** Format markdown = plus facile à lire pour un LLM que du JSON brut.

---

### 2️⃣ (Optionnel) Accès rapports JSON bruts pour détails

Si tu as besoin de **plus de détails** après avoir lu le résumé :

```python
import json

# Production (détails complets)
with open('c:/dev/emergenceV8/reports/prod_report.json', 'r', encoding='utf-8') as f:
    prod = json.load(f)

# Documentation
with open('c:/dev/emergenceV8/reports/docs_report.json', 'r', encoding='utf-8') as f:
    docs = json.load(f)

# Intégrité
with open('c:/dev/emergenceV8/reports/integrity_report.json', 'r', encoding='utf-8') as f:
    integrity = json.load(f)

# Rapport unifié
with open('c:/dev/emergenceV8/reports/unified_report.json', 'r', encoding='utf-8') as f:
    unified = json.load(f)
```

**Champs utiles dans prod_report.json :**
- `errors_detailed` : Liste erreurs avec full context (endpoint, file, line, stack trace)
- `error_patterns.by_endpoint` : Endpoints les plus affectés
- `error_patterns.by_file` : Fichiers les plus affectés
- `code_snippets` : Code source avec numéros de ligne
- `recent_commits` : 5 derniers commits (potentiels coupables)
- `recommendations` : Actions prioritaires avec commandes gcloud

---

## 📊 Exemple d'utilisation complète

```python
# 1. Lire le résumé markdown
with open('c:/dev/emergenceV8/reports/codex_summary.md', 'r', encoding='utf-8') as f:
    summary = f.read()

print("📋 RÉSUMÉ GUARDIAN")
print(summary)

# 2. Si erreurs détectées, approfondir avec JSON
import json
with open('c:/dev/emergenceV8/reports/prod_report.json', 'r', encoding='utf-8') as f:
    prod = json.load(f)

if prod['summary']['errors'] > 0:
    print("\n🔍 DÉTAILS DES ERREURS")
    for error in prod['errors_detailed'][:5]:
        print(f"Type: {error.get('error_type')}")
        print(f"Endpoint: {error.get('endpoint')}")
        print(f"File: {error.get('file_path')}:{error.get('line_number')}")
        print(f"Message: {error.get('message')[:200]}")
        print("---")
```

---

## 🔄 Génération du résumé

Le résumé `codex_summary.md` est généré par :

```bash
python scripts/generate_codex_summary.py
```

**Mise à jour automatique :**
- ✅ Hooks Git (post-commit, pre-push)
- ✅ Task Scheduler (toutes les 6h)

**Mise à jour manuelle :**
```bash
cd c:/dev/emergenceV8
python scripts/generate_codex_summary.py
```

---

## 🚨 PAS BESOIN de gcloud !

**Les rapports sont LOCAUX dans le dépôt.**
- ❌ Pas besoin de se connecter à Cloud Run
- ❌ Pas besoin de gcloud auth
- ✅ Juste lire les fichiers dans `reports/`

---

## 💻 Alternative : Script Python tout-en-un (ancien)

Si tu préfères utiliser le script Python qui analyse les JSON :

```bash
python scripts/analyze_guardian_reports.py --summary
```

**Ce script fait :**
- Lit les rapports JSON
- Analyse toutes les infos utiles
- Affiche un résumé complet et actionnable

Mais le **résumé markdown (`codex_summary.md`) est plus exploitable** pour un LLM.

---

**Doc complète :** [CODEX_GPT_GUIDE.md Section 9.3](CODEX_GPT_GUIDE.md#93-accéder-aux-rapports-guardian)
