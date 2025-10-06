/**
 * Welcome Popup
 * Affiche un popup d'accueil avec lien vers le tutoriel
 */

const STORAGE_KEY = 'emergence_welcome_dismissed';

export class WelcomePopup {
    constructor(eventBus) {
        this.eventBus = eventBus;
        this.popup = null;
    }

    /**
     * Check if popup should be shown
     */
    shouldShow() {
        try {
            const dismissed = localStorage.getItem(STORAGE_KEY);
            return !dismissed || dismissed !== 'true';
        } catch (error) {
            console.warn('[WelcomePopup] Error checking localStorage:', error);
            return true;
        }
    }

    /**
     * Mark popup as dismissed
     */
    dismiss(permanent = false) {
        if (permanent) {
            try {
                localStorage.setItem(STORAGE_KEY, 'true');
            } catch (error) {
                console.warn('[WelcomePopup] Error saving to localStorage:', error);
            }
        }
        this.hide();
    }

    /**
     * Show the welcome popup
     */
    show() {
        if (!this.shouldShow()) {
            return;
        }

        // Create popup element
        this.popup = document.createElement('div');
        this.popup.className = 'welcome-popup-overlay';
        this.popup.innerHTML = `
            <div class="welcome-popup">
                <div class="welcome-popup-header">
                    <div class="welcome-popup-icon">👋</div>
                    <h2>Bienvenue dans ÉMERGENCE !</h2>
                    <button class="welcome-popup-close" aria-label="Fermer">×</button>
                </div>
                <div class="welcome-popup-body">
                    <p>
                        Nous sommes ravis de vous accueillir dans ÉMERGENCE, votre plateforme d'intelligence
                        artificielle collaborative et multi-agents.
                    </p>
                    <p>
                        <strong>Pour bien démarrer :</strong> Un guide d'utilisation complet est disponible
                        dans la section <strong>"📚 Documentation"</strong> accessible depuis le menu latéral.
                    </p>
                    <p>
                        Vous y trouverez des guides détaillés sur toutes les fonctionnalités :
                    </p>
                    <ul class="welcome-features-list">
                        <li>💬 <strong>Chat Multi-Agents</strong> - Anima, Neo & Nexus</li>
                        <li>🧠 <strong>Base de Connaissances</strong> - Mémoire sémantique</li>
                        <li>📚 <strong>Documents & RAG</strong> - Vos données comme source</li>
                        <li>📂 <strong>Conversations</strong> - Organisation et contexte</li>
                        <li>📊 <strong>Dashboard</strong> - Métriques et statistiques</li>
                    </ul>
                </div>
                <div class="welcome-popup-footer">
                    <label class="welcome-checkbox-label">
                        <input type="checkbox" id="welcome-no-show" class="welcome-checkbox">
                        <span>Ne plus montrer ce message</span>
                    </label>
                    <div class="welcome-popup-actions">
                        <button class="btn-welcome-close">Fermer</button>
                        <button class="btn-welcome-tutorial">
                            📚 Voir le guide
                        </button>
                    </div>
                </div>
            </div>
        `;

        // Append to body
        document.body.appendChild(this.popup);

        // Add styles if not already present
        this.injectStyles();

        // Attach event listeners
        this.attachEventListeners();

        // Focus trap
        this.setupFocusTrap();
    }

    /**
     * Hide the popup
     */
    hide() {
        if (this.popup) {
            this.popup.remove();
            this.popup = null;
        }
    }

