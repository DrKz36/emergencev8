/**
 * @module utils/glossary-navigation
 * @description Système de navigation pour le glossaire avec historique de position de scroll
 */

export class GlossaryNavigator {
    constructor() {
        this.scrollHistory = [];
        this.backButton = null;
        this.currentScrollPosition = 0;
        this.scrollContainer = null;
    }

    /**
     * Détecte le conteneur de scroll actif
     */
    getScrollContainer() {
        // Si déjà détecté et que ce n'est pas window, vérifier s'il existe toujours
        if (this.scrollContainer && this.scrollContainer !== window) {
            if (document.body.contains(this.scrollContainer)) {
                return this.scrollContainer;
            } else {
                // Le conteneur n'existe plus, réinitialiser
                this.scrollContainer = null;
            }
        }

        // Si c'est window et déjà défini, retourner
        if (this.scrollContainer === window) {
            return window;
        }

        // Liste des conteneurs potentiels, par ordre de priorité
        const potentialContainers = [
            '.documentation-modal-body',
            '#tab-content-documentation',
            '.tab-content.active',
            '.app-content',
            '.doc-content',
            '.documentation-page'
        ];

        for (const selector of potentialContainers) {
            const container = document.querySelector(selector);
            if (container) {
                // Vérifier si le conteneur a du scroll
                const hasScroll = container.scrollHeight > container.clientHeight;
                const computedStyle = window.getComputedStyle(container);
                const hasOverflow = computedStyle.overflowY === 'auto' || computedStyle.overflowY === 'scroll';

                console.log(`[GlossaryNavigator] Checking ${selector}: hasScroll=${hasScroll}, hasOverflow=${hasOverflow}, scrollTop=${container.scrollTop}`);

                if (hasScroll || hasOverflow || container.scrollTop > 0) {
                    console.log(`[GlossaryNavigator] Using ${selector} as scroll container`);
                    this.scrollContainer = container;
                    return container;
                }
            }
        }

        // Sinon utiliser window
        console.log('[GlossaryNavigator] Using window as scroll container');
        this.scrollContainer = window;
        return window;
    }

    /**
     * Obtient la position de scroll actuelle
     */
    getCurrentScrollPosition() {
        const container = this.getScrollContainer();
        if (container === window) {
            return window.scrollY || window.pageYOffset;
        }
        return container.scrollTop;
    }

    /**
     * Initialise le navigateur de glossaire
     */
    init() {
        console.log('[GlossaryNavigator] Initializing...');
        this.loadHistoryFromStorage();
        this.createBackButton();
        this.attachScrollListener();
        this.enhanceGlossaryLinks();
        console.log('[GlossaryNavigator] Initialization complete');
    }

    /**
     * Charge l'historique depuis localStorage
     */
    loadHistoryFromStorage() {
        try {
            const saved = localStorage.getItem('glossary_scroll_history');
            if (saved) {
                this.scrollHistory = JSON.parse(saved);
                console.log('[GlossaryNavigator] Loaded history from storage:', this.scrollHistory.length, 'entries');
                // Afficher le bouton si l'historique n'est pas vide
                if (this.scrollHistory.length > 0) {
                    setTimeout(() => {
                        console.log('[GlossaryNavigator] Showing back button from loaded history');
                        this.showBackButton();
                    }, 500);
                }
            } else {
                console.log('[GlossaryNavigator] No history found in storage');
            }
        } catch (e) {
            console.warn('[GlossaryNavigator] Failed to load history from localStorage', e);
            this.scrollHistory = [];
        }
    }

    /**
     * Crée le bouton "Retour" flottant
     */
    createBackButton() {
        // Vérifier si le bouton existe déjà
        if (document.getElementById('glossary-back-btn')) {
            console.log('[GlossaryNavigator] Back button already exists');
            this.backButton = document.getElementById('glossary-back-btn');
            return;
        }

        console.log('[GlossaryNavigator] Creating back button');

        const button = document.createElement('button');
        button.id = 'glossary-back-btn';
        button.className = 'glossary-back-button hidden';
        button.setAttribute('aria-label', 'Retour à la position précédente');
        button.innerHTML = `
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M19 12H5M12 19l-7-7 7-7"/>
            </svg>
            <span>Retour</span>
        `;

        button.addEventListener('click', () => {
            console.log('[GlossaryNavigator] Back button clicked');
            this.goBack();
        });
        document.body.appendChild(button);
        this.backButton = button;

        console.log('[GlossaryNavigator] Back button created and appended to body');

        // Ajouter les styles CSS si nécessaire
        this.injectStyles();
    }

