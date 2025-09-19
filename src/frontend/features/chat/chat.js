// src/frontend/features/chat/chat.js
// Chat Module + UI — V28.3.2
// - Restaure l’affichage du module Dialogues avec logs détaillés
// - CSS hook correct: <div class="messages" id="chat-messages"> (aligne chat.css)
// - Mount-safe: rend dans le container fourni par App.showModule()
// - Aucune dépendance globale à #chat-root

import { EVENTS, AGENTS } from '../../shared/constants.js';
import { ChatUI } from './chat-ui.js';
import { MemoryCenter } from '../memory/memory-center.js';
import { api } from '../../shared/api-client.js';

/* ------------------------- ChatModule ------------------------- */
export default class ChatModule {
  constructor(eventBus, stateManager) {
    this.eventBus = eventBus;
    this.state = stateManager;
    this.ui = new ChatUI(eventBus, stateManager);
    this.memoryCenter = new MemoryCenter(eventBus, stateManager);
    this.container = null;
    this.inited = false;
    this._activeStreams = new Map();
    this._memoryAnalysisInFlight = false;
  }

  init() {
    if (this.inited) return;
    this._wireState();
    this._wireWS();
    this._wireMemoryEvents();
    this.memoryCenter?.init?.();
    this.inited = true;
    console.log('[ChatModule] V28.3.2 initialized (handlers & state).');
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
  _wireMemoryEvents() {
    this.eventBus.on?.('memory:tend', (payload = {}) => this._runMemoryAnalysis(!!payload.force));
    this.eventBus.on?.('memory:clear', () => this._clearMemory());
    this.eventBus.on?.('memory:center:open', () => {
      try { this.memoryCenter?.open?.(); }
      catch (err) { console.warn('[ChatModule] memory center open failed', err); }
    });
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

  _resolveSessionId() {
    try {
      const sid = this.state?.get?.('websocket.sessionId');
      if (sid) return String(sid);
    } catch (_) {}
    try {
      const raw = localStorage.getItem('emergenceState-V14');
      if (raw) {
        const parsed = JSON.parse(raw);
        const sid = parsed?.websocket?.sessionId;
        if (sid) return String(sid);
      }
    } catch (_) {}
    return null;
  }

  async _runMemoryAnalysis(force = false) {
    if (this._memoryAnalysisInFlight) {
      this.eventBus.emit?.('ui:toast', { kind: 'info', text: 'Analyse memoire deja en cours.' });
      return;
    }
    const sessionId = this._resolveSessionId();
    if (!sessionId) {
      this.eventBus.emit?.('ui:toast', { kind: 'error', text: 'Session introuvable : analyse memoire impossible.' });
      return;
    }

    this._memoryAnalysisInFlight = true;
    const startedAt = Date.now();
    try {
      this.state.set('chat.lastAnalysis', { status: 'running', force, startedAt });
      this.ui.update(this.container, { lastAnalysis: this.state.get('chat.lastAnalysis') });

      const result = await api.analyzeMemory({ session_id: sessionId, force });
      const completedAt = Date.now();
      const payload = { ...result, completedAt, force };
      this.state.set('chat.lastAnalysis', payload);

      const currentStats = this.state.get('chat.memoryStats') || { has_stm: false, ltm_items: 0, injected: false };
      const analysis = (result && result.analysis) || {};
      const metadata = (result && result.metadata) || {};
      const summaryText = (analysis.summary || metadata.summary || '').toString();
      const hasSummary = summaryText.trim().length > 0;
      const nextStats = {
        ...currentStats,
        has_stm: hasSummary,
      };
      if (typeof metadata.ltm_items === 'number' && Number.isFinite(metadata.ltm_items)) {
        nextStats.ltm_items = Number(metadata.ltm_items);
      }
      this.state.set('chat.memoryStats', nextStats);
      this.state.set('chat.memoryBannerAt', completedAt);
      this.ui.update(this.container, {
        memoryStats: nextStats,
        memoryBannerAt: completedAt,
        lastAnalysis: payload,
      });

      if (result && result.status === 'skipped') {
        const reason = result.reason || 'no_changes';
        let message = 'Aucune mise a jour memoire.';
        if (reason === 'already_analyzed') message = 'Memoire deja analysee.';
        if (reason === 'no_history') message = 'Aucun historique a analyser.';
        this.eventBus.emit?.('ui:toast', { kind: 'info', text: message });
      } else {
        this.eventBus.emit?.('ui:toast', { kind: 'success', text: 'Analyse memoire terminee.' });
        try {
          if (typeof api.tendMemory === 'function') {
            api.tendMemory().catch(() => {});
          }
        } catch (err) {
          console.debug('[ChatModule] tendMemory optional call failed', err);
        }
      }
    } catch (err) {
      console.error('[ChatModule] analyse memoire echouee', err);
      const message = (err && err.message) ? err.message : 'Erreur inconnue';
      this.state.set('chat.lastAnalysis', { status: 'error', error: message, at: Date.now(), force });
      this.eventBus.emit?.('ui:toast', { kind: 'error', text: 'Analyse memoire impossible: ' + message });
    } finally {
      this._memoryAnalysisInFlight = false;
      this.ui.update(this.container, { lastAnalysis: this.state.get('chat.lastAnalysis') });
    }
  }

  async _clearMemory() {
    try {
      await api.clearMemory();
      const clearedAt = Date.now();
      const resetStats = { has_stm: false, ltm_items: 0, injected: false };
      this.state.set('chat.memoryStats', resetStats);
      this.state.set('chat.memoryBannerAt', null);
      this.state.set('chat.lastAnalysis', { status: 'cleared', clearedAt });
      this.ui.update(this.container, {
        memoryStats: resetStats,
        memoryBannerAt: null,
        lastAnalysis: this.state.get('chat.lastAnalysis'),
      });
      this.eventBus.emit?.('ui:toast', { kind: 'success', text: 'Memoire de session effacee.' });
    } catch (err) {
      console.error('[ChatModule] clearMemory echouee', err);
      const message = (err && err.message) ? err.message : 'Erreur inconnue';
      this.eventBus.emit?.('ui:toast', { kind: 'error', text: 'Effacement memoire impossible: ' + message });
    }
  }

  _refreshUi(agentId, messagesSnapshot) {
    if (!this.container) return;
    const currentAgentId = agentId ? this._normalizeAgentId(agentId) : this._currentAgentId();
    const messages = messagesSnapshot || this.state.get('chat.messages') || {};
    this.ui.update(this.container, {
      messages,
      currentAgentId,
    });
  }

}
