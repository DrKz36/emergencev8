# 🧪 Guide de Test - Cockpit & Coûts LLM

**Version** : 1.0
**Date** : 2025-10-10
**Objectif** : Valider les corrections des coûts Gemini & Anthropic

---

## 📋 Vue d'Ensemble

Ce guide vous accompagne pas à pas pour tester et valider les corrections apportées au système de tracking des coûts LLM.

**Corrections testées** :
- ✅ Gemini : Format `count_tokens()` corrigé
- ✅ Anthropic : Logs détaillés ajoutés
- ✅ Tous les providers : Uniformisation des logs

---

## 🚀 Prérequis

### 1. Backend Arrêté et Redémarré

**IMPORTANT** : Les modifications de code ne seront pas prises en compte sans redémarrage !

```bash
# Si le backend tourne, l'arrêter avec Ctrl+C

# Redémarrer avec reload
python -m uvicorn src.backend.main:app --reload

# OU en mode production
python -m uvicorn src.backend.main:app --host 0.0.0.0 --port 8000
```

**Vérification** :
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### 2. Frontend Accessible

- Ouvrir le navigateur : `http://localhost:3000` (ou port configuré)
- Se connecter avec un compte utilisateur
- Vérifier que la session est active

### 3. Scripts de Diagnostic Prêts

```bash
# Tester les scripts
python check_db_simple.py
python check_cockpit_data.py  # Peut échouer sur Windows (encodage UTF-8)
```

---

## 🧪 Plan de Test

### Test 1 : Baseline - État Initial

**Objectif** : Documenter l'état actuel avant les tests

**Étapes** :

1. **Analyser la BDD** :
   ```bash
   python check_db_simple.py
   ```

2. **Noter les valeurs actuelles** :
   ```
   Total costs: ___
   Total messages: ___

   Costs by model:
     gpt-4o-mini: ___ entries, $___.______, ___ in, ___ out
     gemini-1.5-flash: ___ entries, $___.______, ___ in, ___ out
     claude-3-5-haiku: ___ entries, $___.______, ___ in, ___ out
   ```

3. **Capture d'écran du cockpit** :
   - Ouvrir `/cockpit` ou activer le module Cockpit
   - Noter les valeurs affichées :
     - Messages : Total = ___, Aujourd'hui = ___
     - Threads : Total = ___, Actifs = ___
     - Tokens : Total = ___, Input = ___, Output = ___
     - Coûts : Total = $___.__, Aujourd'hui = $___.__, Semaine = $___.__, Mois = $___.__

---

### Test 2 : Conversation avec Gemini

**Objectif** : Vérifier que les coûts Gemini sont enregistrés correctement

**Étapes** :

1. **Créer une nouvelle session** :
   - Cliquer sur "Nouvelle Conversation" ou "+"
   - Titre : "Test Coûts Gemini"

2. **Sélectionner le modèle Gemini** :
   - Vérifier que le modèle actif est `gemini-1.5-flash` ou `gemini-2.0-flash-exp`
   - Si besoin, changer dans les paramètres

3. **Envoyer 3 messages** :

   **Message 1** :
   ```
   Bonjour ! Explique-moi brièvement ce qu'est un LLM.
   ```

   **Message 2** :
   ```
   Quels sont les principaux providers de LLM en 2024 ?
   ```

   **Message 3** :
   ```
   Comment calculer le coût d'une requête API ?
   ```

4. **Vérifier les logs backend** (en temps réel) :

   Dans le terminal du backend, chercher :
   ```
   [Gemini] Cost calculated: $0.000XXX (model=gemini-1.5-flash, input=XXX tokens, output=XXX tokens, ...)
   ```

   **✅ SUCCÈS si** :
   - 3 lignes `[Gemini] Cost calculated` apparaissent
   - `input=XXX tokens` avec XXX > 0
   - `output=XXX tokens` avec XXX > 0
   - `total_cost` > $0.00

   **❌ ÉCHEC si** :
   - Aucun log `[Gemini] Cost calculated`
   - `input=0 tokens` et `output=0 tokens`
   - Warnings `[Gemini] Failed to count input/output tokens`

5. **Analyser la BDD** :
   ```bash
   python check_db_simple.py
   ```

   **Vérifier** :
   - `gemini-1.5-flash` : nombre d'entries augmenté de +3
   - Coût total > baseline
   - Tokens input et output > 0

6. **Vérifier le cockpit** :
   - Actualiser la page du cockpit
   - Vérifier que les valeurs ont augmenté :
     - Messages Total : +3
     - Tokens Total : augmenté
     - Coûts Total : augmenté

---

### Test 3 : Conversation avec Claude (Anthropic)

**Objectif** : Vérifier que les coûts Anthropic sont enregistrés correctement

**Étapes** :

1. **Créer une nouvelle session** :
   - Titre : "Test Coûts Claude"

