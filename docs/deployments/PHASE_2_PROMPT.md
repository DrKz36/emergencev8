# 🚀 PHASE 2 : Optimisation Performance Mémoire & Agents

## 📋 CONTEXTE

Suite à la **Phase 1** (terminée ✅), le système de mémoire temporelle est maintenant fonctionnel :
- ✅ Fix timeout Gemini + triple fallback (Neo → Nexus → Anima)
- ✅ Injection horodatages dans RAG (ex: "Docker (1ère mention: 5 oct, 3 fois)")
- ✅ Détection proactive connexions conceptuelles

**Problème restant** : L'agent **Néo (Gemini)** est **notablement plus lent** que les autres agents (Nexus/Anima), impactant l'UX des débats et analyses.

---

## 🎯 OBJECTIFS PHASE 2

Optimiser les performances pour réduire la latence des agents et des analyses mémoire.

### Gains attendus :
- **-50% latence débats** (6s → 2-3s pour 3 agents)
- **-40% latence analyses** (grâce à modèle dédié)
- **-60% coût API** (cache résumés identiques)

---

## 📝 TÂCHES À RÉALISER

### ✅ **Tâche 1 : Modèle Dédié pour Analyses Mémoire**
**Durée estimée** : 2h | **Priorité** : P1

#### Problème
- Les analyses mémoire (résumés/concepts) utilisent Neo (Gemini) par défaut
- Gemini est lent pour génération JSON structuré (~4-6s)
- OpenAI GPT-4o-mini est **3x plus rapide** pour ce use case (~1-2s)

#### Solution
1. Créer un agent virtuel `neo_analysis` dans la config utilisant GPT-4o-mini
2. Modifier `analyzer.py` pour utiliser `neo_analysis` au lieu de `neo`
3. Conserver les fallbacks Nexus/Anima

#### Fichiers à modifier :

**`src/backend/shared/config.py`** (ligne ~40)
```python
DEFAULT_AGENT_CONFIGS: Dict[str, Dict[str, str]] = {
    "default": {"provider": "google", "model": DEFAULT_GOOGLE_MODEL},
    "neo": {"provider": "google", "model": DEFAULT_GOOGLE_MODEL},
    "neo_analysis": {"provider": "openai", "model": "gpt-4o-mini"},  # ⚡ NOUVEAU
    "nexus": {"provider": "anthropic", "model": "claude-3-5-haiku-20241022"},
    "anima": {"provider": "openai", "model": "gpt-4o-mini"},
}
```

**`src/backend/features/memory/analyzer.py`** (ligne ~159)
```python
# Tentative primaire : neo_analysis (GPT-4o-mini - rapide pour JSON)
try:
    analysis_result = await chat_service.get_structured_llm_response(
        agent_id="neo_analysis",  # ⚡ CHANGÉ (était "neo")
        prompt=prompt,
        json_schema=ANALYSIS_JSON_SCHEMA
    )
    logger.info(f"[MemoryAnalyzer] Analyse réussie avec neo_analysis pour session {session_id}")
except Exception as e:
    primary_error = e
    error_type = type(e).__name__
    logger.warning(
        f"[MemoryAnalyzer] Analyse neo_analysis échouée ({error_type}) — fallback Nexus",
        exc_info=True,
    )
```

#### Tests
```bash
# 1. Vérifier config chargée
python -c "from backend.shared.config import DEFAULT_AGENT_CONFIGS; print(DEFAULT_AGENT_CONFIGS.get('neo_analysis'))"

# 2. Tester analyse mémoire (observer logs provider utilisé)
# POST /api/memory/analyze avec session_id
# Logs attendus: "[MemoryAnalyzer] Analyse réussie avec neo_analysis"
```

---

### ✅ **Tâche 2 : Parallélisation Appels Agents dans Débats**
**Durée estimée** : 3h | **Priorité** : P1

#### Problème
- Les débats appellent les 3 agents **séquentiellement** (Neo → Nexus → Anima)
- Latence totale = somme latences (3s + 2s + 2s = **7s**)
- Possibilité d'exécuter en **parallèle** avec `asyncio.gather()`

#### Solution
Modifier le service de débat pour lancer les appels LLM en parallèle.

#### Fichier à identifier et modifier :

