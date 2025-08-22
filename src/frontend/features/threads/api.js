/**
 * @module features/threads/api
 * Client REST Threads — V1.8 (aligné threads-list)
 * - Exports Nommés attendus par threads-list:
 *   listThreads, createThread, patchThread, exportThread, postMessage, listMessages
 * - Auth: Bearer ID token (GIS) si dispo; sinon fallback dev via X-User-Id quand VITE_AUTH_DEV_MODE === '1'
 * - Aucune dépendance externe; respecte l’arbo.
 */

import { AUTH } from '../../shared/constants.js'; // présent dans l’arbo

// ---- Base & helpers ---------------------------------------------------------------------------

const API_BASE = (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_API_BASE)
  ? String(import.meta.env.VITE_API_BASE).replace(/\/+$/, '')
  : ''; // même origine → '' (les chemins commencent par /api)

const DEV_MODE = (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_AUTH_DEV_MODE === '1');

function getIdToken() {
  try {
    if (AUTH && typeof AUTH.getToken === 'function') {
      const t = AUTH.getToken();
      if (t) return t;
    }
  } catch { /* ignore */ }
  try {
    if (typeof window !== 'undefined') {
      return window.__EMERGENCE_ID_TOKEN || localStorage.getItem('emergence.idToken') || null;
    }
  } catch { /* ignore */ }
  return null;
}

function buildHeaders(isJson = true) {
  const h = new Headers();
  if (isJson) h.set('Content-Type', 'application/json');

  const token = getIdToken();
  if (token) h.set('Authorization', `Bearer ${token}`);
  else if (DEV_MODE) h.set('X-User-Id', 'dev_alice');

  return h;
}

async function req(path, { method = 'GET', body, headers, expect = 'json' } = {}) {
  const url = `${API_BASE}/api${path}`;
  const opts = {
    method,
    headers: headers instanceof Headers ? headers : buildHeaders(body != null),
    credentials: 'include',
    body: body == null ? undefined : (typeof body === 'string' ? body : JSON.stringify(body)),
  };

  const res = await fetch(url, opts);
  const ctype = res.headers.get('content-type') || '';
  const isJSON = ctype.includes('application/json');

  if (!res.ok) {
    let msg = `${res.status} ${res.statusText}`;
    try {
      if (isJSON) {
        const err = await res.json();
        if (err && (err.detail || err.message)) msg = `${msg} — ${err.detail || err.message}`;
      } else {
        const txt = await res.text();
        if (txt) msg = `${msg} — ${txt.slice(0, 400)}`;
      }
    } catch { /* ignore */ }
    const e = new Error(msg);
    e.status = res.status;
    throw e;
  }

  if (expect === 'text') return res.text();
  if (expect === 'blob') return res.blob();
  if (expect === 'json' || isJSON) return res.json();
  return res.text();
}

function qs(params = {}) {
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== '') sp.append(k, String(v));
  }
  const s = sp.toString();
  return s ? `?${s}` : '';
}

function download(filename, mime, data) {
  try {
    const blob = data instanceof Blob ? data : new Blob([data], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.style.display = 'none';
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    setTimeout(() => { URL.revokeObjectURL(url); a.remove(); }, 0);
  } catch (e) { console.error('download failed', e); }
}

// ---- Exports Nommés (API attendue par threads-list) -------------------------------------------

/** Liste des threads (option: archived=true/false, limit, before) */
export async function listThreads(opts = {}) {
  const { archived = false, limit, before } = opts;
  return req(`/threads${qs({ archived: archived ? 'true' : undefined, limit, before })}`, { method: 'GET' });
}

/** Création de thread: payload ex { title?: string, doc_ids?: string[] } */
export async function createThread(payload = {}) {
  return req(`/threads`, { method: 'POST', body: payload });
}

/** Patch (rename, archive…) : patchThread(id, { title } | { archived }) */
export async function patchThread(threadId, patch) {
  if (!threadId) throw new Error('patchThread: threadId manquant');
  return req(`/threads/${encodeURIComponent(threadId)}`, { method: 'PATCH', body: patch });
}

/** Export (md|json) avec téléchargement client */
export async function exportThread(threadId, format = 'md') {
  if (!threadId) throw new Error('exportThread: threadId manquant');
  const f = String(format || 'md').toLowerCase();
  // Essai endpoint dédié
  try {
    if (f === 'md' || f === 'markdown') {
      const text = await req(`/threads/${encodeURIComponent(threadId)}/export?format=markdown`, { method: 'GET', expect: 'text' });
      download(`thread-${threadId}.md`, 'text/markdown;charset=utf-8', text);
      return { ok: true, format: 'md' };
    } else {
      const json = await req(`/threads/${encodeURIComponent(threadId)}/export?format=json`, { method: 'GET', expect: 'json' });
      const text = JSON.stringify(json, null, 2);
      download(`thread-${threadId}.json`, 'application/json;charset=utf-8', text);
      return { ok: true, format: 'json' };
    }
  } catch {
    // Fallback: GET thread puis export local
    const data = await req(`/threads/${encodeURIComponent(threadId)}`, { method: 'GET' });
    if (f === 'md') {
      const title = data?.title || `thread-${threadId}`;
      const lines = [`# ${title}`, ''];
      if (Array.isArray(data?.messages)) {
        for (const m of data.messages) {
          const who = (m.role || 'user').toUpperCase();
          const ts = m.timestamp || m.created_at || '';
          lines.push(`**${who}** ${ts ? `*(${ts})*` : ''}`);
          lines.push(m.content || '');
          lines.push('');
        }
      }
      download(`thread-${threadId}.md`, 'text/markdown;charset=utf-8', lines.join('\n'));
      return { ok: true, format: 'md', fallback: true };
    } else {
      const text = JSON.stringify(data || {}, null, 2);
      download(`thread-${threadId}.json`, 'application/json;charset=utf-8', text);
      return { ok: true, format: 'json', fallback: true };
    }
  }
}

/** Liste des messages d’un thread (opts: limit, before) */
export async function listMessages(threadId, opts = {}) {
  if (!threadId) throw new Error('listMessages: threadId manquant');
  const { limit, before } = opts;
  return req(`/threads/${encodeURIComponent(threadId)}/messages${qs({ limit, before })}`, { method: 'GET' });
}

/** Ajout d’un message { role, content, agent?, rag_sources?, ts? } */
export async function postMessage(threadId, message) {
  if (!threadId) throw new Error('postMessage: threadId manquant');
  if (!message || typeof message !== 'object') throw new Error('postMessage: payload invalide');
  return req(`/threads/${encodeURIComponent(threadId)}/messages`, { method: 'POST', body: message });
}

// ---- Export par défaut (facultatif) ------------------------------------------------------------

const ThreadsAPI = {
  listThreads,
  createThread,
  patchThread,
  exportThread,
  listMessages,
  postMessage,
};

export default ThreadsAPI;
