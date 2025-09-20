# ÉMERGENCE — Contrats d’API internes (WS + REST)
> V4.0 — Aligné architecture multi-agents + mémoire progressive.

## 0) Principes
- Tous les échanges utilisent `{ "type": string, "payload": object }`.
- Les événements serveur sont préfixés `ws:` ; les erreurs critiques côté serveur déclenchent `ws:error` + log.
- Auth : ID token obligatoire (header `Authorization: Bearer <JWT>`). Mode dev : `X-User-Id`.

---

## 1) WebSocket Frames

### 1.1 Client → Serveur
```json
{ "type": "chat.message", "payload": {
    "text": "…", "agent_id": "anima|neo|nexus",
    "thread_id": "uuid", "use_rag": true,
    "metadata": { "documents": ["doc-id"], "origin": "ui|retry" }
} }
{ "type": "debate:create", "payload": {
    "topic": "…", "agent_order": ["anima","neo"],
    "rounds": 3, "use_rag": false, "thread_id": "uuid?"
} }
{ "type": "memory:refresh", "payload": { "thread_id": "uuid?", "mode": "stm|ltm|full" } }
```

### 1.2 Serveur → Client
```json
{ "type": "ws:session_established", "payload": { "session_id": "…" } }
{ "type": "ws:auth_required", "payload": { "reason": "missing_or_invalid_token" } }
{ "type": "ws:chat_stream_start", "payload": { "agent_id": "anima", "thread_id": "uuid" } }
{ "type": "ws:chat_stream_chunk", "payload": { "id": "…", "content": "delta" } }
{ "type": "ws:chat_stream_end", "payload": {
    "id": "…", "session_id": "…", "role": "assistant",
    "agent": "anima", "content": "final text",
    "meta": { "provider": "openai|anthropic|google|memory",
               "model": "…", "fallback": false,
               "rag_sources": [{ "document_id": "…", "chunk_id": "…", "score": 0.76 }],
               "memory": { "stm": true, "ltm_items": 3 }
    }
} }
{ "type": "ws:model_info", "payload": { "provider": "openai", "model": "gpt-4o-mini" } }
{ "type": "ws:model_fallback", "payload": { "from_provider": "anthropic", "to_provider": "openai", "reason": "quota" } }
{ "type": "ws:memory_banner", "payload": { "agent_id": "anima", "has_stm": true, "ltm_items": 3, "injected_into_prompt": true } }
{ "type": "ws:analysis_status", "payload": { "status": "running|done|error", "thread_id": "uuid?", "summary_id": "…" } }
{ "type": "ws:debate_status_update", "payload": { "round": 1, "agent": "neo", "status": "speaking" } }
{ "type": "ws:debate_result", "payload": { "topic": "…", "summary": "…", "cost": { "total_usd": 0.12 } } }
{ "type": "ws:error", "payload": { "message": "…", "code": "rate_limited|internal_error" } }
```

---

## 2) REST Endpoints majeurs

### Threads & messages
- `GET /api/threads?type=chat&limit=1` → `{ items:[{id,type,created_at,last_message_at}] }`
- `POST /api/threads` → crée un thread chat (payload optionnel `{ "type": "chat", "title": "…" }`).
- `GET /api/threads/{id}/messages?limit=50&before=cursor` → pagination descendante, messages `{ id, role, agent, content, created_at, rag_sources[] }`.
- `POST /api/threads/{id}/messages` → fallback REST si WS indispo (`{ text, agent_id, use_rag }`).
- `POST /api/threads/{id}/documents` → associe documents (`{ document_ids: [] }`).

### Mémoire
- `POST /api/memory/tend-garden` (`{ thread_id?, mode? }`) → 202 + job async ; renvoie état courant (`{ status, last_run_at, summary_id }`).
- `GET /api/memory/tend-garden` → état consolidé (`{ summaries: [], facts: [], ltm_count }`).
- `POST /api/memory/clear` (`{ scope: "stm|ltm|all", thread_id? }`) → 200 + compte rendu (`{ removed_stm: 1, removed_ltm: 12 }`).

### Documents
- `GET /api/documents` → `{ total, items:[{id,name,size,state,tokens,created_at}] }`.
- `POST /api/documents/upload` (multipart) → 201 (`{ id, name, chunks }`).
- `DELETE /api/documents/{id}` → 204 (purge embeddings + metadata).

### Dashboard / coûts
- `GET /api/dashboard/costs/summary` → `{ day, week, month, total, sessions, documents }`.

### Débats
- `POST /api/debates/export` → export texte d’un débat (`{ debate_id }`).

---

## 3) Erreurs & codes
- `401` : token manquant/invalide.
- `403` : deny-list / accès interdit.
- `409` : upload document dupliqué ou thread déjà associé.
- `422` : payload invalide (topic trop court, extension non supportée).
- `500` : erreur interne (ex: clé IA absente) → `ws:error` miroir côté temps réel.
