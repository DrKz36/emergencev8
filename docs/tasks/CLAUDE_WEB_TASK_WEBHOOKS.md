# 🌐 TÂCHE CLAUDE CODE WEB — Webhooks et Intégrations (P3.11)

**Branche:** `feature/webhooks-integrations`
**Durée estimée:** 3 jours
**Priorité:** P3 (BASSE - Nice-to-have)
**Assigné à:** Claude Code Web
**Date d'attribution:** 2025-10-24

---

## 🎯 Objectif

Implémenter système de webhooks pour permettre intégrations externes (Slack, Discord, Zapier, n8n, Make, etc.)

---

## 📋 Tâches Détaillées

### 1. Backend: table `webhooks` (migration SQL)

**Fichier:** `migrations/add_webhooks_table.sql`

```sql
-- Migration: Add webhooks table for external integrations
CREATE TABLE IF NOT EXISTS webhooks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    url TEXT NOT NULL,
    events TEXT NOT NULL,  -- JSON array: ["thread.created", "message.sent"]
    secret TEXT NOT NULL,  -- HMAC signature key (32 chars hex)
    enabled BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX idx_webhooks_user_enabled ON webhooks(user_id, enabled);

-- Table pour tracking deliveries
CREATE TABLE IF NOT EXISTS webhook_deliveries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    webhook_id INTEGER NOT NULL,
    event TEXT NOT NULL,
    payload TEXT NOT NULL,  -- JSON
    status TEXT NOT NULL,  -- 'success', 'failed', 'pending'
    response_code INTEGER,
    response_body TEXT,
    attempts INTEGER DEFAULT 0,
    next_retry_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (webhook_id) REFERENCES webhooks(id) ON DELETE CASCADE
);

CREATE INDEX idx_webhook_deliveries_status ON webhook_deliveries(webhook_id, status);
CREATE INDEX idx_webhook_deliveries_retry ON webhook_deliveries(status, next_retry_at);
```

**Actions:**
- [ ] Créer migration SQL
- [ ] Tester migration sur DB dev (SQLite)
- [ ] Ajouter triggers pour `updated_at`:
  ```sql
  CREATE TRIGGER update_webhooks_timestamp
  AFTER UPDATE ON webhooks
  BEGIN
      UPDATE webhooks SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
  END;
  ```

---

### 2. Endpoints POST/GET/DELETE webhooks

**Fichier:** `src/backend/features/webhooks/router.py`

**Endpoints à implémenter:**

```python
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from .service import WebhookService
from .models import WebhookCreate, WebhookUpdate, WebhookResponse

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])

@router.post("/", response_model=WebhookResponse)
async def create_webhook(
    data: WebhookCreate,
    user_id: int = Depends(get_current_user_id),
    service: WebhookService = Depends()
):
    """Créer un nouveau webhook."""
    # Validation URL (HTTPS only, pas localhost)
    # Génération secret automatique (secrets.token_hex(32))
    return await service.create_webhook(user_id, data)

@router.get("/", response_model=List[WebhookResponse])
async def list_webhooks(
    user_id: int = Depends(get_current_user_id),
    service: WebhookService = Depends()
):
    """Liste tous les webhooks de l'utilisateur."""
    return await service.list_webhooks(user_id)

@router.get("/{webhook_id}", response_model=WebhookResponse)
async def get_webhook(
    webhook_id: int,
    user_id: int = Depends(get_current_user_id),
    service: WebhookService = Depends()
):
    """Détails d'un webhook (avec stats deliveries)."""
    return await service.get_webhook(webhook_id, user_id)

@router.patch("/{webhook_id}", response_model=WebhookResponse)
async def update_webhook(
    webhook_id: int,
    data: WebhookUpdate,
    user_id: int = Depends(get_current_user_id),
    service: WebhookService = Depends()
):
    """Modifier un webhook."""
    return await service.update_webhook(webhook_id, user_id, data)

@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook(
    webhook_id: int,
    user_id: int = Depends(get_current_user_id),
    service: WebhookService = Depends()
):
    """Supprimer un webhook."""
    await service.delete_webhook(webhook_id, user_id)

@router.post("/{webhook_id}/test", response_model=dict)
async def test_webhook(
    webhook_id: int,
    user_id: int = Depends(get_current_user_id),
    service: WebhookService = Depends()
):
    """Envoyer un événement de test au webhook."""
    return await service.test_webhook(webhook_id, user_id)
```

