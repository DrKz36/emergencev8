/**
 * src/frontend/features/chat/chat-ui.js
 * V24.6 — Agent selector en header (haut-gauche), bandeau RAG retiré, composer dark lisible,
 *         payload propre (plus de agent:"user").
 */
import { EVENTS, AGENTS } from '../../shared/constants.js';

export class ChatUI {
  constructor(eventBus, stateManager) {
    this.eventBus = eventBus;
    this.stateManager = stateManager;
    this.state = {
      isLoading: false,
      currentAgentId: 'anima',
      ragEnabled: false,
      messages: {},
      ragStatus: {},
      ragSources: {},
      // Mémoire
      memoryStatus: {},
      memorySources: {},
    };
    this.listeners = [];
    this.isInitialized = false;

    this._streamBuffers = new Map(); // id -> string
    this._flushScheduled = false;
  }

  init() {
    if (this.isInitialized) return;
    this.isInitialized = true;
  }

  render(container, chatState = {}) {
    if (!container) return;
    this.state = { ...this.state, ...chatState };

    const agentTabs = this._agentTabsHTML(this.state.currentAgentId);

    container.innerHTML = `
      <div class="chat-container card">
        <div class="chat-header card-header">
          <div class="header-left">
            <div class="agent-selector agent-selector--header">
              ${agentTabs}
            </div>
          </div>
          <div class="chat-title">Dialogue</div>
        </div>

        <!-- Bandeau mémoire (placeholder, mis à jour dynamiquement) -->
        <div class="memory-banner" style="display:none">
          <div class="memory-dot"></div>
          <div class="memory-text"><strong> Mémoire </strong><span class="memory-status"></span></div>
          <div class="memory-sources"></div>
        </div>

        <div class="chat-messages card-body" id="chat-messages"></div>

        <div class="chat-input-area card-footer">
          <form id="chat-form" class="chat-form" autocomplete="off">
            <textarea id="chat-input" class="chat-input" rows="1" placeholder="Écrivez votre message..."></textarea>
            <button type="submit" id="chat-send" class="chat-send-button" title="Envoyer" aria-label="Envoyer">➤</button>
          </form>

          <div class="chat-actions">
            <span class="rag-label">RAG</span>
            <button
              type="button"
              id="chat-rag-power"
              class="rag-power"
              role="switch"
              aria-checked="${String(!!this.state.ragEnabled)}"
              title="${this.state.ragEnabled ? 'RAG activé' : 'RAG désactivé'}">
              <svg viewBox="0 0 24 24" class="icon-power" aria-hidden="true" focusable="false">
                <path class="power-line" d="M12 3 v7" />
                <path class="power-circle" d="M6.5 7.5a7 7 0 1 0 11 0" />
              </svg>
            </button>

            <button type="button" id="chat-export" class="button">Exporter</button>
            <button type="button" id="chat-clear" class="button">Effacer</button>
          </div>
        </div>
      </div>
    `;

    this._bindEvents(container);
    this.update(container, this.state); // met aussi à jour le bandeau mémoire
  }

  update(container, chatState = {}) {
    if (!container) return;
    this.state = { ...this.state, ...chatState };

    container
      .querySelector('#chat-rag-power')
      ?.setAttribute('aria-checked', String(!!this.state.ragEnabled));

    this._setActiveAgentTab(container, this.state.currentAgentId);

    const raw = this.state.messages?.[this.state.currentAgentId];
    const list = this._asArray(raw).map((m) => this._normalizeMessage(m));
    this._renderMessages(container.querySelector('#chat-messages'), list);

    // MAJ bandeau mémoire pour l’agent courant
    const agentId = this.state.currentAgentId;
    const status = (this.state.memoryStatus || {})[agentId];
    const sources = (this.state.memorySources || {})[agentId] || [];
    this.updateMemoryBanner(agentId, { status, sources });
  }

  // ───────────────────── Bandeau Mémoire ─────────────────────
  _formatMemoryStatus(status) {
    switch (status) {
      case 'searching': return { label: 'Recherche en cours…', cls: 'memory--searching' };
      case 'found':     return { label: 'Mémoire chargée',     cls: 'memory--found' };
      case 'empty':     return { label: 'Aucune mémoire pertinente', cls: 'memory--empty' };
      case 'error':     return { label: 'Erreur mémoire',      cls: 'memory--error' };
      default:          return { label: '', cls: '' };
    }
  }

  updateMemoryBanner(agentId, data) {
    const el = this._ensureMemoryBanner();
    const statusEl = el.querySelector('.memory-status');
    const sourcesEl = el.querySelector('.memory-sources');

    // reset classes
    el.classList.remove('memory--searching','memory--found','memory--empty','memory--error');

    const { label, cls } = this._formatMemoryStatus((data && data.status) || '');
    if (!label) { el.style.display = 'none'; return; }

    el.style.display = 'flex';
    el.classList.add(cls);
    if (statusEl) statusEl.textContent = `— ${label}`;

    const sources = (data && Array.isArray(data.sources)) ? data.sources.slice(0,5) : [];
    if (sourcesEl) {
      if (!sources.length) { sourcesEl.innerHTML = ''; }
      else {
        sourcesEl.innerHTML = `
          <ul class="memory-list">
            ${sources.map(s => `<li title="${this._escapeAttr(s.preview||'')}">
              ${(s.preview||'').slice(0,90)}${(s.preview||'').length>90?'…':''}
            </li>`).join('')}
          </ul>
        `;
      }
    }
  }

