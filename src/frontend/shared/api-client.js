// src/frontend/shared/api-client.js
/**
 * @file /src/frontend/shared/api-client.js
 * @description Client API centralisé (Fetch) avec injection GIS (ID token) intégrée.
 * @version V6.2 — inline fetchWithAuth (GIS) + headers sûrs + timeouts + 401 events
 *
 * Invariants:
 * - Ajoute automatiquement `Authorization: Bearer <ID token>` si disponible.
 * - N'impose pas Content-Type quand body est un FormData.
 * - 401/403 -> lève une erreur explicite et émet un event 'auth:missing'.
 * - Timeout par AbortController (par défaut 15s).
 */

import { API_ENDPOINTS } from './config.js'; // respecte l'arbo

/* ------------------------------ Constantes ----------------------------- */

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

function getIdToken() {
  try {
    // Clés tolérées (StateManager V15.x + GIS)
    const keys = [
      'id_token',
      'google_id_token',
      'emergence_id_token',
      'GIS_ID_TOKEN'
    ];
    for (const k of keys) {
      const v = sessionStorage.getItem(k) || localStorage.getItem(k);
      if (v && typeof v === 'string') return v.trim();
    }
    // Exposition éventuelle par bootstrap
    // eslint-disable-next-line no-underscore-dangle
    const fromWindow = (typeof window !== 'undefined' && window.__EMERGENCE && window.__EMERGENCE.auth && window.__EMERGENCE.auth.id_token) || null;
    if (fromWindow) return String(fromWindow).trim();
  } catch {}
  return null;
}

/**
 * fetchWithAuth (inline)
 * - Ajoute l'ID token si disponible (ou lève une 401 si ensure === true).
 * - Définit Accept / Cache-Control / X-Requested-With.
 * - N'ajoute pas Content-Type si body est FormData.
 */
async function fetchWithAuth(input, init = {}, { ensure = true } = {}) {
  const headers = new Headers(init.headers || {});
  headers.set('Accept', 'application/json');
  headers.set('Cache-Control', 'no-store');
  headers.set('X-Requested-With', 'XMLHttpRequest');

  const isForm = typeof FormData !== 'undefined' && init.body instanceof FormData;
  const hasBody = !!init.body && !isForm;

  if (hasBody && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json; charset=utf-8');
  }

  const token = getIdToken();
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  } else if (ensure) {
    // Signale à l'UI qu'un login est requis.
    try { window.dispatchEvent(new CustomEvent('auth:missing')); } catch {}
    const err = new Error('Authentication required');
    err.status = 401;
    throw err;
  }

  const finalInit = {
    method: init.method || 'GET',
    mode: 'cors',
    cache: 'no-store',
    redirect: 'follow',
    credentials: 'same-origin',
    ...init,
    headers
  };

  return fetch(input, finalInit);
}

/* ------------------------------ Fetch core ---------------------------- */

async function doFetch(endpoint, config, timeoutMs = DEFAULT_TIMEOUT_MS) {
  const controller = new AbortController();
  const timer = withTimeout(controller, timeoutMs);
  const finalConfig = { ...config, signal: controller.signal };

  try {
    const res = await fetchWithAuth(endpoint, finalConfig, { ensure: true });

    // Gestion des statuts non OK
    if (!res.ok) {
      const contentType = res.headers.get('content-type') || '';
      let errorData = null;
      try {
        errorData = contentType.includes('application/json') ? await res.json() : null;
      } catch {}

      const detail =
        (errorData && (errorData.detail || errorData.message)) ||
        (res.status === 503 ? 'Service Unavailable' : res.statusText) ||
        `Erreur HTTP : ${res.status}`;

      const err = new Error(detail);
      err.status = res.status;

      // Événement dédié pour 401/403 (UI peut afficher un CTA login)
      if (err.status === 401 || err.status === 403) {
        try { window.dispatchEvent(new CustomEvent('auth:missing', { detail: { status: err.status } })); } catch {}
      }
      throw err;
    }

    // 204 No Content
    if (res.status === 204) return {};

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
      console.error(`[API Client] Erreur sur l\'endpoint ${url}:`, err);
      throw err;
    }
  },

  uploadDocument: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    // Pas de Content-Type explicite (FormData)
    return doFetch(API_ENDPOINTS.DOCUMENTS_UPLOAD, { method: 'POST', body: formData });
  },

  deleteDocument: (docId) =>
    doFetch(`${API_ENDPOINTS.DOCUMENTS}/${encodeURIComponent(docId)}`, { method: 'DELETE' }),

  /* ------------------------ THREADS ---------------------- */
  listThreads: ({ type, limit = 20, offset } = {}) =>
    doFetch(`${THREADS_BASE}${buildQuery({ type, limit, offset })}`, { method: 'GET' })
      .then((data) => (Array.isArray(data?.items) ? data : { items: Array.isArray(data) ? data : [] })),

  createThread: ({ type = 'chat', title, metadata, agent_id } = {}) =>
    doFetch(`${THREADS_BASE}/`, {
      method: 'POST',
      body: JSON.stringify({ type, title, agent_id, meta: metadata })
    }),

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

// Dev: exposer l'API en local uniquement
try {
  if (typeof window !== 'undefined' && (location.hostname === 'localhost' || location.hostname === '127.0.0.1')) {
    window.api = api;
  }
} catch {}
