/**
 * src/frontend/features/debate/debate-ui.js
 * V41 — Titre + sujet centrés, actions bas, RAG chat-like, auto‑médiateur Neo→Nexus→Anima
 */
import { EVENTS, AGENTS } from '../../shared/constants.js';
import { marked } from 'https://cdn.jsdelivr.net/npm/marked/lib/marked.esm.js';

export class DebateUI {
  constructor(eventBus) {
    this.eventBus = eventBus;
    this._touched = { attacker:false, challenger:false, mediator:false, rounds:false };
    console.log('✅ DebateUI V41 prêt.');
  }

  render(container, debateState) {
    if (!container) return;

    const hasHistory = Array.isArray(debateState?.history) && debateState.history.length > 0;
    const isActive   = !!debateState?.isActive;
    const statusText = debateState?.statusText ?? 'Prêt à commencer.';

    if (!hasHistory && !isActive) {
      container.innerHTML = this._renderCreateView(statusText);
      this._bindCreateEvents(container);
      return;
    }

    container.innerHTML = this._renderTimelineView(debateState);
    this._bindTimelineEvents(container, debateState);
  }

  /* ---------------------------- Vue Création ---------------------------- */

  _renderCreateView(statusText) {
    const defaultAttacker   = this._defaultFor('attacker');
    const defaultChallenger = this._defaultFor('challenger');
    const defaultMediator   = this._autoFrom(defaultAttacker, defaultChallenger);

    const segAttacker   = this._segAgents('attacker',   defaultAttacker);
    const segChallenger = this._segAgents('challenger', defaultChallenger);
    const segMediator   = this._segAgents('mediator',   defaultMediator);
    const roundsTabs    = this._segRounds(3);

    return `
      <div class="debate-view-wrapper">
        <div class="card">

          <!-- Header centré -->
          <div class="card-header timeline-header">
            <div class="title-center">
              <div class="debate-title">Sujet du Débat</div>
              <div class="debate-topic muted">—</div>
            </div>
            <div class="debate-status">${this._html(statusText)}</div>
          </div>

          <div class="card-body">
            <div class="debate-create-body">
              <div class="form-group form-topic">
                <label for="debate-topic">Sujet du Débat</label>
                <textarea id="debate-topic" class="input-text" rows="4"
                  placeholder="Ex: L’IA peut-elle développer une conscience authentique ?"></textarea>
              </div>

              <div class="form-group form-attacker">
                <label>Attaquant</label>
                ${segAttacker}
              </div>

              <div class="form-group form-challenger">
                <label>Challenger</label>
                ${segChallenger}
              </div>

              <div class="form-group form-rounds">
                <label>Nombre de tours</label>
                ${roundsTabs}
              </div>

              <div class="form-group form-mediator">
                <label>Médiateur</label>
                ${segMediator}
              </div>
            </div>
          </div>

          <div class="card-footer debate-create-footer">
            <div class="rag-control">
              <button
                type="button"
                id="rag-power"
                class="rag-power"
                role="switch"
                aria-checked="true"
                title="Activer/Désactiver RAG">
                <svg class="power-icon" viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
                  <path d="M12 3v9" stroke="currentColor" stroke-width="2" stroke-linecap="round" fill="none"/>
                  <path d="M5.5 7a8 8 0 1 0 13 0" stroke="currentColor" stroke-width="2" stroke-linecap="round" fill="none"/>
                </svg>
              </button>
              <span id="rag-label" class="rag-label">RAG</span>
            </div>

            <div class="action-center">
              <button class="btn btn-primary button button-primary" id="debate-start">
                Lancer le débat
              </button>
            </div>
          </div>
        </div>
      </div>`;
  }

  _bindCreateEvents(root) {
    // Reflect topic in header
    const topicEl = root.querySelector('#debate-topic');
    const headerTopic = root.querySelector('.debate-topic');
    const syncTopic = () => { headerTopic.textContent = topicEl.value.trim() || '—'; };
    topicEl?.addEventListener('input', syncTopic);

    // Toggle RAG (chat‑like)
    const ragBtn = root.querySelector('#rag-power');
    const ragLbl = root.querySelector('#rag-label');
    const toggleRag = () => {
      const on = ragBtn.getAttribute('aria-checked') === 'true';
      ragBtn.setAttribute('aria-checked', String(!on));
    };
    ragBtn?.addEventListener('click', toggleRag);
    ragLbl?.addEventListener('click', toggleRag);

    // Pills (agents + rounds)
    root.addEventListener('click', (ev) => {
      const btn = ev.target.closest('.button-tab');
      if (!btn) return;
      const seg = btn.closest('[data-seg]');
      if (!seg) return;

      seg.querySelectorAll('.button-tab').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      const segName = seg.getAttribute('data-seg');
      if (segName === 'attacker')   this._touched.attacker = true;
      if (segName === 'challenger') this._touched.challenger = true;
      if (segName === 'mediator')   this._touched.mediator = true;
      if (segName === 'rounds')     this._touched.rounds = true;

      if ((segName === 'attacker' || segName === 'challenger') && !this._touched.mediator) {
        this._autoSelectMediator(root);
      }
    });

    // Lancer
    root.querySelector('#debate-start')?.addEventListener('click', () => {
      const topic = root.querySelector('#debate-topic')?.value?.trim() ?? '';
      const attacker   = this._getSegValue(root, 'attacker');
      const challenger = this._getSegValue(root, 'challenger');
      let   mediator   = this._getSegValue(root, 'mediator');
      const rounds     = parseInt(this._getSegValue(root, 'rounds') || '3', 10) || 3;
      const useRag     = (root.querySelector('#rag-power')?.getAttribute('aria-checked') === 'true');

      if (!topic) { alert('Merci de renseigner un sujet de débat.'); return; }
      if (!attacker || !challenger) { alert('Merci de sélectionner Attaquant/Challenger.'); return; }

      // Règle demandée : Neo (A) + Nexus (C) => Médiateur forcé Anima
      if (attacker === 'neo' && challenger === 'nexus') mediator = 'anima';

      if (!mediator) { alert('Merci de sélectionner le Médiateur.'); return; }

      this.eventBus.emit('debate:create', {
        topic,
        rounds,
        agentOrder: [attacker, challenger, mediator],
        useRag
      });
    });
  }

