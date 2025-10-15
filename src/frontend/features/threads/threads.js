/**
 * @module features/threads/threads
 * Threads management panel (list, create, select, archive) with EventBus synchronization.
 */

import {
  fetchThreads,
  fetchThreadDetail,
  createThread as apiCreateThread,
  archiveThread as apiArchiveThread,
  deleteThread as apiDeleteThread,
  updateThread as apiUpdateThread,
} from './threads-service.js';
import { EVENTS, AGENTS } from '../../shared/constants.js';

const THREAD_STORAGE_KEY = 'emergence.threadId';
const STATUS_LABELS = Object.freeze({ active: 'Actif', archived: 'Archive' });
const MAX_FETCH_LIMIT = 50;

function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function formatDateTime(value) {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  const pad = (n) => String(n).padStart(2, '0');
  const day = pad(date.getDate());
  const month = pad(date.getMonth() + 1);
  const year = date.getFullYear();
  const hours = pad(date.getHours());
  const minutes = pad(date.getMinutes());
  return `${day}.${month}.${year} ${hours}:${minutes}`;
}

function agentLabel(agentId) {
  if (!agentId) return '--';
  const normalized = typeof agentId === 'string' ? agentId.trim().toLowerCase() : '';
  if (!normalized) return agentId;
  return (AGENTS[normalized] && AGENTS[normalized].label) || agentId;
}

function cloneThreadsState(state) {
  const map = state?.map && typeof state.map === 'object' ? { ...state.map } : {};
  const order = Array.isArray(state?.order) ? [...state.order] : [];
  return { map, order };
}

function ensureArray(value) {
  return Array.isArray(value) ? [...value] : [];
}

function normalizeId(value) {
  if (value === undefined || value === null) return null;
  const candidate = String(value).trim();
  return candidate ? candidate : null;
}

function coerceTimestamp(value) {
  if (!value) return null;
  if (value instanceof Date) {
    const time = value.getTime();
    return Number.isNaN(time) ? null : time;
  }
  if (typeof value === 'number') {
    if (!Number.isFinite(value) || value <= 0) return null;
    if (value > 1e12) return Math.trunc(value);
    if (value > 1e9) return Math.trunc(value * 1000);
    return Math.trunc(value);
  }
  if (typeof value === 'string') {
    const trimmed = value.trim();
    if (!trimmed) return null;
    const numeric = Number(trimmed);
    if (Number.isFinite(numeric)) return coerceTimestamp(numeric);
    const parsed = Date.parse(trimmed);
    if (!Number.isNaN(parsed)) return parsed;
  }
  return null;
}

function extractMessageTimestamp(message) {
  if (!message || typeof message !== 'object') return null;
  return coerceTimestamp(
    message.created_at ??
    message.createdAt ??
    message.updated_at ??
    message.updatedAt ??
    message.timestamp ??
    message.time ??
    message.datetime ??
    message.date ??
    (message.meta && (message.meta.timestamp ?? message.meta.created_at ?? message.meta.updated_at))
  );
}

function resolveThreadRecord(entry, record) {
  if (record && typeof record === 'object') return record;
  if (entry && typeof entry === 'object') {
    if (entry.thread && typeof entry.thread === 'object') return entry.thread;
    return entry;
  }
  return null;
}

export function getInteractionCount(entry, record) {
  const messages = Array.isArray(entry?.messages) ? entry.messages.filter(Boolean) : [];
  if (messages.length) return messages.length;
  const target = resolveThreadRecord(entry, record);
  if (Array.isArray(target?.messages) && target.messages.length) {
    return target.messages.filter(Boolean).length;
  }
  const targetStats = target?.stats || {};
  const entryStats = entry?.stats || {};
  const targetMeta = target?.meta || target?.metadata || {};
  const entryMeta = entry?.meta || entry?.metadata || {};
  const candidates = [
    targetStats.interactions,
    targetStats.messages,
    targetStats.total,
    targetStats.count,
    entryStats.interactions,
    entryStats.messages,
    entryStats.total,
    entryStats.count,
    target?.message_count,
    target?.messages_count,
    target?.messages_total,
    target?.total_messages,
    entry?.message_count,
    entry?.messages_count,
    entry?.messages_total,
    entry?.total_messages,
    targetMeta.interaction_count,
    targetMeta.interactions,
    targetMeta.messages_count,
    entryMeta.interaction_count,
    entryMeta.interactions,
    entryMeta.messages_count
  ];
  for (const candidate of candidates) {
    const num = Number(candidate);
    if (Number.isFinite(num) && num >= 0) {
      return Math.max(0, Math.floor(num));
    }
  }
  return 0;
}

export function formatInteractionCount(count) {
  const safe = Number.isFinite(count) ? Math.max(0, Math.floor(count)) : 0;
  if (safe === 0) return 'Aucune interaction';
  if (safe === 1) return '1 interaction';
  return `${safe} interactions`;
}

