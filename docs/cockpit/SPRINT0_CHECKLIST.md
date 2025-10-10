# ✅ Sprint 0 Cockpit - Checklist Détaillée

**Date Création** : 2025-10-10
**À Faire Après** : Phase P2 Mémoire
**Durée Estimée** : 1-2 jours (7-11 heures)
**Statut** : ⏳ EN ATTENTE (P2 en priorité)

---

## 📋 Vue d'Ensemble

### **3 Actions Critiques**

| Action | Durée | Priorité | Fichiers Impactés |
|--------|-------|----------|-------------------|
| #1 - Frontend Dashboard UI | 4-6h | 🔴 P0 | `src/frontend/features/dashboard/` (nouveau) |
| #2 - Fix Coûts Gemini | 1-2h | 🔴 P0 | `src/backend/features/chat/llm_stream.py` |
| #3 - Métriques Prometheus | 2-3h | 🟠 P1 | `src/backend/core/cost_tracker.py` |

---

## 🎨 Action #1 : Frontend Dashboard UI (4-6h)

### **Fichiers à Créer**

#### ✅ `src/frontend/features/dashboard/dashboard-ui.js`
**Lignes** : ~350
**Composant** : Classe `DashboardUI`
**Features** :
- [ ] Méthode `init(containerId)` - Initialisation composant
- [ ] Méthode `render()` - Génération HTML
  - [ ] Header avec bouton refresh
  - [ ] 4 cards coûts (today/week/month/total)
  - [ ] 4 stats monitoring (messages/sessions/documents/tokens)
  - [ ] 2 canvas pour charts (coûts + activité)
- [ ] Méthode `loadData()` - Fetch API
  - [ ] `GET /api/dashboard/costs/summary` avec `X-Session-Id` header
  - [ ] Parsing réponse + appels `renderCosts()` et `renderMonitoring()`
- [ ] Méthode `renderCosts(costs, thresholds)` - Affichage 4 cards
  - [ ] Format `$X.XX` avec `toFixed(2)`
  - [ ] Appel `renderThreshold()` pour chaque période
- [ ] Méthode `renderThreshold(period, current, threshold)` - Badge % budget
  - [ ] Calcul `percent = (current / threshold) * 100`
  - [ ] Classes CSS : `threshold-ok` (<80%), `threshold-warning` (80-100%), `threshold-exceeded` (>100%)
- [ ] Méthode `renderMonitoring(monitoring, messages, tokens)` - Stats
  - [ ] Formatter tokens avec `formatNumber()` (1.5K, 2.3M)
- [ ] Méthode `loadTimelines(headers)` - Fetch timelines
  - [ ] `Promise.all()` sur `/timeline/costs` et `/timeline/activity`
  - [ ] Appels `renderCostsChart()` et `renderActivityChart()`
- [ ] Méthode `renderCostsChart(data)` - Canvas chart coûts
  - [ ] **Placeholder** : `console.log(data)` OU
  - [ ] Implémentation Chart.js (optionnel)
- [ ] Méthode `renderActivityChart(data)` - Canvas chart activité
  - [ ] **Placeholder** : `console.log(data)` OU
  - [ ] Implémentation Chart.js (optionnel)
- [ ] Méthode `attachEventListeners()` - Bind events
  - [ ] Bouton refresh → `this.refresh()`
  - [ ] EventBus `session:changed` → `this.loadData()`
- [ ] Méthode `refresh()` - Refresh manuel
  - [ ] Disable bouton + texte "⏳ Actualisation..."
  - [ ] `await this.loadData()`
  - [ ] Re-enable après 2s avec "✓ Actualisé"
- [ ] Méthode `startAutoRefresh()` - Interval 2 min
  - [ ] `setInterval(() => this.loadData(), 2 * 60 * 1000)`
- [ ] Méthode `stopAutoRefresh()` - Cleanup
- [ ] Helpers :
  - [ ] `getCurrentSessionId()` - Lit `emergenceState-V14` localStorage
  - [ ] `getAuthToken()` - Lit `emergence.id_token` localStorage/sessionStorage
  - [ ] `formatNumber(num)` - Format 1K/1M
  - [ ] `showError(message)` - Console.error (TODO: notification system)
  - [ ] `destroy()` - Cleanup + clear interval

