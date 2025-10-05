/**
 * Settings Models Module
 * AI model configuration per agent with advanced parameters
 */

import { api } from '../../shared/api-client.js';

export class SettingsModels {
    constructor() {
        this.container = null;
        this.agents = [
            { id: 'orchestrator', name: 'Orchestrateur', icon: '🎯' },
            { id: 'researcher', name: 'Chercheur', icon: '🔍' },
            { id: 'developer', name: 'Développeur', icon: '💻' },
            { id: 'reviewer', name: 'Reviewer', icon: '👁️' },
            { id: 'tester', name: 'Testeur', icon: '🧪' }
        ];
        this.models = [
            { id: 'gpt-4', name: 'GPT-4', provider: 'OpenAI', cost: 0.03 },
            { id: 'gpt-4-turbo', name: 'GPT-4 Turbo', provider: 'OpenAI', cost: 0.01 },
            { id: 'gpt-3.5-turbo', name: 'GPT-3.5 Turbo', provider: 'OpenAI', cost: 0.002 },
            { id: 'claude-3-opus', name: 'Claude 3 Opus', provider: 'Anthropic', cost: 0.015 },
            { id: 'claude-3-sonnet', name: 'Claude 3 Sonnet', provider: 'Anthropic', cost: 0.003 },
            { id: 'claude-3-haiku', name: 'Claude 3 Haiku', provider: 'Anthropic', cost: 0.00025 },
            { id: 'gemini-pro', name: 'Gemini Pro', provider: 'Google', cost: 0.00025 },
            { id: 'gemini-ultra', name: 'Gemini Ultra', provider: 'Google', cost: 0.01 }
        ];
        this.settings = {};
    }