export function getLastInteractionTimestamp(entry, record) {
  const timestamps = [];
  const addTimestamp = (value) => {
    const epoch = coerceTimestamp(value);
    if (epoch) timestamps.push(epoch);
  };
  const messages = Array.isArray(entry?.messages) ? entry.messages : [];
  for (const message of messages) {
    const ts = extractMessageTimestamp(message);
    if (ts) timestamps.push(ts);
  }
  const target = resolveThreadRecord(entry, record);
  const candidateValues = [
    entry?.lastInteractionAt,
    entry?.last_interaction_at,
    entry?.lastMessageAt,
    entry?.last_message_at,
    target?.lastInteractionAt,
    target?.last_interaction_at,
    target?.lastMessageAt,
    target?.last_message_at,
    target?.latestMessageAt,
    target?.latest_message_at,
    target?.updatedAt,
    target?.updated_at,
    target?.createdAt,
    target?.created_at,
    entry?.updatedAt,
    entry?.updated_at
  ];
  const targetMeta = target?.meta || target?.metadata || {};
  const entryMeta = entry?.meta || entry?.metadata || {};
  candidateValues.push(
    targetMeta.lastInteractionAt,
    targetMeta.last_interaction_at,
    targetMeta.lastMessageAt,
    targetMeta.last_message_at,
    entryMeta.lastInteractionAt,
    entryMeta.last_interaction_at,
    entryMeta.lastMessageAt,
    entryMeta.last_message_at
  );
  if (!timestamps.length && Array.isArray(target?.messages) && target.messages.length) {
    for (const message of target.messages) {
      const ts = extractMessageTimestamp(message);
      if (ts) timestamps.push(ts);
    }
  }
  if (!timestamps.length) return null;
  const latest = Math.max(...timestamps);
  return new Date(latest).toISOString();
}

export class ThreadsPanel {
  constructor(eventBus, stateManager, options = {}) {
    this.eventBus = eventBus;
    this.state = stateManager;
    const opts = options || {};
    this.options = {
      keepMarkup: !!opts.keepMarkup,
      hostId: typeof opts.hostId === 'string' ? opts.hostId : null,
    };
    this.hostElement = opts.hostElement || null;
    this.deleteThreadFn = typeof opts.deleteThread === 'function' ? opts.deleteThread : apiDeleteThread;

    this.container = null;
    this.listEl = null;
    this.errorEl = null;
    this.newButton = null;
    this.searchInput = null;
    this.sortSelect = null;
    this.viewToggle = null;

    this.unsubscribeState = null;
    this.unsubscribeRefresh = null;

    this.selectionLoadingId = null;
    this.archivingId = null;
    this.unarchivingId = null;
    this.pendingCreate = false;
    this.pendingDeleteId = null;
    this.deletingId = null;
    this.searchQuery = '';
    this.editingId = null;
    this.editingValue = '';
    this.sortBy = 'modified'; // 'modified', 'created', 'alphabetical'
    this.viewMode = 'active'; // 'active', 'archived'
    this.contextMenuId = null;
    this.contextMenuX = 0;
    this.contextMenuY = 0;

    this._hasInitialRender = false;
    this._domBound = false;
    this._initialized = false;
    this._onContainerClick = this.handleContainerClick.bind(this);
    this._onRefreshRequested = this.reload.bind(this);
    this._onSearchInput = this.handleSearchInput.bind(this);
    this._onKeyDown = this.handleKeyDown.bind(this);
  }

  setHostElement(element) {
    if (this.container && this._domBound) {
      this.container.removeEventListener('click', this._onContainerClick);
    }
    if (this.searchInput) {
      this.searchInput.removeEventListener('input', this._onSearchInput);
    }
    this.hostElement = element || null;
    this.container = null;
    this.listEl = null;
    this.errorEl = null;
    this.newButton = null;
    this.searchInput = null;
    this.pendingDeleteId = null;
    this.deletingId = null;
    this.searchQuery = '';
    this._domBound = false;
    this._hasInitialRender = false;
  }

  template() {
    return `
      <div class="threads-panel__inner">
        <header class="threads-panel__header">
          <div class="threads-panel__titles">
            <h2 class="threads-panel__title">Conversations</h2>
            <p class="threads-panel__subtitle">Gerer vos discussions actives et archivees.</p>
          </div>
          <button type="button" class="threads-panel__new" data-action="new" aria-label="Lancer une nouvelle conversation">
            Nouvelle conversation
          </button>
        </header>
        <div class="threads-panel__view-toggle" data-role="thread-view-toggle">
          <button type="button" class="threads-panel__view-btn" data-view="active" data-role="toggle-active">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="10"></circle>
            </svg>
            Actifs
            <span class="threads-panel__view-count" data-role="active-count">0</span>
          </button>
          <button type="button" class="threads-panel__view-btn" data-view="archived" data-role="toggle-archived">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="21 8 21 21 3 21 3 8"></polyline>
              <rect x="1" y="3" width="22" height="5"></rect>
              <line x1="10" y1="12" x2="14" y2="12"></line>
            </svg>
            Archivés
            <span class="threads-panel__view-count" data-role="archived-count">0</span>
          </button>
        </div>
        <div class="threads-panel__controls">
          <div class="threads-panel__search">
            <input
              type="search"
              class="threads-panel__search-input"
              data-role="thread-search"
              placeholder="Rechercher une conversation..."
              aria-label="Rechercher dans les conversations"
            />
          </div>
          <div class="threads-panel__sort">
            <label for="thread-sort" class="threads-panel__sort-label">Trier par :</label>
            <select id="thread-sort" class="threads-panel__sort-select" data-role="thread-sort">
              <option value="modified">Date de modification</option>
              <option value="created">Date de création</option>
              <option value="alphabetical">Alphabétique</option>
            </select>
          </div>
        </div>
        <div class="threads-panel__body">
          <p class="threads-panel__error" data-role="thread-error" hidden></p>
          <ul class="threads-panel__list" data-role="thread-list" role="list"></ul>
        </div>
      </div>
    `;
  }

