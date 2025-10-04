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
