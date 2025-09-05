/**
 * @module features/chat/chat
 * @description Module Chat - V25.8 "Memory banner: robust REST mapping + auto-refresh on analysis + ws compat"
 *
 * Diff vs V25.7:
 * - Mapping REST robuste (STM via summary|stm.summary; LTM via ltm_items|ltm_count|facts+episodes)
 * - Le reste inchangé (eventBus/state, WS-first, watchdog REST, UI, etc.)
 */

import { ChatUI } from './chat-ui.js?v=2713';
import { EVENTS } from '../../shared/constants.js';
import { api } from '../../shared/api-client.js';

export default class ChatModule {
  constructor(eventBus, state) {
    this.eventBus = eventBus;
    this.state = state;

    this.ui = null;
    this.container = null;
    this.listeners = [];
    this.isInitialized = false;

    // Threads / convo
    this.threadId = null;
    this.loadedThreadId = null;

    // Connexion & flux
    this._wsConnected = false;
    this._wsConnectWaitMs = 700;
    this._streamStartTimer = null;
    this._streamStartTimeoutMs = 1500;
    this._pendingMsg = null;

    // Anti double actions
    this._sendLock = false;
    this._sendGateMs = 400;
    this._assistantPersistedIds = new Set();

    // UX
    this._lastToastAt = 0;

    // Mémoire
    this._lastMemoryTendAt = 0;
    this._memoryTendThrottleMs = 2000;
    this._memPreloadDone = false;

    // Idempotence abonnements
    this._subs = Object.create(null);
    this._H = Object.create(null);
    this._bindHandlers();
  }

  _bindHandlers() {
    // UI
    this._H.CHAT_SEND           = this.handleSendMessage.bind(this);
    this._H.CHAT_AGENT_SELECTED = this.handleAgentSelected.bind(this);
    this._H.CHAT_CLEAR          = this.handleClearChat.bind(this);
    this._H.CHAT_EXPORT         = this.handleExport.bind(this);
    this._H.CHAT_RAG_TOGGLED    = this.handleRagToggle.bind(this);

    // WS flux
    this._H.WS_START            = this.handleStreamStart.bind(this);
    this._H.WS_CHUNK            = this.handleStreamChunk.bind(this);
    this._H.WS_END              = this.handleStreamEnd.bind(this);
    this._H.WS_ANALYSIS         = this.handleAnalysisStatus.bind(this);

    // WS état
    this._H.WS_CONNECTED        = () => { this._wsConnected = true;  try { this.state.set('connection.status', 'connected'); } catch {} };
    this._H.WS_CLOSE            = () => { this._wsConnected = false; try { this.state.set('connection.status', 'disconnected'); } catch {} };

    // Hooks RAG/Mémoire
    this._H.MEM_BANNER          = this.handleMemoryBanner.bind(this);   // ws:memory_banner (compat)
    this._H.MEM_STATUS          = this.handleMemoryStatus.bind(this);   // memory:status (broadcast local éventuel)
    this._H.RAG_STATUS          = this.handleRagStatus.bind(this);
    this._H.MEM_TEND            = this.handleMemoryTend.bind(this);
    this._H.MEM_CLEAR           = this.handleMemoryClear.bind(this);
  }

  _onOnce(eventName, handler) {
    if (this._subs[eventName]) return;
    const off = this.eventBus.on(eventName, handler);
    this._subs[eventName] = off;
    if (typeof off === 'function') this.listeners.push(off);
  }

  /* ============================ Cycle de vie ============================ */
  init() {
    if (this.isInitialized) return;

    this.ui = new ChatUI(this.eventBus, this.state);
    this.initializeState();
    this.registerStateChanges();
    this.registerEvents();

    try {
      const conn = this.state.get('connection.status');
      this._wsConnected = (conn === 'connected');
    } catch {}

    // Précharge mémoire au boot (REST)
    this._refreshMemoryStatsFromServer();

    this.isInitialized = true;
    console.log('✅ ChatModule V25.8 initialisé (bannière mémoire: preload & auto-refresh).');
  }