  init() {
    this.ensureContainer();
    if (!this.container) return;

    if (!this._domBound) {
      this.container.addEventListener('click', this._onContainerClick);
      this.container.addEventListener('keydown', this._onKeyDown);
      this.container.addEventListener('contextmenu', (e) => this.handleContextMenu(e));
      // Close context menu when clicking elsewhere
      document.addEventListener('click', () => this.closeContextMenu());
      this._domBound = true;
    }

    if (this.searchInput && !this.searchInput.hasAttribute('data-listener-attached')) {
      this.searchInput.addEventListener('input', this._onSearchInput);
      this.searchInput.setAttribute('data-listener-attached', 'true');
    }

    if (this.sortSelect && !this.sortSelect.hasAttribute('data-listener-attached')) {
      this.sortSelect.addEventListener('change', (e) => {
        this.sortBy = e.target.value;
        this.render(this.state.get('threads'));
      });
      this.sortSelect.setAttribute('data-listener-attached', 'true');
      this.sortSelect.value = this.sortBy;
    }

    if (!this.unsubscribeRefresh && this.eventBus?.on) {
      this.unsubscribeRefresh = this.eventBus.on(EVENTS.THREADS_REFRESH_REQUEST, this._onRefreshRequested);
    }

    if (!this.unsubscribeState) {
      this.unsubscribeState = this.state.subscribe('threads', (threads) => {
        this.render(threads);
      });
    }

    const currentThreadsState = this.state.get('threads');
    this.render(currentThreadsState);

    if (!this._initialized && (!currentThreadsState || currentThreadsState.status === 'idle')) {
      this.reload();
    }

    this._initialized = true;
  }

  destroy() {
    if (this.container && this._domBound) {
      this.container.removeEventListener('click', this._onContainerClick);
      this.container.removeEventListener('keydown', this._onKeyDown);
      this._domBound = false;
    }
    if (this.searchInput) {
      this.searchInput.removeEventListener('input', this._onSearchInput);
    }
    if (typeof this.unsubscribeState === 'function') {
      this.unsubscribeState();
      this.unsubscribeState = null;
    }
    if (typeof this.unsubscribeRefresh === 'function') {
      this.unsubscribeRefresh();
      this.unsubscribeRefresh = null;
    }
    this._initialized = false;
    this.pendingDeleteId = null;
    this.deletingId = null;
    this.searchQuery = '';
    if (!this.options.keepMarkup && this.container) {
      this.container.innerHTML = '';
      this.container = null;
      this.listEl = null;
      this.errorEl = null;
      this.newButton = null;
      this.searchInput = null;
    }
  }

  ensureContainer() {
    if (this.container) return;

    let host = this.hostElement;
    if (!host && this.options.hostId) {
      host = document.getElementById(this.options.hostId);
    }
    if (!host) return;

    if (!host.querySelector('[data-role="thread-list"]')) {
      host.classList.add('threads-panel');
      host.setAttribute('data-threads-panel', 'module');
      host.innerHTML = this.template();
    } else {
      host.classList.add('threads-panel');
      host.setAttribute('data-threads-panel', 'module');
    }

    this.container = host;
    this.listEl = host.querySelector('[data-role="thread-list"]');
    this.errorEl = host.querySelector('[data-role="thread-error"]');
    this.newButton = host.querySelector('[data-action="new"]');
    this.searchInput = host.querySelector('[data-role="thread-search"]');
    this.sortSelect = host.querySelector('[data-role="thread-sort"]');
    this.viewToggle = host.querySelector('[data-role="thread-view-toggle"]');
  }

  async reload() {
    this.setStatus('loading');
    try {
      const items = await fetchThreads({ type: 'chat', limit: MAX_FETCH_LIMIT });
      const meta = this.hydrateStateFromList(items);
      this.setStatus('ready');
      const payload = { items, fetchedAt: meta?.fetchedAt };
      this.eventBus.emit?.(EVENTS.THREADS_LIST_UPDATED, payload);
      this.eventBus.emit?.(EVENTS.THREADS_READY, payload);
    } catch (error) {
      const message = error?.message || 'Chargement impossible.';
      this.setStatus('error', message);
      this.eventBus.emit?.(EVENTS.THREADS_ERROR, { action: 'list', error });
      if (error?.status === 401) {
        this.eventBus.emit?.('auth:missing', { reason: 401 });
      }
    }
  }

  hydrateStateFromList(items) {
    const threadsState = this.state.get('threads') || {};
    const { map, order } = cloneThreadsState(threadsState);
    const nextOrder = [];

    for (const item of Array.isArray(items) ? items : []) {
      const id = normalizeId(item?.id);
      if (!id) continue;
      const threadRecord = { ...(item || {}), id };
      const existing = map[id] || { id, messages: [], docs: [] };
      map[id] = { ...existing, id, thread: threadRecord };
      nextOrder.push(id);
    }

    const mergedOrder = [...new Set([...nextOrder, ...order])];
    const fetchedAt = Date.now();
    this.state.set('threads.map', map);
    this.state.set('threads.order', mergedOrder);
    this.state.set('threads.lastFetchedAt', fetchedAt);
    this.state.set('threads.error', null);

    let currentId = normalizeId(this.state.get('threads.currentId'));
    if (currentId && !map[currentId]) currentId = null;
    if (!currentId) {
      const stored = this.readStoredThreadId();
      if (stored && map[stored]) currentId = stored;
    }
    if (!currentId && mergedOrder.length) {
      currentId = mergedOrder[0];
    }
    if (currentId) {
      this.state.set('threads.currentId', currentId);
    }

    return { map, order: mergedOrder, fetchedAt };
  }

