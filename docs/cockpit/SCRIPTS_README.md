# 🔧 Scripts de Diagnostic - Guide d'Utilisation

**Version** : 1.0
**Date** : 2025-10-10

---

## 📋 Vue d'Ensemble

Ce document décrit les scripts de diagnostic disponibles pour analyser et valider les données du cockpit et du tracking des coûts LLM.

---

## 📦 Scripts Disponibles

### 1. check_db_simple.py

**Localisation** : [`check_db_simple.py`](../../check_db_simple.py)

**Description** : Script d'analyse rapide de la base de données pour vérifier les coûts, messages, sessions et documents.

**Usage** :
```bash
cd /path/to/emergenceV8
python check_db_simple.py
```

**Fonctionnalités** :
- ✅ Compte total des coûts et messages
- ✅ Analyse des coûts par modèle (avec tokens input/output)
- ✅ Affiche les 5 entrées de coûts les plus récentes
- ✅ Détection automatique si coûts = $0.00
- ✅ Compte des sessions et documents

**Exemple de sortie** :
```
=== DATABASE ANALYSIS ===

Total costs: 156
Total messages: 82

Costs by model:
  gpt-4o-mini: 78 entries, $0.034292, 179,408 in, 12,302 out
  gpt-4o: 23 entries, $0.176685, 31,812 in, 1,175 out
  gemini-1.5-flash: 29 entries, $0.000000, 0 in, 0 out ← PROBLÈME !
  claude-3-5-haiku: 14 entries, $0.000000, 0 in, 0 out ← PROBLÈME !

Recent costs:
  2025-09-20T11:43:15.345079+00:00: gpt-4o-mini - $0.000939 (6014 in, 62 out)
  ...

WARNING: No costs recorded!
This means cost_tracker.record_cost() is NOT being called.
```

**Prérequis** :
- Python 3.11+
- Base de données `data/emergence.db` accessible

**Limitations** :
- Pas d'analyse par période (today/week/month)
- Pas de diagnostic spécifique Gemini

---

### 2. check_cockpit_data.py

**Localisation** : [`check_cockpit_data.py`](../../check_cockpit_data.py)

**Description** : Diagnostic complet des données du cockpit avec analyse par période et recommandations.

**Usage** :
```bash
cd /path/to/emergenceV8
python check_cockpit_data.py
```

