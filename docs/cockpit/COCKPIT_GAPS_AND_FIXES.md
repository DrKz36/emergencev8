# 🚨 Cockpit Gaps & Fixes - Plan de Déblocage

**Date** : 2025-10-10
**Statut** : 📋 ANALYSE COMPLÈTE - Prêt pour implémentation
**Priorité** : P0 (à faire après P2 Mémoire)

---

## 📊 État Actuel du Cockpit

### ✅ Ce Qui Fonctionne (85% Backend)

#### **Backend Infrastructure - SOLIDE**

**1. Endpoints API Opérationnels**
- `src/backend/features/dashboard/router.py` (v3.2)
  - `GET /api/dashboard/costs/summary` - Résumé coûts + monitoring
  - `GET /api/dashboard/costs/summary/session/{session_id}` - Par session
  - `GET /api/dashboard/timeline/activity?period=7d|30d|90d|1y` - Messages/threads
  - `GET /api/dashboard/timeline/costs?period=...` - Coûts par jour
  - `GET /api/dashboard/timeline/tokens?period=...` - Tokens par jour
  - `GET /api/dashboard/distribution/{metric}?period=...` - Distribution par agent

**2. Services Backend**
- `src/backend/features/dashboard/service.py` (v11.1 - DTO robuste)
  - Tolérance aux champs manquants
  - Fallback seuils d'alerte via env vars
  - Gestion erreurs complète
  - Retourne structure:
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
        "daily_threshold": 1.0,
        "weekly_threshold": 1.0,
        "monthly_threshold": 1.0
      },
      "messages": {"total": 0, "today": 0, "week": 0, "month": 0},
      "tokens": {"total": 0, "input": 0, "output": 0, "avgPerMessage": 0},
      "raw_data": {"documents": [], "sessions": []}
    }
    ```

- `src/backend/features/dashboard/timeline_service.py`
  - Queries SQL optimisées avec CTE récursives
  - Support filtrage user_id + session_id
  - Agrégations temporelles précises

**3. Tracking Coûts**
- `src/backend/core/cost_tracker.py` (v13.1)
  - Enregistrement async (aiosqlite)
  - Alertes configurables (daily/weekly/monthly)
  - Mapping tolérant clés UI/BDD

- `src/backend/features/chat/pricing.py`
  - Tarifs à jour tous providers:
    - GPT-4o-mini: $0.15/$0.60 par M tokens
    - Gemini 2.5 Flash: $0.35/$0.70 par M tokens
    - Claude 3.5 Haiku: $0.25/$1.25 par M tokens

- `src/backend/features/chat/llm_stream.py`
  - Calcul coûts OpenAI: ✅ OK (ligne 127-136)
  - Calcul coûts Anthropic: ✅ OK (ligne 215-225)
  - Calcul coûts Gemini: ❌ BROKEN (ligne 178-180)

- `src/backend/features/chat/service.py`
  - Enregistrement `cost_tracker.record_cost()`: ✅ OK (ligne 1394)
  - user_id + session_id trackés correctement

**4. Admin Dashboard**
- `src/backend/features/dashboard/admin_router.py`
  - `GET /api/admin/dashboard/global` - Stats globales
  - `GET /api/admin/dashboard/user/{user_id}` - Détails user
  - Protection role admin

- `src/backend/features/dashboard/admin_service.py`
  - Agrégations multi-users
  - Breakdown par utilisateur

**5. Frontend Admin**
- `src/frontend/features/admin/admin-dashboard.js` (v1.0)
  - Vue globale (stats système)
  - Vue utilisateurs (liste + détails)
  - Vue coûts (répartition)
  - Auto-refresh 2 min
  - ⚠️ **ADMIN ONLY** (pas pour users standards)

---

### ❌ Ce Qui Manque (3 Gaps Critiques)

#### 🔴 **GAP #1 : Frontend Dashboard Utilisateur ABSENT**

**Problème** :
- ❌ Aucun fichier `dashboard-ui.js` ou `cockpit.js` trouvé
- ❌ Le dashboard admin existe mais est **inaccessible aux users normaux**
- ❌ Pas d'intégration menu/routing pour le cockpit

**Impact** :
- **Les utilisateurs ne peuvent PAS voir leurs coûts/métriques**
- Les endpoints backend `/api/dashboard/*` sont inutilisés côté user
- ROI du travail backend = 0 sans UI

**Fichiers à Créer** :
```
src/frontend/features/dashboard/
├── dashboard-ui.js          (composant principal)
├── dashboard-ui.css         (styles)
├── metrics-chart.js         (graphiques Chart.js)
└── README.md                (doc composant)
```

**Intégration** :
- `src/frontend/main.js` : Ajouter route `/dashboard`
- `src/frontend/index.html` : Lien menu "📊 Cockpit"
- EventBus : Écouter `session:changed` pour refresh

---

#### 🔴 **GAP #2 : Coûts Gemini = 0 (Sous-estimation 70-80%)**

**Problème** :
```python
# src/backend/features/chat/llm_stream.py:178-180
cost_info_container.setdefault("input_tokens", 0)   # ← Toujours 0
cost_info_container.setdefault("output_tokens", 0)  # ← Toujours 0
cost_info_container.setdefault("total_cost", 0.0)   # ← Toujours 0
```

**Cause Racine** :
- Google Generative AI **ne retourne PAS** `usage` dans la réponse streaming
- Contrairement à OpenAI (`stream_options={"include_usage": True}`)
- Il faut utiliser `model.count_tokens()` manuellement

**Impact** :
- ❌ **Tous les coûts Gemini sont à 0** dans la BDD
- Gemini = modèle par défaut (70-80% du traffic)
- **Sous-estimation massive** des coûts réels
- Alertes budgétaires inefficaces

**Solution** :
```python
# Modifier _get_gemini_stream() dans llm_stream.py
async def _get_gemini_stream(self, model, system_prompt, history, cost_info_container):
    _model = genai.GenerativeModel(model_name=model, system_instruction=system_prompt)

    # COUNT TOKENS AVANT (input)
    prompt_parts = [system_prompt] + [msg.get("content", "") for msg in history]
    input_tokens = _model.count_tokens(prompt_parts).total_tokens

    resp = await _model.generate_content_async(history, stream=True, ...)

    full_response_text = ""
    async for chunk in resp:
        text = getattr(chunk, "text", None)
        if text:
            full_response_text += text
            yield text

    # COUNT TOKENS APRÈS (output)
    output_tokens = _model.count_tokens(full_response_text).total_tokens

    # CALCUL COÛT
    pricing = MODEL_PRICING.get(model, {"input": 0, "output": 0})
    cost_info_container.update({
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_cost": (input_tokens * pricing["input"]) + (output_tokens * pricing["output"])
    })
```

---

#### 🟠 **GAP #3 : Métriques Prometheus Coûts ABSENTES**

**Problème** :
- ✅ Phase 3 Prometheus implémentée pour **MemoryAnalyzer uniquement**
  - `memory_analysis_success_total`
  - `memory_analysis_failure_total`
  - `memory_cache_hits_total`
  - `memory_analysis_duration_seconds`

- ❌ **Aucune métrique** pour coûts/tokens/billing :
  - Pas de `llm_cost_dollars_total` par agent/model
  - Pas de `llm_tokens_total` par provider
  - Pas de `llm_daily_cost_gauge` pour alertes
  - Pas de `llm_cost_per_request_histogram`

**Impact** :
- ❌ Impossible de monitorer les dépenses en temps réel
- ❌ Pas d'alertes Prometheus sur dépassement budget
- ❌ Pas de dashboards Grafana pour billing
- ❌ Pas de métriques pour optimisation coûts

**Solution** :
Ajouter dans `src/backend/core/cost_tracker.py` :
```python
from prometheus_client import Counter, Histogram, Gauge

# Coûts par agent/model
COST_BY_AGENT = Counter(
    "llm_cost_dollars_total",
    "Total cost in dollars by agent and model",
    ["agent", "model", "provider"]
)

# Tokens consommés
TOKENS_CONSUMED = Counter(
    "llm_tokens_total",
    "Total tokens consumed",
    ["provider", "model", "type"]  # type = input|output
)

# Distribution coût par requête
COST_PER_REQUEST = Histogram(
    "llm_cost_per_request_dollars",
    "Cost per request distribution",
    buckets=[0.0001, 0.001, 0.01, 0.1, 1.0]
)

# Gauges pour alertes
DAILY_COST_GAUGE = Gauge("llm_daily_cost_dollars", "Current daily cost")
WEEKLY_COST_GAUGE = Gauge("llm_weekly_cost_dollars", "Current weekly cost")
MONTHLY_COST_GAUGE = Gauge("llm_monthly_cost_dollars", "Current monthly cost")
```

Instrumenter `record_cost()` :
```python
async def record_cost(self, agent, model, input_tokens, output_tokens, total_cost, ...):
    # ... existing DB recording ...

    # Prometheus metrics
    provider = self._detect_provider(model)
    COST_BY_AGENT.labels(agent=agent, model=model, provider=provider).inc(total_cost)
    TOKENS_CONSUMED.labels(provider=provider, model=model, type="input").inc(input_tokens)
    TOKENS_CONSUMED.labels(provider=provider, model=model, type="output").inc(output_tokens)
    COST_PER_REQUEST.observe(total_cost)

    # Update gauges (requires daily/weekly/monthly aggregation)
    summary = await self.get_spending_summary()
    DAILY_COST_GAUGE.set(summary.get("today", 0))
    WEEKLY_COST_GAUGE.set(summary.get("this_week", 0))
    MONTHLY_COST_GAUGE.set(summary.get("this_month", 0))
```

---

## 🎯 Plan d'Action - Sprint 0 Cockpit (1-2 jours)

### **Action #1 : Frontend Dashboard UI** (4-6 heures)

**Créer** : `src/frontend/features/dashboard/dashboard-ui.js`

```javascript
/**
 * User Dashboard - Cockpit de pilotage
 * V1.0 - Visualisation coûts et métriques utilisateur
 */
