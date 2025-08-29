/**
 * @module features/chat/chat
 * @description Module Chat - V24.6 "Single-Emit + ActiveAgent + Watchdog + SendGate"
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
    this.threadId = null;
    this.loadedThreadId = null;
    this._lastToastAt = 0;

    // ⏱️ Watchdog stream-start
    this._streamStartTimer = null;
    this._streamStartTimeoutMs = 1500;

    // 🚦 Gate anti double-clic / multi-émission
    this._sendLock = false;
    this._sendGateMs = 400; // 300–500ms recommandé
  }

  init() {
    if (this.isInitialized) return;
    this.ui = new ChatUI(this.eventBus, this.state);
    this.initializeState();
    this.registerStateChanges();
    this.registerEvents();
    this.isInitialized = true;
    console.log('✅ ChatModule V24.6 (Single-Emit + ActiveAgent + Watchdog + SendGate) initialisé.');
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

  destroy() {
    this.listeners.forEach(u => { if (typeof u === 'function') { try { u(); } catch {} } });
    this.listeners = [];
    this.container = null;
    this._clearStreamWatchdog();
  }

  initializeState() {
    if (!this.state.get('chat')) {
      this.state.set('chat', {
        isLoading: false,
        currentAgentId: 'anima',
        ragEnabled: false,
        messages: {},
        threadId: null,
        lastAnalysis: null,
        activeAgent: 'anima'
      });
    } else {
      if (this.state.get('chat.threadId') == null) this.state.set('chat.threadId', null);
      if (this.state.get('chat.lastAnalysis') == null) this.state.set('chat.lastAnalysis', null);
      if (!this.state.get('chat.activeAgent'))
        this.state.set('chat.activeAgent', this.state.get('chat.currentAgentId') || 'anima');
    }
  }

  registerStateChanges() {
    const unsub = this.state.subscribe('chat', (chatState) => {
      if (this.ui && this.container) this.ui.update(this.container, chatState);
    });
    if (typeof unsub === 'function') this.listeners.push(unsub);
  }

  registerEvents() {
    this.listeners.push(this.eventBus.on(EVENTS.CHAT_SEND, this.handleSendMessage.bind(this)));
    this.listeners.push(this.eventBus.on(EVENTS.CHAT_AGENT_SELECTED, this.handleAgentSelected.bind(this)));
    this.listeners.push(this.eventBus.on(EVENTS.CHAT_CLEAR, this.handleClearChat.bind(this)));
    this.listeners.push(this.eventBus.on(EVENTS.CHAT_EXPORT, this.handleExport.bind(this)));
    this.listeners.push(this.eventBus.on(EVENTS.CHAT_RAG_TOGGLED, this.handleRagToggle.bind(this)));

    this.listeners.push(this.eventBus.on('ws:chat_stream_start', this.handleStreamStart.bind(this)));
    this.listeners.push(this.eventBus.on('ws:chat_stream_chunk', this.handleStreamChunk.bind(this)));
    this.listeners.push(this.eventBus.on('ws:chat_stream_end', this.handleStreamEnd.bind(this)));
    this.listeners.push(this.eventBus.on('ws:analysis_status', this.handleAnalysisStatus.bind(this)));
  }

  getCurrentThreadId() { return this.threadId || this.state.get('threads.currentId') || null; }

  hydrateFromThread(thread) {
    const msgsRaw = Array.isArray(thread?.messages) ? [...thread.messages] : [];
    const msgs = msgsRaw.sort((a, b) => (a?.created_at ?? 0) - (b?.created_at ?? 0));
    const buckets = {}; let lastAssistantAgent = null;
    for (const m of msgs) {
      const role = m.role || 'assistant';
      let agentId = m.agent_id || null;
      if (!agentId) agentId = (role === 'assistant')
        ? (lastAssistantAgent || (this.state.get('chat.currentAgentId') || 'anima'))
        : (lastAssistantAgent || null);
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

  handleSendMessage(payload) {
    // 🚦 Gate anti double-clic
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

    const threadId = this.getCurrentThreadId();
    if (threadId) {
      api.appendMessage(threadId, {
        role: 'user',
        content: trimmed,
        agent_id: currentAgentId,
        metadata: { rag: !!ragEnabled }
      }).catch(err => console.error('[Chat] Échec appendMessage(user):', err));
    } else {
      console.warn('[Chat] Aucun threadId disponible — message non persisté côté backend.');
    }

    try {
      // ⚠️ Le bridge WS exige un msg_uid — OK
      this.eventBus.emit('ui:chat:send', {
        text: trimmed,
        agent_id: currentAgentId,
        use_rag: !!ragEnabled,
        msg_uid: userMessage.id
      });
      this._startStreamWatchdog();
    } catch (e) {
      console.error('[Chat] Emission ui:chat:send a échoué', e);
      this._clearStreamWatchdog();
      this.state.set('chat.isLoading', false);
      this._sendLock = false; // libérer en cas d’échec d’émission
      this.showToast('Envoi impossible (WS).');
    }
  }

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
    this.state.set('chat.messages.${agent_id}'.replace('${agent_id}', agent_id), [...curr, agentMessage]);
    this._clearStreamWatchdog();
    this.state.set('chat.isLoading', true);
    // ✅ Reset gate dès que le flux démarre
    this._sendLock = false;
  }

  handleStreamChunk({ id, chunk }) {
    const messages = this.state.get('chat.messages');
    for (const aid in messages) {
      const i = messages[aid].findIndex(m => m.id === id);
      if (i !== -1) {
        messages[aid][i].content = (messages[aid][i].content || '') + (chunk || '');
        this.state.set('chat.messages', { ...messages });
        return;
      }
    }
  }

  handleStreamEnd({ id, agent_id }) {
    const messages = this.state.get('chat.messages');
    for (const aid in messages) {
      const i = messages[aid].findIndex(m => m.id === id);
      if (i !== -1) {
        messages[aid][i] = { ...messages[aid][i], isStreaming: false };
        this.state.set('chat.messages', { ...messages });
        this._clearStreamWatchdog();
        this.state.set('chat.isLoading', false);

        const threadId = this.getCurrentThreadId();
        if (threadId) {
          const finalMsg = messages[aid][i];
          api.appendMessage(threadId, {
            role: 'assistant',
            content: typeof finalMsg.content === 'string' ? finalMsg.content : String(finalMsg.content ?? ''),
            agent_id: finalMsg.agent_id || agent_id || aid
          }).catch(err => console.error('[Chat] Échec appendMessage(assistant):', err));
        } else {
          console.warn('[Chat] Aucun threadId — assistant non persisté.');
        }
        return;
      }
    }
  }

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

  handleAnalysisStatus({ session_id, status, error }) {
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

  _startStreamWatchdog() {
    this._clearStreamWatchdog();
    try {
      this._streamStartTimer = setTimeout(() => {
        if (this.state.get('chat.isLoading')) {
          // Flux jamais démarré : on libère l’UI et le gate
          this.state.set('chat.isLoading', false);
          this._sendLock = false;
          this.showToast('Envoi bloqué (aucun flux démarré).');
        }
      }, this._streamStartTimeoutMs);
    } catch {}
  }

  _clearStreamWatchdog() {
    try {
      if (this._streamStartTimer) { clearTimeout(this._streamStartTimer); this._streamStartTimer = null; }
    } catch {}
  }

  showToast(message) {
    try {
      const el = document.createElement('div'); el.setAttribute('role', 'status');
      el.style.position = 'fixed'; el.style.right = '20px'; el.style.bottom = '20px';
      el.style.padding = '12px 14px'; el.style.borderRadius = '12px';
      el.style.background = '#121212'; el.style.color = '#fff'; el.style.boxShadow = '0 6px 14px rgba(0,0,0,.3)';
      el.style.font = '14px/1.2 system-ui,-apple-system,Segoe UI,Roboto,Ubuntu'; el.style.opacity = '0'; el.style.transform = 'translateY(6px)'; el.style.transition = 'opacity .15s, transform .15s';
      el.textContent = message; document.body.appendChild(el);
      requestAnimationFrame(() => { el.style.opacity = '1'; el.style.transform = 'translateY(0)'; });
      setTimeout(() => { el.style.opacity = '0'; el.style.transform = 'translateY(6px)'; setTimeout(() => el.remove(), 180); }, 2200);
    } catch {}
  }
}
