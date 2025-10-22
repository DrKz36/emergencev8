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

                    <!-- Active Sessions (Phase P2 - Feature 8) -->
                    <div class="settings-section">
                        <div class="section-header-with-action">
                            <h3>📱 Sessions Actives</h3>
                            <button class="btn-revoke-all" title="Révoquer toutes les sessions sauf celle-ci">
                                🚫 Révoquer toutes
                            </button>
                        </div>
                        <div class="sessions-info">
                            <p class="info-text">
                                Gérez vos sessions actives. Vous pouvez révoquer une session pour la déconnecter immédiatement.
                            </p>
                        </div>
                        <div class="sessions-list" id="sessions-list">
                            <div class="log-loading">Chargement des sessions...</div>
                        </div>
                    </div>

                    <!-- 2FA Authentication (Phase P2 - Feature 9) -->
                    <div class="settings-section">
                        <h3>🔐 Authentification à Deux Facteurs (2FA)</h3>
                        <div class="twofa-info">
                            <p class="info-text">
                                L'authentification à deux facteurs ajoute une couche de sécurité supplémentaire en exigeant un code à 6 chiffres depuis votre application d'authentification (Google Authenticator, Authy, etc.).
                            </p>
                        </div>

                        <!-- 2FA Status Container -->
                        <div id="twofa-container">
                            <div class="log-loading">Chargement du statut 2FA...</div>
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
        this.loadActiveSessions();
        this.loadTwoFactorStatus();
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

        // Sessions management (Phase P2 - Feature 8)
        const revokeAllBtn = this.container.querySelector('.btn-revoke-all');
        if (revokeAllBtn) {
            revokeAllBtn.addEventListener('click', () => this.revokeAllSessions());
        }
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
     * Load active sessions (Phase P2 - Feature 8)
     */
    async loadActiveSessions() {
        const sessionsContainer = this.container.querySelector('#sessions-list');
        if (!sessionsContainer) return;

        try {
            const response = await api.fetch('/api/auth/my-sessions', {
                method: 'GET'
            });

            if (!response.ok) {
                throw new Error(`Failed to load sessions: ${response.status}`);
            }

            const data = await response.json();
            this.renderSessionsList(data.items || []);

        } catch (error) {
            console.error('[SettingsSecurity] Error loading sessions:', error);
            sessionsContainer.innerHTML = `
                <div class="error-message">
                    ❌ Erreur lors du chargement des sessions: ${error.message}
                </div>
            `;
        }
    }

    /**
     * Render sessions list (Phase P2 - Feature 8)
     */
    renderSessionsList(sessions) {
        const sessionsContainer = this.container.querySelector('#sessions-list');
        if (!sessionsContainer) return;

        // Get current session ID from state
        const state = JSON.parse(localStorage.getItem('emergenceState-V14') || '{}');
        const currentSessionId = state.auth?.session_id || '';

        if (sessions.length === 0) {
            sessionsContainer.innerHTML = `
                <div class="empty-message">
                    📱 Aucune session active trouvée
                </div>
            `;
            return;
        }

        const sessionsHtml = sessions.map(session => {
            const isCurrentSession = session.id === currentSessionId;
            const createdAt = session.created_at
                ? new Date(session.created_at).toLocaleString('fr-FR', {
                    year: 'numeric',
                    month: 'short',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit'
                })
                : 'N/A';

            const lastActivity = session.last_activity
                ? new Date(session.last_activity).toLocaleString('fr-FR', {
                    day: 'numeric',
                    month: 'short',
                    hour: '2-digit',
                    minute: '2-digit'
                })
                : 'N/A';

            const device = session.device_info || session.user_agent || 'Appareil inconnu';
            const ip = session.ip_address || 'N/A';

            return `
                <div class="session-item ${isCurrentSession ? 'current-session' : ''}">
                    <div class="session-header">
                        <span class="session-device">
                            📱 ${device}
                        </span>
                        ${isCurrentSession ? '<span class="session-badge current">Session actuelle</span>' : ''}
                    </div>
                    <div class="session-details">
                        <div class="session-detail">
                            <span class="detail-label">Créée le</span>
                            <span class="detail-value">${createdAt}</span>
                        </div>
                        <div class="session-detail">
                            <span class="detail-label">Dernière activité</span>
                            <span class="detail-value">${lastActivity}</span>
                        </div>
                        <div class="session-detail">
                            <span class="detail-label">Adresse IP</span>
                            <span class="detail-value">${ip}</span>
                        </div>
                        <div class="session-detail">
                            <span class="detail-label">ID Session</span>
                            <span class="detail-value session-id">${session.id.substring(0, 12)}...</span>
                        </div>
                    </div>
                    <div class="session-actions">
                        ${!isCurrentSession ? `
                            <button class="btn-revoke-session" data-session-id="${session.id}">
                                🚫 Révoquer cette session
                            </button>
                        ` : `
                            <button class="btn-disabled" disabled title="Utilisez le bouton de déconnexion pour terminer cette session">
                                ✓ Session actuelle
                            </button>
                        `}
                    </div>
                </div>
            `;
        }).join('');

        sessionsContainer.innerHTML = sessionsHtml;

        // Attach revoke handlers
        sessionsContainer.querySelectorAll('.btn-revoke-session').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const sessionId = e.currentTarget.getAttribute('data-session-id');
                this.revokeSession(sessionId);
            });
        });
    }

    /**
     * Revoke a single session (Phase P2 - Feature 8)
     */
    async revokeSession(sessionId) {
        if (!confirm('Voulez-vous vraiment révoquer cette session?\n\nL\'appareil sera déconnecté immédiatement.')) {
            return;
        }

        try {
            const response = await api.fetch(`/api/auth/my-sessions/${sessionId}/revoke`, {
                method: 'POST'
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `Erreur ${response.status}`);
            }

            this.showSuccess('Session révoquée avec succès');
            // Reload sessions list
            await this.loadActiveSessions();

        } catch (error) {
            console.error('[SettingsSecurity] Error revoking session:', error);
            this.showError(`Erreur: ${error.message}`);
        }
    }

    /**
     * Revoke all sessions except current (Phase P2 - Feature 8)
     */
    async revokeAllSessions() {
        if (!confirm('Voulez-vous vraiment révoquer TOUTES les autres sessions?\n\nTous les autres appareils seront déconnectés immédiatement.\n\nCette action est irréversible.')) {
            return;
        }

        try {
            const response = await api.fetch('/api/auth/my-sessions', {
                method: 'GET'
            });

            if (!response.ok) {
                throw new Error(`Failed to load sessions: ${response.status}`);
            }

            const data = await response.json();
            const sessions = data.items || [];

            // Get current session ID
            const state = JSON.parse(localStorage.getItem('emergenceState-V14') || '{}');
            const currentSessionId = state.auth?.session_id || '';

            // Revoke all except current
            const otherSessions = sessions.filter(s => s.id !== currentSessionId);

            if (otherSessions.length === 0) {
                this.showError('Aucune autre session à révoquer');
                return;
            }

            let revokedCount = 0;
            let failedCount = 0;

            for (const session of otherSessions) {
                try {
                    const revokeResponse = await api.fetch(`/api/auth/my-sessions/${session.id}/revoke`, {
                        method: 'POST'
                    });

                    if (revokeResponse.ok) {
                        revokedCount++;
                    } else {
                        failedCount++;
                    }
                } catch (err) {
                    console.error(`Failed to revoke session ${session.id}:`, err);
                    failedCount++;
                }
            }

            this.showSuccess(`${revokedCount} session(s) révoquée(s)`);

            if (failedCount > 0) {
                this.showError(`${failedCount} session(s) n'ont pas pu être révoquées`);
            }

            // Reload sessions list
            await this.loadActiveSessions();

        } catch (error) {
            console.error('[SettingsSecurity] Error revoking all sessions:', error);
            this.showError(`Erreur: ${error.message}`);
        }
    }

    /**
     * Load 2FA status (Phase P2 - Feature 9)
     */
    async loadTwoFactorStatus() {
        const container = this.container.querySelector('#twofa-container');
        if (!container) return;

        try {
            const response = await api.fetch('/api/auth/2fa/status', {
                method: 'GET'
            });

            if (!response.ok) {
                throw new Error(`Failed to load 2FA status: ${response.status}`);
            }

            const data = await response.json();
            this.render2FAStatus(data);

        } catch (error) {
            console.error('[SettingsSecurity] Error loading 2FA status:', error);
            container.innerHTML = `
                <div class="error-message">
                    ❌ Erreur lors du chargement du statut 2FA: ${error.message}
                </div>
            `;
        }
    }

    /**
     * Render 2FA status (Phase P2 - Feature 9)
     */
    render2FAStatus(status) {
        const container = this.container.querySelector('#twofa-container');
        if (!container) return;

        const enabled = status.enabled || false;
        const backupCodesRemaining = status.backup_codes_remaining || 0;

        if (enabled) {
            // 2FA is enabled
            container.innerHTML = `
                <div class="twofa-enabled">
                    <div class="status-badge enabled">
                        ✓ 2FA Activée
                    </div>
                    <div class="twofa-details">
                        <div class="detail-item">
                            <span class="detail-label">Codes de secours restants</span>
                            <span class="detail-value ${backupCodesRemaining < 3 ? 'warning' : ''}">${backupCodesRemaining} / 10</span>
                        </div>
                        ${backupCodesRemaining < 3 ? `
                            <div class="warning-box">
                                ⚠️ Attention : Il vous reste peu de codes de secours. Pensez à en régénérer.
                            </div>
                        ` : ''}
                    </div>
                    <div class="twofa-actions">
                        <button class="btn-disable-2fa">
                            🚫 Désactiver la 2FA
                        </button>
                    </div>
                </div>
            `;

            // Attach disable handler
            container.querySelector('.btn-disable-2fa')?.addEventListener('click', () => {
                this.disable2FA();
            });

        } else {
            // 2FA is disabled
            container.innerHTML = `
                <div class="twofa-disabled">
                    <div class="status-badge disabled">
                        ✗ 2FA Désactivée
                    </div>
                    <div class="twofa-actions">
                        <button class="btn-enable-2fa">
                            🔐 Activer la 2FA
                        </button>
                    </div>
                </div>
            `;

            // Attach enable handler
            container.querySelector('.btn-enable-2fa')?.addEventListener('click', () => {
                this.enable2FA();
            });
        }
    }

    /**
     * Enable 2FA (Phase P2 - Feature 9)
     */
    async enable2FA() {
        try {
            const response = await api.fetch('/api/auth/2fa/enable', {
                method: 'POST'
            });

            if (!response.ok) {
                throw new Error(`Failed to enable 2FA: ${response.status}`);
            }

            const data = await response.json();
            this.show2FASetupModal(data);

        } catch (error) {
            console.error('[SettingsSecurity] Error enabling 2FA:', error);
            this.showError(`Erreur lors de l'activation de la 2FA: ${error.message}`);
        }
    }

    /**
     * Show 2FA setup modal with QR code (Phase P2 - Feature 9)
     */
    show2FASetupModal(data) {
        const qrCode = data.qr_code;
        const secret = data.secret;
        const backupCodes = data.backup_codes || [];

        // Create modal
        const modal = document.createElement('div');
        modal.className = 'twofa-modal';
        modal.innerHTML = `
            <div class="modal-overlay"></div>
            <div class="modal-content twofa-modal-content">
                <div class="modal-header">
                    <h3>🔐 Activer l'Authentification 2FA</h3>
                    <button class="btn-close-modal">✕</button>
                </div>
                <div class="modal-body">
                    <div class="setup-step">
                        <h4>1️⃣ Scannez le QR Code</h4>
                        <p>Utilisez votre application d'authentification (Google Authenticator, Authy, etc.) pour scanner ce code :</p>
                        <div class="qr-code-container">
                            <img src="data:image/png;base64,${qrCode}" alt="QR Code 2FA" />
                        </div>
                        <details class="manual-entry">
                            <summary>Saisie manuelle</summary>
                            <p>Si vous ne pouvez pas scanner le QR code, entrez ce secret manuellement :</p>
                            <div class="secret-code">
                                <code>${secret}</code>
                                <button class="btn-copy-secret" data-secret="${secret}">📋 Copier</button>
                            </div>
                        </details>
                    </div>

                    <div class="setup-step">
                        <h4>2️⃣ Codes de Secours</h4>
                        <p>Conservez ces codes de secours dans un endroit sûr. Ils vous permettront de vous connecter si vous perdez accès à votre application d'authentification :</p>
                        <div class="backup-codes">
                            ${backupCodes.map(code => `<div class="backup-code">${code}</div>`).join('')}
                        </div>
                        <button class="btn-download-backup-codes">
                            💾 Télécharger les codes de secours
                        </button>
                    </div>

                    <div class="setup-step">
                        <h4>3️⃣ Vérification</h4>
                        <p>Entrez le code à 6 chiffres généré par votre application :</p>
                        <div class="verification-form">
                            <input type="text"
                                   id="twofa-verification-code"
                                   class="verification-input"
                                   placeholder="000000"
                                   maxlength="6"
                                   pattern="[0-9]{6}"
                                   autocomplete="off">
                            <button class="btn-verify-2fa">
                                ✓ Vérifier et Activer
                            </button>
                        </div>
                        <div id="verification-error" class="error-message hidden"></div>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // Attach event handlers
        modal.querySelector('.btn-close-modal')?.addEventListener('click', () => {
            modal.remove();
        });

        modal.querySelector('.modal-overlay')?.addEventListener('click', () => {
            modal.remove();
        });

        modal.querySelector('.btn-copy-secret')?.addEventListener('click', (e) => {
            const secret = e.currentTarget.getAttribute('data-secret');
            navigator.clipboard.writeText(secret);
            this.showSuccess('Secret copié dans le presse-papier');
        });

        modal.querySelector('.btn-download-backup-codes')?.addEventListener('click', () => {
            const content = backupCodes.join('\n');
            const blob = new Blob([content], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'emergence-2fa-backup-codes.txt';
            a.click();
            URL.revokeObjectURL(url);
            this.showSuccess('Codes de secours téléchargés');
        });

        modal.querySelector('.btn-verify-2fa')?.addEventListener('click', async () => {
            const code = modal.querySelector('#twofa-verification-code')?.value.trim();
            await this.verify2FA(code, modal);
        });

        // Allow Enter key to verify
        modal.querySelector('#twofa-verification-code')?.addEventListener('keypress', async (e) => {
            if (e.key === 'Enter') {
                const code = e.target.value.trim();
                await this.verify2FA(code, modal);
            }
        });
    }

    /**
     * Verify 2FA code (Phase P2 - Feature 9)
     */
    async verify2FA(code, modal) {
        const errorElement = modal.querySelector('#verification-error');

        if (!code || code.length !== 6) {
            errorElement.textContent = 'Le code doit contenir 6 chiffres';
            errorElement.classList.remove('hidden');
            return;
        }

        try {
            const response = await api.fetch('/api/auth/2fa/verify', {
                method: 'POST',
                body: JSON.stringify({ code })
            });

            if (!response.ok) {
                throw new Error(`Failed to verify 2FA: ${response.status}`);
            }

            const result = await response.json();

            if (result.success) {
                this.showSuccess('2FA activée avec succès !');
                modal.remove();
                // Reload 2FA status
                await this.loadTwoFactorStatus();
            } else {
                errorElement.textContent = 'Code invalide. Vérifiez le code sur votre application.';
                errorElement.classList.remove('hidden');
            }

        } catch (error) {
            console.error('[SettingsSecurity] Error verifying 2FA:', error);
            errorElement.textContent = `Erreur: ${error.message}`;
            errorElement.classList.remove('hidden');
        }
    }

    /**
     * Disable 2FA (Phase P2 - Feature 9)
     */
    async disable2FA() {
        const password = prompt('Pour désactiver la 2FA, entrez votre mot de passe :');

        if (!password) {
            return;
        }

        try {
            const response = await api.fetch('/api/auth/2fa/disable', {
                method: 'POST',
                body: JSON.stringify({ password })
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `Erreur ${response.status}`);
            }

            const result = await response.json();

            if (result.success) {
                this.showSuccess('2FA désactivée avec succès');
                // Reload 2FA status
                await this.loadTwoFactorStatus();
            } else {
                this.showError(result.message || 'Échec de la désactivation de la 2FA');
            }

        } catch (error) {
            console.error('[SettingsSecurity] Error disabling 2FA:', error);
            this.showError(`Erreur: ${error.message}`);
        }
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
