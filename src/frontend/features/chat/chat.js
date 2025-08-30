/**
 * @module features/chat/chat
 * @description Module Chat - V25.2 "WS-first strict + RAG/Memo hooks + Watchdog REST fallback + metrics/fallback counter + memory.tend"
 *
 * Ajouts:
 * - Compteurs metrics: incrément 'rest_fallback_count' + 'last_fallback_at' lors du fallback REST.
 * - Action mémoire: écoute 'memory:tend' → api.tendMemory() + toasts + mise à jour lastAnalysis.
 * - Sans modification d’architecture ni d’imports externes.
 */

import { ChatUI } from './chat-ui.js';
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
    this._wsConnectWaitMs = 700;       // ⏳ anti-course avant d'émettre
    this._streamStartTimer = null;
    this._streamStartTimeoutMs = 1500; // ⏱️ Watchdog
    this._pendingMsg = null;           // { id, agent_id, text, triedRest }

    // Anti double actions
    this._sendLock = false;
    this._sendGateMs = 400;
    this._assistantPersistedIds = new Set();

    // UX
    this._lastToastAt = 0;

    // Mémoire
    this._lastMemoryTendAt = 0;
    this._memoryTendThrottleMs = 2000;
  }

  /* ============================ Cycle de vie ============================ */
  init() {
    if (this.isInitialized) return;

    this.ui = new ChatUI(this.eventBus, this.state);
    this.initializeState();
    this.registerStateChanges();
    this.registerEvents();

    // 🔄 Sync état WS au boot pour WS-first strict
    try {
      const conn = this.state.get('connection.status');
      this._wsConnected = (conn === 'connected');
    } catch {}

    this.isInitialized = true;
    console.log('✅ ChatModule V25.2 (WS-first strict + RAG/Memo hooks + Watchdog fallback + metrics) initialisé.');
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
        isLoading: false,
        messages: {},
        metrics: { send_count: 0, ws_start_count: 0, last_ttfb_ms: 0, rest_fallback_count: 0, last_fallback_at: null }
      });
    } else {
      if (this.state.get('chat.ragEnabled') === undefined) this.state.set('chat.ragEnabled', false);
      if (!this.state.get('chat.messages')) this.state.set('chat.messages', {});
      if (!this.state.get('chat.ragStatus')) this.state.set('chat.ragStatus', 'idle');
      if (!this.state.get('chat.memoryBannerAt')) this.state.set('chat.memoryBannerAt', null);
      if (!this.state.get('chat.metrics')) this.state.set('chat.metrics', { send_count: 0, ws_start_count: 0, last_ttfb_ms: 0, rest_fallback_count: 0, last_fallback_at: null });
    }
  }

  registerStateChanges() {
    const unsub = this.state.subscribe('chat', (chatState) => {
      if (this.ui && this.container) this.ui.update(this.container, chatState);
    });
    if (typeof unsub === 'function') this.listeners.push(unsub);
  }

  registerEvents() {
    // UI
    this.listeners.push(this.eventBus.on(EVENTS.CHAT_SEND, this.handleSendMessage.bind(this)));
    this.listeners.push(this.eventBus.on(EVENTS.CHAT_AGENT_SELECTED, this.handleAgentSelected.bind(this)));
    this.listeners.push(this.eventBus.on(EVENTS.CHAT_CLEAR, this.handleClearChat.bind(this)));
    this.listeners.push(this.eventBus.on(EVENTS.CHAT_EXPORT, this.handleExport.bind(this)));
    this.listeners.push(this.eventBus.on(EVENTS.CHAT_RAG_TOGGLED, this.handleRagToggle.bind(this)));

    // Flux WS
    this.listeners.push(this.eventBus.on('ws:chat_stream_start', this.handleStreamStart.bind(this)));
    this.listeners.push(this.eventBus.on('ws:chat_stream_chunk', this.handleStreamChunk.bind(this)));
    this.listeners.push(this.eventBus.on('ws:chat_stream_end', this.handleStreamEnd.bind(this)));
    this.listeners.push(this.eventBus.on('ws:analysis_status', this.handleAnalysisStatus.bind(this)));

    // Connexion WS → pilote WS-first
    this.listeners.push(this.eventBus.on('ws:connected', () => {
      this._wsConnected = true;
      try { this.state.set('connection.status', 'connected'); } catch {}
    }));
    this.listeners.push(this.eventBus.on('ws:close', () => {
      this._wsConnected = false;
      try { this.state.set('connection.status', 'disconnected'); } catch {}
    }));

    // Hooks RAG/Mémoire
    this.listeners.push(this.eventBus.on('ws:memory_banner', this.handleMemoryBanner.bind(this)));
    this.listeners.push(this.eventBus.on('ws:rag_status', this.handleRagStatus.bind(this)));

    // Action mémoire (UI)
    this.listeners.push(this.eventBus.on('memory:tend', this.handleMemoryTend.bind(this)));
  }

  /* ============================ Utils ============================ */
  getCurrentThreadId() {
    return this.threadId || this.state.get('threads.currentId') || null;
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
    console.debug('[Chat] Répartition messages par agent',
      Object.fromEntries(Object.entries(buckets).map(([k, v]) => [k, v.length])));
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

    // Ajoute localement le message USER
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

    // 🛡️ Anti-course: attends brièvement WS avant d'émettre
    await this._waitForWS(this._wsConnectWaitMs);

    // Émission enrichie UI→WS (prise en charge par WebSocketClient)
    try {
      this.eventBus.emit('ui:chat:send', {
        text: trimmed,
        agent_id: currentAgentId,
        use_rag: !!ragEnabled,
        msg_uid: userMessage.id,
        __enriched: true
      });
      // Pour watchdog (fallback REST si flux ne démarre pas)
      this._pendingMsg = { id: userMessage.id, agent_id: currentAgentId, text: trimmed, triedRest: false };
      this._startStreamWatchdog();
    } catch (e) {
      console.error('[Chat] Emission ui:chat:send a échoué', e);
      this._clearStreamWatchdog();
      this.state.set('chat.isLoading', false);
      this._sendLock = false;
      this.showToast('Envoi impossible (WS).');
    }
  }

  /* ============================ Flux assistant (WS) ============================ */
  handleStreamStart({ agent_id, id }) {
    const agentMessage = {
      id,
      role: 'assistant',
      content: '',
      agent_id,
      isStreaming: true,
      created_at: Date.now()
    };
    const curr = this.state.get(`chat.messages.${agent_id}`) || [];
    this.state.set(`chat.messages.${agent_id}`, [...curr, agentMessage]);
    this._clearStreamWatchdog(); // le flux a bien démarré
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
    // finalise le message assistant
    const list = this.state.get(`chat.messages.${agent_id}`) || [];
    const idx = list.findIndex((m) => m.id === id);
    if (idx >= 0) {
      const msg = { ...list[idx], isStreaming: false };
      list[idx] = msg;
      this.state.set(`chat.messages.${agent_id}`, [...list]);
    }

    // Terminer l’état de chargement
    this.state.set('chat.isLoading', false);
    this._clearStreamWatchdog();

    // Persistence assistant : une seule fois si non géré par le back
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
          .catch(err => console.error('[Chat] Échec appendMessage(assistant):', err));
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

    const now = Date.now();
    if (now - this._lastToastAt < 1000) return;
    this._lastToastAt = now;

    if (status === 'completed') this.showToast('Mémoire consolidée ✓');
    else if (status === 'failed') this.showToast('Analyse mémoire : échec');
  }

  /* ============================ Hooks RAG/Mémoire ============================ */
  handleMemoryBanner() {
    try { this.state.set('chat.memoryBannerAt', Date.now()); } catch {}
    this.showToast('Mémoire chargée ✓');
  }

  handleRagStatus(payload = {}) {
    const st = String(payload.status || '').toLowerCase();
    this.state.set('chat.ragStatus', st || 'idle');
    if (st === 'searching') this.showToast('RAG : recherche en cours…');
    if (st === 'found') this.showToast('RAG : sources trouvées ✓');
  }

  async handleMemoryTend() {
    const now = Date.now();
    if (now - this._lastMemoryTendAt < this._memoryTendThrottleMs) return;
    this._lastMemoryTendAt = now;

    try {
      this.showToast('Analyse mémoire démarrée…');
      await api.tendMemory();
      // Le backend émettra ensuite ws:analysis_status → géré dans handleAnalysisStatus()
    } catch (e) {
      console.error('[Chat] memory.tend error', e);
      this.showToast('Analyse mémoire : échec');
    }
  }

  /* ============================ Watchdog / Fallback ============================ */
  _startStreamWatchdog() {
    this._clearStreamWatchdog();
    try {
      this._streamStartTimer = setTimeout(async () => {
        // Si toujours en attente → fallback REST pour le USER (une seule fois)
        if (!this.state.get('chat.isLoading')) return;
        const p = this._pendingMsg;
        if (!p || p.triedRest) return;

        const threadId = this.getCurrentThreadId();
        if (!threadId) {
          this.showToast('Flux indisponible — aucun thread actif (fallback annulé).');
          return;
        }
        try {
          await api.appendMessage(threadId, {
            role: 'user',
            content: p.text,
            agent_id: p.agent_id,
            meta: { watchdog_fallback: true }
          });

          // ✅ Metrics: fallback REST
          try {
            const m = this.state.get('chat.metrics') || {};
            const next = {
              ...m,
              rest_fallback_count: (m.rest_fallback_count || 0) + 1,
              last_fallback_at: Date.now()
            };
            this.state.set('chat.metrics', next);
          } catch {}

          p.triedRest = true;
          this._pendingMsg = p;
          this.showToast('Flux indisponible — fallback REST effectué.');
        } catch (e) {
          console.error('[Chat] Watchdog fallback REST a échoué', e);
          this.showToast('Fallback REST impossible.');
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
}
