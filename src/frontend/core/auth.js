/**
 * @module core/auth
 * @description AuthManager V4 - helpers for local JWT (email/password).
 */
const TOKEN_KEYS = ['emergence.id_token', 'id_token'];
const COOKIE_NAME = 'id_token';
const SESSION_COOKIE = 'emergence_session_id';

function shouldUseSecureCookies() {
  try {
    const location = window.location || {};
    const protocol = (location.protocol || '').toLowerCase();
    if (protocol !== 'https:') return false;
    const hostname = (location.hostname || '').toLowerCase();
    return !['localhost', '127.0.0.1', '0.0.0.0', '::1'].includes(hostname);
  } catch (_) {
    return false;
  }
}

function readCookie(name) {
  try {
    const pattern = new RegExp('(?:^|; )' + name + '=([^;]*)');
    const match = (typeof document !== 'undefined' ? document.cookie : '').match(pattern);
    return match ? decodeURIComponent(match[1]) : '';
  } catch (_) {
    return '';
  }
}

function persistTokenInStorage(token) {
  for (const key of TOKEN_KEYS) {
    try { sessionStorage.setItem(key, token); } catch (_) {}
    try { localStorage.setItem(key, token); } catch (_) {}
  }
}

function removeTokenFromStorage() {
  for (const key of TOKEN_KEYS) {
    try { sessionStorage.removeItem(key); } catch (_) {}
    try { localStorage.removeItem(key); } catch (_) {}
  }
}

export function getIdToken() {
  for (const key of TOKEN_KEYS) {
    try {
      const fromSession = sessionStorage.getItem(key);
      if (fromSession && fromSession.trim()) return fromSession.trim();
    } catch (_) {}
    try {
      const fromLocal = localStorage.getItem(key);
      if (fromLocal && fromLocal.trim()) return fromLocal.trim();
    } catch (_) {}
  }
  const fromCookie = readCookie(COOKIE_NAME);
  return fromCookie && fromCookie.trim() ? fromCookie.trim() : null;
}

export function storeAuthToken(token, { expiresAt } = {}) {
  if (!token) return null;
  const trimmed = String(token).trim();
  if (!trimmed) return null;

  persistTokenInStorage(trimmed);

  try {
    const parts = [
      `${COOKIE_NAME}=${encodeURIComponent(trimmed)}`,
      'path=/',
      'SameSite=Lax',
    ];
    if (expiresAt) {
      const dt = new Date(expiresAt);
      if (!Number.isNaN(dt.getTime())) parts.push(`expires=${dt.toUTCString()}`);
      else parts.push('Max-Age=604800');
    } else {
      parts.push('Max-Age=604800');
    }
    if (shouldUseSecureCookies()) parts.push('Secure');
    document.cookie = parts.join('; ');
  } catch (_) {}

  return trimmed;
}

export function clearAuth() {
  removeTokenFromStorage();
  try {
    const base = [`${COOKIE_NAME}=`, 'Max-Age=0', 'path=/', 'SameSite=Lax'];
    if (shouldUseSecureCookies()) base.push('Secure');
    document.cookie = base.join('; ');
  } catch (_) {}
  try {
    const parts = [`${SESSION_COOKIE}=`, 'Max-Age=0', 'path=/', 'SameSite=Lax'];
    if (shouldUseSecureCookies()) parts.push('Secure');
    document.cookie = parts.join('; ');
  } catch (_) {}
}

export async function ensureAuth() {
  return getIdToken();
}
