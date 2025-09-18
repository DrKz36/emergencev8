// src/frontend/features/chat/chat.js
// Chat Module + UI — V28.3.2
// - Restaure l’affichage du module Dialogues avec logs détaillés
// - CSS hook correct: <div class="messages" id="chat-messages"> (aligne chat.css)
// - Mount-safe: rend dans le container fourni par App.showModule()
// - Aucune dépendance globale à #chat-root

import { EVENTS, AGENTS } from '../../shared/constants.js';

/* ------------------------- ChatUI ------------------------- */
class ChatUI {
  constructor(eventBus, stateManager) {
    this.eventBus = eventBus;
    this.stateManager = stateManager;
    this.root = null;
    this.state = {
      isLoading: false,
      currentAgentId: 'anima',
      ragEnabled: false,
      messages: {},                       // { agentId: [ {role, content, ...}, ... ] }
      memoryBannerAt: null,
      lastAnalysis: null,
      metrics: { send_count: 0, ws_start_count: 0, last_ttfb_ms: 0, rest_fallback_count: 0, last_fallback_at: null },
      memoryStats: { has_stm: false, ltm_items: 0, injected: false },
      modelInfo: null,
      lastMessageMeta: null,              // { provider, model, fallback?, sources?: [...] }
      userName: 'Vous',
      userInitials: 'VO'
    };
    console.log('✅ ChatUI V28.3.2 instancié.');
  }

  render(container, chatState = {}) {
    if (!container) {
      console.error('[ChatUI] render() sans container.');
      return;
    }
    this.root = container;
    this.state = { ...this.state, ...chatState };

    const agentTabs = this._agentTabsHTML(this.state.currentAgentId);

    // Markup aligné au CSS (classe ".messages" requise par chat.css)
    // Voir chat.css → .messages { flex:1; overflow:auto; ... } pour la zone scrollable.
    this.root.innerHTML = `
      <div id="chat-root" class="chat-container card" data-version="28.3.2">
        <div class="chat-header card-header">
          <div class="chat-title">Dialogue</div>
          <div class="agent-selector">${agentTabs}</div>
          <div id="model-badge" class="model-badge">--</div>
        </div>

        <div class="messages card-body" id="chat-messages"></div>

        <div id="rag-sources" class="rag-sources"></div>

        <div class="chat-input-area card-footer">
          <form id="chat-form" class="chat-form" autocomplete="off">
            <textarea id="chat-input" class="chat-input" rows="3" placeholder="Ecrivez votre message..."></textarea>
          </form>

          <div class="chat-actions">
            <div class="rag-control">
              <button
                type="button"
                id="rag-power"
                class="rag-power"
                role="switch"
                aria-checked="${String(!!this.state.ragEnabled)}"
                title="Activer/Desactiver RAG">
                <svg class="power-icon" viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
                  <path d="M12 3v9" stroke="currentColor" stroke-width="2" stroke-linecap="round" fill="none"></path>
                  <path d="M5.5 7a 8 8 0 1 0 13 0" stroke="currentColor" stroke-width="2" stroke-linecap="round" fill="none"></path>
                </svg>
              </button>
              <span id="rag-label" class="rag-label">RAG</span>
            </div>

            <div class="memory-control">
              <span id="memory-dot" class="memory-dot" aria-hidden="true"></span>
              <span id="memory-label" class="memory-label" title="Statut memoire">Memoire OFF</span>
              <span id="memory-counters" class="memory-counters"></span>
              <button type="button" id="memory-analyze" class="button memory-action" title="Analyser / consolider la memoire">Analyser</button>
              <button type="button" id="memory-clear" class="button memory-action" title="Effacer la memoire de session">Clear</button>
            </div>

            <button type="button" id="chat-export" class="button">Exporter</button>
            <button type="button" id="chat-clear" class="button">Effacer</button>
            <button type="button" id="chat-send" class="chat-send-button" title="Envoyer">Envoyer</button>
          </div>

          <div id="chat-metrics" class="chat-metrics">
            <span id="metric-ttfb">TTFB: -- ms</span>
            <span class="chat-metrics-separator" aria-hidden="true">&#8226;</span>
            <span id="metric-fallbacks">Fallback REST: 0</span>
          </div>
        </div>
      </div>
    `;

    this._bindEvents(this.root);
    this.update(this.root, this.state);

    const host = this.root.querySelector('#chat-messages');
    const dbg = {
      container_id: container.id || '(no-id)',
      has_active_class: container.classList.contains('active'),
      host_exists: !!host,
      host_class: host ? host.className : '(none)',
      clientHeight: this.root.clientHeight,
      offsetHeight: this.root.offsetHeight
    };
    console.log('[BOOT][chat] ChatUI mounted', dbg);
  }

