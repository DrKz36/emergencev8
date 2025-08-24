/**
 * @file /src/frontend/shared/api-client.js
 * @description Client API centralisé pour les requêtes HTTP (Fetch).
 * @version V3.2 - DevAuth headers + normalisation getThreadById + mapping metadata->meta
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

function resolveDevHeaders() {
  const st = getStateFromStorage();
  const userId = st?.user?.id || 'FG';
  const userEmail = st?.user?.email;
  const sessionId = st?.websocket?.sessionId;

  const headers = { 'X-User-Id': userId }; // requis par le backend en local
  if (userEmail) headers['X-User-Email'] = userEmail;
  if (sessionId) headers['X-Session-Id'] = sessionId;
  return headers;
}

/* ------------------------------ Core ---------------------------------- */
async function fetchApi(endpoint, options = {}) {
  const { method = 'GET', body = null, headers = {} } = options;

  // Injecte les entêtes dev (local) attendues par le backend
  const defaultHeaders = resolveDevHeaders();
  const finalHeaders = { ...defaultHeaders, ...headers };

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
    const response = await fetch(endpoint, config);
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ message: response.statusText }));
      throw new Error(errorData.detail || errorData.message || `Erreur HTTP : ${response.status}`);
    }
    const contentType = response.headers.get("content-type");
    if (contentType && contentType.includes("application/json")) {
      return response.json();
    }
    return {};
  } catch (error) {
    console.error(`[API Client] Erreur sur l'endpoint ${endpoint}:`, error);
    throw error;
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

  createThread: ({ type = 'chat', title, metadata, agent_id } = {}) =>
    fetchApi(THREADS_BASE, { method: 'POST', body: { type, title, agent_id, meta: metadata } })
      .then((data) => ({ id: data?.id, thread: data?.thread })),

  // ⚠️ Normalisation: renvoie toujours un objet avec { id, thread, messages, docs }
  getThreadById: (id, { messages_limit } = {}) =>
    fetchApi(`${THREADS_BASE}/${encodeURIComponent(id)}${buildQuery({ messages_limit })}`)
      .then((data) => {
        const t = data?.thread || null;               // backend: {"thread": {...}, "messages": [...], "docs": [...]}
        const msgs = Array.isArray(data?.messages) ? data.messages : [];
        const docs = Array.isArray(data?.docs) ? data.docs : [];
        return { id: t?.id || id, thread: t, messages: msgs, docs };
      }),

  // Mappe metadata -> meta pour coller au schéma backend MessageCreate (extra ignorés sinon)
  appendMessage: (threadId, { role = 'user', content, agent_id, meta, metadata } = {}) => {
    const body = { role, content, agent_id, meta: meta ?? metadata ?? {} };
    return fetchApi(`${THREADS_BASE}/${encodeURIComponent(threadId)}/messages`, { method: 'POST', body });
  },
};
