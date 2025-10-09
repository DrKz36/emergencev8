# Prompt Debug/Amélioration Cockpit - Prochaines Features

**Date** : 2025-10-09
**Agent** : Claude Code / Développeur Frontend
**Objectif** : Améliorer et enrichir le cockpit avec visualisations, filtres avancés et export

---

## 📊 État Actuel du Cockpit

### ✅ Features Implémentées (Phase 3 - En Production)

**Backend API** :
- ✅ `/api/dashboard/costs/summary` - Métriques enrichies
  - Messages : {total, today, week, month}
  - Tokens : {total, input, output, avgPerMessage}
  - Costs : {total_cost, today_cost, current_week_cost, current_month_cost}
  - Monitoring : {total_documents, total_sessions}

- ✅ Timeline Endpoints (données temporelles)
  - `/api/dashboard/timeline/activity?period=30d` - Messages + threads par jour
  - `/api/dashboard/timeline/costs?period=30d` - Coûts par jour
  - `/api/dashboard/timeline/tokens?period=30d` - Tokens par jour
  - Périodes supportées : 7d, 30d, 90d, 1y

- ✅ Filtrage par Session
  - Header `X-Session-Id` pour filtrer métriques
  - Endpoint dédié `/api/dashboard/costs/summary/session/{session_id}`

