/**
 * @module core/main
 * Point d'entrée universel — PROD sans bundler : aucun import CSS ici.
 */
import { App } from './core/app.js';
import { EventBus } from './core/event-bus.js';
import { StateManager } from './core/state-manager.js';
import { WebSocketClient } from './core/websocket.js';
import { MemoryCenter } from './features/memory/memory-center.js';
import { ThreadsPanel } from './features/threads/threads.js';
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

/* === Nouveaux helpers (auto-auth) === */
function pickTokenFromLocation() {
  const blob = (window.location.hash || '') + '&' + (window.location.search || '');
  const m = blob.match(/(?:^|[?#&])(id_token|token)=([^&#]+)/i);
  return m ? decodeURIComponent(m[2]) : '';
}
function saveToken(tok) {
  if (!tok) return;
  try { localStorage.setItem('emergence.id_token', tok); } catch {}
  try { localStorage.setItem('id_token', tok); } catch {}
}
function isLocalHost() {
  const h = (window.location && window.location.hostname || '').toLowerCase();
  return h === 'localhost' || h === '127.0.0.1' || h === '0.0.0.0';
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

function setupMobileShell(appInstance, eventBus) {
  const body = document.body;
  const sidebar = document.getElementById('app-sidebar');
  const memoryOverlay = document.getElementById('memory-overlay');
  const memoryPanel = memoryOverlay?.querySelector('.memory-overlay__panel');
  const menuToggle = document.getElementById('mobile-menu-toggle');
  let brainToggle = document.getElementById('mobile-brain-toggle');
  const backdrop = document.getElementById('mobile-backdrop');
  if (brainToggle) {
    try { brainToggle.remove(); } catch (_) {}
    brainToggle = null;
  }

  const memoryClosers = memoryOverlay ? memoryOverlay.querySelectorAll('[data-memory-close]') : [];

  if (!menuToggle && !brainToggle && !memoryOverlay && !sidebar) return;

  const navMode = sidebar?.dataset?.mobileNav || '';
  const persistentNav = navMode.toLowerCase() === 'persistent';

  if (persistentNav) {
    try { body.classList.add('mobile-nav-persistent'); } catch (_) {}
    if (menuToggle) {
      menuToggle.setAttribute('hidden', 'hidden');
      menuToggle.setAttribute('aria-hidden', 'true');
      menuToggle.setAttribute('tabindex', '-1');
      menuToggle.removeAttribute('aria-expanded');
    }
  }

  const syncBackdrop = () => {
    if (!backdrop) return;
    if (persistentNav) {
      backdrop.hidden = true;
      return;
    }
    const open = body.classList.contains('mobile-menu-open') || body.classList.contains('brain-panel-open');
    backdrop.hidden = !open;
  };

  const updateAria = () => {
    if (menuToggle && !persistentNav) {
      menuToggle.setAttribute('aria-expanded', body.classList.contains('mobile-menu-open') ? 'true' : 'false');
    }
    if (brainToggle) {
      brainToggle.setAttribute('aria-expanded', body.classList.contains('brain-panel-open') ? 'true' : 'false');
    }
    if (sidebar) {
      if (persistentNav) {
        sidebar.removeAttribute('aria-hidden');
      } else if (window.innerWidth <= 760) {
        const navVisible = body.classList.contains('mobile-menu-open') || body.classList.contains('brain-panel-open');
        sidebar.setAttribute('aria-hidden', navVisible ? 'false' : 'true');
      } else {
        sidebar.removeAttribute('aria-hidden');
      }
    }
    if (memoryOverlay) {
      const open = body.classList.contains('brain-panel-open');
      memoryOverlay.setAttribute('aria-hidden', open ? 'false' : 'true');
    }
  };

  const closeMenu = () => {
    if (persistentNav) return;
    if (!body.classList.contains('mobile-menu-open')) return;
    body.classList.remove('mobile-menu-open');
    syncBackdrop();
    updateAria();
  };

  const closeBrain = () => {
    if (!body.classList.contains('brain-panel-open')) return;
    body.classList.remove('brain-panel-open');
    if (memoryOverlay) memoryOverlay.setAttribute('aria-hidden', 'true');
    try { window.dispatchEvent(new CustomEvent('emergence:memory:close')); } catch (_) {}
    syncBackdrop();
    updateAria();
  };

  const openMenu = () => {
    if (persistentNav) return;
    body.classList.add('mobile-menu-open');
    body.classList.remove('brain-panel-open');
    syncBackdrop();
    updateAria();
  };

  const openBrain = () => {
    body.classList.add('brain-panel-open');
    if (!persistentNav) body.classList.remove('mobile-menu-open');
    if (memoryOverlay) memoryOverlay.setAttribute('aria-hidden', 'false');
    syncBackdrop();
    updateAria();
    if (memoryPanel) {
      if (!memoryPanel.hasAttribute('tabindex')) memoryPanel.setAttribute('tabindex', '-1');
      try { memoryPanel.focus({ preventScroll: true }); } catch (_) {}
    }
    try { window.dispatchEvent(new CustomEvent('emergence:memory:open')); } catch (_) {}
  };

  if (!persistentNav && menuToggle) {
    menuToggle.addEventListener('click', () => {
      if (body.classList.contains('mobile-menu-open')) {
        closeMenu();
      } else {
        openMenu();
      }
    });
  }

  brainToggle?.addEventListener('click', () => {
    if (body.classList.contains('brain-panel-open')) {
      closeBrain();
    } else {
      openBrain();
    }
  });

  backdrop?.addEventListener('click', () => {
    if (!persistentNav) closeMenu();
    closeBrain();
  });

  memoryClosers?.forEach((btn) => {
    btn.addEventListener('click', () => closeBrain());
  });

  memoryOverlay?.addEventListener('click', (event) => {
    if (event.target === memoryOverlay) {
      closeBrain();
    }
  });

  window.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
      if (body.classList.contains('brain-panel-open')) {
        closeBrain();
      } else if (!persistentNav && body.classList.contains('mobile-menu-open')) {
        closeMenu();
      }
    }
  });

  window.addEventListener('resize', () => {
    if (window.innerWidth > 760) {
      body.classList.remove('brain-panel-open');
      if (!persistentNav) {
        body.classList.remove('mobile-menu-open');
        syncBackdrop();
      }
    }
    updateAria();
  });

  if (typeof window !== 'undefined') {
    window.__EMERGENCE_MEMORY__ = {
      open: openBrain,
      close: closeBrain,
      toggle: () => (body.classList.contains('brain-panel-open') ? closeBrain() : openBrain()),
    };
  }

  if (eventBus?.on) {
    eventBus.on(EVENTS.MODULE_SHOW, () => {
      if (!persistentNav && body.classList.contains('mobile-menu-open')) closeMenu();
    });
  }

  syncBackdrop();
  updateAria();
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
  const ensureBox = () => {
    let node = document.getElementById('auth-badge');
    if (!node) {
      node = document.createElement('div');
      node.id = 'auth-badge';
      node.className = 'auth-badge is-floating';
      node.innerHTML = `
        <span id="auth-dot" class="auth-dot" aria-hidden="true"></span>
        <button id="auth-btn" type="button" class="auth-button">Se connecter</button>
        <span id="model-chip" class="auth-model-chip" role="status" aria-live="polite" style="display:none"></span>
      `;
      document.body.appendChild(node);
    }
    return node;
  };

  const box = ensureBox();
  const dot = box.querySelector('#auth-dot');
  const btn = box.querySelector('#auth-btn');
  const chip = box.querySelector('#model-chip');

  const updateChipVisibility = () => {
    if (!chip) return;
    const floating = box.classList.contains('is-floating');
    const hasText = (chip.textContent || '').trim().length > 0;
    chip.style.display = floating && hasText ? 'inline-flex' : 'none';
  };

  const attach = () => {
    const target = document.querySelector('[data-auth-host]');
    if (target) {
      target.appendChild(box);
      box.classList.remove('is-floating');
    } else {
      if (!box.classList.contains('is-floating')) document.body.appendChild(box);
      box.classList.add('is-floating');
    }
    updateChipVisibility();
  };

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
    updateChipVisibility();
  };

  // Abonnements d’état
  eventBus.on?.('auth:missing', () => { setLogged(false); setConnected(false); });
  eventBus.on?.('auth:logout', () => { setLogged(false); setConnected(false); });
  eventBus.on?.(EVENTS.WS_CONNECTED || 'ws:connected', () => { setLogged(true); setConnected(true); });
  eventBus.on?.('ws:close', () => { setConnected(false); });

  // Hooks model/meta (affiche le modèle utilisé)
  eventBus.on?.('chat:model_info', (p) => { if (p) setModel(p.provider, p.model, false); });
  eventBus.on?.('chat:last_message_meta', (meta) => { if (meta) setModel(meta.provider, meta.model, !!meta.fallback); });
  eventBus.on?.(EVENTS.MODULE_SHOW, () => setTimeout(attach, 0));
  eventBus.on?.('ui:auth:host-changed', () => setTimeout(attach, 0));

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
  attach();
  return { setLogged, setConnected, attach };
}

