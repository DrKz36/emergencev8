/**
 * src/frontend/features/debate/debate-ui.js
 * V42.3 — Affichage timeline basé sur turns OU status 'completed' (plus history),
 *         + "Nouveau débat" désactivé pendant HOLD avec compte à rebours,
 *         + labels agents robustes.
 */
import { EVENTS, AGENTS } from '../../shared/constants.js';
import { marked } from 'https://cdn.jsdelivr.net/npm/marked/lib/marked.esm.js';

function agentLabel(id) {
  const a = AGENTS?.[id];
  return (a?.label || a?.name || id);
}

export class DebateUI {
  constructor(eventBus) {
    this.eventBus = eventBus;
    this._touched = { attacker:false, challenger:false, mediator:false, rounds:false };
    console.log('✅ DebateUI V42.3 prêt.');
  }

  render(container, debateState) {
    if (!container) return;

    const turns = Array.isArray(debateState?.turns) ? debateState.turns : [];
    const hasHistory = Array.isArray(debateState?.history) && debateState.history.length > 0;
    const isActive   = !!debateState?.isActive;
    const isCompleted = (debateState?.status === 'completed');
    const statusText = debateState?.statusText ?? 'Prêt à commencer.';

    // ✅ Montre la timeline si on a des tours OU si c'est actif OU si c'est terminé,
    //    pas uniquement si 'history' est rempli.
    const shouldShowTimeline = isActive || isCompleted || (turns.length > 0) || hasHistory;

    if (!shouldShowTimeline) {
      container.innerHTML = this._renderCreateView(statusText);
      this._bindCreateEvents(container);
      return;
    }

    container.innerHTML = this._renderTimelineView(debateState);
    this._bindTimelineEvents(container, debateState);
  }

  /* ---------------------------- Vue Création ---------------------------- */
  _renderCreateView(statusText) {
    const defaultAttacker='neo', defaultChallenger='nexus';
    const defaultMediator = this._autoFrom(defaultAttacker, defaultChallenger);

    const segAttacker   = this._segAgents('attacker',   defaultAttacker);
    const segChallenger = this._segAgents('challenger', defaultChallenger);
    const segMediator   = this._segAgents('mediator',   defaultMediator);
    const roundsTabs    = this._segRounds(3);

    return `
      <div class="debate-view-wrapper">
        <div class="card">
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

              <div class="form-group form-mediator">
                <label>Médiateur (synthèse finale)</label>
                ${segMediator}
              </div>

              <div class="form-group form-rounds">
                <label>Nombre de tours</label>
                ${roundsTabs}
              </div>

              <div class="form-group form-rag">
                <label>RAG</label>
                <button type="button" id="rag-power" class="rag-power toggle-metal" role="switch" aria-checked="true" aria-label="Activer ou desactiver le RAG" title="Activer/Desactiver RAG">
                  <svg class="power-icon" viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
                    <path d="M12 3v9" stroke="currentColor" stroke-width="2" stroke-linecap="round" fill="none"/>
                    <path d="M5.5 7a8 8 0 1 0 13 0" stroke="currentColor" stroke-width="2" stroke-linecap="round" fill="none"/>
                  </svg>
                </button>
                <span id="rag-label" class="rag-label">RAG actif</span>
              </div>

              <div class="action-center">
                <button class="button button-primary" id="debate-start">Lancer le débat</button>
              </div>
            </div>
          </div>
        </div>
      </div>`;
  }

