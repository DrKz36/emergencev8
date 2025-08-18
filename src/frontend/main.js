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

    // 4) Auth Google (GIS) + fetch patch (non intrusifs)
    this._setupAuthAndFetch(eventBus);
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

  _setupAuthAndFetch(eventBus) {
    const CLIENT_ID = window.EMERGENCE_GOOGLE_CLIENT_ID || '';
    let _idToken = null;
    let _email = null;

    // --- Helpers publics (ex: pour un bouton "Déconnexion" dans l'UI)
    window.getIdToken = () => _idToken;
    window.signIn = () => {
      if (window.google?.accounts?.id) {
        try { window.google.accounts.id.prompt(); } catch (_) {}
      }
    };
    window.signOut = () => {
      try {
        if (window.google?.accounts?.id && _email) {
          window.google.accounts.id.disableAutoSelect();
          window.google.accounts.id.revoke(_email, () => {
            _idToken = null; _email = null;
            document.dispatchEvent(new CustomEvent('auth:changed', { detail: { signedIn: false, email: null } }));
          });
        } else {
          _idToken = null; _email = null;
          document.dispatchEvent(new CustomEvent('auth:changed', { detail: { signedIn: false, email: null } }));
        }
      } catch (e) {
        console.warn('[auth] signOut error:', e);
        _idToken = null; _email = null;
        document.dispatchEvent(new CustomEvent('auth:changed', { detail: { signedIn: false, email: null } }));
      }
    };

    // --- Init GIS quand le SDK est prêt
    const initGIS = () => {
      if (!CLIENT_ID) {
        console.error('[auth] CLIENT_ID manquant. Renseigne window.EMERGENCE_GOOGLE_CLIENT_ID dans index.html');
        return;
      }
      if (!window.google?.accounts?.id) return;

      window.google.accounts.id.initialize({
        client_id: CLIENT_ID,
        callback: (response) => {
          const token = response?.credential || null;
          _idToken = token;
          if (_idToken) {
            // best-effort: extraire email du payload JWT (non une preuve !)
            try {
              const payloadStr = atob(_idToken.split('.')[1].replace(/-/g,'+').replace(/_/g,'/'));
              const payload = JSON.parse(payloadStr);
              _email = payload?.email || null;
            } catch (_) { /* noop */ }
          } else {
            _email = null;
          }
          document.dispatchEvent(new CustomEvent('auth:changed', { detail: { signedIn: !!_idToken, email: _email } }));
        },
        auto_select: true,
        ux_mode: 'popup',
        itp_support: true
      });

      // Tente One Tap (silencieux si pas possible)
      try { window.google.accounts.id.prompt(); } catch (_) {}
      console.log('[auth] GIS initialisé.');
    };

    // Si le SDK est déjà dispo → init direct ; sinon attend son chargement
    if (document.readyState === 'complete' || document.readyState === 'interactive') {
      setTimeout(() => initGIS(), 0);
    } else {
      window.addEventListener('DOMContentLoaded', () => initGIS());
    }

    // --- Patch global de fetch : ajoute Authorization pour /api/*
    const _origFetch = window.fetch.bind(window);
    window.fetch = async (input, init = {}) => {
      try {
        const url = (typeof input === 'string') ? input : input?.url;
        const isApi = typeof url === 'string' && url.includes('/api/');
        if (isApi) {
          const headers = new Headers(init.headers || {});
          if (!_idToken) {
            // Essaie d’obtenir un token (One Tap) si absent
            try { window.google?.accounts?.id?.prompt(); } catch (_) {}
            // Laisse passer la requête sans token (backend répondra 401)
          } else {
            headers.set('Authorization', `Bearer ${_idToken}`);
          }
          init = { ...init, headers };
        }
      } catch (e) {
        console.warn('[auth] fetch patch warning:', e);
      }
      return _origFetch(input, init);
    };
  }
}

window.emergenceApp = new EmergenceClient();
