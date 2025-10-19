/**
 * @module features/chat/chat
 * @description Module Chat - V25.4 "WS-first strict + RAG/Memo hooks + Watchdog REST fallback + metrics + memory.clear + listeners idempotents"
 *
 * Ajouts V25.4:
 * - Dédoublon robuste des listeners WS/UI (pré-bind + _onOnce) pour éviter toute double subscription au hot-reload / réinit.
 */

import { ChatUI } from './chat-ui.js';   // cache-bust UI présent
import { EVENTS, AGENTS } from '../../shared/constants.js';
import { api } from '../../shared/api-client.js';
import { ConceptRecallBanner } from './concept-recall-banner.js';

export default class ChatModule {
  constructor(eventBus, state) {
    this.eventBus = eventBus;
    this.state = state;

    this.ui = null;
    this.container = null;
    this.listeners = [];
    this.isInitialized = false;
    this.recallBanner = null;  // ConceptRecallBanner instance

    // Threads / convo
    this.threadId = null;
    this.loadedThreadId = null;

    // Connexion & flux
    this._wsConnected = false;
    this._wsConnectWaitMs = 700;
    this._streamStartTimer = null;
    this._streamStartTimeoutMs = 1500;
    this._pendingMsg = null;
    this._isStreamingNow = false; // 🔥 FIX: Flag pour bloquer le listener state pendant le streaming

    // Anti double actions
    this._sendLock = false;
    this._sendGateMs = 400;
    this._assistantPersistedIds = new Set();
    this._messageBuckets = new Map();
    this._lastChunkByMessage = new Map();

    // UX
    this._lastToastAt = 0;

    // Mémoire
    this._lastMemoryTendAt = 0;
    this._memoryTendThrottleMs = 2000;

    // Idempotence abonnements
    this._subs = Object.create(null);   // event -> off()
    this._H = Object.create(null);      // handlers pré-bindés
    this._bindHandlers();
  }

  _determineBucketForMessage(agentId, meta) {
    const baseAgent = typeof agentId === 'string' ? agentId.trim().toLowerCase() : '';
    const metaObj = (meta && typeof meta === 'object') ? meta : null;
    if (metaObj) {
      const opinion = (metaObj.opinion && typeof metaObj.opinion === 'object') ? metaObj.opinion : null;
      if (opinion) {
        const source = String(opinion.source_agent_id ?? opinion.source_agent ?? opinion.agent ?? '').trim().toLowerCase();
        if (source) return source;
      }
      const opinionRequest = (metaObj.opinion_request && typeof metaObj.opinion_request === 'object') ? metaObj.opinion_request : null;
      if (opinionRequest) {
        const sourceReq = String(opinionRequest.source_agent ?? opinionRequest.source_agent_id ?? '').trim().toLowerCase();
        if (sourceReq) return sourceReq;
      }
    }
    return baseAgent || 'nexus';
  }

  _rememberMessageBucket(messageId, bucketId) {
    if (!messageId) return;
    try {
      this._messageBuckets.set(String(messageId), bucketId || null);
    } catch (error) {
      console.warn('[Chat] unable to remember message bucket', error);
    }
  }

  _removeMessageById(messageId, bucketHint) {
    const key = messageId ? String(messageId) : null;
    if (!key) return false;
    const bucketId = bucketHint || this._messageBuckets.get(key) || null;
    if (!bucketId) return false;
    try {
      const pathKey = `chat.messages.${bucketId}`;
      const list = this.state.get(pathKey) || [];
      const idx = list.findIndex((msg) => msg && msg.id === messageId);
      if (idx === -1) return false;
      const next = [...list.slice(0, idx), ...list.slice(idx + 1)];
      this.state.set(pathKey, next);
      this._messageBuckets.delete(key);
      this._lastChunkByMessage.delete(key);
      this._updateThreadCacheFromBuckets();
      return true;
    } catch (error) {
      console.warn('[Chat] unable to remove message by id', error);
      return false;
    }
  }

  _resolveBucketFromCache(messageId, agentId, meta) {
    const key = messageId ? String(messageId) : null;
    if (key && this._messageBuckets.has(key)) {
      const stored = this._messageBuckets.get(key);
      if (stored) return stored;
    }
    return this._determineBucketForMessage(agentId, meta);
  }

  _findOpinionArtifacts(targetAgentId, sourceAgentId, messageId) {
    const normalizeAgent = (value) => (value ? String(value).trim().toLowerCase() : '');
    const target = normalizeAgent(targetAgentId);
    const source = normalizeAgent(sourceAgentId);
    const requestedId = messageId ? String(messageId).trim() : '';
    const result = { request: null, response: null };
    if (!target || !requestedId) return result;

    const requests = [];
    const responses = [];

    try {
      const buckets = this.state.get('chat.messages') || {};
      const agentKeys = Object.keys(buckets || {});
      for (const agentKey of agentKeys) {
        const entries = Array.isArray(buckets[agentKey]) ? buckets[agentKey] : [];
        for (const entry of entries) {
          if (!entry || typeof entry !== 'object') continue;
          const role = normalizeAgent(entry.role);
          const meta = (entry.meta && typeof entry.meta === 'object') ? entry.meta : null;
          if (!meta) continue;

          if (role === 'user') {
            const opinionReq = (typeof meta.opinion_request === 'object') ? meta.opinion_request : null;
            if (!opinionReq) continue;
            const reqTarget = normalizeAgent(opinionReq.target_agent ?? opinionReq.target_agent_id ?? '');
            if (!reqTarget || reqTarget !== target) continue;
            const reqSource = normalizeAgent(opinionReq.source_agent ?? opinionReq.source_agent_id ?? '');
            if (source && reqSource && reqSource !== source) continue;
            const reqMessage = String(opinionReq.requested_message_id ?? opinionReq.message_id ?? opinionReq.of_message_id ?? '').trim();
            if (reqMessage && reqMessage !== requestedId) continue;
            const noteId = String(opinionReq.request_id ?? opinionReq.request_note_id ?? opinionReq.note_id ?? entry.id ?? '').trim();
            requests.push({ message: entry, bucket: agentKey, noteId, messageId: reqMessage || requestedId });
          } else if (role === 'assistant') {
            const opinionMeta = (typeof meta.opinion === 'object') ? meta.opinion : null;
            if (!opinionMeta) continue;
            const reviewer = normalizeAgent(opinionMeta.reviewer_agent_id ?? opinionMeta.reviewer_agent ?? opinionMeta.agent_id ?? opinionMeta.agent ?? '');
            if (reviewer && reviewer !== target) continue;
            const srcMeta = normalizeAgent(opinionMeta.source_agent_id ?? opinionMeta.source_agent ?? '');
            if (source && srcMeta && srcMeta !== source) continue;
            const relatedMsg = String(opinionMeta.of_message_id ?? opinionMeta.of_message ?? opinionMeta.message_id ?? opinionMeta.target_message_id ?? '').trim();
            const noteId = String(opinionMeta.request_note_id ?? opinionMeta.request_id ?? opinionMeta.note_id ?? '').trim();
            responses.push({ message: entry, bucket: agentKey, relatedMessage: relatedMsg, noteId });
          }
        }
      }
    } catch (error) {
      console.warn('[Chat] Unable to inspect existing opinion requests', error);
    }

    if (requests.length) {
      result.request = requests[0];
    }

    const noteToMatch = result.request?.noteId || '';
    if (noteToMatch) {
      const byNote = responses.find((item) => item.noteId && item.noteId === noteToMatch);
      if (byNote) {
        result.response = byNote;
        return result;
      }
    }

    const byMessage = responses.find((item) => item.relatedMessage && item.relatedMessage === requestedId);
    if (byMessage) {
      result.response = byMessage;
    } else if (!result.response && noteToMatch) {
      const fallback = responses.find((item) => item.noteId && item.noteId === noteToMatch);
      if (fallback) result.response = fallback;
    }

    return result;
  }

  _findExistingOpinionRequest(targetAgentId, sourceAgentId, messageId) {
    const artifacts = this._findOpinionArtifacts(targetAgentId, sourceAgentId, messageId);
    return artifacts.request ? artifacts.request.message : null;
  }

  _generateMessageId(prefix = 'msg') {
    try {
      if (globalThis.crypto && typeof globalThis.crypto.randomUUID === 'function') {
        return globalThis.crypto.randomUUID();
      }
    } catch (error) {
      console.warn('[Chat] crypto.randomUUID unavailable', error);
    }
    const rand = Math.random().toString(16).slice(2);
    return `${prefix}-${Date.now()}-${rand}`;
  }

