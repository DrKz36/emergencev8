/**
 * Admin Analytics Module
 * Advanced analytics with Chart.js visualizations
 * Phase P2 - Feature 7: Dashboard Administrateur Avancé
 * V1.0.0 - 2025-10-22
 */

import { AdminIcons, getIcon } from './admin-icons.js';

let chartModulePromise;

async function ensureChart() {
    if (!chartModulePromise) {
        chartModulePromise = import('chart.js').then((module) => {
            const Chart = module.Chart ?? module.default;
            if (!Chart) {
                throw new Error('[AdminAnalytics] Chart.js module unavailable');
            }
            const registerables = Array.isArray(module.registerables) ? module.registerables : [];
            if (registerables.length > 0) {
                Chart.register(...registerables);
            }
            return Chart;
        });
    }
    return chartModulePromise;
}

export class AdminAnalytics {
    constructor() {
        this.container = null;
        this.charts = {
            topUsers: null,
            costHistory: null,
        };
        this.refreshInterval = null;
    }

    /**
     * Initialize analytics view
     */
    async init(containerId) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            console.error('[AdminAnalytics] Container not found');
            return;
        }

        await this.render();
        await this.loadAnalytics();
    }

    /**
     * Render analytics UI
     */
    async render() {
        this.container.innerHTML = `
            <div class="admin-analytics">
                <!-- Header -->
                <div class="analytics-header">
                    <div class="analytics-title">
                        <h2>${getIcon('activity', 'section-icon')} Analytics Avancées</h2>
                        <p class="analytics-subtitle">Analyse détaillée des coûts et de l'utilisation</p>
                    </div>
                    <button class="btn-refresh-analytics" title="Actualiser">
                        ${getIcon('refresh', 'btn-icon')} Actualiser
                    </button>
                </div>

                <!-- Charts Grid -->
                <div class="analytics-charts">
                    <!-- Top 10 Consumers -->
                    <div class="analytics-card">
                        <div class="card-header">
                            <h3>${getIcon('users', 'card-icon')} Top 10 Consommateurs</h3>
                            <span class="card-badge">Coûts par utilisateur</span>
                        </div>
                        <div class="card-body">
                            <canvas id="chart-top-users" height="300"></canvas>
                        </div>
                        <div class="card-footer" id="top-users-summary">
                            <div class="summary-item">
                                <span class="summary-label">Total utilisateurs</span>
                                <span class="summary-value">-</span>
                            </div>
                            <div class="summary-item">
                                <span class="summary-label">Coût total</span>
                                <span class="summary-value">-</span>
                            </div>
                        </div>
                    </div>

                    <!-- Cost History (7 days) -->
                    <div class="analytics-card">
                        <div class="card-header">
                            <h3>${getIcon('barChart', 'card-icon')} Historique des Coûts (7 jours)</h3>
                            <span class="card-badge">Par jour</span>
                        </div>
                        <div class="card-body">
                            <canvas id="chart-cost-history" height="300"></canvas>
                        </div>
                        <div class="card-footer" id="cost-history-summary">
                            <div class="summary-item">
                                <span class="summary-label">Moyenne/jour</span>
                                <span class="summary-value">-</span>
                            </div>
                            <div class="summary-item">
                                <span class="summary-label">Tendance</span>
                                <span class="summary-value">-</span>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Active Sessions List -->
                <div class="analytics-card analytics-sessions">
                    <div class="card-header">
                        <h3>${getIcon('activity', 'card-icon')} Sessions Actives</h3>
                        <span class="card-badge" id="sessions-count">0</span>
                    </div>
                    <div class="card-body">
                        <div id="sessions-list" class="sessions-grid">
                            <p class="loading">Chargement des sessions...</p>
                        </div>
                    </div>
                </div>

                <!-- System Metrics -->
                <div class="analytics-card analytics-metrics">
                    <div class="card-header">
                        <h3>${getIcon('cpu', 'card-icon')} Métriques Système</h3>
                        <span class="card-badge">Temps réel</span>
                    </div>
                    <div class="card-body">
                        <div id="system-metrics" class="metrics-grid">
                            <p class="loading">Chargement des métriques...</p>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Attach event listeners
        this.attachEventListeners();
    }

    /**
     * Attach event listeners
     */
    attachEventListeners() {
        const refreshBtn = this.container.querySelector('.btn-refresh-analytics');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.loadAnalytics());
        }
    }

    /**
     * Load all analytics data
     */
    async loadAnalytics() {
        try {
            // Show loading state
            this.showLoading();

            // Load data in parallel
            const [costsData, sessionsData, metricsData, costHistory] = await Promise.all([
                this.fetchCostsBreakdown(),
                this.fetchActiveSessions(),
                this.fetchSystemMetrics(),
                this.fetchCostHistory(),
            ]);

            // Render charts
            await Promise.all([
                this.renderTopUsersChart(costsData),
                this.renderCostHistoryChart(costHistory),
            ]);

            // Render sessions
            this.renderSessionsList(sessionsData);

            // Render metrics
            this.renderSystemMetrics(metricsData);

        } catch (error) {
            console.error('[AdminAnalytics] Error loading analytics:', error);
            this.showError('Erreur lors du chargement des analytics');
        }
    }

    /**
     * Show loading state
     */
    showLoading() {
        const sessionsContainer = this.container.querySelector('#sessions-list');
        const metricsContainer = this.container.querySelector('#system-metrics');

        if (sessionsContainer) {
            sessionsContainer.innerHTML = '<p class="loading">Chargement des sessions...</p>';
        }
        if (metricsContainer) {
            metricsContainer.innerHTML = '<p class="loading">Chargement des métriques...</p>';
        }
    }

    /**
     * Show error message
     */
    showError(message) {
        const sessionsContainer = this.container.querySelector('#sessions-list');
        const metricsContainer = this.container.querySelector('#system-metrics');

        if (sessionsContainer) {
            sessionsContainer.innerHTML = `<p class="error">${message}</p>`;
        }
        if (metricsContainer) {
            metricsContainer.innerHTML = `<p class="error">${message}</p>`;
        }
    }

    /**
     * Fetch costs breakdown from API
     */
    async fetchCostsBreakdown() {
        const token = this._getAuthToken();
        const response = await fetch('/api/admin/costs/detailed', {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error(`Costs API error: ${response.status}`);
        }

        return await response.json();
    }

    /**
     * Fetch active sessions from API
     */
    async fetchActiveSessions() {
        const token = this._getAuthToken();
        const response = await fetch('/api/admin/analytics/threads', {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error(`Sessions API error: ${response.status}`);
        }

        return await response.json();
    }

    /**
     * Fetch system metrics from API
     */
    async fetchSystemMetrics() {
        const token = this._getAuthToken();
        const response = await fetch('/api/admin/metrics/system', {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error(`Metrics API error: ${response.status}`);
        }

        return await response.json();
    }

    /**
     * Render Top 10 Users Chart (Bar Chart)
     */
    async renderTopUsersChart(data) {
        const users = data.users || [];
        const totalCost = data.total_cost || 0;

        // Sort by total cost and take top 10
        const top10 = users
            .sort((a, b) => (b.total_cost || 0) - (a.total_cost || 0))
            .slice(0, 10);

        // Prepare data
        const labels = top10.map((u, idx) => {
            const email = u.user_id || `User ${idx + 1}`;
            // Truncate email if too long
            return email.length > 20 ? email.substring(0, 17) + '...' : email;
        });
        const costs = top10.map(u => (u.total_cost || 0).toFixed(2));
        const percentages = top10.map(u => {
            const pct = totalCost > 0 ? ((u.total_cost || 0) / totalCost * 100) : 0;
            return pct.toFixed(1);
        });

        // Destroy previous chart if exists
        if (this.charts.topUsers) {
            this.charts.topUsers.destroy();
        }

        // Create chart
        const ctx = this.container.querySelector('#chart-top-users');
        if (!ctx) return;

        const Chart = await ensureChart();
        this.charts.topUsers = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Coût ($)',
                    data: costs,
                    backgroundColor: 'rgba(99, 102, 241, 0.7)',
                    borderColor: 'rgba(99, 102, 241, 1)',
                    borderWidth: 1,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: 'y', // Horizontal bar chart
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const idx = context.dataIndex;
                                const cost = costs[idx];
                                const pct = percentages[idx];
                                return `Coût: $${cost} (${pct}%)`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Coût ($)'
                        }
                    }
                }
            }
        });

        // Update summary
        const summary = this.container.querySelector('#top-users-summary');
        if (summary) {
            summary.innerHTML = `
                <div class="summary-item">
                    <span class="summary-label">Total utilisateurs</span>
                    <span class="summary-value">${users.length}</span>
                </div>
                <div class="summary-item">
                    <span class="summary-label">Coût total</span>
                    <span class="summary-value">$${totalCost.toFixed(2)}</span>
                </div>
            `;
        }
    }

    /**
     * Render Cost History Chart (Line Chart - 7 days)
     */
    async renderCostHistoryChart(historyData) {
        try {
            const history = historyData?.history || [];

            const last7Days = history.slice(-7);

            const labels = last7Days.map(item => {
                const date = new Date(item.date);
                return date.toLocaleDateString('fr-FR', { day: 'numeric', month: 'short' });
            });
            const costs = last7Days.map(item => (item.cost || 0).toFixed(2));

            const avgCost = costs.length > 0
                ? (costs.reduce((sum, c) => sum + parseFloat(c), 0) / costs.length).toFixed(2)
                : 0;

            const trend = costs.length >= 2
                ? (parseFloat(costs[costs.length - 1]) - parseFloat(costs[0])).toFixed(2)
                : 0;

            const trendIcon = trend > 0 ? '??' : (trend < 0 ? '??' : '??');

            if (this.charts.costHistory) {
                this.charts.costHistory.destroy();
            }

            const ctx = this.container.querySelector('#chart-cost-history');
            if (!ctx) return;

            const Chart = await ensureChart();
            this.charts.costHistory = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Coût ($)',
                        data: costs,
                        fill: true,
                        backgroundColor: 'rgba(59, 130, 246, 0.2)',
                        borderColor: 'rgba(59, 130, 246, 1)',
                        borderWidth: 2,
                        tension: 0.3,
                        pointRadius: 4,
                        pointHoverRadius: 6,
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    return `Coût: $${context.parsed.y}`;
                                }
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: 'Coût ($)'
                            }
                        }
                    }
                }
            });

            const summary = this.container.querySelector('#cost-history-summary');
            if (summary) {
                summary.innerHTML = `
                    <div class="summary-item">
                        <span class="summary-label">Moyenne/jour</span>
                        <span class="summary-value">$${avgCost}</span>
                    </div>
                    <div class="summary-item">
                        <span class="summary-label">Tendance</span>
                        <span class="summary-value">${trendIcon} $${Math.abs(trend)}</span>
                    </div>
                `;
            }
        } catch (error) {
            console.error('[AdminAnalytics] Error loading cost history:', error);
        }
    }

    /**
     * Fetch cost history (7 days)
     */
    async fetchCostHistory() {
        const token = this._getAuthToken();
        const response = await fetch('/api/admin/dashboard/global', {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error(`Cost history API error: ${response.status}`);
        }

        const globalData = await response.json();
        return {
            history: globalData.global?.last_7_days || []
        };
    }

    /**
     * Render sessions list
     */
    renderSessionsList(data) {
        const sessions = data.threads || [];
        const container = this.container.querySelector('#sessions-list');
        const countBadge = this.container.querySelector('#sessions-count');

        if (countBadge) {
            countBadge.textContent = sessions.length;
        }

        if (sessions.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <p>Aucune session active</p>
                </div>
            `;
            return;
        }

        // Render sessions grid
        const sessionsHtml = sessions.map(session => {
            const lastActivity = session.last_activity
                ? new Date(session.last_activity).toLocaleString('fr-FR', {
                    day: 'numeric',
                    month: 'short',
                    hour: '2-digit',
                    minute: '2-digit'
                })
                : 'N/A';

            const isActive = session.is_active;
            const statusClass = isActive ? 'active' : 'inactive';
            const statusText = isActive ? 'Actif' : 'Inactif';

            return `
                <div class="session-card">
                    <div class="session-header">
                        <span class="session-status ${statusClass}">${statusText}</span>
                        <span class="session-id" title="${session.id}">${session.id.substring(0, 8)}...</span>
                    </div>
                    <div class="session-body">
                        <div class="session-info">
                            <span class="info-label">Utilisateur</span>
                            <span class="info-value">${session.user_id || 'N/A'}</span>
                        </div>
                        <div class="session-info">
                            <span class="info-label">Dernière activité</span>
                            <span class="info-value">${lastActivity}</span>
                        </div>
                        <div class="session-info">
                            <span class="info-label">Device</span>
                            <span class="info-value">${session.device_info || 'N/A'}</span>
                        </div>
                    </div>
                    <div class="session-actions">
                        <button class="btn-revoke-session" data-session-id="${session.id}">
                            ${getIcon('x', 'btn-icon')} Révoquer
                        </button>
                    </div>
                </div>
            `;
        }).join('');

        container.innerHTML = sessionsHtml;

        // Attach revoke handlers
        container.querySelectorAll('.btn-revoke-session').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const sessionId = e.currentTarget.getAttribute('data-session-id');
                this.revokeSession(sessionId);
            });
        });
    }

    /**
     * Render system metrics
     */
    renderSystemMetrics(data) {
        const container = this.container.querySelector('#system-metrics');

        const uptime = data.uptime_seconds || 0;
        const uptimeHours = (uptime / 3600).toFixed(1);
        const avgLatency = data.average_latency_ms || 0;
        const errorRate = data.error_rate_percent || 0;
        const totalRequests = data.total_requests || 0;

        container.innerHTML = `
            <div class="metric-card">
                <div class="metric-icon">⏱️</div>
                <div class="metric-content">
                    <div class="metric-label">Uptime</div>
                    <div class="metric-value">${uptimeHours}h</div>
                </div>
            </div>
            <div class="metric-card">
                <div class="metric-icon">⚡</div>
                <div class="metric-content">
                    <div class="metric-label">Latence Moyenne</div>
                    <div class="metric-value">${avgLatency.toFixed(0)}ms</div>
                </div>
            </div>
            <div class="metric-card">
                <div class="metric-icon">⚠️</div>
                <div class="metric-content">
                    <div class="metric-label">Taux d'Erreur</div>
                    <div class="metric-value">${errorRate.toFixed(2)}%</div>
                </div>
            </div>
            <div class="metric-card">
                <div class="metric-icon">📊</div>
                <div class="metric-content">
                    <div class="metric-label">Total Requêtes</div>
                    <div class="metric-value">${totalRequests.toLocaleString()}</div>
                </div>
            </div>
        `;
    }

    /**
     * Revoke session
     */
    async revokeSession(sessionId) {
        if (!confirm(`Voulez-vous vraiment révoquer cette session?\n\nID: ${sessionId}\n\nL'utilisateur sera déconnecté immédiatement.`)) {
            return;
        }

        try {
            const token = this._getAuthToken();
            const response = await fetch(`/api/admin/sessions/${sessionId}/revoke`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error(`Revoke API error: ${response.status}`);
            }

            const result = await response.json();

            if (result.success) {
                alert(`Session ${sessionId} révoquée avec succès.`);
                // Reload sessions list
                const sessionsData = await this.fetchActiveSessions();
                this.renderSessionsList(sessionsData);
            } else {
                alert(`Échec de la révocation: ${result.message || 'Erreur inconnue'}`);
            }

        } catch (error) {
            console.error('[AdminAnalytics] Error revoking session:', error);
            alert(`Erreur lors de la révocation de la session: ${error.message}`);
        }
    }

    /**
     * Get auth token from localStorage
     */
    _getAuthToken() {
        const state = JSON.parse(localStorage.getItem('emergenceState-V14') || '{}');
        return state.auth?.token || '';
    }

    /**
     * Destroy analytics (cleanup)
     */
    destroy() {
        // Destroy charts
        if (this.charts.topUsers) {
            this.charts.topUsers.destroy();
            this.charts.topUsers = null;
        }
        if (this.charts.costHistory) {
            this.charts.costHistory.destroy();
            this.charts.costHistory = null;
        }

        // Clear refresh interval
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }

        // Clear container
        if (this.container) {
            this.container.innerHTML = '';
            this.container = null;
        }
    }
}
