# Consignes pour les contributions agent

Ces instructions s'appliquent à tout le dépôt `emergencev8`.

## 1. Lecture des consignes
- Lire intégralement ce fichier (et tout `AGENTS.md` plus spécifique dans un sous-dossier) avant de modifier un fichier.
- Appliquer immédiatement toute nouvelle consigne découverte pendant la session.

## 2. Préparation de l'environnement
- Utiliser **Python 3.11** dans un virtualenv (`python -m venv .venv && source .venv/bin/activate`).
- Installer/mettre à jour les dépendances avec `python -m pip install --upgrade pip && pip install -r requirements.txt`.
- Utiliser **Node.js ≥ 18** (`nvm use 18` conseillé) et installer les dépendances web via `npm ci`.

## 3. Avant de coder
- Vérifier que `git status` est propre avant de commencer.
- Mettre à jour/configurer `.env.local` si les changements le nécessitent (clés API, tokens, allow/deny lists).
- S'assurer que les migrations ou initialisations nécessaires sont effectuées selon la documentation (scripts `run-local.ps1`, docs d'architecture, etc.).

## 4. Pendant la modification
- Respecter la structure des dossiers (`src/backend`, `src/frontend`, `docs`, ... ) et les conventions existantes.
- Créer les fichiers complémentaires (config/tests) requis par tout nouveau fichier ajouté.

## 5. Vérifications avant commit
- Backend : exécuter les linters/tests pertinents (par ex. `pytest`, `ruff`, `mypy`) lorsqu'ils sont requis par la portée des changements.
- Frontend : exécuter `npm run build` (et autres scripts spécifiés localement) lorsque du code frontend est modifié.
- Relire `git diff` pour éliminer secrets, artefacts ou modifications accidentelles.

## 6. Procédure Git
- Utiliser des messages de commit explicites (ex. `<type>: <résumé>` si applicable).
- Garder `git status` propre après chaque commit.
- Avant push : `git fetch && git rebase origin/main`, résoudre les conflits et relancer les tests si nécessaire.
- Pousser ensuite sur la branche (`git push origin <branche>`).

## 7. Vérifications supplémentaires
- Lancer les scripts de tests disponibles (`pwsh -File tests/run_all.ps1`) pour valider les endpoints backend critiques lorsque des modifications les touchent.
- Pour le frontend, vérifier que `npm run build` réussit et reste compatible avec la cible configurée par Vite.
- Si besoin de vérifier la parité avec l'environnement de production, construire l'image Docker locale (`docker build -t emergence-local .`).

## 8. Préparation de la PR
- Préparer un résumé des changements, des tests exécutés et des commandes utilisées.
- S'assurer que l'intégration continue passe (si accessible) après le push.

---

En appliquant systématiquement ces consignes, l'agent dispose d'une procédure standard pour éviter les problèmes de compatibilité et maintenir un workflow fluide.

Parfait. Voici le **fichier racine exhaustif** que tu peux déposer tel quel dans ton repo sous le nom :

`CODex_GUIDE.md`

---

````markdown
# ÉMERGENCE — Guide Citadelle pour Codex
_Version intégrée (2025-09-18)_

---

## 0. Principes Citadelle / ARBO-LOCK

