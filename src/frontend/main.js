/**
 * @module core/main
 * @description Point d'entrée universel - Version unifiée (post-Opération Unification Visuelle)
 * - Import CSS centralisé avec suppression des anciens fichiers obsolètes (buttons.css, cards.css, inputs.css, etc.).
 * - Initialise l'application ÉMERGENCE.
 */

// --- Imports CSS ---
import './styles/core/_variables.css';
import './styles/core/_base.css';
import './styles/core/_layout.css';
import './styles/core/_typography.css';
import './styles/core/_navigation.css';
import './styles/main-styles.css'; // Styles unifiés
import './features/chat/chat.css'; // Styles spécifiques chat
import './features/debate/debate.css'; // Styles spécifiques débat
import './features/documents/documents.css'; // ✅ Styles spécifiques documents
import './features/dashboard/dashboard.css'; // ✅ NEW: Styles cockpit (cartes KPI, grille, progress bars)

// --- Imports JAVASCRIPT ---
import { App } from './core/app.js';
import { EventBus } from './core/event-bus.js';
import { StateManager } from './core/state-manager.js';
import { WebSocketClient } from './core/websocket.js';
import { WS_CONFIG, EVENTS } from './shared/constants.js';

class EmergenceClient {
    constructor() {
        this.initialize();
    }

    async initialize() {
        console.log("🚀 ÉMERGENCE - Lancement du client.");

        const eventBus = new EventBus();
        const stateManager = new StateManager();
        await stateManager.init();

        const websocket = new WebSocketClient(WS_CONFIG.URL, eventBus, stateManager);

        eventBus.on(EVENTS.APP_READY, () => this.hideLoader());

        const app = new App(eventBus, stateManager);

        websocket.connect();

        console.log("✅ Client ÉMERGENCE prêt. En attente du signal APP_READY...");
    }

    hideLoader() {
        console.log("👍 Signal APP_READY reçu. Masquage du loader.");
        const loader = document.getElementById('app-loader');
        if (loader) {
            loader.classList.add('fade-out');
            setTimeout(() => {
                loader.remove();
                document.body.classList.remove('loading');
            }, 500);
        }
    }
}

window.emergenceApp = new EmergenceClient();
