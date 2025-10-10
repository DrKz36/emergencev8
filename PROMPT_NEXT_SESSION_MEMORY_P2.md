# 🚀 Prompt Session Suivante - Implémentation Mémoire Phase P2

**Date création** : 2025-10-10
**Contexte** : Suite session audit P0 - Tous gaps critiques résolus
**Objectif** : Continuer implémentation mémoire selon priorités

---

## 📋 Contexte Projet

Tu es **Claude Code**, agent IA spécialisé en développement backend/frontend pour **EMERGENCE V8**, une plateforme multi-agents (Anima, Neo, Nexus) avec système mémoire STM/LTM avancé.

**Stack technique** :
- Backend : Python 3.11 + FastAPI + SQLite + ChromaDB (vectoriel)
- Frontend : Vanilla JS + Vite
- Tests : pytest + asyncio
- Monitoring : Prometheus + métriques custom

---

## ✅ Travail Déjà Accompli (Phase P0 + P1)

### Phase P1 (Complétée ✅)
- ✅ MemoryTaskQueue async (déportation hors boucle WS)
- ✅ PreferenceExtractor modulaire (filtrage lexical + LLM)
- ✅ 5 métriques Prometheus préférences
- ✅ Tests : 20/20 préférences + 8/8 extraction

### Phase P0 (Complétée ✅)
- ✅ **Gap #2** : Persistance préférences ChromaDB implémentée
- ✅ **Gap #1** : Consolidation threads archivés automatique
  - Endpoint `/api/memory/consolidate-archived`
  - Hook archivage → TaskQueue `consolidate_thread`
  - Tests : 10/10 consolidation archivés
- 🟡 **Gap #3** : Architecture hybride sessions/threads (P2 refactoring)

**Documentation complète** :
- [P0_GAPS_RESOLUTION_STATUS.md](docs/validation/P0_GAPS_RESOLUTION_STATUS.md)
- [MEMORY_LTM_GAPS_ANALYSIS.md](docs/architecture/MEMORY_LTM_GAPS_ANALYSIS.md)
- [MEMORY_CAPABILITIES.md](docs/MEMORY_CAPABILITIES.md)

---

## 🎯 Mission Principale : Phase P2 - Optimisations Performance Mémoire

**Plan détaillé** : [MEMORY_P2_PERFORMANCE_PLAN.md](docs/optimizations/MEMORY_P2_PERFORMANCE_PLAN.md)

### Priorités par Sprint

#### 🏆 **Sprint 1 : Indexation & Cache (2-3 jours) - PRIORITÉ MAX**

**Problème** :
- Requêtes ChromaDB lentes (100-200ms) bloquent génération réponses
- Préférences rechargées à chaque message (gaspillage)
- Pas d'index sur métadonnées clés (user_id, type, confidence)

**Actions** :
1. **Créer index ChromaDB** (`src/backend/features/memory/vector_service.py`)
   ```python
   # Ajouter dans get_or_create_collection()
   collection.create_index(field="user_id", index_type="exact")
   collection.create_index(field="type", index_type="exact")
   collection.create_index(field="confidence", index_type="range")
   ```

