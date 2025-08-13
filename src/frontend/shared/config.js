/**
 * @file /src/frontend/shared/config.js
 * @description Centralisation des configurations.
 * @version V2.0 - Standardisé et nettoyé.
 */

// ✅ CORRECTION: L'endpoint de suppression est maintenant correct.
export const API_ENDPOINTS = {
    DOCUMENTS: '/api/documents',
    DOCUMENTS_UPLOAD: '/api/documents/upload',
};

export const WS_CONFIG = {
    URL: 'ws://localhost:8000/ws',
    RECONNECT_INTERVAL: 5000,
    MAX_RECONNECT_ATTEMPTS: 10,
    HEARTBEAT_INTERVAL: 30000,
    TIMEOUT: 5000
};
