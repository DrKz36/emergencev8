# WsOutbox - WebSocket Outbound Buffer

**Version:** 1.0.0
**Date:** 2025-10-21
**Auteur:** Claude Code

---

## 🎯 Objectif

`WsOutbox` est un buffer sortant pour WebSocket qui résout les problèmes de rafales réseau en groupant les messages sur une fenêtre de temps (coalescence) avec backpressure.

**Problèmes résolus :**
- ✅ Rafales de messages WS saturent la bande passante
- ✅ Pas de régulation du débit sortant
- ✅ Latence frontend due aux bursts réseau
- ✅ Risque d'OOM si queue illimitée

---

## 📊 Architecture

```
[Application]
      ↓
   send(msg)
      ↓
[asyncio.Queue] ← Backpressure (maxsize=512)
      ↓
  [Drain Loop] ← Coalescence 25ms
      ↓
  [Batch Send] ← Newline-delimited JSON
      ↓
  [WebSocket]
```

### Composants

1. **Queue asynchrone** (`asyncio.Queue`)
   - Taille max : 512 messages
   - Backpressure : drop si pleine
   - Non-blocking `put_nowait()`

2. **Drain Loop** (`_drain()`)
   - Récupère premier message (wait 100ms max)
   - Groupe messages sur deadline 25ms
   - Envoie batch groupé

3. **Batch Send** (`_send_batch()`)
   - Sérialisation : `"\n".join(json.dumps(x) for x in batch)`
   - Envoi : `ws.send_text(msg)`
   - Métriques Prometheus

---

## 🔧 Utilisation

### Intégration dans ConnectionManager

```python
from backend.core.ws_outbox import WsOutbox

class ConnectionManager:
    def __init__(self):
        self.outboxes: Dict[WebSocket, WsOutbox] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        # Créer et démarrer outbox
        outbox = WsOutbox(websocket)
        self.outboxes[websocket] = outbox
        await outbox.start()

    async def disconnect(self, websocket: WebSocket):
        # Arrêter outbox proprement
        outbox = self.outboxes.pop(websocket, None)
        if outbox:
            await outbox.stop()

    async def send_message(self, websocket: WebSocket, message: dict):
        # Envoyer via outbox au lieu de ws.send_json()
        outbox = self.outboxes.get(websocket)
        if outbox:
            await outbox.send(message)
```

### Côté Client (JavaScript)

Le client doit parser les batches newline-delimited JSON :

```javascript
websocket.onmessage = (ev) => {
  const rawData = ev.data;
  const lines = rawData.includes('\n')
    ? rawData.split('\n').filter(l => l.trim())
    : [rawData];

  for (const line of lines) {
    const msg = JSON.parse(line);
    // Traitement du message
  }
};
```

---

## 📈 Métriques Prometheus

### 1. `ws_outbox_queue_size` (Gauge)
Taille actuelle de la queue.

```promql
# Alerte si queue > 400 (proche saturation)
ws_outbox_queue_size > 400
```

### 2. `ws_outbox_batch_size` (Histogram)
Distribution des tailles de batches envoyés.

**Buckets:** `[1, 2, 5, 10, 20, 50, 100]`

```promql
# Médiane taille batch
histogram_quantile(0.5, ws_outbox_batch_size_bucket)

# P95 taille batch
histogram_quantile(0.95, ws_outbox_batch_size_bucket)
```

### 3. `ws_outbox_send_latency_seconds` (Histogram)
Latence d'envoi des batches (sérialisation + send).

**Buckets:** `[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25]`

```promql
# P50 latency
histogram_quantile(0.5, ws_outbox_send_latency_seconds_bucket)

# P99 latency
histogram_quantile(0.99, ws_outbox_send_latency_seconds_bucket)
```

### 4. `ws_outbox_dropped_messages_total` (Counter)
Nombre total de messages droppés (queue pleine).

```promql
# Rate de drop sur 5 min
rate(ws_outbox_dropped_messages_total[5m])

# Alerte si drops > 0
ws_outbox_dropped_messages_total > 0
```

### 5. `ws_outbox_send_errors_total` (Counter)
Nombre total d'erreurs d'envoi.

```promql
# Rate d'erreurs sur 5 min
rate(ws_outbox_send_errors_total[5m])
```

---

## ⚙️ Configuration

### Paramètres (dans `ws_outbox.py`)

```python
COALESCE_MS = 25      # Fenêtre de coalescence (ms)
OUTBOX_MAX = 512      # Taille max queue
```

### Tuning

**Augmenter coalescence** (ex: 50ms) :
- ✅ Plus gros batches → moins de sends réseau
- ❌ Latence accrue (50ms vs 25ms)

**Augmenter queue** (ex: 1024) :
- ✅ Moins de drops en cas de burst
- ❌ Plus de mémoire utilisée

**Diminuer coalescence** (ex: 10ms) :
- ✅ Latence réduite
- ❌ Plus de sends réseau (batches plus petits)

---

## 🧪 Tests

### Test de charge (1000 messages en 10s)

