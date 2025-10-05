/**
 * Cockpit Main Module
 * Unified metrics and analytics dashboard
 */

import { cockpitMetrics } from './cockpit-metrics.js';
import { cockpitCharts } from './cockpit-charts.js';
import { cockpitInsights } from './cockpit-insights.js';

export class Cockpit {
    constructor() {
        this.container = null;
        this.activeTab = 'overview';
        this.modules = {
            metrics: cockpitMetrics,
            charts: cockpitCharts,
            insights: cockpitInsights
        };
        this.initialized = false;
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
        await this.loadActiveView();
        this.initialized = true;
    }

    /**
     * Render cockpit structure
     */
    render() {
        this.container.innerHTML = `
            <div class="cockpit-container">
                <!-- Cockpit Header -->
                <div class="cockpit-header">
                    <div class="cockpit-title">
                        <h1>📊 Cockpit</h1>
                        <p class="cockpit-subtitle">Vue d'ensemble de votre activité</p>
                    </div>
                    <div class="cockpit-actions">
                        <button class="btn-refresh-all" title="Tout actualiser">
                            🔄 Actualiser
                        </button>
                        <button class="btn-export-report" title="Exporter le rapport">
                            📥 Exporter
                        </button>
                    </div>
                </div>

                <!-- Cockpit Tabs -->
                <div class="cockpit-tabs">
                    <button class="cockpit-tab ${this.activeTab === 'overview' ? 'active' : ''}"
                            data-tab="overview">
                        <span class="tab-icon">📊</span>
                        <span class="tab-label">Vue d'ensemble</span>
                    </button>
                    <button class="cockpit-tab ${this.activeTab === 'metrics' ? 'active' : ''}"
                            data-tab="metrics">
                        <span class="tab-icon">📈</span>
                        <span class="tab-label">Métriques</span>
                    </button>
                    <button class="cockpit-tab ${this.activeTab === 'charts' ? 'active' : ''}"
                            data-tab="charts">
                        <span class="tab-icon">📉</span>
                        <span class="tab-label">Graphiques</span>
                    </button>
                    <button class="cockpit-tab ${this.activeTab === 'insights' ? 'active' : ''}"
                            data-tab="insights">
                        <span class="tab-icon">💡</span>
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
            refreshBtn.innerHTML = '⏳ Actualisation...';
        }

        try {
            // Reload active view
            await this.loadActiveView();

            if (refreshBtn) {
                refreshBtn.innerHTML = '✓ Actualisé';
                setTimeout(() => {
                    refreshBtn.innerHTML = '🔄 Actualiser';
                    refreshBtn.disabled = false;
                }, 2000);
            }
        } catch (error) {
            console.error('Error refreshing cockpit:', error);
            if (refreshBtn) {
                refreshBtn.innerHTML = '✗ Erreur';
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
