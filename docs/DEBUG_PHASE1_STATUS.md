# Phase 1 Debug - Backend Fixes Status

**Date de début:** 16 octobre 2025
**Agent:** Claude Code Assistant
**Objectif:** Corriger les problèmes critiques backend identifiés dans le plan de debug

---

## Référence

Document principal: [PLAN_DEBUG_COMPLET.md](../PLAN_DEBUG_COMPLET.md)

---

## Phase 1: Correctifs Backend Critiques

**Durée estimée:** 2 jours
**Statut:** 🟡 EN COURS

### Sous-Tâches

#### 1.1 - Helper NULL Timestamp dans queries.py
- **Statut:** ⏳ À FAIRE
- **Fichier:** `src/backend/core/database/queries.py`
- **Objectif:** Créer fonction `get_safe_date_column()` pour gérer les timestamps NULL
- **Tests:** Tests unitaires avec cas NULL

#### 1.2 - Fix Timeline Service Endpoints
- **Statut:** ⏳ À FAIRE
- **Fichiers:**
  - `src/backend/features/dashboard/timeline_service.py`
- **Endpoints à corriger:**
  - `/api/dashboard/timeline/activity`
  - `/api/dashboard/timeline/tokens`
  - `/api/dashboard/timeline/costs`
- **Dépendance:** 1.1

#### 1.3 - Fix Admin Users Breakdown
- **Statut:** ⏳ À FAIRE
- **Fichier:** `src/backend/features/dashboard/admin_service.py`
- **Objectif:** Remplacer INNER JOIN par LEFT JOIN pour récupérer tous les utilisateurs
- **Impact:** Fix "Aucun utilisateur trouvé"

#### 1.4 - Fix Admin Date Metrics
- **Statut:** ⏳ À FAIRE
- **Fichier:** `src/backend/features/dashboard/admin_service.py`
- **Objectif:** Gérer NULL timestamps dans `_get_date_metrics()`
- **Impact:** Fix graphique "Évolution des Coûts"
- **Dépendance:** 1.1

#### 1.5 - Endpoint Detailed Costs
- **Statut:** ⏳ À FAIRE
- **Fichiers:**
  - `src/backend/features/dashboard/admin_service.py`
  - `src/backend/features/dashboard/admin_router.py`
- **Objectif:** Créer endpoint `/api/admin/costs/detailed`
- **Impact:** Fix onglet "Coûts Détaillés"
- **Dépendance:** 1.3

#### 1.6 - Tests Phase 1
- **Statut:** ⏳ À FAIRE
- **Objectif:** Valider tous les correctifs backend
- **Tests:**
  - Tests unitaires NULL handling
  - Tests admin service
  - Tests timeline service
  - Tests d'intégration endpoints

---

## Problèmes Ciblés

### Cockpit Module
- ⚠️ Timeline d'Activité vide
- ⚠️ Utilisation des Tokens vide
- ⚠️ Tendances des Coûts vide

### Admin Module
- ⚠️ Évolution des Coûts 7 jours vide
- ⚠️ "Aucun utilisateur trouvé" dans onglet Utilisateurs
- ⚠️ Coûts Détaillés vide

---

## Causes Racines Adressées

### 1. Gestion NULL Timestamps
**Problème:** Les requêtes SQL avec `DATE(timestamp)` échouent silencieusement si `timestamp` est NULL.

**Solution:** Utiliser `COALESCE(timestamp, created_at, 'now')` partout.

**Implémentation:** Helper function `get_safe_date_column(table)` dans queries.py

### 2. Jointures Trop Restrictives
**Problème:** `INNER JOIN auth_allowlist` exclut les utilisateurs sans match exact.

**Solution:** Utiliser `LEFT JOIN` et gérer les NULL.

**Implémentation:** Modifier `_get_users_breakdown()` dans admin_service.py

### 3. Désynchronisation API Fields
**Problème:** Backend retourne `total`, `today`, `this_week` mais frontend attend `total_cost`, `today_cost`, etc.

**Solution:** Utiliser DTO pattern pour normaliser les réponses (déjà implémenté dans service.py, étendre à admin_service.py)

---

## Prochaines Étapes

1. ✅ Documentation et coordination mise à jour
2. ⏳ Implémenter 1.1 (Helper NULL timestamps)
3. ⏳ Implémenter 1.2 (Timeline endpoints)
4. ⏳ Implémenter 1.3 (Admin users)
5. ⏳ Implémenter 1.4 (Admin date metrics)
6. ⏳ Implémenter 1.5 (Detailed costs)
7. ⏳ Tests Phase 1
8. ⏳ Commit Phase 1
9. ⏳ Démarrer Phase 2 (Frontend fixes)

---

## Notes

- Les changements backend ne nécessitent pas de modifications frontend (sauf validation)
- Les tests doivent couvrir les cas NULL explicitement
- Les logs doivent être explicites sur les fallbacks utilisés

---

**Dernière mise à jour:** 2025-10-16 21:00
**Status:** 🟡 Phase 1 en préparation
