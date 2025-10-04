/**
 * @module core/main
 * Point d'entrée universel — PROD sans bundler : aucun import CSS ici.
 */
import { t } from './shared/i18n.js';
import { App } from './core/app.js';
import { EventBus } from './core/event-bus.js';
import { StateManager } from './core/state-manager.js';
import { WebSocketClient } from './core/websocket.js';
import { MemoryCenter } from './features/memory/memory-center.js';
import { HomeModule } from './features/home/home-module.js';
import {
  storeAuthToken as storeAuthTokenImpl,
  clearAuth as clearAuthImpl,
  getIdToken as getIdTokenImpl,
} from './core/auth.js';

import { api } from './shared/api-client.js';
import { WS_CONFIG, EVENTS } from './shared/constants.js';

const storeAuthToken = typeof storeAuthTokenImpl === 'function' ? storeAuthTokenImpl : () => null;
const clearStoredAuth = typeof clearAuthImpl === 'function' ? clearAuthImpl : () => {};
const getIdToken = typeof getIdTokenImpl === 'function' ? getIdTokenImpl : () => null;

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
function getAnyToken() {
  const token = getIdToken();
  return token ? token.trim() : '';
}
function hasToken() { return !!getAnyToken(); }
function openDevAuth() {
  try { window.open('/dev-auth.html', '_blank', 'noopener,noreferrer'); } catch {}
}

function shouldUseSecureCookies() {
  try {
    if (typeof window === 'undefined') return false;
    const location = window.location || {};
    const protocol = location.protocol || '';
    if (protocol !== 'https:') return false;
    const hostname = (location.hostname || '').toLowerCase();
    return hostname !== 'localhost' && hostname !== '127.0.0.1' && hostname !== '0.0.0.0' && hostname !== '::1';
  } catch (_) {
    return false;
  }
}