  _bindCreateEvents(root) {
    const topicEl = root.querySelector('#debate-topic');
    const headerTopic = root.querySelector('.debate-topic');
    topicEl?.addEventListener('input', () => { headerTopic.textContent = topicEl.value.trim() || '—'; });

    const ragBtn = root.querySelector('#rag-power');
    const ragLabel = root.querySelector('#rag-label');
    const setRagState = (isOn) => {
      const next = !!isOn;
      ragBtn?.setAttribute('aria-checked', next ? 'true' : 'false');
      if (ragLabel) {
        ragLabel.textContent = next ? 'RAG actif' : 'RAG inactif';
        ragLabel.classList.toggle('muted', !next);
      }
    };
    if (ragBtn) {
      setRagState(ragBtn.getAttribute('aria-checked') === 'true');
      const toggleRag = () => {
        const current = ragBtn.getAttribute('aria-checked') === 'true';
        setRagState(!current);
      };
      ragBtn.addEventListener('click', toggleRag);
      ragLabel?.addEventListener('click', toggleRag);
    }

    this._bindTabs(root, 'attacker');
    this._bindTabs(root, 'challenger');
    this._bindTabs(root, 'mediator');
    this._bindTabs(root, 'rounds');

    this._autoSelectMediator(root);
    root.querySelector('[data-seg="attacker"]')?.addEventListener('click', () => this._autoSelectMediator(root));
    root.querySelector('[data-seg="challenger"]')?.addEventListener('click', () => this._autoSelectMediator(root));

    root.querySelector('#debate-start')?.addEventListener('click', () => {
      const topic = root.querySelector('#debate-topic')?.value?.trim() ?? '';
      const attacker   = this._getSegValue(root, 'attacker');
      const challenger = this._getSegValue(root, 'challenger');
      let   mediator   = this._getSegValue(root, 'mediator');
      const rounds     = parseInt(this._getSegValue(root, 'rounds') || '3', 10) || 3;
      const useRag     = (root.querySelector('#rag-power')?.getAttribute('aria-checked') === 'true');

      if (!topic) { alert('Merci de renseigner un sujet de débat.'); return; }
      if (!attacker || !challenger) { alert('Merci de sélectionner Attaquant/Challenger.'); return; }
      if (attacker === 'neo' && challenger === 'nexus') mediator = 'anima';
      if (!mediator) { alert('Merci de sélectionner le Médiateur.'); return; }

      this.eventBus.emit(EVENTS.DEBATE_CREATE || 'debate:create', {
        topic, rounds, agentOrder: [attacker, challenger, mediator], useRag
      });
    });
  }

  /* ---------------------------- Vue Timeline ---------------------------- */
  _renderTimelineView(state) {
    const now = Date.now();
    const holdUntil = Number(state?.holdUntil || 0);
    const holdLeftMs = Math.max(0, holdUntil - now);
    const isHold = holdLeftMs > 0;
    const holdLeftS = Math.ceil(holdLeftMs / 1000);

    const topic = (state?.topic || state?.config?.topic || '').trim();
    const statusText = (state?.statusText ?? '').trim();
    const statusClass = state?.status ? ' debate-status--' + this._html(state.status) : '';
    const statusPieces = [];
    if (statusText) {
      statusPieces.push('<span class="debate-status-chip' + statusClass + '">' + this._html(statusText) + '</span>');
    }
    if (isHold) {
      statusPieces.push('<span class="debate-status-note" id="debate-hold-note">Nouveau débat disponible dans ' + holdLeftS + 's</span>');
    }
    const statusBlock = statusPieces.length ? '<div class="debate-header__status">' + statusPieces.join('') + '</div>' : '';

    const turns = Array.isArray(state?.turns) ? state.turns : [];
    const turnCount = turns.length;
    const rounds = Number.isFinite(state?.config?.rounds) ? Math.max(1, state.config.rounds) : 1;
    const participants = Array.isArray(state?.config?.agentOrder) ? Math.max(1, state.config.agentOrder.length - 1) : 2;
    const expectedTurns = Math.max(1, rounds * Math.max(1, participants));
    const clampedTurns = Math.min(turnCount, expectedTurns);
    const ratio = expectedTurns ? Math.min(1, clampedTurns / expectedTurns) : 0;
    const progressPercent = Math.round(ratio * 100);
    const progressInfo = '<div class="debate-progress" role="status" aria-live="polite">' +
      '<div class="debate-progress__label">' + clampedTurns + ' / ' + expectedTurns + ' interventions</div>' +
      '<div class="debate-progress__bar"><span style="width:' + progressPercent + '%;"></span></div>' +
    '</div>';

    const header = '<div class="card-header debate-header">' +
      '<div class="debate-header__topic">' +
        '<h2 class="debate-title">Sujet du débat</h2>' +
        '<p class="debate-topic">' + this._html(topic || '—') + '</p>' +
      '</div>' +
      statusBlock +
      progressInfo +
    '</div>';

    const turnsHtml = turnCount
      ? turns.map((turn, index) => this._renderTurn(turn, index)).join('')
      : '<div class="debate-empty">Aucune intervention pour le moment.</div>';
    const body = '<div class="card-body debate-body">' + turnsHtml + '</div>';

    const synthesizerId = Array.isArray(state?.config?.agentOrder)
      ? state.config.agentOrder[state.config.agentOrder.length - 1] : 'nexus';
    const synthesizerName = agentLabel(synthesizerId);

    const synthesis = (state?.status === 'completed' && state?.synthesis)
      ? this._renderSynthesis(synthesizerId, synthesizerName, state.synthesis)
      : '';

    const footer = '<div class="card-footer debate-footer">' +
        '<div class="debate-actions">' +
          '<button id="debate-export" class="button button-metal" title="Exporter en Markdown">Exporter</button>' +
          '<button id="debate-new" class="button button-primary" title="Lancer un nouveau débat"' +
            (isHold ? ' disabled aria-disabled="true"' : '') + ' data-hold-left="' + holdLeftS + '">' +
            'Nouveau débat' +
          '</button>' +
        '</div>' +
      '</div>';

    return '<div class="debate-view-wrapper"><div class="card">' + header + body + synthesis + footer + '</div></div>';
  }


