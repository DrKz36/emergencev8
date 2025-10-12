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

## Versioning

**Version actuelle:** V3.2

**Changements V3.2:**
- Suppression du préfixe dans le router (évite double `/api/dashboard`)
- Ajout du Safe Resolver Pattern
- Support filtrage par header `X-Session-Id`
- TimelineService avec isolation multi-utilisateurs

## Références

- Code source: [src/backend/features/dashboard/](../../src/backend/features/dashboard/)
- Router: [router.py](../../src/backend/features/dashboard/router.py)
- Timeline Service: [timeline_service.py](../../src/backend/features/dashboard/timeline_service.py)
- API principale: [main.py](../../src/backend/main.py)
