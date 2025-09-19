/**
 * ChatUI - V28.3.2 (glass layout merge)
 * - Adopt glassmorphic layout with header/footer zones and auth host badge.
 * - Keeps mount-safe render, RAG sources, metrics, memory controls, and WS guards.
 * - Merges composer toolbar refinements and message bubble metadata.
 */
import { EVENTS, AGENTS } from '../../shared/constants.js';

export class ChatUI {
  constructor(eventBus, stateManager) {
    this.eventBus = eventBus;
    this.stateManager = stateManager;
    this.root = null;
    this.state = {
      isLoading: false,
      currentAgentId: 'anima',
      ragEnabled: false,
      messages: {},
      memoryBannerAt: null,
      lastAnalysis: null,
      metrics: { send_count: 0, ws_start_count: 0, last_ttfb_ms: 0, rest_fallback_count: 0, last_fallback_at: null },
      memoryStats: { has_stm: false, ltm_items: 0, injected: false },
      exportAgents: Object.keys(AGENTS),
      exportFormat: 'markdown',
      modelInfo: null,
      lastMessageMeta: null
    };
    console.log('[ChatUI] V28.3.2 (glass-layout) initialisee.');
  }

  render(container, chatState = {}) {
    if (!container) return;
    this.root = container;
    this.state = { ...this.state, ...chatState };
    const agentTabs = this._agentTabsHTML(this.state.currentAgentId);

    container.innerHTML = `
      <div class="chat-container card">
        <div class="chat-header">
          <div class="chat-header-left">
            <div class="chat-title">Dialogue</div>
            <div class="agent-selector">${agentTabs}</div>
          </div>
          <div class="chat-header-right">
            <div id="model-badge" class="model-badge">-</div>
            <div id="chat-auth-host" class="chat-auth-host" data-auth-host></div>
          </div>
        </div>
        <div class="chat-body">
          <div class="messages" id="chat-messages"></div>
          <div id="rag-sources" class="rag-sources"></div>
        </div>
        <div class="chat-footer">
          <form id="chat-form" class="chat-form" autocomplete="off">
            <div class="chat-composer" data-role="chat-composer">
              <div class="rag-toggle" data-role="rag-toggle">
                <button
                  type="button"
                  id="rag-power"
                  class="rag-power toggle-metal"
                  role="switch"
                  aria-checked="${String(!!this.state.ragEnabled)}"
                  aria-label="Activer ou desactiver le RAG"
                  title="Activer/Desactiver RAG">
                  <svg class="power-icon" viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
                    <path d="M12 3v9" stroke="currentColor" stroke-width="2" stroke-linecap="round" fill="none"></path>
                    <path d="M5.5 7a 8 8 0 1 0 13 0" stroke="currentColor" stroke-width="2" stroke-linecap="round" fill="none"></path>
                  </svg>
                </button>
                <span id="rag-label" class="rag-label">${this.state.ragEnabled ? 'RAG actif' : 'RAG inactif'}</span>
              </div>
              <div class="chat-input-shell">
                <textarea id="chat-input" class="chat-input" rows="1" placeholder="Ecris ton message..." aria-label="Message"></textarea>
              </div>
              <button type="submit" id="chat-send" class="chat-send-button" title="Envoyer" aria-label="Envoyer">
                <span class="sr-only">Envoyer</span>
                <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" focusable="false">
                  <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" fill="currentColor"></path>
                </svg>
              </button>
            </div>
          </form>
        </div>
      </div>
    `;

    this.eventBus.emit?.('ui:auth:host-changed');
    this._ensureControlPanel();
    this._bindEvents(container);
    this.update(container, this.state);
    console.log('[CHAT] ChatUI rendu -> container.id =', container.id || '(anonyme)');
  }
  update(container, chatState = {}) {
    if (!container) return;
    this.state = { ...this.state, ...chatState };
    this._ensureControlPanel();

    const ragBtn = container.querySelector('#rag-power');
    ragBtn?.setAttribute('aria-checked', String(!!this.state.ragEnabled));
    const ragLabel = container.querySelector('#rag-label');
    if (ragLabel) ragLabel.textContent = this.state.ragEnabled ? 'RAG actif' : 'RAG inactif';
    const ragToggle = container.querySelector('[data-role="rag-toggle"]');
    if (ragToggle) ragToggle.classList.toggle('is-on', !!this.state.ragEnabled);

    this._setActiveAgentTab(container, this.state.currentAgentId);

    const rawMessages = this.state.messages?.[this.state.currentAgentId];
    const list = this._asArray(rawMessages).map((m) => this._normalizeMessage(m));
    this._renderMessages(container.querySelector('#chat-messages'), list);
    this._renderSources(container.querySelector('#rag-sources'), this.state.lastMessageMeta?.sources);

    this._updateControlPanelState();

    const met = this.state.metrics || {};
    const badge = container.querySelector('#model-badge');
    if (badge) {
      const mi = this.state.modelInfo || {};
      const lm = this.state.lastMessageMeta || {};
      const usedProvider = (lm.provider || mi.provider || '').toString();
      const usedModel = (lm.model || mi.model || '').toString();
      const planned = `${mi.provider || '?'}:${mi.model || '?'}`;
      const used = `${usedProvider || '?'}:${usedModel || '?'}`;
      const fallback = !!(mi.provider && mi.model && (mi.provider !== usedProvider || mi.model !== usedModel));
      badge.textContent = usedProvider || usedModel ? (fallback ? `Fallback -> ${used}` : used) : '-';
      const ttfb = Number.isFinite(met.last_ttfb_ms) ? `${met.last_ttfb_ms} ms` : '-';
      badge.title = `Modele planifie: ${planned} - Utilise: ${used} - TTFB: ${ttfb}`;
      badge.classList.toggle('is-fallback', fallback);
    }
  }
  _bindEvents(container) {
    const form = container.querySelector('#chat-form');
    const input = container.querySelector('#chat-input');
    const ragBtn = container.querySelector('#rag-power');
    const ragLbl = container.querySelector('#rag-label');
    const sendBtn = container.querySelector('#chat-send');
    this._ensureControlPanel();
    this._updateControlPanelState();

    const autosize = () => this._autoGrow(input);
    setTimeout(autosize, 0);
    input?.addEventListener('input', autosize);
    window.addEventListener('resize', autosize);

    form?.addEventListener('submit', (e) => {
      e.preventDefault();
      const text = (input?.value || '').trim();
      if (!text) return;
      this.eventBus.emit(EVENTS.CHAT_SEND, { text, agent: 'user' });
      input.value = '';
      autosize();
    });

    input?.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        if (typeof form?.requestSubmit === 'function') form.requestSubmit();
        else form?.dispatchEvent(new Event('submit', { cancelable: true }));
      }
    });

    sendBtn?.addEventListener('click', () => {
      if (typeof form?.requestSubmit === 'function') form.requestSubmit();
      else form?.dispatchEvent(new Event('submit', { cancelable: true }));
    });

    const toggleRag = () => {
      if (!ragBtn) return;
      const on = ragBtn.getAttribute('aria-checked') === 'true';
      ragBtn.setAttribute('aria-checked', String(!on));
      this.eventBus.emit(EVENTS.CHAT_RAG_TOGGLED, { enabled: !on });
    };
    ragBtn?.addEventListener('click', toggleRag);
    ragLbl?.addEventListener('click', toggleRag);

    container.querySelector('.agent-selector')?.addEventListener('click', (e) => {
      const btn = e.target.closest('button[data-agent-id]');
      if (!btn) return;
      const agentId = btn.getAttribute('data-agent-id');
      this.eventBus.emit(EVENTS.CHAT_AGENT_SELECTED, agentId);
      this._setActiveAgentTab(container, agentId);
    });

    container.querySelector('#rag-sources')?.addEventListener('click', (e) => {
      const chip = e.target.closest('button[data-doc-id]');
      if (!chip) return;
      const info = {
        document_id: chip.getAttribute('data-doc-id'),
        filename: chip.getAttribute('data-filename'),
        page: Number(chip.getAttribute('data-page') || '0') || null,
        excerpt: chip.getAttribute('data-excerpt') || ''
      };
      this.eventBus.emit('rag:source:click', info);
    });

    try {
      const off = this.eventBus?.on?.('documents:changed', async (payload = {}) => {
        await this._onDocumentsChanged(container, payload);
      });
      if (typeof off === 'function') this._offDocumentsChanged = off;
    } catch {}
  }
  _ensureControlPanel() {
    try {
      const host = document.getElementById('settings-container');
      if (!host) return null;
      let panel = host.querySelector('[data-role="chat-control-panel"]');
      if (!panel) {
        panel = document.createElement('section');
        panel.dataset.role = 'chat-control-panel';
        panel.className = 'chat-controls-panel';
        panel.innerHTML = this._controlPanelMarkup();
        host.appendChild(panel);
      }
      panel.classList.remove('is-hidden');
      this._controlPanel = panel;
      if (!this._panelHandlersBound) {
        this._bindControlPanelEvents(panel);
        this._panelHandlersBound = true;
      }
      return panel;
    } catch (err) {
      console.error('[ChatUI] ensure control panel failed', err);
      return null;
    }
  }

  _controlPanelMarkup() {
    return `
      <div class="chat-controls-card">
        <div class="chat-controls-header">
          <span class="chat-controls-title">Memoire</span>
          <span id="memory-dot" class="chat-controls-dot" aria-hidden="true"></span>
        </div>
        <div class="chat-controls-status">
          <span id="memory-label" class="memory-label" title="Statut memoire">Memoire OFF</span>
          <span id="memory-counters" class="memory-counters">STM 0 | LTM 0</span>
        </div>
        <div class="chat-controls-actions">
          <button type="button" id="memory-analyze" class="button" title="Analyser / consolider la memoire">Analyser</button>
          <button type="button" id="memory-clear" class="button" title="Effacer la memoire de session">Clear</button>
        </div>
        <div class="chat-controls-actions">
          <button type="button" id="memory-open-center" class="button button-primary" title="Ouvrir le centre memoire">Centre memoire</button>
        </div>
      </div>
      <div class="chat-controls-card">
        <div id="chat-metrics" class="chat-metrics">
          <span id="metric-ttfb">TTFB: - ms</span>
          <span id="metric-fallbacks">Fallback REST: 0</span>
        </div>
      </div>
    `;
  }

  _bindControlPanelEvents(panel) {
    panel.querySelector('#memory-analyze')?.addEventListener('click', () => this.eventBus.emit('memory:tend'));
    panel.querySelector('#memory-clear')?.addEventListener('click', () => this.eventBus.emit('memory:clear'));
    panel.querySelector('#memory-open-center')?.addEventListener('click', () => this.eventBus.emit('memory:center:open'));
  }

  _updateControlPanelState() {
    const panel = this._ensureControlPanel();
    if (!panel) return;

    const lastAnalysis = this.state.lastAnalysis || {};
    const memoryOn = !!(this.state.memoryBannerAt || lastAnalysis.status === 'completed');
    const running = lastAnalysis.status === 'running';
    const dot = panel.querySelector('#memory-dot');
    const lbl = panel.querySelector('#memory-label');
    const cnt = panel.querySelector('#memory-counters');

    if (dot) {
      dot.classList.toggle('is-on', memoryOn);
      dot.style.background = '';
      dot.style.boxShadow = '';
    }
    if (lbl) {
      lbl.textContent = memoryOn ? 'Memoire ON' : 'Memoire OFF';
      lbl.classList.toggle('is-off', !memoryOn);
    }

    const mem = this.state.memoryStats || {};
    if (cnt) {
      const stmTxt = mem.has_stm ? 'STM V' : 'STM 0';
      const ltmTxt = `LTM ${Number(mem.ltm_items || 0)}`;
      const inj = mem.injected ? ' | inj' : '';
      cnt.textContent = `${stmTxt} | ${ltmTxt}${inj}`;
    }

    const met = this.state.metrics || {};
    const metricsHost = panel.querySelector('#chat-metrics');
    const ttfbEl = metricsHost?.querySelector('#metric-ttfb');
    const fbEl = metricsHost?.querySelector('#metric-fallbacks');
    if (ttfbEl) ttfbEl.textContent = `TTFB: ${Number.isFinite(met.last_ttfb_ms) ? met.last_ttfb_ms : 0} ms`;
    if (fbEl) fbEl.textContent = `Fallback REST: ${met.rest_fallback_count || 0}`;
    this.eventBus.emit?.('memory:center:state', {
      memoryOn,
      memoryStats: mem,
      exportAgents: this.state.exportAgents,
      exportFormat: this.state.exportFormat
    });
  }

  async _onDocumentsChanged(container, payload) {
    try {
      let docs = Array.isArray(payload.items) ? payload.items : null;
      if (!docs) docs = await this._refetchDocuments();
      if (!Array.isArray(docs)) {
        this._renderSources(container.querySelector('#rag-sources'), []);
        return;
      }
      const ids = new Set(docs.map((d) => d?.id || d?.document_id || d?._id).filter(Boolean));
      const names = new Set(docs.map((d) => (d?.filename || d?.original_filename || d?.name || '').toString()).filter(Boolean));
      const meta = this.state.lastMessageMeta || {};
      const src = Array.isArray(meta.sources) ? meta.sources : [];
      const filtered = src.filter((s) => {
        const sid = (s.document_id || '').toString();
        const sname = (s.filename || '').toString();
        return (sid && ids.has(sid)) || (sname && names.has(sname));
      });
      if (filtered.length !== src.length) {
        this.state.lastMessageMeta = { ...meta, sources: filtered };
      }
      this._renderSources(container.querySelector('#rag-sources'), filtered);
    } catch (e) {
      console.error('[ChatUI] _onDocumentsChanged failed:', e);
      this._renderSources(container.querySelector('#rag-sources'), []);
    }
  }

  async _refetchDocuments() {
    try {
      const headers = {};
      const tokenGetter =
        (window?.EmergenceAuth && typeof window.EmergenceAuth.getToken === 'function' && window.EmergenceAuth.getToken) ||
        (this.stateManager && typeof this.stateManager.getAuthToken === 'function' && this.stateManager.getAuthToken) ||
        null;
      if (tokenGetter) {
        const token = await tokenGetter();
        if (token) headers.Authorization = `Bearer ${token}`;
      }
      const res = await fetch('/api/documents', { headers });
      if (!res.ok) return null;
      const data = await res.json();
      return Array.isArray(data) ? data : (Array.isArray(data?.items) ? data.items : null);
    } catch {
      return null;
    }
  }

  _autoGrow(el) {
    if (!el) return;
    const max = Math.floor(window.innerHeight * 0.45);
    const min = 52;
    el.style.height = 'auto';
    const next = Math.min(Math.max(el.scrollHeight, min), max);
    el.style.height = `${next}px`;
    el.style.overflowY = el.scrollHeight > max ? 'auto' : 'hidden';
  }

  _renderMessages(host, messages) {
    if (!host) return;
    const html = (messages || []).map((m) => this._messageHTML(m)).join('');
    host.innerHTML = html || '<div class="placeholder">Commencez � discuter.</div>';
    host.scrollTo(0, 1e9);
  }

  _renderSources(host, sources) {
    if (!host) return;
    const items = Array.isArray(sources) ? sources : [];
    if (!items.length) {
      host.style.display = 'none';
      host.innerHTML = '';
      return;
    }

    const chips = items.map((s, i) => {
      const filename = (s.filename || 'Document').toString();
      const page = (Number(s.page) || 0) > 0 ? ` - p.${Number(s.page)}` : '';
      const label = `${filename}${page}`;
      const tip = (s.excerpt || '').toString().slice(0, 300);
      const docId = (s.document_id || `doc-${i}`).toString();
      return `
        <button
          type="button"
          class="chip chip-source rag-source-chip"
          data-doc-id="${this._escapeHTML(docId)}"
          data-filename="${this._escapeHTML(filename)}"
          data-page="${Number(s.page) || ''}"
          data-excerpt="${this._escapeHTML(tip)}"
          title="${this._escapeHTML(tip.replace(/\n/g, ' '))}"
        >
          <svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true">
            <path d="M4 4h10l6 6v10H4z" fill="none" stroke="currentColor" stroke-width="1.5"></path>
            <path d="M14 4v6h6" fill="none" stroke="currentColor" stroke-width="1.5"></path>
          </svg>
          <span>${this._escapeHTML(label)}</span>
        </button>`;
    }).join('');

    host.innerHTML = `
      <div class="rag-sources-wrap">
        <span class="rag-sources-label">Sources :</span>
        ${chips}
      </div>
    `;
    host.style.display = 'block';
  }

  _messageHTML(m) {
    const side = m.role === 'user' ? 'user' : 'assistant';
    const agentId = side === 'assistant' ? (m.agent_id || m.agent || 'nexus') : '';
    const agentInfo = side === 'assistant' ? (AGENTS[agentId] || {}) : {};
    const displayName = side === 'user'
      ? 'FG'
      : (agentInfo.label || agentInfo.name || this._humanizeAgentId(agentId) || 'Assistant');

    const raw = this._toPlainText(m.content);
    const content = this._escapeHTML(raw).replace(/\n/g, '<br/>');
    const cursor = m.isStreaming ? '<span class="blinking-cursor">?</span>' : '';
    const timestamp = this._formatTimestamp(m.created_at ?? m.timestamp ?? m.time ?? m.datetime ?? m.date);

    const classes = ['message', side, `message--${side}`];
    if (side === 'assistant') {
      if (agentId) {
        classes.push(agentId);
        classes.push(`message--${agentId}`);
      }
      if (agentInfo.cssClass) classes.push(agentInfo.cssClass);
    }

    const className = classes
      .filter(Boolean)
      .filter((value, index, arr) => arr.indexOf(value) === index)
      .join(' ');

    return `
      <div class="${className}">
        <div class="message-bubble">
          <div class="message-meta">
            <span class="sender-name">${this._escapeHTML(displayName)}</span>
            <time class="message-time" datetime="${timestamp.iso}">${this._escapeHTML(timestamp.display)}</time>
          </div>
          <div class="message-text">${content}${cursor}</div>
        </div>
      </div>`;
  }
  _agentTabsHTML(activeId) {
    const ids = Object.keys(AGENTS);
    return `
      <div class="tabs-container">
        ${ids.map((id) => {
          const agent = AGENTS[id] || {};
          const isActive = id === activeId;
          const icon = agent.icon ? `<span class="tab-icon" aria-hidden="true">${this._escapeHTML(agent.icon)}</span>` : '';
          const label = agent.label || agent.name || this._humanizeAgentId(id) || id;
          return `
            <button
              type="button"
              class="button-tab agent--${id} ${isActive ? 'active' : ''}"
              data-agent-id="${id}"
              aria-pressed="${isActive}"
            >
              ${icon}
              <span class="tab-label">${this._escapeHTML(label)}</span>
            </button>
          `;
        }).join('')}
      </div>`;
  }

  _setActiveAgentTab(container, agentId) {
    container.querySelectorAll('.button-tab').forEach((b) => b.classList.remove('active'));
    container.querySelector(`.button-tab[data-agent-id="${agentId}"]`)?.classList.add('active');
  }

  _asArray(x) {
    return Array.isArray(x) ? x : (x ? [x] : []);
  }

  _normalizeMessage(m) {
    if (!m) return { role: 'assistant', content: '' };
    if (typeof m === 'string') return { role: 'assistant', content: m };
    const timestamp =
      m.created_at ?? m.timestamp ?? m.time ?? m.datetime ?? m.date ?? m.createdAt ?? (m.meta && m.meta.timestamp) ?? null;
    return {
      role: m.role || 'assistant',
      content: m.content ?? m.text ?? '',
      isStreaming: !!m.isStreaming,
      agent_id: m.agent_id || m.agent,
      id: m.id ?? null,
      created_at: timestamp,
      timestamp
    };
  }

  _toPlainText(val) {
    if (val == null) return '';
    if (typeof val === 'string') return val;
    if (Array.isArray(val)) return val.map((v) => this._toPlainText(v)).join('');
    if (typeof val === 'object') {
      if ('text' in val) return this._toPlainText(val.text);
      if ('content' in val) return this._toPlainText(val.content);
      if ('message' in val) return this._toPlainText(val.message);
      try { return JSON.stringify(val); } catch { return String(val); }
    }
    return String(val);
  }

  _escapeHTML(s) {
    return String(s).replace(/[&<>"']/g, (c) => {
      switch (c) {
        case '&': return '&amp;';
        case '<': return '&lt;';
        case '>': return '&gt;';
        case '"': return '&quot;';
        default: return '&#39;';
      }
    });
  }

  _humanizeAgentId(id) {
    if (!id) return '';
    const base = String(id).replace(/[_-]+/g, ' ').trim();
    if (!base) return '';
    return base
      .split(/\s+/)
      .filter(Boolean)
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase())
      .join(' ');
  }

  _coerceDate(input) {
    if (!input) return null;
    if (input instanceof Date && !Number.isNaN(input.getTime())) return input;
    if (typeof input === 'string') {
      const trimmed = input.trim();
      if (!trimmed) return null;
      const parsed = Date.parse(trimmed);
      if (!Number.isNaN(parsed)) {
        const d = new Date(parsed);
        if (!Number.isNaN(d.getTime())) return d;
      }
    }
    const num = Number(input);
    if (!Number.isFinite(num)) return null;
    const ms = num > 1e12 ? num : (num > 1e9 ? num * 1000 : num);
    if (!Number.isFinite(ms)) return null;
    const d = new Date(ms);
    return Number.isNaN(d.getTime()) ? null : d;
  }

  _formatTimestamp(input) {
    const date = this._coerceDate(input) || new Date();
    const datePart = date.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric' });
    const timePart = date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
    return { display: `${datePart} - ${timePart}`, iso: date.toISOString() };
  }
}





