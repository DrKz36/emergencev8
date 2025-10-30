// src/frontend/core/state-manager.js
/**
 * @module core/state-manager
 * @description Gestionnaire d'Ã©tat V15.4 "Threads Aware" + ensureAuth() + chat meta + metrics
 */
import { AGENTS } from '../shared/constants.js';
import { getIdToken } from './auth.js';


const HEX32_RE = /^[0-9a-f]{32}$/i;
const UUID36_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function sanitizeThreadId(value) {
  if (value === undefined || value === null) return null;
  const candidate = String(value).trim();
  if (!candidate) return null;
  if (HEX32_RE.test(candidate) || UUID36_RE.test(candidate)) return candidate;
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

    const sessionState = (cleanState.session && typeof cleanState.session === 'object') ? { ...cleanState.session } : {};
    const rawSessionId = typeof sessionState.id === 'string' ? sessionState.id.trim() : '';
    sessionState.id = rawSessionId || null;
    const rawStartedAt = Number(sessionState.startedAt);
    sessionState.startedAt = Number.isFinite(rawStartedAt) ? rawStartedAt : Date.now();
    cleanState.session = sessionState;

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
    cleanState.auth.isAuthenticated = cleanState.auth.isAuthenticated === true;
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

    const baseMemoryStats = {
      has_stm: false,
      ltm_items: 0,
      ltm_injected: 0,
      ltm_candidates: 0,
      injected: false,
      ltm_skipped: false
    };
    const rawMemoryStats = cleanState.chat.memoryStats;
    if (!rawMemoryStats || typeof rawMemoryStats !== 'object') {
      cleanState.chat.memoryStats = { ...baseMemoryStats };
    } else {
      cleanState.chat.memoryStats = { ...baseMemoryStats, ...rawMemoryStats };
      cleanState.chat.memoryStats.has_stm = !!cleanState.chat.memoryStats.has_stm;
      cleanState.chat.memoryStats.ltm_items = Number.isFinite(Number(cleanState.chat.memoryStats.ltm_items)) ? Number(cleanState.chat.memoryStats.ltm_items) : 0;
      cleanState.chat.memoryStats.ltm_injected = Number.isFinite(Number(cleanState.chat.memoryStats.ltm_injected)) ? Number(cleanState.chat.memoryStats.ltm_injected) : 0;
      cleanState.chat.memoryStats.ltm_candidates = Number.isFinite(Number(cleanState.chat.memoryStats.ltm_candidates)) ? Number(cleanState.chat.memoryStats.ltm_candidates) : cleanState.chat.memoryStats.ltm_items;
      cleanState.chat.memoryStats.injected = !!cleanState.chat.memoryStats.injected;
      cleanState.chat.memoryStats.ltm_skipped = !!cleanState.chat.memoryStats.ltm_skipped;
    }
    if (!Number.isFinite(cleanState.chat.memoryStats.ltm_candidates)) {
      cleanState.chat.memoryStats.ltm_candidates = cleanState.chat.memoryStats.ltm_items;
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

  getSessionId() {
    return this.state?.session?.id || null;
  }

  resetForSession(newSessionId, options = {}) {
    const {
      preserveAuth = {},
      preserveUser = true,
      userId: nextUserId = null,
      preserveThreads = false,
    } = options || {};

    const {
      role: keepRole = false,
      email: keepEmail = false,
      hasToken: keepHasToken = true,
    } = preserveAuth;

    const preservedAuth = { ...(this.state?.auth || {}) };
    if (!keepRole) delete preservedAuth.role;
    if (!keepEmail) delete preservedAuth.email;
    if (!keepHasToken) delete preservedAuth.hasToken;

    const rawCurrentUserId = this.state?.user?.id;
    const currentUserId = typeof rawCurrentUserId === 'string' ? rawCurrentUserId.trim() : (rawCurrentUserId == null ? null : String(rawCurrentUserId).trim());
    const normalizedNextUserId = nextUserId === null || nextUserId === undefined
      ? null
      : (() => { const text = String(nextUserId).trim(); return text ? text : null; })();
    const sameUser = Boolean(normalizedNextUserId && currentUserId && normalizedNextUserId === currentUserId);

    const preservedUser = this._buildPreservedUser({
      preserveUser,
      normalizedNextUserId,
      sameUser,
    });

    const baseState = {
      session: { id: newSessionId || null, startedAt: Date.now() },
      auth: preservedAuth,
      user: preservedUser,
    };

    let sanitizedState = this.sanitize(baseState);
    if (!sanitizedState.auth || typeof sanitizedState.auth !== 'object') {
      sanitizedState.auth = {};
    }
    if (!keepRole) sanitizedState.auth.role = 'member';
    if (!keepEmail) sanitizedState.auth.email = null;
    if (keepHasToken && Object.prototype.hasOwnProperty.call(preservedAuth, 'hasToken')) {
      sanitizedState.auth.hasToken = !!preservedAuth.hasToken;
    }

    if (!normalizedNextUserId && !sameUser) {
      if (sanitizedState.user && typeof sanitizedState.user === 'object') {
        delete sanitizedState.user.id;
        delete sanitizedState.user.email;
        delete sanitizedState.user.name;
      }
    } else if (normalizedNextUserId) {
      sanitizedState.user = { ...(sanitizedState.user || {}), id: normalizedNextUserId };
    }

    const shouldKeepThreads = (preserveThreads || sameUser) && this.state?.threads;
    if (shouldKeepThreads) {
      const preservedMap = sanitizeThreadsMap(this.state.threads.map);
      const preservedOrder = sanitizeThreadsOrder(this.state.threads.order, preservedMap);
      let nextCurrentId = sanitizeThreadId(this.state.threads.currentId);
      if (!nextCurrentId || !preservedMap[nextCurrentId]) {
        nextCurrentId = preservedOrder[0] || null;
      }
      sanitizedState.threads = {
        ...sanitizedState.threads,
        ...this.state.threads,
        map: preservedMap,
        order: preservedOrder,
        currentId: nextCurrentId,
        status: this.state.threads.status || 'idle',
        error: this.state.threads.error || null,
        lastFetchedAt: this.state.threads.lastFetchedAt || null,
      };

      if (this.state?.chat && typeof this.state.chat === 'object') {
        sanitizedState.chat = { ...sanitizedState.chat, ...this.state.chat };
        const preservedThreadId = sanitizeThreadId(sanitizedState.chat.threadId);
        if (!preservedThreadId || !preservedMap[preservedThreadId]) {
          sanitizedState.chat.threadId = nextCurrentId || null;
        }
      }
    }

    this.state = sanitizedState;
    if (this.state?.auth && typeof this.state.auth === 'object') {
      this.state.auth.isAuthenticated = false;
    }

    try { localStorage.removeItem('emergence.threadId'); } catch (_) {}
    try { localStorage.removeItem('emergence.documents.selection'); } catch (_) {}

    this.notify('session');
    this.notify('auth.role');
    this.notify('auth.email');
    this.notify('auth.isAuthenticated');
    this.notify('user');
    this.notify('user.id');
    this.notify('user.email');
    this.notify('threads');
    this.notify('chat.threadId');
    this.persist();
  }

  _buildPreservedUser({ preserveUser, normalizedNextUserId, sameUser }) {
    if (!preserveUser) {
      return normalizedNextUserId ? { id: normalizedNextUserId } : {};
    }

    const currentUser = this.state?.user && typeof this.state.user === 'object'
      ? { ...this.state.user }
      : {};

    if (normalizedNextUserId) {
      currentUser.id = normalizedNextUserId;
      return currentUser;
    }

    if (!sameUser) {
      delete currentUser.id;
      delete currentUser.email;
      delete currentUser.name;
    }

    return currentUser;
  }

  getInitialState() {
    return this.sanitize({ session: { id: null, startedAt: null } });
  }
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
    if (key === 'websocket.sessionId' && this.state?.session) {
      this.state.session.id = typeof value === 'string' && value.trim() ? value.trim() : null;
      this.state.session.startedAt = Date.now();
    }
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

  reset() {
    this.state = this.getInitialState();
    this.persist();
    this.subscribers.forEach((callbacks, key) => {
      try {
        const value = this.get(key);
        callbacks.forEach(cb => cb(value));
      } catch (error) {
        console.warn('[StateManager] Error notifying subscriber during reset:', error);
      }
    });
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
      const tok = getIdToken();
      const hasToken = !!(tok && String(tok).trim());
      this.set('auth.hasToken', hasToken);
      return hasToken;
    } catch (_) {
      this.set('auth.hasToken', false);
      return false;
    }
  }






}
