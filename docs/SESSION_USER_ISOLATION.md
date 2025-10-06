# Isolation des Données par Utilisateur et Session

## Vue d'ensemble

Ce document décrit l'implémentation complète du système d'isolation des données par utilisateur et par session dans Emergence V8.

## Objectif

Séparer complètement les statistiques et les données du cockpit entre les différents utilisateurs, tout en offrant aux administrateurs une vue globale complète.

## Architecture

### Backend

#### 1. Services de Dashboard

**`DashboardService`** (`src/backend/features/dashboard/service.py`)
- Service pour les utilisateurs normaux
- Filtre automatiquement les données par `user_id`
- Retourne uniquement les données propres à l'utilisateur connecté
- Endpoint: `GET /api/dashboard/costs/summary`

**`AdminDashboardService`** (`src/backend/features/dashboard/admin_service.py`)
- Service exclusif aux administrateurs
- Accès aux données globales de tous les utilisateurs
- Fournit des statistiques agrégées et des breakdowns par utilisateur
- Endpoints:
  - `GET /api/admin/dashboard/global` - Vue globale du système
  - `GET /api/admin/dashboard/user/{user_id}` - Détails d'un utilisateur spécifique

#### 2. Contrôle d'Accès

**Dependencies** (`src/backend/shared/dependencies.py`)
- `get_user_role()` - Extrait le rôle de l'utilisateur du JWT
- `get_user_id()` - Extrait l'identifiant utilisateur du JWT
- `verify_admin_role()` - Vérifie que l'utilisateur a le rôle admin
- `get_admin_dashboard_service()` - Injection de dépendance pour le service admin

**Router Admin** (`src/backend/features/dashboard/admin_router.py`)
- Routes protégées par `verify_admin_role`
- Retourne 403 Forbidden si l'utilisateur n'est pas admin

#### 3. Isolation des Données

**CostTracker** (`src/backend/core/cost_tracker.py`)
- Supporte les paramètres `user_id` et `session_id`
- `record_cost()` enregistre les coûts avec l'ID utilisateur
- `get_spending_summary()` peut filtrer par utilisateur ou session

**SessionManager** (`src/backend/core/session_manager.py`)
- Associe chaque session à un `user_id`
- Méthodes `get_user_id_for_session()` pour récupérer l'utilisateur d'une session

### Frontend

#### 1. Cockpit Utilisateur

**CockpitMetrics** (`src/frontend/features/cockpit/cockpit-metrics.js`)
- Utilise l'API `/api/dashboard/costs/summary`
- Envoie automatiquement le JWT et le session_id dans les headers
- Affiche uniquement les données de l'utilisateur connecté
- Cache les données pour optimiser les performances

#### 2. Dashboard Admin

**AdminDashboard** (`src/frontend/features/admin/admin-dashboard.js`)
- Interface complète pour les administrateurs
- Trois vues principales:
  - **Vue Globale**: Statistiques agrégées de tout le système
  - **Utilisateurs**: Liste des utilisateurs avec leurs métriques
  - **Coûts Détaillés**: Répartition des coûts par utilisateur

**AdminModule** (`src/frontend/features/admin/admin.js`)
- Point d'entrée du module admin
- Vérifie le rôle admin avant l'affichage
- Navigation par onglets entre Dashboard et Gestion Utilisateurs

#### 3. Sécurité Frontend

- Vérification du rôle au niveau du state manager
- Affichage conditionnel des onglets admin
- Message "Accès Refusé" si non-admin tente d'accéder

## Flux de Données

### Utilisateur Normal

```
1. Utilisateur se connecte → JWT contient user_id + role:member
2. Frontend envoie requête à /api/dashboard/costs/summary avec JWT
3. Backend extrait user_id du JWT via get_user_id()
4. DashboardService filtre les données par user_id
5. Retourne uniquement les données de cet utilisateur
```

### Administrateur

```
1. Admin se connecte → JWT contient user_id + role:admin
2. Frontend charge le module Admin
3. Admin accède à /api/admin/dashboard/global
4. verify_admin_role() vérifie le rôle admin
5. AdminDashboardService retourne les données globales
6. Frontend affiche les statistiques de tous les utilisateurs
```

