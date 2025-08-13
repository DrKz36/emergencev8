/**
 * @module core/websocket
 * @description WebSocketClient V19.0 - STREAMING READY.
 * Cette version accepte tous les événements serveur préfixés par 'ws:'
 * pour supporter le streaming et les futures extensions sans modification.
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
        console.log("✅ WebSocketClient V19.0 (Streaming Ready) Initialisé.");
    }

    registerEvents() {
        this.eventBus.on(EVENTS.WS_SEND, this.send.bind(this));
    }

    connect() {
        if (this.websocket && this.websocket.readyState !== WebSocket.CLOSED) return;
        let sessionId = this.state.get('websocket.sessionId') || this._generateUUID();
        this.state.set('websocket.sessionId', sessionId);
        const connectUrl = `${this.url}/${sessionId}?user_id=FG`;
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

            // MODIFICATION V19.0: On accepte tous les événements préfixés par 'ws:'
            // C'est plus flexible et permet de gérer le streaming (start, chunk, end)
            // et les futurs événements sans devoir modifier ce fichier.
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