**Fonctionnalités** :
- ✅ Analyse des messages par période (today, week, month)
- ✅ Analyse des coûts par période et par modèle
- ✅ **Diagnostic spécifique Gemini** (détection Gap #1)
- ✅ Analyse des sessions (actives vs archivées)
- ✅ Analyse des documents par type
- ✅ Calcul des tokens moyens par message
- ✅ **Résumé avec recommandations** automatiques

**Exemple de sortie** :
```
✅ Base de données trouvée: C:\dev\emergenceV8\data\emergence.db
======================================================================
📊 DIAGNOSTIC COCKPIT - ANALYSE DES DONNÉES
======================================================================

📧 MESSAGES
----------------------------------------------------------------------
Total messages: 82
  Aujourd'hui: 6
  Cette semaine (7j): 35
  Ce mois (30j): 82
  Dernier message: 2025-09-20 11:43:15

💰 COÛTS
----------------------------------------------------------------------
Total entrées de coûts: 156
Coût total cumulé: $0.210977

  Coûts par modèle:
    gpt-4o-mini: 78 requêtes, $0.034292, 179,408 in, 12,302 out
    gpt-4o: 23 requêtes, $0.176685, 31,812 in, 1,175 out
    gemini-1.5-flash: 29 requêtes, $0.000000, 0 in, 0 out
    claude-3-5-haiku: 14 requêtes, $0.000000, 0 in, 0 out

  🔥 GEMINI (diagnostic Gap #1):
    Requêtes: 29
    Coût total: $0.000000
    Tokens: 0 in, 0 out
    ⚠️ WARNING: Coûts Gemini à $0.00 avec 29 requêtes!
    💡 Vérifiez que le fix Gap #1 est bien appliqué

  Coûts par période:
    Aujourd'hui: $0.002345
    Cette semaine (7j): $0.150234
    Ce mois (30j): $0.210977

  Coût moyen par requête: $0.001352
  Dernière entrée: 2025-09-20T11:43:15 - gpt-4o-mini ($0.000939)

🧵 SESSIONS
----------------------------------------------------------------------
Total sessions: 12
  Sessions actives: 3
  Sessions archivées: 9
  Dernière session: abc123 (2025-09-20 11:43:00)

📄 DOCUMENTS
----------------------------------------------------------------------
Total documents: 156
  Par type:
    text: 120
    pdf: 24
    code: 12

🪙 TOKENS
----------------------------------------------------------------------
Total tokens: 225,497
  Input: 211,220
  Output: 14,277
  Moyenne par message: 2,750

======================================================================
📋 RÉSUMÉ & RECOMMANDATIONS
======================================================================

✅ Succès:
  • 82 messages enregistrés
  • 156 coûts enregistrés ($0.210977 total)
  • 12 sessions (3 actives)

🔴 Problèmes:
  • 🔥 CRITIQUE: Coûts Gemini = $0.00 → Gap #1 NON corrigé
  • 🔥 CRITIQUE: Coûts Claude = $0.00 → Gap #1 NON corrigé

======================================================================
Pour tester le cockpit:
  1. Démarrez le backend: python -m uvicorn src.backend.main:app --reload
  2. Ouvrez l'application frontend
  3. Allez dans le cockpit (menu ou /cockpit)
  4. Les valeurs affichées devraient correspondre aux chiffres ci-dessus
======================================================================
```

**Prérequis** :
- Python 3.11+
- Base de données `instance/emergence.db` accessible
- **Encodage UTF-8 supporté** (peut échouer sur Windows avec CP1252)

**⚠️ Problème d'Encodage Windows** :

Si vous obtenez :
```
UnicodeEncodeError: 'charmap' codec can't encode character '\u274c'
```

**Solution 1 : Rediriger la sortie** :
```bash
python check_cockpit_data.py > output.txt 2>&1
type output.txt
```

**Solution 2 : Utiliser check_db_simple.py** (pas d'emojis) :
```bash
python check_db_simple.py
```

**Solution 3 : Changer l'encodage du terminal** :
```bash
chcp 65001  # UTF-8
python check_cockpit_data.py
```

---

## 🔄 Quand Utiliser Quel Script ?

### Utiliser `check_db_simple.py` :

- ✅ **Analyse rapide** des coûts et messages
- ✅ **Vérification après conversation** (coûts enregistrés ?)
- ✅ **Validation baseline** avant les tests
- ✅ **Pas de problème d'encodage** (pas d'emojis)
- ✅ **Intégration dans scripts automatisés** (CI/CD)

### Utiliser `check_cockpit_data.py` :

- ✅ **Diagnostic complet** avec analyse par période
- ✅ **Détection automatique** des problèmes Gemini/Claude
- ✅ **Résumé avec recommandations** pour débugger
- ✅ **Validation finale** avant déploiement
- ⚠️ **Nécessite UTF-8** (peut échouer sur Windows)

---

## 📊 Interprétation des Résultats

### Cas 1 : Tout Fonctionne ✅

```
Costs by model:
  gpt-4o-mini: 78 entries, $0.034292, 179,408 in, 12,302 out  ✅
  gemini-1.5-flash: 32 entries, $0.005234, 45,000 in, 12,000 out  ✅
  claude-3-5-haiku: 16 entries, $0.002456, 18,000 in, 6,000 out  ✅
```

**Interprétation** :
- ✅ Tous les modèles ont des coûts > $0.00
- ✅ Tous les modèles ont des tokens > 0
- ✅ Les corrections fonctionnent correctement

**Action** : Aucune, tout est OK !

---

### Cas 2 : Gemini à $0.00 ❌

```
Costs by model:
  gpt-4o-mini: 78 entries, $0.034292, 179,408 in, 12,302 out  ✅
  gemini-1.5-flash: 29 entries, $0.000000, 0 in, 0 out  ❌
```

**Interprétation** :
- ❌ `count_tokens()` ne fonctionne pas
- ❌ Les corrections Gap #1 ne sont pas appliquées OU
- ❌ Le backend n'a pas été redémarré OU
- ❌ Problème avec l'API Google Generative AI

**Actions** :

1. **Vérifier que le backend a été redémarré** :
   ```bash
   # Arrêter le backend (Ctrl+C)
   # Relancer
   python -m uvicorn src.backend.main:app --reload
   ```

2. **Vérifier les logs backend** :
   ```bash
   grep "Gemini.*Failed to count" logs/app.log
   ```

3. **Tester count_tokens() manuellement** :
   ```python
   import google.generativeai as genai
   genai.configure(api_key="VOTRE_API_KEY")
   model = genai.GenerativeModel("gemini-1.5-flash")
   result = model.count_tokens("Hello world")
   print(result.total_tokens)  # Devrait être > 0
   ```

4. **Vérifier la version de google-generativeai** :
   ```bash
   pip show google-generativeai
   pip install --upgrade google-generativeai
   ```

---

### Cas 3 : Claude à $0.00 ❌

```
Costs by model:
  gpt-4o-mini: 78 entries, $0.034292, 179,408 in, 12,302 out  ✅
  claude-3-5-haiku: 14 entries, $0.000000, 0 in, 0 out  ❌
```

**Interprétation** :
- ❌ `stream.get_final_response()` ne retourne pas de `usage`
- ❌ Les corrections Gap #1 ne sont pas appliquées OU
- ❌ Le backend n'a pas été redémarré OU
- ❌ Version d'anthropic trop ancienne

**Actions** :

1. **Vérifier que le backend a été redémarré**

2. **Vérifier les logs backend** :
   ```bash
   grep "Anthropic.*No usage data" logs/app.log
   ```

3. **Vérifier la version d'anthropic** :
   ```bash
   pip show anthropic
   # Version recommandée : ≥ 0.7.0
   pip install --upgrade anthropic
   ```

4. **Tester stream.get_final_response()** :
   ```python
   from anthropic import Anthropic
   import asyncio

   async def test():
       client = Anthropic(api_key="VOTRE_API_KEY")
       async with client.messages.stream(
           model="claude-3-5-haiku-20241022",
           max_tokens=100,
           messages=[{"role": "user", "content": "Hello"}]
       ) as stream:
           async for text in stream.text_stream:
               print(text, end="")
           final = await stream.get_final_response()
           print(f"\nUsage: {final.usage}")

   asyncio.run(test())
   ```

---

### Cas 4 : Aucun Coût Enregistré ❌

```
Total costs: 0
Total messages: 82
```

**Interprétation** :
- ❌ `cost_tracker.record_cost()` n'est PAS appelé
- ❌ Problème dans le code de service
- ❌ CostTracker non initialisé

**Actions** :

1. **Vérifier les logs backend** :
   ```bash
   grep "cost_tracker" logs/app.log
   grep "record_cost" logs/app.log
   ```

2. **Vérifier que CostTracker est initialisé** :
   ```bash
   grep "CostTracker.*initialisé" logs/app.log
   ```

3. **Vérifier le code service.py** :
   - Ligne ~1449 : `await self.cost_tracker.record_cost(...)`
   - S'assurer que le bloc n'est pas commenté

---

## 🔗 Références

### Documentation
- [TESTING_GUIDE.md](TESTING_GUIDE.md) - Guide de test complet
- [COCKPIT_COSTS_FIX_FINAL.md](COCKPIT_COSTS_FIX_FINAL.md) - Corrections appliquées
- [COCKPIT_ROADMAP_FIXED.md](COCKPIT_ROADMAP_FIXED.md) - Feuille de route

### Scripts
- [check_db_simple.py](../../check_db_simple.py) - Analyse rapide
- [check_cockpit_data.py](../../check_cockpit_data.py) - Diagnostic complet

### Code Source
- [llm_stream.py](../../src/backend/features/chat/llm_stream.py) - Streaming + calcul coûts
- [cost_tracker.py](../../src/backend/core/cost_tracker.py) - Tracking coûts
- [service.py](../../src/backend/features/chat/service.py) - Appel record_cost()

---

## 🆘 Support

Si les scripts ne fonctionnent pas ou si vous rencontrez des problèmes :

1. **Vérifier le chemin de la BDD** :
   ```python
   import os
   print(os.path.exists('data/emergence.db'))  # check_db_simple.py
   print(os.path.exists('instance/emergence.db'))  # check_cockpit_data.py
   ```

2. **Vérifier les permissions** :
   ```bash
   ls -la data/emergence.db
   ls -la instance/emergence.db
   ```

3. **Consulter les logs** :
   ```bash
   tail -n 100 logs/app.log
   ```

4. **Contacter l'équipe** avec :
   - Sortie complète du script
   - Logs backend (dernières 50 lignes)
   - Version Python : `python --version`
   - Version des packages : `pip list | grep -E "(google-generativeai|anthropic|openai)"`

---

**Dernière mise à jour** : 2025-10-10
**Version** : 1.0
