import { EVENTS } from './constants.js';

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
            return dismissed !== 'true';
        } catch (error) {
            console.warn('[WelcomePopup] Error reading from localStorage:', error);
            return false;
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
        this.popup.setAttribute('role', 'presentation');
        this.popup.tabIndex = -1;
        this.popup.innerHTML = `
            <div class="welcome-popup" role="dialog" aria-modal="true" aria-labelledby="welcome-popup-title" aria-describedby="welcome-popup-description">
                <div class="welcome-popup-header">
                    <div class="welcome-popup-avatars">
                        <img src="/assets/anima.png" alt="Anima" class="welcome-avatar">
                        <img src="/assets/neo.png" alt="Neo" class="welcome-avatar">
                        <img src="/assets/nexus.png" alt="Nexus" class="welcome-avatar">
                    </div>
                    <h2 id="welcome-popup-title">Bienvenue dans le module Dialogue</h2>
                    <button class="welcome-popup-close" aria-label="Fermer">&times;</button>
                </div>
                <div class="welcome-popup-body" id="welcome-popup-description">
                    <p class="welcome-intro">
                        Ravi(e) de te revoir&nbsp;! Les agents Anima, Néo et Nexus sont prêts à collaborer avec toi pour accélérer tes conversations.
                    </p>
                    <p class="welcome-highlight">
                        Avant de démarrer, prends deux minutes pour parcourir le guide d'embarquement&nbsp;: il rassemble les nouveautés et les meilleures pratiques pour dialoguer efficacement.
                    </p>
                    <ul class="welcome-features-list">
                        <li>Découvre le pas-à-pas du module Dialogue et les focus Mémoire/RAG.</li>
                        <li>Retrouve les raccourcis pour inviter plusieurs agents dans une même discussion.</li>
                        <li>Accède aux checklists de démarrage rapide dans <strong>À&nbsp;Propos &gt; Tutoriel</strong>.</li>
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
                            Consulter le tutoriel
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
                inset: 0;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: clamp(16px, 4vw, 32px);
                background: rgba(5, 12, 30, 0.78);
                backdrop-filter: blur(10px);
                z-index: 12000;
                opacity: 0;
                animation: fadeIn 0.3s ease forwards;
            }

            @keyframes fadeIn {
                from { opacity: 0; }
                to { opacity: 1; }
            }

            .welcome-popup {
                position: relative;
                width: min(420px, 100%);
                max-height: min(88vh, 560px);
                display: flex;
                flex-direction: column;
                background: linear-gradient(150deg, rgba(15, 23, 42, 0.95) 0%, rgba(30, 41, 59, 0.94) 55%, rgba(49, 46, 129, 0.9) 100%);
                color: #e2e8f0;
                border-radius: 20px;
                border: 1px solid rgba(148, 163, 184, 0.24);
                box-shadow: 0 26px 68px rgba(2, 6, 23, 0.55);
                overflow: hidden;
                animation: slideUp 0.32s ease;
            }

            .welcome-popup::before {
                content: '';
                position: absolute;
                inset: 0;
                pointer-events: none;
                background:
                    radial-gradient(circle at 15% 20%, rgba(59, 130, 246, 0.22) 0%, transparent 55%),
                    radial-gradient(circle at 80% 80%, rgba(16, 185, 129, 0.22) 0%, transparent 60%);
                opacity: 0.9;
            }

            .welcome-popup > * {
                position: relative;
                z-index: 1;
            }

            @keyframes slideUp {
                from { transform: translateY(24px); opacity: 0; }
                to { transform: translateY(0); opacity: 1; }
            }

            .welcome-popup-header {
                padding: 1.4rem 1.8rem 1rem;
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 0.9rem;
                border-bottom: 1px solid rgba(148, 163, 184, 0.18);
            }

            .welcome-popup-avatars {
                display: flex;
                justify-content: center;
                align-items: center;
                gap: 1rem;
            }

            .welcome-avatar {
                width: 54px;
                height: 54px;
                border-radius: 50%;
                border: 2px solid rgba(148, 163, 184, 0.35);
                background: rgba(15, 23, 42, 0.55);
                box-shadow: 0 12px 22px rgba(15, 118, 110, 0.35);
                transition: transform 0.25s ease, box-shadow 0.25s ease;
            }

            .welcome-avatar:hover {
                transform: translateY(-4px);
                box-shadow: 0 18px 32px rgba(14, 165, 233, 0.45);
            }

            .welcome-popup-header h2 {
                font-size: 1.38rem;
                font-weight: 600;
                color: #f8fafc;
                margin: 0;
                text-align: center;
            }

            .welcome-popup-close {
                position: absolute;
                top: 1rem;
                right: 1rem;
                background: rgba(15, 23, 42, 0.6);
                border: 1px solid rgba(148, 163, 184, 0.32);
                color: #f8fafc;
                width: 36px;
                height: 36px;
                border-radius: 12px;
                font-size: 1.4rem;
                line-height: 1;
                cursor: pointer;
                transition: background 0.18s ease, border-color 0.18s ease, transform 0.18s ease;
            }

            .welcome-popup-close:hover,
            .welcome-popup-close:focus-visible {
                background: rgba(30, 64, 175, 0.75);
                border-color: rgba(96, 165, 250, 0.75);
                transform: scale(1.04);
                outline: none;
            }

            .welcome-popup-body {
                padding: 0 1.8rem 1.6rem;
                display: flex;
                flex-direction: column;
                gap: 0.85rem;
                font-size: 0.98rem;
                line-height: 1.65;
                color: rgba(226, 232, 240, 0.92);
            }

            .welcome-intro {
                margin: 0;
                color: rgba(226, 232, 240, 0.95);
                font-weight: 500;
            }

            .welcome-highlight {
                margin: 0;
                padding: 0.75rem 0.85rem;
                border-radius: 12px;
                background: rgba(14, 165, 233, 0.18);
                border: 1px solid rgba(56, 189, 248, 0.35);
                color: rgba(244, 249, 255, 0.95);
                font-weight: 500;
            }

            .welcome-features-list {
                list-style: none;
                padding: 0;
                margin: 0;
                display: grid;
                gap: 0.65rem;
            }

            .welcome-features-list li {
                position: relative;
                padding-left: 1.65rem;
                color: rgba(226, 232, 240, 0.9);
            }

            .welcome-features-list li::before {
                content: '';
                position: absolute;
                top: 0.55rem;
                left: 0.55rem;
                width: 6px;
                height: 6px;
                border-radius: 999px;
                background: rgba(56, 189, 248, 0.95);
                box-shadow: 0 0 0 4px rgba(56, 189, 248, 0.18);
            }

            .welcome-popup-footer {
                margin-top: auto;
                padding: 1.4rem 1.8rem 1.75rem;
                border-top: 1px solid rgba(148, 163, 184, 0.2);
                display: flex;
                flex-direction: column;
                gap: 1.1rem;
                background: rgba(5, 12, 30, 0.45);
            }

            .welcome-checkbox-label {
                display: flex;
                align-items: center;
                gap: 0.65rem;
                color: rgba(148, 163, 184, 0.95);
                font-size: 0.88rem;
                cursor: pointer;
                user-select: none;
            }

            .welcome-checkbox {
                cursor: pointer;
                width: 18px;
                height: 18px;
                accent-color: #16a34a;
            }

            .welcome-popup-actions {
                display: flex;
                gap: 0.75rem;
                justify-content: flex-end;
                flex-wrap: wrap;
            }

            .btn-welcome-close,
            .btn-welcome-tutorial {
                padding: 0.68rem 1.4rem;
                border-radius: 999px;
                font-size: 0.96rem;
                font-weight: 600;
                cursor: pointer;
                transition: transform 0.18s ease, box-shadow 0.18s ease, background 0.18s ease;
                border: 1px solid transparent;
            }

            .btn-welcome-close {
                background: rgba(148, 163, 184, 0.14);
                color: rgba(226, 232, 240, 0.9);
                border-color: rgba(148, 163, 184, 0.28);
            }

            .btn-welcome-close:hover,
            .btn-welcome-close:focus-visible {
                background: rgba(148, 163, 184, 0.22);
                border-color: rgba(203, 213, 225, 0.55);
                transform: translateY(-1px);
                outline: none;
            }

            .btn-welcome-tutorial {
                background: linear-gradient(135deg, #38bdf8 0%, #2563eb 55%, #7c3aed 100%);
                color: #f8fafc;
                border-color: rgba(59, 130, 246, 0.45);
                box-shadow: 0 14px 28px rgba(37, 99, 235, 0.35);
            }

            .btn-welcome-tutorial:hover,
            .btn-welcome-tutorial:focus-visible {
                box-shadow: 0 18px 34px rgba(56, 189, 248, 0.45);
                transform: translateY(-1px);
                outline: none;
            }

            @media (max-width: 640px) {
                .welcome-popup-overlay {
                    align-items: flex-start;
                    padding: clamp(20px, 10vh, 36px) clamp(14px, 5vw, 22px);
                }

                .welcome-popup {
                    width: 100%;
                    max-height: calc(100vh - clamp(20px, 10vh, 36px));
                    border-radius: 18px;
                }

                .welcome-popup-header {
                    padding: 1.15rem 1.4rem 0.85rem;
                    gap: 0.75rem;
                }

                .welcome-avatar {
                    width: 48px;
                    height: 48px;
                }

                .welcome-popup-body {
                    padding: 0 1.4rem 1.45rem;
                    font-size: 0.95rem;
                }

                .welcome-popup-footer {
                    padding: 1.35rem 1.4rem 1.55rem;
                }

                .welcome-popup-actions {
                    flex-direction: column;
                    align-items: stretch;
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

        // Tutorial button - navigate to Documentation page and scroll to tutorial section
        tutorialBtn?.addEventListener('click', () => {
            const permanent = checkbox && checkbox.checked;
            this.dismiss(permanent);

            const moduleEvent = (EVENTS && EVENTS.MODULE_NAVIGATE) ? EVENTS.MODULE_NAVIGATE : 'app:navigate';
            this.eventBus?.emit?.(moduleEvent, { moduleId: 'documentation' });

            // Wait for module to load, then scroll to tutorial section
            setTimeout(() => {
                const tutorialSection = document.getElementById('tutorial');
                if (tutorialSection) {
                    tutorialSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            }, 500);
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

// Flag global pour empêcher multiples instances du popup
let _activeWelcomePopup = null;

/**
 * Show welcome popup if needed
 * @param {EventBus} eventBus
 */
export function showWelcomePopupIfNeeded(eventBus) {
    // Empêcher multiples instances (panneaux multiples)
    if (_activeWelcomePopup) {
        console.log('[WelcomePopup] Instance déjà active, skip création nouvelle instance');
        return _activeWelcomePopup;
    }

    const popup = new WelcomePopup(eventBus);
    _activeWelcomePopup = popup;

    const bus = (eventBus && typeof eventBus.on === 'function') ? eventBus : null;
    const unsubscribers = [];
    let disposed = false;
    let pendingTimeout = null;

    const cleanup = () => {
        if (disposed) return;
        disposed = true;
        if (pendingTimeout) {
            clearTimeout(pendingTimeout);
            pendingTimeout = null;
        }
        while (unsubscribers.length > 0) {
            const off = unsubscribers.pop();
            try { off?.(); } catch (_) {}
        }
        // Cleanup flag global
        if (_activeWelcomePopup === popup) {
            _activeWelcomePopup = null;
        }
    };

    const isAppReadyForPopup = () => {
        if (typeof document === 'undefined') return false;
        const body = document.body;
        if (!body) return false;
        // Ne PAS afficher si on est sur la page d'authentification
        if (body.classList?.contains?.('home-active')) return false;

        const appContainer = document.getElementById('app-container');
        if (!appContainer) return false;

        const hasHiddenAttr = appContainer.hasAttribute('hidden');
        let displayNone = false;
        try {
            if (typeof window !== 'undefined' && typeof window.getComputedStyle === 'function') {
                displayNone = window.getComputedStyle(appContainer).display === 'none';
            } else {
                displayNone = appContainer.style.display === 'none';
            }
        } catch (_) {
            displayNone = appContainer.style.display === 'none';
        }

        return !hasHiddenAttr && !displayNone;
    };

    const isUserAuthenticated = () => {
        try {
            // Vérifier qu'il y a un token d'authentification
            const tokenKeys = ['emergence.id_token', 'id_token'];
            for (const key of tokenKeys) {
                const token = sessionStorage.getItem(key) || localStorage.getItem(key);
                if (token && token.trim()) return true;
            }
            return false;
        } catch (_) {
            return false;
        }
    };

    const attemptShow = () => {
        if (disposed) return;

        // Vérifier si popup doit être affiché (localStorage check)
        if (!popup.shouldShow()) {
            cleanup();
            return;
        }

        // Vérifier si utilisateur est authentifié
        if (!isUserAuthenticated()) {
            console.log('[WelcomePopup] Utilisateur pas authentifié, skip affichage');
            cleanup();
            return;
        }

        // Vérifier si app est prête
        if (!isAppReadyForPopup()) {
            queueAttempt(250);
            return;
        }

        popup.show();
        cleanup();
    };

    const queueAttempt = (delay = 0) => {
        if (disposed) return;
        if (pendingTimeout) {
            clearTimeout(pendingTimeout);
        }
        pendingTimeout = setTimeout(() => {
            pendingTimeout = null;
            attemptShow();
        }, delay);
    };

    if (bus) {
        const authRequiredEvent = EVENTS.AUTH_REQUIRED || 'ui:auth:required';
        const authLoginSuccessEvent = EVENTS.AUTH_LOGIN_SUCCESS || 'auth:login:success';

        if (typeof bus.on === 'function') {
            // Masquer popup si authentification requise (déconnexion)
            unsubscribers.push(bus.on(authRequiredEvent, () => {
                popup.hide();
                cleanup();
            }));

            // 🔥 FIX: Afficher popup UNIQUEMENT après connexion réussie
            unsubscribers.push(bus.once(authLoginSuccessEvent, () => {
                console.log('[WelcomePopup] Connexion réussie, affichage popup dans 500ms');
                queueAttempt(500);
            }));
        }
    }

    // Ne PAS lancer queueAttempt() inconditionnellement ici
    // Le popup sera affiché UNIQUEMENT après auth:login:success

    return popup;
}
