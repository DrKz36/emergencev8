// src/frontend/core/websocket.js
// WebSocketClient V24.2 — JWT sub-protocol + de-dup + TTFB + Heartbeat + Memory Prime + Tolerance + 4401→redirect

import { EVENTS, WS_CONFIG } from '../shared/constants.js';
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
    this._lastChatSig = null;
    this._lastChatTs = 0;
    this._dedupMs = 1200;
    this._lastSendAt = 0;

    this._hbTimer = null;
    this._hbLastPongAt = 0;
    this._hbIntervalMs = (WS_CONFIG && WS_CONFIG.HEARTBEAT_INTERVAL) ? WS_CONFIG.HEARTBEAT_INTERVAL : 30000;
    this._hbMissTolerance = 3;

    this._bindEventBus();
    this._bindStorageListener();
    console.log('✅ WebSocketClient V24.2 prêt.');
  }

  _bindEventBus() {
    this.eventBus.on?.('ui:chat:send', (payload = {}) => {
      try {
        const text = String(payload.text ?? '').trim();
        if (!text) return;

        const rawAgent = (payload.agent_id ?? payload.agentId ?? '');
        const isLegacy = (!rawAgent || !String(rawAgent).trim()) && !payload.msg_uid;
        if (isLegacy) return;

        const agent_id = (String(rawAgent || '').trim()) || this._getActiveAgentIdFromState();
        const use_rag = (payload.use_rag ?? payload.useRag ?? this.state?.get?.('chat.ragEnabled')) === true;

        this._lastSendAt = Date.now();
        try {
          const m = this.state?.get?.('chat.metrics') || {};
          this.state?.set?.('chat.metrics', { ...m, send_count: (m.send_count || 0) + 1 });
        } catch {}

        this.send({ type: 'chat.message', payload: { text, agent_id, use_rag } });
      } catch (e) { console.error('[WebSocket] ui:chat:send → chat.message a échoué', e); }
    });

    this.eventBus.on?.(EVENTS.WS_SEND || 'ws:send', (frame) => this.send(frame));

    this.eventBus.on?.('auth:login', async (opts) => {
      const clientId = (opts && typeof opts === 'object') ? (opts.client_id ?? opts.clientId ?? null) : null;
      await ensureAuth({ interactive: true, clientId });
      this.connect();
    });
    this.eventBus.on?.('auth:logout', () => {
      try { clearAuth(); } catch {}
      try { this.state?.set?.('chat.memoryStats', { has_stm: false, ltm_items: 0, injected: false }); } catch {}
      this.close(4001, 'logout');
    });

    this.eventBus.on?.('auth:missing', async () => {
      const now = Date.now();
      if (now - this._authPromptedAt > 4000) {
        this._authPromptedAt = now;
        await ensureAuth({ interactive: true });
        this.connect();
      }
    });

    this.eventBus.on?.('memory:prime', () => this._primeMemoryStatus());
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

  _buildUrl(sessionId) {
    const loc = window.location;
    const scheme = (loc.protocol === 'https:') ? 'wss' : 'ws';

    if (this.url && typeof this.url === 'string') {
      const hasProto = /^wss?:\/\//i.test(this.url);
      const base = hasProto
        ? this.url.replace(/\/+$/, '')
        : `${scheme}://${loc.host}/${this.url.replace(/^\/+/, '')}`.replace(/\/+$/, '');
      return `${base}/${sessionId}`;
    }
    return `${scheme}://${loc.host}/ws/${sessionId}`;
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

    const url = this._buildUrl(sessionId);
    const protocols = token ? ['jwt', token] : [];

    try {
      this.websocket = new WebSocket(url, protocols);
    } catch (e) {
      console.error('[WebSocket] new WebSocket() a échoué', e);
      this._scheduleReconnect();
      return;
    }

    this.websocket.onopen = () => {
      this.reconnectAttempts = 0;
      this._hbLastPongAt = Date.now();
      this._startHeartbeat();
      this.eventBus.emit?.(EVENTS.WS_CONNECTED || 'ws:connected', { url });
      this._primeMemoryStatus();
    };

    this.websocket.onmessage = (ev) => {
      this._hbLastPongAt = Date.now();
      try {
        const msg = JSON.parse(ev.data);

        if (msg?.type === 'ws:pong') return;

        if (msg?.type === 'ws:auth_required') {
          this.eventBus.emit?.('auth:missing', msg?.payload || null);
          return;
        }

        if (msg?.type === 'ws:chat_stream_start') {
          const ttfb = Math.max(0, Date.now() - (this._lastSendAt || 0));
          try {
            const m = this.state?.get?.('chat.metrics') || {};
            this.state?.set?.('chat.metrics', {
              ...m,
              ws_start_count: (m.ws_start_count || 0) + 1,
              last_ttfb_ms: ttfb
            });
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
          if (msg.type === 'ws:memory_banner') {
            const p = msg.payload || {};
            try {
              this.state?.set?.('chat.memoryStats', {
                has_stm: !!p.has_stm,
                ltm_items: Number.isFinite(p.ltm_items) ? p.ltm_items : 0,
                injected: !!p.injected_into_prompt
              });
              this.state?.set?.('chat.memoryBannerAt', Date.now());
            } catch {}
          }
          if (msg.type === 'ws:analysis_status') {
            try { this.state?.set?.('chat.analysisStatus', msg.payload || null); } catch {}
            this.eventBus.emit?.('chat:analysis_status', msg.payload || null);
          }

          this.eventBus.emit?.(msg.type, msg.payload);
        }
      } catch {
        console.warn('[WebSocket] Message non JSON', ev.data);
      }
    };

    this.websocket.onclose = (ev) => {
      this._stopHeartbeat();
      const code = ev?.code || 1006;
      if (code === 4401 || code === 1008) {
        try { clearAuth(); } catch {}
        this.eventBus.emit?.('auth:missing', { reason: code });
        try {
          if (location.pathname !== '/auth.html') location.assign('/auth.html');
        } catch {}
        this.websocket = null;
        return;
      }
      this._scheduleReconnect();
      this.eventBus.emit?.('ws:close', { code, reason: ev?.reason || '' });
    };

    this.websocket.onerror = (e) => { console.error('[WebSocket] error', e); };
  }

  _startHeartbeat() {
    this._stopHeartbeat();
    this._hbLastPongAt = Date.now();
    this._hbTimer = setInterval(() => {
      try {
        if (!this.websocket || this.websocket.readyState !== WebSocket.OPEN) return;
        this.send({ type: 'ws:ping' });
        const now = Date.now();
        if (now - this._hbLastPongAt > this._hbIntervalMs * this._hbMissTolerance) {
          console.warn('[WebSocket] Heartbeat manqué → reconnect…');
          this.close(4000, 'heartbeat-missed');
          this._scheduleReconnect();
        }
      } catch (e) { console.warn('[WebSocket] heartbeat error', e); }
    }, this._hbIntervalMs);
  }

  _stopHeartbeat() {
    if (this._hbTimer) {
      clearInterval(this._hbTimer);
      this._hbTimer = null;
    }
  }

  close(code = 1000, reason = 'normal') {
    try { this.websocket?.close(code, reason); } catch {}
    finally { this.websocket = null; this._stopHeartbeat(); }
  }

  send(frame) {
    try {
      if (!frame || typeof frame !== 'object') return;

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

  async _primeMemoryStatus() {
    try {
      const token = getIdToken();
      if (!token) {
        this.eventBus.emit?.('auth:missing', { reason: 'no-token-for-memory-prime' });
        return;
      }
      const res = await fetch('/api/memory/status', {
        method: 'GET',
        headers: { 'Authorization': `Bearer ${token}`, 'Accept': 'application/json' }
      });

      if (res.status === 401 || res.status === 403) {
        this.eventBus.emit?.('auth:missing', { reason: res.status });
        return;
      }
      if (!res.ok) return;

      const data = await res.json();
      const stats = {
        has_stm: !!data?.has_stm,
        ltm_items: Number.isFinite(data?.ltm_items) ? data.ltm_items : (Number.isFinite(data?.ltm_count) ? data.ltm_count : 0),
        injected: !!(data?.injected ?? data?.injected_into_prompt)
      };

      try {
        this.state?.set?.('chat.memoryStats', stats);
        this.state?.set?.('chat.memoryBannerAt', Date.now());
      } catch {}

      this.eventBus.emit?.('ws:memory_banner', stats);
    } catch (e) {
      console.warn('[WebSocket] _primeMemoryStatus failed', e);
    }
  }
}
