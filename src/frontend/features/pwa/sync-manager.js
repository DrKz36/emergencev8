import { VERSION } from '../../version.js';
import { EVENTS } from '../../shared/constants.js';
import { OfflineStorage } from './offline-storage.js';

const DEFAULT_OPTIONS = {
  maxSnapshots: 30,
  showToast: true,
  outboxFlushDelay: 750,
};

function isSecureContext() {
  try {
    if (self.isSecureContext) return true;
    const { protocol, hostname } = window.location;
    return protocol === 'https:' || hostname === 'localhost' || hostname === '127.0.0.1';
  } catch {
    return false;
  }
}

export class OfflineSyncManager {
  constructor(eventBus, stateManager, options = {}) {
    this.eventBus = eventBus;
    this.state = stateManager;
    this.options = { ...DEFAULT_OPTIONS, ...options };

    this.storage = new OfflineStorage({ maxSnapshots: this.options.maxSnapshots });
    this.registration = null;
    this.isOffline = typeof navigator !== 'undefined' ? navigator.onLine === false : true;
    this.flushTimer = null;
    this.indicator = null;
    this.hydrating = false;
    this.unsubscribers = [];
  }

  async init() {
    await this.storage.ready();
    this.indicator = this._resolveIndicator();
    this._updateIndicator(this.isOffline);
    this._bindNetworkListeners();
    this._bindEventBus();
    this._registerServiceWorker();
    if (this.isOffline) {
      await this._hydrateFromSnapshots();
    } else {
      this.storage.pruneSnapshots(this.options.maxSnapshots).catch(() => {});
    }
    this._emitStatusChange(this.isOffline);
  }

  dispose() {
    if (typeof window !== 'undefined') {
      window.removeEventListener('online', this._handleOnline);
      window.removeEventListener('offline', this._handleOffline);
    }
    this.unsubscribers.forEach((unsubscribe) => {
      try { unsubscribe?.(); } catch {}
    });
    this.unsubscribers = [];
    if (this.flushTimer) {
      clearTimeout(this.flushTimer);
      this.flushTimer = null;
    }
  }

  /* ---------------- Initialisation helpers ---------------- */
  _resolveIndicator() {
    if (typeof document === 'undefined') return null;
    const node = document.getElementById('offline-indicator');
    if (node) return node;
    try {
      const created = document.createElement('div');
      created.id = 'offline-indicator';
      created.className = 'offline-indicator';
      created.setAttribute('role', 'status');
      created.setAttribute('aria-live', 'polite');
      created.setAttribute('hidden', 'true');
      created.innerHTML = '<span class="offline-indicator__dot"></span><span class="offline-indicator__label">Mode hors ligne</span>';
      document.body.appendChild(created);
      return created;
    } catch (error) {
      console.warn('[OfflineSyncManager] Unable to create indicator node', error);
    }
    return null;
  }

  _bindNetworkListeners() {
    this._handleOnline = () => {
      this.isOffline = false;
      this._updateIndicator(false);
      this._emitStatusChange(false);
      if (this.options.showToast) {
        this.eventBus.emit?.('ui:toast', {
          kind: 'success',
          text: 'Connexion rétablie. Synchronisation en cours…',
        });
      }
      this._scheduleOutboxFlush();
    };

    this._handleOffline = () => {
      this.isOffline = true;
      this._updateIndicator(true);
      this._emitStatusChange(true);
      if (this.options.showToast) {
        this.eventBus.emit?.('ui:toast', {
          kind: 'warning',
          text: 'Connexion perdue. Mode hors ligne activé.',
        });
      }
    };

    if (typeof window !== 'undefined') {
      window.addEventListener('online', this._handleOnline);
      window.addEventListener('offline', this._handleOffline);
    }
  }

  _bindEventBus() {
    if (!this.eventBus?.on) return;

    const offThreadsLoaded = this.eventBus.on(EVENTS.THREADS_LOADED, (payload) => {
      if (this.hydrating) return;
      if (!payload || !payload.id) return;
      this.storage
        .saveThreadSnapshot({
          id: payload.id,
          thread: payload.thread ?? null,
          messages: payload.messages ?? [],
          docs: payload.docs ?? [],
        })
        .then(() => this.storage.pruneSnapshots(this.options.maxSnapshots))
        .catch(() => {});
    });
    this.unsubscribers.push(offThreadsLoaded);

    const offThreadList = this.eventBus.on(EVENTS.THREADS_LIST_UPDATED, (payload) => {
      try {
        const items = Array.isArray(payload?.items) ? payload.items : [];
        if (!items.length) return;
        const order = items
          .map((item) => (item?.id ? String(item.id) : null))
          .filter(Boolean);
        if (!order.length) return;
        this.state?.set?.('threads.order', order);
      } catch (error) {
        console.warn('[OfflineSyncManager] Unable to persist thread order', error);
      }
    });
    this.unsubscribers.push(offThreadList);

    const offWsSend = this.eventBus.on('ws:send', (frame) => {
      if (!this.isOffline) return;
      if (!frame || typeof frame !== 'object') return;
      this.storage.enqueueFrame(frame).catch(() => {});
    });
    this.unsubscribers.push(offWsSend);

    const offWsConnected = this.eventBus.on(EVENTS.WS_CONNECTED || 'ws:connected', () => {
      if (this.isOffline) return;
      this._scheduleOutboxFlush();
    });
    this.unsubscribers.push(offWsConnected);
  }

