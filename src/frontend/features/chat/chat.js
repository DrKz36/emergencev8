// src/frontend/features/chat/chat.js
// ChatModule V26.0 — mount() + écoute EVENTS.CHAT_SEND → handleSendMessage()
// + subscribe live au state pour rafraîchir ChatUI
// Dépendances: state-manager (get/set), eventBus, websocket client global (optionnel).

import { EVENTS, AGENTS } from '../../shared/constants.js';
import { ChatUI } from './chat-ui.js';

export default class ChatModule {
  constructor(eventBus, state) {
    this.eventBus = eventBus;
    this.state = state;

    // UI
    this.container = null;
    this.ui = null;

    // Locks & temporaires
    this._sendLock = false;
    this._assistantPersistedIds = new Set();

    // Attente courte pour laisser s’ouvrir le WS si nécessaire
    this._wsConnectWaitMs = 900;

    // Watchdog flux
    this._watchdog = null;
    this._watchdogMs = 25000;

    // Binders
    this._unbinders = [];
    this._offState = null;

    console.log('✅ ChatModule V26.0 initialisé (mount + bindings).');
  }

  async init() {
    this._bindEventBus();

    // Agent actif par défaut si absent (cohérent avec StateManager V15.4)
    const active = (this.state.get('chat.activeAgent') || 'anima').toLowerCase();
    this.state.set('chat.activeAgent', active);
    return this;
  }

  /** Appelé par App.showModule(moduleId) */
  mount(container) {
    if (!container) return;
    this.container = container;

    if (!this.ui) {
      this.ui = new ChatUI(this.eventBus, this.state);
    }
    // premier render
    this.ui.render(container, this._collectChatState());

    // subscribe aux changements du sous-état chat.*
    if (typeof this.state.subscribe === 'function') {
      this._offState = this.state.subscribe('chat', () => {
        try {
          this.ui.update(this.container, this._collectChatState());
        } catch (e) {
          console.warn('[ChatModule] update UI failed:', e);
        }
      });
    }

    // Optionnel: s’assurer que le WS est prêt
    try { window?.wsClient?.connect?.(); } catch {}
  }

  destroy() {
    try { this._unbinders.forEach(u => u && u()); } catch {}
    this._unbinders = [];
    if (typeof this._offState === 'function') {
      try { this._offState(); } catch {}
      this._offState = null;
    }
    this._clearStreamWatchdog();
    this.container = null;
  }

  /* ------------------------------------------------------------------ */
  /* UI/API                                                              */
  /* ------------------------------------------------------------------ */

  async handleSendMessage(textRaw) {
    const trimmed = String(textRaw ?? '').trim();
    if (!trimmed) return;
    if (this._sendLock) return;
    this._sendLock = true;

    // Récupère l’agent courant depuis l’état
    const chatState = this.state.get('chat') || {};
    const currentAgentId = (chatState.activeAgent || 'anima').toLowerCase();
    const ragEnabled = !!chatState.ragEnabled;

    // Source de vérité
    this.state.set('chat.activeAgent', currentAgentId);

    // Ajout local du message USER
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

    // Laisse au WS le temps de s’ouvrir (le client a une queue, mais on réduit les races)
    await this._waitForWS(this._wsConnectWaitMs);

    try {
      // Passe par l’EventBus → WebSocketClient V22.3 (frame {type:'chat.message', payload:{...}})
      this.eventBus.emit(EVENTS.CHAT_SEND || 'ui:chat:send', {
        text: trimmed,
        agent_id: currentAgentId,
        use_rag: ragEnabled,
        msg_uid: userMessage.id,
        __enriched: true
      });

      // Armement watchdog (si aucun ws:chat_stream_start ne survient)
      this._pendingMsg = { id: userMessage.id, agent_id: currentAgentId, text: trimmed, triedRest: false };
      this._startStreamWatchdog();
    } catch (e) {
      console.error('[Chat] Emission ui:chat:send a échoué', e);
      this._clearStreamWatchdog();
      this.state.set('chat.isLoading', false);
      this._sendLock = false;
      this._toast('Envoi impossible (WS).');
    } finally {
      this._sendLock = false;
    }
  }

