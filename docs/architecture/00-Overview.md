# ÉMERGENCE — Overview (C4: Contexte & Conteneurs)

> Snapshot ARBO-LOCK de référence : arborescence_synchronisée_20250914.txt

## 1) Contexte (C4-Context)
- **But** : Plateforme IA multi-agents (Anima, Neo, Nexus) offrant chat temps réel, débats, mémoire progressive (STM/LTM) et RAG multi-documents.
- **Acteurs externes**
  - Utilisateur (web/mobile)
  - Google Identity Services (ID Token)
  - Fournisseurs LLM (Google, Anthropic, OpenAI)
  - Stockages projet (SQLite app + Chroma vector store)
  - Hébergement Cloud Run / infrastructure containerisée
- **Contraintes** : Auth forte (JWT), isolation multi-tenant par `sub`, fonctionnement offline impossible (dépendances IA externes), respect ARBO-LOCK.

## 2) Conteneurs (C4-Container)
- **Frontend (Vite + JS)**
  - Modules clés : `StateManager`, `EventBus`, `WebSocketClient`, `ChatModule`, `DebateModule`, `DocumentsModule`, `DashboardModule`.
  - Responsabilités : Auth GIS (mode dev via `AUTH_DEV_MODE`), initialisation des threads (`ensureCurrentThread()`), connexion WS (`/ws/{session_id}`), rendu des métriques chat/mémoire, interactions RAG/documents.
- **Backend (FastAPI + WebSocket)**
  - Couches : `main.py` (DI + migrations + routers), `containers.py` (`ServiceContainer`), routers REST (`/api/threads`, `/api/memory`, `/api/documents`, `/api/dashboard`, `/api/debates`), router WS (`chat.router`), services (`ChatService`, `MemoryAnalyzer`, `MemoryGardener`, `DocumentService`, `DebateService`, `DashboardService`).
  - Responsabilités : Auth ID Token (fallback `X-User-Id` si dev), gestion des sessions, orchestration multi-agents avec fallback fournisseur, consolidation mémoire, ingestion documents, diffusion WS.
- **Stockages & ressources partagées**
  - **SQLite app** : threads, messages, coûts, documents, mémoire STM/LTM.
  - **Vector DB (Chroma)** : collection `emergence_knowledge` pour chunks documents + faits mémoire (auto-reset en cas de corruption, backup automatique).
  - **Modèles SentenceTransformer** : embeddings pour RAG et mémoire.

## 3) Invariants & Qualité
- **Auth & WS** : aucun accès API critique ni WS sans JWT valide (sauf mode dev). Handshake rejette (`4401`/`1008`) si token manquant.
- **Thread bootstrap** : à l’ouverture, le front garantit un thread `type=chat` (REST) puis hydrate les messages (limite 50). Les erreurs auth doivent être surfacées (logs + toasts).
- **RAG & Mémoire** : activation explicite (toggle) ; bandeau sources côté UI ; consolidation mémoire déclenchée manuellement ou auto (gardener) ; `memory:clear` purge STM puis LTM filtrée.
- **Débat** : tours orchestrés côté back, isolation stricte des contextes agents, diffusion WS (`ws:debate_*`).
- **Observabilité** : logs structurés (`model_fallback`, `ws:handshake`, `rag:active`, `memory:garden`) et notifications front (`ws:model_info`, `ws:memory_banner`).

## 4) Références & Tests clés
- Scripts PowerShell `tests/run_all.ps1`, `tests/test_vector_store_reset.ps1`, `tests/test_vector_store_force_backup.ps1`.
- Documentation complémentaire : `docs/architecture/10-Components.md`, `docs/Memoire.md`, `docs/Roadmap Stratégique.txt`.
