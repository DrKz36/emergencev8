// src/frontend/shared/api-client.js
/**
 * @file /src/frontend/shared/api-client.js
 * @description Client API centralisé pour les requêtes HTTP (Fetch).
 * @version V4.8 - durcissement threadId: sanitize + fallback (getThreadById) + garde (appendMessage)
 */

import { API_ENDPOINTS } from './config.js';

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

const AUTH_LOGIN = (API_ENDPOINTS && API_ENDPOINTS.AUTH_LOGIN) ? API_ENDPOINTS.AUTH_LOGIN : '/api/auth/login';
const AUTH_SESSION = (API_ENDPOINTS && API_ENDPOINTS.AUTH_SESSION) ? API_ENDPOINTS.AUTH_SESSION : '/api/auth/session';
const AUTH_DEV_LOGIN = '/api/auth/dev/login';
const AUTH_ADMIN_ALLOWLIST = (API_ENDPOINTS && API_ENDPOINTS.AUTH_ADMIN_ALLOWLIST) ? API_ENDPOINTS.AUTH_ADMIN_ALLOWLIST : '/api/auth/admin/allowlist';
const AUTH_ADMIN_SESSIONS = (API_ENDPOINTS && API_ENDPOINTS.AUTH_ADMIN_SESSIONS) ? API_ENDPOINTS.AUTH_ADMIN_SESSIONS : '/api/auth/admin/sessions';
const DASHBOARD_SUMMARY =
  (API_ENDPOINTS && API_ENDPOINTS.DASHBOARD_SUMMARY)
    ? API_ENDPOINTS.DASHBOARD_SUMMARY
    : '/api/dashboard/costs/summary';
const BENCHMARKS_RESULTS =
  (API_ENDPOINTS && API_ENDPOINTS.BENCHMARKS_RESULTS)
    ? API_ENDPOINTS.BENCHMARKS_RESULTS
    : '/api/benchmarks/results';

const BENCHMARKS_SCENARIOS =
  (API_ENDPOINTS && API_ENDPOINTS.BENCHMARKS_SCENARIOS)
    ? API_ENDPOINTS.BENCHMARKS_SCENARIOS
    : '/api/benchmarks/scenarios';


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
    const st = getStateFromStorage();
    return st?.session?.id || st?.websocket?.sessionId || null;
  } catch {
    return null;
  }
}

function getUserIdFromStorage() {
  try {
    const st = getStateFromStorage();
    const raw = st?.user?.id;
    if (raw === null || raw === undefined) return null;
    const str = String(raw).trim();
    return str ? str : null;
  } catch {
    return null;
  }
}

function isLocalhost() {
  const h = window.location?.hostname || '';
  return h === 'localhost' || h === '127.0.0.1' || h === '::1';
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
 * - Lit le token stocké (storage ou cookie) si disponible.
 * - Si aucun token et qu’on est en localhost → fallback entêtes de dev.
 * - Ajoute TOUJOURS X-Session-Id si disponible (corrélation REST/WS).
 */
async function getAuthHeaders() {
  let token = null;

  try {
    token = sessionStorage.getItem('emergence.id_token') || localStorage.getItem('emergence.id_token');
  } catch (_) {}
  if (!token) {
    try {
      token = sessionStorage.getItem('id_token') || localStorage.getItem('id_token');
    } catch (_) {}
  }
  if (!token) {
    token = getCookieValue('id_token');
  }

  const headers = {};
  const trimmed = typeof token === 'string' ? token.trim() : '';
  const hasBearer = !!trimmed;
  if (hasBearer) headers['Authorization'] = `Bearer ${trimmed}`;

  const sid = getSessionIdFromStorage();
  if (sid) headers['X-Session-Id'] = sid;

  const userId = getUserIdFromStorage();
  if (userId) headers['X-User-Id'] = userId;

  return headers;
}

/* ------------------------------ Fetch core ---------------------------- */
async function doFetch(endpoint, config, timeoutMs = DEFAULT_TIMEOUT_MS, externalSignal) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  const abortRelay = () => controller.abort();

  if (externalSignal) {
    if (externalSignal.aborted) {
      controller.abort();
    } else {
      try { externalSignal.addEventListener('abort', abortRelay, { once: true }); } catch (_) {}
    }
  }

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
      const err = new Error('Requete expiree (timeout)');
      err.status = 408;
      throw err;
    }
    throw e;
  } finally {
    clearTimeout(timer);
    if (externalSignal) {
      try { externalSignal.removeEventListener('abort', abortRelay); } catch (_) {}
    }
  }
}

