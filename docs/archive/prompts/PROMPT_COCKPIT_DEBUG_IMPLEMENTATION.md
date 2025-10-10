# 🚀 Prompt Implémentation & Debug Cockpit - Phase Sprint 0

**Date** : 2025-10-10
**Priorité** : P0 (après Phase P2 Mémoire)
**Durée Estimée** : 1-2 jours (7-12 heures)
**Objectif** : Débloquer le cockpit utilisateur en s'inspirant des patterns mémoire et corriger les 3 gaps critiques

---

## 📊 Contexte & État Actuel

### ✅ Ce Qui Fonctionne (Backend 85%)

**Backend Infrastructure Solide** :
- ✅ Endpoints API opérationnels ([router.py](src/backend/features/dashboard/router.py))
  - `GET /api/dashboard/costs/summary` - Résumé coûts + monitoring
  - `GET /api/dashboard/timeline/activity?period=7d|30d|90d|1y`
  - `GET /api/dashboard/timeline/costs?period=...`
  - `GET /api/dashboard/timeline/tokens?period=...`
  - `GET /api/dashboard/distribution/{metric}?period=...`

- ✅ Services Backend robustes
  - [service.py](src/backend/features/dashboard/service.py) v11.1 - DTO tolérant
  - [timeline_service.py](src/backend/features/dashboard/timeline_service.py) - Agrégations SQL optimisées
  - [cost_tracker.py](src/backend/core/cost_tracker.py) v13.1 - Enregistrement async

- ✅ Tracking coûts fonctionnel
  - [pricing.py](src/backend/features/chat/pricing.py) - Tarifs à jour
  - OpenAI coûts : ✅ OK
  - Anthropic coûts : ✅ OK
  - Gemini coûts : ❌ **BROKEN** (toujours 0)

- ✅ Frontend Admin existe ([admin-dashboard.js](src/frontend/features/admin/admin-dashboard.js))
  - ⚠️ Accessible **ADMIN ONLY**, pas pour users normaux

### ❌ 3 Gaps Critiques à Résoudre

| Gap | Description | Impact | Priorité |
|-----|-------------|--------|----------|
| **#1** | Dashboard Utilisateur ABSENT | Users ne voient pas leurs métriques | 🔴 P0 |
| **#2** | Coûts Gemini = 0 | Sous-estimation 70-80% (Gemini = modèle par défaut) | 🔴 P0 |
| **#3** | Métriques Prometheus Coûts ABSENTES | Pas de monitoring temps réel | 🟠 P1 |

---

## 🎯 Plan d'Action - Sprint 0 Cockpit

### **Inspiration : Patterns Mémoire LTM (Phase P0/P1)**

**Méthodologie appliquée pour la mémoire** (à réutiliser) :
1. ✅ **Analyse gaps** ([MEMORY_LTM_GAPS_ANALYSIS.md](docs/architecture/MEMORY_LTM_GAPS_ANALYSIS.md))
2. ✅ **Tests complets** (20/20 préférences, 10/10 archivage)
3. ✅ **Métriques Prometheus** (4 métriques extraction préférences)
4. ✅ **Documentation détaillée** ([P0_GAPS_RESOLUTION_STATUS.md](docs/validation/P0_GAPS_RESOLUTION_STATUS.md))

**À appliquer pour le cockpit** :
- ✅ Tests E2E complets AVANT déploiement
- ✅ Métriques Prometheus pour monitoring
- ✅ Fallbacks gracieux (si ChromaDB down → fallback 0)
- ✅ Logs détaillés pour debug production
- ✅ Documentation validation finale

---

## 🔴 Action #1 : Frontend Dashboard Utilisateur (4-6h)

### Objectif
Créer une UI dashboard accessible aux users normaux (contrairement au dashboard admin).

### Inspiration : [memory-center.js](src/frontend/features/memory/memory-center.js)
**Pattern réutilisé** :
```javascript
// Classe singleton avec init/render/destroy
export class DashboardUI {
  constructor() {
    this.container = null;
    this.refreshInterval = null;
  }

  async init(containerId) {
    this.container = document.getElementById(containerId);
    this.render();
    await this.loadData();
    this.startAutoRefresh();
    this.attachEventListeners();
  }

  // ... méthodes render, loadData, etc.
}

export const dashboardUI = new DashboardUI();
```

### Fichiers à Créer

#### 📄 `src/frontend/features/dashboard/dashboard-ui.js` (~350 lignes)

**Structure complète** (inspirée de [cockpit-metrics.js](src/frontend/features/cockpit/cockpit-metrics.js)) :

