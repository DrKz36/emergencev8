const DB_NAME = 'emergence-offline';
const DB_VERSION = 1;
const STORE_SNAPSHOTS = 'snapshots';
const STORE_OUTBOX = 'outbox';

function supportsIndexedDb() {
  try {
    return typeof indexedDB !== 'undefined';
  } catch {
    return false;
  }
}

function clampMessages(messages, limit = 200) {
  if (!Array.isArray(messages)) return [];
  if (messages.length <= limit) return [...messages];
  return messages.slice(messages.length - limit);
}

export class OfflineStorage {
  constructor(options = {}) {
    this.maxSnapshots = Math.max(1, options.maxSnapshots || 30);
    this.dbPromise = supportsIndexedDb() ? this.openDb() : Promise.resolve(null);
    this.memoryFallback = {
      snapshots: new Map(),
      outbox: [],
      outboxSeq: 0,
    };
  }

  async ready() {
    try {
      return await this.dbPromise;
    } catch (error) {
      console.warn('[OfflineStorage] IndexedDB unavailable, fallback to memory.', error);
      return null;
    }
  }

  openDb() {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, DB_VERSION);
      request.onupgradeneeded = (event) => {
        const db = event.target.result;
        if (!db.objectStoreNames.contains(STORE_SNAPSHOTS)) {
          const snapshots = db.createObjectStore(STORE_SNAPSHOTS, { keyPath: 'id' });
          snapshots.createIndex('updatedAt', 'updatedAt', { unique: false });
        }
        if (!db.objectStoreNames.contains(STORE_OUTBOX)) {
          const outbox = db.createObjectStore(STORE_OUTBOX, {
            keyPath: 'uid',
            autoIncrement: true,
          });
          outbox.createIndex('createdAt', 'createdAt', { unique: false });
        }
      };
      request.onerror = () => reject(request.error || new Error('IndexedDB open failed'));
      request.onsuccess = () => resolve(request.result);
    });
  }

  /* ---------------- Snapshots ---------------- */
  async saveThreadSnapshot(snapshot) {
    if (!snapshot || !snapshot.id) return false;
    const payload = {
      id: snapshot.id,
      thread: snapshot.thread ? { ...snapshot.thread } : null,
      messages: clampMessages(snapshot.messages),
      docs: Array.isArray(snapshot.docs) ? [...snapshot.docs] : [],
      updatedAt: Date.now(),
    };

    const db = await this.ready();
    if (!db) {
      this.memoryFallback.snapshots.set(payload.id, payload);
      this.pruneMemorySnapshots();
      return true;
    }

    return new Promise((resolve) => {
      const tx = db.transaction(STORE_SNAPSHOTS, 'readwrite');
      tx.oncomplete = () => resolve(true);
      tx.onerror = () => {
        console.warn('[OfflineStorage] snapshot transaction failed', tx.error);
        resolve(false);
      };
      try {
        tx.objectStore(STORE_SNAPSHOTS).put(payload);
      } catch (error) {
        console.warn('[OfflineStorage] snapshot put failed', error);
        resolve(false);
      }
    });
  }

  async getRecentSnapshots(limit = this.maxSnapshots) {
    const db = await this.ready();
    if (!db) {
      return Array.from(this.memoryFallback.snapshots.values())
        .sort((a, b) => b.updatedAt - a.updatedAt)
        .slice(0, limit);
    }

    return new Promise((resolve) => {
      const tx = db.transaction(STORE_SNAPSHOTS, 'readonly');
      const store = tx.objectStore(STORE_SNAPSHOTS);
      const index = store.index('updatedAt');
      const snapshots = [];
      index.openCursor(null, 'prev').onsuccess = (event) => {
        const cursor = event.target.result;
        if (cursor && snapshots.length < limit) {
          snapshots.push(cursor.value);
          cursor.continue();
        } else {
          resolve(snapshots);
        }
      };
      tx.onerror = () => {
        console.warn('[OfflineStorage] snapshot cursor failed', tx.error);
        resolve([]);
      };
    });
  }

  async pruneSnapshots(limit = this.maxSnapshots) {
    const db = await this.ready();
    if (!db) {
      this.pruneMemorySnapshots(limit);
      return;
    }
    const keep = await this.getRecentSnapshots(limit);
    const keepIds = new Set(keep.map((item) => item.id));
    return new Promise((resolve) => {
      const tx = db.transaction(STORE_SNAPSHOTS, 'readwrite');
      const store = tx.objectStore(STORE_SNAPSHOTS);
      store.openCursor().onsuccess = (event) => {
        const cursor = event.target.result;
        if (!cursor) {
          resolve();
          return;
        }
        if (!keepIds.has(cursor.key)) {
          cursor.delete();
        }
        cursor.continue();
      };
      tx.onerror = () => {
        console.warn('[OfflineStorage] prune snapshots failed', tx.error);
        resolve();
      };
    });
  }

  pruneMemorySnapshots(limit = this.maxSnapshots) {
    const entries = Array.from(this.memoryFallback.snapshots.entries())
      .sort((a, b) => b[1].updatedAt - a[1].updatedAt);
    while (entries.length > limit) {
      const removed = entries.pop();
      if (removed) this.memoryFallback.snapshots.delete(removed[0]);
    }
  }

  /* ---------------- Outbox ---------------- */
  async enqueueFrame(frame) {
    if (!frame || typeof frame !== 'object') return null;
    const entry = {
      frame: JSON.parse(JSON.stringify(frame)),
      createdAt: Date.now(),
    };

    const db = await this.ready();
    if (!db) {
      this.memoryFallback.outboxSeq += 1;
      const uid = this.memoryFallback.outboxSeq;
      this.memoryFallback.outbox.push({ uid, ...entry });
      return uid;
    }

    return new Promise((resolve) => {
      const tx = db.transaction(STORE_OUTBOX, 'readwrite');
      const store = tx.objectStore(STORE_OUTBOX);
      const request = store.add(entry);
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => {
        console.warn('[OfflineStorage] enqueue frame failed', request.error);
        resolve(null);
      };
    });
  }

  async listOutbox() {
    const db = await this.ready();
    if (!db) {
      return [...this.memoryFallback.outbox].sort((a, b) => a.createdAt - b.createdAt);
    }

    return new Promise((resolve) => {
      const tx = db.transaction(STORE_OUTBOX, 'readonly');
      const store = tx.objectStore(STORE_OUTBOX);
      const index = store.index('createdAt');
      const frames = [];
      index.openCursor(null, 'next').onsuccess = (event) => {
        const cursor = event.target.result;
        if (!cursor) {
          resolve(frames);
          return;
        }
        frames.push({ uid: cursor.primaryKey, ...cursor.value });
        cursor.continue();
      };
      tx.onerror = () => {
        console.warn('[OfflineStorage] list outbox failed', tx.error);
        resolve([]);
      };
    });
  }

  async deleteOutboxItem(uid) {
    if (!uid && uid !== 0) return false;
    const db = await this.ready();
    if (!db) {
      const index = this.memoryFallback.outbox.findIndex((item) => item.uid === uid);
      if (index >= 0) {
        this.memoryFallback.outbox.splice(index, 1);
        return true;
      }
      return false;
    }

    return new Promise((resolve) => {
      const tx = db.transaction(STORE_OUTBOX, 'readwrite');
      const store = tx.objectStore(STORE_OUTBOX);
      const request = store.delete(uid);
      request.onsuccess = () => resolve(true);
      request.onerror = () => {
        console.warn('[OfflineStorage] delete outbox item failed', request.error);
        resolve(false);
      };
    });
  }

  async clearOutbox() {
    const db = await this.ready();
    if (!db) {
      this.memoryFallback.outbox.length = 0;
      return true;
    }
    return new Promise((resolve) => {
      const tx = db.transaction(STORE_OUTBOX, 'readwrite');
      const store = tx.objectStore(STORE_OUTBOX);
      const request = store.clear();
      request.onsuccess = () => resolve(true);
      request.onerror = () => {
        console.warn('[OfflineStorage] clear outbox failed', request.error);
        resolve(false);
      };
    });
  }
}

export default OfflineStorage;
