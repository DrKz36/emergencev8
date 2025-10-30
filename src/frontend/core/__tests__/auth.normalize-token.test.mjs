import { test } from 'node:test';
import assert from 'node:assert/strict';

import { storeAuthToken, getIdToken, clearAuth } from '../auth.js';

function createStorageStub() {
  const map = new Map();
  return {
    getItem(key) {
      return map.has(key) ? map.get(key) : null;
    },
    setItem(key, value) {
      map.set(key, String(value));
    },
    removeItem(key) {
      map.delete(key);
    },
    clear() {
      map.clear();
    },
  };
}

function setupEnvironment() {
  const original = {
    window: global.window,
    document: global.document,
    sessionStorage: global.sessionStorage,
    localStorage: global.localStorage,
  };

  const cookieJar = new Map();
  const documentStub = {
    get cookie() {
      return Array.from(cookieJar.entries()).map(([name, value]) => `${name}=${value}`).join('; ');
    },
    set cookie(value) {
      const [pair, ...rest] = String(value).split(';');
      const [name, rawVal = ''] = pair.split('=');
      if (!name) return;
      const trimmedName = name.trim();
      const trimmedValue = rawVal;
      const hasMaxAgeZero = rest.some((segment) => segment.trim().toLowerCase() === 'max-age=0');
      if (hasMaxAgeZero) {
        cookieJar.delete(trimmedName);
        return;
      }
      cookieJar.set(trimmedName, trimmedValue);
    },
  };

  const windowStub = {
    location: { protocol: 'http:', hostname: 'localhost' },
  };

  global.window = windowStub;
  global.document = documentStub;
  global.sessionStorage = createStorageStub();
  global.localStorage = createStorageStub();

  return () => {
    global.window = original.window;
    global.document = original.document;
    global.sessionStorage = original.sessionStorage;
    global.localStorage = original.localStorage;
    cookieJar.clear();
  };
}

test('storeAuthToken normalises wrapped Bearer tokens and getIdToken retrieves them', () => {
  const restore = setupEnvironment();
  try {
    const normalizedToken = 'aaaa.bbbb=.cccc==';
    const rawToken = `"Bearer ${normalizedToken}"`;

    const stored = storeAuthToken(rawToken);
    assert.equal(stored, normalizedToken);

    assert.equal(sessionStorage.getItem('emergence.id_token'), normalizedToken);
    assert.equal(sessionStorage.getItem('id_token'), normalizedToken);

    const retrieved = getIdToken();
    assert.equal(retrieved, normalizedToken);
  } finally {
    clearAuth();
    restore();
  }
});

test('getIdToken purges invalid stored values', () => {
  const restore = setupEnvironment();
  try {
    sessionStorage.setItem('emergence.id_token', 'not-a-jwt');
    localStorage.setItem('id_token', 'Bearer nope');

    const token = getIdToken();
    assert.equal(token, null);
    assert.equal(sessionStorage.getItem('emergence.id_token'), null);
    assert.equal(localStorage.getItem('id_token'), null);
  } finally {
    clearAuth();
    restore();
  }
});

test('storeAuthToken accepts token= prefixed values with padding', () => {
  const restore = setupEnvironment();
  try {
    const normalizedToken = 'zzzz.yyyy=.xxxx==';
    const stored = storeAuthToken(`token=${normalizedToken}`);
    assert.equal(stored, normalizedToken);

    // Simulate storage being cleared so cookie becomes the source of truth
    sessionStorage.removeItem('emergence.id_token');
    sessionStorage.removeItem('id_token');
    localStorage.removeItem('emergence.id_token');
    localStorage.removeItem('id_token');

    const cookieValue = getIdToken();
    assert.equal(cookieValue, normalizedToken);
  } finally {
    clearAuth();
    restore();
  }
});
