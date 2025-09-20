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
      selectedDocIds: [],
      selectedDocs: [],
      exportAgents: Object.keys(AGENTS),
      exportFormat: 'markdown',
      modelInfo: null,
      lastMessageMeta: null,
      areSourcesExpanded: false
    };
    this._panelHandlersBound = false;
    this.disableSidebarPanel = true;
    this._sourcesCache = [];
    this._decoderEl = null;
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
            <div class="chat-actions" role="group" aria-label="Actions de conversation">
              <button type="button" class="chat-action-btn" data-role="chat-clear" title="Effacer les messages de l'agent actif" data-label="Effacer les messages de l'agent actif" data-title="Effacer les messages de l'agent actif">
                <span class="sr-only">Effacer les messages de l'agent actif</span>
                <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" focusable="false">
                  <path d="M9 3h6l1 2h4v2H4V5h4l1-2Zm1 6h2v8h-2V9Zm6 0h-2v8h2V9ZM8 9H6v8h2V9Z" fill="currentColor"></path>
                </svg>
              </button>
              <button type="button" class="chat-action-btn" data-role="chat-export" title="Exporter toute la conversation" data-label="Exporter toute la conversation" data-title="Exporter toute la conversation">
                <span class="sr-only">Exporter toute la conversation</span>
                <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" focusable="false">
                  <path d="M12 3v12.17l3.59-3.58L17 13l-5 5-5-5 1.41-1.41L11 15.17V3h1Zm-7 14h14v2H5v-2Z" fill="currentColor"></path>
                </svg>
              </button>
            </div>
          </div>
        </div>
        <div class="chat-body">
          <div class="messages" id="chat-messages"></div>
          <div id="rag-sources" class="rag-sources"></div>
        </div>
        <div class="chat-footer">
          <form id="chat-form" class="chat-form" autocomplete="off">
            <div class="chat-composer" data-role="chat-composer">
              <div class="chat-input-shell" data-role="chat-input-shell">
                <div class="chat-rag-toggle" data-role="rag-toggle">
                  <button
                    type="button"
                    id="rag-power"
                    class="chat-rag-toggle__button${this.state.ragEnabled ? ' is-on' : ''}"
                    role="switch"
                    aria-checked="${String(!!this.state.ragEnabled)}"
                    aria-label="${this.state.ragEnabled ? 'RAG active' : 'RAG inactive'}"
                    title="Basculer le RAG">
                    <span class="chat-rag-toggle__icon" aria-hidden="true">
                      <svg viewBox="0 0 24 24" width="14" height="14" focusable="false">
                        <path d="M12 2v10" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"></path>
                        <path d="M7.5 4.6A8 8 0 1012 20a8 8 0 004.5-15.4" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"></path>
                      </svg>
                    </span>
                    <span class="chat-rag-toggle__label" aria-hidden="true">RAG</span>
                    <span id="rag-status" class="chat-rag-toggle__state" aria-hidden="true">${this.state.ragEnabled ? 'Actif' : 'Veille'}</span>
                    <span class="sr-only" id="rag-status-text">${this.state.ragEnabled ? 'RAG actif' : 'RAG inactif'}</span>
                  </button>
                </div>
                <div class="chat-doc-chips" id="chat-doc-chips" aria-live="polite"></div>

                <textarea id="chat-input" class="chat-input" rows="1" placeholder="Ecris ton message..." aria-label="Message"></textarea>
                <button type="submit" id="chat-send" class="chat-send-button" title="Envoyer" aria-label="Envoyer">
                  <span class="sr-only">Envoyer</span>
                  <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" focusable="false">
                    <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" fill="currentColor"></path>
                  </svg>
                </button>
              </div>
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
    const previousMeta = this.state.lastMessageMeta;
    this.state = { ...this.state, ...chatState };
    if (chatState && chatState.lastMessageMeta && chatState.lastMessageMeta !== previousMeta) {
      this.state.areSourcesExpanded = false;
    }
    this._ensureControlPanel();

    const ragBtn = container.querySelector('#rag-power');
    const ragEnabled = !!this.state.ragEnabled;
    if (ragBtn) {
      ragBtn.setAttribute('aria-checked', String(ragEnabled));
      ragBtn.setAttribute('aria-label', ragEnabled ? 'RAG active' : 'RAG inactive');
      ragBtn.title = ragEnabled ? 'Desactiver le RAG' : 'Activer le RAG';
      ragBtn.classList.toggle('is-on', ragEnabled);
    }
    const ragStatus = container.querySelector('#rag-status');
    if (ragStatus) ragStatus.textContent = ragEnabled ? 'Actif' : 'Veille';
    const ragStatusText = container.querySelector('#rag-status-text');
    if (ragStatusText) ragStatusText.textContent = ragEnabled ? 'RAG actif' : 'RAG inactif';

    this._renderDocChips(container.querySelector('#chat-doc-chips'), this.state.selectedDocs, this.state.selectedDocIds, ragEnabled);
    this._setActiveAgentTab(container, this.state.currentAgentId);

    const rawMessages = this.state.messages?.[this.state.currentAgentId];
    const list = this._asArray(rawMessages).map((m) => this._normalizeMessage(m));
    this._renderMessages(container.querySelector('#chat-messages'), list);

    const clearEl = container.querySelector('[data-role="chat-clear"]');
    if (clearEl) {
      if (list.length) {
        clearEl.removeAttribute('disabled');
        clearEl.classList.remove('is-disabled');
      } else {
        clearEl.setAttribute('disabled', 'disabled');
        clearEl.classList.add('is-disabled');
      }
    }
    const exportEl = container.querySelector('[data-role="chat-export"]');
    if (exportEl) {
      const buckets = this.state.messages && typeof this.state.messages === 'object' ? Object.values(this.state.messages) : [];
      const hasAny = buckets.some((bucket) => Array.isArray(bucket) && bucket.length > 0);
      if (hasAny) {
        exportEl.removeAttribute('disabled');
        exportEl.classList.remove('is-disabled');
      } else {
        exportEl.setAttribute('disabled', 'disabled');
        exportEl.classList.add('is-disabled');
      }
    }

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
    const sendBtn = container.querySelector('#chat-send');
    const clearButton = container.querySelector('[data-role="chat-clear"]');
    const exportButton = container.querySelector('[data-role="chat-export"]');
    const messagesHost = container.querySelector('#chat-messages');
    const sourcesHost = container.querySelector('#rag-sources');
    this._ensureControlPanel();
    this._updateControlPanelState();

    const autosize = () => this._autoGrow(input);
    setTimeout(autosize, 0);
    input?.addEventListener('input', autosize);
    window.addEventListener('resize', autosize);

    form?.addEventListener('submit', (e) => {
      e.preventDefault();
      const textValue = (input?.value || '').trim();
      if (!textValue) return;
      this.eventBus.emit(EVENTS.CHAT_SEND, { text: textValue, agent: 'user' });
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

    clearButton?.addEventListener('click', () => {
      this.eventBus.emit(EVENTS.CHAT_CLEAR);
    });

    exportButton?.addEventListener('click', () => {
      this.eventBus.emit(EVENTS.CHAT_EXPORT);
    });

    const toggleRag = () => {
      if (!ragBtn) return;
      const on = ragBtn.getAttribute('aria-checked') === 'true';
      const next = !on;
      ragBtn.setAttribute('aria-checked', String(next));
      ragBtn.setAttribute('aria-label', next ? 'RAG active' : 'RAG inactive');
      ragBtn.title = next ? 'Desactiver le RAG' : 'Activer le RAG';
      ragBtn.classList.toggle('is-on', next);
      const ragStatus = container.querySelector('#rag-status');
      if (ragStatus) ragStatus.textContent = next ? 'Actif' : 'Veille';
      const ragStatusText = container.querySelector('#rag-status-text');
      if (ragStatusText) ragStatusText.textContent = next ? 'RAG actif' : 'RAG inactif';
      this.eventBus.emit(EVENTS.CHAT_RAG_TOGGLED, { enabled: next });
    };
    ragBtn?.addEventListener('click', toggleRag);

    const docChipHost = container.querySelector('#chat-doc-chips');
    docChipHost?.addEventListener('click', (e) => {
      const target = e.target;
      if (!target || typeof target.closest !== 'function') return;
      const removeBtn = target.closest('[data-doc-remove]');
      if (removeBtn) {
        const docId = removeBtn.getAttribute('data-doc-id');
        if (docId) {
          const evt = EVENTS?.DOCUMENTS_CMD_DESELECT || 'documents:cmd:deselect';
          try { this.eventBus.emit(evt, { id: docId }); } catch {}
        }
        e.preventDefault();
        return;
      }
      const clearBtn = target.closest('[data-doc-clear]');
      if (clearBtn) {
        const ids = Array.isArray(this.state?.selectedDocIds) ? this.state.selectedDocIds : [];
        if (ids.length) {
          const evt = EVENTS?.DOCUMENTS_CMD_DESELECT || 'documents:cmd:deselect';
          for (const id of ids) {
            if (id || id === 0) {
              try { this.eventBus.emit(evt, { id }); } catch {}
            }
          }
        }
        e.preventDefault();
      }
    });

    container.querySelector('.agent-selector')?.addEventListener('click', (e) => {
      const btn = e.target.closest('button[data-agent-id]');
      if (!btn) return;
      const agentId = btn.getAttribute('data-agent-id');
      this.eventBus.emit(EVENTS.CHAT_AGENT_SELECTED, agentId);
      this._setActiveAgentTab(container, agentId);
    });

    if (sourcesHost) {
      sourcesHost.addEventListener('click', (e) => {
        const toggleBtn = e.target.closest('[data-role="rag-sources-toggle"]');
        if (toggleBtn) {
          const next = toggleBtn.getAttribute('aria-expanded') !== 'true';
          this.state.areSourcesExpanded = next;
          this._renderSources(sourcesHost, this._sourcesCache);
          e.preventDefault();
          return;
        }
        const chip = e.target.closest('button[data-doc-id]');
        if (!chip) return;
        if (!this.state.areSourcesExpanded) {
          this.state.areSourcesExpanded = true;
          this._renderSources(sourcesHost, this._sourcesCache);
          return;
        }
        const info = {
          document_id: chip.getAttribute('data-doc-id'),
          filename: chip.getAttribute('data-filename'),
          page: Number(chip.getAttribute('data-page') || '0') || null,
          excerpt: chip.getAttribute('data-excerpt') || ''
        };
        this.eventBus.emit('rag:source:click', info);
      });
    }

    if (messagesHost) {
      messagesHost.addEventListener('click', async (event) => {
        const button = event.target.closest('[data-role="copy-message"]');
        if (!button || button.hasAttribute('disabled')) return;
        const raw = button.getAttribute('data-message') || '';
        const textValue = this._decodeHTML(raw).replace(/\r?\n/g, '\n').trimEnd();
        if (!textValue) {
          this._flashCopyState(button, false);
          return;
        }
        const ok = await this._copyToClipboard(textValue);
        this._flashCopyState(button, ok);
      });
    }

    try {
      const off = this.eventBus?.on?.('documents:changed', async (payload = {}) => {
        await this._onDocumentsChanged(container, payload);
      });
      if (typeof off === 'function') this._offDocumentsChanged = off;
    } catch {}
  }

  _ensureControlPanel() {
    try {
      if (this.disableSidebarPanel) {
        if (this._controlPanel?.parentElement) {
          this._controlPanel.remove();
        }
        this._controlPanel = null;
        this._panelHandlersBound = false;
        return null;
      }
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
    if (!panel) return;
    panel.querySelector('#memory-analyze')?.addEventListener('click', () => this.eventBus.emit('memory:tend'));
    panel.querySelector('#memory-clear')?.addEventListener('click', () => this.eventBus.emit('memory:clear'));
    panel.querySelector('#memory-open-center')?.addEventListener('click', () => this.eventBus.emit('memory:center:open'));
  }

  _updateControlPanelState() {
    const panel = this._ensureControlPanel();
    const lastAnalysis = this.state.lastAnalysis || {};
    const memoryOn = !!(this.state.memoryBannerAt || lastAnalysis.status === 'completed');
    const mem = this.state.memoryStats || {};

    if (panel) {
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
    }

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
    host.innerHTML = html || '<div class="placeholder">Commencez à discuter.</div>';
    host.scrollTo(0, 1e9);
  }

  _renderDocChips(host, docs, docIds, ragEnabled) {
    if (!host) return;
    const ids = Array.isArray(docIds) ? docIds.map((id) => String(id)) : [];
    const map = new Map();
    if (Array.isArray(docs)) {
      for (const item of docs) {
        const id = String((item?.id ?? item?.document_id ?? item?.doc_id ?? '') || '').trim();
        if (!id || map.has(id)) continue;
        let name = item?.name ?? item?.filename ?? item?.title ?? '';
        name = String(name ?? '').trim();
        if (!name) name = 'Document ' + id;
        const statusRaw = item?.status;
        const status = statusRaw == null ? 'ready' : (String(statusRaw).toLowerCase() || 'ready');
        map.set(id, { id, name, status });
      }
    }
    const order = ids.length ? ids : Array.from(map.keys());
    if (!order.length) {
      host.innerHTML = '';
      host.setAttribute('hidden', 'hidden');
      host.removeAttribute('data-count');
      host.classList.remove('is-disabled');
      return;
    }
    host.removeAttribute('hidden');
    host.dataset.count = String(order.length);
    host.classList.toggle('is-disabled', !ragEnabled);
    const label = ragEnabled ? 'Documents actifs' : 'Documents sélectionnés (RAG off)';
    const chips = order.map((rawId) => {
      const id = String(rawId).trim();
      const info = map.get(id) || { id, name: 'Document ' + id, status: 'ready' };
      const safeId = this._escapeHTML(id);
      const safeName = this._escapeHTML(info.name);
      const status = (info.status || '').toString().toLowerCase();
      const safeStatus = this._escapeHTML(status);
      const statusSpan = status && status !== 'ready'
        ? '<span class="chat-doc-chip__status chat-doc-chip__status--' + safeStatus + '">' + safeStatus + '</span>'
        : '';
      return [
        '<button type="button" class="chat-doc-chip" data-doc-remove data-doc-id="' + safeId + '" title="Retirer ' + safeName + '">',
        '  <span class="chat-doc-chip__icon" aria-hidden="true"></span>',
        '  <span class="chat-doc-chip__label">' + safeName + '</span>',
        statusSpan ? '  ' + statusSpan : '',
        '  <span class="chat-doc-chip__close" aria-hidden="true">&times;</span>',
        '  <span class="sr-only">Retirer ' + safeName + '</span>',
        '</button>'
      ].filter(Boolean).join('');
    }).join('');
    host.innerHTML =
      '<div class="chat-doc-chips__header">' +
        '<span class="chat-doc-chips__title">' + this._escapeHTML(label) + '</span>' +
        '<button type="button" class="chat-doc-chips__clear" data-doc-clear' + (order.length ? '' : ' disabled') + '>Tout retirer</button>' +
      '</div>' +
      '<div class="chat-doc-chips__list">' + chips + '</div>';
  }

  _renderSources(host, sources) {
    if (!host) return;
    const items = Array.isArray(sources) ? sources.filter(Boolean) : [];
    this._sourcesCache = items;
    if (!items.length) {
      host.style.display = 'none';
      host.innerHTML = '';
      host.removeAttribute('data-count');
      host.removeAttribute('data-open');
      this.state.areSourcesExpanded = false;
      return;
    }

    const countLabel = items.length > 1 ? `${items.length} references` : '1 reference';
    const isOpen = !!this.state.areSourcesExpanded;
    const list = items.map((s, index) => {
      const filename = (s?.filename || 'Document').toString();
      const pageNumber = Number(s?.page) || 0;
      const pageLabel = pageNumber > 0 ? ` (p.${pageNumber})` : '';
      const displayName = `${filename}${pageLabel}`;
      const rawExcerpt = (s?.excerpt || '').toString().replace(/\s+/g, ' ').trim();
      const excerptText = rawExcerpt ? rawExcerpt.slice(0, 240) : '';
      const docId = (s?.document_id || `doc-${index}`).toString();
      const tooltip = (excerptText || displayName).replace(/\n/g, ' ');
      return `
        <li class="rag-source-item">
          <button
            type="button"
            class="rag-source-button"
            data-doc-id="${this._escapeHTML(docId)}"
            data-filename="${this._escapeHTML(filename)}"
            data-page="${pageNumber || ''}"
            data-excerpt="${this._escapeHTML(rawExcerpt)}"
            title="${this._escapeHTML(tooltip)}"
          >
            <span class="rag-source-line">
              <span class="rag-source-index">${index + 1}</span>
              <span class="rag-source-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" width="14" height="14">
                  <path d="M7 3h7l5 5v13H7z" fill="none" stroke="currentColor" stroke-width="1.4"></path>
                  <path d="M14 3v5h5" fill="none" stroke="currentColor" stroke-width="1.4"></path>
                </svg>
              </span>
              <span class="rag-source-name">${this._escapeHTML(displayName)}</span>
            </span>
            ${excerptText ? `<span class="rag-source-excerpt">${this._escapeHTML(excerptText)}</span>` : ''}
          </button>
        </li>`;
    }).join('');

    host.innerHTML = `
      <section class="rag-sources-panel ${isOpen ? 'is-open' : 'is-collapsed'}">
        <header class="rag-sources-header">
          <div class="rag-sources-summary">
            <span class="rag-sources-label">Sources</span>
            <span class="rag-sources-count">${countLabel}</span>
          </div>
          <button
            type="button"
            class="rag-sources-toggle"
            data-role="rag-sources-toggle"
            aria-expanded="${isOpen}"
            aria-controls="rag-sources-list"
            title="${isOpen ? 'Reduire les sources' : 'Afficher les sources'}"
          >
            <span class="rag-sources-toggle-icon" aria-hidden="true"></span>
            <span class="sr-only">${isOpen ? 'Reduire les sources' : 'Afficher les sources'}</span>
          </button>
        </header>
        <ul id="rag-sources-list" class="rag-source-list"${isOpen ? '' : ' hidden'} role="list">
          ${list}
        </ul>
      </section>
    `;
    host.style.display = 'block';
    host.dataset.count = String(items.length);
    host.dataset.open = isOpen ? 'true' : 'false';
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
    const cursor = m.isStreaming ? '<span class="blinking-cursor">|</span>' : '';
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

    const encodedRaw = this._encodeForAttribute(raw);
    const copyDisabled = !!m.isStreaming;
    const copyLabel = 'Copier le message';
    const copyTitle = copyDisabled ? 'Message en cours' : copyLabel;
    const srCopyText = copyDisabled ? 'Copie indisponible pendant la generation' : copyLabel;
    const copyClass = `message-action message-action-copy${copyDisabled ? ' is-disabled' : ''}`;

    return `
      <div class="${className}">
        <div class="message-bubble">
          <div class="message-header">
            <div class="message-meta">
              <span class="sender-name">${this._escapeHTML(displayName)}</span>
              <time class="message-time" datetime="${timestamp.iso}">${this._escapeHTML(timestamp.display)}</time>
            </div>
            <div class="message-actions">
              <button
                type="button"
                class="${copyClass}"
                data-role="copy-message"
                data-message="${encodedRaw}"
                data-label="${copyLabel}"
                data-title="${copyTitle}"
                title="${copyTitle}"
                aria-label="${copyTitle}"${copyDisabled ? ' disabled aria-disabled="true"' : ''}
              >
                <span class="sr-only">${srCopyText}</span>
                <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true" focusable="false">
                  <path d="M9 9V5a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-4" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"></path>
                  <rect x="3" y="9" width="12" height="12" rx="2" ry="2" fill="none" stroke="currentColor" stroke-width="1.5"></rect>
                </svg>
              </button>
            </div>
          </div>
          <div class="message-text" data-raw="${encodedRaw}">${content}${cursor}</div>
        </div>
      </div>`;
  }
  _agentTabsHTML(activeId) {
    const baseIds = Object.keys(AGENTS);
    const seen = new Set(baseIds);
    if (this.state && this.state.messages && typeof this.state.messages === 'object') {
      Object.keys(this.state.messages).forEach((id) => {
        if (!id) return;
        seen.add(String(id).trim().toLowerCase());
      });
    }
    if (this.state && this.state.currentAgentId) {
      seen.add(String(this.state.currentAgentId).trim().toLowerCase());
    }
    const ids = baseIds.concat(Array.from(seen).filter((id) => !baseIds.includes(id)));
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

  _encodeForAttribute(value) {
    const safe = this._escapeHTML(String(value ?? ''));
    return safe.replace(/\r?\n/g, '&#10;');
  }

  _decodeHTML(value) {
    if (value == null) return '';
    if (!this._decoderEl) {
      this._decoderEl = document.createElement('textarea');
    }
    this._decoderEl.innerHTML = value;
    return this._decoderEl.value;
  }

  async _copyToClipboard(text) {
    try {
      if (navigator?.clipboard?.writeText) {
        await navigator.clipboard.writeText(text);
      } else {
        const area = document.createElement('textarea');
        area.value = text;
        area.setAttribute('readonly', '');
        area.style.position = 'fixed';
        area.style.top = '-1000px';
        area.style.opacity = '0';
        document.body.appendChild(area);
        area.focus();
        area.select();
        const ok = document.execCommand('copy');
        area.remove();
        if (!ok) throw new Error('execCommand returned false');
      }
      return true;
    } catch (error) {
      console.error('[ChatUI] copy failed', error);
      return false;
    }
  }

  _flashCopyState(button, success) {
    if (!button) return;
    const baseLabel = button.getAttribute('data-label') || 'Copier le message';
    const baseTitle = button.getAttribute('data-title') || baseLabel;
    if (button._copyTimer) {
      clearTimeout(button._copyTimer);
      button._copyTimer = null;
    }
    if (success) {
      button.classList.add('is-copied');
      button.classList.remove('is-error');
      button.setAttribute('data-copied', 'true');
      button.removeAttribute('data-copy-error');
      button.setAttribute('aria-label', 'Message copie');
      button.title = 'Message copie';
    } else {
      button.classList.remove('is-copied');
      button.classList.add('is-error');
      button.setAttribute('data-copy-error', 'true');
      button.removeAttribute('data-copied');
      button.setAttribute('aria-label', 'Copie impossible');
      button.title = 'Copie impossible';
    }
    button._copyTimer = setTimeout(() => {
      try {
        button.classList.remove('is-copied', 'is-error');
        button.removeAttribute('data-copied');
        button.removeAttribute('data-copy-error');
        button.setAttribute('aria-label', baseLabel);
        button.title = baseTitle;
        button._copyTimer = null;
      } catch {}
    }, 1500);
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