**Actions:**
- [ ] Créer `router.py` avec tous les endpoints
- [ ] Implémenter validation URL (HTTPS only):
  ```python
  from urllib.parse import urlparse
  parsed = urlparse(url)
  if parsed.scheme != 'https':
      raise ValueError("URL must be HTTPS")
  ```
- [ ] Générer secret automatique: `secrets.token_hex(32)`
- [ ] Ownership check: `webhook.user_id == current_user_id`

---

### 3. Système événements (thread.created, message.sent, analysis.completed)

**Fichier:** `src/backend/features/webhooks/events.py`

```python
from enum import Enum
from typing import Any, Dict
from datetime import datetime

class WebhookEvent(str, Enum):
    """Types d'événements webhook."""
    THREAD_CREATED = "thread.created"
    THREAD_ARCHIVED = "thread.archived"
    MESSAGE_SENT = "message.sent"
    ANALYSIS_COMPLETED = "analysis.completed"
    CONCEPT_CREATED = "concept.created"

async def emit_webhook_event(
    event: WebhookEvent,
    user_id: int,
    data: Dict[str, Any]
) -> None:
    """
    Émet un événement webhook.

    Args:
        event: Type d'événement (WebhookEvent enum)
        user_id: ID utilisateur propriétaire
        data: Données de l'événement (sera sérialisé en JSON)
    """
    from .delivery import deliver_webhooks

    # Récupérer webhooks actifs pour cet event
    webhooks = await get_webhooks_for_event(user_id, event)

    # Créer payload
    payload = {
        "event": event.value,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "data": data,
        "user_id": user_id
    }

    # Deliver en arrière-plan
    for webhook in webhooks:
        asyncio.create_task(deliver_webhooks(webhook, payload))
```

**Intégrations dans services existants:**

```python
# Dans ChatService.create_thread()
await emit_webhook_event(
    WebhookEvent.THREAD_CREATED,
    user_id,
    {"thread_id": thread.id, "title": thread.title}
)

# Dans ChatService.send_message()
await emit_webhook_event(
    WebhookEvent.MESSAGE_SENT,
    user_id,
    {"message_id": msg.id, "thread_id": msg.thread_id, "agent": msg.agent}
)

# Dans MemoryAnalyzer (après analyse)
await emit_webhook_event(
    WebhookEvent.ANALYSIS_COMPLETED,
    user_id,
    {"thread_id": thread_id, "concepts_count": len(concepts)}
)
```

**Actions:**
- [ ] Créer `events.py` avec enum + `emit_webhook_event()`
- [ ] Intégrer dans `ChatService` (2 events)
- [ ] Intégrer dans `MemoryAnalyzer` (1 event)
- [ ] Ajouter logs debug pour tracking events

---

### 4. POST vers webhook URL avec signature HMAC

**Fichier:** `src/backend/features/webhooks/delivery.py`

```python
import hmac
import hashlib
import json
import httpx
from typing import Dict, Any

async def deliver_webhook(webhook: Webhook, payload: Dict[str, Any]) -> bool:
    """
    Délivre un événement webhook avec signature HMAC.

    Returns:
        True si succès (2xx), False sinon
    """
    # Sérialiser payload
    body = json.dumps(payload, separators=(',', ':'))

    # Générer signature HMAC-SHA256
    signature = hmac.new(
        webhook.secret.encode(),
        body.encode(),
        hashlib.sha256
    ).hexdigest()

    # Headers
    headers = {
        "Content-Type": "application/json",
        "X-Emergence-Event": payload["event"],
        "X-Emergence-Signature": f"sha256={signature}",
        "X-Emergence-Webhook-Id": str(webhook.id),
        "User-Agent": "Emergence-Webhooks/1.0"
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                webhook.url,
                content=body,
                headers=headers
            )

            # Log delivery
            await log_delivery(
                webhook_id=webhook.id,
                event=payload["event"],
                payload=body,
                status="success" if response.is_success else "failed",
                response_code=response.status_code,
                response_body=response.text[:1000]  # Limit 1000 chars
            )

            return response.is_success

    except Exception as e:
        await log_delivery(
            webhook_id=webhook.id,
            event=payload["event"],
            payload=body,
            status="failed",
            response_body=str(e)
        )
        return False
```

