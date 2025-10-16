/**
 * Settings UI Module
 * Interface customization (theme, behavior, display preferences)
 */

import { SettingsIcons, getIcon } from './settings-icons.js';
import { api } from '../../shared/api-client.js';

export class SettingsUI {
    constructor() {
        this.container = null;
        this.settings = {
            theme: 'auto',
            language: 'fr',
            fontSize: 14,
            density: 'comfortable',
            animations: true,
            soundEffects: false,
            notifications: true,
            autoSave: true,
            showTimestamps: true,
            compactView: false,
            highlightSyntax: true,
            lineNumbers: true
        };
    }

    /**
     * Initialize UI settings module
     */
    async init(containerId) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            console.error('Settings UI container not found');
            return;
        }

        await this.loadSettings();
        this.render();
        this.applySettings();
    }

    /**
     * Render UI settings
     */
    render() {
        this.container.innerHTML = `
            <div class="settings-ui">
                <div class="settings-header">
                    <h2>${getIcon('palette', 'header-icon')} Personnalisation de l'Interface</h2>
                    <div class="header-actions">
                        <button class="btn-reset">${getIcon('reset', 'btn-icon')} Réinitialiser</button>
                        <button class="btn-save">${getIcon('save', 'btn-icon')} Sauvegarder</button>
                    </div>
                </div>

                <div class="settings-sections">
                    <!-- Theme Section -->
                    <div class="settings-section">
                        <h3>${getIcon('moon', 'section-icon')} Thème & Apparence</h3>
                        <div class="settings-group">
                            <div class="setting-item">
                                <label class="setting-label">
                                    <span class="label-text">Thème</span>
                                    <span class="label-hint">Choisissez le thème de couleur</span>
                                </label>
                                <div class="theme-selector">
                                    <button class="theme-option ${this.settings.theme === 'light' ? 'active' : ''}"
                                            data-theme="light">
                                        <span class="theme-icon">${SettingsIcons.sun}</span>
                                        <span class="theme-name">Clair</span>
                                    </button>
                                    <button class="theme-option ${this.settings.theme === 'dark' ? 'active' : ''}"
                                            data-theme="dark">
                                        <span class="theme-icon">${SettingsIcons.moon}</span>
                                        <span class="theme-name">Sombre</span>
                                    </button>
                                    <button class="theme-option ${this.settings.theme === 'auto' ? 'active' : ''}"
                                            data-theme="auto">
                                        <span class="theme-icon">${SettingsIcons.refresh}</span>
                                        <span class="theme-name">Auto</span>
                                    </button>
                                </div>
                            </div>

                            <div class="setting-item">
                                <label class="setting-label">
                                    <span class="label-text">Taille de police: <strong>${this.settings.fontSize}px</strong></span>
                                    <span class="label-hint">Ajustez la taille du texte</span>
                                </label>
                                <input type="range" class="font-size-slider"
                                       min="12" max="20" step="1"
                                       value="${this.settings.fontSize}">
                                <div class="slider-marks">
                                    <span>12px</span>
                                    <span>16px</span>
                                    <span>20px</span>
                                </div>
                            </div>

                            <div class="setting-item">
                                <label class="setting-label">
                                    <span class="label-text">Densité de l'interface</span>
                                    <span class="label-hint">Espacement entre les éléments</span>
                                </label>
                                <select class="density-select">
                                    <option value="compact" ${this.settings.density === 'compact' ? 'selected' : ''}>Compact</option>
                                    <option value="comfortable" ${this.settings.density === 'comfortable' ? 'selected' : ''}>Confortable</option>
                                    <option value="spacious" ${this.settings.density === 'spacious' ? 'selected' : ''}>Spacieux</option>
                                </select>
                            </div>
                        </div>
                    </div>

                    <!-- Language Section -->
                    <div class="settings-section">
                        <h3>🌍 Langue & Région</h3>
                        <div class="settings-group">
                            <div class="setting-item">
                                <label class="setting-label">
                                    <span class="label-text">Langue</span>
                                    <span class="label-hint">Langue de l'interface</span>
                                </label>
                                <select class="language-select">
                                    <option value="fr" ${this.settings.language === 'fr' ? 'selected' : ''}>Français</option>
                                    <option value="en" ${this.settings.language === 'en' ? 'selected' : ''}>English</option>
                                    <option value="es" ${this.settings.language === 'es' ? 'selected' : ''}>Español</option>
                                    <option value="de" ${this.settings.language === 'de' ? 'selected' : ''}>Deutsch</option>
                                </select>
                            </div>
                        </div>
                    </div>

                    <!-- Behavior Section -->
                    <div class="settings-section">
                        <h3>⚙️ Comportement</h3>
                        <div class="settings-group">
                            <div class="setting-item toggle-item">
                                <div class="toggle-content">
                                    <span class="label-text">Animations</span>
                                    <span class="label-hint">Activer les animations de l'interface</span>
                                </div>
                                <label class="toggle-switch">
                                    <input type="checkbox" class="animations-toggle"
                                           ${this.settings.animations ? 'checked' : ''}>
                                    <span class="toggle-slider"></span>
                                </label>
                            </div>

                            <div class="setting-item toggle-item">
                                <div class="toggle-content">
                                    <span class="label-text">Effets sonores</span>
                                    <span class="label-hint">Sons pour les actions importantes</span>
                                </div>
                                <label class="toggle-switch">
                                    <input type="checkbox" class="sound-toggle"
                                           ${this.settings.soundEffects ? 'checked' : ''}>
                                    <span class="toggle-slider"></span>
                                </label>
                            </div>

                            <div class="setting-item toggle-item">
                                <div class="toggle-content">
                                    <span class="label-text">Notifications</span>
                                    <span class="label-hint">Afficher les notifications système</span>
                                </div>
                                <label class="toggle-switch">
                                    <input type="checkbox" class="notifications-toggle"
                                           ${this.settings.notifications ? 'checked' : ''}>
                                    <span class="toggle-slider"></span>
                                </label>
                            </div>

                            <div class="setting-item toggle-item">
                                <div class="toggle-content">
                                    <span class="label-text">Sauvegarde automatique</span>
                                    <span class="label-hint">Sauvegarder automatiquement les modifications</span>
                                </div>
                                <label class="toggle-switch">
                                    <input type="checkbox" class="autosave-toggle"
                                           ${this.settings.autoSave ? 'checked' : ''}>
                                    <span class="toggle-slider"></span>
                                </label>
                            </div>
                        </div>
                    </div>

                    <!-- Display Section -->
                    <div class="settings-section">
                        <h3>📺 Affichage</h3>
                        <div class="settings-group">
                            <div class="setting-item toggle-item">
                                <div class="toggle-content">
                                    <span class="label-text">Afficher les timestamps</span>
                                    <span class="label-hint">Horodatage sur les messages</span>
                                </div>
                                <label class="toggle-switch">
                                    <input type="checkbox" class="timestamps-toggle"
                                           ${this.settings.showTimestamps ? 'checked' : ''}>
                                    <span class="toggle-slider"></span>
                                </label>
                            </div>

                            <div class="setting-item toggle-item">
                                <div class="toggle-content">
                                    <span class="label-text">Vue compacte</span>
                                    <span class="label-hint">Réduire l'espace vertical des messages</span>
                                </div>
                                <label class="toggle-switch">
                                    <input type="checkbox" class="compact-toggle"
                                           ${this.settings.compactView ? 'checked' : ''}>
                                    <span class="toggle-slider"></span>
                                </label>
                            </div>

                            <div class="setting-item toggle-item">
                                <div class="toggle-content">
                                    <span class="label-text">Coloration syntaxique</span>
                                    <span class="label-hint">Colorer le code source</span>
                                </div>
                                <label class="toggle-switch">
                                    <input type="checkbox" class="syntax-toggle"
                                           ${this.settings.highlightSyntax ? 'checked' : ''}>
                                    <span class="toggle-slider"></span>
                                </label>
                            </div>

                            <div class="setting-item toggle-item">
                                <div class="toggle-content">
                                    <span class="label-text">Numéros de ligne</span>
                                    <span class="label-hint">Afficher les numéros de ligne dans le code</span>
                                </div>
                                <label class="toggle-switch">
                                    <input type="checkbox" class="linenumbers-toggle"
                                           ${this.settings.lineNumbers ? 'checked' : ''}>
                                    <span class="toggle-slider"></span>
                                </label>
                            </div>
                        </div>
                    </div>

                    <!-- Preview Section -->
                    <div class="settings-section">
                        <h3>👁️ Aperçu</h3>
                        <div class="settings-preview">
                            <div class="preview-box">
                                <div class="preview-message">
                                    <div class="preview-avatar">🤖</div>
                                    <div class="preview-content">
                                        <div class="preview-header">
                                            <strong>Agent de test</strong>
                                            ${this.settings.showTimestamps ? '<span class="preview-time">14:32</span>' : ''}
                                        </div>
                                        <div class="preview-text">
                                            Ceci est un aperçu du message avec la configuration actuelle.
                                        </div>
                                        ${this.settings.highlightSyntax ? `
                                            <pre class="preview-code"><code>function example() {
  return "Hello World";
}</code></pre>
                                        ` : ''}
                                    </div>
                                </div>
                            </div>
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
        // Theme buttons
        this.container.querySelectorAll('.theme-option').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const theme = e.currentTarget.dataset.theme;
                this.updateSetting('theme', theme);
                this.container.querySelectorAll('.theme-option').forEach(b => b.classList.remove('active'));
                e.currentTarget.classList.add('active');
                this.applyTheme(theme);
            });
        });

        // Font size slider
        const fontSlider = this.container.querySelector('.font-size-slider');
        if (fontSlider) {
            fontSlider.addEventListener('input', (e) => {
                const size = parseInt(e.target.value);
                this.updateSetting('fontSize', size);
                e.target.closest('.setting-item').querySelector('.label-text strong').textContent = `${size}px`;
                this.applyFontSize(size);
            });
        }

        // Density select
        const densitySelect = this.container.querySelector('.density-select');
        if (densitySelect) {
            densitySelect.addEventListener('change', (e) => {
                this.updateSetting('density', e.target.value);
                this.applyDensity(e.target.value);
            });
        }

        // Language select
        const languageSelect = this.container.querySelector('.language-select');
        if (languageSelect) {
            languageSelect.addEventListener('change', (e) => {
                this.updateSetting('language', e.target.value);
            });
        }

        // Toggles
        const toggles = {
            'animations-toggle': 'animations',
            'sound-toggle': 'soundEffects',
            'notifications-toggle': 'notifications',
            'autosave-toggle': 'autoSave',
            'timestamps-toggle': 'showTimestamps',
            'compact-toggle': 'compactView',
            'syntax-toggle': 'highlightSyntax',
            'linenumbers-toggle': 'lineNumbers'
        };

        Object.entries(toggles).forEach(([className, setting]) => {
            const toggle = this.container.querySelector(`.${className}`);
            if (toggle) {
                toggle.addEventListener('change', (e) => {
                    this.updateSetting(setting, e.target.checked);
                    this.render();
                });
            }
        });

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
    }

    /**
     * Update setting
     */
    updateSetting(key, value) {
        this.settings[key] = value;
    }

    /**
     * Apply all settings
     */
    applySettings() {
        this.applyTheme(this.settings.theme);
        this.applyFontSize(this.settings.fontSize);
        this.applyDensity(this.settings.density);
    }

    /**
     * Apply theme
     */
    applyTheme(theme) {
        const root = document.documentElement;

        if (theme === 'auto') {
            const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            root.setAttribute('data-theme', prefersDark ? 'dark' : 'light');
        } else {
            root.setAttribute('data-theme', theme);
        }

        // Save to localStorage for persistence across page reloads
        try {
            localStorage.setItem('emergence.theme', theme);
        } catch (error) {
            console.warn('Could not save theme to localStorage:', error);
        }
    }

    /**
     * Apply font size
     */
    applyFontSize(size) {
        document.documentElement.style.setProperty('--font-size-base', `${size}px`);
    }

    /**
     * Apply density
     */
    applyDensity(density) {
        const densityValues = {
            compact: '8px',
            comfortable: '16px',
            spacious: '24px'
        };
        document.documentElement.style.setProperty('--spacing-base', densityValues[density] || '16px');
    }

    /**
     * Load settings
     */
    async loadSettings() {
        // First, try to load from localStorage for immediate application
        try {
            const localTheme = localStorage.getItem('emergence.theme');
            if (localTheme) {
                this.settings.theme = localTheme;
            }
        } catch (error) {
            console.warn('Could not load theme from localStorage:', error);
        }

        // Then load from server (may overwrite local settings)
        try {
            const response = await api.request('/api/settings/ui');
            this.settings = { ...this.settings, ...response };
        } catch (error) {
            console.error('Error loading UI settings:', error);
        }
    }

    /**
     * Save settings
     */
    async saveSettings() {
        try {
            await api.request('/api/settings/ui', {
                method: 'POST',
                body: JSON.stringify(this.settings)
            });
            this.showSuccess('Paramètres sauvegardés avec succès');
        } catch (error) {
            console.error('Error saving UI settings:', error);
            this.showError('Erreur lors de la sauvegarde');
        }
    }

    /**
     * Reset settings
     */
    resetSettings() {
        if (!confirm('Réinitialiser tous les paramètres d\'interface ?')) {
            return;
        }

        this.settings = {
            theme: 'auto',
            language: 'fr',
            fontSize: 14,
            density: 'comfortable',
            animations: true,
            soundEffects: false,
            notifications: true,
            autoSave: true,
            showTimestamps: true,
            compactView: false,
            highlightSyntax: true,
            lineNumbers: true
        };

        this.render();
        this.applySettings();
        this.showSuccess('Paramètres réinitialisés');
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
export const settingsUI = new SettingsUI();