  clearConversation(agentId = null) {
    const ag = (agentId || this.state.get('chat.activeAgent') || 'anima').toLowerCase();
    this.state.set(`chat.messages.${ag}`, []);
  }

  toggleRag(on) {
    const curr = !!this.state.get('chat.ragEnabled');
    const next = (typeof on === 'boolean') ? !!on : !curr;
    this.state.set('chat.ragEnabled', next);
    this.eventBus.emit?.('ui:toast', { kind: next ? 'success' : 'info', text: next ? 'RAG: ON' : 'RAG: OFF' });
  }

  /* ------------------------------------------------------------------ */
  /* EventBus bindings                                                   */
  /* ------------------------------------------------------------------ */

  _bindEventBus() {
    const on = (evt, fn) => {
      try {
        this.eventBus.on(evt, fn);
        this._unbinders.push(() => this.eventBus.off?.(evt, fn));
      } catch {}
    };

    // ⬅️ (NOUVEAU) l’UI émet EVENTS.CHAT_SEND → on relaie via handleSendMessage()
    on(EVENTS.CHAT_SEND || 'ui:chat:send', (payload = {}) => {
      // Si ChatUI a émis {text, agent:'user'}, on traite ici.
      const txt = (payload && payload.text) ? String(payload.text).trim() : '';
      if (txt) this.handleSendMessage(txt);
    });

    // Sélection d’agent via UI
    on(EVENTS.CHAT_AGENT_SELECTED || 'ui:chat:agent_selected', (agentId) => {
      const ag = String(agentId || 'anima').toLowerCase();
      if (!AGENTS[ag]) return;
      this.state.set('chat.activeAgent', ag);
    });

    // RAG toggle depuis l’UI
    on(EVENTS.CHAT_RAG_TOGGLED || 'ui:chat:rag_toggled', (v = {}) => this.toggleRag(!!(v.enabled ?? v)));

    // --- WS events (provenant de WebSocketClient V22.3) ---
    on('ws:model_info', (payload = {}) => {
      try { this.state.set('chat.modelInfo', payload || {}); } catch {}
      this.eventBus.emit?.('chat:model_info', payload);
    });

    on('ws:model_fallback', (p = {}) => {
      this.eventBus.emit?.('ui:toast', { kind: 'warning', text: `Fallback modèle → ${p.to_provider || '?'} / ${p.to_model || '?'}` });
      this.eventBus.emit?.('chat:model_fallback', p);
    });

    on('ws:memory_banner', (p = {}) => {
      try {
        this.state.set('chat.memoryStats', {
          has_stm: !!p.has_stm,
          ltm_items: Number.isFinite(p.ltm_items) ? p.ltm_items : 0,
          injected: !!p.injected_into_prompt
        });
        this.state.set('chat.memoryBannerAt', Date.now());
      } catch {}
    });

    on('ws:chat_stream_start', (payload = {}) => {
      const agent_id = (payload.agent_id || this.state.get('chat.activeAgent') || 'anima').toLowerCase();
      const tempId = payload.id || `asst-${Date.now()}`;
      const messages = this.state.get(`chat.messages.${agent_id}`) || [];
      const newAsst = { id: tempId, role: 'assistant', agent_id, content: '', created_at: Date.now(), _streaming: true };
      this.state.set(`chat.messages.${agent_id}`, [...messages, newAsst]);
      this._clearStreamWatchdog();
    });

    on('ws:chat_stream_chunk', (payload = {}) => {
      const agent_id = (payload.agent_id || this.state.get('chat.activeAgent') || 'anima').toLowerCase();
      const id = payload.id;
      const chunk = String(payload.chunk || '');
      if (!id || !chunk) return;

      const arr = this.state.get(`chat.messages.${agent_id}`) || [];
      const idx = arr.findIndex(m => m.id === id);
      if (idx >= 0) {
        const m = { ...arr[idx] };
        m.content = (m.content || '') + chunk;
        m._streaming = true;
        const next = arr.slice(); next[idx] = m;
        this.state.set(`chat.messages.${agent_id}`, next);
      }
    });

    on('ws:chat_stream_end', (payload = {}) => {
      const agent_id = (payload.agent_id || this.state.get('chat.activeAgent') || 'anima').toLowerCase();
      const id = payload.id || null;

      if (id && this._assistantPersistedIds.has(id)) return;

      const meta = payload.meta || null;
      try { if (meta) this.state.set('chat.lastMessageMeta', meta); } catch {}
      const messages = this.state.get(`chat.messages.${agent_id}`) || [];

      if (id) {
        const idx = messages.findIndex(m => m.id === id);
        if (idx >= 0) {
          const finalized = { ...messages[idx], _streaming: false };
          if (typeof payload.content === 'string' && payload.content.trim()) finalized.content = payload.content;
          const next = messages.slice(); next[idx] = finalized;
          this.state.set(`chat.messages.${agent_id}`, next);
          this._assistantPersistedIds.add(id);
        } else {
          const fallback = {
            id, role: 'assistant', agent_id,
            content: String(payload.content || ''), created_at: Date.now(), _streaming: false
          };
          this.state.set(`chat.messages.${agent_id}`, [...messages, fallback]);
          this._assistantPersistedIds.add(id);
        }
      } else {
        const push = {
          id: `asst-${Date.now()}`, role: 'assistant', agent_id,
          content: String(payload.content || ''), created_at: Date.now(), _streaming: false
        };
        this.state.set(`chat.messages.${agent_id}`, [...messages, push]);
      }

      this.state.set('chat.isLoading', false);
      this._clearStreamWatchdog();
    });

    on('ws:error', (err = {}) => {
      this._clearStreamWatchdog();
      this.state.set('chat.isLoading', false);
      const msg = (err && (err.message || err.error)) || 'Erreur WebSocket.';
      this._toast(msg, 'error');
      console.warn('[WS:error]', err);
    });

    on('ws:rag_status', (p = {}) => {
      const status = (p.status || 'idle');
      try { this.state.set('chat.ragStatus', status); } catch {}
    });
  }

