# Settings Feature - Dynamic Configuration

**Module**: `src/backend/features/settings/router.py`
**Version**: V1.0 (Émergence V8)
**Dernière mise à jour**: 2025-10-11

## Vue d'ensemble

Le module Settings permet de gérer la configuration dynamique de l'application ÉMERGENCE sans redémarrage. Les paramètres sont persistés dans un fichier JSON et peuvent être modifiés via API.

## Architecture

**Persistence**: Fichier JSON (`data/settings.json`)
**Hot-reload**: Modifications prises en compte immédiatement (pas de restart nécessaire)
**Scope**: Configuration globale (tous les utilisateurs/sessions)

---

## Configuration RAG

### GET `/api/settings/rag` - Récupérer Configuration RAG

Récupère les paramètres RAG actuels.

**Réponse** (200 OK):
```json
{
  "strict_mode": false,
  "score_threshold": 0.7
}
```

**Champs**:
- `strict_mode` (bool): Active le filtrage strict par seuil de score
  - `false` (défaut): Retourne tous les résultats, même faible score
  - `true`: Filtre résultats < `score_threshold`
- `score_threshold` (float): Seuil minimum de pertinence [0.0-1.0]
  - `0.7` (défaut): Filtrage modéré
  - `0.3-0.5`: Permissif (plus de résultats)
  - `0.8+`: Strict (haute précision)

### POST `/api/settings/rag` - Mettre à Jour Configuration RAG

Met à jour les paramètres RAG.

**Request Body** (JSON):
```json
{
  "strict_mode": true,
  "score_threshold": 0.8
}
```

**Validation**:
- `strict_mode`: Doit être boolean
- `score_threshold`: Doit être dans [0.0, 1.0]

**Réponse** (200 OK):
```json
{
  "status": "success",
  "message": "RAG settings updated successfully"
}
```

**Erreur** (400 Bad Request):
```json
{
  "detail": "score_threshold must be between 0.0 and 1.0"
}
```

**Exemple cURL**:
```bash
curl -X POST http://localhost:8000/api/settings/rag \
  -H "Content-Type: application/json" \
  -d '{
    "strict_mode": true,
    "score_threshold": 0.8
  }'
```

---

## Configuration Modèles LLM

### GET `/api/settings/models` - Récupérer Configuration Modèles

Récupère les paramètres LLM pour tous les agents.

**Réponse** (200 OK):
```json
{
  "nexus": {
    "model": "claude-3-5-sonnet-20241022",
    "temperature": 0.7,
    "max_tokens": 2000,
    "top_p": 0.9,
    "frequency_penalty": 0.0,
    "presence_penalty": 0.0
  },
  "neo": {
    "model": "gpt-4",
    "temperature": 0.5,
    "max_tokens": 1500,
    "top_p": 0.9,
    "frequency_penalty": 0.0,
    "presence_penalty": 0.0
  },
  "anima": {
    "model": "gpt-4",
    "temperature": 0.8,
    "max_tokens": 2500,
    "top_p": 0.9,
    "frequency_penalty": 0.0,
    "presence_penalty": 0.0
  }
}
```

**Paramètres par agent**:
- `model` (str): ID modèle (ex: `gpt-4`, `claude-3-5-sonnet-20241022`, `gemini-pro`)
- `temperature` (float): Créativité [0.0-1.0]
  - `0.0-0.3`: Déterministe, précis
  - `0.5-0.7`: Équilibré (défaut)
  - `0.8-1.0`: Créatif, varié
- `max_tokens` (int): Longueur maximum réponse [100-32000]
- `top_p` (float): Nucleus sampling [0.0-1.0] (défaut: 0.9)
- `frequency_penalty` (float): Pénalité répétition [-2.0 à 2.0] (défaut: 0.0)
- `presence_penalty` (float): Pénalité redondance [-2.0 à 2.0] (défaut: 0.0)

### POST `/api/settings/models` - Mettre à Jour Configuration Modèles

Met à jour les paramètres LLM pour un ou plusieurs agents.

**Request Body** (JSON):
```json
{
  "nexus": {
    "model": "claude-3-5-sonnet-20241022",
    "temperature": 0.8,
    "max_tokens": 3000,
    "top_p": 0.95,
    "frequency_penalty": 0.0,
    "presence_penalty": 0.0
  },
  "neo": {
    "model": "gpt-4-turbo",
    "temperature": 0.6,
    "max_tokens": 2000,
    "top_p": 0.9,
    "frequency_penalty": 0.1,
    "presence_penalty": 0.1
  }
}
```

**Validation**:
- `model`: Non vide
- `temperature`: [0.0, 1.0]
- `max_tokens`: [100, 32000]
- `top_p`: [0.0, 1.0]
- `frequency_penalty`: [-2.0, 2.0]
- `presence_penalty`: [-2.0, 2.0]

