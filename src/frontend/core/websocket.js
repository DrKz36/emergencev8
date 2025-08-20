/**
 * @module core/websocket
 * @description WebSocketClient V19.1 - STREAMING READY + user_id dynamique (Google ID token)
 */
import { EVENTS, AUTH } from '../shared/constants.js';

export class WebSocketClient {
    constructor(url, eventBus, stateManager) {
        this.url = url; // ex: '/ws' (relatif, résout ws:// ou wss:// selon l'origine)
        this.eventBus = eventBus;
        this.state = stateManager;
        this.websocket = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectInterval = 5000;

        this.registerEvents();
        console.log("✅ WebSocketClient V19.1 (Streaming Ready + user_id dynamique) Initialisé.");
    }

    registerEvents() {
        this.eventBus.on(EVENTS.WS_SEND, this.send.bind(this));
    }

    _parseJwt(token) {
        if (!token || typeof token !== 'string') return {};
        const parts = token.split('.');
        if (parts.length < 2) return {};
        try {
            const payload = atob(parts[1].replace(/-/g, '+').replace(/_/g, '/'));
            return JSON.parse(decodeURIComponent(escape(payload)));
        } catch {
            try {
                return JSON.parse(atob(parts[1]));
            } catch {
                return {};
            }
        }
    }

    _getUserId(sessionId) {
        // 1) déjà en state ?
        const fromState = this.state && this.state.get ? this.state.get('auth.user_id') : null;
        if (fromState) return fromState;

        // 2) localStorage cache ?
        try {
            const cached = localStorage.getItem('emergence_user_id');
            if (cached) return cached;
        } catch { /* no-op */ }

        // 3) depuis le token (Google ID token) — claims.sub prioritaire, sinon email
        const token = AUTH.getToken() || AUTH.ensureDevToken();
        const claims = this._parseJwt(token);
        const sub = claims && (claims.sub || claims.user_id);
        const email = claims && claims.email;
        let uid = sub || email || `web-${(sessionId || '').slice(0, 8) || 'anon'}`;

        // 4) cache
        try { localStorage.setItem('emergence_user_id', uid); } catch { /* no-op */ }
        if (this.state && this.state.set) this.state.set('auth.user_id', uid);

        return uid;
    }

    connect() {
        if (this.websocket && this.websocket.readyState !== WebSocket.CLOSED) return;

        let sessionId = (this.state && this.state.get && this.state.get('websocket.sessionId')) || this._generateUUID();
        if (this.state && this.state.set) this.state.set('websocket.sessionId', sessionId);

        const userId = this._getUserId(sessionId);
        const connectUrl = `${this.url}/${sessionId}?user_id=${encodeURIComponent(userId)}`;

        console.log(`%c[WebSocket] Connexion à : ${connectUrl}`, 'font-weight: bold;');
        this.websocket = new WebSocket(connectUrl);
        this.websocket.onopen = () => this.onOpen();
        this.websocket.onmessage = (event) => this.onMessage(event);
        this.websocket.onclose = (event) => this.onClose(event);
        this.websocket.onerror = (error) => this.onError(error);
    }

    onOpen() {
        console.log("%c[WebSocket] Connexion établie.", "color: #22c55e;");
        this.eventBus.emit(EVENTS.WS_CONNECTED);
        this.reconnectAttempts = 0;
    }

    onMessage(event) {
        try {
            const data = JSON.parse(event.data);
            const receivedType = data.type;
            const payload = data.payload;

            if (!receivedType) {
                console.warn('[WebSocket] Message reçu sans type, ignoré.', data);
                return;
            }
            if (receivedType.startsWith('ws:')) {
                console.log(`%c[WebSocket] Message Reçu & Routé: ${receivedType}`, 'color: #16a34a;', payload);
                this.eventBus.emit(receivedType, payload);
            } else {
                console.warn(`[WebSocket] Type de message serveur non géré ou mal préfixé: '${receivedType}'`);
            }
        } catch (e) {
            console.error("[WebSocket] Erreur de parsing du message JSON.", e);
        }
    }

    send(messageObject) {
        if (!messageObject || typeof messageObject !== 'object' || !messageObject.type) { console.error('%c[WebSocket] Message invalide bloqué.', 'color: red; font-weight: bold;', messageObject); return; }
        if (!this.websocket || this.websocket.readyState !== WebSocket.OPEN) { console.error('[WebSocket] Connexion non ouverte.', messageObject); return; }
        this.websocket.send(JSON.stringify(messageObject));
    }

    onClose(event) {
        console.warn(`[WebSocket] Connexion fermée. Code: ${event.code}`);
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`Tentative de reconnexion ${this.reconnectAttempts}/${this.maxReconnectAttempts}...`);
            setTimeout(() => this.connect(), this.reconnectInterval);
        } else {
            console.error("[WebSocket] Reconnexion impossible après plusieurs tentatives.");
        }
    }

    onError(error) {
        console.error("[WebSocket] Erreur détectée.", error);
    }

    _generateUUID() {
        return ([1e7]+-1e3+-4e3+-8e3+-1e11).replace(/[018]/g, c => (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16));
    }
}