import { EventBus } from '../../core/event-bus.js';

export class DashboardUI {
  constructor() {
    this.container = null;
    this.currentSessionId = null;
    this.refreshInterval = null;
  }

  async init(containerId) {
    this.container = document.getElementById(containerId);
    if (!this.container) {
      console.error('[DashboardUI] Container not found');
      return;
    }

    this.render();
    await this.loadData();
    this.startAutoRefresh();
    this.attachEventListeners();
  }

  render() {
    this.container.innerHTML = `
      <div class="dashboard-cockpit">
        <!-- Header -->
        <div class="dashboard-header">
          <h1>📊 Cockpit de Pilotage</h1>
          <button class="btn-refresh-dashboard">🔄 Actualiser</button>
        </div>

        <!-- Costs Cards -->
        <div class="dashboard-costs-grid">
          <div class="cost-card" data-period="today">
            <div class="cost-label">Aujourd'hui</div>
            <div class="cost-value" data-cost="today">$0.00</div>
            <div class="cost-threshold" data-threshold="daily"></div>
          </div>
          <div class="cost-card" data-period="week">
            <div class="cost-label">Cette Semaine</div>
            <div class="cost-value" data-cost="week">$0.00</div>
            <div class="cost-threshold" data-threshold="weekly"></div>
          </div>
          <div class="cost-card" data-period="month">
            <div class="cost-label">Ce Mois</div>
            <div class="cost-value" data-cost="month">$0.00</div>
            <div class="cost-threshold" data-threshold="monthly"></div>
          </div>
          <div class="cost-card highlight" data-period="total">
            <div class="cost-label">Total</div>
            <div class="cost-value" data-cost="total">$0.00</div>
          </div>
        </div>

        <!-- Monitoring Stats -->
        <div class="dashboard-monitoring">
          <div class="monitoring-stat">
            <span class="stat-icon">💬</span>
            <span class="stat-value" data-stat="messages">0</span>
            <span class="stat-label">Messages</span>
          </div>
          <div class="monitoring-stat">
            <span class="stat-icon">🧵</span>
            <span class="stat-value" data-stat="sessions">0</span>
            <span class="stat-label">Sessions</span>
          </div>
          <div class="monitoring-stat">
            <span class="stat-icon">📄</span>
            <span class="stat-value" data-stat="documents">0</span>
            <span class="stat-label">Documents</span>
          </div>
          <div class="monitoring-stat">
            <span class="stat-icon">🪙</span>
            <span class="stat-value" data-stat="tokens">0</span>
            <span class="stat-label">Tokens</span>
          </div>
        </div>

        <!-- Timeline Charts -->
        <div class="dashboard-charts">
          <div class="chart-container">
            <h3>Évolution des Coûts (7 derniers jours)</h3>
            <canvas id="costs-timeline-chart"></canvas>
          </div>
          <div class="chart-container">
            <h3>Activité (Messages & Threads)</h3>
            <canvas id="activity-timeline-chart"></canvas>
          </div>
        </div>
      </div>
    `;
  }

