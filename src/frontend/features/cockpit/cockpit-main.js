/**
 * Cockpit Main Module
 * Unified metrics and analytics dashboard
 */

import { cockpitMetrics } from './cockpit-metrics.js';
import { cockpitCharts } from './cockpit-charts.js';
import { cockpitInsights } from './cockpit-insights.js';
import { cockpitAgents } from './cockpit-agents.js';
import { getIcon } from './cockpit-icons.js';

export class Cockpit {
    constructor() {
        this.container = null;
        this.activeTab = 'overview';
        this.modules = {
            metrics: cockpitMetrics,
            charts: cockpitCharts,
            insights: cockpitInsights,
            agents: cockpitAgents
        };
        this.initialized = false;
        this.isMobile = this.detectMobile();
    }

    /**
     * Detect if device is mobile
     */
    detectMobile() {
        return window.innerWidth <= 768;
    }

    /**
     * Initialize cockpit
     */
    async init(containerId) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            console.error('Cockpit container not found');
            return;
        }

        this.render();

        // Only load active view for desktop mode
        // Mobile mode loads data in renderMobile() -> loadMobileData()
        if (!this.isMobile) {
            await this.loadActiveView();
        }

        this.initialized = true;
    }

    /**
     * Render cockpit structure
     */
    render() {
        if (this.isMobile) {
            this.renderMobile();
            return;
        }

        this.container.innerHTML = `
            <div class="cockpit-container">
                <!-- Cockpit Header -->
                <div class="cockpit-header">
                    <div class="cockpit-title">
                        <h1>${getIcon('cockpit')} Cockpit</h1>
                        <p class="cockpit-subtitle">Vue d'ensemble de votre activité</p>
                    </div>
                    <div class="cockpit-actions">
                        <button class="btn-refresh-all" title="Tout actualiser">
                            ${getIcon('refresh')} Actualiser
                        </button>
                        <button class="btn-export-report" title="Exporter le rapport">
                            ${getIcon('download')} Exporter
                        </button>
                    </div>
                </div>

                <!-- Cockpit Tabs -->
                <div class="cockpit-tabs">
                    <button class="cockpit-tab ${this.activeTab === 'overview' ? 'active' : ''}"
                            data-tab="overview">
                        <span class="tab-icon">${getIcon('cockpit')}</span>
                        <span class="tab-label">Vue d'ensemble</span>
                    </button>
                    <button class="cockpit-tab ${this.activeTab === 'metrics' ? 'active' : ''}"
                            data-tab="metrics">
                        <span class="tab-icon">${getIcon('barChart')}</span>
                        <span class="tab-label">Métriques</span>
                    </button>
                    <button class="cockpit-tab ${this.activeTab === 'agents' ? 'active' : ''}"
                            data-tab="agents">
                        <span class="tab-icon">${getIcon('robot')}</span>
                        <span class="tab-label">Agents</span>
                    </button>
                    <button class="cockpit-tab ${this.activeTab === 'charts' ? 'active' : ''}"
                            data-tab="charts">
                        <span class="tab-icon">${getIcon('pieChart')}</span>
                        <span class="tab-label">Graphiques</span>
                    </button>
                    <button class="cockpit-tab ${this.activeTab === 'insights' ? 'active' : ''}"
                            data-tab="insights">
                        <span class="tab-icon">${getIcon('lightbulb')}</span>
                        <span class="tab-label">Insights</span>
                    </button>
                </div>

                <!-- Cockpit Content -->
                <div class="cockpit-content">
                    <!-- Overview Tab -->
                    <div class="cockpit-view ${this.activeTab === 'overview' ? 'active' : ''}"
                         data-view="overview">
                        <div class="overview-grid">
                            <div id="overview-metrics" class="overview-section"></div>
                            <div id="overview-charts" class="overview-section"></div>
                            <div id="overview-insights" class="overview-section"></div>
                        </div>
                    </div>

                    <!-- Metrics Tab -->
                    <div class="cockpit-view ${this.activeTab === 'metrics' ? 'active' : ''}"
                         data-view="metrics">
                        <div id="metrics-container"></div>
                    </div>

                    <!-- Charts Tab -->
                    <div class="cockpit-view ${this.activeTab === 'charts' ? 'active' : ''}"
                         data-view="charts">
                        <div id="charts-container"></div>
                    </div>

                    <!-- Agents Tab -->
                    <div class="cockpit-view ${this.activeTab === 'agents' ? 'active' : ''}"
                         data-view="agents">
                        <div id="agents-container"></div>
                    </div>

                    <!-- Insights Tab -->
                    <div class="cockpit-view ${this.activeTab === 'insights' ? 'active' : ''}"
                         data-view="insights">
                        <div id="insights-container"></div>
                    </div>
                </div>
            </div>
        `;

        this.attachEventListeners();
    }

    /**
     * Render mobile-optimized cockpit
     */
    renderMobile() {
        this.container.innerHTML = `
            <div class="cockpit-container cockpit-mobile">
                <!-- Mobile Notice -->
                <div class="cockpit-mobile-notice">
                    <div class="notice-icon">${getIcon('smartphone')}</div>
                    <div class="notice-content">
                        <h3>Version Mobile Simplifiée</h3>
                        <p>Cette vue affiche les données essentielles. Pour accéder aux graphiques détaillés et analyses complètes, veuillez utiliser un ordinateur de bureau.</p>
                    </div>
                </div>

                <!-- Mobile Header -->
                <div class="cockpit-mobile-header">
                    <h1>${getIcon('cockpit')} Cockpit</h1>
                    <button class="btn-refresh-mobile" title="Actualiser">
                        ${getIcon('refresh')}
                    </button>
                </div>

                <!-- Mobile Summary Cards -->
                <div class="cockpit-mobile-summary" id="mobile-summary">
                    <div class="mobile-loading">Chargement...</div>
                </div>

                <!-- Mobile Agents List -->
                <div class="cockpit-mobile-section">
                    <h2>${getIcon('robot')} Agents Actifs</h2>
                    <div class="mobile-agents-list" id="mobile-agents">
                        <div class="mobile-loading">Chargement...</div>
                    </div>
                </div>

                <!-- Mobile Recent Activity -->
                <div class="cockpit-mobile-section">
                    <h2>${getIcon('activity')} Activité Récente</h2>
                    <div class="mobile-activity-list" id="mobile-activity">
                        <div class="mobile-loading">Chargement...</div>
                    </div>
                </div>

                <!-- Mobile Quick Stats -->
                <div class="cockpit-mobile-section">
                    <h2>${getIcon('trendingUp')} Tendances</h2>
                    <div class="mobile-trends-grid" id="mobile-trends">
                        <div class="mobile-loading">Chargement...</div>
                    </div>
                </div>
            </div>
        `;

        this.attachMobileEventListeners();
        this.loadMobileData();
    }

    /**
     * Attach event listeners for mobile
     */
    attachMobileEventListeners() {
        const refreshBtn = this.container.querySelector('.btn-refresh-mobile');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.loadMobileData());
        }
    }

    /**
     * Load data for mobile view
     */
    async loadMobileData() {
        try {
            // Import API client
            const { api } = await import('../../shared/api-client.js');

            // Fetch data directly from API without using desktop modules
            const [metricsData, agentsData] = await Promise.all([
                this.fetchMetricsForMobile(api),
                this.fetchAgentsForMobile(api)
            ]);

            // Render mobile views with fetched data
            this.renderMobileSummary(metricsData);
            this.renderMobileAgents(agentsData);
            this.renderMobileActivity(metricsData);
            this.renderMobileTrends(metricsData);

        } catch (error) {
            console.error('Error loading mobile data:', error);
            this.showMobileError('Impossible de charger les données');
        }
    }

    /**
     * Fetch metrics data for mobile (bypassing desktop module)
     */
    async fetchMetricsForMobile(api) {
        try {
            const data = await api.get('/api/dashboard/costs/summary');

            return {
                costs: {
                    total: data.costs?.total_cost || 0,
                    today: data.costs?.today_cost || 0,
                    week: data.costs?.current_week_cost || 0,
                    month: data.costs?.current_month_cost || 0,
                    last24h: data.costs?.today_cost || 0,
                    last7d: data.costs?.current_week_cost || 0
                },
                tokens: {
                    total: data.tokens?.total || 0,
                    input: data.tokens?.input || 0,
                    output: data.tokens?.output || 0
                },
                messages: {
                    total: data.messages?.total || 0,
                    today: data.messages?.today || 0,
                    week: data.messages?.week || 0,
                    month: data.messages?.month || 0,
                    last24h: data.messages?.today || 0,
                    last7d: data.messages?.week || 0
                }
            };
        } catch (error) {
            console.error('Error fetching metrics:', error);
            return {
                costs: { total: 0, today: 0, week: 0, month: 0, last24h: 0, last7d: 0 },
                tokens: { total: 0, input: 0, output: 0 },
                messages: { total: 0, today: 0, week: 0, month: 0, last24h: 0, last7d: 0 }
            };
        }
    }

    /**
     * Fetch agents data for mobile (bypassing desktop module)
     */
    async fetchAgentsForMobile(api) {
        try {
            const data = await api.get('/api/dashboard/costs/by-agent');
            return Array.isArray(data) ? data : [];
        } catch (error) {
            console.error('Error fetching agents:', error);
            return [];
        }
    }

    /**
     * Show mobile error message
     */
    showMobileError(message) {
        const containers = [
            '#mobile-summary',
            '#mobile-agents',
            '#mobile-activity',
            '#mobile-trends'
        ];

        containers.forEach(selector => {
            const container = this.container.querySelector(selector);
            if (container) {
                container.innerHTML = `
                    <div class="mobile-error">
                        ${getIcon('alertTriangle')}
                        <span>${message}</span>
                    </div>
                `;
            }
        });
    }

    /**
     * Render mobile summary cards
     */
    renderMobileSummary(metrics) {
        const container = this.container.querySelector('#mobile-summary');
        if (!container) return;

        const totalCost = metrics.costs?.total || 0;
        const totalTokens = (metrics.tokens?.input || 0) + (metrics.tokens?.output || 0);
        const totalMessages = metrics.messages?.total || 0;

        container.innerHTML = `
            <div class="mobile-card mobile-card-primary">
                <div class="mobile-card-icon">${getIcon('dollarSign')}</div>
                <div class="mobile-card-content">
                    <div class="mobile-card-label">Coût Total</div>
                    <div class="mobile-card-value">$${totalCost.toFixed(2)}</div>
                </div>
            </div>
            <div class="mobile-card">
                <div class="mobile-card-icon">${getIcon('hash')}</div>
                <div class="mobile-card-content">
                    <div class="mobile-card-label">Tokens</div>
                    <div class="mobile-card-value">${this.formatNumber(totalTokens)}</div>
                </div>
            </div>
            <div class="mobile-card">
                <div class="mobile-card-icon">${getIcon('messageCircle')}</div>
                <div class="mobile-card-content">
                    <div class="mobile-card-label">Messages</div>
                    <div class="mobile-card-value">${totalMessages}</div>
                </div>
            </div>
        `;
    }

    /**
     * Render mobile agents list
     */
    renderMobileAgents(agentsData) {
        const container = this.container.querySelector('#mobile-agents');
        if (!container) return;

        if (!agentsData || agentsData.length === 0) {
            container.innerHTML = '<div class="mobile-empty">Aucun agent actif</div>';
            return;
        }

        // Group by agent
        const agentGroups = {};
        agentsData.forEach(item => {
            if (!agentGroups[item.agent]) {
                agentGroups[item.agent] = {
                    agent: item.agent,
                    totalCost: 0,
                    totalRequests: 0
                };
            }
            agentGroups[item.agent].totalCost += item.total_cost;
            agentGroups[item.agent].totalRequests += item.request_count;
        });

        const agents = Object.values(agentGroups).slice(0, 5);

        container.innerHTML = agents.map(agent => `
            <div class="mobile-agent-item">
                <div class="mobile-agent-info">
                    <div class="mobile-agent-icon">${this.getAgentIcon(agent.agent)}</div>
                    <div class="mobile-agent-name">${agent.agent}</div>
                </div>
                <div class="mobile-agent-stats">
                    <div class="mobile-agent-cost">$${agent.totalCost.toFixed(3)}</div>
                    <div class="mobile-agent-count">${agent.totalRequests} req</div>
                </div>
            </div>
        `).join('');
    }

    /**
     * Render mobile activity
     */
    renderMobileActivity(metrics) {
        const container = this.container.querySelector('#mobile-activity');
        if (!container) return;

        const dailyMessages = metrics.messages?.last24h || 0;
        const weeklyMessages = metrics.messages?.last7d || 0;
        const dailyCost = metrics.costs?.last24h || 0;
        const weeklyCost = metrics.costs?.last7d || 0;

        container.innerHTML = `
            <div class="mobile-activity-row">
                <div class="mobile-activity-label">Dernières 24h</div>
                <div class="mobile-activity-values">
                    <span>${dailyMessages} messages</span>
                    <span class="mobile-activity-cost">$${dailyCost.toFixed(3)}</span>
                </div>
            </div>
            <div class="mobile-activity-row">
                <div class="mobile-activity-label">7 derniers jours</div>
                <div class="mobile-activity-values">
                    <span>${weeklyMessages} messages</span>
                    <span class="mobile-activity-cost">$${weeklyCost.toFixed(3)}</span>
                </div>
            </div>
        `;
    }

    /**
     * Render mobile trends
     */
    renderMobileTrends(metrics) {
        const container = this.container.querySelector('#mobile-trends');
        if (!container) return;

        const avgCostPerMessage = metrics.messages?.total > 0
            ? (metrics.costs?.total || 0) / metrics.messages.total
            : 0;

        const inputTokens = metrics.tokens?.input || 0;
        const outputTokens = metrics.tokens?.output || 0;
        const totalTokens = inputTokens + outputTokens;

        container.innerHTML = `
            <div class="mobile-trend-card">
                <div class="mobile-trend-label">Coût moyen/msg</div>
                <div class="mobile-trend-value">$${avgCostPerMessage.toFixed(4)}</div>
            </div>
            <div class="mobile-trend-card">
                <div class="mobile-trend-label">Tokens Input</div>
                <div class="mobile-trend-value">${this.formatNumber(inputTokens)}</div>
            </div>
            <div class="mobile-trend-card">
                <div class="mobile-trend-label">Tokens Output</div>
                <div class="mobile-trend-value">${this.formatNumber(outputTokens)}</div>
            </div>
            <div class="mobile-trend-card">
                <div class="mobile-trend-label">Total Tokens</div>
                <div class="mobile-trend-value">${this.formatNumber(totalTokens)}</div>
            </div>
        `;
    }

    /**
     * Get icon for agent
     */
    getAgentIcon(agentName) {
        const icons = {
            'Anima': getIcon('target'),
            'Neo': getIcon('eye'),
            'Nexus': getIcon('settings'),
            'User': getIcon('user'),
            'System': getIcon('settings')
        };
        return icons[agentName] || getIcon('robot');
    }

    /**
     * Format large numbers
     */
    formatNumber(num) {
        if (num >= 1000000) {
            return (num / 1000000).toFixed(1) + 'M';
        }
        if (num >= 1000) {
            return (num / 1000).toFixed(1) + 'K';
        }
        return num.toLocaleString();
    }

    /**
     * Attach event listeners
     */
    attachEventListeners() {
        // Tab switching
        this.container.querySelectorAll('.cockpit-tab').forEach(tab => {
            tab.addEventListener('click', (e) => {
                const tabName = e.currentTarget.dataset.tab;
                this.switchTab(tabName);
            });
        });

        // Refresh all
        const refreshBtn = this.container.querySelector('.btn-refresh-all');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.refreshAll());
        }

        // Export report
        const exportBtn = this.container.querySelector('.btn-export-report');
        if (exportBtn) {
            exportBtn.addEventListener('click', () => this.exportReport());
        }
    }

    /**
     * Switch active tab
     */
    async switchTab(tabName) {
        this.activeTab = tabName;

        // Update tab buttons
        this.container.querySelectorAll('.cockpit-tab').forEach(tab => {
            tab.classList.toggle('active', tab.dataset.tab === tabName);
        });

        // Update views
        this.container.querySelectorAll('.cockpit-view').forEach(view => {
            view.classList.toggle('active', view.dataset.view === tabName);
        });

        // Load content for active tab
        await this.loadActiveView();
    }

    /**
     * Load content for active view
     */
    async loadActiveView() {
        switch (this.activeTab) {
            case 'overview':
                await this.loadOverview();
                break;
            case 'metrics':
                await this.modules.metrics.init('metrics-container');
                break;
            case 'agents':
                await this.modules.agents.init('agents-container');
                break;
            case 'charts':
                await this.modules.charts.init('charts-container');
                break;
            case 'insights':
                await this.modules.insights.init('insights-container');
                break;
        }
    }

    /**
     * Load overview (combines all modules in compact form)
     */
    async loadOverview() {
        // Initialize all modules in overview containers
        await Promise.all([
            this.modules.metrics.init('overview-metrics'),
            this.modules.charts.init('overview-charts'),
            this.modules.insights.init('overview-insights')
        ]);
    }

    /**
     * Refresh all cockpit data
     */
    async refreshAll() {
        const refreshBtn = this.container.querySelector('.btn-refresh-all');
        if (refreshBtn) {
            refreshBtn.disabled = true;
            refreshBtn.innerHTML = `${getIcon('clock')} Actualisation...`;
        }

        try {
            // Reload active view
            await this.loadActiveView();

            if (refreshBtn) {
                refreshBtn.innerHTML = `${getIcon('refresh')} Actualisé`;
                setTimeout(() => {
                    refreshBtn.innerHTML = `${getIcon('refresh')} Actualiser`;
                    refreshBtn.disabled = false;
                }, 2000);
            }
        } catch (error) {
            console.error('Error refreshing cockpit:', error);
            if (refreshBtn) {
                refreshBtn.innerHTML = `${getIcon('alertTriangle')} Erreur`;
                refreshBtn.disabled = false;
            }
        }
    }

    /**
     * Export complete cockpit report
     */
    async exportReport() {
        try {
            const report = {
                exportDate: new Date().toISOString(),
                cockpit: this.activeTab,
                data: {
                    metrics: this.modules.metrics.metrics,
                    charts: this.modules.charts.chartData,
                    insights: this.modules.insights.insights
                }
            };

            const blob = new Blob([JSON.stringify(report, null, 2)], {
                type: 'application/json'
            });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `cockpit-report-${Date.now()}.json`;
            a.click();
            URL.revokeObjectURL(url);

            this.showNotification('Rapport exporté avec succès', 'success');
        } catch (error) {
            console.error('Error exporting report:', error);
            this.showNotification('Erreur lors de l\'export', 'error');
        }
    }

    /**
     * Show notification
     */
    showNotification(message, type = 'info') {
        // TODO: Integrate with global notification system
        console.log(`[${type.toUpperCase()}]`, message);
    }

    /**
     * Render mobile summary cards
     */
    renderMobileSummary(metrics) {
        const container = this.container.querySelector('#mobile-summary');
        if (!container) {
            console.warn('[Cockpit Mobile] Summary container not found');
            return;
        }

        const totalCost = metrics.costs?.total || 0;
        const totalTokens = (metrics.tokens?.input || 0) + (metrics.tokens?.output || 0);
        const totalMessages = metrics.messages?.total || 0;

        console.log('[Cockpit Mobile] Rendering summary:', { totalCost, totalTokens, totalMessages });

        container.innerHTML = `
            <div class="mobile-card mobile-card-primary">
                <div class="mobile-card-icon">${getIcon('dollarSign')}</div>
                <div class="mobile-card-content">
                    <div class="mobile-card-label">Coût Total</div>
                    <div class="mobile-card-value">$${totalCost.toFixed(2)}</div>
                </div>
            </div>
            <div class="mobile-card">
                <div class="mobile-card-icon">${getIcon('hash')}</div>
                <div class="mobile-card-content">
                    <div class="mobile-card-label">Tokens</div>
                    <div class="mobile-card-value">${this.formatNumber(totalTokens)}</div>
                </div>
            </div>
            <div class="mobile-card">
                <div class="mobile-card-icon">${getIcon('messageCircle')}</div>
                <div class="mobile-card-content">
                    <div class="mobile-card-label">Messages</div>
                    <div class="mobile-card-value">${totalMessages}</div>
                </div>
            </div>
        `;
    }

    /**
     * Render mobile agents list
     */
    renderMobileAgents(agentsData) {
        const container = this.container.querySelector('#mobile-agents');
        if (!container) {
            console.warn('[Cockpit Mobile] Agents container not found');
            return;
        }

        console.log('[Cockpit Mobile] Rendering agents:', agentsData);

        if (!agentsData || agentsData.length === 0) {
            container.innerHTML = '<div class="mobile-empty">Aucun agent actif</div>';
            return;
        }

        // Group by agent
        const agentGroups = {};
        agentsData.forEach(item => {
            if (!agentGroups[item.agent]) {
                agentGroups[item.agent] = {
                    agent: item.agent,
                    totalCost: 0,
                    totalRequests: 0
                };
            }
            agentGroups[item.agent].totalCost += item.total_cost;
            agentGroups[item.agent].totalRequests += item.request_count;
        });

        const agents = Object.values(agentGroups).slice(0, 5);

        container.innerHTML = agents.map(agent => `
            <div class="mobile-agent-item">
                <div class="mobile-agent-info">
                    <div class="mobile-agent-icon">${this.getAgentIcon(agent.agent)}</div>
                    <div class="mobile-agent-name">${agent.agent}</div>
                </div>
                <div class="mobile-agent-stats">
                    <div class="mobile-agent-cost">$${agent.totalCost.toFixed(3)}</div>
                    <div class="mobile-agent-count">${agent.totalRequests} req</div>
                </div>
            </div>
        `).join('');
    }

    /**
     * Render mobile activity
     */
    renderMobileActivity(metrics) {
        const container = this.container.querySelector('#mobile-activity');
        if (!container) {
            console.warn('[Cockpit Mobile] Activity container not found');
            return;
        }

        const dailyMessages = metrics.messages?.last24h || 0;
        const weeklyMessages = metrics.messages?.last7d || 0;
        const dailyCost = metrics.costs?.last24h || 0;
        const weeklyCost = metrics.costs?.last7d || 0;

        console.log('[Cockpit Mobile] Rendering activity:', { dailyMessages, weeklyMessages, dailyCost, weeklyCost });

        container.innerHTML = `
            <div class="mobile-activity-row">
                <div class="mobile-activity-label">Dernières 24h</div>
                <div class="mobile-activity-values">
                    <span>${dailyMessages} messages</span>
                    <span class="mobile-activity-cost">$${dailyCost.toFixed(3)}</span>
                </div>
            </div>
            <div class="mobile-activity-row">
                <div class="mobile-activity-label">7 derniers jours</div>
                <div class="mobile-activity-values">
                    <span>${weeklyMessages} messages</span>
                    <span class="mobile-activity-cost">$${weeklyCost.toFixed(3)}</span>
                </div>
            </div>
        `;
    }

    /**
     * Render mobile trends
     */
    renderMobileTrends(metrics) {
        const container = this.container.querySelector('#mobile-trends');
        if (!container) {
            console.warn('[Cockpit Mobile] Trends container not found');
            return;
        }

        const avgCostPerMessage = metrics.messages?.total > 0
            ? (metrics.costs?.total || 0) / metrics.messages.total
            : 0;

        const inputTokens = metrics.tokens?.input || 0;
        const outputTokens = metrics.tokens?.output || 0;
        const totalTokens = inputTokens + outputTokens;

        console.log('[Cockpit Mobile] Rendering trends:', { avgCostPerMessage, inputTokens, outputTokens, totalTokens });

        container.innerHTML = `
            <div class="mobile-trend-card">
                <div class="mobile-trend-label">Coût moyen/msg</div>
                <div class="mobile-trend-value">$${avgCostPerMessage.toFixed(4)}</div>
            </div>
            <div class="mobile-trend-card">
                <div class="mobile-trend-label">Tokens Input</div>
                <div class="mobile-trend-value">${this.formatNumber(inputTokens)}</div>
            </div>
            <div class="mobile-trend-card">
                <div class="mobile-trend-label">Tokens Output</div>
                <div class="mobile-trend-value">${this.formatNumber(outputTokens)}</div>
            </div>
            <div class="mobile-trend-card">
                <div class="mobile-trend-label">Total Tokens</div>
                <div class="mobile-trend-value">${this.formatNumber(totalTokens)}</div>
            </div>
        `;
    }

    /**
     * Get icon for agent
     */
    getAgentIcon(agentName) {
        const icons = {
            'Anima': getIcon('target'),
            'Neo': getIcon('eye'),
            'Nexus': getIcon('settings'),
            'User': getIcon('user'),
            'System': getIcon('settings')
        };
        return icons[agentName] || getIcon('robot');
    }

    /**
     * Destroy cockpit
     */
    destroy() {
        Object.values(this.modules).forEach(module => {
            if (module.destroy) {
                module.destroy();
            }
        });

        if (this.container) {
            this.container.innerHTML = '';
        }

        this.initialized = false;
    }
}

// Export singleton instance
export const cockpit = new Cockpit();
