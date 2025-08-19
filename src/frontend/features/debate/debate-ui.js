/**
 * src/frontend/features/debate/debate-ui.js
 * V37.1 — compat mobile: CSS chargée en absolu, sélecteurs visibles, défauts sûrs,
 *          médiateur explicite, anti-blocage agents identiques.
 */
import { EVENTS, AGENTS } from '../../shared/constants.js';
import { marked } from 'https://cdn.jsdelivr.net/npm/marked/lib/marked.esm.js';
import { loadCSS } from '../../core/utils.js';

export class DebateUI {
  constructor(eventBus) {
    this.eventBus = eventBus;
    this.localState = {};
    this._createLocked = false;
    // ✅ Chemin absolu pour garantir le chargement en prod
    try { loadCSS('/src/frontend/features/debate/debate.css'); } catch (_) {}
  }

  render(container, _state = {}) {
    if (!container) return;
    this._renderCreation(container);
  }

  /* ───────────── Vue Création ───────────── */
  _renderCreation(container) {
    const agentDefs = this._agentOptions();
    const defaultState = {
      topic: '',
      attacker: 'anima',
      challenger: 'neo',
      rounds: 3,
      use_rag: false,
    };

    container.innerHTML = `
      <div class="debate-view-wrapper">
        <div class="card">
          <div class="card-header">
            <h2 class="card-title">Débats</h2>
            <div class="debate-status">Configurer un duel d'agents puis lancer le déroulé.</div>
          </div>

          <div class="card-body debate-create-body">
            <!-- Sujet -->
            <div class="form-group form-topic">
              <label for="debate-topic">Sujet du débat</label>
              <textarea id="debate-topic" class="input-text" rows="3"
                placeholder="Ex. « Est-ce qu’on est triste parce qu’on pleure… »"></textarea>
            </div>

            <!-- Cadre CONFIGURATION (2×2) -->
            <div class="config-grid">
              <div class="form-group form-attacker">
                <label>Attaquant</label>
                ${this._seg('attacker-selector', agentDefs, defaultState.attacker, true)}
              </div>

              <div class="form-group form-challenger">
                <label>Challenger</label>
                ${this._seg('challenger-selector', agentDefs, defaultState.challenger, true)}
              </div>

              <div class="form-group form-rounds">
                <label>Nombre de tours</label>
                ${this._seg('rounds-selector', [
                    {value:1,label:'1'}, {value:2,label:'2'}, {value:3,label:'3'}, {value:4,label:'4'}, {value:5,label:'5'}
                  ], defaultState.rounds, false)}
              </div>

              <div class="form-group form-mediator">
                <label>Synthèse par</label>
                <span id="mediator-info" class="mediator-display agent--nexus">Nexus</span>
              </div>
            </div>

            <!-- RAG -->
            <div class="rag-row">
              <span class="rag-label">RAG</span>
              <button id="rag-power" class="rag-power" role="switch" aria-checked="false" title="RAG désactivé">
                <svg viewBox="0 0 24 24" class="icon-power" aria-hidden="true" focusable="false">
                  <path class="power-line" d="M12 3 v7" />
                  <path class="power-circle" d="M6.5 7.5a7 7 0 1 0 11 0" />
                </svg>
              </button>
            </div>
          </div>

          <div class="card-footer debate-create-footer">
            <button id="create-debate-btn" class="button button-primary button-xxl">Lancer le Débat</button>
          </div>
        </div>
      </div>

      <div class="debate-timeline" id="debate-timeline" aria-live="polite" aria-busy="false"></div>
    `;

    // État local
    this.localState = { ...defaultState };

    // Bind segmented controls
    this._bindSegClicks(container.querySelector('#attacker-selector'), v => {
      this.localState.attacker = this._ensureValidAgent(v, 'anima');
      this._ensureAgentsDifferent(container);
    });
    this._bindSegClicks(container.querySelector('#challenger-selector'), v => {
      this.localState.challenger = this._ensureValidAgent(v, 'neo');
      this._ensureAgentsDifferent(container);
    });
    this._bindSegClicks(container.querySelector('#rounds-selector'), v => {
      this.localState.rounds = this._clampInt(v, 1, 5);
    });

    // Sujet + RAG
    const topicEl = container.querySelector('#debate-topic');
    topicEl?.addEventListener('input', (e) => { this.localState.topic = (e.target.value || '').trim(); });

    const ragBtn = container.querySelector('#rag-power');
    ragBtn?.addEventListener('click', () => {
      const on = ragBtn.getAttribute('aria-checked') === 'true';
      const next = !on;
      ragBtn.setAttribute('aria-checked', String(next));
      ragBtn.setAttribute('title', next ? 'RAG activé' : 'RAG désactivé');
      this.localState.use_rag = next;
    });

    // CTA
    const createBtn = container.querySelector('#create-debate-btn');
    createBtn?.addEventListener('click', () => {
      if (this._createLocked) return;
      const topic = (this.localState.topic || '').trim();
      if (topic.length < 10) { alert('Sujet trop court.'); return; }

      // Anti-mirolir: ajuste automatiquement si besoin
      this._ensureAgentsDifferent(container);

      const attacker = this.localState.attacker;
      const challenger = this.localState.challenger;
      const mediatorId = this._computeMediatorId(attacker, challenger);
      const rounds = this._clampInt(this.localState.rounds, 1, 5);

      const payload = {
        topic,
        rounds,
        agent_order: [attacker, challenger, mediatorId],
        use_rag: !!this.localState.use_rag
      };

      this._createLocked = true;
      createBtn.disabled = true;
      this.eventBus.emit(EVENTS.DEBATE_CREATE, payload);
    });

    // Init visu médiateur
    this._updateMediatorUI(container);
  }