  async loadData() {
    try {
      const sessionId = this.getCurrentSessionId();
      const headers = {
        'Authorization': `Bearer ${this.getAuthToken()}`,
        'Content-Type': 'application/json'
      };

      if (sessionId) {
        headers['X-Session-Id'] = sessionId;
      }

      // Load summary
      const summaryResponse = await fetch('/api/dashboard/costs/summary', { headers });
      const data = await summaryResponse.json();

      this.renderCosts(data.costs, data.thresholds);
      this.renderMonitoring(data.monitoring, data.messages, data.tokens);

      // Load timelines
      await this.loadTimelines(headers);

    } catch (error) {
      console.error('[DashboardUI] Error loading data:', error);
      this.showError('Impossible de charger les données du cockpit');
    }
  }

  renderCosts(costs, thresholds) {
    // Today
    this.container.querySelector('[data-cost="today"]').textContent =
      `$${costs.today_cost.toFixed(2)}`;
    this.renderThreshold('daily', costs.today_cost, thresholds.daily_threshold);

    // Week
    this.container.querySelector('[data-cost="week"]').textContent =
      `$${costs.current_week_cost.toFixed(2)}`;
    this.renderThreshold('weekly', costs.current_week_cost, thresholds.weekly_threshold);

    // Month
    this.container.querySelector('[data-cost="month"]').textContent =
      `$${costs.current_month_cost.toFixed(2)}`;
    this.renderThreshold('monthly', costs.current_month_cost, thresholds.monthly_threshold);

    // Total
    this.container.querySelector('[data-cost="total"]').textContent =
      `$${costs.total_cost.toFixed(2)}`;
  }

