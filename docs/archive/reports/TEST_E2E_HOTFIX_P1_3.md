# Test End-to-End Local - Hotfix P1.3

Ce document décrit le scénario de test end-to-end complet pour valider le Hotfix P1.3 en environnement local avant déploiement production.

---

## 🎯 Objectifs

1. Vérifier que l'extraction de préférences fonctionne avec `user_id` en fallback
2. Valider que les préférences sont correctement sauvegardées dans ChromaDB local
3. Confirmer que les métriques Prometheus sont exposées
4. S'assurer qu'aucune régression n'a été introduite

---

## ✅ Pré-requis

- [x] Backend local démarré
- [x] ChromaDB local configuré (./chroma_data)
- [x] Variables d'environnement configurées (.env)
- [x] Hotfix P1.3 appliqué (commit 74c34c1)

---

## 📋 Scénario de Test

### Étape 1 : Vérifier que le backend démarre sans erreur

```powershell
# Terminal 1 : Démarrer le backend
pwsh -File scripts/run-backend.ps1
```

**Vérifications** :
- ✅ Backend démarre sur http://localhost:8000
- ✅ Log : `MemoryAnalyzer V3.7 (P1) initialisé. Prêt: True`
- ✅ Log : `PreferenceExtractor` initialisé sans erreur
- ✅ Aucun warning/error au démarrage

**Si erreur** : Vérifier les logs et corriger avant de continuer

---

### Étape 2 : Tester extraction unitaire (déjà fait ✅)

```powershell
python scripts/test_hotfix_p1_3_local.py
```

**Résultat attendu** :
```
✅ TOUS LES TESTS SONT PASSÉS !
🚀 Hotfix P1.3 prêt pour déploiement production
```

**Status** : ✅ PASSÉ (5/5 tests)

---

### Étape 3 : Test End-to-End via API

#### 3.1 - Health Check

```powershell
curl http://localhost:8000/api/health
```

**Résultat attendu** :
```json
{
  "status": "healthy",
  "version": "1.0.0",
  ...
}
```

#### 3.2 - Créer une session WebSocket et envoyer des messages

**Option A : Via WebSocket client Python**

Créer `scripts/test_e2e_preferences.py` :

```python
import asyncio
import websockets
import json

async def test_preference_extraction():
    # Connexion WebSocket
    uri = "ws://localhost:8000/api/chat/ws"

    async with websockets.connect(uri) as websocket:
        print("✅ WebSocket connecté")

        # Recevoir message session_established
        msg = await websocket.recv()
        print(f"📨 Reçu: {msg}")

        # Envoyer messages avec préférences
        messages = [
            {
                "type": "chat.message",
                "payload": {
                    "text": "Je préfère utiliser Python avec FastAPI pour mes APIs",
                    "agent_id": "anima",
                    "use_rag": False
                }
            },
            {
                "type": "chat.message",
                "payload": {
                    "text": "J'aime beaucoup TypeScript pour le frontend",
                    "agent_id": "nexus",
                    "use_rag": False
                }
            },
            {
                "type": "chat.message",
                "payload": {
                    "text": "J'évite toujours les bases NoSQL pour les données critiques",
                    "agent_id": "anima",
                    "use_rag": False
                }
            }
        ]

        for msg_data in messages:
            await websocket.send(json.dumps(msg_data))
            print(f"📤 Envoyé: {msg_data['payload']['text'][:50]}...")

            # Attendre réponse
            response = await websocket.recv()
            print(f"📨 Réponse reçue")

        print("\n✅ 3 messages avec préférences envoyés")
        print("⏳ Fermeture WebSocket pour déclencher finalisation...")

        # Fermer WebSocket (déclenche session finalization)

asyncio.run(test_preference_extraction())
```

**Exécuter** :
```powershell
python scripts/test_e2e_preferences.py
```

**Option B : Via DevTools navigateur**