  _renderTurn(turn, index) {
    if (!turn) return '';
    const agentId = (turn.agent || 'anima').toLowerCase();
    const agentName = this._html(agentLabel(agentId));
    const order = index + 1;
    const content = marked.parse(turn.text || '');
    return [
      '<article class="debate-turn debate-turn--' + this._html(agentId) + '">',
        '<div class="debate-turn__bubble">',
          '<header class="debate-turn__head">',
            '<span class="debate-turn__badge">' + order + '</span>',
            '<span class="debate-turn__agent">' + agentName + '</span>',
          '</header>',
          '<div class="debate-turn__message">' + content + '</div>',
        '</div>',
      '</article>'
    ].join('');
  }

  _renderSynthesis(agentId, agentName, textValue) {
    const html = marked.parse(textValue || '');
    return [
      '<section class="debate-synthesis">',
        '<h3 class="debate-synthesis__title">Synth&egrave;se &mdash; ' + this._html(agentName) + '</h3>',
        '<article class="debate-turn debate-turn--' + this._html(agentId) + ' debate-turn--synthesis">',
          '<div class="debate-turn__bubble">',
            '<header class="debate-turn__head">',
              '<span class="debate-turn__badge" aria-hidden="true">Σ</span>',
              '<span class="debate-turn__agent">' + this._html(agentName) + '</span>',
            '</header>',
            '<div class="debate-turn__message">' + html + '</div>',
          '</div>',
        '</article>',
      '</section>'
    ].join('');
  }
  _bindTimelineEvents(root, state) {
    root.querySelector('#debate-export')?.addEventListener('click', () => {
      const topic = (state?.topic || '').trim();
      const lines = [];
      lines.push(`# Débat — ${topic || 'Sans titre'}`);
      (state?.turns || []).forEach(t => {
        const agentId = t.agent || 'anima';
        const name = agentLabel(agentId);
        lines.push(`\n## ${name}\n\n${t.text || ''}`);
      });
      if (state?.synthesis) {
        const synName = agentLabel(state.config?.agentOrder?.slice(-1)[0] || 'nexus');
        lines.push(`\n---\n\n### Synthèse (${synName})\n\n${state.synthesis}`);
      }
      const blob = new Blob([lines.join('\n')], { type: 'text/markdown;charset=utf-8' });
      const url  = URL.createObjectURL(blob);
      const a = document.createElement('a'); a.href = url; a.download = `debate_${Date.now()}.md`; a.click();
      URL.revokeObjectURL(url);
    });

    // Verrou + compte à rebours sur "Nouveau débat"
    const btnNew = root.querySelector('#debate-new');
    if (btnNew) {
      const statusNote = root.querySelector('#debate-hold-note');
      const tick = () => {
        const left = parseInt(btnNew.getAttribute('data-hold-left') || '0', 10);
        if (!btnNew.disabled || !left) {
          if (statusNote) statusNote.remove();
          return;
        }
        const next = Math.max(0, left - 1);
        btnNew.setAttribute('data-hold-left', String(next));
        if (statusNote) {
          if (next > 0) statusNote.textContent = 'Nouveau débat disponible dans ' + next + 's';
          else statusNote.remove();
        }
        if (next === 0) {
          btnNew.disabled = false;
          btnNew.removeAttribute('aria-disabled');
        } else {
          setTimeout(tick, 1000);
        }
      };
      if (btnNew.disabled) setTimeout(tick, 1000);
      btnNew.addEventListener('click', () => { if (btnNew.disabled) return; this.eventBus.emit('debate:new'); });
    }
  }