  update(container, chatState = {}) {
    if (!container) return;
    this.state = { ...this.state, ...chatState };

    // RAG toggle + agent tab
    container.querySelector('#rag-power')?.setAttribute('aria-checked', String(!!this.state.ragEnabled));
    this._setActiveAgentTab(container, this.state.currentAgentId);

    // Messages
    const raw = this.state.messages?.[this.state.currentAgentId];
    const list = this._asArray(raw).map((m) => this._normalizeMessage(m));
    this._renderMessages(container.querySelector('#chat-messages'), list);

    // Sources (chips)
    this._renderSources(container.querySelector('#rag-sources'), this.state.lastMessageMeta?.sources);

    // Mémoire: dot + label + compteurs
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

    // Badge modèle / fallback
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

    // Log court d'update (utile pour tracer un render sans contenu)
    console.log('[chat] update → msgs:',
      Array.isArray(list) ? list.length : 0,
      '| rag:', !!this.state.ragEnabled,
      '| agent:', this.state.currentAgentId);
  }

  /* ------------------------- Events & helpers ------------------------- */

  _bindEvents(container) {
    const form   = container.querySelector('#chat-form');
    const input  = container.querySelector('#chat-input');
    const ragBtn = container.querySelector('#rag-power');
    const ragLbl = container.querySelector('#rag-label');
    const sendBtn= container.querySelector('#chat-send');
    const memBtn = container.querySelector('#memory-analyze');
    const memClr = container.querySelector('#memory-clear');

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
        if (typeof form.requestSubmit === 'function') form.requestSubmit();
        else form?.dispatchEvent(new Event('submit', { cancelable: true }));
      }
    });
    sendBtn?.addEventListener('click', () => {
      if (typeof form.requestSubmit === 'function') form.requestSubmit();
      else form?.dispatchEvent(new Event('submit', { cancelable: true }));
    });

    container.querySelector('#chat-export')?.addEventListener('click', () => this.eventBus.emit(EVENTS.CHAT_EXPORT, null));
    container.querySelector('#chat-clear') ?.addEventListener('click', () => this.eventBus.emit(EVENTS.CHAT_CLEAR, null));

    const toggleRag = () => {
      const on = ragBtn.getAttribute('aria-checked') === 'true';
      ragBtn.setAttribute('aria-checked', String(!on));
      this.eventBus.emit(EVENTS.CHAT_RAG_TOGGLED, { enabled: !on });
    };
    ragBtn?.addEventListener('click', toggleRag);
    ragLbl?.addEventListener('click', toggleRag);

    memBtn?.addEventListener('click', () => this.eventBus.emit('memory:tend'));
    memClr?.addEventListener('click', () => this.eventBus.emit('memory:clear'));

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

    // Micro-isomorphisme (hover subtil sur les bulles)
    const host = container.querySelector('#chat-messages');
    if (host) {
      host.addEventListener('mousemove', (e) => {
        const t = e.target.closest('.message');
        if (!t) return;
        const r = t.getBoundingClientRect();
        const mx = ((e.clientX - r.left) / Math.max(r.width, 1) - 0.5) * 4;
        const my = ((e.clientY - r.top ) / Math.max(r.height,1) - 0.5) * 4;
        t.style.setProperty('--mx', `${mx}px`);
        t.style.setProperty('--my', `${my}px`);
      });
      host.addEventListener('mouseleave', () => {
        host.querySelectorAll('.message').forEach(m => {
          m.style.removeProperty('--mx'); m.style.removeProperty('--my');
        });
      });
    }
  }

  _autoGrow(el){
    if (!el) return;
    const MAX_PX = Math.floor(window.innerHeight * 0.40);
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, MAX_PX) + 'px';
    el.style.overflowY = (el.scrollHeight > MAX_PX) ? 'auto' : 'hidden';
  }

  _renderMessages(host, messages) {
    if (!host) return;
    const html = (messages || []).map((entry) => this._messageHTML(entry)).join('');
    host.innerHTML = html || '<div class="messages-placeholder placeholder">Commencez a discuter...</div>';
    host.scrollTo(0, 1e9);
  }

  _renderSources(host, sources) {
    if (!host) return;
    const items = Array.isArray(sources) ? sources : [];
    if (!items.length) {
      host.classList.remove('rag-sources--visible');
      host.classList.add('rag-sources--hidden');
      host.innerHTML = '';
      return;
    }

    const chips = items.map((s, i) => {
      const filename = (s.filename || 'Document').toString();
      const page = (Number(s.page) || 0) > 0 ? ` &#183; p.${Number(s.page)}` : '';
      const label = `${filename}${page}`;
      const tip = (s.excerpt || '').toString().slice(0, 300);
      const safeTip = this._escapeHTML(tip).replace(/\n/g, ' ');
      const docId = (s.document_id || `doc-${i}`).toString();
      const fnAttr = this._escapeHTML(filename);
      const exAttr = this._escapeHTML(tip);

      return `
        <button
          type="button"
          class="rag-source-chip"
          data-doc-id="${docId}"
          data-filename="${fnAttr}"
          data-page="${Number(s.page) || ''}"
          data-excerpt="${exAttr}"
          title="${safeTip}">
          <svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true">
            <path d="M4 4h10l6 6v10H4z" fill="none" stroke="currentColor" stroke-width="1.5"/>
            <path d="M14 4v6h6" fill="none" stroke="currentColor" stroke-width="1.5"/>
          </svg>
          <span>${this._escapeHTML(label)}</span>
        </button>`;
    }).join('');

    host.innerHTML = `
      <div class="rag-sources-wrap">
        <span class="rag-sources-title">Sources :</span>
        ${chips}
      </div>
    `;
    host.classList.add('rag-sources--visible');
    host.classList.remove('rag-sources--hidden');
  }

  _messageHTML(m) {
    const normalized = this._normalizeMessage(m);
    const side = normalized.role === 'user' ? 'user' : 'assistant';
    const agentKey = side === 'assistant'
      ? this._sanitizeAgentId(normalized.agent_id || normalized.agent || this.state.currentAgentId || 'nexus')
      : 'user';
    const agent = side === 'assistant' ? (AGENTS[agentKey] || {}) : null;
    const senderName = side === 'user'
      ? (this.state.userName || 'Vous')
      : this._formatAgentLabel(agentKey);
    const avatarLabel = side === 'user'
      ? (this.state.userInitials || this._computeInitials(senderName))
      : this._computeInitials(agent?.label || agent?.name || agentKey);
    const rawContent = this._toPlainText(normalized.content);
    const content = this._escapeHTML(rawContent).replace(/\n/g, '<br/>');
    const cursor = normalized.isStreaming ? '<span class="message-cursor blinking-cursor"></span>' : '';
    const timestamp = this._formatTimestamp(m?.created_at || m?.timestamp || m?.time || m?.ts || Date.now());

    const wrapperClasses = ['message-wrapper', `message-wrapper--${side}`];
    if (side === 'assistant') wrapperClasses.push(`message-wrapper--${agentKey}`);

    const avatarClasses = ['message-avatar', `message-avatar--${side}`];
    if (side === 'assistant') avatarClasses.push(`message-avatar--${agentKey}`);

    const cardClasses = ['message-card'];
    if (side === 'assistant') {
      cardClasses.push('message-card--assistant');
      cardClasses.push(`message-card--${agentKey}`);
    } else {
      cardClasses.push('message-card--user');
    }
    if (normalized.isStreaming) cardClasses.push('message-card--streaming');

    const metaParts = [`<span class="message-sender">${this._escapeHTML(senderName)}</span>`];
    if (timestamp) {
      metaParts.push(`<time class="message-time">${this._escapeHTML(timestamp)}</time>`);
    }
    const meta = `<div class="message-meta">${metaParts.join('')}</div>`;

    const dataAgentAttr = side === 'assistant' ? ` data-agent="${this._escapeHTML(agentKey)}"` : '';

    return `
      <div class="${wrapperClasses.join(' ')}" data-role="${side}"${dataAgentAttr}>
        <div class="${avatarClasses.join(' ')}" aria-hidden="true">${this._escapeHTML(avatarLabel)}</div>
        <div class="${cardClasses.join(' ')}">
          ${meta}
          <div class="message-content">${content}${cursor}</div>
        </div>
      </div>`;
  }

  _sanitizeAgentId(value, fallback = 'nexus') {
    const base = String(value || '').toLowerCase().replace(/[^a-z0-9_-]/g, '');
    return base || fallback;
  }

  _formatAgentLabel(agentId) {
    const agent = AGENTS[agentId] || {};
    const raw = agent.label || agent.name || agentId || 'agent';
    const label = String(raw);
    return label.charAt(0).toUpperCase() + label.slice(1);
  }

  _computeInitials(label) {
    if (!label) return 'AI';
    const parts = String(label).trim().split(/\s+/).filter(Boolean);
    if (!parts.length) return 'AI';
    let raw = parts.length === 1 ? parts[0].slice(0, 2) : `${parts[0][0]}${parts[parts.length - 1][0]}`;
    if (!raw) raw = parts[0].slice(0, 2);
    if (raw && typeof raw.normalize === 'function') {
      raw = raw.normalize('NFD').replace(/[̀-ͯ]/g, '');
    }
    const clean = (raw || '').replace(/[^A-Za-z0-9]/g, '');
    return clean ? clean.toUpperCase() : 'AI';
  }

  _formatTimestamp(value) {
    try {
      const date = value instanceof Date ? value : new Date(value || Date.now());
      if (Number.isNaN(date.getTime())) return '';
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch (_) {
      return '';
    }
  }

  _agentTabsHTML(activeId){
    const ids = Object.keys(AGENTS);
    return `
      <div class="tabs-container">
        ${ids.map(id => {
          const a = AGENTS[id]; const act = id === activeId ? 'active' : '';
          return `<button class="button-tab agent--${id} ${act}" data-agent-id="${id}">${a?.emoji || ''} ${a?.name || id}</button>`;
        }).join('')}
      </div>`;
  }

  _setActiveAgentTab(container, agentId){
    container.querySelectorAll('.button-tab').forEach(b => b.classList.remove('active'));
    container.querySelector(`.button-tab[data-agent-id="${agentId}"]`)?.classList.add('active');
  }

  _asArray(x){ return Array.isArray(x) ? x : (x ? [x] : []); }

  _normalizeMessage(m){
    if (!m) return { role:'assistant', content:'' };
    if (typeof m === 'string') return { role:'assistant', content:m };
    const agentCandidate = typeof m.agent_id === 'string' ? m.agent_id : (typeof m.agent === 'string' ? m.agent : '');
    const safeAgent = agentCandidate ? this._sanitizeAgentId(agentCandidate) : '';
    return {
      role: m.role || 'assistant',
      content: m.content ?? m.text ?? '',
      isStreaming: !!m.isStreaming,
      agent_id: safeAgent
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

  _escapeHTML(s){ return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;','\'':'&#39;'}[c])); }
}

