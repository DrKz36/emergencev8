# Prompt pour Nouvelle Instance Claude Code - Correction Tests Mémoire Proactive

## 📋 Contexte

Tu travailles sur le projet **EmergenceV8**, un système multi-agents avec mémoire LTM/STM avancée.

**Situation actuelle** :
- ✅ Phase P2 Sprints 1+2+3 **COMPLÉTÉE** (backend + frontend hints proactifs)
- ❌ **PROBLÈME CRITIQUE** : 6/16 tests backend FAILED (méthodes async non awaited)
- ⚠️ Tests E2E non exécutés
- ❓ Endpoint `/api/memory/user/stats` non vérifié

**Documentation de référence** :
- [docs/STATUS_MEMOIRE_PROACTIVE.md](docs/STATUS_MEMOIRE_PROACTIVE.md) - Analyse complète
- [docs/memory-roadmap.md](docs/memory-roadmap.md) - Roadmap P0→P3
- [docs/Memoire.md](docs/Memoire.md) - Documentation système mémoire

---

## 🎯 Mission : Stabilisation Tests Mémoire Proactive

### Étape 1 : Fixer les tests async backend (PRIORITÉ 1)

**Fichier à corriger** : `tests/backend/features/test_proactive_hints.py`

**Problème** : 6 tests utilisent des méthodes async sans `await`, ce qui retourne des coroutines au lieu de valeurs.

**Tests à corriger** :

1. `test_track_mention_increments_counter` (ligne ~64)
2. `test_track_mention_separate_users` (ligne ~74)
3. `test_reset_counter` (ligne ~89)
4. `test_generate_hints_preference_match` (ligne ~114)
5. `test_generate_hints_resets_counter_after_hint` (ligne ~175)
6. `test_custom_recurrence_threshold` (ligne ~190)

**Pattern de correction** :

```python
# ❌ AVANT (INCORRECT)
def test_track_mention_increments_counter(self):
    tracker = ConceptTracker()
    count1 = tracker.track_mention("python", "user_123")  # Retourne coroutine
    assert count1 == 1  # FAIL: compare coroutine à int

# ✅ APRÈS (CORRECT)
async def test_track_mention_increments_counter(self):
    tracker = ConceptTracker()
    count1 = await tracker.track_mention("python", "user_123")  # Retourne int
    assert count1 == 1  # PASS
```

**Actions requises** :
1. Lire le fichier `tests/backend/features/test_proactive_hints.py`
2. Identifier les 6 méthodes de test concernées
3. Ajouter `async` devant `def test_...`
4. Ajouter `await` devant chaque appel à `track_mention()`, `reset_counter()`, etc.
5. Vérifier que les tests passent : `pytest tests/backend/features/test_proactive_hints.py -v`

**Critère de succès** : 16/16 tests PASS

---

### Étape 2 : Vérifier endpoint `/api/memory/user/stats`

**Objectif** : S'assurer que l'endpoint documenté en P2 Sprint 3 est bien implémenté et fonctionnel.

**Fichier backend probable** : `src/backend/features/memory/router.py`

**Actions requises** :

1. **Chercher l'endpoint** :
   ```bash
   grep -r "user/stats" src/backend/features/memory/
   # OU
   grep -r "GET.*user.*stats" src/backend/features/memory/
   ```

2. **Si trouvé** : Tester avec curl
   ```bash
   # Utiliser le token d'auth du fichier test_token_final.py
   TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
   SESSION_ID="a24eefc9-10f1-453f-9fff-6d1b75d94e8e"

   curl -X GET "http://localhost:8000/api/memory/user/stats" \
     -H "Authorization: Bearer $TOKEN" \
     -H "X-Session-Id: $SESSION_ID" \
     -H "Content-Type: application/json"
   ```

3. **Réponse attendue** :
   ```json
   {
     "preferences": [...],  // Top 10 préférences
     "concepts": [...],     // Top 10 concepts
     "stats": {
       "total_sessions": 5,
       "total_preferences": 12,
       "ltm_size": 45
     }
   }
   ```

4. **Si NON trouvé** : Vérifier s'il doit être créé (voir docs/validation/P2_SPRINT3_STATUS.md si existe)

**Critère de succès** : Endpoint répond 200 OK avec données cohérentes

---

### Étape 3 : Exécuter tests E2E Frontend

**Fichier de test** : `tests/e2e/proactive-hints.spec.js`

**Prérequis** :
- Backend running sur `localhost:8000`
- Playwright installé
- Utilisateur authentifié (utiliser le token de test_token_final.py)

**Actions requises** :

1. **Vérifier Playwright installé** :
   ```bash
   npx playwright --version
   # Si absent : npm install -D @playwright/test && npx playwright install
   ```

2. **Lancer le backend** (dans un terminal séparé) :
   ```bash
   python -m uvicorn src.backend.main:app --reload --port 8000
   ```

3. **Exécuter les tests E2E** :
   ```bash
   npx playwright test tests/e2e/proactive-hints.spec.js --headed
   ```

4. **Tests attendus** (10 tests selon docs) :
   - ✅ Display hint banner
   - ✅ Dismiss hint
   - ✅ Snooze hint (1h localStorage)
   - ✅ Apply hint to chat input
   - ✅ Max 3 hints simultaneous
   - ✅ Auto-dismiss after 10s
   - ✅ Dashboard render
   - ✅ Loading/error states
   - ✅ Preference hints display
   - ✅ Intent hints display

**En cas d'échec** :
- Vérifier que le backend émet bien `ws:proactive_hint`
- Vérifier que ProactiveHintsUI est initialisé dans main.js
- Consulter les logs backend et browser console

**Critère de succès** : 10/10 tests E2E PASS

---

## 📝 Commandes Utiles

