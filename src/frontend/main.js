/**
 * @module core/main
 * Point d'entrée universel — PROD sans bundler : aucun import CSS ici.
 */
import { App } from './core/app.js';
import { EventBus } from './core/event-bus.js';
import { StateManager } from './core/state-manager.js';
import { WebSocketClient } from './core/websocket.js';
import { WS_CONFIG, EVENTS } from './shared/constants.js';

/* ---------------- WS-first Chat dedupe & reroute (main.js patch V1) ----------------
   - Empêche le doublon d'affichage du message utilisateur.
   - Reroute 'ui:chat:send' enrichi (__enriched:true) vers 'ws:send' (canal WebSocket).
   - Garde "stream en cours" + dédup par msg_uid (30s).
*/
(function () {
  try {
    const EB = (typeof EventBus !== 'undefined') ? EventBus : null;
    if (!EB || EB.__patched_dedupe_reroute) return;
    const proto = EB.prototype;
    const origEmit = proto.emit;
    let streamOpen = false;
    const seen = new Set();

    proto.emit = function(name, payload) {
      // État du flux
      if (name === 'ws:chat_stream_start') { streamOpen = true; }
      else if (name === 'ws:chat_stream_end' || name === 'ws:close') { streamOpen = false; }

      if (name === 'ui:chat:send') {
        const p = payload || {};
        const enriched = (p && p.__enriched === true);

        // 1) Pendant un stream, ignorer les envois "bruts" (tapotages)
        if (!enriched && streamOpen) {
          console.warn('[Guard/WS] ui:chat:send ignoré (stream en cours).');
          return;
        }

        // 2) Si "enrichi", router vers ws:send (sans réémettre ui:chat:send)
        if (enriched) {
          const uid = p.msg_uid || '';
          if (uid && seen.has(uid)) {
            console.warn('[Guard/Dedupe] ui:chat:send enrichi ignoré (dupe):', uid);
            return;
          }
          if (uid) { seen.add(uid); setTimeout(() => seen.delete(uid), 30000); }

          return origEmit.call(this, 'ws:send', {
            type: 'chat.message',
            payload: { text: p.text, agent_id: p.agent_id, use_rag: !!p.use_rag }
          });
        }
      }
      return origEmit.call(this, name, payload);
    };

    EB.__patched_dedupe_reroute = true;
    console.info('[main.js patch] WS-first Chat dedupe & reroute appliqué.');
  } catch (e) {
    console.error('[main.js patch] échec du patch', e);
  }
})();


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

