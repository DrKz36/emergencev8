# ÉMERGENCE — Contrats d’API internes (WS + REST)
> V3.2 — Aligné UI/Back : frames WS exhaustives, payloads typés, compat héritage.

## 0) Principe
- **Client → Serveur** : `type` + `payload`.
- **Serveur → Client** : `type` + `payload`. Les événements WS sont **namespacés** `ws:*`.

---

## 1) WebSocket Frames

### 1.1 Outbound (Client → Serveur)

#### Chat (message utilisateur)
```json
{ "type": "chat.message",
  "payload": { "text": "…", "agent_id": "anima|neo|nexus", "use_rag": false } }
{ "type": "debate:create",
  "payload": { "topic": "…", "agent_order": ["anima","neo","nexus"], "rounds": 3, "use_rag": false } }
- JWT gating + ws:chat_stream_start/… + model_info/fallback + memory_banner (front)
{ "type": "ws:session_established", "payload": { "session_id": "…" } }
{ "type": "ws:auth_required", "payload": { "message": "Authentication required", "reason": "missing_or_invalid_token" } }
{ "type": "ws:chat_stream_start", "payload": { "agent_id": "anima" } }
{ "type": "ws:chat_stream_chunk", "payload": { "id": "…", "content": "delta" } }
{ "type": "ws:chat_stream_end",
  "payload": { "id": "…", "session_id": "…", "role": "assistant",
               "agent": "anima", "content": "final text",
               "meta": { "provider": "openai|anthropic|google|memory",
                         "model": "…", "fallback": false } } }
{ "type": "ws:model_info", "payload": { "provider": "openai", "model": "gpt-4o-mini" } }
{ "type": "ws:model_fallback", "payload": { "from_provider": "anthropic", "from_model": "haiku",
                                            "to_provider": "openai", "to_model": "gpt-4o-mini",
                                            "reason": "quota|latency|error" } }
{ "type": "ws:memory_banner",
  "payload": { "agent_id": "anima", "has_stm": true, "ltm_items": 3, "injected_into_prompt": true } }
{ "type": "ws:rag_status", "payload": { "status": "searching|found|idle", "agent_id": "…" } }
{ "type": "ws:debate_status_update", "payload": { "status": "…", "topic": "…" } }
{ "type": "ws:debate_result", "payload": { "topic": "…", "summary": "…", "cost": { } } }
{ "type": "ws:error", "payload": { "message": "…" } }
- ws:session_established / auth_required (serveur)
- model_info / model_fallback / chat_stream_* / memory_banner / rag_status (front consomme)