  /* Helpers UI */
  _seg(id, options, selected, colorByAgent=false) {
    return `
      <div id="${id}" class="segmented">
        ${options.map(opt => `
          <button class="button-tab ${colorByAgent ? `agent--${opt.value}` : ''} ${String(opt.value)===String(selected) ? 'active' : ''}"
                  data-value="${opt.value}" aria-pressed="${String(opt.value)===String(selected) ? 'true' : 'false'}">
            <span class="tab-label">${opt.label}</span>
          </button>`).join('')}
      </div>`;
  }

  _bindSegClicks(container, onChange){
    if(!container) return;
    container.addEventListener('click', (e) => {
      const btn = e.target.closest('button[data-value]'); if (!btn) return;
      container.querySelectorAll('button').forEach(b => { b.classList.remove('active'); b.setAttribute('aria-pressed','false'); });
      btn.classList.add('active'); btn.setAttribute('aria-pressed','true');
      onChange?.(btn.dataset.value);
    });
  }

  _ensureAgentsDifferent(container){
    if (this.localState.attacker === this.localState.challenger) {
      const next = this._fallbackOtherAgent(this.localState.attacker) || 'nexus';
      this.localState.challenger = next;
      // reflect UI
      this._setSeg(container.querySelector('#challenger-selector'), next);
    }
    this._updateMediatorUI(container);
  }

  _agentOptions(){
    // Robuste aux deux formes possibles de AGENTS (ids en clés ou en valeurs)
    const entries = Object.entries(AGENTS);
    const ids = new Set();
    for (const [k,v] of entries){
      if (typeof v === 'string'){ ids.add(v); }
      else { ids.add(k); }
    }
    return Array.from(ids).map(id => ({ value:id, label: id.charAt(0).toUpperCase()+id.slice(1) }));
  }

  _fallbackOtherAgent(excludeId) {
    const all = this._agentOptions().map(x=>x.value);
    return all.find(k => k !== excludeId);
  }

  _computeMediatorId(attacker, challenger) {
    const all = this._agentOptions().map(x=>x.value);
    return all.find(k => k !== attacker && k !== challenger) || 'nexus';
  }

  _updateMediatorUI(container) {
    const el = container.querySelector('#mediator-info'); if (!el) return;
    const mediatorId = this._computeMediatorId(this.localState.attacker, this.localState.challenger);
    el.classList.remove('agent--anima','agent--neo','agent--nexus');
    el.classList.add(`agent--${mediatorId}`);
    el.textContent = mediatorId.charAt(0).toUpperCase()+mediatorId.slice(1);
  }

  _setSeg(seg, val){
    seg?.querySelectorAll('.button-tab').forEach(b => {
      const on = b.dataset.value === String(val);
      b.classList.toggle('active', on);
      b.setAttribute('aria-pressed', on ? 'true' : 'false');
    });
  }

  _ensureValidAgent(id, fallback='anima'){
    const ids = this._agentOptions().map(x=>x.value);
    return ids.includes(id) ? id : (ids.includes(fallback) ? fallback : ids[0]);
  }
  _clampInt(n, min, max){ const v = Number.isFinite(Number(n)) ? Math.trunc(Number(n)) : min; return Math.max(min, Math.min(max, v)); }

  /* ───────────── Chrono (utilisé pendant le déroulé) ───────────── */
  appendMessage({ role, agent, text, isSynthesis = false }) {
    const timeline = document.getElementById('debate-timeline'); if (!timeline) return;
    const name = (s)=>s ? s.charAt(0).toUpperCase()+s.slice(1) : '';
    const wrapper = document.createElement('div');
    wrapper.className = ['message', role === 'assistant' ? 'assistant' : 'user', isSynthesis ? 'synthesis' : '', `agent--${agent||'anima'}`].filter(Boolean).join(' ');
    const content = document.createElement('div'); content.className = 'message-content';
    const sender = document.createElement('div'); sender.className = 'sender-name'; sender.textContent = role === 'assistant' ? name(agent) : 'Toi';
    const body = document.createElement('div'); body.className = 'message-text'; body.innerHTML = marked.parse((text||'').toString());
    content.appendChild(sender); content.appendChild(body); wrapper.appendChild(content);
    timeline.appendChild(wrapper); timeline.scrollTop = timeline.scrollHeight;
  }
  appendTurnSeparator(n){
    const t = document.getElementById('debate-timeline'); if(!t) return;
    const sep = document.createElement('div'); sep.className = 'timeline-turn-separator'; sep.innerHTML = `<span>Tour ${n}</span>`; t.appendChild(sep);
  }
}
