# 🧠 PROMPT P1 : ENRICHISSEMENT MÉMOIRE & DÉPORTATION ASYNCHRONE

**Date** : 2025-10-09
**Phase** : P1 - Hors boucle WS & enrichissement conceptuel
**Prérequis** : P0 validée ✅, Phase 2 validée ✅, Phase 3 déployée ✅
**Contexte** : [docs/memory-roadmap.md](docs/memory-roadmap.md)

---

## 📋 CONTEXTE

Bonjour Claude,

Tu travailles sur ÉMERGENCE V8, un système de conversation avec mémoire sémantique à long terme.

### État actuel (P0 + Phases 2-3 validées)

**✅ Ce qui fonctionne** :
- Persistance messages & restauration session (P0)
- Analyse mémoire avec `neo_analysis` (gpt-4o-mini) : 4-6s
- Cache BDD : 0.177s (26x plus rapide)
- Métriques Prometheus : 13 métriques exposées en production
- `MemoryGardener` extrait concepts "mot-code" et les vectorise
- Mécanisme d'oubli par vitalité (decay + purge)

**⚠️ Limitations identifiées** :
1. Analyse/vectorisation dans la boucle WS → risque blocage event loop
2. Extraction limitée aux "mot-code" → manque préférences, intentions, contraintes
3. Pas de signalement proactif des concepts récurrents
4. Métriques cache non instrumentées (WIP session parallèle)

---

## 🎯 MISSION P1

Implémenter **Phase P1 - Enrichissement conceptuel & déportation asynchrone** en 3 volets :

### 🔴 P1.1 - Déportation hors boucle WS (PRIORITÉ HAUTE)
Éviter blocages event loop en déportant tâches lourdes.

### 🟡 P1.2 - Extension extraction de faits (PRIORITÉ MOYENNE)
Capturer préférences, intentions, contraintes utilisateur.

### 🟢 P1.3 - Instrumentation métriques (PRIORITÉ BASSE)
Compléter métriques cache + nouveau pipeline préférences.

---

## 📦 P1.1 - DÉPORTATION ASYNCHRONE (3-4h)

### Objectif
Déporter `MemoryAnalyzer` et `MemoryGardener` dans une file de tâches pour éviter blocage event loop WebSocket.

### Approche recommandée

**Option A : asyncio.create_task() + Queue (Simple)**
- File `asyncio.Queue` pour tâches d'analyse
- Worker background consomme la queue
- Pas de dépendance externe

**Option B : Celery + Redis (Production)**
- File distribuée Redis
- Workers multi-processus
- Retry automatique
- Monitoring intégré

**Recommandation** : Commencer par **Option A** (asyncio), migrer vers **Option B** si scaling requis.

### Fichiers à modifier

#### 1. Créer `src/backend/features/memory/task_queue.py`