**Frontend** :
- ✅ Module cockpit avec 4 cartes métriques
  - Messages (total, today, week, month)
  - Threads (total, active, archived, taux d'activité)
  - Tokens (total, input, output, moyenne/message)
  - Costs (total, today, week, moyenne/message)

- ✅ Boutons refresh et export (UI uniquement, export non fonctionnel)
- ✅ Auto-update toutes les 30s
- ✅ Design responsive avec glassmorphism
- ✅ Animations fluides

**Fichiers Clés** :
- Backend :
  - `src/backend/features/dashboard/router.py` - Endpoints API
  - `src/backend/features/dashboard/service.py` - Business logic
  - `src/backend/features/dashboard/timeline_service.py` - Service timeline
  - `src/backend/core/database/queries.py` - Requêtes SQL optimisées

- Frontend :
  - `src/frontend/features/cockpit/cockpit-metrics.js` - Module métriques
  - `src/frontend/features/cockpit/cockpit-charts.js` - Charts (vide)
  - `src/frontend/features/cockpit/cockpit-insights.js` - Insights (basique)
  - `src/frontend/features/cockpit/cockpit.css` - Styles principaux

**Tests & Validation** :
- ✅ Backend : 45/45 tests pytest passants
- ✅ Qualité : mypy 0 erreur, ruff clean
- ✅ API : 100% cohérence calculée vs BDD
- ✅ Production : Déployé sur `emergence-app-phase3b`

---

## 🎯 Prochaines Améliorations Prioritaires

### 🔴 PRIORITÉ 1 : Graphiques Timeline Interactifs (3-4h)

#### Objectif
Visualiser les données temporelles avec des graphiques interactifs (Chart.js ou D3.js).

#### Features à Implémenter

**1.1 Intégration Chart.js** (1h)
```javascript
// Dans cockpit-charts.js
import Chart from 'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.js';

export class CockpitCharts {
    constructor() {
        this.charts = {
            activity: null,
            costs: null,
            tokens: null
        };
        this.currentPeriod = '30d';
    }

    async init(containerId) {
        this.container = document.getElementById(containerId);
        this.render();
        await this.loadTimelineData();
    }

    render() {
        this.container.innerHTML = `
            <div class="cockpit-charts">
                <div class="charts-header">
                    <h2>📊 Timelines</h2>
                    <div class="period-selector">
                        <button data-period="7d">7 jours</button>
                        <button data-period="30d" class="active">30 jours</button>
                        <button data-period="90d">90 jours</button>
                        <button data-period="1y">1 an</button>
                    </div>
                </div>

                <div class="charts-grid">
                    <div class="chart-card">
                        <h3>Activité (Messages + Threads)</h3>
                        <canvas id="chart-activity"></canvas>
                    </div>

                    <div class="chart-card">
                        <h3>Coûts Journaliers</h3>
                        <canvas id="chart-costs"></canvas>
                    </div>

                    <div class="chart-card">
                        <h3>Tokens Consommés</h3>
                        <canvas id="chart-tokens"></canvas>
                    </div>
                </div>
            </div>
        `;

        this.bindEvents();
    }

    async loadTimelineData() {
        const [activity, costs, tokens] = await Promise.all([
            this.fetchTimeline('activity'),
            this.fetchTimeline('costs'),
            this.fetchTimeline('tokens')
        ]);

        this.renderActivityChart(activity);
        this.renderCostsChart(costs);
        this.renderTokensChart(tokens);
    }

    async fetchTimeline(type) {
        const token = this._getAuthToken();
        const headers = { 'Content-Type': 'application/json' };
        if (token) headers['Authorization'] = `Bearer ${token}`;

        const response = await fetch(
            `/api/dashboard/timeline/${type}?period=${this.currentPeriod}`,
            { headers }
        );
        return response.json();
    }

    renderActivityChart(data) {
        const ctx = document.getElementById('chart-activity').getContext('2d');

        if (this.charts.activity) {
            this.charts.activity.destroy();
        }

        this.charts.activity = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.map(d => d.date),
                datasets: [
                    {
                        label: 'Messages',
                        data: data.map(d => d.messages || 0),
                        borderColor: 'rgb(59, 130, 246)',
                        backgroundColor: 'rgba(59, 130, 246, 0.1)',
                        tension: 0.4
                    },
                    {
                        label: 'Threads',
                        data: data.map(d => d.threads || 0),
                        borderColor: 'rgb(168, 85, 247)',
                        backgroundColor: 'rgba(168, 85, 247, 0.1)',
                        tension: 0.4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: true },
                    tooltip: { mode: 'index', intersect: false }
                },
                scales: {
                    y: { beginAtZero: true, grid: { color: 'rgba(255,255,255,0.05)' } },
                    x: { grid: { color: 'rgba(255,255,255,0.05)' } }
                }
            }
        });
    }

    renderCostsChart(data) {
        const ctx = document.getElementById('chart-costs').getContext('2d');

        if (this.charts.costs) {
            this.charts.costs.destroy();
        }

        this.charts.costs = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.map(d => d.date),
                datasets: [{
                    label: 'Coûts ($)',
                    data: data.map(d => d.cost || 0),
                    backgroundColor: 'rgba(34, 197, 94, 0.7)',
                    borderColor: 'rgb(34, 197, 94)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (context) => `$${context.parsed.y.toFixed(4)}`
                        }
                    }
                },
                scales: {
                    y: { beginAtZero: true, grid: { color: 'rgba(255,255,255,0.05)' } },
                    x: { grid: { display: false } }
                }
            }
        });
    }

    renderTokensChart(data) {
        const ctx = document.getElementById('chart-tokens').getContext('2d');

        if (this.charts.tokens) {
            this.charts.tokens.destroy();
        }

        this.charts.tokens = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.map(d => d.date),
                datasets: [
                    {
                        label: 'Input',
                        data: data.map(d => d.input || 0),
                        borderColor: 'rgb(249, 115, 22)',
                        backgroundColor: 'rgba(249, 115, 22, 0.1)',
                        fill: true,
                        tension: 0.4
                    },
                    {
                        label: 'Output',
                        data: data.map(d => d.output || 0),
                        borderColor: 'rgb(236, 72, 153)',
                        backgroundColor: 'rgba(236, 72, 153, 0.1)',
                        fill: true,
                        tension: 0.4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: true },
                    tooltip: { mode: 'index', intersect: false }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: 'rgba(255,255,255,0.05)' },
                        ticks: { callback: (value) => `${(value/1000).toFixed(0)}k` }
                    },
                    x: { grid: { color: 'rgba(255,255,255,0.05)' } }
                }
            }
        });
    }

    bindEvents() {
        const buttons = this.container.querySelectorAll('.period-selector button');
        buttons.forEach(btn => {
            btn.addEventListener('click', async () => {
                buttons.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this.currentPeriod = btn.dataset.period;
                await this.loadTimelineData();
            });
        });
    }

    _getAuthToken() {
        return localStorage.getItem('emergence.id_token') ||
               sessionStorage.getItem('emergence.id_token');
    }
}
```

**1.2 Styles Chart.js** (30min)
```css
/* Dans cockpit-charts.css - à ajouter */
.cockpit-charts {
    padding: 24px;
}

.charts-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 32px;
}

.charts-header h2 {
    font-size: 24px;
    font-weight: 600;
    color: var(--text-primary);
}

.period-selector {
    display: flex;
    gap: 8px;
    background: var(--bg-secondary);
    padding: 4px;
    border-radius: 8px;
}

.period-selector button {
    padding: 8px 16px;
    border: none;
    background: transparent;
    color: var(--text-muted);
    border-radius: 6px;
    cursor: pointer;
    transition: all 0.2s;
    font-size: 14px;
}

.period-selector button:hover {
    background: rgba(255, 255, 255, 0.05);
    color: var(--text-primary);
}

.period-selector button.active {
    background: var(--accent-blue);
    color: white;
}

.charts-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
    gap: 24px;
}

.chart-card {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: 20px;
    min-height: 300px;
}

.chart-card h3 {
    font-size: 16px;
    font-weight: 500;
    margin-bottom: 16px;
    color: var(--text-primary);
}

.chart-card canvas {
    max-height: 250px;
}

@media (max-width: 768px) {
    .charts-grid {
        grid-template-columns: 1fr;
    }

    .period-selector {
        flex-wrap: wrap;
    }
}
```

**1.3 Intégration dans cockpit.js** (30min)
```javascript
// Dans cockpit.js - ajouter
import { CockpitCharts } from './cockpit-charts.js';

// Dans la méthode init()
async init() {
    // ... existing code ...

    // Initialiser les charts
    this.charts = new CockpitCharts();
    await this.charts.init('charts-container');
}
```

**1.4 Ajout dans HTML** (15min)
```html
<!-- Dans index.html - section cockpit -->
<div id="charts-container" class="cockpit-section"></div>
```

---

### 🟡 PRIORITÉ 2 : Filtres Avancés (2-3h)

#### Objectif
Permettre le filtrage des métriques par agent, session, et plage de dates.

**2.1 UI Filtres** (1h)
```javascript
// Dans cockpit-metrics.js - ajouter renderFilters()
renderFilters() {
    return `
        <div class="metrics-filters">
            <div class="filter-group">
                <label>Agent</label>
                <select id="filter-agent" class="filter-select">
                    <option value="">Tous</option>
                    <option value="anima">Anima</option>
                    <option value="neo">Neo</option>
                    <option value="nexus">Nexus</option>
                </select>
            </div>

            <div class="filter-group">
                <label>Session</label>
                <select id="filter-session" class="filter-select">
                    <option value="">Toutes</option>
                    <!-- Dynamique depuis API -->
                </select>
            </div>

            <div class="filter-group">
                <label>Période</label>
                <input type="date" id="filter-date-start" class="filter-input">
                <span>à</span>
                <input type="date" id="filter-date-end" class="filter-input">
            </div>

            <button id="apply-filters" class="btn-apply-filters">
                Appliquer
            </button>

            <button id="reset-filters" class="btn-reset-filters">
                Réinitialiser
            </button>
        </div>
    `;
}
```

**2.2 Backend - Nouveaux endpoints** (1h)
```python
# Dans dashboard/router.py - ajouter

@router.get("/costs/summary/filtered")
async def get_filtered_summary(
    request: Request,
    agent: Optional[str] = Query(None, description="Filtrer par agent"),
    date_start: Optional[str] = Query(None, description="Date début (YYYY-MM-DD)"),
    date_end: Optional[str] = Query(None, description="Date fin (YYYY-MM-DD)"),
    dashboard_service: DashboardService = Depends(_resolve_get_dashboard_service()),
    user_id: str = Depends(deps.get_user_id),
) -> Dict[str, Any]:
    """Métriques filtrées par agent et dates."""
    return await dashboard_service.get_filtered_data(
        user_id=user_id,
        agent=agent,
        date_start=date_start,
        date_end=date_end
    )
```

**2.3 Sessions List Endpoint** (30min)
```python
# Dans dashboard/router.py - ajouter

@router.get("/sessions/list")
async def get_user_sessions(
    user_id: str = Depends(deps.get_user_id),
    db: DatabaseManager = Depends(deps.get_database_manager),
) -> List[Dict[str, Any]]:
    """Liste des sessions utilisateur pour filtres."""
    query = """
        SELECT id, created_at, updated_at, summary
        FROM threads
        WHERE user_id = ? AND session_id IS NOT NULL
        GROUP BY session_id
        ORDER BY updated_at DESC
        LIMIT 50
    """
    result = await db.fetch_all(query, (user_id,))
    return [dict(row) for row in result]
```

---

### 🟢 PRIORITÉ 3 : Export Données (1-2h)

#### Objectif
Permettre l'export des métriques en CSV, JSON, et PDF.

**3.1 Export CSV** (45min)
```javascript
// Dans cockpit-metrics.js - ajouter
async exportCSV() {
    const data = await this.fetchAllMetrics();

    const csv = [
        ['Métrique', 'Valeur'],
        ['Messages Total', data.messages.total],
        ['Messages Aujourd\'hui', data.messages.today],
        ['Messages Semaine', data.messages.week],
        ['Messages Mois', data.messages.month],
        ['Tokens Total', data.tokens.total],
        ['Tokens Input', data.tokens.input],
        ['Tokens Output', data.tokens.output],
        ['Coût Total', `$${data.costs.total_cost.toFixed(4)}`],
        ['Coût Aujourd\'hui', `$${data.costs.today_cost.toFixed(4)}`],
        ['Coût Semaine', `$${data.costs.current_week_cost.toFixed(4)}`],
    ].map(row => row.join(',')).join('\n');

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `emergence-metrics-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    URL.revokeObjectURL(url);
}
```

**3.2 Export JSON** (15min)
```javascript
async exportJSON() {
    const data = await this.fetchAllMetrics();
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `emergence-metrics-${new Date().toISOString().split('T')[0]}.json`;
    a.click();
    URL.revokeObjectURL(url);
}
```

**3.3 Export PDF (jsPDF)** (1h)
```javascript
// Importer jsPDF
import jsPDF from 'https://cdn.jsdelivr.net/npm/jspdf@2.5.1/dist/jspdf.es.min.js';

