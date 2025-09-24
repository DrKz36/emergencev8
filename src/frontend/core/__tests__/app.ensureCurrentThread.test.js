import { test } from 'node:test';
import assert from 'node:assert/strict';

import { App } from '../app.js';
import { api } from '../../shared/api-client.js';
import { t } from '../../shared/i18n.js';
import { EVENTS } from '../../shared/constants.js';

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
    assert.equal(state.get('chat.authRequired'), true);
    const toastEvents = bus.events.filter(e => e.name === 'ui:toast');
    assert.equal(toastEvents.length, 1);
    assert.equal(toastEvents[0].payload.text, t('auth.login_required', { locale: 'fr' }));
    const authMissingEvents = bus.events.filter(e => e.name === 'auth:missing');
    assert.equal(authMissingEvents.length, 1);
    const authRequiredEvents = bus.events.filter(e => e.name === EVENTS.AUTH_REQUIRED);
    assert.equal(authRequiredEvents.length, 1);
    assert.equal(authRequiredEvents[0].payload?.message, t('auth.login_required', { locale: 'fr' }));
    const authRestoredEvents = bus.events.filter(e => e.name === EVENTS.AUTH_RESTORED);
    assert.equal(authRestoredEvents.length, 0);
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
    const authRequiredEvents = bus.events.filter(e => e.name === EVENTS.AUTH_REQUIRED);
    assert.equal(authRequiredEvents.length, 1);
    assert.equal(state.get('chat.authRequired'), true);
  });
});




test('ensureCurrentThread emet AUTH_REQUIRED avec les metadonnees attendues', async () => {
  await withStubbedDom(async () => {
    const state = createStateStub();
    const bus = createEventBusStub();
    const app = new App(bus, state);
    const originalListThreads = api.listThreads;
    const error = new Error('Session expirée');
    error.status = 419;
    error.response = { status: 419 };
    api.listThreads = async () => { throw error; };

    try {
      await app.ensureCurrentThread();
    } finally {
      api.listThreads = originalListThreads;
    }

    const authRequiredEvents = bus.events.filter((e) => e.name === EVENTS.AUTH_REQUIRED);
    assert.equal(authRequiredEvents.length, 1);
    const payload = authRequiredEvents[0].payload || {};
    assert.equal(payload.status, 419);
    assert.equal(payload.reason, 'threads_boot_failed');
    assert.equal(payload.message, t('auth.login_required', { locale: 'fr' }));
  });
});

test('ensureCurrentThread regenere un thread inaccessible sans auth:missing', async () => {
  await withStubbedDom(async () => {
    const state = createStateStub({ threads: { currentId: 'thread-private' } });
    const bus = createEventBusStub();
    const originalBootstrap = App.prototype.bootstrapFeatures;
    App.prototype.bootstrapFeatures = function bootstrapNoop() {};
    const originalGetThreadById = api.getThreadById;
    const originalCreateThread = api.createThread;

    const inaccessible = new Error('Thread non accessible pour cet utilisateur');
    inaccessible.status = 403;
    inaccessible.detail = 'Thread non accessible pour cet utilisateur';

    const getCalls = [];
    let createCalls = 0;

    api.getThreadById = async (id) => {
      getCalls.push(id);
      if (id === 'thread-private') {
        throw inaccessible;
      }
      return { id, thread: { id }, messages: [], docs: [] };
    };

    api.createThread = async ({ type, title }) => {
      createCalls += 1;
      return { id: 'new-thread-id', thread: { id: 'new-thread-id', type, title } };
    };

    try {
      const app = new App(bus, state);
      await app.ensureCurrentThread();
    } finally {
      api.getThreadById = originalGetThreadById;
      api.createThread = originalCreateThread;
      App.prototype.bootstrapFeatures = originalBootstrap;
    }

    assert.equal(state.get('threads.currentId'), 'new-thread-id');
    const storedThread = state.get('threads.map.new-thread-id');
    assert.equal(storedThread?.id ?? storedThread?.thread?.id, 'new-thread-id');
    assert.deepEqual(getCalls, ['thread-private', 'new-thread-id']);
    assert.equal(createCalls, 1);
    const authMissingEvents = bus.events.filter(e => e.name === 'auth:missing');
    assert.equal(authMissingEvents.length, 0);
    const authRequiredEvents = bus.events.filter(e => e.name === EVENTS.AUTH_REQUIRED);
    assert.equal(authRequiredEvents.length, 0);
    const authRestoredEvents = bus.events.filter(e => e.name === EVENTS.AUTH_RESTORED);
    assert.equal(authRestoredEvents.length, 1);
    assert.equal(authRestoredEvents[0].payload?.threadId, 'new-thread-id');
    const readyEvents = bus.events.filter(e => e.name === 'threads:ready');
    assert.equal(readyEvents.at(-1)?.payload?.id, 'new-thread-id');
    assert.equal(state.get('chat.authRequired'), false);
  });
});
