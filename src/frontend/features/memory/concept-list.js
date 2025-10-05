/**
 * @module features/memory/concept-list
 * @description Component for displaying a complete list of concepts with pagination
 */

const API_BASE = '/api/memory';

function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function formatDateTime(value) {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  const pad = (n) => String(n).padStart(2, '0');
  const day = pad(date.getDate());
  const month = pad(date.getMonth() + 1);
  const year = date.getFullYear();
  const hours = pad(date.getHours());
  const minutes = pad(date.getMinutes());
  return `${day}.${month}.${year} ${hours}:${minutes}`;
}

async function getAuthHeaders() {
  let token = null;
  try {
    token = sessionStorage.getItem('emergence.id_token') || localStorage.getItem('emergence.id_token');
  } catch (_) {}
  if (!token) {
    try {
      token = sessionStorage.getItem('id_token') || localStorage.getItem('id_token');
    } catch (_) {}
  }

  const headers = {
    'Content-Type': 'application/json',
  };

  const trimmed = typeof token === 'string' ? token.trim() : '';
  if (trimmed) {
    headers['Authorization'] = `Bearer ${trimmed}`;
  }

  return headers;
}

async function getAllConcepts(params = {}) {
  const headers = await getAuthHeaders();
  const searchParams = new URLSearchParams();
  if (params.limit) searchParams.set('limit', String(params.limit));
  if (params.offset) searchParams.set('offset', String(params.offset));
  if (params.sort) searchParams.set('sort', params.sort);

  const url = `${API_BASE}/concepts${searchParams.toString() ? '?' + searchParams : ''}`;

  const response = await fetch(url, {
    method: 'GET',
    headers,
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || `HTTP ${response.status}`);
  }

  return response.json();
}

export class ConceptList {
  constructor(eventBus, stateManager, options = {}) {
    this.eventBus = eventBus;
    this.state = stateManager;
    this.options = {
      hostId: typeof options.hostId === 'string' ? options.hostId : null,
      onEdit: typeof options.onEdit === 'function' ? options.onEdit : null,
    };
    this.hostElement = options.hostElement || null;

    this.container = null;
    this.listContainer = null;
    this.errorContainer = null;
    this.paginationContainer = null;

    this.concepts = [];
    this.isLoading = false;
    this.error = null;
    this.currentPage = 1;
    this.pageSize = 20;
    this.totalConcepts = 0;
    this.sortBy = 'recent'; // 'recent', 'frequent', 'alphabetical'

    this._initialized = false;

    // Listen for editor events
    if (this.eventBus) {
      const onUpdated = () => this.loadConcepts();
      this.eventBus.on?.('concepts:updated', onUpdated);
      this._unsubscribeUpdated = () => this.eventBus.off?.('concepts:updated', onUpdated);
    }
  }

  template() {
    return `
      <div class="concept-list__inner">
        <header class="concept-list__header">
          <h3 class="concept-list__title">Base de Connaissances</h3>
          <p class="concept-list__subtitle">Tous vos concepts mémorisés</p>
        </header>

        <div class="concept-list__toolbar">
          <div class="concept-list__actions">
            <button class="concept-list__action-btn" data-action="export-all" title="Exporter tous les concepts">
              💾 Exporter
            </button>
            <label class="concept-list__action-btn" title="Importer des concepts">
              📥 Importer
              <input type="file" accept=".json" data-role="import-file" hidden />
            </label>
          </div>
          <div class="concept-list__controls">
            <label for="concept-sort" class="concept-list__sort-label">Trier par :</label>
            <select id="concept-sort" class="concept-list__sort-select" data-role="concept-sort">
              <option value="recent">Plus récents</option>
              <option value="frequent">Plus fréquents</option>
              <option value="alphabetical">Alphabétique</option>
            </select>
          </div>
        </div>

        <div class="concept-list__body">
          <p class="concept-list__error" data-role="concept-error" hidden></p>
          <div class="concept-list__grid" data-role="concept-grid"></div>
          <div class="concept-list__pagination" data-role="concept-pagination"></div>
        </div>
      </div>
    `;
  }

  init() {
    this.ensureContainer();
    if (!this.container) return;

    this.bindEvents();
    this._initialized = true;
    this.loadConcepts();
  }

