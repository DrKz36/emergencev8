// src/frontend/core/websocket.js
// WebSocketClient V22.3 — queued send + flush onopen (version complète)

import { EVENTS } from '../shared/constants.js';
import { ensureAuth, getIdToken, clearAuth } from './auth.js';

const SESSION_STATE_PRESERVE = {
  preserveAuth: { role: true, email: true, hasToken: true },
  preserveUser: true,
  preserveThreads: true,
};
export class WebSocketClient {
  constructor(url, eventBus, stateManager) {
    this.url = url;
    this.eventBus = eventBus;
    this.state = stateManager;
    this.websocket = null;

    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 50; // Augmenté pour production (Cloud Run instable)
    this.reconnectDelayMs = 1000;

    this._authPromptedAt = 0;

    this._lastChatSig = null;
    this._lastChatTs = 0;
    this._dedupMs = 1200;
    this._opinionDedup = new Map();

    this._lastSendAt = 0;
    this._threadWaitUnsub = null;

    // ✅ queue d’envoi
    this._sendQueue = [];

    this._bindEventBus();
    this._bindStorageListener();
    console.log('✅ WebSocketClient V22.3 (queued send) prêt.');
  }

  _getActiveThreadId() {
    try {
      const direct = this.state?.get?.('threads.currentId');
      if (direct && typeof direct === 'string' && direct.trim()) return direct.trim();
      const cached = localStorage.getItem('emergence.threadId');
      if (cached && cached.trim()) return cached.trim();
    } catch {}
    return null;
  }

  _sanitizeThreadForSession(threadId, sessionId) {
    if (!threadId || typeof threadId !== 'string') return null;
    const trimmed = threadId.trim();
    if (!trimmed) return null;
    if (sessionId && typeof sessionId === 'string' && trimmed === sessionId.trim()) return null;
    return trimmed;
  }

  _resetSessionId() {
    try { this.state?.set?.('websocket.sessionId', null); }
    catch (e) { console.warn('[WebSocket] reset session id failed', e); }
  }

