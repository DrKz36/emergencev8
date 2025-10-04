// src/frontend/features/memory/memory-center.js
// MemoryCenter with history panel + API integration (ASCII friendly).

import { api } from '../../shared/api-client.js';

const HISTORY_LIMIT = 20;
const DEFAULT_HISTORY_INTERVAL = 15000;

const dateFormatter = typeof Intl !== 'undefined'
  ? new Intl.DateTimeFormat('fr-FR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  : null;

function safeText(value) {
  if (value === undefined || value === null) return '';
  return String(value);
}

function normalizeSummary(text, maxLen = 220) {
  const safe = safeText(text).replace(/\s+/g, ' ').trim();
  if (!safe) return 'Résumé indisponible';
  if (safe.length <= maxLen) return safe;
  return `${safe.slice(0, maxLen - 1)}…`;
}

function formatTimestamp(value) {
  if (!value) return '—';
  try {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return safeText(value);
    return dateFormatter ? dateFormatter.format(date) : date.toISOString();
  } catch (_) {
    return safeText(value);
  }
}

export class MemoryCenter {
  constructor(eventBus, stateManager, options = {}) {
    this.eventBus = eventBus || null;
    this.stateManager = stateManager || null;
    this._initialized = false;
    this.hostSelector = options.hostSelector === undefined ? '#memory-panel-host' : options.hostSelector;
    this.host = options.host || null;
    this._bound = false;
    this._handleClick = null;

    this._history = [];
    this._historyError = null;
    this._historyLoading = false;
    this._historyToken = null;
    this._lastFetchAt = 0;
    this._historyInterval = Math.max(options.historyRefreshInterval ?? DEFAULT_HISTORY_INTERVAL, 1000);
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
      this._fetchHistory(true);
    } else {
      this.refresh(true);
    }
  }

  open() {
    if (!this._initialized) this.init();
    this.refresh(false);
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

  refresh(force = false) {
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
    this._render();
    this._fetchHistory(force);
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
      this._fetchHistory(true);
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

  _fetchHistory(force = false) {
    if (typeof api?.getMemoryHistory !== 'function') return;
    if (this._historyLoading && !force) return;
    const now = Date.now();
    if (!force && now - this._lastFetchAt < this._historyInterval) return;

    this._historyLoading = true;
    this._historyError = null;
    this._lastFetchAt = now;
    this._renderHistory();

    const token = Symbol('history');
    this._historyToken = token;
    Promise.resolve(api.getMemoryHistory({ limit: HISTORY_LIMIT }))
      .then((response) => {
        if (this._historyToken !== token) return;
        const summaries = Array.isArray(response?.summaries) ? response.summaries : [];
        this._history = summaries.map((item) => ({
          session_id: safeText(item?.session_id || item?.id || ''),
          updated_at: item?.updated_at || item?.created_at || null,
          summary: safeText(item?.summary || ''),
          concept_count: Number(item?.concept_count) || 0,
          entity_count: Number(item?.entity_count) || 0,
        }));
        this._historyError = null;
        if (this.stateManager?.set) {
          try { this.stateManager.set('memory.history', this._history); } catch (_) {}
        }
        this.eventBus?.emit?.('memory:center:history', { items: this._history });
      })
      .catch((error) => {
        if (this._historyToken !== token) return;
        this._historyError = error instanceof Error ? error : new Error('Chargement impossible');
      })
      .finally(() => {
        if (this._historyToken !== token) return;
        this._historyLoading = false;
        this._renderHistory();
        this._bindHistoryActions();
      });
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
        <section class="memory-section">
          <header class="memory-section__header">
            <h3 class="memory-section__title">Historique des consolidations</h3>
          </header>
          <div class="memory-history" data-memory-history></div>
        </section>
      </div>
    `;
    this._renderHistory();
    this._bindHistoryActions();
  }

  _renderHistory() {
    if (!this.host) return;
    const container = this.host.querySelector('[data-memory-history]');
    if (!container) return;

    container.innerHTML = '';

    if (this._historyLoading) {
      container.innerHTML = '<p class="memory-history__status">Chargement…</p>';
      return;
    }

    if (this._historyError) {
      container.innerHTML = `
        <div class="memory-history__error">
          <p>Impossible de charger l'historique.</p>
          <button type="button" class="memory-history__retry" data-memory-history-retry>Réessayer</button>
        </div>
      `;
      return;
    }

    if (!this._history.length) {
      container.innerHTML = '<p class="memory-history__status">Aucune consolidation enregistrée.</p>';
      return;
    }

    const list = document.createElement('ul');
    list.className = 'memory-history__list';

    this._history.forEach((entry) => {
      const item = document.createElement('li');
      item.className = 'memory-history__item';

      const meta = document.createElement('div');
      meta.className = 'memory-history__meta';

      const date = document.createElement('span');
      date.className = 'memory-history__time';
      date.textContent = formatTimestamp(entry.updated_at);
      meta.appendChild(date);

      const counts = document.createElement('span');
      counts.className = 'memory-history__counts';
      const stmBadge = entry.summary ? 'STM ✓' : 'STM —';
      counts.textContent = `${stmBadge} · Concepts ${entry.concept_count} · Entités ${entry.entity_count}`;
      meta.appendChild(counts);

      const summary = document.createElement('p');
      summary.className = 'memory-history__summary';
      summary.textContent = normalizeSummary(entry.summary);

      item.appendChild(meta);
      item.appendChild(summary);
      list.appendChild(item);
    });

    container.appendChild(list);
  }

  _bindHistoryActions() {
    if (!this.host) return;
    const retryBtn = this.host.querySelector('[data-memory-history-retry]');
    if (retryBtn) {
      retryBtn.addEventListener('click', (event) => {
        event.preventDefault();
        this._fetchHistory(true);
      }, { once: true });
    }
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
    const ts = last.completedAt || last.finishedAt || last.at || last.timestamp;
    if (!ts) return last.status ? String(last.status) : 'Jamais';
    try {
      const date = new Date(ts);
      if (Number.isNaN(date.getTime())) return 'N/A';
      return dateFormatter ? dateFormatter.format(date) : date.toISOString();
    } catch (err) {
      return 'N/A';
    }
  }
}