async exportPDF() {
    const data = await this.fetchAllMetrics();
    const doc = new jsPDF();

    // Header
    doc.setFontSize(20);
    doc.text('Émergence - Rapport Métriques', 20, 20);

    doc.setFontSize(10);
    doc.text(`Généré le ${new Date().toLocaleDateString('fr-FR')}`, 20, 30);

    // Métriques
    doc.setFontSize(12);
    let y = 45;

    doc.text('Messages', 20, y);
    doc.setFontSize(10);
    doc.text(`Total: ${data.messages.total}`, 30, y + 7);
    doc.text(`Aujourd'hui: ${data.messages.today}`, 30, y + 14);
    doc.text(`Cette semaine: ${data.messages.week}`, 30, y + 21);

    y += 35;
    doc.setFontSize(12);
    doc.text('Tokens', 20, y);
    doc.setFontSize(10);
    doc.text(`Total: ${data.tokens.total.toLocaleString()}`, 30, y + 7);
    doc.text(`Input: ${data.tokens.input.toLocaleString()}`, 30, y + 14);
    doc.text(`Output: ${data.tokens.output.toLocaleString()}`, 30, y + 21);

    y += 35;
    doc.setFontSize(12);
    doc.text('Coûts', 20, y);
    doc.setFontSize(10);
    doc.text(`Total: $${data.costs.total_cost.toFixed(4)}`, 30, y + 7);
    doc.text(`Aujourd'hui: $${data.costs.today_cost.toFixed(4)}`, 30, y + 14);
    doc.text(`Cette semaine: $${data.costs.current_week_cost.toFixed(4)}`, 30, y + 21);

    doc.save(`emergence-metrics-${new Date().toISOString().split('T')[0]}.pdf`);
}
```

**3.4 Menu Export** (15min)
```javascript
// Dans renderExportMenu()
renderExportMenu() {
    return `
        <div class="export-menu">
            <button class="export-btn" data-format="csv">
                📄 Export CSV
            </button>
            <button class="export-btn" data-format="json">
                📋 Export JSON
            </button>
            <button class="export-btn" data-format="pdf">
                📑 Export PDF
            </button>
        </div>
    `;
}