/* ------------------------- ChatModule ------------------------- */
export default class ChatModule {
  constructor(eventBus, stateManager) {
    this.eventBus = eventBus;
    this.state = stateManager;
    this.ui = new ChatUI(eventBus, stateManager);
    this.container = null;
    this.inited = false;
    this._activeStreams = new Map();
  }

  init() {
    if (this.inited) return;
    this._wireState();
    this._wireWS();
    this.inited = true;
    console.log('✅ ChatModule V28.3.2 initialisé (handlers & state).');
  }

  mount(container) {
    this.container = container;
    if (!container) {
      console.error('[ChatModule] mount() sans container.');
      return;
    }
    // Sélection de l’agent par défaut si vide
    const agentId = this.state.get('chat.currentAgentId') || 'anima';
    const chatState = this.state.get('chat') || { currentAgentId: agentId, messages: {} };

    // Rendu UI
    this.ui.render(container, chatState);

    // Stats container (debug DOM)
    const rect = container.getBoundingClientRect?.() || {};
    console.log('[BOOT][chat] mount(container) OK →', {
      id: container.id || '(no-id)',
      class: container.className || '',
      size: { w: Math.round(rect.width || 0), h: Math.round(rect.height || 0) }
    });
  }

  /* ----------------- State & Events wiring ----------------- */

