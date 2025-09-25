// src/frontend/shared/api-client.js
/**
 * @file /src/frontend/shared/api-client.js
 * @description Client API centralisé pour les requêtes HTTP (Fetch).
 * @version V4.8 - durcissement threadId: sanitize + fallback (getThreadById) + garde (appendMessage)
 */

import { API_ENDPOINTS } from './config.js';

const DEV_BYPASS_KEY = 'emergence.devAuthBypass';

const THREADS_BASE =
  (API_ENDPOINTS && API_ENDPOINTS.THREADS) ? API_ENDPOINTS.THREADS : '/api/threads';

const MEMORY_TEND =
  (API_ENDPOINTS && (API_ENDPOINTS.MEMORY_TEND || API_ENDPOINTS.MEMORY_TEND_GARDEN))
    ? (API_ENDPOINTS.MEMORY_TEND || API_ENDPOINTS.MEMORY_TEND_GARDEN)
    : '/api/memory/tend-garden';

const MEMORY_ANALYZE =
  (API_ENDPOINTS && API_ENDPOINTS.MEMORY_ANALYZE)
    ? API_ENDPOINTS.MEMORY_ANALYZE
    : '/api/memory/analyze';

const MEMORY_CLEAR =
  (API_ENDPOINTS && (API_ENDPOINTS.MEMORY_CLEAR || API_ENDPOINTS.MEMORY_DELETE))
    ? (API_ENDPOINTS.MEMORY_CLEAR || API_ENDPOINTS.MEMORY_DELETE)
    : '/api/memory/clear';

const DEFAULT_TIMEOUT_MS = 15000;

/* ------------------------------ Utils --------------------------------- */
function getCookieValue(name) {
  try {
    const pattern = new RegExp('(?:^|; )' + name + '=([^;]*)');
    const match = (typeof document !== 'undefined' ? document.cookie : '').match(pattern);
    return match ? decodeURIComponent(match[1]) : '';
  } catch (_) {
    return '';
  }
}

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

function isLanHost() {
  try {
    const h = window.location?.hostname || '';
    if (!h) return false;
    if (/^192\.168\./.test(h)) return true;
    if (/^10\./.test(h)) return true;
    if (/^172\.(1[6-9]|2[0-9]|3[0-1])\./.test(h)) return true;
    if (/\.local$/i.test(h)) return true;
    return false;
  } catch {
    return false;
  }
}

function normalizeDevFlag(val) {
  if (val === undefined || val === null) return null;
  const v = String(val).trim().toLowerCase();
  if (!v) return null;
  if (['0', 'false', 'off', 'no', 'none'].includes(v)) return false;
  if (['1', 'true', 'on', 'yes', 'enable'].includes(v)) return true;
  return null;
}

function seedDevBypassFromLocation() {
  try {
    const params = new URLSearchParams(window.location?.search || '');
    const raw = params.get('dev-auth') ?? params.get('devAuth') ?? params.get('dev');
    const normalized = normalizeDevFlag(raw);
    if (normalized === true) {
      localStorage.setItem(DEV_BYPASS_KEY, '1');
    } else if (normalized === false) {
      localStorage.setItem(DEV_BYPASS_KEY, '0');
    }
  } catch {}
}

seedDevBypassFromLocation();

function isDevBypassEnabled() {
  try {
    const stored = localStorage.getItem(DEV_BYPASS_KEY);
    if (stored === '1') return true;
    if (stored === '0') return false;
  } catch {}
  if (isLocalhost()) return true;
  return isLanHost();
}

/** Entêtes de dev (compat backend local si pas de GIS) */
function resolveDevHeaders() {
  const st = getStateFromStorage();
  const userId = st?.user?.id || 'FG';
  const userEmail = st?.user?.email;
  const sessionId = st?.websocket?.sessionId;
  const headers = { 'X-User-Id': userId, 'X-Dev-Bypass': '1' };
  if (userEmail) headers['X-User-Email'] = userEmail;
  if (sessionId) headers['X-Session-Id'] = sessionId;
  return headers;
}

export function getDevUserId() {
  try {
    const st = getStateFromStorage();
    if (st?.user?.id) return String(st.user.id);
  } catch {}
  return 'FG';
}

export function isDevBypassActive() {
  return isDevBypassEnabled();
}

export function getDevBypassHeaders() {
  return resolveDevHeaders();
}

/** ----------------------- Sanitisation threadId ----------------------- **/
const HEX32  = /^[0-9a-f]{32}$/i;
const UUID36 = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
function normalizeThreadId(val) {
  const s = String(val ?? '').trim().replace(/^[?=\/]+/, '');
  if (HEX32.test(s) || UUID36.test(s)) return s;
  return null;
}

function normalizeDocIds(input) {
  const raw = Array.isArray(input) ? input : (input == null ? [] : [input]);
  const seen = new Set();
  const result = [];
  for (const value of raw) {
    if (value === undefined || value === null || value === '') continue;
    const str = String(value).trim();
    if (!str) continue;
    const num = Number(str);
    if (!Number.isFinite(num)) continue;
    const intVal = Math.trunc(num);
    if (seen.has(intVal)) continue;
    seen.add(intVal);
    result.push(intVal);
  }
  return result;
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
  if (!token) {
    token = getCookieValue('id_token');
  }

  const headers = {};
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const sid = getSessionIdFromStorage();
  if (sid) headers['X-Session-Id'] = sid;

  if (isDevBypassEnabled()) {
    Object.assign(headers, resolveDevHeaders());
    if (!token) return headers;
  }
  return headers;
}

