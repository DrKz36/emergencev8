# Prompt d'Implémentation — Détection et Rappel de Concepts Récurrents

**Date** : 2025-10-04
**Destinataire** : Nouvelle instance Claude Code
**Objectif** : Implémenter le système de détection de concepts récurrents (Phase 1-4)

---

## 🎯 Contexte du Projet

Tu travailles sur **Emergence V8**, une application multi-agents (Anima, Neo, Nexus) avec mémoire STM/LTM, RAG et vectorisation ChromaDB.

**Architecture actuelle** :
- Backend : FastAPI (Python 3.11), SQLite, ChromaDB (SentenceTransformer)
- Frontend : JavaScript vanilla, WebSocket temps réel
- Mémoire : `MemoryAnalyzer` (extraction concepts via LLM), `MemoryGardener` (vectorisation + decay)
- Base : Tables `messages`, `threads`, `monitoring` ; collections vectorielles `emergence_knowledge`, `memory_preferences`

**Documentation de référence** :
- [docs/architecture/CONCEPT_RECALL.md](docs/architecture/CONCEPT_RECALL.md) — Architecture complète (LIRE EN PRIORITÉ)
- [docs/Memoire.md](docs/Memoire.md) — Système mémoire actuel
- [CODEV_PROTOCOL.md](CODEV_PROTOCOL.md) — Protocole multi-agents Claude Code ↔ Codex
- [AGENTS.md](AGENTS.md) — Consignes générales

---

## 📋 Mission : Implémenter Phases 1-4

### ✅ **Phase 1 : Enrichissement Métadonnées (Backend)**

**Objectif** : Ajouter métadonnées temporelles aux concepts vectorisés, sans changement UX.

#### Tâches :

1. **Modifier `src/backend/features/memory/gardener.py`**
   - Fonction `_vectorize_concepts()` (ligne ~1476)
   - Ajouter dans `metadata` :
     ```python
     "first_mentioned_at": now_iso,
     "last_mentioned_at": now_iso,
     "thread_id": thread_id,  # Récupérer depuis session stub
     "thread_ids": [thread_id] if thread_id else [],
     "message_id": message_id,  # À passer depuis ChatService
     "mention_count": 1,
     ```
   - **Attention** : Enrichir `session_stub` dans `_tend_single_thread()` avec `thread_id` et `message_id`

2. **Migration données existantes**
   - Créer `scripts/migrate_concept_metadata.py`
   - Itérer sur collection `emergence_knowledge` (type="concept")
   - Remplir métadonnées manquantes :
     - `first_mentioned_at` = `created_at` existant
     - `last_mentioned_at` = `created_at` existant
     - `mention_count` = 1
     - `thread_ids` = [] (impossible de rétroactivement déterminer)
     - `message_id` = null
   - Logger résultats (X concepts migrés, Y échecs)

3. **Tests unitaires**
   - Créer `tests/backend/features/test_memory_gardener_enrichment.py`
   - Test : Vectoriser nouveau concept → vérifier présence métadonnées enrichies
   - Test : Migration données → vérifier `first_mentioned_at` rempli pour concepts existants
   - Exécuter : `pytest tests/backend/features/test_memory_gardener_enrichment.py -v`

4. **Validation**
   - Lancer `pwsh -File scripts/run-backend.ps1`
   - Créer un thread, envoyer message, déclencher `POST /api/memory/tend-garden`
   - Inspecter ChromaDB : `collection.get(ids=[<concept_id>], include=["metadatas"])` → confirmer nouvelles clés

---

### ✅ **Phase 2 : ConceptRecallTracker (Backend)**

