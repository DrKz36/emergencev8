# ÉMERGENCE — Contrats d’API internes (WS + REST)
> V4.0 — Aligné architecture multi-agents + mémoire progressive.

## 0) Principes
- Note maintenance (2025-11-20) : les healthchecks peuvent etre joints via `/ready` ou `/api/monitoring/health` selon l'origine frontend (Vite dev) ; pas de changement de payload.
- Tous les échanges utilisent `{ "type": string, "payload": object }`.
- Les événements serveur sont préfixés `ws:` ; les erreurs critiques côté serveur déclenchent `ws:error` + log.
- Auth : JWT local (allowlist email, HS256) obligatoire (header `Authorization: Bearer <JWT>`). Le mode dev (local uniquement) tolère un ID token Google ou l'entête `X-User-Id` quand `AUTH_DEV_MODE=1`; en production le flag vaut 0 et les bypass répondent 404.
- _Note maintenance 2025-10-29:_ nettoyage Ruff sur `manager_postgres.py` (aucun contrat REST/WS modifié).

---

## 1) WebSocket Frames

### 1.1 Client → Serveur
```json
{ "type": "chat.message", "payload": {
    "text": "…", "agent_id": "anima|neo|nexus",
    "thread_id": "uuid", "use_rag": true,
    "metadata": { "documents": ["doc-id"], "origin": "ui|retry" }
} }
{ "type": "chat.opinion", "payload": {
    "target_agent_id": "anima|neo|nexus",
    "source_agent_id": "anima|neo|nexus",
    "message_id": "uuid", "message_text": "…"
} }
{ "type": "debate:create", "payload": {
    "topic": "…", "agent_order": ["anima","neo"],
    "rounds": 3, "use_rag": false, "thread_id": "uuid?"
} }
{ "type": "memory:refresh", "payload": { "thread_id": "uuid?", "mode": "stm|ltm|full" } }
```
- `chat.opinion` : le client WebSocket applique une fenetre de 1,2 s pour ignorer les duplicatas (meme cible/message/texte) et le router backend bloque une requete si l'historique contient deja la note correspondante.