    /**
     * Injecte les styles CSS pour le bouton de retour
     */
    injectStyles() {
        if (document.getElementById('glossary-nav-styles')) {
            return;
        }

        const style = document.createElement('style');
        style.id = 'glossary-nav-styles';
        style.textContent = `
            .glossary-back-button {
                position: fixed;
                bottom: 2rem;
                right: 2rem;
                display: flex;
                align-items: center;
                gap: 0.5rem;
                padding: 0.75rem 1.25rem;
                background: var(--accent-color, #64B5F6);
                color: white;
                border: none;
                border-radius: 50px;
                font-size: 0.9rem;
                font-weight: 500;
                cursor: pointer;
                box-shadow: 0 4px 12px rgba(100, 181, 246, 0.4);
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                z-index: 1000;
                opacity: 1;
                transform: translateY(0);
            }

            .glossary-back-button.hidden {
                opacity: 0;
                transform: translateY(20px);
                pointer-events: none;
            }

            .glossary-back-button:hover {
                background: var(--accent-color-hover, #5BA3E0);
                box-shadow: 0 6px 16px rgba(100, 181, 246, 0.5);
                transform: translateY(-2px);
            }

            .glossary-back-button:active {
                transform: translateY(0);
            }

            .glossary-back-button svg {
                width: 18px;
                height: 18px;
            }

            /* Responsive */
            @media (max-width: 768px) {
                .glossary-back-button {
                    bottom: 1rem;
                    right: 1rem;
                    padding: 0.65rem 1rem;
                    font-size: 0.85rem;
                }

                .glossary-back-button span {
                    display: none;
                }

                .glossary-back-button svg {
                    width: 20px;
                    height: 20px;
                }
            }

            /* Style pour les liens de glossaire */
            a[href^="#"]:not(.doc-nav-link):not(.nav-btn) {
                color: var(--accent-color, #64B5F6);
                text-decoration: underline;
                text-decoration-style: dotted;
                text-decoration-thickness: 1px;
                text-underline-offset: 2px;
                transition: all 0.2s ease;
            }

            a[href^="#"]:not(.doc-nav-link):not(.nav-btn):hover {
                color: var(--accent-color-hover, #5BA3E0);
                text-decoration-style: solid;
            }

            /* Highlight pour la cible */
            :target {
                animation: glossary-highlight 1.5s ease-out;
                scroll-margin-top: 2rem;
            }

            @keyframes glossary-highlight {
                0% {
                    background-color: rgba(100, 181, 246, 0.2);
                }
                100% {
                    background-color: transparent;
                }
            }
        `;
        document.head.appendChild(style);
    }

    /**
     * Améliore les liens du glossaire avec la navigation
     */
    enhanceGlossaryLinks() {
        // Observer pour détecter les nouveaux liens ajoutés dynamiquement
        const observer = new MutationObserver(() => {
            this.attachLinkListeners();
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true
        });

        // Attacher les listeners initiaux
        this.attachLinkListeners();
    }

