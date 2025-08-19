/**
 * src/frontend/features/debate/debate-ui.js
 * V36.9 — Validation stricte (agents/rounds), anti double-émission, options agents robustes,
 *          pas de fuite de contexte côté UI (rôles isolés).
 */
import { EVENTS, AGENTS } from '../../shared/constants.js';
import { marked } from 'https://cdn.jsdelivr.net/npm/marked/lib/marked.esm.js';
import { loadCSS } from '../../core/utils.js';

export class DebateUI {
  constructor(eventBus) {
    this.eventBus = eventBus;
    this.localState = {};
    this._createLocked = false; // anti double-émission
    // ✅ Patch Option A : chemin ABSOLU vers la CSS du module Débat
    try { loadCSS('/src/frontend/features/debate/debate.css'); } catch (_) {}
    console.log('✅ DebateUI V36.9 prêt (CSS chargée).');
  }

  render(container, data = {}) {
    container.innerHTML = `
      <div class="debate-view-wrapper">
        <div class="card">

          <div class="card-header">
            <h2 class="card-title">Débats</h2>
            <div class="debate-status">Configurer un duel d'agents puis lancer le déroulé.</div>
          </div>

          <div class="card-body">
            <div class="debate-create-body">

              <!-- Sujet -->
              <div class="form-group form-topic">
                <label for="debate-topic" class="label">Sujet du débat</label>
                <textarea id="debate-topic" class="input-text" placeholder="Ex. « est-ce qu’on est triste parce qu’on pleure ? »"></textarea>
              </div>

              <!-- Configuration 2x2 -->
              <div class="config-grid">

                <div class="form-group form-attacker">
                  <label class="label">Attaquant</label>
                  <div class="segmented" id="seg-attacker">
                    ${this._renderAgentTabs('attacker')}
                  </div>
                </div>

                <div class="form-group form-challenger">
                  <label class="label">Challenger</label>
                  <div class="segmented" id="seg-challenger">
                    ${this._renderAgentTabs('challenger')}
                  </div>
                </div>

                <div class="form-group form-rounds">
                  <label class="label">Nombre de tours</label>
                  <div class="segmented" id="seg-rounds">
                    ${this._renderRoundTabs()}
                  </div>
                </div>

                <div class="form-group form-mediator">
                  <label class="label">Synthèse par</label>
                  <div id="mediator-display" class="mediator-display">Automatique</div>
                </div>

              </div>

              <!-- RAG power -->
              <div class="rag-row">
                <span class="rag-label">RAG</span>
                <button id="rag-power" class="rag-power" role="switch"
                  aria-label="Basculer le RAG"
                  aria-checked="false"
                  title="RAG désactivé">
                  <svg viewBox="0 0 24 24" class="icon-power" aria-hidden="true" focusable="false">
                    <path class="power-line" d="M12 3 v7" />
                    <path class="power-circle" d="M6.5 7.5a7 7 0 1 0 11 0" />
                  </svg>
                </button>
              </div>

            </div>
          </div>

          <!-- CTA -->
          <div class="card-footer debate-create-footer">
            <button id="create-debate-btn" class="button button-primary button-xxl">Lancer le Débat</button>
          </div>

        </div>
      </div>

      <div class="debate-timeline" id="debate-timeline" aria-live="polite" aria-busy="false"></div>
    `;

    this._bindCreate();
    this._bindRagToggle();
    this._initLocalState();
  }

  _renderAgentTabs(kind) {
    const items = [
      { id: AGENTS.ANIMA, label: 'Anima',   cls: 'agent--anima'   },
      { id: AGENTS.NEO,   label: 'Neo',     cls: 'agent--neo'     },
      { id: AGENTS.NEXUS, label: 'Nexus',   cls: 'agent--nexus'   },
    ];
    return items.map((it, i) => `
      <button class="button-tab ${it.cls}" data-kind="${kind}" data-agent="${it.id}" aria-pressed="${i===0?'true':'false'}">${it.label}</button>
    `).join('');
  }

  _renderRoundTabs() {
    const rounds = [1, 2, 3, 4, 5];
    return rounds.map((n, i) => `
      <button class="button-tab" data-kind="rounds" data-rounds="${n}" aria-pressed="${i===2?'true':'false'}">${n}</button>
    `).join('');
  }

  _bindRagToggle() {
    const btn = document.getElementById('rag-power');
    if (!btn) return;
    const setState = (on) => {
      btn.setAttribute('aria-checked', on ? 'true' : 'false');
      btn.title = on ? 'RAG activé' : 'RAG désactivé';
    };
    setState(false);
    btn.addEventListener('click', () => {
      const isOn = btn.getAttribute('aria-checked') === 'true';
      setState(!isOn);
      this.localState.use_rag = !isOn;
    });
  }