```python
"""
File de tâches asynchrone pour MemoryAnalyzer et MemoryGardener.
Évite blocage event loop WebSocket.
"""

import asyncio
import logging
from typing import Callable, Any
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class MemoryTask:
    """Tâche d'analyse/jardinage mémoire"""
    task_type: str  # "analyze" | "garden"
    payload: dict
    callback: Callable | None = None
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()


class MemoryTaskQueue:
    """
    File de tâches asynchrone pour opérations mémoire lourdes.

    Usage:
        queue = MemoryTaskQueue()
        await queue.start()
        await queue.enqueue("analyze", {"session_id": "..."})
    """

    def __init__(self, max_workers: int = 2):
        self.queue: asyncio.Queue = asyncio.Queue()
        self.max_workers = max_workers
        self.workers: list[asyncio.Task] = []
        self.running = False

    async def start(self):
        """Démarre les workers de traitement"""
        if self.running:
            return

        self.running = True
        for i in range(self.max_workers):
            worker = asyncio.create_task(self._worker(i))
            self.workers.append(worker)
        logger.info(f"MemoryTaskQueue started with {self.max_workers} workers")

    async def stop(self):
        """Arrête proprement les workers"""
        self.running = False

        # Envoyer signal arrêt
        for _ in range(self.max_workers):
            await self.queue.put(None)

        # Attendre fin workers
        await asyncio.gather(*self.workers, return_exceptions=True)
        logger.info("MemoryTaskQueue stopped")

    async def enqueue(self, task_type: str, payload: dict, callback: Callable = None):
        """Ajoute une tâche à la file"""
        task = MemoryTask(task_type=task_type, payload=payload, callback=callback)
        await self.queue.put(task)
        logger.debug(f"Task enqueued: {task_type} - {payload.get('session_id', 'N/A')}")

    async def _worker(self, worker_id: int):
        """Worker qui consomme la file"""
        logger.info(f"Worker {worker_id} started")

        while self.running:
            try:
                # Attendre tâche (timeout pour vérifier self.running)
                task = await asyncio.wait_for(self.queue.get(), timeout=1.0)

                if task is None:  # Signal arrêt
                    break

                # Traiter tâche
                await self._process_task(task, worker_id)

            except asyncio.TimeoutError:
                continue  # Pas de tâche, continuer
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}", exc_info=True)

        logger.info(f"Worker {worker_id} stopped")

    async def _process_task(self, task: MemoryTask, worker_id: int):
        """Traite une tâche mémoire"""
        start = datetime.utcnow()

        try:
            if task.task_type == "analyze":
                result = await self._run_analysis(task.payload)
            elif task.task_type == "garden":
                result = await self._run_gardening(task.payload)
            else:
                logger.warning(f"Unknown task type: {task.task_type}")
                return

            duration = (datetime.utcnow() - start).total_seconds()
            logger.info(f"Worker {worker_id} completed {task.task_type} in {duration:.2f}s")

            # Callback si fourni
            if task.callback:
                await task.callback(result)

        except Exception as e:
            logger.error(f"Task {task.task_type} failed: {e}", exc_info=True)

    async def _run_analysis(self, payload: dict):
        """Exécute MemoryAnalyzer.analyze_session"""
        from backend.features.memory.analyzer import MemoryAnalyzer
        from backend.containers import Container

        analyzer = Container.memory_analyzer()
        session_id = payload["session_id"]
        force = payload.get("force", False)

        result = await analyzer.analyze_session(session_id, force=force)
        return result

    async def _run_gardening(self, payload: dict):
        """Exécute MemoryGardener.garden_thread"""
        from backend.features.memory.gardener import MemoryGardener
        from backend.containers import Container

        gardener = Container.memory_gardener()
        thread_id = payload["thread_id"]
        user_sub = payload.get("user_sub")

        await gardener.garden_thread(thread_id, user_sub=user_sub)
        return {"status": "gardened", "thread_id": thread_id}


# Singleton global
_task_queue: MemoryTaskQueue | None = None

def get_memory_queue() -> MemoryTaskQueue:
    """Récupère l'instance globale de la file"""
    global _task_queue
    if _task_queue is None:
        _task_queue = MemoryTaskQueue(max_workers=2)
    return _task_queue
```

#### 2. Modifier `src/backend/features/memory/analyzer.py`

**Ajouter méthode asynchrone** :

```python
# Vers ligne 200, après analyze_session()

async def analyze_session_async(
    self,
    session_id: str,
    force: bool = False,
    callback: Callable = None
) -> None:
    """
    Version asynchrone non-bloquante de analyze_session.
    Enqueue tâche dans MemoryTaskQueue.

    Args:
        session_id: ID session à analyser
        force: Forcer nouvelle analyse
        callback: Fonction appelée avec résultat
    """
    from backend.features.memory.task_queue import get_memory_queue

    queue = get_memory_queue()
    await queue.enqueue(
        task_type="analyze",
        payload={"session_id": session_id, "force": force},
        callback=callback
    )

    logger.info(f"Analyse session {session_id} enqueued (async)")
```

#### 3. Modifier `src/backend/main.py` (Lifecycle)

**Démarrer/arrêter queue** :

```python
# Après ligne 50 (startup)

@app.on_event("startup")
async def startup():
    """Démarrage application"""
    logger.info("Starting Emergence Backend...")

    # Démarrer MemoryTaskQueue
    from backend.features.memory.task_queue import get_memory_queue
    queue = get_memory_queue()
    await queue.start()
    logger.info("MemoryTaskQueue started")

@app.on_event("shutdown")
async def shutdown():
    """Arrêt application"""
    logger.info("Shutting down Emergence Backend...")

    # Arrêter MemoryTaskQueue
    from backend.features.memory.task_queue import get_memory_queue
    queue = get_memory_queue()
    await queue.stop()
    logger.info("MemoryTaskQueue stopped")
```