**Objectif** : Détecter récurrences conceptuelles, logger uniquement (pas d'événements UI encore).

#### Tâches :

1. **Créer `src/backend/features/memory/concept_recall.py`**
   - Copier le code complet depuis [CONCEPT_RECALL.md Section 4.1](docs/architecture/CONCEPT_RECALL.md#41-composant-conceptrecalltracker)
   - Classe `ConceptRecallTracker` avec méthodes :
     - `detect_recurring_concepts()` : Recherche vectorielle + filtrage similarité > 0.75
     - `_update_mention_metadata()` : Incrémenter `mention_count`, ajouter `thread_id`, boost `vitality`
     - `_emit_concept_recall_event()` : Émettre `ws:concept_recall` (désactivé en Phase 2)
     - `query_concept_history()` : Recherche explicite pour API

2. **Intégrer dans `src/backend/features/chat/service.py`**
   - Ajouter dans `__init__()` :
     ```python
     from backend.features.memory.concept_recall import ConceptRecallTracker

     self.concept_recall_tracker = ConceptRecallTracker(
         db_manager=db_manager,
         vector_service=vector_service,
         connection_manager=session_manager.connection_manager,
     )
     ```
   - Dans `handle_chat_message()`, **avant appel LLM** :
     ```python
     message_id = uuid.uuid4().hex
     recalls = await self.concept_recall_tracker.detect_recurring_concepts(
         message_text=message,
         user_id=user_id,
         thread_id=thread_id,
         message_id=message_id,
         session_id=session_id,
     )

     if recalls:
         logger.info(f"[ConceptRecall] {len(recalls)} récurrences détectées : {[r['concept_text'] for r in recalls]}")
         # Phase 2 : NE PAS émettre ws:concept_recall encore
     ```

3. **Désactiver émission WS (Phase 2)**
   - Dans `ConceptRecallTracker._emit_concept_recall_event()`, ajouter en début :
     ```python
     if not os.getenv("CONCEPT_RECALL_EMIT_EVENTS", "false").lower() == "true":
         return  # Phase 2 : émission désactivée
     ```

4. **Tests unitaires**
   - Créer `tests/backend/features/test_concept_recall_tracker.py`
   - Copier les 3 tests depuis [CONCEPT_RECALL.md Section 7.1](docs/architecture/CONCEPT_RECALL.md#71-tests-unitaires)
   - Fixtures :
     - `seed_concept()` : Insérer un concept dans ChromaDB avec métadonnées
   - Tests :
     - `test_detect_recurring_concepts_first_mention` → Aucune récurrence
     - `test_detect_recurring_concepts_second_mention` → 1 récurrence détectée
     - `test_update_mention_metadata` → `mention_count` incrémenté
   - Exécuter : `pytest tests/backend/features/test_concept_recall_tracker.py -v`

5. **Monitoring (optionnel Phase 2)**
   - Ajouter logs INFO dans `detect_recurring_concepts()` :
     ```python
     logger.info(f"[ConceptRecall] Détection pour user={user_id}, thread={thread_id} : {len(recalls)} récurrences")
     ```
   - Observer les logs pendant QA manuelle

---

### ✅ **Phase 3 : Événements WebSocket + UI (Frontend)**

**Objectif** : Afficher les récurrences détectées dans l'UI via toast/banner.

#### Tâches :

1. **Activer émission WS (Backend)**
   - Ajouter dans `.env.local` :
     ```
     CONCEPT_RECALL_EMIT_EVENTS=true
     ```
   - Redémarrer backend

2. **Créer module UI (Frontend)**
   - Fichier : `src/frontend/features/chat/concept-recall-banner.js`
   - Copier le code depuis [CONCEPT_RECALL.md Section 5.1](docs/architecture/CONCEPT_RECALL.md#51-événement-websocket-wsconcept_recall) (adapté)
   - Composant :
     ```javascript
     export class ConceptRecallBanner {
         constructor(container) {
             this.container = container;
             this.isVisible = false;
         }

         show(recalls) {
             // Générer HTML du banner
             const html = this._buildBannerHTML(recalls);
             this.container.innerHTML = html;
             this.container.style.display = 'block';
             this.isVisible = true;
         }

         hide() {
             this.container.style.display = 'none';
             this.isVisible = false;
         }

         _buildBannerHTML(recalls) {
             const recall = recalls[0]; // Premier concept
             return `
                 <div class="concept-recall-banner">
                     <div class="banner-icon">🔗</div>
                     <div class="banner-content">
                         <div class="banner-title">Concept déjà abordé</div>
                         <div class="banner-concept">${recall.concept}</div>
                         <div class="banner-meta">
                             Première mention : ${this._formatDate(recall.first_date)}<br>
                             Mentionné ${recall.count} fois dans ${recall.thread_count} threads
                         </div>
                     </div>
                     <div class="banner-actions">
                         <button class="btn-secondary" data-action="view-history">Voir l'historique</button>
                         <button class="btn-text" data-action="dismiss">Ignorer</button>
                     </div>
                 </div>
             `;
         }

         _formatDate(isoDate) {
             const date = new Date(isoDate);
             return date.toLocaleDateString('fr-FR', {
                 day: 'numeric',
                 month: 'short',
                 year: 'numeric',
                 hour: '2-digit',
                 minute: '2-digit'
             });
         }
     }
     ```

3. **Intégrer dans ChatModule**
   - Fichier : `src/frontend/features/chat/chat-module.js`
   - Importer :
     ```javascript
     import { ConceptRecallBanner } from './concept-recall-banner.js';
     ```
   - Dans `init()` :
     ```javascript
     this.recallBanner = new ConceptRecallBanner(
         document.querySelector('.concept-recall-container')
     );

     EventBus.on('ws:concept_recall', (payload) => {
         this.handleConceptRecall(payload);
     });
     ```
   - Ajouter méthode :
     ```javascript
     handleConceptRecall(payload) {
         if (payload.recalls && payload.recalls.length > 0) {
             this.recallBanner.show(payload.recalls);
         }
     }
     ```

4. **Styles CSS**
   - Fichier : `src/frontend/styles/chat.css` (ou créer `concept-recall.css`)
   - Ajouter :
     ```css
     .concept-recall-banner {
         background: var(--surface-2);
         border-left: 4px solid var(--accent-blue);
         padding: 1rem;
         margin: 1rem 0;
         border-radius: 8px;
         display: flex;
         gap: 1rem;
         align-items: center;
     }

     .banner-icon {
         font-size: 2rem;
     }

     .banner-content {
         flex: 1;
     }

     .banner-title {
         font-weight: 600;
         color: var(--text-primary);
         margin-bottom: 0.25rem;
     }

     .banner-concept {
         font-size: 1.1rem;
         color: var(--accent-blue);
         margin-bottom: 0.5rem;
     }

     .banner-meta {
         font-size: 0.9rem;
         color: var(--text-secondary);
         line-height: 1.4;
     }

     .banner-actions {
         display: flex;
         gap: 0.5rem;
         flex-direction: column;
     }
     ```

5. **HTML container**
   - Fichier : `src/frontend/index.html` (ou template chat)
   - Ajouter dans la zone chat (avant les messages) :
     ```html
     <div class="concept-recall-container" style="display: none;"></div>
     ```

6. **Tests frontend**
   - Créer `src/frontend/features/chat/__tests__/concept-recall.test.js`
   - Test : Simuler événement `ws:concept_recall` → vérifier affichage banner
   - Test : Clic bouton "Ignorer" → banner caché
   - Exécuter : `npm test -- src/frontend/features/chat/__tests__/concept-recall.test.js`

---

### ✅ **Phase 4 : API Recherche Explicite (Backend + Frontend)**

**Objectif** : Endpoint `/api/memory/concepts/search` pour requêtes utilisateur "on a déjà parlé de X ?".

#### Tâches :

1. **Endpoint REST (Backend)**
   - Fichier : `src/backend/features/memory/router.py`
   - Ajouter :
     ```python
     from backend.features.memory.concept_recall import ConceptRecallTracker

     @router.get("/concepts/search")
     async def search_concepts(
         q: str = Query(..., min_length=3, description="Terme de recherche"),
         limit: int = Query(10, ge=1, le=50),
         user_id: str = Depends(get_user_id),
         session_id: str = Header(None, alias="X-Session-Id"),
     ):
         """
         Recherche de concepts dans l'historique utilisateur.
         """
         tracker: ConceptRecallTracker = container.concept_recall_tracker()

         results = await tracker.query_concept_history(
             concept_text=q,
             user_id=user_id,
             limit=limit,
         )

         return {
             "query": q,
             "results": results,
         }
     ```

2. **Enregistrer dans DI container**
   - Fichier : `src/backend/core/containers.py`
   - Ajouter :
     ```python
     from backend.features.memory.concept_recall import ConceptRecallTracker

     @singleton
     def concept_recall_tracker(self) -> ConceptRecallTracker:
         return ConceptRecallTracker(
             db_manager=self.db_manager(),
             vector_service=self.vector_service(),
             connection_manager=self.session_manager().connection_manager,
         )
     ```

3. **Tests backend**
   - Fichier : `tests/backend/features/test_memory_concept_search.py`
   - Test : `GET /api/memory/concepts/search?q=Docker` → 200 + résultats triés par similarité
   - Test : `GET /api/memory/concepts/search?q=xy` (< 3 chars) → 422 Validation Error
   - Test : `GET /api/memory/concepts/search` (sans param) → 422
   - Exécuter : `pytest tests/backend/features/test_memory_concept_search.py -v`

4. **Intégration LLM (optionnel Phase 4)**
   - Prompt système pour agents (fichier config ou prompt template) :
     ```
     Si l'utilisateur demande explicitement "on a déjà parlé de X ?" ou
     "est-ce qu'on a abordé Y ?", appelle l'API :
     GET /api/memory/concepts/search?q=<terme>

     Résume ensuite les résultats avec dates et threads concernés.
     ```
   - **Alternative** : Détection côté `ChatService` via regex :
     ```python
     if re.search(r"(on a déjà parlé|a-t-on abordé|avons-nous discuté)", message, re.IGNORECASE):
         # Extraire le terme clé et appeler l'API
     ```

---

## 📦 Livrables Attendus

### Backend
- [ ] `src/backend/features/memory/gardener.py` modifié (métadonnées enrichies)
- [ ] `src/backend/features/memory/concept_recall.py` créé (~350 lignes)
- [ ] `src/backend/features/chat/service.py` modifié (intégration tracker)
- [ ] `src/backend/features/memory/router.py` modifié (endpoint `/concepts/search`)
- [ ] `src/backend/core/containers.py` modifié (DI `concept_recall_tracker`)
- [ ] `scripts/migrate_concept_metadata.py` créé
- [ ] Tests unitaires :
  - `tests/backend/features/test_memory_gardener_enrichment.py`
  - `tests/backend/features/test_concept_recall_tracker.py`
  - `tests/backend/features/test_memory_concept_search.py`

### Frontend
- [ ] `src/frontend/features/chat/concept-recall-banner.js` créé
- [ ] `src/frontend/features/chat/chat-module.js` modifié (écoute `ws:concept_recall`)
- [ ] `src/frontend/styles/concept-recall.css` créé (ou ajouté dans `chat.css`)
- [ ] `src/frontend/index.html` modifié (container banner)
- [ ] Tests frontend :
  - `src/frontend/features/chat/__tests__/concept-recall.test.js`

### Documentation
- [ ] `docs/Memoire.md` mis à jour (section 3.Flux : ajouter Flux 9 "Détection concepts récurrents")
- [ ] `docs/architecture/30-Contracts.md` mis à jour (événement `ws:concept_recall`, endpoint `/concepts/search`)
- [ ] `docs/passation.md` : Nouvelle entrée avec date/heure, fichiers modifiés, tests exécutés

---

## 🧪 Tests & Validation

### Tests automatisés
```bash
# Backend
pytest tests/backend/features/test_memory_gardener_enrichment.py -v
pytest tests/backend/features/test_concept_recall_tracker.py -v
pytest tests/backend/features/test_memory_concept_search.py -v

# Frontend
npm test -- src/frontend/features/chat/__tests__/concept-recall.test.js

# Build
npm run build
```

### QA manuelle

**Scénario 1 : Détection automatique**
1. Lancer backend : `pwsh -File scripts/run-backend.ps1`
2. Ouvrir UI, créer thread "DevOps"
3. Envoyer message : "Comment setup une CI/CD pipeline ?"
4. Attendre réponse agent
5. Déclencher consolidation : `POST /api/memory/tend-garden`
6. Créer nouveau thread "Automation"
7. Envoyer message : "Je veux automatiser mon pipeline CI/CD"
8. **Vérifier** : Banner 🔗 s'affiche avec "CI/CD pipeline, première mention..."

**Scénario 2 : Recherche explicite**
1. Envoyer message : "Est-ce qu'on a déjà parlé de containerisation ?"
2. **Vérifier** : Agent liste les occurrences avec dates et threads

**Scénario 3 : Métadonnées**
1. Inspecter ChromaDB après consolidation :
   ```python
   collection = vector_service.get_or_create_collection("emergence_knowledge")
   result = collection.get(where={"type": "concept"}, limit=1, include=["metadatas"])
   print(result["metadatas"][0])
   ```
2. **Vérifier** : Présence de `first_mentioned_at`, `thread_ids`, `mention_count`

---

## 📌 Consignes Importantes

### Protocole multi-agents
- **LIRE** `CODEV_PROTOCOL.md` et `AGENTS.md` avant de coder
- **RESPECTER** ARBO-LOCK : Ne pas créer/déplacer/supprimer fichiers sans snapshot
- **LIVRER** du code complet (pas d'ellipses `...`, pas de fragments)
- **NE PAS COMMITTER** sans validation architecte (FG)

### Conventions
- **Backend** : Python 3.11, type hints, docstrings Google-style
- **Frontend** : JavaScript vanilla (pas de framework), ES6 modules
- **Logs** : `logger.info()` pour actions importantes, `logger.debug()` pour détails
- **Tests** : Pytest (backend), Node.js native test runner (frontend)

### Points de vigilance
- **Timeout** : `detect_recurring_concepts()` doit terminer en <500ms (recherche vectorielle rapide)
- **Filtrage** : Toujours filtrer par `user_id` (GDPR compliance)
- **Seuil similarité** : 0.75 pour détection auto, 0.6 pour recherche explicite
- **Limite UI** : Max 3 rappels par message (éviter spam)

---

## 🚀 Workflow Recommandé

1. **Initialisation**
   ```bash
   git checkout main
   git pull origin main
   git checkout -b feat/concept-recall-tracker
   ```

2. **Phase 1** (Backend métadonnées)
   - Modifier `gardener.py`
   - Créer script migration
   - Tests + validation
   - Commit : `feat(memory): enrich concept metadata with temporal tracking`

3. **Phase 2** (ConceptRecallTracker)
   - Créer `concept_recall.py`
   - Intégrer dans `ChatService`
   - Tests
   - Commit : `feat(memory): add ConceptRecallTracker for recurring concept detection`

4. **Phase 3** (Frontend UI)
   - Créer banner component
   - Intégrer dans ChatModule
   - Styles CSS
   - Tests
   - Commit : `feat(ui): add concept recall banner for chat`

5. **Phase 4** (API search)
   - Endpoint REST
   - DI container
   - Tests
   - Commit : `feat(api): add concept search endpoint for explicit queries`

6. **Finalisation**
   - Mise à jour docs (`Memoire.md`, `30-Contracts.md`)
   - QA manuelle complète
   - Exécuter `pwsh -File scripts/sync-workdir.ps1 -SkipTests` (tests déjà exécutés)
   - Passation dans `docs/passation.md`

7. **Soumission**
   - **NE PAS PUSH** : Préparer les changements pour revue FG
   - Générer diff : `git diff main...feat/concept-recall-tracker > /tmp/concept-recall.patch`
   - Documenter dans passation

---

## 📚 Ressources Clés

**Documentation prioritaire** :
1. [docs/architecture/CONCEPT_RECALL.md](docs/architecture/CONCEPT_RECALL.md) — **Architecture complète (LIRE EN ENTIER)**
2. [docs/Memoire.md](docs/Memoire.md) — Système mémoire actuel
3. [src/backend/features/memory/gardener.py](src/backend/features/memory/gardener.py) — Code existant à modifier
4. [src/backend/features/chat/service.py](src/backend/features/chat/service.py) — Point d'intégration

**Protocole** :
- [CODEV_PROTOCOL.md](CODEV_PROTOCOL.md) — Workflow multi-agents
- [AGENTS.md](AGENTS.md) — Consignes générales

**Tests de référence** :
- [tests/backend/features/test_memory_enhancements.py](tests/backend/features/test_memory_enhancements.py) — Style de tests attendu
- [tests/run_all.ps1](tests/run_all.ps1) — Suite smoke tests

---

## ❓ En Cas de Blocage

**Si données manquantes** :
- Consulter `CONCEPT_RECALL.md` Section 4 (implémentation complète)
- Lire code existant `gardener.py` et `analyzer.py` pour comprendre patterns

**Si tests échouent** :
- Vérifier que backend tourne : `pwsh -File scripts/run-backend.ps1`
- Vérifier variables d'environnement dans `.env.local`
- Logger les métadonnées vectorielles pour debug

**Si performance dégradée** :
- Vérifier taille collection ChromaDB : `collection.count()`
- Timeout recherche vectorielle : ajouter `timeout=0.5` dans `query()`
- Désactiver temporairement : `export CONCEPT_RECALL_ENABLED=false`

**Si conflit d'architecture** :
- **STOP** : Ne pas forcer une solution différente
- Documenter le problème dans passation
- Proposer alternative avec justification technique

---

## ✅ Checklist Finale Avant Passation

- [ ] Tous les fichiers livrables créés/modifiés
- [ ] Tests unitaires passent (backend + frontend)
- [ ] `npm run build` réussit
- [ ] QA manuelle : 3 scénarios validés
- [ ] Documentation mise à jour (`Memoire.md`, `30-Contracts.md`)
- [ ] Entrée passation complète dans `docs/passation.md` avec :
  - Date/heure Europe/Zurich
  - Agent : Claude Code
  - Fichiers modifiés (liste exhaustive)
  - Contexte : Implémentation Phases 1-4 système concept recall
  - Tests exécutés (pytest + npm test + QA manuelle)
  - Prochaines actions : Revue FG, validation avant merge
  - Blocages : [aucun ou liste]
- [ ] `git status` propre (ou usage `-AllowDirty` documenté)
- [ ] Branche `feat/concept-recall-tracker` prête pour revue

---

**Bon courage ! Le plan est complet, la documentation exhaustive. Suis les phases dans l'ordre, teste au fur et à mesure, et documente tout. 💪**