- **Vérité** = (1) code source livré complet, (2) dernier snapshot `arborescence_synchronisée_*.txt`.  
- **ARBO-LOCK** : tout fichier non listé n’existe pas. Toute création/déplacement/suppression doit être annoncé + snapshot mis à jour.  
- **Snapshot commande** (Windows PowerShell) :
  ```powershell
  (tree /F /A | Out-String) | Set-Content -Encoding UTF8 .\arborescence_synchronisée_YYYYMMDD.txt
````

* **Pas d’ellipses, pas de fragments** : Codex doit livrer des fichiers **complets** et conformes.
* **Fuseau horaire** : Europe/Zurich.
* **Déploiement Cloud Run** : Google Cloud Run, projet `emergence-469005`, service `emergence-app`, région `europe-west1`.

---

## 1. Genèse & Vision (Résumé intégré)

Extrait de *ÉMERGENCE — Genèse d’un Projet* :

* Projet initié par FG, médecin à Genève, dans une perspective d’exploration de conscience et mémoire.
* Concepts fondateurs :

  * **Scribe intérieur** : IA intime transformant la pensée.
  * **Neo, le veilleur** : observateur permanent.
  * **Nexus** : troisième agent complémentaire.
* Problématique clé : **mémoire persistante** → premières solutions artisanales (`memoire.txt`, mots-codes).
* Système de **figures symboliques** (LUVAZ, Vlad, etc.) comme cartographie émotionnelle.
* Architecture révisée : chaque agent adossé à un fournisseur différent (OpenAI, Google, Anthropic).
* Innovation : **Débats autonomes** multi-agents (3 IA, coûts maîtrisés, personnalités distinctes).
* Enjeux : protection des données, souveraineté cognitive, risques de manipulation, RGPD/AI Act.
* État en juin 2025 : ÉMERGENCE fonctionne à 95 %, bug d’affichage synthèse restait à corriger.

---

## 2. Panorama comparatif (Résumé intégré)

Extrait de *Panorama comparatif des projets similaires à ÉMERGENCE* :

* **AutoGPT** : agent autonome générique, polyvalent mais mémoire faible → ÉMERGENCE se différencie par mémoire multi-niveaux et débats multi-agents.
* **BabyAGI** : moteur minimaliste de génération/exécution de tâches → ÉMERGENCE plus riche (agents différenciés, mémoire symbolique et conceptuelle).
* **AutoGen (Microsoft)** : framework multi-agents pour développeurs → ÉMERGENCE vise un produit utilisateur clé en main avec personnalisation simple.
* **LangChain (Agents)** : bibliothèque modulaire pour orchestrer LLM + outils → ÉMERGENCE reprend l’idée de modularité mais y ajoute débats et personnalités pré-définies.
* Autres (MetaGPT/ChatDev, CAMEL, HuggingGPT) : systèmes exploratoires, mais souvent centrés sur productivité ou démonstration académique, sans dimension relationnelle et mémorielle qu’apporte ÉMERGENCE.

Conclusion du panorama : ÉMERGENCE se distingue par sa **double orientation** :

1. **Expérience relationnelle** (interaction entre agents, extension de conscience).
2. **Système mémoriel multiniveau** (STM, LTM, concepts symboliques).

---

## 3. Architecture & Composants (C4)

### Contexte & Conteneurs

* **Frontend (web)** : modules `StateManager`, `EventBus`, `WebSocketClient`, UI chat, UI débats, UI documents.
* **Backend (FastAPI/WS)** : routers `/api/*`, services (chat, documents, débats, mémoire, threads, dashboard), gestion WS.
* **Stockages** :

  * Vector DB (Chroma) pour documents et RAG.
  * Threads/messages persistants (scope Google `sub`).

### Composants (principaux)

* **Backend** :

  * `main.py` (montage FastAPI, keepalive).
  * `core/websocket.py` (handshake gracieux, auth\_required).
  * `features/chat/service.py` (orchestration multi-fournisseurs, fallback).
  * `shared/dependencies.py` (extraction user ID).
* **Frontend** :

  * `state-manager.js` (bootstrap + auth).
  * `websocket.js` (ouverture WS post-auth).
  * `api-client.js` (fetchWithAuth).
  * `documents.js` + `document-ui.js` (événements, stats).
  * `debate-ui.js` (UI homogène, isolation stricte).
  * `main.js` (branding, responsive).

---

## 4. Roadmap stratégique V8 (Update)

### P0 — Quick wins

* Auth GIS (allowlist bêta-testeurs, refus 401 sinon).
* Dialogue UX : horodatage complet (JJ.MM.AAAA HH\:MM).
* RAG : sélection multi-docs, bandeau RAG actif, sources citées.
* Débat : isolation stricte T1 (pas de fuite contexte).
* UI : responsive mobile portrait/paysage, branding logo/titre, favicon.

### P1 — Cœur produit

* RAG multi-docs clair, hard filter.
* Fix Neo (consommation docs, logs orchestrateur).
* Débat sans pollution.

### P1.5 — Persistance cross-device & multi-tenant

* Threads/messages stockés côté backend (scopés par `sub`).
* UI liste threads après login, archivage, export JSON/MD.
* Isolation stricte multi-utilisateurs.

### P2 — Mémoire (STM/LTM + Jardinier)

* STM : résumés.
* LTM : épisodes + facts.
* Jardinier : consolidation/decay.
* Concepts cockpit + audit mémoire.

### P3 — Mémoire avancée

* Items persistants + graphe conceptuel.

### P4 — Cockpit modèles & coûts

* Sélecteur modèles par agent (GPT, Gemini, Claude).
* Mode réflexion profonde.
* Tableaux + graphiques coûts/latence.

### P5 — Infra souveraine

* Migration potentielle Infomaniak Cloud (12 mois gratuits).
* Objectifs : stockage souverain, chiffrement local, conformité RGPD/AI Act.

---

## 5. Roadmap exécution P0 → P1.5 (2025-08-29)

### P0 (Quick wins)

* **Auth & WS** : handshake gracieux (accept→close 4401/1008), CTA login si token absent.
* **Neo (chat)** : fallback multi-fournisseurs robuste (Google→Anthropic→OpenAI).
* **Docs plot** : stats visibles à chaque refresh (événement `{ total, items }`, redraw canvas au 2e tick).
* **UI** : logo redimensionné, sélecteurs ≥44px, boutons Débat homogènes, switch RAG lisible.

### P1 (Cœur produit)

* **RAG multi-docs** : chips de sélection, hard filter par `doc_ids`.
* **Débat sans pollution** : isolation stricte T1 (pas de contexte Challenger).

### P1.5 (Pré-Beta)

* **Persistance cross-device** : threads/messages côté backend, archivage, export JSON/MD.

### Tests d’acceptation (exemples)

* WS sans login : close proprement.
* Chat Neo : fallback déclenché si quota.
* Docs : upload → stats canvas visibles.
* Débat : Attaquant T1 sans fuite.
* UI : responsive mobile portrait + desktop.

---

## 6. Séquences (User Journeys)

1. **Chat → WS → Agents → Persist (P0)**

   * Auth GIS → ouverture WS.
   * Back : stream deltas + fallback.
   * P1.5 : threads/messages persistants.

2. **Upload → Indexation → Stats Docs (P0.3)**

   * Upload `/api/documents`.
   * Vectorisation + event `{ total, items }`.
   * Front : rendu graphe après 2e tick.

3. **Débat autonome (P1)**

   * Init débat → isolation stricte.
   * Synthèse finale rendue.

---

## 7. Contrats d’API internes (WS + REST)

* Frames WS normalisées :

  * `chat.message`, `debate:create`.
  * Events : `ws:chat_stream_start`, `ws:chat_stream_chunk`, `ws:chat_stream_end`.
  * Fallback : `ws:model_fallback`.
  * Mémoire : `ws:memory_banner`.
  * RAG : `ws:rag_status`.
  * Débats : `ws:debate_status_update`, `ws:debate_result`.

---

## 8. Déploiement Cloud Run (v5, 07/09/2025)

* **Projet** : `emergence-469005`, région `europe-west1`.
* **Service** : `emergence-app`, accès via `https://emergence-app.ch`.
* **Révisions** : canary → stable (00209-nul, 00210-lij).
* **Sécurité** : endpoints `/api/*` protégés par Google ID token.
* **Secrets** : `OPENAI_API_KEY`, `GOOGLE_API_KEY`, `ANTHROPIC_API_KEY` via Secret Manager.
* **Runtime** : concurrency=80, cpu=1, memory=1Gi, timeout=120s, min-instances=1, max-instances=10.
* **Scheduler** : ping `/api/health` toutes 5 min.
* **Tests** : /.git/config = 403, /api/health = 200.
* **Prochaines étapes** : intégration GIS directe (remplacer dev-auth), wrapper `fetchWithAuth`, allowlist emails/domaines.

---

## 9. Sommaire des documents de référence

* **Vision** → Genèse
* **Implémentation technique** → Déploiement & Arbo
* **Stratégie & Priorités** → Roadmaps
* **Benchmark externe** → Panorama
* **Vérrouillage structurel** → Snapshot Arbo (ARBO-LOCK)

---

## 10. Checklist pour Codex

1. **Avant toute modif** :

   * Lire le dernier `arborescence_synchronisée_*.txt`.
   * Vérifier la roadmap dans ce guide.

2. **Pendant la modif** :

   * Ne livrer que des fichiers complets.
   * Respecter l’ARBO-LOCK (pas de déplacement sans snapshot).
   * Commit clair, e.g. `[chat][backend] Fix fallback Neo`.

3. **Après la modif** :

   * Générer un snapshot arbo.
   * Vérifier les tests d’acceptation (auth, chat, docs, débat, UI).
   * Déployer en canary → valider health → promouvoir.

---

# Fin du document

```

---

✅ Ce document est **exhaustif** : genèse, comparatif, architecture, roadmaps (stratégique et exécution), séquences, API, déploiement, checklist Codex.  

Veux-tu que je te prépare aussi un **README simplifié** (1–2 pages) à mettre en parallèle pour les nouveaux contributeurs humains, pendant que `CODex_GUIDE.md` reste le référentiel strict pour l’IA ?
```