```javascript
/**
 * Dashboard UI - Cockpit de pilotage utilisateur
 * V1.0 - Visualisation coûts et métriques (non-admin)
 *
 * Inspiration : memory-center.js, cockpit-metrics.js
 */
import { EventBus } from '../../core/event-bus.js';

export class DashboardUI {
  constructor() {
    this.container = null;
    this.currentSessionId = null;
    this.refreshInterval = null;
    this.autoRefreshEnabled = true;
  }

  /**
   * Initialisation composant
   * @param {string} containerId - ID du conteneur DOM
   */
  async init(containerId) {
    this.container = document.getElementById(containerId);
    if (!this.container) {
      console.error('[DashboardUI] Container not found:', containerId);
      return;
    }

    this.render();
    await this.loadData();
    this.startAutoRefresh();
    this.attachEventListeners();

    console.info('[DashboardUI] Initialized successfully');
  }

  /**
   * Génération HTML du dashboard
   */
  render() {
    this.container.innerHTML = `
      <div class="dashboard-cockpit">
        <!-- Header -->
        <div class="dashboard-header">
          <h1>📊 Cockpit de Pilotage</h1>
          <div class="dashboard-actions">
            <button class="btn-refresh-dashboard" aria-label="Actualiser les données">
              🔄 Actualiser
            </button>
          </div>
        </div>

        <!-- Costs Cards Grid -->
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
            <div class="cost-label">Total Cumulé</div>
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
            <span class="stat-label">Documents Mémoire</span>
          </div>

          <div class="monitoring-stat">
            <span class="stat-icon">🪙</span>
            <span class="stat-value" data-stat="tokens">0</span>
            <span class="stat-label">Tokens</span>
          </div>
        </div>

        <!-- Timeline Charts (placeholders pour Chart.js optionnel) -->
        <div class="dashboard-charts">
          <div class="chart-container">
            <h3>📈 Évolution des Coûts (7 derniers jours)</h3>
            <canvas id="costs-timeline-chart"></canvas>
            <div class="chart-placeholder">Graphique disponible prochainement</div>
          </div>

          <div class="chart-container">
            <h3>📊 Activité (Messages & Threads)</h3>
            <canvas id="activity-timeline-chart"></canvas>
            <div class="chart-placeholder">Graphique disponible prochainement</div>
          </div>
        </div>
      </div>
    `;
  }

  /**
   * Chargement données API
   * Pattern : Similaire à memory-center.js fetchMemoryStats()
   */
  async loadData() {
    try {
      const sessionId = this.getCurrentSessionId();
      const headers = {
        'Authorization': `Bearer ${this.getAuthToken()}`,
        'Content-Type': 'application/json'
      };

      // Ajout X-Session-Id header si session active
      if (sessionId) {
        headers['X-Session-Id'] = sessionId;
      }

      // Fetch summary (coûts + monitoring + métriques)
      const summaryResponse = await fetch('/api/dashboard/costs/summary', { headers });

      if (!summaryResponse.ok) {
        throw new Error(`API error: ${summaryResponse.status}`);
      }

      const data = await summaryResponse.json();

      // Render sections
      this.renderCosts(data.costs, data.thresholds);
      this.renderMonitoring(data.monitoring, data.messages, data.tokens);

      // Optionnel : Charger timelines
      await this.loadTimelines(headers);

      console.info('[DashboardUI] Data loaded successfully', data);

    } catch (error) {
      console.error('[DashboardUI] Error loading data:', error);
      this.showError('Impossible de charger les données du cockpit');
    }
  }

  /**
   * Affichage coûts avec seuils budgétaires
   * @param {Object} costs - {total_cost, today_cost, current_week_cost, current_month_cost}
   * @param {Object} thresholds - {daily_threshold, weekly_threshold, monthly_threshold}
   */
  renderCosts(costs, thresholds) {
    // Today
    const todayEl = this.container.querySelector('[data-cost="today"]');
    if (todayEl) {
      todayEl.textContent = `$${(costs.today_cost || 0).toFixed(2)}`;
    }
    this.renderThreshold('daily', costs.today_cost || 0, thresholds.daily_threshold || 1.0);

    // Week
    const weekEl = this.container.querySelector('[data-cost="week"]');
    if (weekEl) {
      weekEl.textContent = `$${(costs.current_week_cost || 0).toFixed(2)}`;
    }
    this.renderThreshold('weekly', costs.current_week_cost || 0, thresholds.weekly_threshold || 5.0);

    // Month
    const monthEl = this.container.querySelector('[data-cost="month"]');
    if (monthEl) {
      monthEl.textContent = `$${(costs.current_month_cost || 0).toFixed(2)}`;
    }
    this.renderThreshold('monthly', costs.current_month_cost || 0, thresholds.monthly_threshold || 15.0);

    // Total
    const totalEl = this.container.querySelector('[data-cost="total"]');
    if (totalEl) {
      totalEl.textContent = `$${(costs.total_cost || 0).toFixed(2)}`;
    }
  }

  /**
   * Affichage badge seuil budgétaire
   * @param {string} period - 'daily' | 'weekly' | 'monthly'
   * @param {number} current - Coût actuel
   * @param {number} threshold - Seuil configuré
   */
  renderThreshold(period, current, threshold) {
    const el = this.container.querySelector(`[data-threshold="${period}"]`);
    if (!el) return;

    const percent = threshold > 0 ? (current / threshold) * 100 : 0;

    // Classes CSS : threshold-ok (<80%), threshold-warning (80-100%), threshold-exceeded (>100%)
    let className = 'threshold-ok';
    let emoji = '✅';
    if (percent > 100) {
      className = 'threshold-exceeded';
      emoji = '🔴';
    } else if (percent > 80) {
      className = 'threshold-warning';
      emoji = '⚠️';
    }

    el.className = `cost-threshold ${className}`;
    el.textContent = `${emoji} ${percent.toFixed(0)}% de $${threshold.toFixed(2)}`;
  }

  /**
   * Affichage stats monitoring
   * @param {Object} monitoring - {total_documents, total_sessions}
   * @param {Object} messages - {total, today, week, month}
   * @param {Object} tokens - {total, input, output, avgPerMessage}
   */
  renderMonitoring(monitoring, messages, tokens) {
    // Messages
    const messagesEl = this.container.querySelector('[data-stat="messages"]');
    if (messagesEl) {
      messagesEl.textContent = this.formatNumber(messages?.total || 0);
    }

    // Sessions
    const sessionsEl = this.container.querySelector('[data-stat="sessions"]');
    if (sessionsEl) {
      sessionsEl.textContent = this.formatNumber(monitoring?.total_sessions || 0);
    }

    // Documents
    const docsEl = this.container.querySelector('[data-stat="documents"]');
    if (docsEl) {
      docsEl.textContent = this.formatNumber(monitoring?.total_documents || 0);
    }

    // Tokens
    const tokensEl = this.container.querySelector('[data-stat="tokens"]');
    if (tokensEl) {
      tokensEl.textContent = this.formatNumber(tokens?.total || 0);
    }
  }

  /**
   * Chargement timelines (optionnel)
   * @param {Object} headers - Headers HTTP
   */
  async loadTimelines(headers) {
    try {
      const [costsData, activityData] = await Promise.all([
        fetch('/api/dashboard/timeline/costs?period=7d', { headers }).then(r => r.json()),
        fetch('/api/dashboard/timeline/activity?period=7d', { headers }).then(r => r.json())
      ]);

      // Placeholders (TODO: implémenter Chart.js)
      console.log('[DashboardUI] Costs timeline:', costsData);
      console.log('[DashboardUI] Activity timeline:', activityData);

      // Si Chart.js disponible, appeler renderCostsChart() et renderActivityChart()

    } catch (error) {
      console.warn('[DashboardUI] Error loading timelines:', error);
      // Non-bloquant : continuer même si timelines échouent
    }
  }

  /**
   * Event listeners
   */
  attachEventListeners() {
    // Bouton refresh
    const refreshBtn = this.container.querySelector('.btn-refresh-dashboard');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', () => this.refresh());
    }

    // EventBus : session changed → reload data
    EventBus.on('session:changed', () => {
      console.info('[DashboardUI] Session changed, reloading data...');
      this.currentSessionId = null; // Force re-fetch session ID
      this.loadData();
    });

    // EventBus : user logout → destroy
    EventBus.on('user:logout', () => {
      this.destroy();
    });
  }

  /**
   * Refresh manuel
   */
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

  /**
   * Auto-refresh toutes les 2 minutes
   */
  startAutoRefresh() {
    if (this.refreshInterval) {
      clearInterval(this.refreshInterval);
    }

    this.refreshInterval = setInterval(() => {
      if (this.autoRefreshEnabled && document.visibilityState === 'visible') {
        console.info('[DashboardUI] Auto-refresh triggered');
        this.loadData();
      }
    }, 2 * 60 * 1000); // 2 minutes
  }

  /**
   * Stop auto-refresh
   */
  stopAutoRefresh() {
    if (this.refreshInterval) {
      clearInterval(this.refreshInterval);
      this.refreshInterval = null;
    }
  }

  /**
   * Helpers
   */
  getCurrentSessionId() {
    try {
      const state = JSON.parse(localStorage.getItem('emergenceState-V14') || '{}');
      return state.session?.id || null;
    } catch (e) {
      console.warn('[DashboardUI] Error reading session ID:', e);
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
    // TODO: Intégrer avec système de notifications
    // EventBus.emit('notification:error', { message });
  }

  /**
   * Cleanup
   */
  destroy() {
    this.stopAutoRefresh();
    if (this.container) {
      this.container.innerHTML = '';
    }
    console.info('[DashboardUI] Destroyed');
  }
}

// Export singleton
export const dashboardUI = new DashboardUI();
```

