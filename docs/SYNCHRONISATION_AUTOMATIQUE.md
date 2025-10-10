# 🔄 Synchronisation Automatique Inter-Agents - Guide Complet

**Date de mise en service** : 2025-10-10
**Version** : Option A (Automatique complète)
**Statut** : ✅ Opérationnel en production

---

## 📋 Table des matières

1. [Vue d'ensemble](#vue-densemble)
2. [Fichiers surveillés](#fichiers-surveillés)
3. [Fonctionnement technique](#fonctionnement-technique)
4. [Workflow automatique](#workflow-automatique)
5. [Consolidations](#consolidations)
6. [Dashboard & Monitoring](#dashboard--monitoring)
7. [Pour les agents (Claude Code, Codex)](#pour-les-agents)
8. [Troubleshooting](#troubleshooting)

---

## Vue d'ensemble

### Objectif
Éviter que Claude Code, Codex (local) et Codex (cloud) se marchent sur les pieds en détectant automatiquement les changements dans la documentation critique et en déclenchant des consolidations intelligentes.

### Architecture
```
┌─────────────────────────────────────────────────────────┐
│                   AutoSyncService                        │
│                                                          │
│  ┌──────────────┐      ┌──────────────┐                │
│  │ File Watcher │      │ Consolidator │                │
│  │  (30s loop)  │ ───> │  (triggers)  │                │
│  └──────────────┘      └──────────────┘                │
│          │                     │                        │
│          ▼                     ▼                        │
│  ┌──────────────┐      ┌──────────────┐                │
│  │   Checksums  │      │   Reports    │                │
│  │   (MD5 hash) │      │ (AGENT_SYNC) │                │
│  └──────────────┘      └──────────────┘                │
└─────────────────────────────────────────────────────────┘
         │                      │
         ▼                      ▼
  ┌─────────────┐        ┌─────────────┐
  │ Prometheus  │        │  Dashboard  │
  │   Metrics   │        │     Web     │
  └─────────────┘        └─────────────┘
```

### Composants clés
- **AutoSyncService** : Service backend Python asyncio
- **API REST** : Endpoints `/api/sync/*`
- **Dashboard Web** : Interface temps réel
- **Métriques Prometheus** : Observabilité

---

## Fichiers surveillés

Le système surveille **8 fichiers critiques** :

### 1. **AGENT_SYNC.md** ⭐ (Type: sync)
- **Rôle** : État de synchronisation inter-agents
- **Mise à jour** : Automatique + manuelle par agents
- **Lecture** : OBLIGATOIRE avant toute session
- **Contenu** : État dépôt, zones de travail, commits récents

### 2. **docs/passation.md** ⭐ (Type: passation)
- **Rôle** : Journal de passation inter-agents
- **Mise à jour** : Manuelle par chaque agent en fin de session
- **Lecture** : 3 dernières entrées minimum
- **Contenu** : Historique complet des sessions

### 3. **AGENTS.md** (Type: docs)
- **Rôle** : Configuration et consignes agents
- **Mise à jour** : Manuelle quand protocole évolue
- **Lecture** : Début de session
- **Contenu** : Checklist, workflows, conventions

### 4. **CODEV_PROTOCOL.md** (Type: docs)
- **Rôle** : Protocole de collaboration multi-agents
- **Mise à jour** : Manuelle quand process change
- **Lecture** : Début de session
- **Contenu** : Règles de collaboration

### 5. **docs/architecture/00-Overview.md** (Type: architecture)
- **Rôle** : Vue d'ensemble architecture
- **Mise à jour** : Quand architecture évolue
- **Lecture** : Avant modifications majeures
- **Contenu** : Composants, diagrammes, patterns

### 6. **docs/architecture/30-Contracts.md** (Type: architecture)
- **Rôle** : Contrats API et interfaces
- **Mise à jour** : Quand API change
- **Lecture** : Avant modif endpoints
- **Contenu** : Spec OpenAPI, types, contrats

### 7. **docs/architecture/10-Memoire.md** (Type: architecture)
- **Rôle** : Architecture mémoire/RAG
- **Mise à jour** : Quand système mémoire évolue
- **Lecture** : Avant modif mémoire
- **Contenu** : Flux, composants, stratégies
- **⚠️ Statut** : À créer si absent

### 8. **ROADMAP.md** (Type: docs)
- **Rôle** : Roadmap du projet
- **Mise à jour** : Quand priorités changent
- **Lecture** : Début de session
- **Contenu** : Phases, objectifs, statuts
- **⚠️ Statut** : À créer si absent

---

## Fonctionnement technique

### 1. Détection des changements

**Mécanisme** :
- Calcul de checksum MD5 pour chaque fichier
- Comparaison avec checksum précédent
- Détection des événements : `created`, `modified`, `deleted`

**Fréquence** : Toutes les 30 secondes

**Algorithme** :
```python
# 1. Calculer nouveau checksum
new_checksum = md5(file_content)

# 2. Comparer avec checksum stocké
if new_checksum != stored_checksum:
    # Créer événement "modified"
    event = SyncEvent(
        file_path="AGENT_SYNC.md",
        event_type="modified",
        old_checksum=stored_checksum,
        new_checksum=new_checksum,
        timestamp=now()
    )
    pending_changes.append(event)
```

### 2. Triggers de consolidation

#### Trigger A : Seuil de changements
- **Seuil** : 5 changements
- **Logique** : `if len(pending_changes) >= 5 → consolidate()`
- **Use case** : Session intensive avec beaucoup de modifs

#### Trigger B : Intervalle temporel
- **Intervalle** : 60 minutes
- **Logique** : `if time_since_last >= 60min AND pending_changes > 0 → consolidate()`
- **Use case** : Session longue avec modifs espacées

#### Trigger C : Manuel
- **Action** : Bouton dashboard ou API POST
- **Logique** : Consolidation immédiate
- **Use case** : Fin de session, validation agent

### 3. Consolidation

**Processus** :
1. **Capture** : Sauvegarder le nombre de changements
2. **Rapport** : Générer rapport avec tous les événements
3. **Écriture** : Ajouter rapport à `AGENT_SYNC.md` (section `## 🤖 Synchronisation automatique`)
4. **Reset** : Vider `pending_changes`
5. **Métriques** : Incrémenter compteurs Prometheus
6. **Callbacks** : Appeler fonctions enregistrées

**Format du rapport** :
```markdown
### Consolidation - 2025-10-10T15:30:00

**Type de déclenchement** : `threshold`
**Conditions** : {"pending_changes": 5, "threshold": 5}
**Changements consolidés** : 5 événements sur 3 fichiers

**Fichiers modifiés** :
- **AGENT_SYNC.md** : 2 événement(s)
  - `modified` à 2025-10-10T15:25:00 (agent: claude-code)
  - `modified` à 2025-10-10T15:28:00 (agent: codex-local)
- **docs/passation.md** : 3 événement(s)
  - `modified` à 2025-10-10T15:20:00 (agent: codex-cloud)

---
```

---

## Workflow automatique

### Scénario typique

```
1. Agent modifie AGENT_SYNC.md
   ↓
2. AutoSyncService détecte le changement (30s max)
   ↓
3. Événement ajouté à pending_changes
   ↓
4. Si 5 changements OU 60 min écoulées
   ↓
5. Consolidation automatique déclenchée
   ↓
6. Rapport ajouté à AGENT_SYNC.md
   ↓
7. Métriques Prometheus mises à jour
   ↓
8. Dashboard affiche nouveau statut
```

### Timeline exemple

```
15:00 - Claude Code modifie AGENT_SYNC.md
15:00:30 - Détection : 1 changement en attente
15:02 - Claude Code modifie docs/passation.md
15:02:30 - Détection : 2 changements en attente
15:05 - Codex modifie AGENTS.md
15:05:30 - Détection : 3 changements en attente
15:08 - Claude Code modifie AGENT_SYNC.md (again)
15:08:30 - Détection : 4 changements en attente
15:10 - Codex modifie docs/architecture/00-Overview.md
15:10:30 - Détection : 5 changements (SEUIL ATTEINT)
15:11:00 - Consolidation automatique déclenchée
15:11:01 - Rapport ajouté à AGENT_SYNC.md
15:11:02 - pending_changes reset à 0
```

---

## Consolidations

### Types de consolidation

#### 1. Automatique par seuil
```json
{
  "trigger_type": "threshold",
  "conditions_met": {
    "pending_changes": 5,
    "threshold": 5
  }
}
```

#### 2. Automatique temporelle
```json
{
  "trigger_type": "time_based",
  "conditions_met": {
    "pending_changes": 3,
    "time_since_last_minutes": 60
  }
}
```

#### 3. Manuelle
```json
{
  "trigger_type": "manual",
  "conditions_met": {
    "pending_changes": 2
  }
}
```

### Rapport de consolidation

Le rapport est automatiquement ajouté à la section `## 🤖 Synchronisation automatique` de `AGENT_SYNC.md`.

**Informations incluses** :
- Timestamp ISO 8601
- Type de déclenchement
- Conditions remplies
- Nombre total de changements
- Liste des fichiers avec événements détaillés

**Historique** : Les rapports s'accumulent dans AGENT_SYNC.md (nettoyage manuel si nécessaire)

---

## Dashboard & Monitoring

### Dashboard Web

**URL** : http://localhost:8000/sync-dashboard.html

**Sections** :
1. **Statut global**
   - État service (✅ Actif / ❌ Arrêté)
   - Changements en attente
   - Fichiers surveillés
   - Dernière consolidation

2. **Changements en attente**
   - Liste des événements non consolidés
   - Type (modified, created, deleted)
   - Timestamp
   - Checksums (old → new)

3. **Fichiers surveillés**
   - Liste complète des 8 fichiers
   - Checksum actuel
   - Date dernière modification
   - Agent propriétaire (si détecté)

4. **Actions**
   - Bouton "Déclencher consolidation manuelle"
   - Bouton "Rafraîchir"

**Auto-refresh** : Toutes les 10 secondes

### API REST

#### GET /api/sync/status
```json
{
  "running": true,
  "pending_changes": 3,
  "last_consolidation": "2025-10-10T15:30:00",
  "watched_files": 8,
  "checksums_tracked": 6,
  "consolidation_threshold": 5,
  "check_interval_seconds": 30
}
```

#### GET /api/sync/pending-changes
```json
{
  "count": 2,
  "changes": [
    {
      "file_path": "AGENT_SYNC.md",
      "event_type": "modified",
      "timestamp": "2025-10-10T15:25:00",
      "old_checksum": "abc123...",
      "new_checksum": "def456...",
      "agent_owner": "claude-code"
    }
  ]
}
```

#### GET /api/sync/checksums
```json
{
  "count": 6,
  "checksums": {
    "AGENT_SYNC.md": {
      "checksum": "def456...",
      "last_modified": "2025-10-10T15:25:00",
      "agent_owner": "claude-code"
    }
  }
}
```

#### POST /api/sync/consolidate
```json
{
  "status": "success",
  "trigger": {
    "trigger_type": "manual",
    "conditions_met": {"pending_changes": 2},
    "timestamp": "2025-10-10T15:35:00"
  },
  "changes_consolidated": 2
}
```

### Métriques Prometheus

**Endpoint** : http://localhost:8000/api/metrics

#### Métriques disponibles

```prometheus
# Changements détectés (par type de fichier et agent)
sync_changes_detected_total{file_type="sync",agent="claude-code"} 12

# Consolidations déclenchées (par type)
sync_consolidations_triggered_total{trigger_type="threshold"} 5

# Statut par fichier (1=synced, 0=out_of_sync, -1=error)
sync_status{file_path="AGENT_SYNC.md"} 1

# Durée vérifications (histogram)
sync_check_duration_seconds_bucket{le="0.01"} 142

# Durée consolidations (histogram)
sync_consolidation_duration_seconds_bucket{le="1.0"} 8
```

#### Queries PromQL utiles

```promql
# Taux de changements par minute
rate(sync_changes_detected_total[5m]) * 60

# Fichiers non synchronisés
sync_status != 1

# Temps moyen de consolidation
rate(sync_consolidation_duration_seconds_sum[5m]) /
rate(sync_consolidations_triggered_total[5m])
```

---

## Pour les agents

### Claude Code

**Workflow recommandé** :

1. **Début de session**
   ```bash
   # Vérifier le dashboard
   open http://localhost:8000/sync-dashboard.html

   # Lire AGENT_SYNC.md (surveillé automatiquement)
   cat AGENT_SYNC.md
   ```

2. **Pendant la session**
   - Modifier normalement AGENT_SYNC.md, docs/passation.md, etc.
   - Le système détecte automatiquement les changements
   - Pas besoin de déclencher manuellement

3. **Fin de session**
   - Mettre à jour `docs/passation.md` (nouvelle entrée en haut)
   - Mettre à jour `AGENT_SYNC.md` (section "Zones de travail")
   - Option : Déclencher consolidation manuelle via dashboard ou API
   - Vérifier que tout est synchronisé avant de quitter

**Bonnes pratiques** :
- ✅ Modifier AGENT_SYNC.md atomiquement (1 seule fois par tâche)
- ✅ Toujours mettre à jour docs/passation.md en fin de session
- ✅ Vérifier le dashboard avant de quitter
- ❌ Ne pas modifier AGENT_SYNC.md trop fréquemment (pollution événements)

### Codex (local & cloud)

**Workflow recommandé** :

1. **Avant de coder**
   ```bash
   # Vérifier l'état de synchronisation
   curl -H "x-dev-bypass: 1" -H "X-User-ID: codex" \
     http://localhost:8000/api/sync/status
   ```

2. **Modifications**
   - Le système détecte automatiquement
   - Pas besoin d'action manuelle

3. **Fin de session**
   ```bash
   # Déclencher consolidation manuelle
   curl -X POST -H "x-dev-bypass: 1" -H "X-User-ID: codex" \
     http://localhost:8000/api/sync/consolidate
   ```

**Bonnes pratiques** :
- ✅ Utiliser l'API pour vérifier l'état
- ✅ Déclencher consolidation manuelle en fin de session
- ✅ Lire le rapport de consolidation dans AGENT_SYNC.md

---

## Troubleshooting

### Le service ne démarre pas

**Symptômes** : Logs `AutoSyncService startup failed`

**Solutions** :
1. Vérifier que le backend est démarré
2. Vérifier les permissions sur les fichiers surveillés
3. Regarder les logs détaillés :
   ```bash
   docker logs emergence-app | grep AutoSyncService
   ```

### Les changements ne sont pas détectés

**Symptômes** : Fichier modifié mais aucun événement

**Solutions** :
1. Vérifier que le fichier est dans la liste surveillée
2. Attendre 30 secondes (intervalle de check)
3. Vérifier les métriques :
   ```bash
   curl http://localhost:8000/api/metrics | grep sync_changes
   ```
4. Vérifier le dashboard : http://localhost:8000/sync-dashboard.html

### Les consolidations ne se déclenchent pas

**Symptômes** : 5+ changements mais pas de consolidation

**Solutions** :
1. Vérifier que la consolidation loop tourne (60s interval)
2. Attendre jusqu'à 60 secondes
3. Déclencher manuellement :
   ```bash
   curl -X POST -H "x-dev-bypass: 1" \
     http://localhost:8000/api/sync/consolidate
   ```

### Fichier non trouvé (WARNING)

**Symptômes** : `Watched file not found: docs/architecture/10-Memoire.md`

**Solutions** :
1. **Créer le fichier manquant** :
   ```bash
   touch docs/architecture/10-Memoire.md
   # ou créer avec contenu
   ```
2. Le service détectera automatiquement la création
3. Le warning disparaîtra au prochain cycle (30s)

### Le dashboard affiche "Not Found"

**Symptômes** : 404 sur http://localhost:8000/sync-dashboard.html

**Solutions** :
1. Vérifier que le fichier existe : `sync-dashboard.html` à la racine
2. Redémarrer le backend
3. Vérifier les logs :
   ```bash
   # Backend doit afficher
   GET /sync-dashboard.html HTTP/1.1" 200 OK
   ```

### Métriques Prometheus non exposées

**Symptômes** : Queries PromQL vides

**Solutions** :
1. Vérifier endpoint : `curl http://localhost:8000/api/metrics`
2. Chercher les métriques sync :
   ```bash
   curl http://localhost:8000/api/metrics | grep sync_
   ```
3. Redémarrer le backend si nécessaire

---

## Configuration avancée

### Modifier les intervalles

**Fichier** : `src/backend/main.py`

```python
# Ligne ~190
sync_service = get_auto_sync_service(
    check_interval_seconds=30,        # Vérification fichiers
    consolidation_threshold=5,        # Seuil changements
    consolidation_interval_minutes=60 # Intervalle temporel
)
```

### Ajouter des fichiers surveillés

**Fichier** : `src/backend/features/sync/auto_sync_service.py`

```python
# Ligne ~66
self.watched_files = [
    "AGENT_SYNC.md",
    "docs/passation.md",
    "AGENTS.md",
    # ... ajouter ici
    "nouveau_fichier.md",
]
```

### Callbacks personnalisés

```python
from backend.features.sync.auto_sync_service import get_auto_sync_service

sync_service = get_auto_sync_service()

def on_consolidation(trigger):
    print(f"Consolidation: {trigger.trigger_type}")
    # Action personnalisée

sync_service.register_consolidation_callback(on_consolidation)
```

---

## Références

- [docs/features/auto-sync.md](../features/auto-sync.md) - Documentation technique complète
- [AGENT_SYNC.md](../../AGENT_SYNC.md) - État de synchronisation (ce fichier est surveillé)
- [AGENTS.md](../../AGENTS.md) - Configuration agents
- [docs/passation.md](passation.md) - Journal de passation

---

**Dernière mise à jour** : 2025-10-10 03:00 UTC
**Auteur** : Claude Code
**Version** : 1.0.0 (Option A)
