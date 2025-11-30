# Synchronisation automatique inter-agents (Option A)

## Vue d'ensemble

Le système de synchronisation automatique permet aux différents agents (Claude Code, Codex local, Codex cloud) de collaborer efficacement sans se marcher sur les pieds. Il détecte automatiquement les changements dans les fichiers critiques et déclenche des consolidations intelligentes.

## Architecture

### Composants

1. **AutoSyncService** (`src/backend/features/sync/auto_sync_service.py`)
   - Service principal de synchronisation
   - Détection automatique des changements
   - Déclenchement intelligent des consolidations
   - Métriques Prometheus intégrées

2. **API REST** (`src/backend/features/sync/router.py`)
   - `GET /api/sync/status` - Statut du service
   - `POST /api/sync/consolidate` - Consolidation manuelle
   - `GET /api/sync/pending-changes` - Liste des changements en attente
   - `GET /api/sync/checksums` - Checksums des fichiers surveillés

3. **Dashboard Web** (`src/frontend/modules/sync/sync_dashboard.js`)
   - Visualisation temps réel du statut
   - Affichage des changements en attente
   - Bouton de consolidation manuelle
   - Auto-refresh toutes les 10 secondes

## Fonctionnalités

### 1. Détection automatique des changements

Le service surveille en permanence les fichiers critiques :

- `SYNC_STATUS.md` - Vue d'ensemble synchronisation
- `AGENT_SYNC_CLAUDE.md` / `AGENT_SYNC_CODEX.md` / `AGENT_SYNC_GEMINI.md` - suivis agents
- `docs/passation_claude.md` / `docs/passation_codex.md` - journaux 48h
- `AGENTS.md` - Configuration agents
- `CODEV_PROTOCOL.md` - Protocole de collaboration
- `docs/architecture/*.md` - Documentation architecture
- `ROADMAP.md` - Roadmap du projet

**Mécanisme :**
- Calcul de checksums MD5 pour chaque fichier
- Vérification périodique (défaut: toutes les 30s)
- Détection des événements : `created`, `modified`, `deleted`
- Stockage des événements en attente

**Métriques :**
```python
sync_changes_detected_total  # Nombre de changements détectés
sync_status                  # Statut par fichier (1=synced, 0=out_of_sync, -1=error)
sync_check_duration_seconds  # Durée des vérifications
```

### 2. Consolidation intelligente

Deux types de déclencheurs :

#### a) Trigger par seuil
- Déclenche automatiquement quand N changements sont détectés
- Seuil par défaut : 5 changements
- Configurable via paramètre `consolidation_threshold`

#### b) Trigger temporel
- Déclenche après un intervalle de temps
- Intervalle par défaut : 60 minutes
- Configurable via paramètre `consolidation_interval_minutes`

**Métriques :**
```python
sync_consolidations_triggered_total  # Nombre de consolidations (par type)
sync_consolidation_duration_seconds  # Durée des consolidations
```

### 3. Rapport de consolidation

Chaque consolidation génère un rapport automatique ajouté à `SYNC_STATUS.md` :

```markdown
## 🤖 Synchronisation automatique

### Consolidation - 2025-10-10T14:30:00

**Type de déclenchement** : `threshold`
**Conditions** : {"pending_changes": 5, "threshold": 5}
**Changements consolidés** : 5 événements sur 3 fichiers

**Fichiers modifiés** :
- **AGENT_SYNC_CLAUDE.md** : 2 événement(s)
  - `modified` à 2025-10-10T14:25:00 (agent: claude-code)
  - `modified` à 2025-10-10T14:28:00 (agent: codex-local)
- **docs/passation_claude.md** : 1 événement
- **docs/passation_codex.md** : 2 événement(s)
  - `modified` à 2025-10-10T14:20:00 (agent: codex-cloud)
  - `modified` à 2025-10-10T14:26:00 (agent: claude-code)
  - `modified` à 2025-10-10T14:29:00 (agent: codex-local)

---
```

## Configuration

### Paramètres du service

```python
AutoSyncService(
    repo_root=Path("/chemin/vers/repo"),
    check_interval_seconds=30,        # Intervalle de vérification
    consolidation_threshold=5,        # Seuil de changements
    consolidation_interval_minutes=60 # Intervalle temporel
)
```

### Variables d'environnement

```bash
# Aucune variable requise - configuration par défaut fonctionnelle
# Optionnel : désactiver le service
AUTOSYNC_ENABLED=0
```

## Utilisation

### 1. Démarrage automatique

Le service démarre automatiquement avec l'application :

```python
# src/backend/main.py
@app.on_event("startup")
async def _on_startup():
    from backend.features.sync.auto_sync_service import get_auto_sync_service
    sync_service = get_auto_sync_service()
    await sync_service.start()
```

### 2. API REST

#### Récupérer le statut

```bash
curl -H "x-dev-bypass: 1" http://localhost:8000/api/sync/status
```

Réponse :
```json
{
  "running": true,
  "pending_changes": 3,
  "last_consolidation": "2025-10-10T14:30:00",
  "watched_files": 8,
  "checksums_tracked": 8,
  "consolidation_threshold": 5,
  "check_interval_seconds": 30
}
```

#### Déclencher consolidation manuelle

```bash
curl -X POST -H "x-dev-bypass: 1" http://localhost:8000/api/sync/consolidate
```

Réponse :
```json
{
  "status": "success",
  "trigger": {
    "trigger_type": "manual",
    "conditions_met": {"pending_changes": 3},
    "timestamp": "2025-10-10T14:35:00"
  },
  "changes_consolidated": 3
}
```

#### Lister les changements en attente

```bash
curl -H "x-dev-bypass: 1" http://localhost:8000/api/sync/pending-changes
```