  mount(container) {
    this.container = container;
    this.ui.render(this.container, this.state.get('chat'));

    const currentId = this.getCurrentThreadId();
    if (currentId) {
      const cached = this.state.get(`threads.map.${currentId}`);
      if (cached && cached.messages && this.loadedThreadId !== currentId) {
        this.loadedThreadId = currentId;
        this.threadId = currentId;
        this.state.set('chat.threadId', currentId);
        this.hydrateFromThread(cached);
        console.log('[Chat] mount() → hydratation tardive depuis state pour', currentId);
      }
    }

    // Premier rendu de la bannière si stats déjà présentes
    this._renderMemoryBannerFromState();

    // Sécurité: si pas encore préchargé
    if (!this._memPreloadDone) this._refreshMemoryStatsFromServer();
  }

  /* ============================ State init ============================ */
  initializeState() {
    if (!this.state.get('chat')) {
      this.state.set('chat', {
        currentAgentId: 'anima',
        activeAgent: 'anima',
        ragEnabled: false,
        ragStatus: 'idle',
        lastAnalysis: null,
        memoryBannerAt: null,
        messages: {},
        metrics: { send_count: 0, ws_start_count: 0, last_ttfb_ms: 0, rest_fallback_count: 0, last_fallback_at: null },
        memoryStats: { has_stm: false, ltm_items: 0, injected: false }
      });
    } else {
      if (this.state.get('chat.ragEnabled') === undefined) this.state.set('chat.ragEnabled', false);
      if (!this.state.get('chat.messages')) this.state.set('chat.messages', {});
      if (!this.state.get('chat.ragStatus')) this.state.set('chat.ragStatus', 'idle');
      if (!this.state.get('chat.memoryBannerAt')) this.state.set('chat.memoryBannerAt', null);
      if (!this.state.get('chat.metrics')) this.state.set('chat.metrics', { send_count: 0, ws_start_count: 0, last_ttfb_ms: 0, rest_fallback_count: 0, last_fallback_at: null });
      if (!this.state.get('chat.memoryStats')) this.state.set('chat.memoryStats', { has_stm: false, ltm_items: 0, injected: false });
    }
  }

  registerStateChanges() {
    const unsub = this.state.subscribe('chat', (chatState) => {
      if (this.ui && this.container) this.ui.update(this.container, chatState);
      this._renderMemoryBannerFromState();
    });
    if (typeof unsub === 'function') this.listeners.push(unsub);
  }

  registerEvents() {
    this._onOnce(EVENTS.CHAT_SEND,           this._H.CHAT_SEND);
    this._onOnce(EVENTS.CHAT_AGENT_SELECTED, this._H.CHAT_AGENT_SELECTED);
    this._onOnce(EVENTS.CHAT_CLEAR,          this._H.CHAT_CLEAR);
    this._onOnce(EVENTS.CHAT_EXPORT,         this._H.CHAT_EXPORT);
    this._onOnce(EVENTS.CHAT_RAG_TOGGLED,    this._H.CHAT_RAG_TOGGLED);

    this._onOnce('ws:chat_stream_start',     this._H.WS_START);
    this._onOnce('ws:chat_stream_chunk',     this._H.WS_CHUNK);
    this._onOnce('ws:chat_stream_end',       this._H.WS_END);
    this._onOnce('ws:analysis_status',       this._H.WS_ANALYSIS);

    this._onOnce('ws:connected',             this._H.WS_CONNECTED);
    this._onOnce('ws:close',                 this._H.WS_CLOSE);

    // Mémoire
    this._onOnce('ws:memory_banner',         this._H.MEM_BANNER);  // compat
    this._onOnce('memory:status',            this._H.MEM_STATUS);  // broadcast local éventuel
    this._onOnce('memory:tend',              this._H.MEM_TEND);
    this._onOnce('memory:clear',             this._H.MEM_CLEAR);
  }

  /* ============================ Utils ============================ */
  getCurrentThreadId() {
    return this.threadId || this.state.get('threads.currentId') || null;
  }

  _qs(sel, root = document) { try { return root.querySelector(sel); } catch { return null; } }
  _ensureHeaderEl() {
    if (!this.container) return null;
    const header = this._qs('.chat-header', this.container) || this._qs('.chat-header');
    return header || null;
  }