### Tests Backend
```bash
# Tous les tests proactive hints
pytest tests/backend/features/test_proactive_hints.py -v

# Test spécifique avec détails
pytest tests/backend/features/test_proactive_hints.py::TestConceptTracker::test_track_mention_increments_counter -vv

# Avec coverage
pytest tests/backend/features/test_proactive_hints.py --cov=src/backend/features/memory/proactive_hints --cov-report=term-missing
```

### Backend
```bash
# Lancer backend
python -m uvicorn src.backend.main:app --reload --port 8000

# Health check
curl http://localhost:8000/api/health

# Vérifier que ProactiveHintEngine est chargé
curl http://localhost:8000/api/health | grep -i "status.*ok"
```

### Frontend E2E
```bash
# Installer Playwright (si nécessaire)
npm install -D @playwright/test
npx playwright install

# Exécuter tests
npx playwright test tests/e2e/proactive-hints.spec.js

# Mode debug (UI interactive)
npx playwright test tests/e2e/proactive-hints.spec.js --debug

# Générer rapport HTML
npx playwright test tests/e2e/proactive-hints.spec.js --reporter=html
```

---

## 🔍 Fichiers Clés à Connaître

### Backend
- `src/backend/features/memory/proactive_hints.py` - Engine hints proactifs
- `src/backend/features/memory/router.py` - Endpoints mémoire REST
- `src/backend/features/chat/service.py` - Intégration ChatService
- `tests/backend/features/test_proactive_hints.py` - **Tests à corriger**

### Frontend
- `src/frontend/features/memory/ProactiveHintsUI.js` - Component hints
- `src/frontend/features/memory/MemoryDashboard.js` - Dashboard stats
- `src/frontend/main.js` - Initialisation globale (ligne 1412-1416)
- `tests/e2e/proactive-hints.spec.js` - Tests E2E

### Documentation
- `docs/STATUS_MEMOIRE_PROACTIVE.md` - **Analyse complète (LIRE EN PREMIER)**
- `docs/memory-roadmap.md` - Roadmap P0→P3
- `docs/Memoire.md` - Système mémoire complet
- `docs/validation/P2_COMPLETION_FINAL_STATUS.md` - Status P2

---

## ✅ Checklist de Succès

### Étape 1 : Tests Async (30-45 min)
- [ ] Fichier `test_proactive_hints.py` lu et compris
- [ ] 6 tests identifiés (track_mention, reset_counter, generate_hints)
- [ ] Ajout `async` + `await` sur méthodes async
- [ ] **16/16 tests PASS** ✅
- [ ] Commit : `fix: correct async/await in proactive hints tests`

### Étape 2 : Endpoint User Stats (15-30 min)
- [ ] Recherche endpoint `/api/memory/user/stats` effectuée
- [ ] Si trouvé : Test curl réussi (200 OK)
- [ ] Si absent : Vérifié dans docs P2 Sprint 3 si nécessaire
- [ ] **Endpoint fonctionnel** ✅

### Étape 3 : Tests E2E (1-2h)
- [ ] Playwright installé et configuré
- [ ] Backend running sur localhost:8000
- [ ] Tests E2E exécutés
- [ ] **10/10 tests E2E PASS** ✅
- [ ] Screenshots/vidéos générés si échec

---

## 📊 Rapport Final Attendu

À la fin, créer un fichier `docs/MEMORY_PROACTIVE_FIXED.md` avec :

```markdown
# Tests Mémoire Proactive - Corrections et Validation

**Date**: 2025-10-11
**Status**: ✅ TOUS TESTS PASS

## Étape 1 : Corrections Tests Async

- ✅ 6 tests corrigés dans test_proactive_hints.py
- ✅ Résultat : 16/16 tests PASS (100%)
- ✅ Commit : [hash]

### Détails corrections :
[Liste des tests corrigés avec ligne et changement]

## Étape 2 : Endpoint User Stats

- ✅ Endpoint /api/memory/user/stats : [TROUVÉ/CRÉÉ]
- ✅ Test curl : 200 OK
- ✅ Réponse : [snippet JSON]

## Étape 3 : Tests E2E Frontend

- ✅ Playwright : installé
- ✅ Tests exécutés : 10/10 PASS
- ✅ Rapport : [lien rapport HTML]

### Captures d'écran :
[Si tests visuels]

## Conclusion

✅ **Système mémoire proactive VALIDÉ et PRÊT PRODUCTION**

- Backend : 16/16 tests PASS
- Endpoint : Fonctionnel
- Frontend : 10/10 tests E2E PASS
- Performance : -71% latence maintenue
- Hints proactifs : Opérationnels

**Prochaine étape** : Déploiement production ou phase P3 (gouvernance)
```

---

## 🚨 Rappels Importants

1. **Ne PAS modifier** le code de ProactiveHintEngine ou ChatService (déjà fonctionnels)
2. **Seulement corriger** les tests et vérifier endpoints
3. **Limiter les modifications** aux 3 tâches ci-dessus
4. **Documenter** chaque étape pour traçabilité
5. **Commiter** après chaque étape réussie

---

## 🔗 Liens Rapides

- Token d'auth : Voir `test_token_final.py` (ligne 12)
- Session ID : `a24eefc9-10f1-453f-9fff-6d1b75d94e8e`
- Backend port : `8000`
- Tests backend : `pytest tests/backend/features/test_proactive_hints.py -v`
- Tests E2E : `npx playwright test tests/e2e/proactive-hints.spec.js`

---

**BON COURAGE ! 🚀**

Ce prompt te donne toutes les informations pour compléter les 3 étapes.
Si tu rencontres un blocage, consulte `docs/STATUS_MEMOIRE_PROACTIVE.md` pour plus de détails.