/* === Nouveaux helpers (auto-auth) === */
function pickTokenFromLocation() {
  const blob = (window.location.hash || '') + '&' + (window.location.search || '');
  const m = blob.match(/(?:^|[?#&])(id_token|token)=([^&#]+)/i);
  return m ? decodeURIComponent(m[2]) : '';
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
  const menuToggle = document.getElementById('mobile-menu-toggle') || document.getElementById('mobile-nav-toggle');
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

  window.addEventListener('emergence:mobile-menu-state', () => {
    if (persistentNav) return;
    syncBackdrop();
    updateAria();
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
function showToast({ kind = 'info', text = '', duration = 3200, action } = {}) {
  const host = mountToastHost();
  const card = document.createElement('div');
  card.role = 'status';
  card.style.cssText = 'min-width:260px;max-width:420px;padding:.6rem .8rem;border-radius:12px;background:#111a;color:#eee;border:1px solid #333;box-shadow:0 10px 30px rgba(0,0,0,.45);pointer-events:auto';

  const row = document.createElement('div');
  row.style.cssText = 'display:flex;align-items:center;gap:.6rem';

  const chip = kind === 'warning' ? '#f59e0b' : (kind === 'error' ? '#ef4444' : '#22c55e');
  const dot = document.createElement('span');
  dot.style.cssText = `width:10px;height:10px;border-radius:50%;background:${chip};display:inline-block`;
  row.appendChild(dot);

  const message = document.createElement('div');
  message.style.cssText = 'flex:1;font-family:system-ui,Segoe UI,Roboto,Arial;font-size:.95rem;line-height:1.3';
  message.textContent = String(text ?? '');
  row.appendChild(message);

  let removed = false;
  const remove = () => {
    if (removed) return;
    removed = true;
    try { card.remove(); } catch (_) {}
  };

  if (action && action.label) {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.textContent = action.label;
    btn.style.cssText = 'margin-left:auto;background:rgba(148,163,184,.18);border:1px solid rgba(148,163,184,.4);color:#e2e8f0;padding:.35rem .7rem;border-radius:10px;font-size:.85rem;cursor:pointer;font-family:inherit;';
    btn.addEventListener('click', (ev) => {
      ev.preventDefault();
      ev.stopPropagation();
      try {
        if (typeof action.handler === 'function') action.handler();
      } catch (err) {
        console.error('[Toast] action handler error', err);
      }
      try {
        if (action.event) {
          const bus = EventBus.getInstance();
          bus?.emit?.(action.event, action.payload ?? {});
        }
      } catch (err) {
        console.error('[Toast] action event error', err);
      }
      remove();
    });
    row.appendChild(btn);
  }

  card.appendChild(row);
  host.appendChild(card);

  let closeDelay = Number(duration);
  if (!Number.isFinite(closeDelay) || closeDelay <= 0) closeDelay = action && action.label ? 7000 : 3200;
  if (closeDelay !== Infinity) {
    setTimeout(remove, closeDelay);
  }

  return card;
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
  const ensureAlertStyles = () => {
    if (document.getElementById('auth-alert-style')) return;
    const style = document.createElement('style');
    style.id = 'auth-alert-style';
    style.textContent = `.auth-alert{display:none;font-size:.72rem;text-transform:uppercase;letter-spacing:.08em;color:#fecaca;}
.auth-badge--alert{border-color:rgba(248,113,113,.65);box-shadow:0 14px 28px rgba(127,29,29,.28);}
.auth-badge--alert .auth-alert{display:inline-flex;align-items:center;font-weight:600;}`;
    try { document.head?.appendChild(style); } catch (_) {}
  };

  ensureAlertStyles();
  const ensureBox = () => {
    let node = document.getElementById('auth-badge');
    if (!node) {
      node = document.createElement('div');
      node.id = 'auth-badge';
      node.className = 'auth-badge is-floating';
      node.innerHTML = `
        <button id="auth-btn" type="button" class="auth-button auth-button--disconnected" data-auth-action="login">Se connecter</button>
        <span id="auth-alert" class="auth-alert" role="status" aria-live="assertive" aria-hidden="true" hidden></span>
        <span id="model-chip" class="auth-model-chip" role="status" aria-live="polite" style="display:none"></span>
      `;
      document.body.appendChild(node);
    }
    return node;
  };

  const box = ensureBox();
  const btn = box.querySelector('#auth-btn');
  const chip = box.querySelector('#model-chip');
  const alertNode = box.querySelector('#auth-alert');
  const loginRequiredMessage = t('auth.login_required');

  let mobileItem = null;
  let mobileButton = null;

  const ensureMobileButton = () => {
    if (!mobileItem) {
      mobileItem = document.createElement('li');
      mobileItem.id = 'auth-mobile-item';
      mobileItem.className = 'nav-item nav-item--auth';
      mobileItem.innerHTML = `
        <button type="button" class="nav-link nav-link--auth auth-button--disconnected" data-auth-action="login">
          <span class="nav-text">Se connecter</span>
        </button>
      `;
    }
    if (!mobileButton || !mobileItem.contains(mobileButton)) {
      mobileButton = mobileItem.querySelector('button');
    }
    return mobileButton;
  };

  const attachMobile = () => {
    const navList = document.getElementById('app-header-nav-list');
    const button = ensureMobileButton();
    if (!navList || !mobileItem) return button;
    if (mobileItem.parentElement !== navList) {
      navList.appendChild(mobileItem);
    }
    return button;
  };

  const updateButtonLabel = (button, label) => {
    if (!button) return;
    const text = (typeof label === 'string' ? label : '').trim();
    const navText = button.querySelector?.('.nav-text');
    if (navText) navText.textContent = text;
    else button.textContent = text;
  };

  const syncConnectionState = (connected) => {
    const toggle = (button) => {
      if (!button) return;
      button.classList.toggle('auth-button--connected', !!connected);
      button.classList.toggle('auth-button--disconnected', !connected);
    };
    toggle(btn);
    toggle(ensureMobileButton());
  };

  const triggerLogin = () => {
    eventBus.emit('auth:login', {});
    setTimeout(() => { if (!hasToken()) openDevAuth(); }, 300);
  };

  const triggerLogout = () => {
    eventBus.emit('auth:logout');
  };

  const updateChipVisibility = () => {
    if (!chip) return;
    const floating = box.classList.contains('is-floating');
    const hasText = (chip.textContent || '').trim().length > 0;
    chip.style.display = floating && hasText ? 'inline-flex' : 'none';
  };

  const setAlert = (message = '') => {
    if (!alertNode) return;
    const text = (typeof message === 'string' ? message : '').trim();
    if (text) {
      alertNode.textContent = text;
      alertNode.hidden = false;
      alertNode.setAttribute('aria-hidden', 'false');
      box.classList.add('auth-badge--alert');
    } else {
      alertNode.textContent = '';
      alertNode.hidden = true;
      alertNode.setAttribute('aria-hidden', 'true');
      box.classList.remove('auth-badge--alert');
    }
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
    attachMobile();
  };

  const setConnected = (ok) => {
    syncConnectionState(ok);
    if (ok) setAlert('');
  };
  const setLogged = (logged) => {
    const label = logged ? 'Se déconnecter' : 'Se connecter';
    updateButtonLabel(btn, label);
    const mobileBtn = attachMobile() || ensureMobileButton();
    updateButtonLabel(mobileBtn, label);

    const action = logged ? triggerLogout : triggerLogin;

    if (btn) {
      btn.onclick = action;
      btn.dataset.authAction = logged ? 'logout' : 'login';
    }
    if (mobileBtn) {
      mobileBtn.onclick = (event) => {
        if (event) event.preventDefault();
        action();
      };
      mobileBtn.dataset.authAction = logged ? 'logout' : 'login';
    }

    if (logged) setAlert('');
  };


  const setModel = (provider, model, fallback = false) => {
    if (!chip) return;
    const txt = provider && model ? `${provider} • ${model}${fallback ? ' (fallback)' : ''}` : '';
    chip.textContent = txt;
    updateChipVisibility();
  };

  // Abonnements d’état
  eventBus.on?.('auth:missing', () => { setLogged(false); setConnected(false); setAlert(loginRequiredMessage); });
  eventBus.on?.('auth:logout', () => { setLogged(false); setConnected(false); setAlert(loginRequiredMessage); });
  const wsConnectedEvent = EVENTS.WS_CONNECTED || 'ws:connected';
  const wsEstablishedEvent = EVENTS.WS_SESSION_ESTABLISHED || 'ws:session_established';
  const wsRestoredEvent = EVENTS.WS_SESSION_RESTORED || 'ws:session_restored';
  const markConnected = () => { setLogged(true); setConnected(true); setAlert(''); };
  eventBus.on?.(wsConnectedEvent, markConnected);
  eventBus.on?.(wsEstablishedEvent, markConnected);
  eventBus.on?.(wsRestoredEvent, markConnected);
  eventBus.on?.('ws:close', () => { setConnected(false); });
  eventBus.on?.(EVENTS.AUTH_REQUIRED, (payload) => {
    const alertText = (payload && typeof payload?.message === 'string' && payload.message.trim()) ? payload.message.trim() : loginRequiredMessage;
    setAlert(alertText);
  });
  eventBus.on?.(EVENTS.AUTH_RESTORED, () => { setAlert(''); });

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
  return { setLogged, setConnected, attach, setAlert };
}

function createAuthRecorder() {
  const win = (typeof window !== 'undefined') ? window : null;
  const maxEvents = 50;

  return {
    record(type, context = {}) {
      if (!win) return;
      try {
        const root = win.__EMERGENCE_QA_METRICS__ = win.__EMERGENCE_QA_METRICS__ || {};
        const bucket = root.authRequired = root.authRequired || {
          requiredCount: 0,
          missingCount: 0,
          restoredCount: 0,
          events: [],
        };
        if (!Array.isArray(bucket.events)) bucket.events = [];
        const entry = {
          type,
          at: new Date().toISOString(),
          source: context.source ?? null,
          reason: context.reason ?? null,
          status: context.status ?? null,
          message: context.message ?? null,
          threadId: context.threadId ?? null,
        };
        bucket.events.push(entry);
        if (bucket.events.length > maxEvents) {
          bucket.events.splice(0, bucket.events.length - maxEvents);
        }

        if (type === 'required') bucket.requiredCount = (bucket.requiredCount || 0) + 1;
        else if (type === 'missing') bucket.missingCount = (bucket.missingCount || 0) + 1;
        else if (type === 'restored') bucket.restoredCount = (bucket.restoredCount || 0) + 1;

        if (typeof console !== 'undefined' && typeof console.info === 'function') {
          const label = type === 'required'
            ? '[AuthTrace] AUTH_REQUIRED'
            : (type === 'missing' ? '[AuthTrace] AUTH_MISSING' : '[AuthTrace] AUTH_RESTORED');
          console.info(label, entry);
        }

        const dispatcher = typeof win.dispatchEvent === 'function' ? win.dispatchEvent.bind(win) : null;
        const CustomEvt = typeof win.CustomEvent === 'function'
          ? win.CustomEvent
          : (typeof CustomEvent === 'function' ? CustomEvent : null);
        if (dispatcher && CustomEvt) {
          try { dispatcher(new CustomEvt('emergence:auth:banner', { detail: entry })); } catch (_) {}
        }
      } catch (err) {
        try { console.warn('[AuthTrace] QA instrumentation failed', err); } catch (_) {}
      }
    },
  };
}

function installAuthRequiredInstrumentation(eventBus) {
  const recorder = createAuthRecorder();

  const record = (type, payload = {}, fallbackSource = 'event') => {
    const message = typeof payload?.message === 'string' ? payload.message.trim() : null;
    recorder.record(type, {
      source: payload?.source ?? fallbackSource,
      reason: payload?.reason ?? null,
      status: payload?.status ?? null,
      message,
      threadId: payload?.threadId ?? null,
    });
  };

  eventBus.on?.(EVENTS.AUTH_REQUIRED, (payload) => record('required', payload));
  eventBus.on?.('auth:missing', (payload) => record('missing', payload, 'auth:missing'));
  eventBus.on?.(EVENTS.AUTH_RESTORED, (payload) => record('restored', payload));

  const wsConnectedEvent = EVENTS.WS_CONNECTED || 'ws:connected';
  eventBus.on?.(wsConnectedEvent, () => recorder.record('restored', { source: wsConnectedEvent }));
  eventBus.on?.('auth:login', () => recorder.record('restored', { source: 'auth:login' }));

  return { recorder };
}

/* -------------------- App bootstrap -------------------- */
class EmergenceClient {
  constructor() {
    this.__readyFired = false;
    this.eventBus = null;
    this.state = null;
    this.badge = null;
    this.badgeLoginSyncUnsub = null;
    this.home = null;
    this.homeRoot = null;
    this.appContainer = null;
    this.app = null;
    this.appInitialized = false;
    this.memoryCenter = null;
    this.websocket = null;
    this.connectWs = () => {};
    this.storageListener = null;
    this.appReadyWatchdog = null;
    this.devAutoAttempted = false;
    this.devAutoLogged = false;
    this.initialize();
  }

  async initialize() {
    console.log("?? ÉMERGENCE - Lancement du client.");

    const eventBus = this.eventBus = EventBus.getInstance();
    installEventBusGuards(eventBus);

    const stateManager = this.state = new StateManager();
    await stateManager.init();

    try {
      window.App = Object.assign(window.App || {}, { eventBus, state: stateManager });
    } catch {}

    eventBus.on('auth:logout', () => {
      try { stateManager.reset(); }
      catch (e) { console.error('[Main] echec reset state apres logout', e); }
    });

    // Toasts
    eventBus.on('ui:toast', (p) => { if (p?.text) showToast(p); });

    this.homeRoot = typeof document !== 'undefined' ? document.getElementById('home-root') : null;
    this.appContainer = typeof document !== 'undefined' ? document.getElementById('app-container') : null;

    this.badge = mountAuthBadge(eventBus);

    const syncBadgeLoginState = (rawHasToken) => {
      const isLogged = !!rawHasToken;
      try { this.badge?.setLogged?.(isLogged); }
      catch (err) { console.warn('[main] Impossible de synchroniser le badge (logged)', err); }
      if (!isLogged) {
        try { this.badge?.setConnected?.(false); }
        catch (err) { console.warn('[main] Impossible de synchroniser le badge (connected)', err); }
      }
    };
    const app = new App(eventBus, stateManager);
    this.app = app;
    eventBus.on(EVENTS.WS_CONNECTED, () => {
      if (typeof app.ensureCurrentThread === 'function') {
        try {
          const maybe = app.ensureCurrentThread();
          if (maybe && typeof maybe.catch === 'function') {
            maybe.catch((e) => console.warn('[Main] ensureCurrentThread après WS_CONNECTED a échoué', e));
          }
        } catch (e) {
          console.warn('[Main] ensureCurrentThread après WS_CONNECTED a échoué', e);
        }
      }
    });

    try {
      const initialHasToken = stateManager.get?.('auth.hasToken');
      if (initialHasToken !== undefined) syncBadgeLoginState(initialHasToken);
    } catch (err) {
      console.warn('[main] Impossible de lire auth.hasToken pour le badge', err);
    }

    if (typeof stateManager.subscribe === 'function') {
      try {
        if (typeof this.badgeLoginSyncUnsub === 'function') {
          this.badgeLoginSyncUnsub();
        }
      } catch (_) {}
      try {
        this.badgeLoginSyncUnsub = stateManager.subscribe('auth.hasToken', syncBadgeLoginState);
      } catch (err) {
        console.warn("[main] Impossible d'abonner le badge a auth.hasToken", err);
      }
    }
    const authTraceHandle = installAuthRequiredInstrumentation(eventBus);
    const qaRecorder = authTraceHandle?.recorder ?? null;

    this.home = new HomeModule(eventBus, stateManager, { qaRecorder });

    eventBus.on?.('auth:missing', () => {
      this.handleLogout();
    });

    eventBus.on?.('auth:logout', () => {
      this.handleLogout();
    });

    const wsConnectedEvent = EVENTS.WS_CONNECTED || 'ws:connected';
    const wsEstablishedEvent = EVENTS.WS_SESSION_ESTABLISHED || 'ws:session_established';
    const wsRestoredEvent = EVENTS.WS_SESSION_RESTORED || 'ws:session_restored';
    const handleWsReady = () => {
      try { stateManager.set('chat.authRequired', false); }
      catch (err) { console.warn('[main] Impossible de signaler chat.authRequired=false', err); }
      this.badge?.setLogged?.(true);
      this.badge?.setConnected?.(true);
      this.badge?.setAlert?.('');
    };
    eventBus.on?.(wsConnectedEvent, handleWsReady);
    eventBus.on?.(wsEstablishedEvent, handleWsReady);
    eventBus.on?.(wsRestoredEvent, handleWsReady);

    this.websocket = new WebSocketClient(WS_CONFIG.URL, eventBus, stateManager);
    eventBus.on(EVENTS.APP_READY, () => { this.__readyFired = true; this.hideLoader(); });

    this.connectWs = () => {
      try { this.websocket.connect(); }
      catch (e) { console.error('[WS] connect error', e); }
    };

    eventBus.on?.(EVENTS.AUTH_LOGIN_SUBMIT, () => {
      this.badge?.setConnected(false);
    });
    eventBus.on?.(EVENTS.AUTH_LOGIN_SUCCESS, (payload) => this.handleLoginSuccess(payload));
    eventBus.on?.(EVENTS.AUTH_LOGIN_ERROR, () => {
      this.badge?.setConnected(false);
    });
    eventBus.on?.('auth:login', () => {
      if (!hasToken()) this.showHome();
    });

    const tokenFromUrl = pickTokenFromLocation();
    if (tokenFromUrl) storeAuthToken(tokenFromUrl);

    let devAutoLogged = false;
    if (!hasToken()) {
      devAutoLogged = await this.tryDevAutoLogin();
    }

    if (hasToken()) {
      if (!devAutoLogged && !this.devAutoLogged) {
        this.handleTokenAvailable('startup');
      }
    } else {
      this.markAuthRequired();
      this.showHome();
      if (isLocalHost()) {
        setTimeout(() => { if (!hasToken()) openDevAuth(); }, 250);
      }
      this.installStorageListener();
    }

    console.log('? Client ÉMERGENCE prêt. En attente du signal APP_READY...');
  }

  async tryDevAutoLogin() {
    if (this.devAutoAttempted) return false;
    this.devAutoAttempted = true;

    try {
      const data = await api.authDevLogin();
      if (!data || typeof data !== 'object' || !data.token) {
        return false;
      }

      this.devAutoLogged = true;
      const payload = {
        token: data.token,
        role: data.role ?? null,
        sessionId: data.session_id ?? data.sessionId ?? null,
        expiresAt: data.expires_at ?? data.expiresAt ?? null,
        email: data.email ?? null,
        response: data,
      };
      this.handleLoginSuccess(payload);
      return true;
    } catch (error) {
      const status = error?.status ?? error?.response?.status;
      if (status && [401, 403, 404, 405].includes(status)) {
        return false;
      }
      console.warn('[main] Dev auto-login failed', error);
      return false;
    }
  }

  installStorageListener() {
    if (typeof window === 'undefined') return;
    if (this.storageListener) return;
    const listener = (ev) => {
      try {
        const key = ev?.key;
        if (key !== 'emergence.id_token' && key !== 'id_token') return;
        const token = ev?.newValue;
        if (token && token.trim()) {
          storeAuthToken(token.trim());
          window.removeEventListener('storage', this.storageListener);
          this.storageListener = null;
          this.handleTokenAvailable('storage');
        }
      } catch (err) {
        console.warn('[main] storage listener error', err);
      }
    };
    this.storageListener = listener;
    try { window.addEventListener('storage', listener); } catch (_) {}
  }

  markAuthRequired() {
    try { this.state?.set?.('auth.hasToken', false); }
    catch (err) { console.warn('[main] Impossible de mettre a jour auth.hasToken', err); }
    try { this.state?.set?.('chat.authRequired', true); }
    catch (err) { console.warn('[main] Impossible de signaler chat.authRequired=true', err); }
    try { this.state?.set?.('auth.role', 'member'); }
    catch (err) { console.warn('[main] Impossible de remettre auth.role', err); }
    try { this.state?.set?.('auth.email', null); }
    catch (err) { console.warn('[main] Impossible de remettre auth.email', err); }
    try { this.state?.set?.('session.id', null); }
    catch (err) { console.warn('[main] Impossible de remettre session.id', err); }
    try { this.state?.set?.('websocket.sessionId', null); }
    catch (err) { console.warn('[main] Impossible de remettre websocket.sessionId', err); }
    try { this.app?.updateAuthStatus?.(null); }
    catch (err) { console.warn('[main] Impossible de remettre le statut de connexion', err); }
    this.badge?.setLogged(false);
    this.badge?.setConnected(false);
  }

  normalizeSessionId(raw) {
    if (raw === null || raw === undefined) return null;
    const value = String(raw).trim();
    return value ? value : null;
  }

  normalizeRole(raw) {
    if (typeof raw !== 'string') return null;
    const value = raw.trim().toLowerCase();
    return value ? value : null;
  }

  normalizeEmail(raw) {
    if (typeof raw !== 'string') return null;
    const value = raw.trim().toLowerCase();
    return value ? value : null;
  }

  normalizeUserId(raw) {
    if (raw === null || raw === undefined) return null;
    const value = String(raw).trim();
    return value ? value : null;
  }

  handleLoginSuccess(payload = {}) {
    const normalizedSessionId = this.normalizeSessionId(payload?.sessionId ?? payload?.session_id);
    const normalizedUserId = this.normalizeUserId(
      payload?.userId ??
      payload?.user_id ??
      payload?.response?.user_id ??
      payload?.response?.userId ??
      payload?.response?.user?.id
    );
    try { this.state?.resetForSession?.(normalizedSessionId, { userId: normalizedUserId }); }
    catch (err) { console.warn('[main] Impossible de reset l\'etat de session apres login', err, { sessionId: normalizedSessionId }); }
    const token = payload?.token;
    if (token && token.trim()) storeAuthToken(token.trim(), { expiresAt: payload?.expiresAt });
    try { this.state?.set?.('auth.hasToken', true); }
    catch (err) { console.warn('[main] Impossible de mettre a jour auth.hasToken', err); }
    const normalizedRole = this.normalizeRole(payload?.role) ?? 'member';
    try { this.state?.set?.('auth.role', normalizedRole); }
    catch (err) { console.warn('[main] Impossible de mettre a jour auth.role', err); }
    const normalizedEmail = this.normalizeEmail(payload?.email);
    try { this.state?.set?.('auth.email', normalizedEmail); }
    catch (err) { console.warn('[main] Impossible de mettre a jour auth.email', err); }
    if (normalizedEmail !== null) {
      try { this.state?.set?.('user.email', normalizedEmail); }
      catch (err) { console.warn('[main] Impossible de mettre a jour user.email', err); }
    }
    if (normalizedUserId) {
      try { this.state?.set?.('user.id', normalizedUserId); }
      catch (err) { console.warn('[main] Impossible de mettre a jour user.id', err); }
    }
    if (normalizedSessionId !== null) {
      try { this.state?.set?.('websocket.sessionId', normalizedSessionId); }
      catch (err) { console.warn('[main] Impossible d\'enregistrer websocket.sessionId', err); }
      try {
        const cookieParts = [
          `emergence_session_id=${encodeURIComponent(normalizedSessionId)}`,
          'path=/',
          'SameSite=Lax',
        ];
        if (payload?.expiresAt) {
          const dt = new Date(payload.expiresAt);
          if (!Number.isNaN(dt.getTime())) cookieParts.push(`expires=${dt.toUTCString()}`);
        } else {
          cookieParts.push('Max-Age=604800');
        }
        if (shouldUseSecureCookies()) cookieParts.push('Secure');
        document.cookie = cookieParts.join('; ');
      } catch (_) {}
    } else {
      try { this.state?.set?.('websocket.sessionId', null); }
      catch (err) { console.warn('[main] Impossible de purger websocket.sessionId', err); }
    }
    this.handleTokenAvailable('home-login');
    try { this.app?.handleRoleChange?.(normalizedRole); }
    catch (err) { console.warn('[main] Impossible de rafraichir la navigation (login)', err); }
  }

  async refreshSessionRole(source = 'unknown') {
    let session;
    try {
      session = await api.authSession();
    } catch (err) {
      console.warn('[main] Impossible de recuperer la session actuelle', err, { source });
      return;
    }

    if (!session || typeof session !== 'object') {
      console.warn('[main] Session auth absente, retour a l\'etat non authentifie', { source });
      this.handleLogout();
      return;
    }

    const normalizedRole = this.normalizeRole(session.role) ?? 'member';
    const normalizedEmail = this.normalizeEmail(session.email);
    const nextSessionId = this.normalizeSessionId(session.session_id ?? session.sessionId);
    const currentSessionId = this.state?.get?.('session.id') || this.state?.get?.('websocket.sessionId') || null;

    if (nextSessionId) {
      if (!currentSessionId || currentSessionId !== nextSessionId) {
        try { this.state?.resetForSession?.(nextSessionId); }
        catch (err) { console.warn('[main] Impossible d\'appliquer la nouvelle session', err, { source, nextSessionId }); }
      }
      try { this.state?.set?.('websocket.sessionId', nextSessionId); }
      catch (err) { console.warn('[main] Impossible de propager websocket.sessionId', err); }
    } else if (currentSessionId) {
      try { this.state?.resetForSession?.(null); }
      catch (err) { console.warn('[main] Impossible de purger la session courante', err); }
      try { this.state?.set?.('websocket.sessionId', null); }
      catch (err) { console.warn('[main] Impossible de purger websocket.sessionId', err); }
    }

    try { this.state?.set?.('auth.role', normalizedRole); }
    catch (err) { console.warn('[main] Impossible de mettre a jour auth.role', err); }

    try { this.state?.set?.('auth.email', normalizedEmail); }
    catch (err) { console.warn('[main] Impossible de mettre a jour auth.email', err); }
    if (normalizedEmail !== null) {
      try { this.state?.set?.('user.email', normalizedEmail); }
      catch (err) { console.warn('[main] Impossible de mettre a jour user.email', err); }
    }

    try { this.app?.handleRoleChange?.(normalizedRole); }
    catch (err) { console.warn('[main] Impossible de rafraichir la navigation (refreshSessionRole)', err); }
  }

  async handleTokenAvailable(source = 'unknown') {
    this.hideLoader();
    if (this.storageListener) {
      try { window.removeEventListener('storage', this.storageListener); } catch (_) {}
      this.storageListener = null;
    }
    if (this.home) this.home.unmount();
    if (typeof document !== 'undefined') {
      document.body.classList.remove('home-active');
    }
    try { this.state?.set?.('auth.hasToken', true); }
    catch (err) { console.warn('[main] Impossible de mettre a jour auth.hasToken', err); }
    await this.refreshSessionRole(source);
    try { this.state?.set?.('chat.authRequired', false); }
    catch (err) { console.warn('[main] Impossible de signaler chat.authRequired=false', err); }
    this.badge?.setLogged(true);
    this.badge?.setConnected(false);

    this.ensureApp();
    this.connectWs();

    this.eventBus?.emit?.(EVENTS.AUTH_RESTORED, { source });
  }

  ensureApp() {
    if (this.appInitialized) {
      if (!this.app) {
        this.app = new App(this.eventBus, this.state);
      }
      try { this.eventBus?.emit?.('module:show', 'chat'); } catch (_) {}
      return this.app;
    }

    const app = this.app || new App(this.eventBus, this.state);
    this.app = app;
    setupMobileShell(app, this.eventBus);

    try {
      this.memoryCenter = new MemoryCenter(this.eventBus, this.state);
      this.memoryCenter.init();
    } catch (err) {
      console.warn('[Memory] Overlay init failed', err);
      this.memoryCenter = null;
    }

    if (this.memoryCenter) {
      this.eventBus.on?.('memory:center:open', () => {
        try { this.memoryCenter.open(); } catch (e) { console.error('[Memory] open failed', e); }
      });
      this.eventBus.on?.('memory:center:state', () => {
        try { this.memoryCenter.refresh(); } catch (e) { console.error('[Memory] refresh failed', e); }
      });
      this.eventBus.on?.('memory:center:history', (payload = {}) => {
        try {
          const items = Array.isArray(payload.items) ? payload.items : [];
          console.log('[MemoryCenter] history refresh', { count: items.length, first: items[0]?.session_id || null, ts: new Date().toISOString() });
        } catch (err) {
          console.warn('[MemoryCenter] history instrumentation failed', err);
        }
      });
    }

    try { this.eventBus.emit && this.eventBus.emit('module:show', 'chat'); } catch (_) {}

    if (this.appReadyWatchdog) clearTimeout(this.appReadyWatchdog);
    this.appReadyWatchdog = setTimeout(() => {
      if (!this.__readyFired) {
        console.warn('[Watchdog] APP_READY manquant – re-module:show(chat)');
        try { this.eventBus.emit && this.eventBus.emit('module:show', 'chat'); } catch (_) {}
      }
    }, 1200);

    this.appInitialized = true;
    return app;
  }

  showHome() {
    this.hideLoader();
    if (typeof document !== 'undefined') {
      document.body.classList.add('home-active');
    }
    if (this.homeRoot && this.home) {
      this.home.mount(this.homeRoot);
    }
  }

  handleLogout() {
    clearStoredAuth();
    this.devAutoLogged = false;
    this.devAutoAttempted = false;
    try {
      this.state?.resetForSession?.(null, {
        preserveAuth: {},
        preserveUser: false,
        userId: null,
        preserveThreads: false,
      });
    }
    catch (err) { console.warn('[main] Impossible de remettre l\'etat par defaut', err); }
    this.markAuthRequired();
    this.showHome();
    this.installStorageListener();
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