  /* ---------------------------- Helpers UI ---------------------------- */
  _bindTabs(root, segRole) {
    const seg = root.querySelector(`[data-seg="${segRole}"]`);
    if (!seg) return;
    seg.addEventListener('click', (e) => {
      const btn = e.target?.closest?.('.button-tab');
      if (!btn) return;
      seg.querySelectorAll('.button-tab').forEach(b => {
        const isActive = (b === btn);
        b.classList.toggle('active', isActive);
        b.setAttribute('aria-pressed', isActive ? 'true' : 'false');
      });
      if (this._touched && segRole in this._touched) this._touched[segRole] = true;
    }, { passive: true });
  }

  _defaultFor(role){ if (role==='attacker') return 'neo'; if (role==='challenger') return 'nexus'; if (role==='mediator') return 'anima'; return 'anima'; }
  _segAgents(role, def='anima'){
    const agents = ['anima','neo','nexus'];
    const buttons = agents.map(a => {
      const label = agentLabel(a);
      const is = a === def;
      return `<button type="button" class="button-tab ${is?'active':''}" data-value="${a}" aria-pressed="${is?'true':'false'}">${this._html(label)}</button>`;
    }).join('');
    return `<div class="tabs-container" data-seg="${this._html(role)}">${buttons}</div>`;
  }
  _segRounds(d=3){ return `<div class="tabs-container rounds-tabs" data-seg="rounds">${[1,2,3,4,5].map(v => `<button type="button" class="button-tab ${v===d?'active':''}" data-value="${v}" aria-pressed="${v===d?'true':'false'}">${v}</button>`).join('')}</div>`; }
  _autoFrom(a,c){ const tri=['anima','neo','nexus']; const s=new Set([a,c]); return tri.find(x=>!s.has(x))||tri[0]; }
  _getSegValue(root, seg){ return root.querySelector(`[data-seg="${seg}"] .button-tab.active`)?.getAttribute('data-value') || ''; }
  _html(s){ return String(s ?? '').replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m])); }

  _autoSelectMediator(root) {
    try {
      if (this._touched?.mediator) return;
      const attacker   = this._getSegValue(root, 'attacker');
      const challenger = this._getSegValue(root, 'challenger');
      if (!attacker || !challenger) return;
      const mediator = (attacker==='neo' && challenger==='nexus') ? 'anima' : this._autoFrom(attacker, challenger);
      const seg = root.querySelector('[data-seg="mediator"]'); if (!seg) return;
      seg.querySelectorAll('.button-tab[data-value]').forEach(btn => {
        const val = btn.getAttribute('data-value');
        const is = (val === mediator);
        btn.classList.toggle('active', is);
        btn.setAttribute('aria-pressed', is ? 'true' : 'false');
      });
    } catch (e) { console.warn('[DebateUI] _autoSelectMediator():', e); }
  }
}
