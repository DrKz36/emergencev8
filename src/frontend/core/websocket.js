/**
 * @module core/websocket
 * @description WebSocketClient V20.1 - STREAMING READY + Bearer au handshake (subprotocols sans espace).
 * Envoie l'ID token via Sec-WebSocket-Protocol: ["jwt", "<JWT>"].
 */
import { EVENTS } from '../shared/constants.js';

export class WebSocketClient {
    constructor(url, eventBus, stateManager) {
        this.url = url;
        this.eventBus = eventBus;
        this.state = stateManager;
        this.websocket = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectInterval = 5000;

        this.registerEvents();
        console.log("✅ WebSocketClient V20.1 (Streaming + JWT subprotocol) Initialisé.");
    }

    registerEvents() {
        this.eventBus.on(EVENTS.WS_SEND, this.send.bind(this));
    }

    async connect() {
        if (this.websocket && this.websocket.readyState !== WebSocket.CLOSED) return;

        let sessionId = this.state.get('websocket.sessionId') || this._generateUUID();
        this.state.set('websocket.sessionId', sessionId);

        const connectUrl = `${this.url}/${sessionId}`;
        const token = await this._getIdToken();

        // ⚠️ IMPORTANT: pas d’espace dans les sous-protocoles → ["jwt", "<JWT>"]
        const protocols = [];
        if (token) {
            protocols.push("jwt", token);
        } else {
            console.error("[WebSocket] ID token manquant — ouvre /dev-auth.html puis réessaie.");
        }

        console.log(`%c[WebSocket] Connexion à : ${connectUrl}`, 'font-weight: bold;');
        this.websocket = new WebSocket(connectUrl, protocols.length ? protocols : undefined);

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
                console.warn(`[WebSocket] Type non géré/mal préfixé: '${receivedType}'`);
            }
        } catch (e) {
            console.error("[WebSocket] Erreur de parsing JSON.", e);
        }
    }

    send(messageObject) {
        if (!messageObject || typeof messageObject !== 'object' || !messageObject.type) { console.error('%c[WebSocket] Message invalide.', 'color: red; font-weight: bold;', messageObject); return; }
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

    async _getIdToken() {
        try {
            if (window.gis?.getIdToken) {
                const t = await window.gis.getIdToken();
                if (t) return t;
            }
        } catch (_) {}
        try {
            return sessionStorage.getItem('emergence.id_token') || localStorage.getItem('emergence.id_token');
        } catch (_) {}
        return null;
    }
}
