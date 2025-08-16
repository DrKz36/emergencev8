/**
 * @module features/chat/chat
 * @description Module Chat - V22.3 "Compat payload + UI.update + destroy sûr"
 */
import { ChatUI } from './chat-ui.js';
import { EVENTS } from '../../shared/constants.js';

export default class ChatModule {
  constructor(eventBus, state) {
    this.eventBus = eventBus;
    this.state = state;
    this.ui = null;
    this.container = null;
    this.listeners = [];
    this.isInitialized = false;

    // NEW: buffer streaming par messageId pour batcher les updates UI
    this._streamBuffers = new Map(); // id -> string
    this._flushScheduled = false;
  }

  init() {
    if (this.isInitialized) return;
    this.ui = new ChatUI(this.eventBus, this.state);
    this.initializeState();
    this.registerStateChanges();
    this.registerEvents();
    this.isInitialized = true;
    console.log('✅ ChatModule V22.3 initialisé.');
  }

  mount(container) {
    this.container = container;
    this.ui.render(this.container, this.state.get('chat'));
  }

  destroy() {
    this.listeners.forEach(unsub => { if (typeof unsub === 'function') try { unsub(); } catch {} });
    this.listeners = [];
    this.container = null;
  }

  initializeState() {
    if (!this.state.get('chat')) {
      this.state.set('chat', {
        isLoading: false,
        currentAgentId: 'anima',
        ragEnabled: false,
        messages: {}, // { [agentId]: Message[] }
      });
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

  registerEvents() {
    this.listeners.push(this.eventBus.on(EVENTS.CHAT_SEND, this.handleSendMessage.bind(this)));
    this.listeners.push(this.eventBus.on(EVENTS.CHAT_AGENT_SELECTED, this.handleAgentSelected.bind(this)));
    this.listeners.push(this.eventBus.on(EVENTS.CHAT_CLEAR, this.handleClearChat.bind(this)));
    this.listeners.push(this.eventBus.on(EVENTS.CHAT_EXPORT, this.handleExport.bind(this)));
    this.listeners.push(this.eventBus.on(EVENTS.CHAT_RAG_TOGGLED, this.handleRagToggle.bind(this)));

    // WebSocket streaming
    this.listeners.push(this.eventBus.on('ws:chat_stream_start', this.handleStreamStart.bind(this)));
    this.listeners.push(this.eventBus.on('ws:chat_stream_chunk', this.handleStreamChunk.bind(this)));
    this.listeners.push(this.eventBus.on('ws:chat_stream_end', this.handleStreamEnd.bind(this)));
  }

  handleSendMessage(payload) {
    const text = typeof payload === 'string' ? payload : (payload && payload.text) || '';
    const trimmed = (text || '').trim();
    if (!trimmed) return;

    const { currentAgentId, ragEnabled } = this.state.get('chat');

    const userMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: trimmed
    };

    const currentMessages = this.state.get(`chat.messages.${currentAgentId}`) || [];
    this.state.set(`chat.messages.${currentAgentId}`, [...currentMessages, userMessage]);
    this.state.set('chat.isLoading', true);

    this.eventBus.emit(EVENTS.WS_SEND, {
      type: 'chat.message',
      payload: { text: trimmed, agent_id: currentAgentId, use_rag: !!ragEnabled }
    });
  }

  handleStreamStart({ agent_id, id }) {
    const agentMessage = { id, role: 'assistant', content: '', agent_id, isStreaming: true };
    const currentMessages = this.state.get(`chat.messages.${agent_id}`) || [];
    this.state.set(`chat.messages.${agent_id}`, [...currentMessages, agentMessage]);
    this.state.set('chat.isLoading', true);
    // reset buffer pour cet id
    this._streamBuffers.set(id, '');
  }

  handleStreamChunk({ id, chunk }) {
    // Bufferise et flush au max 1x par frame
    const prev = this._streamBuffers.get(id) || '';
    this._streamBuffers.set(id, prev + (chunk || ''));
    if (!this._flushScheduled) {
      this._flushScheduled = true;
      // requestAnimationFrame pour grouper tous les chunks de la frame
      (window.requestAnimationFrame || setTimeout)(() => this._flushStreamBuffers(), 16);
    }
  }

  _flushStreamBuffers() {
    if (this._streamBuffers.size === 0) { this._flushScheduled = false; return; }

    const messages = this.state.get('chat.messages');
    let mutated = false;

    // Applique les buffers dans le store
    this._streamBuffers.forEach((bufferText, msgId) => {
      if (!bufferText) return;
      for (const agentId in messages) {
        const arr = messages[agentId] || [];
        const idx = arr.findIndex(m => m.id === msgId);
        if (idx !== -1) {
          const current = arr[idx].content || '';
          arr[idx] = { ...arr[idx], content: current + bufferText };
          mutated = true;
          break;
        }
      }
    });

    // Clear buffers et push un seul set() pour limiter les reflows
    this._streamBuffers.clear();
    this._flushScheduled = false;
    if (mutated) {
      this.state.set('chat.messages', { ...messages });
    }
  }

  handleStreamEnd({ id }) {
    // Flushe toute fin de buffer avant de clore
    this._flushStreamBuffers();

    const messages = this.state.get('chat.messages');
    for (const agentId in messages) {
      const idx = messages[agentId].findIndex(m => m.id === id);
      if (idx !== -1) {
        messages[agentId][idx].isStreaming = false;
        this.state.set('chat.messages', { ...messages });
        this.state.set('chat.isLoading', false);
        return;
      }
    }
  }

  handleAgentSelected(agentId) {
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
