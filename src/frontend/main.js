/**
 * @module core/main
 * Point d'entrée universel — PROD sans bundler : aucun import CSS ici.
 */

import { App } from './core/app.js';
import { EventBus } from './core/event-bus.js';
import { StateManager } from './core/state-manager.js';
import { WebSocketClient } from './core/websocket.js';
import { WS_CONFIG, EVENTS } from './shared/constants.js';

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
    if (!loader) return;
    loader.classList.add('fade-out');
    setTimeout(() => { try { loader.remove(); } catch {} document.body.classList.remove('loading'); }, 300);
  }
}

window.emergenceApp = new EmergenceClient();
