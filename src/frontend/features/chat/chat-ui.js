// src/frontend/features/chat/chat-ui.js
/**
 * V27.2 — + Badge modèle/fallback (lecture chat.modelInfo + chat.lastMessageMeta)
 *        + Bouton "Clear" mémoire
 *        + Compteurs STM/LTM + TTFB déjà affichés
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
      // champs depuis chat.state
      memoryBannerAt: null,
      lastAnalysis: null,
      metrics: { send_count: 0, ws_start_count: 0, last_ttfb_ms: 0, rest_fallback_count: 0, last_fallback_at: null },
      memoryStats: { has_stm: false, ltm_items: 0, injected: false },
      modelInfo: null,
      lastMessageMeta: null
    };
    console.log('✅ ChatUI V27.2 (badge modèle + clear mémoire) chargé.');
  }

  render(container, chatState = {}) {
    if (!container) return;
    this.state = { ...this.state, ...chatState };

    const agentTabs = this._agentTabsHTML(this.state.currentAgentId);

    container.innerHTML = `
      <div class="chat-container card">
        <div class="chat-header card-header" style="display:flex;align-items:center;gap:.75rem;">
          <div class="chat-title">Dialogue</div>
          <div class="agent-selector">${agentTabs}</div>
          <div id="model-badge"
               class="model-badge"
               style="margin-left:auto;padding:2px 10px;border-radius:999px;border:1px solid rgba(255,255,255,.12);
                      font:12px/1.2 system-ui,Segoe UI,Roboto,Arial;opacity:.9;background:linear-gradient(135deg,#1a1a1a,#0f172a);color:#e5e7eb">
            —
          </div>
        </div>

        <div class="chat-messages card-body" id="chat-messages"></div>

        <div class="chat-input-area card-footer">
          <form id="chat-form" class="chat-form" autocomplete="off">
            <textarea id="chat-input" class="chat-input" rows="3" placeholder="Écrivez votre message..."></textarea>
          </form>

          <div class="chat-actions" style="display:flex;align-items:center;flex-wrap:wrap;gap:.5rem">
            <div class="rag-control">
              <button
                type="button"
                id="rag-power"
                class="rag-power"
                role="switch"
                aria-checked="${String(!!this.state.ragEnabled)}"
                title="Activer/Désactiver RAG">
                <svg class="power-icon" viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
                  <path d="M12 3v9" stroke="currentColor" stroke-width="2" stroke-linecap="round" fill="none"/>
                  <path d="M5.5 7a 8 8 0 1 0 13 0" stroke="currentColor" stroke-width="2" stroke-linecap="round" fill="none"/>
                </svg>
              </button>
              <span id="rag-label" class="rag-label">RAG</span>
            </div>

            <!-- === Mémoire === -->
            <div class="memory-control" style="display:flex;align-items:center;gap:.5rem;margin-left:.6rem">
              <span id="memory-dot" aria-hidden="true" style="width:10px;height:10px;border-radius:50%;background:#6b7280;display:inline-block"></span>
              <span id="memory-label" class="memory-label" title="Statut mémoire">Mémoire OFF</span>
              <span id="memory-counters" class="memory-counters" style="font:12px system-ui,Segoe UI,Roboto,Arial;opacity:.85"></span>
              <button type="button" id="memory-analyze" class="button" title="Analyser / consolider la mémoire">Analyser</button>
              <button type="button" id="memory-clear" class="button" title="Effacer la mémoire de session">Clear</button>
            </div>

            <!-- === Outils === -->
            <button type="button" id="chat-export" class="button">Exporter</button>
            <button type="button" id="chat-clear" class="button">Effacer</button>

            <button type="button" id="chat-send" class="chat-send-button" title="Envoyer">➤</button>
          </div>

          <!-- === Métriques Chat === -->
          <div id="chat-metrics" class="chat-metrics" style="margin-top:6px;font:12px system-ui,Segoe UI,Roboto,Arial;opacity:.85">
            <span id="metric-ttfb">TTFB: — ms</span>
            <span aria-hidden="true">•</span>
            <span id="metric-fallbacks">Fallback REST: 0</span>
          </div>
        </div>
      </div>
    `;

    this._bindEvents(container);
    this.update(container, this.state);
  }

  update(container, chatState = {}) {
    if (!container) return;
    this.state = { ...this.state, ...chatState };

    // Tabs / agent courant
    container.querySelector('#rag-power')
      ?.setAttribute('aria-checked', String(!!this.state.ragEnabled));
    this._setActiveAgentTab(container, this.state.currentAgentId);

    // Messages
    const raw = this.state.messages?.[this.state.currentAgentId];
    const list = this._asArray(raw).map((m) => this._normalizeMessage(m));
    this._renderMessages(container.querySelector('#chat-messages'), list);

    // --- Mémoire (statut + libellé + **compteurs**) ---
    const memoryOn = !!(this.state.memoryBannerAt || (this.state.lastAnalysis && this.state.lastAnalysis.status === 'completed'));
    const dot = container.querySelector('#memory-dot');
    const lbl = container.querySelector('#memory-label');
    if (dot) dot.style.background = memoryOn ? '#22c55e' : '#6b7280';
    if (lbl) lbl.textContent = memoryOn ? 'Mémoire ON' : 'Mémoire OFF';

    const mem = this.state.memoryStats || {};
    const cnt = container.querySelector('#memory-counters');
    if (cnt) {
      const stmTxt = mem.has_stm ? 'STM ✓' : 'STM 0';
      const ltmTxt = `LTM ${Number(mem.ltm_items || 0)}`;
      const inj = mem.injected ? '• inj' : '';
      cnt.textContent = `${stmTxt} • ${ltmTxt}${inj ? ' ' + inj : ''}`;
    }

    // --- Badge modèle / fallback ---
    const badge = container.querySelector('#model-badge');
    if (badge) {
      const mi = this.state.modelInfo || {};
      const lm = this.state.lastMessageMeta || {};
      const usedProvider = (lm.provider || mi.provider || '').toString();
      const usedModel = (lm.model || mi.model || '').toString();
      const planned = (mi.provider || '?') + ':' + (mi.model || '?');
      const used = (usedProvider || '?') + ':' + (usedModel || '?');
      const fallback = !!(mi.provider && mi.model && (mi.provider !== usedProvider || mi.model !== usedModel));
      badge.textContent = usedProvider || usedModel ? (fallback ? `Fallback → ${used}` : used) : '—';
      const ttfb = (this.state.metrics && Number.isFinite(this.state.metrics.last_ttfb_ms)) ? `${this.state.metrics.last_ttfb_ms} ms` : '—';
      badge.title = `Modèle prévu: ${planned} • Utilisé: ${used} • TTFB: ${ttfb}`;
      badge.style.borderColor = fallback ? '#f59e0b' : 'rgba(255,255,255,.12)';
      badge.style.color = fallback ? '#fde68a' : '#e5e7eb';
    }

    // Métriques
    const met = this.state.metrics || {};
    const ttfbEl = container.querySelector('#metric-ttfb');
    const fbEl = container.querySelector('#metric-fallbacks');
    if (ttfbEl) ttfbEl.textContent = `TTFB: ${Number.isFinite(met.last_ttfb_ms) ? met.last_ttfb_ms : 0} ms`;
    if (fbEl) fbEl.textContent = `Fallback REST: ${met.rest_fallback_count || 0}`;
  }

  _bindEvents(container) {
    const form  = container.querySelector('#chat-form');
    const input = container.querySelector('#chat-input');
    const ragBtn = container.querySelector('#rag-power');
    const ragLbl = container.querySelector('#rag-label');
    const sendBtn = container.querySelector('#chat-send');
    const memBtn  = container.querySelector('#memory-analyze');
    const memClr  = container.querySelector('#memory-clear');

    /* Autosize — textarea s’adapte à la frappe (desktop & mobile) */
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

    // ENTER → envoi | Shift+Enter → saut de ligne
    input?.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        if (typeof form.requestSubmit === 'function') form.requestSubmit();
        else form?.dispatchEvent(new Event('submit', { cancelable: true }));
      }
    });

    // Clic avion → submit du formulaire
    sendBtn?.addEventListener('click', () => {
      if (typeof form.requestSubmit === 'function') form.requestSubmit();
      else form?.dispatchEvent(new Event('submit', { cancelable: true }));
    });

    container.querySelector('#chat-export')
      ?.addEventListener('click', () => this.eventBus.emit(EVENTS.CHAT_EXPORT, null));
    container.querySelector('#chat-clear')
      ?.addEventListener('click', () => this.eventBus.emit(EVENTS.CHAT_CLEAR, null));

    const toggleRag = () => {
      const on = ragBtn.getAttribute('aria-checked') === 'true';
      ragBtn.setAttribute('aria-checked', String(!on));
      this.eventBus.emit(EVENTS.CHAT_RAG_TOGGLED, { enabled: !on });
    };
    ragBtn?.addEventListener('click', toggleRag);
    ragLbl?.addEventListener('click', toggleRag);

    // Mémoire — actions
    memBtn?.addEventListener('click', () => this.eventBus.emit('memory:tend'));
    memClr?.addEventListener('click', () => this.eventBus.emit('memory:clear'));

    container.querySelector('.agent-selector')?.addEventListener('click', (e) => {
      const btn = e.target.closest('button[data-agent-id]');
      if (!btn) return;
      const agentId = btn.getAttribute('data-agent-id');
      this.eventBus.emit(EVENTS.CHAT_AGENT_SELECTED, agentId);
      this._setActiveAgentTab(container, agentId);
    });
  }

  /* ----- Helpers UI ------------------------------------------------------ */

  _autoGrow(el){
    if (!el) return;
    const MAX_PX = Math.floor(window.innerHeight * 0.40); // 40% d’écran
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, MAX_PX) + 'px';
    el.style.overflowY = (el.scrollHeight > MAX_PX) ? 'auto' : 'hidden';
  }

  _renderMessages(host, messages) {
    if (!host) return;
    const html = (messages || []).map(m => this._messageHTML(m)).join('');
    host.innerHTML = html || `<div class="placeholder" style="opacity:.6;padding:1rem;">Commence à discuter…</div>`;
    host.scrollTo(0, 1e9);
  }

  _messageHTML(m) {
    const side = m.role === 'user' ? 'user' : 'assistant';
    const agentId = m.agent_id || m.agent || 'nexus';
    const you = 'FG';
    const name = side === 'user' ? you : (AGENTS[agentId]?.name || 'Agent');
    const raw = this._toPlainText(m.content);
    const content = this._escapeHTML(raw).replace(/\n/g, '<br/>');
    const cursor = m.isStreaming ? `<span class="blinking-cursor">▍</span>` : '';
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    return `
      <div class="message ${side} ${side === 'assistant' ? agentId : ''}">
        <div class="message-content">
          <div class="message-meta meta-inside">
            <strong class="sender-name">${name}</strong>
            <span class="message-time">${time}</span>
          </div>
          <div class="message-text">${content}${cursor}</div>
        </div>
      </div>`;
  }

  _agentTabsHTML(activeId) {
    const ids = Object.keys(AGENTS);
    return `
      <div class="tabs-container">
        ${ids.map(id => {
          const a = AGENTS[id];
          const act = id === activeId ? 'active' : '';
          return `<button class="button-tab agent--${id} ${act}" data-agent-id="${id}">${a?.emoji || ''} ${a?.name || id}</button>`;
        }).join('')}
      </div>`;
  }

  _setActiveAgentTab(container, agentId){
    container.querySelectorAll('.button-tab').forEach(b=>b.classList.remove('active'));
    container.querySelector(`.button-tab[data-agent-id="${agentId}"]`)?.classList.add('active');
  }

  _asArray(x){ return Array.isArray(x) ? x : (x ? [x] : []); }

  _normalizeMessage(m){
    if (!m) return { role:'assistant', content:'' };
    if (typeof m === 'string') return { role:'assistant', content:m };
    return {
      role: m.role || 'assistant',
      content: m.content ?? m.text ?? '',
      isStreaming: !!m.isStreaming,
      agent_id: m.agent_id || m.agent
    };
  }

  _toPlainText(val){
    if (val == null) return '';
    if (typeof val === 'string') return val;
    if (Array.isArray(val)) return val.map(v => this._toPlainText(v)).join('');
    if (typeof val === 'object') {
      if ('text' in val) return this._toPlainText(val.text);
      if ('content' in val) return this._toPlainText(val.content);
      if ('message' in val) return this._toPlainText(val.message);
      try { return JSON.stringify(val); } catch { return String(val); }
    }
    return String(val);
  }

  _escapeHTML(s){
    return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;','\'':'&#39;'}[c]));
  }
}