**Étape 1** : Localiser le service de débat
```bash
# Chercher le fichier gérant les débats
grep -r "debate" src/backend/features/ --include="*.py" | grep -i "service\|router"
```

**Étape 2** : Identifier la logique d'appel séquentiel
Chercher un pattern comme :
```python
# ❌ ACTUEL (séquentiel)
response_neo = await chat_service.call_agent("neo", ...)
response_nexus = await chat_service.call_agent("nexus", ...)
response_anima = await chat_service.call_agent("anima", ...)
```

**Étape 3** : Remplacer par appels parallèles
```python
# ✅ OPTIMISÉ (parallèle)
import asyncio

responses = await asyncio.gather(
    chat_service.call_agent("neo", ...),
    chat_service.call_agent("nexus", ...),
    chat_service.call_agent("anima", ...),
    return_exceptions=True  # Continue si un agent fail
)

response_neo, response_nexus, response_anima = responses

# Gérer erreurs individuelles
for i, resp in enumerate(responses):
    if isinstance(resp, Exception):
        logger.warning(f"Agent {['neo', 'nexus', 'anima'][i]} échoué: {resp}")
```

#### Tests
```bash
# 1. Lancer débat 3 agents
# POST /api/chat/debate ou équivalent

# 2. Mesurer latence totale (logs ou métriques)
# Avant: ~7s | Après: ~3s (latence max agent le plus lent)
```

---

### ✅ **Tâche 3 : Cache Redis pour Résumés Sessions**
**Durée estimée** : 3h | **Priorité** : P2

#### Problème
- Les analyses mémoire (résumés/concepts) sont **recalculées** à chaque fois
- Si user demande 2x le même résumé → 2 appels LLM inutiles
- Coût API et latence évitables

#### Solution
Implémenter un cache Redis simple pour les résumés de sessions.

#### Prérequis
Vérifier si Redis est déjà configuré :
```bash
# Chercher configuration Redis existante
grep -r "redis\|Redis\|REDIS" src/backend/ --include="*.py" | head -20

# Vérifier .env
cat .env | grep -i redis
```

#### Implémentation

**Option A : Redis déjà disponible**

**`src/backend/features/memory/analyzer.py`** (dans méthode `_analyze`, ligne ~150)
```python
import json
import hashlib

async def _analyze(self, session_id: str, history: List[Dict[str, Any]], ...):
    # ... code existant ...

    # 🆕 CACHE LAYER
    if persist and not force:
        # Générer clé cache basée sur hash historique
        history_text = "\n".join([f"{m.get('role')}:{m.get('content')}" for m in history])
        cache_key = f"memory_analysis:{session_id}:{hashlib.md5(history_text.encode()).hexdigest()[:8]}"

        # Check cache
        try:
            import redis.asyncio as aioredis
            redis_client = await aioredis.from_url(
                os.getenv("REDIS_URL", "redis://localhost:6379"),
                encoding="utf-8",
                decode_responses=True
            )
            cached = await redis_client.get(cache_key)
            if cached:
                logger.info(f"[MemoryAnalyzer] Cache HIT pour session {session_id}")
                return json.loads(cached)
        except Exception as cache_err:
            logger.debug(f"Cache unavailable: {cache_err}")

    # ... code analyse existant ...

    # 🆕 SAVE TO CACHE (après analyse réussie)
    if analysis_result and persist:
        try:
            await redis_client.setex(
                cache_key,
                3600,  # TTL 1h
                json.dumps(analysis_result)
            )
            logger.info(f"[MemoryAnalyzer] Cache SAVED pour session {session_id}")
        except Exception:
            pass

    return analysis_result
```

**Option B : Redis non disponible → Skip cette tâche**

Si Redis n'est pas configuré et que l'ajout est complexe, **reporter cette tâche à Phase 3** et se concentrer sur les 2 premières.

#### Tests
```bash
# 1. Analyser une session 2 fois
# POST /api/memory/analyze {"session_id": "xxx"}
# POST /api/memory/analyze {"session_id": "xxx"}  # Devrait être instantané

# 2. Vérifier logs
# Attendu: "[MemoryAnalyzer] Cache HIT pour session xxx"
```

---

## 📊 MÉTRIQUES DE SUCCÈS