#### 📄 `src/frontend/features/dashboard/dashboard-ui.css` (~200 lignes)

**Styles inspirés de [cockpit-metrics.css](src/frontend/features/cockpit/cockpit-metrics.css)** :

```css
/* Dashboard Cockpit - User UI */
.dashboard-cockpit {
  padding: 2rem;
  max-width: 1400px;
  margin: 0 auto;
  animation: fadeIn 0.3s ease-out;
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
  color: var(--text-primary, #1a1a1a);
}

.dashboard-actions {
  display: flex;
  gap: 1rem;
}

.btn-refresh-dashboard {
  padding: 0.5rem 1rem;
  background: var(--color-primary, #3b82f6);
  color: white;
  border: none;
  border-radius: 0.5rem;
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 500;
  transition: all 0.2s;
}

.btn-refresh-dashboard:hover {
  background: var(--color-primary-dark, #2563eb);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
}

.btn-refresh-dashboard:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

/* Costs Grid */
.dashboard-costs-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.cost-card {
  background: var(--color-bg-secondary, #f8f9fa);
  border: 1px solid var(--color-border, #e5e7eb);
  border-radius: 0.75rem;
  padding: 1.5rem;
  text-align: center;
  transition: all 0.2s;
}

.cost-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
}

.cost-card.highlight {
  background: linear-gradient(135deg, var(--color-primary, #3b82f6) 0%, var(--color-primary-dark, #2563eb) 100%);
  color: white;
  border: none;
}

.cost-label {
  font-size: 0.875rem;
  color: var(--color-text-secondary, #6b7280);
  margin-bottom: 0.5rem;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.cost-card.highlight .cost-label {
  color: rgba(255, 255, 255, 0.9);
}

.cost-value {
  font-size: 2rem;
  font-weight: 700;
  margin-bottom: 0.5rem;
  color: var(--text-primary, #1a1a1a);
}

.cost-card.highlight .cost-value {
  color: white;
}

.cost-threshold {
  font-size: 0.75rem;
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
  display: inline-block;
  font-weight: 600;
}

.cost-threshold.threshold-ok {
  background: var(--color-success-bg, #d1fae5);
  color: var(--color-success, #10b981);
}

.cost-threshold.threshold-warning {
  background: var(--color-warning-bg, #fef3c7);
  color: var(--color-warning, #f59e0b);
}

.cost-threshold.threshold-exceeded {
  background: var(--color-error-bg, #fee2e2);
  color: var(--color-error, #ef4444);
}

/* Monitoring Stats */
.dashboard-monitoring {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 1rem;
  margin-bottom: 2rem;
}

.monitoring-stat {
  background: var(--color-bg-secondary, #f8f9fa);
  border: 1px solid var(--color-border, #e5e7eb);
  border-radius: 0.5rem;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  transition: all 0.2s;
}

.monitoring-stat:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.stat-icon {
  font-size: 2rem;
  margin-bottom: 0.5rem;
}

.stat-value {
  font-size: 1.5rem;
  font-weight: 600;
  margin-bottom: 0.25rem;
  color: var(--text-primary, #1a1a1a);
}

.stat-label {
  font-size: 0.875rem;
  color: var(--color-text-secondary, #6b7280);
  font-weight: 500;
}

/* Charts */
.dashboard-charts {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 2rem;
  margin-top: 2rem;
}

.chart-container {
  background: var(--color-bg-secondary, #f8f9fa);
  border: 1px solid var(--color-border, #e5e7eb);
  border-radius: 0.75rem;
  padding: 1.5rem;
}

.chart-container h3 {
  font-size: 1.125rem;
  font-weight: 600;
  margin-bottom: 1rem;
  color: var(--text-primary, #1a1a1a);
}

.chart-container canvas {
  width: 100%;
  height: 300px;
}

.chart-placeholder {
  height: 300px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-secondary, #6b7280);
  font-style: italic;
}

/* Animations */
@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Dark mode support */
@media (prefers-color-scheme: dark) {
  .dashboard-cockpit {
    --color-bg-secondary: #1a1a1a;
    --color-border: #333;
    --color-text-secondary: #888;
    --text-primary: #f9fafb;
    --color-primary: #3b82f6;
    --color-primary-dark: #2563eb;
    --color-success: #10b981;
    --color-success-bg: rgba(16, 185, 129, 0.1);
    --color-warning: #f59e0b;
    --color-warning-bg: rgba(245, 158, 11, 0.1);
    --color-error: #ef4444;
    --color-error-bg: rgba(239, 68, 68, 0.1);
  }

  .cost-card,
  .monitoring-stat,
  .chart-container {
    background: #1a1a1a;
    border-color: #333;
  }
}

/* Responsive */
@media (max-width: 768px) {
  .dashboard-cockpit {
    padding: 1rem;
  }

  .dashboard-header {
    flex-direction: column;
    gap: 1rem;
    align-items: flex-start;
  }

  .dashboard-costs-grid {
    grid-template-columns: 1fr;
  }

  .dashboard-charts {
    grid-template-columns: 1fr;
  }

  .chart-container canvas,
  .chart-placeholder {
    height: 200px;
  }
}
```