  _renderMemoryBannerFromState() {
    try {
      const stats = this.state.get('chat.memoryStats') || null;
      const at    = this.state.get('chat.memoryBannerAt') || null;
      if (!stats && !at) { this._destroyMemoryBanner(); return; }
      this._renderMemoryBanner(stats || { has_stm:false, ltm_items:0, injected:false });
    } catch {}
  }

  _destroyMemoryBanner() {
    const header = this._ensureHeaderEl();
    if (!header) return;
    const old = header.querySelector('.memory-banner');
    if (old) try { old.remove(); } catch {}
  }

  _renderMemoryBanner(stats) {
    const header = this._ensureHeaderEl();
    if (!header) return;
    const { has_stm, ltm_items, injected } = (stats || {});
    let el = header.querySelector('.memory-banner');
    if (!el) {
      el = document.createElement('div');
      el.className = 'memory-banner';
      header.appendChild(el);
    }
    const stmClass = has_stm ? 'ok' : 'ko';
    const injClass = injected ? 'ok' : 'ko';
    const ltm = Number.isFinite(ltm_items) ? ltm_items : 0;
    el.innerHTML = `
      <span class="pill ${stmClass}" title="Résumé de session (STM)">
        <span class="dot" aria-hidden="true"></span> STM
      </span>
      <span class="sep" aria-hidden="true"></span>
      <span class="pill" title="Éléments de mémoire longue (LTM)">
        <span class="dot" aria-hidden="true"></span> LTM: ${ltm}
      </span>
      <span class="sep" aria-hidden="true"></span>
      <span class="pill ${injClass}" title="Mémoire injectée dans le prompt">
        <span class="dot" aria-hidden="true"></span> Injecté
      </span>
    `;
  }

  async _waitForWS(timeoutMs = 0) {
    if (this._wsConnected || timeoutMs <= 0) return this._wsConnected;
    return await new Promise((resolve) => {
      let done = false;
      const off = this.eventBus.on('ws:connected', () => {
        if (done) return;
        done = true;
        try { if (typeof off === 'function') off(); } catch {}
        this._wsConnected = true;
        resolve(true);
      });
      setTimeout(() => {
        if (done) return;
        done = true;
        try { if (typeof off === 'function') off(); } catch {}
        resolve(this._wsConnected === true);
      }, timeoutMs);
    });
  }

  /* ============================ PATCH: mapping REST robuste ============================ */
  async _refreshMemoryStatsFromServer() {
    try {
      let data = null;

      // 1) API client si présent
      if (api && typeof api.getMemoryStatus === 'function') {
        data = await api.getMemoryStatus();
      }

      // 2) Fallback direct
      if (!data) {
        const res = await fetch('/api/memory/status', { headers: { 'Accept': 'application/json' } });
        if (res.ok) data = await res.json();
      }

      if (!data || typeof data !== 'object') return;

      const injected = !!(data.injected ?? data.injected_into_prompt);

      // STM: accepte plusieurs formes (bools + présence de résumé)
      const hasSTM =
        !!(data.has_stm ||
           data.summary_available ||
           data.stm_ready ||
           (typeof data.summary === 'string' && data.summary.trim()) ||
           (data.stm && typeof data.stm.summary === 'string' && data.stm.summary.trim()));

      // LTM: compte intelligent (ltm_items|ltm_count|facts+episodes)
      const ltmCount =
        Number.isFinite(data.ltm_items) ? data.ltm_items :
        Number.isFinite(data.ltm_count) ? data.ltm_count :
        ((data.ltm && Array.isArray(data.ltm.facts) ? data.ltm.facts.length : 0) +
         (data.ltm && Array.isArray(data.ltm.episodes) ? data.ltm.episodes.length : 0));

      const stats = { has_stm: hasSTM, ltm_items: ltmCount || 0, injected };

      this.state.set('chat.memoryStats', stats);
      this.state.set('chat.memoryBannerAt', Date.now());
      this._memPreloadDone = true;
      this._renderMemoryBannerFromState();
      console.log('[Chat] Mémoire (REST) préchargée', stats);
    } catch (e) {
      console.warn('[Chat] Impossible de précharger la mémoire', e);
    }
  }