**Réponse** (200 OK):
```json
{
  "status": "success",
  "message": "Model settings updated for 2 agents"
}
```

**Exemple cURL**:
```bash
curl -X POST http://localhost:8000/api/settings/models \
  -H "Content-Type: application/json" \
  -d '{
    "nexus": {
      "model": "claude-3-5-sonnet-20241022",
      "temperature": 0.8,
      "max_tokens": 3000,
      "top_p": 0.95,
      "frequency_penalty": 0.0,
      "presence_penalty": 0.0
    }
  }'
```

---

## Configuration Globale

### GET `/api/settings/all` - Récupérer Toutes les Configurations

Récupère l'ensemble des settings (RAG + modèles + autres).

**Réponse** (200 OK):
```json
{
  "rag": {
    "strict_mode": false,
    "score_threshold": 0.7
  },
  "models": {
    "nexus": {...},
    "neo": {...},
    "anima": {...}
  }
}
```

**Usage**: Export configuration complète, backup, migration.

### DELETE `/api/settings/all` - Reset Toutes les Configurations

Supprime le fichier de settings et restaure les valeurs par défaut.

**Réponse** (200 OK):
```json
{
  "status": "success",
  "message": "All settings reset to defaults"
}
```

**⚠️ Attention**: Action irréversible. Les settings actuels sont perdus.

**Valeurs par défaut restaurées**:
- RAG: `strict_mode=false`, `score_threshold=0.7`
- Models: Configurations par défaut selon agents.yaml

**Exemple cURL**:
```bash
curl -X DELETE http://localhost:8000/api/settings/all
```

---

## Persistence et Stockage

### Format Fichier

**Path**: `data/settings.json`

**Structure**:
```json
{
  "rag": {
    "strict_mode": false,
    "score_threshold": 0.7
  },
  "models": {
    "nexus": {
      "model": "claude-3-5-sonnet-20241022",
      "temperature": 0.7,
      "max_tokens": 2000,
      "top_p": 0.9,
      "frequency_penalty": 0.0,
      "presence_penalty": 0.0
    },
    "neo": {...},
    "anima": {...}
  }
}
```

### Gestion Fichier

**Création automatique**: Le répertoire `data/` est créé automatiquement si absent.

**Initialisation**: Si `settings.json` n'existe pas, valeurs par défaut utilisées (pas de fichier créé jusqu'à première modification).