// Event listeners
bindExportEvents() {
    this.container.querySelectorAll('.export-btn').forEach(btn => {
        btn.addEventListener('click', async () => {
            const format = btn.dataset.format;
            switch(format) {
                case 'csv': await this.exportCSV(); break;
                case 'json': await this.exportJSON(); break;
                case 'pdf': await this.exportPDF(); break;
            }
        });
    });
}
```

---

### 🔵 PRIORITÉ 4 : Comparaisons & Insights (2-3h)

#### Objectif
Ajouter des insights automatiques et comparaisons période vs période.

**4.1 Comparaison Périodes** (1h)
```javascript
// Nouveau module cockpit-comparison.js
export class CockpitComparison {
    async comparePeriodsAPI(period1, period2) {
        const [data1, data2] = await Promise.all([
            fetch(`/api/dashboard/costs/summary?period=${period1}`).then(r => r.json()),
            fetch(`/api/dashboard/costs/summary?period=${period2}`).then(r => r.json())
        ]);

        return {
            messages: this.calculateDelta(data1.messages.total, data2.messages.total),
            tokens: this.calculateDelta(data1.tokens.total, data2.tokens.total),
            costs: this.calculateDelta(data1.costs.total_cost, data2.costs.total_cost)
        };
    }

    calculateDelta(current, previous) {
        const delta = current - previous;
        const percent = previous > 0 ? (delta / previous) * 100 : 0;
        return {
            absolute: delta,
            percent: percent,
            trend: delta > 0 ? 'up' : delta < 0 ? 'down' : 'stable'
        };
    }

