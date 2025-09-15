/**
 * src/frontend/features/debate/debate-ui.js
 * V42 — FIX: implémentation _autoSelectMediator + guards + binding propre.
 * - Auto-médiateur déterministe: {attacker,challenger} -> le 3e agent disponible.
 * - Règle spéciale: si attacker='neo' ET challenger='nexus' => mediator='anima'.
 * - Sélecteurs d’onglets robustes (active toggling + touched-state).
 * - Pas d’impact sur le reste de l’API (events émis, DOM structure conservée).
 */

import { EVENTS, AGENTS } from '../../shared/constants.js';
import { marked } from 'https://cdn.jsdelivr.net/npm/marked/lib/marked.esm.js';

export class DebateUI {
  constructor(eventBus) {
    this.eventBus = eventBus;
    this._touched = { attacker:false, challenger:false, mediator:false, rounds:false };
    console.log('✅ DebateUI V42 prêt.');
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
                <button type="button"
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
        </div>
      </div>`;
  }

  _bindCreateEvents(root) {
    // Titre live
    const topicEl = root.querySelector('#debate-topic');
    const headerTopic = root.querySelector('.debate-topic');
    const syncTopic = () => { headerTopic.textContent = topicEl.value.trim() || '—'; };
    topicEl?.addEventListener('input', syncTopic);

    // Toggle RAG
    root.querySelector('#rag-power')?.addEventListener('click', (e) => {
      const btn = e.currentTarget;
      const on  = btn.getAttribute('aria-checked') === 'true';
      btn.setAttribute('aria-checked', on ? 'false' : 'true');
      root.querySelector('#rag-label')?.classList.toggle('muted', !on);
    });

    // Tabs Agents / Rounds
    this._bindTabs(root, 'attacker');
    this._bindTabs(root, 'challenger');
    this._bindTabs(root, 'mediator');
    this._bindTabs(root, 'rounds');

    // Auto-médiateur initial (au cas où)
    this._autoSelectMediator(root);

    // Raccrocher l’auto-médiateur si Attacker/Challenger changent
    root.querySelector('[data-seg="attacker"]')?.addEventListener('click', () => this._autoSelectMediator(root));
    root.querySelector('[data-seg="challenger"]')?.addEventListener('click', () => this._autoSelectMediator(root));

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

      // Règle spéciale: Neo + Nexus => Médiateur Anima
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

  /**
   * Auto-sélection du médiateur en fonction d’Attacker/Challenger, sauf si l’utilisateur a déjà choisi.
   * - Si l’utilisateur n’a pas touché au segment 'mediator', on calcule le 3e agent disponible.
   * - Règle spéciale: attacker='neo' && challenger='nexus' => mediator='anima'.
   * - Met à jour l’onglet actif dans le segment 'mediator'.
   */
  _autoSelectMediator(root) {
    try {
      if (this._touched?.mediator) return; // l’utilisateur a choisi manuellement => ne pas écraser

      const attacker   = this._getSegValue(root, 'attacker');
      const challenger = this._getSegValue(root, 'challenger');

      if (!attacker || !challenger) return;

      // Règle spéciale prioritaire
      let mediator = (attacker === 'neo' && challenger === 'nexus') ? 'anima' : this._autoFrom(attacker, challenger);

      const seg = root.querySelector('[data-seg="mediator"]');
      if (!seg) return;

      // Activer le bon bouton si présent
      const btns = seg.querySelectorAll('.button-tab[data-value]');
      let found = false;
      btns.forEach(btn => {
        const val = btn.getAttribute('data-value');
        const is = (val === mediator);
        btn.classList.toggle('active', is);
        btn.setAttribute('aria-pressed', is ? 'true' : 'false');
        if (is) found = true;
      });

      // Si l’agent médiateur n’existait pas (ne devrait pas arriver), on n’écrase rien
      if (!found) return;

      // Ne pas marquer "touched" — on laisse la possibilité à l’utilisateur de cliquer ensuite
    } catch (e) {
      console.warn('[DebateUI] _autoSelectMediator():', e);
    }
  }

  /* ---------------------------- Vue Timeline (flux continu) ---------------------------- */

  _renderTimelineView(state) {
    const topic = (state?.topic || '').trim();
    const header = `
      <div class="card-header timeline-header">
        <div class="title-center">
          <div class="debate-title">Sujet du Débat</div>
          <div class="debate-topic">${this._html(topic || '—')}</div>
        </div>
        <div class="debate-status">${this._html(state?.statusText ?? '')}</div>
      </div>`;

    const turns = Array.isArray(state?.turns) ? state.turns : [];
    const body = `
      <div class="card-body">
        <div class="chat-messages">
          ${turns.map(t => {
            const agentId = t.agent || 'anima';
            const name = AGENTS?.[agentId]?.name || agentId;
            const text = marked.parse(t.text || '');
            return `
              <div class="message assistant ${this._html(agentId)}">
                <div class="message-content">
                  <div class="message-meta meta-inside"><strong class="sender-name">${this._html(name)}</strong></div>
                  <div class="message-text">${text}</div>
                </div>
              </div>`;
          }).join('')}
        </div>
      </div>`;

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
          ${body}
          ${synthesis}
          ${footer}
        </div>
      </div>`;
  }

