/**
 * @module core/auth
 * @description AuthManager V4 - helpers for local JWT (email/password).
 */
const TOKEN_KEYS = ['emergence.id_token', 'id_token'];
const COOKIE_NAME = 'id_token';
const SESSION_COOKIE = 'emergence_session_id';
const JWT_SEGMENT_PATTERN = /^[A-Za-z0-9_-]+={0,2}$/;

function isLikelyJwt(candidate) {
  if (typeof candidate !== 'string') return false;
  const parts = candidate.split('.');
  if (!Array.isArray(parts) || parts.length !== 3) return false;
  for (const part of parts) {
    if (!part || !JWT_SEGMENT_PATTERN.test(part)) {
      return false;
    }
  }
  return true;
}
const JWT_PATTERN = /^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$/;

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

function normalizeToken(raw) {
  if (typeof raw !== 'string') return null;
  let candidate = raw.trim();
  if (!candidate) return null;

  // Remove optional quotes that can appear when storage listeners fire
  candidate = candidate.replace(/^"+|"+$/g, '').replace(/^'+|'+$/g, '');

  const lower = candidate.toLowerCase();
  if (lower.startsWith('bearer ')) {
    return normalizeToken(candidate.slice(7));
  }
  if (lower.startsWith('token=')) {
    const eqIndex = candidate.indexOf('=');
    const remainder = eqIndex >= 0 ? candidate.slice(eqIndex + 1) : '';
    return normalizeToken(remainder);
    return normalizeToken(candidate.split('=', 2)[1] || '');
  }
  if (lower.startsWith('jwt ')) {
    return normalizeToken(candidate.slice(4));
  }

  if (!isLikelyJwt(candidate)) {
  if (!JWT_PATTERN.test(candidate)) {
    return null;
  }

  return candidate;
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
      const rawSession = sessionStorage.getItem(key);
      const fromSession = normalizeToken(rawSession);
      if (fromSession) return fromSession;
      if (rawSession && !fromSession) { sessionStorage.removeItem(key); }
    } catch (_) {}
    try {
      const rawLocal = localStorage.getItem(key);
      const fromLocal = normalizeToken(rawLocal);
      if (fromLocal) return fromLocal;
      if (rawLocal && !fromLocal) { localStorage.removeItem(key); }
    } catch (_) {}
  }
  const fromCookie = normalizeToken(readCookie(COOKIE_NAME));
  return fromCookie || null;
}

export function storeAuthToken(token, { expiresAt } = {}) {
  const normalized = normalizeToken(token);
  if (!normalized) {
    try { console.warn('[Auth] Token invalide ignoré lors de la persistance.'); } catch (_) {}
    return null;
  }

  persistTokenInStorage(normalized);

  try {
    const parts = [
      `${COOKIE_NAME}=${encodeURIComponent(normalized)}`,
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

  return normalized;
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
