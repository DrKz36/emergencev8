import { test } from 'node:test';
import assert from 'node:assert/strict';

test('waitForBackendReady falls back to AbortController when AbortSignal.timeout is missing', { concurrency: false }, async () => {
  const originalAbortSignal = globalThis.AbortSignal;
  const originalAbortController = globalThis.AbortController;
  const originalFetch = globalThis.fetch;
  const originalSetTimeout = globalThis.setTimeout;
  const originalClearTimeout = globalThis.clearTimeout;

  const controllers = [];

  class FakeAbortController {
    constructor() {
      this.signal = { aborted: false };
      controllers.push(this);
    }

    abort() {
      this.signal.aborted = true;
    }
  }

  globalThis.AbortSignal = {}; // no timeout support
  globalThis.AbortController = FakeAbortController;

  let scheduledTimeoutId = null;
  let scheduledCallback = null;

  globalThis.setTimeout = (cb, ms) => {
    assert.equal(ms, 5000);
    scheduledTimeoutId = Symbol('timeout');
    scheduledCallback = cb;
    return scheduledTimeoutId;
  };

  let clearedTimeoutId = null;
  globalThis.clearTimeout = (id) => {
    clearedTimeoutId = id;
  };

  const fetchCalls = [];
  globalThis.fetch = async (url, options) => {
    fetchCalls.push({ url, options });
    return {
      ok: true,
      json: async () => ({ ok: true }),
    };
  };

  try {
    const { waitForBackendReady } = await import('../backend-health.js');

    const result = await waitForBackendReady({
      maxRetries: 1,
      timeoutMs: 1000,
      initialDelayMs: 10,
      maxDelayMs: 10,
    });

    assert.ok(result.ok);
    assert.equal(fetchCalls.length, 1);
    assert.equal(fetchCalls[0].url, '/ready');
    assert.ok(fetchCalls[0].options.signal);
    assert.strictEqual(fetchCalls[0].options.signal, controllers[0].signal);
    assert.ok(scheduledCallback, 'fallback should set a timeout');
    assert.strictEqual(clearedTimeoutId, scheduledTimeoutId, 'cleanup should clear the timeout');
    assert.equal(controllers.length, 1);
    assert.equal(controllers[0].signal.aborted, false);
  } finally {
    globalThis.AbortSignal = originalAbortSignal;
    globalThis.AbortController = originalAbortController;
    globalThis.fetch = originalFetch;
    globalThis.setTimeout = originalSetTimeout;
    globalThis.clearTimeout = originalClearTimeout;
  }
});