/* ------------------------------ Core ---------------------------------- */
async function fetchApi(endpoint, options = {}) {
  const { method = 'GET', body = null, headers = {}, timeoutMs, signal } = options;
  const authHeaders = await getAuthHeaders();
  const finalHeaders = { Accept: 'application/json', ...authHeaders, ...headers };
  const config = { method, headers: finalHeaders };

  if (body !== undefined && body !== null) {
    const ensureHeader = (name, value) => {
      const lowerName = name.toLowerCase();
      const hasHeader = Object.keys(config.headers).some((key) => String(key).toLowerCase() === lowerName);
      if (!hasHeader) {
        config.headers[name] = value;
      }
    };

    const isFormData = typeof FormData !== 'undefined' && body instanceof FormData;
    const isUrlSearchParams = typeof URLSearchParams !== 'undefined' && body instanceof URLSearchParams;
    const isBlob = typeof Blob !== 'undefined' && body instanceof Blob;
    const isArrayBuffer = typeof ArrayBuffer !== 'undefined'
      && (body instanceof ArrayBuffer || (typeof ArrayBuffer.isView === 'function' && ArrayBuffer.isView(body)));

    if (isFormData || isBlob || isArrayBuffer) {
      config.body = body;
    } else if (isUrlSearchParams) {
      config.body = body;
      ensureHeader('Content-Type', 'application/x-www-form-urlencoded;charset=UTF-8');
    } else if (typeof body === 'string') {
      config.body = body;
    } else if (typeof body === 'object') {
      config.body = JSON.stringify(body);
      ensureHeader('Content-Type', 'application/json');
    } else {
      config.body = body;
    }
  }

  try {
    return await doFetch(endpoint, config, timeoutMs, signal);
  } catch (err) {
    throw err;
  }
}

