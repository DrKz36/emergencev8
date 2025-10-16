# Dashboard API Documentation

## Overview

Le module Dashboard fournit une API complète pour visualiser les métriques, coûts et activité de l'application ÉMERGENCE. Il expose 7 endpoints REST pour alimenter le cockpit frontend avec des données temporelles et des statistiques agrégées.

## Architecture

### Module Structure

```
src/backend/features/dashboard/
├── router.py           # API endpoints (V3.2)
├── service.py          # DashboardService (résumés, coûts)
└── timeline_service.py # TimelineService (données temporelles)
```

### API Mounting

- **Base path:** `/api/dashboard` (configuré dans main.py)
- **Tags:** Dashboard, Timeline, Distribution, Costs
- **Authentication:** Requiert `user_id` via dependencies

## API Dashboard & Timeline (V3.2)

### Endpoints principaux

#### 1. Résumé Dashboard

```http
GET /api/dashboard/costs/summary
```

Récupère le résumé complet des données du cockpit (coûts, métriques, seuils d'alerte).

**Filtrage:**
- Header `X-Session-Id`: filtre par session spécifique
- Sans header: agrège toutes les sessions de l'utilisateur

**Response:**
```json
{
  "costs": {
    "total": 0.05,
    "by_agent": [...]
  },
  "metrics": {
    "messages": 45,
    "threads": 12,
    "tokens": 15000
  },
  "thresholds": {...}
}
```

#### 2. Résumé par session

```http
GET /api/dashboard/costs/summary/session/{session_id}
```

Résumé filtré strictement pour une session donnée.

**Path params:**
- `session_id`: ID de la session

**Response:** Même structure que `/costs/summary`

#### 3. Timeline d'activité

```http
GET /api/dashboard/timeline/activity?period=30d
```

Timeline d'activité (messages + threads) par jour.

**Query params:**
- `period`: 7d, 30d, 90d, 1y (défaut: 30d)

**Headers (optionnel):**
- `X-Session-Id`: filtre par session

**Response:**
```json
[
  {
    "date": "2025-10-05",
    "messages": 12,
    "threads": 3
  },
  {
    "date": "2025-10-06",
    "messages": 15,
    "threads": 4
  }
]
```

#### 4. Timeline des coûts

```http
GET /api/dashboard/timeline/costs?period=30d
```

Timeline des coûts par jour.

**Query params:**
- `period`: 7d, 30d, 90d, 1y (défaut: 30d)

**Response:**
```json
[
  {
    "date": "2025-10-05",
    "cost": 0.012
  },
  {
    "date": "2025-10-06",
    "cost": 0.018
  }
]
```

#### 5. Timeline des tokens

```http
GET /api/dashboard/timeline/tokens?period=30d
```

Timeline des tokens (input/output) par jour.

**Query params:**
- `period`: 7d, 30d, 90d, 1y (défaut: 30d)

**Response:**
```json
[
  {
    "date": "2025-10-05",
    "input": 5000,
    "output": 3000,
    "total": 8000
  }
]
```

#### 6. Distribution par agent

```http
GET /api/dashboard/distribution/{metric}?period=30d
```

Distribution par agent pour une métrique (messages, tokens, costs).

**Path params:**
- `metric`: "messages", "tokens", ou "costs"

**Query params:**
- `period`: 7d, 30d, 90d, 1y (défaut: 30d)

**Response:**
```json
{
  "Assistant": 150,
  "Orchestrator": 80,
  "Researcher": 45
}
```

#### 7. Coûts par agent

```http
GET /api/dashboard/costs/by-agent
```

Détail des coûts par agent avec modèle utilisé.

**Headers (optionnel):**
- `X-Session-Id`: filtre par session

**Response:**
```json
[
  {
    "agent": "Assistant",
    "costs": 0.025,
    "tokens": 10000,
    "model": "claude-3-5-sonnet"
  }
]
```

## Services

### TimelineService

Service dédié aux données temporelles pour les graphiques du cockpit.

**Initialisation:**
```python
from backend.core.database.manager import DatabaseManager
from backend.features.dashboard.timeline_service import TimelineService

timeline_service = TimelineService(db_manager)
```

**Isolation des données:**
- `user_id` est **OBLIGATOIRE** en production (isolation multi-utilisateurs)
- En mode dev, si `user_id=None`, agrège toutes les données
- Support filtrage additionnel par `session_id`

**Méthodes:**

##### get_activity_timeline()
```python
async def get_activity_timeline(
    period: str = "30d",
    *,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> List[Dict[str, Any]]
```

Retourne messages + threads par jour.

##### get_costs_timeline()
```python
async def get_costs_timeline(
    period: str = "30d",
    *,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> List[Dict[str, Any]]
```

Retourne coûts par jour.

##### get_tokens_timeline()
```python
async def get_tokens_timeline(
    period: str = "30d",
    *,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> List[Dict[str, Any]]
```

Retourne tokens input/output par jour.

##### get_distribution_by_agent()
```python
async def get_distribution_by_agent(
    metric: str = "messages",
    period: str = "30d",
    *,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> Dict[str, int]
```

Retourne répartition par agent pour une métrique.

**Périodes supportées:** 7d, 30d, 90d, 1y

**Gestion robuste des valeurs NULL (Phase 1.2):**

Toutes les méthodes du TimelineService utilisent maintenant le pattern COALESCE pour gérer les timestamps NULL de manière robuste :

```sql
DATE(COALESCE(timestamp, created_at, 'now'))
```

Ce pattern garantit que :
- Les enregistrements avec `timestamp = NULL` utilisent `created_at` comme fallback
- Si `created_at` est également NULL, la date actuelle est utilisée
- Aucun enregistrement n'est exclu des agrégations

**Impact:** Les graphiques timeline du Cockpit affichent maintenant des données même en présence de valeurs NULL.

**Logging standardisé:**

Toutes les opérations loguent maintenant avec le format standardisé :
```python
logger.info(f"[Timeline] Activity timeline returned {len(rows)} days for user_id={user_id}")
```

### DashboardService

Service principal pour les résumés et statistiques globales.

**Méthodes:**
- `get_dashboard_data()`: résumé complet (coûts, métriques, seuils)
- `get_costs_by_agent()`: détail des coûts par agent avec modèle

## Safe Resolver Pattern

Le router utilise un pattern de résolution sûr pour les dépendances afin d'éviter les erreurs au démarrage:

```python
def _resolve_get_dashboard_service() -> Callable[..., Awaitable[DashboardService]]:
    try:
        candidate = getattr(deps, "get_dashboard_service")
        if callable(candidate):
            return candidate
    except Exception:
        logger.debug("get_dashboard_service not available")

    async def _placeholder(*args, **kwargs) -> DashboardService:
        raise HTTPException(status_code=503, detail="Dashboard service unavailable.")

    return _placeholder
```

**Avantages:**
- Évite les erreurs au démarrage si les dépendances ne sont pas prêtes
- Retourne HTTP 503 si service non disponible au runtime
- Logs de debug pour faciliter le diagnostic

## Exemples d'utilisation

### Frontend - Récupérer timeline d'activité

```javascript
const response = await fetch('/api/dashboard/timeline/activity?period=7d', {
  headers: {
    'X-Session-Id': currentSessionId  // optionnel
  }
});
const timeline = await response.json();
// [{date: "2025-10-05", messages: 12, threads: 3}, ...]
```

### Frontend - Récupérer coûts par agent

```javascript
const response = await fetch('/api/dashboard/costs/by-agent', {
  headers: {
    'X-Session-Id': currentSessionId  // optionnel
  }
});
const costs = await response.json();
// [{agent: "Assistant", costs: 0.025, tokens: 10000, model: "claude-3-5-sonnet"}, ...]
```

### Backend - Utiliser TimelineService

```python
from backend.features.dashboard.timeline_service import TimelineService

# Obtenir timeline d'activité pour un utilisateur
timeline = await timeline_service.get_activity_timeline(
    period="30d",
    user_id="user123",
    session_id="session456"  # optionnel
)
```

## Configuration

### Dépendances requises

Le module dashboard requiert les dépendances suivantes configurées dans `backend/shared/dependencies.py`:

- `get_dashboard_service()`: fournit DashboardService
- `get_timeline_service()`: fournit TimelineService
- `get_user_id()`: extrait user_id de l'auth
- `get_user_id_optional()`: idem, mais optionnel (mode dev)

### Base de données

Le module utilise les tables suivantes:

- `messages`: messages utilisateur et assistant
- `threads`: sessions/conversations
- `costs`: métriques de coûts et tokens

**Schéma attendu:**
- `messages.user_id`, `messages.session_id`, `messages.created_at`
- `threads.user_id`, `threads.session_id`, `threads.created_at`
- `costs.user_id`, `costs.session_id`, `costs.timestamp`, `costs.total_cost`, `costs.input_tokens`, `costs.output_tokens`, `costs.agent`

## Admin Dashboard (V1.0)

Le module admin dashboard fournit des endpoints réservés aux administrateurs pour consulter les données globales.

### Endpoints Admin

#### 1. Dashboard global

```http
GET /api/admin/dashboard/global
```

**Authorization:** Rôle admin requis

Récupère les statistiques globales de la plateforme (tous utilisateurs).

**Response:**
```json
{
  "total_users": 42,
  "total_sessions": 156,
  "total_messages": 3420,
  "total_costs": 12.45,
  "active_sessions": 8,
  "costs_by_agent": [...],
  "recent_activity": [...]
}
```

#### 2. Détails utilisateur

```http
GET /api/admin/dashboard/user/{user_id}
```

**Authorization:** Rôle admin requis

Récupère les données détaillées d'un utilisateur spécifique.

**Path params:**
- `user_id`: ID hashé de l'utilisateur

**Response:**
```json
{
  "user_id": "hash...",
  "sessions": 12,
  "messages": 245,
  "total_cost": 2.34,
  "documents": 5,
  "threads": 18,
  "activity_timeline": [...]
}
```

#### 3. Liste des emails allowlist

```http
GET /api/admin/allowlist/emails
```

**Authorization:** Rôle admin requis

Récupère tous les emails de l'allowlist pour l'envoi d'invitations beta.

**Response:**
```json
{
  "emails": [
    "user1@example.com",
    "user2@example.com"
  ],
  "total": 2
}
```

#### 4. Envoi d'invitations beta

```http
POST /api/admin/beta-invitations/send
```

**Authorization:** Rôle admin requis

Envoie des emails d'invitation beta à une liste d'adresses.

**Request body:**
```json
{
  "emails": [
    "user1@example.com",
    "user2@example.com"
  ],
  "base_url": "https://emergence-app.ch"
}
```

**Response:**
```json
{
  "total": 2,
  "sent": 2,
  "failed": 0,
  "sent_to": [
    "user1@example.com",
    "user2@example.com"
  ],
  "failed_emails": []
}
```

#### 5. Breakdown détaillé des coûts

```http
GET /api/admin/costs/detailed
```

**Authorization:** Rôle admin requis
**Nouveau (Phase 1.5):** Retourne le breakdown détaillé des coûts par utilisateur et par feature/module.

**Response:**
```json
{
  "users": [
    {
      "user_id": "hash123",
      "email": "user@example.com",
      "total_cost": 2.45,
      "modules": [
        {
          "feature": "chat",
          "cost": 1.20,
          "first_request": "2025-10-10T10:00:00",
          "last_request": "2025-10-16T09:00:00"
        },
        {
          "feature": "memory",
          "cost": 0.85,
          "first_request": "2025-10-12T14:00:00",
          "last_request": "2025-10-15T16:00:00"
        }
      ]
    }
  ],
  "total_cost": 12.45
}
```

**Usage frontend:**
```javascript
const response = await fetch('/api/admin/costs/detailed', {
  headers: { 'Authorization': `Bearer ${adminToken}` }
});
const breakdown = await response.json();
// Affiche dans l'onglet "Detailed Costs"
```

### AdminDashboardService

Service dédié aux statistiques globales d'administration.

**Méthodes:**

##### get_global_dashboard_data()
```python
async def get_global_dashboard_data() -> Dict[str, Any]
```

Retourne les statistiques globales de la plateforme (tous utilisateurs agrégés).

##### get_user_detailed_data()
```python
async def get_user_detailed_data(user_id: str) -> Dict[str, Any]
```

Retourne les données détaillées d'un utilisateur spécifique.

##### get_detailed_costs_breakdown()
```python
async def get_detailed_costs_breakdown() -> Dict[str, Any]
```

**Nouveau (Phase 1.5):** Retourne un breakdown détaillé des coûts par utilisateur et par feature/module.

**Structure de réponse:**
```json
{
  "users": [
    {
      "user_id": "hash123",
      "email": "user@example.com",
      "total_cost": 2.45,
      "modules": [
        {
          "feature": "chat",
          "cost": 1.20,
          "first_request": "2025-10-10T10:00:00",
          "last_request": "2025-10-16T09:00:00"
        }
      ]
    }
  ],
  "total_cost": 12.45
}
```

**Gestion robuste des NULL:**
- Utilise `COALESCE` pour first_request et last_request
- LEFT JOIN pour assurer l'inclusion de tous les utilisateurs
- Fallback avec données vides en cas d'erreur

##### Corrections Phase 1.3-1.4

**`_get_users_breakdown()` (Phase 1.3):**
- Utilise maintenant LEFT JOIN au lieu de INNER JOIN
- Matching flexible : `s.user_id = a.email OR s.user_id = a.user_id`
- COALESCE pour email et role : `COALESCE(a.email, s.user_id)`, `COALESCE(a.role, 'member')`
- **Impact:** Tous les utilisateurs sont affichés dans l'onglet Admin "Users"

**`_get_date_metrics()` (Phase 1.4):**
- COALESCE pour NULL timestamps
- Nouveau champ `request_count` ajouté aux résultats
- Fallback robuste : retourne 7 jours de données vides en cas d'erreur
- **Impact:** Chart "Cost Evolution (7 days)" affiche maintenant des données

**`_get_user_cost_history()` (Phase 1.4):**
- COALESCE appliqué partout
- Gestion d'erreur robuste avec logging

### Sécurité Admin

Tous les endpoints admin sont protégés par:

1. **Vérification du rôle:**
```python
async def verify_admin_role(user_role: str = Depends(deps.get_user_role)):
    if user_role != "admin":
        raise HTTPException(status_code=403, detail="Access denied. Admin role required.")
    return True
```

2. **JWT valide requis** (via `get_auth_claims`)
3. **Audit logging** de toutes les actions admin

## Versioning

**Version actuelle:** V3.4

**Changements V3.4 (Octobre 2025 - Phase 1 Debug):**
- ✅ **Phase 1.2** : TimelineService - COALESCE pour NULL timestamps dans toutes les méthodes
- ✅ **Phase 1.3** : AdminService - LEFT JOIN avec matching flexible dans `_get_users_breakdown()`
- ✅ **Phase 1.4** : AdminService - Corrections `_get_date_metrics()` et `_get_user_cost_history()`
- ✅ **Phase 1.5** : AdminService - Nouvelle fonction `get_detailed_costs_breakdown()`
- ✅ **Phase 1.5** : AdminRouter - Nouvel endpoint `GET /admin/costs/detailed`
- ✅ Gestion robuste des erreurs avec fallbacks partout
- ✅ Logging standardisé avec préfixes `[Timeline]` et `[admin_dashboard]`
- ✅ Fixes critiques : Charts Cockpit et Admin Dashboard affichent maintenant des données

**Conventions établies (Phase 1.6):**
- Pattern COALESCE obligatoire pour les timestamps : `COALESCE(timestamp, created_at, 'now')`
- Préférence LEFT JOIN sur INNER JOIN pour éviter l'exclusion de données
- Format logging standardisé : `logger.info(f"[ServiceName] Action: details")`
- Gestion d'erreur avec try/except et fallbacks (jamais de crash)

**Documentation associée:**
- [AGENTS_COORDINATION.md](../../docs/AGENTS_COORDINATION.md) - Conventions de développement
- [INTER_AGENT_SYNC.md](../../docs/INTER_AGENT_SYNC.md) - Points de synchronisation
- [tests/PHASE1_VALIDATION_CHECKLIST.md](../../docs/tests/PHASE1_VALIDATION_CHECKLIST.md) - Tests de validation

**Changements V3.3 (Octobre 2025):**
- ✅ Ajout AdminDashboardService pour statistiques globales
- ✅ Endpoints admin `/admin/dashboard/global` et `/admin/dashboard/user/{user_id}`
- ✅ Endpoint `/admin/allowlist/emails` pour récupérer liste d'emails
- ✅ Endpoint `/admin/beta-invitations/send` pour invitations beta
- ✅ Fix dépendances avec `Depends(deps.get_auth_service)`
- ✅ Sécurisation avec vérification de rôle admin

**Changements V3.2:**
- Suppression du préfixe dans le router (évite double `/api/dashboard`)
- Ajout du Safe Resolver Pattern
- Support filtrage par header `X-Session-Id`
- TimelineService avec isolation multi-utilisateurs

## Références

- Code source: [src/backend/features/dashboard/](../../src/backend/features/dashboard/)
- Router: [router.py](../../src/backend/features/dashboard/router.py)
- Admin Router: [admin_router.py](../../src/backend/features/dashboard/admin_router.py)
- Timeline Service: [timeline_service.py](../../src/backend/features/dashboard/timeline_service.py)
- Admin Service: [admin_service.py](../../src/backend/features/dashboard/admin_service.py)
- API principale: [main.py](../../src/backend/main.py)
- Documentation Auth: [auth.md](./auth.md)
- Documentation Beta: [beta_report.md](./beta_report.md)
