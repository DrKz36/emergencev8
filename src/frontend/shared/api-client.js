// src/frontend/shared/api-client.js
/**
 * @file /src/frontend/shared/api-client.js
 * @description Client API centralisé pour les requêtes HTTP (Fetch).
 * @version V5.0 — pivot fetchWithAuth (GIS) + compat timeouts/retries
 */
import { API_ENDPOINTS } from './config.js';
import { fetchWithAuth } from '../core/auth.js';

const THREADS_BASE =
  (API_ENDPOINTS && API_ENDPOINTS.THREADS) ? API_ENDPOINTS.THREADS : '/api/threads';

const MEMORY_TEND =
  (API_ENDPOINTS && (API_ENDPOINTS.MEMORY_TEND || API_ENDPOINTS.MEMORY_TEND_GARDEN))
    ? (API_ENDPOINTS.MEMORY_TEND || API_ENDPOINTS.MEMORY_TEND_GARDEN)
    : '/api/memory/tend-garden';

const MEMORY_CLEAR =
  (API_ENDPOINTS && (API_ENDPOINTS.MEMORY_CLEAR || API_ENDPOINTS.MEMORY_DELETE))
    ? (API_ENDPOINTS.MEMORY_CLEAR || API_ENDPOINTS.MEMORY_DELETE)
    : '/api/memory/clear';

const MEMORY_STATUS =
  (API_ENDPOINTS && (API_ENDPOINTS.MEMORY_STATUS))
    ? API_ENDPOINTS.MEMORY_STATUS
    : '/api/memory/status';

const DEFAULT_TIMEOUT_MS = 15000;

/* ------------------------------ Utils --------------------------------- */
function buildQuery(params = {}) {
  const entries = Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== '');
  return entries.length ? `?${new URLSearchParams(entries).toString()}` : '';
}

function withTimeout(controller, ms = DEFAULT_TIMEOUT_MS) {
  return setTimeout(() => controller.abort(), ms);
}

/* ------------------------------ Fetch core ---------------------------- */
async function doFetch(endpoint, config, timeoutMs = DEFAULT_TIMEOUT_MS) {
  const controller = new AbortController();
  const timer = withTimeout(controller, timeoutMs);
  const finalConfig = { ...config, signal: controller.signal };

  try {
    const response = await fetchWithAuth(endpoint, finalConfig, { ensure: true });
    if (!response || typeof response.json !== 'function') {
      // fetchWithAuth renvoie Response → on laisse faire ci-dessous
    }
    const res = response;
    if (!res.ok) {
      const contentType = res.headers.get('content-type') || '';
      let errorData = null;
      try { errorData = contentType.includes('application/json') ? await res.json() : null; } catch {}
      const detail = (errorData && (errorData.detail || errorData.message))
        || (res.status === 503 ? 'Service Unavailable' : res.statusText)
        || `Erreur HTTP : ${res.status}`;
      const err = new Error(detail);
      err.status = res.status;
      throw err;
    }
    const ct = res.headers.get('content-type') || '';
    return ct.includes('application/json') ? res.json() : {};
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

/* ------------------------------ API ----------------------------------- */
export const api = {
  /* ---------------------- DOCUMENTS ---------------------- */
  async getDocuments() {
    const url = `${API_ENDPOINTS.DOCUMENTS}/`;
    try {
      const data = await doFetch(url, { method: 'GET' });
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
    return doFetch(API_ENDPOINTS.DOCUMENTS_UPLOAD, { method: 'POST', body: formData });
  },

  deleteDocument: (docId) =>
    doFetch(`${API_ENDPOINTS.DOCUMENTS}/${encodeURIComponent(docId)}`, { method: 'DELETE' }),

  /* ------------------------ THREADS ---------------------- */
  listThreads: ({ type, limit = 20, offset } = {}) =>
    doFetch(`${THREADS_BASE}${buildQuery({ type, limit, offset })}`, { method: 'GET' })
      .then((data) => (Array.isArray(data?.items) ? data : { items: Array.isArray(data) ? data : [] })),

  createThread: ({ type = 'chat', title, metadata, agent_id } = {}) =>
    doFetch(`${THREADS_BASE}/`, { method: 'POST', body: JSON.stringify({ type, title, agent_id, meta: metadata }) })
      .then(async (res) => res),

  getThreadById: async (id, { messages_limit } = {}) => {
    const safeId = String(id || '').trim();
    const url = `${THREADS_BASE}/${encodeURIComponent(safeId)}${buildQuery({ messages_limit })}`;
    try {
      const data = await doFetch(url, { method: 'GET' });
      const t = data?.thread || null;
      const msgs = Array.isArray(data?.messages) ? data.messages : [];
      const docs = Array.isArray(data?.docs) ? data.docs : [];
      return { id: t?.id || safeId, thread: t, messages: msgs, docs };
    } catch (err) {
      if (err?.status === 404) {
        console.warn(`[API Client] Thread ${safeId} introuvable (404) — création d’un nouveau thread.`);
        const created = await doFetch(`${THREADS_BASE}/`, { method: 'POST', body: JSON.stringify({ type: 'chat' }) });
        return { id: created?.id ?? null, thread: created?.thread ?? null, messages: [], docs: [] };
      }
      throw err;
    }
  },

  appendMessage: (threadId, { role = 'user', content, agent_id, meta, metadata } = {}) => {
    const safeId = String(threadId || '').trim();
    if (!safeId) {
      const err = new Error('Thread ID invalide');
      err.status = 400;
      return Promise.reject(err);
    }
    const body = { role, content, agent_id, meta: meta ?? metadata ?? {} };
    return doFetch(`${THREADS_BASE}/${encodeURIComponent(safeId)}/messages`, {
      method: 'POST',
      body: JSON.stringify(body)
    });
  },

  /* ------------------------ MEMORY ----------------------- */
  tendMemory: () => doFetch(MEMORY_TEND, { method: 'POST', body: JSON.stringify({}) }),
  clearMemory: async () => {
    try {
      return await doFetch(MEMORY_CLEAR, { method: 'DELETE' });
    } catch (err) {
      if (err?.status === 404 || err?.status === 405) {
        return await doFetch(MEMORY_CLEAR, { method: 'POST', body: JSON.stringify({}) });
      }
      throw err;
    }
  },
  getMemoryStatus: async () => {
    try { return await doFetch(MEMORY_STATUS, { method: 'GET' }); }
    catch (err) { console.warn('[API Client] /api/memory/status indisponible.', err); throw err; }
  },
};

// Dev: accès console
try { if (typeof window !== 'undefined' && (location.hostname === 'localhost' || location.hostname === '127.0.0.1')) window.api = api; } catch {}
