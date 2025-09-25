// src/frontend/core/state-manager.js
/**
 * @module core/state-manager
 * @description Gestionnaire d'Ã©tat V15.4 "Threads Aware" + ensureAuth() + chat meta + metrics
 */
import { AGENTS } from '../shared/constants.js';


const HEX32_RE = /^[0-9a-f]{32}$/i;
const UUID36_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function sanitizeThreadId(value) {
  if (value === undefined || value === null) return null;
  const candidate = String(value).trim();
  if (!candidate) return null;
  if (HEX32_RE.test(candidate) || UUID36_RE.test(candidate)) return candidate;
  if (/^[0-9a-z-]{8,}$/i.test(candidate)) return candidate;
  return null;
}

function sanitizeThreadsMap(rawMap) {
  const safeMap = {};
  if (!rawMap || typeof rawMap !== 'object') return safeMap;
  for (const [rawKey, rawValue] of Object.entries(rawMap)) {
    const source = rawValue && typeof rawValue === 'object' ? { ...rawValue } : {};
    const safeId = sanitizeThreadId(source.id ?? rawKey);
    if (!safeId) continue;
    const entry = { ...source, id: safeId };
    if (!Array.isArray(entry.messages)) entry.messages = [];
    if (!Array.isArray(entry.docs)) entry.docs = [];
    if (entry.thread && typeof entry.thread === 'object') {
      entry.thread = { ...entry.thread };
      const threadId = sanitizeThreadId(entry.thread.id ?? safeId);
      if (threadId) entry.thread.id = threadId;
      else entry.thread.id = safeId;
      if (entry.thread.archived === 1) entry.thread.archived = true;
      if (entry.thread.archived === 0) entry.thread.archived = false;
      if (typeof entry.thread.archived !== 'boolean') {
        entry.thread.archived = entry.thread.archived === true;
      }
    }
    safeMap[safeId] = entry;
  }
  return safeMap;
}

function sanitizeThreadsOrder(rawOrder, map) {
  const result = [];
  const seen = new Set();
  if (Array.isArray(rawOrder)) {
    for (const value of rawOrder) {
      const id = sanitizeThreadId(value);
      if (!id) continue;
      if (!map[id]) continue;
      if (seen.has(id)) continue;
      seen.add(id);
      result.push(id);
    }
  }
  if (!result.length) {
    for (const id of Object.keys(map)) {
      if (seen.has(id)) continue;
      seen.add(id);
      result.push(id);
    }
  }
  return result;
}

export class StateManager {
  constructor() {
    this.DEFAULT_STATE = this.getInitialState();
    this.state = this.DEFAULT_STATE;

    this.subscribers = new Map();
    console.log("âœ… StateManager V15.4 (Threads Aware + metrics) Constructor: Default state is set.");
  }

