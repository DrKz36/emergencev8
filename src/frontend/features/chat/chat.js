/**
 * @module features/chat/chat
 * @description Module Chat - V24.0 "StrictHydrate"
 * - Persistance inter-session (Threads API) côté front.
 * - Hydratation stricte par agent_id + idempotente (rebuild à blanc).
 * - Dédoublonnage agent_selected.
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
    this.threadId = null;           // fixé par threads:ready / state
    this.loadedThreadId = null;     // évite re-hydratations inutiles
  }

  /* ----------------------------- Lifecycle ----------------------------- */

  init() {
    if (this.isInitialized) return;
    this.ui = new ChatUI(this.eventBus, this.state);
    this.initializeState();
    this.registerStateChanges();
    this.registerEvents();
    this.isInitialized = true;
    console.log('✅ ChatModule V24.0 (StrictHydrate) initialisé.');
  }

  mount(container) {
    this.container = container;
    this.ui.render(this.container, this.state.get('chat'));

    // 🔁 Rattrapage: si App a déjà chargé le thread avant que Chat s'abonne,
    // on hydrate immédiatement depuis le state (sans attendre l’event).
    const currentId = this.getCurrentThreadId();
    if (currentId) {
      const cached = this.state.get(`threads.map.${currentId}`);
      if (cached && cached.messages && this.loadedThreadId !== currentId) {
        this.loadedThreadId = currentId;
        this.threadId = currentId;
        this.state.set('chat.threadId', currentId); // utile si l’UI s’y réfère
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
        threadId: null,      // ➕ pour certaines UIs
      });
    } else if (this.state.get('chat.threadId') == null) {
      this.state.set('chat.threadId', null);
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

    // Threads (depuis App)
    this.listeners.push(this.eventBus.on('threads:ready', ({ id }) => {
      if (id && typeof id === 'string') {
        this.threadId = id;
        this.state.set('threads.currentId', id);
        this.state.set('chat.threadId', id); // ➕ garde-fou pour l’UI
        console.log('[Chat] threads:ready → threadId =', id);

        // Si App a déjà mis le thread en cache, hydrate sans attendre 'threads:loaded'
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
        if (this.loadedThreadId === thread.id) return; // évite double hydratation
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

  /**
   * Hydrate l'état UI à partir d'un objet thread { id, messages: [...] }.
   * - Partitionne STRICTEMENT par agent_id (assistant ET user).
   * - Fallback legacy: dernier assistant.agent_id vu, sinon 'global'.
   * - Idempotent: reconstruit à BLANC (aucun merge).
   */
  hydrateFromThread(thread) {
    const msgsRaw = Array.isArray(thread?.messages) ? [...thread.messages] : [];
    // Tri chronologique croissant si timestamps fournis
    const msgs = msgsRaw.sort((a, b) => {
      const ta = (a?.created_at ?? 0); const tb = (b?.created_at ?? 0);
      return ta - tb;
    });

    const buckets = {}; // rebuild à blanc
    let lastAssistantAgent = null;

    for (const m of msgs) {
      const role = m.role || 'assistant';
      // Source de vérité : agent_id du message (user & assistant).
      let agentId = m.agent_id || null;

      // Fallback legacy si agent_id manquant
      if (!agentId) {
        if (role === 'assistant') {
          agentId = lastAssistantAgent || (this.state.get('chat.currentAgentId') || 'anima');
        } else {
          // user sans agent_id → utiliser dernier assistant vu si possible
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

    // ⛔️ Pas de merge: remplace entièrement
    this.state.set('chat.messages', buckets);

    // Observabilité simple
    const dist = Object.fromEntries(Object.entries(buckets).map(([k, v]) => [k, v.length]));
    console.debug('[Chat] Répartition messages par agent', dist);
  }

  /* ----------------------------- Handlers ------------------------------ */

  handleSendMessage(payload) {
    const text = typeof payload === 'string' ? payload : (payload && payload.text) || '';
    const trimmed = (text || '').trim();
    if (!trimmed) return;

    const { currentAgentId, ragEnabled } = this.state.get('chat');

    const userMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: trimmed,
      agent_id: currentAgentId
    };

    const currentMessages = this.state.get(`chat.messages.${currentAgentId}`) || [];
    this.state.set(`chat.messages.${currentAgentId}`, [...currentMessages, userMessage]);
    this.state.set('chat.isLoading', true);

    // 1) Persistance immédiate côté backend (user)
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

    // 2) Déclenche le streaming via WebSocket
    this.eventBus.emit(EVENTS.WS_SEND, {
      type: 'chat.message',
      payload: { text: trimmed, agent_id: currentAgentId, use_rag: !!ragEnabled }
    });
  }

  handleStreamStart({ agent_id, id }) {
    const agentMessage = { id, role: 'assistant', content: '', agent_id, isStreaming: true };
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
    if (prev === agentId) {
      // Dédoublonnage (évite bruit de boot)
      return;
    }
    this.state.set('chat.currentAgentId', agentId);
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
}