  hydrateFromThread(thread) {
    const msgsRaw = Array.isArray(thread?.messages) ? [...thread.messages] : [];
    const msgs = msgsRaw.sort((a, b) => (a?.created_at ?? 0) - (b?.created_at ?? 0));

    const buckets = {};
    let lastAssistantAgent = null;

    for (const m of msgs) {
      const role = m.role || 'assistant';
      let agentId = m.agent_id || null;

      if (!agentId) {
        agentId = (role === 'assistant')
          ? (lastAssistantAgent || (this.state.get('chat.currentAgentId') || 'anima'))
          : (lastAssistantAgent || null);
      }
      if (!agentId) agentId = 'global';
      if (role === 'assistant' && agentId) lastAssistantAgent = agentId;

      (buckets[agentId] ||= []).push({
        id: m.id || `${role}-${m.created_at || Date.now()}`,
        role,
        content: typeof m.content === 'string' ? m.content : JSON.stringify(m.content ?? ''),
        agent_id: agentId,
        created_at: m.created_at
      });
    }

    this.state.set('chat.messages', buckets);
    console.debug('[Chat] Répartition messages par agent', Object.fromEntries(Object.entries(buckets).map(([k, v]) => [k, v.length])));
  }

  /* ============================ Envoi USER (WS-first strict) ============================ */
  async handleSendMessage(payload) {
    if (this._sendLock) return;
    this._sendLock = true;
    setTimeout(() => { this._sendLock = false; }, this._sendGateMs);

    const text = typeof payload === 'string' ? payload : (payload && payload.text) || '';
    const trimmed = (text || '').trim();
    if (!trimmed) { this._sendLock = false; return; }

    const { currentAgentId, ragEnabled } = this.state.get('chat');
    this.state.set('chat.activeAgent', currentAgentId);

    const userMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: trimmed,
      agent_id: currentAgentId,
      created_at: Date.now()
    };
    const curr = this.state.get(`chat.messages.${currentAgentId}`) || [];
    this.state.set(`chat.messages.${currentAgentId}`, [...curr, userMessage]);
    this.state.set('chat.isLoading', true);

    await this._waitForWS(this._wsConnectWaitMs);

