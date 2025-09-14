/**
 * @module core/auth
 * AuthManager V5.1 — GIS One-Tap + storage + fetchWithAuth + ensureAuth + setGisClientId + renderGoogleButton
 * Motif : build Vite cassé car state-manager attend { setGisClientId }. On expose aussi ensureAuth & renderGoogleButton.
 */

const TOKEN_KEY = "emergence.id_token";
let _gisClientId = "486095406755-mbjgt9np24o4jg15jrgko74dennlqhp7.apps.googleusercontent.com";

/* --------------------------- Storage --------------------------- */
function _setToken(t) {
  if (!t || !String(t).trim()) return null;
  const v = String(t).trim();
  try { sessionStorage.setItem(TOKEN_KEY, v); } catch {}
  try { localStorage.setItem(TOKEN_KEY, v); } catch {}
  return v;
}

export function getIdToken() {
  try { return sessionStorage.getItem(TOKEN_KEY) || localStorage.getItem(TOKEN_KEY) || null; } catch {}
  return null;
}

export function clearAuth() {
  try { sessionStorage.removeItem(TOKEN_KEY); } catch {}
  try { localStorage.removeItem(TOKEN_KEY); } catch {}
}

/* ------------------------- GIS loader -------------------------- */
function ensureGisLoaded() {
  return new Promise((resolve, reject) => {
    if (window.google?.accounts?.id) return resolve();
    const s = document.createElement("script");
    s.src = "https://accounts.google.com/gsi/client";
    s.async = true; s.defer = true;
    s.onload = () => resolve();
    s.onerror = () => reject(new Error("GIS load error"));
    document.head.appendChild(s);
  });
}

/* ----------------------- Public API GIS ------------------------ */
let _inited = false;

export async function initGIS({ clientId = _gisClientId, oneTap = true } = {}) {
  _gisClientId = clientId;
  await ensureGisLoaded();
  window.google.accounts.id.initialize({
    client_id: _gisClientId,
    auto_select: false,
    callback: (resp) => { if (resp?.credential) _setToken(resp.credential); }
  });
  if (oneTap) {
    try { window.google.accounts.id.prompt(); } catch {}
  }
  _inited = true;
}

/** Compat pour anciens imports (state-manager) */
export function setGisClientId(nextId) {
  if (nextId && typeof nextId === "string") _gisClientId = nextId.trim();
  return _gisClientId;
}

export async function signOut() {
  clearAuth();
  try { window.google?.accounts?.id?.disableAutoSelect(); } catch {}
}

/** Bouton Google (optionnel) */
export async function renderGoogleButton(containerSelector = "#gsi-btn", options = {}) {
  await ensureGisLoaded();
  const el = document.querySelector(containerSelector);
  if (!el) return;
  const opts = {
    type: "standard", theme: "outline", size: "large",
    text: "signin_with", shape: "rectangular", logo_alignment: "left", width: 260,
    ...options
  };
  window.google.accounts.id.renderButton(el, opts);
}

/* ---------------------- fetch / ensure ------------------------- */
export async function fetchWithAuth(input, init = {}, { ensure = true } = {}) {
  let token = getIdToken();
  if (!token && ensure) {
    await initGIS({ clientId: _gisClientId, oneTap: false });
    token = getIdToken();
  }
  const headers = new Headers(init.headers || {});
  if (token) headers.set("Authorization", `Bearer ${token}`);
  return fetch(input, { ...init, headers });
}

/** Garde simple côté front : exige un token sinon redirige vers /auth.html */
export async function ensureAuth({ redirectTo = "/auth.html", required = true } = {}) {
  const tok = getIdToken();
  if (tok) return tok;
  // tente une init silencieuse si GIS déjà prêt
  try {
    if (!_inited) await initGIS({ clientId: _gisClientId, oneTap: false });
  } catch {}
  const again = getIdToken();
  if (again) return again;
  if (required) {
    try { window.location.replace(redirectTo); } catch {}
    throw new Error("auth_required");
  }
  return null;
}

/* ---------------------- Global bridge -------------------------- */
(function bootstrapBridge() {
  if (!window.gis) {
    window.gis = { getIdToken: () => getIdToken(), setGisClientId: (v) => setGisClientId(v) };
  }
})();
