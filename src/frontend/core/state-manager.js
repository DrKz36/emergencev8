/**
 * @module core/state-manager
 * @description Gestionnaire d'état V14.1 — unsubscribe effectif + garde undefined
 */
import { AGENTS } from '../shared/constants.js';

export class StateManager {
  constructor() {
    this.DEFAULT_STATE = this.getInitialState();
    this.state = this.DEFAULT_STATE;
    this.subscribers = new Map();
    console.log("✅ StateManager V14 (Input Validation) Constructor: Default state is set.");
  }

  async init() {
    const savedState = this.loadFromStorage();
    const merged = this._deepMerge(this.DEFAULT_STATE, savedState);
    this.state = this.sanitize(merged);
    console.log("[StateManager] V14 Initialized: State loaded from localStorage and sanitized.");
    this.persist();
  }

  sanitize(stateToClean) {
    let clean = { ...stateToClean };
    clean.agents = clean.agents || {};
    for (const agentId of Object.keys(AGENTS || {})) {
      clean.agents[agentId] = clean.agents[agentId] || { status: 'disconnected', history: [] };
    }
    clean.connection = clean.connection || { status: 'disconnected', attempt: 0 };
    clean.costs = clean.costs || { total: 0, last_session: 0 };
    clean.debate = clean.debate || { status: 'idle', topic: null, history: [], config: {} };
    clean.chat = clean.chat || { currentAgentId: 'anima', ragEnabled: false, isLoading: false, messages:{}, ragStatus:{}, ragSources:{}, memoryStatus:{}, memorySources:{} };
    return clean;
  }

  getInitialState() { return this.sanitize({}); }

  get(key) { return key.split('.').reduce((acc, part) => acc && acc[part], this.state); }

  set(key, value) {
    if (value === undefined) {
      console.warn(`[StateManager] Tentative de 'set' avec undefined pour '${key}'. Ignoré.`);
      return;
    }
    const keys = key.split('.'); const last = keys.pop(); let target = this.state;
    for (const k of keys) { if (!target[k] || typeof target[k] !== 'object') target[k] = {}; target = target[k]; }
    target[last] = value;
    this.notify(key); this.persist();
  }

  subscribe(key, callback) {
    if (!this.subscribers.has(key)) this.subscribers.set(key, []);
    const arr = this.subscribers.get(key); arr.push(callback);
    return () => {
      const list = this.subscribers.get(key); if (!list) return;
      const idx = list.indexOf(callback); if (idx !== -1) list.splice(idx, 1);
      if (list.length === 0) this.subscribers.delete(key);
    };
  }

  notify(changedKey) {
    this.subscribers.forEach((callbacks, key) => {
      if (changedKey.startsWith(key)) {
        const value = this.get(key);
        callbacks.forEach(cb => { try { cb(value); } catch(e){ console.error('[StateManager] subscriber error:', e); } });
      }
    });
  }

  persist() {
    try { localStorage.setItem('emergenceState-V14', JSON.stringify(this.state)); }
    catch (e) { console.error('[StateManager] persist error:', e); }
  }

  loadFromStorage() {
    try { const raw = localStorage.getItem('emergenceState-V14'); return raw ? JSON.parse(raw) : {}; }
    catch (e) { console.error('[StateManager] load error:', e); return {}; }
  }

  _deepMerge(target, source) {
    const output = { ...target };
    if (source && typeof source === 'object') {
      for (const key in source) if (Object.prototype.hasOwnProperty.call(source, key)) {
        if (source[key] && typeof source[key] === 'object' && !Array.isArray(source[key])) {
          output[key] = this._deepMerge(target[key] || {}, source[key]);
        } else {
          output[key] = source[key];
        }
      }
    }
    return output;
  }
}
