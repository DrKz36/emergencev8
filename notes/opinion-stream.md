# Opinion Stream Log

## 2025-10-03 / Session aa327d90-3547-4396-a409-f565182db61a
- thread_id: 7f3c7aa6f2b2403dade4abf8623041ed
- payload.message_text: "Reponseinitiale" (accent dropped, spacing lost)
- frontStored.message.content: "Reponseinitiale" (matches mutated payload)
- server message (GET /api/threads/{id}): "Reponse initiale" (accent should be on first E)
- note: corruption reproduced on front; backend payload remains intact.
## 2025-10-04 / Session 9fbaf850-b107-4cac-921b-8c8d4ae25a41
- Added OpenAI stream instrumentation in `src/backend/features/chat/service.py:598` to log the raw `delta.content` object; first captures show the provider emits a list payload, not a plain string.
- The first backend mutation happens in `_compute_chunk_delta` (`src/backend/features/chat/service.py:1774`) which coerces `raw_chunk` to `str(...)`, producing the truncated text seen in `chunk_debug primary raw` before persistence.
- TODO next run: collect paired logs (provider vs. `chunk_debug`) on the same session to confirm the provider text stays intact, then replace the `str(...)` cast with a join over content parts.
- Applied Option 1 fix: `_normalize_openai_delta_content` now flattens OpenAI delta parts before streaming; `_get_openai_stream` yields the joined string and only logs raw content at debug level.
- Added regression test `tests/backend/features/test_chat_service_openai_delta_normalization.py` to lock the behavior (covers list of content parts, dict payloads, str/None fallbacks).
- Adjusted `_compute_chunk_delta` to remove over-aggressive duplicate dropping; now only skips suffix repeats and merges overlapping chunks so intermediate tokens (e.g. "re d'un") persist. Added dedicated tests in `tests/backend/features/test_chat_stream_chunk_delta.py`.

## 2025-10-05 / Session pending-id
- Backend router `_history_has_opinion_request` now checks for paired user notes + assistant reviews before deduping; regression cases live in `tests/backend/features/test_chat_router_opinion_dedupe.py` and cover mixed Anima/Neo/Nexus flows plus `ChatMessage`-style objects.
- Frontend `ChatModule` routes `ws:error` with `code=opinion_already_exists` to a toast, dedupes repeated stream chunks, and keeps last chunk caches when ids change; `src/frontend/features/chat/__tests__/chat-opinion.flow.test.js` locks retries-before-response and toast fallbacks.
- Opinion debug instrumentation removed from the frontend; no `[OpinionDebug]` output remains in standard builds.

### WebSocket Error Matrix (ws:error)

**Backend sources** (`router.py` + `service.py`):
| Location | Code | Message | Trigger |
|----------|------|---------|---------|
| router.py:262 | - | "Message WebSocket incomplet (type/payload)." | Missing type/payload in WS frame |
| router.py:296 | - | "Débat: 'topic' manquant ou invalide." | debate:create without valid topic |
| router.py:311 | - | "Débat: 'agent_order' ≥ 2 agents requis." | debate:create agent_order < 2 |
| router.py:322 | - | "Débat: 'rounds' doit être un entier ≥ 1." | debate:create rounds < 1 |
| router.py:360 | - | f"Type débat inconnu: {message_type}" | Unknown debate:* subtype |
| router.py:371 | - | f"Erreur débat: {e}" | Exception during debate processing |
| router.py:389 | - | "chat.message: 'text' et 'agent_id' requis." | chat.message missing text/agent_id |
| router.py:472 | - | f"chat.message erreur: {e}" | Exception during chat.message |
| router.py:509 | - | "chat.opinion: 'target_agent_id' et 'message_id' requis." | chat.opinion missing required fields |
| router.py:539 | **opinion_already_exists** | "Avis déjà disponible pour cette réponse." | Duplicate opinion request detected in history |
| router.py:561 | - | f"chat.opinion erreur: {e}" | Exception during chat.opinion |
| router.py:571 | - | f"Type inconnu: {message_type}" | Unknown message type (fallback) |
| service.py:1339 | - | f"Erreur interne pour l'agent {agent_id}: {e}" | Streaming exception |
| service.py:1648 | - | f"Agent {target_agent_id!r} indisponible pour un avis." | Invalid opinion target agent |
| service.py:1675 | - | "Impossible de récupérer la réponse à analyser." | Opinion message_text empty/not found |

