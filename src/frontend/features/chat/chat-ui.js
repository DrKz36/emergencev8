/**
 * src/frontend/features/chat/chat-ui.js
 * V22 — Rendu robuste (content string|array|object), update(), sélecteur d’agent, sync RAG
 */
import { EVENTS, AGENTS } from '../../shared/constants.js';

export class ChatUI {
  constructor(eventBus, stateManager) {
    this.eventBus = eventBus;
    this.stateManager = stateManager;
    this.state = {
      isLoading: false,
      currentAgentId: 'anima',
      ragEnabled: false,
      messages: {} // { [agentId]: Message[] }
    };
    console.log('✅ ChatUI V22 prêt.');
  }

  render(container, chatState = {}) {
    if (!container) return;
    this.state = { ...this.state, ...chatState };

    const agentTabs = this._agentTabsHTML(this.state.currentAgentId);

    container.innerHTML = `
      <div class="chat-container card">
        <div class="chat-header card-header">
          <div class="chat-title">Dialogue</div>
          <div class="agent-selector">${agentTabs}</div>
        </div>

        <div class="chat-messages card-body" id="chat-messages"></div>

        <div class="chat-input-area card-footer">
          <form id="chat-form" class="chat-form" autocomplete="off">
            <textarea id="chat-input" class="chat-input" rows="1" placeholder="Écrivez votre message..."></textarea>
            <button type="submit" id="chat-send" class="chat-send-button" title="Envoyer">➤</button>
          </form>

          <div class="chat-actions">
            <button
              type="button"
              id="chat-rag-toggle"
              class="toggle toggle-metal action-rag-toggle"
              role="switch"
              aria-checked="${String(!!this.state.ragEnabled)}"
              title="Activer/Désactiver RAG">
              <span class="toggle-track"><span class="toggle-thumb"></span></span>
              <span class="toggle-label">RAG</span>
            </button>

            <button type="button" id="chat-export" class="button">Exporter</button>
            <button type="button" id="chat-clear" class="button">Effacer</button>
          </div>
        </div>
      </div>
    `;

    this._bindEvents(container);
    this.update(container, this.state);
  }

  /**
   * Mise à jour incrémentale (appelée par le module après chaque set())
   */
  update(container, chatState = {}) {
    if (!container) return;
    this.state = { ...this.state, ...chatState };

    // Sync RAG
    container.querySelector('#chat-rag-toggle')
      ?.setAttribute('aria-checked', String(!!this.state.ragEnabled));

    // Sync onglets agents
    this._setActiveAgentTab(container, this.state.currentAgentId);

    // Messages de l'agent courant (robuste à tout format)
    const raw = this.state.messages?.[this.state.currentAgentId];
    const list = this._asArray(raw).map((m) => this._normalizeMessage(m));
    this._renderMessages(container.querySelector('#chat-messages'), list);
  }

  /* ─────────────────── private ─────────────────── */

  _bindEvents(container) {
    const form = container.querySelector('#chat-form');
    const input = container.querySelector('#chat-input');
    const ragBtn = container.querySelector('#chat-rag-toggle');

    // Envoi message
    form?.addEventListener('submit', (e) => {
      e.preventDefault();
      const text = (input?.value || '').trim();
      if (!text) return;
      // Envoi objet (le module accepte string|objet)
      this.eventBus.emit(EVENTS.CHAT_SEND, { text, agent: 'user' });
      input.value = '';
      input.dispatchEvent(new Event('input'));
    });

    // Export
    container.querySelector('#chat-export')
      ?.addEventListener('click', () => this.eventBus.emit(EVENTS.CHAT_EXPORT, null));

    // Clear
    container.querySelector('#chat-clear')
      ?.addEventListener('click', () => this.eventBus.emit(EVENTS.CHAT_CLEAR, null));

    // RAG toggle
    ragBtn?.addEventListener('click', () => {
      const on = ragBtn.getAttribute('aria-checked') === 'true';
      ragBtn.setAttribute('aria-checked', String(!on));
      this.eventBus.emit(EVENTS.CHAT_RAG_TOGGLED, { enabled: !on });
    });

    // Sélecteur d’agent
    container.querySelector('.agent-selector')?.addEventListener('click', (e) => {
      const btn = e.target.closest('button[data-agent-id]');
      if (!btn) return;
      const agentId = btn.getAttribute('data-agent-id');
      this.eventBus.emit(EVENTS.CHAT_AGENT_SELECTED, agentId);
      this._setActiveAgentTab(container, agentId);
    });
  }

  _renderMessages(host, messages) {
    if (!host) return;
    const html = (messages || []).map(m => this._messageHTML(m)).join('');
    host.innerHTML = html || `<div class="placeholder" style="opacity:.6;padding:1rem;">Commence à discuter…</div>`;
    host.scrollTo(0, 1e9);
  }

  _messageHTML(m) {
    const side = m.role === 'user' ? 'user' : 'assistant';
    const agentId = m.agent_id || m.agent || 'nexus';
    const you = this.stateManager?.get?.('user.name') || 'Vous';
    const name = side === 'user' ? you : (AGENTS[agentId]?.name || 'Agent');
    const raw = this._toPlainText(m.content);
    const content = this._escapeHTML(raw).replace(/\n/g, '<br/>');
    const cursor = m.isStreaming ? `<span class="blinking-cursor">▍</span>` : '';

    return `
      <div class="message ${side} ${side === 'assistant' ? agentId : ''}">
        <div class="message-content">
          <div class="message-meta meta-inside"><strong class="sender-name">${name}</strong></div>
          <div class="message-text">${content}${cursor}</div>
        </div>
      </div>`;
  }

  _agentTabsHTML(activeId) {
    const ids = Object.keys(AGENTS).filter(id => id !== 'nexus');
    return `
      <div class="segmented" id="chat-agent-tabs">
        ${ids.map(id => `
          <button
            type="button"
            class="button-tab ${id===activeId ? 'active' : ''} agent--${id}"
            data-agent-id="${id}">
            <span class="tab-label">${AGENTS[id]?.name || id}</span>
          </button>
        `).join('')}
      </div>`;
  }

  _setActiveAgentTab(container, activeId) {
    container.querySelectorAll('.agent-selector .button-tab')
      ?.forEach(b => b.classList.toggle('active', b.getAttribute('data-agent-id') === activeId));
  }

  /* ─── helpers robustes ─── */

  _asArray(v) {
    if (Array.isArray(v)) return v;
    if (!v) return [];
    if (typeof v === 'object') return Object.values(v);
    return [];
  }

  _normalizeMessage(m) {
    if (m == null) return { role: 'assistant', content: '' };
    if (typeof m === 'string') return { role: 'assistant', content: m };
    const role = m.role || (m.author === 'user' ? 'user' : 'assistant');
    const content = m.content ?? m.text ?? m.message ?? '';
    const agent_id = m.agent_id || m.agent || m.agentId;
    return { ...m, role, content, agent_id };
  }

  _toPlainText(val) {
    if (val == null) return '';
    if (typeof val === 'string') return val;
    if (Array.isArray(val)) return val.map(v => this._toPlainText(v)).join('');
    if (typeof val === 'object') {
      if ('text' in val) return this._toPlainText(val.text);
      if ('content' in val) return this._toPlainText(val.content);
      if ('message' in val) return this._toPlainText(val.message);
      try { return JSON.stringify(val); } catch { return String(val); }
    }
    return String(val);
  }

  _escapeHTML(s) {
    return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  }
}