  _bindTimelineEvents(root, state) {
    root.querySelector('#debate-export')?.addEventListener('click', () => {
      const topic = (state?.topic || '').trim();
      const lines = [];
      lines.push(`# Débat — ${topic || 'Sans titre'}`);
      (state?.turns || []).forEach(t => {
        const agentId = t.agent || 'anima';
        const name = AGENTS?.[agentId]?.name || agentId;
        lines.push(`\n## ${name}\n\n${t.text || ''}`);
      });
      if (state?.synthesis) {
        lines.push(`\n---\n\n### Synthèse (${AGENTS?.[state.config?.agentOrder?.slice(-1)[0]]?.name || 'Nexus'})\n\n${state.synthesis}`);
      }
      const blob = new Blob([lines.join('\n')], { type: 'text/markdown;charset=utf-8' });
      const url  = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = `debate_${Date.now()}.md`;
      a.click();
      URL.revokeObjectURL(url);
    });

    root.querySelector('#debate-new')?.addEventListener('click', () => {
      this.eventBus.emit('debate:new');
    });
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

  _defaultFor(role){
    // Valeurs par défaut simples, arbitraires mais stables
    if (role === 'attacker')   return 'neo';
    if (role === 'challenger') return 'nexus';
    if (role === 'mediator')   return 'anima';
    return 'anima';
  }

  _segAgents(role, def='anima') {
    const agents = ['anima','neo','nexus'];
    const buttons = agents.map(a => {
      const label = AGENTS?.[a]?.name || a;
      const is = a === def;
      return `<button type="button" class="button-tab ${is?'active':''}" data-value="${a}" aria-pressed="${is?'true':'false'}">${this._html(label)}</button>`;
    }).join('');
    return `<div class="tabs-container" data-seg="${this._html(role)}">${buttons}</div>`;
  }

  _segRounds(d=3){
    return `<div class="tabs-container rounds-tabs" data-seg="rounds">
      ${[1,2,3,4,5].map(v => `<button type="button" class="button-tab ${v===d?'active':''}" data-value="${v}" aria-pressed="${v===d?'true':'false'}">${v}</button>`).join('')}
    </div>`;
  }

  _autoFrom(a,c){
    const tri = ['anima','neo','nexus'];
    const s = new Set([a,c]);
    return tri.find(x => !s.has(x)) || tri[0];
  }

  _getSegValue(root, seg){
    return root.querySelector(`[data-seg="${seg}"] .button-tab.active`)?.getAttribute('data-value') || '';
    }

  _html(s){
    return String(s ?? '').replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
  }
}
