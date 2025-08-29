/**
 * @file /src/frontend/shared/api-client.js
 * @description Client API centralisé pour les requêtes HTTP (Fetch).
 * @version V4.4 - 404 auto-recovery threads (create on not found) + logs doux
 */

import { API_ENDPOINTS } from './config.js';

const THREADS_BASE =
  (API_ENDPOINTS && API_ENDPOINTS.THREADS) ? API_ENDPOINTS.THREADS : '/api/threads';

const DEFAULT_TIMEOUT_MS = 15000;

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

function getSessionIdFromStorage() {
  try {
    return getStateFromStorage()?.websocket?.sessionId || null;
  } catch {
    return null;
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
 * - Ajoute TOUJOURS X-Session-Id si disponible (corrélation REST/WS).
 */
async function getAuthHeaders() {
  let token = null;

  try {
    if (window.gis?.getIdToken) {
      token = await window.gis.getIdToken();
      if (token) {
        try { sessionStorage.setItem('emergence.id_token', token); } catch (_) {}
      }
    }
  } catch (_) {}

  if (!token) {
    try {
      token = sessionStorage.getItem('emergence.id_token') || localStorage.getItem('emergence.id_token');
    } catch (_) {}
  }

  const headers = {};
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const sid = getSessionIdFromStorage();
  if (sid) headers['X-Session-Id'] = sid;

  if (!token && isLocalhost()) return { ...headers, ...resolveDevHeaders() };
  return headers;
}

/**
 * Fetch avec timeout + gestion d’erreurs homogène.
 */
async function doFetch(endpoint, config, timeoutMs = DEFAULT_TIMEOUT_MS) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  const finalConfig = { ...config, signal: controller.signal };

  try {
    const response = await fetch(endpoint, finalConfig);
    if (!response.ok) {
      const contentType = response.headers.get('content-type') || '';
      let errorData = null;
      try { errorData = contentType.includes('application/json') ? await response.json() : null; } catch (_) {}
      const detail = (errorData && (errorData.detail || errorData.message))
        || (response.status === 503 ? 'Service Unavailable' : response.statusText)
        || `Erreur HTTP : ${response.status}`;
      const err = new Error(detail);
      err.status = response.status;
      throw err;
    }
    const ct = response.headers.get('content-type') || '';
    return ct.includes('application/json') ? response.json() : {};
  } catch (e) {
    if (e?.name === 'AbortError') {
      const err = new Error('Requête expirée (timeout)');
      err.status = 408;
      throw err;
    }
    throw e;
  } finally {
    clearTimeout(timer);
  }
}

/* ------------------------------ Core ---------------------------------- */
async function fetchApi(endpoint, options = {}) {
  const { method = 'GET', body = null, headers = {}, timeoutMs } = options;
  const authHeaders = await getAuthHeaders();
  const finalHeaders = { Accept: 'application/json', ...authHeaders, ...headers };
  const config = { method, headers: finalHeaders };

  if (body) {
    if (body instanceof FormData) {
      config.body = body;
    } else {
      config.body = JSON.stringify(body);
      config.headers['Content-Type'] = 'application/json';
    }
  }

  try {
    return await doFetch(endpoint, config, timeoutMs);
  } catch (err) {
    // Retry unique sur 401: refresh GIS si possible
    if (err?.status === 401 && window.gis?.getIdToken) {
      try {
        const fresh = await window.gis.getIdToken();
        if (fresh) {
          config.headers['Authorization'] = `Bearer ${fresh}`;
          try { sessionStorage.setItem('emergence.id_token', fresh); } catch (_) {}
          return await doFetch(endpoint, config, timeoutMs);
        }
      } catch (_) {}
    }
    throw err;
  }
}

/* ------------------------------ API ----------------------------------- */
export const api = {
  /* ---------------------- DOCUMENTS ---------------------- */
  async getDocuments() {
    const url = `${API_ENDPOINTS.DOCUMENTS}/`;
    try {
      const data = await fetchApi(url);
      if (Array.isArray(data?.items)) return data;
      if (Array.isArray(data)) return { items: data };
      return { items: [] };
    } catch (err) {
      if (err?.status === 503) {
        console.warn('[API Client] Service Documents indisponible (503) → retour {items: []}.');
        return { items: [] };
      }
      console.error(`[API Client] Erreur sur l'endpoint ${url}:`, err);
      throw err;
    }
  },

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
      .then((data) => (Array.isArray(data?.items) ? data : { items: Array.isArray(data) ? data : [] })),

  // POST sur /api/threads/ (avec slash) pour éviter 405.
  createThread: ({ type = 'chat', title, metadata, agent_id } = {}) =>
    fetchApi(`${THREADS_BASE}/`, { method: 'POST', body: { type, title, agent_id, meta: metadata } })
      .then((data) => ({ id: data?.id, thread: data?.thread })),

  // 🔧 PATCH: auto-recovery si le thread n’existe plus (404 après reset DB)
  getThreadById: async (id, { messages_limit } = {}) => {
    const url = `${THREADS_BASE}/${encodeURIComponent(id)}${buildQuery({ messages_limit })}`;
    try {
      const data = await fetchApi(url);
      const t = data?.thread || null;
      const msgs = Array.isArray(data?.messages) ? data.messages : [];
      const docs = Array.isArray(data?.docs) ? data.docs : [];
      return { id: t?.id || id, thread: t, messages: msgs, docs };
    } catch (err) {
      if (err?.status === 404) {
        console.warn(`[API Client] Thread ${id} introuvable (404). Création d’un nouveau thread…`);
        const created = await api.createThread({ type: 'chat' });
        return { id: created?.id, thread: created?.thread ?? null, messages: [], docs: [] };
      }
      throw err;
    }
  },

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
