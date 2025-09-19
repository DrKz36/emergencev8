// src/frontend/features/memory/memory-center.js
// MemoryCenter placeholder with basic UI rendering for overlay (ASCII friendly).

export class MemoryCenter {
  constructor(eventBus, stateManager, options = {}) {
    this.eventBus = eventBus || null;
    this.stateManager = stateManager || null;
    this._initialized = false;
    this.hostSelector = options.hostSelector === undefined ? '#memory-panel-host' : options.hostSelector;
    this.host = options.host || null;
    this._bound = false;
    this._handleClick = null;
  }

  init(hostOverride) {
    if (hostOverride) this.setHost(hostOverride);
    if (!this.host) {
      if (this.hostSelector && typeof document !== 'undefined') {
        try {
          this.host = document.querySelector(this.hostSelector);
        } catch (_) {
          this.host = null;
        }
      }
    }
    if (!this.host) return;
    if (!this._initialized) {
      this._render();
      this._bind();
      this._initialized = true;
    } else {
      this.refresh();
    }
  }

  open() {
    if (!this._initialized) this.init();
    this.refresh();
    try {
      const handle = typeof window !== 'undefined' ? window.__EMERGENCE_MEMORY__ : null;
      if (handle && typeof handle.open === 'function') {
        handle.open();
      } else if (typeof document !== 'undefined') {
        document.body.classList.add('brain-panel-open');
      }
    } catch (_) {
      try { document.body?.classList.add('brain-panel-open'); } catch (_) {}
    }
    this.eventBus?.emit?.('memory:center:ui:opened');
  }

  refresh() {
    if (!this.host) {
      if (this.hostSelector && typeof document !== 'undefined') {
        try {
          this.host = document.querySelector(this.hostSelector);
        } catch (_) {
          this.host = null;
        }
      }
      if (!this.host) return;
    }
    if (!this._initialized) {
      this._render();
      this._bind();
      this._initialized = true;
      return;
    }
    this._render();
  }

  setHost(hostElement) {
    if (hostElement === this.host) return;
    if (this._bound && this.host && this._handleClick) {
      try { this.host.removeEventListener('click', this._handleClick); } catch (_) {}
      this._bound = false;
    }
    this.host = hostElement || null;
    if (this.host && this._initialized) {
      this._render();
      this._bind();
    }
  }

  hydrate() {}

  getSnapshot() {
    return this._buildSnapshot();
  }

  _bind() {
    if (!this.host || this._bound) return;
    const handler = (event) => {
      const btn = event.target.closest('[data-memory-export]');
      if (!btn) return;
      const format = (btn.dataset.memoryExport || '').toLowerCase();
      if (!format) return;
      this.eventBus?.emit?.('memory:export', { format });
    };
    this.host.addEventListener('click', handler);
    this._handleClick = handler;
    this._bound = true;
  }

  _render() {
    if (!this.host) return;
    const snapshot = this._buildSnapshot();
    this.host.innerHTML = `
      <div class="memory-panel">
        <section class="memory-section">
          <header class="memory-section__header">
            <h3 class="memory-section__title">Synthese</h3>
            <span class="memory-section__badge ${snapshot.stmActive ? 'is-on' : ''}">
              ${snapshot.stmActive ? 'STM active' : 'STM vide'}
            </span>
          </header>
          <ul class="memory-metrics">
            <li><strong>STM</strong> ${snapshot.stmActive ? 'Disponible' : 'Aucun resume'}</li>
            <li><strong>LTM</strong> ${snapshot.ltmCount} elements</li>
            <li><strong>Derniere analyse</strong> ${snapshot.lastAnalysis}</li>
          </ul>
          <p class="memory-section__hint">${snapshot.hint}</p>
        </section>
        <section class="memory-section">
          <h3 class="memory-section__title">Exports</h3>
          <div class="memory-actions">
            <button type="button" class="memory-action" data-memory-export="json">Exporter JSON</button>
            <button type="button" class="memory-action" data-memory-export="csv">Exporter CSV</button>
          </div>
        </section>
      </div>
    `;
  }

  _buildSnapshot() {
    const stats = this.stateManager?.get?.('chat.memoryStats') || {};
    const lastAnalysis = this.stateManager?.get?.('chat.lastAnalysis') || {};
    const stmActive = !!stats.has_stm;
    const ltmCount = Number.isFinite(stats.ltm_items) ? Number(stats.ltm_items) : 0;
    const lastLabel = this._formatAnalysis(lastAnalysis);
    let hint = 'Aucune memoire persistee pour le moment. Active le RAG pour nourrir les agents.';
    if (stmActive || ltmCount > 0) {
      hint = 'Memoire prete. Les resumes et faits clefs sont disponibles pour les agents.';
    }
    if (lastAnalysis?.status === 'running') {
      hint = 'Analyse en cours... Tu peux poursuivre la discussion, la consolidation tourne en arriere-plan.';
    }
    return {
      stmActive,
      ltmCount,
      lastAnalysis: lastLabel,
      hint
    };
  }

  _formatAnalysis(last) {
    if (!last || typeof last !== 'object') return 'Jamais';
    if (last.status === 'running') return 'Analyse en cours';
    if (last.status === 'error') return 'Echec: ' + (last.error || 'inconnu');
    if (last.status === 'cleared') return 'Reinitialisee';
    const ts = last.completedAt || last.finishedAt || last.at;
    if (!ts) return last.status ? String(last.status) : 'Jamais';
    try {
      const date = new Date(ts);
      if (Number.isNaN(date.getTime())) return 'N/A';
      return date.toLocaleString('fr-FR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch (err) {
      return 'N/A';
    }
  }
}
