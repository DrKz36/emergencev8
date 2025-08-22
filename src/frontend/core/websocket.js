/**
 * @module core/websocket
 * @description WebSocketClient V21.0 — queue d'envoi + auto-reconnect + token en query
 */
import { EVENTS, AUTH } from '../shared/constants.js';

export class WebSocketClient {
  constructor(url, eventBus, stateManager) {
    this.url = url;                     // ex: '/ws'
    this.eventBus = eventBus;
    this.state = stateManager;

    this.websocket = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectInterval = 5000;

    this.outbox = [];                   // ✅ messages en attente avant OPEN
    this._unsubSend = this.eventBus.on(EVENTS.WS_SEND, this.send.bind(this));

    console.log('✅ WebSocketClient V21.0 (Queue + Reconnect) Initialisé.');
  }

  _parseJwt(token) {
    if (!token || typeof token !== 'string') return {};
    const parts = token.split('.');
    if (parts.length < 2) return {};
    try {
      const payload = atob(parts[1].replace(/-/g, '+').replace(/_/g, '/'));
      return JSON.parse(decodeURIComponent(escape(payload)));
    } catch {
      try { return JSON.parse(atob(parts[1])); } catch { return {}; }
    }
  }

  _getUserId(sessionId) {
    const fromState = (this.state && this.state.get) ? this.state.get('auth.user_id') : null;
    if (fromState) return fromState;

    try {
      const cached = localStorage.getItem('emergence_user_id');
      if (cached) return cached;
    } catch {}

    const token = (AUTH && typeof AUTH.getToken === 'function') ? (AUTH.getToken() || AUTH.ensureDevToken()) : null;
    const claims = this._parseJwt(token);
    const sub = claims && (claims.sub || claims.user_id);
    const email = claims && claims.email;
    let uid = sub || email || `web-${(sessionId || '').slice(0, 8) || 'anon'}`;

    try { localStorage.setItem('emergence_user_id', uid); } catch {}
    if (this.state && this.state.set) this.state.set('auth.user_id', uid);
    return uid;
  }

  connect() {
    // ✅ évite les doubles connexions
    if (this.websocket && (this.websocket.readyState === WebSocket.OPEN || this.websocket.readyState === WebSocket.CONNECTING)) {
      return;
    }

    let sessionId = (this.state && this.state.get && this.state.get('websocket.sessionId')) || this._generateUUID();
    if (this.state && this.state.set) this.state.set('websocket.sessionId', sessionId);

    const userId = this._getUserId(sessionId);

    // 🔑 token optionnel
    let token = null;
    try { token = (AUTH && typeof AUTH.getToken === 'function') ? AUTH.getToken() : null; } catch {}

    const qs = `?user_id=${encodeURIComponent(userId)}${token ? `&token=${encodeURIComponent(token)}` : ''}`;
    const connectUrl = `${this.url}/${sessionId}${qs}`;

    console.log(`[WebSocket] Connexion à : ${connectUrl}`);
    this.websocket = new WebSocket(connectUrl);
    this.websocket.onopen = () => this.onOpen();
    this.websocket.onmessage = (event) => this.onMessage(event);
    this.websocket.onclose = (event) => this.onClose(event);
    this.websocket.onerror = (error) => this.onError(error);
  }

  onOpen() {
    console.log('[WebSocket] Connexion établie.');
    this.eventBus.emit(EVENTS.WS_CONNECTED);
    this.reconnectAttempts = 0;

    // ✅ flush de la file d’attente
    try {
      while (this.outbox.length && this.websocket && this.websocket.readyState === WebSocket.OPEN) {
        const msg = this.outbox.shift();
        this._rawSend(msg);
      }
    } catch (e) { console.warn('[WebSocket] flush error:', e); }
  }

  onMessage(event) {
    try {
      const data = JSON.parse(event.data);
      const type = data.type;
      const payload = data.payload;
      if (!type) { console.warn('[WebSocket] Message reçu sans type, ignoré.', data); return; }
      if (type.startsWith('ws:')) {
        console.log(`[WebSocket] Message Reçu & Routé: ${type}`, payload);
        this.eventBus.emit(type, payload);
      } else {
        console.warn(`[WebSocket] Type serveur non géré: '${type}'`);
      }
    } catch (e) {
      console.error('[WebSocket] Erreur de parsing JSON.', e);
    }
  }

  _rawSend(messageObject) {
    try {
      console.log(`[WebSocket] → send ${messageObject.type}`, messageObject);
      this.websocket.send(JSON.stringify(messageObject));
    } catch (e) {
      console.error('[WebSocket] send error:', e, messageObject);
    }
  }

  send(messageObject) {
    if (!messageObject || typeof messageObject !== 'object' || !messageObject.type) {
      console.error('[WebSocket] Message invalide bloqué.', messageObject);
      return;
    }
    // CONNECTING / CLOSED ⇒ on queue + (re)connect
    if (!this.websocket || this.websocket.readyState === WebSocket.CONNECTING || this.websocket.readyState === WebSocket.CLOSED) {
      this.outbox.push(messageObject);
      if (!this.websocket || this.websocket.readyState === WebSocket.CLOSED) this.connect();
      return;
    }
    // NON-OPEN ⇒ queue
    if (this.websocket.readyState !== WebSocket.OPEN) {
      this.outbox.push(messageObject);
      return;
    }
    // OPEN ⇒ envoi direct
    this._rawSend(messageObject);
  }

  onClose(event) {
    console.warn(`[WebSocket] Connexion fermée. Code: ${event.code}`);
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      console.log(`Tentative de reconnexion ${this.reconnectAttempts}/${this.maxReconnectAttempts}...`);
      setTimeout(() => this.connect(), this.reconnectInterval);
    } else {
      console.error('[WebSocket] Reconnexion impossible après plusieurs tentatives.');
    }
  }

  onError(error) { console.error('[WebSocket] Erreur détectée.', error); }

  _generateUUID() {
    return ([1e7]+-1e3+-4e3+-8e3+-1e11).replace(/[018]/g, c =>
      (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
    );
  }
}
