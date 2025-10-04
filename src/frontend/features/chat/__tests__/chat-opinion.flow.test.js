
import { test } from 'node:test';
import assert from 'node:assert/strict';
import ChatModule from '../chat.js';
import { EVENTS } from '../../../shared/constants.js';

function createStateStub(initial = {}) {
  const store = JSON.parse(JSON.stringify(initial));
  return {
    get(path) {
      if (!path) return store;
      return path.split('.').reduce((acc, key) => (acc && Object.prototype.hasOwnProperty.call(acc, key) ? acc[key] : undefined), store);
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

test('chat opinion flow reuses request id and routes buckets to the source agent', async () => {
  const state = createStateStub({});
  const bus = createEventBusStub();
  const module = new ChatModule(bus, state);

  module.showToast = () => {};
  module._updateThreadCacheFromBuckets = () => {};
  module._clearStreamWatchdog = () => {};
  module._startStreamWatchdog = () => {};
  module._waitForWS = async () => true;
  module._generateMessageId = () => 'client-request-id';

  module.initializeState();
  state.set('chat.currentAgentId', 'neo');
  state.set('chat.activeAgent', 'neo');
  state.set('chat.messages', {
    neo: [{
      id: 'assistant-1',
      role: 'assistant',
      content: 'Réponse initiale',
      agent_id: 'neo',
      created_at: Date.now(),
    }],
  });

  await module.handleOpinionRequest({
    target_agent_id: 'anima',
    source_agent_id: 'neo',
    message_id: 'assistant-1',
    message_text: 'Réponse initiale',
  });

  const wsEvents = bus.events.filter((evt) => evt.name === EVENTS.WS_SEND);
  assert.equal(wsEvents.length, 1);
  const wsFrame = wsEvents[0].payload;
  assert.equal(wsFrame.type, 'chat.opinion');
  const framePayload = wsFrame.payload;
  assert.equal(framePayload.target_agent_id, 'anima');
  assert.equal(framePayload.source_agent_id, 'neo');
  assert.equal(framePayload.message_id, 'assistant-1');
  assert.equal(framePayload.request_id, 'client-request-id');

  const guidanceEvents = bus.events.filter((evt) => evt.name === 'ui:guidance:opinion_request');
  assert.equal(guidanceEvents.length, 1);
  assert.equal(guidanceEvents[0].payload.request_id, 'client-request-id');

  const metrics = state.get('chat.metrics');
  assert.equal(metrics.opinion_request_count, 1);
  assert.equal(metrics.last_opinion_request.bucket, 'neo');

  const neoMessages = state.get('chat.messages.neo');
  assert.equal(neoMessages.length, 2);
  const note = neoMessages.find((msg) => msg.id === 'client-request-id');
  assert(note);
  assert.equal(note.agent_id, 'anima');
  assert.equal(note.meta.opinion_request.request_id, 'client-request-id');
  assert.equal(module._messageBuckets.get('client-request-id'), 'neo');

  // Simulate opinion response streaming from Anima toward Neo bucket
  module.handleStreamStart({
    agent_id: 'anima',
    id: 'stream-1',
    meta: { opinion: { source_agent_id: 'neo', reviewer_agent_id: 'anima', request_note_id: 'client-request-id' } },
  });
  let bucketMessages = state.get('chat.messages.neo');
  const streamingMsg = bucketMessages.find((msg) => msg.id === 'stream-1');
  assert(streamingMsg);
  assert.equal(streamingMsg.agent_id, 'anima');
  assert.equal(module._messageBuckets.get('stream-1'), 'neo');

  module.handleStreamChunk({ agent_id: 'anima', id: 'stream-1', chunk: 'Bravo' });
  module.handleStreamChunk({ agent_id: 'anima', id: 'stream-1', chunk: 'Encore' });
  module.handleStreamChunk({ agent_id: 'anima', id: 'stream-1', chunk: 'Encore' });
  bucketMessages = state.get('chat.messages.neo');
  const chunked = bucketMessages.find((msg) => msg.id === 'stream-1');
  assert.equal(chunked.content, 'BravoEncore');

  module.handleStreamEnd({
    agent_id: 'anima',
    id: 'stream-1',
    meta: { opinion: { source_agent_id: 'neo', reviewer_agent_id: 'anima', request_note_id: 'client-request-id' } },
  });
  bucketMessages = state.get('chat.messages.neo');
  const ended = bucketMessages.find((msg) => msg.id === 'stream-1');
  assert(ended);
  assert.equal(ended.isStreaming, false);
  assert.equal(ended.meta.opinion.source_agent_id, 'neo');

  // Persisted event for the user note with a different backend id
  module.handleMessagePersisted({
    message_id: 'client-request-id',
    id: 'db-note-1',
    role: 'user',
    agent_id: 'anima',
  });
  const persistedNote = state.get('chat.messages.neo').find((msg) => msg.id === 'db-note-1');
  assert(persistedNote);
  assert.equal(persistedNote.meta.opinion_request.request_id, 'db-note-1');
  assert.equal(module._messageBuckets.get('db-note-1'), 'neo');
  assert(!module._messageBuckets.has('client-request-id'));

  // Persisted event for the assistant opinion response
  module._assistantPersistedIds.add('stream-1');
  module.handleMessagePersisted({
    message_id: 'stream-1',
    id: 'db-opinion-1',
    role: 'assistant',
    agent_id: 'anima',
  });
  const persistedOpinion = state.get('chat.messages.neo').find((msg) => msg.id === 'db-opinion-1');
  assert(persistedOpinion);
  assert(!module._assistantPersistedIds.has('stream-1'));
  assert(module._assistantPersistedIds.has('db-opinion-1'));
});
test('chat opinion duplicate request is ignored', async () => {
  const state = createStateStub({});
  const bus = createEventBusStub();
  const module = new ChatModule(bus, state);

  module.showToast = () => {};
  module._updateThreadCacheFromBuckets = () => {};
  module._clearStreamWatchdog = () => {};
  module._startStreamWatchdog = () => {};
  module._waitForWS = async () => true;
  module._generateMessageId = () => 'client-request-id';

  module.initializeState();
  state.set('chat.currentAgentId', 'neo');
  state.set('chat.activeAgent', 'neo');
  state.set('chat.messages', {
    neo: [{
      id: 'assistant-1',
      role: 'assistant',
      content: 'Réponse initiale',
      agent_id: 'neo',
      created_at: Date.now(),
    }],
  });

  await module.handleOpinionRequest({
    target_agent_id: 'anima',
    source_agent_id: 'neo',
    message_id: 'assistant-1',
    message_text: 'Réponse initiale',
  });

  const baselineMessages = state.get('chat.messages.neo').slice();
  bus.events.length = 0;

  module.handleStreamStart({
    agent_id: 'anima',
    id: 'stream-opinion',
    meta: { opinion: { source_agent_id: 'neo', reviewer_agent_id: 'anima', request_note_id: 'client-request-id' } },
  });
  module.handleStreamEnd({
    agent_id: 'anima',
    id: 'stream-opinion',
    meta: { opinion: { source_agent_id: 'neo', reviewer_agent_id: 'anima', request_note_id: 'client-request-id' } },
  });

  await module.handleOpinionRequest({
    target_agent_id: 'anima',
    source_agent_id: 'neo',
    message_id: 'assistant-1',
    message_text: 'Réponse initiale',
  });

  const wsEvents = bus.events.filter((evt) => evt.name === EVENTS.WS_SEND);
  assert.equal(wsEvents.length, 0);
  const updatedMessages = state.get('chat.messages.neo');
  assert.equal(updatedMessages.length, baselineMessages.length + 1);
  const requestMessages = updatedMessages.filter((msg) => msg?.meta?.opinion_request);
  assert.equal(requestMessages.length, 1);
  assert.equal(requestMessages[0].id, 'client-request-id');
});


test('chat opinion retry allowed before response', async () => {
  const state = createStateStub({});
  const bus = createEventBusStub();
  const module = new ChatModule(bus, state);

  module.showToast = () => {};
  module._updateThreadCacheFromBuckets = () => {};
  module._clearStreamWatchdog = () => {};
  module._startStreamWatchdog = () => {};
  module._waitForWS = async () => true;
  let seq = 0;
  module._generateMessageId = () => (seq++ === 0 ? 'req-1' : 'req-2');

  module.initializeState();
  state.set('chat.currentAgentId', 'neo');
  state.set('chat.activeAgent', 'neo');
  state.set('chat.messages', {
    neo: [{
      id: 'assistant-1',
      role: 'assistant',
      content: 'Réponse initiale',
      agent_id: 'neo',
      created_at: Date.now(),
    }],
  });

  await module.handleOpinionRequest({
    target_agent_id: 'anima',
    source_agent_id: 'neo',
    message_id: 'assistant-1',
    message_text: 'Réponse initiale',
  });
  const firstFrame = bus.events.find((evt) => evt.name === EVENTS.WS_SEND);
  assert(firstFrame);
  assert.equal(firstFrame.payload.payload.request_id, 'req-1');

  bus.events.length = 0;
  await module.handleOpinionRequest({
    target_agent_id: 'anima',
    source_agent_id: 'neo',
    message_id: 'assistant-1',
    message_text: 'Réponse initiale',
  });

  const retryEvents = bus.events.filter((evt) => evt.name === EVENTS.WS_SEND);
  assert.equal(retryEvents.length, 1);
  assert.equal(retryEvents[0].payload.payload.request_id, 'req-2');
  const neoMessages = state.get('chat.messages.neo');
  assert(neoMessages.some((msg) => msg.id === 'req-2'));
  assert(!neoMessages.some((msg) => msg.id === 'req-1'));
});

test('chat opinion ws error surfaces toast fallback', () => {
  const state = createStateStub({});
  const bus = createEventBusStub();
  const module = new ChatModule(bus, state);

  const toasts = [];
  module.showToast = (msg) => { toasts.push(msg); };

  const originalWarn = console.warn;
  console.warn = () => {};
  try {
    module.handleWsError({ code: 'opinion_already_exists', message: 'Dupliqué' });
    assert.deepEqual(toasts, ['Dupliqué']);

    toasts.length = 0;
    module.handleWsError({ code: 'opinion_already_exists' });
    assert.deepEqual(toasts, ['Avis déjà disponible pour cette réponse.']);

    toasts.length = 0;
    module.handleWsError({ message: 'Erreur générique' });
    assert.deepEqual(toasts, ['Erreur générique']);
  } finally {
    console.warn = originalWarn;
  }
});