**Retry logic (3 tentatives, backoff exponentiel):**

```python
async def deliver_with_retry(webhook: Webhook, payload: Dict[str, Any]) -> None:
    """Délivre avec retry automatique (3 max)."""
    max_attempts = 3
    backoff = [1, 5, 15]  # seconds

    for attempt in range(max_attempts):
        success = await deliver_webhook(webhook, payload)
        if success:
            return

        if attempt < max_attempts - 1:
            await asyncio.sleep(backoff[attempt])

    # Failed after 3 attempts
    logger.warning(f"Webhook {webhook.id} failed after {max_attempts} attempts")
```

**Actions:**
- [ ] Créer `delivery.py` avec HMAC signature
- [ ] Implémenter retry logic (3 max, backoff 1s/5s/15s)
- [ ] Logger toutes les deliveries dans `webhook_deliveries` table
- [ ] Timeout 10s par requête

---

### 5. UI: onglet "Webhooks" (Paramètres > Intégrations)

**Fichier:** `src/frontend/features/settings/webhooks.js`

**UI à implémenter:**

```javascript
class WebhooksSettings {
  async init() {
    // Fetch webhooks
    const webhooks = await this.fetchWebhooks();

    // Render liste
    this.renderWebhooksList(webhooks);

    // Bouton "Créer Webhook"
    this.attachCreateHandler();
  }

  renderWebhooksList(webhooks) {
    // Tableau: Nom | URL | Events | Status | Actions
    // Colonnes:
    // - Nom (éditable inline)
    // - URL (tronquée, tooltip complet)
    // - Events (badges: "thread.created", "message.sent")
    // - Status (toggle Enabled/Disabled)
    // - Actions (Modifier, Tester, Supprimer)
  }

  async showCreateModal() {
    // Modal avec:
    // - Input nom (required)
    // - Input URL (validation HTTPS, required)
    // - Multiselect events (checkboxes)
    // - Afficher secret généré (copy button)
    // - Bouton "Créer"
  }

  async testWebhook(webhookId) {
    // POST /api/webhooks/{id}/test
    // Afficher toast: "Test envoyé" ou "Échec: [erreur]"
  }

  async deleteWebhook(webhookId) {
    // Confirmation modal: "Êtes-vous sûr ?"
    // DELETE /api/webhooks/{id}
    // Reload liste
  }
}
```

**Design:**
- Tableau responsive (mobile: cards au lieu de table)
- Badges colorés par event type
- Toggle animé pour enable/disable
- Modal avec tabs (Créer | Modifier | Stats)

**Actions:**
- [ ] Créer `webhooks.js` avec class WebhooksSettings
- [ ] Créer `webhooks.css` (styles table + modal)
- [ ] Intégrer dans `settings.js` (nouveau tab)
- [ ] Tests manuels: créer, modifier, supprimer webhook

---

### 6. Retry automatique si échec (3 tentatives)

**Fichier:** `src/backend/features/webhooks/retry_worker.py`

```python
import asyncio
from datetime import datetime, timedelta

async def retry_worker():
    """Worker périodique qui retry les failed deliveries."""
    while True:
        try:
            # Fetch failed deliveries à retry
            failed = await get_failed_deliveries_to_retry()

            for delivery in failed:
                if delivery.attempts < 3:
                    # Retry
                    webhook = await get_webhook(delivery.webhook_id)
                    payload = json.loads(delivery.payload)
                    success = await deliver_webhook(webhook, payload)

                    # Update attempts
                    await update_delivery_attempts(
                        delivery.id,
                        delivery.attempts + 1,
                        next_retry_at=None if success else calculate_next_retry(delivery.attempts + 1)
                    )
                else:
                    # Max attempts reached, mark as permanently failed
                    await mark_delivery_permanently_failed(delivery.id)

        except Exception as e:
            logger.error(f"Retry worker error: {e}")

        # Run every 30s
        await asyncio.sleep(30)

def calculate_next_retry(attempts: int) -> datetime:
    """Calcule prochain retry (backoff exponentiel)."""
    delays = [60, 300, 900]  # 1min, 5min, 15min
    delay = delays[min(attempts - 1, len(delays) - 1)]
    return datetime.utcnow() + timedelta(seconds=delay)
```

