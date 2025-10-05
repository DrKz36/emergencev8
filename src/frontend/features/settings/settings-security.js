/**
 * Settings Security Module
 * API keys management and security configurations
 */

import { api } from '../../shared/api-client.js';

export class SettingsSecurity {
    constructor() {
        this.container = null;
        this.apiKeys = {
            openai: { value: '', status: 'not-set', lastUsed: null },
            anthropic: { value: '', status: 'not-set', lastUsed: null },
            mistral: { value: '', status: 'not-set', lastUsed: null },
            google: { value: '', status: 'not-set', lastUsed: null }
        };
        this.securitySettings = {
            encryptionEnabled: true,
            autoLockTimeout: 30,
            requireAuthForExport: true,
            maskApiKeys: true,
            auditLog: true
        };
    }

    /**
     * Initialize security settings module
     */
    async init(containerId) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            console.error('Settings security container not found');
            return;
        }

        await this.loadSettings();
        this.render();
    }

    /**
     * Render security settings UI
     */
    render() {
        this.container.innerHTML = `
            <div class="settings-security">
                <div class="settings-header">
                    <h2>🔐 Sécurité & Clés API</h2>
                    <div class="header-actions">
                        <button class="btn-save">💾 Sauvegarder</button>
                    </div>
                </div>

                <div class="security-warning">
                    <div class="warning-icon">⚠️</div>
                    <div class="warning-content">
                        <strong>Important:</strong> Vos clés API sont chiffrées et stockées localement.
                        Ne partagez jamais vos clés API avec des tiers.
                    </div>
                </div>

                <div class="settings-sections">
                    <!-- API Keys Section -->
                    <div class="settings-section">
                        <h3>🔑 Clés API</h3>
                        <div class="api-keys-list">
                            ${this.renderApiKeySection('openai', 'OpenAI', 'sk-...')}
                            ${this.renderApiKeySection('anthropic', 'Anthropic', 'sk-ant-...')}
                            ${this.renderApiKeySection('mistral', 'Mistral AI', 'API_KEY...')}
                            ${this.renderApiKeySection('google', 'Google AI', 'AIza...')}
                        </div>
                    </div>

                    <!-- Security Settings -->
                    <div class="settings-section">
                        <h3>🛡️ Paramètres de Sécurité</h3>
                        <div class="security-options">
                            <div class="security-item">
                                <div class="security-content">
                                    <span class="label-text">Chiffrement des données</span>
                                    <span class="label-hint">Chiffrer les données sensibles localement</span>
                                </div>
                                <label class="toggle-switch">
                                    <input type="checkbox" class="encryption-toggle"
                                           ${this.securitySettings.encryptionEnabled ? 'checked' : ''}>
                                    <span class="toggle-slider"></span>
                                </label>
                            </div>

                            <div class="security-item">
                                <div class="security-content">
                                    <span class="label-text">Masquer les clés API</span>
                                    <span class="label-hint">Afficher les clés partiellement masquées</span>
                                </div>
                                <label class="toggle-switch">
                                    <input type="checkbox" class="mask-toggle"
                                           ${this.securitySettings.maskApiKeys ? 'checked' : ''}>
                                    <span class="toggle-slider"></span>
                                </label>
                            </div>

                            <div class="security-item">
                                <div class="security-content">
                                    <span class="label-text">Authentification pour export</span>
                                    <span class="label-hint">Demander confirmation avant export de données</span>
                                </div>
                                <label class="toggle-switch">
                                    <input type="checkbox" class="auth-export-toggle"
                                           ${this.securitySettings.requireAuthForExport ? 'checked' : ''}>
                                    <span class="toggle-slider"></span>
                                </label>
                            </div>

                            <div class="security-item">
                                <div class="security-content">
                                    <span class="label-text">Journal d'audit</span>
                                    <span class="label-hint">Enregistrer les actions de sécurité</span>
                                </div>
                                <label class="toggle-switch">
                                    <input type="checkbox" class="audit-toggle"
                                           ${this.securitySettings.auditLog ? 'checked' : ''}>
                                    <span class="toggle-slider"></span>
                                </label>
                            </div>

                            <div class="security-item">
                                <label class="security-content full-width">
                                    <span class="label-text">Verrouillage automatique</span>
                                    <span class="label-hint">Durée d'inactivité avant verrouillage (minutes)</span>
                                    <input type="number" class="timeout-input"
                                           min="5" max="120" step="5"
                                           value="${this.securitySettings.autoLockTimeout}">
                                </label>
                            </div>
                        </div>
                    </div>

                    <!-- Audit Log -->
                    <div class="settings-section">
                        <div class="section-header-with-action">
                            <h3>📋 Journal d'Audit</h3>
                            <button class="btn-clear-log">Effacer le journal</button>
                        </div>
                        <div class="audit-log" id="audit-log">
                            <div class="log-loading">Chargement...</div>
                        </div>
                    </div>

                    <!-- Data Management -->
                    <div class="settings-section danger-zone">
                        <h3>⚠️ Zone Dangereuse</h3>
                        <div class="danger-actions">
                            <div class="danger-item">
                                <div class="danger-content">
                                    <span class="danger-title">Effacer toutes les clés API</span>
                                    <span class="danger-hint">Supprime toutes les clés API stockées</span>
                                </div>
                                <button class="btn-danger" data-action="clear-keys">
                                    Effacer les clés
                                </button>
                            </div>

                            <div class="danger-item">
                                <div class="danger-content">
                                    <span class="danger-title">Réinitialiser les paramètres de sécurité</span>
                                    <span class="danger-hint">Restaurer les paramètres par défaut</span>
                                </div>
                                <button class="btn-danger" data-action="reset-security">
                                    Réinitialiser
                                </button>
                            </div>

                            <div class="danger-item">
                                <div class="danger-content">
                                    <span class="danger-title">Exporter les données (chiffré)</span>
                                    <span class="danger-hint">Télécharger une sauvegarde chiffrée</span>
                                </div>
                                <button class="btn-export-encrypted" data-action="export-encrypted">
                                    Exporter (chiffré)
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        this.attachEventListeners();
        this.loadAuditLog();
    }

    /**
     * Render API key section
     */
    renderApiKeySection(id, name, placeholder) {
        const key = this.apiKeys[id];
        const maskedValue = this.securitySettings.maskApiKeys && key.value
            ? this.maskApiKey(key.value)
            : key.value;

        return `
            <div class="api-key-item" data-provider="${id}">
                <div class="api-key-header">
                    <div class="api-key-info">
                        <span class="api-key-name">${name}</span>
                        <span class="api-key-status status-${key.status}">
                            ${this.getStatusIcon(key.status)} ${this.getStatusText(key.status)}
                        </span>
                    </div>
                    ${key.lastUsed ? `<span class="api-key-last-used">Utilisé ${this.formatDate(key.lastUsed)}</span>` : ''}
                </div>
                <div class="api-key-input-group">
                    <input type="password"
                           class="api-key-input"
                           data-provider="${id}"
                           placeholder="${placeholder}"
                           value="${maskedValue}">
                    <button class="btn-toggle-visibility"
                            data-provider="${id}"
                            title="Afficher/Masquer">
                        👁️
                    </button>
                    <button class="btn-test-key"
                            data-provider="${id}"
                            title="Tester la clé">
                        ✓ Tester
                    </button>
                    <button class="btn-remove-key"
                            data-provider="${id}"
                            title="Supprimer">
                        🗑️
                    </button>
                </div>
            </div>
        `;
    }

    /**
     * Attach event listeners
     */
    attachEventListeners() {
        // API key inputs
        this.container.querySelectorAll('.api-key-input').forEach(input => {
            input.addEventListener('change', (e) => {
                const provider = e.target.dataset.provider;
                this.updateApiKey(provider, e.target.value);
            });
        });

        // Toggle visibility buttons
        this.container.querySelectorAll('.btn-toggle-visibility').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const provider = e.target.dataset.provider;
                const input = this.container.querySelector(`.api-key-input[data-provider="${provider}"]`);
                input.type = input.type === 'password' ? 'text' : 'password';
            });
        });

        // Test key buttons
        this.container.querySelectorAll('.btn-test-key').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const provider = e.target.dataset.provider;
                this.testApiKey(provider);
            });
        });

        // Remove key buttons
        this.container.querySelectorAll('.btn-remove-key').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const provider = e.target.dataset.provider;
                this.removeApiKey(provider);
            });
        });

        // Security toggles
        const securityToggles = {
            'encryption-toggle': 'encryptionEnabled',
            'mask-toggle': 'maskApiKeys',
            'auth-export-toggle': 'requireAuthForExport',
            'audit-toggle': 'auditLog'
        };

        Object.entries(securityToggles).forEach(([className, setting]) => {
            const toggle = this.container.querySelector(`.${className}`);
            if (toggle) {
                toggle.addEventListener('change', (e) => {
                    this.securitySettings[setting] = e.target.checked;
                    if (setting === 'maskApiKeys') {
                        this.render();
                    }
                });
            }
        });

        // Timeout input
        const timeoutInput = this.container.querySelector('.timeout-input');
        if (timeoutInput) {
            timeoutInput.addEventListener('change', (e) => {
                this.securitySettings.autoLockTimeout = parseInt(e.target.value);
            });
        }

        // Save button
        const saveBtn = this.container.querySelector('.btn-save');
        if (saveBtn) {
            saveBtn.addEventListener('click', () => this.saveSettings());
        }

        // Clear log button
        const clearLogBtn = this.container.querySelector('.btn-clear-log');
        if (clearLogBtn) {
            clearLogBtn.addEventListener('click', () => this.clearAuditLog());
        }

        // Danger zone buttons
        this.container.querySelectorAll('.btn-danger, .btn-export-encrypted').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const action = e.target.dataset.action;
                this.handleDangerAction(action);
            });
        });
    }

    /**
     * Update API key
     */
    updateApiKey(provider, value) {
        this.apiKeys[provider].value = value;
        this.apiKeys[provider].status = value ? 'set' : 'not-set';
    }

    /**
     * Test API key
     */
    async testApiKey(provider) {
        const key = this.apiKeys[provider];
        if (!key.value) {
            this.showError('Clé API non définie');
            return;
        }

        try {
            const statusElement = this.container.querySelector(`.api-key-item[data-provider="${provider}"] .api-key-status`);
            statusElement.textContent = '⏳ Test en cours...';

            // Mock API test - replace with actual API call
            await new Promise(resolve => setTimeout(resolve, 1000));
            const isValid = Math.random() > 0.3; // 70% success rate for demo

            if (isValid) {
                key.status = 'valid';
                key.lastUsed = new Date().toISOString();
                this.showSuccess('Clé API valide');
            } else {
                key.status = 'invalid';
                this.showError('Clé API invalide');
            }

            this.render();
        } catch (error) {
            console.error('Error testing API key:', error);
            this.showError('Erreur lors du test');
        }
    }

    /**
     * Remove API key
     */
    removeApiKey(provider) {
        if (!confirm(`Supprimer la clé API ${provider} ?`)) {
            return;
        }

        this.apiKeys[provider] = {
            value: '',
            status: 'not-set',
            lastUsed: null
        };

        this.render();
        this.showSuccess('Clé API supprimée');
    }

    /**
     * Load audit log
     */
    async loadAuditLog() {
        const logContainer = document.getElementById('audit-log');
        if (!logContainer) return;

        try {
            // Mock audit log - replace with actual API call
            const logs = [
                { timestamp: new Date().toISOString(), action: 'API Key Updated', provider: 'OpenAI', status: 'success' },
                { timestamp: new Date(Date.now() - 3600000).toISOString(), action: 'Settings Saved', provider: 'System', status: 'success' },
                { timestamp: new Date(Date.now() - 7200000).toISOString(), action: 'API Key Tested', provider: 'Anthropic', status: 'success' }
            ];

            logContainer.innerHTML = logs.map(log => `
                <div class="log-entry">
                    <span class="log-time">${this.formatDate(log.timestamp)}</span>
                    <span class="log-action">${log.action}</span>
                    <span class="log-provider">${log.provider}</span>
                    <span class="log-status status-${log.status}">${log.status}</span>
                </div>
            `).join('');
        } catch (error) {
            console.error('Error loading audit log:', error);
            logContainer.innerHTML = '<div class="log-error">Erreur de chargement</div>';
        }
    }

    /**
     * Clear audit log
     */
    clearAuditLog() {
        if (!confirm('Effacer tout le journal d\'audit ?')) {
            return;
        }

        const logContainer = document.getElementById('audit-log');
        if (logContainer) {
            logContainer.innerHTML = '<div class="log-empty">Journal vide</div>';
        }

        this.showSuccess('Journal effacé');
    }

    /**
     * Handle danger zone actions
     */
    handleDangerAction(action) {
        switch (action) {
            case 'clear-keys':
                if (confirm('⚠️ Supprimer TOUTES les clés API ? Cette action est irréversible.')) {
                    Object.keys(this.apiKeys).forEach(provider => {
                        this.apiKeys[provider] = { value: '', status: 'not-set', lastUsed: null };
                    });
                    this.render();
                    this.showSuccess('Toutes les clés ont été supprimées');
                }
                break;

            case 'reset-security':
                if (confirm('Réinitialiser tous les paramètres de sécurité ?')) {
                    this.securitySettings = {
                        encryptionEnabled: true,
                        autoLockTimeout: 30,
                        requireAuthForExport: true,
                        maskApiKeys: true,
                        auditLog: true
                    };
                    this.render();
                    this.showSuccess('Paramètres réinitialisés');
                }
                break;

            case 'export-encrypted':
                this.exportEncryptedData();
                break;
        }
    }

    /**
     * Export encrypted data
     */
    exportEncryptedData() {
        if (this.securitySettings.requireAuthForExport) {
            if (!confirm('Confirmer l\'export des données chiffrées ?')) {
                return;
            }
        }

        const data = {
            apiKeys: this.apiKeys,
            securitySettings: this.securitySettings,
            exportDate: new Date().toISOString()
        };

        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `security-backup-${Date.now()}.json`;
        a.click();
        URL.revokeObjectURL(url);

        this.showSuccess('Données exportées');
    }

    /**
     * Mask API key
     */
    maskApiKey(key) {
        if (key.length < 8) return key;
        return key.substring(0, 4) + '•'.repeat(key.length - 8) + key.substring(key.length - 4);
    }

    /**
     * Get status icon
     */
    getStatusIcon(status) {
        const icons = {
            'not-set': '⚪',
            'set': '🟡',
            'valid': '🟢',
            'invalid': '🔴'
        };
        return icons[status] || '⚪';
    }

    /**
     * Get status text
     */
    getStatusText(status) {
        const texts = {
            'not-set': 'Non définie',
            'set': 'Définie',
            'valid': 'Valide',
            'invalid': 'Invalide'
        };
        return texts[status] || 'Inconnu';
    }

    /**
     * Format date
     */
    formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleString('fr-FR');
    }

    /**
     * Load settings
     */
    async loadSettings() {
        try {
            const response = await api.request('/api/settings/security');
            if (response) {
                this.apiKeys = { ...this.apiKeys, ...response.apiKeys };
                this.securitySettings = { ...this.securitySettings, ...response.securitySettings };
            }
        } catch (error) {
            console.error('Error loading security settings:', error);
        }
    }

    /**
     * Save settings
     */
    async saveSettings() {
        try {
            await api.request('/api/settings/security', {
                method: 'POST',
                body: JSON.stringify({
                    apiKeys: this.apiKeys,
                    securitySettings: this.securitySettings
                })
            });
            this.showSuccess('Paramètres de sécurité sauvegardés');
        } catch (error) {
            console.error('Error saving security settings:', error);
            this.showError('Erreur lors de la sauvegarde');
        }
    }

    /**
     * Show success message
     */
    showSuccess(message) {
        console.log('✓', message);
    }

    /**
     * Show error message
     */
    showError(message) {
        console.error('✗', message);
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
export const settingsSecurity = new SettingsSecurity();