#### 4. Modifier appels bloquants (WebSocket, routes)

**Exemple dans `src/backend/features/chat/service.py`** :

```python
# Remplacer (ligne ~850) :
# result = await memory_analyzer.analyze_session(session_id)

# Par :
await memory_analyzer.analyze_session_async(
    session_id=session_id,
    callback=lambda res: logger.info(f"Analysis completed: {res['status']}")
)
```

### Tests P1.1

```python
# tests/memory/test_task_queue.py

import pytest
import asyncio
from backend.features.memory.task_queue import MemoryTaskQueue, MemoryTask

@pytest.mark.asyncio
async def test_queue_starts_workers():
    queue = MemoryTaskQueue(max_workers=2)
    await queue.start()

    assert len(queue.workers) == 2
    assert queue.running is True

    await queue.stop()

@pytest.mark.asyncio
async def test_enqueue_analyze_task():
    queue = MemoryTaskQueue()
    await queue.start()

    result = []

    async def callback(res):
        result.append(res)

    await queue.enqueue(
        "analyze",
        {"session_id": "test-123", "force": True},
        callback=callback
    )

    # Attendre traitement (max 5s)
    for _ in range(50):
        if result:
            break
        await asyncio.sleep(0.1)

    await queue.stop()

    assert len(result) == 1
    assert result[0]["session_id"] == "test-123"
```

### Critères de succès P1.1

- ✅ File `MemoryTaskQueue` créée et testée
- ✅ Workers démarrent/arrêtent proprement
- ✅ `analyze_session_async()` enqueue sans bloquer
- ✅ Tests unitaires passent
- ✅ Aucun blocage event loop WebSocket (mesure latence WS <100ms)

---

## 📦 P1.2 - EXTENSION EXTRACTION DE FAITS (6-8h)

### Objectif
Capturer préférences, intentions, contraintes utilisateur au-delà des "mot-code".

### Pipeline hybride

**Étape 1 : Filtrage lexical**
Détecter phrases avec verbes cibles avant appel LLM.

**Étape 2 : Classification LLM**
Catégoriser en `preference`, `intent`, `constraint`, `neutral`.

**Étape 3 : Normalisation**
Extraire `topic`, `action`, `timeframe`, `entities`.

### Fichiers à créer

#### 1. `src/backend/features/memory/preference_extractor.py`