  /* ---------------------------- Vue Timeline (flux continu) ---------------------------- */

  _renderTimelineView(state) {
    const header = `
      <div class="card-header timeline-header">
        <div class="title-center">
          <div class="debate-title">Sujet du Débat</div>
          <div class="debate-topic muted">${this._html(state?.config?.topic || state?.topic || '—')}</div>
        </div>
        <div class="debate-status">${this._html(state?.statusText ?? '')}</div>
      </div>`;

    const turns = (state?.history ?? []).map((turn, idx) => {
      const order = Array.isArray(state?.config?.agentOrder) && state.config.agentOrder.length
        ? state.config.agentOrder
        : Object.keys(turn.agentResponses || {});

      const bubbles = order.map((agentId) => {
        const txt = turn.agentResponses?.[agentId];
        if (txt == null) return '';
        const name = AGENTS?.[agentId]?.name || agentId;
        return `
          <div class="message assistant ${agentId}">
            <div class="message-content">
              <div class="message-meta meta-inside"><strong class="sender-name">${this._html(name)}</strong></div>
              <div class="message-text">${marked.parse(txt || '')}</div>
            </div>
          </div>`;
      }).join('');

      return `
        <section class="debate-turn">
          <div class="turn-title">Tour ${Number(turn.roundNumber) || (idx + 1)}</div>
          <div class="chat-messages">${bubbles}</div>
        </section>`;
    }).join('');

    // Synthèse
    const synthesizerId = Array.isArray(state?.config?.agentOrder)
      ? state.config.agentOrder[state.config.agentOrder.length - 1]
      : 'nexus';
    const synthesizerName = AGENTS?.[synthesizerId]?.name || 'Nexus';

    const synthesis = (state?.status === 'completed' && state?.synthesis)
      ? `
        <section class="debate-synthesis">
          <div class="synthesis-title">Synthèse — ${this._html(synthesizerName)}</div>
          <div class="chat-messages">
            <div class="message assistant ${this._html(synthesizerId)}">
              <div class="message-content">
                <div class="message-meta meta-inside">
                  <strong class="sender-name">${this._html(synthesizerName)}</strong>
                </div>
                <div class="message-text"><em>${marked.parse(state.synthesis)}</em></div>
              </div>
            </div>
          </div>
        </section>` : '';

    const footer = `
      <div class="card-footer">
        <div class="debate-actions">
          <button id="debate-export" class="button button-metal" title="Exporter en Markdown">Exporter</button>
          <button id="debate-new" class="button button-primary" title="Lancer un nouveau débat">Nouveau débat</button>
        </div>
      </div>`;

    return `
      <div class="debate-view-wrapper">
        <div class="card">
          ${header}
          <div class="card-body">
            <div class="debate-flow">
              ${turns}
              ${synthesis}
            </div>
          </div>
          ${footer}
        </div>
      </div>`;
  }

  _bindTimelineEvents(root, state) {
    root.querySelector('#debate-export')
      ?.addEventListener('click', () => this.eventBus.emit('debate:export', state));
    root.querySelector('#debate-new')
      ?.addEventListener('click', () => this.eventBus.emit('debate:reset'));
  }

  /* ---------------------------- Helpers ---------------------------- */

  _defaultFor(role) {
    const keys = Object.keys(AGENTS || {});
    const has  = (k) => keys.includes(k);
    if (role === 'attacker')   return has('anima') ? 'anima' : (keys[0] || '');
    if (role === 'challenger') return has('neo')   ? 'neo'   : (keys[1] || keys[0] || '');
    if (role === 'mediator')   return has('nexus') ? 'nexus' : (keys[2] || keys[0] || '');
    return keys[0] || '';
  }

  _segAgents(role, def) {
    const entries = Object.entries(AGENTS || {});
    const d = def || (entries[0]?.[0] ?? '');
    const buttons = entries.map(([id, meta]) => {
      const active = id === d ? 'active' : '';
      const name = meta?.name || id;
      return `<button type="button" class="button-tab ${active}" data-value="${this._html(id)}">${this._html(name)}</button>`;
    }).join('');
    return `<div class="tabs-container" data-seg="${this._html(role)}">${buttons}</div>`;
  }

  _segRounds(d=3){ return `<div class="tabs-container rounds-tabs" data-seg="rounds">
    ${[1,2,3,4,5].map(v => `<button type="button" class="button-tab ${v===d?'active':''}" data-value="${v}">${v}</button>`).join('')}
  </div>`; }

  _autoFrom(a,c){ const tri=['anima','neo','nexus']; const s=new Set([a,c]); return tri.find(x=>!s.has(x))||tri[0]; }

  _getSegValue(root, seg){ return root.querySelector(`[data-seg="${seg}"] .button-tab.active`)?.getAttribute('data-value') || ''; }

  _html(s){ return String(s ?? '').replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m])); }
}