**Démarrage worker:**

```python
# Dans main.py
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(retry_worker())
```

**Actions:**
- [ ] Créer `retry_worker.py`
- [ ] Implémenter backoff exponentiel (1min, 5min, 15min)
- [ ] Max 3 attempts, puis mark permanently failed
- [ ] Notification user si 5+ échecs consécutifs
- [ ] Démarrer worker au startup app

---

## 📁 Fichiers à Créer

### Backend
- `migrations/add_webhooks_table.sql`
- `src/backend/features/webhooks/__init__.py`
- `src/backend/features/webhooks/models.py` (Pydantic models)
- `src/backend/features/webhooks/service.py` (Business logic)
- `src/backend/features/webhooks/events.py` (Event enum + emit)
- `src/backend/features/webhooks/delivery.py` (HTTP POST + HMAC)
- `src/backend/features/webhooks/retry_worker.py` (Background retry)
- `src/backend/features/webhooks/router.py` (API endpoints)

### Frontend
- `src/frontend/features/settings/webhooks.js`
- `src/frontend/styles/webhooks.css`

## 📝 Fichiers à Modifier

### Backend
- `src/backend/main.py` (register router + start retry worker)
- `src/backend/features/chat/service.py` (emit events)
- `src/backend/features/memory/analyzer.py` (emit events)

### Frontend
- `src/frontend/features/settings/settings.js` (ajouter onglet)

---

## ✅ Acceptance Criteria

- [ ] Webhooks CRUD complets (create, list, get, update, delete)
- [ ] Delivery automatique events sélectionnés
- [ ] Signature HMAC vérifiable côté destinataire
- [ ] Retry automatique 3x si échec (5xx, timeout)
- [ ] UI intuitive (modal création, liste, stats)
- [ ] Documentation exemple intégration Slack/Discord
- [ ] Tests manuels: webhook Slack fonctionne end-to-end

---

## 📚 Exemple Test Slack

**1. Créer Incoming Webhook Slack:**
- https://api.slack.com/messaging/webhooks
- Copier URL: `https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX`

**2. Créer webhook dans Emergence:**
- Nom: "Notifications Slack"
- URL: [URL Slack]
- Events: `["thread.created", "message.sent"]`
- Secret: (généré auto)

**3. Tester:**
- Créer nouveau thread dans Emergence
- Vérifier message Slack reçu: "New thread: [titre]"

**Format payload Slack:**
```json
{
  "text": "New thread created",
  "blocks": [
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "*Thread:* Test conversation\n*User:* user@example.com"
      }
    }
  ]
}
```

---

## ⚠️ Notes Importantes

1. **Secret webhook:** Générer avec `secrets.token_hex(32)` (64 chars hex)
2. **Signature HMAC:** `hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()`
3. **Validation URL:** `from urllib.parse import urlparse` → scheme must be 'https'
4. **Async delivery:** `asyncio.create_task(deliver_webhook(...))` pour pas bloquer requête user
5. **Timeout:** 10s max par requête webhook
6. **Retry:** Max 3 attempts, backoff exponentiel (1min, 5min, 15min)

---

## 🔄 Prochaines Étapes Après Webhooks

Une fois Webhooks terminé et PR mergée:
- Option A: Enchaîner sur P3.12 API Publique (5 jours)
- Option B: Enchaîner sur P3.13 Agents Personnalisés (6 jours)
- Option C: Attendre validation FG pour décider

**Coordination:** Consulter `AGENT_SYNC.md` pour voir progression Codex sur PWA

---

**Contact Architecte:** gonzalefernando@gmail.com
**Dernière mise à jour:** 2025-10-24