```python
"""
Extracteur de préférences, intentions et contraintes utilisateur.
Pipeline hybride : filtrage lexical + classification LLM + normalisation.
"""

import re
import logging
from typing import List, Dict, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)

# Verbes cibles pour filtrage lexical
PREFERENCE_VERBS = {
    "fr": ["préfér", "aim", "déteste", "adore", "appréci", "favoris"],
    "en": ["prefer", "like", "love", "hate", "enjoy", "favorite"]
}

INTENT_VERBS = {
    "fr": ["vouloir", "veux", "souhaite", "planifie", "prévoi", "décide", "compte"],
    "en": ["want", "wish", "plan", "intend", "decide", "will", "going to"]
}

CONSTRAINT_VERBS = {
    "fr": ["évite", "refuse", "jamais", "interdit", "ne pas", "impossible"],
    "en": ["avoid", "refuse", "never", "forbidden", "don't", "cannot"]
}


@dataclass
class PreferenceRecord:
    """Enregistrement préférence/intention/contrainte"""
    id: str  # Hash MD5 court
    type: str  # "preference" | "intent" | "constraint" | "neutral"
    topic: str  # Sujet normalisé
    action: str  # Verbe infinitif
    text: str  # Texte original
    timeframe: str  # ISO 8601 ou "ongoing"
    sentiment: str  # "positive" | "negative" | "neutral"
    confidence: float  # 0.0-1.0
    entities: List[str]  # Personnes, outils, lieux
    source_message_id: str
    thread_id: str
    captured_at: str  # ISO timestamp

    @staticmethod
    def generate_id(user_sub: str, topic: str, type_: str) -> str:
        """Génère ID unique basé sur (user_sub, topic, type)"""
        key = f"{user_sub}:{topic}:{type_}"
        return hashlib.md5(key.encode()).hexdigest()[:12]


class PreferenceExtractor:
    """
    Extracteur de préférences/intentions/contraintes.

    Usage:
        extractor = PreferenceExtractor(llm_client)
        records = await extractor.extract(messages, user_sub="user123")
    """

    def __init__(self, llm_client):
        self.llm = llm_client
        self.stats = {"extracted": 0, "filtered": 0, "classified": 0}

    async def extract(
        self,
        messages: List[Dict],
        user_sub: str,
        thread_id: str
    ) -> List[PreferenceRecord]:
        """
        Extrait préférences/intentions depuis messages.

        Args:
            messages: Liste messages (role, content, id)
            user_sub: ID utilisateur
            thread_id: ID thread

        Returns:
            Liste PreferenceRecord avec confidence > 0.6
        """
        records = []

        # Filtrer messages utilisateur
        user_messages = [m for m in messages if m.get("role") == "user"]

        for msg in user_messages:
            content = msg.get("content", "")
            msg_id = msg.get("id", "unknown")

            # Étape 1 : Filtrage lexical
            if not self._contains_target_verbs(content):
                self.stats["filtered"] += 1
                continue

            # Étape 2 : Classification LLM
            classification = await self._classify_llm(content)
            self.stats["classified"] += 1

            if classification["type"] == "neutral":
                continue

            if classification["confidence"] < 0.6:
                logger.debug(f"Low confidence {classification['confidence']:.2f}: {content[:50]}")
                continue

            # Étape 3 : Normalisation
            record = PreferenceRecord(
                id=PreferenceRecord.generate_id(user_sub, classification["topic"], classification["type"]),
                type=classification["type"],
                topic=classification["topic"],
                action=classification["action"],
                text=content,
                timeframe=classification.get("timeframe", "ongoing"),
                sentiment=classification.get("sentiment", "neutral"),
                confidence=classification["confidence"],
                entities=classification.get("entities", []),
                source_message_id=msg_id,
                thread_id=thread_id,
                captured_at=datetime.utcnow().isoformat()
            )

            records.append(record)
            self.stats["extracted"] += 1

        logger.info(f"Extracted {len(records)} preferences/intents (filtered: {self.stats['filtered']}, classified: {self.stats['classified']})")
        return records

    def _contains_target_verbs(self, text: str) -> bool:
        """Filtre lexical : contient verbes cibles ?"""
        text_lower = text.lower()

        all_verbs = (
            PREFERENCE_VERBS["fr"] + PREFERENCE_VERBS["en"] +
            INTENT_VERBS["fr"] + INTENT_VERBS["en"] +
            CONSTRAINT_VERBS["fr"] + CONSTRAINT_VERBS["en"]
        )

        return any(verb in text_lower for verb in all_verbs)

    async def _classify_llm(self, text: str) -> Dict[str, Any]:
        """
        Classification LLM (gpt-4o-mini ou claude-3-haiku).

        Returns:
            {
                "type": "preference" | "intent" | "constraint" | "neutral",
                "topic": "programmation",
                "action": "apprendre",
                "timeframe": "ongoing",
                "sentiment": "positive",
                "confidence": 0.85,
                "entities": ["Python", "FastAPI"]
            }
        """
        prompt = f"""Tu es un extracteur de préférences utilisateur.

Analyse ce message et extrait :
- **type** : "preference" (goût, habitude), "intent" (action future), "constraint" (limite), ou "neutral"
- **topic** : Sujet principal (1-3 mots)
- **action** : Verbe principal (infinitif)
- **timeframe** : Date ISO 8601 si mentionnée, sinon "ongoing"
- **sentiment** : "positive", "negative", "neutral"
- **confidence** : Score 0.0-1.0 (certitude extraction)
- **entities** : Noms propres, outils, lieux (liste)

Message : "{text}"

Réponds UNIQUEMENT en JSON valide :
{{"type": "...", "topic": "...", "action": "...", "timeframe": "...", "sentiment": "...", "confidence": 0.0, "entities": []}}"""

        try:
            # Appel LLM (gpt-4o-mini par défaut)
            response = await self.llm.generate(
                prompt=prompt,
                model="gpt-4o-mini",
                temperature=0.1,
                response_format="json"
            )

            import json
            result = json.loads(response)

            # Normalisation clés (prévention localisation)
            return {
                "type": result.get("type", "neutral"),
                "topic": result.get("topic", "unknown"),
                "action": result.get("action", ""),
                "timeframe": result.get("timeframe", "ongoing"),
                "sentiment": result.get("sentiment", "neutral"),
                "confidence": float(result.get("confidence", 0.5)),
                "entities": result.get("entities", [])
            }

        except Exception as e:
            logger.error(f"LLM classification failed: {e}")
            return {
                "type": "neutral",
                "topic": "unknown",
                "action": "",
                "timeframe": "ongoing",
                "sentiment": "neutral",
                "confidence": 0.0,
                "entities": []
            }
```

