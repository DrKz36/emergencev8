// src/frontend/core/websocket.js
// WebSocketClient V22.0 — JWT gating + no-retry 4401/1008 + token in query + DE-DUP chat.message
// + UI hooks: ws:model_info / ws:model_fallback / ws:chat_stream_start(ttfb) / ws:chat_stream_end(meta)

import { EVENTS } from '../shared/constants.js';
import { ensureAuth, getIdToken, clearAuth } from './auth.js';

export class WebSocketClient {
  constructor(url, eventBus, stateManager) {
    this.url = url;
    this.eventBus = eventBus;
    this.state = stateManager;
    this.websocket = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelayMs = 1000;
    this._authPromptedAt = 0;

    // Anti-doublon (fenêtre courte)
    this._lastChatSig = null;
    this._lastChatTs = 0;
    this._dedupMs = 1200;

    // Metrics
    this._lastSendAt = 0;

    this._bindEventBus();
    this._bindStorageListener();
    console.log("✅ WebSocketClient V22.0 (JWT gating + de-dup + metrics TTFB) prêt.");
  }

  _bindEventBus() {
    // UI → chat
    this.eventBus.on?.('ui:chat:send', (payload = {}) => {
      try {
        const text = String(payload.text ?? '').trim();
        if (!text) return;

        // 🔒 Filtre legacy
        const rawAgent = (payload.agent_id ?? payload.agentId ?? '');
        const isLegacy = (!rawAgent || !String(rawAgent).trim()) && !payload.msg_uid;
        if (isLegacy) return;

        const agent_id = (String(rawAgent || '').trim()) || this._getActiveAgentIdFromState();
        const use_rag = (payload.use_rag ?? payload.useRag ?? this.state?.get?.('chat.ragEnabled')) === true;

        // t0 pour TTFB + compteur d'envoi
        this._lastSendAt = Date.now();
        try {
          const m = this.state?.get?.('chat.metrics') || {};
          const next = { ...m, send_count: (m.send_count || 0) + 1 };
          this.state?.set?.('chat.metrics', next);
        } catch {}

        // Debug optionnel
        if (localStorage.getItem('debug.ws') === '1') {
          try { console.debug('[WS] ui:chat:send → chat.message', { use_rag }); } catch {}
        }
        this.send({ type: 'chat.message', payload: { text, agent_id, use_rag } });
      } catch (e) { console.error('[WebSocket] ui:chat:send → chat.message a échoué', e); }
    });

    // Frames brutes éventuelles
    this.eventBus.on?.(EVENTS.WS_SEND || 'ws:send', (frame) => this.send(frame));

    // Auth events
    this.eventBus.on?.('auth:login', async (opts) => {
      const clientId = (opts && typeof opts === 'object') ? (opts.client_id ?? opts.clientId ?? null) : null;
      await ensureAuth({ interactive: true, clientId });
      this.connect();
    });
    this.eventBus.on?.('auth:logout', () => { try { clearAuth(); } catch {} this.close(4001, 'logout'); });

    // Si le serveur réclame l’auth
    this.eventBus.on?.('auth:missing', async () => {
      const now = Date.now();
      if (now - this._authPromptedAt > 4000) {
        this._authPromptedAt = now;
        await ensureAuth({ interactive: true });
        this.connect();
      }
    });
  }

  _bindStorageListener() {
    try {
      window.addEventListener('storage', (ev) => {
        if ((ev.key === 'emergence.id_token' || ev.key === 'id_token') && ev.newValue && ev.newValue.trim()) {
          console.log('[WebSocket] Token détecté via storage — reconnexion…');
          this.connect();
        }
      });
    } catch {}
  }

  _getActiveAgentIdFromState() {
    try {
      const v = this.state?.get?.('chat.activeAgent') || this.state?.get?.('chat.currentAgentId');
      if (v) return String(v).trim().toLowerCase();
      for (const k of ['emergence.activeAgent','chat.activeAgent']) {
        const vv = localStorage.getItem(k);
        if (vv && vv.trim()) return vv.trim().toLowerCase();
      }
    } catch {}
    return 'anima';
  }

  _buildUrl(sessionId, token) {
    const loc = window.location;
    const scheme = (loc.protocol === 'https:') ? 'wss' : 'ws';

    if (this.url && typeof this.url === 'string') {
      const hasProto = /^wss?:\/\//i.test(this.url);
      const path = hasProto ? this.url.replace(/\/+$/, '') : `${scheme}://${loc.host}/${this.url.replace(/^\/+/, '')}`.replace(/\/+$/, '');
      return `${path}/${sessionId}?token=${encodeURIComponent(token)}&id_token=${encodeURIComponent(token)}`;
    }
    return `${scheme}://${loc.host}/ws/${sessionId}?token=${encodeURIComponent(token)}&id_token=${encodeURIComponent(token)}`;
  }