**Atomicité**: Écritures JSON complètes (pas d'écriture partielle).

---

## Intégration

### Avec ChatService

Les settings modèles sont appliqués lors de l'initialisation des requêtes LLM.

**Exemple ChatService**:
```python
# Charger settings modèle pour agent
settings = load_settings()
model_config = settings.get("models", {}).get(agent_id, {})

# Appliquer à la requête LLM
response = await llm_client.create_completion(
    model=model_config.get("model", "gpt-4"),
    temperature=model_config.get("temperature", 0.7),
    max_tokens=model_config.get("max_tokens", 2000),
    top_p=model_config.get("top_p", 0.9),
    frequency_penalty=model_config.get("frequency_penalty", 0.0),
    presence_penalty=model_config.get("presence_penalty", 0.0),
    messages=messages
)
```

### Avec HybridRetriever

Les settings RAG sont appliqués lors de la recherche hybride.

**Exemple HybridRetriever**:
```python
from backend.features.settings.router import load_settings

# Charger settings RAG
settings = load_settings()
rag_config = settings.get("rag", {})
strict_mode = rag_config.get("strict_mode", False)
score_threshold = rag_config.get("score_threshold", 0.7)

# Appliquer à la recherche
results = hybrid_query(
    vector_service=vector_service,
    collection=collection,
    query_text=query,
    n_results=5,
    score_threshold=score_threshold if strict_mode else 0.0,
    alpha=0.5
)
```

### Frontend (Cockpit)

**Fetch settings RAG**:
```typescript
async function getRAGSettings() {
  const response = await fetch('/api/settings/rag');
  return await response.json();
}

async function updateRAGSettings(strictMode: boolean, threshold: number) {
  const response = await fetch('/api/settings/rag', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      strict_mode: strictMode,
      score_threshold: threshold
    })
  });
  return await response.json();
}
```

**Fetch settings modèles**:
```typescript
async function getModelSettings() {
  const response = await fetch('/api/settings/models');
  return await response.json();
}

async function updateModelSettings(agentId: string, config: ModelConfig) {
  const response = await fetch('/api/settings/models', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      [agentId]: config
    })
  });
  return await response.json();
}
```

---

## Cas d'Usage

### 1. Activer Mode RAG Strict (Production)

**Problème**: Trop de résultats RAG peu pertinents polluent le contexte.

**Solution**:
```bash
curl -X POST http://localhost:8000/api/settings/rag \
  -H "Content-Type: application/json" \
  -d '{"strict_mode": true, "score_threshold": 0.75}'
```

**Résultat**: Seuls les résultats >0.75 sont injectés dans le contexte.

### 2. Tuning Température Agent (Créativité)

**Problème**: Nexus génère des réponses trop déterministes/ennuyeuses.

**Solution**:
```bash
curl -X POST http://localhost:8000/api/settings/models \
  -H "Content-Type: application/json" \
  -d '{
    "nexus": {
      "model": "claude-3-5-sonnet-20241022",
      "temperature": 0.9,
      "max_tokens": 2000,
      "top_p": 0.95,
      "frequency_penalty": 0.0,
      "presence_penalty": 0.0
    }
  }'
```

**Résultat**: Nexus génère des réponses plus variées et créatives.

### 3. Limiter Longueur Réponses (Coûts API)

**Problème**: Coûts API trop élevés (réponses longues).

**Solution**:
```bash
curl -X POST http://localhost:8000/api/settings/models \
  -H "Content-Type: application/json" \
  -d '{
    "neo": {"model": "gpt-4", "temperature": 0.7, "max_tokens": 1000, "top_p": 0.9, "frequency_penalty": 0.0, "presence_penalty": 0.0},
    "anima": {"model": "gpt-4", "temperature": 0.7, "max_tokens": 1000, "top_p": 0.9, "frequency_penalty": 0.0, "presence_penalty": 0.0}
  }'
```

**Résultat**: Réponses plus courtes, coûts réduits.

### 4. Backup et Restore Configuration

**Backup**:
```bash
curl http://localhost:8000/api/settings/all > settings_backup.json
```

**Restore**:
```bash
cp settings_backup.json data/settings.json
# Restart application (ou hot-reload si implémenté)
```

---

## Sécurité et Bonnes Pratiques

### Production

1. **Authentification**: Protéger les endpoints settings (admin uniquement)
   ```python
   @router.post("/rag", dependencies=[Depends(verify_admin)])
   async def update_rag_settings(settings: RAGSettings):
       ...
   ```

2. **Validation stricte**: Ne jamais accepter de valeurs hors limites
   ```python
   if not (0.0 <= settings.score_threshold <= 1.0):
       raise HTTPException(400, "Invalid threshold")
   ```

3. **Backup automatique**: Sauvegarder `settings.json` avant chaque modification
   ```python
   import shutil
   shutil.copy(SETTINGS_FILE, f"{SETTINGS_FILE}.backup")
   ```

4. **Logging**: Logger toutes les modifications de settings
   ```python
   logger.info(f"Settings updated by {user_id}: {settings.dict()}")
   ```

### Développement

1. **Version Control**: Ne **PAS** commit `data/settings.json` (ajouter à `.gitignore`)
   ```gitignore
   data/settings.json
   ```

2. **Settings par environnement**: Utiliser des fichiers séparés
   ```python
   SETTINGS_FILE = os.getenv("SETTINGS_FILE", "data/settings.json")
   # dev: data/settings.dev.json
   # prod: data/settings.prod.json
   ```

3. **Tests**: Utiliser un fichier temporaire pour tests
   ```python
   import tempfile
   SETTINGS_FILE = tempfile.mktemp(suffix=".json")
   ```

---

## Limitations Connues

1. **Pas de hot-reload automatique**: Certains composants nécessitent redémarrage pour prendre en compte nouveaux settings
2. **Pas d'historique**: Modifications écrasent anciennes valeurs (pas de rollback)
3. **Pas de validation croisée**: Seuils RAG et alpha HybridRetriever non coordonnés
4. **Pas d'authentification**: Endpoints publics (à sécuriser en production)

---

## Roadmap

- **V1.1**: Authentification admin (JWT + RBAC)
- **V1.2**: Historique modifications (audit trail)
- **V1.3**: Hot-reload automatique (signal tous les workers)
- **V1.4**: Validation croisée (cohérence RAG + HybridRetriever)
- **V2.0**: UI Cockpit pour gestion settings (formulaires, toggles)
- **V2.1**: Settings par utilisateur/tenant (multi-tenancy)

---

## Références

- [Chat](chat.md) - MemoryContextBuilder (utilise settings RAG)
- [Memory](memory.md) - HybridRetriever (filtrage par score_threshold)
- [Metrics](metrics.md) - Monitoring impact settings sur métriques
- [Monitoring](monitoring.md) - Health checks pour valider settings

---

## Changelog

### V1.0 - 2025-10-11
- Endpoints RAG settings (strict_mode, score_threshold)
- Endpoints model settings par agent
- Persistence JSON (`data/settings.json`)
- Validation Pydantic (limites paramètres)
- GET/POST/DELETE pour CRUD complet
