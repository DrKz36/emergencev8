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
function saveToken(tok, { expiresAt } = {}) {
  if (!tok) return;
  try { localStorage.setItem('emergence.id_token', tok); } catch {}
  try { localStorage.setItem('id_token', tok); } catch {}
  try { sessionStorage.setItem('id_token', tok); } catch {}
  try { sessionStorage.setItem('emergence.id_token', tok); } catch {}
  try {
    const parts = [
      `id_token=${encodeURIComponent(tok)}`,
      'path=/',
      'SameSite=Lax',
    ];
    if (expiresAt) {
      const dt = new Date(expiresAt);
      if (!Number.isNaN(dt.getTime())) {
        parts.push(`expires=${dt.toUTCString()}`);
      } else {
        parts.push('Max-Age=604800');
      }
    } else {
      parts.push('Max-Age=604800');
    }
    if (shouldUseSecureCookies()) parts.push('Secure');
    document.cookie = parts.join('; ');
  } catch {}
}
function clearToken() {
  try { localStorage.removeItem('emergence.id_token'); } catch {}
  try { localStorage.removeItem('id_token'); } catch {}
  try { sessionStorage.removeItem('id_token'); } catch {}
  try { sessionStorage.removeItem('emergence.id_token'); } catch {}
  try { document.cookie = (function() {
    const parts = ['id_token=', 'Max-Age=0', 'path=/', 'SameSite=Lax'];
    if (shouldUseSecureCookies()) parts.push('Secure');
    return parts.join('; ');
  })(); } catch {}
  try { document.cookie = (function() {
    const parts = ['emergence_session_id=', 'Max-Age=0', 'path=/', 'SameSite=Lax'];
    if (shouldUseSecureCookies()) parts.push('Secure');
    return parts.join('; ');
  })(); } catch {}
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
        <span id="auth-dot" class="auth-dot" aria-hidden="true"></span>
        <button id="auth-btn" type="button" class="auth-button">Se connecter</button>
        <span id="auth-alert" class="auth-alert" role="status" aria-live="assertive" aria-hidden="true" hidden></span>
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
  const alertNode = box.querySelector('#auth-alert');
  const loginRequiredMessage = t('auth.login_required');

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
  };

  const setConnected = (ok) => {
    if (dot) dot.style.background = ok ? '#22c55e' : '#f97316';
    if (ok) setAlert('');
  };
  const setLogged = (logged) => {
    if (!btn) return;
    btn.textContent = logged ? 'Se déconnecter' : 'Se connecter';
    btn.onclick = logged
      ? () => eventBus.emit('auth:logout')
      : () => {
          eventBus.emit('auth:login', {});
          setTimeout(() => { if (!hasToken()) openDevAuth(); }, 300);
        };
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
  eventBus.on?.(EVENTS.WS_CONNECTED || 'ws:connected', () => { setLogged(true); setConnected(true); setAlert(''); });
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

function createAuthBannerRecorder() {
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
            ? '[AuthBanner] AUTH_REQUIRED'
            : (type === 'missing' ? '[AuthBanner] AUTH_MISSING' : '[AuthBanner] AUTH_RESTORED');
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
        try { console.warn('[AuthBanner] QA instrumentation failed', err); } catch (_) {}
      }
    },
  };
}

