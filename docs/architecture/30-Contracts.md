# ÉMERGENCE — Contrats d’API internes (WS + REST)
> V4.0 — Aligné architecture multi-agents + mémoire progressive.

## 0) Principes
- Tous les échanges utilisent `{ "type": string, "payload": object }`.
- Les événements serveur sont préfixés `ws:` ; les erreurs critiques côté serveur déclenchent `ws:error` + log.
- Auth : JWT local (allowlist email, HS256) obligatoire (header `Authorization: Bearer <JWT>`). Mode dev : ID token Google ou header `X-User-Id` quand `AUTH_DEV_MODE=1`.

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
{ "type": "ws:memory_banner", "payload": { "agent_id": "anima", "has_stm": true, "ltm_items": 3, "ltm_injected": 3, "ltm_candidates": 3, "ltm_skipped": false, "injected_into_prompt": true } }
- `ltm_injected` représente le nombre d'éléments effectivement injectés dans le prompt.
- `ltm_candidates` conserve le total d'éléments rappelés depuis le vector store (équivalent de `ltm_items`).
- `ltm_skipped` devient `true` lorsque des souvenirs ont été rappelés mais non injectés (ex: mode RAG actif); un log backend et un toast UI sont émis pour signaler la situation.
{ "type": "ws:analysis_status", "payload": { "status": "running|done|error", "thread_id": "uuid?", "summary_id": "…" } }
{ "type": "ws:debate_status_update", "payload": { "stage": "round_attacker", "status": "speaking", "round": 1, "agent": "neo", "role": "attacker", "message": "Tour 1 - Neo intervient.", "topic": "..." } }
{ "type": "ws:debate_turn_update", "payload": { "round": 1, "agent": "neo", "text": "Ouverture du debat", "speaker": "attacker", "meta": { "role": "attacker", "provider": "anthropic", "model": "claude-neo", "fallback": false, "cost": { "total_cost": 0.0105, "input_tokens": 100, "output_tokens": 48 } } } }
{ "type": "ws:debate_result", "payload": {
    "topic": "…",
    "status": "completed",
    "stage": "completed",
    "turns": [
      { "round": 1, "agent": "neo", "text": "…", "meta": { "role": "attacker", "provider": "anthropic", "model": "claude-neo", "fallback": false, "cost": { "total_cost": 0.0105, "input_tokens": 100, "output_tokens": 48 } } },
      { "round": 1, "agent": "nexus", "text": "…", "meta": { "role": "challenger", "provider": "anthropic", "model": "claude-nexus", "fallback": false, "cost": { "total_cost": 0.0210, "input_tokens": 120, "output_tokens": 60 } } }
    ],
    "synthesis": "…",
    "synthesis_meta": { "role": "mediator", "provider": "anthropic", "model": "claude-anima", "fallback": false, "cost": { "total_cost": 0.0158, "input_tokens": 150, "output_tokens": 76 } },
    "cost": { "total_usd": 0.0473, "tokens": { "input": 370, "output": 184 }, "by_agent": { "neo": { "usd": 0.0105, "input_tokens": 100, "output_tokens": 48 }, "nexus": { "usd": 0.0210, "input_tokens": 120, "output_tokens": 60 }, "anima": { "usd": 0.0158, "input_tokens": 150, "output_tokens": 76 } } }
  } }
{ "type": "ws:error", "payload": { "message": "…", "code": "rate_limited|internal_error" } }
```

- `ws:debate_turn_update.payload.meta` expose le role declare, le fournisseur LLM, le modele choisi, le flag fallback et le cout granularise (`total_cost`, `input_tokens`, `output_tokens`).
- `ws:debate_result.cost` resume le cout total (`total_usd`), les tokens injectes/produits et la repartition `by_agent`.

---

## 2) REST Endpoints majeurs

- `POST /api/auth/login` -> 200 `{ token, expires_at, role, session_id, email }` (body `{ email, password, meta? }`). `Set-Cookie` renvoie `id_token` + `emergence_session_id` avec `SameSite=Lax`. 401 si identifiants invalides ou email hors allowlist, 429 si rate-limit depasse, 423 si compte revoque.
- POST /api/auth/dev/login -> 200 { token, expires_at, role, session_id, email } (body optionnel { email? }, accessible uniquement si AUTH_DEV_MODE=1; 404 sinon).
- `POST /api/auth/logout` -> 204 (idempotent). Payload optionnel `{ session_id }` pour marquer la session `revoked_at`. Réponse: `Set-Cookie` vide (`id_token=`, `emergence_session_id=`) avec `Max-Age=0` et `SameSite=Lax` pour forcer la purge navigateur.
- `GET /api/auth/session` -> 200 `{ email, role, expires_at, issued_at }` (verifie token courant).
- `GET /api/auth/admin/allowlist` -> 200 `{ items:[...], total, page, page_size, has_more, status, query }` (paramètres `status=active|revoked|all`, `search`, `page`, `page_size`; compat hérité `include_revoked=true`).
- `POST /api/auth/admin/allowlist` -> 201 `{ entry:{ email, role, note, password_updated_at? }, clear_password?, generated }`. Payload: `{ email, role?, note?, password?, generate_password? }` (mot de passe >= 8 caracteres si fourni; `generate_password=true` renvoie le secret en clair une seule fois et journalise `allowlist:password_generated`).
- `DELETE /api/auth/admin/allowlist/{email}` -> 204 (suppression).
- `GET /api/auth/admin/sessions` -> 200 `{ items:[{ id, email, ip, issued_at, expires_at, revoked_at }] }`.
- `POST /api/auth/admin/sessions/revoke` -> 200 `{ updated:1 }` (révoque `id`).

### Threads & messages
- `GET /api/threads?type=chat&limit=1` → `{ items:[{id,type,created_at,last_message_at}] }`
- `POST /api/threads` → crée un thread chat (payload optionnel `{ "type": "chat", "title": "…" }`).
- `DELETE /api/threads/{id}` → 204 (cascade: messages + documents associés).
- `GET /api/threads/{id}/messages?limit=50&before=cursor` → pagination descendante, messages `{ id, role, agent, content, created_at, rag_sources[] }`.
- `POST /api/threads/{id}/messages` → fallback REST si WS indispo (`{ text, agent_id, use_rag }`).
- `POST /api/threads/{id}/documents` → associe documents (`{ document_ids: [] }`).

### Mémoire
- `POST /api/memory/tend-garden` (`{ thread_id?, mode? }`) → 202 + job async ; renvoie état courant (`{ status, last_run_at, summary_id }`).
- `GET /api/memory/tend-garden` → état consolidé (`{ status: "ok", summaries: [...], facts: [], ltm_count, total }`).
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

---

## 4) Auth tokens
- JWT HS256 (`iss=emergence.local`, `aud=emergence-app`, `sub=sha256(email)`, `exp=issued_at+7j`).
- Claim `role` (`tester` par défaut, `admin` si email dans `LOCAL_AUTH_ADMIN_EMAILS`).
- Header `Authorization: Bearer <token>` partagé REST/WS; WebSocket subprotocol `jwt`.
- Révocation : `auth_sessions.revoked_at` + liste en mémoire purgée toutes les 5 minutes.
- Les claims enrichis exposent `session_revoked` et `revoked_at` le cas échéant; le handshake WS refuse une session révoquée.
- OTP futur : champs réservés (`otp_secret`, `otp_expires_at`, `otp_channel`) pour SMS/OTP; routes resteront compatibles.





