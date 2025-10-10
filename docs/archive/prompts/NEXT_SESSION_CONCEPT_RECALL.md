# 🚀 Prochaine Session - Concept Recall QA & Suite

**Date de préparation** : 2025-10-04
**Statut actuel** : ✅ Bug ChromaDB corrigé, backend opérationnel, tests 12/12 passent

## 📋 Résumé de la session précédente

### ✅ Accomplissements

1. **Correction bug ChromaDB thread_ids**
   - Migration `thread_ids` (liste) → `thread_ids_json` (JSON string)
   - Commits : [f4e12e1](https://github.com/DrKz36/emergencev8/commit/f4e12e1), [b036afb](https://github.com/DrKz36/emergencev8/commit/b036afb)

2. **Corrections techniques**
   - Formule distance→score : `1 - (distance/2)` pour L2² ChromaDB
   - Seuil ajusté : 0.5 (au lieu de 0.75)
   - Métadonnées NULL → `""` pour compatibilité

3. **Tests validés**
   - 8/8 concept_recall_tracker
   - 4/4 memory_gardener_enrichment
   - **Total : 12/12 passent** ✅

4. **Documentation**
   - [README_CONCEPT_RECALL_TESTS.md](tests/backend/features/README_CONCEPT_RECALL_TESTS.md) - Marqué FIXED
   - [concept-recall-monitoring.md](docs/features/concept-recall-monitoring.md) - Plan métriques Prometheus
   - [concept-recall-manual-qa.md](docs/qa/concept-recall-manual-qa.md) - Guide QA UI

5. **Backend opérationnel**
   - ConceptRecallTracker initialisé
   - `CONCEPT_RECALL_EMIT_EVENTS=true` configuré
   - Aucune migration nécessaire (vector store vide)

## 🎯 Prochaines actions prioritaires

### 1. QA Manuelle UI (1-2h) - **PRIORITÉ 1**

**Guide complet** : [docs/qa/concept-recall-manual-qa.md](docs/qa/concept-recall-manual-qa.md)

#### Checklist rapide
```bash
# 1. Backend actif
pwsh -File scripts/run-backend.ps1
# Vérifier log: "ConceptRecallTracker initialisé"

# 2. Ouvrir UI + DevTools (F12)
npm run dev  # ou ouvrir http://localhost:5173

# 3. Scénario test
# A. Thread "DevOps Setup" → message CI/CD
# B. Consolider mémoire (bouton "Jardiner")
# C. Nouveau thread "Automation" → message CI/CD similaire
# D. ✅ Vérifier banner "🔗 Concept déjà abordé"
```

#### Captures attendues
- `docs/assets/qa/concept-recall/concept-recall-banner.png`
- `docs/assets/qa/concept-recall/concept-recall-console.png`
- `docs/assets/qa/concept-recall/concept-recall-ignore.png`

#### Critères succès
- [ ] Banner s'affiche < 500ms
- [ ] Événement `ws:concept_recall` reçu
- [ ] Score ≥ 0.5 affiché
- [ ] Auto-hide après 15s fonctionne
- [ ] Pas de détection dans même thread

### 2. Modal "Voir l'historique" (3-4h) - **PRIORITÉ 2**

**Objectif** : Permettre navigation vers threads passés mentionnant le concept

#### Tâches
1. **Backend endpoint** : `GET /api/memory/concept-history/{concept_id}`
   - Retourne threads avec dates, messages, liens
   - Filtré par user_id

2. **Frontend modal component**
   ```javascript
   // src/frontend/features/memory/components/ConceptHistoryModal.js
   class ConceptHistoryModal {
     async loadHistory(conceptId) {
       const threads = await api.getConceptHistory(conceptId);
       this.render(threads);
     }
   }
   ```

3. **Intégration banner**
   - Bouton "Voir l'historique" → ouvre modal
   - Liste threads chronologique
   - Clic thread → navigation + fermeture modal

4. **Tests**
   ```bash
   # Backend
   pytest tests/backend/features/test_concept_history_endpoint.py

   # Frontend
   npm test -- src/frontend/features/memory/__tests__/concept-history-modal.test.js
   ```

### 3. Métriques Prometheus (4-5h) - **PRIORITÉ 3**

**Plan détaillé** : [docs/features/concept-recall-monitoring.md](docs/features/concept-recall-monitoring.md)

#### Phase 1 : Infrastructure
```python
# src/backend/features/memory/metrics.py
from prometheus_client import Counter, Histogram

DETECTIONS = Counter(
    'concept_recall_detections_total',
    'Total detections',
    ['user_id', 'similarity_range']
)

SIMILARITY_SCORE = Histogram(
    'concept_recall_similarity_score',
    'Score distribution',
    buckets=[0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)
```

#### Phase 2 : Instrumentation
- `detect_recurring_concepts()` → compteurs + histogrammes
- `_emit_concept_recall_event()` → événements WS
- Labels : `similarity_range`, `thread_count_range`

#### Phase 3 : Endpoint
- `GET /api/metrics` → format Prometheus
- Optionnel : Dashboard Grafana

## 📁 Fichiers importants

### Code source
- [src/backend/features/memory/concept_recall.py](src/backend/features/memory/concept_recall.py)
- [src/backend/features/memory/gardener.py](src/backend/features/memory/gardener.py)

### Tests
- [tests/backend/features/test_concept_recall_tracker.py](tests/backend/features/test_concept_recall_tracker.py)
- [tests/backend/features/test_memory_gardener_enrichment.py](tests/backend/features/test_memory_gardener_enrichment.py)

### Documentation
- [tests/backend/features/README_CONCEPT_RECALL_TESTS.md](tests/backend/features/README_CONCEPT_RECALL_TESTS.md)
- [docs/qa/concept-recall-manual-qa.md](docs/qa/concept-recall-manual-qa.md)
- [docs/features/concept-recall-monitoring.md](docs/features/concept-recall-monitoring.md)
- [docs/passation.md](docs/passation.md) - Entrée 2025-10-04 16:39

### Configuration
- `.env.local` → `CONCEPT_RECALL_EMIT_EVENTS=true`

## 🔧 Commandes utiles

```bash
# Backend
pwsh -File scripts/run-backend.ps1
curl http://127.0.0.1:8000/api/health

# Tests
pytest tests/backend/features/test_concept_recall_*.py -v

# Frontend (si nécessaire)
npm run dev
npm test -- concept-recall

# Git
git log --oneline -5  # Voir derniers commits
git show f4e12e1       # Voir commit fix ChromaDB
```

## ⚠️ Points d'attention

1. **Backend requis** : Toujours démarrer backend avant QA UI
2. **Env vars** : Vérifier `CONCEPT_RECALL_EMIT_EVENTS=true`
3. **Consolidation** : Cliquer "Jardiner" entre étapes test
4. **Seuil 0.5** : Messages doivent être sémantiquement similaires (50%+)
5. **Cross-thread only** : Aucune détection dans même thread (by design)

## 📊 Métriques de succès globales

### Phase actuelle (QA)
- [ ] QA manuelle validée (5/5 scénarios)
- [ ] Captures archivées
- [ ] Aucune erreur console/backend
- [ ] Documentation passation mise à jour

### Phase suivante (Features)
- [ ] Modal "Voir l'historique" implémenté
- [ ] Tests modal 100% couverture
- [ ] Métriques Prometheus exposées
- [ ] Dashboard Grafana configuré (optionnel)

## 🚦 État des features

| Feature | Statut | Tests | Documentation |
|---------|--------|-------|---------------|
| Détection concepts | ✅ Opérationnel | 8/8 ✅ | ✅ Complète |
| Enrichissement métadonnées | ✅ Opérationnel | 4/4 ✅ | ✅ Complète |
| Événements WebSocket | ✅ Opérationnel | - | ✅ Complète |
| Banner UI | ⚠️ À valider QA | - | ✅ Guide QA |
| Modal historique | 📋 Planifié | - | - |
| Métriques Prometheus | 📋 Planifié | - | ✅ Plan détaillé |

## 📞 Support

Si problème pendant QA :
1. Vérifier logs backend : `ConceptRecallTracker initialisé`
2. DevTools Console : chercher `ws:concept_recall`
3. Relancer backend si événements non émis
4. Consulter [README_CONCEPT_RECALL_TESTS.md](tests/backend/features/README_CONCEPT_RECALL_TESTS.md)

---

**Prêt pour la QA !** 🚀 Commencer par [docs/qa/concept-recall-manual-qa.md](docs/qa/concept-recall-manual-qa.md)
