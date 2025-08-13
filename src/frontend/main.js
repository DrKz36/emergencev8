/**
 * @module core/main
 * @description Entrée client (statique) — chargement CSS via <link> pour compat mobile.
 *              On évite tout import ESM de .css (non supporté sans bundler).
 */

// --- JS uniquement ---
import { App } from './core/app.js';
import { EventBus } from './core/event-bus.js';
import { StateManager } from './core/state-manager.js';
import { WebSocketClient } from './core/websocket.js';
import { WS_CONFIG, EVENTS } from './shared/constants.js';
import { loadCSS } from './core/utils.js'; // util existant pour injecter des <link> . :contentReference[oaicite:4]{index=4}

// --- Feuilles de style à charger (ordre important : variables → reset → layout/typo → reste) ---
[
  'styles/core/_variables.css',   // tokens & palette Aura . :contentReference[oaicite:5]{index=5}
  'styles/core/reset.css',        // reset V7.1 mobile-safe . :contentReference[oaicite:6]{index=6}
  'styles/core/_layout.css',      // layout responsive + safe areas . :contentReference[oaicite:7]{index=7}
  'styles/core/_typography.css',  // typo fluide . :contentReference[oaicite:8]{index=8}
  'styles/core/_navigation.css',  // styles de nav (sidebar/header) . :contentReference[oaicite:9]{index=9}
  'styles/main-styles.css',
  'features/chat/chat.css',
  'features/debate/debate.css',
  'features/documents/documents.css',
  'features/dashboard/dashboard.css'
].forEach(loadCSS);

class EmergenceClient {
  constructor() { this.initialize(); }

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