**Tests** :
- [ ] `await dashboardUI.init('app-container')` dans console
- [ ] Vérifier render HTML complet
- [ ] Vérifier fetch API avec Network tab
- [ ] Vérifier affichage coûts (si données BDD présentes)
- [ ] Vérifier refresh auto après 2 min
- [ ] Vérifier session change → reload data

---

#### ✅ `src/frontend/features/dashboard/dashboard-ui.css`
**Lignes** : ~200
**Styles** :
- [ ] `.dashboard-cockpit` - Container principal
  - [ ] `padding: 2rem`, `max-width: 1400px`, `margin: 0 auto`
- [ ] `.dashboard-header` - Header avec titre + bouton
  - [ ] `display: flex`, `justify-content: space-between`
- [ ] `.btn-refresh-dashboard` - Bouton refresh
  - [ ] `background: var(--color-primary)`, `color: white`
  - [ ] `border-radius: 0.5rem`, `cursor: pointer`
  - [ ] `:hover` darker, `:disabled` opacity 0.6
- [ ] `.dashboard-costs-grid` - Grid 4 cards
  - [ ] `display: grid`, `grid-template-columns: repeat(auto-fit, minmax(200px, 1fr))`
  - [ ] `gap: 1.5rem`
- [ ] `.cost-card` - Card coût individuel
  - [ ] `background: var(--color-bg-secondary)`, `border-radius: 0.75rem`
  - [ ] `padding: 1.5rem`, `text-align: center`
- [ ] `.cost-card.highlight` - Card total (gradient)
  - [ ] `background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-dark) 100%)`
  - [ ] `color: white`