1. Ouvrir http://localhost:3000 (frontend local)
2. Ouvrir DevTools → Console
3. Envoyer messages via interface chat :
   - "Je préfère utiliser Python avec FastAPI pour mes APIs"
   - "J'aime beaucoup TypeScript pour le frontend"
   - "J'évite toujours les bases NoSQL pour les données critiques"
4. Fermer l'onglet (déclenche session finalization)

---

### Étape 4 : Vérifier les logs backend

**Dans le terminal backend, chercher** :

✅ **Logs attendus (SUCCESS)** :
```
[PreferenceExtractor] Extracted 3 preferences/intents for session XXX (user_sub=None, user_id=YYY)
[PreferenceExtractor] user_sub missing, using user_id=YYY as fallback (thread_id=ZZZ)
[PreferenceExtractor] Saved 3/3 preferences to ChromaDB for user YYY
```

❌ **Logs à NE PAS voir (FAILURE)** :
```
[PreferenceExtractor] Cannot extract: user_sub not found for session XXX
ValueError: Cannot extract preferences: no user identifier
```

---

### Étape 5 : Valider ChromaDB local

```powershell
python scripts/validate_preferences.py --limit 10
```

**Résultat attendu** :
```
🔍 Validation ChromaDB - Collection 'memory_preferences'
📂 Répertoire: ./chroma_data
------------------------------------------------------------
✅ Connexion ChromaDB établie
✅ Collection 'memory_preferences' trouvée
📊 Total préférences: 3 (ou plus)

📋 Affichage de 3 préférences:
------------------------------------------------------------

🔹 Préférence 1/3
   User: user_XXX (ou None si user_sub absent)
   Type: preference
   Topic: programmation
   Action: utiliser
   Sentiment: positive
   Confidence: 0.85
   Session: session_YYY
   Thread: thread_ZZZ
   Text: Je préfère utiliser Python avec FastAPI...

🔹 Préférence 2/3
   ...

============================================================
✅ Validation terminée avec succès
```

**Si échec** :
- Vérifier logs backend (erreurs extraction)
- Vérifier chemin ChromaDB (./chroma_data)
- Réessayer test E2E

---

### Étape 6 : Vérifier métriques Prometheus

```powershell
curl http://localhost:8000/api/metrics | Select-String "memory_preference"
```

**Métriques attendues** :

✅ **Succès (valeurs > 0)** :
```
memory_preferences_extracted_total{type="preference"} 2.0
memory_preferences_extracted_total{type="intent"} 0.0
memory_preferences_extracted_total{type="constraint"} 1.0

memory_preferences_confidence_bucket{le="0.5"} 0.0
memory_preferences_confidence_bucket{le="0.8"} 1.0
memory_preferences_confidence_bucket{le="1.0"} 3.0

memory_preferences_extraction_duration_seconds_count 1.0
memory_preferences_extraction_duration_seconds_sum 0.523
```

✅ **Échecs (valeurs = 0)** :
```
memory_preference_extraction_failures_total{reason="user_identifier_missing"} 0.0
memory_preference_extraction_failures_total{reason="extraction_error"} 0.0
memory_preference_extraction_failures_total{reason="persistence_error"} 0.0
```

**Si métriques échecs > 0** : Vérifier logs pour identifier la cause

---

### Étape 7 : Tests de régression

```powershell
# Tous les tests mémoire
python -m pytest tests/backend/features/ -k "memory" -v

# Tests spécifiques hotfix
python -m pytest tests/backend/features/test_preference_extraction_context.py -v

# Tests extraction + persistence
python -m pytest tests/backend/features/test_memory_preferences_persistence.py -v
```

**Résultat attendu** :
- ✅ Tous tests passants (0 échecs)
- ✅ Aucune régression détectée

---

## 🎯 Checklist Validation Finale

Avant déploiement production, vérifier :

### Tests unitaires
- [x] 8/8 tests hotfix passants
- [x] 49/49 tests mémoire passants
- [x] 5/5 tests script local passants

