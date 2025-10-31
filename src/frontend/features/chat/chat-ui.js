/**
 * ChatUI - V28.3.3 (proactive hints integration)
 * - Adopt glassmorphic layout with header/footer zones and auth host badge.
 * - Keeps mount-safe render, RAG sources, metrics, memory controls, and WS guards.
 * - Merges composer toolbar refinements and message bubble metadata.
 * - Integrates ProactiveHintsUI for contextual hints display
 */
import { EVENTS, AGENTS } from '../../shared/constants.js';
import { t } from '../../shared/i18n.js';
import { getInteractionCount, formatInteractionCount, getLastInteractionTimestamp } from '../threads/threads.js';
import { ProactiveHintsUI } from '../memory/ProactiveHintsUI.js';

export class ChatUI {
  constructor(eventBus, stateManager) {
    this.eventBus = eventBus;
    this.stateManager = stateManager;
    this.root = null;
    this.state = {
      isLoading: false,
      currentAgentId: 'anima',
      ragEnabled: false,
      ttsEnabled: false,  // TTS activé/désactivé
      messages: {},
      memoryBannerAt: null,
      lastAnalysis: null,
      metrics: { send_count: 0, ws_start_count: 0, last_ttfb_ms: 0, rest_fallback_count: 0, last_fallback_at: null },
      memoryStats: { has_stm: false, ltm_items: 0, ltm_injected: 0, ltm_candidates: 0, injected: false, ltm_skipped: false },
      selectedDocIds: [],
      selectedDocs: [],
      exportAgents: Object.keys(AGENTS),
      exportFormat: 'markdown',
      modelInfo: null,
      lastMessageMeta: null,
      areSourcesExpanded: false
    };
    this._panelHandlersBound = false;
    this.disableSidebarPanel = true;
    this._sourcesCache = [];
    this._decoderEl = null;
    this._globalKeyHandler = null;
    this._mounted = false;
    this._lastContainer = null;
    this.proactiveHintsUI = null;
    console.log('[ChatUI] V28.3.3 (proactive-hints) initialisee.');
  }

  destroy() {
    // Cleanup global keyboard handler
    if (this._globalKeyHandler) {
      document.removeEventListener('keydown', this._globalKeyHandler);
      this._globalKeyHandler = null;
    }
    // Cleanup proactive hints
    if (this.proactiveHintsUI) {
      this.proactiveHintsUI.destroy();
      this.proactiveHintsUI = null;
    }
    this.root = null;
  }

  render(container, chatState = {}) {
    if (!container) return;

    // Guard: Skip re-render if already mounted on same container with same state
    if (this._mounted && this._lastContainer === container) {
      console.log('[CHAT] Skip full re-render (already mounted) -> using update()');
      this.update(container, chatState);
      return;
    }

    this._mounted = true;
    this._lastContainer = container;
    this.root = container;
    this.state = { ...this.state, ...chatState };
    const agentTabs = this._agentTabsHTML(this.state.currentAgentId);

    container.innerHTML = `
      <div class="chat-container card">
        <div class="chat-header">
          <div class="chat-header-left">
            <div class="chat-title">Dialogue</div>
            <div class="agent-selector">${agentTabs}</div>
            <div class="rag-control">
              <button
                type="button"
                id="rag-power"
                class="rag-power"
                role="switch"
                aria-checked="${String(!!this.state.ragEnabled)}"
                aria-label="${this.state.ragEnabled ? 'RAG actif' : 'RAG inactif'}"
                title="${this.state.ragEnabled ? 'Désactiver le RAG' : 'Activer le RAG'}">
                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">
                  <path d="M12 2v10M6.34 6.34a8 8 0 1 0 11.32 0"></path>
                </svg>
              </button>
              <span class="rag-label">RAG</span>
            </div>
            <div class="rag-control">
              <button
                type="button"
                id="tts-power"
                class="rag-power"
                role="switch"
                aria-checked="${String(!!this.state.ttsEnabled)}"
                aria-label="${this.state.ttsEnabled ? 'TTS actif' : 'TTS inactif'}"
                title="${this.state.ttsEnabled ? 'Désactiver la synthèse vocale' : 'Activer la synthèse vocale'}">
                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">
                  <path d="M11 5 6 9H2v6h4l5 4V5zM15.54 8.46a5 5 0 0 1 0 7.07M19.07 4.93a10 10 0 0 1 0 14.14"></path>
                </svg>
              </button>
              <span class="rag-label">TTS</span>
            </div>
          </div>
          <div class="chat-header-right">
            <div id="model-badge" class="model-badge" hidden></div>
            <div class="rag-control rag-control--mobile">
              <button
                type="button"
                id="rag-power-mobile"
                class="rag-power"
                role="switch"
                aria-checked="${String(!!this.state.ragEnabled)}"
                aria-label="${this.state.ragEnabled ? 'RAG actif' : 'RAG inactif'}"
                title="${this.state.ragEnabled ? 'Désactiver le RAG' : 'Activer le RAG'}">
                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">
                  <path d="M12 2v10M6.34 6.34a8 8 0 1 0 11.32 0"></path>
                </svg>
              </button>
              <span class="rag-label">RAG</span>
            </div>
            <div class="rag-control rag-control--mobile">
              <button
                type="button"
                id="tts-power-mobile"
                class="rag-power"
                role="switch"
                aria-checked="${String(!!this.state.ttsEnabled)}"
                aria-label="${this.state.ttsEnabled ? 'TTS actif' : 'TTS inactif'}"
                title="${this.state.ttsEnabled ? 'Désactiver la synthèse vocale' : 'Activer la synthèse vocale'}">
                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">
                  <path d="M11 5 6 9H2v6h4l5 4V5zM15.54 8.46a5 5 0 0 1 0 7.07M19.07 4.93a10 10 0 0 1 0 14.14"></path>
                </svg>
              </button>
              <span class="rag-label">TTS</span>
            </div>
            <div class="chat-actions" role="group" aria-label="Actions de conversation">
              <button type="button" class="chat-action-btn" data-role="chat-clear" title="Effacer les messages de l'agent actif" data-label="Effacer les messages de l'agent actif" data-title="Effacer les messages de l'agent actif">
                <span class="sr-only">Effacer les messages de l'agent actif</span>
                <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" focusable="false">
                  <path d="M9 3h6l1 2h4v2H4V5h4l1-2Zm1 6h2v8h-2V9Zm6 0h-2v8h2V9ZM8 9H6v8h2V9Z" fill="currentColor"></path>
                </svg>
              </button>
              <button type="button" class="chat-action-btn" data-role="chat-memory" title="Consolider la memoire de cet agent" data-label="Consolider la memoire pour cet agent" data-title="Consolider la memoire pour cet agent">
                <span class="sr-only">Consolider la memoire de l'agent actif</span>
                <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" focusable="false">
                  <path d="M8.5 3C6 3 4 5 4 7.5v1c0 .8-.3 1.5-.8 2.1A3.5 3.5 0 006 15.5V17a3 3 0 003 3h1v-7H8.5a.5.5 0 110-1H11V3.1A5.1 5.1 0 008.5 3Zm7 0c-1 0-2 .3-2.8.9V12h2.5a.5.5 0 110 1H12v7h1a3 3 0 003-3v-1.5a3.5 3.5 0 001.8-3.4c-.5-.6-.8-1.3-.8-2.1v-1C17 5 15 3 12.5 3Z" fill="currentColor"></path>
                </svg>
              </button>
              <button type="button" class="chat-action-btn" data-role="chat-export" title="Exporter toute la conversation" data-label="Exporter toute la conversation" data-title="Exporter toute la conversation">
                <span class="sr-only">Exporter toute la conversation</span>
                <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" focusable="false">
                  <path d="M12 3v12.17l3.59-3.58L17 13l-5 5-5-5 1.41-1.41L11 15.17V3h1Zm-7 14h14v2H5v-2Z" fill="currentColor"></path>
                </svg>
              </button>
            </div>
          </div>
        </div>
        <div class="chat-thread-meta" id="chat-thread-meta" hidden>
          <span class="chat-thread-meta__item" data-role="thread-date"></span>
          <span class="chat-thread-meta__separator" aria-hidden="true">•</span>
          <span class="chat-thread-meta__item" data-role="thread-count"></span>
        </div>
        <div class="concept-recall-container" style="display: none;"></div>
        <div class="chat-body">
          <div class="messages" id="chat-messages"></div>
          <div id="rag-sources" class="rag-sources"></div>
        </div>
        <div class="chat-footer">
          <div id="proactive-hints-container" class="proactive-hints-container"></div>
          <form id="chat-form" class="chat-form" autocomplete="off">
            <div class="chat-composer" data-role="chat-composer">
              <div class="chat-input-shell" data-role="chat-input-shell">
                <div class="chat-doc-chips" id="chat-doc-chips" aria-live="polite"></div>
                <textarea id="chat-input" class="chat-input" rows="1" placeholder="Ecris ton message..." aria-label="Message"></textarea>
                <button type="submit" id="chat-send" class="chat-send-button" title="Envoyer" aria-label="Envoyer">
                  <span class="sr-only">Envoyer</span>
                  <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" focusable="false">
                    <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" fill="currentColor"></path>
                  </svg>
                </button>
              </div>
            </div>
          </form>
        </div>
        <div id="chat-auth-overlay" class="chat-auth-overlay" role="alertdialog" aria-live="assertive" aria-hidden="true" hidden>
          <div class="chat-auth-overlay__content">
            <h2 class="chat-auth-overlay__title">${t('auth.login_required')}</h2>
            <p class="chat-auth-overlay__text">${t('auth.login_hint')}</p>
            <button type="button" class="chat-auth-overlay__action" data-role="chat-auth-login">${t('auth.login_action')}</button>
          </div>
        </div>
      </div>
    `;

    this.eventBus.emit?.('ui:auth:host-changed');
    this._ensureControlPanel();
    this._bindEvents(container);
    this._initProactiveHints(container);
    this.update(container, this.state);
    console.log('[CHAT] ChatUI rendu -> container.id =', container.id || '(anonyme)');
  }

