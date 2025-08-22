// ÉMERGENCE — Threads API client (fetch only, Authorization déjà patché globalement par ton front)
const API = '/api';

async function parseError(res) {
  let detail = '';
  try { detail = await res.text(); } catch {}
  const err = new Error(`HTTP ${res.status} ${res.statusText}` + (detail ? ` – ${detail}` : ''));
  err.status = res.status;
  err.body = detail;
  return err;
}

export async function listThreads({ archived = false, limit = 50, cursor = '' } = {}) {
  const url = new URL(`${API}/threads`, window.location.origin);
  url.searchParams.set('archived', archived ? 'true' : 'false');
  if (limit) url.searchParams.set('limit', String(limit));
  if (cursor) url.searchParams.set('cursor', cursor);
  const res = await fetch(url.toString(), { headers: { 'Accept': 'application/json' } });
  if (!res.ok) throw await parseError(res);
  return res.json();
}

export async function createThread({ title = '', doc_ids = [] } = {}) {
  const res = await fetch(`${API}/threads`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
    body: JSON.stringify({ title, doc_ids })
  });
  if (!res.ok) throw await parseError(res);
  return res.json(); // { id, ... }
}

export async function patchThread(threadId, patch) {
  const res = await fetch(`${API}/threads/${encodeURIComponent(threadId)}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
    body: JSON.stringify(patch || {})
  });
  if (!res.ok) throw await parseError(res);
  return res.json();
}

export async function exportThread(threadId, format = 'md') {
  const res = await fetch(`${API}/threads/${encodeURIComponent(threadId)}/export?format=${encodeURIComponent(format)}`, {
    method: 'POST'
  });
  if (!res.ok) throw await parseError(res);
  // Tente blob avec fallback texte
  const contentType = res.headers.get('content-type') || '';
  const isText = contentType.includes('text/');
  const filename = `thread_${threadId}.${format === 'json' ? 'json' : 'md'}`;
  if (isText) {
    const text = await res.text();
    downloadBlob(new Blob([text], { type: contentType || 'text/plain' }), filename);
    return { ok: true };
  }
  const blob = await res.blob();
  downloadBlob(blob, filename);
  return { ok: true };
}

export async function postMessage(threadId, { role = 'user', content = '' } = {}) {
  const res = await fetch(`${API}/threads/${encodeURIComponent(threadId)}/messages`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
    body: JSON.stringify({ role, content })
  });
  if (!res.ok) throw await parseError(res);
  return res.json(); // { id, role, content, created_at, ... }
}

/* listMessages : robustesse -> tente /messages ; fallback GET thread complet */
export async function listMessages(threadId, { limit = 200, cursor = '' } = {}) {
  // Option 1: /threads/{id}/messages
  let url = `${API}/threads/${encodeURIComponent(threadId)}/messages`;
  const u = new URL(url, window.location.origin);
  if (limit) u.searchParams.set('limit', String(limit));
  if (cursor) u.searchParams.set('cursor', cursor);
  let res = await fetch(u.toString(), { headers: { 'Accept': 'application/json' } });
  if (res.status === 404) {
    // Option 2: GET /threads/{id}
    res = await fetch(`${API}/threads/${encodeURIComponent(threadId)}`, { headers: { 'Accept': 'application/json' } });
    if (!res.ok) throw await parseError(res);
    const data = await res.json();
    return Array.isArray(data?.messages) ? data.messages : [];
  }
  if (!res.ok) throw await parseError(res);
  return res.json();
}

function downloadBlob(blob, filename) {
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}
