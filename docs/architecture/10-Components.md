# ÉMERGENCE — Components (C4-Component)

## Backend
- **main.py** : montage FastAPI, middlewares, routers, ping/pong keepalive.
- **core/websocket.py** : handshake WS, auth_required, accept→close 4401/1008, mode invité (optionnel).
- **features/chat/router.py** : endpoints chat + WS, session stateless si invité, routage erreurs WS.
- **features/chat/service.py** : orchestration multi-fournisseurs, renormalisation historique, fallback (Google→Anthropic→OpenAI).
- **shared/dependencies.py** : extraction user (ID token), fallback `X-User-ID` lecture simple.

## Frontend
- **core/state-manager.js** : bootstrap + `ensureAuth()` avant `app:ready`.
- **core/websocket.js** : ouverture WS uniquement **après** auth (pas de sub-proto `jwt` sans token).
- **shared/api-client.js** : `fetchWithAuth` (injecte `Authorization: Bearer <ID token>`), erreurs `auth:missing`.
- **features/documents/** : `documents.js` (événement `{ total, items }`), `document-ui.js` (data-first + retick).
- **features/debate/** : layout symétrique, règles d’isolation; déclencheurs UI homogènes.
- **main.js (front)** : branding (logo, header gaps), responsive portrait/desktop.

## Interfaces & Contrats (liens)
- WebSocket Frames et REST clés détaillés dans `30-Contracts.md`.

## Qualité / Observabilité
- Logs ciblés : `model_fallback`, `ws:handshake`, `rag:active`.
- Tests d’acceptation (manuels rapides) : voir plan d’exécution; automatisation future possible.
