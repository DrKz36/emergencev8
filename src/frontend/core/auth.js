/**
 * @module core/auth
 * @description AuthManager V5.0 — GIS One-Tap + storage + fetchWithAuth
 * Aligné Roadmap P0/P1 : GIS natif, plus de dev-auth manuel:contentReference[oaicite:4]{index=4}.
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

/* ------------------------- GIS One Tap ------------------------- */
function ensureGisLoaded() {
  return new Promise((resolve, reject) => {
    if (window.google?.accounts?.id) return resolve();
    const s = document.createElement("script");
    s.src = "https://accounts.google.com/gsi/client";
    s.async = true;
    s.defer = true;
    s.onload = () => resolve();
    s.onerror = () => reject(new Error("GIS load error"));
    document.head.appendChild(s);
  });
}

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
}

export async function signOut() {
  clearAuth();
  try { window.google.accounts.id.disableAutoSelect(); } catch {}
}

/* ---------------------- fetchWithAuth -------------------------- */
export async function fetchWithAuth(input, init = {}, { ensure = true } = {}) {
  let token = getIdToken();
  if (!token && ensure) {
    await initGIS({ oneTap: false });
    token = getIdToken();
  }
  const headers = new Headers(init.headers || {});
  if (token) headers.set("Authorization", `Bearer ${token}`);
  return fetch(input, { ...init, headers });
}

/* ---------------------- Global bridge -------------------------- */
(function bootstrapBridge() {
  if (!window.gis) {
    window.gis = { getIdToken: () => getIdToken() };
  }
})();
