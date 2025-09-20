/**
 * @module features/threads/threads
 * Threads management panel (list, create, select, archive) with EventBus synchronization.
 */

import {
  fetchThreads,
  fetchThreadDetail,
  createThread as apiCreateThread,
  archiveThread as apiArchiveThread,
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

export class ThreadsPanel {
  constructor(eventBus, stateManager) {
    this.eventBus = eventBus;
    this.state = stateManager;

    this.container = null;
    this.listEl = null;
    this.errorEl = null;
    this.newButton = null;

    this.unsubscribeState = null;
    this.unsubscribeRefresh = null;

    this.selectionLoadingId = null;
    this.archivingId = null;
    this.pendingCreate = false;

    this._hasInitialRender = false;
    this._onContainerClick = this.handleContainerClick.bind(this);
    this._onRefreshRequested = this.reload.bind(this);
  }

  init() {
    this.ensureContainer();
    if (this.container) {
      this.container.addEventListener('click', this._onContainerClick);
    }
    if (this.eventBus?.on) {
      this.unsubscribeRefresh = this.eventBus.on(EVENTS.THREADS_REFRESH_REQUEST, this._onRefreshRequested);
    }

    const currentThreadsState = this.state.get('threads');
    this.render(currentThreadsState);

    this.unsubscribeState = this.state.subscribe('threads', (threads) => {
      this.render(threads);
    });

    if (!currentThreadsState || currentThreadsState.status === 'idle') {
      this.reload();
    }
  }

  destroy() {
    if (this.container) {
      this.container.removeEventListener('click', this._onContainerClick);
    }
    if (typeof this.unsubscribeState === 'function') {
      this.unsubscribeState();
      this.unsubscribeState = null;
    }
    if (typeof this.unsubscribeRefresh === 'function') {
      this.unsubscribeRefresh();
      this.unsubscribeRefresh = null;
    }
  }

  ensureContainer() {
    if (this.container) return;

    const sidebar = document.getElementById('app-sidebar');
    if (!sidebar) return;

    let host = document.getElementById('threads-panel');
    if (!host) {
      host = document.createElement('section');
      host.id = 'threads-panel';
      host.className = 'threads-panel card';
      host.innerHTML = `
        <header class="threads-panel__header">
          <h2 class="threads-panel__title">Conversations</h2>
          <button type="button" class="threads-panel__new" data-action="new" aria-label="Lancer une nouvelle conversation">
            Nouvelle conversation
          </button>
        </header>
        <div class="threads-panel__body">
          <p class="threads-panel__error" data-role="thread-error" hidden></p>
          <ul class="threads-panel__list" data-role="thread-list" role="list"></ul>
        </div>
      `;

      const tabs = document.getElementById('app-tabs');
      if (tabs && tabs.parentNode === sidebar) {
        sidebar.insertBefore(host, tabs.nextSibling);
      } else {
        sidebar.appendChild(host);
      }
    }

    this.container = host;
    this.listEl = host.querySelector('[data-role="thread-list"]');
    this.errorEl = host.querySelector('[data-role="thread-error"]');
    this.newButton = host.querySelector('[data-action="new"]');
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
    this.state.set('websocket.sessionId', safeId);
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
    this._hasInitialRender = true;
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

    const currentId = state.currentId || null;
    const itemsHtml = order.map((id) => {
      const entry = map[id] || { id };
      const record = entry.thread || entry;
      const title = record?.title || 'Conversation';
      const agentId = record?.agent_id || record?.agentId || null;
      const statusLabel = record?.archived ? STATUS_LABELS.archived : STATUS_LABELS.active;
      const timestamp = record?.updated_at || record?.created_at || null;
      const isActive = currentId === id;
      const isLoading = this.selectionLoadingId === id;
      const isArchiving = this.archivingId === id;
      const buttonClasses = ['threads-panel__select'];
      if (isActive) buttonClasses.push('is-active');
      const archiveClasses = ['threads-panel__archive'];
      if (isArchiving) archiveClasses.push('is-busy');
      const label = agentLabel(agentId);
      const statusText = isLoading ? 'Chargement...' : statusLabel;
      const updated = formatDateTime(timestamp);
      return `
        <li class="threads-panel__item${isActive ? ' is-active' : ''}" data-thread-id="${escapeHtml(id)}">
          <button type="button" class="${buttonClasses.join(' ')}" data-action="select" data-thread-id="${escapeHtml(id)}" aria-pressed="${isActive ? 'true' : 'false'}">
            <span class="threads-panel__item-title">${escapeHtml(title)}</span>
            <span class="threads-panel__item-meta">
              <span class="threads-panel__item-agent">${escapeHtml(label)}</span>
              <span class="threads-panel__item-status">${escapeHtml(statusText)}</span>
            </span>
            <span class="threads-panel__item-timestamp">${escapeHtml(updated)}</span>
          </button>
          <button type="button" class="${archiveClasses.join(' ')}" data-action="archive" data-thread-id="${escapeHtml(id)}" aria-label="Archiver la conversation"${isArchiving ? ' disabled' : ''}>Archiver</button>
        </li>
      `;
    }).join('');

    this.listEl.innerHTML = itemsHtml;
  }
}
