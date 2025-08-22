/**
 * @module features/chat/chat
 * @description ChatModule V23.1 — envoi WS 'chat:send' + update UI + handlers streaming/RAG/mémoire
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

    this.handleSendMessage   = this.handleSendMessage.bind(this);
    this.handleAgentSelected = this.handleAgentSelected.bind(this);
    this.handleClearChat     = this.handleClearChat.bind(this);
    this.handleExport        = this.handleExport.bind(this);
    this.handleRagToggle     = this.handleRagToggle.bind(this);

    // WS inbound
    this.handleStreamStart   = this.handleStreamStart.bind(this);
    this.handleStreamChunk   = this.handleStreamChunk.bind(this);
    this.handleStreamEnd     = this.handleStreamEnd.bind(this);
    this.handleRagStatus     = this.handleRagStatus.bind(this);
    this.handleChatSources   = this.handleChatSources.bind(this);
    this.handleMemoryStatus  = this.handleMemoryStatus.bind(this);
    this.handleMemorySources = this.handleMemorySources.bind(this);

    console.log('✅ ChatModule V23.1 prêt.');
  }

  init() {
    if (this.isInitialized) return;
    this.ui = new ChatUI(this.eventBus, this.state);
    this.initializeState();
    this.registerStateChanges();
    this.registerEvents();
    this.isInitialized = true;
    console.log('✅ ChatModule V23.1 initialisé.');
  }

  mount(container) {
    this.container = container;
    this.ui.render(this.container, this.state.get('chat'));
  }

  destroy() {
    this.listeners.forEach(unsub => { if (typeof unsub === 'function') { try { unsub(); } catch {} } });
    this.listeners = [];
    this.container = null;
  }

  initializeState() {
    const current = this.state.get('chat') || {};
    const base = {
      currentAgentId: 'anima',
      ragEnabled: false,
      isLoading: false,
      messages: {},           // { [agentId]: [{id,role,content,ts,isStreaming}] }
      ragStatus: {},          // { [agentId]: {...} }
      ragSources: {},         // { [agentId]: [] }
      memoryStatus: {},       // { [agentId]: {...} }
      memorySources: {},      // { [agentId]: [] }
    };
    const merged = { ...base, ...current };
    ['anima','neo','nexus'].forEach(a => { if (!Array.isArray(merged.messages[a])) merged.messages[a] = []; });
    this.state.set('chat', merged);
  }

  registerStateChanges() {
    const unsubscribe = this.state.subscribe('chat', (chatState) => {
      if (!this.container) return;
      try { this.ui.update(this.container, chatState); }
      catch (e) { console.error('[ChatModule] update error:', e); }
    });
    if (typeof unsubscribe === 'function') this.listeners.push(unsubscribe);
  }

  registerEvents() {
    // UI → ChatModule
    this.listeners.push(this.eventBus.on(EVENTS.CHAT_SEND, this.handleSendMessage));
    this.listeners.push(this.eventBus.on(EVENTS.CHAT_AGENT_SELECTED, this.handleAgentSelected));
    this.listeners.push(this.eventBus.on(EVENTS.CHAT_CLEAR, this.handleClearChat));
    this.listeners.push(this.eventBus.on(EVENTS.CHAT_EXPORT, this.handleExport));
    this.listeners.push(this.eventBus.on(EVENTS.CHAT_RAG_TOGGLED, this.handleRagToggle));

    // WS → ChatModule
    this.listeners.push(this.eventBus.on(EVENTS.WS_CHAT_STREAM_START, this.handleStreamStart));
    this.listeners.push(this.eventBus.on(EVENTS.WS_CHAT_STREAM_CHUNK, this.handleStreamChunk));
    this.listeners.push(this.eventBus.on(EVENTS.WS_CHAT_STREAM_END, this.handleStreamEnd));
    this.listeners.push(this.eventBus.on(EVENTS.WS_RAG_STATUS, this.handleRagStatus));
    this.listeners.push(this.eventBus.on(EVENTS.WS_CHAT_SOURCES, this.handleChatSources));
    this.listeners.push(this.eventBus.on(EVENTS.WS_MEMORY_STATUS, this.handleMemoryStatus));
    this.listeners.push(this.eventBus.on(EVENTS.WS_MEMORY_SOURCES, this.handleMemorySources));
  }

  // ────────────── UI ──────────────
  handleSendMessage({ text }) {
    const trimmed = (text || '').trim();
    if (!trimmed) return;

    const { currentAgentId, ragEnabled } = this.state.get('chat');

    // push user message local
    const userMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: trimmed,
      ts: new Date().toISOString()
    };
    const currentList = this.state.get(`chat.messages.${currentAgentId}`) || [];
    this.state.set(`chat.messages.${currentAgentId}`, [...currentList, userMessage]);
    this.state.set('chat.isLoading', true);

    // ✅ ENVOI WS — type corrigé (colon) : 'chat:send'
    this.eventBus.emit(EVENTS.WS_SEND, {
      type: 'chat:send',
      payload: { text: trimmed, agent_id: currentAgentId, use_rag: !!ragEnabled }
    });
  }

  handleAgentSelected(agentId) {
    if (!agentId) return;
    this.state.set('chat.currentAgentId', agentId);
  }

  handleClearChat() {
    const agentId = this.state.get('chat.currentAgentId');
    this.state.set(`chat.messages.${agentId}`, []);
    const cur = this.state.get('chat');
    this.state.set('chat.ragStatus',     { ...(cur.ragStatus || {}),     [agentId]: undefined });
    this.state.set('chat.ragSources',    { ...(cur.ragSources || {}),    [agentId]: [] });
    this.state.set('chat.memoryStatus',  { ...(cur.memoryStatus || {}),  [agentId]: undefined });
    this.state.set('chat.memorySources', { ...(cur.memorySources || {}), [agentId]: [] });
  }

  handleExport() {
    const agentId = this.state.get('chat.currentAgentId');
    const msgs = this.state.get(`chat.messages.${agentId}`) || [];
    const lines = msgs.map(m => `[${m.ts}] ${m.role.toUpperCase()}: ${m.content}`).join('\n\n');
    const blob = new Blob([lines], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = `chat_${agentId}_${Date.now()}.txt`;
    document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
  }

  handleRagToggle() {
    const cur = !!this.state.get('chat.ragEnabled');
    this.state.set('chat.ragEnabled', !cur);
  }

  // ────────────── WS ──────────────
  _appendAssistantChunk(agentId, id, chunk, end = false) {
    const list = this.state.get(`chat.messages.${agentId}`) || [];
    let idx = list.findIndex(m => m.id === id);
    if (idx === -1) {
      list.push({ id, role: 'assistant', content: '', ts: new Date().toISOString(), isStreaming: true, agent_id: agentId });
      idx = list.length - 1;
    }
    const msg = { ...list[idx] };
    msg.content = (msg.content || '') + (chunk || '');
    if (end) msg.isStreaming = false;
    list[idx] = msg;
    this.state.set(`chat.messages.${agentId}`, [...list]);
  }

  handleStreamStart({ agent_id, id }) {
    const agentId = agent_id || this.state.get('chat.currentAgentId');
    this._appendAssistantChunk(agentId, id, '');
  }

  handleStreamChunk({ agent_id, id, delta }) {
    const agentId = agent_id || this.state.get('chat.currentAgentId');
    this._appendAssistantChunk(agentId, id, delta || '');
  }

  handleStreamEnd({ agent_id, id }) {
    const agentId = agent_id || this.state.get('chat.currentAgentId');
    this._appendAssistantChunk(agentId, id, '', true);
    this.state.set('chat.isLoading', false);
  }

  handleRagStatus(status) {
    const agentId = this.state.get('chat.currentAgentId');
    const cur = this.state.get('chat');
    this.state.set('chat.ragStatus', { ...(cur.ragStatus || {}), [agentId]: status });
  }

  handleChatSources({ agent_id, sources }) {
    const agentId = agent_id || this.state.get('chat.currentAgentId');
    const cur = this.state.get('chat');
    this.state.set('chat.ragSources', { ...(cur.ragSources || {}), [agentId]: Array.isArray(sources) ? sources : [] });
  }

  handleMemoryStatus({ agent_id, status }) {
    const agentId = agent_id || this.state.get('chat.currentAgentId');
    const cur = this.state.get('chat');
    this.state.set('chat.memoryStatus', { ...(cur.memoryStatus || {}), [agentId]: status });
  }

  handleMemorySources({ agent_id, sources }) {
    const agentId = agent_id || this.state.get('chat.currentAgentId');
    const cur = this.state.get('chat');
    this.state.set('chat.memorySources', { ...(cur.memorySources || {}), [agentId]: Array.isArray(sources) ? sources : [] });
  }
}
