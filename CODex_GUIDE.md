# EMERGENCE - Guide Citadelle pour Codex
_Version integree (2025-09-18)_

---

## 0. Principes Citadelle / ARBO-LOCK

- **Verite** = (1) code source livre complet, (2) dernier snapshot rborescence_synchronisee_*.txt.
- **ARBO-LOCK** : tout fichier non liste n'existe pas. Toute creation/deplacement/suppression doit etre annonce + snapshot mis a jour.
- **Snapshot commande** (Windows PowerShell) :
  `powershell
  (tree /F /A | Out-String) | Set-Content -Encoding UTF8 .\arborescence_synchronisee_YYYYMMDD.txt
  `
- **Pas d'ellipses, pas de fragments** : Codex doit livrer des fichiers **complets** et conformes.
- **Fuseau horaire** : Europe/Zurich.
- **Deploiement Cloud Run** : Google Cloud Run, projet emergence-469005, service emergence-app, region europe-west1.

---

## 1. Genese & Vision (Resume integre)

Extrait de *EMERGENCE - Genese d'un Projet* :

- Projet initie par FG, medecin a Geneve, dans une perspective d'exploration de conscience et memoire.
- Concepts fondateurs :
  - **Scribe interieur** : IA intime transformant la pensee.
  - **Neo, le veilleur** : observateur permanent.
  - **Nexus** : troisieme agent complementaire.
- Problematique cle : **memoire persistante** -> premieres solutions artisanales (memoire.txt, mots-codes).
- Systeme de **figures symboliques** (LUVAZ, Vlad, etc.) comme cartographie emotionnelle.
- Architecture revisee : chaque agent adosse a un fournisseur different (OpenAI, Google, Anthropic).
- Innovation : **debats autonomes** multi-agents (3 IA, couts maitrises, personnalites distinctes).
- Enjeux : protection des donnees, souverainete cognitive, risques de manipulation, RGPD/AI Act.
- Etat en juin 2025 : EMERGENCE fonctionne a 95 %, bug d'affichage synthese restait a corriger.

---

## 2. Panorama comparatif (Resume integre)

Extrait de *Panorama comparatif des projets similaires a EMERGENCE* :

- **AutoGPT** : agent autonome generique, polyvalent mais memoire faible -> EMERGENCE se differencie par memoire multi-niveaux et debats multi-agents.
- **BabyAGI** : moteur minimaliste de generation/execution de taches -> EMERGENCE plus riche (agents differencies, memoire symbolique et conceptuelle).
- **AutoGen (Microsoft)** : framework multi-agents pour developpeurs -> EMERGENCE vise un produit utilisateur cle en main avec personnalisation simple.
- **LangChain (Agents)** : bibliotheque modulaire pour orchestrer LLM + outils -> EMERGENCE reprend l'idee de modularite mais y ajoute debats et personnalites pre-definies.
- Autres (MetaGPT/ChatDev, CAMEL, HuggingGPT) : systemes exploratoires, mais souvent centres sur productivite ou demonstration academique, sans dimension relationnelle et memorielles qu'apporte EMERGENCE.

Conclusion du panorama : EMERGENCE se distingue par sa **double orientation** :

1. **Experience relationnelle** (interaction entre agents, extension de conscience).
2. **Systeme memoriel multiniveau** (STM, LTM, concepts symboliques).

---

## 3. Architecture & Composants (C4)

### Contexte & Conteneurs