#### 2. Modifier `src/backend/features/memory/gardener.py`

**Ajouter extraction préférences** :

```python
# Vers ligne 150, dans garden_thread()

async def garden_thread(self, thread_id: str, user_sub: str = None):
    """Jardinage thread : concepts + préférences"""

    # Extraction concepts (existant)
    concepts = await self.extract_concepts(nodes)

    # 🆕 Extraction préférences/intentions
    from backend.features.memory.preference_extractor import PreferenceExtractor

    extractor = PreferenceExtractor(self.llm_client)
    preferences = await extractor.extract(
        messages=nodes,
        user_sub=user_sub or "anonymous",
        thread_id=thread_id
    )

    # Vectoriser préférences
    if preferences:
        await self._vectorize_preferences(preferences, user_sub)
        logger.info(f"Vectorized {len(preferences)} preferences for thread {thread_id}")

async def _vectorize_preferences(self, records: List[PreferenceRecord], user_sub: str):
    """Vectorise préférences dans collection dédiée"""
    from backend.features.memory.preference_extractor import PreferenceRecord

    collection_name = f"memory_preferences_{user_sub}"

    for rec in records:
        # Embedding du texte + topic
        text_to_embed = f"{rec.topic}: {rec.text}"
        embedding = await self.embedder.embed(text_to_embed)

        # Stocker avec métadonnées
        await self.vector_store.upsert(
            collection=collection_name,
            id=rec.id,
            vector=embedding,
            metadata={
                "type": rec.type,
                "topic": rec.topic,
                "action": rec.action,
                "timeframe": rec.timeframe,
                "sentiment": rec.sentiment,
                "confidence": rec.confidence,
                "entities": rec.entities,
                "source_message_id": rec.source_message_id,
                "thread_id": rec.thread_id,
                "captured_at": rec.captured_at
            }
        )
```

### Tests P1.2

```python
# tests/memory/test_preference_extractor.py

import pytest
from backend.features.memory.preference_extractor import PreferenceExtractor, PreferenceRecord

@pytest.fixture
def mock_llm():
    class MockLLM:
        async def generate(self, **kwargs):
            return '{"type": "preference", "topic": "Python", "action": "apprendre", "timeframe": "ongoing", "sentiment": "positive", "confidence": 0.9, "entities": ["FastAPI"]}'
    return MockLLM()

@pytest.mark.asyncio
async def test_extract_preference(mock_llm):
    extractor = PreferenceExtractor(mock_llm)

    messages = [
        {"role": "user", "content": "Je préfère Python à Java", "id": "msg1"},
        {"role": "assistant", "content": "Compris", "id": "msg2"}
    ]

    records = await extractor.extract(messages, user_sub="user123", thread_id="thread1")

    assert len(records) == 1
    assert records[0].type == "preference"
    assert records[0].topic == "Python"
    assert records[0].confidence >= 0.6

@pytest.mark.asyncio
async def test_lexical_filtering(mock_llm):
    extractor = PreferenceExtractor(mock_llm)

    messages = [
        {"role": "user", "content": "Bonjour comment ça va ?", "id": "msg1"}
    ]

    records = await extractor.extract(messages, user_sub="user123", thread_id="thread1")

    assert len(records) == 0  # Filtré (pas de verbe cible)
    assert extractor.stats["filtered"] == 1
```

### Critères de succès P1.2

- ✅ `PreferenceExtractor` créé et testé
- ✅ Filtrage lexical réduit appels LLM de >70%
- ✅ Classification LLM atteint précision >0.85 (corpus validation)
- ✅ Vectorisation dans collection `memory_preferences_{user_sub}`
- ✅ Déduplication par `(user_sub, topic, type)` fonctionne
- ✅ Tests unitaires passent

---

## 📦 P1.3 - INSTRUMENTATION MÉTRIQUES (1-2h)

### Objectif
Compléter métriques Prometheus pour cache + nouveau pipeline préférences.

