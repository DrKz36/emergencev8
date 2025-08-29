# ÉMERGENCE — Séquences (User Journeys)

## 1) Chat → WS → Agents → Persist (P0)
1. Front : `ensureAuth()` → obtention ID token (GIS).
2. Front : ouverture `WS /ws/{uuid}` (sans sub-proto si pas de token).
3. Back : handshake → si token invalide et pas de mode invité : `auth_required` puis close (4401/1008).
4. Front : envoi `{type:"chat.message", payload:{text, agent_id, thread_id?}}`.
5. Back : service chat → agent primaire; si **Google 429** → renormalise historique → **Anthropic**, sinon **OpenAI**.
6. Back → stream deltas `{type:"chat.delta"}` puis `{type:"chat.done"}`.
7. (P1.5) Persist threads/messages côté backend (scope par `sub` Google).

## 2) Upload → Indexation → Stats Docs (P0.3)
1. Front : upload → `/api/documents`.
2. Back : vectorisation → collection.
3. Back → Front : event `documents:list:refreshed` avec `{ total, items }`.
4. Front : `document-ui` rend le graphe après 2nd tick (canvas mesurable).

## 3) Débat autonome (P1)
1. Front : init débat → back orchestre T1 (Attaquant) sans contexte Challenger.
2. Back : tours successifs (isolation stricte) → synthèse finale.
3. Front : rendu synthèse + UI homogène.
