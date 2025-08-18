/**
 * @module core/main
 * @description Entrée client statique — V35.2 (GIS + fetch patch)
 */

import { App } from './core/app.js';
import { EventBus } from './core/event-bus.js';
import { StateManager } from './core/state-manager.js';
import { WebSocketClient } from './core/websocket.js';
import { WS_CONFIG, EVENTS } from './shared/constants.js';
import { loadCSSBatch } from './core/utils.js';

const CSS_ORDERED = [
  'styles/core/_variables.css',
  'styles/core/reset.css',
  'styles/core/_layout.css',
  'styles/core/_typography.css',
  'styles/core/_navigation.css',
  'styles/main-styles.css',
  'features/chat/chat.css',
  'features/debate/debate.css',
  'features/documents/documents.css',
  'features/dashboard/dashboard.css'
];

class EmergenceClient {
  constructor() { this.initialize(); }

  async initialize() {
    console.log('🚀 ÉMERGENCE - Lancement du client.');

    const eventBus = new EventBus();
    const stateManager = new StateManager();
    await stateManager.init();

    await loadCSSBatch(CSS_ORDERED);

    const websocket = new WebSocketClient(WS_CONFIG.URL, eventBus, stateManager);
    eventBus.on(EVENTS.APP_READY, () => this.hideLoader());

    const app = new App(eventBus, stateManager);
    websocket.connect();

    // Auth & fetch patch non intrusifs
    this._setupAuthAndFetch();
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

  _setupAuthAndFetch() {
    const CLIENT_ID = window.EMERGENCE_GOOGLE_CLIENT_ID || '';
    let _idToken = null;
    let _email = null;

    // API publiques pour l’UI (optionnel)
    window.getIdToken = () => _idToken;
    window.signIn = () => { try { window.google?.accounts?.id?.prompt(); } catch(_){} };
    window.signOut = () => {
      try {
        if (window.google?.accounts?.id && _email) {
          window.google.accounts.id.disableAutoSelect();
          window.google.accounts.id.revoke(_email, () => {
            _idToken = null; _email = null;
            document.dispatchEvent(new CustomEvent('auth:changed', { detail: { signedIn:false, email:null } }));
          });
        } else {
          _idToken = null; _email = null;
          document.dispatchEvent(new CustomEvent('auth:changed', { detail: { signedIn:false, email:null } }));
        }
      } catch(e) {
        console.warn('[auth] signOut error:', e);
        _idToken = null; _email = null;
        document.dispatchEvent(new CustomEvent('auth:changed', { detail: { signedIn:false, email:null } }));
      }
    };

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
            try {
              const payloadStr = atob(_idToken.split('.')[1].replace(/-/g,'+').replace(/_/g,'/'));
              const payload = JSON.parse(payloadStr);
              _email = payload?.email || null;
            } catch {}
          } else {
            _email = null;
          }
          document.dispatchEvent(new CustomEvent('auth:changed', { detail: { signedIn: !!_idToken, email: _email } }));
        },
        auto_select: true,
        ux_mode: 'popup',
        itp_support: true
      });

      try { window.google.accounts.id.prompt(); } catch {}
      console.log('[auth] GIS initialisé.');
    };

    if (document.readyState === 'complete' || document.readyState === 'interactive') {
      setTimeout(initGIS, 0);
    } else {
      window.addEventListener('DOMContentLoaded', initGIS);
    }

    // Patch fetch: ajoute Authorization pour /api/*
    const _origFetch = window.fetch.bind(window);
    window.fetch = async (input, init = {}) => {
      try {
        const url = (typeof input === 'string') ? input : input?.url;
        const isApi = typeof url === 'string' && url.includes('/api/');
        if (isApi) {
          const headers = new Headers(init.headers || {});
          if (_idToken) {
            headers.set('Authorization', `Bearer ${_idToken}`);
          } else {
            try { window.google?.accounts?.id?.prompt(); } catch {}
            // Laisse passer → backend répondra 401 si nécessaire
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