  async init() {
    const savedState = this.loadFromStorage();
    let mergedState = this._deepMerge(this.DEFAULT_STATE, savedState);
    this.state = this.sanitize(mergedState);
    console.log("[StateManager] V15.4 Initialized: State loaded from localStorage and sanitized.");
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

    // Threads
    const threadsState = (cleanState.threads && typeof cleanState.threads === 'object') ? { ...cleanState.threads } : {};
    threadsState.map = sanitizeThreadsMap(threadsState.map);
    threadsState.order = sanitizeThreadsOrder(threadsState.order, threadsState.map);
    const resolvedCurrentId = sanitizeThreadId(threadsState.currentId);
    threadsState.currentId = resolvedCurrentId && threadsState.map[resolvedCurrentId] ? resolvedCurrentId : null;
    threadsState.status = typeof threadsState.status === 'string' ? threadsState.status : 'idle';
    const errorText = typeof threadsState.error === 'string' ? threadsState.error.trim() : '';
    threadsState.error = errorText ? errorText : null;
    const lastFetched = Number(threadsState.lastFetchedAt);
    threadsState.lastFetchedAt = Number.isFinite(lastFetched) && lastFetched > 0 ? lastFetched : null;
    cleanState.threads = threadsState;

    // Auth
    cleanState.auth = cleanState.auth || { hasToken: false };
    if (typeof cleanState.auth.hasToken !== 'boolean') {
      cleanState.auth.hasToken = !!cleanState.auth.hasToken;
    }
    const authRole = cleanState.auth.role;
    if (typeof authRole === 'string' && authRole.trim()) {
      cleanState.auth.role = authRole.trim().toLowerCase();
    } else {
      cleanState.auth.role = 'member';
    }
    if (cleanState.auth.email === undefined) cleanState.auth.email = null;

    // Chat meta
    cleanState.chat = cleanState.chat || {};
    const safeChatThreadId = sanitizeThreadId(cleanState.chat.threadId);
    if (safeChatThreadId && threadsState.map[safeChatThreadId]) {
      cleanState.chat.threadId = safeChatThreadId;
    } else {
      cleanState.chat.threadId = threadsState.currentId || null;
    }
    const normalizeAgentId = (value) => {
      if (typeof value !== 'string') return '';
      let candidate = value.trim().toLowerCase();
      if (!candidate) return '';
      if (!AGENTS[candidate] && candidate.endsWith('_lite')) {
        const base = candidate.slice(0, -5);
        if (AGENTS[base]) candidate = base;
      }
      return candidate;
    };

    let activeAgent = normalizeAgentId(cleanState.chat.activeAgent);
    if (!activeAgent) activeAgent = 'anima';
    cleanState.chat.activeAgent = activeAgent;
    cleanState.agents[activeAgent] = cleanState.agents[activeAgent] || { status: 'disconnected', history: [] };

    let currentAgent = normalizeAgentId(cleanState.chat.currentAgentId);
    if (!currentAgent) currentAgent = activeAgent;
    cleanState.chat.currentAgentId = currentAgent;
    cleanState.agents[currentAgent] = cleanState.agents[currentAgent] || { status: 'disconnected', history: [] };

    const messageBuckets = (cleanState.chat.messages && typeof cleanState.chat.messages === 'object') ? { ...cleanState.chat.messages } : {};
    if (!Array.isArray(messageBuckets[activeAgent])) {
      messageBuckets[activeAgent] = [];
    }
    if (!Array.isArray(messageBuckets[currentAgent])) {
      messageBuckets[currentAgent] = [];
    }
    Object.keys(AGENTS).forEach((agentId) => {
      if (!Array.isArray(messageBuckets[agentId])) {
        messageBuckets[agentId] = [];
      }
    });
    cleanState.chat.messages = messageBuckets;
    cleanState.chat.lastMessageMeta = cleanState.chat.lastMessageMeta || null;
    cleanState.chat.modelInfo = cleanState.chat.modelInfo || null;
    if (cleanState.chat.lastAnalysis === undefined) cleanState.chat.lastAnalysis = null;

    // Chat metrics
    cleanState.chat.metrics = cleanState.chat.metrics || {
      send_count: 0,
      ws_start_count: 0,
      last_ttfb_ms: 0,
      rest_fallback_count: 0,
      last_fallback_at: null
    };

    // Flags
    if (cleanState.chat.ragEnabled === undefined) cleanState.chat.ragEnabled = false;
    if (cleanState.chat.ragStatus === undefined) cleanState.chat.ragStatus = 'idle';
    if (cleanState.chat.memoryBannerAt === undefined) cleanState.chat.memoryBannerAt = null;

    if (cleanState.chat.memoryStats === undefined) {
      cleanState.chat.memoryStats = { has_stm: false, ltm_items: 0, injected: false };
    }
    if (cleanState.chat.authRequired === undefined) cleanState.chat.authRequired = false;
    else cleanState.chat.authRequired = !!cleanState.chat.authRequired;
    cleanState.chat.selectedDocIds = Array.isArray(cleanState.chat.selectedDocIds) ? cleanState.chat.selectedDocIds : [];
    cleanState.chat.selectedDocs = Array.isArray(cleanState.chat.selectedDocs) ? cleanState.chat.selectedDocs : [];

    cleanState.documents = cleanState.documents || {};
    cleanState.documents.selectedIds = Array.isArray(cleanState.documents.selectedIds) ? cleanState.documents.selectedIds : [];
    cleanState.documents.selectionMeta = Array.isArray(cleanState.documents.selectionMeta) ? cleanState.documents.selectionMeta : [];

    // âœ… NEW: agent actif par dÃ©faut
    return cleanState;
  }

  getInitialState() { return this.sanitize({}); }
  get(key) { return key.split('.').reduce((acc, part) => acc && acc[part], this.state); }

  set(key, value) {
    if (value === undefined) {
      console.warn(`[StateManager] Tentative de 'set' avec une valeur 'undefined' pour la clÃ© '${key}'. OpÃ©ration bloquÃ©e.`);
      return;
    }
    const keys = key.split('.');
    const lastKey = keys.pop();
    let target = this.state;

    for (let part of keys) {
      if (!target[part] || typeof target[part] !== 'object') {
        target[part] = {};
      }
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
    try { localStorage.setItem('emergenceState-V14', JSON.stringify(this.state)); } catch (error) {
      console.error('[StateManager] Error persisting state:', error);
    }
  }

  loadFromStorage() {
    try {
      const savedState = localStorage.getItem('emergenceState-V14');
      return savedState ? JSON.parse(savedState) : {};
    } catch (error) {
      console.error('[StateManager] Error loading state, returning empty object.', error);
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

  async ensureAuth() {
    try {
      if (window.gis?.getIdToken) {
        const tok = await window.gis.getIdToken()
        if (tok) {
          try { sessionStorage.setItem('emergence.id_token', tok); } catch (_) {}
          try { localStorage.setItem('emergence.id_token', tok); } catch (_) {}
          this.set('auth.hasToken', true);
          return true;
        }
      }
    } catch (_) {}
    this.set('auth.hasToken', false);
    return false;
  }
}






