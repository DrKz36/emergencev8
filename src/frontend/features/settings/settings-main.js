/**
 * Settings Main Module
 * Integrates all settings components (models, UI, security)
 */

import { settingsModels } from './settings-models.js';
import { settingsUI } from './settings-ui.js';
import { settingsSecurity } from './settings-security.js';

export class Settings {
    constructor() {
        this.container = null;
        this.activeTab = 'models';
        this.modules = {
            models: settingsModels,
            ui: settingsUI,
            security: settingsSecurity
        };
        this.initialized = false;
        this.hasUnsavedChanges = false;
    }

    /**
     * Initialize settings
     */
    async init(containerId) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            console.error('Settings container not found');
            return;
        }

        this.render();
        await this.loadActiveView();
        this.initialized = true;
    }

    /**
     * Render settings structure
     */
    render() {
        this.container.innerHTML = `
            <div class="settings-container">
                <!-- Settings Header -->
                <div class="settings-main-header">
                    <div class="settings-title">
                        <h1>⚙️ Paramètres</h1>
                        <p class="settings-subtitle">Configuration et personnalisation</p>
                    </div>
                    <div class="settings-actions">
                        <button class="btn-reset-all" title="Tout réinitialiser">
                            ↺ Réinitialiser tout
                        </button>
                        <button class="btn-save-all" title="Tout sauvegarder">
                            💾 Tout sauvegarder
                        </button>
                    </div>
                </div>

                <!-- ÉMERGENCE Brand Panel -->
                <div class="emergence-brand-panel">
                    <img src="/assets/emergence_logo.png" alt="ÉMERGENCE" class="brand-logo">
                    <div class="brand-info">
                        <h2 class="brand-title">ÉMERGENCE V8</h2>
                        <p class="brand-version">Version 8.0.0</p>
                    </div>
                </div>

                <!-- Settings Navigation -->
                <div class="settings-nav">
                    <button class="settings-nav-item ${this.activeTab === 'models' ? 'active' : ''}"
                            data-tab="models">
                        <span class="nav-icon">🤖</span>
                        <div class="nav-content">
                            <span class="nav-label">Modèles IA</span>
                            <span class="nav-hint">Configuration des agents</span>
                        </div>
                    </button>
                    <button class="settings-nav-item ${this.activeTab === 'ui' ? 'active' : ''}"
                            data-tab="ui">
                        <span class="nav-icon">🎨</span>
                        <div class="nav-content">
                            <span class="nav-label">Interface</span>
                            <span class="nav-hint">Thème et apparence</span>
                        </div>
                    </button>
                    <button class="settings-nav-item ${this.activeTab === 'about' ? 'active' : ''}"
                            data-tab="about">
                        <span class="nav-icon">ℹ️</span>
                        <div class="nav-content">
                            <span class="nav-label">À propos</span>
                            <span class="nav-hint">Version et informations</span>
                        </div>
                    </button>
                </div>

                <!-- Settings Content -->
                <div class="settings-main-content">
                    <!-- Models Tab -->
                    <div class="settings-panel ${this.activeTab === 'models' ? 'active' : ''}"
                         data-panel="models">
                        <div id="settings-models-container"></div>
                    </div>

                    <!-- UI Tab -->
                    <div class="settings-panel ${this.activeTab === 'ui' ? 'active' : ''}"
                         data-panel="ui">
                        <div id="settings-ui-container"></div>
                    </div>

                    <!-- About Tab -->
                    <div class="settings-panel ${this.activeTab === 'about' ? 'active' : ''}"
                         data-panel="about">
                        <div id="settings-about-container">
                            ${this.renderAbout()}
                        </div>
                    </div>
                </div>

                <!-- Unsaved Changes Warning -->
                ${this.hasUnsavedChanges ? `
                    <div class="unsaved-changes-bar">
                        <span class="unsaved-icon">⚠️</span>
                        <span class="unsaved-text">Vous avez des modifications non sauvegardées</span>
                        <div class="unsaved-actions">
                            <button class="btn-discard">Annuler</button>
                            <button class="btn-save-changes">Sauvegarder</button>
                        </div>
                    </div>
                ` : ''}
            </div>
        `;

        this.attachEventListeners();
    }

    /**
     * Render about section
     */
    renderAbout() {
        return `
            <div class="settings-about">
                <div class="about-sections">
                    <div class="about-section">
                        <h3>📋 Informations Système</h3>
                        <div class="about-info-grid">
                            <div class="info-item">
                                <span class="info-label">Version:</span>
                                <span class="info-value">8.0.0</span>
                            </div>
                            <div class="info-item">
                                <span class="info-label">Build:</span>
                                <span class="info-value">${Date.now()}</span>
                            </div>
                            <div class="info-item">
                                <span class="info-label">Modules:</span>
                                <span class="info-value">Dashboard, Memory, Settings</span>
                            </div>
                            <div class="info-item">
                                <span class="info-label">Navigateur:</span>
                                <span class="info-value">${navigator.userAgent.split(' ').pop()}</span>
                            </div>
                        </div>
                    </div>

                    <div class="about-section">
                        <h3>🔗 Liens Utiles</h3>
                        <div class="about-links">
                            <a href="#" class="about-link">📚 Documentation</a>
                            <a href="#" class="about-link">💬 Support</a>
                            <a href="#" class="about-link">🐛 Signaler un bug</a>
                            <a href="#" class="about-link">⭐ GitHub</a>
                        </div>
                    </div>

                    <div class="about-section">
                        <h3>📦 Modules Installés</h3>
                        <div class="modules-list">
                            <div class="module-item">
                                <span class="module-icon">📊</span>
                                <div class="module-info">
                                    <span class="module-name">Dashboard</span>
                                    <span class="module-version">v3.0</span>
                                </div>
                                <span class="module-status status-active">✓</span>
                            </div>
                            <div class="module-item">
                                <span class="module-icon">🧠</span>
                                <div class="module-info">
                                    <span class="module-name">Memory System</span>
                                    <span class="module-version">v2.0</span>
                                </div>
                                <span class="module-status status-active">✓</span>
                            </div>
                            <div class="module-item">
                                <span class="module-icon">⚙️</span>
                                <div class="module-info">
                                    <span class="module-name">Settings</span>
                                    <span class="module-version">v4.0</span>
                                </div>
                                <span class="module-status status-active">✓</span>
                            </div>
                        </div>
                    </div>

                    <div class="about-section">
                        <h3>📜 Licence & Crédits</h3>
                        <p class="about-text">
                            ÉMERGENCE est une plateforme de gestion multi-agents développée
                            pour orchestrer des systèmes d'IA complexes.
                        </p>
                        <p class="about-credits">
                            Développé par Fernando Gonzalez avec acharnement et résilience et surtout le soutien indéfectible de son magnifique et charmante épouse Marem
                        </p>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Attach event listeners
     */
    attachEventListeners() {
        // Navigation tabs
        this.container.querySelectorAll('.settings-nav-item').forEach(item => {
            item.addEventListener('click', (e) => {
                const tab = e.currentTarget.dataset.tab;
                this.switchTab(tab);
            });
        });

        // Save all button
        const saveAllBtn = this.container.querySelector('.btn-save-all');
        if (saveAllBtn) {
            saveAllBtn.addEventListener('click', () => this.saveAll());
        }

        // Reset all button
        const resetAllBtn = this.container.querySelector('.btn-reset-all');
        if (resetAllBtn) {
            resetAllBtn.addEventListener('click', () => this.resetAll());
        }
    }

    /**
     * Switch active tab
     */
    async switchTab(tabName) {
        this.activeTab = tabName;

        // Update navigation
        this.container.querySelectorAll('.settings-nav-item').forEach(item => {
            item.classList.toggle('active', item.dataset.tab === tabName);
        });

        // Update panels
        this.container.querySelectorAll('.settings-panel').forEach(panel => {
            panel.classList.toggle('active', panel.dataset.panel === tabName);
        });

        // Load content for active tab
        await this.loadActiveView();
    }

    /**
     * Load content for active view
     */
    async loadActiveView() {
        switch (this.activeTab) {
            case 'models':
                await this.modules.models.init('settings-models-container');
                break;
            case 'ui':
                await this.modules.ui.init('settings-ui-container');
                break;
            case 'about':
                // About is static, no initialization needed
                break;
        }
    }

    /**
     * Save all settings
     */
    async saveAll() {
        const saveAllBtn = this.container.querySelector('.btn-save-all');
        if (saveAllBtn) {
            saveAllBtn.disabled = true;
            saveAllBtn.innerHTML = '⏳ Sauvegarde...';
        }

        try {
            await Promise.all([
                this.modules.models.saveSettings(),
                this.modules.ui.saveSettings()
            ]);

            this.hasUnsavedChanges = false;
            this.showNotification('Tous les paramètres ont été sauvegardés', 'success');

            if (saveAllBtn) {
                saveAllBtn.innerHTML = '✓ Sauvegardé';
                setTimeout(() => {
                    saveAllBtn.innerHTML = '💾 Tout sauvegarder';
                    saveAllBtn.disabled = false;
                }, 2000);
            }
        } catch (error) {
            console.error('Error saving settings:', error);
            this.showNotification('Erreur lors de la sauvegarde', 'error');

            if (saveAllBtn) {
                saveAllBtn.innerHTML = '✗ Erreur';
                saveAllBtn.disabled = false;
            }
        }
    }

    /**
     * Reset all settings
     */
    async resetAll() {
        if (!confirm('⚠️ Réinitialiser TOUS les paramètres ? Cette action est irréversible.')) {
            return;
        }

        try {
            await Promise.all([
                this.modules.models.resetSettings(),
                this.modules.ui.resetSettings()
            ]);

            this.hasUnsavedChanges = false;
            this.showNotification('Tous les paramètres ont été réinitialisés', 'success');

            // Reload active view
            await this.loadActiveView();
        } catch (error) {
            console.error('Error resetting settings:', error);
            this.showNotification('Erreur lors de la réinitialisation', 'error');
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
     * Destroy settings
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
export const settings = new Settings();
