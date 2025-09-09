// src/frontend/main.dev.js
/**
 * Entrée DEV (INDEX_DEV) — sans imports CSS ESM.
 * - Injecte les CSS via <link rel="stylesheet"> pour éviter les erreurs MIME.
 * - Conserve le bootstrap et les comportements de main.js (patch EventBus, GIS, WS, etc.).
 */

// --- Injection CSS (ordre aligné sur les chargements observés) ---
(function injectCssLinks() {
  const HEAD = document.head || document.getElementsByTagName('head')[0];
  const ensureLink = (href) => {
    if (HEAD.querySelector(`link[rel="stylesheet"][href="${href}"]`)) return;
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = href;
    HEAD.appendChild(link);
  };

  const css = [
    // Core
    '/src/styles/core/reset.css',
    '/src/styles/core/_variables.css',
    '/src/styles/core/_typography.css',
    '/src/styles/core/_layout.css',
    '/src/styles/core/_navigation.css',

    // Components
    '/src/styles/components/agent-buttons.css',
    '/src/styles/components/agent-selector.css',
    '/src/styles/components/custom-select.css',
    '/src/styles/components/custom-toggle.css',
    '/src/styles/components/buttons.css',
    '/src/styles/components/glassmorphism.css',
    '/src/styles/components/header-nav.css',
    '/src/styles/components/inputs.css',
    '/src/styles/components/modals.css',
    '/src/styles/components/tabs.css',

    // Features
    '/src/features/chat/chat.css',
    '/src/features/debate/debate.css',
    '/src/features/documents/documents.css',
    '/src/features/dashboard/dashboard.css',
    '/src/features/threads/threads.css',
    '/src/features/voice/voice.css',
    '/src/features/timeline/timeline.css',

    // Overrides + extras
    '/src/styles/overrides/ui-hotfix-20250823.css',
    '/src/features/costs/costs.css',

    // Global last
    '/src/styles/main-styles.css'
  ];

  for (const href of css) ensureLink(href);
  console.info('[main.dev.js] CSS injectées via <link> (%d fichiers).', css.length);
})();

// --- JS imports (identiques à main.js, sans CSS ESM) ---
import { App } from './core/app.js';
import { EventBus } from './core/event-bus.js';
import { StateManager } from './core/state-manager.js';
import { WebSocketClient } from './core/websocket.js';
import { WS_CONFIG } from './shared/constants.js';
import { setGisClientId, ensureAuth, getIdToken } from './core/auth.js';

/* ---------------- WS-first Chat dedupe & reroute (patch identique main.js) ---------------- */
(function () {
  try {
    if (!EventBus || !EventBus.prototype) return;
    const proto = EventBus.prototype;
    if (proto.__patched_dedupe_reroute) return;
    const origEmit = proto.emit;
    let streamOpen = false;
    const seen = new Set();

    proto.emit = function (name, payload) {
      if (name === 'ws:chat_stream_start') { streamOpen = true; }
      else if (name === 'ws:chat_stream_end' || name === 'ws:close') { streamOpen = false; }

      if (name === 'ui:chat:send') {
        const p = payload || {};
        const enriched = (p && p.__enriched === true);

        // Empêche l'envoi si un stream est en cours (avant enrichissement)
        if (!enriched && streamOpen) {
          console.warn('[Guard/WS] ui:chat:send ignoré (stream en cours).');
          return;
        }

        // Dédoublonnage après enrichissement
        if (enriched) {
          const uid = p.msg_uid || '';
          if (uid && seen.has(uid)) {
            console.warn('[Guard/Dedupe] dupe:', uid);
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

    proto.__patched_dedupe_reroute = true;
    console.info('[main.dev.js] Patch EventBus appliqué.');
  } catch (e) {
    console.warn('[main.dev.js] avertissement lors du patch EventBus', e);
  }
})();

/* ---------------- Bootstrap application ---------------- */
(async function bootstrap() {
  console.log('🚀 ÉMERGENCE (DEV) — Lancement du client.');

  // 1) GIS client id (depuis <meta>) — One-Tap possible.
  setGisClientId();

  // 2) Auth stricte côté UI (interactive si nécessaire)
  let token = await ensureAuth({ interactive: true });
  if (!token) {
    for (let i = 0; i < 10 && !token; i++) {
      await new Promise(r => setTimeout(r, 200));
      token = getIdToken();
    }
  }

  // 3) Init App
  const state = new StateManager();
  const eventBus = new EventBus();
  const ws = new WebSocketClient(WS_CONFIG, eventBus, state);

  const app = new App(eventBus, state);
  if (typeof app.init === 'function') await app.init();

  console.log('✅ Client ÉMERGENCE (DEV) prêt. En attente du signal APP_READY...');
})();