  renderThreshold(period, current, threshold) {
    const el = this.container.querySelector(`[data-threshold="${period}"]`);
    const percent = (current / threshold) * 100;

    let className = 'threshold-ok';
    if (percent > 100) className = 'threshold-exceeded';
    else if (percent > 80) className = 'threshold-warning';

    el.className = `cost-threshold ${className}`;
    el.textContent = `${percent.toFixed(0)}% de $${threshold.toFixed(2)}`;
  }

  renderMonitoring(monitoring, messages, tokens) {
    this.container.querySelector('[data-stat="messages"]').textContent = messages.total || 0;
    this.container.querySelector('[data-stat="sessions"]').textContent = monitoring.total_sessions || 0;
    this.container.querySelector('[data-stat="documents"]').textContent = monitoring.total_documents || 0;
    this.container.querySelector('[data-stat="tokens"]').textContent =
      this.formatNumber(tokens.total || 0);
  }

  async loadTimelines(headers) {
    try {
      const [costsData, activityData] = await Promise.all([
        fetch('/api/dashboard/timeline/costs?period=7d', { headers }).then(r => r.json()),
        fetch('/api/dashboard/timeline/activity?period=7d', { headers }).then(r => r.json())
      ]);

      this.renderCostsChart(costsData);
      this.renderActivityChart(activityData);

    } catch (error) {
      console.error('[DashboardUI] Error loading timelines:', error);
    }
  }

  renderCostsChart(data) {
    const ctx = document.getElementById('costs-timeline-chart');
    if (!ctx) return;

    // Use Chart.js or simple canvas drawing
    // TODO: Implement chart rendering
    console.log('[DashboardUI] Costs chart data:', data);
  }

  renderActivityChart(data) {
    const ctx = document.getElementById('activity-timeline-chart');
    if (!ctx) return;

    // TODO: Implement chart rendering
    console.log('[DashboardUI] Activity chart data:', data);
  }

  attachEventListeners() {
    // Refresh button
    const refreshBtn = this.container.querySelector('.btn-refresh-dashboard');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', () => this.refresh());
    }

    // Session change
    EventBus.on('session:changed', () => {
      this.currentSessionId = null; // Will reload on next refresh
      this.loadData();
    });
  }

  async refresh() {
    const btn = this.container.querySelector('.btn-refresh-dashboard');
    if (btn) {
      btn.disabled = true;
      btn.textContent = '⏳ Actualisation...';
    }

    await this.loadData();

    if (btn) {
      btn.textContent = '✓ Actualisé';
      setTimeout(() => {
        btn.textContent = '🔄 Actualiser';
        btn.disabled = false;
      }, 2000);
    }
  }

  startAutoRefresh() {
    // Refresh every 2 minutes
    this.refreshInterval = setInterval(() => {
      this.loadData();
    }, 2 * 60 * 1000);
  }

  stopAutoRefresh() {
    if (this.refreshInterval) {
      clearInterval(this.refreshInterval);
      this.refreshInterval = null;
    }
  }

  getCurrentSessionId() {
    try {
      const state = JSON.parse(localStorage.getItem('emergenceState-V14') || '{}');
      return state.session?.id || null;
    } catch (e) {
      return null;
    }
  }

  getAuthToken() {
    return localStorage.getItem('emergence.id_token') ||
           sessionStorage.getItem('emergence.id_token');
  }

  formatNumber(num) {
    if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(1)}M`;
    if (num >= 1_000) return `${(num / 1_000).toFixed(1)}K`;
    return num.toString();
  }

  showError(message) {
    console.error('[DashboardUI]', message);
    // TODO: Integrate with notification system
  }

  destroy() {
    this.stopAutoRefresh();
    if (this.container) {
      this.container.innerHTML = '';
    }
  }
}

// Export singleton
export const dashboardUI = new DashboardUI();
```