2. **Sélectionner le modèle Claude** :
   - Vérifier que le modèle actif est `claude-3-5-haiku-20241022`
   - Si besoin, changer dans les paramètres

3. **Envoyer 2 messages** :

   **Message 1** :
   ```
   Quelle est la différence entre un token et un caractère ?
   ```

   **Message 2** :
   ```
   Comment Anthropic calcule-t-il les tokens pour Claude ?
   ```

4. **Vérifier les logs backend** :

   Chercher :
   ```
   [Anthropic] Cost calculated: $0.000XXX (model=claude-3-5-haiku-20241022, input=XXX tokens, output=XXX tokens, ...)
   ```

   **✅ SUCCÈS si** :
   - 2 lignes `[Anthropic] Cost calculated` apparaissent
   - Tokens > 0
   - Coût > $0.00

   **❌ ÉCHEC si** :
   - Warnings `[Anthropic] No usage data in final response`
   - Warnings `[Anthropic] Failed to get usage data`

5. **Analyser la BDD** :
   ```bash
   python check_db_simple.py
   ```

   **Vérifier** :
   - `claude-3-5-haiku` : nombre d'entries augmenté de +2
   - Coût total > Test 2
   - Tokens input et output > 0

---

### Test 4 : Conversation avec GPT (OpenAI)

**Objectif** : Vérifier que les coûts OpenAI fonctionnent toujours (régression)

**Étapes** :

1. **Créer une nouvelle session** :
   - Titre : "Test Coûts GPT"

2. **Sélectionner le modèle GPT** :
   - Vérifier que le modèle actif est `gpt-4o-mini`

3. **Envoyer 2 messages** :

   **Message 1** :
   ```
   Quel est le coût moyen d'une requête GPT-4o-mini ?
   ```

   **Message 2** :
   ```
   Compare les tarifs de GPT-4o-mini avec Gemini Flash.
   ```

4. **Vérifier les logs backend** :

   Chercher :
   ```
   [OpenAI] Cost calculated: $0.000XXX (model=gpt-4o-mini, input=XXX tokens, output=XXX tokens, ...)
   ```

5. **Analyser la BDD** :
   ```bash
   python check_db_simple.py
   ```

   **Vérifier** :
   - `gpt-4o-mini` : nombre d'entries augmenté de +2
   - Coûts cohérents avec les tests précédents

---

### Test 5 : Validation Cockpit Final

**Objectif** : Vérifier que toutes les métriques sont correctes dans le cockpit

**Étapes** :

1. **Actualiser le cockpit** :
   - Ouvrir `/cockpit`
   - Cliquer sur "Actualiser" si disponible

2. **Vérifier chaque carte** :

   **Messages** :
   - Total : devrait avoir augmenté de +7 (3 Gemini + 2 Claude + 2 GPT)
   - Aujourd'hui : +7
   - Cette semaine : +7
   - Ce mois : +7

   **Threads** :
   - Total : devrait avoir augmenté de +3 (3 nouvelles sessions)
   - Actifs : +3

   **Tokens** :
   - Total : devrait être > 0 et avoir augmenté
   - Input : > 0
   - Output : > 0
   - Moyenne/message : > 0

   **Coûts** :
   - Total : devrait être > baseline et > $0.00
   - Aujourd'hui : > $0.00
   - Cette semaine : > $0.00
   - Ce mois : > $0.00

3. **Capture d'écran finale** :
   - Prendre une capture d'écran du cockpit
   - Comparer avec la baseline (Test 1)

---

### Test 6 : Validation API

**Objectif** : Vérifier que l'API Dashboard retourne les bonnes données

**Étapes** :

1. **Récupérer le token d'authentification** :
   - Ouvrir les DevTools du navigateur (F12)
   - Console → Taper : `localStorage.getItem('emergence.id_token')`
   - Copier le token

2. **Tester l'API** :
   ```bash
   curl http://localhost:8000/api/dashboard/costs/summary \
     -H "Authorization: Bearer <VOTRE_TOKEN>" \
     | jq
   ```

3. **Vérifier la réponse JSON** :

   ```json
   {
     "costs": {
       "total_cost": 0.XXX,        // > 0
       "today_cost": 0.XXX,        // > 0
       "current_week_cost": 0.XXX, // > 0
       "current_month_cost": 0.XXX // > 0
     },
     "monitoring": {
       "total_documents": XXX,
       "total_sessions": XXX        // Augmenté de +3
     },
     "messages": {
       "total": XXX,                // Augmenté de +7
       "today": XXX,
       "week": XXX,
       "month": XXX
     },
     "tokens": {
       "total": XXX,                // > 0
       "input": XXX,                // > 0
       "output": XXX,               // > 0
       "avgPerMessage": XXX         // > 0
     }
   }
   ```

---

## ✅ Critères de Succès