  async connect() {
    if (this.websocket && this.websocket.readyState !== WebSocket.CLOSED) return;

    const token = getIdToken() || await ensureAuth({ interactive: false });
    if (!token) {
      this.eventBus.emit?.('auth:missing', null);
      console.warn('[WebSocket] Aucun ID token — connexion WS annulée.');
      return;
    }

    let sessionId = this.state?.get?.('websocket.sessionId');
    if (!sessionId) {
      sessionId = crypto?.randomUUID?.() || (Math.random().toString(16).slice(2) + Date.now());
      this.state?.set?.('websocket.sessionId', sessionId);
    }

    const url = this._buildUrl(sessionId, token);
    const protocols = ['jwt']; // token en query

    try {
      this.websocket = new WebSocket(url, protocols);
    } catch (e) {
      console.error('[WebSocket] new WebSocket() a échoué', e);
      this._scheduleReconnect();
      return;
    }

    this.websocket.onopen = () => {
      this.reconnectAttempts = 0;
      this.eventBus.emit?.(EVENTS.WS_CONNECTED || 'ws:connected', { url });
    };

    this.websocket.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        if (msg?.type === 'ws:auth_required') { this.eventBus.emit?.('auth:missing', msg?.payload || null); return; }

        // --- Metrics: TTFB (ws:chat_stream_start) ---
        if (msg?.type === 'ws:chat_stream_start') {
          const ttfb = Math.max(0, Date.now() - (this._lastSendAt || 0));
          try {
            const m = this.state?.get?.('chat.metrics') || {};
            const next = {
              ...m,
              ws_start_count: (m.ws_start_count || 0) + 1,
              last_ttfb_ms: ttfb
            };
            this.state?.set?.('chat.metrics', next);
          } catch {}
        }

        if (msg?.type) {
          if (msg.type === 'ws:model_info') {
            try { this.state?.set?.('chat.modelInfo', msg.payload || {}); } catch {}
            this.eventBus.emit?.('chat:model_info', msg.payload || null);
          }
          if (msg.type === 'ws:model_fallback') {
            const p = msg.payload || {};
            this.eventBus.emit?.('ui:toast', { kind: 'warning', text: `Fallback modèle → ${p.to_provider || '?'} / ${p.to_model || '?'}` });
            this.eventBus.emit?.('chat:model_fallback', p);
          }
          if (msg.type === 'ws:chat_stream_end') {
            const meta = (msg.payload && msg.payload.meta) || null;
            if (meta) {
              try { this.state?.set?.('chat.lastMessageMeta', meta); } catch {}
              this.eventBus.emit?.('chat:last_message_meta', meta);
            }
          }
          this.eventBus.emit?.(msg.type, msg.payload);
        }
      } catch { console.warn('[WebSocket] Message non JSON', ev.data); }
    };

    this.websocket.onclose = (ev) => {
      const code = ev?.code || 1006;
      if (code === 4401 || code === 1008) {
        this.eventBus.emit?.('auth:missing', { reason: code });
        this.websocket = null;
        return;
      }
      this._scheduleReconnect();
      this.eventBus.emit?.('ws:close', { code, reason: ev?.reason || '' });
    };

    this.websocket.onerror = (e) => { console.error('[WebSocket] error', e); };
  }

  close(code = 1000, reason = 'normal') {
    try { this.websocket?.close(code, reason); } catch {} finally { this.websocket = null; }
  }

  send(frame) {
    try {
      if (!frame || typeof frame !== 'object') return;

      // 🔒 Pare-feu anti-doublon seulement pour chat.message
      if (frame.type === 'chat.message') {
        const txt = String(frame?.payload?.text ?? '').trim();
        const ag  = String(frame?.payload?.agent_id ?? '').trim().toLowerCase();
        const sig = `${ag}::${txt}`;
        const now = Date.now();
        if (sig && this._lastChatSig === sig && (now - this._lastChatTs) < this._dedupMs) {
          console.warn('[WebSocket] Duplicate chat.message ignoré (de-dup).');
          return;
        }
        this._lastChatSig = sig;
        this._lastChatTs = now;
      }

      if (!this.websocket || this.websocket.readyState !== WebSocket.OPEN) {
        console.warn('[WebSocket] Connexion non ouverte, tentative connect()', frame?.type);
        this.connect();
        return;
      }
      this.websocket.send(JSON.stringify(frame));
    } catch (e) { console.error('[WebSocket] send failed', e); }
  }

  _scheduleReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) return;
    const delay = Math.min(8000, this.reconnectDelayMs * Math.pow(2, this.reconnectAttempts++));
    setTimeout(() => this.connect(), delay);
  }
}