  _wireState() {
    // Threads chargés → hydrate l’état chat
    this.eventBus.on?.('threads:loaded', (thread) => {
      try {
        const msgs = (thread?.messages || []).map(m => ({
          role: m.role || (m.is_user ? 'user' : 'assistant'),
          content: m.content || m.text || '',
          agent_id: m.agent_id || m.agent
        }));
        const curAgent = this.state.get('chat.currentAgentId') || 'anima';
        const map = { ...(this.state.get('chat.messages') || {}) };
        map[curAgent] = msgs;
        this.state.set('chat.messages', map);
        this.ui.update(this.container, { messages: map, currentAgentId: curAgent });
      } catch (e) {
        console.error('[ChatModule] threads:loaded hydration failed', e);
      }
    });

    // Sélection d’agent
    this.eventBus.on?.(EVENTS.CHAT_AGENT_SELECTED, (agentId) => {
      this.state.set('chat.currentAgentId', agentId);
      this.ui.update(this.container, { currentAgentId: agentId });
    });

    // Toggle RAG
    this.eventBus.on?.(EVENTS.CHAT_RAG_TOGGLED, ({ enabled }) => {
      this.state.set('chat.ragEnabled', !!enabled);
      this.ui.update(this.container, { ragEnabled: !!enabled });
    });

    // Export / Clear (propagés au back ou à d’autres modules selon implémentation)
    this.eventBus.on?.(EVENTS.CHAT_EXPORT, () => console.log('[chat] export requested'));
    this.eventBus.on?.(EVENTS.CHAT_CLEAR,  () => {
      const curAgent = this.state.get('chat.currentAgentId') || 'anima';
      const map = { ...(this.state.get('chat.messages') || {}) };
      map[curAgent] = [];
      this.state.set('chat.messages', map);
      this.ui.update(this.container, { messages: map });
    });
  }