/* ---------------------- Dédup/normalisation texte ---------------------- */
const INVISIBLES_RE = /[\u200B-\u200D\uFEFF\u00A0]/g; // ZWSP.., BOM, NBSP
const CURSOR_GLYPHS_RE = /[▍▌▎▏▮▯█]+$/;            // glyphs "curseur"
const BLOCKS_RE = /[\u2580-\u259F\u25A0-\u25FF]+$/; // blocks & geometric shapes
function normalizeForDedupe(s) {
  if (!s) return '';
  return String(s)
    .replace(INVISIBLES_RE, '')
    .replace(CURSOR_GLYPHS_RE, '')
    .replace(BLOCKS_RE, '')
    .replace(/\s+/g, ' ')
    .trim();
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

/* ---------------------- Guards EventBus (V3) ---------------------- */
function installEventBusGuards(eventBus) {
  if (!eventBus || eventBus.__guardsInstalled) return;
  eventBus.__guardsInstalled = true;

  // Verrou global "stream en cours" (pour le flux enrichi uniquement)
  let inFlight = false;
  eventBus.on?.('ws:chat_stream_start', () => { inFlight = true; });
  eventBus.on?.('ws:chat_stream_end',   () => { inFlight = false; });

  // Fenêtres
  const UI_DEDUP_MS = 800;    // anti double submit (UI)
  const WS_DEDUP_MS = 30000;  // anti double envoi (WS)

  // États séparés UI vs WS
  let lastUiAt = 0, lastUiTxtN = '';
  let lastWsAt = 0, lastWsTxtN = '', lastWsUid = '';

  const origEmit = eventBus.emit?.bind(eventBus);
  eventBus.emit = function(name, payload) {
    if (name !== 'ui:chat:send') {
      return origEmit ? origEmit(name, payload) : undefined;
    }

    const now = Date.now();
    const enriched = !!(payload && (payload.__enriched || payload.msg_uid));

    if (!enriched) {
      // ---------- UI → ChatModule ----------
      const txtN = normalizeForDedupe((payload && (payload.text || payload.content)) || '');
      if (txtN && txtN === lastUiTxtN && (now - lastUiAt) < UI_DEDUP_MS) {
        console.warn('[Guard/UI] ui:chat:send ignoré (double submit court).');
        return;
      }
      lastUiAt = now; lastUiTxtN = txtN;
      return origEmit ? origEmit(name, payload) : undefined;
    } else {
      // ---------- ChatModule → WebSocketClient ----------
      const txtN = normalizeForDedupe((payload && (payload.text || payload.content)) || '');
      const uid  = String((payload && (payload.msg_uid || payload.uid || payload.id)) || '');

      if (inFlight) {
        console.warn('[Guard/WS] ui:chat:send ignoré (stream en cours).');
        return;
      }
      if (uid && uid === lastWsUid && (now - lastWsAt) < WS_DEDUP_MS) {
        console.warn('[Guard/WS] ui:chat:send ignoré (dupe uid <30s):', uid);
        return;
      }
      if (!uid && txtN && txtN === lastWsTxtN && (now - lastWsAt) < WS_DEDUP_MS) {
        console.warn('[Guard/WS] ui:chat:send ignoré (dupe texte <30s>):', txtN);
        return;
      }
      lastWsAt = now; lastWsUid = uid || lastWsUid; lastWsTxtN = txtN;
      return origEmit ? origEmit(name, payload) : undefined;
    }
  };

  // Anti-double enregistrement du même handler pour 'ui:chat:send'
  const origOn = eventBus.on?.bind(eventBus);
  const seenHandlers = new WeakSet();
  eventBus.on = function(name, handler) {
    if (name === 'ui:chat:send' && handler) {
      if (seenHandlers.has(handler)) {
        console.warn('[Guard] listener ui:chat:send ignoré (déjà enregistré).');
        return this;
      }
      seenHandlers.add(handler);
    }
    return origOn ? origOn(name, handler) : this;
  };

  // Cleanup du glyph "▍" résiduel en fin de stream (sécurité visuelle)
  const cleanCursorGlyphs = () => {
    try {
      const candidates = document.querySelectorAll('[data-role="assistant"], .assistant, .message.assistant, [data-message-role="assistant"]');
      const re = new RegExp(`${CURSOR_GLYPHS_RE.source}|${BLOCKS_RE.source}`, 'g');
      candidates.forEach(el => {
        const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT, null, false);
        let t;
        while ((t = walker.nextNode())) {
          const before = t.nodeValue;
          const after = before && before.replace(re, '');
          if (after !== before) t.nodeValue = after;
        }
      });
    } catch {}
  };
  eventBus.on?.('ws:chat_stream_end', () => {
    cleanCursorGlyphs();
    setTimeout(cleanCursorGlyphs, 30);
    requestAnimationFrame(cleanCursorGlyphs);
  });

  console.debug('[Guard] EventBus guards V3 installés (UI≠WS, dédup séparée + cleanup).');
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

  // Hooks model/meta (affiche le modèle utilisé)
  eventBus.on?.('chat:model_info', (p) => { if (p) setModel(p.provider, p.model, false); });
  eventBus.on?.('chat:last_message_meta', (meta) => { if (meta) setModel(meta.provider, meta.model, !!meta.fallback); });

  // Sync multi-onglets (une seule fois)
  try {
    if (!window.__em_auth_listeners__) {
      window.addEventListener('storage', (ev) => {
        if (ev.key === 'emergence.id_token' || ev.key === 'id_token') {
          const has = !!(ev.newValue && ev.newValue.trim());
          setLogged(has);
        }
      });
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
      window.__em_auth_listeners__ = true;
    }
  } catch {}

  setLogged(hasToken()); setConnected(false);
  return { setLogged, setConnected };
}

/* -------------------- App bootstrap -------------------- */
class EmergenceClient {
  constructor() { this.initialize(); }

  async initialize() {
    console.log("🚀 ÉMERGENCE - Lancement du client.");

    const eventBus = new EventBus();
    installEventBusGuards(eventBus);

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

/* ---------- Boot guard : éviter tout second bootstrap involontaire ---------- */
(function bootOnce() {
  const FLAG = '__emergence_boot_v25_1__';
  if (window[FLAG]) {
    console.warn('[Boot] Client déjà initialisé — second bootstrap ignoré.');
    return;
  }
  window[FLAG] = true;
  window.emergenceApp = new EmergenceClient();
})();