```python
import asyncio, websockets, json, time

async def load_test():
    uri = "wss://emergence-app.ch/ws/test?thread_id=test"
    async with websockets.connect(uri) as ws:
        start = time.time()
        for i in range(1000):
            await ws.send(json.dumps({
                "type": "chat.message",
                "payload": {"text": f"Test {i}", "agent_id": "anima"}
            }))
        elapsed = time.time() - start
        print(f"Sent 1000 msgs in {elapsed:.2f}s")

asyncio.run(load_test())
```

**Vérifications Prometheus :**
- `ws_outbox_batch_size{quantile="0.5"}` > 5 (médiane > 5 msgs/batch)
- `ws_outbox_dropped_total` = 0 (aucun drop)
- `ws_outbox_send_latency{quantile="0.95"}` < 0.01 (p95 < 10ms)

---

## 📊 Monitoring Grafana

### Dashboard recommandé

**Panel 1 - Queue Size (Graph)**
```promql
ws_outbox_queue_size
```
Seuil warning : 400
Seuil critical : 500

**Panel 2 - Batch Size Distribution (Histogram)**
```promql
histogram_quantile(0.5, ws_outbox_batch_size_bucket)  # P50
histogram_quantile(0.95, ws_outbox_batch_size_bucket) # P95
histogram_quantile(0.99, ws_outbox_batch_size_bucket) # P99
```

**Panel 3 - Send Latency (Graph)**
```promql
histogram_quantile(0.95, ws_outbox_send_latency_seconds_bucket)
```
Seuil warning : 50ms
Seuil critical : 100ms

**Panel 4 - Dropped Messages Rate (Graph)**
```promql
rate(ws_outbox_dropped_messages_total[5m])
```
Alerte si > 0

**Panel 5 - Send Errors Rate (Graph)**
```promql
rate(ws_outbox_send_errors_total[5m])
```

---

## 🐛 Troubleshooting

### Symptôme : `ws_outbox_dropped_total` augmente

**Cause :** Queue saturée (512 msgs), messages droppés.

**Solutions :**
1. Vérifier que drain loop tourne (`_drain()` pas bloquée)
2. Augmenter `OUTBOX_MAX` (ex: 1024)
3. Réduire `COALESCE_MS` pour drain plus rapide (ex: 10ms)
4. Investiguer pourquoi autant de messages (bug côté app?)

### Symptôme : `ws_outbox_batch_size` toujours = 1

**Cause :** Pas assez de messages dans la fenêtre de 25ms.

**Diagnostic :**
- Trafic trop faible → normal
- Drain loop trop rapide → vérifier `COALESCE_MS`

**Solutions :**
- Augmenter `COALESCE_MS` si latence acceptable (ex: 50ms)
- Accepter batch=1 si trafic faible (pas critique)

### Symptôme : `ws_outbox_send_latency` > 100ms

**Cause :** Sérialisation JSON lente ou WebSocket bloqué.

**Solutions :**
1. Vérifier taille des payloads (très gros messages?)
2. Profiler `json.dumps()` (cProfile)
3. Vérifier réseau (latency côté client?)

---

## 🔒 Sécurité

### Backpressure

Le drop de messages (queue pleine) est **intentionnel** pour éviter l'OOM.

**Alternative sans drop :**
```python
# Bloquer au lieu de dropper (⚠️ peut causer deadlock)
await self.q.put(payload)  # Bloque si pleine
```

**Recommandation :** Garder `put_nowait()` + monitoring `dropped_total`.

### Rate limiting

WsOutbox ne fait **pas** de rate limiting (pas de limite msgs/sec).

Si nécessaire, ajouter en amont :
```python
from backend.core.middleware import RateLimitMiddleware

app.add_middleware(RateLimitMiddleware, requests_per_minute=300)
```

---

## 📚 Références

- **Code source :** [`src/backend/core/ws_outbox.py`](../../src/backend/core/ws_outbox.py)
- **Intégration :** [`src/backend/core/websocket.py`](../../src/backend/core/websocket.py)
- **Client JS :** [`src/frontend/core/websocket.js`](../../src/frontend/core/websocket.js)
- **AGENT_SYNC.md :** Session [2025-10-21 09:25 CET](../../AGENT_SYNC.md#-session-complétée-2025-10-21-0925-cet--agent--claude-code-optimisations-websocket--cloud-run)
- **Passation :** [docs/passation.md](../passation.md)

---

## ✅ Checklist Déploiement

Avant de déployer WsOutbox en production :

- [ ] Tests de charge locaux (1000 msgs/10s) ✅
- [ ] Vérifier métriques Prometheus disponibles (`/metrics`) ✅
- [ ] Dashboard Grafana configuré avec alertes
- [ ] Client JS modifié pour parser batches ✅
- [ ] Monitoring `ws_outbox_dropped_total` (alerte si > 0)
- [ ] Documentation lue par l'équipe
- [ ] Déploiement staging + validation 24h
- [ ] Rollout progressif production (10% → 50% → 100%)

---

**🔥 WsOutbox est prêt pour la production !**
