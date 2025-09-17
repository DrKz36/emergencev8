// src/frontend/features/chat/chat.js
// ChatModule V25.5 — guard agent + attente WS courte + watchdog stream
// Aligne les clés d'état sur StateManager V15.4 (chat.*) et consomme les événements WS V22.3.
// Dépendances de fait : state-manager (get/set), eventBus, websocket client global (optionnel).

import { EVENTS, AGENTS } from '../../shared/constants.js'; // icônes/meta agents + noms d'événements

export default class ChatModule {
  constructor(eventBus, state) {
    this.eventBus = eventBus;
    this.state = state;

    // Locks & temporaires
    this._sendLock = false;
    this._pendingMsg = null;
    this._assistantPersistedIds = new Set();

    // Attente courte avant émission (laisser le temps au WS de s'ouvrir si nécessaire)
    this._wsConnectWaitMs = 900;

    // Watchdog flux (ex: si aucun ws:chat_stream_start reçu)
    this._watchdog = null;
    this._watchdogMs = 25000;

    // Bind
    this._unbinders = [];

    console.log('✅ ChatModule V25.5 initialisé (guards + watchdog).');
  }

  async init() {
    this._bindEventBus();
    // Agent actif par défaut si absent (cohérent avec StateManager V15.4)
    const active = this.state.get('chat.activeAgent') || 'anima';
    this.state.set('chat.activeAgent', String(active).toLowerCase());
    return this;
  }

  destroy() {
    try { this._unbinders.forEach(u => u && u()); } catch {}
    this._unbinders = [];
    this._clearStreamWatchdog();
  }

  /* ------------------------------------------------------------------ */
  /* UI/API                                                              */
  /* ------------------------------------------------------------------ */