### 1.2 Serveur → Client
```json
{ "type": "ws:session_established", "payload": { "session_id": "…" } }
{ "type": "ws:auth_required", "payload": { "reason": "missing_or_invalid_token" } }
{ "type": "ws:chat_stream_start", "payload": { "agent_id": "anima", "thread_id": "uuid", "meta": { "opinion": { "of_message_id": "uuid", "source_agent_id": "neo", "reviewer_agent_id": "anima", "request_note_id": "uuid" } } } }
{ "type": "ws:chat_stream_chunk", "payload": { "id": "…", "content": "delta" } }
{ "type": "ws:chat_stream_end", "payload": {
    "id": "…", "session_id": "…", "role": "assistant",
    "agent": "anima", "content": "final text",
    "meta": { "provider": "openai|anthropic|google|memory",
               "model": "…", "fallback": false,
               "rag_sources": [{ "document_id": "…", "chunk_id": "…", "score": 0.76 }],
               "memory": { "stm": true, "ltm_items": 3 },
               "opinion": { "of_message_id": "uuid", "source_agent_id": "neo", "reviewer_agent_id": "anima", "request_note_id": "uuid" }
    }
} }
{ "type": "ws:model_info", "payload": { "provider": "openai", "model": "gpt-4o-mini" } }
{ "type": "ws:model_fallback", "payload": { "from_provider": "anthropic", "to_provider": "openai", "reason": "quota" } }
{ "type": "ws:memory_banner", "payload": { "agent_id": "anima", "has_stm": true, "ltm_items": 3, "ltm_injected": 3, "ltm_candidates": 3, "ltm_skipped": false, "injected_into_prompt": true } }
- `ltm_injected` représente le nombre d'éléments effectivement injectés dans le prompt.
- `ltm_candidates` conserve le total d'éléments rappelés depuis le vector store (équivalent de `ltm_items`).
- `ltm_skipped` devient `true` lorsque des souvenirs ont été rappelés mais non injectés (ex: mode RAG actif); un log backend et un toast UI sont émis pour signaler la situation.
- `meta.opinion` est présent uniquement pour les réponses d'avis et expose `of_message_id` (message évalué), `source_agent_id`, `reviewer_agent_id` (agent qui commente) et `request_note_id` (note locale liée à la demande).
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
- POST /api/auth/dev/login -> 200 { token, expires_at, role, session_id, email } (exposé pour le debug local quand `AUTH_DEV_MODE=1`; en staging/prod le flag vaut 0 et la route renvoie 404).
- `POST /api/auth/logout` -> 204 (idempotent). Payload optionnel `{ session_id }` pour marquer la session `revoked_at`. Réponse: `Set-Cookie` vide (`id_token=`, `emergence_session_id=`) avec `Max-Age=0` et `SameSite=Lax` pour forcer la purge navigateur.
- `GET /api/auth/session` -> 200 `{ email, role, expires_at, issued_at }` (verifie token courant).
- `GET /api/auth/admin/allowlist` -> 200 `{ items:[...], total, page, page_size, has_more, status, query }` (paramètres `status=active|revoked|all`, `search`, `page`, `page_size`; compat hérité `include_revoked=true`).
- `POST /api/auth/admin/allowlist` -> 201 `{ entry:{ email, role, note, password_updated_at? }, clear_password?, generated }`. Payload: `{ email, role?, note?, password?, generate_password? }` (mot de passe >= 8 caracteres si fourni; `generate_password=true` renvoie le secret en clair une seule fois et journalise `allowlist:password_generated`).
- `DELETE /api/auth/admin/allowlist/{email}` -> 204 (suppression).
- `GET /api/auth/admin/sessions` -> 200 `{ items:[{ id, email, ip, issued_at, expires_at, revoked_at }] }`.
- `POST /api/auth/admin/sessions/revoke` -> 200 `{ updated:1 }` (révoque `id`).
- `GET /api/admin/analytics/threads` -> 200 `{ threads:[...], total }` (admin seulement). Retourne tous les threads de conversation actifs avec détails (user_id, email, role, timestamps, durée, statut actif). **Note** : Renvoie des THREADS (table `sessions`), pas des sessions d'auth JWT (voir `/api/auth/admin/sessions` pour ça).

### Threads & messages
- `GET /api/threads?type=chat&limit=1` → `{ items:[{id,type,created_at,last_message_at,message_count,archival_reason,archived_at}] }`
- `POST /api/threads` → crée un thread chat (payload optionnel `{ "type": "chat", "title": "…" }`).
- `DELETE /api/threads/{id}` → 204 (cascade: messages + documents associés).
- `GET /api/threads/{id}/messages?limit=50&before=cursor` → pagination descendante, messages `{ id, role, agent, content, created_at, rag_sources[] }`.
- `POST /api/threads/{id}/messages` → fallback REST si WS indispo (`{ text, agent_id, use_rag }`).
- `POST /api/threads/{id}/documents` → associe documents (`{ document_ids: [] }`).

### Monitoring et Healthchecks
- `GET /api/monitoring/health` → 200 `{ status: "healthy", timestamp, version }` (version: `beta-2.1.3`)
- `GET /api/monitoring/health/detailed` → 200 `{ status, timestamp, system: { platform, python_version, cpu_percent, memory, disk } }`
- `GET /api/system/info` → 200 Informations système complètes pour About page
  ```json
  {
    "version": { "backend": "beta-2.1.3", "python": "3.11.5", "environment": "production" },
    "platform": { "system": "Linux", "release": "5.15.0", "machine": "x86_64" },
    "resources": { "cpu_percent": 12.4, "memory": {...}, "disk": {...} },
    "uptime": { "seconds": 3628800, "formatted": "42 days, 0 hours", "started_at": "..." },
    "services": { "database": {...}, "vector_service": {...}, "llm_providers": {...} },
    "timestamp": "..."
  }
  ```
  Version backend via `BACKEND_VERSION` env var (défaut: `beta-2.1.3`), synchronisée avec `package.json` et `index.html`.

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
- `GET /api/benchmarks/results` → nécessite un token utilisateur ; accepte `scenario_id`/`limit` et renvoie les matrices triées par `created_at` avec `summary` agrégé (succès, coûts, latence) et la liste complète des `runs`. Fallback SQLite automatique si Firestore est absent ou si `EDGE_MODE=1`.
- `GET /api/benchmarks/scenarios` → catalogue des scénarios disponibles (défaut ARE|Gaia2) enrichi avec `success_threshold`, `base_cost`, `tasks`. Peut être surchargé via `BENCHMARKS_SCENARIO_INDEX`.
- `POST /api/benchmarks/run` → 202 + `{ matrix }`, déclenche un run synchrone de la matrice demandée. Accès admin requis (`require_admin_claims`).
- `POST /api/benchmarks/metrics/ndcg-temporal` → Calcule la métrique **nDCG@k temporelle** pour évaluer la qualité d'un classement avec pénalisation temporelle exponentielle. Nécessite un token utilisateur. Payload : `{ ranked_items: [{ rel: float, ts: datetime }], k: int (défaut 10), now?: datetime, T_days?: float (défaut 7.0), lam?: float (défaut 0.3) }`. Retourne `{ "ndcg_time@k": float [0-1], k: int, num_items: int, parameters: { T_days, lambda } }`. Utilisé pour mesurer l'impact des boosts de fraîcheur/entropie dans le moteur de ranking.
> Persistance cloud : activer `EMERGENCE_FIRESTORE_PROJECT` + credentials Google (ou `GOOGLE_APPLICATION_CREDENTIALS`) pour répliquer les résultats dans Firestore ; sinon seul SQLite est alimenté.

### Débats
<!-- Feature export débats : reportée à Phase P3+ selon roadmap -->

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

---

## 6) Voice API Endpoints (TTS/STT avec ElevenLabs + Whisper)

### REST Endpoints

- `POST /api/voice/tts` → **Génération audio TTS (Text-to-Speech)**
  - **Auth:** JWT Bearer token requis
  - **Body:** `{ "text": "Texte à synthétiser" }`
  - **Retourne:** Stream audio/mpeg (MP3)
  - **Headers response:**
    - `Content-Type: audio/mpeg`
    - `Content-Disposition: inline`
    - `Cache-Control: no-cache`
  - **Provider:** ElevenLabs API (model: `eleven_multilingual_v2`, voice: `ohItIVrXTBI80RrUECOD`)
  - **Erreurs:**
    - 400 si texte vide
    - 503 si VoiceService indisponible
    - 500 si génération TTS échoue

### WebSocket Endpoints

- `WS /api/voice/ws/{agent_name}?session_id=<uuid>` → **Interaction vocale bi-directionnelle**
  - **Auth:** JWT via query param ou header
  - **Flow:**
    1. Client envoie bytes audio (format: webm/opus)
    2. Serveur transcrit via Whisper (`transcribe_audio`)
    3. Serveur génère réponse LLM via ChatService
    4. Serveur synthétise réponse via ElevenLabs
    5. Serveur stream audio MP3 au client
  - **Messages serveur:**
    - `{ "type": "text", "data": "réponse textuelle" }` - Réponse LLM
    - `{ "type": "audio", "data": bytes }` - Chunks audio MP3
    - `{ "type": "error", "data": "message d'erreur" }` - Erreur serveur
  - **Erreurs:**
    - 4401 si auth échoue
    - Fermeture propre si client déconnecte
  - **Note:** WebSocket vocal non encore utilisé par l'UI (prévu pour v3.4+)

### Configuration (.env)

```
ELEVENLABS_API_KEY=sk_...
ELEVENLABS_VOICE_ID=ohItIVrXTBI80RrUECOD  # Voix française naturelle
ELEVENLABS_MODEL_ID=eleven_multilingual_v2
OPENAI_API_KEY=sk-proj-...  # Pour Whisper STT
```

---

## 7) Gmail API Endpoints (Phase 3 Guardian Cloud)

### OAuth Flow (Admin uniquement)

- `GET /auth/gmail` → **Initie OAuth2 flow Gmail**
  - Redirect vers Google consent screen
  - Demande scope `gmail.readonly` (lecture seule)
  - Retourne 302 redirect vers `https://accounts.google.com/o/oauth2/auth`

