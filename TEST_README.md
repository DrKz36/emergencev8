# Guide d'Exécution des Tests - Phases 1 & 3

## Vue d'ensemble

Ce document décrit comment exécuter les tests automatisés pour valider les modifications des Phases 1 et 3.

**Phases testées :**
- **Phase 1** : Correctifs backend critiques (5 tests)
- **Phase 3** : Améliorations UI/UX (11 tests)

**Total** : 16 tests automatisés

---

## Prérequis

### Pour Phase 1 (Tests Backend)

- **Python 3.11+**
- **Serveur backend actif** sur `http://localhost:8000`
- **Bibliothèque requests** : `pip install requests`

### Pour Phase 3 (Tests Frontend)

- **Python 3.11+**
- **Build frontend effectué** : `npm run build`
- Aucune autre dépendance (tests statiques)

---

## Exécution Rapide

### Tester tout (Phase 1 + Phase 3)

```bash
# 1. Lancer le serveur backend (terminal 1)
uvicorn src.backend.main:app --reload --port 8000

# 2. Build frontend (terminal 2)
npm run build

# 3. Exécuter tests backend (terminal 2)
python test_phase1_validation.py

# 4. Exécuter tests frontend (terminal 2)
python test_phase3_validation.py
```

### Tester seulement Phase 3 (Frontend)

```bash
# Build d'abord
npm run build

# Puis exécuter les tests
python test_phase3_validation.py
```

**Avantage** : Aucun serveur backend requis, tests rapides (~5 secondes)

---

## Tests Phase 1 - Backend

### Script : `test_phase1_validation.py`

**Tests effectués :**

1. **Timeline Activity** (`/api/dashboard/timeline/activity`)
   - Vérifie structure de réponse
   - Valide champs `date`, `messages`, `threads`
   - Gère cas liste vide

2. **Timeline Tokens** (`/api/dashboard/timeline/tokens`)
   - Vérifie structure de réponse
   - Valide champs `date`, `input`, `output`, `total`
   - Vérifie calcul total = input + output

3. **Timeline Costs** (`/api/dashboard/timeline/costs`)
   - Vérifie structure de réponse
   - Valide champs `date`, `cost`

4. **Admin Global Dashboard** (`/api/admin/dashboard/global`)
   - Vérifie présence `users_breakdown`
   - Valide structure utilisateur
   - Vérifie `date_metrics` (7 jours)

5. **Admin Detailed Costs** (`/api/admin/costs/detailed`)
   - Vérifie structure top-level
   - Valide structure utilisateur
   - Valide structure modules

### Commande

```bash
python test_phase1_validation.py
```

### Configuration

Les identifiants de test peuvent être modifiés dans le script :

```python
TEST_USER_EMAIL = "test@example.com"
ADMIN_USER_EMAIL = "admin@example.com"
BASE_URL = "http://localhost:8000"
```

### Output Attendu

```
================================================================================
                     PHASE 1 BACKEND VALIDATION TESTS
================================================================================

✓ Server is healthy

================================================================================
                    PHASE 1.2 - TIMELINE SERVICE ENDPOINTS
================================================================================

Test: Timeline Activity Endpoint
✓ Status: 200
✓ Data points: X
...

================================================================================
                              TEST SUMMARY
================================================================================

Total Tests: 5
✓ Passed: 5

Status: ✓ ALL TESTS PASSED ✓
```

---

## Tests Phase 3 - Frontend

### Script : `test_phase3_validation.py`

**Tests effectués :**

#### TASK 3.1 - BUTTON SYSTEM

1. **Button System File Exists**
   - Vérifie `src/frontend/styles/components/button-system.css` existe

2. **Button Variants Defined**
   - Vérifie 6 variantes : `primary`, `secondary`, `metal`, `ghost`, `danger`, `success`

3. **Button Sizes Defined**
   - Vérifie 3 tailles : `sm`, `md`, `lg`

4. **Button States Defined**
   - Vérifie états : `active`, `disabled`, `loading`

5. **Button System Imported**
   - Vérifie import dans `main-styles.css`

#### TASK 3.2 - MEMORY BUTTONS MIGRATION

6. **Memory Buttons Migrated**
   - Vérifie CSS a commentaire de migration
   - Vérifie JS utilise classes `.btn .btn--secondary`
   - Vérifie présence boutons History et Graph

#### TASK 3.3 - GRAPH BUTTONS MIGRATION

7. **Graph Buttons Migrated**
   - Vérifie CSS a commentaire de migration
   - Vérifie JS utilise classes `.btn .btn--ghost`
   - Vérifie présence boutons reset-view et reload

#### TASK 3.4 - STICKY HEADER

8. **Sticky Header Implemented**
   - Vérifie 4 propriétés CSS : `position:sticky`, `top:0`, `z-index:100`, `backdrop-filter:blur`

9. **Responsive Adjustments**
   - Vérifie media queries pour `.references__header`