  _bindCreate() {
    const btn = document.getElementById('create-debate-btn');
    const topicEl = document.getElementById('debate-topic');
    const segAtt = document.getElementById('seg-attacker');
    const segCha = document.getElementById('seg-challenger');
    const segRnd = document.getElementById('seg-rounds');
    const timeline = document.getElementById('debate-timeline');

    const parseAgent = (segEl, fallback) => {
      const pressed = segEl?.querySelector('[aria-pressed="true"]');
      const id = pressed?.getAttribute('data-agent');
      return id ?? fallback;
    };
    const parseRounds = (segEl, fallback = 3) => {
      const pressed = segEl?.querySelector('[aria-pressed="true"]');
      const n = Number(pressed?.getAttribute('data-rounds'));
      if (!Number.isFinite(n) || n < 1 || n > 5) return fallback;
      return n;
    };
    const sanitizeTopic = (s) => (s ?? '').trim().slice(0, 2000);

    const setBusy = (busy) => {
      timeline.setAttribute('aria-busy', busy ? 'true' : 'false');
      btn.disabled = !!busy;
    };

    // Tabs behavior (exclusive)
    const onTabClick = (ev) => {
      const t = ev.target.closest('.button-tab');
      if (!t) return;
      const kind = t.getAttribute('data-kind');
      const parent = t.parentElement;
      parent.querySelectorAll('.button-tab').forEach(b => b.setAttribute('aria-pressed', 'false'));
      t.setAttribute('aria-pressed', 'true');

      if (kind === 'attacker' || kind === 'challenger') {
        document.getElementById('mediator-display').textContent = 'Automatique';
      }
    };
    segAtt?.addEventListener('click', onTabClick);
    segCha?.addEventListener('click', onTabClick);
    segRnd?.addEventListener('click', onTabClick);

    btn?.addEventListener('click', async () => {
      if (this._createLocked) return;
      this._createLocked = true;
      setBusy(true);
      try {
        const topic = sanitizeTopic(topicEl?.value);
        if (!topic) {
          alert('Merci de saisir un sujet de débat.');
          return;
        }
        const attacker  = parseAgent(segAtt, AGENTS.ANIMA);
        const challenger= parseAgent(segCha, AGENTS.NEO);
        const rounds    = parseRounds(segRnd, 3);
        const use_rag   = !!this.localState.use_rag;

        // Sûreté : pas d’auto-miroir
        if (attacker === challenger) {
          alert('Choisis deux agents différents.');
          return;
        }

        this.eventBus.emit(EVENTS.DEBATE_CREATE, { topic, attacker, challenger, rounds, use_rag });
      } finally {
        setBusy(false);
        this._createLocked = false;
      }
    });
  }

  /**
   * Déroulé : append messages (centrés, stylés via debate.css)
   */
  appendMessage({ role, agent, text, isSynthesis = false }) {
    const timeline = document.getElementById('debate-timeline');
    if (!timeline) return;

    const safe = (s) => (s ?? '').toString();
    const nameByAgent = (a) => a === AGENTS.ANIMA ? 'Anima' : a === AGENTS.NEO ? 'Neo' : 'Nexus';
    const clsAgent = (a) => a === AGENTS.ANIMA ? 'agent--anima' : a === AGENTS.NEO ? 'agent--neo' : 'agent--nexus';

    const wrapper = document.createElement('div');
    wrapper.className = [
      'message',
      role === 'assistant' ? 'assistant' : 'user',
      isSynthesis ? 'synthesis' : '',
      role === 'assistant' ? `agent--${nameByAgent(agent).toLowerCase()}` : ''
    ].filter(Boolean).join(' ');

    const content = document.createElement('div');
    content.className = 'message-content';

    // Entête (nom + "Tour X" géré par l'orchestrateur côté mediator si besoin)
    const sender = document.createElement('div');
    sender.className = 'sender-name';
    sender.textContent = role === 'assistant' ? nameByAgent(agent) : 'Toi';

    // Texte (markdown)
    const body = document.createElement('div');
    body.className = 'message-text';
    body.innerHTML = marked.parse(safe(text));

    content.appendChild(sender);
    content.appendChild(body);
    wrapper.appendChild(content);

    timeline.appendChild(wrapper);
    timeline.scrollTop = timeline.scrollHeight;
  }

  /**
   * Turn separator
   */
  appendTurnSeparator(n) {
    const timeline = document.getElementById('debate-timeline');
    if (!timeline) return;
    const sep = document.createElement('div');
    sep.className = 'timeline-turn-separator';
    sep.innerHTML = `<span>Tour ${n}</span>`;
    timeline.appendChild(sep);
  }

  _initLocalState() {
    // État local par défaut
    this.localState = {
      use_rag: false,
    };
  }
}
