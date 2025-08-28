/**
 * @module core/websocket
 * @description WebSocketClient V20.5 - STREAMING READY + JWT subprotocol + bridge + idempotence
 * - Bridge 'ui:chat:send' -> 'chat.message'
 * - Aliases console inconditionnels (window.wsClient, window.bus)
 * - Déduplication client (fenêtre 1.2s) + msg_uid
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

        // Déduplication des envois de chat côté client
        this._dedupeWindowMs = 1200;
        this._recentChatSends = new Map(); // key -> timestamp

        this.registerEvents();
        console.log("✅ WebSocketClient V20.5 (Streaming + JWT + UI bridge + idempotence) Initialisé.");
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

                const msg = {
                    type: 'chat.message',
                    payload: {
                        text,
                        agent_id,
                        use_rag,
                        // idempotence
                        msg_uid: payload.msg_uid || (crypto?.randomUUID?.() || this._generateUUID()),
                        ts: Date.now()
                    }
                };

                // Déduplication client (même agent + même texte, fenêtre courte)
                const key = `${(agent_id || '').toLowerCase()}|${(text || '').trim().toLowerCase()}`;
                const now = Date.now();
                const last = this._recentChatSends.get(key) || 0;
                if (now - last < this._dedupeWindowMs) {
                    console.warn('[WebSocket] chat.message dédoublonné côté client.', { key, delta: now - last });
                    return;
                }
                this._recentChatSends.set(key, now);

                this.send(msg);
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

        // Garde idempotence générique côté client pour chat.message si un code externe appelle send()
        if (messageObject.type === 'chat.message') {
            try {
                const p = messageObject.payload || {};
                const key = `${(p.agent_id || '').toLowerCase()}|${(p.text || '').trim().toLowerCase()}`;
                const now = Date.now();
                const last = this._recentChatSends.get(key) || 0;
                if (now - last < this._dedupeWindowMs) {
                    console.warn('[WebSocket] chat.message dédoublonné (send direct).', { key, delta: now - last });
                    return;
                }
                this._recentChatSends.set(key, now);
                p.msg_uid = p.msg_uid || (crypto?.randomUUID?.() || this._generateUUID());
                p.ts = p.ts || now;
            } catch (_) {}
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
        return 'anima';
    }

    async _getIdToken() {
        try { if (window.gis?.getIdToken) { const t = await window.gis.getIdToken(); if (t) return t; } } catch (_) {}
        try { return sessionStorage.getItem('emergence.id_token') || localStorage.getItem('emergence.id_token'); } catch (_) {}
        return null;
    }
}
