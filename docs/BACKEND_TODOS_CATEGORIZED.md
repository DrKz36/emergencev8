# Backend TODOs - Catégorisation & Actions

**Dernière mise à jour :** 2025-10-23
**Status :** 18 TODOs identifiés, 3 fixés, 15 restants catégorisés

---

## ✅ Quick Wins - COMPLÉTÉS (3/3)

### Dashboard Admin Service
- ❌ ~~`admin_service.py:686` - Implement actual error tracking~~ → ✅ **FIXÉ** (utilise MetricsCollector)
- ❌ ~~`admin_service.py:692` - Implement actual latency tracking~~ → ✅ **FIXÉ** (utilise MetricsCollector)
- ❌ ~~`admin_service.py:698` - Implement actual error counting~~ → ✅ **FIXÉ** (utilise MetricsCollector)

---

## 🟡 Features P3 - Long Terme (9 TODOs)

### 1. RoutePolicy & ToolCircuitBreaker (P3.1 - Circuit Breaker)
**Priorité :** P3 (Basse)
**Temps estimé :** 3-4h

**TODOs concernés :**
- `chat/service.py:195` - Intégration RoutePolicy dans `_get_agent_config()` pour choisir SLM vs LLM
- `chat/service.py:205` - Log `[P2.3] RoutePolicy initialisé - TODO: intégration active`
- `chat/service.py:207` - ToolCircuitBreaker wrapper appels async tools (MemoryQueryTool, ProactiveHintEngine)
- `chat/service.py:218` - Log `[P2.3] ToolCircuitBreaker initialisé - TODO: intégration active`

**Action :**
- Feature P3.1 dans ROADMAP.md
- Requires: Intégration active RoutePolicy (Gemini Flash vs GPT-4o) + Circuit Breaker pour tools async
- Créer issue GitHub `#P3-1-circuit-breaker` avec specs détaillées

---

### 2. Memory Phase 2 Enrichissements (P3.4 - Memory Advanced)
**Priorité :** P3 (Basse)
**Temps estimé :** 2-3h

**TODOs concernés :**
- `core/ws/handlers/handshake.py:162` - Récupérer items STM/LTM depuis ChromaDB
- `memory/memory_query_tool.py:490` - Phase 2: Enrichir avec détails des conversations
- `memory/router.py:2278` - Améliorer avec topics via MemoryQueryTool
- `memory/router.py:2283` - `"topics": []` → TODO enrichir
- `memory/unified_retriever.py:392` - Améliorer avec recherche fulltext SQLite FTS5

**Action :**
- Feature P3.4 dans ROADMAP.md
- Requires: Phase Agent Memory complète (ChromaDB STM/LTM + topics extraction + FTS5)
- Créer issue GitHub `#P3-4-memory-advanced` avec specs

---

### 3. Guardian Email Notifications (P3 Nice-to-have)
**Priorité :** P3 (Basse)
**Temps estimé :** 1h

**TODOs concernés :**
- `guardian/router.py:246` - Envoyer email de confirmation avec résultats

**Action :**
- Nice-to-have feature
- Requires: SendGrid/SMTP config + template email
- Créer issue GitHub `#P3-guardian-email` si nécessaire

---

## 🔵 Refactoring Futur (2 TODOs)

### 1. Dependency Injection Usage Tracking
**Priorité :** P3 (Technique Debt)
**Temps estimé :** 30min

**TODOs concernés :**
- `usage/router.py:27` - Intégrer dans ServiceContainer pour DI propre

**Action :**
- Refactoring technique (pas bloquant)
- Lors de refactor global DI (si nécessaire)

---

### 2. Guardian Auth Requirements
**Priorité :** P2 (Sécurité)
**Temps estimé :** 15min

**TODOs concernés :**
- `guardian/router.py:354` - Accessible sans auth pour l'instant (TODO: require admin)
- `guardian/router.py:439` - Accessible sans auth pour l'instant (TODO: require admin)

**Action :**
- ⚠️ **IMPORTANT SÉCURITÉ** : Ajouter `Depends(require_admin_claims)` dans signature endpoints Guardian
- Facile à faire, juste pas fait car en DEV mode actuellement
- **À FAIRE AVANT PROD PUBLIC** (actuellement prod stable interne OK)

---

## 🔹 Mineurs / Non-Critiques (1 TODO)

### Middleware Stack Trace
**Priorité :** P4 (Très Basse)
**Temps estimé :** 5min

**TODOs concernés :**
- `middleware/usage_tracking.py:254` - `stack_trace=None, # TODO: extraire si besoin`

**Action :**
- Pas critique, stack trace pas nécessaire pour usage tracking
- Si besoin futur : utiliser `traceback.format_exc()` dans exception handler
- **LAISSER TEL QUEL** pour l'instant

---

## 📊 Résumé

```
Total TODOs Backend : 18
  ✅ Quick Wins fixés  : 3 (Dashboard admin metrics)
  🟡 Features P3       : 9 (RoutePolicy, Memory Phase 2, Guardian Email)
  🔵 Refactoring       : 2 (DI Usage, Guardian Auth)
  🔹 Mineurs           : 1 (Stack trace usage)
  ⏳ Restants         : 15 (documentés ici)
```

**Actions prises :**
1. ✅ Fixé 3 TODOs Dashboard admin (intégration MetricsCollector)
2. ✅ Documenté 15 TODOs restants avec catégories + priorités + actions
3. ⏳ Issues GitHub à créer pour Features P3 (optionnel, si on planifie vraiment ces features)

**Recommandation :**
- Les 15 TODOs restants sont **non-bloquants** pour production actuelle
- Features P3 à planifier si budget temps disponible (8-10h total)
- Guardian Auth (2 TODOs) à faire **avant prod publique** (actuellement OK pour prod interne)

---

**Dernière révision :** Claude Code (2025-10-23)