**Créer** : `src/frontend/features/dashboard/dashboard-ui.css`

```css
/* Dashboard Cockpit Styles */
.dashboard-cockpit {
  padding: 2rem;
  max-width: 1400px;
  margin: 0 auto;
}

.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
}

.dashboard-header h1 {
  font-size: 2rem;
  font-weight: 600;
  margin: 0;
}

.btn-refresh-dashboard {
  padding: 0.5rem 1rem;
  background: var(--color-primary);
  color: white;
  border: none;
  border-radius: 0.5rem;
  cursor: pointer;
  font-size: 0.9rem;
}

.btn-refresh-dashboard:hover {
  background: var(--color-primary-dark);
}

.btn-refresh-dashboard:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Costs Grid */
.dashboard-costs-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.cost-card {
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: 0.75rem;
  padding: 1.5rem;
  text-align: center;
}

.cost-card.highlight {
  background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-dark) 100%);
  color: white;
  border: none;
}

.cost-label {
  font-size: 0.875rem;
  color: var(--color-text-secondary);
  margin-bottom: 0.5rem;
}

.cost-card.highlight .cost-label {
  color: rgba(255, 255, 255, 0.9);
}

.cost-value {
  font-size: 2rem;
  font-weight: 700;
  margin-bottom: 0.5rem;
}

.cost-threshold {
  font-size: 0.75rem;
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
}

.cost-threshold.threshold-ok {
  background: var(--color-success-bg);
  color: var(--color-success);
}

.cost-threshold.threshold-warning {
  background: var(--color-warning-bg);
  color: var(--color-warning);
}

.cost-threshold.threshold-exceeded {
  background: var(--color-error-bg);
  color: var(--color-error);
}

/* Monitoring Stats */
.dashboard-monitoring {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 1rem;
  margin-bottom: 2rem;
}

.monitoring-stat {
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: 0.5rem;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.stat-icon {
  font-size: 2rem;
  margin-bottom: 0.5rem;
}

.stat-value {
  font-size: 1.5rem;
  font-weight: 600;
  margin-bottom: 0.25rem;
}

.stat-label {
  font-size: 0.875rem;
  color: var(--color-text-secondary);
}

/* Charts */
.dashboard-charts {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 2rem;
}

.chart-container {
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: 0.75rem;
  padding: 1.5rem;
}

.chart-container h3 {
  font-size: 1.125rem;
  font-weight: 600;
  margin-bottom: 1rem;
}

.chart-container canvas {
  width: 100%;
  height: 300px;
}

/* Dark mode support */
@media (prefers-color-scheme: dark) {
  .dashboard-cockpit {
    --color-bg-secondary: #1a1a1a;
    --color-border: #333;
    --color-text-secondary: #888;
    --color-primary: #3b82f6;
    --color-primary-dark: #2563eb;
    --color-success: #10b981;
    --color-success-bg: rgba(16, 185, 129, 0.1);
    --color-warning: #f59e0b;
    --color-warning-bg: rgba(245, 158, 11, 0.1);
    --color-error: #ef4444;
    --color-error-bg: rgba(239, 68, 68, 0.1);
  }
}
```

**Intégrer dans** : `src/frontend/main.js`

```javascript
// Add after other feature imports
import { dashboardUI } from './features/dashboard/dashboard-ui.js';

// In router or navigation handler
if (window.location.pathname === '/dashboard') {
  await dashboardUI.init('app-container');
}
```

**Ajouter lien menu** : `src/frontend/index.html`

```html
<nav class="main-nav">
  <!-- ... existing links ... -->
  <a href="/dashboard" class="nav-link">
    <span class="nav-icon">📊</span>
    <span class="nav-label">Cockpit</span>
  </a>
</nav>
```

---

### **Action #2 : Fixer Coûts Gemini** (1-2 heures)

