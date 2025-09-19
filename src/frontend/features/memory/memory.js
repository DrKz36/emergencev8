import { MemoryCenter } from './memory-center.js';
import { EVENTS } from '../../shared/constants.js';

export default class MemoryModule {
  constructor(eventBus, stateManager) {
    this.eventBus = eventBus;
    this.state = stateManager;
    this.memoryCenter = new MemoryCenter(eventBus, stateManager, { hostSelector: null });
    this.container = null;
    this._nodes = {};
    this._wired = false;
  }

  init() {
    if (this._wired) return;
    this._wired = true;
    this.eventBus.on?.('memory:center:state', () => this._handleStateChange());
    this.eventBus.on?.(EVENTS.MODULE_SHOW || 'module:show', (moduleId) => {
      if (moduleId === 'memory') this._handleStateChange();
    });
  }

  mount(container) {
    this.init();
    if (!container) return;
    this.container = container;
    container.innerHTML = this._template();
    this._cacheNodes();

    const host = container.querySelector('[data-memory-center-host]');
    this.memoryCenter.init(host);
    this.memoryCenter.refresh();

    this._syncStatus();
    this._bindActions();
  }

  _template() {
    return `
      <section class="memory-page card">
        <header class="memory-page__header">
          <div class="memory-page__legend">
            <h1 class="memory-page__title">Centre memoire</h1>
            <p class="memory-page__subtitle" data-memory-status></p>
          </div>
          <div class="memory-page__actions">
            <button type="button" class="button button-primary" data-memory-action="analyze">Analyser</button>
            <button type="button" class="button" data-memory-action="clear">Effacer</button>
          </div>
        </header>
        <section class="memory-page__summary">
          <article class="memory-stat-card" data-memory-stm-card>
            <span class="memory-stat-card__label">STM</span>
            <span class="memory-stat-card__value" data-memory-stm></span>
          </article>
          <article class="memory-stat-card">
            <span class="memory-stat-card__label">LTM</span>
            <span class="memory-stat-card__value" data-memory-ltm-count></span>
          </article>
          <article class="memory-stat-card">
            <span class="memory-stat-card__label">Derniere analyse</span>
            <span class="memory-stat-card__value" data-memory-last-analysis></span>
          </article>
        </section>
        <section class="memory-page__body" data-memory-center-host></section>
      </section>
    `;
  }

  _cacheNodes() {
    if (!this.container) return;
    this._nodes = {
      status: this.container.querySelector('[data-memory-status]'),
      stm: this.container.querySelector('[data-memory-stm]'),
      stmCard: this.container.querySelector('[data-memory-stm-card]'),
      ltm: this.container.querySelector('[data-memory-ltm-count]'),
      lastAnalysis: this.container.querySelector('[data-memory-last-analysis]'),
      analyzeBtn: this.container.querySelector('[data-memory-action="analyze"]'),
      clearBtn: this.container.querySelector('[data-memory-action="clear"]'),
    };
  }

  _bindActions() {
    const { analyzeBtn, clearBtn } = this._nodes;
    analyzeBtn?.addEventListener('click', () => {
      this.eventBus.emit?.('memory:tend', { force: true });
    });
    clearBtn?.addEventListener('click', () => {
      this.eventBus.emit?.('memory:clear');
    });
  }

  _handleStateChange() {
    if (!this.container) return;
    this.memoryCenter.refresh();
    this._syncStatus();
  }

  _syncStatus() {
    if (!this.container) return;
    const snapshot = this.memoryCenter.getSnapshot();
    const last = this.state?.get?.('chat.lastAnalysis');

    if (this._nodes.status) this._nodes.status.textContent = snapshot.hint;
    if (this._nodes.stm) this._nodes.stm.textContent = snapshot.stmActive ? 'Disponible' : 'Vide';
    if (this._nodes.stmCard) this._nodes.stmCard.classList.toggle('is-on', !!snapshot.stmActive);
    if (this._nodes.ltm) this._nodes.ltm.textContent = String(snapshot.ltmCount);
    if (this._nodes.lastAnalysis) this._nodes.lastAnalysis.textContent = this._formatLastAnalysis(last, snapshot.lastAnalysis);

    const isRunning = last?.status === 'running';
    if (this._nodes.analyzeBtn) {
      this._nodes.analyzeBtn.disabled = !!isRunning;
      this._nodes.analyzeBtn.textContent = isRunning ? 'Analyse...' : 'Analyser';
    }
  }

  _formatLastAnalysis(last, fallback) {
    if (!last) return fallback || 'Jamais';
    if (last.status === 'running') return 'Analyse en cours';
    if (last.status === 'error') return 'Echec';
    if (last.status === 'cleared') return 'Reinitialisee';
    if (last.status === 'skipped') return 'Aucune mise a jour';
    if (last.completedAt || last.finishedAt || last.at) {
      try {
        const date = new Date(last.completedAt || last.finishedAt || last.at);
        if (!Number.isNaN(date.getTime())) {
          return date.toLocaleString('fr-FR', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
          });
        }
      } catch (_) {}
    }
    return fallback || 'Jamais';
  }
}