- [ ] `.cost-label` - Label période (Aujourd'hui, etc.)
  - [ ] `font-size: 0.875rem`, `color: var(--color-text-secondary)`
- [ ] `.cost-value` - Valeur $X.XX
  - [ ] `font-size: 2rem`, `font-weight: 700`
- [ ] `.cost-threshold` - Badge % budget
  - [ ] `font-size: 0.75rem`, `padding: 0.25rem 0.5rem`, `border-radius: 0.25rem`
- [ ] `.cost-threshold.threshold-ok` - Badge vert (<80%)
  - [ ] `background: var(--color-success-bg)`, `color: var(--color-success)`
- [ ] `.cost-threshold.threshold-warning` - Badge orange (80-100%)
  - [ ] `background: var(--color-warning-bg)`, `color: var(--color-warning)`
- [ ] `.cost-threshold.threshold-exceeded` - Badge rouge (>100%)
  - [ ] `background: var(--color-error-bg)`, `color: var(--color-error)`
- [ ] `.dashboard-monitoring` - Grid stats monitoring
  - [ ] `display: grid`, `grid-template-columns: repeat(auto-fit, minmax(150px, 1fr))`
- [ ] `.monitoring-stat` - Stat individuelle
  - [ ] `background: var(--color-bg-secondary)`, `border-radius: 0.5rem`
  - [ ] `display: flex`, `flex-direction: column`, `align-items: center`
- [ ] `.stat-icon` - Emoji icône
  - [ ] `font-size: 2rem`
- [ ] `.stat-value` - Valeur numérique
  - [ ] `font-size: 1.5rem`, `font-weight: 600`
- [ ] `.stat-label` - Label stat
  - [ ] `font-size: 0.875rem`, `color: var(--color-text-secondary)`
- [ ] `.dashboard-charts` - Grid 2 charts
  - [ ] `display: grid`, `grid-template-columns: repeat(auto-fit, minmax(400px, 1fr))`
- [ ] `.chart-container` - Container chart
  - [ ] `background: var(--color-bg-secondary)`, `border-radius: 0.75rem`
  - [ ] `padding: 1.5rem`
- [ ] `.chart-container canvas` - Canvas
  - [ ] `width: 100%`, `height: 300px`
- [ ] Dark mode support `@media (prefers-color-scheme: dark)` - Variables CSS
  - [ ] `--color-bg-secondary: #1a1a1a`
  - [ ] `--color-border: #333`
  - [ ] `--color-text-secondary: #888`
  - [ ] Etc.

**Tests** :
- [ ] Vérifier render propre (pas de layout cassé)
- [ ] Vérifier responsive (mobile + desktop)
- [ ] Vérifier dark mode (si applicable)
- [ ] Vérifier badges seuils (couleurs OK/warning/exceeded)

---

#### ✅ `src/frontend/features/dashboard/README.md`
**Contenu** :
```markdown
# Dashboard UI - Cockpit de Pilotage

Composant frontend pour la visualisation des coûts et métriques utilisateur.

## Usage

```javascript
import { dashboardUI } from './features/dashboard/dashboard-ui.js';

await dashboardUI.init('app-container');
```

## API Endpoints Utilisés

- `GET /api/dashboard/costs/summary` - Résumé coûts + monitoring
- `GET /api/dashboard/timeline/costs?period=7d` - Timeline coûts
- `GET /api/dashboard/timeline/activity?period=7d` - Timeline activité

## Features

- ✅ Affichage coûts par période (today/week/month/total)
- ✅ Seuils budgétaires visuels (OK/Warning/Exceeded)
- ✅ Stats monitoring (messages/sessions/documents/tokens)
- ✅ Auto-refresh toutes les 2 minutes
- ⏳ Charts timelines (TODO: Chart.js)

## Dependencies

- EventBus (core)
- localStorage (emergenceState-V14)
- (Optionnel) Chart.js pour graphiques

## Tests

```bash
# Console browser
await dashboardUI.init('app-container');
dashboardUI.loadData();
```
```

**Tests** :
- [ ] README créé et lisible

---

### **Intégrations**

#### ✅ `src/frontend/main.js` (Modifier)
**Ajouter** :
```javascript
// Après imports existants
import { dashboardUI } from './features/dashboard/dashboard-ui.js';

// Dans router ou navigation handler
function handleRoute(path) {
  if (path === '/dashboard') {
    await dashboardUI.init('app-container');
    return;
  }
  // ... existing routes
}

// OU si SPA avec EventBus :
EventBus.on('route:dashboard', async () => {
  await dashboardUI.init('app-container');
});
```

**Tests** :
- [ ] Navigation vers `/dashboard` charge composant
- [ ] Pas d'erreur console
- [ ] Pas de conflit avec autres routes

---

#### ✅ `src/frontend/index.html` (Modifier)
**Ajouter lien menu** :
```html
<nav class="main-nav">
  <!-- ... existing links ... -->
  <a href="/dashboard" class="nav-link" data-route="dashboard">
    <span class="nav-icon">📊</span>
    <span class="nav-label">Cockpit</span>
  </a>
</nav>
```

**Tests** :
- [ ] Lien visible dans menu
- [ ] Click → navigation `/dashboard`
- [ ] Icône + label affichés correctement

---

#### ✅ (Optionnel) Intégrer Chart.js
**Si implémentation charts** :
```html
<!-- Dans index.html <head> -->
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
```

**Puis dans `dashboard-ui.js`** :
```javascript
renderCostsChart(data) {
  const ctx = document.getElementById('costs-timeline-chart').getContext('2d');
  new Chart(ctx, {
    type: 'line',
    data: {
      labels: data.map(d => d.date),
      datasets: [{
        label: 'Coûts ($)',
        data: data.map(d => d.cost),
        borderColor: '#3b82f6',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        tension: 0.4
      }]
    },
    options: { responsive: true, maintainAspectRatio: false }
  });
}
```

**Tests** :
- [ ] Chart.js loaded (vérifier `window.Chart` dans console)
- [ ] Charts rendus correctement
- [ ] Hover sur points affiche tooltips

---

### **Validation Action #1**

- [ ] ✅ 4 fichiers créés (`dashboard-ui.js`, `dashboard-ui.css`, `README.md` + intégrations)
- [ ] ✅ Route `/dashboard` fonctionnelle
- [ ] ✅ Lien menu "Cockpit" visible
- [ ] ✅ Fetch API `GET /api/dashboard/costs/summary` OK (200)
- [ ] ✅ Affichage 4 cards coûts avec valeurs
- [ ] ✅ Badges seuils colorés (ok/warning/exceeded)
- [ ] ✅ Stats monitoring affichées
- [ ] ✅ Refresh auto après 2 min
- [ ] ✅ Pas d'erreur console
- [ ] ✅ Responsive (mobile + desktop)
- [ ] 🟡 Charts (optionnel si temps)

---

## 🐛 Action #2 : Fix Coûts Gemini (1-2h)

### **Fichier à Modifier**

#### ✅ `src/backend/features/chat/llm_stream.py`
**Lignes à modifier** : 142-184 (méthode `_get_gemini_stream`)

**Avant (BROKEN)** :
```python
cost_info_container.setdefault("input_tokens", 0)   # ← Toujours 0
cost_info_container.setdefault("output_tokens", 0)  # ← Toujours 0
cost_info_container.setdefault("total_cost", 0.0)   # ← Toujours 0
```

**Après (FIXED)** :
```python
# COUNT TOKENS INPUT
input_tokens = _model.count_tokens(prompt_parts).total_tokens

# STREAMING (conserver full_response_text)
full_response_text = ""
async for chunk in resp:
    text = ...
    if text:
        full_response_text += text
        yield text

# COUNT TOKENS OUTPUT
output_tokens = _model.count_tokens(full_response_text).total_tokens

# CALCUL COÛT
pricing = MODEL_PRICING.get(model, {"input": 0, "output": 0})
cost_info_container.update({
    "input_tokens": input_tokens,
    "output_tokens": output_tokens,
    "total_cost": (input_tokens * pricing["input"]) + (output_tokens * pricing["output"])
})

logger.info(f"[Gemini] Cost: ${cost:.6f} ({input_tokens} in + {output_tokens} out)")
```

**Checklist Implémentation** :
- [ ] Ajouter variable `full_response_text = ""`
- [ ] Dans boucle `async for chunk`, accumuler : `full_response_text += text`
- [ ] **Avant génération** : `input_tokens = _model.count_tokens(prompt_parts).total_tokens`
  - [ ] Construire `prompt_parts = [system_prompt] + [msg["content"] for msg in history if msg.get("content")]`
- [ ] **Après génération** : `output_tokens = _model.count_tokens(full_response_text).total_tokens`
- [ ] Calculer `total_cost` avec `MODEL_PRICING`
- [ ] `cost_info_container.update({...})`
- [ ] Logger coût calculé
- [ ] Try/except autour count_tokens (fallback 0 si erreur)
- [ ] Conserver fallback 0 dans `except Exception as e:` global

**Tests** :
- [ ] Lancer conversation avec Gemini (ex: "Hello, tell me about Python")
- [ ] Vérifier logs backend :
  ```bash
  grep "Gemini.*Cost calculated" logs/backend.log
  # Attendu : [Gemini] Cost calculated: $0.000123 (150 in + 50 out tokens)
  ```
- [ ] Vérifier BDD :
  ```bash
  sqlite3 instance/emergence.db "SELECT model, input_tokens, output_tokens, total_cost FROM costs WHERE model LIKE '%gemini%' ORDER BY timestamp DESC LIMIT 5;"
  # Attendu : Valeurs NON-ZERO
  ```
- [ ] Tester erreur count_tokens (mock API failure) → vérifier fallback 0 sans crash

---

### **Validation Action #2**

- [ ] ✅ Code modifié dans `llm_stream.py:142-184`
- [ ] ✅ Test conversation Gemini : coût > 0
- [ ] ✅ Logs backend affichent `[Gemini] Cost calculated: $X.XXXXXX`
- [ ] ✅ BDD : `input_tokens`, `output_tokens`, `total_cost` NON-ZERO
- [ ] ✅ Test erreur count_tokens : fallback 0 sans crash
- [ ] ✅ Conversations OpenAI/Anthropic toujours OK (non-régression)

---

## 📊 Action #3 : Métriques Prometheus (2-3h)

### **Fichier à Modifier**

#### ✅ `src/backend/core/cost_tracker.py`
**Sections à ajouter** :

**1. Imports Prometheus** (ligne ~10)
```python
from prometheus_client import Counter, Histogram, Gauge
```

**Checklist** :
- [ ] Import `prometheus_client`

---

**2. Définition Métriques** (après classe CostTracker, ligne ~110)
```python
# Coûts par agent/model/provider
COST_BY_AGENT = Counter(
    "llm_cost_dollars_total",
    "Total cost in dollars by agent, model and provider",
    ["agent", "model", "provider"]
)

# Tokens consommés
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

# Compteur requêtes
REQUESTS_BY_PROVIDER = Counter(
    "llm_requests_total",
    "Total LLM requests by provider and model",
    ["provider", "model"]
)

# Gauges pour alertes
DAILY_COST_GAUGE = Gauge("llm_daily_cost_dollars", "Current daily cost in dollars")
WEEKLY_COST_GAUGE = Gauge("llm_weekly_cost_dollars", "Current weekly cost in dollars")
MONTHLY_COST_GAUGE = Gauge("llm_monthly_cost_dollars", "Current monthly cost in dollars")
```

**Checklist** :
- [ ] 6 métriques définies (3 Counter + 1 Histogram + 3 Gauge)
- [ ] Labels corrects (`agent`, `model`, `provider`, `type`)
- [ ] Buckets histogram pertinents ($0.0001 → $1.0)

---

**3. Helper `_detect_provider_from_model()`** (ligne ~110)
```python
def _detect_provider_from_model(self, model: str) -> str:
    """Détecte le provider depuis le nom du modèle."""
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

**Checklist** :
- [ ] Méthode `_detect_provider_from_model(self, model: str) -> str` créée
- [ ] Détection `gpt-*` → `openai`
- [ ] Détection `gemini` → `google`
- [ ] Détection `claude` → `anthropic`
- [ ] Fallback `unknown` avec warning log

---

**4. Instrumentation `record_cost()`** (ligne ~43-78)

**Ajouter après l'enregistrement BDD (ligne ~69)** :
```python
# MÉTRIQUES PROMETHEUS (nouveau)
try:
    provider = self._detect_provider_from_model(model)

    COST_BY_AGENT.labels(agent=agent, model=model, provider=provider).inc(total_cost)
    TOKENS_CONSUMED.labels(provider=provider, model=model, type="input").inc(input_tokens)
    TOKENS_CONSUMED.labels(provider=provider, model=model, type="output").inc(output_tokens)
    COST_PER_REQUEST.observe(total_cost)
    REQUESTS_BY_PROVIDER.labels(provider=provider, model=model).inc()

    logger.debug(
        f"[Prometheus] Metrics recorded for {provider}/{model}: "
        f"${total_cost:.6f}, {input_tokens} in, {output_tokens} out"
    )

except Exception as metrics_error:
    logger.warning(f"[Prometheus] Failed to record metrics: {metrics_error}", exc_info=True)
    # Ne pas fail si métriques KO
```

**Checklist** :
- [ ] Try/except autour instrumentation (pas de crash si Prometheus KO)
- [ ] Appel `_detect_provider_from_model(model)`
- [ ] 5 métriques mises à jour :
  - [ ] `COST_BY_AGENT.labels(...).inc(total_cost)`
  - [ ] `TOKENS_CONSUMED.labels(...type="input").inc(input_tokens)`
  - [ ] `TOKENS_CONSUMED.labels(...type="output").inc(output_tokens)`
  - [ ] `COST_PER_REQUEST.observe(total_cost)`
  - [ ] `REQUESTS_BY_PROVIDER.labels(...).inc()`
- [ ] Logger debug avec provider/model/cost/tokens

---

**5. Méthode `update_periodic_gauges()`** (ligne ~115)
```python
async def update_periodic_gauges(self) -> None:
    """Met à jour les gauges Prometheus pour coûts daily/weekly/monthly."""
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

**Checklist** :
- [ ] Méthode `update_periodic_gauges(self) -> None` créée
- [ ] Appel `get_spending_summary()` pour récupérer coûts
- [ ] Set 3 gauges : `DAILY_COST_GAUGE`, `WEEKLY_COST_GAUGE`, `MONTHLY_COST_GAUGE`
- [ ] Logger debug avec valeurs
- [ ] Try/except global (pas de crash)

---

**6. Background Task pour Gauges** (fichier `src/backend/main.py`)

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

@app.on_event("startup")
async def startup_background_tasks():
    asyncio.create_task(update_cost_gauges_periodically())
```

**Checklist** :
- [ ] Fonction `update_cost_gauges_periodically()` créée
- [ ] Boucle infinie `while True`
- [ ] Try/except autour appel `update_periodic_gauges()`
- [ ] `await asyncio.sleep(5 * 60)` (5 minutes)
- [ ] Startup event handler `@app.on_event("startup")`
- [ ] `asyncio.create_task(update_cost_gauges_periodically())`

---

### **Tests Prometheus**

#### Test #1 : Métriques Exposées
```bash
# 1. Déclencher quelques requêtes LLM (3-5 messages)
curl -X POST http://localhost:8000/api/chat/send \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Session-Id: $SESSION_ID" \
  -d '{"message": "Hello, tell me about AI"}'

# 2. Vérifier endpoint /api/metrics
curl http://localhost:8000/api/metrics | grep llm_

# Exemple output attendu :
# llm_cost_dollars_total{agent="assistant",model="gpt-4o-mini",provider="openai"} 0.000123
# llm_tokens_total{provider="openai",model="gpt-4o-mini",type="input"} 150
# llm_tokens_total{provider="openai",model="gpt-4o-mini",type="output"} 50
# llm_cost_per_request_dollars_bucket{le="0.001"} 3
# llm_requests_total{provider="openai",model="gpt-4o-mini"} 3
# llm_daily_cost_dollars 0.000369
```

**Checklist** :
- [ ] Endpoint `/api/metrics` retourne 200
- [ ] Métriques `llm_*` présentes
- [ ] `llm_cost_dollars_total` avec labels `agent`, `model`, `provider`
- [ ] `llm_tokens_total` avec labels `provider`, `model`, `type`
- [ ] `llm_cost_per_request_dollars_bucket` avec buckets
- [ ] `llm_requests_total` avec compteur
- [ ] `llm_daily_cost_dollars` avec valeur > 0 (si conversations récentes)

---

#### Test #2 : Requêtes PromQL
```promql
# Taux de coût par seconde (tous providers)
sum(rate(llm_cost_dollars_total[5m]))

# Coût par provider (top 3)
topk(3, sum by (provider) (rate(llm_cost_dollars_total[5m])))

# Coût moyen par requête (P50)
histogram_quantile(0.5, rate(llm_cost_per_request_dollars_bucket[5m]))

# Tokens/sec par provider
sum by (provider) (rate(llm_tokens_total[1m]))
```

**Checklist** :
- [ ] Requête "Taux de coût" retourne valeur > 0
- [ ] Requête "Top 3 providers" retourne (ex: openai, google, anthropic)
- [ ] Requête "P50 coût" retourne valeur réaliste (ex: $0.0001-$0.01)
- [ ] Requête "Tokens/sec" retourne valeur > 0

---

#### Test #3 : Background Task Gauges
```bash
# Attendre 5 minutes OU déclencher manuellement :
# Dans code temporaire :
await container.cost_tracker().update_periodic_gauges()

# Vérifier logs :
grep "Prometheus.*Periodic gauges updated" logs/backend.log

# Vérifier métriques :
curl http://localhost:8000/api/metrics | grep llm_daily_cost_dollars
# Attendu : valeur non-zero
```

**Checklist** :
- [ ] Log "Periodic gauges updated" présent
- [ ] `llm_daily_cost_dollars` mis à jour toutes les 5 min
- [ ] `llm_weekly_cost_dollars` mis à jour
- [ ] `llm_monthly_cost_dollars` mis à jour

---

### **Validation Action #3**

- [ ] ✅ 6 métriques Prometheus définies
- [ ] ✅ Helper `_detect_provider_from_model()` OK
- [ ] ✅ `record_cost()` instrumenté (5 métriques incrémentées)
- [ ] ✅ `update_periodic_gauges()` créé
- [ ] ✅ Background task scheduler lancé (startup event)
- [ ] ✅ Endpoint `/api/metrics` retourne métriques `llm_*`
- [ ] ✅ Test requête LLM → métriques incrémentées
- [ ] ✅ Test requêtes PromQL → valeurs réalistes
- [ ] ✅ Gauges periodic mises à jour toutes les 5 min

---

## 🧪 Tests End-to-End Sprint 0

### **E2E Test #1 : Flow Complet User**

**Scénario** :
1. User login
2. Navigation `/dashboard`
3. Dashboard charge données
4. User envoie 3 messages chat (Gemini)
5. Dashboard refresh (manuel + auto)
6. Vérifier coûts affichés

**Checklist** :
- [ ] Login OK
- [ ] Navigation `/dashboard` → render dashboard UI
- [ ] Fetch API `/api/dashboard/costs/summary` → 200
- [ ] Cards coûts affichées avec valeurs
- [ ] 3 messages envoyés (Gemini)
- [ ] Logs backend : `[Gemini] Cost calculated: $X`
- [ ] BDD : 3 nouvelles lignes `costs` table (coûts > 0)
- [ ] Dashboard refresh manuel → nouvelles valeurs
- [ ] Attendre 2 min → auto-refresh
- [ ] Pas d'erreur console

---

### **E2E Test #2 : Prometheus Flow**

**Scénario** :
1. Déclencher 5 requêtes LLM (mix OpenAI + Gemini + Anthropic)
2. Vérifier métriques Prometheus
3. Requêtes PromQL
4. Attendre 5 min → vérifier gauges

**Checklist** :
- [ ] 5 requêtes LLM envoyées (providers différents)
- [ ] Logs backend : métriques enregistrées
- [ ] `curl /api/metrics | grep llm_` → métriques présentes
- [ ] `llm_cost_dollars_total` compteurs par provider
- [ ] `llm_tokens_total` compteurs input + output
- [ ] `llm_cost_per_request_dollars` histogram rempli
- [ ] Requêtes PromQL retournent valeurs cohérentes
- [ ] Attendre 5 min → gauges mises à jour

---

### **E2E Test #3 : Seuils Alertes**

**Scénario** :
1. Simuler dépassement budget journalier
2. Vérifier badge threshold dashboard
3. Vérifier alerte Prometheus (si configurée)

**Checklist** :
- [ ] Insérer coût élevé dans BDD (ex: $5) :
  ```sql
  INSERT INTO costs (timestamp, agent, model, total_cost, feature, user_id)
  VALUES (datetime('now'), 'test', 'gpt-4o', 5.0, 'test', 'user_123');
  ```
- [ ] Dashboard refresh
- [ ] Badge "Aujourd'hui" → classe `threshold-exceeded` (rouge)
- [ ] Texte "XXX% de $3.00" affiché
- [ ] Prometheus : `llm_daily_cost_dollars` > seuil
- [ ] (Si alertes configurées) Alerte `DailyCostExceeded` trigger

---

## 📝 Documentation Finale Sprint 0

### **Fichiers à Mettre à Jour**

#### ✅ `docs/cockpit/COCKPIT_GAPS_AND_FIXES.md`
**Sections à modifier** :
- [ ] Changer statut de "📋 ANALYSE COMPLÈTE" → "✅ IMPLÉMENTÉ"
- [ ] Ajouter section "Résultats Sprint 0" avec :
  - Screenshots dashboard UI
  - Logs Gemini cost calculation
  - Capture métriques Prometheus
  - Requêtes PromQL validées

---

#### ✅ `docs/passation.md` ou `AGENT_SYNC.md`
**Ajouter** :
```markdown
## Sprint 0 Cockpit - Terminé (2025-10-XX)

### Implémentations
1. ✅ Frontend Dashboard UI (`src/frontend/features/dashboard/`)
   - 4 cards coûts (today/week/month/total)
   - Seuils budgétaires visuels
   - Stats monitoring
   - Auto-refresh 2 min

2. ✅ Fix coûts Gemini (`src/backend/features/chat/llm_stream.py`)
   - Utilisation `count_tokens()` pour input/output
   - Coûts Gemini maintenant trackés correctement

3. ✅ Métriques Prometheus coûts (`src/backend/core/cost_tracker.py`)
   - 6 métriques : Counter (cost/tokens/requests) + Histogram + Gauge
   - Background task update gauges (5 min)
   - Endpoint `/api/metrics` exposé

### Tests Validés
- ✅ E2E dashboard UI
- ✅ Gemini coûts > 0
- ✅ Métriques Prometheus exposées
- ✅ Requêtes PromQL OK
- ✅ Seuils alertes visuels

### Prochaines Étapes
- Phase P2 Mémoire (suite du plan)
```

---

#### ✅ `src/frontend/features/dashboard/README.md`
**Créé** (voir Action #1)

---

## 🎯 KPIs Succès Sprint 0

| KPI | Target | Validation |
|-----|--------|------------|
| **Dashboard UI Accessible** | Route `/dashboard` OK | ⏳ À tester |
| **Coûts Gemini Trackés** | >0 dans BDD | ⏳ À tester |
| **Métriques Prometheus Exposées** | 6 métriques `llm_*` | ⏳ À tester |
| **Seuils Alertes Visuels** | Badge coloré OK/Warning/Exceeded | ⏳ À tester |
| **Performance Dashboard** | Load <2s | ⏳ À mesurer |
| **Rétrocompatibilité** | Admin dashboard non cassé | ⏳ À vérifier |
| **Coûts Gemini Précision** | ±5% vs estimation manuelle | ⏳ À valider |
| **Prometheus Scraping** | Prometheus scrape OK | 🟡 Optionnel (config infra) |

---

## 📅 Timeline Sprint 0

| Jour | Actions | Durée Cumulée |
|------|---------|---------------|
| **J1 Matin** | Action #1 (Dashboard UI - fichiers + HTML) | 3h |
| **J1 Après-midi** | Action #1 (Dashboard UI - logic JS + CSS) | 6h |
| **J1 Soir** | Action #2 (Fix Gemini) | 7h30 |
| **J2 Matin** | Action #3 (Prometheus - métriques + instrumentation) | 9h30 |
| **J2 Après-midi** | Action #3 (Prometheus - gauges + tests) | 11h |
| **J2 Fin** | Tests E2E + Documentation | 12h |

**Total** : 1.5 jours (12h effectives)

---

## ✅ Critères de Complétion

### **Sprint 0 Est Terminé Quand** :
- [x] ✅ Document créé (ce fichier)
- [ ] ✅ Action #1 : Dashboard UI fonctionnel et accessible
- [ ] ✅ Action #2 : Coûts Gemini non-zero dans BDD
- [ ] ✅ Action #3 : Métriques Prometheus exposées et testées
- [ ] ✅ Tests E2E validés (3 scénarios)
- [ ] ✅ Documentation mise à jour (COCKPIT_GAPS_AND_FIXES.md + passation.md)
- [ ] ✅ Aucune régression (admin dashboard, conversations, tests existants)
- [ ] ✅ Review code + commit + push
- [ ] ✅ (Optionnel) Deploy production + smoke test

---

**Document créé le** : 2025-10-10
**Dernière mise à jour** : 2025-10-10
**Statut** : ⏳ EN ATTENTE (après P2 Mémoire)
