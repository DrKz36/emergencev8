/**
 * @module core/websocket
 * @description WebSocketClient V21.3 — JWT gating + auto-login (dev-auth) + storage-listener
 */
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

    this._bindEventBus();
    this._bindStorageListener();
    console.log("✅ WebSocketClient V21.3 (JWT gating + auto-login) prêt.");
  }

  _bindEventBus() {
    // UI → chat
    this.eventBus.on?.('ui:chat:send', (payload = {}) => {
      try {
        const text = String(payload.text ?? '').trim();
        if (!text) return;
        const rawAgent = (payload.agent_id ?? payload.agentId ?? '').trim();
        const agent_id = rawAgent || this._getActiveAgentIdFromState();
        const use_rag = Boolean(payload.use_rag ?? payload.useRag);
        this.send({ type: 'chat.message', payload: { text, agent_id, use_rag } });
      } catch (e) { console.error('[WebSocket] ui:chat:send → chat.message a échoué', e); }
    });

    // Frames brutes
    this.eventBus.on?.(EVENTS.WS_SEND, (frame) => this.send(frame));

    // Auth events
    this.eventBus.on?.('auth:login', async (opts = {}) => {
      await ensureAuth({ interactive: true, clientId: opts.client_id || null });
      this.connect();
    });
    this.eventBus.on?.('auth:logout', () => { try { clearAuth(); } catch {} this.close(4001, 'logout'); });

    // Si le serveur réclame l'auth
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
        if (ev.key === 'emergence.id_token' && ev.newValue && ev.newValue.trim()) {
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

  async connect() {
    if (this.websocket && this.websocket.readyState !== WebSocket.CLOSED) return;

    const token = getIdToken() || await ensureAuth({ interactive: false });
    if (!token) {
      this.eventBus.emit('auth:missing', null);
      console.warn('[WebSocket] Aucun ID token — connexion WS annulée.');
      return;
    }

    let sessionId = this.state?.get?.('websocket.sessionId');
    if (!sessionId) {
      sessionId = crypto?.randomUUID?.() || (Math.random().toString(16).slice(2) + Date.now());
      this.state?.set?.('websocket.sessionId', sessionId);
    }

    const loc = window.location;
    const scheme = (loc.protocol === 'https:') ? 'wss' : 'ws';
    const url = `${scheme}://${loc.host}/ws/${sessionId}`;
    const protocols = ['jwt', token];

    try {
      this.websocket = new WebSocket(url, protocols);
    } catch (e) {
      console.error('[WebSocket] new WebSocket() a échoué', e);
      this._scheduleReconnect();
      return;
    }

    this.websocket.onopen = () => {
      this.reconnectAttempts = 0;
      this.eventBus.emit(EVENTS.WS_CONNECTED || 'ws:open', { url });
    };

    this.websocket.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        if (msg?.type === 'ws:auth_required') { this.eventBus.emit('auth:missing', msg?.payload || null); return; }
        if (msg?.type) this.eventBus.emit(msg.type, msg.payload);
      } catch { console.warn('[WebSocket] Message non JSON', ev.data); }
    };

    this.websocket.onclose = (ev) => {
      const code = ev?.code || 1006;
      if (code === 4401 || code === 1008) this.eventBus.emit('auth:missing', { reason: code });
      this._scheduleReconnect();
      this.eventBus.emit('ws:close', { code, reason: ev?.reason || '' });
    };

    this.websocket.onerror = (e) => { console.error('[WebSocket] error', e); };
  }

  close(code = 1000, reason = 'normal') {
    try { this.websocket?.close(code, reason); } catch {} finally { this.websocket = null; }
  }

  send(frame) {
    try {
      if (!frame || typeof frame !== 'object') return;
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