  _initProactiveHints(container) {
    if (!container) return;

    // Destroy existing instance if any
    if (this.proactiveHintsUI) {
      this.proactiveHintsUI.destroy();
      this.proactiveHintsUI = null;
    }

    const hintsContainer = container.querySelector('#proactive-hints-container');
    if (!hintsContainer) {
      console.warn('[ChatUI] Proactive hints container not found');
      return;
    }

    // Initialize ProactiveHintsUI with custom configuration
    this.proactiveHintsUI = new ProactiveHintsUI(hintsContainer);

    // Override applyHint method to inject into chat input
    const chatInput = container.querySelector('#chat-input');
    if (chatInput) {
      const originalApplyHint = this.proactiveHintsUI.applyHint.bind(this.proactiveHintsUI);
      this.proactiveHintsUI.applyHint = (hint) => {
        console.info('[ChatUI] Applying hint to chat input', hint);

        // Try to get the preference or message from action_payload
        let textToInject = '';
        if (hint.action_payload?.preference) {
          textToInject = hint.action_payload.preference;
        } else if (hint.action_payload?.message) {
          textToInject = hint.action_payload.message;
        } else if (hint.message) {
          textToInject = hint.message;
        }

        if (textToInject) {
          // Inject into chat input
          const currentValue = chatInput.value.trim();
          if (currentValue) {
            // If there's already text, append with a space
            chatInput.value = currentValue + ' ' + textToInject;
          } else {
            chatInput.value = textToInject;
          }

          // Focus and position cursor at end
          chatInput.focus();
          chatInput.setSelectionRange(chatInput.value.length, chatInput.value.length);

          // Trigger input event to update textarea height
          chatInput.dispatchEvent(new Event('input', { bubbles: true }));

          // Show success notification
          this.eventBus.emit('ui:notification', {
            type: 'success',
            message: 'Hint appliqué au chat'
          });
        } else {
          // Fallback to original implementation
          originalApplyHint(hint);
        }
      };
    }

    console.info('[ChatUI] ProactiveHintsUI initialized');
  }
  update(container, chatState = {}) {
    if (!container) return;
    console.log('[ChatUI] 🔍 update() called with chatState.messages:', chatState.messages);
    const previousMeta = this.state.lastMessageMeta;
    this.state = { ...this.state, ...chatState };
    console.log('[ChatUI] 🔍 After merge, this.state.messages:', this.state.messages);
    console.log('[ChatUI] 🔍 currentAgentId:', this.state.currentAgentId);
    if (chatState && chatState.lastMessageMeta && chatState.lastMessageMeta !== previousMeta) {
      this.state.areSourcesExpanded = false;
    }
    this._ensureControlPanel();

    const ragBtn = container.querySelector('#rag-power');
    const ragBtnMobile = container.querySelector('#rag-power-mobile');
    const ragEnabled = !!this.state.ragEnabled;

    // Synchroniser l'état des deux boutons (desktop et mobile)
    [ragBtn, ragBtnMobile].forEach(btn => {
      if (btn) {
        btn.setAttribute('aria-checked', String(ragEnabled));
        btn.setAttribute('aria-label', ragEnabled ? 'RAG actif' : 'RAG inactif');
        btn.title = ragEnabled ? 'Désactiver le RAG' : 'Activer le RAG';
      }
    });

    this._renderDocChips(container.querySelector('#chat-doc-chips'), this.state.selectedDocs, this.state.selectedDocIds, ragEnabled);
    this._setActiveAgentTab(container, this.state.currentAgentId);

    const rawMessages = this.state.messages?.[this.state.currentAgentId];
    console.log('[ChatUI] 🔍 rawMessages for', this.state.currentAgentId, ':', rawMessages);
    const list = this._asArray(rawMessages).map((m) => this._normalizeMessage(m));
    console.log('[ChatUI] 🔍 Calling _renderMessages with', list.length, 'messages');
    this._renderMessages(container.querySelector('#chat-messages'), list);
    this._updateThreadMeta(container);

    const clearEl = container.querySelector('[data-role="chat-clear"]');
    if (clearEl) {
      if (list.length) {
        clearEl.removeAttribute('disabled');
        clearEl.classList.remove('is-disabled');
      } else {
        clearEl.setAttribute('disabled', 'disabled');
        clearEl.classList.add('is-disabled');
      }
    }
    const memoryEl = container.querySelector('[data-role="chat-memory"]');
    if (memoryEl) {
      const agentId = (this.state.currentAgentId || '').trim().toLowerCase() || 'anima';
      const agentInfo = AGENTS[agentId] || {};
      const agentLabel = agentInfo.label || agentInfo.name || this._humanizeAgentId(agentId) || agentId;
      memoryEl.setAttribute('aria-label', 'Consolider la memoire pour ' + agentLabel);
      memoryEl.setAttribute('title', 'Consolider la memoire pour ' + agentLabel);
      const lastAnalysis = this.state.lastAnalysis || {};
      const isRunning = lastAnalysis?.status === 'running';
      if (list.length === 0 || isRunning) {
        memoryEl.setAttribute('disabled', 'disabled');
        memoryEl.classList.add('is-disabled');
      } else {
        memoryEl.removeAttribute('disabled');
        memoryEl.classList.remove('is-disabled');
      }
    }
    const exportEl = container.querySelector('[data-role="chat-export"]');
    if (exportEl) {
      const buckets = this.state.messages && typeof this.state.messages === 'object' ? Object.values(this.state.messages) : [];
      const hasAny = buckets.some((bucket) => Array.isArray(bucket) && bucket.length > 0);
      if (hasAny) {
        exportEl.removeAttribute('disabled');
        exportEl.classList.remove('is-disabled');
      } else {
        exportEl.setAttribute('disabled', 'disabled');
        exportEl.classList.add('is-disabled');
      }
    }

    this._renderSources(container.querySelector('#rag-sources'), this.state.lastMessageMeta?.sources);

    this._updateControlPanelState();

    const met = this.state.metrics || {};
    const badge = container.querySelector('#model-badge');
    if (badge) {
      const mi = this.state.modelInfo || {};
      const lm = this.state.lastMessageMeta || {};
      const plannedProvider = (mi.provider || '').toString();
      const plannedModel = (mi.model || '').toString();
      const usedProvider = (lm.provider || '').toString();
      const usedModel = (lm.model || '').toString();
      const hasUsed = !!(usedProvider || usedModel);
      const usedLabel = hasUsed ? [usedProvider, usedModel].filter(Boolean).join(':') || usedProvider || usedModel : '';
      const plannedLabel = plannedProvider && plannedModel ? `${plannedProvider}:${plannedModel}` : '';
      const fallback = hasUsed && plannedLabel && (plannedProvider !== usedProvider || plannedModel !== usedModel);
      if (hasUsed) {
        badge.textContent = fallback ? `Fallback -> ${usedLabel}` : usedLabel;
        const ttfb = Number.isFinite(met.last_ttfb_ms) ? `${met.last_ttfb_ms} ms` : '-';
        badge.title = `Modele prevu: ${plannedLabel || 'n/d'} - Utilise: ${usedLabel || 'n/d'} - TTFB: ${ttfb}`;
        badge.hidden = false;
      } else {
        badge.textContent = '';
        badge.hidden = true;
        badge.removeAttribute('title');
      }
      badge.classList.toggle('is-fallback', fallback);
    }

    this._updateAuthOverlay(container);
  }