### Métriques à ajouter

#### Cache (3 métriques manquantes)

```python
# src/backend/features/memory/analyzer.py

from prometheus_client import Counter, Gauge

CACHE_HITS_TOTAL = Counter(
    "memory_analysis_cache_hits_total",
    "Nombre total de cache hits"
)

CACHE_MISSES_TOTAL = Counter(
    "memory_analysis_cache_misses_total",
    "Nombre total de cache misses"
)

CACHE_SIZE = Gauge(
    "memory_analysis_cache_size",
    "Taille actuelle du cache in-memory"
)

# Dans analyze_session() :
if hash_key in _ANALYSIS_CACHE:
    CACHE_HITS_TOTAL.inc()  # 🆕
    return cached_result
else:
    CACHE_MISSES_TOTAL.inc()  # 🆕

# Après ajout au cache :
CACHE_SIZE.set(len(_ANALYSIS_CACHE))  # 🆕
```

#### Préférences (5 nouvelles métriques)

```python
# src/backend/features/memory/preference_extractor.py

from prometheus_client import Counter, Histogram

PREFERENCES_EXTRACTED_TOTAL = Counter(
    "memory_preferences_extracted_total",
    "Total préférences/intentions extraites",
    ["type"]  # preference, intent, constraint
)

PREFERENCES_CONFIDENCE = Histogram(
    "memory_preferences_confidence",
    "Distribution scores de confiance",
    buckets=[0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)

PREFERENCES_EXTRACTION_DURATION = Histogram(
    "memory_preferences_extraction_duration_seconds",
    "Durée extraction préférences",
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0]
)

# Dans extract() :
PREFERENCES_EXTRACTED_TOTAL.labels(type=record.type).inc()
PREFERENCES_CONFIDENCE.observe(record.confidence)
PREFERENCES_EXTRACTION_DURATION.observe(duration)
```

### Tests métriques

```bash
# Générer données
curl -X POST http://localhost:8000/api/memory/analyze \
  -d '{"session_id":"test", "force":true}'

# Vérifier métriques
curl http://localhost:8000/api/metrics | grep -E "cache|preference"

# Attendu :
# memory_analysis_cache_hits_total 1.0
# memory_analysis_cache_misses_total 2.0
# memory_preferences_extracted_total{type="preference"} 5.0
```

### Critères de succès P1.3

- ✅ 3 métriques cache instrumentées
- ✅ 5 métriques préférences instrumentées
- ✅ Compteurs incrémentent correctement en tests
- ✅ Histogrammes capturent distributions
- ✅ Dashboard Grafana mis à jour

---

## 📊 ORDRE D'EXÉCUTION RECOMMANDÉ

### Semaine 1 : Déportation asynchrone (P1.1)
**Durée** : 3-4h
1. Créer `task_queue.py` (1h)
2. Ajouter `analyze_session_async()` (30min)
3. Modifier lifecycle `main.py` (30min)
4. Tests unitaires (1h)
5. Tests intégration WebSocket (1h)

### Semaine 2 : Extension extraction (P1.2)
**Durée** : 6-8h
1. Créer `preference_extractor.py` (2h)
2. Implémenter filtrage lexical (1h)
3. Implémenter classification LLM (2h)
4. Intégrer dans `MemoryGardener` (1h)
5. Vectorisation collection dédiée (1h)
6. Tests + validation corpus (2h)

### Semaine 3 : Instrumentation (P1.3)
**Durée** : 1-2h
1. Métriques cache (30min)
2. Métriques préférences (30min)
3. Tests métriques (30min)
4. Dashboard Grafana update (30min)

---

## ✅ CHECKLIST FINALE P1

### P1.1 - Déportation
- [ ] `MemoryTaskQueue` créée
- [ ] Workers démarrent/arrêtent
- [ ] `analyze_session_async()` implémentée
- [ ] Tests unitaires passent
- [ ] Latence WebSocket <100ms validée

### P1.2 - Extraction
- [ ] `PreferenceExtractor` créé
- [ ] Filtrage lexical opérationnel
- [ ] Classification LLM >0.85 précision
- [ ] Vectorisation fonctionnelle
- [ ] Déduplication testée
- [ ] Corpus validation (100+50 messages)