  async _registerServiceWorker() {
    if (typeof navigator === 'undefined') return;
    if (!('serviceWorker' in navigator)) return;
    if (!isSecureContext()) return;
    try {
      const swUrl = `/sw.js?v=${encodeURIComponent(VERSION || 'dev')}`;
      this.registration = await navigator.serviceWorker.register(swUrl, { scope: '/' });
      if (this.registration?.waiting) {
        this.registration.waiting.postMessage({ type: 'SKIP_WAITING' });
      }
      this.registration?.addEventListener?.('updatefound', () => {
        const installing = this.registration?.installing;
        if (!installing) return;
        installing.addEventListener('statechange', () => {
          if (installing.state === 'installed' && navigator.serviceWorker?.controller) {
            this.eventBus.emit?.('ui:toast', {
              kind: 'info',
              text: 'Une mise à jour hors ligne est disponible. Rechargez pour appliquer.',
            });
          }
        });
      });
    } catch (error) {
      console.warn('[OfflineSyncManager] Service worker registration failed', error);
    }
  }

  async _hydrateFromSnapshots() {
    try {
      const snapshots = await this.storage.getRecentSnapshots(this.options.maxSnapshots);
      if (!snapshots.length) return;

      const map = this.state?.get?.('threads.map') || {};
      const nextMap = { ...map };
      const order = [];

      for (const snapshot of snapshots) {
        order.push(snapshot.id);
        nextMap[snapshot.id] = {
          ...(nextMap[snapshot.id] || {}),
          id: snapshot.id,
          thread: snapshot.thread ?? null,
          messages: Array.isArray(snapshot.messages) ? [...snapshot.messages] : [],
          docs: Array.isArray(snapshot.docs) ? [...snapshot.docs] : [],
          updatedAt: snapshot.updatedAt ?? Date.now(),
          offlineCachedAt: snapshot.updatedAt ?? Date.now(),
        };
      }

      this.state?.set?.('threads.map', nextMap);
      if (order.length) {
        this.state?.set?.('threads.order', order);
      }
      if (!this.state?.get?.('threads.currentId') && order.length) {
        this.state?.set?.('threads.currentId', order[0]);
      }

      const first = snapshots[0];
      if (first) {
        this.hydrating = true;
        try {
          this.eventBus.emit?.(EVENTS.THREADS_LOADED, {
            id: first.id,
            thread: first.thread,
            messages: first.messages,
            docs: first.docs,
            offline: true,
          });
        } finally {
          this.hydrating = false;
        }
      }
    } catch (error) {
      console.warn('[OfflineSyncManager] Hydration failed', error);
    }
  }

  _emitStatusChange(offline) {
    try {
      this.eventBus.emit?.(EVENTS.OFFLINE_STATUS_CHANGED || 'app:offline_status', { offline });
    } catch {}
    try {
      this.options.onStatusChange?.({ offline });
    } catch (error) {
      console.warn('[OfflineSyncManager] onStatusChange callback failed', error);
    }
  }

  _updateIndicator(offline) {
    if (typeof document !== 'undefined') {
      document.body.classList.toggle('offline-mode', !!offline);
    }
    if (!this.indicator) return;
    if (offline) {
      this.indicator.removeAttribute('hidden');
    } else {
      this.indicator.setAttribute('hidden', 'true');
    }
  }

  _scheduleOutboxFlush() {
    if (this.flushTimer) {
      clearTimeout(this.flushTimer);
      this.flushTimer = null;
    }
    if (this.isOffline) return;
    this.flushTimer = setTimeout(() => {
      this.flushTimer = null;
      this.flushOutbox();
    }, this.options.outboxFlushDelay);
  }

  async flushOutbox() {
    try {
      const frames = await this.storage.listOutbox();
      if (!frames.length) return 0;
      let sent = 0;
      for (const entry of frames) {
        if (this.isOffline) break;
        if (entry?.frame) {
          this.eventBus.emit?.('ws:send', entry.frame);
          sent += 1;
        }
        await this.storage.deleteOutboxItem(entry.uid);
      }
      if (sent && this.options.showToast) {
        this.eventBus.emit?.('ui:toast', {
          kind: 'info',
          text: `${sent} message(s) synchronisés après reconnexion.`,
        });
      }
      return sent;
    } catch (error) {
      console.warn('[OfflineSyncManager] Flush outbox failed', error);
      return 0;
    }
  }
}

export default OfflineSyncManager;
