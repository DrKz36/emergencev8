// src/frontend/shared/api-client.js
// ÉMERGENCE — API Client (GIS Bearer + retry 401) v3
import { ensureIdToken, getStoredIdToken, clearIdToken } from '../lib/gis.js';

const API_BASE = '/api';

function norm(path) {
  if (!path) return API_BASE + '/';
  if (path.startsWith('http://') || path.startsWith('https://')) return path;
  if (path.startsWith('/api/')) return path;
  if (path.startsWith('/')) return '/api' + path;
  return API_BASE + (path.startsWith('/') ? path : '/' + path);
}

async function withAuthHeaders(headers = {}) {
  const h = new Headers(headers);
  let token = getStoredIdToken();
  if (!token) {
    try { token = await ensureIdToken({ promptIfNeeded: true }); }
    catch (e) { console.warn('[api-client] Pas de token GIS disponible:', e); }
  }
  if (token) h.set('Authorization', 'Bearer ' + token);
  return h;
}

async function coreFetch(path, options = {}, _retry = false) {
  const url = norm(path);
  const headers = await withAuthHeaders(options.headers);
  const res = await fetch(url, { ...options, headers, credentials: 'include' });

  // Token expiré → flush + retry 1x
  if (res.status === 401 && !_retry) {
    console.warn(`[api-client] 401 sur ${path} → flush token + retry`);
    clearIdToken();
    const headers2 = await withAuthHeaders(options.headers);
    return fetch(url, { ...options, headers: headers2, credentials: 'include' });
  }
  return res;
}

async function fetchApi(path, opts = {}) {
  const res = await coreFetch(path, opts);
  if (!res.ok) {
    let detail = '';
    try { detail = await res.text(); } catch {}
    const msg = detail || res.statusText || 'Erreur API';
    console.error(`[API Client] Erreur sur l'endpoint ${norm(path)}: ${msg}`);
    throw new Error(msg);
  }
  const ct = res.headers.get('content-type') || '';
  if (ct.includes('application/json')) return res.json();
  return res.text();
}

/* === Documents =========================================================== */

async function getDocuments() {
  return fetchApi('/api/documents/', { method: 'GET', headers: { 'Accept': 'application/json' } });
}

async function uploadDocument(file, fields = {}) {
  const fd = new FormData();
  fd.append('file', file);
  for (const [k, v] of Object.entries(fields)) fd.append(k, v);
  return fetchApi('/api/documents/upload', { method: 'POST', body: fd });
}

async function deleteDocument(id) {
  return fetchApi(`/api/documents/${encodeURIComponent(id)}`, { method: 'DELETE' });
}

export const api = {
  fetchApi,
  getDocuments,
  uploadDocument,
  deleteDocument,
};
