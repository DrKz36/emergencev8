# Guide d'Utilisation - Prompts Étapes Suivantes

## 📋 Vue d'Ensemble

Ce dossier contient les prompts prêts à l'emploi pour continuer le travail sur la **mémoire proactive** d'EmergenceV8 dans une nouvelle instance Claude Code.

**Contexte actuel** :
- ✅ Phase P2 Sprints 1+2+3 **IMPLÉMENTÉE** (code backend + frontend)
- ❌ Tests backend défaillants (6/16 FAILED)
- ⚠️ Validation production non effectuée

**Objectif** : Stabiliser et valider pour production

---

## 🗂️ Fichiers Disponibles

### 1. Documentation d'Analyse

| Fichier | Description | Usage |
|---------|-------------|-------|
| `STATUS_MEMOIRE_PROACTIVE.md` | Analyse complète de l'état actuel | 📖 Lire en premier |
| `AUTHENTICATION.md` | Documentation système auth JWT | 📚 Référence auth |

### 2. Prompts pour Nouvelles Instances

| Fichier | Option | Prérequis | Durée |
|---------|--------|-----------|-------|
| `PROMPT_NEXT_STEPS_MEMORY.md` | **Option 1** | Aucun | 3-5h |
| `PROMPT_OPTION2_MEMORY_VALIDATION.md` | **Option 2** | Option 1 complétée | 2-3h |

---

## 🚀 Mode d'Emploi

### Étape 1 : Lire l'Analyse

**Avant de commencer**, lire `STATUS_MEMOIRE_PROACTIVE.md` pour comprendre :
- ✅ Ce qui est déjà fait
- ❌ Les problèmes identifiés
- 🎯 Les actions prioritaires

**Temps** : 10-15 minutes de lecture

---

### Étape 2 : Copier-Coller le Prompt Option 1

1. **Ouvrir une nouvelle instance Claude Code**
   - Ouvrir le dossier : `C:\dev\emergenceV8`
   - S'assurer d'avoir une fenêtre de contexte vide

2. **Copier le contenu de `PROMPT_NEXT_STEPS_MEMORY.md`**
   ```bash
   # Ouvrir le fichier
   code docs/PROMPT_NEXT_STEPS_MEMORY.md

   # Copier TOUT le contenu (Ctrl+A puis Ctrl+C)
   ```

3. **Coller dans Claude Code**
   - Coller le prompt complet
   - Claude comprendra immédiatement le contexte et les 3 tâches

4. **Suivre les instructions de Claude**
   - Claude va fixer les 6 tests async
   - Vérifier l'endpoint `/api/memory/user/stats`
   - Exécuter les tests E2E Playwright

**Résultat attendu** :
- ✅ 16/16 tests backend PASS
- ✅ Endpoint user/stats fonctionnel
- ✅ 10/10 tests E2E PASS
- ✅ Document `MEMORY_PROACTIVE_FIXED.md` créé

**Durée totale** : 3-5 heures

---

### Étape 3 : Copier-Coller le Prompt Option 2 (Après Option 1)

**⚠️ IMPORTANT** : Attendre que l'Option 1 soit **100% complétée** avant de lancer l'Option 2.

1. **Vérifier que l'Option 1 est complète** :
   ```bash
   # Tous les tests passent ?
   pytest tests/backend/features/test_proactive_hints.py -v
   # Résultat attendu : 16/16 PASS

   # Tests E2E passent ?
   npx playwright test tests/e2e/proactive-hints.spec.js
   # Résultat attendu : 10/10 PASS
   ```

2. **Ouvrir une nouvelle instance Claude Code** (recommandé)
   - Permet de démarrer avec contexte frais
   - Évite dépassement fenêtre contexte

3. **Copier le contenu de `PROMPT_OPTION2_MEMORY_VALIDATION.md`**
   ```bash
   code docs/PROMPT_OPTION2_MEMORY_VALIDATION.md
   # Copier tout (Ctrl+A puis Ctrl+C)
   ```

4. **Coller dans Claude Code**
   - Claude va effectuer validation end-to-end
   - Tests manuels du flux complet
   - Vérification performance et métriques
   - Création documentation production