  _bindEventBus() {
    this.eventBus.on?.('ui:chat:send', (payload = {}) => {
      try {
        const text = String(payload.text ?? '').trim();
        if (!text) return;

        const rawAgent = (payload.agent_id ?? payload.agentId ?? '').trim().toLowerCase();
        const agent_id = rawAgent || this._getActiveAgentIdFromState();
        const doc_ids = Array.isArray(payload.doc_ids)
          ? payload.doc_ids.map((id) => String(id))
          : [];

        this._lastSendAt = Date.now();
        try {
          const m = this.state?.get?.('chat.metrics') || {};
          this.state?.set?.('chat.metrics', { ...m, send_count: (m.send_count || 0) + 1 });
        } catch {}

        this.send({
          type: 'chat.message',
          payload: {
            text,
            agent_id,
            use_rag: !!(payload.use_rag ?? payload.useRag ?? this.state?.get?.('chat.ragEnabled')),
            doc_ids,
          }
        });
      } catch (e) {
        console.error('[WebSocket] ui:chat:send → chat.message a échoué', e);
      }
    });

    this.eventBus.on?.(EVENTS.WS_SEND || 'ws:send', (frame) => this.send(frame));

    this.eventBus.on?.('auth:login', async (opts) => {
      const clientId = (opts && typeof opts === 'object') ? (opts.client_id ?? opts.clientId ?? null) : null;
      this._resetSessionId();
      await ensureAuth({ interactive: true, clientId });
      this.connect();
    });
    this.eventBus.on?.('auth:logout', () => {
      try { clearAuth(); } catch {}
      try { if (typeof this.state?.resetForSession === 'function') this.state.resetForSession(null); } catch {}
      this._resetSessionId();
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
  }

  _bindStorageListener() {
    try {
      window.addEventListener('storage', (ev) => {
        if ((ev.key === 'emergence.id_token' || ev.key === 'id_token') && ev.newValue && ev.newValue.trim()) {
          console.log('[WebSocket] Token détecté via storage — reconnexion…');
          this._resetSessionId();
          this.connect();
        }
      });
    } catch {}
  }

  _getActiveAgentIdFromState() {
    try {
      const v = this.state?.get?.('chat.activeAgent') || this.state?.get?.('chat.currentAgentId');
      if (v) return String(v).trim().toLowerCase();
      for (const k of ['emergence.activeAgent', 'chat.activeAgent']) {
        const vv = localStorage.getItem(k);
        if (vv && vv.trim()) return vv.trim().toLowerCase();
      }
    } catch {}
    return 'anima';
  }

  _buildUrl(sessionId) {
    const loc = window.location;
    const scheme = (loc.protocol === 'https:') ? 'wss' : 'ws';
    const rawThreadId = this._getActiveThreadId();
    const threadId = this._sanitizeThreadForSession(rawThreadId, sessionId);
    if (this.url && typeof this.url === 'string') {
      const hasProto = /^wss?:\/\//i.test(this.url);
      const base = hasProto
        ? this.url.replace(/\/+$/, '')
        : `${scheme}://${loc.host}/${this.url.replace(/^\/+/, '')}`.replace(/\/+$/, '');
      const query = threadId ? `?thread_id=${encodeURIComponent(threadId)}` : '';
      return `${base}/${sessionId}${query}`;
    }
    const query = threadId ? `?thread_id=${encodeURIComponent(threadId)}` : '';
    return `${scheme}://${loc.host}/ws/${sessionId}${query}`;
  }


  _extractSessionIdFromToken(token) {
    if (!token || typeof token !== 'string') return null;
    const parts = token.split('.');
    if (!Array.isArray(parts) || parts.length !== 3) return null;
    try {
      let payload = parts[1].replace(/-/g, '+').replace(/_/g, '/');
      const pad = payload.length % 4;
      if (pad) payload += '='.repeat(4 - pad);
      let decoded;
      if (typeof atob === 'function') {
        decoded = atob(payload);
      } else if (typeof Buffer !== 'undefined') {
        decoded = Buffer.from(payload, 'base64').toString('utf8');
      } else {
        return null;
      }
      const data = JSON.parse(decoded);
      const sid = data?.sid || data?.session_id || data?.sessionId;
      if (sid && typeof sid === 'string' && sid.trim()) return sid.trim();
    } catch (error) {
      console.debug('[WebSocket] Unable to decode auth session id from token', error);
    }
    return null;
  }

  async connect() {
    if (this.websocket && this.websocket.readyState !== WebSocket.CLOSED) return;

    const rawToken = getIdToken();
    const token = typeof rawToken === 'string' ? rawToken.trim() : '';
    if (!token) { this.eventBus.emit?.('auth:missing', null); console.warn('[WebSocket] Aucun ID token — connexion WS annulée.'); return; }

    let sessionId = this.state?.get?.('websocket.sessionId');
    const sidFromToken = this._extractSessionIdFromToken(token);
    if (sidFromToken && sessionId !== sidFromToken) {
      sessionId = sidFromToken;
      try {
        if (typeof this.state?.resetForSession === 'function') {
          this.state.resetForSession(sessionId, SESSION_STATE_PRESERVE);
        }
        this.state?.set?.('websocket.sessionId', sessionId);
      } catch {}
    }
    if (!sessionId) {
      sessionId = crypto?.randomUUID?.() || (Math.random().toString(16).slice(2) + Date.now());
      try {
        if (typeof this.state?.resetForSession === 'function') {
          this.state.resetForSession(sessionId, SESSION_STATE_PRESERVE);
        }
        this.state?.set?.('websocket.sessionId', sessionId);
      } catch {}
    }

    const readyThreadId = this._sanitizeThreadForSession(this._getActiveThreadId(), sessionId);
    if (!readyThreadId) {
      if (!this._threadWaitUnsub && this.eventBus?.on) {
        const handler = () => {
          const candidate = this._sanitizeThreadForSession(this._getActiveThreadId(), sessionId);
          if (!candidate) return;
          if (typeof this._threadWaitUnsub === 'function') {
            try { this._threadWaitUnsub(); } catch {}
          }
          this._threadWaitUnsub = null;
          this.connect();
        };
        const off = this.eventBus.on('threads:ready', handler);
        if (typeof off === 'function') {
          this._threadWaitUnsub = () => { try { off(); } catch {} };
        } else if (this.eventBus?.off) {
          this._threadWaitUnsub = () => { try { this.eventBus.off('threads:ready', handler); } catch {} };
        }
        console.warn('[WebSocket] Thread id missing; deferring connection until threads:ready.');
      }
      if (!this._threadWaitUnsub) {
        console.warn('[WebSocket] Thread id missing and no event bus listener available; aborting connect.');
      }
      return;
    }

    if (this._threadWaitUnsub) {
      try { this._threadWaitUnsub(); } catch {}
      this._threadWaitUnsub = null;
    }

    const url = this._buildUrl(sessionId);
    const protocols = token ? ['jwt', token] : [];

    try { this.websocket = new WebSocket(url, protocols); }
    catch (e) { console.error('[WebSocket] new WebSocket() a échoué', e); this._scheduleReconnect(); return; }

    this.websocket.onopen = () => {
      this.reconnectAttempts = 0;
      this.eventBus.emit?.(EVENTS.WS_CONNECTED || 'ws:connected', { url });

      // 🔁 flush queue
      try {
        const q = this._sendQueue.splice(0);
        for (const frame of q) { try { this.websocket.send(JSON.stringify(frame)); } catch (e) { console.warn('[WebSocket] flush item failed', e); } }
      } catch (e) { console.warn('[WebSocket] flush queue failed', e); }
    };

    this.websocket.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);

        // Auth required handler
        if (msg?.type === 'ws:auth_required') {
          console.warn('[WebSocket] Auth required:', msg?.payload);
          this.eventBus.emit?.(EVENTS.AUTH_REQUIRED, {
            reason: msg.payload?.reason || 'session_expired',
            message: msg.payload?.message
          });
          this.close();
          return;
        }

        // TTFB métriques
        if (msg?.type === 'ws:chat_stream_start') {
          const ttfb = Math.max(0, Date.now() - (this._lastSendAt || 0));
          try { const m = this.state?.get?.('chat.metrics') || {}; this.state?.set?.('chat.metrics', { ...m, ws_start_count: (m.ws_start_count || 0) + 1, last_ttfb_ms: ttfb }); } catch {}
        }

        // Model info handler
        if (msg?.type === 'ws:model_info') {
          console.log('[WebSocket] Model info:', msg.payload);
          try { this.state?.set?.('chat.modelInfo', msg.payload || {}); } catch {}
          this.eventBus.emit?.(EVENTS.MODEL_INFO_RECEIVED, {
            provider: msg.payload?.provider,
            model: msg.payload?.model,
            agent: msg.payload?.agent
          });
        }

        // Model fallback handler
        if (msg?.type === 'ws:model_fallback') {
          const p = msg.payload || {};
          console.warn('[WebSocket] Model fallback:', p);
          this.eventBus.emit?.(EVENTS.MODEL_FALLBACK, {
            from: p.from_provider,
            to: p.to_provider,
            reason: p.reason
          });
          const toastText = `Basculement vers ${p.to_provider || '?'} (${p.reason || 'unknown'})`;
          this.eventBus.emit?.('ui:toast', { kind: 'warning', text: toastText });
        }

        if (msg?.type === 'ws:chat_stream_end') {
          const meta = (msg.payload && msg.payload.meta) || null;
          if (meta) { try { this.state?.set?.('chat.lastMessageMeta', meta); } catch {} this.eventBus.emit?.('chat:last_message_meta', meta); }
        }

        // Memory banner handler
        if (msg?.type === 'ws:memory_banner') {
          const p = msg.payload || {};
          console.log('[WebSocket] Memory banner:', p);
          this.eventBus.emit?.(EVENTS.MEMORY_BANNER_UPDATE, {
            type: p.type,
            content: p.content,
            metadata: p.metadata
          });
          try {
            const prev = this.state?.get?.('chat.memoryStats') || {};
            const ltmItems = Number.isFinite(p.ltm_items) ? Number(p.ltm_items) : 0;
            const ltmInjected = Number.isFinite(p.ltm_injected) ? Number(p.ltm_injected) : (p.injected_into_prompt ? ltmItems : 0);
            const stats = {
              has_stm: !!p.has_stm,
              ltm_items: ltmItems,
              ltm_injected: ltmInjected,
              ltm_candidates: Number.isFinite(p.ltm_candidates) ? Number(p.ltm_candidates) : ltmItems,
              injected: !!p.injected_into_prompt,
              ltm_skipped: !!p.ltm_skipped
            };
            this.state?.set?.('chat.memoryStats', stats);
            this.state?.set?.('chat.memoryBannerAt', Date.now());
            if (stats.ltm_skipped && !prev?.ltm_skipped) {
              const count = stats.ltm_items || 0;
              const label = count ? `Memoire longue disponible (${count}) non injectee dans le prompt.` : 'Memoire longue non injectee dans le prompt.';
              this.eventBus.emit?.('ui:toast', { kind: 'info', text: label });
            }
          } catch { }
        }

        // Analysis status handler
        if (msg?.type === 'ws:analysis_status') {
          console.log('[WebSocket] Analysis status:', msg.payload);
          this.eventBus.emit?.(EVENTS.MEMORY_ANALYSIS_STATUS, {
            status: msg.payload?.status,
            progress: msg.payload?.progress,
            message: msg.payload?.message
          });
        }

        // Dispatch générique
        if (msg?.type) this.eventBus.emit?.(msg.type, msg.payload);
      } catch { console.warn('[WebSocket] Message non JSON', ev.data); }
    };

