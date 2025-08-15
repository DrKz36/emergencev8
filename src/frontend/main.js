/**
 * @module core/main
 * @description Entrée client statique — V35.1
 *  - Charge les CSS via <link> (pas d'import ESM de .css) pour compat Cloud Run / mobile.
 *  - Initialise EventBus, StateManager, WebSocketClient et App.
 */

import { App } from './core/app.js';
import { EventBus } from './core/event-bus.js';
import { StateManager } from './core/state-manager.js';
import { WebSocketClient } from './core/websocket.js';
import { WS_CONFIG, EVENTS } from './shared/constants.js';
import { loadCSSBatch } from './core/utils.js';

// --- CSS à charger (ordre: variables → reset → layout/typo → modules) ---
const CSS_ORDERED = [
  'styles/core/_variables.css',
  'styles/core/reset.css',
  'styles/core/_layout.css',
  'styles/core/_typography.css',
  'styles/core/_navigation.css',
  'styles/main-styles.css',

  // Features
  'features/chat/chat.css',
  'features/debate/debate.css',
  'features/documents/documents.css',
  'features/dashboard/dashboard.css'
];

// Démarrage client
class EmergenceClient {
  constructor() { this.initialize(); }

  async initialize() {
    console.log('🚀 ÉMERGENCE - Lancement du client.');

    // 1) Bus & state
    const eventBus = new EventBus();
    const stateManager = new StateManager();
    await stateManager.init();

    // 2) CSS en séquence (limite FOUC)
    await loadCSSBatch(CSS_ORDERED);

    // 3) WebSocket + App
    const websocket = new WebSocketClient(WS_CONFIG.URL, eventBus, stateManager);
    eventBus.on(EVENTS.APP_READY, () => this.hideLoader());

    const app = new App(eventBus, stateManager);
    websocket.connect();

    console.log('✅ Client ÉMERGENCE prêt. En attente du signal APP_READY...');
  }

  hideLoader() {
    const loader = document.getElementById('app-loader');
    if (!loader) return;
    loader.classList.add('fade-out');
    setTimeout(() => {
      loader.remove();
      document.body.classList.remove('loading');
    }, 500);
  }
}

window.emergenceApp = new EmergenceClient();
