/**
 * Settings RAG Module
 * RAG system configuration (strict mode, score threshold)
 */

import { SettingsIcons, getIcon } from './settings-icons.js';
import { api } from '../../shared/api-client.js';

export class SettingsRAG {
    constructor() {
        this.container = null;
        this.settings = {
            strictMode: false,
            scoreThreshold: 0.7
        };
    }

    /**
     * Initialize RAG settings module
     */
    async init(containerId) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            console.error('Settings RAG container not found');
            return;
        }

        await this.loadSettings();
        this.render();
    }

    /**
     * Render RAG settings UI
     */
    render() {
        this.container.innerHTML = `
            <div class="settings-rag">
                <div class="settings-header">
                    <h2>${getIcon('database', 'header-icon')} Configuration RAG (Recherche Sémantique)</h2>
                    <div class="header-actions">
                        <button class="btn-reset" title="Réinitialiser aux valeurs par défaut">
                            ${getIcon('reset', 'btn-icon')} Réinitialiser
                        </button>
                        <button class="btn-save" title="Sauvegarder les modifications">
                            ${getIcon('save', 'btn-icon')} Sauvegarder
                        </button>
                    </div>
                </div>

                <div class="settings-info">
                    <div class="info-card">
                        <span class="info-icon">${SettingsIcons.info}</span>
                        <div class="info-content">
                            <strong>RAG Hybride:</strong> Le système combine recherche vectorielle et recherche par mots-clés
                            pour fournir les contextes les plus pertinents aux agents IA.
                        </div>
                    </div>
                </div>

                <div class="rag-config">
                    <!-- Strict Mode Toggle -->
                    <div class="setting-group toggle-group">
                        <div class="setting-header">
                            <label class="setting-label">
                                <span class="label-text">Mode RAG Strict</span>
                                <span class="label-hint">Active uniquement les résultats au-dessus du seuil de score</span>
                            </label>
                            <label class="toggle-switch">
                                <input type="checkbox" id="strict-mode-toggle"
                                       ${this.settings.strictMode ? 'checked' : ''}>
                                <span class="toggle-slider"></span>
                            </label>
                        </div>
                        <div class="setting-description">
                            ${this.settings.strictMode
                                ? '<span class="status-active">✓ Mode strict activé - seuls les résultats de haute qualité sont utilisés</span>'
                                : '<span class="status-inactive">Mode flexible - tous les résultats sont considérés</span>'
                            }
                        </div>
                    </div>

                    <!-- Score Threshold Slider -->
                    <div class="setting-group ${this.settings.strictMode ? '' : 'disabled'}">
                        <label class="setting-label">
                            <span class="label-text">Seuil de Score de Similarité: <strong>${this.settings.scoreThreshold}</strong></span>
                            <span class="label-hint">Score minimum pour qu'un résultat soit considéré pertinent (0.0 - 1.0)</span>
                        </label>
                        <input type="range" id="score-threshold-slider"
                               min="0" max="1" step="0.05"
                               value="${this.settings.scoreThreshold}"
                               ${this.settings.strictMode ? '' : 'disabled'}>
                        <div class="slider-marks">
                            <span>0.0<br><small>Permissif</small></span>
                            <span>0.5<br><small>Équilibré</small></span>
                            <span>1.0<br><small>Strict</small></span>
                        </div>
                        <div class="threshold-explanation">
                            ${this.getThresholdExplanation(this.settings.scoreThreshold)}
                        </div>
                    </div>

                    <!-- RAG System Info -->
                    <div class="rag-system-info">
                        <h3>${getIcon('info', 'section-icon')} Fonctionnement du RAG Hybride</h3>
                        <div class="info-sections">
                            <div class="info-section">
                                <h4>🔍 Recherche Vectorielle</h4>
                                <p>Utilise des embeddings pour trouver des documents sémantiquement similaires, même avec des mots différents.</p>
                            </div>
                            <div class="info-section">
                                <h4>📝 Recherche par Mots-clés (BM25)</h4>
                                <p>Recherche basée sur la correspondance exacte des termes pour une précision lexicale.</p>
                            </div>
                            <div class="info-section">
                                <h4>⚖️ Fusion des Résultats</h4>
                                <p>Combine les deux méthodes avec Reciprocal Rank Fusion (RRF) pour des résultats optimaux.</p>
                            </div>
                        </div>
                    </div>

                    <!-- Metrics Preview -->
                    <div class="metrics-preview">
                        <h3>${getIcon('activity', 'section-icon')} Métriques RAG (Live)</h3>
                        <div class="metrics-grid" id="rag-metrics-grid">
                            <div class="metric-card">
                                <span class="metric-label">Requêtes hybrides</span>
                                <span class="metric-value" id="metric-hybrid-queries">-</span>
                            </div>
                            <div class="metric-card">
                                <span class="metric-label">Score moyen</span>
                                <span class="metric-value" id="metric-avg-score">-</span>
                            </div>
                            <div class="metric-card">
                                <span class="metric-label">Résultats filtrés</span>
                                <span class="metric-value" id="metric-filtered">-</span>
                            </div>
                            <div class="metric-card">
                                <span class="metric-label">Taux de succès</span>
                                <span class="metric-value" id="metric-success-rate">-</span>
                            </div>
                        </div>
                        <button class="btn-refresh-metrics" id="btn-refresh-metrics">
                            ${getIcon('refresh', 'btn-icon')} Actualiser les métriques
                        </button>
                    </div>
                </div>
            </div>
        `;

        this.attachEventListeners();
        this.loadMetrics();
    }

    /**
     * Get explanation for threshold value
     */
    getThresholdExplanation(threshold) {
        if (threshold >= 0.8) {
            return `
                <div class="explanation strict">
                    <strong>Très strict:</strong> Seuls les résultats hautement pertinents sont acceptés.
                    Peut réduire le nombre de contextes disponibles mais garantit une haute qualité.
                </div>
            `;
        } else if (threshold >= 0.6) {
            return `
                <div class="explanation balanced">
                    <strong>Équilibré:</strong> Bon compromis entre qualité et quantité de résultats.
                    Recommandé pour la plupart des cas d'usage.
                </div>
            `;
        } else {
            return `
                <div class="explanation permissive">
                    <strong>Permissif:</strong> Accepte un large éventail de résultats.
                    Utile pour exploration ou quand peu de données correspondent exactement.
                </div>
            `;
        }
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

        // Strict mode toggle
        const strictToggle = document.getElementById('strict-mode-toggle');
        if (strictToggle) {
            strictToggle.addEventListener('change', (e) => {
                this.settings.strictMode = e.target.checked;
                this.updateStrictModeUI();
            });
        }

        // Score threshold slider
        const thresholdSlider = document.getElementById('score-threshold-slider');
        if (thresholdSlider) {
            thresholdSlider.addEventListener('input', (e) => {
                const value = parseFloat(e.target.value);
                this.settings.scoreThreshold = value;
                this.updateThresholdUI(value);
            });
        }

        // Refresh metrics button
        const refreshBtn = document.getElementById('btn-refresh-metrics');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.loadMetrics());
        }
    }

    /**
     * Update strict mode UI state
     */
    updateStrictModeUI() {
        const slider = document.getElementById('score-threshold-slider');
        const settingGroup = slider?.closest('.setting-group');
        const description = this.container.querySelector('.setting-description');

        if (this.settings.strictMode) {
            settingGroup?.classList.remove('disabled');
            slider?.removeAttribute('disabled');
            if (description) {
                description.innerHTML = '<span class="status-active">✓ Mode strict activé - seuls les résultats de haute qualité sont utilisés</span>';
            }
        } else {
            settingGroup?.classList.add('disabled');
            slider?.setAttribute('disabled', 'disabled');
            if (description) {
                description.innerHTML = '<span class="status-inactive">Mode flexible - tous les résultats sont considérés</span>';
            }
        }
    }

    /**
     * Update threshold UI
     */
    updateThresholdUI(value) {
        const label = this.container.querySelector('.label-text strong');
        if (label) {
            label.textContent = value.toFixed(2);
        }

        const explanation = this.container.querySelector('.threshold-explanation');
        if (explanation) {
            explanation.innerHTML = this.getThresholdExplanation(value);
        }
    }

    /**
     * Load RAG metrics from Prometheus/API
     */
    async loadMetrics() {
        try {
            const response = await api.request('/api/metrics/rag');

            if (response) {
                this.updateMetric('metric-hybrid-queries', response.hybrid_queries_total || 0);
                this.updateMetric('metric-avg-score', (response.avg_score || 0).toFixed(3));
                this.updateMetric('metric-filtered', response.filtered_results || 0);

                const successRate = response.hybrid_queries_total > 0
                    ? ((response.successful_queries || 0) / response.hybrid_queries_total * 100).toFixed(1)
                    : '0.0';
                this.updateMetric('metric-success-rate', `${successRate}%`);
            }
        } catch (error) {
            console.error('Error loading RAG metrics:', error);
            // Show placeholder values
            this.updateMetric('metric-hybrid-queries', 'N/A');
            this.updateMetric('metric-avg-score', 'N/A');
            this.updateMetric('metric-filtered', 'N/A');
            this.updateMetric('metric-success-rate', 'N/A');
        }
    }

    /**
     * Update individual metric display
     */
    updateMetric(elementId, value) {
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = value;
        }
    }

    /**
     * Load settings from storage/API
     */
    async loadSettings() {
        try {
            const response = await api.request('/api/settings/rag');
            if (response) {
                this.settings = {
                    strictMode: response.strict_mode || false,
                    scoreThreshold: response.score_threshold || 0.7
                };
            }
        } catch (error) {
            console.error('Error loading RAG settings:', error);
            // Use defaults
            this.settings = {
                strictMode: false,
                scoreThreshold: 0.7
            };
        }
    }

    /**
     * Save settings to API
     */
    async saveSettings() {
        const saveBtn = this.container.querySelector('.btn-save');
        if (saveBtn) {
            saveBtn.disabled = true;
            saveBtn.innerHTML = '⏳ Sauvegarde...';
        }

        try {
            await api.request('/api/settings/rag', {
                method: 'POST',
                body: {
                    strict_mode: this.settings.strictMode,
                    score_threshold: this.settings.scoreThreshold
                }
            });

            this.showSuccess('Configuration RAG sauvegardée avec succès');

            if (saveBtn) {
                saveBtn.innerHTML = '✓ Sauvegardé';
                setTimeout(() => {
                    saveBtn.innerHTML = `${getIcon('save', 'btn-icon')} Sauvegarder`;
                    saveBtn.disabled = false;
                }, 2000);
            }
        } catch (error) {
            console.error('Error saving RAG settings:', error);
            this.showError('Erreur lors de la sauvegarde');

            if (saveBtn) {
                saveBtn.innerHTML = '✗ Erreur';
                saveBtn.disabled = false;
            }
        }
    }

    /**
     * Reset to default settings
     */
    resetSettings() {
        if (!confirm('Réinitialiser les paramètres RAG aux valeurs par défaut ?')) {
            return;
        }

        this.settings = {
            strictMode: false,
            scoreThreshold: 0.7
        };

        this.render();
        this.showSuccess('Paramètres RAG réinitialisés');
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
export const settingsRAG = new SettingsRAG();
