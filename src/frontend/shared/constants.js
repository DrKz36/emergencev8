﻿/**
 * @file /src/frontend/shared/constants.js
 * @description Fichier de constantes V24.1 - "Opération Vélocité"
 * - Réintégration de TOUS les événements pour assurer la communication inter-modules.
 * - Ajout AUTH.TOKEN_KEY pour l’API client.
 */

const wsUrl = '/ws';
console.log(`%c[Config] URL WebSocket configurée pour : ${wsUrl}`, 'color: #4ade80;');

const ICONS = {
    ANIMA: `<svg viewBox="0 0 24 24" fill="currentColor" width="18" height="18" style="vertical-align: middle;"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm-1-12h2v2h-2zm0 4h2v6h-2z"></path></svg>`,
    NEO: `<svg viewBox="0 0 24 24" fill="currentColor" width="18" height="18" style="vertical-align: middle;"><path d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"></path></svg>`,
    NEXUS: `<svg viewBox="0 0 24 24" fill="currentColor" width="18" height="18" style="vertical-align: middle;"><path d="M20.5 10H19V7c0-1.1-.9-2-2-2h-4V3.5C13 2.12 11.88 1 10.5 1S8 2.12 8 3.5V5H4c-1.1 0-2 .9-2 2v3H1.5C.67 10 0 10.67 0 11.5v1C0 13.33.67 14 1.5 14H3v3c0 1.1.9 2 2 2h4v1.5c0 1.38 1.12 2.5 2.5 2.5s2.5-1.12 2.5-2.5V19h4c1.1 0 2-.9 2-2v-3h1.5c.83 0 1.5-.67 1.5-1.5v-1c0-.83-.67-1.5-1.5-1.5z"></path></svg>`
};

export const AGENTS = {
    anima: { id: 'anima', name: 'Anima', icon: ICONS.ANIMA, color: 'var(--color-anima)', cssClass: 'anima', description: 'L\'exploratrice des profondeurs émotionnelles' },
    neo: { id: 'neo', name: 'Neo', icon: ICONS.NEO, color: 'var(--color-neo)', cssClass: 'neo', description: 'Le challenger logique et provocateur' },
    nexus: { id: 'nexus', name: 'Nexus', icon: ICONS.NEXUS, color: 'var(--color-nexus)', cssClass: 'nexus', description: 'Le tisseur de liens et synthétiseur' },
};

export const WS_CONFIG = {
    URL: wsUrl,
    RECONNECT_DELAY: 5000,
};

export const EVENTS = {
    // Core & App Lifecycle
    APP_READY: 'app:ready',
    MODULE_SHOW: 'module:show',

    // WebSocket
    WS_CONNECTED: 'ws:connected',
    WS_SEND: 'ws:send',
    WS_ERROR: 'ws:error',
    SERVER_NOTIFICATION: 'notification',

    // Server Events (ws:)
    WS_SESSION_ESTABLISHED: 'ws:session_established',
    WS_CHAT_STREAM_START: 'ws:chat_stream_start',
    WS_CHAT_STREAM_CHUNK: 'ws:chat_stream_chunk',
    WS_CHAT_STREAM_END: 'ws:chat_stream_end',
    WS_RAG_STATUS: 'ws:rag_status',
    WS_DEBATE_STARTED: 'ws:debate_started',
    WS_DEBATE_TURN_UPDATE: 'ws:debate_turn_update',
    WS_DEBATE_ENDED: 'ws:debate_ended',
    WS_DEBATE_STATUS_UPDATE: 'ws:debate_status_update',

    // UI/Modules
    CHAT_SEND: 'ui:chat:send',
    CHAT_CLEAR: 'ui:chat:clear',
    CHAT_EXPORT: 'ui:chat:export',
    CHAT_MODE_TOGGLED: 'ui:chat:mode_toggled',
    CHAT_AGENT_SELECTED: 'ui:chat:agent_selected',
    CHAT_PARALLEL_AGENTS_CHANGED: 'ui:chat:parallel_agents_changed',
    CHAT_RAG_TOGGLED: 'ui:chat:rag_toggled',

    DEBATE_CREATE: 'debate:create',
    DEBATE_RESET: 'debate:reset',
    DEBATE_EXPORT: 'debate:export',

    SHOW_MODAL: 'ui:show_modal',
    SHOW_NOTIFICATION: 'ui:show_notification',
};

/**
 * ✅ Constantes d'auth centralisées
 * - TOKEN_KEY: clé utilisée par le client API pour récupérer le Bearer en localStorage
 */
export const AUTH = {
    TOKEN_KEY: 'emergence_bearer',
};