  /* ------------------------------------------------------------------ */
  /* Helpers                                                             */
  /* ------------------------------------------------------------------ */

  _collectChatState() {
    const st = this.state.get('chat') || {};
    return {
      currentAgentId: (st.activeAgent || 'anima').toLowerCase(),
      ragEnabled: !!st.ragEnabled,
      messages: st.messages || {},
      memoryBannerAt: st.memoryBannerAt || null,
      metrics: st.metrics || { send_count: 0, ws_start_count: 0, last_ttfb_ms: 0, rest_fallback_count: 0, last_fallback_at: null },
      memoryStats: st.memoryStats || { has_stm: false, ltm_items: 0, injected: false },
      modelInfo: st.modelInfo || null,
      lastMessageMeta: st.lastMessageMeta || null
    };
  }

  async _waitForWS(maxWaitMs = 800) {
    const t0 = Date.now();
    const ready = () => {
      try { const ws = window?.wsClient?.websocket || null; return !!ws && ws.readyState === 1; }
      catch { return false; }
    };
    if (ready()) return;
    try { window?.wsClient?.connect?.(); } catch {}
    while ((Date.now() - t0) < maxWaitMs) {
      if (ready()) break;
      await new Promise(r => setTimeout(r, 60));
    }
  }

  _startStreamWatchdog() {
    this._clearStreamWatchdog();
    this._watchdog = setTimeout(() => {
      try {
        const ag = this.state.get('chat.activeAgent') || 'anima';
        console.warn('[Chat] Watchdog: aucun flux reçu dans le délai.');
        this.state.set('chat.isLoading', false);
        this._toast(`Temps d'attente dépassé (agent ${ag}). Réessaie.`);
      } catch {}
    }, this._watchdogMs);
  }

  _clearStreamWatchdog() {
    if (this._watchdog) { clearTimeout(this._watchdog); this._watchdog = null; }
  }

  _toast(text, kind = 'error') {
    try { this.eventBus.emit?.('ui:toast', { kind, text }); } catch {}
  }
}