  _updateThreadMeta(container) {
    const host = container?.querySelector('#chat-thread-meta');
    if (!host) return;

    const dateEl = host.querySelector('[data-role="thread-date"]');
    const countEl = host.querySelector('[data-role="thread-count"]');
    const separatorEl = host.querySelector('.chat-thread-meta__separator');

    const safeGet = (pathKey) => {
      if (!this.stateManager || typeof this.stateManager.get !== 'function') return null;
      try { return this.stateManager.get(pathKey); }
      catch { return null; }
    };

    let threadId = this.state.threadId || null;
    if (!threadId) {
      const altId = safeGet('chat.threadId');
      const fallbackId = safeGet('threads.currentId');
      threadId = altId || fallbackId || null;
    }

    if (!threadId) {
      if (dateEl) {
        dateEl.textContent = '';
        dateEl.removeAttribute('title');
        delete dateEl.dataset.iso;
      }
      if (countEl) {
        countEl.textContent = '';
        countEl.removeAttribute('data-count');
        countEl.setAttribute('hidden', 'hidden');
      }
      if (separatorEl) separatorEl.setAttribute('hidden', 'hidden');
      host.hidden = true;
      host.setAttribute('hidden', 'hidden');
      delete host.dataset.threadId;
      return;
    }

    host.dataset.threadId = threadId;

    const threadsState = safeGet('threads') || {};
    const threadsMap = threadsState && typeof threadsState.map === 'object' ? threadsState.map : null;
    const entry = threadsMap && Object.prototype.hasOwnProperty.call(threadsMap, threadId) ? threadsMap[threadId] : null;
    const record = entry && typeof entry === 'object' ? (entry.thread || entry) : null;

    let interactionCount = null;
    let interactionLabel = null;
    if (entry || record) {
      interactionCount = getInteractionCount(entry, record);
      interactionLabel = formatInteractionCount(interactionCount);
    }

    if (countEl) {
      if (interactionLabel) {
        countEl.textContent = 'Interactions : ' + interactionLabel;
        countEl.dataset.count = String(interactionCount ?? 0);
        countEl.removeAttribute('hidden');
      } else {
        countEl.textContent = 'Interactions : inconnues';
        countEl.removeAttribute('data-count');
        countEl.removeAttribute('hidden');
      }
    }

    let lastInteraction = entry || record ? getLastInteractionTimestamp(entry, record) : null;
    if (!lastInteraction) {
      const fallbacks = [
        this.state.lastMessageMeta?.created_at,
        this.state.lastMessageMeta?.timestamp,
        record?.updated_at,
        record?.updatedAt,
        record?.last_message_at,
        record?.lastMessageAt,
        entry?.updated_at,
        entry?.updatedAt,
        entry?.last_message_at,
        entry?.lastMessageAt
      ];
      for (const candidate of fallbacks) {
        if (candidate) {
          lastInteraction = candidate;
          break;
        }
      }
    }

    if (dateEl) {
      if (lastInteraction) {
        const { display, iso } = this._formatTimestamp(lastInteraction);
        dateEl.textContent = 'Derniere activite : ' + display;
        dateEl.setAttribute('title', iso);
        dateEl.dataset.iso = iso;
        dateEl.removeAttribute('hidden');
      } else {
        dateEl.textContent = 'Derniere activite : inconnue';
        dateEl.removeAttribute('title');
        delete dateEl.dataset.iso;
        dateEl.removeAttribute('hidden');
      }
    }

    if (separatorEl) {
      const hasDate = !!(dateEl && dateEl.textContent && dateEl.textContent.trim());
      const hasCount = !!(countEl && countEl.textContent && countEl.textContent.trim());
      if (hasDate && hasCount) separatorEl.removeAttribute('hidden');
      else separatorEl.setAttribute('hidden', 'hidden');
    }

    host.hidden = false;
    host.removeAttribute('hidden');
  }