    /**
     * Attache les listeners sur les liens de glossaire
     */
    attachLinkListeners() {
        // Sélectionner tous les liens internes (hash links) qui ne sont pas déjà gérés
        const links = document.querySelectorAll('a[href^="#"]:not([data-glossary-enhanced]):not(.doc-nav-link):not(.btn-load-tutorial)');

        console.log('[GlossaryNavigator] Found', links.length, 'links to enhance');

        links.forEach(link => {
            // Marquer comme géré
            link.setAttribute('data-glossary-enhanced', 'true');

            link.addEventListener('click', (e) => {
                const href = link.getAttribute('href');

                // Vérifier si c'est un lien vers une définition de glossaire
                if (href && href.startsWith('#') && href.length > 1) {
                    console.log('[GlossaryNavigator] Link clicked:', href);

                    // Empêcher le comportement par défaut pour avoir un meilleur contrôle
                    e.preventDefault();

                    // Sauvegarder la position de l'élément cliqué (le lien lui-même)
                    // pour pouvoir y revenir exactement
                    this.saveScrollPositionForElement(link, href);
                    this.showBackButton();

                    console.log('[GlossaryNavigator] Position saved, showing back button');

                    // Mettre à jour l'URL avec le hash
                    if (window.history.pushState) {
                        window.history.pushState('', document.title, window.location.pathname + window.location.search + href);
                    }

                    // Scroll smooth vers la cible
                    setTimeout(() => {
                        const targetElement = document.querySelector(href);
                        if (targetElement) {
                            targetElement.scrollIntoView({
                                behavior: 'smooth',
                                block: 'start'
                            });
                        }
                    }, 100);
                }
            });
        });
    }

    /**
     * Sauvegarde la position de scroll actuelle
     */
    saveScrollPosition() {
        this.currentScrollPosition = this.getCurrentScrollPosition();

        // Ajouter l'URL actuelle (hash) pour mieux identifier la position
        const currentHash = window.location.hash;

        console.log('[GlossaryNavigator] Saving position:', this.currentScrollPosition, 'hash:', currentHash);

        this.scrollHistory.push({
            position: this.currentScrollPosition,
            hash: currentHash,
            timestamp: Date.now(),
            element: null
        });

        // Limiter l'historique à 20 entrées pour permettre plus de navigation
        if (this.scrollHistory.length > 20) {
            this.scrollHistory.shift();
        }

        // Sauvegarder dans localStorage pour persistance
        try {
            localStorage.setItem('glossary_scroll_history', JSON.stringify(this.scrollHistory));
        } catch (e) {
            console.warn('[GlossaryNavigator] Failed to save history to localStorage', e);
        }
    }

    /**
     * Sauvegarde la position d'un élément spécifique (pour revenir exactement à cet élément)
     */
    saveScrollPositionForElement(element, targetHash) {
        const container = this.getScrollContainer();

        // Calculer la position de l'élément par rapport au conteneur
        const elementRect = element.getBoundingClientRect();
        let elementPosition;

        if (container === window) {
            elementPosition = window.scrollY + elementRect.top;
        } else {
            const containerRect = container.getBoundingClientRect();
            elementPosition = container.scrollTop + (elementRect.top - containerRect.top);
        }

        console.log('[GlossaryNavigator] Saving element position:', elementPosition, 'target:', targetHash);

        // Créer un ID unique pour l'élément basé sur son contenu
        const elementId = `elem_${Date.now()}`;
        element.setAttribute('data-nav-id', elementId);

        this.scrollHistory.push({
            position: elementPosition,
            hash: '', // Le hash actuel (avant de naviguer vers la définition)
            targetHash: targetHash, // Le hash de la définition
            elementId: elementId, // ID de l'élément pour le retrouver
            timestamp: Date.now()
        });

        // Limiter l'historique
        if (this.scrollHistory.length > 20) {
            this.scrollHistory.shift();
        }

        // Sauvegarder dans localStorage
        try {
            // Pas de sauvegarde dans localStorage car les IDs d'éléments ne persistent pas
            // On garde juste en mémoire de session
        } catch (e) {
            console.warn('[GlossaryNavigator] Failed to save history', e);
        }
    }

    /**
     * Affiche le bouton de retour
     */
    showBackButton() {
        if (this.backButton) {
            this.backButton.classList.remove('hidden');
        }
    }

    /**
     * Masque le bouton de retour
     */
    hideBackButton() {
        if (this.backButton) {
            this.backButton.classList.add('hidden');
        }
    }

