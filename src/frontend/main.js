/**
 * @module core/main
 * @description Entrée client statique — V36.3
 *  - GIS exposé globalement (globalThis.*)
 *  - fetch patché: ajoute Authorization: Bearer <id_token> sur /api/*
 *  - 🔧 Sync token vers localStorage(AUTH.TOKEN_KEY) pour WS/API (cohérence)
 */

import { App } from './core/app.js';
import { EventBus } from './core/event-bus.js';
import { StateManager } from './core/state-manager.js';
import { WebSocketClient } from './core/websocket.js';
import { WS_CONFIG, EVENTS, AUTH } from './shared/constants.js';
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

/* =========================
   AUTH: Google Identity Services
   ========================= */
const CLIENT_ID = window.EMERGENCE_GOOGLE_CLIENT_ID || '';

let _idToken = sessionStorage.getItem('emergence_id_token') || '';
let _email = null;
let _tokenExp = Number(sessionStorage.getItem('emergence_id_token_exp') || '0');

// 🔁 Fallback: si un token existe déjà en localStorage(AUTH.TOKEN_KEY), on le reprend au boot
try {
  if (!_idToken) {
    const t = localStorage.getItem(AUTH?.TOKEN_KEY);
    if (t) {
      // on passe par setToken pour bien hydrater exp/email + notifs
      _idToken = t;
      const seg = t.split('.')[1];
      const p = seg ? JSON.parse(atob(seg.replace(/-/g, '+').replace(/_/g, '/'))) : {};
      _email = p?.email || null;
      _tokenExp = (p?.exp || 0) * 1000;
      sessionStorage.setItem('emergence_id_token', _idToken);
      sessionStorage.setItem('emergence_id_token_exp', String(_tokenExp));
    }
  }
} catch { /* no-op */ }

function decodeJwtPayload(token) {
  try {
    const seg = token.split('.')[1];
    return JSON.parse(atob(seg.replace(/-/g, '+').replace(/_/g, '/')));
  } catch { return {}; }
}

function setToken(token) {
  _idToken = token || '';
  let expMs = 0;
  let email = null;
  if (_idToken) {
    const p = decodeJwtPayload(_idToken);
    email = p?.email || null;
    expMs = (p?.exp || 0) * 1000;
  }
  _email = email;
  _tokenExp = expMs;

  // Session storage (historique)
  if (_idToken) {
    sessionStorage.setItem('emergence_id_token', _idToken);
    sessionStorage.setItem('emergence_id_token_exp', String(_tokenExp));
  } else {
    sessionStorage.removeItem('emergence_id_token');
    sessionStorage.removeItem('emergence_id_token_exp');
  }

  // 🔧 Local storage pour WS/API (AUTH.TOKEN_KEY)
  try {
    if (_idToken) {
      localStorage.setItem(AUTH?.TOKEN_KEY, _idToken);
    } else {
      localStorage.removeItem(AUTH?.TOKEN_KEY);
    }
  } catch { /* no-op */ }

  document.dispatchEvent(new CustomEvent('auth:changed', { detail: { signedIn: !!_idToken, email: _email } }));
}

function sdkReady() {
  return !!(window.google && window.google.accounts && window.google.accounts.id);
}
async function waitForSDK(timeoutMs = 8000) {
  const t0 = Date.now();
  while (!sdkReady()) {
    if (Date.now() - t0 > timeoutMs) throw new Error('GIS non chargé (timeout)');
    await new Promise(r => setTimeout(r, 50));
  }
}
async function initGIS() {
  if (!CLIENT_ID) {
    console.error('[auth] CLIENT_ID manquant (window.EMERGENCE_GOOGLE_CLIENT_ID).');
    return;
  }
  await waitForSDK();
  window.google.accounts.id.initialize({
    client_id: CLIENT_ID,
    callback: ({ credential }) => { if (credential) setToken(credential); },
    auto_select: true,
    ux_mode: 'popup',
    itp_support: true
  });
  try { window.google.accounts.id.prompt(); } catch {}
}
async function getIdToken() {
  const now = Date.now();
  if (_idToken && _tokenExp && now < (_tokenExp - 60_000)) return _idToken;
  // sinon, essaie d'en obtenir un (One Tap)
  try {
    await waitForSDK();
    let resolved = false;
    await window.google.accounts.id.prompt(() => {});
    for (let i = 0; i < 40; i++) { // ~2s
      if (_idToken) { resolved = true; break; }
      await new Promise(r => setTimeout(r, 50));
    }
    if (!resolved) throw new Error('ID token indisponible (refus/annulation ?)');
    return _idToken;
  } catch (e) {
    console.warn('[auth] Impossible d’obtenir un ID token:', e);
    throw e;
  }
}
function signIn() { try { window.google?.accounts?.id?.prompt(); } catch {} }
function signOut() {
  try {
    if (window.google?.accounts?.id && _email) {
      window.google.accounts.id.disableAutoSelect();
      window.google.accounts.id.revoke(_email, () => setToken(null));
    } else { setToken(null); }
  } catch (e) {
    console.warn('[auth] signOut error:', e);
    setToken(null);
  }
  // 🔧 Nettoyage localStorage (redondance)
  try { localStorage.removeItem(AUTH?.TOKEN_KEY); } catch {}
}

/* ✅ EXPOSITION IMMÉDIATE SUR LE GLOBAL (console/devtools) */
try {
  globalThis.getIdToken = getIdToken;
  globalThis.signIn = signIn;
  globalThis.signOut = signOut;
} catch {}

/* Patch global de fetch → ajoute Authorization pour /api/* */
function patchFetch() {
  const nativeFetch = window.fetch.bind(window);
  window.fetch = async (input, init = {}) => {
    try {
      const url = (typeof input === 'string') ? input : input?.url;
      const isApi = typeof url === 'string' && url.includes('/api/');
      if (isApi) {
        let token = _idToken;
        if (!token) {
          try { token = await getIdToken(); } catch { /* backend renverra 401 si pas de token */ }
        }
        const headers = new Headers(init.headers || {});
        if (token) headers.set('Authorization', `Bearer ${token}`);
        init = { ...init, headers };
      }
    } catch (e) {
      console.warn('[auth] fetch patch warning:', e);
    }
    return nativeFetch(input, init);
  };
}

/* =========================
   APP BOOTSTRAP
   ========================= */
class EmergenceClient {
  constructor() { this.initialize(); }

  async initialize() {
    console.log('🚀 ÉMERGENCE - Lancement du client.');

    const eventBus = new EventBus();
    const stateManager = new StateManager();
    await stateManager.init();

    await loadCSSBatch(CSS_ORDERED);

    // Auth d’abord (non bloquant pour l’UI), fetch patch ensuite
    try { await initGIS(); } catch (e) { console.error('[auth] initGIS:', e); }
    patchFetch();

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
