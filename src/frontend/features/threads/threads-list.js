/**
 * @module features/threads/threads-list
 * @description Module UI "Conversations" + pont de persistance (cross-device).
 * - Liste threads (actifs/archivés), création, ouverture, archivage, export.
 * - Persistance auto des messages (user/assistant) via EventBus WS.
 * - Preview RAG/sources sur la dernière réponse assistant du thread.
 */
import { EVENTS } from '../../shared/constants.js';
import {
  listThreads,
  createThread,
  patchThread,
  exportThread,
  postMessage,
  listMessages,
} from './api.js';

export default class ThreadsModule {
  constructor(eventBus, state) {
    this.eventBus = eventBus;
    this.state = state;

    // Adaptateur simple pour conserver l’interface this.api.*
    this.api = {
      list:       (opts)               => listThreads(opts),
      create:     ({ title, doc_ids }) => createThread({ title, doc_ids }),
      archive:    (id, archived)       => patchThread(id, { archived: !!archived }),
      export:     (id, format)         => exportThread(id, format || 'md'),
      messages:   (id, opts)           => listMessages(id, opts),
      addMessage: (id, msg)            => postMessage(id, msg),
    };

    this.container = null;
    this.listEl = null;
    this.viewArchived = false;

    this._listeners = [];
    this._assistantBuffers = new Map(); // streamId -> { agent_id, chunks[] }
    this._lastMeta = new Map();         // threadId -> { hasRag, sources[] }
  }

  // ───────────────────────── Lifecycle ─────────────────────────
  init() {
    // clear old listeners
    this._listeners.forEach(off => { try { off && off(); } catch {} });
    this._listeners = [];
    const on = (evt, fn) => this._listeners.push(this.eventBus.on(evt, fn));

    // rafraîchir quand l’onglet s’affiche
    on(EVENTS.MODULE_SHOW, (moduleId) => {
      if (moduleId === 'threads') this.refreshThreads().catch(console.error);
    });

    // Pont WS → persistance
    on(EVENTS.WS_SEND,             (msg) => this._onUserSend(msg));
    on('ws:chat_stream_start',     (e)   => this._onStreamStart(e));
    on('ws:chat_stream_chunk',     (e)   => this._onStreamChunk(e));
    on('ws:chat_stream_end',       (e)   => this._onStreamEnd(e));
  }

  mount(container) {
    this.container = container;
    this.container.innerHTML = this._renderShell();
    this.listEl = this.container.querySelector('[data-threads-list]');
    this._bindUI();
    this.refreshThreads().catch(console.error);
  }

  unmount() {
    this._listeners.forEach(off => { try { off && off(); } catch {} });
    this._listeners = [];
    this._assistantBuffers.clear();
    this._lastMeta.clear();
    if (this.container) this.container.innerHTML = '';
    this.container = null;
  }

  // ───────────────────────── UI ─────────────────────────
  _renderShell() {
    return `
      <section class="threads-module">
        <header class="threads-header" style="display:flex;justify-content:space-between;align-items:center;gap:.75rem;margin-bottom:.75rem;">
          <div class="left"><h2 style="margin:0;font-size:1.1rem;">Conversations</h2></div>
          <div class="right" style="display:flex;gap:.5rem;align-items:center;">
            <button class="btn btn-primary" data-action="new-thread">+ Nouveau</button>
            <div class="segmented" style="display:flex;gap:.25rem;">
              <button class="seg ${this.viewArchived ? '' : 'active'}" data-action="view-active">Actifs</button>
              <button class="seg ${this.viewArchived ? 'active' : ''}" data-action="view-archived">Archivés</button>
            </div>
          </div>
        </header>
        <div class="threads-list" data-threads-list></div>
      </section>
    `;
  }

  _bindUI() {
    this.container.addEventListener('click', async (ev) => {
      const btn = ev.target.closest('button,[data-action],[data-thread-id]');
      if (!btn) return;

      if (btn.matches('[data-action="new-thread"]'))       { await this._createThread(); return; }
      if (btn.matches('[data-action="view-active"]'))      { this.viewArchived = false; this._updateTabs(); await this.refreshThreads(); return; }
      if (btn.matches('[data-action="view-archived"]'))    { this.viewArchived = true;  this._updateTabs(); await this.refreshThreads(); return; }

      const tid = btn.getAttribute('data-thread-id'); if (!tid) return;
      if (btn.matches('[data-action="open"]'))             { await this._openThread(tid); return; }
      if (btn.matches('[data-action="archive"]'))          { await this._archiveThread(tid); return; }
      if (btn.matches('[data-action="export"]'))           { await this._exportThread(tid); return; }
    });
  }

