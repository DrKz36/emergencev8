# ÉMERGENCE — Séquences (User Journeys)

## 1) Chat temps réel (Bootstrap → WS → Agents → Persist)
1. Front : `ensureAuth()` (GIS) → ID token (ou `AUTH_DEV_MODE`).
2. Front : `ensureCurrentThread()` → `GET /api/threads?type=chat&limit=1` ; crée (`POST /api/threads`) si vide, hydrate `state.threads.map` via `GET /api/threads/{id}/messages?limit=50`.
3. Front : ouverture WS `wss:///ws/{session_id}` (sub-proto `jwt` + token) → écoute `ws:session_established`.
4. Front : envoi `{type:"chat.message", payload:{text, agent_id, use_rag, thread_id}}` ; watchdog REST (`POST /api/threads/{id}/messages`) si `ws:chat_stream_start` ne survient pas en 1,5 s.
5. Back : `ChatService` persiste message, enrichit prompt (mémoire STM/LTM + RAG si activé), appelle modèles (fallback Google → Anthropic → OpenAI).
6. Back : stream `ws:chat_stream_start/chunk/end`, `ws:model_info`, `ws:model_fallback`, `ws:memory_banner`, `ws:rag_status`.
7. Front : intègre chunks, affiche sources RAG, met à jour métriques; REST `GET /api/threads/{id}/messages` pour pagination.

## 2) Mémoire (Analyse → Consolidation → Clear)
1. Front : utilisateur clique `Analyser` → `POST /api/memory/tend-garden` (payload optionnel `thread_id`).
2. Back : `MemoryGardener` agrège historique (global ou thread), `MemoryAnalyzer` produit résumé/faits/concepts via LLM, persiste en base et vectorise (Chroma).
3. Back : notifie via `ws:analysis_status` + `ws:memory_banner` (STM/LTM injectées).
4. Front : badges mémoire mis à jour; `GET /api/memory/tend-garden` disponible pour vérifier l’état courant.
5. Clear : `POST /api/memory/clear` → purge STM + items LTM filtrés par session/agent, notifie WS.

## 3) Documents (Upload → Indexation → Utilisation RAG)
1. Front : drop/upload → `POST /api/documents/upload` (FormData).
2. Back : `DocumentService` valide extension (`.pdf|.txt|.docx`), parse, chunk, vectorise, persiste métadonnées.
3. Back : répond `201` + déclenche rafraîchissement (`GET /api/documents`).
4. Front : `DocumentsModule` met à jour liste + quotas; `ChatModule` peut lier `document_ids` au thread.
5. RAG : lors du chat, `ChatService` interroge `VectorService` pour récupérer passages pertinents (filtre thread/doc), inclut sources dans `ws:chat_stream_end`.

## 4) Débat multi-agents
1. Front : configure débat → envoie `{type:"debate:create"}` (topic, agents, rounds, `use_rag`).
2. Back : `DebateService` crée session interne, boucle sur les agents (isolation contextuelle), invoque `ChatService` pour chaque tour.
3. Back : publie `ws:debate_status_update` pour chaque round + `ws:debate_result` (synthèse, coûts).
4. Front : affiche tours, synthèse, permet export.

## 5) Dashboard & coûts
1. Front : `DashboardModule` → `GET /api/dashboard/costs/summary`.
2. Back : `DashboardService` agrège coûts, sessions, documents.
3. Front : rend cartes (jour/semaine/mois/total) + monitoring ; rafraîchissement manuel possible.