  _bindHandlers() {
    // UI
    this._H.CHAT_SEND          = this.handleSendMessage.bind(this);
    this._H.CHAT_AGENT_SELECTED= this.handleAgentSelected.bind(this);
    this._H.CHAT_REQUEST_OPINION = this.handleOpinionRequest.bind(this);
    this._H.CHAT_CLEAR         = this.handleClearChat.bind(this);
    this._H.CHAT_EXPORT        = this.handleExport.bind(this);
    this._H.CHAT_RAG_TOGGLED   = this.handleRagToggle.bind(this);
    this._H.DOC_SELECTION_CHANGED = this.handleDocumentSelectionChanged.bind(this);
    this._H.THREADS_SELECTED = this.handleThreadSwitch.bind(this);
    this._H.THREADS_LOADED = this.handleThreadSwitch.bind(this);

    // WS flux
    this._H.WS_START           = this.handleStreamStart.bind(this);
    this._H.WS_CHUNK           = this.handleStreamChunk.bind(this);
    this._H.WS_END             = this.handleStreamEnd.bind(this);
    this._H.WS_ANALYSIS        = this.handleAnalysisStatus.bind(this);
    this._H.WS_PERSISTED       = this.handleMessagePersisted.bind(this);
    this._H.WS_ERROR          = this.handleWsError.bind(this);
    this._H.WS_SESSION_ESTABLISHED = this.handleSessionEstablished.bind(this);
    this._H.WS_SESSION_RESTORED    = this.handleSessionRestored.bind(this);

    // WS état
    this._H.WS_CONNECTED       = () => { this._wsConnected = true;  try { this.state.set('connection.status', 'connected'); } catch {} };
    this._H.WS_CLOSE           = () => { this._wsConnected = false; try { this.state.set('connection.status', 'disconnected'); } catch {} };

    // Hooks RAG/Mémoire
    this._H.MEM_BANNER         = this.handleMemoryBanner.bind(this);
    this._H.RAG_STATUS         = this.handleRagStatus.bind(this);
    this._H.MEM_TEND           = this.handleMemoryTend.bind(this);
    this._H.MEM_CLEAR          = this.handleMemoryClear.bind(this);

    // Concept Recall (Phase 3)
    this._H.CONCEPT_RECALL     = this.handleConceptRecall.bind(this);
  }

  _onOnce(eventName, handler) {
    if (this._subs[eventName]) return;                // déjà abonné
    const off = this.eventBus.on(eventName, handler); // EventBus renvoie bien une fonction off()
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

    // 🔄 Sync état WS au boot pour WS-first strict
    try {
      const conn = this.state.get('connection.status');
      this._wsConnected = (conn === 'connected');
    } catch {}

    this.isInitialized = true;
    console.log('✅ ChatModule V25.4 initialisé (listeners idempotents).');
  }