    try {
      this.eventBus.emit('ui:chat:send', {
        text: trimmed, agent_id: currentAgentId, use_rag: !!ragEnabled, msg_uid: userMessage.id, __enriched: true
      });
      this._pendingMsg = { id: userMessage.id, agent_id: currentAgentId, text: trimmed, triedRest: false };
      this._startStreamWatchdog();
    } catch (e) {
      console.error('[Chat] Emission ui:chat:send a échoué', e);
      this._clearStreamWatchdog();
      this.state.set('chat.isLoading', false);
      this._sendLock = false;
      this.showToast('Envoi impossible via WebSocket');
    }
  }

  /* ============================ Flux assistant (WS) ============================ */
  handleStreamStart({ agent_id, id }) {
    const agentMessage = {
      id, role: 'assistant', content: '', agent_id, isStreaming: true, created_at: Date.now()
    };
    const curr = this.state.get(`chat.messages.${agent_id}`) || [];
    this.state.set(`chat.messages.${agent_id}`, [...curr, agentMessage]);
    this._clearStreamWatchdog();
  }

  handleStreamChunk({ agent_id, id, chunk }) {
    const list = this.state.get(`chat.messages.${agent_id}`) || [];
    const idx = list.findIndex((m) => m.id === id);
    if (idx >= 0) {
      const msg = { ...list[idx] };
      msg.content = (msg.content || '') + String(chunk || '');
      list[idx] = msg;
      this.state.set(`chat.messages.${agent_id}`, [...list]);
    }
  }

  handleStreamEnd({ agent_id, id, meta }) {
    const list = this.state.get(`chat.messages.${agent_id}`) || [];
    const idx = list.findIndex((m) => m.id === id);
    if (idx >= 0) {
      const msg = { ...list[idx], isStreaming: false };
      list[idx] = msg;
      this.state.set(`chat.messages.${agent_id}`, [...list]);
    }
    this.state.set('chat.isLoading', false);
    this._clearStreamWatchdog();

    try {
      if (this._assistantPersistedIds.has(id)) return;

      const backendPersisted =
        !!(meta && (meta.persisted === true || meta.persisted_by === 'backend' || meta.persisted_by_ws === true));

      const threadId = this.getCurrentThreadId();
      const finalMsg = (this.state.get(`chat.messages.${agent_id}`) || []).find(m => m.id === id);

      if (!backendPersisted && threadId && finalMsg) {
        api.appendMessage(threadId, {
          role: 'assistant',
          content: typeof finalMsg.content === 'string' ? finalMsg.content : String(finalMsg.content ?? ''),
          agent_id: finalMsg.agent_id || agent_id
        })
          .then(() => this._assistantPersistedIds.add(id))
          .catch(err => console.error('[Chat] Échec appendMessage assistant', err));
      }
    } catch (e) {
      console.error('[Chat] handleStreamEnd persist error', e);
    }
  }

  /* ============================ UI actions ============================ */
  handleAgentSelected(agentId) {
    const prev = this.state.get('chat.currentAgentId');
    if (prev === agentId) return;
    this.state.set('chat.currentAgentId', agentId);
    this.state.set('chat.activeAgent', agentId);
  }

  handleClearChat() {
    const agentId = this.state.get('chat.currentAgentId');
    this.state.set(`chat.messages.${agentId}`, []);
  }

  handleExport() {
    const { currentAgentId, messages } = this.state.get('chat');
    const conv = messages[currentAgentId] || [];
    const you = this.state.get('user.id') || 'Vous';
    const text = conv.map(m =>
      `${m.role === 'user' ? you : (m.agent_id || 'Assistant')}: ${
        typeof m.content === 'string' ? m.content : JSON.stringify(m.content || '')
      }`
    ).join('\n\n');
    const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = `chat_${currentAgentId}_${Date.now()}.txt`;
    document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
  }

  handleRagToggle() {
    const current = !!this.state.get('chat.ragEnabled');
    this.state.set('chat.ragEnabled', !current);
  }

  handleAnalysisStatus({ session_id, status, error } = {}) {
    this.state.set('chat.lastAnalysis', {
      session_id: session_id || null,
      status: status || 'unknown',
      error: error || null,
      at: Date.now()
    });
    console.log('[Chat] ws:analysis_status', { session_id, status, error });

    if (status === 'completed') {
      // 🔄 Tire l’état mémoire depuis le serveur pour mettre à jour la bannière
      this._refreshMemoryStatsFromServer();
      this.showToast('Mémoire consolidée');
    } else if (status === 'failed') {
      this.showToast('Analyse mémoire: échec');
    }
  }

  /* ============================ Hooks RAG/Mémoire ============================ */
  handleMemoryBanner(payload = {}) {
    try {
      const injected = !!(payload.injected ?? payload.injected_into_prompt);
      const stats = {
        has_stm: !!payload.has_stm,
        ltm_items: Number.isFinite(payload.ltm_items) ? payload.ltm_items : 0,
        injected
      };
      this.state.set('chat.memoryStats', stats);
      this.state.set('chat.memoryBannerAt', Date.now());
    } catch {}
    this._renderMemoryBannerFromState();
    this.showToast('Mémoire chargée ✓');
  }

  handleMemoryStatus(payload = {}) {
    // même forme que handleMemoryBanner (broadcast local depuis app.js le cas échéant)
    this.handleMemoryBanner(payload);
  }

  handleRagStatus(payload = {}) {
    const st = String(payload.status || '').toLowerCase();
    this.state.set('chat.ragStatus', st || 'idle');
    if (st === 'searching') this.showToast('RAG: recherche en cours');
    if (st === 'found')     this.showToast('RAG: sources trouvées');
  }

  async handleMemoryTend() {
    const now = Date.now();
    if (now - this._lastMemoryTendAt < this._memoryTendThrottleMs) return;
    this._lastMemoryTendAt = now;

    try {
      this.showToast('Analyse mémoire démarrée');
      await api.tendMemory(); // le back émettra ws:analysis_status
      // on laisse handleAnalysisStatus tirer l'état quand c'est "completed"
    } catch (e) {
      console.error('[Chat] memory.tend error', e);
      this.showToast('Analyse mémoire: échec');
    }
  }

  async handleMemoryClear() {
    try {
      this.showToast('Nettoyage mémoire');
      if (typeof api.clearMemory === 'function') {
        await api.clearMemory();
      } else {
        // fallback: on relance un tend-garden, puis on réinitialise côté UI
        await api.tendMemory();
      }
      try {
        this.state.set('chat.memoryStats', { has_stm: false, ltm_items: 0, injected: false });
        this.state.set('chat.memoryBannerAt', null);
      } catch {}
      this._renderMemoryBannerFromState();
      this.showToast('Mémoire effacée');
    } catch (e) {
      console.error('[Chat] memory.clear error', e);
      this.showToast('Effacement mémoire: échec');
    }
  }

  /* ============================ Watchdog / Fallback ============================ */
  _startStreamWatchdog() {
    this._clearStreamWatchdog();
    try {
      this._streamStartTimer = setTimeout(async () => {
        if (!this.state.get('chat.isLoading')) return;
        const p = this._pendingMsg;
        if (!p || p.triedRest) return;

        const threadId = this.getCurrentThreadId();
        if (!threadId) {
          this.showToast('Flux indisponible. Aucun thread actif.');
          return;
        }
        try {
          await api.appendMessage(threadId, {
            role: 'user', content: p.text, agent_id: p.agent_id, meta: { watchdog_fallback: true }
          });
          try {
            const m = this.state.get('chat.metrics') || {};
            const next = { ...m, rest_fallback_count: (m.rest_fallback_count || 0) + 1, last_fallback_at: Date.now() };
            this.state.set('chat.metrics', next);
          } catch {}

          p.triedRest = true;
          this._pendingMsg = p;
          this.showToast('Flux indisponible. Fallback REST effectué.');
        } catch (e) {
          console.error('[Chat] Watchdog fallback REST a échoué', e);
          this.showToast('Fallback REST impossible');
        }
      }, this._streamStartTimeoutMs);
    } catch (e) {
      console.warn('[Chat] Watchdog non initialisé', e);
    }
  }

  _clearStreamWatchdog() {
    if (this._streamStartTimer) {
      clearTimeout(this._streamStartTimer);
      this._streamStartTimer = null;
    }
  }

  /* ============================ UI toast ============================ */
  showToast(message) {
    try {
      const el = document.createElement('div');
      el.setAttribute('role', 'status');
      el.style.position = 'fixed';
      el.style.right = '20px';
      el.style.bottom = '20px';
      el.style.padding = '12px 14px';
      el.style.borderRadius = '12px';
      el.style.background = '#121212';
      el.style.color = '#fff';
      el.style.boxShadow = '0 6px 14px rgba(0,0,0,.3)';
      el.style.font = '14px/1.2 system-ui,-apple-system,Segoe UI,Roboto,Arial';
      el.style.opacity = '0';
      el.style.transform = 'translateY(6px)';
      el.style.transition = 'opacity .15s, transform .15s';
      el.textContent = message;
      document.body.appendChild(el);
      requestAnimationFrame(() => {
        el.style.opacity = '1';
        el.style.transform = 'translateY(0)';
      });
      setTimeout(() => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(6px)';
        setTimeout(() => { try { el.remove(); } catch {} }, 180);
      }, 2200);
    } catch {}
  }

  /* ============================ Rendu messages ============================ */
  get _AGENTS(){ try { return (window.AGENTS || {}).AGENTS || {}; } catch { return {}; } }

  _renderMessages(host, messages) {
    if (!host) return;
    const html = (messages || []).map(m => this._messageHTML(m)).join('');
    host.innerHTML = html || `<div class="placeholder">Commence à discuter</div>`;
    host.scrollTo(0, 1000000000);
  }

  _messageHTML(m) {
    const side = m.role === 'user' ? 'user' : 'assistant';
    const agentId = m.agent_id || m.agent || 'nexus';
    const AGENTS = this._AGENTS;
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