  _ensureMemoryBanner() {
    const container = document.querySelector('.chat-container');
    let el = container?.querySelector('.memory-banner');
    if (!el && container) {
      el = document.createElement('div');
      el.className = 'memory-banner';
      el.innerHTML = `
        <div class="memory-dot"></div>
        <div class="memory-text"><strong> Mémoire </strong><span class="memory-status"></span></div>
        <div class="memory-sources"></div>
      `;
      container.insertBefore(el, container.querySelector('.chat-messages'));
    }
    return el || document.createElement('div');
  }

  // ───────────────────── Messages ─────────────────────
  _renderMessages(container, list = []) {
    try {
      if (!container) return;
      const items = Array.isArray(list) ? list : [];
      const atBottom =
        container.scrollHeight - container.scrollTop - container.clientHeight < 8;

      container.innerHTML = items.map(m => this._messageHTML(m)).join('');
      if (atBottom) container.scrollTop = container.scrollHeight;
    } catch (err) {
      console.error('[ChatUI] _renderMessages error', err);
    }
  }

  _bindEvents(container) {
    const form = container.querySelector('#chat-form');
    const input = container.querySelector('#chat-input');
    const ragBtn = container.querySelector('#chat-rag-power');

    form?.addEventListener('submit', (e) => {
      e.preventDefault();
      const text = (input?.value || '').trim();
      if (!text) return;
      this.eventBus.emit(EVENTS.CHAT_SEND, { text });
      input.value = '';
      input.dispatchEvent(new Event('input'));
    });

    input?.addEventListener('keydown', (ev) => {
      if (ev.key === 'Enter' && !ev.shiftKey) {
        ev.preventDefault();
        try {
          if (typeof form?.requestSubmit === 'function') form.requestSubmit();
          else form?.dispatchEvent(new Event('submit', { cancelable: true }));
        } catch {}
      }
    });

    container.querySelector('#chat-export')
      ?.addEventListener('click', () => this.eventBus.emit(EVENTS.CHAT_EXPORT, null));

    container.querySelector('#chat-clear')
      ?.addEventListener('click', () => this.eventBus.emit(EVENTS.CHAT_CLEAR, null));

    ragBtn?.addEventListener('click', () => {
      this.eventBus.emit(EVENTS.CHAT_RAG_TOGGLED, null);
    });

    // ⚠️ Émet l'ID string attendu par ChatModule.handleAgentSelected(agentId)
    container.querySelector('#chat-agent-tabs')
      ?.addEventListener('click', (e) => {
        const btn = e.target?.closest('button[data-agent-id]');
        if (!btn) return;
        const id = btn.getAttribute('data-agent-id');
        if (!id || id === this.state.currentAgentId) return;
        this.eventBus.emit(EVENTS.CHAT_AGENT_SELECTED, id);
      });
  }

  _messageHTML(m) {
    const side = m.role === 'user' ? 'user' : 'assistant';
    const agentId = m.agent_id || m.agent || 'nexus';
    const you = "FG";
    const name = side === 'user' ? you : (AGENTS[agentId]?.name || 'Agent');
    const raw = this._toPlainText(m.content);
    const content = this._escapeHTML(raw).replace(/\n/g, '<br/>');
    const cursor = m.isStreaming ? `<span class="blinking-cursor">▍</span>` : '';
    const stamp = this._formatTimestamp(m?.ts || Date.now());

    return `
      <div class="message ${side} ${side === 'assistant' ? agentId : ''}">
        <div class="message-content">
          <div class="message-meta meta-inside">
            <strong class="sender-name" data-role="author">${name}</strong>
            <span class="message-time">${stamp}</span>
          </div>
          <div class="message-text">${content}${cursor}</div>
        </div>
      </div>`;
  }

  _agentTabsHTML(activeId) {
    const ids = Object.keys(AGENTS);
    return `
      <div class="segmented" id="chat-agent-tabs">
        ${ids.map(id => `
          <button
            type="button"
            class="button-tab ${id===activeId ? 'active' : ''} agent--${id}"
            data-agent-id="${id}">
            <span class="tab-label">${AGENTS[id]?.name || id}</span>
          </button>
        `).join('')}
      </div>`;
  }

  _setActiveAgentTab(container, activeId) {
    container.querySelectorAll('.agent-selector .button-tab')
      ?.forEach(b => b.classList.toggle('active', b.getAttribute('data-agent-id') === activeId));
  }

  _asArray(v) {
    if (Array.isArray(v)) return v;
    if (!v) return [];
    if (typeof v === 'object') return Object.values(v);
    return [];
  }

  _normalizeMessage(m) {
    if (!m) return { role:'assistant', content:'' };
    if (typeof m === 'string') return { role:'assistant', content:m };
    return m;
  }

  _escapeHTML(s='') { return s.replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c])); }
  _escapeAttr(s='') { return this._escapeHTML(String(s)).replace(/\s+/g, ' ').trim(); }
  _toPlainText(v) { if (v == null) return ''; return typeof v === 'string' ? v : JSON.stringify(v); }

  _pad2(n) { return n < 10 ? `0${n}` : String(n); }
  _formatTimestamp(input) {
    try {
      const d = new Date(input);
      const DD = this._pad2(d.getDate());
      const MM = this._pad2(d.getMonth() + 1);
      const YYYY = d.getFullYear();
      const hh = this._pad2(d.getHours());
      const mm = this._pad2(d.getMinutes());
      return `${DD}.${MM}.${YYYY} ${hh}:${mm}`;
    } catch { return ''; }
  }
}
