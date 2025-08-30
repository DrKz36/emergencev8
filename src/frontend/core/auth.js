/**
 * @module core/auth
 * @description AuthManager V3.0 — GIS + stockage local + helpers
 * - Stocke le token dans sessionStorage sous la clé 'emergence.id_token'
 * - Fournit ensureAuth(), getIdToken(), clearAuth()
 * - Optionnel : tente One Tap si google.accounts.id est dispo, sinon fallback /dev-auth.html
 */
const TOKEN_KEY = 'emergence.id_token';

function setToken(token) {
  try {
    if (token && token.trim()) {
      sessionStorage.setItem(TOKEN_KEY, token.trim());
      try { localStorage.setItem(TOKEN_KEY, token.trim()); } catch (_) {}
      return token.trim();
    }
  } catch (_) {}
  return null;
}

export function getIdToken() {
  try { if (window.gis?.getIdToken) { const t = window.gis.getIdToken(); if (t) return t; } } catch (_) {}
  try { const t = sessionStorage.getItem(TOKEN_KEY) || localStorage.getItem(TOKEN_KEY); if (t) return t; } catch (_) {}
  return null;
}

export function clearAuth() {
  try { sessionStorage.removeItem(TOKEN_KEY); } catch (_) {}
  try { localStorage.removeItem(TOKEN_KEY); } catch (_) {}
}

function initOneTap(clientId) {
  if (!clientId) return false;
  const g = window.google?.accounts?.id;
  if (!g) return false;
  try {
    g.initialize({
      client_id: clientId,
      callback: (resp) => { if (resp?.credential) setToken(resp.credential); },
      auto_select: false,
      cancel_on_tap_outside: true,
      use_fedcm_for_prompt: true,
    });
    g.prompt();
    return true;
  } catch (_) { return false; }
}

/**
 * ensureAuth
 * @param {object} opts
 *  - clientId?: string (si fourni, tente One Tap)
 *  - interactive?: boolean (si true et pas de token → ouvre /dev-auth.html)
 * @returns {Promise<string|null>} id_token
 */
export async function ensureAuth(opts = {}) {
  const { clientId = null, interactive = false } = opts;
  let token = getIdToken();
  if (token) return token;

  if (clientId && initOneTap(clientId)) {
    await new Promise(r => setTimeout(r, 400));
    token = getIdToken();
    if (token) return token;
  }

  if (interactive) {
    try { window.open('/dev-auth.html', '_blank', 'noopener'); } catch (_) {}
  }
  return getIdToken();
}