**Résultat attendu** :
- ✅ Validation manuelle flux complet
- ✅ Performance vérifiée (< 50ms latence)
- ✅ Documentation production créée
- ✅ Document `MEMORY_PROACTIVE_PRODUCTION_READY.md` finalisé

**Durée totale** : 2-3 heures

---

## 📊 Progression Globale

```
┌─────────────────────────────────────────────────────────────┐
│                    MÉMOIRE PROACTIVE                        │
│                  Progression Globale                         │
└─────────────────────────────────────────────────────────────┘

Phase P0 (Fondations)          ████████████████████ 100% ✅
Phase P1 (Enrichissement)      ████████████████████ 100% ✅
Phase P2 Sprint 1 (Perf)       ████████████████████ 100% ✅
Phase P2 Sprint 2 (Hints)      ████████████████████ 100% ✅
Phase P2 Sprint 3 (UI)         ████████████████████ 100% ✅

┌─────────────────────────────────────────────────────────────┐
│                  ÉTAPES RESTANTES                           │
└─────────────────────────────────────────────────────────────┘

Option 1 (Stabilisation)       ░░░░░░░░░░░░░░░░░░░░   0% ⏳
  ├─ Fix tests async           ░░░░░░░░░░░░░░░░░░░░   0%
  ├─ Verify endpoint           ░░░░░░░░░░░░░░░░░░░░   0%
  └─ Run E2E tests             ░░░░░░░░░░░░░░░░░░░░   0%

Option 2 (Validation Prod)     ░░░░░░░░░░░░░░░░░░░░   0% 🔒
  ├─ Test manuel complet       ░░░░░░░░░░░░░░░░░░░░   0%
  ├─ Vérif performance         ░░░░░░░░░░░░░░░░░░░░   0%
  └─ Documentation prod        ░░░░░░░░░░░░░░░░░░░░   0%

Production Deployment          ░░░░░░░░░░░░░░░░░░░░   0% 🔒
```

**Temps total restant** : 5-8 heures
**État actuel** : Option 1 prête à démarrer

---

## 🎯 Ordre d'Exécution Recommandé

### Scénario A : Tout d'une traite (Rapide)

**Si vous avez 6-8h de disponibilité** :

1. ✅ Lire `STATUS_MEMOIRE_PROACTIVE.md` (15 min)
2. ✅ Exécuter Option 1 (3-5h)
3. ☕ **Pause** (30 min)
4. ✅ Exécuter Option 2 (2-3h)
5. 🎉 **Production Ready !**

**Avantage** : Contexte frais en mémoire
**Temps total** : 6-9h (avec pauses)

---

### Scénario B : En plusieurs sessions (Recommandé)

**Si vous avez des contraintes de temps** :

#### Session 1 (3-5h)
1. ✅ Lire `STATUS_MEMOIRE_PROACTIVE.md`
2. ✅ Exécuter Option 1 complète
3. ✅ Commit & push
4. 📝 Noter où vous en êtes

#### Pause (1 jour ou plus)

#### Session 2 (2-3h)
1. ✅ Relire `MEMORY_PROACTIVE_FIXED.md` (résumé session 1)
2. ✅ Exécuter Option 2 complète
3. ✅ Commit & push avec tag
4. 🎉 **Production Ready !**

**Avantage** : Moins de fatigue, meilleure qualité
**Temps total** : 5-8h (réparties sur 2 sessions)

---

## 📝 Checklist Globale

### Avant de Commencer
- [ ] Backend installé et fonctionnel
- [ ] Tests peuvent s'exécuter (`pytest` installé)
- [ ] Playwright installé (pour E2E)
- [ ] Token d'auth disponible (voir `test_token_final.py`)
- [ ] Git propre (pas de changements non committés)

### Après Option 1
- [ ] ✅ 16/16 tests backend PASS
- [ ] ✅ Endpoint `/api/memory/user/stats` vérifié
- [ ] ✅ 10/10 tests E2E PASS
- [ ] ✅ Document `MEMORY_PROACTIVE_FIXED.md` créé
- [ ] ✅ Commit + push effectués