    this.websocket.onclose = (ev) => {
      const code = ev?.code || 1006;
      if (code === 4401 || code === 1008) { this.eventBus.emit?.('auth:missing', { reason: code }); this.websocket = null; return; }
      this._scheduleReconnect();
      this.eventBus.emit?.('ws:close', { code, reason: ev?.reason || '' });
    };

    this.websocket.onerror = (e) => { console.error('[WebSocket] error', e); };
  }

  close(code = 1000, reason = 'normal') {
    try { this.websocket?.close(code, reason); } catch {}
    this.websocket = null;
    if (typeof this._threadWaitUnsub === 'function') {
      try { this._threadWaitUnsub(); } catch {}
    }
    this._threadWaitUnsub = null;
  }

  send(frame) {
    try {
      if (!frame || typeof frame !== 'object') return;

      // De-dup chat.message
      if (frame.type === 'chat.message') {
        const txt = String(frame?.payload?.text ?? '').trim();
        const ag  = String(frame?.payload?.agent_id ?? '').trim().toLowerCase();
        const sig = `${ag}::${txt}`;
        const now = Date.now();
        if (sig && this._lastChatSig === sig && (now - this._lastChatTs) < this._dedupMs) { console.warn('[WebSocket] Duplicate chat.message ignoré (de-dup).'); return; }
        this._lastChatSig = sig; this._lastChatTs = now;
      }

      if (frame.type === 'chat.opinion') {
        const payload = frame && typeof frame === 'object' ? (frame.payload || {}) : {};
        const target = String(payload.target_agent_id ?? payload.targetAgentId ?? '').trim().toLowerCase();
        const messageId = String(payload.message_id ?? payload.messageId ?? '').trim();
        if (target && messageId) {
          const source = String(payload.source_agent_id ?? payload.sourceAgentId ?? '').trim().toLowerCase();
          let messageText = '';
          if (typeof payload.message_text === 'string') messageText = payload.message_text.trim();
          else if (typeof payload.messageText === 'string') messageText = payload.messageText.trim();
          const sig = `${target}|${source}|${messageId}|${messageText}`;
          const nowOpinion = Date.now();
          const previous = this._opinionDedup.get(sig) || 0;
          if (previous && (nowOpinion - previous) < this._dedupMs) {
            console.warn('[WebSocket] Duplicate chat.opinion ignoré (de-dup).');
            return;
          }
          this._opinionDedup.set(sig, nowOpinion);
          if (this._opinionDedup.size > 128) {
            for (const [key, ts] of this._opinionDedup.entries()) {
              if (nowOpinion - ts >= this._dedupMs) this._opinionDedup.delete(key);
            }
            if (this._opinionDedup.size > 160) {
              const overflow = this._opinionDedup.size - 128;
              const keys = Array.from(this._opinionDedup.keys());
              for (let i = 0; i < overflow && i < keys.length; i += 1) {
                this._opinionDedup.delete(keys[i]);
              }
            }
          }
        }
      }

      // Buffer si non OPEN
      if (!this.websocket || this.websocket.readyState !== WebSocket.OPEN) {
        console.warn('[WebSocket] Connexion non ouverte → queue', frame?.type);
        this._sendQueue.push(frame);
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