    render(comparison) {
        return `
            <div class="comparison-card">
                <h3>Comparaison vs Période Précédente</h3>

                <div class="comparison-metric">
                    <span class="metric-name">Messages</span>
                    <span class="metric-delta ${comparison.messages.trend}">
                        ${comparison.messages.trend === 'up' ? '↑' : '↓'}
                        ${Math.abs(comparison.messages.percent).toFixed(1)}%
                    </span>
                </div>

                <div class="comparison-metric">
                    <span class="metric-name">Tokens</span>
                    <span class="metric-delta ${comparison.tokens.trend}">
                        ${comparison.tokens.trend === 'up' ? '↑' : '↓'}
                        ${Math.abs(comparison.tokens.percent).toFixed(1)}%
                    </span>
                </div>

                <div class="comparison-metric">
                    <span class="metric-name">Coûts</span>
                    <span class="metric-delta ${comparison.costs.trend}">
                        ${comparison.costs.trend === 'up' ? '↑' : '↓'}
                        ${Math.abs(comparison.costs.percent).toFixed(1)}%
                    </span>
                </div>
            </div>
        `;
    }
}
```

**4.2 Insights Automatiques** (1h)
```javascript
// Dans cockpit-insights.js - améliorer
generateInsights(data) {
    const insights = [];

    // Détection usage intensif
    if (data.messages.today > data.messages.week / 7 * 2) {
        insights.push({
            type: 'warning',
            icon: '⚠️',
            title: 'Usage intensif détecté',
            message: `Vous avez envoyé ${data.messages.today} messages aujourd'hui (2x la moyenne hebdo).`
        });
    }

    // Optimisation coûts
    const avgCostPerMessage = data.costs.total_cost / data.messages.total;
    if (avgCostPerMessage > 0.001) {
        insights.push({
            type: 'info',
            icon: '💡',
            title: 'Optimisation possible',
            message: `Coût moyen/message : $${avgCostPerMessage.toFixed(4)}. Considérez des modèles plus légers.`
        });
    }

    // Ratio tokens input/output
    const ratio = data.tokens.output / data.tokens.input;
    if (ratio < 0.05) {
        insights.push({
            type: 'tip',
            icon: '📊',
            title: 'Réponses concises',
            message: `Ratio output/input : ${(ratio * 100).toFixed(1)}%. Les agents sont très concis.`
        });
    }

    // Trend positif
    if (data.messages.week > data.messages.month / 4) {
        insights.push({
            type: 'success',
            icon: '🚀',
            title: 'Activité en hausse',
            message: `L'usage hebdomadaire dépasse la moyenne mensuelle (+${((data.messages.week / (data.messages.month / 4) - 1) * 100).toFixed(0)}%).`
        });
    }

    return insights;
}

