# Concept Recall - Guide QA Manuelle

**Date** : 2025-10-04
**Version** : 1.0 (Post-fix ChromaDB)
**Prérequis** : Backend actif avec `CONCEPT_RECALL_EMIT_EVENTS=true`

## Objectif

Valider le système de détection de concepts récurrents en conditions réelles avec l'interface utilisateur.

## Configuration

### 1. Vérifier l'environnement

```bash
# .env.local doit contenir
CONCEPT_RECALL_EMIT_EVENTS=true

# Démarrer backend
pwsh -File scripts/run-backend.ps1

# Vérifier initialisation dans les logs
# Chercher : "ConceptRecallTracker initialisé"
```

### 2. Préparer le navigateur

- Ouvrir DevTools (F12)
- Onglet Console : surveiller événements WebSocket
- Onglet Network : filtrer `ws:` pour voir les frames

## Scénario de test

### Étape 1 : Première mention (baseline)

**Objectif** : Créer un concept sans détection

1. **Créer thread "DevOps Setup"**
   - Ouvrir UI → Module Chat
   - Nouveau thread → titre "DevOps Setup"

2. **Envoyer message initial**
   ```
   Comment setup une CI/CD pipeline GitHub Actions ?
   ```

3. **Attendre réponse complète**
   - L'agent répond normalement
   - Vérifier Console : aucun événement `ws:concept_recall`

4. **Consolider mémoire**
   - Cliquer bouton "Jardiner la mémoire" (ou POST `/api/memory/tend-garden`)
   - Attendre fin consolidation
   - Vérifier logs backend : "concepts vectorisés"

### Étape 2 : Détection cross-thread

**Objectif** : Déclencher rappel de concept

1. **Créer nouveau thread "Automation"**
   - Nouveau thread → titre "Automation"
   - **Important** : Thread différent du précédent

2. **Envoyer message similaire**
   ```
   Je veux automatiser mon pipeline CI/CD sur AWS
   ```

3. **Observer détection** ✅
   - **Banner doit apparaître** en haut du chat
   - Texte : "🔗 Concept déjà abordé : CI/CD pipeline"
   - Métadonnées : date première mention, nombre de threads
   - Score de similarité ≥ 0.5 (50%)

4. **Vérifier événement WebSocket**
   ```javascript
   // Console DevTools
   {
     type: "ws:concept_recall",
     payload: {
       recalls: [{
         concept: "CI/CD pipeline",
         first_mentioned_at: "2025-10-04T...",
         thread_count: 1,
         similarity: 0.547
       }]
     }
   }
   ```

### Étape 3 : Interactions utilisateur

**Objectif** : Tester les actions sur le banner

1. **Bouton "Ignorer"**
   - Cliquer "Ignorer" sur le banner
   - ✅ Banner disparaît immédiatement
   - Note : Comptabilisé comme false positive (future métrique)

2. **Auto-hide après 15s**
   - Refaire Étape 2 (nouveau thread + message similaire)
   - ✅ Banner s'affiche
   - Attendre 15 secondes sans interaction
   - ✅ Banner disparaît automatiquement

3. **Bouton "Voir l'historique"** (si implémenté)
   - Cliquer "Voir l'historique"
   - ✅ Modal affiche threads passés
   - ✅ Navigation vers thread source fonctionne

### Étape 4 : Limites et edge cases

**Objectif** : Valider comportements limites

1. **Même thread** (pas de détection)
   - Rester sur thread "Automation"
   - Envoyer nouveau message sur CI/CD
   - ✅ Aucun banner (concept du thread actuel exclu)

2. **Limite 3 détections**
   - Créer message avec 4+ concepts récurrents
   - ✅ Maximum 3 banners affichés (MAX_RECALLS_PER_MESSAGE)

3. **Score faible** (pas de détection)
   - Message très différent (ex: "Quel temps fait-il ?")
   - ✅ Aucune détection (score < 0.5)

