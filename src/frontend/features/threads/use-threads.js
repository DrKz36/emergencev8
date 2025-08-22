// ÉMERGENCE — Threads store (vanilla, EventTarget)
import { listThreads, createThread, patchThread, exportThread, listMessages, postMessage } from './api.js';

class ThreadsStore extends EventTarget {
  state = {
    archived: false,
    loading: false,
    items: [],
    selectedId: null,
    messages: [],
  };

  emit() { this.dispatchEvent(new CustomEvent('change', { detail: this.state })); }

  setArchived(flag) {
    if (this.state.archived !== !!flag) {
      this.state.archived = !!flag;
      this.load();
    }
  }

  async load() {
    this.state.loading = true; this.emit();
    try {
      const data = await listThreads({ archived: this.state.archived, limit: 50 });
      this.state.items = Array.isArray(data?.items) ? data.items : (Array.isArray(data) ? data : []);
    } catch (e) {
      console.error('[threads] load failed', e);
    } finally {
      this.state.loading = false; this.emit();
    }
  }

  async select(threadId) {
    this.state.selectedId = threadId;
    this.state.messages = [];
    this.emit();
    try {
      this.state.messages = await listMessages(threadId, { limit: 200 });
    } catch (e) {
      console.error('[threads] list messages failed', e);
    } finally {
      this.emit();
    }
  }

  async create({ title = '', doc_ids = [] } = {}) {
    const t = await createThread({ title, doc_ids });
    await this.load();
    if (t?.id) await this.select(t.id);
    return t;
  }

  async toggleArchive(thread) {
    const archived = !!thread?.archived;
    await patchThread(thread.id, { archived: !archived });
    await this.load();
  }

  async export(thread, format = 'md') {
    return exportThread(thread.id, format);
  }

  async sendMessage(content) {
    if (!this.state.selectedId || !content?.trim()) return;
    const msg = await postMessage(this.state.selectedId, { role: 'user', content: content.trim() });
    // Concat optimiste + reload partiel
    this.state.messages = [...this.state.messages, msg];
    this.emit();
  }
}

export const threadsStore = new ThreadsStore();