2. **Cache préférences déjà implémenté** ✅
   - `_fetch_active_preferences_cached()` existe ([memory_ctx.py:132-149](src/backend/features/chat/memory_ctx.py#L132-L149))
   - TTL 5 min, metrics Prometheus intégrées
   - **Action** : Vérifier utilisation effective (grep `_fetch_active_preferences_cached`)

3. **Batch prefetch concepts LTM**
   - Charger top 20 concepts user au handshake WS
   - Stocker dans SessionManager pour réutilisation
   - Éviter requêtes répétées pendant conversation

4. **Tests performance**
   ```python
   # tests/backend/features/test_memory_performance.py (à créer)
   async def test_preference_cache_hit_rate():
       # Target: >80% hit rate après warmup

   async def test_chromadb_query_latency():
       # Target: <50ms avec index (vs 200ms sans)

   async def test_batch_prefetch_vs_incremental():
       # Target: 5x faster (1 query vs 10)
   ```

**Livrables** :
- Index ChromaDB opérationnels
- Cache préférences validé (hit rate >80%)
- Batch prefetch implémenté
- Tests performance (3 tests min)
- Métriques Prometheus : `memory_query_duration_seconds`, `memory_cache_hit_rate`

---

#### 🎯 **Sprint 2 : Proactive Hints Backend (2-3 jours)**

**Objectif** : Agents suggèrent actions basées sur préférences/intentions capturées

**Architecture** :
```
PreferenceExtractor (existant)
    ↓
ProactiveHintEngine (nouveau)
    ├─> Règles métier (if topic="language" AND confidence>0.7 → suggest)
    ├─> Scoring pertinence contexte actuel
    └─> Génération hints JSON
         ↓
WebSocket event ws:proactive_hint
    ↓
Frontend affiche suggestion
```

**Implémentation** :

1. **Créer `ProactiveHintEngine`** (`src/backend/features/memory/proactive_hints.py`)
   ```python
   class ProactiveHintEngine:
       def __init__(self, vector_service, db_manager):
           self.vector_service = vector_service
           self.db = db_manager

       async def generate_hints(
           self,
           user_id: str,
           current_context: dict
       ) -> List[ProactiveHint]:
           """
           Analyse préférences user + contexte actuel
           Retourne suggestions pertinentes
           """
           # 1. Fetch préférences haute confidence (>0.7)
           # 2. Match avec contexte conversation (topics similaires)
           # 3. Score pertinence (0-1)
           # 4. Générer hints (top 3 max)

   @dataclass
   class ProactiveHint:
       id: str
       type: str  # "preference_reminder" | "intent_followup" | "constraint_warning"
       title: str
       message: str
       action_label: Optional[str]
       action_payload: Optional[dict]
       relevance_score: float
       source_preference_id: str
   ```

2. **Intégrer dans ChatService** (`src/backend/features/chat/service.py`)
   ```python
   # Après génération réponse agent, avant envoi WS
   if user_preferences_enabled:
       hints = await proactive_engine.generate_hints(
           user_id=user_id,
           current_context={
               "topic": extract_topic(message),
               "agent": agent_id,
               "conversation_context": last_5_messages
           }
       )

       if hints:
           await connection_manager.send_personal_message(
               session_id=session_id,
               message={
                   "type": "ws:proactive_hint",
                   "hints": [h.to_dict() for h in hints[:3]]  # Max 3
               }
           )
   ```

3. **Tests** (`tests/backend/features/test_proactive_hints.py`)
   ```python
   async def test_hint_generation_preference_match()
   async def test_hint_relevance_scoring()
   async def test_hint_max_limit_3()
   async def test_hint_websocket_emission()
   ```

**Livrables** :
- `ProactiveHintEngine` fonctionnel
- Intégration ChatService
- Event WS `ws:proactive_hint`
- Tests unitaires (4 min)
- Métriques : `memory_proactive_hints_generated_total{type}`

---

#### 🎨 **Sprint 3 : Proactive Hints UI + Dashboard Mémoire (2-3 jours)**

**Frontend** :

1. **Composant Hints** (`src/frontend/features/memory/proactive-hints.js`)
   ```javascript
   class ProactiveHintsUI {
       init() {
           this.container = document.getElementById('proactive-hints-container');
           EventBus.on('ws:proactive_hint', (data) => {
               this.displayHints(data.hints);
           });
       }

       displayHints(hints) {
           // Badge discret coin supérieur droit
           // Clic → dropdown suggestions
           // Actions : "Appliquer", "Ignorer", "Rappeler plus tard"
       }
   }
   ```

2. **Dashboard Mémoire** (`src/frontend/features/memory/memory-dashboard.js`)
   ```javascript
   // Page dédiée /memory-dashboard
   class MemoryDashboard {
       async loadData() {
           // 1. Préférences capturées (table triable)
           // 2. Concepts LTM (nuage tags pondéré)
           // 3. Threads archivés consolidés (timeline)
           // 4. Stats : taux rappel, précision extraction
       }
   }
   ```

3. **Intégration Menu**
   ```html
   <!-- src/frontend/index.html -->
   <nav>
       <a href="/memory-dashboard">🧠 Ma Mémoire</a>
   </nav>
   ```

**Livrables** :
- UI hints proactifs fonctionnelle
- Dashboard mémoire complet
- Tests E2E (Playwright)
- Documentation utilisateur

---

## 🐛 Bugs Détectés à Corriger (Priorité Haute)

### 🔴 Bug #1 : Coûts Gemini = 0 (Sous-estimation 70-80%)

**Localisation** : [llm_stream.py:178-180](src/backend/features/chat/llm_stream.py#L178-L180)

**Problème** :
```python
# Ligne 178-180 - INCORRECT
cost_info_container.setdefault("input_tokens", 0)   # ← Toujours 0
cost_info_container.setdefault("output_tokens", 0)  # ← Toujours 0
cost_info_container.setdefault("total_cost", 0.0)   # ← Toujours 0
```

**Cause** : Google Generative AI ne retourne PAS `usage` en streaming, contrairement à OpenAI.

**Solution** :
```python
async def _get_gemini_stream(self, model, system_prompt, history, cost_info_container):
    _model = genai.GenerativeModel(model_name=model, system_instruction=system_prompt)

    # COUNT TOKENS INPUT (avant génération)
    prompt_parts = [system_prompt] + [msg.get("content", "") for msg in history]
    input_tokens = _model.count_tokens(prompt_parts).total_tokens

    # Génération streaming
    resp = await _model.generate_content_async(history, stream=True, ...)
    full_response_text = ""
    async for chunk in resp:
        text = getattr(chunk, "text", None)
        if text:
            full_response_text += text
            yield text

    # COUNT TOKENS OUTPUT (après génération)
    output_tokens = _model.count_tokens(full_response_text).total_tokens

    # CALCUL COÛT
    pricing = MODEL_PRICING.get(model, {"input": 0, "output": 0})
    cost_info_container.update({
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_cost": (input_tokens * pricing["input"]) + (output_tokens * pricing["output"])
    })
```

**Validation** :
```bash
# Après fix
python -m pytest tests/backend/features/test_llm_costs.py -v
sqlite3 emergence.db "SELECT model, total_cost FROM costs WHERE model LIKE '%gemini%' LIMIT 5;"
# Vérifier total_cost > 0
```

**Impact** : Critique - Gemini = 70-80% du trafic, sous-estimation massive coûts.

---

### 🟡 Bug #2 : Gap #3 Architecture Hybride (Refactoring P2)

**Problème** : Mode batch `tend_the_garden()` sans `thread_id` utilise table `sessions` legacy au lieu de `threads` modernes.

**Code actuel** :
```python
# gardener.py:549-568
sessions = await self._fetch_recent_sessions(limit=consolidation_limit)
for s in sessions:
    history = self._extract_history(s.get("session_data"))  # ← JSON legacy
```

**Solution recommandée** : Migrer vers threads
```python
# Nouveau mode batch (à implémenter)
threads = await queries.get_threads(
    db,
    user_id=user_id,
    include_archived=False,  # Seulement actifs en batch
    limit=consolidation_limit
)

for thread in threads:
    await self._tend_single_thread(
        thread_id=thread["id"],
        session_id=thread["session_id"],
        user_id=thread["user_id"]
    )
```

**Décision requise** :
- Option A : Migration complète (recommandé, 2-3 jours)
- Option B : Maintenir hybride + sync explicite

**Action** : Créer ADR (Architecture Decision Record) et soumettre à validation avant implémentation.

---

## 📊 Métriques Succès Phase P2

| Objectif | KPI Actuel | Target P2 | Outil Mesure |
|----------|-----------|-----------|--------------|
| **Latence requêtes ChromaDB** | 100-200ms | <50ms | `memory_query_duration_seconds` |
| **Cache hit rate préférences** | 0% (pas utilisé) | >80% | `memory_cache_hit_rate` |
| **Hints proactifs générés** | 0 | >5/jour/user | `memory_proactive_hints_generated_total` |
| **Précision extraction préférences** | ~75% | >85% | Tests corpus annotés |
| **Threads archivés consolidés** | 0% | 100% | SQL vs ChromaDB count |

---

## 🚀 Comment Démarrer la Session

### 1. Relire le Contexte (10 min)
```bash
# Lire ces 3 docs dans l'ordre
cat docs/validation/P0_GAPS_RESOLUTION_STATUS.md
cat docs/optimizations/MEMORY_P2_PERFORMANCE_PLAN.md
cat docs/cockpit/COCKPIT_GAPS_AND_FIXES.md
```

### 2. Vérifier l'Environnement (5 min)
```bash
# Backend
python -m pytest tests/backend/features/ -k "memory" -v --tb=short
# Doit afficher : 30+ tests passants

# Vérifier ChromaDB
python -c "from src.backend.features.memory.vector_service import VectorService; print('✅ VectorService OK')"

# Vérifier TaskQueue
python -c "from src.backend.features.memory.task_queue import MemoryTaskQueue; print('✅ TaskQueue OK')"
```

### 3. Prioriser les Actions
**Ordre recommandé** :
1. 🔴 **URGENT** : Fixer Bug #1 (coûts Gemini) → 1-2h
2. 🏆 **Sprint 1** : Indexation ChromaDB + validation cache → 1-2 jours
3. 🎯 **Sprint 2** : Proactive hints backend → 2-3 jours
4. 🎨 **Sprint 3** : Proactive hints UI + dashboard → 2-3 jours
5. 🟡 **Refactoring** : Gap #3 architecture (après validation FG)

### 4. Créer Todo List
```javascript
// Utiliser TodoWrite pour tracker
[
  {
    "content": "🔴 URGENT - Fixer coûts Gemini (count_tokens manquant)",
    "status": "in_progress",
    "activeForm": "Fix calcul coûts Gemini"
  },
  {
    "content": "Créer index ChromaDB (user_id, type, confidence)",
    "status": "pending",
    "activeForm": "Création index ChromaDB"
  },
  {
    "content": "Valider cache préférences (_fetch_active_preferences_cached)",
    "status": "pending",
    "activeForm": "Validation cache préférences"
  },
  // ... etc
]
```

### 5. Commencer par le Bug Critique
```python
# Ouvrir llm_stream.py et chercher _get_gemini_stream
# Appliquer le fix documenté ci-dessus
# Lancer tests
python -m pytest tests/backend/features/test_llm_costs.py -v -k gemini
```

---

## 📁 Fichiers Clés à Connaître

### Backend Mémoire
- `src/backend/features/memory/analyzer.py` - MemoryAnalyzer + PreferenceExtractor
- `src/backend/features/memory/gardener.py` - MemoryGardener (consolidation)
- `src/backend/features/memory/vector_service.py` - ChromaDB + SBERT
- `src/backend/features/memory/task_queue.py` - MemoryTaskQueue (async)
- `src/backend/features/memory/router.py` - Endpoints API mémoire
- `src/backend/features/chat/memory_ctx.py` - MemoryContextBuilder (injection RAG)

### Backend Chat/LLM
- `src/backend/features/chat/service.py` - ChatService (orchestration)
- `src/backend/features/chat/llm_stream.py` - 🔴 **BUG ICI** (coûts Gemini)
- `src/backend/features/chat/pricing.py` - MODEL_PRICING (tarifs)

### Frontend
- `src/frontend/features/memory/memory.js` - UI mémoire existante
- `src/frontend/features/chat/chat-ui.js` - Chat (où intégrer hints)
- `src/frontend/core/event-bus.js` - EventBus (écouter ws:proactive_hint)

### Tests
- `tests/backend/features/test_memory_preferences_persistence.py` - 20 tests ✅
- `tests/backend/features/test_memory_archived_consolidation.py` - 10 tests ✅
- `tests/backend/features/test_preference_extraction_context.py` - 8 tests ✅

### Documentation
- `docs/validation/P0_GAPS_RESOLUTION_STATUS.md` - État P0 (créé cette session)
- `docs/optimizations/MEMORY_P2_PERFORMANCE_PLAN.md` - Plan P2 détaillé
- `docs/architecture/MEMORY_LTM_GAPS_ANALYSIS.md` - Analyse gaps initiale
- `docs/MEMORY_CAPABILITIES.md` - Capacités système
- `docs/memory-roadmap.md` - Roadmap globale

---

## 🎯 Objectifs de la Session

**Minimum Viable** (1 journée) :
- ✅ Bug #1 coûts Gemini fixé + testé
- ✅ Index ChromaDB créés
- ✅ Cache préférences validé (hit rate mesuré)
- ✅ Tests performance (3 tests min)

**Optimal** (2-3 jours) :
- ✅ Tout le Sprint 1 complété
- ✅ ProactiveHintEngine backend démarré
- ✅ Event WS `ws:proactive_hint` fonctionnel

**Stretch Goal** (1 semaine) :
- ✅ Sprint 1 + 2 + 3 complets
- ✅ Dashboard mémoire UI opérationnel
- ✅ Tests E2E Playwright
- ✅ Métriques Prometheus complètes

---

## ⚠️ Points d'Attention

### Performance
- **ChromaDB** : Indexation = gains 4-5x latence (200ms → 50ms)
- **Cache** : Hit rate >80% critique pour UX fluide
- **Batch prefetch** : Éviter N+1 queries (1 batch vs 10 incrémentales)

### Architecture
- **Gap #3** : NE PAS modifier sans validation FG (risque breaking changes)
- **ProactiveHints** : Max 3 hints simultanés (éviter spam)
- **WebSocket** : Hints envoyés APRÈS réponse agent (pas avant)

### Tests
- **Toujours** lancer tests avant commit : `python -m pytest tests/backend/features/ -k memory -v`
- **Performance** : Ajouter benchmarks (pytest-benchmark)
- **E2E** : Utiliser Playwright pour UI hints

### Métriques
- **Prometheus** : Toutes nouvelles métriques doivent avoir buckets adaptés
- **Logs** : Logger niveau INFO pour hints générés (debug traces)

---

## 📞 Ressources & Support

### Documentation Externe
- ChromaDB indexing : https://docs.trychroma.com/guides/performance#indexing
- Prometheus histograms : https://prometheus.io/docs/practices/histograms/
- pytest-asyncio : https://pytest-asyncio.readthedocs.io/

### Commandes Utiles
```bash
# Tests mémoire complets
python -m pytest tests/backend/features/ -k memory -v --tb=short

# Vérifier métriques Prometheus
curl http://localhost:8000/api/metrics | grep memory_

# Inspecter ChromaDB
python scripts/inspect_chromadb.py --collection emergence_knowledge --limit 10

# Profiling performance
python -m cProfile -o profile.stats src/backend/main.py
python -m pstats profile.stats
```

---

## ✅ Checklist Avant de Terminer la Session

### Code
- [ ] Bug #1 (coûts Gemini) fixé et testé
- [ ] Index ChromaDB créés et validés
- [ ] Cache préférences hit rate >80%
- [ ] Tests performance ajoutés (min 3)
- [ ] Tous tests passent (pytest -v)

### Documentation
- [ ] Mettre à jour [memory-roadmap.md](docs/memory-roadmap.md) avec avancement
- [ ] Documenter nouvelles métriques Prometheus
- [ ] Créer ADR pour Gap #3 si abordé
- [ ] Mettre à jour [docs/passation.md](docs/passation.md)

### Git
- [ ] Commits atomiques avec messages clairs
- [ ] Branch `feat/memory-p2-sprint1` (ou équivalent)
- [ ] Push réguliers (éviter perte travail)
- [ ] PR description détaillée si merge

### Handover
- [ ] Créer `PROMPT_NEXT_SESSION_*.md` pour session suivante
- [ ] Lister blocages/décisions en attente
- [ ] Documenter TODO restants avec priorités

---

## 🚀 Let's Go!

**Première action recommandée** :
```bash
# 1. Lire statut P0
cat docs/validation/P0_GAPS_RESOLUTION_STATUS.md

# 2. Fixer bug critique
code src/backend/features/chat/llm_stream.py
# → Chercher ligne 178, appliquer fix count_tokens

# 3. Tester
python -m pytest tests/backend/features/ -k gemini -v

# 4. Créer todo list
# Utiliser TodoWrite pour tracker progression
```

**Bon courage ! 💪**

---

**Version** : 1.0
**Auteur** : Claude Code (session 2025-10-10)
**Prochaine session** : Démarrer par Bug #1 puis Sprint 1 P2
