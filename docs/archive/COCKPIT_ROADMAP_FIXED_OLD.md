# 🎯 Feuille de Route Cockpit - Version Corrigée

**Date** : 2025-10-10
**Statut** : 📋 PLAN D'ACTION PRIORITAIRE
**Objectif** : Corriger les problèmes de valeurs et métriques du cockpit

---

## 📊 État des Lieux - Diagnostic Complet

### ✅ Ce qui FONCTIONNE Déjà (85%)

#### **Backend Infrastructure - OPÉRATIONNEL**

1. **API Endpoints** ✅
   - `GET /api/dashboard/costs/summary` - Résumé complet ([router.py](../../src/backend/features/dashboard/router.py))
   - Retourne : `costs`, `monitoring`, `thresholds`, `messages`, `tokens`, `raw_data`

2. **Services Backend** ✅
   - [DashboardService](../../src/backend/features/dashboard/service.py) v11.1 - DTO robuste
   - [get_messages_by_period()](../../src/backend/core/database/queries.py#L317) - Compte messages par période ✅
   - [get_tokens_summary()](../../src/backend/core/database/queries.py#L368) - Agrège tokens depuis costs ✅
   - [get_costs_summary()](../../src/backend/core/database/queries.py) - Coûts par période ✅

3. **Frontend Cockpit** ✅
   - [cockpit-main.js](../../src/frontend/features/cockpit/cockpit-main.js) - Structure principale
   - [cockpit-metrics.js](../../src/frontend/features/cockpit/cockpit-metrics.js) - Métriques UI
   - [cockpit.js](../../src/frontend/features/cockpit/cockpit.js) - Module d'intégration
   - **INTÉGRÉ dans app.js** ligne 53 ✅

4. **Tracking Coûts** ✅
   - [cost_tracker.py](../../src/backend/core/cost_tracker.py) v13.1 - Enregistrement async
   - [pricing.py](../../src/backend/features/chat/pricing.py) - Tarifs à jour

---

### 🔴 Problèmes Identifiés (3 Gaps Critiques)

#### **Gap #1 : Calcul Coûts Gemini Incomplet** 🔥

**Localisation** : [llm_stream.py:159-171](../../src/backend/features/chat/llm_stream.py#L159)

**Problème** :
```python
# Ligne 159-171 : COUNT INPUT TOKENS
try:
    prompt_parts = [system_prompt]
    for msg in history:
        content = msg.get("content", "")
        if content:
            prompt_parts.append(content)
    input_tokens = _model.count_tokens(prompt_parts).total_tokens
    logger.debug(f"[Gemini] Input tokens: {input_tokens}")
except Exception as e:
    logger.warning(f"[Gemini] Failed to count input tokens: {e}")
    # ❌ MANQUE : input_tokens = 0
```

**Impact** :
- Si `count_tokens()` échoue, la variable `input_tokens` n'est pas définie
- Provoque un crash ou met 0 par défaut
- **70-80% des conversations utilisent Gemini** → sous-estimation massive des coûts

**Solution** :
```python
# Ligne 159-171 : Ajouter fallback
try:
    prompt_parts = [system_prompt]
    for msg in history:
        content = msg.get("content", "")
        if content:
            prompt_parts.append(content)
    input_tokens = _model.count_tokens(prompt_parts).total_tokens
    logger.debug(f"[Gemini] Input tokens: {input_tokens}")
except Exception as e:
    logger.warning(f"[Gemini] Failed to count input tokens: {e}")
    input_tokens = 0  # ✅ AJOUTER CETTE LIGNE
```

---

#### **Gap #2 : Métriques Prometheus Absentes** 🟠

**Problème** :
- Phase 3 Prometheus implémentée **uniquement pour MemoryAnalyzer**
- **Aucune métrique** pour les coûts LLM :
  - Pas de `llm_cost_dollars_total` par agent/model
  - Pas de `llm_tokens_total` par provider
  - Pas de `llm_daily_cost_gauge` pour alertes
  - Pas de `llm_cost_per_request_histogram`

**Impact** :
- ❌ Impossible de monitorer les dépenses en temps réel
- ❌ Pas d'alertes Prometheus sur dépassement budget
- ❌ Pas de dashboards Grafana pour billing

**Solution** : Voir Action #3 ci-dessous

---

#### **Gap #3 : Affichage Frontend peut être vide** 🟡

**Problème Potentiel** :
- Le cockpit frontend appelle correctement l'API ✅
- Mais si la BDD est vide ou les données ne sont pas trackées, affichage = $0.00

**Cause Racine** :
- Gap #1 (Gemini) → pas de coûts enregistrés
- Vérifier que `cost_tracker.record_cost()` est bien appelé après chaque requête LLM

**Validation nécessaire** :
1. Vérifier que les coûts sont bien enregistrés dans la table `costs`
2. Vérifier que les messages sont dans la table `messages`
3. Tester une conversation complète et voir si les valeurs s'affichent

---

## 🎯 Plan d'Action - Priorisation

### **Phase 0 : Validation État Actuel** (30 minutes) 🔍

#### Étape 1 : Vérifier la BDD
```bash
# Créer script de diagnostic
python check_cockpit_data.py
```

**Fichier** : `check_cockpit_data.py`
```python
import sqlite3
from datetime import datetime, timedelta

conn = sqlite3.connect('instance/emergence.db')
cursor = conn.cursor()

print("=== COCKPIT DATA ANALYSIS ===\n")

# 1. Messages
cursor.execute("SELECT COUNT(*) FROM messages")
total_messages = cursor.fetchone()[0]
print(f"📧 Total Messages: {total_messages}")

cursor.execute("""
    SELECT COUNT(*) FROM messages
    WHERE datetime(created_at) >= datetime('now', '-1 day')
""")
today_messages = cursor.fetchone()[0]
print(f"   Today: {today_messages}")

# 2. Coûts
cursor.execute("SELECT COUNT(*) FROM costs")
total_costs = cursor.fetchone()[0]
print(f"\n💰 Total Cost Entries: {total_costs}")

cursor.execute("""
    SELECT model, COUNT(*), SUM(total_cost), SUM(input_tokens), SUM(output_tokens)
    FROM costs
    GROUP BY model
""")
print("\nCoûts par Modèle:")
for row in cursor.fetchall():
    model, count, cost, inp, out = row
    print(f"  {model}: {count} entries, ${cost:.6f}, {inp} in, {out} out")

# 3. Coûts Gemini spécifiquement
cursor.execute("""
    SELECT COUNT(*), SUM(total_cost)
    FROM costs
    WHERE model LIKE '%gemini%'
""")
gemini_count, gemini_cost = cursor.fetchone()
print(f"\n🔥 GEMINI: {gemini_count} entries, ${gemini_cost or 0:.6f}")

if gemini_count > 0 and (gemini_cost or 0) == 0:
    print("   ⚠️ WARNING: Gemini costs are 0 → Gap #1 confirmé!")

# 4. Sessions
cursor.execute("SELECT COUNT(*) FROM sessions")
print(f"\n🧵 Total Sessions: {cursor.fetchone()[0]}")

# 5. Documents
cursor.execute("SELECT COUNT(*) FROM documents")
print(f"📄 Total Documents: {cursor.fetchone()[0]}")

conn.close()

print("\n" + "="*50)
print("✅ Si tous les compteurs sont à 0 → Pas de données à afficher (normal)")
print("🔥 Si Gemini costs = 0 mais entries > 0 → Gap #1 à corriger")
```

#### Étape 2 : Tester l'API Backend
```bash
# Démarrer le backend
python -m uvicorn src.backend.main:app --reload

# Tester l'endpoint
curl http://localhost:8000/api/dashboard/costs/summary \
  -H "Authorization: Bearer <ton_token>"
```

**Résultat attendu** :
```json
{
  "costs": {
    "total_cost": 0.0,
    "today_cost": 0.0,
    "current_week_cost": 0.0,
    "current_month_cost": 0.0
  },
  "monitoring": {
    "total_documents": 0,
    "total_sessions": 0
  },
  "thresholds": {
    "daily_threshold": 3.0,
    "weekly_threshold": 12.0,
    "monthly_threshold": 20.0
  },
  "messages": {
    "total": 0,
    "today": 0,
    "week": 0,
    "month": 0
  },
  "tokens": {
    "total": 0,
    "input": 0,
    "output": 0,
    "avgPerMessage": 0
  },
  "raw_data": {
    "documents": [],
    "sessions": []
  }
}
```

#### Étape 3 : Tester le Frontend
1. Ouvrir l'application
2. Naviguer vers `/cockpit` ou activer le module cockpit
3. Vérifier :
   - Les cartes de coûts affichent des valeurs
   - Les métriques (messages, threads, tokens) sont correctes
   - Les seuils d'alerte fonctionnent (vert/jaune/rouge)

---

### **Phase 1 : Corriger Gemini** (1 heure) 🔧

**Priorité** : P0 - CRITIQUE

#### Action 1.1 : Fixer le fallback input_tokens

**Fichier** : [src/backend/features/chat/llm_stream.py](../../src/backend/features/chat/llm_stream.py)

**Modification** : Ligne 159-172

**Avant** :
```python
try:
    prompt_parts = [system_prompt]
    for msg in history:
        content = msg.get("content", "")
        if content:
            prompt_parts.append(content)
    input_tokens = _model.count_tokens(prompt_parts).total_tokens
    logger.debug(f"[Gemini] Input tokens: {input_tokens}")
except Exception as e:
    logger.warning(f"[Gemini] Failed to count input tokens: {e}")
```

**Après** :
```python
try:
    prompt_parts = [system_prompt]
    for msg in history:
        content = msg.get("content", "")
        if content:
            prompt_parts.append(content)
    input_tokens = _model.count_tokens(prompt_parts).total_tokens
    logger.debug(f"[Gemini] Input tokens: {input_tokens}")
except Exception as e:
    logger.warning(f"[Gemini] Failed to count input tokens: {e}")
    input_tokens = 0  # ✅ Fallback si count_tokens échoue
```

#### Action 1.2 : Même correction pour output_tokens

**Modification** : Ligne 199-209

**Avant** :
```python
# COUNT TOKENS OUTPUT (après génération)
try:
    output_tokens = _model.count_tokens(full_response_text).total_tokens
    logger.debug(f"[Gemini] Output tokens: {output_tokens}")
except Exception as e:
    logger.warning(f"[Gemini] Failed to count output tokens: {e}")
```

**Après** :
```python
# COUNT TOKENS OUTPUT (après génération)
try:
    output_tokens = _model.count_tokens(full_response_text).total_tokens
    logger.debug(f"[Gemini] Output tokens: {output_tokens}")
except Exception as e:
    logger.warning(f"[Gemini] Failed to count output tokens: {e}")
    output_tokens = 0  # ✅ Fallback si count_tokens échoue
```

#### Action 1.3 : Améliorer les logs

**Modification** : Ligne 211-225

**Ajouter** :
```python
# CALCUL COÛT
pricing = MODEL_PRICING.get(model, {"input": 0, "output": 0})
total_cost = (input_tokens * pricing["input"]) + (output_tokens * pricing["output"])

cost_info_container.update({
    "input_tokens": input_tokens,
    "output_tokens": output_tokens,
    "total_cost": total_cost,
})

# ✅ AJOUTER LOG DÉTAILLÉ
logger.info(
    f"[Gemini] Cost calculated: ${total_cost:.6f} "
    f"(model={model}, in={input_tokens}, out={output_tokens}, "
    f"pricing_in=${pricing['input']:.6f}, pricing_out=${pricing['output']:.6f})"
)
```

#### Action 1.4 : Test de validation

```bash
# 1. Relancer le backend
python -m uvicorn src.backend.main:app --reload

# 2. Faire une conversation avec Gemini
# 3. Vérifier les logs
grep "Gemini.*Cost calculated" logs/backend.log

# 4. Vérifier la BDD
python check_cockpit_data.py

# Attendu : Gemini costs > 0
```

---

### **Phase 2 : Métriques Prometheus** (2-3 heures) 📊

**Priorité** : P1 - IMPORTANT (mais après Gemini)

#### Action 2.1 : Définir les métriques

**Fichier** : [src/backend/core/cost_tracker.py](../../src/backend/core/cost_tracker.py)

**Ajouter après les imports** (ligne ~10) :

```python
from prometheus_client import Counter, Histogram, Gauge

# =============================================================================
# PROMETHEUS METRICS - LLM Costs & Tokens
# =============================================================================

# Coûts totaux par agent/model/provider
COST_BY_AGENT = Counter(
    "llm_cost_dollars_total",
    "Total cost in dollars by agent, model and provider",
    ["agent", "model", "provider"]
)

# Tokens consommés (input vs output)
TOKENS_CONSUMED = Counter(
    "llm_tokens_total",
    "Total tokens consumed by provider, model and type",
    ["provider", "model", "type"]  # type = input|output
)

# Distribution coût par requête
COST_PER_REQUEST = Histogram(
    "llm_cost_per_request_dollars",
    "Cost per request distribution in dollars",
    buckets=[0.0001, 0.0005, 0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0]
)

# Compteur requêtes par provider
REQUESTS_BY_PROVIDER = Counter(
    "llm_requests_total",
    "Total LLM requests by provider and model",
    ["provider", "model"]
)

# Gauges pour coûts périodiques (alertes)
DAILY_COST_GAUGE = Gauge(
    "llm_daily_cost_dollars",
    "Current daily cost in dollars"
)

WEEKLY_COST_GAUGE = Gauge(
    "llm_weekly_cost_dollars",
    "Current weekly cost in dollars"
)

MONTHLY_COST_GAUGE = Gauge(
    "llm_monthly_cost_dollars",
    "Current monthly cost in dollars"
)
```

#### Action 2.2 : Instrumenter record_cost()

**Modifier la méthode** `record_cost()` (ligne ~43-78) :

```python
async def record_cost(
    self,
    agent: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    total_cost: float,
    feature: str,
    *,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
):
    """Enregistre le coût + métriques Prometheus."""
    async with self._lock:
        try:
            # 1. ENREGISTREMENT BDD (existant)
            await db_queries.add_cost_log(
                db=self.db_manager,
                timestamp=datetime.now(timezone.utc),
                agent=agent,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_cost=total_cost,
                feature=feature,
                session_id=session_id,
                user_id=user_id,
            )
            logger.info(
                f"Coût de {total_cost:.6f} pour '{agent}' ('{model}') enregistré."
            )

            # 2. MÉTRIQUES PROMETHEUS (nouveau)
            try:
                provider = self._detect_provider_from_model(model)

                # Coût par agent/model/provider
                COST_BY_AGENT.labels(
                    agent=agent,
                    model=model,
                    provider=provider
                ).inc(total_cost)

                # Tokens consommés
                TOKENS_CONSUMED.labels(
                    provider=provider,
                    model=model,
                    type="input"
                ).inc(input_tokens)

                TOKENS_CONSUMED.labels(
                    provider=provider,
                    model=model,
                    type="output"
                ).inc(output_tokens)

                # Distribution coût par requête
                COST_PER_REQUEST.observe(total_cost)

                # Compteur requêtes
                REQUESTS_BY_PROVIDER.labels(
                    provider=provider,
                    model=model
                ).inc()

                logger.debug(
                    f"[Prometheus] Metrics recorded for {provider}/{model}: "
                    f"${total_cost:.6f}, {input_tokens} in, {output_tokens} out"
                )

            except Exception as metrics_error:
                logger.warning(
                    f"[Prometheus] Failed to record metrics: {metrics_error}",
                    exc_info=True
                )
                # Ne pas fail si métriques KO

        except Exception as e:
            logger.error(
                f"Erreur lors de l'enregistrement du coût pour {model}: {e}",
                exc_info=True,
            )
```

#### Action 2.3 : Ajouter helper _detect_provider_from_model()

**Ajouter après la classe** (ligne ~110) :

```python
def _detect_provider_from_model(self, model: str) -> str:
    """
    Détecte le provider depuis le nom du modèle.

    Returns:
        "openai" | "google" | "anthropic" | "unknown"
    """
    model_lower = model.lower()

    if model_lower.startswith("gpt-"):
        return "openai"
    elif "gemini" in model_lower or model_lower.startswith("models/gemini"):
        return "google"
    elif "claude" in model_lower:
        return "anthropic"
    else:
        logger.warning(f"[CostTracker] Unknown provider for model: {model}")
        return "unknown"
```

#### Action 2.4 : Mise à jour périodique des gauges

**Ajouter méthode** :

```python
async def update_periodic_gauges(self) -> None:
    """
    Met à jour les gauges Prometheus pour coûts daily/weekly/monthly.
    À appeler périodiquement (ex: toutes les 5 minutes).
    """
    try:
        summary = await self.get_spending_summary()

        DAILY_COST_GAUGE.set(float(summary.get("today", 0.0) or 0.0))
        WEEKLY_COST_GAUGE.set(float(summary.get("this_week", 0.0) or 0.0))
        MONTHLY_COST_GAUGE.set(float(summary.get("this_month", 0.0) or 0.0))

        logger.debug(
            f"[Prometheus] Periodic gauges updated: "
            f"daily=${summary.get('today', 0):.2f}, "
            f"weekly=${summary.get('this_week', 0):.2f}, "
            f"monthly=${summary.get('this_month', 0):.2f}"
        )

    except Exception as e:
        logger.error(f"[Prometheus] Failed to update periodic gauges: {e}", exc_info=True)
```

#### Action 2.5 : Background task

**Fichier** : [src/backend/main.py](../../src/backend/main.py)

**Ajouter** :

```python
import asyncio
from backend.core.cost_tracker import CostTracker

async def update_cost_gauges_periodically():
    """Background task pour mettre à jour les gauges Prometheus coûts."""
    while True:
        try:
            cost_tracker = container.cost_tracker()
            await cost_tracker.update_periodic_gauges()
        except Exception as e:
            logger.error(f"Error updating cost gauges: {e}", exc_info=True)

        # Toutes les 5 minutes
        await asyncio.sleep(5 * 60)

# Lancer au startup
@app.on_event("startup")
async def startup_background_tasks():
    asyncio.create_task(update_cost_gauges_periodically())
```

#### Action 2.6 : Test Prometheus

```bash
# 1. Relancer le backend
python -m uvicorn src.backend.main:app --reload

# 2. Faire quelques requêtes LLM

# 3. Vérifier métriques exposées
curl http://localhost:8000/api/metrics | grep llm_

# Attendu :
# llm_cost_dollars_total{agent="assistant",model="gemini-2.0-flash-exp",provider="google"} 0.000123
# llm_tokens_total{provider="google",model="gemini-2.0-flash-exp",type="input"} 150
# llm_tokens_total{provider="google",model="gemini-2.0-flash-exp",type="output"} 50
# llm_cost_per_request_dollars_bucket{le="0.001"} 3
# llm_requests_total{provider="google",model="gemini-2.0-flash-exp"} 3
# llm_daily_cost_dollars 0.000369
```

---

### **Phase 3 : Tests E2E** (30 minutes) ✅

#### Test 1 : Conversation complète

1. Démarrer le backend
2. Ouvrir l'application frontend
3. Créer une nouvelle session
4. Envoyer 3-5 messages
5. Aller dans le cockpit (`/cockpit`)
6. Vérifier :
   - Messages : total > 0, today > 0
   - Threads : total > 0, active > 0
   - Tokens : total > 0, input > 0, output > 0
   - Coûts : total > $0.00, today > $0.00

#### Test 2 : Validation BDD

```python
# Après la conversation
python check_cockpit_data.py

# Attendu :
# Messages: 5
# Costs: 5 entries
# Gemini costs > $0.00 (si Gemini utilisé)
```

#### Test 3 : Validation API

```bash
curl http://localhost:8000/api/dashboard/costs/summary \
  -H "Authorization: Bearer <token>" | jq

# Vérifier :
# - costs.total_cost > 0
# - messages.total > 0
# - tokens.total > 0
```

---

## 📋 Checklist d'Implémentation

### **Phase 0 : Validation** ✅
- [ ] Créer `check_cockpit_data.py`
- [ ] Exécuter diagnostic BDD
- [ ] Tester API `/api/dashboard/costs/summary`
- [ ] Tester cockpit frontend
- [ ] Documenter l'état actuel

### **Phase 1 : Gemini Fix** 🔥
- [ ] Ajouter `input_tokens = 0` fallback (ligne 171)
- [ ] Ajouter `output_tokens = 0` fallback (ligne 209)
- [ ] Améliorer logs de coûts Gemini
- [ ] Tester conversation Gemini
- [ ] Vérifier BDD : `costs WHERE model LIKE '%gemini%'`
- [ ] Valider coûts > 0

### **Phase 2 : Prometheus** 📊
- [ ] Importer `prometheus_client` dans `cost_tracker.py`
- [ ] Définir 7 métriques (Counter + Histogram + Gauge)
- [ ] Modifier `record_cost()` pour instrumenter
- [ ] Ajouter `_detect_provider_from_model()`
- [ ] Ajouter `update_periodic_gauges()`
- [ ] Créer background task dans `main.py`
- [ ] Tester endpoint `/api/metrics`
- [ ] Vérifier métriques `llm_*` exposées

### **Phase 3 : Tests E2E** ✅
- [ ] Test conversation complète
- [ ] Vérifier affichage cockpit
- [ ] Valider BDD (messages, costs, tokens)
- [ ] Valider API (tous endpoints)
- [ ] Valider Prometheus metrics

---

## 🎯 Critères de Succès

| Critère | KPI | Status |
|---------|-----|--------|
| **Coûts Gemini** | > $0.00 dans BDD après conversation | ⏳ À corriger |
| **Métriques Messages** | Nombre correct dans cockpit | ⏳ À valider |
| **Métriques Tokens** | Input + output corrects | ⏳ À valider |
| **Métriques Coûts** | Today/Week/Month corrects | ⏳ À valider |
| **Prometheus** | 7 métriques `llm_*` exposées | ⏳ À implémenter |
| **Performance** | Cockpit load < 2s | ⏳ À mesurer |
| **Alertes** | Seuils visuels fonctionnels | ⏳ À tester |

---

## 📚 Références

### Documentation
- [COCKPIT_GAPS_AND_FIXES.md](COCKPIT_GAPS_AND_FIXES.md) - Analyse initiale
- [cockpit-qa-playbook.md](../qa/cockpit-qa-playbook.md) - Scripts QA

### Code Backend
- [dashboard/service.py](../../src/backend/features/dashboard/service.py) - DTO v11.1
- [database/queries.py](../../src/backend/core/database/queries.py) - Queries SQL
- [cost_tracker.py](../../src/backend/core/cost_tracker.py) - Tracking v13.1
- [llm_stream.py](../../src/backend/features/chat/llm_stream.py) - Streaming + coûts

### Code Frontend
- [cockpit-main.js](../../src/frontend/features/cockpit/cockpit-main.js) - Structure principale
- [cockpit-metrics.js](../../src/frontend/features/cockpit/cockpit-metrics.js) - Métriques UI
- [cockpit.js](../../src/frontend/features/cockpit/cockpit.js) - Intégration module

---

## ⚠️ Notes Importantes

### Gemini count_tokens() Latence
- `count_tokens()` est **synchrone** dans l'API officielle
- Ajoute ~50-100ms de latence par requête
- **Acceptable** pour tracking précis des coûts réels
- Alternative : estimation `len(text) // 4` (moins précis)

### Prometheus Gauges
- Les gauges `llm_daily_cost_dollars` doivent être refresh périodiquement
- Background task toutes les 5 min recommandé
- Alternative : Prometheus recording rules (côté Prometheus)

### Synchronisation Plan P2 Mémoire
- **P2 Mémoire reste PRIORITAIRE** (6-9 jours)
- Ce plan Cockpit peut être fait **après** ou **en parallèle** (1-2 jours)
- Total : 7-11 jours pour P2 + Cockpit

---

**Document créé le** : 2025-10-10
**Auteur** : Claude Code
**Statut** : ✅ PRÊT À IMPLÉMENTER
