/**
 * src/frontend/features/debate/debate-ui.js
 * V38.0 — Vue pilotée par state (création ↔ déroulé), timeline depuis history,
 *          synthèse affichée, sujet conservé, CSS chargée (anti-double),
 *          valeurs par défaut sûres (Anima/Neo), médiateur explicite.
 */
import { EVENTS, AGENTS } from '../../shared/constants.js';
import { marked } from 'https://cdn.jsdelivr.net/npm/marked/lib/marked.esm.js';
import { loadCSS } from '../../core/utils.js';

export class DebateUI {
  constructor(eventBus) {
    this.eventBus = eventBus;
    this.localState = {
      topic: '',
      attacker: 'anima',
      challenger: 'neo',
      rounds: 3,
      use_rag: false,
    };
    this._createLocked = false;

    // ✅ Charger la CSS une fois (anti-double)
    try {
      const href = '/src/frontend/features/debate/debate.css';
      const already = Array.from(document.querySelectorAll('link[rel="stylesheet"]'))
        .some(l => (l.getAttribute('href') || '').endsWith('/src/frontend/features/debate/debate.css'));
      if (!already) loadCSS(href);
    } catch (_) {}
  }

  /**
   * Render décide de la vue en fonction du state normalisé par l’orchestrateur.
   * - state.status ∈ {pending, in_progress, completed} → vue Déroulé
   * - sinon → vue Création
   */
  render(container, debateState = {}) {
    if (!container) return;

    const status = debateState?.status;
    const hasHistory = Array.isArray(debateState?.history) && debateState.history.length > 0;
    const showTimeline = status === 'pending' || status === 'in_progress' || status === 'completed' || hasHistory;

    if (showTimeline) {
      this._renderTimeline(container, debateState);
    } else {
      this._renderCreation(container);
    }
  }