    /**
     * Inject CSS styles
     */
    injectStyles() {
        if (document.getElementById('welcome-popup-styles')) {
            return;
        }

        const style = document.createElement('style');
        style.id = 'welcome-popup-styles';
        style.textContent = `
            .welcome-popup-overlay {
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0, 0, 0, 0.7);
                backdrop-filter: blur(4px);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 10000;
                padding: 1rem;
                animation: fadeIn 0.3s ease;
            }

            @keyframes fadeIn {
                from { opacity: 0; }
                to { opacity: 1; }
            }

            .welcome-popup {
                background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 16px;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
                max-width: 560px;
                width: 100%;
                max-height: 90vh;
                overflow-y: auto;
                animation: slideUp 0.4s ease;
            }

            @keyframes slideUp {
                from { transform: translateY(30px); opacity: 0; }
                to { transform: translateY(0); opacity: 1; }
            }

            .welcome-popup-header {
                padding: 1.5rem 2rem;
                border-bottom: 1px solid rgba(255, 255, 255, 0.1);
                position: relative;
            }

            .welcome-popup-icon {
                font-size: 3rem;
                margin-bottom: 0.5rem;
                text-align: center;
            }

            .welcome-popup-header h2 {
                font-size: 1.5rem;
                font-weight: 600;
                color: #e2e8f0;
                margin: 0;
                text-align: center;
            }

            .welcome-popup-close {
                position: absolute;
                top: 1rem;
                right: 1rem;
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
                color: #e2e8f0;
                width: 32px;
                height: 32px;
                border-radius: 8px;
                font-size: 1.5rem;
                line-height: 1;
                cursor: pointer;
                transition: all 0.2s;
            }

            .welcome-popup-close:hover {
                background: rgba(255, 255, 255, 0.2);
                border-color: rgba(255, 255, 255, 0.3);
            }

            .welcome-popup-body {
                padding: 2rem;
                color: #cbd5e1;
                line-height: 1.6;
            }

            .welcome-popup-body p {
                margin: 0 0 1rem 0;
            }

            .welcome-popup-body p:last-child {
                margin-bottom: 0;
            }

            .welcome-popup-body strong {
                color: #e2e8f0;
                font-weight: 600;
            }

            .welcome-features-list {
                list-style: none;
                padding: 0;
                margin: 1rem 0 0 0;
            }

            .welcome-features-list li {
                padding: 0.5rem 0;
                border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            }

            .welcome-features-list li:last-child {
                border-bottom: none;
            }

            .welcome-popup-footer {
                padding: 1.5rem 2rem;
                border-top: 1px solid rgba(255, 255, 255, 0.1);
                display: flex;
                flex-direction: column;
                gap: 1rem;
            }

            .welcome-checkbox-label {
                display: flex;
                align-items: center;
                gap: 0.5rem;
                color: #94a3b8;
                font-size: 0.9rem;
                cursor: pointer;
                user-select: none;
            }

            .welcome-checkbox {
                cursor: pointer;
                width: 16px;
                height: 16px;
            }

            .welcome-popup-actions {
                display: flex;
                gap: 0.75rem;
                justify-content: flex-end;
            }

            .btn-welcome-close,
            .btn-welcome-tutorial {
                padding: 0.6rem 1.2rem;
                border-radius: 8px;
                font-size: 0.95rem;
                font-weight: 500;
                cursor: pointer;
                transition: all 0.2s;
                border: none;
            }

            .btn-welcome-close {
                background: rgba(255, 255, 255, 0.1);
                color: #cbd5e1;
                border: 1px solid rgba(255, 255, 255, 0.2);
            }

            .btn-welcome-close:hover {
                background: rgba(255, 255, 255, 0.15);
                border-color: rgba(255, 255, 255, 0.3);
            }

            .btn-welcome-tutorial {
                background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
                color: white;
                border: 1px solid rgba(59, 130, 246, 0.5);
                box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
            }

            .btn-welcome-tutorial:hover {
                background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
                box-shadow: 0 6px 16px rgba(59, 130, 246, 0.4);
            }

            @media (max-width: 640px) {
                .welcome-popup {
                    max-width: 100%;
                    margin: 0;
                    border-radius: 0;
                    max-height: 100vh;
                }

                .welcome-popup-header,
                .welcome-popup-body,
                .welcome-popup-footer {
                    padding: 1.25rem;
                }

                .welcome-popup-actions {
                    flex-direction: column;
                }

                .btn-welcome-close,
                .btn-welcome-tutorial {
                    width: 100%;
                }
            }
        `;

        document.head.appendChild(style);
    }

    /**
     * Attach event listeners
     */
    attachEventListeners() {
        if (!this.popup) return;

        const closeBtn = this.popup.querySelector('.welcome-popup-close');
        const closeBtnFooter = this.popup.querySelector('.btn-welcome-close');
        const tutorialBtn = this.popup.querySelector('.btn-welcome-tutorial');
        const checkbox = this.popup.querySelector('#welcome-no-show');

        // Close handlers
        const handleClose = () => {
            const permanent = checkbox && checkbox.checked;
            this.dismiss(permanent);
        };

        closeBtn?.addEventListener('click', handleClose);
        closeBtnFooter?.addEventListener('click', handleClose);

        // Tutorial button - navigate to documentation
        tutorialBtn?.addEventListener('click', () => {
            const permanent = checkbox && checkbox.checked;
            this.dismiss(permanent);

            // Navigate to documentation module
            if (this.eventBus) {
                this.eventBus.emit('module:show', 'documentation');
            }
        });

        // Close on overlay click
        this.popup.addEventListener('click', (e) => {
            if (e.target === this.popup) {
                handleClose();
            }
        });

        // Close on Escape key
        const escapeHandler = (e) => {
            if (e.key === 'Escape') {
                handleClose();
                document.removeEventListener('keydown', escapeHandler);
            }
        };
        document.addEventListener('keydown', escapeHandler);
    }

    /**
     * Setup focus trap for accessibility
     */
    setupFocusTrap() {
        if (!this.popup) return;

        const focusableElements = this.popup.querySelectorAll(
            'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );

        const firstElement = focusableElements[0];
        const lastElement = focusableElements[focusableElements.length - 1];

        firstElement?.focus();

        const trapFocus = (e) => {
            if (e.key !== 'Tab') return;

            if (e.shiftKey) {
                if (document.activeElement === firstElement) {
                    e.preventDefault();
                    lastElement?.focus();
                }
            } else {
                if (document.activeElement === lastElement) {
                    e.preventDefault();
                    firstElement?.focus();
                }
            }
        };

        this.popup.addEventListener('keydown', trapFocus);
    }
}

/**
 * Show welcome popup if needed
 * @param {EventBus} eventBus
 */
export function showWelcomePopupIfNeeded(eventBus) {
    const popup = new WelcomePopup(eventBus);

    // Show after a short delay to let the app initialize
    setTimeout(() => {
        popup.show();
    }, 500);

    return popup;
}