  _wireWS() {
    // Flux modele/metadata -> badge
    this.eventBus.on?.('chat:model_info', (p) => this.ui.update(this.container, { modelInfo: p || null }));
    this.eventBus.on?.('chat:last_message_meta', (meta) => {
      this.ui.update(this.container, { lastMessageMeta: meta || null });
    });

    // Envoi (UI -> WS) -- laisse au WebSocketClient via guards main.js
    this.eventBus.on?.(EVENTS.CHAT_SEND, (payload) => {
      // L'UI envoie un evenement simple ; le patch main.js route vers ws:send si enrichi
      this.eventBus.emit?.('ui:chat:send', { text: payload?.text || '', agent_id: this.state.get('chat.currentAgentId') || 'anima' });
      // Affichage optimiste du message utilisateur
      const curAgent = this.state.get('chat.currentAgentId') || 'anima';
      const map = { ...(this.state.get('chat.messages') || {}) };
      const arr = Array.isArray(map[curAgent]) ? map[curAgent].slice() : [];
      arr.push({ role: 'user', content: String(payload?.text || '') });
      map[curAgent] = arr;
      this.state.set('chat.messages', map);
      this.ui.update(this.container, { messages: map });
    });

    // Flux streaming WS -> UI
    this.eventBus.on?.('ws:chat_stream_start', (payload) => this._handleStreamStart(payload));
    this.eventBus.on?.('ws:chat_stream_chunk', (payload) => this._handleStreamChunk(payload));
    this.eventBus.on?.('ws:chat_stream_end', (payload) => this._handleStreamEnd(payload));

  }

  _handleStreamStart(payload = {}) {
    const messageId = this._resolveMessageId(payload);
    if (!messageId) return;

    const agentId = this._normalizeAgentId(payload?.agent_id ?? payload?.agent ?? payload?.agentId);
    const messages = this.state.get('chat.messages') || {};
    const list = Array.isArray(messages[agentId]) ? messages[agentId].slice() : [];
    const idx = list.findIndex((m) => m && (m.id === messageId || m.message_id === messageId));
    const base = {
      id: messageId,
      role: 'assistant',
      agent_id: agentId,
      content: '',
      isStreaming: true,
    };
    if (idx >= 0) {
      list[idx] = { ...list[idx], ...base };
    } else {
      list.push(base);
    }
    const next = { ...messages, [agentId]: list };
    this.state.set('chat.messages', next);
    this._activeStreams.set(messageId, { agentId });
    this._refreshUi(agentId, next);
  }

