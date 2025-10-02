import { test } from 'node:test';
import assert from 'node:assert/strict';

import { WebSocketClient } from '../websocket.js';

function createEventBusStub() {
  return {
    emit() {},
    on() {
      return () => {};
    },
  };
}

function createStateStub() {
  return {
    get() { return undefined; },
    set() {},
  };
}

test('WebSocketClient dedupes repeated chat.opinion frames', async () => {
  const eventBus = createEventBusStub();
  const state = createStateStub();

  class FakeWebSocket {
    constructor() {
      this.sent = [];
      this.readyState = FakeWebSocket.OPEN;
    }

    send(payload) {
      this.sent.push(JSON.parse(payload));
    }
  }
  FakeWebSocket.OPEN = 1;

  const originalWebSocket = global.WebSocket;
  global.WebSocket = FakeWebSocket;

  try {
    const client = new WebSocketClient('ws://local.test', eventBus, state);
    client.websocket = new FakeWebSocket();
    client.websocket.readyState = FakeWebSocket.OPEN;
    client._dedupMs = 20;

    const frame = {
      type: 'chat.opinion',
      payload: {
        target_agent_id: 'nexus',
        source_agent_id: 'neo',
        message_id: 'assistant-1',
        message_text: 'Réponse initiale',
      },
    };

    client.send(frame);
    assert.equal(client.websocket.sent.length, 1);

    client.send(frame);
    assert.equal(client.websocket.sent.length, 1);

    await new Promise((resolve) => setTimeout(resolve, 30));

    client.send(frame);
    assert.equal(client.websocket.sent.length, 2);
  } finally {
    global.WebSocket = originalWebSocket;
  }
});
