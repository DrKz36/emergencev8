/**
 * @module core/main
 * Point d'entrée universel — PROD avec bundling CSS.
 */

/* ===== CSS bundle (Vite) ===== */
import '@/styles/core/reset.css';
import '@/styles/core/_variables.css';
import '@/styles/core/_typography.css';
import '@/styles/core/_layout.css';
import '@/styles/core/_navigation.css';

import '@/styles/components/agent-buttons.css';
import '@/styles/components/agent-selector.css';
import '@/styles/components/buttons.css';
import '@/styles/components/custom-select.css';
import '@/styles/components/custom-toggle.css';
import '@/styles/components/glassmorphism.css';
import '@/styles/components/header-nav.css';
import '@/styles/components/inputs.css';
import '@/styles/components/modals.css';
import '@/styles/components/tabs.css';

import '@/features/chat/chat.css';
import '@/features/debate/debate.css';
import '@/features/documents/documents.css';
import '@/features/dashboard/dashboard.css';
import '@/features/threads/threads.css';
import '@/features/voice/voice.css';
import '@/features/timeline/timeline.css';
import '@/features/costs/costs.css';

import '@/styles/main-styles.css';
import '@/styles/overrides/ui-hotfix-20250823.css';
/* ===== fin CSS bundle ===== */

import { App } from './core/app.js';
import { EventBus } from './core/event-bus.js';
import { StateManager } from './core/state-manager.js';
import { WebSocketClient } from './core/websocket.js';
import { WS_CONFIG } from './shared/constants.js';
import { setGisClientId, ensureAuth, getIdToken } from './core/auth.js';

/* ---------------- WS-first Chat dedupe & reroute (main.js patch) ---------------- */
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
        if (!enriched && streamOpen) { console.warn('[Guard/WS] ui:chat:send ignoré (stream en cours).'); return; }
        if (enriched) {
          const uid = p.msg_uid || '';
          if (uid && seen.has(uid)) { console.warn('[Guard/Dedupe] dupe:', uid); return; }
          if (uid) { seen.add(uid); setTimeout(() => seen.delete(uid), 30000); }
          return origEmit.call(this, 'ws:send', { type:'chat.message', payload:{ text:p.text, agent_id:p.agent_id, use_rag:!!p.use_rag } });
        }
      }
      return origEmit.call(this, name, payload);
    };
    proto.__patched_dedupe_reroute = true;
    console.info('[main.js patch] WS-first Chat dedupe & reroute appliqué.');
  } catch (e) { console.warn('[main.js patch] avertissement lors du patch EventBus', e); }
})();

/* ---------------- Bootstrap application ---------------- */
(async function bootstrap() {
  console.log('🚀 ÉMERGENCE - Lancement du client.');

  // 1) GIS client id (depuis <meta>) — si présent, One-Tap pourra fournir un token automatiquement.
  setGisClientId();

  // 2) Auth stricte : force le mode interactif (ouvre /dev-auth.html si besoin et attend le token)
  let token = await ensureAuth({ interactive: true }); // ← clé pour éviter "Authentication required"
  if (!token) {
    // Attente active courte (bridge storage) au cas où le token arrive juste après
    for (let i = 0; i < 10 && !token; i++) {
      await new Promise(r => setTimeout(r, 200));
      token = getIdToken();
    }
  }

  // 3) Initialisation des clients et de l'app — avec EventBus unique
  const state = new StateManager();
  const eventBus = new EventBus();
  const ws = new WebSocketClient(WS_CONFIG, eventBus, state);

  const app = new App(eventBus, state);
  if (typeof app.init === 'function') await app.init();

  console.log('✅ Client ÉMERGENCE prêt. En attente du signal APP_READY...');
})();
