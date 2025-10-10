# 🚀 Prompt pour la Prochaine Session Claude Code

**Date de création** : 2025-10-04
**Contexte** : Suite correction bug ChromaDB + Concept Recall System

---

## 📋 Contexte Rapide

Le système de **Concept Recall** (détection de concepts récurrents) a été corrigé et validé par tests automatisés (12/12 ✅). Le backend est opérationnel. **Prochaine étape : QA manuelle avec UI**.

### État actuel
- ✅ Bug ChromaDB thread_ids corrigé ([commit f4e12e1](https://github.com/DrKz36/emergencev8/commit/f4e12e1))
- ✅ Tests : 12/12 passent (8 tracker + 4 gardener)
- ✅ Documentation complète créée
- ✅ Backend actif avec ConceptRecallTracker initialisé
- ⏳ QA manuelle UI à effectuer

### Commits récents
```
f418dbc docs: add concept recall QA guide and next session instructions
b036afb docs: update concept recall documentation and add monitoring plan
f4e12e1 fix: ChromaDB thread_ids bug - use JSON strings instead of lists
```

---

## 🎯 Mission Prioritaire : QA Manuelle UI

### Objectif
Valider le système de détection de concepts récurrents en conditions réelles avec l'interface utilisateur.

### Guide complet
📖 **[docs/qa/concept-recall-manual-qa.md](docs/qa/concept-recall-manual-qa.md)**

### Scénario rapide (30 min)

#### 1. Préparer l'environnement
```bash
# Vérifier backend actif
curl http://127.0.0.1:8000/api/health
# Si non actif : pwsh -File scripts/run-backend.ps1

# Vérifier configuration
cat .env.local | grep CONCEPT_RECALL
# Doit afficher : CONCEPT_RECALL_EMIT_EVENTS=true

# Ouvrir UI
npm run dev  # ou ouvrir http://localhost:5173
```

#### 2. Exécuter test cross-thread

**A. Créer baseline (première mention)**
1. Ouvrir UI → Module Chat
2. Nouveau thread → titre "DevOps Setup"
3. Message : `Comment setup une CI/CD pipeline GitHub Actions ?`
4. Attendre réponse complète
5. Cliquer "Jardiner la mémoire" (consolider)

**B. Déclencher détection (cross-thread)**
1. Nouveau thread → titre "Automation"
2. Message : `Je veux automatiser mon pipeline CI/CD sur AWS`
3. **✅ Vérifier : Banner "🔗 Concept déjà abordé : CI/CD pipeline" s'affiche**

**C. Valider événement WebSocket**
1. DevTools (F12) → Console
2. Chercher : `ws:concept_recall`
3. **✅ Vérifier payload avec concept, date, thread_count, similarity ≥ 0.5**

**D. Tester interactions**
- Cliquer "Ignorer" → banner disparaît ✅
- Refaire étape B → attendre 15s → auto-hide ✅

#### 3. Captures à archiver
```bash
# Créer dossier
mkdir -p docs/assets/qa/concept-recall

# Screenshots attendus
# 1. concept-recall-banner.png (banner affiché)
# 2. concept-recall-console.png (DevTools event)
# 3. concept-recall-ignore.png (après clic Ignorer)
```

#### 4. Validation finale
**Checklist succès** :
- [ ] Banner s'affiche en < 500ms
- [ ] Événement `ws:concept_recall` reçu avec payload correct
- [ ] Score similarité ≥ 0.5 affiché
- [ ] Auto-hide après 15s fonctionne
- [ ] Aucune détection dans même thread (by design)
- [ ] Aucune erreur console/backend

### En cas de problème

**❌ Banner ne s'affiche pas**
```bash
# 1. Vérifier env var
cat .env.local | grep CONCEPT_RECALL_EMIT_EVENTS
# Doit être "true"

# 2. Relancer backend
# Arrêter processus actuel (Ctrl+C)
pwsh -File scripts/run-backend.ps1
# Chercher log : "ConceptRecallTracker initialisé"

# 3. Vérifier connexion WS
# DevTools > Network > WS > Frames
# Doit voir messages ws:* actifs
```

**❌ Score toujours < 0.5**
- Messages trop différents sémantiquement
- Essayer phrases plus similaires (ex: "CI/CD", "pipeline", "automation")

**Support** : Consulter [README_CONCEPT_RECALL_TESTS.md](tests/backend/features/README_CONCEPT_RECALL_TESTS.md)

---

## 📦 Livrables Attendus

### 1. Validation QA (30-60 min)
- [ ] 3 screenshots archivés dans `docs/assets/qa/concept-recall/`
- [ ] Checklist succès complétée (5/5 critères)
- [ ] Aucune erreur backend/console reportée

### 2. Documentation passation
```bash
# Mettre à jour docs/passation.md avec :
## [2025-10-XX HH:MM] — Agent: Claude Code

### Fichiers modifiés
- docs/passation.md
- docs/assets/qa/concept-recall/*.png (ajouts)

### Actions réalisées
✅ QA manuelle concept recall validée
✅ 5/5 scénarios passent
✅ Banner s'affiche correctement
✅ Événements WebSocket fonctionnels
✅ Captures archivées

### Prochaines actions recommandées
1. Implémenter modal "Voir l'historique"
2. Métriques Prometheus (cf. concept-recall-monitoring.md)
```

---

## 🔄 Après QA : Prochaines Features

### Option A : Modal "Voir l'historique" (3-4h)

**Objectif** : Navigation vers threads passés mentionnant le concept

**Tâches** :
1. Backend endpoint `GET /api/memory/concept-history/{concept_id}`
2. Frontend component `ConceptHistoryModal.js`
3. Intégration bouton banner → modal
4. Tests unitaires + intégration

**Documentation** : Voir [NEXT_SESSION_CONCEPT_RECALL.md](NEXT_SESSION_CONCEPT_RECALL.md) section "Modal historique"

### Option B : Métriques Prometheus (4-5h)

**Objectif** : Monitoring détections, scores, performance

**Plan détaillé** : [docs/features/concept-recall-monitoring.md](docs/features/concept-recall-monitoring.md)

**Tâches** :
1. Créer `src/backend/features/memory/metrics.py`
2. Instrumenter ConceptRecallTracker
3. Endpoint `/api/metrics` (format Prometheus)
4. Dashboard Grafana (optionnel)

---

## 📚 Références Clés

### Documentation
- **Guide QA complet** : [docs/qa/concept-recall-manual-qa.md](docs/qa/concept-recall-manual-qa.md)
- **Instructions session** : [NEXT_SESSION_CONCEPT_RECALL.md](NEXT_SESSION_CONCEPT_RECALL.md)
- **Tests README** : [tests/backend/features/README_CONCEPT_RECALL_TESTS.md](tests/backend/features/README_CONCEPT_RECALL_TESTS.md)
- **Plan monitoring** : [docs/features/concept-recall-monitoring.md](docs/features/concept-recall-monitoring.md)
- **Passation** : [docs/passation.md](docs/passation.md) (entrée 2025-10-04 16:39)

### Code source
- [src/backend/features/memory/concept_recall.py](src/backend/features/memory/concept_recall.py)
- [src/backend/features/memory/gardener.py](src/backend/features/memory/gardener.py)

### Tests
```bash
# Relancer tests si modifications
pytest tests/backend/features/test_concept_recall_tracker.py -v
pytest tests/backend/features/test_memory_gardener_enrichment.py -v
# Objectif : 12/12 passent ✅
```

---

## ⚡ Commandes Rapides

```bash
# 1. État projet
git status
git log --oneline -5

# 2. Backend
pwsh -File scripts/run-backend.ps1
curl http://127.0.0.1:8000/api/health

# 3. Tests
pytest tests/backend/features/test_concept_recall_*.py -v

# 4. UI (si nécessaire)
npm run dev

# 5. Après QA - commit captures
git add docs/assets/qa/concept-recall/
git add docs/passation.md
git commit -m "qa: validate concept recall UI - all scenarios pass

- Banner displays correctly < 500ms
- WebSocket events ws:concept_recall received
- Auto-hide after 15s functional
- Screenshots archived

🤖 Generated with Claude Code"
git push origin main
```

---

## 🎯 Critère de Succès Session

✅ **Session réussie si** :
1. QA manuelle validée (5/5 scénarios)
2. 3 screenshots archivés
3. Documentation passation mise à jour
4. **OU** Feature suivante initiée (modal/métriques)

---

## 💡 Conseils

- **Priorité absolue** : QA manuelle (30-60 min max)
- **DevTools ouverts** : Console + Network > WS pour debug
- **Backend requis** : Toujours vérifier `ConceptRecallTracker initialisé` dans logs
- **Messages similaires** : Utiliser vocabulaire proche (CI/CD, pipeline, automation) pour score ≥ 0.5
- **Cross-thread only** : Aucune détection dans même thread (c'est normal, by design)

---

**Bonne QA !** 🚀

En cas de blocage, consulter [docs/qa/concept-recall-manual-qa.md](docs/qa/concept-recall-manual-qa.md) section "Problèmes connus et résolutions"