  async handleSendMessage(textRaw) {
    const trimmed = String(textRaw ?? '').trim();
    if (!trimmed) return;
    if (this._sendLock) return;
    this._sendLock = true;

    // Récupère l’agent courant depuis l’état, garde une valeur valide
    const chatState = this.state.get('chat') || {};
    const currentAgentId = (chatState.currentAgentId || chatState.activeAgent || 'anima').toLowerCase();
    const ragEnabled = !!chatState.ragEnabled;

    // ✅ Sécurise l’agent actif (source de vérité côté StateManager)
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

    // Attends brièvement l’OPEN (WebSocket V22.3 a une queue, mais on réduit les races) :contentReference[oaicite:5]{index=5}
    await this._waitForWS(this._wsConnectWaitMs);

    try {
      // Passe par l’EventBus → WebSocketClient V22.3 (convertit en frame {type:'chat.message', payload:{...}})
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
      this.showToast('Envoi impossible (WS).');
    } finally {
      // On libère tôt pour permettre un envoi rapproché ; la dé-dup est gérée côté WebSocket V22.3 :contentReference[oaicite:6]{index=6}
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

    // Sélection d’agent via UI
    on(EVENTS.CHAT_AGENT_SELECTED || 'ui:chat:agent_selected', (agentId) => {
      const ag = String(agentId || 'anima').toLowerCase();
      if (!AGENTS[ag]) return;
      this.state.set('chat.activeAgent', ag);
    });

    // RAG toggle
    on(EVENTS.CHAT_RAG_TOGGLED || 'ui:chat:rag_toggled', (on) => this.toggleRag(!!on));

    // --- WS events (depuis WebSocketClient V22.3) ---
    on('ws:model_info', (payload = {}) => {
      // Stocke la meta modèle (pour affichage) :contentReference[oaicite:7]{index=7}
      try { this.state.set('chat.modelInfo', payload || {}); } catch {}
      this.eventBus.emit?.('chat:model_info', payload);
    });

    on('ws:model_fallback', (p = {}) => {
      // Feedback discret lors d’un fallback (chaîne de secours) :contentReference[oaicite:8]{index=8}
      this.eventBus.emit?.('ui:toast', { kind: 'warning', text: `Fallback modèle → ${p.to_provider || '?'} / ${p.to_model || '?'}` });
      this.eventBus.emit?.('chat:model_fallback', p);
    });

    on('ws:memory_banner', (p = {}) => {
      // Mémoire STM/LTM banner (stats côté back) :contentReference[oaicite:9]{index=9}
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
      // Démarre un message assistant temporaire pour l’agent concerné
      const agent_id = (payload.agent_id || this.state.get('chat.activeAgent') || 'anima').toLowerCase();
      const tempId = payload.id || `asst-${Date.now()}`;
      const messages = this.state.get(`chat.messages.${agent_id}`) || [];
      // Pousse un conteneur assistant vide (sera rempli par les chunks)
      const newAsst = { id: tempId, role: 'assistant', agent_id, content: '', created_at: Date.now(), _streaming: true };
      this.state.set(`chat.messages.${agent_id}`, [...messages, newAsst]);
      this._clearStreamWatchdog(); // on a bien démarré le flux
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

      // Évite doubles finalisations (certains backends peuvent renvoyer deux fois en edge-cases)
      if (id && this._assistantPersistedIds.has(id)) return;

      const meta = payload.meta || null;
      try { if (meta) this.state.set('chat.lastMessageMeta', meta); } catch {}
      const messages = this.state.get(`chat.messages.${agent_id}`) || [];

      if (id) {
        const idx = messages.findIndex(m => m.id === id);
        if (idx >= 0) {
          const finalized = { ...messages[idx], _streaming: false };
          // Si le back a renvoyé "content" définitif, privilégie-le
          if (typeof payload.content === 'string' && payload.content.trim()) {
            finalized.content = payload.content;
          }
          const next = messages.slice(); next[idx] = finalized;
          this.state.set(`chat.messages.${agent_id}`, next);
          this._assistantPersistedIds.add(id);
        } else {
          // Si on ne retrouve pas l’ID, on append quand même
          const fallback = {
            id: id,
            role: 'assistant',
            agent_id,
            content: String(payload.content || ''),
            created_at: Date.now(),
            _streaming: false
          };
          this.state.set(`chat.messages.${agent_id}`, [...messages, fallback]);
          this._assistantPersistedIds.add(id);
        }
      } else {
        // Cas sans id → push simple
        const push = {
          id: `asst-${Date.now()}`,
          role: 'assistant',
          agent_id,
          content: String(payload.content || ''),
          created_at: Date.now(),
          _streaming: false
        };
        this.state.set(`chat.messages.${agent_id}`, [...messages, push]);
      }

      // Fin du chargement pour ce tour
      this.state.set('chat.isLoading', false);
      this._clearStreamWatchdog();
    });

    on('ws:error', (err = {}) => {
      this._clearStreamWatchdog();
      this.state.set('chat.isLoading', false);
      const msg = (err && (err.message || err.error)) || 'Erreur WebSocket.';
      this.showToast(msg, 'error');
      console.warn('[WS:error]', err);
    });

    // Optionnel : statut RAG (pour chips/badges UI)
    on('ws:rag_status', (p = {}) => {
      const status = (p.status || 'idle');
      try { this.state.set('chat.ragStatus', status); } catch {}
    });
  }

  /* ------------------------------------------------------------------ */
  /* Helpers                                                             */
  /* ------------------------------------------------------------------ */

  async _waitForWS(maxWaitMs = 800) {
    const t0 = Date.now();
    const ready = () => {
      try {
        const ws = window?.wsClient?.websocket || null;
        return !!ws && ws.readyState === 1; // OPEN
      } catch { return false; }
    };
    if (ready()) return;
    // Déclenche la connexion si nécessaire
    try { window?.wsClient?.connect?.(); } catch {}
    // Attente courte (boucle)
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
        console.warn('[Chat] Watchdog: aucun flux reçu dans le délai.', this._pendingMsg);
        this.state.set('chat.isLoading', false);
        this.showToast(`Temps d'attente dépassé (agent ${ag}). Réessaie.`);
      } catch {}
    }, this._watchdogMs);
  }

  _clearStreamWatchdog() {
    if (this._watchdog) { clearTimeout(this._watchdog); this._watchdog = null; }
  }

  showToast(text, kind = 'error') {
    try { this.eventBus.emit?.('ui:toast', { kind, text }); } catch {}
  }
}
