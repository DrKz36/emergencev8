# 🔄 Fonctionnement du Système de Synchronisation Automatique

**Date** : 2025-10-10
**Version** : Option A (Automatique complète)
**Statut** : ✅ Opérationnel

---

## 📋 Résumé Exécutif

Le système de synchronisation automatique **AutoSyncService** surveille en permanence **8 fichiers critiques** de documentation et déclenche automatiquement des **consolidations intelligentes** pour éviter les conflits entre agents (Claude Code, Codex local, Codex cloud).

### Qu'est-ce qui est surveillé ?

1. **AGENT_SYNC.md** - État de synchronisation inter-agents
2. **docs/passation.md** - Journal de passation
3. **AGENTS.md** - Configuration agents
4. **CODEV_PROTOCOL.md** - Protocole collaboration
5. **docs/architecture/00-Overview.md** - Vue d'ensemble
6. **docs/architecture/30-Contracts.md** - Contrats API
7. **docs/architecture/10-Memoire.md** - Mémoire (⚠️ à créer)
8. **ROADMAP.md** - Roadmap (⚠️ à créer)

### Comment ça fonctionne ?

```
┌─────────────────────────────────────────────────┐
│         1. DÉTECTION AUTOMATIQUE                │
│    Toutes les 30 secondes, le système :         │
│    - Calcule checksum MD5 de chaque fichier     │
│    - Compare avec checksum précédent            │
│    - Crée événement si changement détecté       │
└─────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────┐
│         2. ACCUMULATION ÉVÉNEMENTS              │
│    Chaque changement est ajouté à la liste      │
│    pending_changes (type: modified/created/     │
│    deleted, timestamp, checksums old→new)       │
└─────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────┐
│         3. TRIGGERS DE CONSOLIDATION            │
│    La consolidation se déclenche si :           │
│    A) 5 changements accumulés (seuil)          │
│    B) 60 minutes depuis dernière consolidation  │
│    C) Déclenchement manuel (dashboard/API)      │
└─────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────┐
│         4. CONSOLIDATION AUTOMATIQUE            │
│    Le système :                                  │
│    - Génère rapport avec tous les événements    │
│    - Ajoute rapport à AGENT_SYNC.md             │
│    - Réinitialise pending_changes               │
│    - Met à jour métriques Prometheus            │
└─────────────────────────────────────────────────┘
```

---

## 🎯 Fonctionnement Précis

### Phase 1 : Détection (Check Loop)

**Fréquence** : Toutes les 30 secondes

**Processus** :
1. Pour chaque fichier surveillé :
   ```python
   # 1. Lire le fichier
   content = read_file("AGENT_SYNC.md")

   # 2. Calculer checksum MD5
   new_checksum = md5(content)

   # 3. Comparer avec checksum stocké
   if new_checksum != stored_checksums["AGENT_SYNC.md"]:
       # 4. Créer événement
       event = SyncEvent(
           file_path="AGENT_SYNC.md",
           event_type="modified",
           old_checksum=stored_checksums["AGENT_SYNC.md"],
           new_checksum=new_checksum,
           timestamp=datetime.now(),
           agent_owner=detect_owner()  # via git blame
       )

       # 5. Ajouter à pending_changes
       pending_changes.append(event)

       # 6. Mettre à jour checksum stocké
       stored_checksums["AGENT_SYNC.md"] = new_checksum

       # 7. Métriques
       sync_changes_detected_total.labels(
           file_type="sync",
           agent="claude-code"
       ).inc()

       sync_status.labels(file_path="AGENT_SYNC.md").set(0)  # out_of_sync
   ```

### Phase 2 : Vérification Triggers (Consolidation Loop)

**Fréquence** : Toutes les 60 secondes

**Processus** :
```python
# Trigger A : Seuil de changements
if len(pending_changes) >= consolidation_threshold:  # 5 par défaut
    await trigger_consolidation(
        type="threshold",
        conditions={"pending_changes": len(pending_changes), "threshold": 5}
    )
    return

# Trigger B : Intervalle temporel
if last_consolidation is not None:
    time_elapsed = now() - last_consolidation
    if time_elapsed >= 60 minutes AND len(pending_changes) > 0:
        await trigger_consolidation(
            type="time_based",
            conditions={"pending_changes": len(pending_changes), "minutes": 60}
        )
```

### Phase 3 : Consolidation

**Processus** :
1. **Capture** : Sauvegarder le nombre de changements AVANT de les réinitialiser
2. **Rapport** : Générer rapport Markdown avec tous les événements groupés par fichier
3. **Écriture** : Insérer rapport dans AGENT_SYNC.md (section `## 🤖 Synchronisation automatique`)
4. **Reset** : Vider `pending_changes = []`
5. **Statuts** : Mettre tous les fichiers à `sync_status = 1` (synced)
6. **Timestamp** : `last_consolidation = now()`
7. **Métriques** : `sync_consolidations_triggered_total.labels(type).inc()`
8. **Callbacks** : Appeler toutes les fonctions enregistrées

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
  - `modified` à 2025-10-10T15:26:00 (agent: claude-code)
  - `modified` à 2025-10-10T15:29:00 (agent: codex-local)

