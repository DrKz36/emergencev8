from pathlib import Path
path = Path("src/frontend/features/chat/chat-ui.js")
text = path.read_text(encoding="utf-8")

def replace_block(start_token, end_token, new_block):
    global text
    start = text.index(start_token)
    end = text.index(end_token, start)
    text = text[:start] + new_block + text[end:]

render_block = '''  render(container, chatState = {}) {
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
            <div class="chat-entry-row">
              <div class="rag-toggle" data-role="rag-toggle">
                <button
                  type="button"
                  id="rag-power"
                  class="rag-power toggle-metal"
                  role="switch"
                  aria-checked="${String(!!this.state.ragEnabled)}"
                  title="Activer/Desactiver RAG">
                  <svg class="power-icon" viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
                    <path d="M12 3v9" stroke="currentColor" stroke-width="2" stroke-linecap="round" fill="none"></path>
                    <path d="M5.5 7a 8 8 0 1 0 13 0" stroke="currentColor" stroke-width="2" stroke-linecap="round" fill="none"></path>
                  </svg>
                </button>
                <span id="rag-label" class="rag-label">${this.state.ragEnabled ? 'RAG actif' : 'RAG inactif'}</span>
              </div>

              <div class="input-wrapper chat-input-shell">
                <textarea id="chat-input" class="chat-input" rows="2" placeholder="Ecris ton message..."></textarea>
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
'''

update_block = '''  update(container, chatState = {}) {
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
'''

bind_block = '''  _bindEvents(container) {
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
'''

replace_block('  render(container, chatState = {}) {', '  update(container, chatState = {}) {', render_block)
replace_block('  update(container, chatState = {}) {', '  _bindEvents(container) {', update_block)
replace_block('  _bindEvents(container) {', '  async _onDocumentsChanged', bind_block)

extra_methods = '''  _ensureControlPanel() {
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
          <span id="memory-counters" class="memory-counters"></span>
        </div>
        <div class="chat-controls-actions">
          <button type="button" id="memory-analyze" class="button" title="Analyser / consolider la memoire">Analyser</button>
          <button type="button" id="memory-clear" class="button" title="Effacer la memoire de session">Clear</button>
        </div>
      </div>
      <div class="chat-controls-card">
        <div class="chat-controls-actions">
          <button type="button" id="chat-export" class="button">Exporter</button>
          <button type="button" id="chat-clear" class="button">Effacer</button>
        </div>
        <div id="chat-metrics" class="chat-metrics">
          <span id="metric-ttfb">TTFB: - ms</span>
          <span aria-hidden="true">-</span>
          <span id="metric-fallbacks">Fallback REST: 0</span>
        </div>
      </div>
    `;
  }

  _bindControlPanelEvents(panel) {
    panel.querySelector('#memory-analyze')?.addEventListener('click', () => this.eventBus.emit('memory:tend'));
    panel.querySelector('#memory-clear')?.addEventListener('click', () => this.eventBus.emit('memory:clear'));
    panel.querySelector('#chat-export')?.addEventListener('click', () => this.eventBus.emit(EVENTS.CHAT_EXPORT, null));
    panel.querySelector('#chat-clear')?.addEventListener('click', () => this.eventBus.emit(EVENTS.CHAT_CLEAR, null));
  }

  _updateControlPanelState() {
    const panel = this._ensureControlPanel();
    if (!panel) return;

    const memoryOn = !!(this.state.memoryBannerAt || (this.state.lastAnalysis && this.state.lastAnalysis.status === 'completed'));
    const dot = panel.querySelector('#memory-dot');
    const lbl = panel.querySelector('#memory-label');
    const cnt = panel.querySelector('#memory-counters');

    if (dot) dot.style.background = memoryOn ? '#22c55e' : '#6b7280';
    if (lbl) lbl.textContent = memoryOn ? 'Memoire ON' : 'Memoire OFF';

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
  }

'''

insert_pos = text.index('  async _onDocumentsChanged')
text = text[:insert_pos] + extra_methods + text[insert_pos:]

path.write_text(text, encoding='utf-8')
