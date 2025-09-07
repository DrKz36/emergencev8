/**
 * @module core/auth
 * @description AuthManager V4.0 — GIS One-Tap + storage + fetchWithAuth + waitForTokenChange
 *
 * Contexte (Roadmap P0): intégration GIS native + wrapper fetch pour /api/* protégés:contentReference[oaicite:5]{index=5}:contentReference[oaicite:6]{index=6}.
 */

const TOKEN_KEY = 'emergence.id_token';
let _gisClientId = null;

/* ---------------------------------- Storage --------------------------------- */
function _setToken(t) {
  if (!t || !String(t).trim()) return null;
  const v = String(t).trim();
  try { sessionStorage.setItem(TOKEN_KEY, v); } catch {}
  try { localStorage.setItem(TOKEN_KEY, v); } catch {}
  return v;
}

export function getIdToken() {
  // 1) Source GIS locale (si exposée par l’app)
  try {
    if (window.gis?.getIdToken) {
      const t = window.gis.getIdToken();
      if (t) return _setToken(t);
    }
  } catch {}
  // 2) Storage
  try { return sessionStorage.getItem(TOKEN_KEY) || localStorage.getItem(TOKEN_KEY) || null; } catch {}
  return null;
}

export function clearAuth() {
  try { sessionStorage.removeItem(TOKEN_KEY); } catch {}
  try { localStorage.removeItem(TOKEN_KEY); } catch {}
}

/* --------------------------- Token change waiters --------------------------- */
function waitForTokenChange(timeoutMs = 60000) {
  return new Promise((resolve) => {
    let done = false;
    const finish = (val) => {
      if (!done) {
        done = true;
        try { window.removeEventListener('storage', onStorage); } catch {}
        resolve(val || null);
      }
    };
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

/* ------------------------------- GIS One-Tap ------------------------------- */
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
  } catch {
    return false;
  }
}

/* ------------------------------- Public API -------------------------------- */
export function setGisClientId(clientId) {
  _gisClientId = clientId || null;
}

/**
 * ensureAuth
 * - Essaie storage
 * - Tente One-Tap si clientId fourni
 * - Si interactive: ouvre /dev-auth.html (legacy) et attend l’event storage (fallback debug)
 */
export async function ensureAuth({ clientId = _gisClientId, interactive = false } = {}) {
  let tok = getIdToken();
  if (tok) return tok;

  if (clientId && _initOneTap(clientId)) {
    // Laisse One-Tap pousser le credential → storage
    await new Promise(r => setTimeout(r, 500));
    tok = getIdToken();
    if (tok) return tok;
  }

  // Fallback debug (legacy dev-auth) si demandé
  if (interactive) {
    try { window.open('/dev-auth.html', '_blank', 'noopener'); } catch {}
    const fromStorage = await waitForTokenChange();
    if (fromStorage) return _setToken(fromStorage);
  }

  return getIdToken();
}

/* ---------------------------- fetchWithAuth (REST) -------------------------- */
/**
 * fetchWithAuth(input, init?, options?)
 * Injecte automatiquement `Authorization: Bearer <id_token>` pour les endpoints /api/*
 *
 * @param {RequestInfo} input
 * @param {RequestInit} init
 * @param {{ ensure?: boolean, interactive?: boolean, clientId?: string }} options
 *   - ensure: si true, appelle ensureAuth() si aucun token présent.
 *   - interactive: si true, autorise le fallback /dev-auth.html (debug).
 *   - clientId: force un clientId GIS spécifique pour ensureAuth().
 */
export async function fetchWithAuth(input, init = {}, options = {}) {
  const { ensure = true, interactive = false, clientId = _gisClientId } = options;

  let token = getIdToken();
  if (!token && ensure) {
    token = await ensureAuth({ clientId, interactive });
  }

  const headers = new Headers(init.headers || {});
  if (token) headers.set('Authorization', `Bearer ${token}`);

  // JSON par défaut si body objet simple
  const nextInit = { ...init, headers };
  if (nextInit.body && typeof nextInit.body === 'object' && !(nextInit.body instanceof FormData)) {
    headers.set('Content-Type', headers.get('Content-Type') || 'application/json');
    nextInit.body = JSON.stringify(nextInit.body);
  }

  return fetch(input, nextInit);
}

/* ---------------------------- Helpers & Bridges ----------------------------- */
/**
 * Bridge optionnel: expose une mini-API globale pour d’autres modules
 * window.gis.getIdToken() → déjà supporté par getIdToken()
 */
(function bootstrapBridge() {
  if (!window.gis) {
    try {
      window.gis = {
        getIdToken: () => {
          try { return sessionStorage.getItem(TOKEN_KEY) || localStorage.getItem(TOKEN_KEY) || null; } catch { return null; }
        }
      };
    } catch {}
  }
})();
