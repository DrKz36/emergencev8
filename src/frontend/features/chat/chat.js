/**
 * @module features/chat/chat
 * @description Module Chat - V24.3 "Single-Emit + ActiveAgent"
 * - Persistance inter-session (Threads API) côté front.
 * - Hydratation stricte par agent_id + idempotente (rebuild à blanc).
 * - Dédoublonnage agent_selected.
 * - Toast léger sur ws:analysis_status.
 * - ✅ created_at côté UI (user + stream start) pour affichage horodatage.
 * - ✅ NEW: plus d’émission WS_SEND (single-emit via ui:chat:send) + state.chat.activeAgent publié.
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

    // Threads
    this.threadId = null;
    this.loadedThreadId = null;

    // Anti-dup toast
    this._lastToastAt = 0;
  }

  /* ----------------------------- Lifecycle ----------------------------- */

  init() {
    if (this.isInitialized) return;
    this.ui = new ChatUI(this.eventBus, this.state);
    this.initializeState();
    this.registerStateChanges();
    this.registerEvents();
    this.isInitialized = true;
    console.log('✅ ChatModule V24.3 (Single-Emit + ActiveAgent) initialisé.');
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
    this.listeners.forEach(unsub => { if (typeof unsub === 'function') try { unsub(); } catch {} });
    this.listeners = [];
    this.container = null;
  }

  /* ------------------------------ State -------------------------------- */

  initializeState() {
    if (!this.state.get('chat')) {
      this.state.set('chat', {
        isLoading: false,
        currentAgentId: 'anima',
        ragEnabled: false,
        messages: {},        // { [agentId]: Message[] }
        threadId: null,
        lastAnalysis: null,
        activeAgent: 'anima', /* ✅ NEW */
      });
    } else {
      if (this.state.get('chat.threadId') == null) this.state.set('chat.threadId', null);
      if (this.state.get('chat.lastAnalysis') == null) this.state.set('chat.lastAnalysis', null);
      if (!this.state.get('chat.activeAgent')) this.state.set('chat.activeAgent', this.state.get('chat.currentAgentId') || 'anima');
    }
  }

  registerStateChanges() {
    const unsubscribe = this.state.subscribe('chat', (chatState) => {
      if (this.ui && this.container) {
        this.ui.update(this.container, chatState);
      }
    });
    if (typeof unsubscribe === 'function') this.listeners.push(unsubscribe);
  }

  /* ------------------------------ Events ------------------------------- */

  registerEvents() {
    // UI
    this.listeners.push(this.eventBus.on(EVENTS.CHAT_SEND, this.handleSendMessage.bind(this)));
    this.listeners.push(this.eventBus.on(EVENTS.CHAT_AGENT_SELECTED, this.handleAgentSelected.bind(this)));
    this.listeners.push(this.eventBus.on(EVENTS.CHAT_CLEAR, this.handleClearChat.bind(this)));
    this.listeners.push(this.eventBus.on(EVENTS.CHAT_EXPORT, this.handleExport.bind(this)));
    this.listeners.push(this.eventBus.on(EVENTS.CHAT_RAG_TOGGLED, this.handleRagToggle.bind(this)));

    // WebSocket streaming
    this.listeners.push(this.eventBus.on('ws:chat_stream_start', this.handleStreamStart.bind(this)));
    this.listeners.push(this.eventBus.on('ws:chat_stream_chunk', this.handleStreamChunk.bind(this)));
    this.listeners.push(this.eventBus.on('ws:chat_stream_end', this.handleStreamEnd.bind(this)));
    // état d'analyse (toast)
    this.listeners.push(this.eventBus.on('ws:analysis_status', this.handleAnalysisStatus.bind(this)));

    // Threads (depuis App)
    this.listeners.push(this.eventBus.on('threads:ready', ({ id }) => {
      if (id && typeof id === 'string') {
        this.threadId = id;
        this.state.set('threads.currentId', id);
        this.state.set('chat.threadId', id);
        console.log('[Chat] threads:ready → threadId =', id);

        const cached = this.state.get(`threads.map.${id}`);
        if (cached && cached.messages && this.loadedThreadId !== id) {
          this.loadedThreadId = id;
          this.hydrateFromThread(cached);
          console.log('[Chat] threads:ready → hydratation immédiate depuis state pour', id);
        }
      }
    }));

    this.listeners.push(this.eventBus.on('threads:loaded', (thread) => {
      try {
        if (!thread || !thread.id) return;
        if (this.loadedThreadId === thread.id) return;
        this.loadedThreadId = thread.id;
        this.threadId = thread.id;
        this.state.set('chat.threadId', thread.id);
        this.hydrateFromThread(thread);
        console.log('[Chat] threads:loaded → hydratation terminée pour', thread.id);
      } catch (e) {
        console.error('[Chat] Erreur hydratation threads:loaded', e);
      }
    }));
  }

  /* --------------------------- Thread helpers -------------------------- */

  getCurrentThreadId() {
    return this.threadId || this.state.get('threads.currentId') || null;
  }

  hydrateFromThread(thread) {
    const msgsRaw = Array.isArray(thread?.messages) ? [...thread.messages] : [];
    const msgs = msgsRaw.sort((a, b) => {
      const ta = (a?.created_at ?? 0); const tb = (b?.created_at ?? 0);
      return ta - tb;
    });

    const buckets = {};
    let lastAssistantAgent = null;

    for (const m of msgs) {
      const role = m.role || 'assistant';
      let agentId = m.agent_id || null;

      if (!agentId) {
        if (role === 'assistant') {
          agentId = lastAssistantAgent || (this.state.get('chat.currentAgentId') || 'anima');
        } else {
          agentId = lastAssistantAgent || null;
        }
      }

      if (!agentId) agentId = 'global';
      if (role === 'assistant' && agentId) lastAssistantAgent = agentId;

      if (!buckets[agentId]) buckets[agentId] = [];
      buckets[agentId].push({
        id: m.id || `${role}-${m.created_at || Date.now()}`,
        role,
        content: typeof m.content === 'string' ? m.content : JSON.stringify(m.content ?? ''),
        agent_id: agentId,
        created_at: m.created_at
      });
    }

    this.state.set('chat.messages', buckets);
    const dist = Object.fromEntries(Object.entries(buckets).map(([k, v]) => [k, v.length]));
    console.debug('[Chat] Répartition messages par agent', dist);
  }

  /* ----------------------------- Handlers ------------------------------ */

  handleSendMessage(payload) {
    const text = typeof payload === 'string' ? payload : (payload && payload.text) || '';
    const trimmed = (text || '').trim();
    if (!trimmed) return;

    const { currentAgentId, ragEnabled } = this.state.get('chat');

    // ✅ publier l'agent actif pour le WS (fallback fiable)
    this.state.set('chat.activeAgent', currentAgentId);

    const userMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: trimmed,
      agent_id: currentAgentId,
      created_at: Date.now()
    };

    const currentMessages = this.state.get(`chat.messages.${currentAgentId}`) || [];
    this.state.set(`chat.messages.${currentAgentId}`, [...currentMessages, userMessage]);
    this.state.set('chat.isLoading', true);

    // Persistance immédiate côté backend (user)
    const threadId = this.getCurrentThreadId();
    if (!threadId) {
      console.warn('[Chat] Aucun threadId disponible — message non persisté côté backend.');
    } else {
      api.appendMessage(threadId, {
        role: 'user',
        content: trimmed,
        agent_id: currentAgentId,
        metadata: { rag: !!ragEnabled }
      }).catch(err => console.error('[Chat] Échec appendMessage(user):', err));
    }

    // ❌ [SUPPRIMÉ] : double émission. Le WS écoute déjà 'ui:chat:send'.
    // this.eventBus.emit(EVENTS.WS_SEND, { type: 'chat.message', payload: { text: trimmed, agent_id: currentAgentId, use_rag: !!ragEnabled } });
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
    const currentMessages = this.state.get(`chat.messages.${agent_id}`) || [];
    this.state.set('chat.messages.${agent_id}'.replace('${agent_id}', agent_id), [...currentMessages, agentMessage]);
    this.state.set('chat.isLoading', true);
  }

  handleStreamChunk({ id, chunk }) {
    const messages = this.state.get('chat.messages');
    for (const agentId in messages) {
      const idx = messages[agentId].findIndex(m => m.id === id);
      if (idx !== -1) {
        messages[agentId][idx].content = (messages[agentId][idx].content || '') + (chunk || '');
        this.state.set('chat.messages', { ...messages });
        return;
      }
    }
  }

  handleStreamEnd({ id, agent_id }) {
    const messages = this.state.get('chat.messages');
    for (const agentId in messages) {
      const idx = messages[agentId].findIndex(m => m.id === id);
      if (idx !== -1) {
        const finalMsg = { ...messages[agentId][idx], isStreaming: false };
        messages[agentId][idx] = finalMsg;
        this.state.set('chat.messages', { ...messages });
        this.state.set('chat.isLoading', false);

        // Persistance backend (assistant)
        const threadId = this.getCurrentThreadId();
        if (!threadId) {
          console.warn('[Chat] Aucun threadId — assistant non persisté.');
        } else {
          api.appendMessage(threadId, {
            role: 'assistant',
            content: typeof finalMsg.content === 'string' ? finalMsg.content : String(finalMsg.content ?? ''),
            agent_id: finalMsg.agent_id || agent_id || agentId
          }).catch(err => console.error('[Chat] Échec appendMessage(assistant):', err));
        }
        return;
      }
    }
  }

  handleAgentSelected(agentId) {
    const prev = this.state.get('chat.currentAgentId');
    if (prev === agentId) return;
    this.state.set('chat.currentAgentId', agentId);
    this.state.set('chat.activeAgent', agentId); // ✅ publier l’agent actif pour le WS
  }

  handleClearChat() {
    const agentId = this.state.get('chat.currentAgentId');
    this.state.set(`chat.messages.${agentId}`, []);
  }

  handleExport() {
    const { currentAgentId, messages } = this.state.get('chat');
    const conv = messages[currentAgentId] || [];
    const you = this.state.get('user.id') || 'Vous';
    const text = conv
      .map(m => `${m.role === 'user' ? you : (m.agent_id || 'Assistant')}: ${typeof m.content === 'string' ? m.content : JSON.stringify(m.content || '')}`)
      .join('\n\n');
    const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = `chat_${currentAgentId}_${Date.now()}.txt`;
    document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
  }

  handleRagToggle() {
    const current = !!this.state.get('chat.ragEnabled');
    this.state.set('chat.ragEnabled', !current);
  }

  // toast mémoire
  handleAnalysisStatus({ session_id, status, error }) {
    this.state.set('chat.lastAnalysis', {
      session_id: session_id || null,
      status: status || 'unknown',
      error: error || null,
      at: Date.now()
    });
    console.log('[Chat] ws:analysis_status', { session_id, status, error });

    const now = Date.now();
    if (now - this._lastToastAt < 1000) return; // anti-spam
    this._lastToastAt = now;

    if (status === 'completed') {
      this.showToast('Mémoire consolidée ✓');
    } else if (status === 'failed') {
      this.showToast('Analyse mémoire : échec');
    }
  }

  // Petit toast DOM autonome
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
      el.style.font = '14px/1.2 system-ui, -apple-system, Segoe UI, Roboto, Ubuntu';
      el.style.opacity = '0';
      el.style.transform = 'translateY(6px)';
      el.style.transition = 'opacity .15s ease, transform .15s ease';
      el.textContent = message;
      document.body.appendChild(el);
      requestAnimationFrame(() => { el.style.opacity = '1'; el.style.transform = 'translateY(0)'; });
      setTimeout(() => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(6px)';
        setTimeout(() => el.remove(), 180);
      }, 2200);
    } catch {}
  }
}
