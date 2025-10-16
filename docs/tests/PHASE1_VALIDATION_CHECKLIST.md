# Phase 1 Backend Fixes - Validation Checklist

**Date:** 2025-10-16
**Version:** Beta 1.1.0
**Phase:** 1 - Backend Critical Fixes

---

## Objectif

Valider que toutes les corrections de la Phase 1 fonctionnent correctement et que les graphiques/données vides sont maintenant remplis.

---

## Phase 1.2 - Timeline Service Endpoints

### Endpoint: `/api/dashboard/timeline/activity`

**Test 1: Activité avec données**
```bash
curl -X GET "http://localhost:8000/api/dashboard/timeline/activity?period=30d" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "X-User-Id: test@example.com"
```

**Résultat attendu:**
- Status 200
- JSON avec tableau `activity` contenant 30 jours de données
- Chaque entrée a: `date`, `messages`, `threads`
- Aucune donnée ne devrait être manquante due à NULL timestamps

**Validation:**
- [ ] L'endpoint retourne des données (pas de tableau vide)
- [ ] Les dates couvrent les 30 derniers jours
- [ ] Les compteurs messages/threads sont cohérents

---

### Endpoint: `/api/dashboard/timeline/tokens`

**Test 2: Timeline tokens**
```bash
curl -X GET "http://localhost:8000/api/dashboard/timeline/tokens?period=30d" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "X-User-Id: test@example.com"
```

**Résultat attendu:**
- Status 200
- Tableau avec `date`, `input`, `output`, `total` pour chaque jour

**Validation:**
- [ ] L'endpoint retourne des données
- [ ] Les valeurs de tokens sont numériques et >= 0
- [ ] `total` = `input` + `output`

---

### Endpoint: `/api/dashboard/timeline/costs`

**Test 3: Timeline coûts**
```bash
curl -X GET "http://localhost:8000/api/dashboard/timeline/costs?period=30d" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "X-User-Id: test@example.com"
```

**Résultat attendu:**
- Status 200
- Tableau avec `date`, `cost` pour chaque jour

**Validation:**
- [ ] L'endpoint retourne des données
- [ ] Les coûts sont numériques et >= 0
- [ ] Aucun jour manquant dans la période

---

## Phase 1.3 - Admin Users Breakdown

### Endpoint: `/api/admin/dashboard/global`

**Test 4: Dashboard global admin**
```bash
curl -X GET "http://localhost:8000/api/admin/dashboard/global" \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -H "X-User-Role: admin"
```

**Résultat attendu:**
- Status 200
- Section `users_breakdown` avec au moins 1 utilisateur
- Chaque utilisateur a: `user_id`, `email`, `role`, `total_cost`

**Validation:**
- [ ] Pas de message "Aucun utilisateur trouvé"
- [ ] Tous les utilisateurs ayant des sessions sont listés
- [ ] Les utilisateurs sans email dans auth_allowlist sont inclus avec fallback

---

## Phase 1.4 - Admin Date Metrics

### Endpoint: `/api/admin/dashboard/global` (date_metrics)

**Test 5: Évolution des coûts 7 jours**
```bash
curl -X GET "http://localhost:8000/api/admin/dashboard/global" \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -H "X-User-Role: admin"
```

**Résultat attendu:**
- Section `date_metrics` avec `last_7_days`
- Tableau de 7 entrées avec `date`, `cost`, `request_count`

**Validation:**
- [ ] Les 7 derniers jours sont présents
- [ ] Chaque jour a une date, un coût et un compteur de requêtes
- [ ] Les coûts incluent les enregistrements avec NULL timestamps

---

## Phase 1.5 - Detailed Costs Endpoint

### Endpoint: `/api/admin/costs/detailed`

**Test 6: Breakdown détaillé des coûts**
```bash
curl -X GET "http://localhost:8000/api/admin/costs/detailed" \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -H "X-User-Role: admin"
```

**Résultat attendu:**
```json
{
  "users": [
    {
      "user_id": "test@example.com",
      "total_cost": 0.18,
      "total_requests": 45,
      "modules": [
        {
          "module": "chat",
          "cost": 0.12,
          "input_tokens": 1500,
          "output_tokens": 800,
          "request_count": 30,
          "first_request": "2025-10-10T10:00:00",
          "last_request": "2025-10-16T15:30:00"
        }
      ]
    }
  ],
  "total_users": 1,
  "grand_total_cost": 0.18,
  "total_requests": 45
}
```

