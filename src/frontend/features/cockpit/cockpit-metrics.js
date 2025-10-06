/**
 * Cockpit Metrics Module
 * Displays comprehensive usage statistics for messages, threads, tokens, and costs
 */

export class CockpitMetrics {
    constructor() {
        this.container = null;
        this.metrics = {
            messages: { total: 0, today: 0, week: 0, month: 0 },
            threads: { total: 0, active: 0, archived: 0 },
            tokens: { total: 0, input: 0, output: 0, avgPerMessage: 0 },
            costs: { total: 0, today: 0, week: 0, month: 0, avgPerMessage: 0 }
        };
        this.updateInterval = null;
    }

    /**
     * Initialize metrics module
     */
    async init(containerId) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            console.error('Cockpit metrics container not found');
            return;
        }

        this.render();
        await this.loadMetrics();
        this.startAutoUpdate();
    }

    /**
     * Render metrics UI structure
     */
    render() {
        this.container.innerHTML = `
            <div class="cockpit-metrics">
                <div class="metrics-header">
                    <h2>📊 Métriques d'Utilisation</h2>
                    <div class="metrics-actions">
                        <button class="btn-refresh" title="Actualiser">
                            <span class="icon">🔄</span>
                            Actualiser
                        </button>
                        <button class="btn-export" title="Exporter les données">
                            <span class="icon">📥</span>
                            Exporter
                        </button>
                    </div>
                </div>

                <div class="metrics-grid">
                    <!-- Messages Metrics -->
                    <div class="metric-card messages-card">
                        <div class="metric-icon">💬</div>
                        <div class="metric-content">
                            <h3>Messages</h3>
                            <div class="metric-main">
                                <span class="metric-value" data-metric="messages-total">0</span>
                                <span class="metric-label">Total</span>
                            </div>
                            <div class="metric-details">
                                <div class="metric-stat">
                                    <span class="stat-label">Aujourd'hui</span>
                                    <span class="stat-value" data-metric="messages-today">0</span>
                                </div>
                                <div class="metric-stat">
                                    <span class="stat-label">Cette semaine</span>
                                    <span class="stat-value" data-metric="messages-week">0</span>
                                </div>
                                <div class="metric-stat">
                                    <span class="stat-label">Ce mois</span>
                                    <span class="stat-value" data-metric="messages-month">0</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Threads Metrics -->
                    <div class="metric-card threads-card">
                        <div class="metric-icon">🧵</div>
                        <div class="metric-content">
                            <h3>Threads</h3>
                            <div class="metric-main">
                                <span class="metric-value" data-metric="threads-total">0</span>
                                <span class="metric-label">Total</span>
                            </div>
                            <div class="metric-details">
                                <div class="metric-stat">
                                    <span class="stat-label">Actifs</span>
                                    <span class="stat-value" data-metric="threads-active">0</span>
                                </div>
                                <div class="metric-stat">
                                    <span class="stat-label">Archivés</span>
                                    <span class="stat-value" data-metric="threads-archived">0</span>
                                </div>
                                <div class="metric-stat">
                                    <span class="stat-label">Taux d'activité</span>
                                    <span class="stat-value" data-metric="threads-rate">0%</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Tokens Metrics -->
                    <div class="metric-card tokens-card">
                        <div class="metric-icon">🎯</div>
                        <div class="metric-content">
                            <h3>Tokens</h3>
                            <div class="metric-main">
                                <span class="metric-value" data-metric="tokens-total">0</span>
                                <span class="metric-label">Total</span>
                            </div>
                            <div class="metric-details">
                                <div class="metric-stat">
                                    <span class="stat-label">Input</span>
                                    <span class="stat-value" data-metric="tokens-input">0</span>
                                </div>
                                <div class="metric-stat">
                                    <span class="stat-label">Output</span>
                                    <span class="stat-value" data-metric="tokens-output">0</span>
                                </div>
                                <div class="metric-stat">
                                    <span class="stat-label">Moy. / message</span>
                                    <span class="stat-value" data-metric="tokens-avg">0</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Costs Metrics -->
                    <div class="metric-card costs-card">
                        <div class="metric-icon">💰</div>
                        <div class="metric-content">
                            <h3>Coûts</h3>
                            <div class="metric-main">
                                <span class="metric-value" data-metric="costs-total">$0.00</span>
                                <span class="metric-label">Total</span>
                            </div>
                            <div class="metric-details">
                                <div class="metric-stat">
                                    <span class="stat-label">Aujourd'hui</span>
                                    <span class="stat-value" data-metric="costs-today">$0.00</span>
                                </div>
                                <div class="metric-stat">
                                    <span class="stat-label">Cette semaine</span>
                                    <span class="stat-value" data-metric="costs-week">$0.00</span>
                                </div>
                                <div class="metric-stat">
                                    <span class="stat-label">Ce mois</span>
                                    <span class="stat-value" data-metric="costs-month">$0.00</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Additional Stats -->
                <div class="metrics-summary">
                    <div class="summary-card">
                        <span class="summary-label">Coût moyen par message</span>
                        <span class="summary-value" data-metric="costs-avg">$0.00</span>
                    </div>
                    <div class="summary-card">
                        <span class="summary-label">Messages par thread (moyenne)</span>
                        <span class="summary-value" data-metric="messages-per-thread">0</span>
                    </div>
                    <div class="summary-card">
                        <span class="summary-label">Dernière activité</span>
                        <span class="summary-value" data-metric="last-activity">-</span>
                    </div>
                    <div class="summary-card">
                        <span class="summary-label">Période d'analyse</span>
                        <span class="summary-value" data-metric="analysis-period">-</span>
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
        const refreshBtn = this.container.querySelector('.btn-refresh');
        const exportBtn = this.container.querySelector('.btn-export');

        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.loadMetrics());
        }

        if (exportBtn) {
            exportBtn.addEventListener('click', () => this.exportMetrics());
        }
    }

    /**
     * Load metrics from API
     */
    async loadMetrics() {
        try {
            // Simulate API calls - replace with actual API endpoints
            const [messages, threads, tokens, costs] = await Promise.all([
                this.fetchMessagesMetrics(),
                this.fetchThreadsMetrics(),
                this.fetchTokensMetrics(),
                this.fetchCostsMetrics()
            ]);

            this.metrics = { messages, threads, tokens, costs };
            this.updateUI();
        } catch (error) {
            console.error('Error loading metrics:', error);
            this.showError('Impossible de charger les métriques');
        }
    }

    /**
     * Fetch all metrics from dashboard API
     */
    async fetchAllMetrics() {
        try {
            const token = this._getAuthToken();
            const sessionId = this._getSessionId();

            const headers = {
                'Content-Type': 'application/json'
            };

            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }

            if (sessionId) {
                headers['X-Session-Id'] = sessionId;
            }

            const response = await fetch('/api/dashboard/costs/summary', {
                method: 'GET',
                headers: headers
            });

            if (!response.ok) {
                throw new Error(`Dashboard API error: ${response.status}`);
            }

            const data = await response.json();
            return data;
        } catch (error) {
            console.error('[Cockpit] Error fetching dashboard data:', error);
            // Return fallback empty data
            return {
                costs: {
                    total_cost: 0,
                    today_cost: 0,
                    current_week_cost: 0,
                    current_month_cost: 0
                },
                monitoring: {
                    total_documents: 0,
                    total_sessions: 0
                },
                raw_data: {
                    documents: [],
                    sessions: []
                }
            };
        }
    }

    /**
     * Fetch messages metrics
     */
    async fetchMessagesMetrics() {
        const data = await this.fetchAllMetrics();
        const sessions = data.raw_data?.sessions || [];

        // Calculate message stats from sessions
        let totalMessages = 0;
        sessions.forEach(session => {
            if (session.message_count) {
                totalMessages += session.message_count;
            }
        });

        return {
            total: totalMessages,
            today: 0, // TODO: calculate from session dates
            week: 0,
            month: totalMessages
        };
    }

    /**
     * Fetch threads metrics
     */
    async fetchThreadsMetrics() {
        const data = await this.fetchAllMetrics();
        const sessions = data.raw_data?.sessions || [];

        return {
            total: sessions.length,
            active: sessions.filter(s => !s.archived).length,
            archived: sessions.filter(s => s.archived).length
        };
    }

    /**
     * Fetch tokens metrics
     */
    async fetchTokensMetrics() {
        // TODO: Add tokens tracking in backend
        return {
            total: 0,
            input: 0,
            output: 0,
            avgPerMessage: 0
        };
    }

    /**
     * Fetch costs metrics
     */
    async fetchCostsMetrics() {
        const data = await this.fetchAllMetrics();
        const costs = data.costs || {};

        return {
            total: costs.total_cost || 0,
            today: costs.today_cost || 0,
            week: costs.current_week_cost || 0,
            month: costs.current_month_cost || 0,
            avgPerMessage: 0 // TODO: calculate
        };
    }

    /**
     * Get auth token from storage
     */
    _getAuthToken() {
        try {
            return localStorage.getItem('emergence.id_token') ||
                   localStorage.getItem('id_token') ||
                   sessionStorage.getItem('emergence.id_token') ||
                   sessionStorage.getItem('id_token');
        } catch (e) {
            return null;
        }
    }

    /**
     * Get session ID from storage
     */
    _getSessionId() {
        try {
            const state = JSON.parse(localStorage.getItem('emergenceState-V14') || '{}');
            return state.session?.id || state.websocket?.sessionId;
        } catch (e) {
            return null;
        }
    }

    /**
     * Update UI with current metrics
     */
    updateUI() {
        // Messages
        this.updateMetric('messages-total', this.metrics.messages.total.toLocaleString());
        this.updateMetric('messages-today', this.metrics.messages.today.toLocaleString());
        this.updateMetric('messages-week', this.metrics.messages.week.toLocaleString());
        this.updateMetric('messages-month', this.metrics.messages.month.toLocaleString());

        // Threads
        this.updateMetric('threads-total', this.metrics.threads.total.toLocaleString());
        this.updateMetric('threads-active', this.metrics.threads.active.toLocaleString());
        this.updateMetric('threads-archived', this.metrics.threads.archived.toLocaleString());
        const activeRate = this.metrics.threads.total > 0
            ? Math.round((this.metrics.threads.active / this.metrics.threads.total) * 100)
            : 0;
        this.updateMetric('threads-rate', `${activeRate}%`);

        // Tokens
        this.updateMetric('tokens-total', this.formatNumber(this.metrics.tokens.total));
        this.updateMetric('tokens-input', this.formatNumber(this.metrics.tokens.input));
        this.updateMetric('tokens-output', this.formatNumber(this.metrics.tokens.output));
        this.updateMetric('tokens-avg', this.metrics.tokens.avgPerMessage.toLocaleString());

        // Costs
        this.updateMetric('costs-total', this.formatCurrency(this.metrics.costs.total));
        this.updateMetric('costs-today', this.formatCurrency(this.metrics.costs.today));
        this.updateMetric('costs-week', this.formatCurrency(this.metrics.costs.week));
        this.updateMetric('costs-month', this.formatCurrency(this.metrics.costs.month));
        this.updateMetric('costs-avg', this.formatCurrency(this.metrics.costs.avgPerMessage));

        // Summary stats
        const messagesPerThread = this.metrics.threads.total > 0
            ? (this.metrics.messages.total / this.metrics.threads.total).toFixed(1)
            : 0;
        this.updateMetric('messages-per-thread', messagesPerThread);
        this.updateMetric('last-activity', new Date().toLocaleString('fr-FR'));
        this.updateMetric('analysis-period', 'Données complètes');
    }

    /**
     * Update individual metric in UI
     */
    updateMetric(name, value) {
        const element = this.container.querySelector(`[data-metric="${name}"]`);
        if (element) {
            element.textContent = value;
            element.classList.add('metric-updated');
            setTimeout(() => element.classList.remove('metric-updated'), 300);
        }
    }

    /**
     * Format large numbers with K/M suffixes
     */
    formatNumber(num) {
        if (num >= 1000000) {
            return (num / 1000000).toFixed(2) + 'M';
        }
        if (num >= 1000) {
            return (num / 1000).toFixed(1) + 'K';
        }
        return num.toLocaleString();
    }

    /**
     * Format currency values
     */
    formatCurrency(amount) {
        return `$${amount.toFixed(2)}`;
    }

    /**
     * Export metrics to JSON
     */
    exportMetrics() {
        const data = {
            exportDate: new Date().toISOString(),
            metrics: this.metrics
        };

        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `metrics-export-${Date.now()}.json`;
        a.click();
        URL.revokeObjectURL(url);

        this.showSuccess('Métriques exportées avec succès');
    }

    /**
     * Start auto-update interval
     */
    startAutoUpdate() {
        // Update every 5 minutes
        this.updateInterval = setInterval(() => {
            this.loadMetrics();
        }, 5 * 60 * 1000);
    }

    /**
     * Stop auto-update
     */
    stopAutoUpdate() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
            this.updateInterval = null;
        }
    }

    /**
     * Show success message
     */
    showSuccess(message) {
        // TODO: Integrate with global notification system
        console.log('✓', message);
    }

    /**
     * Show error message
     */
    showError(message) {
        // TODO: Integrate with global notification system
        console.error('✗', message);
    }

    /**
     * Cleanup
     */
    destroy() {
        this.stopAutoUpdate();
        if (this.container) {
            this.container.innerHTML = '';
        }
    }
}

// Export singleton instance
export const cockpitMetrics = new CockpitMetrics();