#### 📄 `src/frontend/features/dashboard/README.md`

```markdown
# Dashboard UI - Cockpit de Pilotage Utilisateur

Composant frontend pour la visualisation des coûts et métriques utilisateur (non-admin).

## Usage

\`\`\`javascript
import { dashboardUI } from './features/dashboard/dashboard-ui.js';

// Initialiser dans container
await dashboardUI.init('app-container');

// Cleanup (lors de navigation)
dashboardUI.destroy();
\`\`\`

## API Endpoints Utilisés

- `GET /api/dashboard/costs/summary` - Résumé coûts + monitoring + métriques
- `GET /api/dashboard/timeline/costs?period=7d` - Timeline coûts (optionnel)
- `GET /api/dashboard/timeline/activity?period=7d` - Timeline activité (optionnel)

## Features Implémentées

- ✅ Affichage coûts par période (today/week/month/total)
- ✅ Seuils budgétaires visuels (OK ✅ / Warning ⚠️ / Exceeded 🔴)
- ✅ Stats monitoring (messages/sessions/documents/tokens)
- ✅ Auto-refresh toutes les 2 minutes
- ✅ Refresh manuel via bouton
- ✅ Responsive design (mobile + desktop)
- ✅ Dark mode support
- ⏳ Charts timelines (placeholders, Chart.js optionnel)

## Dependencies

- **Core** : EventBus, localStorage (emergenceState-V14)
- **Optionnel** : Chart.js pour graphiques timelines

## Architecture

Inspirée de :
- [memory-center.js](../memory/memory-center.js) - Pattern singleton + lifecycle
- [cockpit-metrics.js](../cockpit/cockpit-metrics.js) - Métriques display

## Tests

\`\`\`bash
# Browser console
await dashboardUI.init('app-container');
dashboardUI.loadData(); // Force refresh
\`\`\`

## Maintenance

- **Fallbacks** : Si API erreur, affiche 0 (graceful degradation)
- **Logs** : Préfixe `[DashboardUI]` pour debug
- **Cleanup** : Appeler `destroy()` lors de navigation
\`\`\`

### Intégrations

#### ✅ `src/frontend/main.js` (Modifier)

**Ajouter routing dashboard** :

```javascript
// Après imports existants
import { dashboardUI } from './features/dashboard/dashboard-ui.js';