| Métrique | Avant | Cible Après | Validation |
|----------|-------|-------------|------------|
| **Latence analyse mémoire** | 4-6s | 1-2s | Logs `[MemoryAnalyzer]` |
| **Latence débat 3 agents** | 6-7s | 2-3s | Métriques endpoint débat |
| **Cache hit rate** | 0% | 40%+ | Logs cache HIT/MISS |
| **Coût API analyses** | 100% | 60% | Prometheus metrics |

---

## 🧪 PLAN DE TEST COMPLET

### Test 1 : Analyse Mémoire Rapide
```bash
# 1. Créer session avec historique
# 2. POST /api/memory/analyze {"session_id": "test_perf", "force": true}
# 3. Mesurer temps réponse (target < 2s)
# 4. Vérifier logs provider = "neo_analysis" (OpenAI)
```

### Test 2 : Débat Parallèle
```bash
# 1. Lancer débat avec question complexe
# 2. Mesurer temps total (target < 3s)
# 3. Vérifier logs : appels agents doivent se chevaucher temporellement
```

### Test 3 : Cache Redis
```bash
# 1. Analyser session A → MISS (calcul)
# 2. Analyser session A → HIT (cache, < 100ms)
# 3. Analyser session B → MISS (différent hash)
# 4. Wait 1h → Analyser session A → MISS (TTL expiré)
```

---

## 🔧 ENVIRONNEMENT

### Variables ENV requises :
```bash
# Déjà configurées (Phase 1)
MEMORY_ANALYSIS_TIMEOUT=30

# Nouvelles (Phase 2)
REDIS_URL=redis://localhost:6379  # Si cache Redis implémenté
```

### Dépendances Python (vérifier requirements.txt) :
```bash
# Si Redis utilisé
redis>=5.0.0
```

---

## ⚠️ POINTS D'ATTENTION

1. **Modèle neo_analysis** : S'assurer que GPT-4o-mini supporte `response_format={"type": "json_object"}` (oui, vérifié)

2. **Débats parallèles** : Gérer correctement les exceptions individuelles avec `return_exceptions=True`

3. **Cache Redis** :
   - Si Redis non dispo, skip cette tâche sans bloquer
   - Hash MD5 court (8 chars) pour éviter clés trop longues
   - TTL 1h (ajustable selon usage)

4. **Logs** : Enrichir avec provider utilisé pour monitoring post-déploiement

---

## 📦 LIVRABLE ATTENDU

À la fin de cette phase, tu devrais avoir :

✅ **Code modifié** :
- `config.py` : Agent `neo_analysis` ajouté
- `analyzer.py` : Utilise `neo_analysis` + cache (optionnel)
- `debate/service.py` : Appels agents parallèles

✅ **Tests validés** :
- Analyse < 2s (vs 4-6s avant)
- Débat < 3s (vs 6-7s avant)
- Cache fonctionne (si implémenté)

✅ **Documentation** :
- Update `AGENT_SYNC.md` avec nouvelles perfs
- Créer `docs/deployments/2025-10-08-phase2-perf.md` avec métriques

---

## 🚀 COMMANDES RAPIDES

```bash
# Vérifier structure projet
ls -la src/backend/features/

# Chercher service débat
grep -r "debate" src/backend/features/ --include="*.py"

# Tester analyse mémoire
curl -X POST http://localhost:8000/api/memory/analyze \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test_perf", "force": true}'

# Vérifier logs temps réel
tail -f logs/backend.log | grep -i "memoryanalyzer\|debate"
```

---

## 📚 RESSOURCES

### Fichiers clés à consulter :
- `src/backend/shared/config.py` (config agents)
- `src/backend/features/memory/analyzer.py` (analyses mémoire)
- `src/backend/features/debate/service.py` (débats - à localiser)
- `src/backend/features/chat/service.py` (référence appels LLM)

### Documentation :
- [OpenAI JSON mode](https://platform.openai.com/docs/guides/structured-outputs)
- [asyncio.gather](https://docs.python.org/3/library/asyncio-task.html#asyncio.gather)
- [Redis Python asyncio](https://redis.readthedocs.io/en/stable/examples/asyncio_examples.html)

---

**Bonne chance ! 🚀**

Si tu bloques sur un point, concentre-toi sur les **Tâches 1 & 2** (les plus impactantes). Le cache Redis est optionnel si complexe à implémenter.