### Tests E2E local
- [ ] Backend démarre sans erreur
- [ ] Session WebSocket fonctionne
- [ ] 3+ messages avec préférences envoyés
- [ ] Logs montrent extraction réussie
- [ ] Logs montrent fallback user_id utilisé
- [ ] ChromaDB contient préférences (count > 0)
- [ ] Métriques Prometheus exposées
- [ ] Métriques échecs = 0
- [ ] Aucune régression tests

### Logs backend
- [ ] `[PreferenceExtractor] Extracted X preferences`
- [ ] `[PreferenceExtractor] user_sub missing, using user_id=XXX`
- [ ] `[PreferenceExtractor] Saved X/X preferences to ChromaDB`
- [ ] AUCUNE erreur `user_sub not found`
- [ ] AUCUNE ValueError

### ChromaDB local
- [ ] Collection `memory_preferences` existe
- [ ] Count ≥ 3 préférences
- [ ] Metadata contient `user_id` (et/ou `user_sub`)
- [ ] Metadata contient `session_id`, `thread_id`
- [ ] Metadata contient `type`, `topic`, `confidence`

### Métriques
- [ ] `memory_preferences_extracted_total` > 0
- [ ] `memory_preference_extraction_failures_total` = 0
- [ ] `memory_preferences_confidence_*` présentes
- [ ] `memory_preferences_extraction_duration_seconds` présente

---

## 🚀 Après validation complète

Si **TOUS** les points de la checklist sont cochés :

1. **Commit et push** :
   ```bash
   git push origin main
   ```

2. **Déployer en production** :
   ```bash
   gcloud builds submit --config cloudbuild.yaml
   ```

3. **Répéter validation en production** (voir ci-dessous)

---

## 🔍 Validation Production (Post-Déploiement)

### Logs production

```bash
gcloud run services logs read emergence-app --limit 200 | grep "PreferenceExtractor"
```

Chercher :
- ✅ `[PreferenceExtractor] Extracted X preferences`
- ✅ `[PreferenceExtractor] user_sub missing, using user_id=XXX`
- ❌ AUCUNE erreur `user_sub not found`

### Métriques production

```bash
curl https://emergence-app-47nct44nma-ew.a.run.app/api/metrics | grep "memory_preference"
```

Vérifier :
- `memory_preferences_extracted_total > 0`
- `memory_preference_extraction_failures_total = 0`

### ChromaDB production

⚠️ **Note** : ChromaDB production n'est pas directement accessible. Utiliser les logs backend pour confirmer :
- `[PreferenceExtractor] Saved X/X preferences to ChromaDB`

---

## 📚 Troubleshooting

### Problème : Backend ne démarre pas

**Solution** :
1. Vérifier .env configuré
2. Vérifier dépendances : `pip install -r requirements.txt`
3. Vérifier port 8000 libre : `netstat -ano | findstr :8000`

### Problème : ChromaDB collection introuvable

**Solution** :
1. Supprimer ./chroma_data : `rm -r -force ./chroma_data`
2. Redémarrer backend (recrée collections)
3. Réessayer test E2E

### Problème : Métriques échecs > 0

**Solution** :
1. Vérifier logs backend : `reason="XXX"`
2. Si `user_identifier_missing` : vérifier session contient user_id
3. Si `extraction_error` : vérifier LLM API accessible
4. Si `persistence_error` : vérifier ChromaDB accessible

### Problème : Tests E2E échouent

**Solution** :
1. Vérifier logs backend (erreurs détaillées)
2. Vérifier WebSocket connecté correctement
3. Vérifier messages envoyés contiennent mots-clés préférences
4. Réessayer avec délai entre messages (rate limiting)

---

## ✅ Validation Réussie

Si tous les tests locaux passent :
- ✅ **Hotfix P1.3 validé localement**
- 🚀 **Prêt pour déploiement production**
- 📋 **Suivre procédure déploiement ci-dessus**

---

**Dernière mise à jour** : 2025-10-10 14:45
**Status** : Tests unitaires ✅ | E2E local ⏳ | Production ⏳