### Après Option 2
- [ ] ✅ Test manuel flux complet OK
- [ ] ✅ Performance vérifiée (< 50ms)
- [ ] ✅ Guide utilisateur créé
- [ ] ✅ Checklist déploiement créée
- [ ] ✅ Document `MEMORY_PROACTIVE_PRODUCTION_READY.md` créé
- [ ] ✅ Commit + push + tag effectués

### Production Deployment
- [ ] ✅ Review équipe
- [ ] ✅ Staging deployment
- [ ] ✅ Smoke tests staging
- [ ] ✅ Production deployment
- [ ] ✅ Monitoring 24h
- [ ] 🎉 **SUCCÈS !**

---

## 🆘 En Cas de Problème

### Problème : Tests backend ne passent pas après corrections

**Solution** :
1. Vérifier que toutes les méthodes async ont bien `async def` + `await`
2. Vérifier qu'il n'y a pas de typo dans les noms de méthodes
3. Exécuter un test à la fois pour isoler le problème :
   ```bash
   pytest tests/backend/features/test_proactive_hints.py::TestConceptTracker::test_track_mention_increments_counter -vv
   ```

### Problème : Tests E2E échouent

**Solutions** :
1. Vérifier que le backend tourne : `curl http://localhost:8000/api/health`
2. Vérifier que ProactiveHintsUI est initialisé :
   - Ouvrir console browser (F12)
   - Chercher : `[ProactiveHintsUI] Initialized globally`
3. Vérifier authentification :
   - Utiliser dev-auth.html pour se connecter
   - Vérifier token dans localStorage

### Problème : Endpoint `/api/memory/user/stats` introuvable

**Solutions** :
1. Chercher dans le code backend :
   ```bash
   grep -r "user/stats" src/backend/
   ```
2. Si absent, vérifier documentation P2 Sprint 3
3. Si vraiment manquant, créer selon spec (voir PROMPT_OPTION2)

### Problème : Fenêtre de contexte dépassée

**Solution** :
- ✅ **C'est normal !** C'est pour ça qu'on utilise de nouvelles instances
- Ouvrir une nouvelle instance Claude Code
- Copier-coller le prompt correspondant (Option 1 ou 2)
- Claude aura tout le contexte nécessaire dans le prompt

---

## 📚 Références Rapides

### Documentation Technique
- `docs/Memoire.md` - Système mémoire complet
- `docs/memory-roadmap.md` - Roadmap P0→P3
- `docs/MEMORY_CAPABILITIES.md` - Capacités mémoire

### Documentation Validation
- `docs/validation/P2_COMPLETION_FINAL_STATUS.md` - Status P2
- `docs/STATUS_MEMOIRE_PROACTIVE.md` - **Analyse actuelle**

### Code Backend
- `src/backend/features/memory/proactive_hints.py` - Engine hints
- `src/backend/features/chat/service.py` - Intégration chat
- `tests/backend/features/test_proactive_hints.py` - **Tests à fixer**

### Code Frontend
- `src/frontend/features/memory/ProactiveHintsUI.js` - Component hints
- `src/frontend/main.js` - Initialisation (ligne 1412)
- `tests/e2e/proactive-hints.spec.js` - Tests E2E

---

## ✅ Critères de Succès Final

Le projet sera **Production Ready** quand :

1. ✅ **Tests Backend** : 16/16 PASS
2. ✅ **Tests E2E** : 10/10 PASS
3. ✅ **Performance** : < 50ms latence LTM
4. ✅ **Validation Manuelle** : Flux complet testé
5. ✅ **Documentation** : Guide utilisateur + déploiement
6. ✅ **Métriques** : Prometheus opérationnel
7. ✅ **Aucune Erreur** : Logs propres backend + frontend

---

## 🎉 Après Production Ready

**Félicitations !** Vous aurez complété la Phase P2 Mémoire Proactive.

**Prochaines étapes possibles** :
- 🚀 Phase P3 : Gouvernance & Observabilité avancée
- 📊 Analytics : Collecte métriques usage hints
- 🔧 Optimisations : Fine-tuning seuils et paramètres
- 🌟 Features : Nouveaux types de hints (learning patterns, etc.)

---

**BON COURAGE ! 💪**

Ces prompts sont conçus pour vous guider pas à pas.
Si vous êtes bloqué, relisez `STATUS_MEMOIRE_PROACTIVE.md` pour le contexte complet.
