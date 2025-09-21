import { test } from 'node:test';
import assert from 'node:assert/strict';

import { App } from '../app.js';
import { api } from '../../shared/api-client.js';
import { t } from '../../shared/i18n.js';

async function withStubbedDom(fn) {
  const originalDocument = global.document;
  const originalWindow = global.window;
  const hasNavigator = Object.prototype.hasOwnProperty.call(global, 'navigator');
  const originalNavigator = hasNavigator ? global.navigator : undefined;
  const stubBody = {
    appendChild: () => {},
    removeChild: () => {},
    classList: { add: () => {}, remove: () => {} },
  };
  global.document = {
    getElementById: () => null,
    addEventListener: () => {},
    body: stubBody,
  };
  global.window = {
    location: { hostname: 'localhost' },
    gis: null,
    addEventListener: () => {},
    removeEventListener: () => {},
  };
  Object.defineProperty(global, 'navigator', {
    configurable: true,
    enumerable: false,
    writable: true,
    value: { language: 'fr-FR', languages: ['fr-FR'] },
  });
  try {
    return await fn();
  } finally {
    if (originalDocument === undefined) delete global.document;
    else global.document = originalDocument;
    if (originalWindow === undefined) delete global.window;
    else global.window = originalWindow;
    if (!hasNavigator) {
      delete global.navigator;
    } else {
      Object.defineProperty(global, 'navigator', {
        configurable: true,
        enumerable: false,
        writable: true,
        value: originalNavigator,
      });
    }
  }
}

function createStateStub(initial = {}) {
  const store = JSON.parse(JSON.stringify(initial));
  return {
    get(path) {
      return path.split('.').reduce((acc, key) => (acc ? acc[key] : undefined), store);
    },
    set(path, value) {
      const keys = path.split('.');
      let target = store;
      while (keys.length > 1) {
        const key = keys.shift();
        if (!target[key] || typeof target[key] !== 'object') target[key] = {};
        target = target[key];
      }
      target[keys[0]] = value;
    },
  };
}

function createEventBusStub() {
  const events = [];
  return {
    events,
    emit(name, payload) {
      events.push({ name, payload });
    },
  };
}

test('ensureCurrentThread signale la nécessité de connexion sur erreur 401', async () => {
  await withStubbedDom(async () => {
    const state = createStateStub();
    const bus = createEventBusStub();
    const app = new App(bus, state);
    const originalListThreads = api.listThreads;
    const error = new Error('Unauthorized');
    error.status = 401;
    api.listThreads = async () => { throw error; };

    try {
      await app.ensureCurrentThread();
    } finally {
      api.listThreads = originalListThreads;
    }

    assert.equal(state.get('auth.hasToken'), false);
    const toastEvents = bus.events.filter(e => e.name === 'ui:toast');
    assert.equal(toastEvents.length, 1);
    assert.equal(toastEvents[0].payload.text, t('auth.login_required', { locale: 'fr' }));
    const authMissingEvents = bus.events.filter(e => e.name === 'auth:missing');
    assert.equal(authMissingEvents.length, 1);
  });
});

test('ensureCurrentThread ne duplique pas le toast auth', async () => {
  await withStubbedDom(async () => {
    const state = createStateStub();
    const bus = createEventBusStub();
    const app = new App(bus, state);
    const originalListThreads = api.listThreads;
    const error = new Error('Unauthorized');
    error.status = 401;
    api.listThreads = async () => { throw error; };

    try {
      await app.ensureCurrentThread();
      await app.ensureCurrentThread();
    } finally {
      api.listThreads = originalListThreads;
    }

    const toastEvents = bus.events.filter(e => e.name === 'ui:toast');
    assert.equal(toastEvents.length, 1);
  });
});