function installAuthRequiredBanner(eventBus) {
  const recorder = createAuthBannerRecorder();
  let banner = null;
  let messageNode = null;

  const ensureBanner = () => {
    if (banner && typeof document !== 'undefined' && document.body?.contains(banner)) return banner;
    const existing = (typeof document !== 'undefined') ? document.getElementById('app-auth-required-banner') : null;
    if (existing) {
      banner = existing;
      messageNode = banner.querySelector('.app-auth-required-banner__message');
      return banner;
    }
    if (typeof document === 'undefined') return null;
    banner = document.createElement('div');
    banner.id = 'app-auth-required-banner';
    banner.className = 'app-auth-required-banner';
    banner.setAttribute('role', 'alert');
    banner.setAttribute('aria-live', 'assertive');
    banner.setAttribute('hidden', 'true');

    const icon = document.createElement('span');
    icon.className = 'app-auth-required-banner__icon';
    icon.setAttribute('aria-hidden', 'true');
    icon.innerHTML = "<svg viewBox='0 0 20 20' fill='currentColor' xmlns='http://www.w3.org/2000/svg'><path d='M10 2a8 8 0 1 0 0 16 8 8 0 0 0 0-16Zm0 3.5a1 1 0 0 1 .993.883L11 6.5v4a1 1 0 0 1-1.993.117L9 10.5v-4a1 1 0 0 1 1-1Zm.002 8a1.25 1.25 0 1 1 0 2.5 1.25 1.25 0 0 1 0-2.5Z'/></svg>";

    messageNode = document.createElement('span');
    messageNode.className = 'app-auth-required-banner__message';

    const action = document.createElement('button');
    action.type = 'button';
    action.className = 'app-auth-required-banner__action';
    action.textContent = t('auth.login_action');
    action.addEventListener('click', () => {
      try { eventBus.emit('auth:login', {}); } catch (_) {}
      setTimeout(() => {
        try { if (!hasToken()) openDevAuth(); } catch (_) {}
      }, 300);
    });

    banner.append(icon, messageNode, action);
    const host = document.body || document.documentElement;
    if (host) host.appendChild(banner);
    return banner;
  };

  const show = (message) => {
    const node = ensureBanner();
    if (!node) return;
    const textValue = (typeof message === 'string' && message.trim()) ? message.trim() : t('auth.login_required');
    if (messageNode) messageNode.textContent = textValue;
    node.classList.add('is-visible');
    node.removeAttribute('hidden');
  };

  const hide = () => {
    if (!banner) return;
    banner.classList.remove('is-visible');
    banner.setAttribute('hidden', 'true');
  };

  eventBus.on?.(EVENTS.AUTH_REQUIRED, (payload) => {
    const message = typeof payload?.message === 'string' ? payload.message : undefined;
    recorder.record('required', {
      source: payload?.source ?? 'event',
      reason: payload?.reason ?? null,
      status: payload?.status ?? null,
      message: message ? message.trim() : null,
    });
    show(message);
  });

  eventBus.on?.('auth:missing', (payload) => {
    const message = typeof payload?.message === 'string' ? payload.message : undefined;
    recorder.record('missing', {
      source: 'auth:missing',
      reason: payload?.reason ?? null,
      status: payload?.status ?? null,
      message: message ? message.trim() : null,
    });
    show(message);
  });

  eventBus.on?.(EVENTS.AUTH_RESTORED, (payload) => {
    recorder.record('restored', {
      source: payload?.source ?? 'event',
      threadId: payload?.threadId ?? null,
    });
    hide();
  });

  const wsConnectedEvent = EVENTS.WS_CONNECTED || 'ws:connected';
  eventBus.on?.(wsConnectedEvent, () => {
    recorder.record('restored', { source: wsConnectedEvent });
    hide();
  });

  eventBus.on?.('auth:login', () => {
    recorder.record('restored', { source: 'auth:login' });
    hide();
  });

  return { show, hide, recorder };
}

/* -------------------- App bootstrap -------------------- */
class EmergenceClient {
  constructor() {
    this.__readyFired = false;
    this.eventBus = null;
    this.state = null;
    this.badge = null;
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

    eventBus.on('ui:toast', (p) => { if (p?.text) showToast(p); });

    this.homeRoot = typeof document !== 'undefined' ? document.getElementById('home-root') : null;
    this.appContainer = typeof document !== 'undefined' ? document.getElementById('app-container') : null;

    this.badge = mountAuthBadge(eventBus);
    const authBannerHandle = installAuthRequiredBanner(eventBus);
    const qaRecorder = authBannerHandle?.recorder ?? null;

    this.home = new HomeModule(eventBus, stateManager, { qaRecorder });

    eventBus.on?.('auth:missing', () => {
      this.handleLogout();
    });

    eventBus.on?.('auth:logout', () => {
      this.handleLogout();
    });

    const wsConnectedEvent = EVENTS.WS_CONNECTED || 'ws:connected';
    eventBus.on?.(wsConnectedEvent, () => {
      try { stateManager.set('chat.authRequired', false); }
      catch (err) { console.warn('[main] Impossible de signaler chat.authRequired=false', err); }
      this.badge?.setConnected(true);
    });

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
    if (tokenFromUrl) saveToken(tokenFromUrl);

    if (hasToken()) {
      this.handleTokenAvailable('startup');
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

  installStorageListener() {
    if (typeof window === 'undefined') return;
    if (this.storageListener) return;
    const listener = (ev) => {
      try {
        const key = ev?.key;
        if (key !== 'emergence.id_token' && key !== 'id_token') return;
        const token = ev?.newValue;
        if (token && token.trim()) {
          saveToken(token.trim());
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
    catch (err) { console.warn('[main] Impossible de mettre à jour auth.hasToken', err); }
    try { this.state?.set?.('chat.authRequired', true); }
    catch (err) { console.warn('[main] Impossible de signaler chat.authRequired=true', err); }
    this.badge?.setLogged(false);
    this.badge?.setConnected(false);
  }

  handleLoginSuccess(payload = {}) {
    const token = payload?.token;
    if (token && token.trim()) saveToken(token.trim(), { expiresAt: payload?.expiresAt });
    if (payload?.sessionId) {
      try { this.state?.set?.('websocket.sessionId', payload.sessionId); }
      catch (err) { console.warn('[main] Impossible d’enregistrer websocket.sessionId', err); }
      try {
        const cookieParts = [
          `emergence_session_id=${encodeURIComponent(payload.sessionId)}`,
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
    }
    this.handleTokenAvailable('home-login');
  }

  handleTokenAvailable(source = 'unknown') {
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
    catch (err) { console.warn('[main] Impossible de mettre à jour auth.hasToken', err); }
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
      try { this.eventBus?.emit?.('module:show', 'chat'); } catch (_) {}
      return this.app;
    }

    const app = new App(this.eventBus, this.state);
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
    clearToken();
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