  destroy() {
    if (this._unsubscribeUpdated) {
      this._unsubscribeUpdated();
      this._unsubscribeUpdated = null;
    }
    this._initialized = false;
  }

  ensureContainer() {
    if (this.container) return;

    let host = this.hostElement;
    if (!host && this.options.hostId) {
      host = document.getElementById(this.options.hostId);
    }
    if (!host) return;

    host.classList.add('concept-list');
    host.innerHTML = this.template();

    this.container = host;
    this.listContainer = host.querySelector('[data-role="concept-grid"]');
    this.errorContainer = host.querySelector('[data-role="concept-error"]');
    this.paginationContainer = host.querySelector('[data-role="concept-pagination"]');
  }

  bindEvents() {
    const sortSelect = this.container?.querySelector('[data-role="concept-sort"]');
    if (sortSelect) {
      sortSelect.addEventListener('change', (e) => {
        this.sortBy = e.target.value;
        this.currentPage = 1;
        this.loadConcepts();
      });
      sortSelect.value = this.sortBy;
    }

    const exportBtn = this.container?.querySelector('[data-action="export-all"]');
    if (exportBtn) {
      exportBtn.addEventListener('click', () => this.exportConcepts());
    }

    const importInput = this.container?.querySelector('[data-role="import-file"]');
    if (importInput) {
      importInput.addEventListener('change', (e) => this.importConcepts(e));
    }
  }

  async loadConcepts() {
    if (!this.container) return;

    this.isLoading = true;
    this.error = null;
    this.render();

    try {
      const response = await getAllConcepts({
        limit: this.pageSize,
        offset: (this.currentPage - 1) * this.pageSize,
        sort: this.sortBy,
      });

      this.concepts = response.concepts || response.results || [];
      this.totalConcepts = response.total || this.concepts.length;
      this.error = null;
      this.eventBus?.emit?.('concepts:list:loaded', { concepts: this.concepts, total: this.totalConcepts });
    } catch (error) {
      this.error = error.message || 'Erreur lors du chargement des concepts';
      this.concepts = [];
      this.eventBus?.emit?.('concepts:list:error', { error });
    } finally {
      this.isLoading = false;
      this.render();
    }
  }

  render() {
    if (!this.container) return;

    this.renderError();
    this.renderList();
    this.renderPagination();
  }

  renderError() {
    if (!this.errorContainer) return;

    if (this.error) {
      this.errorContainer.textContent = this.error;
      this.errorContainer.hidden = false;
    } else {
      this.errorContainer.textContent = '';
      this.errorContainer.hidden = true;
    }
  }