  _updateTabs() {
    const active = this.container.querySelector('[data-action="view-active"]');
    const archived = this.container.querySelector('[data-action="view-archived"]');
    if (active && archived) {
      active.classList.toggle('active', !this.viewArchived);
      archived.classList.toggle('active', this.viewArchived);
    }
  }

  _rowHTML(t) {
    const dt = (s) => {
      if (!s) return '';
      try {
        const d = new Date(s);
        const pad = (n) => String(n).padStart(2, '0');
        return `${pad(d.getDate())}.${pad(d.getMonth()+1)}.${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
      } catch { return s; }
    };

    const meta = this._lastMeta.get(t.id) || { hasRag: false, sources: [] };
    const ragBadge = meta.hasRag
      ? `<span class="chip rag-chip" title="RAG activé (${meta.sources.length} source${meta.sources.length>1?'s':''})"
           style="display:inline-flex;align-items:center;gap:.35rem;padding:.15rem .5rem;border:1px solid rgba(255,255,255,.15);border-radius:999px;font-size:.75rem;opacity:.9;">
           <span style="width:.55rem;height:.55rem;border-radius:50%;background:#10b981;display:inline-block;"></span>
           RAG • ${meta.sources.length}
         </span>` : '';

    const sourceList = meta.hasRag && meta.sources.length
      ? `<div class="rag-sources" style="margin-top:.25rem;opacity:.9;font-size:.78rem;">
           ${meta.sources.slice(0,3).map(s => `<span style="display:inline-block;max-width:260px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;border:1px solid rgba(255,255,255,.12);border-radius:8px;padding:.1rem .4rem;margin:.1rem;">${s.filename || s.document_id}</span>`).join('')}
           ${meta.sources.length>3 ? `<span style="opacity:.7;">+${meta.sources.length-3}…</span>` : ''}
         </div>` : '';

    const preview = (t.last_message_preview || '').slice(0, 120);
    return `
      <div class="thread-row" data-id="${t.id}" style="display:flex;justify-content:space-between;gap:.75rem;border:1px solid rgba(255,255,255,.12);border-radius:12px;padding:.6rem .75rem;margin:.45rem 0;">
        <div class="meta" style="flex:1 1 auto;min-width:0;">
          <div class="title" style="font-weight:700;">${t.title || '(sans titre)'}</div>
          <div class="sub" style="opacity:.8;font-size:.82rem;">${dt(t.updated_at || t.created_at)} — ${t.message_count ?? 0} msg ${ragBadge ? ' · ' + ragBadge : ''}</div>
          ${preview ? `<div class="preview" style="margin-top:.25rem;opacity:.95;">${preview}</div>` : ''}
          ${sourceList}
        </div>
        <div class="actions" style="display:flex;gap:.35rem;align-items:center;">
          <button class="btn" data-action="open" data-thread-id="${t.id}">Ouvrir</button>
          ${t.archived ? '' : `<button class="btn" data-action="archive" data-thread-id="${t.id}">Archiver</button>`}
          <button class="btn" data-action="export" data-thread-id="${t.id}">Export</button>
        </div>
      </div>
    `;
  }

  async refreshThreads() {
    if (!this.listEl) return;
    try {
      const rows = await this.api.list({ archived: this.viewArchived });
      const html = (rows || []).map((t) => this._rowHTML(t)).join('') || `
        <div class="empty">Aucune conversation ${this.viewArchived ? 'archivée' : 'active'}.</div>`;
      this.listEl.innerHTML = html;
    } catch (err) {
      console.error('Threads: list failed', err);
      this.listEl.innerHTML = `<div class="error">Erreur chargement conversations.</div>`;
    }
  }

  // ───────────────────────── Actions ─────────────────────────
  async _createThread() {
    const title = `Nouveau chat ${new Date().toLocaleString()}`;
    try {
      const t = await this.api.create({ title });
      this.state.set('threads.currentThreadId', t.id);
      await this.refreshThreads();
      await this._openThread(t.id);
    } catch (err) {
      console.error('Threads: create failed', err);
    }
  }

  async _openThread(threadId) {
    try {
      this.state.set('threads.currentThreadId', threadId);
      const msgs = await this.api.messages(threadId, { limit: 500 });

      // ✅ FIX: faute de frappe corrigée "[.(...)]" → "[...(…)]"
      const lastWithRag = [...(msgs || [])]
        .reverse()
        .find(m => m.role === 'assistant' && Array.isArray(m.rag_sources) && m.rag_sources.length);

      this._lastMeta.set(threadId, { hasRag: !!lastWithRag, sources: lastWithRag?.rag_sources || [] });
      this._hydrateChatFromThread(msgs || []);
      this._toast('Conversation chargée dans le Chat.');
      await this.refreshThreads();
    } catch (err) {
      console.error('Threads: open failed', err);
      this._toast('Erreur lors de l\'ouverture.', true);
    }
  }

  async _archiveThread(threadId) {
    try {
      await this.api.archive(threadId, true);
      await this.refreshThreads();
    } catch (err) {
      console.error('Threads: archive failed', err);
    }
  }

  async _exportThread(threadId) {
    try {
      await this.api.export(threadId, 'md');
    } catch (err) {
      console.error('Threads: export failed', err);
    }
  }

  // ───────────── Persistance Chat ↔ Threads (WS) ─────────────
  async _ensureCurrentThread() {
    let tid = this.state.get('threads.currentThreadId');
    if (tid) return tid;
    const t = await this.api.create({ title: `Session ${new Date().toLocaleString()}` });
    tid = t.id;
    this.state.set('threads.currentThreadId', tid);
    this.refreshThreads().catch(console.error);
    return tid;
  }

  async _onUserSend(wsSendPayload) {
    if (!wsSendPayload || wsSendPayload.type !== 'chat.message') return;
    const { text, agent_id } = wsSendPayload.payload || {};
    const content = (text || '').trim();
    if (!content) return;
    try {
      const threadId = await this._ensureCurrentThread();
      await this.api.addMessage(threadId, {
        role: 'user',
        content,
        agent: agent_id || this.state.get('chat.currentAgentId'),
        ts: new Date().toISOString(),
      });
    } catch (err) {
      console.error('Threads: persist user message failed', err);
    }
  }

  _onStreamStart({ agent_id, id }) {
    if (!id) return;
    this._assistantBuffers.set(id, { agent_id: agent_id || this.state.get('chat.currentAgentId'), chunks: [] });
  }

  _onStreamChunk({ id, chunk, delta }) {
    const rec = this._assistantBuffers.get(id);
    if (!rec) return;
    const part = typeof chunk === 'string' ? chunk : (typeof delta === 'string' ? delta : '');
    if (part) rec.chunks.push(part);
  }

  async _onStreamEnd({ id }) {
    const rec = this._assistantBuffers.get(id);
    if (!rec) return;
    this._assistantBuffers.delete(id);

    const content = (rec.chunks || []).join('') || '';
    if (!content) return;

    try {
      const threadId = await this._ensureCurrentThread();

      // Sources RAG courantes depuis l'état du Chat (rempli par ws:chat_sources)
      const allRag = this.state.get('chat.ragSources') || {};
      const ragSources = allRag[rec.agent_id] || [];

      await this.api.addMessage(threadId, {
        role: 'assistant',
        content,
        agent: rec.agent_id,
        rag_sources: ragSources,
        ts: new Date().toISOString(),
      });

      if (ragSources.length) this._lastMeta.set(threadId, { hasRag: true, sources: ragSources });
      await this.refreshThreads();
    } catch (err) {
      console.error('Threads: persist assistant message failed', err);
    }
  }

  // ───────────── Hydratation Chat ─────────────
  _hydrateChatFromThread(messages) {
    const byAgent = {};
    for (const m of messages) {
      const agent = m.agent || this.state.get('chat.currentAgentId') || 'neo';
      byAgent[agent] = byAgent[agent] || [];
      byAgent[agent].push({
        id: m.id,
        role: m.role,
        content: m.content || '',
        agent_id: agent,
        ts: m.ts || new Date().toISOString(),
        isStreaming: false,
      });
    }
    const firstAgent = Object.keys(byAgent)[0] || this.state.get('chat.currentAgentId') || 'neo';
    this.state.set('chat.messages', byAgent);
    this.state.set('chat.currentAgentId', firstAgent);
    this.eventBus.emit && this.eventBus.emit('chat:hydrate_from_thread', { agentId: firstAgent });
  }

  _toast(text, isError = false) {
    try {
      const ev = new CustomEvent('toast', { detail: { text, isError } });
      window.dispatchEvent(ev);
    } catch {}
  }
}