Réponse :
```json
{
  "count": 3,
  "changes": [
    {
      "file_path": "AGENT_SYNC.md",
      "event_type": "modified",
      "timestamp": "2025-10-10T14:32:00",
      "old_checksum": "a1b2c3d4...",
      "new_checksum": "e5f6g7h8...",
      "agent_owner": "claude-code"
    }
  ]
}
```

### 3. Dashboard Web

Accès : http://localhost:8000/sync-dashboard.html

Fonctionnalités :
- Statut global temps réel
- Liste des changements en attente
- Checksums des fichiers surveillés
- Bouton de consolidation manuelle
- Auto-refresh toutes les 10 secondes

### 4. Callbacks programmatiques

```python
from backend.features.sync.auto_sync_service import get_auto_sync_service

sync_service = get_auto_sync_service()

def on_consolidation(trigger: ConsolidationTrigger):
    print(f"Consolidation {trigger.trigger_type}: {trigger.conditions_met}")

sync_service.register_consolidation_callback(on_consolidation)
```

## Métriques Prometheus

Le service expose 5 métriques :

```prometheus
# Changements détectés (par type de fichier et agent)
sync_changes_detected_total{file_type="sync",agent="claude-code"} 12

# Consolidations déclenchées (par type)
sync_consolidations_triggered_total{trigger_type="threshold"} 5
sync_consolidations_triggered_total{trigger_type="time_based"} 2
sync_consolidations_triggered_total{trigger_type="manual"} 3

# Statut par fichier (1=synced, 0=out_of_sync, -1=error)
sync_status{file_path="AGENT_SYNC.md"} 1

# Durée des vérifications (histogram)
sync_check_duration_seconds_bucket{le="0.01"} 142
sync_check_duration_seconds_bucket{le="0.1"} 158

# Durée des consolidations (histogram)
sync_consolidation_duration_seconds_bucket{le="1.0"} 8
sync_consolidation_duration_seconds_bucket{le="5.0"} 10
```

### Queries PromQL

```promql
# Taux de changements détectés (par minute)
rate(sync_changes_detected_total[5m]) * 60

# Temps moyen de consolidation
rate(sync_consolidation_duration_seconds_sum[5m]) / rate(sync_consolidations_triggered_total[5m])

# Fichiers hors sync
sync_status != 1

# Consolidations par type (dernière heure)
increase(sync_consolidations_triggered_total[1h])
```

## Tests

### Tests unitaires

```bash
pytest tests/backend/features/test_auto_sync.py -v
```

Tests couverts :
- ✅ Lifecycle (start/stop)
- ✅ Initialisation checksums
- ✅ Détection modifications
- ✅ Détection créations
- ✅ Détection suppressions
- ✅ Trigger seuil
- ✅ Consolidation manuelle
- ✅ Récupération statut
- ✅ Génération rapport
- ✅ Détection type fichier

### Tests d'intégration

Pour tester en conditions réelles :

1. Démarrer le backend : `uvicorn main:app --reload`
2. Modifier `AGENT_SYNC.md` plusieurs fois
3. Vérifier dans le dashboard : http://localhost:8000/sync-dashboard.html
4. Déclencher consolidation manuelle
5. Vérifier le rapport ajouté à `AGENT_SYNC.md`

## Troubleshooting

### Le service ne démarre pas

```bash
# Vérifier les logs
docker logs emergence-app | grep AutoSyncService

# Output attendu :
# AutoSyncService started successfully
```

### Les changements ne sont pas détectés

1. Vérifier que le fichier est dans la liste surveillée
2. Vérifier l'intervalle de check (défaut 30s)
3. Consulter les métriques : `curl http://localhost:8000/api/metrics | grep sync_changes`

### Les consolidations ne se déclenchent pas

1. Vérifier le seuil : `GET /api/sync/status` → `consolidation_threshold`
2. Vérifier le nombre de changements : `GET /api/sync/pending-changes` → `count`
3. Attendre l'intervalle de consolidation (60 min par défaut) OU déclencher manuellement

### Erreurs lors des consolidations

```bash
# Vérifier les permissions d'écriture sur AGENT_SYNC.md
ls -la AGENT_SYNC.md

# Vérifier les logs d'erreur
docker logs emergence-app | grep "Error in consolidation"
```

## Roadmap

### Phase actuelle (P1) ✅
- [x] Détection automatique fichiers
- [x] Trigger par seuil
- [x] Trigger temporel
- [x] Consolidation manuelle
- [x] Rapport AGENT_SYNC.md
- [x] Dashboard Web
- [x] Métriques Prometheus

### Phase P2 (à venir)
- [ ] Détection agent propriétaire (via git blame)
- [ ] Webhooks de notification
- [ ] Historique des consolidations
- [ ] Configuration dynamique (sans redémarrage)
- [ ] Résolution automatique de conflits simples

### Phase P3 (futur)
- [ ] Intégration Git (auto-commit/push)
- [ ] Notifications Slack/Discord
- [ ] Dashboard analytics avancés
- [ ] Machine learning pour prédiction des conflits

## Références

- [SYNC_STATUS.md](../../SYNC_STATUS.md) - Vue d'ensemble synchronisation
- [AGENT_SYNC_CLAUDE.md](../../AGENT_SYNC_CLAUDE.md) / [AGENT_SYNC_CODEX.md](../../AGENT_SYNC_CODEX.md) / [AGENT_SYNC_GEMINI.md](../../AGENT_SYNC_GEMINI.md) - Suivi agents
- [CODEV_PROTOCOL.md](../../CODEV_PROTOCOL.md) - Protocole multi-agents
- [Architecture mémoire](../architecture/10-Memoire.md) - Architecture système
- [Métriques Prometheus](../monitoring/prometheus-p1-metrics.md) - Guide métriques