/* ------------------------------ API ----------------------------------- */
export const api = {
  request(endpoint, options = {}) {
    const url = typeof endpoint === 'string' ? endpoint.trim() : '';
    if (!url) {
      const err = new Error('Endpoint requis.');
      err.status = 400;
      throw err;
    }

    const { query, method, headers, body, timeoutMs, signal } = options;
    let finalUrl = url;

    if (query && typeof query === 'object' && !Array.isArray(query)) {
      const queryString = buildQuery(query);
      if (queryString) {
        if (finalUrl.includes('?')) {
          const separator = finalUrl.endsWith('?') || finalUrl.endsWith('&') ? '' : '&';
          finalUrl += separator + queryString.slice(1);
        } else {
          finalUrl += queryString;
        }
      }
    }

    const fetchOptions = {};
    if (method !== undefined) fetchOptions.method = method;
    if (headers !== undefined && headers !== null) fetchOptions.headers = headers;
    if (body !== undefined) fetchOptions.body = body;
    if (timeoutMs !== undefined) fetchOptions.timeoutMs = timeoutMs;
    if (signal !== undefined) fetchOptions.signal = signal;

    return fetchApi(finalUrl, fetchOptions);
  },

  // Shorthand methods for common HTTP verbs
  get(endpoint, options = {}) {
    return this.request(endpoint, { ...options, method: 'GET' });
  },

  post(endpoint, body, options = {}) {
    return this.request(endpoint, { ...options, method: 'POST', body });
  },

  put(endpoint, body, options = {}) {
    return this.request(endpoint, { ...options, method: 'PUT', body });
  },

  patch(endpoint, body, options = {}) {
    return this.request(endpoint, { ...options, method: 'PATCH', body });
  },

  delete(endpoint, options = {}) {
    return this.request(endpoint, { ...options, method: 'DELETE' });
  },
  /* ------------------------ AUTH ----------------------- */
  authLogin: async ({ email, password, meta, signal } = {}) => {
    const safeEmail = typeof email === 'string' ? email.trim().toLowerCase() : '';
    const safePassword = typeof password === 'string' ? password : '';
    if (!safeEmail || !safePassword) {
      const err = new Error('Email et mot de passe requis.');
      err.status = 400;
      throw err;
    }
    const payload = { email: safeEmail, password: safePassword };
    if (meta && typeof meta === 'object' && !Array.isArray(meta)) {
      payload.meta = meta;
    }
    return fetchApi(AUTH_LOGIN, { method: 'POST', body: payload, signal });
  },
  authDevLogin: async ({ email } = {}) => {
    const safeEmail = typeof email === 'string' ? email.trim().toLowerCase() : '';
    const options = { method: 'POST' };
    if (safeEmail) {
      options.body = { email: safeEmail };
    }
    return fetchApi(AUTH_DEV_LOGIN, options);
  },
  authSession: () => fetchApi(AUTH_SESSION),
  authAdminListAllowlist: ({ status, includeRevoked = false, query, search, page, pageSize } = {}) => {
    const params = new URLSearchParams();
    const normalizedStatus = typeof status === 'string' ? status.trim().toLowerCase() : undefined;
    if (includeRevoked) {
      params.set('include_revoked', 'true');
    } else if (normalizedStatus && ['active', 'all', 'revoked'].includes(normalizedStatus)) {
      params.set('status', normalizedStatus);
    }
    const rawSearch = typeof query === 'string' ? query : (typeof search === 'string' ? search : '');
    if (rawSearch && rawSearch.trim()) {
      params.set('search', rawSearch.trim());
    }
    const pageNumber = Number(page);
    if (Number.isFinite(pageNumber) && pageNumber > 1) {
      params.set('page', String(Math.floor(pageNumber)));
    }
    const pageSizeNumber = Number(pageSize);
    if (Number.isFinite(pageSizeNumber) && pageSizeNumber > 0 && pageSizeNumber !== 20) {
      params.set('page_size', String(Math.floor(pageSizeNumber)));
    }
    const qs = params.toString();
    const url = qs ? `${AUTH_ADMIN_ALLOWLIST}?${qs}` : AUTH_ADMIN_ALLOWLIST;
    return fetchApi(url);
  },
  authAdminUpsertAllowlist: async ({ email, role, note, password, generatePassword } = {}) => {
    const safeEmail = typeof email === 'string' ? email.trim().toLowerCase() : '';
    if (!safeEmail) {
      const err = new Error('Email requis.');
      err.status = 400;
      throw err;
    }
    const payload = { email: safeEmail };
    if (typeof role === 'string' && role.trim()) {
      payload.role = role.trim();
    }
    if (note !== undefined) {
      payload.note = typeof note === 'string' ? note.trim() : note;
    }
    const hasPassword = typeof password === 'string' && password.trim().length > 0;
    if (hasPassword) {
      payload.password = password.trim();
    }
    if (generatePassword) {
      if (hasPassword) {
        const err = new Error('Ne pas combiner mot de passe et génération automatique.');
        err.status = 400;
        throw err;
      }
      payload.generate_password = true;
    }
    return fetchApi(AUTH_ADMIN_ALLOWLIST, { method: 'POST', body: payload });
  },
  authAdminDeleteAllowlist: async ({ email } = {}) => {
    const safeEmail = typeof email === 'string' ? email.trim().toLowerCase() : '';
    if (!safeEmail) {
      const err = new Error('Email requis.');
      err.status = 400;
      throw err;
    }
    const url = `${AUTH_ADMIN_ALLOWLIST}/${encodeURIComponent(safeEmail)}`;
    return fetchApi(url, { method: 'DELETE' });
  },
  authAdminListSessions: ({ status } = {}) => {
    const params = new URLSearchParams();
    const normalized = typeof status === 'string' ? status.trim().toLowerCase() : '';
    if (normalized === 'active') {
      params.set('status_filter', 'active');
    }
    const qs = params.toString();
    const url = qs ? `${AUTH_ADMIN_SESSIONS}?${qs}` : AUTH_ADMIN_SESSIONS;
    return fetchApi(url);
  },


  /* ---------------------- DOCUMENTS ---------------------- */
  async getDocuments() {
    const url = `${API_ENDPOINTS.DOCUMENTS}/`;
    try {
      // Timeout plus long pour la récupération de la liste (peut être lente après upload)
      const data = await fetchApi(url, { timeoutMs: 30000 });
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

  /* ---------------------- DASHBOARD ---------------------- */
  async getDashboardSummary() {
    return fetchApi(DASHBOARD_SUMMARY);
  },

  uploadDocument: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    // Timeout augmenté à 30 min pour gros fichiers (20 000+ lignes : parsing + chunking + DB + vectorisation)
    // Aligné avec timeoutSeconds Cloud Run (1800s)
    return fetchApi(API_ENDPOINTS.DOCUMENTS_UPLOAD, { method: 'POST', body: formData, timeoutMs: 1800000 });
  },

  deleteDocument: (docId) =>
    fetchApi(`${API_ENDPOINTS.DOCUMENTS}/${docId}`, { method: 'DELETE' }),

  getDocumentContent: (docId) =>
    fetchApi(`${API_ENDPOINTS.DOCUMENTS}/${docId}/content`),

  downloadDocument: async (docId) => {
    const headers = await getAuthHeaders();
    const url = `${API_ENDPOINTS.DOCUMENTS}/${docId}/download`;
    const response = await fetch(url, { headers });
    if (!response.ok) {
      throw new Error(`Download failed: ${response.status}`);
    }
    return response.blob();
  },

  reindexDocument: (docId) =>
    fetchApi(`${API_ENDPOINTS.DOCUMENTS}/${docId}/reindex`, { method: 'POST' }),

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
        console.warn(`[API Client] Thread ${safeId} introuvable (404). Création d'un nouveau thread…`);
        // Nettoyer le localStorage pour éviter de réessayer le thread 404
        try {
          const cached = localStorage.getItem('emergence.threadId');
          if (cached === safeId) {
            localStorage.removeItem('emergence.threadId');
          }
        } catch (_) {}
        const created = await api.createThread({ type: 'chat' });
        // Stocker le nouveau thread ID
        try {
          if (created?.id) {
            localStorage.setItem('emergence.threadId', created.id);
          }
        } catch (_) {}
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
  tendMemory: (options = {}) => {
    const payload = {};
    const rawThread = options?.thread_id ?? options?.threadId ?? null;
    if (rawThread && typeof rawThread === 'string' && rawThread.trim()) {
      payload.thread_id = rawThread.trim();
    }
    const agentRaw = options?.agent_id ?? options?.agentId ?? options?.agent ?? null;
    if (agentRaw && typeof agentRaw === 'string' && agentRaw.trim()) {
      payload.agent_id = agentRaw.trim();
    }
    const rawMode = options?.mode ?? options?.scope ?? null;
    if (rawMode && typeof rawMode === 'string') {
      const normalizedMode = rawMode.trim().toLowerCase();
      if (['stm', 'ltm', 'full', 'all'].includes(normalizedMode)) {
        payload.mode = normalizedMode === 'all' ? 'full' : normalizedMode;
      }
    }
    const body = Object.keys(payload).length ? payload : {};
    return fetchApi(MEMORY_TEND, { method: 'POST', body });
  },

  // Récupère l’historique de consolidation mémoire (GET /api/memory/tend-garden).
  getMemoryHistory: ({ limit } = {}) => {
    let url = MEMORY_TEND;
    const size = Number(limit);
    if (Number.isFinite(size) && size > 0) {
      const capped = Math.min(50, Math.max(1, Math.floor(size)));
      const qs = new URLSearchParams({ limit: String(capped) }).toString();
      url = `${MEMORY_TEND}?${qs}`;
    }
    return fetchApi(url);
  },

  // Efface la mémoire de session. Essaie DELETE /api/memory/clear ; si non supporté → POST /api/memory/clear

  // Benchmarks matrices
  getBenchmarkResults: async ({ scenarioId, limit } = {}) => {
    const params = {};
    if (scenarioId) {
      params.scenario_id = String(scenarioId).trim();
    }
    const parsedLimit = Number(limit);
    if (Number.isFinite(parsedLimit)) {
      const bounded = Math.max(1, Math.min(50, Math.floor(parsedLimit)));
      params.limit = bounded;
    }
    const query = buildQuery(params);
    const url = query ? `${BENCHMARKS_RESULTS}${query}` : BENCHMARKS_RESULTS;
    return fetchApi(url);
  },

  getBenchmarkScenarios: async () => fetchApi(BENCHMARKS_SCENARIOS),

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