#### INTEGRATION CHECKS

10. **Design Tokens Available**
    - Vérifie existence `design-tokens.css` et `design-system.css`
    - Compte utilisation variables CSS (28 attendues)

11. **Build Artifacts Valid**
    - Vérifie fichiers CSS dans `dist/assets/`
    - Vérifie présence classes boutons dans build minifié

### Commande

```bash
python test_phase3_validation.py
```

### Output Attendu

```
================================================================================
                         PHASE 3 UI/UX VALIDATION TESTS
================================================================================

✓ Project structure validated

================================================================================
                            TASK 3.1 - BUTTON SYSTEM
================================================================================

Test: Button System CSS File Existence
✓ File exists: src\frontend\styles\components\button-system.css
  File size: 8640 characters

Test: Button Variants Definition
✓ All 6 button variants defined
    .btn--primary
    .btn--secondary
    ...

================================================================================
                                  TEST SUMMARY
================================================================================

Total Tests: 11
✓ Passed: 11

Status: ✓ ALL TESTS PASSED ✓
```

---

## Résolution de Problèmes

### Phase 1 - Erreur "Cannot connect to server"

**Cause** : Le serveur backend n'est pas lancé ou n'est pas sur le port 8000.

**Solution** :
```bash
# Terminal 1 : Lancer le backend
uvicorn src.backend.main:app --reload --port 8000

# Vérifier dans le navigateur
http://localhost:8000/health
```

### Phase 1 - Erreur "Module requests not found"

**Cause** : La bibliothèque `requests` n'est pas installée.

**Solution** :
```bash
pip install requests
```

### Phase 3 - Erreur "Not in project root directory"

**Cause** : Le script doit être exécuté depuis la racine du projet.

**Solution** :
```bash
# Naviguer vers la racine
cd c:\dev\emergenceV8

# Puis exécuter
python test_phase3_validation.py
```

### Phase 3 - Warning "No CSS files found in dist/assets"

**Cause** : Le build frontend n'a pas été effectué.

**Solution** :
```bash
npm run build
```

---

## Tests Manuels Complémentaires

Après que tous les tests automatisés passent, vérifier visuellement :

### Phase 1 (Backend)

1. **Module Cockpit** :
   - [ ] Timeline d'Activité affiche des données
   - [ ] Utilisation des Tokens affiche des graphiques
   - [ ] Tendances des Coûts affiche une courbe

2. **Module Admin** :
   - [ ] Évolution des Coûts (7 derniers jours) affiche un graphique
   - [ ] Onglet Utilisateurs liste les utilisateurs
   - [ ] Onglet Coûts Détaillés affiche la répartition par module

### Phase 3 (UI/UX)

1. **Module Memory** :
   - [ ] Boutons "Historique" et "Graphe" ont un style unifié
   - [ ] Hover et état actif fonctionnent correctement

2. **Graphe de Connaissances** :
   - [ ] Boutons "🔄 Vue" et "↻ Recharger" ont un style unifié
   - [ ] Hover fonctionne correctement

3. **Module À propos** :
   - [ ] Header reste fixe lors du scroll
   - [ ] Effet glassmorphique visible
   - [ ] Responsive fonctionne sur mobile

---

## Rapport de Bugs

Si un test échoue, suivre cette procédure :

1. **Noter le test qui échoue** (nom + message d'erreur)
2. **Capturer l'output complet** du script de test
3. **Vérifier les logs** du serveur backend (si Phase 1)
4. **Consulter** [docs/PHASE_1_3_COMPLETION_REPORT.md](docs/PHASE_1_3_COMPLETION_REPORT.md) pour détails techniques
5. **Créer un rapport** avec :
   - Nom du test
   - Message d'erreur
   - Logs backend/frontend
   - Étapes pour reproduire

---

## Statistiques Attendues

| Phase | Tests | Succès Attendu | Durée Moyenne |
|-------|-------|----------------|---------------|
| Phase 1 | 5 | 5/5 (100%) | ~10-15s |
| Phase 3 | 11 | 11/11 (100%) | ~5-10s |
| **Total** | **16** | **16/16 (100%)** | **~20s** |

---

## Références

- **Rapport Complet** : [docs/PHASE_1_3_COMPLETION_REPORT.md](docs/PHASE_1_3_COMPLETION_REPORT.md)
- **Plan Debug** : [PLAN_DEBUG_COMPLET.md](PLAN_DEBUG_COMPLET.md)
- **Status Phase 1** : [docs/DEBUG_PHASE1_STATUS.md](docs/DEBUG_PHASE1_STATUS.md)
- **Agent Sync** : [AGENT_SYNC.md](AGENT_SYNC.md)
- **Passation** : [docs/passation.md](docs/passation.md)

---

**Dernière mise à jour** : 2025-10-16
**Version** : 1.0
**Statut** : ✅ Tous les tests passent