## Checklist de validation

### Affichage UI
- [ ] Banner s'affiche en haut du chat
- [ ] Icône 🔗 présente
- [ ] Texte concept correct
- [ ] Métadonnées (date, threads) affichées
- [ ] Score de similarité affiché
- [ ] Bouton "Ignorer" présent
- [ ] Bouton "Voir l'historique" présent (si implémenté)

### Événements WebSocket
- [ ] Frame `ws:concept_recall` reçue
- [ ] Payload contient `recalls[]`
- [ ] Chaque recall contient : `concept`, `first_mentioned_at`, `thread_count`, `similarity`
- [ ] Pas d'événement pour même thread
- [ ] Maximum 3 recalls par message

### Comportement
- [ ] Auto-hide fonctionne après 15s
- [ ] Bouton "Ignorer" ferme immédiatement
- [ ] Détection fonctionne cross-thread uniquement
- [ ] Pas de détection si score < 0.5
- [ ] Gardening consolide correctement les concepts

## Captures à archiver

Créer screenshots dans `docs/assets/qa/concept-recall/` :

1. **concept-recall-banner.png**
   - Banner affiché avec métadonnées complètes

2. **concept-recall-console.png**
   - Console DevTools avec événement `ws:concept_recall`

3. **concept-recall-ignore.png**
   - État après clic "Ignorer"

4. **concept-recall-history-modal.png** (si implémenté)
   - Modal historique ouvert

## Logs à vérifier

### Backend logs (rechercher dans output)

```
# Détection
[ConceptRecallTracker] Concept: CI/CD pipeline | Distance: 0.905 | Score: 0.547

# Mise à jour métadonnées
[ConceptRecallTracker] Concept {id} mis à jour : 2 mentions

# Émission événement
[ConceptRecallTracker] Événement ws:concept_recall émis : 1 récurrences
```

### Frontend console (filtrer "concept")

```javascript
[WebSocket] Received: ws:concept_recall
[ConceptRecall] Displaying banner for: CI/CD pipeline
[ConceptRecall] Auto-hiding in 15s
```

## Problèmes connus et résolutions

### ❌ Banner ne s'affiche pas
- Vérifier `CONCEPT_RECALL_EMIT_EVENTS=true` dans `.env.local`
- Relancer backend
- Vérifier logs : "ConceptRecallTracker initialisé"

### ❌ Événement WS non reçu
- Vérifier DevTools > Network > WS frame
- Confirmer connexion WebSocket active
- Tester avec autre concept (score peut être trop faible)

### ❌ Détection dans même thread
- Bug potentiel : vérifier filtrage `thread_ids_json`
- Voir logs backend pour thread_id

### ❌ Score toujours < 0.5
- Messages trop différents sémantiquement
- Essayer phrases plus similaires
- Vérifier formule : `score = 1 - (distance / 2)`

## Critères de succès

✅ **QA validée si** :
- 5/5 détections cross-thread réussies
- 0/5 faux positifs (même thread)
- Banner s'affiche en < 500ms après réponse
- Auto-hide fonctionne
- Événements WS corrects
- Aucune erreur console/backend

## Prochaines étapes

Après validation QA :
1. Archiver captures dans `docs/assets/qa/concept-recall/`
2. Mettre à jour `docs/passation.md` avec résultats
3. Créer issue GitHub pour modal "Voir l'historique" (si non implémenté)
4. Planifier implémentation métriques Prometheus (voir [concept-recall-monitoring.md](../features/concept-recall-monitoring.md))

## Support

- **Documentation** : [README_CONCEPT_RECALL_TESTS.md](../../tests/backend/features/README_CONCEPT_RECALL_TESTS.md)
- **Code** : [concept_recall.py](../../src/backend/features/memory/concept_recall.py)
- **Tests** : `pytest tests/backend/features/test_concept_recall_*.py -v`
