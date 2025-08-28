/**
 * @file /src/frontend/shared/config.js
 * @description Centralisation des configurations (prod & dev).
 * @version V3.0 - +THREADS; WS auto wss/ws; valeurs stables et relatives.
 */

function computeWsUrl() {
  try {
    // Choix auto wss/ws selon le protocole courant, fallback '/ws' si indispo (SSR/tests)
    if (typeof window !== 'undefined' && window.location) {
      const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      return `${proto}//${window.location.host}/ws`;
    }
  } catch (_) {}
  return '/ws';
}

export const API_ENDPOINTS = {
  DOCUMENTS: '/api/documents',
  DOCUMENTS_UPLOAD: '/api/documents/upload',
  THREADS: '/api/threads',    // ← ajouté pour solidifier l’API client
};

export const WS_CONFIG = {
  URL: computeWsUrl(),         // ex: wss://emergence-app.ch/ws en prod ; ws://localhost:8000/ws en dev
  RECONNECT_INTERVAL: 5000,
  MAX_RECONNECT_ATTEMPTS: 10,
  HEARTBEAT_INTERVAL: 30000,
  TIMEOUT: 5000,
};