### P1.3 - Métriques
- [ ] Cache metrics instrumentées (3)
- [ ] Preferences metrics instrumentées (5)
- [ ] Tests métriques validés
- [ ] Dashboard Grafana mis à jour

---

## 🚀 VALIDATION POST-IMPLÉMENTATION

### Tests end-to-end

```bash
# 1. Démarrer app
python -m uvicorn backend.main:app --reload

# 2. Tester extraction préférences
curl -X POST http://localhost:8000/api/memory/garden \
  -H "Content-Type: application/json" \
  -d '{"thread_id":"thread123","user_sub":"user456"}'

# 3. Vérifier collection vector store
# (doit contenir memory_preferences_user456)

# 4. Vérifier métriques
curl http://localhost:8000/api/metrics | grep preferences

# 5. Tester queue async
# (latence WS <100ms même avec analyse en cours)
```

### Critères globaux de succès P1

- ✅ Event loop WebSocket non bloqué (latence <100ms constante)
- ✅ Préférences/intentions extraites automatiquement
- ✅ Collection `memory_preferences_*` peuplée
- ✅ Précision extraction >0.85, rappel >0.75
- ✅ 8 nouvelles métriques Prometheus exposées
- ✅ Tests unitaires + intégration passent
- ✅ Documentation mise à jour

---

## 📚 RESSOURCES

### Fichiers à lire

1. [docs/memory-roadmap.md](docs/memory-roadmap.md) - Roadmap complète
2. [src/backend/features/memory/analyzer.py](src/backend/features/memory/analyzer.py) - Analyseur actuel
3. [src/backend/features/memory/gardener.py](src/backend/features/memory/gardener.py) - Jardinier actuel
4. [docs/deployments/2025-10-09-validation-phase3-complete.md](docs/deployments/2025-10-09-validation-phase3-complete.md) - État Phase 3

### Documentation à créer

- `docs/memory/p1-task-queue.md` - Architecture file de tâches
- `docs/memory/p1-preference-extraction.md` - Pipeline préférences
- `docs/memory/p1-metrics.md` - Nouvelles métriques

### Commits recommandés

```bash
git commit -m "feat(P1.1): file de tâches asynchrone MemoryTaskQueue"
git commit -m "feat(P1.2): extraction préférences/intentions - pipeline hybride"
git commit -m "feat(P1.3): instrumentation métriques cache + préférences"
git commit -m "docs: P1 enrichissement mémoire - spécification complète"
```

---

## 🆘 TROUBLESHOOTING

### Problème : Workers ne démarrent pas

```python
# Vérifier lifecycle
import logging
logging.basicConfig(level=logging.DEBUG)

# Logs attendus :
# INFO: MemoryTaskQueue started with 2 workers
# INFO: Worker 0 started
# INFO: Worker 1 started
```

### Problème : LLM classification échoue

```python
# Vérifier prompt + response_format
response = await llm.generate(
    prompt=prompt,
    response_format="json",  # 🔥 Critique pour OpenAI
    temperature=0.1
)

# Ajouter fallback
try:
    result = json.loads(response)
except json.JSONDecodeError:
    logger.error(f"Invalid JSON: {response}")
    return {"type": "neutral", ...}
```

### Problème : Collection vector store non créée

```python
# Vérifier backend vector store
if vector_store.backend == "chroma":
    # Collections auto-créées
    pass
elif vector_store.backend == "qdrant":
    # Créer manuellement
    await vector_store.create_collection(
        name=f"memory_preferences_{user_sub}",
        vector_size=1536  # text-embedding-3-large
    )
```

---

## 🎯 OBJECTIF FINAL

À la fin de P1, tu auras :

1. ✅ **File de tâches asynchrone** évitant blocages event loop
2. ✅ **Pipeline enrichi** capturant préférences/intentions/contraintes
3. ✅ **Collection vectorielle** dédiée avec métadonnées riches
4. ✅ **8 nouvelles métriques** Prometheus pour monitoring
5. ✅ **Tests validés** (unitaires + intégration + corpus)
6. ✅ **Documentation complète** architecture + usage

**Phase P1 prépare P2 (réactivité proactive)** où les préférences/intentions seront utilisées pour déclencher suggestions contextuelles.

---

**Bon courage pour P1 ! 🚀**

*Généré par Claude Code - 2025-10-09*
*Basé sur [docs/memory-roadmap.md](docs/memory-roadmap.md)*
