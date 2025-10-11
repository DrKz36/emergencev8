/**
 * Cockpit Agents Module
 * Displays agent-specific costs, usage, and models
 */

import { getIcon } from './cockpit-icons.js';

export class CockpitAgents {
    constructor() {
        this.container = null;
        this.agentsData = [];
        this.updateInterval = null;
    }

    /**
     * Initialize agents module
     */
    async init(containerId) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            console.error('Cockpit agents container not found');
            return;
        }

        this.render();
        await this.loadAgentsData();
        this.startAutoUpdate();
    }

    /**
     * Render agents UI structure
     */
    render() {
        this.container.innerHTML = `
            <div class="cockpit-agents">
                <div class="agents-header">
                    <h2>${getIcon('robot')} Agents & Modèles</h2>
                    <div class="agents-actions">
                        <button class="btn-refresh" title="Actualiser">
                            <span class="icon">${getIcon('refresh')}</span>
                            Actualiser
                        </button>
                    </div>
                </div>

                <div class="agents-grid" id="agents-grid">
                    <div class="loading">Chargement des données...</div>
                </div>

                <div class="agents-summary">
                    <h3>Résumé</h3>
                    <div class="summary-grid" id="summary-grid">
                        <div class="summary-card">
                            <span class="summary-label">Coût total</span>
                            <span class="summary-value" id="total-cost">$0.00</span>
                        </div>
                        <div class="summary-card">
                            <span class="summary-label">Total tokens</span>
                            <span class="summary-value" id="total-tokens">0</span>
                        </div>
                        <div class="summary-card">
                            <span class="summary-label">Total requêtes</span>
                            <span class="summary-value" id="total-requests">0</span>
                        </div>
                        <div class="summary-card">
                            <span class="summary-label">Coût moyen/requête</span>
                            <span class="summary-value" id="avg-cost">$0.00</span>
                        </div>
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
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.loadAgentsData());
        }
    }

    /**
     * Load agents data from API
     */
    async loadAgentsData() {
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

            const response = await fetch('/api/dashboard/costs/by-agent', {
                method: 'GET',
                headers: headers
            });

            if (!response.ok) {
                throw new Error(`API error: ${response.status}`);
            }

            this.agentsData = await response.json();
            this.updateUI();
        } catch (error) {
            console.error('Error loading agents data:', error);
            this.showError('Impossible de charger les données des agents');
        }
    }

    /**
     * Update UI with agents data
     */
    updateUI() {
        const agentsGrid = document.getElementById('agents-grid');
        if (!agentsGrid) return;

        if (this.agentsData.length === 0) {
            agentsGrid.innerHTML = '<div class="no-data">Aucune donnée disponible</div>';
            this.updateSummary();
            return;
        }

        // Group by agent (sum across models)
        const agentGroups = {};
        this.agentsData.forEach(item => {
            if (!agentGroups[item.agent]) {
                agentGroups[item.agent] = {
                    agent: item.agent,
                    models: [],
                    totalCost: 0,
                    totalInputTokens: 0,
                    totalOutputTokens: 0,
                    totalRequests: 0
                };
            }
            agentGroups[item.agent].models.push({
                model: item.model,
                cost: item.total_cost,
                inputTokens: item.input_tokens,
                outputTokens: item.output_tokens,
                requests: item.request_count
            });
            agentGroups[item.agent].totalCost += item.total_cost;
            agentGroups[item.agent].totalInputTokens += item.input_tokens;
            agentGroups[item.agent].totalOutputTokens += item.output_tokens;
            agentGroups[item.agent].totalRequests += item.request_count;
        });

        // Render agent cards
        const html = Object.values(agentGroups).map(group => this.renderAgentCard(group)).join('');
        agentsGrid.innerHTML = html;

        // Update summary
        this.updateSummary();
    }

    /**
     * Render individual agent card
     */
    renderAgentCard(group) {
        const agentIcons = {
            'Anima': getIcon('target'),
            'Neo': getIcon('eye'),
            'Nexus': getIcon('settings'),
            'User': getIcon('user'),
            'System': getIcon('settings')
        };

        const icon = agentIcons[group.agent] || getIcon('robot');
        const totalTokens = group.totalInputTokens + group.totalOutputTokens;
        const avgCost = group.totalRequests > 0 ? group.totalCost / group.totalRequests : 0;

        return `
            <div class="agent-card">
                <div class="agent-card-header">
                    <div class="agent-info">
                        <span class="agent-icon">${icon}</span>
                        <h3 class="agent-name">${group.agent}</h3>
                    </div>
                    <div class="agent-cost">
                        <span class="cost-value">$${group.totalCost.toFixed(4)}</span>
                    </div>
                </div>

                <div class="agent-stats">
                    <div class="stat">
                        <span class="stat-label">Requêtes</span>
                        <span class="stat-value">${group.totalRequests.toLocaleString()}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Tokens</span>
                        <span class="stat-value">${this.formatNumber(totalTokens)}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Input</span>
                        <span class="stat-value">${this.formatNumber(group.totalInputTokens)}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Output</span>
                        <span class="stat-value">${this.formatNumber(group.totalOutputTokens)}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Coût/req</span>
                        <span class="stat-value">$${avgCost.toFixed(4)}</span>
                    </div>
                </div>

                <div class="agent-models">
                    <h4>Modèles utilisés</h4>
                    <div class="models-list">
                        ${group.models.map(model => `
                            <div class="model-item">
                                <div class="model-info">
                                    <span class="model-name">${model.model}</span>
                                    <span class="model-requests">${model.requests} req</span>
                                </div>
                                <div class="model-cost">$${model.cost.toFixed(4)}</div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Update summary statistics
     */
    updateSummary() {
        const totalCost = this.agentsData.reduce((sum, item) => sum + item.total_cost, 0);
        const totalTokens = this.agentsData.reduce((sum, item) => sum + item.input_tokens + item.output_tokens, 0);
        const totalRequests = this.agentsData.reduce((sum, item) => sum + item.request_count, 0);
        const avgCost = totalRequests > 0 ? totalCost / totalRequests : 0;

        this.updateElement('total-cost', `$${totalCost.toFixed(2)}`);
        this.updateElement('total-tokens', this.formatNumber(totalTokens));
        this.updateElement('total-requests', totalRequests.toLocaleString());
        this.updateElement('avg-cost', `$${avgCost.toFixed(4)}`);
    }

    /**
     * Update element text
     */
    updateElement(id, value) {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
        }
    }

    /**
     * Format large numbers
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
     * Get auth token
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
     * Get session ID
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
     * Start auto-update interval
     */
    startAutoUpdate() {
        // Update every 5 minutes
        this.updateInterval = setInterval(() => {
            this.loadAgentsData();
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
     * Show error message
     */
    showError(message) {
        console.error('✗', message);
        // TODO: Integrate with notification system
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
export const cockpitAgents = new CockpitAgents();