- `GET /auth/callback/gmail?code=...` → **Callback OAuth2**
  - Échange `code` contre tokens OAuth (access_token + refresh_token)
  - Stocke tokens dans Firestore (collection `gmail_oauth_tokens`, document `admin`)
  - Tokens encrypted at rest (Firestore security)
  - Retourne 200 `{ success: true, message: "Gmail OAuth authentication successful!", next_step: "..." }`
  - Erreur: 400 si `error` param ou `code` manquant
  - Erreur: 500 si échange token échoue

### API Codex (lecture rapports Guardian)

- `GET /api/gmail/read-reports` → **Lire emails Guardian pour Codex GPT**
  - **Auth:** Header `X-Codex-API-Key: <secret>` (API key stockée dans Secret Manager GCP)
  - **Query params (optionnel):** `max_results=10`
  - **Query Gmail:** `subject:(emergence OR guardian OR audit)` (emails Guardian uniquement)
  - **Retourne:** 200 `{ success: true, count: 3, emails: [...] }`
    - Chaque email: `{ id, subject, from, date, timestamp, body, snippet }`
    - `body`: HTML ou plaintext (décodé base64url)
  - **Erreurs:**
    - 401 si API key invalide
    - 500 si OAuth tokens manquants ou expirés (relancer OAuth flow)
    - 500 si Gmail API quota exceeded

### Status OAuth

- `GET /api/gmail/status` → **Vérifier status OAuth Gmail**
  - **Pas d'auth requise** (endpoint public pour debug)
  - Retourne 200 `{ authenticated: true|false, message: "...", scopes?: [...] }`
  - Si `authenticated: false`, message indique `/auth/gmail` requis

### Variables env requises

```bash
CODEX_API_KEY=<secret>  # API key Codex (Secret Manager: codex-api-key)
GCP_PROJECT_ID=emergence-469005  # Pour Secret Manager
```

### Sécurité

- ✅ OAuth scope readonly uniquement (aucune modification emails)
- ✅ Tokens Gmail stockés Firestore (encrypted at rest)
- ✅ Auto-refresh tokens expirés (refresh_token persist)
- ✅ Credentials OAuth depuis Secret Manager (gmail-oauth-client-secret)
- ✅ API key Codex depuis Secret Manager (codex-api-key)
- ✅ HTTPS obligatoire (TLS 1.3)

### Workflow Codex

1. **Polling**: POST `/api/gmail/read-reports` (toutes les 2h)
2. **Parse**: Extract erreurs depuis HTML Guardian report
3. **Auto-fix**: Créer branche Git + commit + PR GitHub
4. **Notify**: Slack/Email confirmation

**Voir:** `docs/GMAIL_CODEX_INTEGRATION.md` pour doc complète Codex GPT.