// Dans router (exemple SPA)
const routes = {
  '/': () => loadHome(),
  '/chat': () => loadChat(),
  '/memory': () => loadMemory(),
  '/dashboard': async () => {
    await dashboardUI.init('app-container');
  },
  // ... autres routes
};

// EventBus routing (si utilisé)
EventBus.on('route:dashboard', async () => {
  await dashboardUI.init('app-container');
});

// Cleanup lors de changement de route
EventBus.on('route:change', (newRoute) => {
  if (newRoute !== '/dashboard') {
    dashboardUI.destroy();
  }
});
```

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

### Validation Action #1

- [ ] ✅ 3 fichiers créés (`dashboard-ui.js`, `dashboard-ui.css`, `README.md`)
- [ ] ✅ Route `/dashboard` fonctionnelle
- [ ] ✅ Lien menu "Cockpit" visible et cliquable
- [ ] ✅ Fetch API `GET /api/dashboard/costs/summary` OK (200)
- [ ] ✅ Affichage 4 cards coûts avec valeurs réelles (ou 0 si BDD vide)
- [ ] ✅ Badges seuils colorés (ok/warning/exceeded)
- [ ] ✅ Stats monitoring affichées (messages/sessions/documents/tokens)
- [ ] ✅ Refresh auto après 2 min
- [ ] ✅ Pas d'erreur console
- [ ] ✅ Responsive (mobile + desktop)
- [ ] 🟡 Charts (optionnel Chart.js)

---

## 🐛 Action #2 : Fix Coûts Gemini (1-2h)

### Problème

**Gemini coûts toujours 0** car l'API Google ne retourne pas `usage` dans la réponse streaming.

**Cause racine** ([llm_stream.py:178-180](src/backend/features/chat/llm_stream.py#L178-L180)) :
```python
cost_info_container.setdefault("input_tokens", 0)   # ← Hardcodé à 0
cost_info_container.setdefault("output_tokens", 0)  # ← Hardcodé à 0
cost_info_container.setdefault("total_cost", 0.0)   # ← Hardcodé à 0
```

**Impact** :
- ❌ 70-80% du trafic (Gemini = modèle par défaut)
- ❌ Sous-estimation massive des coûts réels
- ❌ Alertes budgétaires inefficaces

### Solution

**Utiliser `model.count_tokens()`** pour compter manuellement input/output.

### Fichier à Modifier

#### ✅ `src/backend/features/chat/llm_stream.py`

**Méthode `_get_gemini_stream()` (lignes 142-184)** :

```python
async def _get_gemini_stream(
    self, model, system_prompt, history, cost_info_container
):
    """
    Stream Gemini avec calcul coûts via count_tokens().

    Fix : Google Generative AI ne retourne pas usage dans streaming.
    Solution : Appeler model.count_tokens() avant (input) et après (output).
    """
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

        # ===================================================================
        # COUNT TOKENS INPUT (avant génération)
        # ===================================================================
        try:
            # Construire prompt complet pour count_tokens
            prompt_parts = [system_prompt] if system_prompt else []
            for msg in history:
                content = msg.get("content", "")
                if content:
                    prompt_parts.append(content)

            # Compter tokens input
            input_tokens = _model.count_tokens(prompt_parts).total_tokens
            logger.debug(f"[Gemini] Input tokens counted: {input_tokens}")

        except Exception as e:
            logger.warning(f"[Gemini] Failed to count input tokens: {e}")
            input_tokens = 0

        # ===================================================================
        # GÉNÉRATION STREAMING
        # ===================================================================
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
            except Exception as chunk_error:
                logger.warning(f"[Gemini] Chunk error: {chunk_error}")
                pass

        # ===================================================================
        # COUNT TOKENS OUTPUT (après génération)
        # ===================================================================
        try:
            output_tokens = _model.count_tokens(full_response_text).total_tokens
            logger.debug(f"[Gemini] Output tokens counted: {output_tokens}")
        except Exception as e:
            logger.warning(f"[Gemini] Failed to count output tokens: {e}")
            output_tokens = 0

        # ===================================================================
        # CALCUL COÛT
        # ===================================================================
        pricing = MODEL_PRICING.get(model, {"input": 0, "output": 0})

        # Calcul coût total : (input_tokens * prix_input) + (output_tokens * prix_output)
        total_cost = (input_tokens * pricing["input"]) + (output_tokens * pricing["output"])

        # Mise à jour container
        cost_info_container.update({
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_cost": total_cost,
        })

        logger.info(
            f"[Gemini] Cost calculated: ${total_cost:.6f} "
            f"({input_tokens} input + {output_tokens} output tokens)"
        )

    except Exception as e:
        logger.error(f"[Gemini] Stream error: {e}", exc_info=True)
        cost_info_container["__error__"] = "provider_error"

        # Fallback à 0 si erreur globale
        cost_info_container.setdefault("input_tokens", 0)
        cost_info_container.setdefault("output_tokens", 0)
        cost_info_container.setdefault("total_cost", 0.0)
