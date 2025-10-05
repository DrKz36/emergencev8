/**
 * Settings Tutorial Module
 * Documentation exhaustive des features et lancement du tutoriel interactif
 */

import { Tutorial } from '../../components/tutorial/Tutorial.js';
import { TUTORIAL_GUIDES } from '../../components/tutorial/tutorialGuides.js';

export class SettingsTutorial {
    constructor() {
        this.container = null;
        this.tutorial = new Tutorial();
        this.activeGuide = null;
    }

    /**
     * Initialize tutorial settings module
     */
    async init(containerId) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            console.error('Settings Tutorial container not found');
            return;
        }

        this.render();
    }

    /**
     * Render tutorial settings
     */
    render() {
        this.container.innerHTML = `
            <div class="settings-tutorial">
                <div class="settings-header">
                    <h2>🎓 Tutoriel et Documentation</h2>
                    <p class="header-description">
                        Découvrez toutes les fonctionnalités d'ÉMERGENCE et apprenez à les utiliser efficacement
                    </p>
                </div>

                <div class="settings-sections">
                    <!-- Interactive Tutorial Section -->
                    <div class="settings-section tutorial-launch-section">
                        <div class="tutorial-hero">
                            <div class="tutorial-hero-icon">🚀</div>
                            <div class="tutorial-hero-content">
                                <h3>Tutoriel Interactif</h3>
                                <p>
                                    Lancez le tutoriel interactif guidé pour découvrir les fonctionnalités principales
                                    d'ÉMERGENCE pas à pas. Le tutoriel vous accompagne à travers l'interface et
                                    vous montre comment utiliser chaque module efficacement.
                                </p>
                                <button class="btn-launch-tutorial">
                                    <span class="btn-icon">▶️</span>
                                    Lancer le tutoriel interactif
                                </button>
                            </div>
                        </div>
                    </div>

                    <!-- Features Documentation -->
                    <div class="settings-section">
                        <h3>📚 Documentation des Fonctionnalités</h3>
                        <p class="section-description">
                            Explorez la documentation détaillée de chaque fonctionnalité pour maîtriser tous les aspects d'ÉMERGENCE.
                        </p>

                        <div class="features-grid">
                            ${this.renderFeatureCards()}
                        </div>
                    </div>

                    <!-- Quick Tips Section -->
                    <div class="settings-section">
                        <h3>💡 Astuces Rapides</h3>
                        <div class="tips-grid">
                            ${this.renderQuickTips()}
                        </div>
                    </div>

                    <!-- Keyboard Shortcuts -->
                    <div class="settings-section">
                        <h3>⌨️ Raccourcis Clavier</h3>
                        <div class="shortcuts-list">
                            ${this.renderKeyboardShortcuts()}
                        </div>
                    </div>
                </div>

                <!-- Guide Detail Modal Placeholder -->
                <div id="guide-modal-container"></div>
            </div>
        `;

        this.attachEventListeners();
    }

    /**
     * Render feature cards
     */
    renderFeatureCards() {
        return TUTORIAL_GUIDES.map(guide => `
            <div class="feature-card" data-guide-id="${guide.id}">
                <div class="feature-icon">${guide.icon}</div>
                <div class="feature-content">
                    <h4>${guide.title}</h4>
                    <p>${guide.summary}</p>
                    <button class="btn-view-guide" data-guide-id="${guide.id}">
                        Voir le guide complet →
                    </button>
                </div>
            </div>
        `).join('');
    }

    /**
     * Render quick tips
     */
    renderQuickTips() {
        const tips = [
            {
                icon: '🤖',
                title: 'Agents Spécialisés',
                text: 'Chaque agent (Anima, Neo, Nexus) a ses forces. Choisissez selon votre besoin : créativité, analyse ou synthèse.'
            },
            {
                icon: '📚',
                title: 'Mode RAG',
                text: 'Activez le RAG pour que l\'IA utilise vos documents comme source. Idéal pour des réponses basées sur vos données.'
            },
            {
                icon: '🧠',
                title: 'Mémoire Conceptuelle',
                text: 'L\'IA mémorise automatiquement les concepts importants de vos conversations pour un contexte enrichi.'
            },
            {
                icon: '💬',
                title: 'Conversations Organisées',
                text: 'Créez des conversations séparées par projet ou sujet pour garder un contexte clair et organisé.'
            },
            {
                icon: '📊',
                title: 'Dashboard de Suivi',
                text: 'Consultez le Cockpit pour suivre votre utilisation, vos coûts et vos métriques en temps réel.'
            },
            {
                icon: '🔍',
                title: 'Recherche Intelligente',
                text: 'Utilisez la recherche pour retrouver rapidement messages, concepts ou documents dans toute l\'application.'
            }
        ];

        return tips.map(tip => `
            <div class="tip-card">
                <div class="tip-icon">${tip.icon}</div>
                <div class="tip-content">
                    <h4>${tip.title}</h4>
                    <p>${tip.text}</p>
                </div>
            </div>
        `).join('');
    }

    /**
     * Render keyboard shortcuts
     */
    renderKeyboardShortcuts() {
        const shortcuts = [
            { keys: ['Entrée'], description: 'Envoyer le message dans le chat' },
            { keys: ['Maj', 'Entrée'], description: 'Nouvelle ligne dans le message' },
            { keys: ['Ctrl/Cmd', 'K'], description: 'Focus sur la zone de saisie' },
            { keys: ['Ctrl/Cmd', 'N'], description: 'Nouvelle conversation' },
            { keys: ['Ctrl/Cmd', 'F'], description: 'Rechercher' },
            { keys: ['Échap'], description: 'Fermer modal ou panneau' },
            { keys: ['↑', '↓'], description: 'Naviguer dans les listes' }
        ];

        return shortcuts.map(shortcut => `
            <div class="shortcut-item">
                <div class="shortcut-keys">
                    ${shortcut.keys.map(key => `<kbd>${key}</kbd>`).join(' + ')}
                </div>
                <div class="shortcut-description">${shortcut.description}</div>
            </div>
        `).join('');
    }

    /**
     * Attach event listeners
     */
    attachEventListeners() {
        // Launch tutorial button
        const launchBtn = this.container.querySelector('.btn-launch-tutorial');
        if (launchBtn) {
            launchBtn.addEventListener('click', () => this.launchTutorial());
        }

        // View guide buttons
        this.container.querySelectorAll('.btn-view-guide').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const guideId = e.currentTarget.dataset.guideId;
                this.showGuideDetail(guideId);
            });
        });

        // Feature cards click
        this.container.querySelectorAll('.feature-card').forEach(card => {
            card.addEventListener('click', (e) => {
                // Only trigger if not clicking the button
                if (!e.target.closest('.btn-view-guide')) {
                    const guideId = card.dataset.guideId;
                    this.showGuideDetail(guideId);
                }
            });
        });
    }

    /**
     * Launch interactive tutorial
     */
    launchTutorial() {
        console.log('[SettingsTutorial] Launching interactive tutorial...');
        this.tutorial.open();
    }

    /**
     * Show guide detail in modal
     */
    showGuideDetail(guideId) {
        const guide = TUTORIAL_GUIDES.find(g => g.id === guideId);
        if (!guide) {
            console.error('Guide not found:', guideId);
            return;
        }

        this.activeGuide = guide;

        // Create modal
        const modal = document.createElement('div');
        modal.className = 'guide-modal-overlay';
        modal.innerHTML = `
            <div class="guide-modal">
                <div class="guide-modal-header">
                    <div class="guide-modal-title">
                        <span class="guide-modal-icon">${guide.icon}</span>
                        <h2>${guide.title}</h2>
                    </div>
                    <button class="guide-modal-close" aria-label="Fermer">×</button>
                </div>
                <div class="guide-modal-body">
                    ${guide.content}
                </div>
                <div class="guide-modal-footer">
                    <button class="btn-close-guide">Fermer</button>
                    <button class="btn-launch-from-guide">
                        <span class="btn-icon">▶️</span>
                        Lancer le tutoriel interactif
                    </button>
                </div>
            </div>
        `;

        // Add to container
        const modalContainer = this.container.querySelector('#guide-modal-container');
        modalContainer.innerHTML = '';
        modalContainer.appendChild(modal);

        // Event listeners
        modal.querySelector('.guide-modal-close').addEventListener('click', () => {
            modal.remove();
        });

        modal.querySelector('.btn-close-guide').addEventListener('click', () => {
            modal.remove();
        });

        modal.querySelector('.btn-launch-from-guide').addEventListener('click', () => {
            modal.remove();
            this.launchTutorial();
        });

        // Close on overlay click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.remove();
            }
        });

        // Close on Escape
        const escapeHandler = (e) => {
            if (e.key === 'Escape') {
                modal.remove();
                document.removeEventListener('keydown', escapeHandler);
            }
        };
        document.addEventListener('keydown', escapeHandler);
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
export const settingsTutorial = new SettingsTutorial();