**Frontend handling** (`chat.js:763-785`):
- `code=opinion_already_exists` → toast avec message custom (ligne 774-776)
- Autres codes → toast avec `payload.message` (ligne 779-780)
- Tous les `ws:error` sont loggés en `console.warn` (ligne 769/771)

**Documentation** ([30-Contracts.md:71](c:\dev\emergenceV8\docs\architecture\30-Contracts.md#L71)):
```json
{ "type": "ws:error", "payload": { "message": "…", "code": "rate_limited|internal_error" } }
```
→ Les codes `rate_limited|internal_error` mentionnés dans la spec ne sont pas encore implémentés côté backend

**TODO** :
- [ ] Ajouter métriques/telemetry pour les `ws:error` (compteur par code/message_type)
- [ ] Implémenter les codes manquants : `rate_limited`, `internal_error`
- [ ] Standardiser le format : tous les `ws:error` devraient avoir un `code` (actuellement seul `opinion_already_exists` l'expose)

### Integration tests
- `tests/backend/integration/test_ws_opinion_flow.py` : tests intégration du flux opinion avec détection de duplicata
  - `test_opinion_flow_with_duplicate_detection` : vérifie que le 2e avis identique → `ws:error` avec `code=opinion_already_exists`
  - `test_opinion_different_targets_not_duplicate` : vérifie que les avis pour des cibles différentes ne sont pas considérés comme duplicata
  - Simule le cycle complet : note USER + réponse ASSISTANT + vérification `_history_has_opinion_request`

---

## Passation / Review notes (2025-10-05)

### Résumé de la branche `fix/debate-chat-ws-events-20250915-1808`

**Objectif** : Corriger la déduplication des opinions + normalisation des chunks OpenAI + gestion d'erreurs WS

**Commits clés** :
1. `9119e0a` - fix: tighten opinion dedupe flow (backend router + frontend cache)
2. `27a2f63` - fix: normalize streaming chunks (OpenAI delta parts)
3. `86358ec` - docs: add ws:error matrix and integration tests

**Changements backend** :
- `router.py` : `_history_has_opinion_request` détecte les paires note+réponse (pas juste les notes isolées)
- `service.py` : normalisation des deltas OpenAI avec `_normalize_openai_delta_content`
- `ws:error` avec `code=opinion_already_exists` envoyé sur duplicata opinion

**Changements frontend** :
- `chat.js` : `handleWsError` route `opinion_already_exists` vers toast
- Déduplication chunks répétés avec `_lastChunkByMessage` cache
- `_findOpinionArtifacts` recherche note+réponse dans le DOM

**Tests** :
- ✅ `test_chat_router_opinion_dedupe.py` (3 tests backend)
- ✅ `test_ws_opinion_flow.py` (2 tests intégration)
- ✅ `chat-opinion.flow.test.js` (4 tests frontend)
- ✅ `npm run build` OK

**Documentation** :
- `notes/opinion-stream.md` : matrice complète des 15 points d'émission `ws:error`
- `30-Contracts.md` : spec existante `{ code: "rate_limited|internal_error" }` non implémentée

**Métriques** :
- 0 régression sur les tests existants
- +5 nouveaux tests (2 intégration, 3 dedupe)
- Couverture opinion flow : note creation → duplicate detection → toast UI

**Prochaines étapes suggérées** :
1. ✅ Merge dans `main` après revue
2. 📊 Implémenter métriques/telemetry pour `ws:error` (compteur par code)
3. 🔧 Standardiser : tous les `ws:error` devraient avoir un `code` (actuellement 1/15)
4. 🚀 Ajouter codes manquants : `rate_limited`, `internal_error`