  readStoredThreadId() {
    try {
      const stored = localStorage.getItem(THREAD_STORAGE_KEY);
      return stored && stored.trim() ? stored.trim() : null;
    } catch {
      return null;
    }
  }

  handleSearchInput(event) {
    this.searchQuery = event.target.value.toLowerCase().trim();
    this.render(this.state.get('threads'));
  }

  filterThreadsBySearch(order, map) {
    if (!this.searchQuery) return order;

    return order.filter((id) => {
      const entry = map[id] || { id };
      const record = entry.thread || entry;
      const title = (record?.title || '').toLowerCase();
      const agentId = (record?.agent_id || record?.agentId || '').toLowerCase();

      // Search in title
      if (title.includes(this.searchQuery)) return true;

      // Search in agent name
      if (agentId.includes(this.searchQuery)) return true;

      // Search in messages content
      const messages = Array.isArray(entry.messages) ? entry.messages : [];
      for (const message of messages) {
        const content = (message?.content || message?.text || '').toLowerCase();
        if (content.includes(this.searchQuery)) return true;
      }

      return false;
    });
  }

  sortThreads(order, map) {
    const orderCopy = [...order];

    if (this.sortBy === 'alphabetical') {
      orderCopy.sort((idA, idB) => {
        const entryA = map[idA] || { id: idA };
        const entryB = map[idB] || { id: idB };
        const recordA = entryA.thread || entryA;
        const recordB = entryB.thread || entryB;
        const titleA = (recordA?.title || 'Conversation').toLowerCase();
        const titleB = (recordB?.title || 'Conversation').toLowerCase();
        return titleA.localeCompare(titleB);
      });
    } else if (this.sortBy === 'created') {
      orderCopy.sort((idA, idB) => {
        const entryA = map[idA] || { id: idA };
        const entryB = map[idB] || { id: idB };
        const recordA = entryA.thread || entryA;
        const recordB = entryB.thread || entryB;
        const createdA = coerceTimestamp(recordA?.created_at || recordA?.createdAt) || 0;
        const createdB = coerceTimestamp(recordB?.created_at || recordB?.createdAt) || 0;
        return createdB - createdA; // Newest first
      });
    } else {
      // Default: 'modified' - sort by last interaction or update time
      orderCopy.sort((idA, idB) => {
        const entryA = map[idA] || { id: idA };
        const entryB = map[idB] || { id: idB };
        const lastA = getLastInteractionTimestamp(entryA, entryA.thread);
        const lastB = getLastInteractionTimestamp(entryB, entryB.thread);
        const tsA = coerceTimestamp(lastA) || 0;
        const tsB = coerceTimestamp(lastB) || 0;
        return tsB - tsA; // Most recent first
      });
    }

    return orderCopy;
  }

  async handleContainerClick(event) {
    const target = event.target instanceof Element ? event.target.closest('[data-action]') : null;
    if (!target) return;

    const action = target.getAttribute('data-action');
    if (action === 'new') {
      event.preventDefault();
      await this.handleCreate();
      return;
    }

    const threadId = target.getAttribute('data-thread-id');
    if (!threadId) return;

    if (action === 'select') {
      event.preventDefault();
      await this.handleSelect(threadId);
    } else if (action === 'archive') {
      event.preventDefault();
      await this.handleArchive(threadId);
    } else if (action === 'delete') {
      event.preventDefault();
      this.pendingDeleteId = threadId;
      this.render(this.state.get('threads'));
    } else if (action === 'delete-cancel') {
      event.preventDefault();
      if (this.pendingDeleteId === threadId) {
        this.pendingDeleteId = null;
        this.render(this.state.get('threads'));
      }
    } else if (action === 'delete-confirm') {
      event.preventDefault();
      await this.handleDelete(threadId);
    } else if (action === 'rename') {
      event.preventDefault();
      this.startRename(threadId);
    } else if (action === 'rename-cancel') {
      event.preventDefault();
      this.cancelRename();
    } else if (action === 'rename-save') {
      event.preventDefault();
      await this.saveRename(threadId);
    } else if (action === 'context-rename') {
      event.preventDefault();
      this.closeContextMenu();
      this.startRename(threadId);
    } else if (action === 'context-export') {
      event.preventDefault();
      this.closeContextMenu();
      await this.exportThread(threadId);
    } else if (action === 'context-archive') {
      event.preventDefault();
      this.closeContextMenu();
      await this.handleArchive(threadId);
    } else if (action === 'context-delete') {
      event.preventDefault();
      this.closeContextMenu();
      this.pendingDeleteId = threadId;
      this.render(this.state.get('threads'));
    }
  }

  handleKeyDown(event) {
    // Handle rename input Enter/Escape
    if (this.editingId && event.target.classList?.contains('threads-panel__rename-input')) {
      if (event.key === 'Enter') {
        event.preventDefault();
        this.saveRename(this.editingId);
      } else if (event.key === 'Escape') {
        event.preventDefault();
        this.cancelRename();
      }
      return;
    }

    // Don't interfere with input fields
    if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') {
      return;
    }