/* -------------------- App bootstrap -------------------- */
class EmergenceClient {
  constructor() { this.__readyFired=false; this.threadsPanel = null; this.initialize(); }

  async initialize() {
    console.log("🚀 ÉMERGENCE - Lancement du client.");

    // 🔧 Unifier sur le singleton
    const eventBus = EventBus.getInstance();
    installEventBusGuards(eventBus);

    const stateManager = new StateManager();
    await stateManager.init();

    // Exposition (debug/devtools)
    try {
      window.App = Object.assign(window.App || {}, { eventBus, state: stateManager });
    } catch {}

    // Toasts
    eventBus.on('ui:toast', (p) => { if (p?.text) showToast(p); });

    const badge = mountAuthBadge(eventBus);

    const websocket = new WebSocketClient(WS_CONFIG.URL, eventBus, stateManager);
    eventBus.on(EVENTS.APP_READY, () => { this.__readyFired=true; this.hideLoader(); });

    const app = new App(eventBus, stateManager);
    this.threadsPanel = new ThreadsPanel(eventBus, stateManager);
    this.threadsPanel.init();
    setupMobileShell(app, eventBus);

    let overlayMemoryCenter = null;
    try {
      overlayMemoryCenter = new MemoryCenter(eventBus, stateManager);
      overlayMemoryCenter.init();
    } catch (err) {
      console.warn('[Memory] Overlay init failed', err);
    }

    if (overlayMemoryCenter) {
      eventBus.on?.('memory:center:open', () => {
        try { overlayMemoryCenter.open(); } catch (e) { console.error('[Memory] open failed', e); }
      });
      eventBus.on?.('memory:center:state', () => {
        try { overlayMemoryCenter.refresh(); } catch (e) { console.error('[Memory] refresh failed', e); }
      });
    }

    // Sélection initiale du module (débloque mount & APP_READY)
    try { eventBus.emit && eventBus.emit('module:show','chat'); } catch {}

    // Watchdog APP_READY
    setTimeout(() => {
      if (!this.__readyFired) {
        console.warn('[Watchdog] APP_READY manquant → re-module:show(chat)');
        try { eventBus.emit && eventBus.emit('module:show','chat'); } catch {}
      }
    }, 1200);

    /* ====== Auto-auth & auto-connect WS ====== */
    const tokenFromUrl = pickTokenFromLocation();
    if (tokenFromUrl) saveToken(tokenFromUrl);

    const connectWs = () => {
      try { websocket.connect(); }
      catch (e) { console.error('[WS] connect error', e); }
    };

    if (hasToken()) {
      badge.setLogged(true);
      connectWs();
    } else {
      try { eventBus.emit('auth:missing'); } catch (_) {}
      // En local : ouvre la page d'auth si aucun token
      if (isLocalHost()) {
        setTimeout(() => { if (!hasToken()) openDevAuth(); }, 250);
      }
      // Quand le token arrive (dev-auth ou autre), on connecte automatiquement
      const onStorage = (ev) => {
        if (ev.key === 'emergence.id_token' || ev.key === 'id_token') {
          if (ev.newValue && ev.newValue.trim()) {
            window.removeEventListener('storage', onStorage);
            badge.setLogged(true);
            connectWs();
          }
        }
      };
      window.addEventListener('storage', onStorage);
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
  const FLAG = '__emergence_boot_v25_3__';
  if (window[FLAG]) {
    console.warn('[Boot] Client déjà initialisé — second bootstrap ignoré.');
    return;
  }
  window[FLAG] = true;
  window.emergenceApp = new EmergenceClient();
})();