    /**
     * Retourne à la position précédente
     */
    goBack() {
        console.log('[GlossaryNavigator] goBack called, history length:', this.scrollHistory.length);

        if (this.scrollHistory.length === 0) {
            console.log('[GlossaryNavigator] No history, hiding button');
            this.hideBackButton();
            return;
        }

        // Récupérer la dernière position sauvegardée (sans la retirer pour l'instant)
        const previousEntry = this.scrollHistory[this.scrollHistory.length - 1];

        console.log('[GlossaryNavigator] Going back to:', previousEntry);

        // Restaurer le hash si nécessaire
        if (previousEntry.hash && previousEntry.hash !== window.location.hash) {
            if (window.history.pushState) {
                window.history.pushState('', document.title, window.location.pathname + window.location.search + previousEntry.hash);
            } else {
                window.location.hash = previousEntry.hash;
            }
        } else if (!previousEntry.hash && window.location.hash) {
            // Supprimer le hash si la position précédente n'en avait pas
            if (window.history.pushState) {
                window.history.pushState('', document.title, window.location.pathname + window.location.search);
            } else {
                window.location.hash = '';
            }
        }

        // Scroll smooth vers la position précédente
        setTimeout(() => {
            const container = this.getScrollContainer();
            const currentPos = this.getCurrentScrollPosition();

            // Si on a un elementId, essayer de retrouver l'élément et scroller dessus
            if (previousEntry.elementId) {
                const element = document.querySelector(`[data-nav-id="${previousEntry.elementId}"]`);
                if (element) {
                    console.log('[GlossaryNavigator] Scrolling to element:', previousEntry.elementId);
                    element.scrollIntoView({
                        behavior: 'smooth',
                        block: 'center'
                    });
                    return;
                }
            }

            // Sinon utiliser la position
            console.log('[GlossaryNavigator] Scrolling to position:', previousEntry.position, 'Current position:', currentPos, 'Container:', container === window ? 'window' : 'element');

            if (container === window) {
                window.scrollTo({
                    top: previousEntry.position,
                    behavior: 'smooth'
                });
            } else {
                container.scrollTo({
                    top: previousEntry.position,
                    behavior: 'smooth'
                });
            }
        }, 100);

        // MAINTENANT retirer l'entrée de l'historique après avoir navigué
        this.scrollHistory.pop();

        // Masquer le bouton si l'historique est vide après le retour
        setTimeout(() => {
            if (this.scrollHistory.length === 0) {
                console.log('[GlossaryNavigator] History empty after navigation, hiding button');
                this.hideBackButton();
            } else {
                console.log('[GlossaryNavigator] Still', this.scrollHistory.length, 'entries in history');
            }
        }, 500);

        // Sauvegarder dans localStorage
        try {
            localStorage.setItem('glossary_scroll_history', JSON.stringify(this.scrollHistory));
        } catch (e) {
            console.warn('[GlossaryNavigator] Failed to save history to localStorage', e);
        }
    }

    /**
     * Écoute les événements de scroll pour gérer l'affichage du bouton
     */
    attachScrollListener() {
        let scrollTimeout;

        window.addEventListener('scroll', () => {
            clearTimeout(scrollTimeout);

            scrollTimeout = setTimeout(() => {
                // Masquer le bouton si on est en haut de la page
                if (window.scrollY < 100 && this.scrollHistory.length === 0) {
                    this.hideBackButton();
                }
            }, 150);
        });
    }

    /**
     * Nettoie l'historique
     */
    clearHistory() {
        this.scrollHistory = [];
        this.hideBackButton();
        try {
            localStorage.removeItem('glossary_scroll_history');
        } catch (e) {
            console.warn('[GlossaryNavigator] Failed to clear history from localStorage', e);
        }
    }

    /**
     * Détruit le navigateur
     */
    destroy() {
        this.clearHistory();
        if (this.backButton) {
            this.backButton.remove();
            this.backButton = null;
        }

        const styles = document.getElementById('glossary-nav-styles');
        if (styles) {
            styles.remove();
        }
    }
}

// Instance globale
export const glossaryNavigator = new GlossaryNavigator();

// Exposer dans window pour un accès global
if (typeof window !== 'undefined') {
    window.glossaryNavigator = glossaryNavigator;
}

// Auto-initialisation au chargement du DOM
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        glossaryNavigator.init();
    });
} else {
    glossaryNavigator.init();
}