    // Global keyboard shortcuts
    if (event.ctrlKey || event.metaKey) {
      if (event.key === 'n' || event.key === 'N') {
        event.preventDefault();
        this.handleCreate();
      }
    }

    // Arrow navigation
    if (event.key === 'ArrowUp' || event.key === 'ArrowDown') {
      event.preventDefault();
      this.navigateThreads(event.key === 'ArrowUp' ? -1 : 1);
    }
  }

  navigateThreads(direction) {
    const threadsState = this.state.get('threads');
    const order = Array.isArray(threadsState?.order) ? threadsState.order : [];
    const map = threadsState?.map || {};

    if (!order.length) return;

    // Apply filters and sorting to get the visible order
    let visibleOrder = this.filterThreadsBySearch(order, map);
    visibleOrder = this.sortThreads(visibleOrder, map);

    if (!visibleOrder.length) return;

    const currentId = threadsState?.currentId;
    const currentIndex = currentId ? visibleOrder.indexOf(currentId) : -1;

    let nextIndex;
    if (currentIndex === -1) {
      // No selection, select first
      nextIndex = 0;
    } else {
      nextIndex = currentIndex + direction;
      // Wrap around
      if (nextIndex < 0) nextIndex = visibleOrder.length - 1;
      if (nextIndex >= visibleOrder.length) nextIndex = 0;
    }

    const nextId = visibleOrder[nextIndex];
    if (nextId) {
      this.handleSelect(nextId);
    }
  }

  handleContextMenu(event) {
    const item = event.target.closest('.threads-panel__item');
    if (!item) return;

    event.preventDefault();
    const threadId = item.getAttribute('data-thread-id');
    if (!threadId) return;

    this.contextMenuId = threadId;
    this.contextMenuX = event.clientX;
    this.contextMenuY = event.clientY;
    this.render(this.state.get('threads'));
  }

  closeContextMenu() {
    if (this.contextMenuId) {
      this.contextMenuId = null;
      this.render(this.state.get('threads'));
    }
  }

  async exportThread(threadId) {
    const safeId = normalizeId(threadId);
    if (!safeId) return;

    try {
      const threadsState = this.state.get('threads');
      const entry = threadsState?.map?.[safeId];
      const record = entry?.thread || entry || {};
      const messages = entry?.messages || [];

      const exportData = {
        id: safeId,
        title: record.title || 'Conversation',
        agent_id: record.agent_id || record.agentId,
        created_at: record.created_at || record.createdAt,
        updated_at: record.updated_at || record.updatedAt,
        messages: messages.map((msg) => ({
          role: msg.role,
          content: msg.content,
          timestamp: msg.created_at || msg.createdAt || msg.timestamp,
        })),
        exported_at: new Date().toISOString(),
      };

      const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `conversation-${safeId}-${Date.now()}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

      this.eventBus.emit?.(EVENTS.SHOW_NOTIFICATION, {
        type: 'success',
        message: 'Conversation exportée avec succès',
      });
    } catch (error) {
      this.eventBus.emit?.(EVENTS.SHOW_NOTIFICATION, {
        type: 'error',
        message: 'Erreur lors de l\'export',
      });
    }
  }

  startRename(threadId) {
    const safeId = normalizeId(threadId);
    if (!safeId) return;

    const threadsState = this.state.get('threads');
    const entry = threadsState?.map?.[safeId];
    const record = entry?.thread || entry || {};
    const currentTitle = record.title || 'Conversation';

    this.editingId = safeId;
    this.editingValue = currentTitle;
    this.render(this.state.get('threads'));

    // Focus the input after render
    requestAnimationFrame(() => {
      const input = this.container?.querySelector(`.threads-panel__rename-input[data-thread-id="${safeId}"]`);
      if (input) {
        input.focus();
        input.select();
      }
    });
  }

  cancelRename() {
    this.editingId = null;
    this.editingValue = '';
    this.render(this.state.get('threads'));
  }

  async saveRename(threadId) {
    const safeId = normalizeId(threadId);
    if (!safeId || this.editingId !== safeId) return;

    const input = this.container?.querySelector(`.threads-panel__rename-input[data-thread-id="${safeId}"]`);
    if (!input) return;

    const newTitle = input.value.trim();
    if (!newTitle) {
      this.cancelRename();
      return;
    }

    const oldEditingId = this.editingId;
    this.editingId = null;
    this.editingValue = '';

    try {
      const updated = await apiUpdateThread(safeId, { title: newTitle });
      if (updated) {
        this.mergeThread(safeId, updated);
        this.eventBus.emit?.(EVENTS.THREADS_UPDATED, { id: safeId, thread: updated });
      }
    } catch (error) {
      const message = error?.message || 'Impossible de renommer la conversation.';
      this.setStatus('error', message);
      this.eventBus.emit?.(EVENTS.THREADS_ERROR, { action: 'rename', error });
      this.editingId = oldEditingId;
      this.editingValue = newTitle;
    } finally {
      this.render(this.state.get('threads'));
    }
  }

  async handleCreate() {
    if (this.pendingCreate) return;

    this.pendingCreate = true;
    this.render(this.state.get('threads'));

    try {
      const created = await apiCreateThread({ type: 'chat' });
      const id = normalizeId(created?.id);
      if (!id) throw new Error('Thread non cree');

      this.mergeThread(id, created.thread || { id });
      this.state.set('threads.currentId', id);
      this.eventBus.emit?.(EVENTS.THREADS_CREATED, created);

      await this.handleSelect(id);
    } catch (error) {
      const message = error?.message || 'Impossible de creer la conversation.';
      this.setStatus('error', message);
      this.eventBus.emit?.(EVENTS.THREADS_ERROR, { action: 'create', error });
      if (error?.status === 401) {
        this.eventBus.emit?.('auth:missing', { reason: 401 });
      }
    } finally {
      this.pendingCreate = false;
      this.render(this.state.get('threads'));
    }
  }

  async handleSelect(threadId) {
    const safeId = normalizeId(threadId);
    if (!safeId) return;
    if (this.selectionLoadingId === safeId) return;

    this.selectionLoadingId = safeId;
    this.state.set('threads.currentId', safeId);
    this.state.set('chat.threadId', safeId);
    this.updateOrderForSelection(safeId);
    this.render(this.state.get('threads'));

    try {
      const cached = this.state.get(`threads.map.${safeId}`) || null;
      const needsFetch = !cached || !Array.isArray(cached.messages) || !cached.messages.length;
      const detail = needsFetch ? await fetchThreadDetail(safeId, { messages_limit: 100 }) : cached;

      if (detail?.id) {
        const entry = {
          id: safeId,
          thread: detail.thread || cached?.thread || { id: safeId },
          messages: ensureArray(detail.messages ?? cached?.messages),
          docs: ensureArray(detail.docs ?? cached?.docs),
        };

        this.state.set(`threads.map.${safeId}`, entry);
        this.mergeThread(safeId, entry.thread);

        try { localStorage.setItem(THREAD_STORAGE_KEY, safeId); } catch {}

        this.eventBus.emit?.(EVENTS.THREADS_SELECTED, entry);
        this.eventBus.emit?.(EVENTS.THREADS_LOADED, entry);
        this.state.set('threads.error', null);
      }
    } catch (error) {
      const message = error?.message || 'Impossible de charger la conversation.';
      this.setStatus('error', message);
      this.eventBus.emit?.(EVENTS.THREADS_ERROR, { action: 'select', error });
      if (error?.status === 401) {
        this.eventBus.emit?.('auth:missing', { reason: 401 });
      }
    } finally {
      this.selectionLoadingId = null;
      this.render(this.state.get('threads'));
    }
  }

  async handleArchive(threadId) {
    const safeId = normalizeId(threadId);
    if (!safeId || this.archivingId === safeId) return;

    this.archivingId = safeId;
    this.render(this.state.get('threads'));

    try {
      const updated = await apiArchiveThread(safeId);
      this.mergeThread(safeId, updated?.thread || updated || { id: safeId, archived: true });
      this.removeThreadFromState(safeId);
      this.eventBus.emit?.(EVENTS.THREADS_ARCHIVED, { id: safeId });

      const state = this.state.get('threads');
      if (state?.currentId === safeId) {
        const nextId = state?.order?.[0] || null;
        if (nextId) {
          await this.handleSelect(nextId);
        } else {
          await this.handleCreate();
        }
      }

      try {
        const stored = this.readStoredThreadId();
        if (stored === safeId) {
          localStorage.removeItem(THREAD_STORAGE_KEY);
        }
      } catch {}
    } catch (error) {
      const message = error?.message || "Impossible d'archiver la conversation.";
      this.setStatus('error', message);
      this.eventBus.emit?.(EVENTS.THREADS_ERROR, { action: 'archive', error });
      if (error?.status === 401) {
        this.eventBus.emit?.('auth:missing', { reason: 401 });
      }
    } finally {
      this.archivingId = null;
      this.render(this.state.get('threads'));
    }
  }

  async handleDelete(threadId) {
    const safeId = normalizeId(threadId);
    if (!safeId || this.deletingId === safeId) return;

    const wasActive = this.state.get('threads.currentId') === safeId;

    this.deletingId = safeId;
    this.render(this.state.get('threads'));

    try {
      await this.deleteThreadFn(safeId);
      this.removeThreadFromState(safeId);
      this.pendingDeleteId = null;
      this.eventBus.emit?.(EVENTS.THREADS_DELETED, { id: safeId });

      const order = this.state.get('threads.order') || [];
      const fallbackId = this.state.get('threads.currentId') || (order.length ? order[0] : null);
      if (!order.length) {
        await this.handleCreate();
      } else if (wasActive && fallbackId) {
        await this.handleSelect(fallbackId);
      }

      try {
        const stored = this.readStoredThreadId();
        if (stored === safeId) {
          localStorage.removeItem(THREAD_STORAGE_KEY);
        }
      } catch {}
    } catch (error) {
      const message = error?.message || "Impossible de supprimer la conversation.";
      this.setStatus('error', message);
      this.eventBus.emit?.(EVENTS.THREADS_ERROR, { action: 'delete', error });
      if (error?.status === 401) {
        this.eventBus.emit?.('auth:missing', { reason: 401 });
      }
    } finally {
      this.deletingId = null;
      this.pendingDeleteId = null;
      this.render(this.state.get('threads'));
    }
  }


  mergeThread(id, threadRecord) {
    const safeId = normalizeId(id);
    if (!safeId) return;

    const mapKey = `threads.map.${safeId}`;
    const existing = this.state.get(mapKey) || { id: safeId, messages: [], docs: [] };
    const entry = {
      ...existing,
      id: safeId,
      thread: threadRecord && typeof threadRecord === 'object'
        ? { ...threadRecord, id: threadRecord.id || safeId }
        : (existing.thread || { id: safeId }),
    };

    this.state.set(mapKey, entry);

    const order = this.state.get('threads.order');
    if (!Array.isArray(order) || !order.includes(safeId)) {
      const nextOrder = [safeId, ...(Array.isArray(order) ? order.filter((item) => item !== safeId) : [])];
      this.state.set('threads.order', nextOrder);
    }

    this.eventBus.emit?.(EVENTS.THREADS_UPDATED, { id: safeId, thread: entry.thread });
  }

  removeThreadFromState(id) {
    const safeId = normalizeId(id);
    if (!safeId) return;

    const threadsState = this.state.get('threads') || {};
    const { map, order } = cloneThreadsState(threadsState);
    delete map[safeId];

    const filteredOrder = order.filter((item) => item !== safeId);
    this.state.set('threads.map', map);
    this.state.set('threads.order', filteredOrder);

    if (threadsState.currentId === safeId) {
      this.state.set('threads.currentId', filteredOrder[0] || null);
      this.state.set('chat.threadId', filteredOrder[0] || null);
    }
  }

  updateOrderForSelection(id) {
    const safeId = normalizeId(id);
    if (!safeId) return;

    const threadsState = this.state.get('threads') || {};
    const order = Array.isArray(threadsState.order) ? threadsState.order : [];
    const nextOrder = [safeId, ...order.filter((item) => item !== safeId)];
    this.state.set('threads.order', nextOrder);
  }

  setStatus(status, errorMessage = undefined) {
    const allowed = ['idle', 'loading', 'ready', 'error'];
    const nextStatus = allowed.includes(status) ? status : 'idle';
    if (this.state.get('threads.status') !== nextStatus) {
      this.state.set('threads.status', nextStatus);
    }
    if (errorMessage !== undefined) {
      this.state.set('threads.error', errorMessage);
    } else if (nextStatus !== 'error') {
      this.state.set('threads.error', null);
    }
  }

  render(threadsState) {
    if (!this.container) return;
    const state = threadsState || {};

    if (this.newButton) {
      this.newButton.disabled = this.pendingCreate || state.status === 'loading';
    }

    if (this.errorEl) {
      const message = state.status === 'error' ? (state.error || 'Une erreur est survenue.') : '';
      this.errorEl.textContent = message;
      this.errorEl.hidden = !message;
    }

    this.renderList(state);
    this.renderContextMenu();
    this._hasInitialRender = true;
  }

  renderContextMenu() {
    // Remove existing context menu
    const existingMenu = document.querySelector('.threads-context-menu');
    if (existingMenu) {
      existingMenu.remove();
    }

    if (!this.contextMenuId) return;

    const menu = document.createElement('div');
    menu.className = 'threads-context-menu';
    menu.style.left = `${this.contextMenuX}px`;
    menu.style.top = `${this.contextMenuY}px`;

    menu.innerHTML = `
      <button type="button" class="threads-context-menu__item" data-action="context-rename" data-thread-id="${escapeHtml(this.contextMenuId)}">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z"></path>
        </svg>
        Renommer
      </button>
      <button type="button" class="threads-context-menu__item" data-action="context-export" data-thread-id="${escapeHtml(this.contextMenuId)}">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
          <polyline points="7 10 12 15 17 10"></polyline>
          <line x1="12" y1="15" x2="12" y2="3"></line>
        </svg>
        Exporter
      </button>
      <button type="button" class="threads-context-menu__item" data-action="context-archive" data-thread-id="${escapeHtml(this.contextMenuId)}">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="21 8 21 21 3 21 3 8"></polyline>
          <rect x="1" y="3" width="22" height="5"></rect>
          <line x1="10" y1="12" x2="14" y2="12"></line>
        </svg>
        Archiver
      </button>
      <button type="button" class="threads-context-menu__item threads-context-menu__item--danger" data-action="context-delete" data-thread-id="${escapeHtml(this.contextMenuId)}">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="3 6 5 6 21 6"></polyline>
          <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
        </svg>
        Supprimer
      </button>
    `;

    document.body.appendChild(menu);

    // Adjust position if menu goes off screen
    requestAnimationFrame(() => {
      const rect = menu.getBoundingClientRect();
      if (rect.right > window.innerWidth) {
        menu.style.left = `${this.contextMenuX - rect.width}px`;
      }
      if (rect.bottom > window.innerHeight) {
        menu.style.top = `${this.contextMenuY - rect.height}px`;
      }
    });
  }

  renderList(state) {
    if (!this.listEl) return;

    const order = Array.isArray(state.order) ? state.order : [];
    const map = state.map && typeof state.map === 'object' ? state.map : {};

    if (state.status === 'loading' && !order.length) {
      this.listEl.innerHTML = '<li class="threads-panel__placeholder">Chargement en cours...</li>';
      return;
    }

    if (!order.length) {
      this.listEl.innerHTML = '<li class="threads-panel__placeholder">Aucune conversation enregistree.</li>';
      return;
    }

    // Apply search filter
    let filteredOrder = this.filterThreadsBySearch(order, map);

    // Apply sorting
    filteredOrder = this.sortThreads(filteredOrder, map);

    if (this.searchQuery && !filteredOrder.length) {
      this.listEl.innerHTML = '<li class="threads-panel__placeholder">Aucune conversation ne correspond à votre recherche.</li>';
      return;
    }

    const currentId = state.currentId || null;
    const confirmId = this.pendingDeleteId || null;
    const deletingId = this.deletingId || null;
    const archivingId = this.archivingId || null;
    const loadingId = this.selectionLoadingId || null;

    const itemsHtml = filteredOrder.map((id) => {
      const entry = map[id] || { id };
      const record = entry.thread || entry;
      const title = record?.title || 'Conversation';
      const agentId = record?.agent_id || record?.agentId || null;
      const statusLabel = record?.archived ? STATUS_LABELS.archived : STATUS_LABELS.active;
      const messageCount = getInteractionCount(entry, record);
      const interactionsLabel = formatInteractionCount(messageCount);
      const lastTimestamp = getLastInteractionTimestamp(entry, record);
      const timestamp = lastTimestamp || record?.updated_at || record?.last_message_at || record?.created_at || null;
      const isActive = currentId === id;
      const isLoading = loadingId === id;
      const isArchiving = archivingId === id;
      const isDeleting = deletingId === id;
      const showConfirmDelete = confirmId === id;
      const buttonClasses = ['threads-panel__select'];
      if (isActive) buttonClasses.push('is-active');
      if (isLoading) buttonClasses.push('is-loading');
      if (isDeleting) buttonClasses.push('is-disabled');
      const archiveClasses = ['threads-panel__archive'];
      if (isArchiving) archiveClasses.push('is-busy');
      if (isDeleting) archiveClasses.push('is-disabled');
      const deleteClasses = ['threads-panel__delete'];
      if (isDeleting) deleteClasses.push('is-busy');
      const label = agentLabel(agentId);
      let statusText = statusLabel;
      if (isDeleting) statusText = 'Suppression...';
      else if (isArchiving) statusText = 'Archivage...';
      else if (isLoading) statusText = 'Chargement...';
      const updated = formatDateTime(timestamp);
      const updatedTitle = timestamp ? new Date(timestamp).toISOString() : '';
      const timestampAttributes = [];
      if (updatedTitle) timestampAttributes.push('title="' + escapeHtml(updatedTitle) + '"');
      if (lastTimestamp) timestampAttributes.push('data-source="last-interaction"');
      const timestampAttr = timestampAttributes.length ? ' ' + timestampAttributes.join(' ') : '';
      const isEditing = this.editingId === id;
      const actionsHtml = showConfirmDelete
        ? `
          <div class="threads-panel__confirm" data-thread-id="${escapeHtml(id)}">
            <p class="threads-panel__confirm-text">Supprimer cette conversation ?</p>
            <div class="threads-panel__confirm-actions">
              <button type="button" class="threads-panel__confirm-delete" data-action="delete-confirm" data-thread-id="${escapeHtml(id)}"${isDeleting ? ' disabled' : ''}>Confirmer</button>
              <button type="button" class="threads-panel__confirm-cancel" data-action="delete-cancel" data-thread-id="${escapeHtml(id)}"${isDeleting ? ' disabled' : ''}>Annuler</button>
            </div>
          </div>
        `
        : isEditing
        ? `
          <div class="threads-panel__rename-form" data-thread-id="${escapeHtml(id)}">
            <input
              type="text"
              class="threads-panel__rename-input"
              data-thread-id="${escapeHtml(id)}"
              value="${escapeHtml(title)}"
              placeholder="Nouveau nom..."
              aria-label="Nouveau nom de conversation"
            />
            <div class="threads-panel__rename-actions">
              <button type="button" class="threads-panel__rename-save" data-action="rename-save" data-thread-id="${escapeHtml(id)}">✓</button>
              <button type="button" class="threads-panel__rename-cancel" data-action="rename-cancel" data-thread-id="${escapeHtml(id)}">✕</button>
            </div>
          </div>
        `
        : `
          <div class="threads-panel__actions">
            <button type="button" class="threads-panel__rename" data-action="rename" data-thread-id="${escapeHtml(id)}" title="Renommer"${(isArchiving || isDeleting) ? ' disabled' : ''}>
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z"></path>
              </svg>
            </button>
            <button type="button" class="${archiveClasses.join(' ')}" data-action="archive" data-thread-id="${escapeHtml(id)}"${(isArchiving || isDeleting) ? ' disabled' : ''}>Archiver</button>
            <button type="button" class="${deleteClasses.join(' ')}" data-action="delete" data-thread-id="${escapeHtml(id)}"${isDeleting ? ' disabled' : ''}>Supprimer</button>
          </div>
        `;
      return `
        <li class="threads-panel__item${isActive ? ' is-active' : ''}" data-thread-id="${escapeHtml(id)}">
          <button type="button" class="${buttonClasses.join(' ')}" data-action="select" data-thread-id="${escapeHtml(id)}" aria-pressed="${isActive ? 'true' : 'false'}"${isDeleting ? ' disabled' : ''}>
            <span class="threads-panel__item-title">${escapeHtml(title)}</span>
            <span class="threads-panel__item-meta">
              <span class="threads-panel__item-agent">${escapeHtml(label)}</span>
              <span class="threads-panel__item-status">${escapeHtml(statusText)}</span>
              <span class="threads-panel__item-count">${escapeHtml(interactionsLabel)}</span>
            </span>
            <span class="threads-panel__item-timestamp"${timestampAttr}>${escapeHtml(updated)}</span>
          </button>
          ${actionsHtml}
        </li>
      `;
    }).join('');

    this.listEl.innerHTML = itemsHtml;
  }
}