## Données Isolées

### Par Utilisateur
- Coûts totaux et historiques
- Sessions créées
- Documents uploadés
- Threads de conversation
- Statistiques d'utilisation

### Données Globales (Admin Only)
- Agrégation de tous les utilisateurs
- Breakdown par utilisateur
- Historique complet des coûts
- Métriques système complètes
- Évolution temporelle globale

## Sécurité

### Backend
1. **Authentication**: JWT requis sur tous les endpoints
2. **Authorization**: Vérification du rôle pour les endpoints admin
3. **Data Filtering**: Filtrage automatique par user_id pour les utilisateurs normaux
4. **Admin Check**: Double vérification (JWT role + claims validation)

### Frontend
1. **Role Verification**: Vérification du rôle avant affichage des interfaces
2. **Conditional Rendering**: Masquage des éléments selon les permissions
3. **Token Management**: Gestion sécurisée des tokens JWT
4. **Access Denial**: Messages clairs en cas d'accès non autorisé

## Base de Données

### Tables Concernées

**sessions**
- `user_id` - Identifiant de l'utilisateur propriétaire
- Toutes les requêtes filtrent par user_id

**cost_logs**
- `user_id` - Identifiant de l'utilisateur
- `session_id` - Identifiant de session
- Permet le filtrage à deux niveaux

**documents**
- `user_id` - Propriétaire du document
- Isolation complète entre utilisateurs

**threads**
- `user_id` - Créateur du thread
- `session_id` - Session associée

## Configuration

### Variables d'Environnement

```bash
# Pas de configuration supplémentaire requise
# Le système utilise les configurations JWT existantes
```

### Roles Utilisateur

```python
# Roles supportés
- "admin"   # Accès complet + dashboard global
- "member"  # Accès standard, données isolées
```

## Tests

### Scénarios à Tester

1. **Isolation Utilisateur**
   - User A ne voit que ses données
   - User B ne voit que ses données
   - Les coûts sont bien séparés

2. **Accès Admin**
   - Admin voit toutes les données
   - Admin peut accéder aux détails de chaque utilisateur
   - Les agrégations sont correctes

3. **Sécurité**
   - Non-admin ne peut pas accéder aux endpoints admin (403)
   - Requêtes sans JWT sont rejetées (401)
   - Tentative de voir les données d'un autre user est bloquée

4. **Performance**
   - Cache des requêtes dashboard
   - Pas de requêtes inutiles
   - Chargement rapide des dashboards

## Évolutions Futures

### Court Terme
- [ ] Ajouter le tracking des tokens par utilisateur
- [ ] Calculer les messages par période (aujourd'hui, semaine)
- [ ] Ajouter des graphiques d'évolution temporelle

### Moyen Terme
- [ ] Export des rapports par utilisateur
- [ ] Alertes de dépassement de quota par utilisateur
- [ ] Dashboard comparatif entre utilisateurs

### Long Terme
- [ ] Système de quotas personnalisés par utilisateur
- [ ] Facturation automatique basée sur l'utilisation
- [ ] Analytics prédictifs de consommation

## Notes Importantes

1. **Migration**: Aucune migration de données requise, le système est rétrocompatible
2. **Performance**: Les requêtes sont indexées sur `user_id` pour optimiser les performances
3. **Scalabilité**: Architecture prête pour des milliers d'utilisateurs
4. **Audit**: Tous les accès admin sont loggés automatiquement

## Support

Pour toute question ou problème:
- Backend: Vérifier les logs dans `src/backend/features/dashboard/`
- Frontend: Console du navigateur pour les erreurs d'API
- Auth: Vérifier le contenu du JWT et le rôle utilisateur

## Changelog

### V1.0 (2025-10-06)
- ✅ Implémentation complète de l'isolation par utilisateur
- ✅ Dashboard admin avec vue globale
- ✅ API sécurisées avec vérification de rôle
- ✅ Interface frontend complète
- ✅ Documentation technique