**Validation:**
- [ ] L'endpoint retourne des utilisateurs
- [ ] Chaque utilisateur a une liste de modules
- [ ] Les modules sont triés par coût décroissant
- [ ] Les timestamps utilisent COALESCE (pas de NULL)
- [ ] `grand_total_cost` = somme des `total_cost` des utilisateurs

---

## Phase 1.6 - Tests Fonctionnels

### Test Frontend: Cockpit Module

**Test 7: Graphique Timeline d'Activité**
1. Se connecter à l'application
2. Naviguer vers le module Cockpit
3. Observer le graphique "Timeline d'Activité"

**Validation:**
- [ ] Le graphique affiche des données (pas vide)
- [ ] Les 30 derniers jours sont visibles
- [ ] Les barres de messages et threads sont présentes

---

**Test 8: Graphique Utilisation des Tokens**
1. Dans le Cockpit, observer le graphique "Utilisation des Tokens"

**Validation:**
- [ ] Le graphique affiche des données
- [ ] Les courbes Input/Output/Total sont visibles
- [ ] Les valeurs sont cohérentes

---

**Test 9: Graphique Tendances des Coûts**
1. Dans le Cockpit, observer le graphique "Tendances des Coûts"

**Validation:**
- [ ] Le graphique affiche des données
- [ ] La ligne de coûts quotidiens est visible
- [ ] Total période et Moyenne/jour affichent des valeurs non-nulles

---

### Test Frontend: Admin Module

**Test 10: Onglet Utilisateurs**
1. Se connecter avec un compte admin
2. Naviguer vers le module Admin
3. Cliquer sur l'onglet "Utilisateurs"

**Validation:**
- [ ] La liste des utilisateurs s'affiche (pas "Aucun utilisateur trouvé")
- [ ] Chaque utilisateur a un email, rôle, coût total
- [ ] Les utilisateurs peuvent être triés et filtrés

---

**Test 11: Graphique Évolution des Coûts (7 jours)**
1. Dans Admin, observer le graphique "Évolution des Coûts"

**Validation:**
- [ ] Le graphique affiche 7 jours de données
- [ ] Chaque jour a une barre de coût
- [ ] Aucun jour manquant

---

**Test 12: Onglet Coûts Détaillés**
1. Dans Admin, cliquer sur l'onglet "Coûts Détaillés"

**Validation:**
- [ ] La liste des utilisateurs avec breakdown par module s'affiche
- [ ] Chaque utilisateur peut être étendu pour voir ses modules
- [ ] Les coûts par module sont listés et sommés correctement

---

## Résumé des Validations

| Phase | Tests | Passés | Échecs | Statut |
|-------|-------|--------|--------|--------|
| 1.2 - Timeline Endpoints | 3 | - | - | ⏳ |
| 1.3 - Admin Users | 1 | - | - | ⏳ |
| 1.4 - Admin Metrics | 1 | - | - | ⏳ |
| 1.5 - Detailed Costs | 1 | - | - | ⏳ |
| 1.6 - Frontend Tests | 6 | - | - | ⏳ |
| **TOTAL** | **12** | **-** | **-** | **⏳** |

---

## Problèmes Identifiés Pendant les Tests

_À compléter lors de l'exécution des tests_

### Problème 1
- **Endpoint/Fonctionnalité:**
- **Symptôme:**
- **Cause:**
- **Solution:**

---

## Notes de Validation

### Points Positifs
- Gestion NULL timestamps implémentée partout
- Logging amélioré pour debugging
- Fallbacks robustes en cas d'erreur

### Points à Surveiller
- Performance des requêtes avec COALESCE
- Impact des LEFT JOIN sur les gros datasets
- Logs trop verbeux en production (à ajuster si nécessaire)

---

## Prochaines Étapes Après Validation

1. ✅ Tous les tests passent → Commit Phase 1
2. ❌ Certains tests échouent → Debug et correction
3. ✅ Phase 1 validée → Démarrer Phase 2 (Frontend fixes)

---

**Validé par:** ___________
**Date:** ___________
**Signature:** ___________