renderInsights(insights) {
    return `
        <div class="insights-panel">
            <h3>💡 Insights</h3>
            ${insights.map(insight => `
                <div class="insight-card ${insight.type}">
                    <span class="insight-icon">${insight.icon}</span>
                    <div class="insight-content">
                        <h4>${insight.title}</h4>
                        <p>${insight.message}</p>
                    </div>
                </div>
            `).join('')}
        </div>
    `;
}
```

---

## 🧪 Tests & Validation

### Tests Frontend

**1. Tests Unitaires (Jest)** (1h)
```javascript
// tests/frontend/cockpit-charts.test.js
import { CockpitCharts } from '../src/frontend/features/cockpit/cockpit-charts.js';

describe('CockpitCharts', () => {
    let charts;

    beforeEach(() => {
        charts = new CockpitCharts();
        document.body.innerHTML = '<div id="test-container"></div>';
    });

    test('should initialize charts', async () => {
        await charts.init('test-container');
        expect(charts.charts.activity).toBeDefined();
        expect(charts.charts.costs).toBeDefined();
        expect(charts.charts.tokens).toBeDefined();
    });

    test('should change period', async () => {
        await charts.init('test-container');
        charts.currentPeriod = '7d';
        expect(charts.currentPeriod).toBe('7d');
    });
});
```

**2. Tests E2E (Playwright)** (1h)
```javascript
// tests/e2e/cockpit.spec.js
import { test, expect } from '@playwright/test';

