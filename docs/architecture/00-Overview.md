# ÉMERGENCE — Overview (C4: Contexte & Conteneurs)

> Snapshot ARBO-LOCK de référence : arborescence_synchronisée_20250829.txt

## 1) Contexte (C4-Context)
- **But** : Interface IA multi-agents (Anima, Neo, Nexus), chat + débat autonome, RAG multi-docs, mémoire progressive.
- **Acteurs externes**
  - Utilisateur (web/mobile)
  - Google Identity Services (ID Token)
  - Google Cloud Run (hébergement backend)
  - Stockages projet (vector store, blobs selon implémentation)
- **Contraintes** : ARBO-LOCK, livraisons de fichiers complets, aucune invention hors arbo.

## 2) Conteneurs (C4-Container)
- **Frontend (web)**  
  - Modules clés : `StateManager`, `EventBus`, `WebSocketClient`, UI chat, UI débats, UI documents.
  - Responsabilités : Auth GIS, ouverture WS (après auth), rendu, RAG ON/OFF explicite.
- **Backend (FastAPI/WS)**  
  - Couches : Routers (`/api/*`), Services (chat, documents, débat), WebSocket handler, DI/shared deps.
  - Responsabilités : Auth ID Token côté app, orchestration agents, fallback multi-fournisseurs, vectorisation docs.
- **Stockages**  
  - **Vector DB** : index des documents, passages RAG.
  - **Persistance threads/messages (échelonné)** : cross-device scoping par `sub` Google.

## 3) Invariants & Qualité
- **Auth & WS** : Aucun WS sans token si mode invité inactif. Handshake gracieux (accept → close 4401/1008).
- **RAG** : Sélection explicite des docs; hard-filter par `doc_ids`; bandeau RAG actif + sources.
- **Débat** : Isolation stricte T1 (Attaquant ne “voit” pas Challenger).
- **I/O** : Fichiers **complets** à chaque livraison; encodages conformes; aucun fragment.
- **Fuseau** : Europe/Zurich pour les dates communiquées.

## 4) Références
- Plan d’exécution P0→P1.5, Roadmap V8, déploiement Cloud Run (GIS/ID Token).