---
```

---

## 🔍 Détails Techniques

### Checksums MD5

**Pourquoi MD5 ?**
- Rapide (important pour vérifications toutes les 30s)
- Collision négligeable pour fichiers texte petits
- Supporté nativement par Python (`hashlib.md5`)

**Calcul** :
```python
import hashlib

def compute_checksum(file_path: Path) -> str:
    md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            md5.update(chunk)
    return md5.hexdigest()  # ex: "a1b2c3d4e5f6..."
```

### Détection Agent Propriétaire

**Actuel** : Retourne `None` (non implémenté)

**Future implémentation** :
```python
def detect_agent_owner(file_path: str) -> str | None:
    # Utiliser git blame pour la dernière ligne modifiée
    result = subprocess.run(
        ["git", "blame", "-L", "-1,-1", "--", file_path],
        capture_output=True,
        text=True
    )
    # Parser output pour extraire author
    # ex: "^1868b25 (Claude Code 2025-10-10 ...)"
    if "Claude Code" in result.stdout:
        return "claude-code"
    elif "Codex" in result.stdout:
        return "codex-local" or "codex-cloud"
    return None
```

### Thread Safety

**Architecture asyncio** :
- **Check loop** : `asyncio.create_task(self._check_loop())`
- **Consolidation loop** : `asyncio.create_task(self._consolidation_loop())`
- **Pas de race conditions** : Chaque loop accède à ses propres variables
- **Shared state** : `pending_changes` (list) thread-safe pour append

**Graceful shutdown** :
```python
async def stop(self):
    self._running = False
    if self._check_task:
        self._check_task.cancel()
        await self._check_task  # Attendre annulation
    if self._consolidation_task:
        self._consolidation_task.cancel()
        await self._consolidation_task
```

---

## 📊 Dashboard & Monitoring

### Dashboard Web

**Accès** : http://localhost:8000/sync-dashboard.html

**Données affichées** :
1. **Statut global**
   - État service : ✅ Actif / ❌ Arrêté
   - Changements en attente : 3
   - Fichiers surveillés : 8
   - Checksums trackés : 6
   - Seuil consolidation : 5
   - Intervalle vérification : 30s
   - Dernière consolidation : 2025-10-10T15:30:00

2. **Changements en attente**
   - Liste événements non consolidés
   - Type (modified/created/deleted) avec couleur
   - Timestamp
   - Checksums (old → new)
   - Agent propriétaire

3. **Fichiers surveillés**
   - Liste 8 fichiers
   - Checksum actuel (12 premiers chars)
   - Date dernière modification
   - Agent propriétaire

4. **Actions**
   - Bouton "Déclencher consolidation manuelle"
   - Bouton "Rafraîchir"

**Auto-refresh** : Toutes les 10 secondes via `setInterval(loadSyncStatus, 10000)`

### API REST

#### GET /api/sync/status
```bash
curl -H "x-dev-bypass: 1" -H "X-User-ID: dev" \
  http://localhost:8000/api/sync/status
```

Réponse :
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

#### POST /api/sync/consolidate
```bash
curl -X POST -H "x-dev-bypass: 1" -H "X-User-ID: dev" \
  http://localhost:8000/api/sync/consolidate
```

Réponse :
```json
{
  "status": "success",
  "trigger": {
    "trigger_type": "manual",
    "conditions_met": {"pending_changes": 3},
    "timestamp": "2025-10-10T15:35:00"
  },
  "changes_consolidated": 3
}
```

### Métriques Prometheus

**Endpoint** : http://localhost:8000/api/metrics

```prometheus
# Changements détectés
sync_changes_detected_total{file_type="sync",agent="claude-code"} 12
sync_changes_detected_total{file_type="passation",agent="codex-local"} 5

# Consolidations
sync_consolidations_triggered_total{trigger_type="threshold"} 8
sync_consolidations_triggered_total{trigger_type="time_based"} 3
sync_consolidations_triggered_total{trigger_type="manual"} 2

# Statut fichiers
sync_status{file_path="AGENT_SYNC.md"} 1  # 1=synced, 0=out_of_sync, -1=error
sync_status{file_path="docs/passation.md"} 1

# Durées (histograms)
sync_check_duration_seconds_bucket{le="0.01"} 142
sync_consolidation_duration_seconds_bucket{le="1.0"} 8
```

**Queries PromQL utiles** :
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

## 🚀 Utilisation par les Agents

### Claude Code

**Début de session** :
```bash
# 1. Vérifier dashboard
open http://localhost:8000/sync-dashboard.html

# 2. Lire AGENT_SYNC.md (surveillé auto)
cat AGENT_SYNC.md