  _handleStreamChunk(payload = {}) {
    const messageId = this._resolveMessageId(payload);
    const chunk = (payload?.chunk ?? '').toString();
    if (!messageId || !chunk) return;

    const info = this._activeStreams.get(messageId);
    const agentId = this._normalizeAgentId(payload?.agent_id ?? payload?.agent ?? payload?.agentId ?? (info && info.agentId));

    let messages = this.state.get('chat.messages');
    if (!messages || typeof messages !== 'object') {
      messages = {};
      this.state.set('chat.messages', messages);
    }

    let list = messages[agentId];
    if (!Array.isArray(list)) {
      list = [];
      messages[agentId] = list;
    }

    let target = list.find((m) => m && (m.id === messageId || m.message_id === messageId));
    if (!target) {
      target = { id: messageId, role: 'assistant', agent_id: agentId, content: '', isStreaming: true };
      list.push(target);
    }

    target.content = (target.content || '') + chunk;
    target.isStreaming = true;
    this._activeStreams.set(messageId, { agentId });
    this._refreshUi(agentId, messages);
  }

  _handleStreamEnd(payload = {}) {
    const messageId = this._resolveMessageId(payload);
    const info = messageId ? this._activeStreams.get(messageId) : null;
    const agentCandidate = payload?.agent_id ?? payload?.agent ?? payload?.agentId ?? (info && info.agentId);
    const agentId = this._normalizeAgentId(agentCandidate);
    const text = this._extractPayloadText(payload);

    const messages = this.state.get('chat.messages') || {};
    const existing = Array.isArray(messages[agentId]) ? messages[agentId] : [];
    const list = existing.slice();
    const idx = list.findIndex((m) => m && (m.id === messageId || m.message_id === messageId));
    if (idx >= 0) {
      const base = list[idx] || {};
      list[idx] = {
        ...base,
        id: messageId || base.id,
        role: base.role || 'assistant',
        agent_id: agentId,
        content: text !== '' ? text : (base.content || ''),
        isStreaming: false,
        meta: payload?.meta ?? base.meta,
      };
    } else if (messageId || text) {
      list.push({
        id: messageId || `ws-${Date.now()}`,
        role: 'assistant',
        agent_id: agentId,
        content: text,
        isStreaming: false,
        meta: payload?.meta || null,
      });
    }

    const next = { ...messages, [agentId]: list };
    this.state.set('chat.messages', next);
    this._refreshUi(agentId, next);
    if (messageId) this._activeStreams.delete(messageId);
  }

  _resolveMessageId(payload = {}) {
    const candidates = [
      payload?.id,
      payload?.message_id,
      payload?.messageId,
      payload?.msg_id,
      payload?.msgId,
      payload?.temp_id,
      payload?.tempId,
      payload?.uuid,
    ];
    for (const candidate of candidates) {
      if (candidate != null) {
        const s = String(candidate).trim();
        if (s) return s;
      }
    }
    return null;
  }

  _normalizeAgentId(value) {
    const raw = (value ?? '').toString().trim().toLowerCase();
    if (raw) return raw;
    return this._currentAgentId();
  }

  _extractPayloadText(payload = {}) {
    const val = payload?.content ?? payload?.message ?? payload?.text ?? '';
    if (Array.isArray(val)) {
      return val.map((entry) => this._extractPayloadText({ content: entry })).join('');
    }
    if (val && typeof val === 'object') {
      if ('text' in val) return this._extractPayloadText({ content: val.text });
      if ('content' in val) return this._extractPayloadText({ content: val.content });
      if ('message' in val) return this._extractPayloadText({ content: val.message });
      try {
        return JSON.stringify(val);
      } catch (_) {
        return '';
      }
    }
    return String(val ?? '');
  }

  _currentAgentId() {
    const cur = this.state.get('chat.currentAgentId');
    const base = cur ? String(cur) : 'anima';
    const trimmed = base.trim().toLowerCase();
    return trimmed || 'anima';
  }

  _refreshUi(agentId, messagesSnapshot) {
    if (!this.container) return;
    const payload = {
      messages: messagesSnapshot || this.state.get('chat.messages') || {},
      currentAgentId: this._currentAgentId(),
    };
    this.ui.update(this.container, payload);
  }

}
