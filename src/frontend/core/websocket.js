/**
 * @module core/websocket
 * @description WebSocketClient V21.2 — JWT gating + auto-reconnect + auth events
 * - N’ouvre PAS le WS sans token (émission 'auth:missing'); tente reconnect quand 'auth:token'
 * - Subprotocols: ['jwt', <id_token>] si dispo (fallback ['jwt'])
 * - Bridge EventBus: 'ws:send' (raw) + 'ui:chat:send' → {type:'chat.message', payload:{text,agent_id,use_rag}}
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
    this._bindEventBus();
  }

  _bindEventBus() {
    // UI chat → message agent
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
    this.eventBus.on?.('ws:send', (frame) => this.send(frame));

    // Auth workflow
    this.eventBus.on?.('auth:login', async (opts = {}) => {
      const token = await ensureAuth({ interactive: true, clientId: opts.client_id || null });
      if (token) this.eventBus.emit(EVENTS.AUTH_TOKEN ?? 'auth:token', token);
      this.connect();
    });
    this.eventBus.on?.(EVENTS.AUTH_TOKEN ?? 'auth:token', () => this.connect());
    this.eventBus.on?.('auth:logout', () => { try { clearAuth(); } catch {} this.close(4001, 'logout'); });
  }

  _getActiveAgentIdFromState() {
    try {
      const v = this.state?.get?.('chat.active_agent');
      if (v) return String(v).trim();
      try {
        for (const k of ['chat.active_agent','emergence.active_agent']) {
          const vv = localStorage.getItem(k);
          if (vv && vv.trim()) return vv.trim().toLowerCase();
        }
      } catch {}
    } catch {}
    return 'anima';
  }

  async connect() {
    if (this.websocket && this.websocket.readyState !== WebSocket.CLOSED) return;

    // Gating
    const token = getIdToken() || await ensureAuth({ interactive: false });
    if (!token) {
      this.eventBus.emit('auth:missing', null);
      console.warn('[WebSocket] Aucun ID token — connexion WS annulée.');
      return;
    }

    // Session ID stable
    let sessionId = this.state?.get?.('websocket.sessionId');
    if (!sessionId) {
      sessionId = crypto?.randomUUID?.() || (Math.random().toString(16).slice(2) + Date.now());
      this.state?.set?.('websocket.sessionId', sessionId);
    }

    const url = this._buildWsUrl(sessionId);
    const protocols = token ? ['jwt', token] : ['jwt'];

    try {
      this.websocket = new WebSocket(url, protocols);
    } catch (e) {
      console.error('[WebSocket] new WebSocket() a échoué', e);
      this._scheduleReconnect();
      return;
    }

    this.websocket.onopen = () => {
      this.reconnectAttempts = 0;
      this.eventBus.emit('ws:open', { url });
    };

    this.websocket.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        if (msg?.type === 'ws:auth_required') {
          this.eventBus.emit('auth:missing', msg?.payload || null);
          return;
        }
        this.eventBus.emit(msg.type, msg.payload);
      } catch {
        console.warn('[WebSocket] Message non JSON', ev.data);
      }
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
        console.warn('[WebSocket] Connexion non ouverte, tentative de connect()', frame?.type);
        this.connect();
        return;
      }
      this.websocket.send(JSON.stringify(frame));
    } catch (e) { console.error('[WebSocket] send failed', e); }
  }

  _buildWsUrl(sessionId) {
    const loc = window.location;
    const scheme = (loc.protocol === 'https:') ? 'wss' : 'ws';
    return `${scheme}://${loc.host}/ws/${sessionId}`;
  }

  _scheduleReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) return;
    const delay = Math.min(8000, this.reconnectDelayMs * Math.pow(2, this.reconnectAttempts++));
    setTimeout(() => this.connect(), delay);
  }
}
