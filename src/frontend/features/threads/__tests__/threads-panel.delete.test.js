
import { test } from 'node:test';
import assert from 'node:assert/strict';

import { ThreadsPanel } from '../threads.js';
import { EVENTS } from '../../../shared/constants.js';

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
  const listeners = new Map();
  return {
    events,
    emit(name, payload) {
      events.push({ name, payload });
      const handlers = listeners.get(name) || [];
      handlers.forEach((fn) => {
        try { fn(payload); } catch (error) { console.warn('[eventBusStub] handler error', error); }
      });
    },
    on(name, handler) {
      if (!listeners.has(name)) listeners.set(name, []);
      listeners.get(name).push(handler);
      return () => {
        const arr = listeners.get(name) || [];
        const idx = arr.indexOf(handler);
        if (idx >= 0) arr.splice(idx, 1);
      };
    },
  };
}

test('handleDelete selects the next thread when the active one is removed', async () => {
  const state = createStateStub({
    threads: {
      map: {
        a: { id: 'a', thread: { id: 'a', title: 'Alpha' } },
        b: { id: 'b', thread: { id: 'b', title: 'Beta' } },
      },
      order: ['a', 'b'],
      currentId: 'a',
      status: 'ready',
    },
    chat: { threadId: 'a' },
  });
  const bus = createEventBusStub();
  const panel = new ThreadsPanel(bus, state, { keepMarkup: true });
  panel.render = () => {};
  panel.listEl = { innerHTML: '' };
  panel.newButton = { disabled: false };
  panel.errorEl = { textContent: '', hidden: true };

  const deleteCalls = [];
  panel.deleteThreadFn = async (id) => { deleteCalls.push(id); };

  const selectCalls = [];
  panel.handleSelect = async (id) => { selectCalls.push(id); };
  panel.handleCreate = async () => { throw new Error('handleCreate should not be called'); };

  await panel.handleDelete('a');

  assert.deepEqual(deleteCalls, ['a']);
  assert.equal(state.get('threads.currentId'), 'b');
  assert.equal(state.get('chat.threadId'), 'b');
  assert.deepEqual(state.get('threads.order'), ['b']);
  assert.deepEqual(selectCalls, ['b']);
  const deletionEvents = bus.events.filter((evt) => evt.name === EVENTS.THREADS_DELETED);
  assert.equal(deletionEvents.length, 1);
  assert.equal(deletionEvents[0].payload.id, 'a');
});

test('handleDelete creates a new conversation when the last thread is removed', async () => {
  const state = createStateStub({
    threads: {
      map: { a: { id: 'a', thread: { id: 'a', title: 'Solo' } } },
      order: ['a'],
      currentId: 'a',
      status: 'ready',
    },
    chat: { threadId: 'a' },
  });
  const bus = createEventBusStub();
  const panel = new ThreadsPanel(bus, state, { keepMarkup: true });
  panel.render = () => {};
  panel.listEl = { innerHTML: '' };
  panel.newButton = { disabled: false };
  panel.errorEl = { textContent: '', hidden: true };

  const deleteCalls = [];
  panel.deleteThreadFn = async (id) => { deleteCalls.push(id); };

  let createCalls = 0;
  panel.handleSelect = async () => { throw new Error('handleSelect should not be invoked'); };
  panel.handleCreate = async () => { createCalls += 1; };

  await panel.handleDelete('a');

  assert.deepEqual(deleteCalls, ['a']);
  assert.equal((state.get('threads.order') || []).length, 0);
  assert.equal(createCalls, 1);
  const deletionEvents = bus.events.filter((evt) => evt.name === EVENTS.THREADS_DELETED);
  assert.equal(deletionEvents.length, 1);
  assert.equal(deletionEvents[0].payload.id, 'a');
});
