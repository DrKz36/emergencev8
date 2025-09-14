// src/frontend/core/state-manager.js
/**
 * @module core/state-manager
 * @description Gestionnaire d'état V15.5 — Threads Aware + GIS ensureAuth + auth required @ boot
 */
import { AGENTS } from '../shared/constants.js';
import { ensureAuth as ensureAuthCore, getIdToken, setGisClientId } from './auth.js';

export class StateManager {
  constructor() {
    this.DEFAULT_STATE = this.getInitialState();
    this.state = this.DEFAULT_STATE;
    this.subscribers = new Map();
    console.log("✅ StateManager V15.5 (Threads Aware + GIS ensureAuth + auth-required@boot).");
  }

  async init(opts = {}) {
    const { requireAuth = true } = opts;

    // Passer le clientId GIS si présent en meta
    try {
      const meta = document.querySelector('meta[name="google-signin-client_id"]');
      if (meta && meta.content) setGisClientId(meta.content.trim());
    } catch {}

    const savedState = this.loadFromStorage();
    let mergedState = this._deepMerge(this.DEFAULT_STATE, savedState);
    this.state = this.sanitize(mergedState);

    // 1) tentative douce
    try {
      const tokBefore = getIdToken();
      if (!tokBefore) {
        await ensureAuthCore({ interactive: false });
      }
    } catch {}

    // 2) exigence éventuelle d'auth
    let has = !!getIdToken();
    if (requireAuth && !has && location.pathname !== '/auth.html') {
      try { await ensureAuthCore({ interactive: true }); } catch {}
      has = !!getIdToken();
      if (!has) {
        try { location.assign('/auth.html'); } catch {}
      }
    }
    this.set('auth.hasToken', !!getIdToken());

    console.log("[StateManager] Initialized: state sanitized & persisted.");
    this.persist();
  }

  sanitize(stateToClean) {
    let cleanState = { ...stateToClean };

    cleanState.agents = cleanState.agents || {};
    for (const agentId of Object.keys(AGENTS)) {
      cleanState.agents[agentId] = cleanState.agents[agentId] || { status: 'disconnected', history: [] };
    }

    cleanState.connection = cleanState.connection || { status: 'disconnected', attempt: 0 };
    cleanState.costs = cleanState.costs || { total: 0, last_session: 0 };
    cleanState.debate = cleanState.debate || { status: 'idle', topic: null, history: [] };
    cleanState.user = cleanState.user || { id: 'FG', name: 'Fernando' };
    cleanState.threads = cleanState.threads || { currentId: null, map: {} };
    cleanState.auth = cleanState.auth || { hasToken: false };

    cleanState.chat = cleanState.chat || {};
    cleanState.chat.lastMessageMeta = cleanState.chat.lastMessageMeta || null;
    cleanState.chat.modelInfo = cleanState.chat.modelInfo || null;
    cleanState.chat.metrics = cleanState.chat.metrics || {
      send_count: 0,
      ws_start_count: 0,
      last_ttfb_ms: 0,
      rest_fallback_count: 0,
      last_fallback_at: null
    };
    if (cleanState.chat.ragEnabled === undefined) cleanState.chat.ragEnabled = false;
    if (cleanState.chat.ragStatus === undefined) cleanState.chat.ragStatus = 'idle';
    if (cleanState.chat.memoryBannerAt === undefined) cleanState.chat.memoryBannerAt = null;
    if (cleanState.chat.memoryStats === undefined) {
      cleanState.chat.memoryStats = { has_stm: false, ltm_items: 0, injected: false };
    }

    return cleanState;
  }

  getInitialState() { return this.sanitize({}); }

  get(key) { return key.split('.').reduce((acc, part) => acc && acc[part], this.state); }

  set(key, value) {
    if (value === undefined) {
      console.warn(`[StateManager] Tentative de 'set' undefined pour '${key}' — ignoré.`);
      return;
    }
    const keys = key.split('.');
    const lastKey = keys.pop();
    let target = this.state;
    for (let part of keys) {
      if (!target[part] || typeof target[part] !== 'object') target[part] = {};
      target = target[part];
    }
    target[lastKey] = value;
    this.notify(key);
    this.persist();
  }

  subscribe(key, callback) {
    if (!this.subscribers.has(key)) this.subscribers.set(key, []);
    this.subscribers.get(key).push(callback);
    return () => {
      try {
        const arr = this.subscribers.get(key) || [];
        const i = arr.indexOf(callback);
        if (i >= 0) arr.splice(i, 1);
      } catch {}
    };
  }

  notify(changedKey) {
    this.subscribers.forEach((callbacks, key) => {
      if (changedKey.startsWith(key)) {
        const value = this.get(key);
        callbacks.forEach(cb => cb(value));
      }
    });
  }

  persist() {
    try { localStorage.setItem('emergenceState-V14', JSON.stringify(this.state)); }
    catch (error) { console.error('[StateManager] Persist error:', error); }
  }

  loadFromStorage() {
    try {
      const saved = localStorage.getItem('emergenceState-V14');
      return saved ? JSON.parse(saved) : {};
    } catch (error) {
      console.error('[StateManager] Load error — retour {}', error);
      return {};
    }
  }

  _deepMerge(target, source) {
    const output = { ...target };
    if (source && typeof source === 'object') {
      for (const key in source) {
        if (Object.prototype.hasOwnProperty.call(source, key)) {
          if (source[key] && typeof source[key] === 'object' && !Array.isArray(source[key])) {
            output[key] = this._deepMerge(target[key] || {}, source[key]);
          } else {
            output[key] = source[key];
          }
        }
      }
    }
    return output;
  }

  // Back-compat
  async ensureAuth() {
    try {
      const tok = getIdToken();
      if (tok) { this.set('auth.hasToken', true); return true; }
      const maybe = await ensureAuthCore({ interactive: false });
      const has = !!(maybe || getIdToken());
      this.set('auth.hasToken', has);
      return has;
    } catch {
      this.set('auth.hasToken', false);
      return false;
    }
  }
}
