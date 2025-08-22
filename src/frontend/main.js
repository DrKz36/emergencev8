/**
 * @module core/main
 * @description Entrée client — V36.5 (fetch non-bloquant + singletons + GIS async)
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

/* ===== AUTH: Google Identity Services (non bloquant) ===== */
const CLIENT_ID = window.EMERGENCE_GOOGLE_CLIENT_ID || '';

let _idToken = sessionStorage.getItem('emergence_id_token') || '';
let _email = null;
let _tokenExp = Number(sessionStorage.getItem('emergence_id_token_exp') || '0');

function decodeJwtPayload(token) {
  try {
    const seg = token.split('.')[1];
    return JSON.parse(atob(seg.replace(/-/g, '+').replace(/_/g, '/')));
  } catch { return {}; }
}

function setToken(token) {
  _idToken = token || '';
  let expMs = 0; let email = null;
  if (_idToken) {
    const p = decodeJwtPayload(_idToken);
    email = p?.email || null;
    expMs = (p?.exp || 0) * 1000;
  }
  _email = email; _tokenExp = expMs;

  if (_idToken) {
    sessionStorage.setItem('emergence_id_token', _idToken);
    sessionStorage.setItem('emergence_id_token_exp', String(_tokenExp));
    try { localStorage.setItem(AUTH?.TOKEN_KEY, _idToken); } catch {}
  } else {
    sessionStorage.removeItem('emergence_id_token');
    sessionStorage.removeItem('emergence_id_token_exp');
    try { localStorage.removeItem(AUTH?.TOKEN_KEY); } catch {}
  }

  document.dispatchEvent(new CustomEvent('auth:changed', { detail: { signedIn: !!_idToken, email: _email } }));
}

function sdkReady() { return !!(window.google && window.google.accounts && window.google.accounts.id); }
async function waitForSDK(timeoutMs = 8000) {
  const t0 = Date.now();
  while (!sdkReady()) {
    if (Date.now() - t0 > timeoutMs) throw new Error('GIS non chargé (timeout)');
    await new Promise(r => setTimeout(r, 50));
  }
}
async function initGIS() {
  if (!CLIENT_ID) return;
  try {
    await waitForSDK();
    window.google.accounts.id.initialize({
      client_id: CLIENT_ID,
      callback: ({ credential }) => { if (credential) setToken(credential); },
      auto_select: true, ux_mode: 'popup', itp_support: true
    });
    try { window.google.accounts.id.prompt(); } catch {}
  } catch (e) {
    console.warn('[auth] initGIS:', e);
  }
}
function signIn() { try { window.google?.accounts?.id?.prompt(); } catch {} }
function signOut() {
  try {
    if (window.google?.accounts?.id && _email) {
      window.google.accounts.id.disableAutoSelect();
      window.google.accounts.id.revoke(_email, () => setToken(null));
    } else { setToken(null); }
  } catch { setToken(null); }
}

try { globalThis.getIdToken = () => _idToken; globalThis.signIn = signIn; globalThis.signOut = signOut; } catch {}

/* ✅ fetch NON BLOQUANT + fallback dev */
function patchFetchNonBlocking() {
  const nativeFetch = window.fetch.bind(window);
  window.fetch = (input, init = {}) => {
    try {
      const url = (typeof input === 'string') ? input : (input && input.url) || '';
      const isApi = url.includes('/api/');
      if (isApi) {
        const headers = new Headers(init.headers || {});
        const token = _idToken || (AUTH && typeof AUTH.getToken === 'function' ? AUTH.getToken() : null);
        if (token) headers.set('Authorization', `Bearer ${token}`);
        else if (['localhost','127.0.0.1'].includes(location.hostname) || /^192\.168\./.test(location.hostname)) {
          headers.set('X-User-Id', 'dev_alice'); // fallback dev
        }
        init = { ...init, headers };
      }
    } catch { /* no-op */ }
    return nativeFetch(input, init);
  };
}

/* ===== BOOTSTRAP ===== */
class EmergenceClient {
  constructor() { this.initialize(); }

  async initialize() {
    console.log('🚀 ÉMERGENCE - Lancement du client.');

    const eventBus = (window.__eventBus ||= new EventBus());
    const stateManager = (window.__stateManager ||= new StateManager());
    if (!window.__stateInitDone) { await stateManager.init(); window.__stateInitDone = true; }

    await loadCSSBatch(CSS_ORDERED);

    patchFetchNonBlocking();
    initGIS(); // async, non bloquant

    const websocket = (window.__wsClient ||= new WebSocketClient(WS_CONFIG.URL, eventBus, stateManager));
    eventBus.on(EVENTS.APP_READY, () => this.hideLoader());

    const app = new App(eventBus, stateManager);
    websocket.connect();

    console.log('✅ Client ÉMERGENCE prêt. En attente du signal APP_READY...');
  }

  hideLoader() {
    const loader = document.getElementById('app-loader');
    if (!loader) return;
    loader.classList.add('fade-out');
    setTimeout(() => { loader.remove(); document.body.classList.remove('loading'); }, 500);
  }
}

window.emergenceApp = new EmergenceClient();