```

### Tests Action #2

#### Test #1 : Conversation Gemini

```bash
# 1. Lancer conversation avec Gemini
curl -X POST http://localhost:8000/api/chat/send \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Session-Id: $SESSION_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello, tell me about Python in 2 sentences",
    "agent": "assistant",
    "model": "gemini-2.0-flash-exp"
  }'

# 2. Vérifier logs backend
grep "Gemini.*Cost calculated" logs/backend.log

# Attendu :
# [Gemini] Cost calculated: $0.000123 (150 input + 50 output tokens)
```

#### Test #2 : Vérification BDD

```bash
sqlite3 instance/emergence.db <<EOF
SELECT
  timestamp,
  model,
  input_tokens,
  output_tokens,
  total_cost
FROM costs
WHERE model LIKE '%gemini%'
ORDER BY timestamp DESC
LIMIT 5;
EOF

# Attendu : Valeurs NON-ZERO dans input_tokens, output_tokens, total_cost
```

#### Test #3 : Erreur count_tokens (Robustesse)

**Simuler erreur API** (mock temporaire) :
```python
# Dans llm_stream.py temporairement, forcer erreur :
input_tokens = _model.count_tokens([]).total_tokens  # ← Liste vide, peut fail
```

**Vérifier** :
- ✅ Logs warning : `Failed to count input tokens`
- ✅ Fallback à 0 sans crash
- ✅ Streaming continue normalement

### Validation Action #2

- [ ] ✅ Code modifié dans `llm_stream.py:142-184`
- [ ] ✅ Test conversation Gemini : coût > 0 dans logs
- [ ] ✅ Logs backend affichent `[Gemini] Cost calculated: $X.XXXXXX`
- [ ] ✅ BDD : `input_tokens`, `output_tokens`, `total_cost` NON-ZERO
- [ ] ✅ Test erreur count_tokens : fallback 0 sans crash
- [ ] ✅ Conversations OpenAI/Anthropic toujours OK (non-régression)

---

## 📊 Action #3 : Métriques Prometheus Coûts (2-3h)

### Problème

Phase 3 Prometheus implémentée **uniquement pour MemoryAnalyzer** :
- ✅ `memory_analysis_success_total`
- ✅ `memory_cache_hits_total`
- ✅ `memory_analysis_duration_seconds`

**Manque** : Métriques coûts/tokens/billing pour monitoring LLM.

### Objectif

Ajouter 6 métriques Prometheus pour tracking coûts LLM en temps réel.

### Inspiration

**Pattern MemoryAnalyzer** ([analyzer.py:18-32](src/backend/features/memory/analyzer.py#L18-L32)) :

```python
from prometheus_client import Counter, Histogram

PREFERENCE_EXTRACTED = Counter(
    "memory_preferences_extracted_total",
    "Total preferences extracted by type",
    ["type"]
)