  renderList() {
    if (!this.listContainer) return;

    if (this.isLoading) {
      this.listContainer.innerHTML = '<p class="concept-list__status">Chargement...</p>';
      return;
    }

    if (!this.concepts.length) {
      this.listContainer.innerHTML = '<p class="concept-list__status">Aucun concept trouvé</p>';
      return;
    }

    const cardsHtml = this.concepts.map((concept) => {
      const text = escapeHtml(concept.concept_text || 'Concept');
      const count = concept.occurrence_count || 0;
      const firstMentioned = formatDateTime(concept.first_mentioned);
      const lastMentioned = formatDateTime(concept.last_mentioned);
      const threads = Array.isArray(concept.thread_ids) ? concept.thread_ids : [];
      const threadsCount = threads.length;

      return `
        <div class="concept-card" data-concept-id="${escapeHtml(concept.id || concept.concept_id || '')}">
          <h4 class="concept-card__title">${text}</h4>
          <div class="concept-card__meta">
            <span class="concept-card__stat">
              <span class="concept-card__stat-icon">🔁</span>
              <span class="concept-card__stat-value">${count}</span>
              <span class="concept-card__stat-label">occurrence${count > 1 ? 's' : ''}</span>
            </span>
            <span class="concept-card__stat">
              <span class="concept-card__stat-icon">💬</span>
              <span class="concept-card__stat-value">${threadsCount}</span>
              <span class="concept-card__stat-label">conversation${threadsCount > 1 ? 's' : ''}</span>
            </span>
          </div>
          ${firstMentioned ? `<p class="concept-card__date"><strong>Première mention :</strong> ${escapeHtml(firstMentioned)}</p>` : ''}
          ${lastMentioned ? `<p class="concept-card__date"><strong>Dernière mention :</strong> ${escapeHtml(lastMentioned)}</p>` : ''}
          <div class="concept-card__actions">
            <button class="concept-card__action" data-action="edit" data-concept-id="${escapeHtml(concept.id || concept.concept_id || '')}">✏️ Éditer</button>
            <button class="concept-card__action" data-action="delete" data-concept-id="${escapeHtml(concept.id || concept.concept_id || '')}">🗑️ Supprimer</button>
          </div>
        </div>
      `;
    }).join('');

    this.listContainer.innerHTML = cardsHtml;

    // Bind action buttons
    this.listContainer.querySelectorAll('[data-action]').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        const action = e.target.dataset.action;
        const conceptId = e.target.dataset.conceptId;
        if (action === 'edit') {
          if (this.options.onEdit) {
            this.options.onEdit(conceptId);
          } else {
            this.eventBus?.emit?.('concepts:edit:requested', { conceptId });
          }
        } else if (action === 'delete') {
          this.deleteConcept(conceptId);
        }
      });
    });
  }

  renderPagination() {
    if (!this.paginationContainer) return;

    const totalPages = Math.ceil(this.totalConcepts / this.pageSize);
    if (totalPages <= 1) {
      this.paginationContainer.innerHTML = '';
      return;
    }

    const prevDisabled = this.currentPage <= 1;
    const nextDisabled = this.currentPage >= totalPages;

    this.paginationContainer.innerHTML = `
      <div class="concept-pagination">
        <button
          class="concept-pagination__btn"
          data-action="prev-page"
          ${prevDisabled ? 'disabled' : ''}
        >← Précédent</button>
        <span class="concept-pagination__info">Page ${this.currentPage} / ${totalPages}</span>
        <button
          class="concept-pagination__btn"
          data-action="next-page"
          ${nextDisabled ? 'disabled' : ''}
        >Suivant →</button>
      </div>
    `;

    // Bind pagination buttons
    const prevBtn = this.paginationContainer.querySelector('[data-action="prev-page"]');
    const nextBtn = this.paginationContainer.querySelector('[data-action="next-page"]');

    if (prevBtn) {
      prevBtn.addEventListener('click', () => {
        if (this.currentPage > 1) {
          this.currentPage--;
          this.loadConcepts();
        }
      });
    }

    if (nextBtn) {
      nextBtn.addEventListener('click', () => {
        if (this.currentPage < totalPages) {
          this.currentPage++;
          this.loadConcepts();
        }
      });
    }
  }

  async deleteConcept(conceptId) {
    if (!conceptId) return;
    if (!confirm('Êtes-vous sûr de vouloir supprimer ce concept ?')) return;

    try {
      const headers = await getAuthHeaders();
      const response = await fetch(`${API_BASE}/concepts/${conceptId}`, {
        method: 'DELETE',
        headers,
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      this.eventBus?.emit?.('concepts:deleted', { conceptId });
      this.loadConcepts();
    } catch (error) {
      this.error = 'Erreur lors de la suppression';
      this.render();
    }
  }

  async exportConcepts() {
    try {
      const headers = await getAuthHeaders();
      const response = await fetch(`${API_BASE}/concepts/export`, {
        method: 'GET',
        headers,
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `concepts-export-${Date.now()}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

      this.eventBus?.emit?.('notification:show', {
        type: 'success',
        message: 'Concepts exportés avec succès',
      });
    } catch (error) {
      this.eventBus?.emit?.('notification:show', {
        type: 'error',
        message: 'Erreur lors de l\'export',
      });
    }
  }

  async importConcepts(event) {
    const file = event.target?.files?.[0];
    if (!file) return;

    try {
      const text = await file.text();
      const data = JSON.parse(text);

      const headers = await getAuthHeaders();
      const response = await fetch(`${API_BASE}/concepts/import`, {
        method: 'POST',
        headers,
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const result = await response.json();
      const imported = result.imported || result.count || 0;

      this.eventBus?.emit?.('notification:show', {
        type: 'success',
        message: `${imported} concept(s) importé(s)`,
      });

      this.loadConcepts();
    } catch (error) {
      this.eventBus?.emit?.('notification:show', {
        type: 'error',
        message: 'Erreur lors de l\'import: ' + (error.message || 'Format invalide'),
      });
    } finally {
      // Reset file input
      event.target.value = '';
    }
  }
}
