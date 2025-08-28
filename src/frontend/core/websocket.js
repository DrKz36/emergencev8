/**
 * @module core/websocket
 * @description WebSocketClient V20.4 - STREAMING READY + JWT subprotocol + bridge 'ui:chat:send' -> 'chat.message'
 * - Fallback agent_id depuis State/Storage (défaut 'anima') pour éviter l'envoi vide au premier message.
 * - Aliases console exposés inconditionnellement: window.wsClient et window.bus.
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
        console.log("✅ WebSocketClient V20.4 (Streaming + JWT subprotocol + UI bridge + console aliases) Initialisé.");
    }

    registerEvents() {
        this.eventBus.on(EVENTS.WS_SEND, this.send.bind(this));

        // Bridge UI -> WS chat
        this.eventBus.on('ui:chat:send', (payload = {}) => {
            try {
                const text = payload.text ?? payload.content ?? payload.message;
                if (typeof text !== 'string' || !text.trim()) {
                    console.warn('[WebSocket] ui:chat:send sans texte, ignoré.', payload);
                    return;
                }
                const rawAgent = (payload.agent_id ?? payload.agentId ?? '').trim();
                const agent_id = rawAgent || this._getActiveAgentIdFromState();
                const use_rag = Boolean(payload.use_rag ?? payload.useRag);
                this.send({ type: 'chat.message', payload: { text, agent_id, use_rag } });
            } catch (e) {
                console.error('[WebSocket] Bridge ui:chat:send -> chat.message a échoué.', e);
            }
        });
    }

    async connect() {
        if (this.websocket && this.websocket.readyState !== WebSocket.CLOSED) return;

        let sessionId = this.state.get('websocket.sessionId') || this._generateUUID();
        this.state.set('websocket.sessionId', sessionId);

        const connectUrl = `${this.url}/${sessionId}`;
        const token = await this._getIdToken();

        const protocols = [];
        if (token) {
            protocols.push('jwt', token);
        } else {
            console.error('[WebSocket] ID token manquant — ouvre /dev-auth.html puis réessaie.');
        }

        console.log(`%c[WebSocket] Connexion à : ${connectUrl}`, 'font-weight: bold;');
        this.websocket = new WebSocket(connectUrl, protocols.length ? protocols : undefined);

        this.websocket.onopen = () => this.onOpen();
        this.websocket.onmessage = (event) => this.onMessage(event);
        this.websocket.onclose = (event) => this.onClose(event);
        this.websocket.onerror = (error) => this.onError(error);
    }

    onOpen() {
        console.log('%c[WebSocket] Connexion établie.', 'color: #22c55e;');
        this.eventBus.emit(EVENTS.WS_CONNECTED);
        this.reconnectAttempts = 0;

        // Aliases console exposés inconditionnellement
        try {
            if (typeof window !== 'undefined') {
                window.wsClient = this;
                window.bus = this.eventBus;
                console.log('[WebSocket] Aliases console exposés: window.wsClient, window.bus');
            }
        } catch (_) {}
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
            console.error('[WebSocket] Erreur de parsing JSON.', e);
        }
    }

    send(messageObject) {
        if (!messageObject || typeof messageObject !== 'object' || !messageObject.type) {
            console.error('%c[WebSocket] Message invalide.', 'color: red; font-weight: bold;', messageObject);
            return;
        }
        if (!this.websocket || this.websocket.readyState !== WebSocket.OPEN) {
            console.error('[WebSocket] Connexion non ouverte.', messageObject);
            return;
        }
        this.websocket.send(JSON.stringify(messageObject));
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

    _getActiveAgentIdFromState() {
        try {
            const keys = ['chat.activeAgent', 'ui.activeAgent', 'agent.selected', 'activeAgent', 'chat.selectedAgent'];
            for (const k of keys) {
                const v = this.state?.get?.(k);
                if (typeof v === 'string' && v.trim()) return v.trim().toLowerCase();
            }
            try {
                const lsKeys = ['emergence.activeAgent', 'chat.activeAgent'];
                for (const k of lsKeys) {
                    const v = localStorage.getItem(k);
                    if (v && v.trim()) return v.trim().toLowerCase();
                }
            } catch (_) {}
        } catch (_) {}
        return 'anima'; // défaut sûr
    }

    async _getIdToken() {
        try { if (window.gis?.getIdToken) { const t = await window.gis.getIdToken(); if (t) return t; } } catch (_) {}
        try { return sessionStorage.getItem('emergence.id_token') || localStorage.getItem('emergence.id_token'); } catch (_) {}
        return null;
    }
}