### Succès Complet ✅

- ✅ **Gemini** : 3 logs `[Gemini] Cost calculated`, tokens > 0, coût > $0.00
- ✅ **Anthropic** : 2 logs `[Anthropic] Cost calculated`, tokens > 0, coût > $0.00
- ✅ **OpenAI** : 2 logs `[OpenAI] Cost calculated`, tokens > 0, coût > $0.00
- ✅ **BDD** : Total coûts augmenté, tous les modèles ont tokens > 0
- ✅ **Cockpit** : Toutes les cartes affichent des valeurs > 0
- ✅ **API** : `/api/dashboard/costs/summary` retourne des valeurs correctes

### Succès Partiel ⚠️

- ✅ OpenAI fonctionne
- ⚠️ Gemini ou Anthropic : coûts à $0.00 mais logs présents
  → Problème de pricing ou de calcul
- ⚠️ Cockpit affiche des valeurs mais elles ne correspondent pas à la BDD
  → Problème de frontend ou d'API

### Échec ❌

- ❌ Aucun log `[Gemini] Cost calculated` après 3 messages
  → `count_tokens()` ne fonctionne toujours pas
- ❌ Warnings `[Gemini] Failed to count input/output tokens` persistants
  → Problème avec l'API Google Generative AI
- ❌ Warnings `[Anthropic] No usage data in final response`
  → Problème avec `stream.get_final_response()`

---

## 🐛 Debugging

### Gemini : count_tokens() échoue

**Symptômes** :
- Warnings `[Gemini] Failed to count input tokens`
- Tokens = 0 dans la BDD

**Solutions** :

1. **Vérifier la version de google-generativeai** :
   ```bash
   pip show google-generativeai
   ```
   Version recommandée : ≥ 0.3.0

2. **Tester count_tokens() manuellement** :
   ```python
   import google.generativeai as genai
   genai.configure(api_key="VOTRE_API_KEY")
   model = genai.GenerativeModel("gemini-1.5-flash")
   result = model.count_tokens("Hello world")
   print(result.total_tokens)  # Devrait être > 0
   ```

3. **Vérifier l'API key** :
   ```bash
   echo $GOOGLE_API_KEY
   # Ou dans .env
   grep GOOGLE_API_KEY .env
   ```

### Anthropic : No usage data

**Symptômes** :
- Warnings `[Anthropic] No usage data in final response`
- Tokens = 0 dans la BDD

**Solutions** :

1. **Vérifier la version d'anthropic** :
   ```bash
   pip show anthropic
   ```
   Version recommandée : ≥ 0.7.0 (pour `stream.get_final_response()`)

2. **Tester stream.get_final_response() manuellement** :
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

## 📊 Rapport de Test (Template)

```markdown
# Rapport de Test - Coûts LLM
**Date** : YYYY-MM-DD
**Testeur** : [Nom]
**Version** : [Version du code]

## Résultats

### Test 1 : Baseline
- Total costs baseline : ___
- Total messages baseline : ___

### Test 2 : Gemini
- ✅/❌ Logs présents : Oui/Non
- ✅/❌ Tokens > 0 : Oui/Non
- ✅/❌ Coût > $0.00 : Oui/Non
- Coût moyen par message : $___.______

### Test 3 : Anthropic
- ✅/❌ Logs présents : Oui/Non
- ✅/❌ Tokens > 0 : Oui/Non
- ✅/❌ Coût > $0.00 : Oui/Non
- Coût moyen par message : $___.______

### Test 4 : OpenAI
- ✅/❌ Logs présents : Oui/Non (régression)
- ✅/❌ Tokens > 0 : Oui/Non
- ✅/❌ Coût > $0.00 : Oui/Non

### Test 5 : Cockpit
- ✅/❌ Messages : Valeurs correctes
- ✅/❌ Threads : Valeurs correctes
- ✅/❌ Tokens : Valeurs > 0
- ✅/❌ Coûts : Valeurs > $0.00

### Test 6 : API
- ✅/❌ Réponse JSON valide
- ✅/❌ Valeurs cohérentes avec BDD

## Conclusion
- ✅ SUCCÈS : Tous les tests passent
- ⚠️ PARTIEL : [Détails des problèmes]
- ❌ ÉCHEC : [Détails des échecs]

## Recommandations
[Actions à entreprendre si des problèmes persistent]
```

---

## 📚 Références

- [COCKPIT_COSTS_FIX_FINAL.md](COCKPIT_COSTS_FIX_FINAL.md) - Guide des corrections
- [COCKPIT_ROADMAP_FIXED.md](COCKPIT_ROADMAP_FIXED.md) - Feuille de route complète
- [check_db_simple.py](../../check_db_simple.py) - Script de diagnostic BDD

---

**Dernière mise à jour** : 2025-10-10
**Version du guide** : 1.0