    /**
     * Initialize settings module
     */
    async init(containerId) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            console.error('Settings models container not found');
            return;
        }

        await this.loadSettings();
        this.render();
    }

    /**
     * Render settings UI
     */
    render() {
        this.container.innerHTML = `
            <div class="settings-models">
                <div class="settings-header">
                    <h2>🤖 Configuration des Modèles IA</h2>
                    <div class="header-actions">
                        <button class="btn-reset" title="Réinitialiser aux valeurs par défaut">
                            ↺ Réinitialiser
                        </button>
                        <button class="btn-save" title="Sauvegarder les modifications">
                            💾 Sauvegarder
                        </button>
                    </div>
                </div>

                <div class="settings-info">
                    <div class="info-card">
                        <span class="info-icon">ℹ️</span>
                        <div class="info-content">
                            <strong>Configuration par agent:</strong> Chaque agent peut utiliser un modèle différent
                            selon ses besoins (précision, vitesse, coût).
                        </div>
                    </div>
                </div>

                <div class="agents-config">
                    ${this.agents.map(agent => this.renderAgentConfig(agent)).join('')}
                </div>

                <div class="cost-estimate">
                    <h3>💰 Estimation des Coûts</h3>
                    <div class="cost-breakdown" id="cost-breakdown">
                        <div class="loading">Calcul en cours...</div>
                    </div>
                </div>
            </div>
        `;

        this.attachEventListeners();
        this.updateCostEstimate();
    }

    /**
     * Render agent configuration section
     */
    renderAgentConfig(agent) {
        const config = this.settings[agent.id] || this.getDefaultConfig();

        return `
            <div class="agent-config" data-agent="${agent.id}">
                <div class="agent-header">
                    <div class="agent-info">
                        <span class="agent-icon">${agent.icon}</span>
                        <h3>${agent.name}</h3>
                    </div>
                    <button class="btn-expand" data-expanded="true">
                        <span class="expand-icon">▼</span>
                    </button>
                </div>

                <div class="agent-settings">
                    <!-- Model Selection -->
                    <div class="setting-group">
                        <label class="setting-label">
                            <span class="label-text">Modèle IA</span>
                            <span class="label-hint">Sélectionnez le modèle pour cet agent</span>
                        </label>
                        <select class="model-select" data-agent="${agent.id}">
                            ${this.models.map(model => `
                                <option value="${model.id}" ${config.model === model.id ? 'selected' : ''}>
                                    ${model.name} (${model.provider}) - $${model.cost}/1k tokens
                                </option>
                            `).join('')}
                        </select>
                    </div>

                    <!-- Temperature -->
                    <div class="setting-group">
                        <label class="setting-label">
                            <span class="label-text">Temperature: <strong>${config.temperature}</strong></span>
                            <span class="label-hint">Contrôle la créativité (0 = déterministe, 1 = créatif)</span>
                        </label>
                        <input type="range" class="temperature-slider"
                               data-agent="${agent.id}"
                               min="0" max="1" step="0.1"
                               value="${config.temperature}">
                        <div class="slider-marks">
                            <span>0</span>
                            <span>0.5</span>
                            <span>1</span>
                        </div>
                    </div>

                    <!-- Max Tokens -->
                    <div class="setting-group">
                        <label class="setting-label">
                            <span class="label-text">Max Tokens</span>
                            <span class="label-hint">Nombre maximum de tokens par réponse</span>
                        </label>
                        <input type="number" class="max-tokens-input"
                               data-agent="${agent.id}"
                               min="100" max="32000" step="100"
                               value="${config.maxTokens}">
                    </div>

                    <!-- Top P -->
                    <div class="setting-group">
                        <label class="setting-label">
                            <span class="label-text">Top P: <strong>${config.topP}</strong></span>
                            <span class="label-hint">Nucleus sampling (0.1 = conservateur, 1 = varié)</span>
                        </label>
                        <input type="range" class="topp-slider"
                               data-agent="${agent.id}"
                               min="0.1" max="1" step="0.1"
                               value="${config.topP}">
                        <div class="slider-marks">
                            <span>0.1</span>
                            <span>0.5</span>
                            <span>1</span>
                        </div>
                    </div>

                    <!-- Frequency Penalty -->
                    <div class="setting-group">
                        <label class="setting-label">
                            <span class="label-text">Frequency Penalty: <strong>${config.frequencyPenalty}</strong></span>
                            <span class="label-hint">Pénalité pour répétitions (-2 à 2)</span>
                        </label>
                        <input type="range" class="frequency-slider"
                               data-agent="${agent.id}"
                               min="-2" max="2" step="0.1"
                               value="${config.frequencyPenalty}">
                        <div class="slider-marks">
                            <span>-2</span>
                            <span>0</span>
                            <span>2</span>
                        </div>
                    </div>

                    <!-- Presence Penalty -->
                    <div class="setting-group">
                        <label class="setting-label">
                            <span class="label-text">Presence Penalty: <strong>${config.presencePenalty}</strong></span>
                            <span class="label-hint">Pénalité pour nouveaux sujets (-2 à 2)</span>
                        </label>
                        <input type="range" class="presence-slider"
                               data-agent="${agent.id}"
                               min="-2" max="2" step="0.1"
                               value="${config.presencePenalty}">
                        <div class="slider-marks">
                            <span>-2</span>
                            <span>0</span>
                            <span>2</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Get default configuration
     */
    getDefaultConfig() {
        return {
            model: 'gpt-4',
            temperature: 0.7,
            maxTokens: 2000,
            topP: 0.9,
            frequencyPenalty: 0,
            presencePenalty: 0,
            systemPrompt: ''
        };
    }

    /**
     * Attach event listeners
     */
    attachEventListeners() {
        // Save button
        const saveBtn = this.container.querySelector('.btn-save');
        if (saveBtn) {
            saveBtn.addEventListener('click', () => this.saveSettings());
        }

        // Reset button
        const resetBtn = this.container.querySelector('.btn-reset');
        if (resetBtn) {
            resetBtn.addEventListener('click', () => this.resetSettings());
        }

        // Expand/collapse buttons
        this.container.querySelectorAll('.btn-expand').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const agentConfig = e.target.closest('.agent-config');
                const settings = agentConfig.querySelector('.agent-settings');
                const isExpanded = btn.dataset.expanded === 'true';

                if (isExpanded) {
                    settings.style.display = 'none';
                    btn.dataset.expanded = 'false';
                    btn.querySelector('.expand-icon').textContent = '▶';
                } else {
                    settings.style.display = 'block';
                    btn.dataset.expanded = 'true';
                    btn.querySelector('.expand-icon').textContent = '▼';
                }
            });
        });

        // Model selects
        this.container.querySelectorAll('.model-select').forEach(select => {
            select.addEventListener('change', (e) => {
                const agentId = e.target.dataset.agent;
                this.updateAgentSetting(agentId, 'model', e.target.value);
                this.updateCostEstimate();
            });
        });

        // Temperature sliders
        this.container.querySelectorAll('.temperature-slider').forEach(slider => {
            slider.addEventListener('input', (e) => {
                const agentId = e.target.dataset.agent;
                const value = parseFloat(e.target.value);
                this.updateAgentSetting(agentId, 'temperature', value);
                e.target.closest('.setting-group').querySelector('.label-text strong').textContent = value;
            });
        });

        // Max tokens inputs
        this.container.querySelectorAll('.max-tokens-input').forEach(input => {
            input.addEventListener('change', (e) => {
                const agentId = e.target.dataset.agent;
                this.updateAgentSetting(agentId, 'maxTokens', parseInt(e.target.value));
            });
        });

        // Top P sliders
        this.container.querySelectorAll('.topp-slider').forEach(slider => {
            slider.addEventListener('input', (e) => {
                const agentId = e.target.dataset.agent;
                const value = parseFloat(e.target.value);
                this.updateAgentSetting(agentId, 'topP', value);
                e.target.closest('.setting-group').querySelector('.label-text strong').textContent = value;
            });
        });

        // Frequency penalty sliders
        this.container.querySelectorAll('.frequency-slider').forEach(slider => {
            slider.addEventListener('input', (e) => {
                const agentId = e.target.dataset.agent;
                const value = parseFloat(e.target.value);
                this.updateAgentSetting(agentId, 'frequencyPenalty', value);
                e.target.closest('.setting-group').querySelector('.label-text strong').textContent = value;
            });
        });

        // Presence penalty sliders
        this.container.querySelectorAll('.presence-slider').forEach(slider => {
            slider.addEventListener('input', (e) => {
                const agentId = e.target.dataset.agent;
                const value = parseFloat(e.target.value);
                this.updateAgentSetting(agentId, 'presencePenalty', value);
                e.target.closest('.setting-group').querySelector('.label-text strong').textContent = value;
            });
        });
    }

    /**
     * Update agent setting
     */
    updateAgentSetting(agentId, key, value) {
        if (!this.settings[agentId]) {
            this.settings[agentId] = this.getDefaultConfig();
        }
        this.settings[agentId][key] = value;
    }

    /**
     * Update cost estimate
     */
    updateCostEstimate() {
        const breakdown = document.getElementById('cost-breakdown');
        if (!breakdown) return;

        const estimates = this.agents.map(agent => {
            const config = this.settings[agent.id] || this.getDefaultConfig();
            const model = this.models.find(m => m.id === config.model);
            const avgTokens = config.maxTokens * 0.7; // Assume 70% usage
            const costPer1k = model ? model.cost : 0;
            const estimatedCost = (avgTokens / 1000) * costPer1k;

            return {
                agent: agent.name,
                model: model ? model.name : 'Unknown',
                cost: estimatedCost
            };
        });

        const totalCost = estimates.reduce((sum, e) => sum + e.cost, 0);

        breakdown.innerHTML = `
            <div class="cost-table">
                <div class="cost-row cost-header">
                    <span>Agent</span>
                    <span>Modèle</span>
                    <span>Coût/requête</span>
                </div>
                ${estimates.map(e => `
                    <div class="cost-row">
                        <span>${e.agent}</span>
                        <span>${e.model}</span>
                        <span class="cost-value">$${e.cost.toFixed(4)}</span>
                    </div>
                `).join('')}
                <div class="cost-row cost-total">
                    <span>Total estimé/requête</span>
                    <span></span>
                    <span class="cost-value">$${totalCost.toFixed(4)}</span>
                </div>
            </div>
        `;
    }

    /**
     * Load settings from storage
     */
    async loadSettings() {
        try {
            const response = await api.request('/api/settings/models');
            this.settings = response || {};
        } catch (error) {
            console.error('Error loading settings:', error);
            this.settings = {};
        }
    }

    /**
     * Save settings
     */
    async saveSettings() {
        try {
            await api.request('/api/settings/models', {
                method: 'POST',
                body: JSON.stringify(this.settings)
            });
            this.showSuccess('Configuration sauvegardée avec succès');
        } catch (error) {
            console.error('Error saving settings:', error);
            this.showError('Erreur lors de la sauvegarde');
        }
    }

    /**
     * Reset to default settings
     */
    resetSettings() {
        if (!confirm('Réinitialiser tous les paramètres aux valeurs par défaut ?')) {
            return;
        }

        this.settings = {};
        this.agents.forEach(agent => {
            this.settings[agent.id] = this.getDefaultConfig();
        });

        this.render();
        this.showSuccess('Paramètres réinitialisés');
    }

    /**
     * Show success message
     */
    showSuccess(message) {
        console.log('✓', message);
        // TODO: Integrate with notification system
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
        if (this.container) {
            this.container.innerHTML = '';
        }
    }
}

// Export singleton instance
export const settingsModels = new SettingsModels();