**Modifier** : `src/backend/features/chat/llm_stream.py:142-184`

```python
async def _get_gemini_stream(
    self, model, system_prompt, history, cost_info_container
):
    """Stream Gemini avec calcul coûts via count_tokens()."""
    try:
        # Créer modèle
        def _mk_model():
            return genai.GenerativeModel(
                model_name=model,
                system_instruction=system_prompt
            )

        async def _op():
            return (_mk_model(),)

        (_model,) = await self.with_rate_limit_retries("google", _op)

        # COUNT TOKENS INPUT (avant génération)
        try:
            # Construire prompt complet pour count_tokens
            prompt_parts = [system_prompt]
            for msg in history:
                content = msg.get("content", "")
                if content:
                    prompt_parts.append(content)

            # Compter tokens input
            input_tokens = _model.count_tokens(prompt_parts).total_tokens
            logger.debug(f"[Gemini] Input tokens: {input_tokens}")
        except Exception as e:
            logger.warning(f"[Gemini] Failed to count input tokens: {e}")
            input_tokens = 0

        # GÉNÉRATION STREAMING
        resp = await _model.generate_content_async(
            history,
            stream=True,
            generation_config={"temperature": 0.4}
        )

        full_response_text = ""
        async for chunk in resp:
            try:
                text = getattr(chunk, "text", None)
                if not text and getattr(chunk, "candidates", None):
                    cand = chunk.candidates[0]
                    if getattr(cand, "content", None) and getattr(
                        cand.content, "parts", None
                    ):
                        text = "".join(
                            [
                                getattr(p, "text", "") or str(p)
                                for p in cand.content.parts
                                if p
                            ]
                        )
                if text:
                    full_response_text += text
                    yield text
            except Exception:
                pass

        # COUNT TOKENS OUTPUT (après génération)
        try:
            output_tokens = _model.count_tokens(full_response_text).total_tokens
            logger.debug(f"[Gemini] Output tokens: {output_tokens}")
        except Exception as e:
            logger.warning(f"[Gemini] Failed to count output tokens: {e}")
            output_tokens = 0

        # CALCUL COÛT
        pricing = MODEL_PRICING.get(model, {"input": 0, "output": 0})
        total_cost = (input_tokens * pricing["input"]) + (output_tokens * pricing["output"])

        cost_info_container.update({
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_cost": total_cost,
        })

        logger.info(
            f"[Gemini] Cost calculated: ${total_cost:.6f} "
            f"({input_tokens} in + {output_tokens} out tokens)"
        )

    except Exception as e:
        logger.error(f"Gemini stream error: {e}", exc_info=True)
        cost_info_container["__error__"] = "provider_error"
        # Fallback à 0 si erreur
        cost_info_container.setdefault("input_tokens", 0)
        cost_info_container.setdefault("output_tokens", 0)
        cost_info_container.setdefault("total_cost", 0.0)
```

**Test** :
```bash
# Lancer une conversation avec Gemini
# Vérifier les logs backend :
grep "Gemini.*Cost calculated" logs/backend.log

# Vérifier BDD :
sqlite3 instance/emergence.db "SELECT model, input_tokens, output_tokens, total_cost FROM costs WHERE model LIKE '%gemini%' ORDER BY timestamp DESC LIMIT 5;"
```

---

### **Action #3 : Métriques Prometheus Coûts** (2-3 heures)

**Modifier** : `src/backend/core/cost_tracker.py`