PREFERENCE_CONFIDENCE = Histogram(
    "memory_preferences_confidence",
    "Confidence scores of extracted preferences",
    buckets=[0.0, 0.3, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)
```

### Fichier à Modifier

#### ✅ `src/backend/core/cost_tracker.py`

**1. Imports Prometheus** (ligne ~10)

```python
from prometheus_client import Counter, Histogram, Gauge
```

**2. Définition Métriques** (après classe CostTracker, ligne ~110)

```python
# =============================================================================
# PROMETHEUS METRICS - LLM COSTS
# =============================================================================

# Coûts par agent/model/provider
COST_BY_AGENT = Counter(
    "llm_cost_dollars_total",
    "Total cost in dollars by agent, model and provider",
    ["agent", "model", "provider"]
)

# Tokens consommés (input + output séparés)
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

**3. Helper `_detect_provider_from_model()`** (ligne ~115)

```python
def _detect_provider_from_model(self, model: str) -> str:
    """
    Détecte le provider depuis le nom du modèle.

    Args:
        model: Nom du modèle (ex: "gpt-4o-mini", "gemini-2.0-flash", "claude-3-5-haiku")

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

**4. Instrumentation `record_cost()`** (ligne ~43-78, **ajouter après enregistrement BDD**)

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

            # =====================================================================
            # 2. MÉTRIQUES PROMETHEUS (NOUVEAU)
            # =====================================================================
            try:
                provider = self._detect_provider_from_model(model)

                # Coût par agent/model/provider
                COST_BY_AGENT.labels(
                    agent=agent,
                    model=model,
                    provider=provider
                ).inc(total_cost)

                # Tokens consommés (input + output séparés)
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
                # Ne pas fail si métriques KO (graceful degradation)

        except Exception as e:
            logger.error(
                f"Erreur lors de l'enregistrement du coût pour {model}: {e}",
                exc_info=True,
            )
```

**5. Méthode `update_periodic_gauges()`** (ligne ~120)

```python
async def update_periodic_gauges(self) -> None:
    """
    Met à jour les gauges Prometheus pour coûts daily/weekly/monthly.
    À appeler périodiquement (ex: toutes les 5 minutes via background task).
    """
    try:
        summary = await self.get_spending_summary()

        # Mise à jour gauges
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
        logger.error(
            f"[Prometheus] Failed to update periodic gauges: {e}",
            exc_info=True
        )
```

**6. Background Task Scheduler** (fichier `src/backend/main.py`)

**Ajouter** :

```python
import asyncio
from backend.core.cost_tracker import CostTracker

async def update_cost_gauges_periodically():
    """Background task pour mettre à jour les gauges Prometheus coûts."""
    logger.info("[Startup] Background task: update_cost_gauges_periodically started")

    while True:
        try:
            # Récupérer CostTracker via container DI
            cost_tracker = container.cost_tracker()
            await cost_tracker.update_periodic_gauges()
        except Exception as e:
            logger.error(f"[Background] Error updating cost gauges: {e}", exc_info=True)

        # Toutes les 5 minutes
        await asyncio.sleep(5 * 60)

@app.on_event("startup")
async def startup_background_tasks():
    """Lancer background tasks au démarrage."""
    # Lancer task gauges Prometheus
    asyncio.create_task(update_cost_gauges_periodically())

    logger.info("[Startup] Background tasks launched")
```

### Tests Action #3

#### Test #1 : Métriques Exposées

```bash
# 1. Déclencher 3-5 requêtes LLM (mix providers)
curl -X POST http://localhost:8000/api/chat/send \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello AI", "model": "gpt-4o-mini"}'

curl -X POST http://localhost:8000/api/chat/send \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello Gemini", "model": "gemini-2.0-flash-exp"}'

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

#### Test #2 : Requêtes PromQL

**Si Prometheus configuré** :

```promql
# Taux de coût par seconde (tous providers)
sum(rate(llm_cost_dollars_total[5m]))

# Coût par provider (top 3)
topk(3, sum by (provider) (rate(llm_cost_dollars_total[5m])))

# Coût moyen par requête (P50)
histogram_quantile(0.5, rate(llm_cost_per_request_dollars_bucket[5m]))

# Alerte dépassement budget journalier
llm_daily_cost_dollars > 3.0

# Tokens/sec par provider
sum by (provider) (rate(llm_tokens_total[1m]))
```

#### Test #3 : Background Task Gauges

```bash
# Attendre 5 minutes OU déclencher manuellement :
# (Code temporaire dans endpoint debug)
await container.cost_tracker().update_periodic_gauges()

# Vérifier logs
grep "Prometheus.*Periodic gauges updated" logs/backend.log

# Vérifier métriques
curl http://localhost:8000/api/metrics | grep llm_daily_cost_dollars
# Attendu : valeur non-zero
```

### Validation Action #3

- [ ] ✅ 6 métriques Prometheus définies (3 Counter + 1 Histogram + 3 Gauge)
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
1. Login user
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

### Fichiers à Mettre à Jour

#### ✅ `docs/cockpit/COCKPIT_GAPS_AND_FIXES.md`

**Changer statut** :
- `📋 ANALYSE COMPLÈTE - Prêt pour implémentation` → `✅ IMPLÉMENTÉ - Sprint 0 Terminé`

**Ajouter section "Résultats Sprint 0"** :
```markdown
## ✅ Résultats Sprint 0 - Implémentation Terminée

**Date** : 2025-10-XX
**Durée** : X heures

### Implémentations

#### 1. Frontend Dashboard UI
- ✅ Fichiers créés : `dashboard-ui.js`, `dashboard-ui.css`, `README.md`
- ✅ Route `/dashboard` accessible
- ✅ Lien menu "Cockpit" ajouté
- ✅ 4 cards coûts (today/week/month/total)
- ✅ Seuils budgétaires visuels (ok/warning/exceeded)
- ✅ Stats monitoring (messages/sessions/documents/tokens)
- ✅ Auto-refresh 2 min
- ✅ Responsive + dark mode

#### 2. Fix Coûts Gemini
- ✅ Méthode `_get_gemini_stream()` modifiée
- ✅ Utilisation `model.count_tokens()` pour input/output
- ✅ Coûts Gemini maintenant trackés correctement
- ✅ Logs : `[Gemini] Cost calculated: $X.XXXXXX`
- ✅ BDD : valeurs non-zero confirmées

#### 3. Métriques Prometheus Coûts
- ✅ 6 métriques définies (Counter + Histogram + Gauge)
- ✅ Instrumentation `record_cost()`
- ✅ Background task update gauges (5 min)
- ✅ Endpoint `/api/metrics` exposé
- ✅ Requêtes PromQL validées

### Tests Validés
- ✅ E2E dashboard UI (flow complet user)
- ✅ Gemini coûts > 0 (vérifiés BDD + logs)
- ✅ Métriques Prometheus exposées
- ✅ Seuils alertes visuels fonctionnels
- ✅ Aucune régression (admin dashboard OK)

### Métriques Succès
| KPI | Target | Résultat |
|-----|--------|----------|
| Dashboard UI Accessible | Route `/dashboard` OK | ✅ OK |
| Coûts Gemini Trackés | >0 dans BDD | ✅ $0.00XX |
| Métriques Prometheus | 6 métriques `llm_*` | ✅ Exposées |
| Performance Dashboard | Load <2s | ✅ 1.2s |
| Rétrocompatibilité | Admin dashboard OK | ✅ Non cassé |
```

#### ✅ `AGENT_SYNC.md` ou `docs/passation.md`

**Ajouter** :
```markdown
## Sprint 0 Cockpit - Terminé (2025-10-XX)

### Implémentations
1. ✅ Frontend Dashboard UI (`src/frontend/features/dashboard/`)
2. ✅ Fix coûts Gemini (`src/backend/features/chat/llm_stream.py`)
3. ✅ Métriques Prometheus coûts (`src/backend/core/cost_tracker.py`)

### Prochaines Étapes
- Phase P2 Mémoire (optimisations performance)
```

---

## 🎯 Critères de Complétion Sprint 0

### **Sprint 0 Est Terminé Quand** :

- [ ] ✅ Action #1 : Dashboard UI fonctionnel et accessible
- [ ] ✅ Action #2 : Coûts Gemini non-zero dans BDD
- [ ] ✅ Action #3 : Métriques Prometheus exposées et testées
- [ ] ✅ Tests E2E validés (3 scénarios)
- [ ] ✅ Documentation mise à jour (COCKPIT_GAPS_AND_FIXES.md + passation.md)
- [ ] ✅ Aucune régression (tests existants passent)
- [ ] ✅ Review code + commit
- [ ] 🟡 (Optionnel) Deploy production + smoke test

---

## 📊 Timeline Sprint 0

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

## 📚 Références

### Documentation
- [COCKPIT_GAPS_AND_FIXES.md](docs/cockpit/COCKPIT_GAPS_AND_FIXES.md) - Analyse gaps initiale
- [PROMPT_DEBUG_COCKPIT_METRICS.md](PROMPT_DEBUG_COCKPIT_METRICS.md) - Debug métriques Phase 3
- [PROMPT_COCKPIT_NEXT_FEATURES.md](PROMPT_COCKPIT_NEXT_FEATURES.md) - Features futures (charts, filtres, export)
- [P0_GAPS_RESOLUTION_STATUS.md](docs/validation/P0_GAPS_RESOLUTION_STATUS.md) - Pattern mémoire LTM (inspiration)

### Code Source
- **Backend** :
  - [dashboard/router.py](src/backend/features/dashboard/router.py) - Endpoints API
  - [dashboard/service.py](src/backend/features/dashboard/service.py) - DTO robuste
  - [cost_tracker.py](src/backend/core/cost_tracker.py) - Tracking coûts
  - [llm_stream.py](src/backend/features/chat/llm_stream.py) - Streaming + coûts

- **Frontend** :
  - [memory-center.js](src/frontend/features/memory/memory-center.js) - Pattern singleton
  - [cockpit-metrics.js](src/frontend/features/cockpit/cockpit-metrics.js) - Métriques display
  - [admin-dashboard.js](src/frontend/features/admin/admin-dashboard.js) - Dashboard admin (ref)

---

**Document créé le** : 2025-10-10
**Auteur** : Claude Code
**Statut** : ✅ **PRÊT POUR IMPLÉMENTATION** (après Phase P2 Mémoire)
**Priorité** : P0 - Critique pour utilisabilité

---

## 🚀 Quick Start

**Pour démarrer Sprint 0 Cockpit** :

1. **Vérifier pré-requis** :
   ```bash
   # Backend API opérationnels
   curl http://localhost:8000/api/dashboard/costs/summary
   # Doit retourner 200
   ```

2. **Action #1** : Créer frontend dashboard
   ```bash
   # Créer dossier
   mkdir -p src/frontend/features/dashboard

   # Créer fichiers (copier code depuis prompt)
   # - dashboard-ui.js
   # - dashboard-ui.css
   # - README.md
   ```

3. **Action #2** : Fixer Gemini
   ```bash
   # Modifier src/backend/features/chat/llm_stream.py
   # (voir section Action #2)
   ```

4. **Action #3** : Ajouter Prometheus
   ```bash
   # Modifier src/backend/core/cost_tracker.py
   # Modifier src/backend/main.py
   # (voir section Action #3)
   ```

5. **Tests E2E** :
   ```bash
   # Lancer backend
   cd src/backend && uvicorn main:app --reload

   # Lancer frontend (si dev server séparé)
   npm run dev

   # Ouvrir browser : http://localhost:8000/dashboard
   ```

6. **Validation finale** :
   ```bash
   # Tests pytest
   python -m pytest tests/ -v

   # Vérifier métriques
   curl http://localhost:8000/api/metrics | grep llm_
   ```

**Bonne implémentation ! 🎯**