/* ------------------------------ Fetch core ---------------------------- */
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

  createThread: ({ type = 'chat', title, metadata, agent_id } = {}) =>
    fetchApi(`${THREADS_BASE}/`, { method: 'POST', body: { type, title, agent_id, meta: metadata } })
      .then((data) => ({ id: data?.id, thread: data?.thread })),

  deleteThread: async (id) => {
    const safeId = normalizeThreadId(id);
    if (!safeId) {
      const err = new Error('Thread ID invalide');
      err.status = 400;
      throw err;
    }
    await fetchApi(`${THREADS_BASE}/${encodeURIComponent(safeId)}`, { method: 'DELETE' });
    return true;
  },
  updateThread: (id, updates = {}) => {
    const safeId = normalizeThreadId(id);
    if (!safeId) {
      const err = new Error('Thread ID invalide');
      err.status = 400;
      return Promise.reject(err);
    }
    const payload = {};
    if (Object.prototype.hasOwnProperty.call(updates, 'title')) payload.title = updates.title;
    const agentValue = updates.agent_id ?? updates.agentId;
    if (agentValue !== undefined) payload.agent_id = agentValue;
    if (Object.prototype.hasOwnProperty.call(updates, 'archived')) payload.archived = !!updates.archived;
    const metaValue = updates.meta ?? updates.metadata;
    if (metaValue !== undefined) payload.meta = metaValue;
    if (!Object.keys(payload).length) return Promise.resolve(null);
    return fetchApi(`${THREADS_BASE}/${encodeURIComponent(safeId)}`, { method: 'PATCH', body: payload })
      .then((data) => data?.thread || null);
  },

  getThreadById: async (id, { messages_limit } = {}) => {
    const safeId = normalizeThreadId(id);
    if (!safeId) {
      console.warn('[API Client] threadId invalide → création d’un nouveau thread (fallback).');
      const created = await api.createThread({ type: 'chat' });
      return { id: created?.id ?? null, thread: created?.thread ?? null, messages: [], docs: [] };
    }
    const url = `${THREADS_BASE}/${encodeURIComponent(safeId)}${buildQuery({ messages_limit })}`;
    try {
      const data = await fetchApi(url);
      const t = data?.thread || null;
      const msgs = Array.isArray(data?.messages) ? data.messages : [];
      const docs = Array.isArray(data?.docs) ? data.docs : [];
      return { id: t?.id || safeId, thread: t, messages: msgs, docs };
    } catch (err) {
      if (err?.status === 404) {
        console.warn(`[API Client] Thread ${safeId} introuvable (404). Création d’un nouveau thread…`);
        const created = await api.createThread({ type: 'chat' });
        return { id: created?.id, thread: created?.thread ?? null, messages: [], docs: [] };
      }
      throw err;
    }
  },

  appendMessage: (threadId, { role = 'user', content, agent_id, meta, metadata } = {}) => {
    const safeId = normalizeThreadId(threadId);
    if (!safeId) {
      const err = new Error('Thread ID invalide');
      err.status = 400;
      return Promise.reject(err);
    }
    const body = { role, content, agent_id, meta: meta ?? metadata ?? {} };
    return fetchApi(`${THREADS_BASE}/${encodeURIComponent(safeId)}/messages`, { method: 'POST', body });
  },

  getThreadDocs: async (threadId) => {
    const safeId = normalizeThreadId(threadId);
    if (!safeId) return { docs: [] };
    const url = `${THREADS_BASE}/${encodeURIComponent(safeId)}/docs`;
    try {
      const data = await fetchApi(url);
      const docs = Array.isArray(data?.docs) ? data.docs : [];
      return { docs };
    } catch (err) {
      if (err?.status === 404) {
        return { docs: [] };
      }
      console.error(`[API Client] Erreur sur l'endpoint ${url}:`, err);
      throw err;
    }
  },

  setThreadDocs: async (threadId, docIds, { mode = 'replace', weight } = {}) => {
    const safeId = normalizeThreadId(threadId);
    if (!safeId) {
      const err = new Error('Thread ID invalide');
      err.status = 400;
      throw err;
    }
    const normalizedIds = normalizeDocIds(docIds);
    const payload = {
      doc_ids: normalizedIds,
      mode: mode === 'append' ? 'append' : 'replace',
    };
    if (weight !== undefined) {
      const numeric = Number(weight);
      if (Number.isFinite(numeric)) payload.weight = numeric;
    }
    const url = `${THREADS_BASE}/${encodeURIComponent(safeId)}/docs`;
    const data = await fetchApi(url, { method: 'POST', body: payload });
    const docs = Array.isArray(data?.docs) ? data.docs : [];
    return { docs };
  },

  /* ------------------------ MEMORY ----------------------- */
  analyzeMemory: ({ force = false, session_id } = {}) => {
    const body = { force: !!force };
    if (session_id) body.session_id = session_id;
    return fetchApi(MEMORY_ANALYZE, { method: 'POST', body });
  },

  // Lance l’analyse/compactage mémoire (non bloquant).
  tendMemory: () => fetchApi(MEMORY_TEND, { method: 'POST', body: {} }),

  // Efface la mémoire de session. Essaie DELETE /api/memory/clear ; si non supporté → POST /api/memory/clear
  clearMemory: async () => {
    try {
      return await fetchApi(MEMORY_CLEAR, { method: 'DELETE' });
    } catch (err) {
      if (err?.status === 404 || err?.status === 405) {
        return await fetchApi(MEMORY_CLEAR, { method: 'POST', body: {} });
      }
      throw err;
    }
  },
};

// Qualité de vie: accès console en dev
try {
  if (isLocalhost() && typeof window !== 'undefined') {
    // @ts-ignore
    window.api = api;
  }
} catch (_) {}