  /* ────────────────────────── Vue Création ────────────────────────── */
  _renderCreation(container) {
    const agentDefs = this._agentOptions();
    const selectedAttacker   = this.localState.attacker || 'anima';
    const selectedChallenger = this.localState.challenger || 'neo';
    const selectedRounds     = Number.isFinite(this.localState.rounds) ? this.localState.rounds : 3;

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
                ${this._seg('attacker-selector', agentDefs, selectedAttacker, true)}
              </div>

              <div class="form-group form-challenger">
                <label>Challenger</label>
                ${this._seg('challenger-selector', agentDefs, selectedChallenger, true)}
              </div>

              <div class="form-group form-rounds">
                <label>Nombre de tours</label>
                ${this._seg('rounds-selector',
                  [{value:1,label:'1'},{value:2,label:'2'},{value:3,label:'3'},{value:4,label:'4'},{value:5,label:'5'}],
                  selectedRounds, false)}
              </div>

              <div class="form-group form-mediator">
                <label>Synthèse par</label>
                <span id="mediator-info" class="mediator-display agent--nexus">Nexus</span>
              </div>
            </div>

            <!-- RAG -->
            <div class="rag-row">
              <span class="rag-label">RAG</span>
              <button id="rag-power" class="rag-power" role="switch" aria-checked="${this.localState.use_rag?'true':'false'}"
                title="${this.localState.use_rag ? 'RAG activé' : 'RAG désactivé'}">
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

    // Restaurer le sujet saisi si re-render
    const topicEl = container.querySelector('#debate-topic');
    if (topicEl) topicEl.value = this.localState.topic || '';

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

      // Anti-miroir : ajuste automatiquement si besoin
      this._ensureAgentsDifferent(container);

      const attacker   = this.localState.attacker   || 'anima';
      const challenger = this.localState.challenger || 'neo';
      const mediatorId = this._computeMediatorId(attacker, challenger);
      const rounds     = this._clampInt(this.localState.rounds, 1, 5);

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

  /* ────────────────────────── Vue Déroulé ────────────────────────── */
  _renderTimeline(container, state) {
    const cfg = state?.config || {};
    const topic   = cfg.topic || this.localState.topic || '';
    const rounds  = Number(cfg.rounds || this.localState.rounds || 3);
    const order   = Array.isArray(cfg.agentOrder) ? cfg.agentOrder : (Array.isArray(cfg.agent_order) ? cfg.agent_order : []);
    const statusText = state?.statusText || this._statusTextFallback(state);

    container.innerHTML = `
      <div class="debate-view-wrapper">
        <div class="card">
          <div class="card-header">
            <h2 class="card-title">Déroulé du débat</h2>
            <div class="debate-status">${statusText}</div>
          </div>

          <div class="card-body">
            <div class="form-group">
              <label style="display:block; margin-bottom:.35rem; opacity:.85;">Sujet</label>
              <div class="input-text" style="min-height:auto; padding:.6rem 1rem;">${this._escape(topic)}</div>
            </div>

            <div class="debate-timeline" id="debate-timeline" aria-live="polite" aria-busy="${state?.status==='in_progress'?'true':'false'}"></div>
          </div>

          <div class="card-footer" style="display:flex; gap:.5rem; flex-wrap:wrap;">
            <button id="export-debate-btn" class="button">Exporter (.md)</button>
            <button id="reset-debate-btn" class="button button-secondary">Nouveau débat</button>
          </div>
        </div>
      </div>
    `;

    // Hydrate la timeline complète depuis l’historique
    const t = container.querySelector('#debate-timeline');
    if (t) {
      const history = Array.isArray(state?.history) ? state.history : [];
      history.forEach(turn => {
        const round = turn?.roundNumber ?? turn?.round_number ?? null;
        if (round != null) this._appendTurnSeparatorEl(t, round);

        const responses = turn?.agentResponses || turn?.agent_responses || {};
        const idsInOrder = order.length ? order.slice(0, -1) /* sans médiateur */ : Object.keys(responses);

        idsInOrder.forEach(agentId => {
          const txt = responses?.[agentId];
          if (!txt) return;
          this._appendMessageEl(t, { role:'assistant', agent: agentId, text: txt, isSynthesis:false });
        });
      });

      // Synthèse si disponible
      if (state?.synthesis) {
        const mediatorId = order.length ? order[order.length - 1] : 'nexus';
        this._appendTurnSeparatorEl(t, 'Synthèse');
        this._appendMessageEl(t, { role:'assistant', agent: mediatorId, text: state.synthesis, isSynthesis:true });
      }

      // Auto-scroll bas
      t.scrollTop = t.scrollHeight;
    }

    // Actions
    container.querySelector('#export-debate-btn')?.addEventListener('click', () => {
      this.eventBus.emit('debate:export', state);
    });
    container.querySelector('#reset-debate-btn')?.addEventListener('click', () => {
      this._createLocked = false;
      this.eventBus.emit('debate:reset');
    });
  }

  /* ───────────────────── Helpers UI/Markup ───────────────────── */
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
      this._setSeg(container?.querySelector('#challenger-selector'), next);
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
    const el = container?.querySelector('#mediator-info'); if (!el) return;
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
  _escape(s){ return String(s ?? '').replace(/[&<>"]/g, c=>({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;' }[c])); }

  /* ─────────── Rendu timeline (éléments DOM) ─────────── */
  _appendMessageEl(timeline, { role, agent, text, isSynthesis = false }) {
    const name = (s)=>s ? s.charAt(0).toUpperCase()+s.slice(1) : '';
    const wrapper = document.createElement('div');
    wrapper.className = ['message', role === 'assistant' ? 'assistant' : 'user', isSynthesis ? 'synthesis' : '', `agent--${agent||'anima'}`]
      .filter(Boolean).join(' ');
    const content = document.createElement('div'); content.className = 'message-content';
    const sender = document.createElement('div'); sender.className = 'sender-name'; sender.textContent = role === 'assistant' ? name(agent) : 'Toi';
    const body = document.createElement('div'); body.className = 'message-text'; body.innerHTML = marked.parse((text||'').toString());
    content.appendChild(sender); content.appendChild(body); wrapper.appendChild(content);
    timeline.appendChild(wrapper);
  }
  _appendTurnSeparatorEl(timeline, n){
    const sep = document.createElement('div'); sep.className = 'timeline-turn-separator';
    sep.innerHTML = `<span>${n === 'Synthèse' ? 'Synthèse' : `Tour ${n}`}</span>`;
    timeline.appendChild(sep);
  }
}