test.describe('Cockpit Features', () => {
    test('should display metrics cards', async ({ page }) => {
        await page.goto('http://localhost:8000');
        await page.click('nav a[href="#cockpit"]');

        await expect(page.locator('.metric-card.messages-card')).toBeVisible();
        await expect(page.locator('.metric-card.tokens-card')).toBeVisible();
        await expect(page.locator('.metric-card.costs-card')).toBeVisible();
    });

    test('should load timeline charts', async ({ page }) => {
        await page.goto('http://localhost:8000#cockpit');

        await expect(page.locator('#chart-activity')).toBeVisible();
        await expect(page.locator('#chart-costs')).toBeVisible();
        await expect(page.locator('#chart-tokens')).toBeVisible();
    });

    test('should export CSV', async ({ page }) => {
        await page.goto('http://localhost:8000#cockpit');

        const downloadPromise = page.waitForEvent('download');
        await page.click('.export-btn[data-format="csv"]');
        const download = await downloadPromise;

        expect(download.suggestedFilename()).toContain('.csv');
    });
});
```

### Tests Backend

**3. Tests API Filtres** (30min)
```python
# tests/test_dashboard_filters.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_filtered_summary_by_agent(client: AsyncClient, auth_headers):
    response = await client.get(
        "/api/dashboard/costs/summary/filtered?agent=anima",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "messages" in data
    assert "tokens" in data

@pytest.mark.asyncio
async def test_filtered_summary_by_date(client: AsyncClient, auth_headers):
    response = await client.get(
        "/api/dashboard/costs/summary/filtered?date_start=2025-10-01&date_end=2025-10-09",
        headers=auth_headers
    )
    assert response.status_code == 200
```

---

## 📋 Checklist Implémentation

### Phase 1 : Graphiques (3-4h)
- [ ] Intégrer Chart.js CDN
- [ ] Créer `CockpitCharts` class complète
- [ ] Connecter aux endpoints `/timeline/*`
- [ ] Implémenter sélecteur période (7d/30d/90d/1y)
- [ ] Ajouter styles responsifs
- [ ] Tests unitaires Chart.js
- [ ] Validation visuelle sur mobile

### Phase 2 : Filtres (2-3h)
- [ ] UI filtres (agent, session, dates)
- [ ] Backend endpoint `/costs/summary/filtered`
- [ ] Backend endpoint `/sessions/list`
- [ ] Logique filtrage SQL (queries.py)
- [ ] Event listeners frontend
- [ ] Tests API filtres
- [ ] Validation UX filtres

### Phase 3 : Export (1-2h)
- [ ] Export CSV fonctionnel
- [ ] Export JSON fonctionnel
- [ ] Export PDF (jsPDF)
- [ ] Menu export avec icônes
- [ ] Nom fichiers timestampés
- [ ] Tests téléchargement
- [ ] Validation formats

### Phase 4 : Insights (2-3h)
- [ ] Comparaison périodes
- [ ] Calcul deltas et trends
- [ ] Génération insights automatiques
- [ ] UI insights avec types (warning/info/success)
- [ ] Refresh insights avec métriques
- [ ] Tests logique insights
- [ ] Validation pertinence

---

## 🎨 Design & UX

### Palette Couleurs
```css
:root {
    /* Graphiques */
    --chart-blue: rgb(59, 130, 246);
    --chart-purple: rgb(168, 85, 247);
    --chart-green: rgb(34, 197, 94);
    --chart-orange: rgb(249, 115, 22);
    --chart-pink: rgb(236, 72, 153);

    /* Trends */
    --trend-up: #22c55e;
    --trend-down: #ef4444;
    --trend-stable: #64748b;

    /* Insights */
    --insight-warning: #f59e0b;
    --insight-info: #3b82f6;
    --insight-success: #10b981;
    --insight-tip: #8b5cf6;
}
```

### Animations
```css
@keyframes fadeInUp {
    from {
        opacity: 0;
        transform: translateY(20px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.chart-card {
    animation: fadeInUp 0.5s ease-out;
}

.chart-card:nth-child(2) { animation-delay: 0.1s; }
.chart-card:nth-child(3) { animation-delay: 0.2s; }
```

---

## 🚀 Déploiement

### Build Frontend
```bash
npm run build
# Vérifier bundles générés
ls -lh dist/
```

### Tests Pré-Deploy
```bash
# Backend
pytest tests/test_dashboard*.py -v

# Frontend
npm test
npm run test:e2e

# Qualité
mypy src
ruff check
```

### Deploy Cloud Run
```bash
# Build + Push + Deploy (voir PROMPT_CODEX_DEPLOY_PHASE3.md)
timestamp=$(date +%Y%m%d-%H%M%S)
docker build --platform linux/amd64 -t europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:cockpit-enhanced-$timestamp .
docker push europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:cockpit-enhanced-$timestamp
gcloud run deploy emergence-app --image europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:cockpit-enhanced-$timestamp ...
```

---

## 📚 Documentation

### Fichiers à Créer
- [ ] `docs/features/cockpit-advanced.md` - Guide utilisateur filtres + export
- [ ] `docs/api/dashboard-filters.md` - Documentation endpoints filtres
- [ ] `README-COCKPIT.md` - Guide développeur cockpit

### Fichiers à Mettre à Jour
- [ ] `docs/passation.md` - Entrée nouvelles features
- [ ] `AGENT_SYNC.md` - Sync features cockpit
- [ ] `docs/deployments/README.md` - Nouveau deploy

---

## 🎯 Priorités Session

**Si 3-4h disponibles** :
1. ✅ Graphiques Timeline (PRIORITÉ 1)
2. ✅ Tests basiques

**Si 6-8h disponibles** :
1. ✅ Graphiques Timeline
2. ✅ Filtres Avancés
3. ✅ Tests complets

**Si 10h+ disponibles** :
1. ✅ Graphiques Timeline
2. ✅ Filtres Avancés
3. ✅ Export Données
4. ✅ Insights Automatiques
5. ✅ Tests E2E complets
6. ✅ Documentation

---

## 🔗 Ressources

### Bibliothèques
- **Chart.js** : https://www.chartjs.org/docs/latest/
- **jsPDF** : https://github.com/parallax/jsPDF
- **Playwright** : https://playwright.dev/

### Endpoints API Existants
```
GET  /api/dashboard/costs/summary
GET  /api/dashboard/costs/summary/session/{session_id}
GET  /api/dashboard/timeline/activity?period={7d|30d|90d|1y}
GET  /api/dashboard/timeline/costs?period={7d|30d|90d|1y}
GET  /api/dashboard/timeline/tokens?period={7d|30d|90d|1y}
```

### Nouveaux Endpoints à Créer
```
GET  /api/dashboard/costs/summary/filtered?agent=X&date_start=Y&date_end=Z
GET  /api/dashboard/sessions/list
GET  /api/dashboard/comparison?period1=X&period2=Y
```

---

**Bon développement ! 🚀**

**Note** : Commencer par PRIORITÉ 1 (Graphiques) car les données API sont déjà prêtes et l'impact visuel est immédiat.
