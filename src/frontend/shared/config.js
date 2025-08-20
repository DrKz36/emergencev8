/**
 * @file /src/frontend/shared/config.js
 * @description Centralisation des configurations.
 * @version V2.1 - WS relatif (prod-safe) + endpoints stables
 */

export const API_ENDPOINTS = {
    DOCUMENTS: '/api/documents',
    DOCUMENTS_UPLOAD: '/api/documents/upload',
};

export const WS_CONFIG = {
    // ⚠️ Prod-safe: chemin relatif → le navigateur choisit ws:// ou wss:// selon l'origine
    URL: '/ws',
    RECONNECT_INTERVAL: 5000,
    MAX_RECONNECT_ATTEMPTS: 10,
    HEARTBEAT_INTERVAL: 30000,
    TIMEOUT: 5000,
};
