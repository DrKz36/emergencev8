/**
 * @file /src/frontend/shared/api-client.js
 * @description Client API centralisé pour les requêtes HTTP (Fetch).
 * @version V4.1 - GIS-first (y compris en localhost), fallback dev-headers seulement si pas de token
 *               - Retry 401 -> refresh GIS si dispo
 *               - window.api exposé en localhost pour tests console
 */

import { API_ENDPOINTS } from './config.js';

const THREADS_BASE = (API_ENDPOINTS && API_ENDPOINTS.THREADS) ? API_ENDPOINTS.THREADS : '/api/threads';

/* ------------------------------ Utils --------------------------------- */
function buildQuery(params = {}) {
  const entries = Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== '');
  return entries.length ? `?${new URLSearchParams(entries).toString()}` : '';
}

function getStateFromStorage() {
  try {
    const raw = localStorage.getItem('emergenceState-V14');
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

function isLocalhost() {
  const h = window.location?.hostname || '';
  return h === 'localhost' || h === '127.0.0.1' || h === '::1';
}

/** Entêtes de dev (compat backend local si pas de GIS) */
function resolveDevHeaders() {
  const st = getStateFromStorage();
  const userId = st?.user?.id || 'FG';
  const userEmail = st?.user?.email;
  const sessionId = st?.websocket?.sessionId;
  const headers = { 'X-User-Id': userId };
  if (userEmail) headers['X-User-Email'] = userEmail;
  if (sessionId) headers['X-Session-Id'] = sessionId;
  return headers;
}

/**
 * Auth headers:
 * - Tente TOUJOURS d’abord un ID token GIS (y compris en localhost).
 * - Si aucun token et qu’on est en localhost → fallback entêtes de dev.
 */
async function getAuthHeaders() {
  let token = null;

  // 1) Wrapper applicatif
  try {
    if (window.gis?.getIdToken) {
      token = await window.gis.getIdToken();
    }
  } catch (_) {}

  // 2) Cache local éventuel
  if (!token) {
    try {
      token = sessionStorage.getItem('emergence.id_token') || localStorage.getItem('emergence.id_token');
    } catch (_) {}
  }

  if (token) return { Authorization: `Bearer ${token}` };

  // 3) Fallback dev UNIQUEMENT si localhost
  if (isLocalhost()) return resolveDevHeaders();

  // 4) Sinon pas d’auth header (laissera un 401 côté backend)
  return {};
}

async function doFetch(endpoint, config) {
  const response = await fetch(endpoint, config);
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ message: response.statusText }));
    const detail = errorData.detail || errorData.message || `Erreur HTTP : ${response.status}`;
    const err = new Error(detail);
    err.status = response.status;
    throw err;
  }
  const contentType = response.headers.get('content-type');
  if (contentType && contentType.includes('application/json')) {
    return response.json();
  }
  return {};
}

/* ------------------------------ Core ---------------------------------- */
async function fetchApi(endpoint, options = {}) {
  const { method = 'GET', body = null, headers = {} } = options;

  // Auth headers (GIS d’abord)
  const authHeaders = await getAuthHeaders();

  // Base headers
  const finalHeaders = { Accept: 'application/json', ...authHeaders, ...headers };
  const config = { method, headers: finalHeaders };

  if (body) {
    if (body instanceof FormData) {
      config.body = body; // ne pas fixer Content-Type
    } else {
      config.body = JSON.stringify(body);
      config.headers['Content-Type'] = 'application/json';
    }
  }

  try {
    return await doFetch(endpoint, config);
  } catch (err) {
    // Retry unique sur 401: demander un token GIS frais si possible
    if (err?.status === 401 && window.gis?.getIdToken) {
      try {
        const fresh = await window.gis.getIdToken();
        if (fresh) {
          config.headers['Authorization'] = `Bearer ${fresh}`;
          try { sessionStorage.setItem('emergence.id_token', fresh); } catch (_) {}
          return await doFetch(endpoint, config);
        }
      } catch (_) {}
    }
    console.error(`[API Client] Erreur sur l'endpoint ${endpoint}:`, err);
    throw err;
  }
}

/* ------------------------------ API ----------------------------------- */
export const api = {
  /* ---------------------- DOCUMENTS ---------------------- */
  getDocuments: () => fetchApi(`${API_ENDPOINTS.DOCUMENTS}/`),

  uploadDocument: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return fetchApi(API_ENDPOINTS.DOCUMENTS_UPLOAD, { method: 'POST', body: formData });
  },

  deleteDocument: (docId) =>
    fetchApi(`${API_ENDPOINTS.DOCUMENTS}/${docId}`, { method: 'DELETE' }),

  /* ------------------------ THREADS ---------------------- */
  listThreads: ({ type, limit = 20, offset } = {}) =>
    fetchApi(`${THREADS_BASE}${buildQuery({ type, limit, offset })}`)
      .then((data) => Array.isArray(data?.items) ? data : { items: [] }),

  // POST sur /api/threads/ (avec slash) pour éviter 405.
  createThread: ({ type = 'chat', title, metadata, agent_id } = {}) =>
    fetchApi(`${THREADS_BASE}/`, { method: 'POST', body: { type, title, agent_id, meta: metadata } })
      .then((data) => ({ id: data?.id, thread: data?.thread })),

  // Normalisation: renvoie toujours { id, thread, messages, docs }
  getThreadById: (id, { messages_limit } = {}) =>
    fetchApi(`${THREADS_BASE}/${encodeURIComponent(id)}${buildQuery({ messages_limit })}`)
      .then((data) => {
        const t = data?.thread || null;
        const msgs = Array.isArray(data?.messages) ? data.messages : [];
        const docs = Array.isArray(data?.docs) ? data.docs : [];
        return { id: t?.id || id, thread: t, messages: msgs, docs };
      }),

  appendMessage: (threadId, { role = 'user', content, agent_id, meta, metadata } = {}) => {
    const body = { role, content, agent_id, meta: meta ?? metadata ?? {} };
    return fetchApi(`${THREADS_BASE}/${encodeURIComponent(threadId)}/messages`, { method: 'POST', body });
  },
};

// Qualité de vie: accès console en dev
try {
  if (isLocalhost() && typeof window !== 'undefined') {
    // @ts-ignore
    window.api = api;
  }
} catch (_) {}
