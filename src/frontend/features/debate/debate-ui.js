/**
 * src/frontend/features/debate/debate-ui.js
 * V36.7 — Unification police auteurs (data-role="author") + garde-fou émission
 */
import { EVENTS, AGENTS } from '../../shared/constants.js';
import { marked } from 'https://cdn.jsdelivr.net/npm/marked/lib/marked.esm.js';
import { loadCSS } from '../../core/utils.js';

export class DebateUI {
  constructor(eventBus) {
    this.eventBus = eventBus;
    this.localState = {};
    try { loadCSS('../features/debate/debate.css'); } catch (_) {}
    console.log('✅ DebateUI V36.7 prêt (CSS chargée).');
  }

  render(container, debateState) {
    if (!container) return;
    const showHistory = Array.isArray(debateState?.history) && debateState.history.length > 0;
    if (showHistory || debateState?.status) return this.renderDebateView(container, debateState);
    return this.renderCreationView(container);
  }

  /* ───────────── Vue Création ───────────── */
  renderCreationView(container) {
    const defaultState = { topic:'', attacker:'anima', challenger:'neo', rounds:2, use_rag:false };
    const agentOptions = Object.values(AGENTS).map(a => ({ value:a.id, label:a.name }));

    container.innerHTML = `
      <div class="debate-view-wrapper">
        <div class="card">
          <div class="card-header">
            <h2 class="card-title">Nouveau Débat Autonome</h2>
            <p class="card-subtitle">Configurez les participants et le sujet du débat.</p>
          </div>

          <div class="card-body debate-create-body">
            <!-- Sujet -->
            <div class="form-group form-topic">
              <label for="debate-topic">Sujet du Débat</label>
              <textarea id="debate-topic" class="input-text" rows="3"
                placeholder="Ex: L'IA peut-elle développer une conscience authentique ?"></textarea>
            </div>

            <!-- Cadre CONFIGURATION (2×2) -->
            <div class="config-grid">
              <div class="form-group form-attacker">
                <label>Attaquant</label>
                ${this._seg('attacker-selector', agentOptions, defaultState.attacker, true)}
              </div>

              <div class="form-group form-challenger">
                <label>Challenger</label>
                ${this._seg('challenger-selector', agentOptions, defaultState.challenger, true)}
              </div>

              <div class="form-group form-rounds">
                <label>Nombre de Rounds</label>
                ${this._seg('rounds-selector', [
                    {value:1,label:'1 round'},
                    {value:2,label:'2 rounds'},
                    {value:3,label:'3 rounds'}
                  ], defaultState.rounds, false)}
              </div>

              <div class="form-group form-mediator">
                <label>Synthèse par</label>
                <span id="mediator-info" class="mediator-display agent--nexus">Nexus</span>
              </div>
            </div>

            <!-- RAG (optionnel) -->
            <div class="rag-row">
              <span class="rag-label">RAG</span>
              <button
                id="debate-rag-power"
                class="rag-power"
                role="switch"
                aria-checked="false"
                title="RAG désactivé">
                <svg viewBox="0 0 24 24" class="icon-power" aria-hidden="true" focusable="false">
                  <path class="power-line" d="M12 3 v7" />
                  <path class="power-circle" d="M6.5 7.5a7 7 0 1 0 11 0" />
                </svg>
              </button>
            </div>
          </div>

          <!-- CTA -->
          <div class="card-footer debate-create-footer">
            <button id="create-debate-btn" class="button button-primary button-xxl">Lancer le Débat</button>
          </div>
        </div>
      </div>
    `;

    this.localState = { ...defaultState };
    this._bindCreationEvents(container);
    this._updateAgentSelection(container); // initialise médiateur affiché
  }

  _bindCreationEvents(container) {
    const topicEl = container.querySelector('#debate-topic');
    const ragBtn = container.querySelector('#debate-rag-power');

    this._bindSegClicks(container.querySelector('#attacker-selector'), v => {
      this.localState.attacker = v;
      this._updateAgentSelection(container);
    });
    this._bindSegClicks(container.querySelector('#challenger-selector'), v => {
      this.localState.challenger = v;
      this._updateAgentSelection(container);
    });
    this._bindSegClicks(container.querySelector('#rounds-selector'), v => {
      this.localState.rounds = Number(v);
    });

    topicEl?.addEventListener('input', (e) => { this.localState.topic = e.target.value || ''; });

    ragBtn?.addEventListener('click', () => {
      const on = ragBtn.getAttribute('aria-checked') === 'true';
      const next = !on;
      ragBtn.setAttribute('aria-checked', String(next));
      ragBtn.setAttribute('title', next ? 'RAG activé' : 'RAG désactivé');
      this.localState.use_rag = next;
      this.eventBus.emit(EVENTS.CHAT_RAG_TOGGLED, { enabled: next });
    });

    container.querySelector('#create-debate-btn')?.addEventListener('click', () => {
      const topic = (topicEl?.value || '').trim();
      if (topic.length < 10) {
        this.eventBus.emit(EVENTS.SHOW_NOTIFICATION, { type:'warning', message:'Le sujet du débat est trop court.' });
        return;
      }
      const mediatorId = this._computeMediatorId();
      const config = {
        topic,
        rounds: this.localState.rounds,
        agent_order: [this.localState.attacker, this.localState.challenger, mediatorId],
        use_rag: this.localState.use_rag
      };

      // IMPORTANT: émettre UNE SEULE FOIS
      this.eventBus.emit('debate:create', config);
    });
  }

