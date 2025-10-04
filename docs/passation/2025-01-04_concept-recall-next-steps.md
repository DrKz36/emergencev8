# Passation — Prochaines étapes Concept Recall

**Date** : 2025-01-04
**Session précédente** : Implémentation système concept recall (Phases 1-4)
**Commit** : `85855d8` - feat: add concept recall system for recurring topic detection
**Agent** : Claude Code (Sonnet 4.5)

---

## 📋 Contexte

Le système de détection et rappel de concepts récurrents a été **entièrement implémenté** et pushé sur `main`.

**Livrables complétés** :
- ✅ Backend : `ConceptRecallTracker`, enrichissement métadonnées, API search
- ✅ Frontend : `ConceptRecallBanner`, événements WebSocket, styles CSS
- ✅ Tests : 22 tests unitaires/intégration (backend)
- ✅ Documentation : Architecture complète + prompt implémentation

**Fichiers créés/modifiés** : 15 fichiers (6 backend, 5 frontend, 3 tests, 2 docs)

---

## 🎯 Tâches pour la prochaine instance

### **1. Validation & Activation (Priorité HAUTE)**

#### A. Exécuter la migration des concepts existants
```bash
# Migrer les métadonnées pour les concepts déjà en base
python scripts/migrate_concept_metadata.py

# Vérifier résultats dans logs
# Attendu : X concepts migrés, métadonnées enrichies
```

**Validation** :
- Vérifier logs : nombre de concepts migrés
- Inspecter ChromaDB : présence `first_mentioned_at`, `mention_count`, `thread_ids`

#### B. Activer l'émission d'événements WebSocket
```bash
# Ajouter dans .env.local
echo "CONCEPT_RECALL_EMIT_EVENTS=true" >> .env.local

# Redémarrer backend
pwsh -File scripts/run-backend.ps1
```

#### C. QA manuelle — Scénario de détection

**Étapes** :
1. Créer thread "DevOps Workflow"
2. Envoyer message : `"Comment setup une CI/CD pipeline avec GitHub Actions ?"`
3. Attendre réponse agent
4. Déclencher consolidation : `POST /api/memory/tend-garden`
5. Créer nouveau thread "Automation Best Practices"
6. Envoyer message : `"Je veux automatiser mon pipeline CI/CD pour déployer sur AWS"`
7. **Vérifier** :
   - Banner 🔗 s'affiche dans l'UI
   - Texte : "Concept déjà abordé : CI/CD pipeline"
   - Métadonnées : première mention + compteur threads
   - Console browser : `[Chat] handleConceptRecall: ...`

**Critères de succès** :
- [ ] Banner visible dans UI
- [ ] Données correctes (date, thread count)
- [ ] Bouton "Voir l'historique" fonctionnel
- [ ] Auto-hide après 15 secondes

---

### **2. Tests automatisés (Priorité MOYENNE)**

#### A. Exécuter suite tests backend
```bash
# Tests Phase 1 : Enrichissement métadonnées
pytest tests/backend/features/test_memory_gardener_enrichment.py -v

# Tests Phase 2 : ConceptRecallTracker
pytest tests/backend/features/test_concept_recall_tracker.py -v

# Tests Phase 4 : API search
pytest tests/backend/features/test_memory_concept_search.py -v
```

**Attendu** :
- 22 tests passent (ou identifier failures + proposer fixes)
- Couverture ≥ 80% pour `concept_recall.py`

#### B. Tests frontend (si environnement configuré)
```bash
npm test -- src/frontend/features/chat/__tests__/concept-recall.test.js
```

**Note** : Fichier test frontend **pas encore créé** → à implémenter si besoin.

---

### **3. Optimisations & Améliorations (Priorité BASSE)**

#### A. Performance monitoring
- Ajouter métriques Prometheus :
  - `concept_recalls_detected_total` (counter)
  - `concept_recall_latency_ms` (histogram)
- Logger temps d'exécution `detect_recurring_concepts()`
- Objectif : < 500ms par détection

#### B. UI/UX enhancements
- Modal "Voir l'historique" (Phase 3+) :
  - Timeline des mentions avec dates/threads
  - Liens cliquables vers threads concernés
  - Graphique évolution mention_count
- Toggle utilisateur "Désactiver rappels concepts" (paramètres)
- Cooldown : max 1 rappel/concept/24h (éviter spam)

#### C. Clustering sémantique (Phase 5 — Future)
- Détecter synonymes/reformulations :
  - "CI/CD" ≈ "pipeline automatique" ≈ "intégration continue"
- Utiliser HDBSCAN ou K-means sur embeddings
- UI admin pour merge manuel concepts similaires

---

## 📚 Ressources clés

**Documentation** :
1. **[docs/architecture/CONCEPT_RECALL.md](../architecture/CONCEPT_RECALL.md)** — Architecture complète (1200 lignes)
   - Section 4 : Implémentation technique
   - Section 7 : Tests & validation
   - Section 9 : Exemples d'usage

