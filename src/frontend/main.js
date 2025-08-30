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
  try { window.open('/dev-auth.html', '_blank', 'noopener,noreferrer'); } catch {}
}

/* ---------------------- Toast minimal ---------------------- */
function mountToastHost() {
  let host = document.getElementById('toast-host');
  if (host) return host;
  host = document.createElement('div');
  host.id = 'toast-host';
  host.style.cssText = 'position:fixed;bottom:16px;right:16px;z-index:2147483647;display:flex;flex-direction:column;gap:8px;pointer-events:none';
  document.body.appendChild(host);
  return host;
}
function showToast({ kind = 'info', text = '' } = {}) {
  const host = mountToastHost();
  const card = document.createElement('div');
  card.role = 'status';
  card.style.cssText = 'min-width:260px;max-width:420px;padding:.6rem .8rem;border-radius:12px;background:#111a;color:#eee;border:1px solid #333;box-shadow:0 10px 30px rgba(0,0,0,.45);pointer-events:auto';
  const chip = kind === 'warning' ? '#f59e0b' : (kind === 'error' ? '#ef4444' : '#22c55e');
  card.innerHTML = `<div style="display:flex;align-items:center;gap:.6rem">
    <span style="width:10px;height:10px;border-radius:50%;background:${chip};display:inline-block"></span>
    <div style="font-family:system-ui,Segoe UI,Roboto,Arial;font-size:.95rem;line-height:1.3">${text}</div>
  </div>`;
  host.appendChild(card);
  setTimeout(() => { try { card.remove(); } catch {} }, 3200);
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
      <span id="model-chip" style="display:none;padding:.2rem .5rem;border-radius:999px;border:1px solid #555;background:#0b0b0b;color:#ddd;font-size:.8rem"></span>
    `;
    host.appendChild(box);
  }
  const dot = box.querySelector('#auth-dot');
  const btn = box.querySelector('#auth-btn');
  const chip = box.querySelector('#model-chip');

  const setConnected = (ok) => { if (dot) dot.style.background = ok ? '#22c55e' : '#f97316'; };
  const setLogged = (logged) => {
    if (!btn) return;
    btn.textContent = logged ? 'Se déconnecter' : 'Se connecter';
    btn.onclick = logged
      ? () => eventBus.emit('auth:logout')
      : () => {
          eventBus.emit('auth:login', {});
          setTimeout(() => { if (!hasToken()) openDevAuth(); }, 300);
        };
  };
  const setModel = (provider, model, fallback = false) => {
    if (!chip) return;
    const txt = provider && model ? `${provider} • ${model}${fallback ? ' (fallback)' : ''}` : '';
    chip.textContent = txt;
    chip.style.display = txt ? 'inline-block' : 'none';
  };

  // Abonnements d’état
  eventBus.on?.('auth:missing', () => { setLogged(false); setConnected(false); });
  eventBus.on?.('auth:logout', () => { setLogged(false); setConnected(false); });
  eventBus.on?.(EVENTS.WS_CONNECTED || 'ws:connected', () => { setLogged(true); setConnected(true); });
  eventBus.on?.('ws:close', () => { setConnected(false); });
  // Nouveaux hooks fallback
  eventBus.on?.('chat:model_info', (p) => { if (p) setModel(p.provider, p.model, false); });
  eventBus.on?.('chat:last_message_meta', (meta) => { if (meta) setModel(meta.provider, meta.model, !!meta.fallback); });

  // Sync multi-onglets + compat clés
  try {
    window.addEventListener('storage', (ev) => {
      if (ev.key === 'emergence.id_token' || ev.key === 'id_token') {
        const has = !!(ev.newValue && ev.newValue.trim());
        setLogged(has);
      }
    });
  } catch {}

  // Délégation : tout bouton/lien "Se connecter" déclenche l’auth
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

    // Toasts
    eventBus.on('ui:toast', (p) => { if (p?.text) showToast(p); });

    const badge = mountAuthBadge(eventBus);

    const websocket = new WebSocketClient(WS_CONFIG.URL, eventBus, stateManager);
    eventBus.on(EVENTS.APP_READY, () => this.hideLoader());

    const app = new App(eventBus, stateManager);

    // Auth initiale
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