```python
# Ajouter après les imports (ligne ~10)
from prometheus_client import Counter, Histogram, Gauge

# Définir métriques (après la classe CostTracker, ligne ~110)
# =============================================================================
# PROMETHEUS METRICS
# =============================================================================

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

# Compteur requêtes par provider
REQUESTS_BY_PROVIDER = Counter(
    "llm_requests_total",
    "Total LLM requests by provider and model",
    ["provider", "model"]
)

# Gauges pour coûts périodiques (pour alertes)
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

**Modifier la méthode `record_cost()`** (ligne ~43-78) :

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
    """Enregistre le coût d'une opération via le module requêtes + métriques Prometheus."""
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

**Ajouter helper `_detect_provider_from_model()`** (ligne ~110) :

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

**Mettre à jour les gauges périodiques** (nouvelle méthode, ligne ~115) :

```python
async def update_periodic_gauges(self) -> None:
    """
    Met à jour les gauges Prometheus pour coûts daily/weekly/monthly.
    À appeler périodiquement (ex: toutes les 5 minutes via cron/scheduler).
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

**Ajouter scheduler pour gauges** (dans `src/backend/main.py` ou `containers.py`) :

```python
# Dans main.py, après init app
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

# Lancer background task
@app.on_event("startup")
async def startup_background_tasks():
    asyncio.create_task(update_cost_gauges_periodically())
```

**Test Prometheus** :

```bash
# 1. Déclencher quelques requêtes LLM
curl -X POST http://localhost:8000/api/chat/send ...

# 2. Vérifier métriques exposées
curl http://localhost:8000/api/metrics | grep llm_

# Exemple output attendu :
# llm_cost_dollars_total{agent="assistant",model="gpt-4o-mini",provider="openai"} 0.000123
# llm_tokens_total{provider="openai",model="gpt-4o-mini",type="input"} 150
# llm_tokens_total{provider="openai",model="gpt-4o-mini",type="output"} 50
# llm_cost_per_request_dollars_bucket{le="0.001"} 3
# llm_requests_total{provider="openai",model="gpt-4o-mini"} 3
# llm_daily_cost_dollars 0.000369
```

**Requêtes Prometheus utiles** :

```promql
# Taux de coût par seconde (tous providers)
sum(rate(llm_cost_dollars_total[5m]))

# Coût par provider (top 3)
topk(3, sum by (provider) (rate(llm_cost_dollars_total[5m])))

# Coût moyen par requête (P50)
histogram_quantile(0.5, rate(llm_cost_per_request_dollars_bucket[5m]))

# Alerte dépassement budget journalier
llm_daily_cost_dollars > 5.0

# Tokens/sec par provider
sum by (provider) (rate(llm_tokens_total[1m]))
```

**Alertes Prometheus recommandées** (`prometheus_rules.yml`) :

```yaml
groups:
  - name: llm_costs
    interval: 1m
    rules:
      # Budget journalier dépassé
      - alert: DailyCostExceeded
        expr: llm_daily_cost_dollars > 3.0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Budget journalier dépassé"
          description: "Coût journalier actuel: ${{ $value }}"

      # Budget mensuel proche
      - alert: MonthlyCostApproaching
        expr: llm_monthly_cost_dollars > 15.0
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Budget mensuel proche de la limite"
          description: "Coût mensuel actuel: ${{ $value }}"

      # Coût par requête anormalement élevé
      - alert: HighCostPerRequest
        expr: histogram_quantile(0.95, rate(llm_cost_per_request_dollars_bucket[5m])) > 0.1
        for: 5m
        labels:
          severity: info
        annotations:
          summary: "Coût par requête élevé (P95)"
          description: "P95 cost: ${{ $value }}"
```

---

## 📋 Checklist Sprint 0 Cockpit

### **Frontend (Action #1)**
- [ ] Créer `src/frontend/features/dashboard/dashboard-ui.js`
- [ ] Créer `src/frontend/features/dashboard/dashboard-ui.css`
- [ ] Intégrer dans `src/frontend/main.js` (route `/dashboard`)
- [ ] Ajouter lien menu dans `src/frontend/index.html`
- [ ] Tester chargement données via API
- [ ] Tester refresh auto (2 min)
- [ ] Tester affichage seuils alertes (today/week/month)
- [ ] (Optionnel) Implémenter charts Chart.js

### **Backend Gemini (Action #2)**
- [ ] Modifier `src/backend/features/chat/llm_stream.py:142-184`
- [ ] Ajouter `count_tokens()` pour input (avant génération)
- [ ] Ajouter `count_tokens()` pour output (après génération)
- [ ] Calculer coût avec tarifs `MODEL_PRICING`
- [ ] Logger tokens + coût pour debug
- [ ] Tester avec conversation Gemini
- [ ] Vérifier BDD : `SELECT * FROM costs WHERE model LIKE '%gemini%'`
- [ ] Valider coûts non-zero

### **Prometheus (Action #3)**
- [ ] Ajouter imports `prometheus_client` dans `cost_tracker.py`
- [ ] Définir 6 métriques (Counter + Histogram + Gauge)
- [ ] Modifier `record_cost()` pour instrumenter métriques
- [ ] Ajouter helper `_detect_provider_from_model()`
- [ ] Ajouter méthode `update_periodic_gauges()`
- [ ] Créer background task dans `main.py` (toutes les 5 min)
- [ ] Tester endpoint `/api/metrics` (vérifier `llm_*`)
- [ ] (Optionnel) Configurer Prometheus scraping
- [ ] (Optionnel) Créer dashboard Grafana
- [ ] (Optionnel) Ajouter alertes Prometheus

### **Tests & Validation**
- [ ] Test E2E : Conversation → Vérifier coûts BDD → Vérifier métriques Prometheus
- [ ] Test Gemini : Coûts non-zero après fix
- [ ] Test Dashboard UI : Affichage correct toutes sections
- [ ] Test Seuils : Alertes visuelles si budget dépassé
- [ ] Smoke test admin dashboard (pas cassé)

### **Documentation**
- [ ] Mettre à jour ce document avec résultats tests
- [ ] Créer `src/frontend/features/dashboard/README.md`
- [ ] Documenter métriques Prometheus dans `docs/monitoring/`
- [ ] Mettre à jour `AGENT_SYNC.md` ou `docs/passation.md`

---

## 🔄 Synchronisation avec Plan P2 Mémoire

### **Timeline Globale Ajustée**

**Phase Actuelle : P2 Mémoire (Prioritaire)**
- Sprint 1 : Indexation ChromaDB + Cache préférences (2-3 jours)
- Sprint 2 : Batch prefetch + Proactive hints backend (2-3 jours)
- Sprint 3 : Proactive hints UI + Dashboard mémoire (2-3 jours)
- **Durée P2** : 6-9 jours

**Après P2 : Sprint 0 Cockpit**
- Action #1 : Frontend Dashboard UI (4-6 heures)
- Action #2 : Fix coûts Gemini (1-2 heures)
- Action #3 : Métriques Prometheus coûts (2-3 heures)
- **Durée Sprint 0** : 1-2 jours

**Durée Totale** : 7-11 jours

---

## 📚 Références Docs Existantes

### **Plans & Architecture**
- [MEMORY_P2_PERFORMANCE_PLAN.md](../optimizations/MEMORY_P2_PERFORMANCE_PLAN.md) - Plan détaillé P2 (à suivre en priorité)
- [PHASES_RECAP.md](../deployments/PHASES_RECAP.md) - Historique Phase 2 & 3 Prometheus
- [cockpit-qa-playbook.md](../qa/cockpit-qa-playbook.md) - Scripts QA + validation

### **Code Backend**
- `src/backend/features/dashboard/router.py` - Endpoints API
- `src/backend/features/dashboard/service.py` - DTO cockpit (v11.1)
- `src/backend/features/dashboard/timeline_service.py` - Agrégations temporelles
- `src/backend/core/cost_tracker.py` - Tracking coûts (v13.1)
- `src/backend/features/chat/pricing.py` - Tarifs models
- `src/backend/features/chat/llm_stream.py` - Streaming + calcul coûts

### **Code Frontend**
- `src/frontend/features/admin/admin-dashboard.js` - Dashboard admin (v1.0)
- `src/frontend/features/memory/memory.js` - UI mémoire LTM

---

## ⚠️ Points d'Attention

### **Gemini count_tokens() Limitations**
- ⚠️ `count_tokens()` est **synchrone** dans l'API officielle
- Peut ajouter ~50-100ms de latence par requête
- Acceptable pour tracking précis des coûts
- Alternative : estimation tokens (moins précis) :
  ```python
  # Rough estimate: 1 token ≈ 4 chars
  estimated_tokens = len(text) // 4
  ```

### **Prometheus Gauges Update**
- Les gauges `llm_daily_cost_dollars` etc. doivent être **refresh périodiquement**
- Background task toutes les 5 min recommandé
- Alternative : Prometheus recording rules (côté Prometheus, pas backend)

### **Chart.js pour Timelines**
- `dashboard-ui.js` inclut placeholders pour charts
- Nécessite `chart.js` library :
  ```html
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
  ```
- Ou implémenter charts simples en SVG/Canvas natif

---

## 🎯 Critères de Succès Sprint 0

| Critère | KPI | Status |
|---------|-----|--------|
| **Frontend Dashboard** | UI accessible à `/dashboard` | ⏳ À implémenter |
| **Coûts Gemini** | >0 dans BDD après conversations | ⏳ À fixer |
| **Métriques Prometheus** | `llm_*` métriques exposées | ⏳ À implémenter |
| **Alertes Budgétaires** | Seuils visuels fonctionnels | ⏳ À tester |
| **Performance** | Dashboard load <2s | ⏳ À valider |
| **Rétrocompatibilité** | Admin dashboard non cassé | ⏳ À vérifier |

---

**Document créé le** : 2025-10-10
**Auteur** : Claude Code
**Statut** : ✅ COMPLET - Prêt pour implémentation post-P2
