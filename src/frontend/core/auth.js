/**
 * @module core/auth
 * @description AuthManager V3.1 — GIS + storage + waitForTokenChange
 */
const TOKEN_KEY = 'emergence.id_token';

function _setToken(t) {
  if (!t || !t.trim()) return null;
  const v = t.trim();
  try { sessionStorage.setItem(TOKEN_KEY, v); } catch {}
  try { localStorage.setItem(TOKEN_KEY, v); } catch {}
  return v;
}

export function getIdToken() {
  try {
    if (window.gis?.getIdToken) {
      const t = window.gis.getIdToken();
      if (t) return _setToken(t);
    }
  } catch {}
  try { return sessionStorage.getItem(TOKEN_KEY) || localStorage.getItem(TOKEN_KEY) || null; } catch {}
  return null;
}

export function clearAuth() {
  try { sessionStorage.removeItem(TOKEN_KEY); } catch {}
  try { localStorage.removeItem(TOKEN_KEY); } catch {}
}

function waitForTokenChange(timeoutMs = 60000) {
  return new Promise((resolve) => {
    let done = false;
    const finish = (val) => { if (!done) { done = true; try { window.removeEventListener('storage', onStorage); } catch {} resolve(val || null); } };
    const onStorage = (ev) => {
      try {
        if (ev && ev.key === TOKEN_KEY && ev.newValue && ev.newValue.trim()) {
          finish(ev.newValue.trim());
        }
      } catch {}
    };
    window.addEventListener('storage', onStorage);
    setTimeout(() => finish(null), timeoutMs);
  });
}

function _initOneTap(clientId) {
  const g = window.google?.accounts?.id;
  if (!clientId || !g) return false;
  try {
    g.initialize({
      client_id: clientId,
      callback: (resp) => { if (resp?.credential) _setToken(resp.credential); },
      auto_select: false,
      cancel_on_tap_outside: true,
      use_fedcm_for_prompt: true
    });
    g.prompt();
    return true;
  } catch { return false; }
}

/**
 * ensureAuth
 * - Essaie de récupérer un token (storage/OneTap)
 * - Si interactive: ouvre /dev-auth.html et attend le storage event
 */
export async function ensureAuth({ clientId = null, interactive = false } = {}) {
  let tok = getIdToken();
  if (tok) return tok;

  if (clientId && _initOneTap(clientId)) {
    await new Promise(r => setTimeout(r, 500));
    tok = getIdToken();
    if (tok) return tok;
  }

  if (interactive) {
    try { window.open('/dev-auth.html', '_blank', 'noopener'); } catch {}
    const fromStorage = await waitForTokenChange();
    if (fromStorage) return _setToken(fromStorage);
  }

  return getIdToken();
}