  _bindEvents(container) {
    const form = container.querySelector('#chat-form');
    const input = container.querySelector('#chat-input');
    const ragBtn = container.querySelector('#rag-power');
    const ragBtnMobile = container.querySelector('#rag-power-mobile');
    const sendBtn = container.querySelector('#chat-send');
    const clearButton = container.querySelector('[data-role="chat-clear"]');
    const memoryButton = container.querySelector('[data-role="chat-memory"]');
    const exportButton = container.querySelector('[data-role="chat-export"]');
    const messagesHost = container.querySelector('#chat-messages');
    const sourcesHost = container.querySelector('#rag-sources');
    this._ensureControlPanel();
    this._updateControlPanelState();

    const autosize = () => this._autoGrow(input);
    setTimeout(autosize, 0);
    input?.addEventListener('input', autosize);
    window.addEventListener('resize', autosize);

    form?.addEventListener('submit', (e) => {
      e.preventDefault();
      const textValue = (input?.value || '').trim();
      if (!textValue) return;
      this.eventBus.emit(EVENTS.CHAT_SEND, { text: textValue, agent: 'user' });
      input.value = '';
      autosize();
    });

    input?.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        if (typeof form?.requestSubmit === 'function') form.requestSubmit();
        else form?.dispatchEvent(new Event('submit', { cancelable: true }));
      }
      // Shift+Enter for new line is default behavior, no need to handle
    });

    // Global keyboard shortcut: Ctrl/Cmd+K to focus chat input
    const globalKeyHandler = (e) => {
      if ((e.ctrlKey || e.metaKey) && (e.key === 'k' || e.key === 'K')) {
        // Don't interfere if user is already in an input/textarea
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
          return;
        }
        e.preventDefault();
        input?.focus();
      }
    };

    document.addEventListener('keydown', globalKeyHandler);

    // Store reference for cleanup
    if (!this._globalKeyHandler) {
      this._globalKeyHandler = globalKeyHandler;
    }

    sendBtn?.addEventListener('click', () => {
      if (typeof form?.requestSubmit === 'function') form.requestSubmit();
      else form?.dispatchEvent(new Event('submit', { cancelable: true }));
    });

    clearButton?.addEventListener('click', () => {
      this.eventBus.emit(EVENTS.CHAT_CLEAR);
    });

    memoryButton?.addEventListener('click', () => {
      const agentId = (this.state.currentAgentId || '').trim();
      if (!agentId) return;
      const payload = { agent_id: agentId, agentId };
      let threadId = this.state.threadId || null;
      if (!threadId && this.stateManager?.get) {
        threadId = this.stateManager.get('chat.threadId') || this.stateManager.get('threads.currentId');
      }
      if (threadId) payload.thread_id = threadId;
      else payload.useActiveThread = true;
      this.eventBus.emit('memory:tend', payload);
    });

    exportButton?.addEventListener('click', () => {
      this.eventBus.emit(EVENTS.CHAT_EXPORT);
    });

    const authLoginBtn = container.querySelector('[data-role="chat-auth-login"]');
    authLoginBtn?.addEventListener('click', () => {
      try { this.eventBus.emit('auth:login', {}); }
      catch (err) { console.warn('[ChatUI] auth login emit failed', err); }
    });

    const toggleRag = (e) => {
      const clickedBtn = e.currentTarget;
      const on = clickedBtn.getAttribute('aria-checked') === 'true';
      const next = !on;

      // Synchroniser l'état des deux boutons
      [ragBtn, ragBtnMobile].forEach(btn => {
        if (btn) {
          btn.setAttribute('aria-checked', String(next));
          btn.setAttribute('aria-label', next ? 'RAG actif' : 'RAG inactif');
          btn.title = next ? 'Désactiver le RAG' : 'Activer le RAG';
        }
      });

      this.eventBus.emit(EVENTS.CHAT_RAG_TOGGLED, { enabled: next });
    };

    // Attacher le handler aux deux boutons
    ragBtn?.addEventListener('click', toggleRag);
    ragBtnMobile?.addEventListener('click', toggleRag);

    // TTS Toggle (desktop + mobile)
    const ttsBtn = container.querySelector('#tts-power');
    const ttsBtnMobile = container.querySelector('#tts-power-mobile');
    const toggleTTS = (e) => {
      const clickedBtn = e.currentTarget;
      const on = clickedBtn.getAttribute('aria-checked') === 'true';
      const next = !on;

      // Synchroniser les deux boutons (desktop + mobile)
      [ttsBtn, ttsBtnMobile].forEach(btn => {
        if (btn) {
          btn.setAttribute('aria-checked', String(next));
          btn.setAttribute('aria-label', next ? 'TTS actif' : 'TTS inactif');
          btn.title = next ? 'Désactiver la synthèse vocale' : 'Activer la synthèse vocale';
        }
      });

      this.state.ttsEnabled = next;
      console.log(`[ChatUI] TTS ${next ? 'activé' : 'désactivé'}`);
    };

    // Attacher le handler aux deux boutons
    ttsBtn?.addEventListener('click', toggleTTS);
    ttsBtnMobile?.addEventListener('click', toggleTTS);

    const docChipHost = container.querySelector('#chat-doc-chips');
    docChipHost?.addEventListener('click', (e) => {
      const target = e.target;
      if (!target || typeof target.closest !== 'function') return;
      const removeBtn = target.closest('[data-doc-remove]');
      if (removeBtn) {
        const docId = removeBtn.getAttribute('data-doc-id');
        if (docId) {
          const evt = EVENTS?.DOCUMENTS_CMD_DESELECT || 'documents:cmd:deselect';
          try { this.eventBus.emit(evt, { id: docId }); } catch {}
        }
        e.preventDefault();
        return;
      }
      const clearBtn = target.closest('[data-doc-clear]');
      if (clearBtn) {
        const ids = Array.isArray(this.state?.selectedDocIds) ? this.state.selectedDocIds : [];
        if (ids.length) {
          const evt = EVENTS?.DOCUMENTS_CMD_DESELECT || 'documents:cmd:deselect';
          for (const id of ids) {
            if (id || id === 0) {
              try { this.eventBus.emit(evt, { id }); } catch {}
            }
          }
        }
        e.preventDefault();
      }
    });

    container.querySelector('.agent-selector')?.addEventListener('click', (e) => {
      const btn = e.target.closest('button[data-agent-id]');
      if (!btn) return;
      const agentId = btn.getAttribute('data-agent-id');
      this.eventBus.emit(EVENTS.CHAT_AGENT_SELECTED, agentId);
      this._setActiveAgentTab(container, agentId);
    });

    if (sourcesHost) {
      sourcesHost.addEventListener('click', (e) => {
        const toggleBtn = e.target.closest('[data-role="rag-sources-toggle"]');
        if (toggleBtn) {
          const next = toggleBtn.getAttribute('aria-expanded') !== 'true';
          this.state.areSourcesExpanded = next;
          this._renderSources(sourcesHost, this._sourcesCache);
          e.preventDefault();
          return;
        }
        const chip = e.target.closest('button[data-doc-id]');
        if (!chip) return;
        if (!this.state.areSourcesExpanded) {
          this.state.areSourcesExpanded = true;
          this._renderSources(sourcesHost, this._sourcesCache);
          return;
        }
        const info = {
          document_id: chip.getAttribute('data-doc-id'),
          filename: chip.getAttribute('data-filename'),
          page: Number(chip.getAttribute('data-page') || '0') || null,
          excerpt: chip.getAttribute('data-excerpt') || ''
        };
        this.eventBus.emit('rag:source:click', info);
      });
    }

    if (messagesHost) {
      messagesHost.addEventListener('click', async (event) => {
        const opinionBtn = event.target.closest('[data-role="ask-opinion"]');
        if (opinionBtn) {
          if (opinionBtn.hasAttribute('disabled')) {
            event.preventDefault();
            return;
          }
          const targetAgentId = (opinionBtn.getAttribute('data-target-agent') || '').trim().toLowerCase();
          const sourceAgentId = (opinionBtn.getAttribute('data-source-agent') || '').trim().toLowerCase();
          const messageId = (opinionBtn.getAttribute('data-message-id') || '').trim();
          if (!targetAgentId || !messageId) {
            console.warn('[ChatUI] opinion button missing target/message id');
            return;
          }
          const rawMessage = opinionBtn.getAttribute('data-message') || '';
          const messageText = this._decodeHTML(rawMessage).replace(/\r?\n/g, '\n').trim();
          const payload = {
            target_agent_id: targetAgentId,
            message_id: messageId,
          };
          if (sourceAgentId) payload.source_agent_id = sourceAgentId;
          if (messageText) payload.message_text = messageText;
          let emitted = false;
          try {
            opinionBtn.setAttribute('disabled', 'true');
            opinionBtn.setAttribute('aria-disabled', 'true');
            if (this.eventBus?.emit) {
              this.eventBus.emit(EVENTS.CHAT_REQUEST_OPINION, payload);
              emitted = true;
            }
          } catch (err) {
            console.error('[ChatUI] opinion request emit failed', err);
          } finally {
            if (!emitted) {
              opinionBtn.removeAttribute('disabled');
              opinionBtn.removeAttribute('aria-disabled');
            }
          }
          event.preventDefault();
          return;
        }

        // Listen button supprimé - TTS auto-play géré via toggle header

        // Handle copy button
        const button = event.target.closest('[data-role="copy-message"]');
        if (!button || button.hasAttribute('disabled')) return;
        const raw = button.getAttribute('data-message') || '';
        const textValue = this._decodeHTML(raw).replace(/\r?\n/g, '\n').trimEnd();
        if (!textValue) {
          this._flashCopyState(button, false);
          return;
        }
        const ok = await this._copyToClipboard(textValue);
        this._flashCopyState(button, ok);
      });
    }

    try {
      const off = this.eventBus?.on?.('documents:changed', async (payload = {}) => {
        await this._onDocumentsChanged(container, payload);
      });
      if (typeof off === 'function') this._offDocumentsChanged = off;
    } catch {}
  }

  _updateAuthOverlay(container) {
    if (!container) return;
    const root = container.querySelector('.chat-container');
    if (!root) return;
    const overlay = root.querySelector('#chat-auth-overlay');
    if (!overlay) return;
    const requiresAuth = !!this.state.authRequired;
    overlay.hidden = !requiresAuth;
    overlay.setAttribute('aria-hidden', requiresAuth ? 'false' : 'true');
    overlay.classList.toggle('is-visible', requiresAuth);
    root.classList.toggle('chat-auth-required', requiresAuth);
  }

  _ensureControlPanel() {
    try {
      if (this.disableSidebarPanel) {
        if (this._controlPanel?.parentElement) {
          this._controlPanel.remove();
        }
        this._controlPanel = null;
        this._panelHandlersBound = false;
        return null;
      }
      const host = document.getElementById('settings-container');
      if (!host) return null;
      let panel = host.querySelector('[data-role="chat-control-panel"]');
      if (!panel) {
        panel = document.createElement('section');
        panel.dataset.role = 'chat-control-panel';
        panel.className = 'chat-controls-panel';
        panel.innerHTML = this._controlPanelMarkup();
        host.appendChild(panel);
      }
      panel.classList.remove('is-hidden');
      this._controlPanel = panel;
      if (!this._panelHandlersBound) {
        this._bindControlPanelEvents(panel);
        this._panelHandlersBound = true;
      }
      return panel;
    } catch (err) {
      console.error('[ChatUI] ensure control panel failed', err);
      return null;
    }
  }

  _controlPanelMarkup() {
    return `
      <div class="chat-controls-card">
        <div class="chat-controls-header">
          <span class="chat-controls-title">Memoire</span>
          <span id="memory-dot" class="chat-controls-dot" aria-hidden="true"></span>
        </div>
        <div class="chat-controls-status">
          <span id="memory-label" class="memory-label" title="Statut memoire">Memoire OFF</span>
          <span id="memory-counters" class="memory-counters">STM 0 | LTM 0</span>
        </div>
        <div class="chat-controls-actions">
          <button type="button" id="memory-analyze" class="button" title="Analyser / consolider la memoire">Analyser</button>
          <button type="button" id="memory-clear" class="button" title="Effacer la memoire de session">Clear</button>
        </div>
        <div class="chat-controls-actions">
          <button type="button" id="memory-open-center" class="button button-primary" title="Ouvrir le centre memoire">Centre memoire</button>
        </div>
      </div>
      <div class="chat-controls-card">
        <div id="chat-metrics" class="chat-metrics">
          <span id="metric-ttfb">TTFB: - ms</span>
          <span id="metric-fallbacks">Fallback REST: 0</span>
        </div>
      </div>
    `;
  }

  _bindControlPanelEvents(panel) {
    if (!panel) return;
    panel.querySelector('#memory-analyze')?.addEventListener('click', () => this.eventBus.emit('memory:tend', { useActiveThread: true }));
    panel.querySelector('#memory-clear')?.addEventListener('click', () => this.eventBus.emit('memory:clear'));
    panel.querySelector('#memory-open-center')?.addEventListener('click', () => this.eventBus.emit('memory:center:open'));
  }

  _updateControlPanelState() {
    const panel = this._ensureControlPanel();
    const lastAnalysis = this.state.lastAnalysis || {};
    const memoryOn = !!(this.state.memoryBannerAt || lastAnalysis.status === 'completed');
    const mem = this.state.memoryStats || {};

    if (panel) {
      const dot = panel.querySelector('#memory-dot');
      const lbl = panel.querySelector('#memory-label');
      const cnt = panel.querySelector('#memory-counters');

      if (dot) {
        dot.classList.toggle('is-on', memoryOn);
        dot.style.background = '';
        dot.style.boxShadow = '';
      }
      if (lbl) {
        lbl.textContent = memoryOn ? 'Memoire ON' : 'Memoire OFF';
        lbl.classList.toggle('is-off', !memoryOn);
      }
      if (cnt) {
        const stmTxt = mem.has_stm ? 'STM V' : 'STM 0';
        const totalLtm = Number.isFinite(Number(mem.ltm_items)) ? Number(mem.ltm_items) : 0;
        const injectedLtm = Number.isFinite(Number(mem.ltm_injected)) ? Number(mem.ltm_injected) : (mem.injected ? totalLtm : 0);
        let ltmTxt = `LTM ${totalLtm}`;
        if (totalLtm && injectedLtm !== totalLtm) {
          ltmTxt = `LTM ${injectedLtm}/${totalLtm}`;
        }
        let flags = '';
        if (mem.ltm_skipped) flags = ' | skip';
        else if (mem.injected) flags = ' | inj';
        cnt.textContent = `${stmTxt} | ${ltmTxt}${flags}`;
      }

      const met = this.state.metrics || {};
      const metricsHost = panel.querySelector('#chat-metrics');
      const ttfbEl = metricsHost?.querySelector('#metric-ttfb');
      const fbEl = metricsHost?.querySelector('#metric-fallbacks');
      if (ttfbEl) ttfbEl.textContent = `TTFB: ${Number.isFinite(met.last_ttfb_ms) ? met.last_ttfb_ms : 0} ms`;
      if (fbEl) fbEl.textContent = `Fallback REST: ${met.rest_fallback_count || 0}`;
    }

    this.eventBus.emit?.('memory:center:state', {
      memoryOn,
      memoryStats: mem,
      exportAgents: this.state.exportAgents,
      exportFormat: this.state.exportFormat
    });
  }

  async _onDocumentsChanged(container, payload) {
    try {
      let docs = Array.isArray(payload.items) ? payload.items : null;
      if (!docs) docs = await this._refetchDocuments();
      if (!Array.isArray(docs)) {
        this._renderSources(container.querySelector('#rag-sources'), []);
        return;
      }
      const ids = new Set(docs.map((d) => d?.id || d?.document_id || d?._id).filter(Boolean));
      const names = new Set(docs.map((d) => (d?.filename || d?.original_filename || d?.name || '').toString()).filter(Boolean));
      const meta = this.state.lastMessageMeta || {};
      const src = Array.isArray(meta.sources) ? meta.sources : [];
      const filtered = src.filter((s) => {
        const sid = (s.document_id || '').toString();
        const sname = (s.filename || '').toString();
        return (sid && ids.has(sid)) || (sname && names.has(sname));
      });
      if (filtered.length !== src.length) {
        this.state.lastMessageMeta = { ...meta, sources: filtered };
      }
      this._renderSources(container.querySelector('#rag-sources'), filtered);
    } catch (e) {
      console.error('[ChatUI] _onDocumentsChanged failed:', e);
      this._renderSources(container.querySelector('#rag-sources'), []);
    }
  }

  async _refetchDocuments() {
    try {
      const headers = {};
      const tokenGetter =
        (window?.EmergenceAuth && typeof window.EmergenceAuth.getToken === 'function' && window.EmergenceAuth.getToken) ||
        (this.stateManager && typeof this.stateManager.getAuthToken === 'function' && this.stateManager.getAuthToken) ||
        null;
      if (tokenGetter) {
        const token = await tokenGetter();
        if (token) headers.Authorization = `Bearer ${token}`;
      }
      const res = await fetch('/api/documents', { headers });
      if (!res.ok) return null;
      const data = await res.json();
      return Array.isArray(data) ? data : (Array.isArray(data?.items) ? data.items : null);
    } catch {
      return null;
    }
  }

  _autoGrow(el) {
    if (!el) return;
    const max = Math.floor(window.innerHeight * 0.45);
    const min = 52;
    el.style.height = 'auto';
    const next = Math.min(Math.max(el.scrollHeight, min), max);
    el.style.height = `${next}px`;
    el.style.overflowY = el.scrollHeight > max ? 'auto' : 'hidden';
  }

  _renderMessages(host, messages) {
    if (!host) return;
    const html = (messages || []).map((m) => this._messageHTML(m)).join('');
    host.innerHTML = html || '<div class="placeholder">Commencez à discuter.</div>';
    host.scrollTo(0, 1e9);
  }

  _renderDocChips(host, docs, docIds, ragEnabled) {
    if (!host) return;
    const ids = Array.isArray(docIds) ? docIds.map((id) => String(id)) : [];
    const map = new Map();
    if (Array.isArray(docs)) {
      for (const item of docs) {
        const id = String((item?.id ?? item?.document_id ?? item?.doc_id ?? '') || '').trim();
        if (!id || map.has(id)) continue;
        let name = item?.name ?? item?.filename ?? item?.title ?? '';
        name = String(name ?? '').trim();
        if (!name) name = 'Document ' + id;
        const statusRaw = item?.status;
        const status = statusRaw == null ? 'ready' : (String(statusRaw).toLowerCase() || 'ready');
        map.set(id, { id, name, status });
      }
    }
    const order = ids.length ? ids : Array.from(map.keys());
    if (!order.length) {
      host.innerHTML = '';
      host.setAttribute('hidden', 'hidden');
      host.removeAttribute('data-count');
      host.classList.remove('is-disabled');
      return;
    }
    host.removeAttribute('hidden');
    host.dataset.count = String(order.length);
    host.classList.toggle('is-disabled', !ragEnabled);
    const label = ragEnabled ? 'Documents actifs' : 'Documents sélectionnés (RAG off)';
    const chips = order.map((rawId) => {
      const id = String(rawId).trim();
      const info = map.get(id) || { id, name: 'Document ' + id, status: 'ready' };
      const safeId = this._escapeHTML(id);
      const safeName = this._escapeHTML(info.name);
      const status = (info.status || '').toString().toLowerCase();
      const safeStatus = this._escapeHTML(status);
      const statusSpan = status && status !== 'ready'
        ? '<span class="chat-doc-chip__status chat-doc-chip__status--' + safeStatus + '">' + safeStatus + '</span>'
        : '';
      return [
        '<button type="button" class="chat-doc-chip" data-doc-remove data-doc-id="' + safeId + '" title="Retirer ' + safeName + '">',
        '  <span class="chat-doc-chip__icon" aria-hidden="true"></span>',
        '  <span class="chat-doc-chip__label">' + safeName + '</span>',
        statusSpan ? '  ' + statusSpan : '',
        '  <span class="chat-doc-chip__close" aria-hidden="true">&times;</span>',
        '  <span class="sr-only">Retirer ' + safeName + '</span>',
        '</button>'
      ].filter(Boolean).join('');
    }).join('');
    host.innerHTML =
      '<div class="chat-doc-chips__header">' +
        '<span class="chat-doc-chips__title">' + this._escapeHTML(label) + '</span>' +
        '<button type="button" class="chat-doc-chips__clear" data-doc-clear' + (order.length ? '' : ' disabled') + '>Tout retirer</button>' +
      '</div>' +
      '<div class="chat-doc-chips__list">' + chips + '</div>';
  }

  _renderSources(host, sources) {
    if (!host) return;
    const items = Array.isArray(sources) ? sources.filter(Boolean) : [];
    this._sourcesCache = items;
    if (!items.length) {
      host.style.display = 'none';
      host.innerHTML = '';
      host.removeAttribute('data-count');
      host.removeAttribute('data-open');
      this.state.areSourcesExpanded = false;
      return;
    }

    const countLabel = items.length > 1 ? `${items.length} references` : '1 reference';
    const isOpen = !!this.state.areSourcesExpanded;
    const list = items.map((s, index) => {
      const filename = (s?.filename || 'Document').toString();
      const pageNumber = Number(s?.page) || 0;
      const pageLabel = pageNumber > 0 ? ` (p.${pageNumber})` : '';
      const displayName = `${filename}${pageLabel}`;
      const rawExcerpt = (s?.excerpt || '').toString().replace(/\s+/g, ' ').trim();
      const excerptText = rawExcerpt ? rawExcerpt.slice(0, 240) : '';
      const docId = (s?.document_id || `doc-${index}`).toString();
      const tooltip = (excerptText || displayName).replace(/\n/g, ' ');
      return `
        <li class="rag-source-item">
          <button
            type="button"
            class="rag-source-button"
            data-doc-id="${this._escapeHTML(docId)}"
            data-filename="${this._escapeHTML(filename)}"
            data-page="${pageNumber || ''}"
            data-excerpt="${this._escapeHTML(rawExcerpt)}"
            title="${this._escapeHTML(tooltip)}"
          >
            <span class="rag-source-line">
              <span class="rag-source-index">${index + 1}</span>
              <span class="rag-source-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" width="14" height="14">
                  <path d="M7 3h7l5 5v13H7z" fill="none" stroke="currentColor" stroke-width="1.4"></path>
                  <path d="M14 3v5h5" fill="none" stroke="currentColor" stroke-width="1.4"></path>
                </svg>
              </span>
              <span class="rag-source-name">${this._escapeHTML(displayName)}</span>
            </span>
            ${excerptText ? `<span class="rag-source-excerpt">${this._escapeHTML(excerptText)}</span>` : ''}
          </button>
        </li>`;
    }).join('');

    host.innerHTML = `
      <section class="rag-sources-panel ${isOpen ? 'is-open' : 'is-collapsed'}">
        <header class="rag-sources-header">
          <div class="rag-sources-summary">
            <span class="rag-sources-label">Sources</span>
            <span class="rag-sources-count">${countLabel}</span>
          </div>
          <button
            type="button"
            class="rag-sources-toggle"
            data-role="rag-sources-toggle"
            aria-expanded="${isOpen}"
            aria-controls="rag-sources-list"
            title="${isOpen ? 'Reduire les sources' : 'Afficher les sources'}"
          >
            <span class="rag-sources-toggle-icon" aria-hidden="true"></span>
            <span class="sr-only">${isOpen ? 'Reduire les sources' : 'Afficher les sources'}</span>
          </button>
        </header>
        <ul id="rag-sources-list" class="rag-source-list"${isOpen ? '' : ' hidden'} role="list">
          ${list}
        </ul>
      </section>
    `;
    host.style.display = 'block';
    host.dataset.count = String(items.length);
    host.dataset.open = isOpen ? 'true' : 'false';
  }
  _getAgentLabel(agentId) {
    if (!agentId) return 'Agent';
    const info = AGENTS[agentId] || {};
    return info.label || info.name || this._humanizeAgentId(agentId) || agentId;
  }