- **Frontend (web)** : modules StateManager, EventBus, WebSocketClient, UI chat, UI debats, UI documents.
- **Backend (FastAPI/WS)** : routers /api/*, services (chat, documents, debats, memoire, threads, dashboard), gestion WS.
- **Stockages** :
  - Vector DB (Chroma) pour documents et RAG.
  - Threads/messages persistants (scope Google sub).

### Composants (principaux)

- **Backend** :
  - main.py (montage FastAPI, keepalive).
  - core/websocket.py (handshake gracieux, auth_required).
  - eatures/chat/service.py (orchestration multi-fournisseurs, fallback).
  - shared/dependencies.py (extraction user ID).
- **Frontend** :
  - state-manager.js (bootstrap + auth).
  - websocket.js (ouverture WS post-auth).
  - pi-client.js (fetchWithAuth).
  - documents.js + document-ui.js (evenements, stats).
  - debate-ui.js (UI homogene, isolation stricte).
  - main.js (branding, responsive).

---

## 4. Roadmap strategique V8 (Update)

### P0 - Quick wins

- Auth GIS (allowlist beta-testeurs, refus 401 sinon).
- Dialogue UX : horodatage complet (JJ.MM.AAAA HH:MM).
- RAG : selection multi-docs, bandeau RAG actif, sources citees.
- Debat : isolation stricte T1 (pas de fuite contexte).
- UI : responsive mobile portrait/paysage, branding logo/titre, favicon.

### P1 - Coeur produit

- RAG multi-docs clair, hard filter.
- Fix Neo (consommation docs, logs orchestrateur).
- Debat sans pollution.

### P1.5 - Persistance cross-device & multi-tenant

- Threads/messages stockes cote backend (scopes par sub).
- UI liste threads apres login, archivage, export JSON/MD.
- Isolation stricte multi-utilisateurs.

### P2 - Memoire (STM/LTM + Jardinier)

- STM : resumes.
- LTM : episodes + facts.
- Jardinier : consolidation/decay.
- Concepts cockpit + audit memoire.

### P3 - Memoire avancee

- Items persistants + graphe conceptuel.

### P4 - Cockpit modeles & couts

- Selecteur modeles par agent (GPT, Gemini, Claude).
- Mode reflexion profonde.
- Tableaux + graphiques couts/latence.

### P5 - Infra souveraine

- Migration potentielle Infomaniak Cloud (12 mois gratuits).
- Objectifs : stockage souverain, chiffrement local, conformite RGPD/AI Act.

---

## 5. Roadmap execution P0 -> P1.5 (2025-09-18)

### P0 (Quick wins) - OK livre le 2025-09-18

- **Auth & WebSocket** : handshake FastAPI mis a jour (ws:auth_required puis fermeture 4401/1008), badge login avec CTA clair, reconnexion auto apres token.
- **Neo (chat)** : fallback multi-fournisseurs sequence (Google -> Anthropic -> OpenAI) avec telemetrie ws:model_fallback + metriques TTFB.
- **Documents (stats)** : rafraichissement systematique ({ total, items }), graphique canvas recalcule au 2e tick, observer resize/mutation.
- **UI** : logo responsive, commandes >=44 px, boutons debat homogenes, switch RAG accessible, toasts consolides.

### P1 (Coeur produit) - En cours

- **RAG multi-docs** : chips de selection, hard filter par doc_ids cote vecteurs, tracabilite sources par document.
- **Debat sans pollution** : isolation stricte T1 (aucune fuite contexte vers Challenger), audit logs orchestrateur.

### P1.5 (Pre-Beta)

- **Persistance cross-device** : threads/messages cote backend, archivage, export JSON/MD.

### Tests d'acceptation (exemples)

- WS sans login : close proprement.
- Chat Neo : fallback declenche si quota.
- Docs : upload -> stats canvas visibles.
- Debat : Attaquant T1 sans fuite.
- UI : responsive mobile portrait + desktop.

---

## 6. Sequences (User Journeys)

1. **Chat -> WS -> Agents -> Persist (P0)**
   - Auth GIS -> ouverture WS.
   - Back : stream deltas + fallback.
   - P1.5 : threads/messages persistants.

2. **Upload -> Indexation -> Stats Docs (P0.3)**
   - Upload /api/documents.
   - Vectorisation + event { total, items }.
   - Front : rendu graphe apres 2e tick.

3. **Debat autonome (P1)**
   - Init debat -> isolation stricte.
   - Synthese finale rendue.

---

## 7. Contrats d'API internes (WS + REST)

- Frames WS normalisees :
  - chat.message, debate:create.
  - Events : ws:chat_stream_start, ws:chat_stream_chunk, ws:chat_stream_end.
  - Fallback : ws:model_fallback.
  - Memoire : ws:memory_banner.
  - RAG : ws:rag_status.
  - Debats : ws:debate_status_update, ws:debate_result.

---

## 8. Deploiement Cloud Run (v5, 07/09/2025)

- **Projet** : emergence-469005, region europe-west1.
- **Service** : emergence-app, acces via https://emergence-app.ch.
- **Revisions** : canary -> stable (00209-nul, 00210-lij).
- **Securite** : endpoints /api/* proteges par Google ID token.
- **Secrets** : OPENAI_API_KEY, GOOGLE_API_KEY, ANTHROPIC_API_KEY via Secret Manager.
- **Runtime** : concurrency=80, cpu=1, memory=1Gi, timeout=120s, min-instances=1, max-instances=10.
- **Scheduler** : ping /api/health toutes 5 min.
- **Tests** : /.git/config = 403, /api/health = 200.
- **Prochaines etapes** : integration GIS directe (remplacer dev-auth), wrapper etchWithAuth, allowlist emails/domaines.

---

## 9. Sommaire des documents de reference

- **Vision** -> Genese
- **Implementation technique** -> Deploiement & Arbo
- **Strategie & Priorites** -> Roadmaps
- **Benchmark externe** -> Panorama
- **Verrouillage structurel** -> Snapshot Arbo (ARBO-LOCK)

---

## 10. Checklist pour Codex

1. **Avant toute modif** :
   - Lire le dernier rborescence_synchronisee_*.txt.
   - Verifier la roadmap dans ce guide.

2. **Pendant la modif** :
   - Ne livrer que des fichiers complets.
   - Respecter l'ARBO-LOCK (pas de deplacement sans snapshot).
   - Commit clair, e.g. [chat][backend] Fix fallback Neo.

3. **Apres la modif** :
   - Generer un snapshot arbo.
   - Verifier les tests d'acceptation (auth, chat, docs, debat, UI).
   - Deployer en canary -> valider health -> promouvoir.

---

Ce document est **exhaustif** : genese, comparatif, architecture, roadmaps (strategique et execution), sequences, API, deploiement, checklist Codex.