  mount(container) {
    this.container = container;
    this.ui.render(this.container, this.state.get('chat'));

    // Initialize ConceptRecallBanner
    const bannerContainer = container.querySelector('.concept-recall-container');
    if (bannerContainer && !this.recallBanner) {
      try {
        this.recallBanner = new ConceptRecallBanner(bannerContainer);
        console.log('✅ ConceptRecallBanner initialized');
      } catch (err) {
        console.warn('[Chat] ConceptRecallBanner init failed:', err);
      }
    }

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
    } else {
      // ✅ Pas de conversation active : en récupérer une ou en créer une nouvelle
      this._ensureActiveConversation();
    }
  }

  /**
   * S'assure qu'une conversation est active au chargement du module.
   * Récupère la dernière conversation existante ou en crée une nouvelle.
   */
  async _ensureActiveConversation() {
    try {
      console.log('[Chat] Aucune conversation active détectée, récupération/création en cours...');

      // Récupérer la liste des threads depuis le state (déjà chargés par app.js)
      const threadsOrder = this.state.get('threads.order') || [];

      if (threadsOrder.length > 0) {
        // Prendre le premier thread de la liste (le plus récent)
        const latestThreadId = threadsOrder[0];
        const threadData = this.state.get(`threads.map.${latestThreadId}`);

        if (threadData) {
          console.log('[Chat] Activation de la dernière conversation:', latestThreadId);
          this.loadedThreadId = latestThreadId;
          this.threadId = latestThreadId;
          this.state.set('chat.threadId', latestThreadId);
          this.state.set('threads.currentId', latestThreadId);
          try { localStorage.setItem('emergence.threadId', latestThreadId); } catch {}

          // Charger les messages de cette conversation
          this.hydrateFromThread(threadData);

          // Émettre l'événement pour que le WebSocket se connecte
          this.eventBus.emit('threads:ready', { id: latestThreadId });
          this.eventBus.emit(EVENTS.THREADS_SELECTED || 'threads:selected', { id: latestThreadId });

          console.log('[Chat] ✅ Conversation active chargée automatiquement');
          return;
        }
      }

      // Si aucun thread n'existe dans la liste, créer un nouveau
      console.log('[Chat] Aucune conversation existante, création d\'une nouvelle...');
      const created = await api.createThread({ type: 'chat', title: 'Conversation' });
      const newThreadId = created?.id;

      if (newThreadId) {
        this.loadedThreadId = newThreadId;
        this.threadId = newThreadId;
        this.state.set('chat.threadId', newThreadId);
        this.state.set('threads.currentId', newThreadId);
        try { localStorage.setItem('emergence.threadId', newThreadId); } catch {}

        // Initialiser avec des messages vides
        this.hydrateFromThread({ id: newThreadId, messages: [] });

        // Émettre les événements nécessaires
        this.eventBus.emit('threads:ready', { id: newThreadId });
        this.eventBus.emit(EVENTS.THREADS_CREATED || 'threads:created', created);

        console.log('[Chat] ✅ Nouvelle conversation créée et activée:', newThreadId);
      }
    } catch (error) {
      console.error('[Chat] Erreur lors de l\'activation automatique de conversation:', error);
      // En cas d'erreur, continuer sans conversation active (mode dégradé)
    }
  }

  /* ============================ State init ============================ */
  initializeState() {
    try { this._messageBuckets.clear(); } catch {}
    try { this._lastChunkByMessage.clear(); } catch {}
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
        selectedDocIds: [],
        selectedDocs: [],
        metrics: { send_count: 0, ws_start_count: 0, last_ttfb_ms: 0, rest_fallback_count: 0, last_fallback_at: null, opinion_request_count: 0 }
      });
    } else {
      if (this.state.get('chat.ragEnabled') === undefined) this.state.set('chat.ragEnabled', false);
      if (!this.state.get('chat.messages')) this.state.set('chat.messages', {});
      if (!this.state.get('chat.ragStatus')) this.state.set('chat.ragStatus', 'idle');
      if (!this.state.get('chat.memoryBannerAt')) this.state.set('chat.memoryBannerAt', null);
      if (!this.state.get('chat.metrics')) this.state.set('chat.metrics', { send_count: 0, ws_start_count: 0, last_ttfb_ms: 0, rest_fallback_count: 0, last_fallback_at: null, opinion_request_count: 0 });
      if (!Array.isArray(this.state.get('chat.selectedDocIds'))) this.state.set('chat.selectedDocIds', []);
      if (!Array.isArray(this.state.get('chat.selectedDocs'))) this.state.set('chat.selectedDocs', []);
    }
    if (this.state.get('chat.authRequired') === undefined) this.state.set('chat.authRequired', false);
    try {
      const savedDocIds = this.state.get('documents.selectedIds');
      const savedDocMeta = this.state.get('documents.selectionMeta');
      const hasIds = Array.isArray(savedDocIds) && savedDocIds.length > 0;
      const hasMeta = Array.isArray(savedDocMeta) && savedDocMeta.length > 0;
      if (hasIds || hasMeta) {
        this.handleDocumentSelectionChanged({
          ids: hasIds ? savedDocIds : [],
          items: hasMeta ? savedDocMeta : []
        });
      }
    } catch (err) {
      console.warn('[Chat] Sync doc selection failed', err);
    }

  }

  registerStateChanges() {
    const unsub = this.state.subscribe('chat', (chatState) => {
      // 🔥 FIX: Ne PAS appeler ui.update() pendant le streaming
      // Sinon _renderMessages() écrase la modification directe du DOM faite dans handleStreamChunk
      if (this._isStreamingNow) {
        console.log('[Chat] 🚫 State listener: ui.update() skipped (streaming in progress)');
        return;
      }
      if (this.ui && this.container) this.ui.update(this.container, chatState);
    });
    if (typeof unsub === 'function') this.listeners.push(unsub);
  }

  registerEvents() {
    // UI (idempotent)
    this._onOnce(EVENTS.CHAT_SEND,          this._H.CHAT_SEND);
    this._onOnce(EVENTS.CHAT_AGENT_SELECTED,this._H.CHAT_AGENT_SELECTED);
    this._onOnce(EVENTS.CHAT_REQUEST_OPINION, this._H.CHAT_REQUEST_OPINION);
    this._onOnce(EVENTS.CHAT_CLEAR,         this._H.CHAT_CLEAR);
    this._onOnce(EVENTS.CHAT_EXPORT,        this._H.CHAT_EXPORT);
    this._onOnce(EVENTS.CHAT_RAG_TOGGLED,   this._H.CHAT_RAG_TOGGLED);
    this._onOnce(EVENTS.DOCUMENTS_SELECTION_CHANGED, this._H.DOC_SELECTION_CHANGED);
    this._onOnce(EVENTS.THREADS_SELECTED, this._H.THREADS_SELECTED);
    this._onOnce(EVENTS.THREADS_LOADED, this._H.THREADS_LOADED);

    // Flux WS (idempotent)
    this._onOnce('ws:chat_stream_start',    this._H.WS_START);
    this._onOnce('ws:chat_stream_chunk',    this._H.WS_CHUNK);
    this._onOnce('ws:chat_stream_end',      this._H.WS_END);
    this._onOnce('ws:analysis_status',      this._H.WS_ANALYSIS);
    this._onOnce('ws:message_persisted',    this._H.WS_PERSISTED);
    this._onOnce('ws:error',               this._H.WS_ERROR);

    // Connexion WS (idempotent)
    this._onOnce('ws:session_established',  this._H.WS_SESSION_ESTABLISHED);
    this._onOnce('ws:session_restored',     this._H.WS_SESSION_RESTORED);
    this._onOnce('ws:connected',            this._H.WS_CONNECTED);
    this._onOnce('ws:close',                this._H.WS_CLOSE);

    // Hooks RAG/Mémoire (idempotent)
    this._onOnce('ws:memory_banner',        this._H.MEM_BANNER);
    this._onOnce('ws:rag_status',           this._H.RAG_STATUS);
    this._onOnce('memory:tend',             this._H.MEM_TEND);
    this._onOnce('memory:clear',            this._H.MEM_CLEAR);

    // Concept Recall (Phase 3)
    this._onOnce('ws:concept_recall',       this._H.CONCEPT_RECALL);
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
    const threadId = (thread && (thread.id || thread.thread_id)) || this.getCurrentThreadId();
    const msgsRaw = Array.isArray(thread?.messages) ? [...thread.messages] : [];
    const msgs = msgsRaw.sort((a, b) => (a?.created_at ?? 0) - (b?.created_at ?? 0));

    const buckets = {};
    let lastAssistantAgent = null;
    try { this._messageBuckets.clear(); } catch {}

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

      const meta = (m && typeof m.meta === 'object') ? m.meta : null;
      const bucketId = this._determineBucketForMessage(agentId, meta);
      const entry = {
        id: m.id || `${role}-${m.created_at || Date.now()}`,
        role,
        content: typeof m.content === 'string' ? m.content : JSON.stringify(m.content ?? ''),
        agent_id: agentId,
        created_at: m.created_at
      };
      if (meta) entry.meta = meta;
      (buckets[bucketId] ||= []).push(entry);
      this._rememberMessageBucket(entry.id, bucketId);
    }

    this.state.set('chat.messages', buckets);

    if (threadId) {
      this.threadId = threadId;
      this.loadedThreadId = threadId;
      try { this.state.set('threads.currentId', threadId); } catch {}
      try { this.state.set('chat.threadId', threadId); } catch {}
      try { localStorage.setItem('emergence.threadId', threadId); } catch {}
    }

    const hasDocsProperty = thread && Object.prototype.hasOwnProperty.call(thread, 'docs');
    if (threadId && hasDocsProperty) {
      const docsForState = this._normalizeThreadDocsForState(Array.isArray(thread?.docs) ? thread.docs : []);
      const docIds = docsForState.map((doc) => String(doc.id));
      const selectionItems = docsForState.map((doc) => ({ id: String(doc.id), name: doc.name, status: doc.status }));

      try { this.state.set(`threads.map.${threadId}.docs`, docsForState); } catch {}
      this.state.set('chat.selectedDocIds', docIds);
      this.state.set('chat.selectedDocs', selectionItems);
      try { this.state.set('documents.selectedIds', docIds); } catch {}
      try { this.state.set('documents.selectionMeta', selectionItems); } catch {}
    }

    const extras = {};
    if (thread && typeof thread === 'object') {
      if (thread.metadata) extras.metadata = thread.metadata;
      else if (thread.meta) extras.metadata = thread.meta;
    }
    this._updateThreadCacheFromBuckets(threadId, extras);

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
    const docIdsRaw = this.state.get('chat.selectedDocIds') || [];
    const selectedDocIds = this._sanitizeDocIds(docIdsRaw);
    const messageMeta = {};
    if (selectedDocIds.length) messageMeta.doc_ids = selectedDocIds;
    messageMeta.use_rag = !!ragEnabled;
    this.state.set('chat.activeAgent', currentAgentId);

    // Ajoute localement le message USER
    const userMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: trimmed,
      agent_id: currentAgentId,
      created_at: Date.now()
    };
    if (Object.keys(messageMeta).length) {
      userMessage.meta = { ...messageMeta };
    }
    const curr = this.state.get(`chat.messages.${currentAgentId}`) || [];
    this.state.set(`chat.messages.${currentAgentId}`, [...curr, userMessage]);
    this.state.set('chat.isLoading', true);
    this._updateThreadCacheFromBuckets();

    let threadId = this.getCurrentThreadId();
    if (threadId) {
      api.appendMessage(threadId, {
        role: 'user',
        content: trimmed,
        agent_id: currentAgentId,
        meta: { ...messageMeta }
      }).catch(async (err) => {
        // Si le thread n'existe pas (404), créer un nouveau thread et réessayer
        if (err?.status === 404) {
          console.warn('[Chat] Thread introuvable (404) → création nouveau thread');
          try {
            const created = await api.createThread({ type: 'chat', agent_id: currentAgentId });
            const newThreadId = created?.id;
            if (newThreadId) {
              // Mettre à jour l'état avec le nouveau thread
              this.threadId = newThreadId;
              this.loadedThreadId = newThreadId;
              this.state.set('threads.currentId', newThreadId);
              this.state.set('chat.threadId', newThreadId);
              try { localStorage.setItem('emergence.threadId', newThreadId); } catch {}

              // Émettre l'événement pour que le WebSocket se reconnecte avec le bon thread
              this.eventBus.emit('threads:ready', { id: newThreadId });

              // Réessayer l'ajout du message
              await api.appendMessage(newThreadId, {
                role: 'user',
                content: trimmed,
                agent_id: currentAgentId,
                meta: { ...messageMeta }
              });
              console.log('[Chat] Message ajouté au nouveau thread', newThreadId);
            }
          } catch (retryErr) {
            console.error('[Chat] Échec création thread/retry:', retryErr);
          }
        } else {
          console.error('[Chat] Échec appendMessage(user):', err);
        }
      });
    }

    // 🛡️ Anti-course: attends brièvement WS avant d'émettre
    await this._waitForWS(this._wsConnectWaitMs);

    // Émission enrichie UI→WS (prise en charge par WebSocketClient)
    try {
      this.eventBus.emit('ui:chat:send', {
        text: trimmed,
        agent_id: currentAgentId,
        doc_ids: selectedDocIds,
        use_rag: !!ragEnabled,
        msg_uid: userMessage.id,
        __enriched: true
      });
      // Pour watchdog (fallback REST si flux ne démarre pas)
      this._pendingMsg = { id: userMessage.id, agent_id: currentAgentId, text: trimmed, doc_ids: selectedDocIds, use_rag: !!ragEnabled, triedRest: false };
      this._startStreamWatchdog();
    } catch (e) {
      console.error('[Chat] Emission ui:chat:send a échoué', e);
      this._clearStreamWatchdog();
      this.state.set('chat.isLoading', false);
      this._sendLock = false;
      this.showToast('Envoi impossible (WS).');
    }
  }

  async handleOpinionRequest(payload = {}) {
    try {
      const data = (payload && typeof payload === 'object') ? payload : {};
      const targetAgentId = String(data.target_agent_id ?? data.targetAgentId ?? data.target_agent ?? data.targetAgent ?? '').trim().toLowerCase();
      const sourceAgentId = String(data.source_agent_id ?? data.sourceAgentId ?? data.source_agent ?? data.sourceAgent ?? '').trim().toLowerCase();
      const messageId = String(data.message_id ?? data.messageId ?? '').trim();
      if (!targetAgentId || !AGENTS[targetAgentId]) {
        this.showToast('Agent indisponible pour avis.');
        return;
      }
      if (targetAgentId === sourceAgentId) {
        this.showToast('Sélectionnez un autre agent pour l\'avis.');
        return;
      }
      if (!messageId) {
        this.showToast('Message cible introuvable.');
        return;
      }

      let messageText = '';
      if (typeof data.message_text === 'string') messageText = data.message_text;
      else if (typeof data.messageText === 'string') messageText = data.messageText;

      if (!messageText) {
        try {
          const buckets = this.state.get('chat.messages') || {};
          for (const key of Object.keys(buckets || {})) {
            const bucket = Array.isArray(buckets[key]) ? buckets[key] : [];
            const found = bucket.find((msg) => msg && msg.id === messageId);
            if (found) {
              if (typeof found.content === 'string') messageText = found.content;
              else if (typeof found.text === 'string') messageText = found.text;
              break;
            }
          }
        } catch (err) {
          console.warn('[Chat] opinion request message lookup failed', err);
        }
      }
      messageText = String(messageText || '').trim();
      const artifacts = this._findOpinionArtifacts(targetAgentId, sourceAgentId, messageId);
      if (artifacts.response) {
        this.showToast('Avis déjà disponible pour cette réponse.');
        return;
      }
      if (artifacts.request?.message?.id) {
        this._removeMessageById(artifacts.request.message.id, artifacts.request.bucket);
      }

      const agentInfo = AGENTS[targetAgentId] || {};
      const sourceInfo = sourceAgentId ? (AGENTS[sourceAgentId] || {}) : {};
      const agentLabel = agentInfo.label || agentInfo.name || (targetAgentId || 'agent');
      const sourceLabel = sourceInfo.label || sourceInfo.name || (sourceAgentId || 'cet agent');

      const requestId = this._generateMessageId('opinion-request');
      const createdAt = Date.now();
      const requestMessage = {
        id: requestId,
        role: 'user',
        content: `@${agentLabel}, peux-tu donner ton avis sur la réponse de ${sourceLabel} ?`,
        agent_id: targetAgentId,
        created_at: createdAt,
        meta: {
          opinion_request: {
            target_agent: targetAgentId,
            source_agent: sourceAgentId || null,
            requested_message_id: messageId,
            request_id: requestId,
            request_note_id: requestId
          }
        }
      };

      const bucketTarget = (artifacts.request?.bucket || (sourceAgentId || targetAgentId || '').trim().toLowerCase()) || targetAgentId;
      const existing = this.state.get(`chat.messages.${bucketTarget}`) || [];
      this.state.set(`chat.messages.${bucketTarget}`, [...existing, requestMessage]);
      this._rememberMessageBucket(requestId, bucketTarget);
      this._updateThreadCacheFromBuckets();
      this.showToast(`Avis demandé à ${agentLabel}.`);

      try {
        const metrics = this.state.get('chat.metrics') || {};
        const nextMetrics = {
          ...metrics,
          opinion_request_count: (metrics.opinion_request_count || 0) + 1,
          last_opinion_request: {
            target_agent_id: targetAgentId,
            source_agent_id: sourceAgentId || null,
            message_id: messageId,
            bucket: bucketTarget,
            at: createdAt
          }
        };
        this.state.set('chat.metrics', nextMetrics);
      } catch (err) {
        console.warn('[Chat] unable to trace opinion request metrics', err);
      }
      try {
        this.eventBus?.emit?.('ui:guidance:opinion_request', {
          target_agent_id: targetAgentId,
          source_agent_id: sourceAgentId || null,
          message_id: messageId,
          request_id: requestId,
          bucket: bucketTarget,
          at: createdAt
        });
      } catch (err) {
        console.warn('[Chat] unable to emit guidance trace', err);
      }

      await this._waitForWS(this._wsConnectWaitMs);

      const framePayload = {
        target_agent_id: targetAgentId,
        source_agent_id: sourceAgentId || null,
        message_id: messageId,
        request_id: requestId,
      };
      if (messageText) framePayload.message_text = messageText;

      this.eventBus.emit(EVENTS.WS_SEND, {
        type: 'chat.opinion',
        payload: framePayload,
      });
    } catch (error) {
      console.error('[Chat] handleOpinionRequest error', error);
      this.showToast('Impossible de demander un avis.');
    }
  }
  /* ============================ Flux assistant (WS) ============================ */
  handleStreamStart(payload = {}) {
    const agentIdRaw = payload && typeof payload === 'object' ? (payload.agent_id ?? payload.agentId) : null;
    const agentId = String(agentIdRaw ?? '').trim() || 'nexus';
    const messageId = payload && typeof payload === 'object' && payload.id ? payload.id : `assistant-${Date.now()}`;
    const baseMeta = (payload && typeof payload.meta === 'object') ? { ...payload.meta } : null;

    const bucketId = this._resolveBucketFromCache(messageId, agentId, baseMeta);
    const agentMessage = {
      id: messageId,
      role: 'assistant',
      content: '',
      agent_id: agentId,
      isStreaming: true,
      created_at: Date.now(),
    };
    if (baseMeta && Object.keys(baseMeta).length) agentMessage.meta = baseMeta;

    const curr = this.state.get(`chat.messages.${bucketId}`) || [];
    this.state.set(`chat.messages.${bucketId}`, [...curr, agentMessage]);
    this._rememberMessageBucket(messageId, bucketId);
    this._lastChunkByMessage.set(String(messageId), '');
    this._updateThreadCacheFromBuckets();
    this._clearStreamWatchdog(); // le flux a bien démarré

    // 🔥 FIX CRITIQUE: Activer le flag APRÈS que state.set() ait déclenché le listener
    // Le state.set() ci-dessus a déclenché le listener state qui a appelé ui.update()
    // Le message vide est maintenant dans le DOM, on peut bloquer les prochains updates
    this._isStreamingNow = true;
  }

  handleStreamChunk(payload = {}) {
    console.log('[Chat] 🔍 handleStreamChunk called:', payload);
    const agentId = String(payload && typeof payload === 'object' ? (payload.agent_id ?? payload.agentId) : '').trim();
    const messageId = payload && typeof payload === 'object' ? payload.id : null;
    if (!agentId || !messageId) {
      console.warn('[Chat] ❌ Chunk ignored: agentId=', agentId, 'messageId=', messageId);
      return;
    }
    const rawChunk = payload && typeof payload.chunk !== 'undefined' ? payload.chunk : '';
    const chunkText = typeof rawChunk === 'string' ? rawChunk : String(rawChunk ?? '');
    console.log('[Chat] 🔍 Chunk text:', chunkText);
    const meta = (payload && typeof payload.meta === 'object') ? payload.meta : null;

    const lastChunk = this._lastChunkByMessage.get(String(messageId));
    if (chunkText && lastChunk === chunkText) {
      console.log('[Chat] ⏭️ Chunk duplicate ignored');
      return;
    }

    const bucketId = this._resolveBucketFromCache(messageId, agentId, meta);
    console.log('[Chat] 🔍 BucketId:', bucketId);
    const list = this.state.get(`chat.messages.${bucketId}`) || [];
    const idx = list.findIndex((m) => m.id === messageId);
    console.log('[Chat] 🔍 Message idx:', idx, 'list.length:', list.length);
    if (idx >= 0) {
      const msg = { ...list[idx] };
      msg.content = (msg.content || '') + chunkText;
      list[idx] = msg;
      this.state.set(`chat.messages.${bucketId}`, [...list]);
      this._lastChunkByMessage.set(String(messageId), chunkText);
      this._updateThreadCacheFromBuckets();
      console.log('[Chat] ✅ Chunk applied! Content length:', msg.content.length);

      // 🔥 FIX OPTION E: Modification directe du DOM (bypass du flux state→UI)
      // Au lieu de passer par le flux complet state.set() → ui.update() → _renderMessages() → innerHTML,
      // on met à jour directement l'élément DOM du message pour éviter le problème de référence d'objet
      const messageEl = document.querySelector(`[data-message-id="${messageId}"]`);
      if (messageEl) {
        const contentEl = messageEl.querySelector('.message-text');
        if (contentEl) {
          // Mise à jour incrémentale directe du contenu
          // Note: on utilise innerHTML (pas textContent) car le contenu peut contenir des <br/> pour les retours à la ligne
          const escapedContent = this._escapeHTML(msg.content).replace(/\n/g, '<br/>');
          const cursor = msg.isStreaming ? '<span class="blinking-cursor">|</span>' : '';
          const finalHTML = escapedContent + cursor;

          console.log('[Chat] 🔍 DOM update details:', {
            messageId,
            rawContentLength: msg.content.length,
            rawContentPreview: msg.content.substring(0, 50),
            escapedContentLength: escapedContent.length,
            escapedContentPreview: escapedContent.substring(0, 50),
            finalHTMLLength: finalHTML.length,
            finalHTMLPreview: finalHTML.substring(0, 100),
            contentElTagName: contentEl.tagName,
            contentElVisible: contentEl.offsetHeight > 0
          });

          contentEl.innerHTML = finalHTML;

          console.log('[Chat] 🔥 DOM updated - innerHTML set. Current innerHTML length:', contentEl.innerHTML.length);
          console.log('[Chat] 🔥 DOM updated - Current textContent:', contentEl.textContent.substring(0, 50));
        } else {
          console.warn('[Chat] ⚠️ .message-text not found in message element');
        }
      } else {
        console.warn('[Chat] ⚠️ Message element not found in DOM for id:', messageId);
      }

      // ⚠️ NE PAS appeler ui.update() ici pendant le streaming !
      // Raison: _renderMessages() fait un full re-render avec innerHTML qui ÉCRASE la modification directe du DOM
      // qu'on vient de faire. Le state sera synchronisé à la fin du streaming via handleStreamEnd.
    } else {
      console.warn('[Chat] ❌ Message not found in bucket!');
    }
  }

  handleStreamEnd(payload = {}) {
    const agentId = String(payload && typeof payload === 'object' ? (payload.agent_id ?? payload.agentId) : '').trim();
    const messageId = payload && typeof payload === 'object' ? payload.id : null;
    const meta = (payload && typeof payload.meta === 'object') ? { ...payload.meta } : null;
    if (!agentId || !messageId) return;

    const bucketId = this._resolveBucketFromCache(messageId, agentId, meta);
    const list = this.state.get(`chat.messages.${bucketId}`) || [];
    const idx = list.findIndex((m) => m.id === messageId);
    if (idx >= 0) {
      const current = list[idx] || {};
      const baseMeta = current && typeof current.meta === 'object' ? { ...current.meta } : {};
      if (meta) Object.assign(baseMeta, meta);
      const mergedMeta = Object.keys(baseMeta).length ? baseMeta : null;

      const msg = { ...current, isStreaming: false };
      if (mergedMeta) msg.meta = mergedMeta;
      else if (msg.meta) delete msg.meta;

      list[idx] = msg;
      this.state.set(`chat.messages.${bucketId}`, [...list]);
    }

    this._rememberMessageBucket(messageId, bucketId);
    this._lastChunkByMessage.delete(String(messageId));
    this._updateThreadCacheFromBuckets();

    this.state.set('chat.isLoading', false);
    this._clearStreamWatchdog();

    // 🔥 DEBUG: Vérifier le contenu du message avant le re-render final
    const finalList = this.state.get(`chat.messages.${bucketId}`) || [];
    const finalMsg = finalList.find((m) => m.id === messageId);
    console.log('[Chat] 🔍 handleStreamEnd - Message content before ui.update():', {
      messageId,
      contentLength: finalMsg?.content?.length || 0,
      content: finalMsg?.content?.substring(0, 50) || 'EMPTY',
      isStreaming: finalMsg?.isStreaming
    });

    // 🔥 FIX: Désactiver le flag de streaming AVANT de synchroniser l'UI
    this._isStreamingNow = false;

    // 🔥 FIX: Synchroniser l'UI à la fin du streaming
    // On appelle ui.update() ici pour:
    // - Retirer le curseur clignotant (isStreaming: false)
    // - Activer le bouton de copie
    // - Synchroniser l'état final de l'UI avec le state
    if (this.ui && this.container) {
      this.ui.update(this.container, this.state.get('chat'));
    }

    try {
      if (this._assistantPersistedIds.has(messageId)) return;

      const backendPersisted = !!(meta && (meta.persisted === true || meta.persisted_by === 'backend' || meta.persisted_by_ws === true));

      const threadId = this.getCurrentThreadId();
      const finalBucketList = this.state.get(`chat.messages.${bucketId}`) || [];
      const finalMsg = finalBucketList.find((m) => m.id === messageId);

      if (!backendPersisted && threadId && finalMsg) {
        const payloadToPersist = {
          role: 'assistant',
          content: typeof finalMsg.content === 'string' ? finalMsg.content : String(finalMsg.content ?? ''),
          agent_id: finalMsg.agent_id || agentId,
        };
        if (finalMsg.meta && typeof finalMsg.meta === 'object') {
          payloadToPersist.meta = { ...finalMsg.meta };
        }
        api.appendMessage(threadId, payloadToPersist)
          .then(() => this._assistantPersistedIds.add(messageId))
          .catch(err => console.error('[Chat] échec appendMessage(assistant):', err));
      }
    } catch (e) {
      console.error('[Chat] handleStreamEnd persist error', e);
    }
  }

  handleWsError(payload = {}) {
    try {
      const code = typeof payload?.code === 'string' ? payload.code.trim() : '';
      const message = typeof payload?.message === 'string' ? payload.message.trim() : '';

      if (code) {
        console.warn('[Chat] ws:error', { code, payload });
      } else {
        console.warn('[Chat] ws:error', payload);
      }

      if (code === 'opinion_already_exists') {
        this.showToast(message || 'Avis déjà disponible pour cette réponse.');
        return;
      }

      if (message) {
        this.showToast(message);
      }
    } catch (error) {
      console.warn('[Chat] ws:error handler failure', error, payload);
    }
  }

  handleSessionEstablished(payload = {}) {
    try {
      const rawSessionId = typeof payload?.session_id === 'string' ? payload.session_id.trim() : '';
      const sessionId = rawSessionId || null;
      const sanitizeThread = (candidate) => {
        if (!candidate || typeof candidate !== 'string') return null;
        const trimmed = candidate.trim();
        if (!trimmed) return null;
        if (sessionId && trimmed === sessionId) return null;
        return trimmed;
      };
      const threadFromPayload = sanitizeThread(payload?.thread_id);
      const threadFromState = sanitizeThread(this.getCurrentThreadId());
      const threadFromInstance = sanitizeThread(this.threadId);

      if (sessionId) {
        try { this.state.set('websocket.sessionId', sessionId); } catch {}
      }

      const threadId = threadFromPayload || threadFromState || threadFromInstance;
      if (threadId) {
        this.threadId = threadId;
        this.loadedThreadId = threadId;
        try { this.state.set('threads.currentId', threadId); } catch {}
        try { this.state.set('chat.threadId', threadId); } catch {}
        try { localStorage.setItem('emergence.threadId', threadId); } catch {}
      }
    } catch (err) {
      console.warn('[Chat] handleSessionEstablished error', err);
    }
  }

  handleSessionRestored(payload = {}) {
    try {
      const rawSessionId = typeof payload?.session_id === 'string' ? payload.session_id.trim() : '';
      const sessionId = rawSessionId || null;
      const sanitizeThread = (candidate) => {
        if (!candidate || typeof candidate !== 'string') return null;
        const trimmed = candidate.trim();
        if (!trimmed) return null;
        if (sessionId && trimmed === sessionId) return null;
        return trimmed;
      };
      const threadFromPayload = sanitizeThread(payload?.thread_id);
      const threadFromState = sanitizeThread(this.getCurrentThreadId());
      const threadFromInstance = sanitizeThread(this.threadId);
      const threadId = threadFromPayload || threadFromState || threadFromInstance;
      const messages = Array.isArray(payload?.messages) ? payload.messages : [];

      if (threadId) {
        this.threadId = threadId;
        this.loadedThreadId = threadId;
        try { this.state.set('threads.currentId', threadId); } catch {}
        try { this.state.set('chat.threadId', threadId); } catch {}
        try { localStorage.setItem('emergence.threadId', threadId); } catch {}
      }

      if (messages.length && threadId) {
        this.hydrateFromThread({ id: threadId, messages, metadata: payload.metadata });
      } else if (threadId && payload?.metadata) {
        const threadKey = `threads.map.${threadId}`;
        const existing = this.state.get(threadKey) || { id: threadId, messages: [] };
        const next = { ...existing, metadata: payload.metadata };
        this.state.set(threadKey, next);
      }

      if (payload?.metadata) {
        this._applyMemoryMetadata(sessionId || threadId || null, payload.metadata);
      }
      if (threadId) {
        this._updateThreadCacheFromBuckets(threadId, payload?.metadata ? { metadata: payload.metadata } : {});
      }

      if (messages.length) {
        this.showToast('Session restaurée.');
      } else if (payload?.metadata) {
        this.showToast('Mémoire synchronisée.');
      }
    } catch (err) {
      console.error('[Chat] handleSessionRestored error', err);
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
  if (!agentId) return;
  try {
    const list = this.state.get(`chat.messages.${agentId}`) || [];
    list.forEach((msg) => {
      if (msg && msg.id) {
        this._messageBuckets.delete(String(msg.id));
      }
    });
  } catch {}
  this.state.set(`chat.messages.${agentId}`, []);
  this._updateThreadCacheFromBuckets();
  try {
    const meta = this.state.get('chat.lastMessageMeta');
    if (meta && (meta.agent_id === agentId || meta.agent === agentId || !meta.agent_id)) {
      this.state.set('chat.lastMessageMeta', null);
    }
  } catch {}
  const label = AGENTS?.[agentId]?.label || String(agentId || 'agent');
  this.showToast(`Conversation ${label} effacee.`);
}

  handleExport() {
    const chatState = this.state.get('chat') || {};
    const messagesByAgent = (chatState.messages && typeof chatState.messages === 'object') ? chatState.messages : {};
    const agentIds = Object.keys(messagesByAgent);
    if (!agentIds.length) {
      this.showToast('Aucun message a exporter.');
      return;
    }

    const you = this.state.get('user.id') || 'Vous';
    const formatAgentLabel = (id) => {
      if (!id) return 'Global';
      const info = AGENTS?.[id];
      if (info && info.label) return info.label;
      return String(id).trim() || 'Agent';
    };
    const formatTimestamp = (value) => {
      if (!value && value !== 0) return '';
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) return '';
      try {
        return date.toLocaleString('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
      } catch {
        return date.toISOString();
      }
    };
    const renderContent = (payload) => {
      if (payload == null) return '';
      if (typeof payload === 'string') return payload;
      try { return JSON.stringify(payload, null, 2); } catch { return String(payload); }
    };

    const sections = [];
    for (const agentId of agentIds) {
      const bucket = Array.isArray(messagesByAgent[agentId]) ? messagesByAgent[agentId] : [];
      if (!bucket.length) continue;
      const title = formatAgentLabel(agentId);
      sections.push(`## ${title}`);
      for (const message of bucket) {
        const author = message.role === 'user' ? you : (message.agent_id || title || 'Assistant');
        const stamp = formatTimestamp(message.created_at ?? message.timestamp ?? message.time ?? message.datetime ?? message.date);
        const body = renderContent(message.content ?? message.text ?? '');
        sections.push(stamp ? `[${stamp}] ${author}: ${body}` : `${author}: ${body}`);
      }
      sections.push('');
    }

    const exportPayload = sections.join('\n').trim();
    if (!exportPayload) {
      this.showToast('Aucun message a exporter.');
      return;
    }

    const blob = new Blob([exportPayload], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const filename = `chat_full_${Date.now()}.txt`;
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    this.showToast('Export conversation pret.');
  }

  handleRagToggle() {
    const current = !!this.state.get('chat.ragEnabled');
    const newState = !current;
    this.state.set('chat.ragEnabled', newState);

    // Notifier l'utilisateur du changement d'état
    const selectedDocs = this.state.get('chat.selectedDocIds') || [];
    if (newState && selectedDocs.length > 0) {
      this.eventBus.emit('show:notification', {
        type: 'success',
        message: `RAG activé - ${selectedDocs.length} document(s) accessible(s) aux agents`
      });
    } else if (!newState && selectedDocs.length > 0) {
      this.eventBus.emit('show:notification', {
        type: 'info',
        message: 'RAG désactivé - Les agents ne peuvent plus accéder aux documents'
      });
    }
  }

  handleDocumentSelectionChanged(payload = {}) {
    const data = (payload && typeof payload === 'object') ? payload : {};
    const rawIds = Array.isArray(data.ids) ? data.ids : [];
    const itemsArray = Array.isArray(data.items) ? data.items : [];
    const resolveId = (input) => {
      if (!input) return '';
      const cand = input.id ?? input.document_id ?? input.doc_id;
      return cand == null ? '' : String(cand);
    };
    const normalizedIds = [];
    const seen = new Set();
    for (const value of rawIds) {
      const id = String(value ?? '').trim();
      if (!id || seen.has(id)) continue;
      seen.add(id);
      normalizedIds.push(id);
    }
    if (!normalizedIds.length && itemsArray.length) {
      for (const item of itemsArray) {
        const candidate = resolveId(item).trim();
        if (!candidate || seen.has(candidate)) continue;
        seen.add(candidate);
        normalizedIds.push(candidate);
      }
    }
    const itemsById = new Map();
    for (const item of itemsArray) {
      const itemId = resolveId(item).trim();
      if (!itemId) continue;
      let label = item?.name ?? item?.filename ?? item?.title ?? '';
      label = String(label ?? '').trim();
      if (!label) label = 'Document ' + itemId;
      const statusRaw = item?.status;
      const status = statusRaw == null ? 'ready' : (String(statusRaw).toLowerCase() || 'ready');
      itemsById.set(itemId, { id: itemId, name: label, status });
    }
    const normalizedItems = normalizedIds.map((id) => itemsById.get(id) || { id, name: 'Document ' + id, status: 'ready' });
    this.state.set('chat.selectedDocIds', normalizedIds);
    this.state.set('chat.selectedDocs', normalizedItems);
    try { this.state.set('documents.selectedIds', normalizedIds); } catch {}
    try { this.state.set('documents.selectionMeta', normalizedItems); } catch {}

    // ✅ Option A : Auto-activation intelligente du RAG
    // Lorsque des documents sont sélectionnés ET que le RAG est désactivé, l'activer automatiquement
    if (normalizedIds.length > 0 && !this.state.get('chat.ragEnabled')) {
      this.state.set('chat.ragEnabled', true);
      this.showToast(`RAG activé automatiquement - ${normalizedIds.length} document(s) sélectionné(s)`);
    }

    const threadId = this.getCurrentThreadId();
    if (threadId) {
      const docsForThread = normalizedItems
        .map((item) => {
          const num = Number(item?.id);
          if (!Number.isFinite(num)) return null;
          return {
            doc_id: Math.trunc(num),
            id: Math.trunc(num),
            name: item?.name || `Document ${num}`,
            status: item?.status || 'ready',
          };
        })
        .filter(Boolean);
      try { this.state.set(`threads.map.${threadId}.docs`, docsForThread); } catch {}
    }
  }

  handleThreadSwitch(payload = {}) {
    const threadId = payload?.id || payload?.thread?.id || payload?.thread_id;
    if (!threadId) return;
    this.loadedThreadId = null;
    this.state.set('chat.isLoading', false);
    try { this.state.set('threads.currentId', threadId); } catch {}
    const detail = Array.isArray(payload?.messages) ? payload : this.state.get('threads.map.' + threadId);
    if (detail) {
      this.hydrateFromThread(detail);
    } else {
      this.hydrateFromThread({ id: threadId, messages: [] });
    }
  }

  handleAnalysisStatus({ session_id, status, error, reason, retry_after } = {}) {
    const rawStatus = typeof status === 'string' ? status.trim().toLowerCase() : '';
    const normalizedStatus = rawStatus === 'failed' ? 'error' : (rawStatus || 'unknown');
    const payload = {
      session_id: session_id || null,
      status: normalizedStatus,
      rawStatus: rawStatus || null,
      error: error || null,
      reason: reason || null,
      retryAfter: retry_after ?? null,
      at: Date.now()
    };
    this.state.set('chat.lastAnalysis', payload);
    console.log('[Chat] ws:analysis_status', { session_id, status: normalizedStatus, error, reason });

    const now = Date.now();
    const delta = now - this._lastToastAt;

    if (normalizedStatus === 'completed') {
      if (delta > 1000) {
        this._lastToastAt = now;
        const message = 'Mémoire consolidée ✓';
        if (this.eventBus?.emit) this.eventBus.emit('ui:toast', { kind: 'info', text: message });
        else this.showToast(message);
      }
      return;
    }

    if (normalizedStatus === 'error') {
      if (delta > 1000) {
        this._lastToastAt = now;
        let detail = '';
        if (typeof error === 'string' && error.trim()) {
          const cleaned = error.trim().split('\n')[0].slice(0, 140);
          detail = ` (${cleaned})`;
        } else if (typeof reason === 'string' && reason.trim()) {
          const cleaned = reason.trim().split('\n')[0].slice(0, 140);
          detail = ` (${cleaned})`;
        }
        const message = `Analyse mémoire : échec${detail}`;
        const retryPayload = { force: true, source: 'analysis_status_toast', useActiveThread: true };
        if (this.eventBus?.emit) {
          this.eventBus.emit('ui:toast', {
            kind: 'error',
            text: message,
            action: {
              label: 'Réessayer',
              event: 'memory:tend',
              payload: retryPayload
            },
            duration: 6500
          });
        } else {
          this.showToast(message);
        }
      }
      return;
    }

    if (normalizedStatus === 'skipped' && delta > 1000) {
      this._lastToastAt = now;
      const note = (typeof reason === 'string' && reason.trim()) ? ` (${reason.trim()})` : '';
      const message = `Analyse mémoire ignorée${note}`;
      if (this.eventBus?.emit) this.eventBus.emit('ui:toast', { kind: 'warning', text: message });
      else this.showToast(message);
    }
  }

handleMessagePersisted(payload = {}) {
  try {
    const originalIdRaw = payload.message_id ?? payload.temp_id ?? payload.client_id ?? payload.id;
    const persistedIdRaw = payload.id ?? null;
    const originalId = originalIdRaw ? String(originalIdRaw) : null;
    const persistedId = persistedIdRaw ? String(persistedIdRaw) : (originalId || null);
    if (!originalId && !persistedId) return;
    const role = String(payload.role || '').toLowerCase();
    const agentIdHintRaw = payload.agent_id || (role === 'assistant' ? null : this.state.get('chat.currentAgentId'));
    const agentIdHint = agentIdHintRaw ? String(agentIdHintRaw).trim().toLowerCase() : null;

    if (this._pendingMsg && originalId && this._pendingMsg.id === originalId) {
      this._pendingMsg.triedRest = true;
    }

    const candidateBuckets = new Set();
    if (agentIdHint) candidateBuckets.add(agentIdHint);
    if (originalId && this._messageBuckets.has(originalId)) {
      const mapped = this._messageBuckets.get(originalId);
      if (mapped) candidateBuckets.add(mapped);
    }
    if (originalId && this._lastChunkByMessage.has(originalId)) {
      const chunkValue = this._lastChunkByMessage.get(originalId);
      if (persistedId) {
        this._lastChunkByMessage.set(persistedId, chunkValue);
      }
      this._lastChunkByMessage.delete(originalId);
    }
    if (persistedId && this._messageBuckets.has(persistedId)) {
      const mapped = this._messageBuckets.get(persistedId);
      if (mapped) candidateBuckets.add(mapped);
    }

    try {
      const active = this.state.get('chat.activeAgent');
      if (active) candidateBuckets.add(active);
    } catch {}
    if (!candidateBuckets.size) {
      try {
        const map = this.state.get('chat.messages') || {};
        Object.keys(map || {}).forEach((key) => candidateBuckets.add(key));
      } catch {}
    }

    const updatedBuckets = [];
    candidateBuckets.forEach((aid) => {
      if (!aid) return;
      const statePath = `chat.messages.${aid}`;
      const list = this.state.get(statePath) || [];
      const idx = list.findIndex((m) => m && (m.id === originalId || m.id === persistedId));
      if (idx >= 0) {
        const current = list[idx] || {};
        const msg = { ...current, persisted: true };
        if (msg.meta && typeof msg.meta === 'object') {
          msg.meta = { ...msg.meta, persisted: true, persisted_by: 'backend' };
          if (msg.meta.opinion_request && typeof msg.meta.opinion_request === 'object' && persistedId) {
            msg.meta.opinion_request = { ...msg.meta.opinion_request, request_id: persistedId };
          }
        } else {
          msg.meta = { persisted: true, persisted_by: 'backend' };
        }
        if (persistedId) {
          msg.id = persistedId;
        }
        const next = [...list];
        next[idx] = msg;
        this.state.set(statePath, next);
        updatedBuckets.push({ bucket: aid, id: msg.id });
      }
    });

    updatedBuckets.forEach(({ bucket, id }) => {
      if (originalId && originalId !== id) {
        this._messageBuckets.delete(originalId);
      }
      const key = id || originalId;
      if (key) this._rememberMessageBucket(key, bucket);
    });

    this._updateThreadCacheFromBuckets();

    if (role === 'assistant') {
      if (originalId && this._assistantPersistedIds.has(originalId)) {
        this._assistantPersistedIds.delete(originalId);
      }
      if (persistedId) {
        this._assistantPersistedIds.add(persistedId);
      }
    }
  } catch (e) {
    console.warn('[Chat] handleMessagePersisted erreur', e);
  }
}

  /* ============================ Hooks RAG/Mémoire ============================ */
  handleMemoryBanner(payload = {}) {
    try { this.state.set('chat.memoryBannerAt', Date.now()); } catch {}

    const { stm_content = '', ltm_content = '', ltm_items = 0, has_stm = false, agent_id = 'system' } = payload;

    // Log pour debug
    console.log('[Chat] handleMemoryBanner:', { agent_id, has_stm, ltm_items, stm_length: stm_content.length, ltm_length: ltm_content.length });

    // Afficher un message système avec le contenu de la mémoire
    if (has_stm || ltm_items > 0) {
      const parts = [];
      if (stm_content && stm_content.trim()) {
        parts.push(`**Résumé de session:**\n${stm_content}`);
      }
      if (ltm_content && ltm_content.trim()) {
        parts.push(`**Faits & souvenirs (${ltm_items} items):**\n${ltm_content}`);
      }

      if (parts.length > 0) {
        const memoryMessage = {
          id: `memory_${Date.now()}`,
          role: 'system',
          content: `🧠 **Mémoire chargée**\n\n${parts.join('\n\n---\n\n')}`,
          timestamp: Date.now(),
          agent_id: agent_id
        };

        // Déterminer le bucket de l'agent qui répond (pour que le message soit visible)
        const bucketId = this._determineBucketForMessage(agent_id, null);
        console.log('[Chat] Adding memory message to bucket:', bucketId);

        // Ajouter le message dans le bucket de l'agent actuel
        try {
          const pathKey = `chat.messages.${bucketId}`;
          const messages = this.state.get(pathKey) || [];
          this.state.set(pathKey, [...messages, memoryMessage]);
          this._rememberMessageBucket(memoryMessage.id, bucketId);
        } catch (err) {
          console.warn('[Chat] Failed to add memory message to state:', err);
        }
      }
    }

    this.showToast(`Mémoire chargée ✓ (${ltm_items} items)`);
  }

  handleConceptRecall(payload = {}) {
    console.log('[Chat] handleConceptRecall:', payload);

    if (!this.recallBanner) {
      console.warn('[Chat] ConceptRecallBanner not initialized, cannot display recalls');
      return;
    }

    const recalls = payload?.recalls;
    if (!recalls || !Array.isArray(recalls) || recalls.length === 0) {
      console.log('[Chat] No recalls to display');
      return;
    }

    try {
      this.recallBanner.show(recalls);
      console.log(`[Chat] Displayed ${recalls.length} concept recall(s)`);
    } catch (err) {
      console.error('[Chat] Failed to display concept recalls:', err);
    }
  }

  handleRagStatus(payload = {}) {
    const st = String(payload.status || '').toLowerCase();
    this.state.set('chat.ragStatus', st || 'idle');
    if (st === 'searching') this.showToast('RAG : recherche en cours…');
    if (st === 'found') this.showToast('RAG : sources trouvées ✓');
  }

  async handleMemoryTend(payload = {}) {
    const forced = payload?.force === true;
    const now = Date.now();
    if (!forced && (now - this._lastMemoryTendAt) < this._memoryTendThrottleMs) return;
    this._lastMemoryTendAt = now;

    const request = {};
    const explicitThread = payload?.thread_id ?? payload?.threadId ?? null;
    if (explicitThread && typeof explicitThread === 'string' && explicitThread.trim()) {
      request.thread_id = explicitThread.trim();
    } else if (payload?.useActiveThread) {
      const activeThread = this.getCurrentThreadId();
      if (activeThread) request.thread_id = activeThread;
    }

    try {
      const previous = this.state?.get?.('chat.lastAnalysis') || {};
      const sessionValue = request.thread_id || previous.session_id || null;
      this.state?.set?.('chat.lastAnalysis', {
        ...previous,
        session_id: sessionValue,
        status: 'running',
        rawStatus: 'running',
        error: null,
        reason: null,
        at: Date.now()
      });
    } catch (_) {}

    try {
      if (!payload?.quiet) this.showToast('Analyse mémoire démarrée…');
      await api.tendMemory(request);
      // Le backend émettra ensuite ws:analysis_status → géré dans handleAnalysisStatus()
    } catch (e) {
      console.error('[Chat] memory.tend error', e);
      if (e?.status === 401) {
        this.eventBus.emit?.('auth:missing', { reason: 401, source: 'memory:tend' });
        this.showToast('Connexion requise pour la mémoire.');
        return;
      }
      this.showToast('Analyse mémoire : échec');
    }
  }

  async handleMemoryClear() {
    try {
      this.showToast('Nettoyage mémoire…');
      if (typeof api.clearMemory === 'function') {
        await api.clearMemory();
      } else {
        // Fallback doux si l’endpoint n’existe pas encore
        await api.tendMemory();
      }
      // Reset local (affichage OFF)
      try {
        this.state.set('chat.memoryStats', { has_stm: false, ltm_items: 0, ltm_injected: 0, ltm_candidates: 0, injected: false, ltm_skipped: false });
        this.state.set('chat.memoryBannerAt', null);
      } catch {}
      this.showToast('Mémoire effacée ✓');
    } catch (e) {
      console.error('[Chat] memory.clear error', e);
      if (e?.status === 401) {
        this.eventBus.emit?.('auth:missing', { reason: 401, source: 'memory:clear' });
        this.showToast('Connexion requise pour la mémoire.');
        return;
      }
      this.showToast('Effacement mémoire : échec');
    }
  }

  _sanitizeDocIds(raw) {
    const source = Array.isArray(raw) ? raw : (raw == null ? [] : [raw]);
    const cleaned = [];
    const seen = new Set();
    for (const value of source) {
      const num = Number.parseInt(String(value ?? '').trim(), 10);
      if (!Number.isFinite(num)) continue;
      if (seen.has(num)) continue;
      seen.add(num);
      cleaned.push(num);
    }
    return cleaned;
  }

  _normalizeThreadDocsForState(docs) {
    const normalized = [];
    const seen = new Set();
    for (const doc of docs || []) {
      const rawId = doc?.doc_id ?? doc?.id ?? doc;
      const num = Number(rawId);
      if (!Number.isFinite(num)) continue;
      const docId = Math.trunc(num);
      if (seen.has(docId)) continue;
      seen.add(docId);

      const statusRaw = doc?.status;
      const status = statusRaw == null ? 'ready' : (String(statusRaw).toLowerCase() || 'ready');
      normalized.push({
        doc_id: docId,
        id: docId,
        name: doc?.filename || doc?.name || doc?.title || `Document ${docId}`,
        status,
        weight: Number.isFinite(doc?.weight) ? Number(doc.weight) : 1,
        last_used_at: doc?.last_used_at ?? null,
      });
    }
    return normalized;
  }

  _flattenMessagesFromState() {
    const buckets = this.state.get('chat.messages') || {};
    const combined = [];
    for (const [agentId, list] of Object.entries(buckets)) {
      if (!Array.isArray(list)) continue;
      for (const message of list) {
        if (!message) continue;
        const cloned = { ...message };
        if (!cloned.agent_id) cloned.agent_id = agentId;
        if (cloned.created_at === undefined && cloned.timestamp !== undefined) {
          cloned.created_at = cloned.timestamp;
        }
        combined.push(cloned);
      }
    }
    return combined.sort((a, b) => this._compareTimestamps(a?.created_at ?? a?.timestamp, b?.created_at ?? b?.timestamp));
  }

  _compareTimestamps(a, b) {
    const left = this._toEpoch(a);
    const right = this._toEpoch(b);
    if (left === right) return 0;
    return left - right;
  }

  _toEpoch(value) {
    if (value == null) return 0;
    if (value instanceof Date) {
      const ms = value.getTime();
      return Number.isFinite(ms) ? ms : 0;
    }
    if (typeof value === 'number' && Number.isFinite(value)) {
      if (value > 1e12) return value;
      if (value > 1e9) return Math.trunc(value * 1000);
      return value;
    }
    if (typeof value === 'string') {
      const trimmed = value.trim();
      if (trimmed) {
        const parsed = Date.parse(trimmed);
        if (!Number.isNaN(parsed)) return parsed;
        const numeric = Number(trimmed);
        if (Number.isFinite(numeric)) {
          return this._toEpoch(numeric);
        }
      }
    }
    return 0;
  }

  _updateThreadCacheFromBuckets(threadId = null, extras = {}) {
    try {
      const targetId = threadId || this.getCurrentThreadId();
      if (!targetId) return;
      const flattened = this._flattenMessagesFromState();
      const threadKey = `threads.map.${targetId}`;
      const current = this.state.get(threadKey) || { id: targetId, messages: [] };
      const next = { ...current, id: targetId, messages: flattened };
      if (extras && typeof extras === 'object') {
        if (extras.metadata) next.metadata = extras.metadata;
      }
      this.state.set(threadKey, next);
    } catch (err) {
      console.warn('[Chat] thread cache update failed', err);
    }
  }

  _applyMemoryMetadata(sessionId, metadata) {
    try {
      const summary = typeof metadata?.summary === 'string' ? metadata.summary : '';
      const concepts = Array.isArray(metadata?.concepts) ? metadata.concepts.filter(Boolean) : [];
      const entities = Array.isArray(metadata?.entities) ? metadata.entities.filter(Boolean) : [];
      const ltmCount = concepts.length + entities.length;
      this.state.set('chat.memoryStats', { has_stm: !!summary, ltm_items: ltmCount, ltm_injected: 0, ltm_candidates: ltmCount, injected: false, ltm_skipped: false });
      this.state.set('chat.memoryBannerAt', Date.now());
      this.state.set('chat.lastAnalysis', {
        session_id: sessionId || null,
        status: 'restored',
        summary,
        concepts,
        entities,
        at: Date.now()
      });
    } catch (err) {
      console.warn('[Chat] memory metadata sync failed', err);
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

        let threadId = this.getCurrentThreadId();
        if (!threadId) {
          this.showToast('Flux indisponible — aucun thread actif (fallback annulé).');
          return;
        }
        try {
          const fallbackMeta = { watchdog_fallback: true };
          fallbackMeta.use_rag = typeof p.use_rag === 'boolean' ? p.use_rag : !!this.state.get('chat.ragEnabled');
          const docIdsForFallback = Array.isArray(p.doc_ids) ? this._sanitizeDocIds(p.doc_ids) : [];
          if (docIdsForFallback.length) fallbackMeta.doc_ids = docIdsForFallback;

          try {
            await api.appendMessage(threadId, {
              role: 'user',
              content: p.text,
              agent_id: p.agent_id,
              meta: fallbackMeta
            });
          } catch (err) {
            // Si le thread n'existe pas, créer un nouveau thread et réessayer
            if (err?.status === 404) {
              console.warn('[Chat] Watchdog: Thread introuvable (404) → création nouveau thread');
              const created = await api.createThread({ type: 'chat', agent_id: p.agent_id });
              const newThreadId = created?.id;
              if (newThreadId) {
                // Mettre à jour l'état
                this.threadId = newThreadId;
                this.loadedThreadId = newThreadId;
                this.state.set('threads.currentId', newThreadId);
                this.state.set('chat.threadId', newThreadId);
                try { localStorage.setItem('emergence.threadId', newThreadId); } catch {}

                // Émettre l'événement pour reconnexion WebSocket
                this.eventBus.emit('threads:ready', { id: newThreadId });

                // Réessayer avec le nouveau thread
                await api.appendMessage(newThreadId, {
                  role: 'user',
                  content: p.text,
                  agent_id: p.agent_id,
                  meta: fallbackMeta
                });
                threadId = newThreadId;
              }
            } else {
              throw err;
            }
          }

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

  /**
   * Escape HTML special characters to prevent XSS
   * @private
   */
  _escapeHTML(s) {
    return String(s).replace(/[&<>"']/g, (c) => {
      switch (c) {
        case '&': return '&amp;';
        case '<': return '&lt;';
        case '>': return '&gt;';
        case '"': return '&quot;';
        default: return '&#39;';
      }
    });
  }
}