_hasOpinionFromAgent(agentId, messageId) {
  if (!agentId || !messageId) return false;
  try {
    const targetAgent = String(agentId).trim().toLowerCase();
    const targetMessageId = String(messageId);
    const buckets = (this.state && typeof this.state === 'object') ? this.state.messages : null;
    if (!buckets || typeof buckets !== 'object') return false;
    return Object.keys(buckets || {}).some((bucketKey) => {
      const bucket = Array.isArray(buckets[bucketKey]) ? buckets[bucketKey] : [];
      return bucket.some((entry) => {
        if (!entry || typeof entry !== 'object') return false;
        const meta = (entry.meta && typeof entry.meta === 'object') ? entry.meta : {};
        const opinion = (meta.opinion && typeof meta.opinion === 'object') ? meta.opinion : null;
        const opinionRequest = (meta.opinion_request && typeof meta.opinion_request === 'object') ? meta.opinion_request : null;
        if (opinion) {
          const reviewer = String(opinion.reviewer_agent_id ?? opinion.agent_id ?? entry.agent_id ?? '').trim().toLowerCase();
          if (reviewer && reviewer !== targetAgent) return false;
          const candidates = [
            opinion.of_message_id,
            opinion.message_id,
            opinion.target_message_id,
            opinion.about_message_id,
            opinion.request_note_id,
            opinion.request_id,
          ];
          return candidates.some((value) => value != null && String(value) === targetMessageId);
        }
        if (opinionRequest) {
          const candidates = [opinionRequest.requested_message_id, opinionRequest.of_message_id, opinionRequest.request_id];
          const reviewer = String(entry.agent_id || entry.agent || '').trim().toLowerCase();
          if (reviewer && reviewer !== targetAgent) return false;
          return candidates.some((value) => value != null && String(value) === targetMessageId);
        }
        return false;
      });
    });
  } catch (error) {
    console.warn('[ChatUI] _hasOpinionFromAgent failed', error);
    return false;
  }
}


  _opinionButtonsHTML(message, encodedRaw) {
    if (!message || typeof message !== 'object') return '';
    const role = String(message.role || '').toLowerCase();
    if (role && role !== 'assistant') return '';
    if (message.isStreaming) return '';
    const messageId = message.id ? String(message.id).trim() : '';
    if (!messageId) return '';
    const sourceAgentId = String(message.agent_id || message.agent || '').trim().toLowerCase();
    if (!sourceAgentId) return '';
    const candidates = Object.keys(AGENTS).filter((id) => id && id !== 'global' && id !== sourceAgentId);
    if (!candidates.length) return '';
    const parts = [];
    for (const targetId of candidates) {
      const info = AGENTS[targetId] || {};
      const disabled = this._hasOpinionFromAgent(targetId, messageId);
      const color = this._escapeHTML(info.color || '#94a3b8');
      const label = this._escapeHTML(info.label || info.name || this._humanizeAgentId(targetId) || targetId);
      const targetAttr = this._escapeHTML(targetId);
      const sourceAttr = this._escapeHTML(sourceAgentId);
      const messageAttr = this._escapeHTML(messageId);
      const disabledAttr = disabled ? ' disabled aria-disabled="true"' : '';
      parts.push('<button type="button" class="opinion-request-btn agent--' + targetAttr + '" data-role="ask-opinion" data-target-agent="' + targetAttr + '" data-source-agent="' + sourceAttr + '" data-message-id="' + messageAttr + '" data-message="' + encodedRaw + '" title="Demander l\'avis de ' + label + '" style="--agent-color: ' + color + ';"' + disabledAttr + '>' + '<span class="sr-only">Demander l\'avis de ' + label + '</span>' + '</button>');
    }
    if (!parts.length) return '';
    return '<div class="opinion-actions" role="group" aria-label="Demander un avis">' + parts.join('') + '</div>';
  }

  _opinionBadgeHTML(opinion) {
    if (!opinion || typeof opinion !== 'object') return '';
    const sourceAgentId = String(opinion.source_agent_id ?? opinion.source_agent ?? opinion.agent ?? '').trim().toLowerCase();
    if (sourceAgentId) {
      const label = this._escapeHTML(this._getAgentLabel(sourceAgentId));
      return '<span class="message-badge message-badge--opinion">Avis sur ' + label + '</span>';
    }
    return '<span class="message-badge message-badge--opinion">Avis</span>';
  }


  _messageHTML(m) {
    const side = m.role === 'user' ? 'user' : 'assistant';
    const agentId = side === 'assistant' ? (m.agent_id || m.agent || 'nexus') : '';
    const agentInfo = side === 'assistant' ? (AGENTS[agentId] || {}) : {};
    const displayName = side === 'user'
      ? 'FG'
      : (agentInfo.label || agentInfo.name || this._humanizeAgentId(agentId) || 'Assistant');

    const raw = this._toPlainText(m.content);
    const content = this._escapeHTML(raw).replace(/\n/g, '<br/>');
    const cursor = m.isStreaming ? '<span class="blinking-cursor">|</span>' : '';
    const timestamp = this._formatTimestamp(m.created_at ?? m.timestamp ?? m.time ?? m.datetime ?? m.date);

    const classes = ['message', side, `message--${side}`];
    if (side === 'assistant') {
      if (agentId) {
        classes.push(agentId);
        classes.push(`message--${agentId}`);
      }
      if (agentInfo.cssClass) classes.push(agentInfo.cssClass);
    }

    const className = classes
      .filter(Boolean)
      .filter((value, index, arr) => arr.indexOf(value) === index)
      .join(' ');

    const encodedRaw = this._encodeForAttribute(raw);
    const copyDisabled = !!m.isStreaming;
    const copyLabel = 'Copier le message';
    const copyTitle = copyDisabled ? 'Message en cours' : copyLabel;
    const srCopyText = copyDisabled ? 'Copie indisponible pendant la generation' : copyLabel;
    const copyClass = `message-action message-action-copy${copyDisabled ? ' is-disabled' : ''}`;
    const meta = (m.meta && typeof m.meta === 'object') ? m.meta : {};
    const opinion = (meta && typeof meta.opinion === 'object') ? meta.opinion : null;
    if (opinion) {
      classes.push('message--opinion');
      const opinionSource = String(opinion.source_agent_id ?? opinion.source_agent ?? opinion.agent ?? '').trim().toLowerCase();
      if (opinionSource) classes.push(`message--opinion-${opinionSource}`);
    }
    const opinionBadgeHTML = opinion ? this._opinionBadgeHTML(opinion) : '';
    const opinionButtonsHTML = (side === 'assistant') ? this._opinionButtonsHTML(m, encodedRaw) : '';

    return `
      <div class="${className}" data-message-id="${this._escapeHTML(m.id || '')}">
        <div class="message-bubble">
          <div class="message-header">
            <div class="message-meta">
              <div class="message-meta__title">
                <span class="sender-name">${this._escapeHTML(displayName)}</span>
                ${opinionButtonsHTML}
              </div>
              ${opinionBadgeHTML}
              <time class="message-time" datetime="${timestamp.iso}">${this._escapeHTML(timestamp.display)}</time>
            </div>
            <div class="message-actions">
              <button
                type="button"
                class="${copyClass}"
                data-role="copy-message"
                data-message="${encodedRaw}"
                data-label="${copyLabel}"
                data-title="${copyTitle}"
                title="${copyTitle}"
                aria-label="${copyTitle}"${copyDisabled ? ' disabled aria-disabled="true"' : ''}
              >
                <span class="sr-only">${srCopyText}</span>
                <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true" focusable="false">
                  <path d="M9 9V5a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-4" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"></path>
                  <rect x="3" y="9" width="12" height="12" rx="2" ry="2" fill="none" stroke="currentColor" stroke-width="1.5"></rect>
                </svg>
              </button>
            </div>
          </div>
          <div class="message-text" data-raw="${encodedRaw}">${content}${cursor}</div>
        </div>
      </div>`;
  }
  _agentTabsHTML(activeId) {
    const baseIds = Object.keys(AGENTS);
    const seen = new Set(baseIds);
    if (this.state && this.state.messages && typeof this.state.messages === 'object') {
      Object.keys(this.state.messages).forEach((id) => {
        if (!id) return;
        seen.add(String(id).trim().toLowerCase());
      });
    }
    if (this.state && this.state.currentAgentId) {
      seen.add(String(this.state.currentAgentId).trim().toLowerCase());
    }
    const ids = baseIds.concat(Array.from(seen).filter((id) => !baseIds.includes(id)));
    return `
      <div class="tabs-container">
        ${ids.map((id) => {
          const agent = AGENTS[id] || {};
          const isActive = id === activeId;
          const icon = agent.icon ? `<span class="tab-icon" aria-hidden="true">${this._escapeHTML(agent.icon)}</span>` : '';
          const label = agent.label || agent.name || this._humanizeAgentId(id) || id;
          return `
            <button
              type="button"
              class="button-tab agent--${id} ${isActive ? 'active' : ''}"
              data-agent-id="${id}"
              aria-pressed="${isActive}"
            >
              ${icon}
              <span class="tab-label">${this._escapeHTML(label)}</span>
            </button>
          `;
        }).join('')}
      </div>`;
  }

  _setActiveAgentTab(container, agentId) {
    container.querySelectorAll('.button-tab').forEach((b) => b.classList.remove('active'));
    container.querySelector(`.button-tab[data-agent-id="${agentId}"]`)?.classList.add('active');
  }

  _asArray(x) {
    return Array.isArray(x) ? x : (x ? [x] : []);
  }

  _normalizeMessage(m) {
    if (!m) return { role: 'assistant', content: '' };
    if (typeof m === 'string') return { role: 'assistant', content: m };
    const timestamp =
      m.created_at ?? m.timestamp ?? m.time ?? m.datetime ?? m.date ?? m.createdAt ?? (m.meta && m.meta.timestamp) ?? null;
    return {
      role: m.role || 'assistant',
      content: m.content ?? m.text ?? '',
      isStreaming: !!m.isStreaming,
      agent_id: m.agent_id || m.agent,
      id: m.id ?? null,
      created_at: timestamp,
      timestamp
    };
  }

  _toPlainText(val) {
    if (val == null) return '';
    if (typeof val === 'string') return val;
    if (Array.isArray(val)) return val.map((v) => this._toPlainText(v)).join('');
    if (typeof val === 'object') {
      if ('text' in val) return this._toPlainText(val.text);
      if ('content' in val) return this._toPlainText(val.content);
      if ('message' in val) return this._toPlainText(val.message);
      try { return JSON.stringify(val); } catch { return String(val); }
    }
    return String(val);
  }

  _encodeForAttribute(value) {
    const safe = this._escapeHTML(String(value ?? ''));
    return safe.replace(/\r?\n/g, '&#10;');
  }

  _decodeHTML(value) {
    if (value == null) return '';
    if (!this._decoderEl) {
      this._decoderEl = document.createElement('textarea');
    }
    this._decoderEl.innerHTML = value;
    return this._decoderEl.value;
  }

  /**
   * Génère et joue automatiquement le TTS pour un message d'agent.
   * Auto-play silencieux (pas de player visible).
   * @param {string} text - Le texte du message à synthétiser
   * @param {string} agentId - L'ID de l'agent (pour voice mapping)
   */
  async _playTTS(text, agentId = null) {
    if (!text || !text.trim()) {
      console.warn('[ChatUI] Pas de texte à synthétiser');
      return;
    }

    if (!this.state.ttsEnabled) {
      console.log('[ChatUI] TTS désactivé, skip');
      return;
    }

    console.log(`[ChatUI] TTS auto-play pour agent "${agentId}"`);

    try {
      // Appel API TTS avec agent_id pour voice mapping
      const { getIdToken } = await import('../../core/auth.js');
      const token = getIdToken();
      const response = await fetch('/api/voice/tts', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': token ? `Bearer ${token}` : ''
        },
        body: JSON.stringify({
          text: text.trim(),
          agent_id: agentId
        })
      });

      if (!response.ok) {
        throw new Error(`TTS API error: ${response.status}`);
      }

      // Lire l'audio stream
      const blob = await response.blob();
      const audioUrl = URL.createObjectURL(blob);

      // Créer audio element invisible (pas de controls)
      const audio = new Audio(audioUrl);

      // Cleanup URL après lecture
      audio.addEventListener('ended', () => {
        URL.revokeObjectURL(audioUrl);
      });

      // Cleanup URL en cas d'erreur
      audio.addEventListener('error', () => {
        URL.revokeObjectURL(audioUrl);
      });

      // Auto-play (silencieux, en arrière-plan)
      await audio.play();
      console.log('[ChatUI] TTS lecture démaré (auto-play)');

    } catch (error) {
      console.error('[ChatUI] TTS auto-play failed:', error);
    }
  }

  async _copyToClipboard(text) {
    try {
      if (navigator?.clipboard?.writeText) {
        await navigator.clipboard.writeText(text);
      } else {
        const area = document.createElement('textarea');
        area.value = text;
        area.setAttribute('readonly', '');
        area.style.position = 'fixed';
        area.style.top = '-1000px';
        area.style.opacity = '0';
        document.body.appendChild(area);
        area.focus();
        area.select();
        const ok = document.execCommand('copy');
        area.remove();
        if (!ok) throw new Error('execCommand returned false');
      }
      return true;
    } catch (error) {
      console.error('[ChatUI] copy failed', error);
      return false;
    }
  }

  _flashCopyState(button, success) {
    if (!button) return;
    const baseLabel = button.getAttribute('data-label') || 'Copier le message';
    const baseTitle = button.getAttribute('data-title') || baseLabel;
    if (button._copyTimer) {
      clearTimeout(button._copyTimer);
      button._copyTimer = null;
    }
    if (success) {
      button.classList.add('is-copied');
      button.classList.remove('is-error');
      button.setAttribute('data-copied', 'true');
      button.removeAttribute('data-copy-error');
      button.setAttribute('aria-label', 'Message copie');
      button.title = 'Message copie';
    } else {
      button.classList.remove('is-copied');
      button.classList.add('is-error');
      button.setAttribute('data-copy-error', 'true');
      button.removeAttribute('data-copied');
      button.setAttribute('aria-label', 'Copie impossible');
      button.title = 'Copie impossible';
    }
    button._copyTimer = setTimeout(() => {
      try {
        button.classList.remove('is-copied', 'is-error');
        button.removeAttribute('data-copied');
        button.removeAttribute('data-copy-error');
        button.setAttribute('aria-label', baseLabel);
        button.title = baseTitle;
        button._copyTimer = null;
      } catch {}
    }, 1500);
  }

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

  _humanizeAgentId(id) {
    if (!id) return '';
    const base = String(id).replace(/[_-]+/g, ' ').trim();
    if (!base) return '';
    return base
      .split(/\s+/)
      .filter(Boolean)
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase())
      .join(' ');
  }

  _coerceDate(input) {
    if (!input) return null;
    if (input instanceof Date && !Number.isNaN(input.getTime())) return input;
    if (typeof input === 'string') {
      const trimmed = input.trim();
      if (!trimmed) return null;
      const parsed = Date.parse(trimmed);
      if (!Number.isNaN(parsed)) {
        const d = new Date(parsed);
        if (!Number.isNaN(d.getTime())) return d;
      }
    }
    const num = Number(input);
    if (!Number.isFinite(num)) return null;
    const ms = num > 1e12 ? num : (num > 1e9 ? num * 1000 : num);
    if (!Number.isFinite(ms)) return null;
    const d = new Date(ms);
    return Number.isNaN(d.getTime()) ? null : d;
  }

  _formatTimestamp(input) {
    const date = this._coerceDate(input) || new Date();
    const datePart = date.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric' });
    const timePart = date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
    return { display: `${datePart} - ${timePart}`, iso: date.toISOString() };
  }
}
