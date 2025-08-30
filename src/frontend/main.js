/**
 * @module core/main
 * Point d'entrée universel — PROD sans bundler : aucun import CSS ici.
 */
import { App } from './core/app.js';
import { EventBus } from './core/event-bus.js';
import { StateManager } from './core/state-manager.js';
import { WebSocketClient } from './core/websocket.js';
import { WS_CONFIG, EVENTS } from './shared/constants.js';

/* ---------------- Helpers token ---------------- */
function getCookie(name) {
  const m = document.cookie.match(new RegExp('(?:^|; )' + name + '=([^;]*)'));
  return m ? decodeURIComponent(m[1]) : null;
}
function getAnyToken() {
  return (
    localStorage.getItem('emergence.id_token') ||
    localStorage.getItem('id_token') ||
    sessionStorage.getItem('id_token') ||
    getCookie('id_token') ||
    ''
  ).trim();
}
function hasToken() { return !!getAnyToken(); }
function openDevAuth() {
  // Ouverture explicite (évite blocage popup si déclenché par clic)
  try { window.open('/dev-auth.html', '_blank', 'noopener,noreferrer'); } catch {}
}

/* --------------- Badge Login (CTA + voyant) --------------- */
function mountAuthBadge(eventBus) {
  const host = document.body;
  let box = document.getElementById('auth-badge');
  if (!box) {
    box = document.createElement('div');
    box.id = 'auth-badge';
    box.style.cssText = 'position:fixed;top:12px;right:12px;z-index:2147483647;display:flex;gap:.5rem;align-items:center;font-family:system-ui,Segoe UI,Roboto,Arial;color:#eee;pointer-events:auto;';
    box.innerHTML = `
      <span id="auth-dot" style="width:10px;height:10px;border-radius:50%;background:#f97316;display:inline-block"></span>
      <button id="auth-btn" type="button" style="padding:.35rem .75rem;border-radius:999px;border:1px solid #666;background:#111;color:#eee;cursor:pointer;pointer-events:auto">Se connecter</button>
    `;
    host.appendChild(box);
  }
  const dot = box.querySelector('#auth-dot');
  const btn = box.querySelector('#auth-btn');

  const setConnected = (ok) => { if (dot) dot.style.background = ok ? '#22c55e' : '#f97316'; };
  const setLogged = (logged) => {
    if (!btn) return;
    btn.textContent = logged ? 'Se déconnecter' : 'Se connecter';
    btn.onclick = logged
      ? () => eventBus.emit('auth:logout')
      : () => {
          eventBus.emit('auth:login', {});        // ⇦ ne jamais émettre null
          // Si pas de token dans les 300 ms → fallback dev-auth
          setTimeout(() => { if (!hasToken()) openDevAuth(); }, 300);
        };
  };

  // Abonnements d’état
  eventBus.on?.('auth:missing', () => { setLogged(false); setConnected(false); });
  eventBus.on?.('auth:logout', () => { setLogged(false); setConnected(false); });
  eventBus.on?.(EVENTS.WS_CONNECTED || 'ws:connected', () => { setLogged(true); setConnected(true); });
  eventBus.on?.('ws:close', () => { setConnected(false); });

  // Sync multi-onglets + compat clés ('emergence.id_token' | 'id_token')
  try {
    window.addEventListener('storage', (ev) => {
      if (ev.key === 'emergence.id_token' || ev.key === 'id_token') {
        const has = !!(ev.newValue && ev.newValue.trim());
        setLogged(has);
      }
    });
  } catch {}

  // Délégation de clic globale : tout bouton/lien "Se connecter" déclenche l’auth
  document.addEventListener('click', (e) => {
    const t = e.target && (e.target.closest?.('button, a') || e.target);
    if (!t) return;
    const label = (t.innerText || t.textContent || '').trim().toLowerCase();
    if (label === 'se connecter') {
      e.preventDefault();
      if (hasToken()) { eventBus.emit('auth:login', {}); return; }
      eventBus.emit('auth:login', {});
      setTimeout(() => { if (!hasToken()) openDevAuth(); }, 300);
    }
  }, { capture: true });

  setLogged(hasToken()); setConnected(false);
  return { setLogged, setConnected };
}

/* -------------------- App bootstrap -------------------- */
class EmergenceClient {
  constructor() { this.initialize(); }

  async initialize() {
    console.log("🚀 ÉMERGENCE - Lancement du client.");

    const eventBus = new EventBus();
    const stateManager = new StateManager();
    await stateManager.init();

    const badge = mountAuthBadge(eventBus);

    const websocket = new WebSocketClient(WS_CONFIG.URL, eventBus, stateManager);
    eventBus.on(EVENTS.APP_READY, () => this.hideLoader());

    const app = new App(eventBus, stateManager);

    // Auth initiale : si token présent → connect WS ; sinon → signaler missing
    if (hasToken()) {
      badge.setLogged(true);
      websocket.connect();
    } else {
      try { eventBus.emit('auth:missing'); } catch (_) {}
    }

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