  _seg(id, options, selected, colorByAgent=false) {
    return `
      <div id="${id}" class="segmented">
        ${options.map(opt => `
          <button class="button-tab ${colorByAgent ? `agent--${opt.value}` : ''} ${opt.value===selected ? 'active' : ''}" data-value="${opt.value}">
            <span class="tab-label">${opt.label}</span>
          </button>`).join('')}
      </div>`;
  }

  _bindSegClicks(container, onChange){
    if(!container) return;
    container.addEventListener('click', (e) => {
      const btn = e.target.closest('button[data-value]'); if (!btn) return;
      container.querySelectorAll('button').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      onChange?.(btn.dataset.value);
    });
  }

  _updateAgentSelection(container) {
    // Si A == C, choisir automatiquement un challenger différent d'A (Nexus autorisé).
    if (this.localState.attacker === this.localState.challenger) {
      const next = Object.keys(AGENTS).find(k => k !== this.localState.attacker) || this.localState.challenger;
      this.localState.challenger = next;
      this._setSeg(container.querySelector('#challenger-selector'), this.localState.challenger);
    }
    // Mettre à jour l’UI du médiateur selon l’agent restant.
    this._updateMediatorUI(container);
  }

  _computeMediatorId() {
    const all = Object.keys(AGENTS);
    const { attacker, challenger } = this.localState;
    return (
      all.find(k => k !== attacker && k !== challenger) || // agent restant
      all.find(k => k !== attacker) ||                     // fallback
      all[0] || 'nexus'
    );
  }

  _updateMediatorUI(container) {
    const el = container.querySelector('#mediator-info');
    if (!el) return;
    const mediatorId = this._computeMediatorId();
    el.classList.remove('agent--anima','agent--neo','agent--nexus');
    el.classList.add(`agent--${mediatorId}`);
    el.textContent = AGENTS[mediatorId]?.name || mediatorId;
  }

  _setSeg(el, val){ el?.querySelectorAll('.button-tab').forEach(b => b.classList.toggle('active', b.dataset.value === val)); }

  /* ───────────── Vue Déroulé ───────────── */
  renderDebateView(container, state) {
    const order = state.config?.agentOrder || state.config?.agent_order || [];
    const attackerId = order[0] || state.config?.attacker || 'anima';
    const synthesizerId = order[order.length - 1] || 'nexus';
    const synthesizerName = AGENTS[synthesizerId]?.name || 'Nexus';

    // Désactive le bouton "Lancer" tant qu’un débat est en cours côté store
    const busy = state?.status === 'pending' || state?.status === 'in_progress';

    container.innerHTML = `
      <div class="debate-view-wrapper">
        <div class="card debate-in-progress">
          <div class="card-header">
            <h2 class="card-title">${state.config?.topic || 'Débat'}</h2>
            <div class="debate-status">${state.statusText || ''}</div>
          </div>
          <div class="card-body">
            <div class="debate-timeline">
              ${this._buildTimeline(state, attackerId)}
              ${state.synthesis ? this._buildSynthesis(state.synthesis, synthesizerId, synthesizerName) : ''}
            </div>
          </div>
          <div class="card-footer" style="display:flex; justify-content:flex-end; gap:.5rem;">
            <button id="debate-export-btn" class="button" title="Exporter">Exporter</button>
            <button id="debate-reset-btn" class="button" title="Réinitialiser"${busy ? '' : ''}>Réinitialiser</button>
          </div>
        </div>
      </div>
    `;

    container.querySelector('#debate-reset-btn')?.addEventListener('click', () => this.eventBus.emit('debate:reset'));
    container.querySelector('#debate-export-btn')?.addEventListener('click', () => this.eventBus.emit('debate:export', state));
    container.querySelector('.debate-timeline')?.scrollTo(0, 1e9);
  }

  _buildTimeline(state, attackerId) {
    if (!state.history || state.history.length === 0) {
      return `<div class="placeholder">Le débat va bientôt commencer...</div>`;
    }
    return state.history.map((turn) => {
      const header = `<div class="timeline-turn-separator turn--${attackerId}"><span>Tour ${turn.roundNumber}</span></div>`;
      const messages = Object.entries(turn.agentResponses).map(([agentId, response]) => {
        const agent = AGENTS[agentId] || { name: 'Inconnu', id: agentId };
        return `
          <div class="message assistant agent--${agentId}">
            <div class="message-content">
              <div class="message-text">
                <div class="message-meta"><strong class="sender-name" data-role="author">${agent.name}</strong></div>
                ${marked.parse(response)}
              </div>
            </div>
          </div>`;
      }).join('');
      return `${header}${messages}`;
    }).join('');
  }

  _buildSynthesis(text, synthesizerId, synthesizerName) {
    return `
      <div class="message assistant agent--${synthesizerId} synthesis">
        <div class="message-content">
          <div class="message-text">
            <div class="message-meta"><strong class="sender-name" data-role="author">Synthèse par ${synthesizerName}</strong></div>
            <div class="synthesis-body">${marked.parse(text)}</div>
          </div>
        </div>
      </div>
    `;
  }
}