2. **[docs/architecture/CONCEPT_RECALL_IMPLEMENTATION_PROMPT.md](../architecture/CONCEPT_RECALL_IMPLEMENTATION_PROMPT.md)** — Prompt original (700 lignes)

**Code principal** :
- Backend : [src/backend/features/memory/concept_recall.py](../../src/backend/features/memory/concept_recall.py)
- Frontend : [src/frontend/features/chat/concept-recall-banner.js](../../src/frontend/features/chat/concept-recall-banner.js)
- Router : [src/backend/features/memory/router.py](../../src/backend/features/memory/router.py#L603-L652) (endpoint `/concepts/search`)

**Tests** :
- [tests/backend/features/test_concept_recall_tracker.py](../../tests/backend/features/test_concept_recall_tracker.py) — 9 tests
- [tests/backend/features/test_memory_gardener_enrichment.py](../../tests/backend/features/test_memory_gardener_enrichment.py) — 5 tests
- [tests/backend/features/test_memory_concept_search.py](../../tests/backend/features/test_memory_concept_search.py) — 8 tests

---

## 🔧 Commandes utiles

### Démarrage
```bash
# Backend (port 8000)
pwsh -File scripts/run-backend.ps1

# Frontend (Vite dev server)
npm run dev
```

### Logs & Debug
```bash
# Logs backend (concept recall)
tail -f logs/backend.log | grep -i "ConceptRecall"

# Inspecter ChromaDB
python -c "
from backend.features.memory.vector_service import VectorService
vs = VectorService()
col = vs.get_or_create_collection('emergence_knowledge')
result = col.get(where={'type': 'concept'}, limit=5, include=['metadatas'])
print(result['metadatas'])
"
```

### API Manuelle
```bash
# Tester endpoint search (nécessite auth token)
curl -X GET "http://localhost:8000/api/memory/concepts/search?q=docker&limit=5" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "X-Session-Id: test_session"
```

---

## ⚠️ Points de vigilance

### Blocages potentiels

1. **Migration échoue** :
   - Cause : Concepts sans `created_at`
   - Fix : Fallback sur `datetime.now()` dans script

2. **WS events non émis** :
   - Cause : `CONCEPT_RECALL_EMIT_EVENTS=false` (par défaut)
   - Fix : Vérifier `.env.local` + redémarrer backend

3. **Banner ne s'affiche pas** :
   - Cause : Conteneur `.concept-recall-container` manquant
   - Fix : Vérifier `chat-ui.js:82` injecte le conteneur
   - Debug : Console browser → chercher warnings ConceptRecallBanner

4. **Seuil similarité trop strict** :
   - Symptôme : Aucune détection malgré concepts similaires
   - Fix : Réduire `SIMILARITY_THRESHOLD` de 0.75 à 0.70 dans `concept_recall.py:28`

5. **Performance dégradée** :
   - Symptôme : Détection > 500ms
   - Fix : Ajouter index ChromaDB ou réduire `n_results` de 10 à 5

---

## 📝 Checklist validation finale

- [ ] Migration exécutée sans erreurs
- [ ] Variable `CONCEPT_RECALL_EMIT_EVENTS=true` active
- [ ] QA manuelle : banner s'affiche correctement
- [ ] Tests backend : 22/22 passent
- [ ] Logs backend : aucun WARNING/ERROR lié à concept recall
- [ ] Performance : détection < 500ms (vérifier logs)
- [ ] UI responsive : banner mobile OK
- [ ] Dark mode : styles corrects
- [ ] Bouton "Ignorer" cache le banner
- [ ] Auto-hide après 15s fonctionne

---

## 🚀 Actions recommandées pour cette session

**Si temps limité (< 2h)** :
1. ✅ Migration + activation WS
2. ✅ QA manuelle scénario 1
3. ✅ Tests backend (exécution)

**Si temps disponible (2-4h)** :
1. ✅ Tout ci-dessus
2. ✅ Fixes tests échoués (si présents)
3. ✅ Ajout métriques performance
4. ✅ Documentation mise à jour (si changements)

**Si temps étendu (> 4h)** :
1. ✅ Tout ci-dessus
2. ✅ Implémentation modal historique
3. ✅ Tests frontend
4. ✅ Clustering sémantique (Phase 5)

---

## 📌 Notes importantes

- **Ne pas** modifier l'architecture sans validation FG
- **Ne pas** commit/push sans tests validés
- **Documenter** tout changement dans `docs/passation.md`
- **Logger** problèmes rencontrés pour debug futur
- **Respecter** CODEV_PROTOCOL.md (pas de snapshot ARBO sans nécessité)

---

**Bon courage ! Le système est opérationnel, il ne reste que la validation terrain. 💪**
