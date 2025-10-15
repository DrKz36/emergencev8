/**
 * @module components/tutorial/TutorialNavigator
 * @description Système de navigation pour tutoriel et glossaire avec historique
 */

import { TutorialIcons } from './TutorialIcons.js';
import { TUTORIAL_GUIDES } from './tutorialGuides.js';

export class TutorialNavigator {
    constructor() {
        this.history = [];
        this.currentIndex = -1;
        this.container = null;
        this.onNavigate = null;
    }

    init(containerId, onNavigateCallback) {
        this.container = typeof containerId === 'string'
            ? document.getElementById(containerId)
            : containerId;

        this.onNavigate = onNavigateCallback;

        if (!this.container) {
            console.warn('[TutorialNavigator] Container not found', containerId);
            return;
        }

        this.render();
    }

    /**
     * Navigue vers un guide
     * @param {string} guideId - ID du guide
     */
    navigateTo(guideId) {
        // Supprimer l'historique après l'index actuel si on navigue depuis le milieu
        if (this.currentIndex < this.history.length - 1) {
            this.history = this.history.slice(0, this.currentIndex + 1);
        }

        // Ajouter le nouveau guide à l'historique
        this.history.push(guideId);
        this.currentIndex = this.history.length - 1;

        // Sauvegarder dans localStorage
        this.saveHistory();

        // Callback de navigation
        if (this.onNavigate) {
            this.onNavigate(guideId);
        }

        this.render();
    }

    /**
     * Retour arrière dans l'historique
     */
    goBack() {
        if (this.canGoBack()) {
            this.currentIndex--;
            const guideId = this.history[this.currentIndex];

            if (this.onNavigate) {
                this.onNavigate(guideId);
            }

            this.render();
        }
    }

    /**
     * Avancer dans l'historique
     */
    goForward() {
        if (this.canGoForward()) {
            this.currentIndex++;
            const guideId = this.history[this.currentIndex];

            if (this.onNavigate) {
                this.onNavigate(guideId);
            }

            this.render();
        }
    }

    /**
     * Retour à l'accueil (liste des guides)
     */
    goHome() {
        this.navigateTo('home');
    }

    canGoBack() {
        return this.currentIndex > 0;
    }

    canGoForward() {
        return this.currentIndex < this.history.length - 1;
    }

    getCurrentGuide() {
        if (this.currentIndex >= 0 && this.currentIndex < this.history.length) {
            return this.history[this.currentIndex];
        }
        return null;
    }

    /**
     * Sauvegarde l'historique dans localStorage
     */
    saveHistory() {
        try {
            localStorage.setItem('tutorial_history', JSON.stringify({
                history: this.history,
                currentIndex: this.currentIndex
            }));
        } catch (err) {
            console.warn('[TutorialNavigator] Failed to save history', err);
        }
    }

    /**
     * Restaure l'historique depuis localStorage
     */
    loadHistory() {
        try {
            const saved = localStorage.getItem('tutorial_history');
            if (saved) {
                const data = JSON.parse(saved);
                this.history = data.history || [];
                this.currentIndex = data.currentIndex ?? -1;
            }
        } catch (err) {
            console.warn('[TutorialNavigator] Failed to load history', err);
        }
    }

    /**
     * Efface l'historique
     */
    clearHistory() {
        this.history = [];
        this.currentIndex = -1;
        localStorage.removeItem('tutorial_history');
        this.render();
    }

    render() {
        if (!this.container) return;

        const canGoBack = this.canGoBack();
        const canGoForward = this.canGoForward();
        const currentGuide = this.getCurrentGuide();
        const currentGuideName = this.getGuideName(currentGuide);

        this.container.innerHTML = `
            <nav class="tutorial-navigator">
                <div class="navigator-controls">
                    <button
                        class="nav-btn nav-btn--back"
                        ${canGoBack ? '' : 'disabled'}
                        data-action="back"
                        title="Retour"
                    >
                        ${TutorialIcons.arrowLeft}
                    </button>

                    <button
                        class="nav-btn nav-btn--forward"
                        ${canGoForward ? '' : 'disabled'}
                        data-action="forward"
                        title="Suivant"
                    >
                        ${TutorialIcons.arrowRight}
                    </button>

                    <button
                        class="nav-btn nav-btn--home"
                        data-action="home"
                        title="Accueil"
                    >
                        ${TutorialIcons.home}
                    </button>
                </div>

                <div class="navigator-breadcrumb">
                    <span class="breadcrumb-item">
                        ${currentGuideName || 'Guides & Tutoriels'}
                    </span>
                </div>
            </nav>
        `;

        this.attachEventListeners();
    }

    attachEventListeners() {
        if (!this.container) return;

        const backBtn = this.container.querySelector('[data-action="back"]');
        const forwardBtn = this.container.querySelector('[data-action="forward"]');
        const homeBtn = this.container.querySelector('[data-action="home"]');

        if (backBtn) {
            backBtn.addEventListener('click', () => this.goBack());
        }

        if (forwardBtn) {
            forwardBtn.addEventListener('click', () => this.goForward());
        }

        if (homeBtn) {
            homeBtn.addEventListener('click', () => this.goHome());
        }
    }

    getGuideName(guideId) {
        if (!guideId || guideId === 'home') return null;

        const guide = TUTORIAL_GUIDES.find(g => g.id === guideId);
        return guide ? guide.title : guideId;
    }

    destroy() {
        this.history = [];
        this.currentIndex = -1;
        this.onNavigate = null;

        if (this.container) {
            this.container.innerHTML = '';
            this.container = null;
        }
    }
}

export const tutorialNavigator = new TutorialNavigator();
