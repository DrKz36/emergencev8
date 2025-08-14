/**
 * src/frontend/features/debate/debate-ui.js
 * V36.2 — layout PC selon schéma : config-grid 2×2, RAG (checkbox) sous config, CTA centré large.
 */
import { EVENTS, AGENTS } from '../../shared/constants.js';
import { marked } from 'https://cdn.jsdelivr.net/npm/marked/lib/marked.esm.js';
import { loadCSS } from '../../core/utils.js';

export class DebateUI {
  constructor(eventBus) {
    this.eventBus = eventBus;
    this.localState = {};
    try { loadCSS('../features/debate/debate.css'); } catch (_) {}
    console.log('✅ DebateUI V36.2 prêt (CSS chargée).');
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
              <label class="checkbox-rag" for="debate-rag">
                <input id="debate-rag" type="checkbox" />
                <span>Activer RAG (recherche documentaire)</span>
              </label>
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
    this._updateAgentSelection(container);
  }

  _bindCreationEvents(container) {
    const topicEl = container.querySelector('#debate-topic');
    const ragInput = container.querySelector('#debate-rag');

    this._bindSegClicks(container.querySelector('#attacker-selector'), v => {
      this.localState.attacker = v; this._updateAgentSelection(container);
    });
    this._bindSegClicks(container.querySelector('#challenger-selector'), v => {
      this.localState.challenger = v; this._updateAgentSelection(container);
    });
    this._bindSegClicks(container.querySelector('#rounds-selector'), v => {
      this.localState.rounds = Number(v);
    });

    topicEl?.addEventListener('input', (e) => { this.localState.topic = e.target.value || ''; });

    ragInput?.addEventListener('change', (e) => {
      this.localState.use_rag = !!e.target.checked;
      this.eventBus.emit(EVENTS.CHAT_RAG_TOGGLED, { enabled: this.localState.use_rag });
    });

    container.querySelector('#create-debate-btn')?.addEventListener('click', () => {
      const topic = (topicEl?.value || '').trim();
      if (topic.length < 10) {
        this.eventBus.emit(EVENTS.SHOW_NOTIFICATION, { type:'warning', message:'Le sujet du débat est trop court.' });
        return;
      }
      const config = {
        topic,
        rounds: this.localState.rounds,
        agent_order: [this.localState.attacker, this.localState.challenger, 'nexus'],
        use_rag: this.localState.use_rag
      };
      this.eventBus.emit(EVENTS.DEBATE_CREATE, config);
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
    if (this.localState.attacker === this.localState.challenger) {
      this.localState.challenger = Object.keys(AGENTS).find(k => k !== this.localState.attacker && k !== 'nexus') || 'neo';
      this._setSeg(container.querySelector('#challenger-selector'), this.localState.challenger);
    }
    const el = container.querySelector('#mediator-info');
    el?.classList.remove('agent--anima','agent--neo','agent--nexus');
    el?.classList.add('agent--nexus');   // Nexus confirmé (backend)
    if (el) el.textContent = AGENTS['nexus']?.name || 'Nexus';
  }

  _setSeg(el, val){ el?.querySelectorAll('.button-tab').forEach(b => b.classList.toggle('active', b.dataset.value === val)); }

  /* ───────────── Vue Déroulé ───────────── */
  renderDebateView(container, state) {
    const order = state.config?.agentOrder || state.config?.agent_order || [];
    const attackerId = order[0] || state.config?.attacker || 'anima';
    const synthesizerId = order[order.length - 1] || 'nexus';
    const synthesizerName = AGENTS[synthesizerId]?.name || 'Nexus';

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
            <button id="debate-reset-btn" class="button" title="Réinitialiser">Réinitialiser</button>
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
                <div class="message-meta"><strong class="sender-name">${agent.name}</strong></div>
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
            <div class="message-meta"><strong class="sender-name">Synthèse par ${synthesizerName}</strong></div>
            <div class="synthesis-body">${marked.parse(text)}</div>
          </div>
        </div>
      </div>
    `;
  }
}