# 3. Lire docs/passation.md (surveillé auto)
head -n 100 docs/passation.md
```

**Pendant la session** :
- Modifier normalement AGENT_SYNC.md, docs/passation.md, etc.
- Le système détecte automatiquement (max 30s)
- Pas besoin de déclencher manuellement

**Fin de session** :
```bash
# 1. Mettre à jour docs/passation.md (nouvelle entrée en haut)
# 2. Mettre à jour AGENT_SYNC.md (section "Zones de travail")
# 3. Option A : Laisser consolidation auto (seuil 5 ou 60 min)
# 3. Option B : Dashboard → bouton "Déclencher consolidation"
# 3. Option C : curl -X POST http://localhost:8000/api/sync/consolidate
```

### Codex (local & cloud)

**Avant de coder** :
```bash
# Vérifier état sync
curl -H "x-dev-bypass: 1" -H "X-User-ID: codex" \
  http://localhost:8000/api/sync/status
```

**Fin de session** :
```bash
# Déclencher consolidation manuelle
curl -X POST -H "x-dev-bypass: 1" -H "X-User-ID: codex" \
  http://localhost:8000/api/sync/consolidate

# Lire rapport dans AGENT_SYNC.md
tail -n 30 AGENT_SYNC.md
```

---

## 📚 Documentation Complète

### Fichiers de référence

1. **[docs/SYNCHRONISATION_AUTOMATIQUE.md](docs/SYNCHRONISATION_AUTOMATIQUE.md)**
   - Guide utilisateur complet (12 sections)
   - Architecture, fichiers, workflow, troubleshooting
   - Instructions par agent (Claude Code, Codex)
   - **À LIRE EN PRIORITÉ**

2. **[docs/features/auto-sync.md](docs/features/auto-sync.md)**
   - Documentation technique développeur
   - Architecture, configuration, tests, roadmap
   - Métriques Prometheus détaillées

3. **[AGENT_SYNC.md](AGENT_SYNC.md)**
   - État synchronisation (fichier surveillé)
   - Rapports consolidation automatiques (section `## 🤖 Synchronisation automatique`)

4. **[AGENTS.md](AGENTS.md)**
   - Configuration agents (fichier surveillé)
   - Instructions sync auto (sections début/fin session)

5. **[docs/passation.md](docs/passation.md)**
   - Journal passation (fichier surveillé)
   - Entrée session auto-sync (2025-10-10 03:00)

---

## ⚙️ Configuration

### Modifier les intervalles

**Fichier** : `src/backend/main.py` (ligne ~190)

```python
sync_service = get_auto_sync_service(
    check_interval_seconds=30,        # Vérification fichiers
    consolidation_threshold=5,        # Seuil changements
    consolidation_interval_minutes=60 # Intervalle temporel
)
```

### Ajouter des fichiers surveillés

**Fichier** : `src/backend/features/sync/auto_sync_service.py` (ligne ~66)

```python
self.watched_files = [
    "AGENT_SYNC.md",
    "docs/passation.md",
    "AGENTS.md",
    "CODEV_PROTOCOL.md",
    "docs/architecture/00-Overview.md",
    "docs/architecture/30-Contracts.md",
    "docs/architecture/10-Memoire.md",  # À créer
    "ROADMAP.md",  # À créer
    # Ajouter ici :
    "nouveau_fichier.md",
]
```

---

## ✅ Checklist Validation

### Vérification système opérationnel

```bash
# 1. Backend démarré ?
curl http://localhost:8000/api/health
# ✅ {"status": "ok"}

# 2. AutoSyncService actif ?
curl http://localhost:8000/api/sync/status | jq '.running'
# ✅ true

# 3. Fichiers surveillés ?
curl http://localhost:8000/api/sync/status | jq '.watched_files'
# ✅ 8

# 4. Dashboard accessible ?
curl -I http://localhost:8000/sync-dashboard.html
# ✅ HTTP/1.1 200 OK

# 5. Métriques exposées ?
curl http://localhost:8000/api/metrics | grep sync_
# ✅ sync_changes_detected_total{...}
#    sync_consolidations_triggered_total{...}
#    sync_status{...}
#    sync_check_duration_seconds{...}
#    sync_consolidation_duration_seconds{...}
```

### Test fonctionnel complet

```bash
# 1. Modifier un fichier surveillé
echo "# Test" >> AGENT_SYNC.md

# 2. Attendre détection (max 30s)
sleep 31

# 3. Vérifier changement détecté
curl http://localhost:8000/api/sync/pending-changes | jq '.count'
# ✅ 1

# 4. Déclencher consolidation manuelle
curl -X POST http://localhost:8000/api/sync/consolidate | jq '.changes_consolidated'
# ✅ 1

# 5. Vérifier rapport dans AGENT_SYNC.md
tail -n 20 AGENT_SYNC.md
# ✅ Section "### Consolidation - 2025-10-10T..." présente
```

---

**Dernière mise à jour** : 2025-10-10 03:15 UTC
**Auteur** : Claude Code
**Version** : 1.0.0
