/**
 * @module features/memory/concept-search
 * @description Component for searching concepts in user's memory
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

async function searchConcepts(query, limit = 10) {
  const headers = await getAuthHeaders();
  const params = new URLSearchParams({ q: query, limit: String(limit) });
  const url = `${API_BASE}/concepts/search?${params}`;

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

export class ConceptSearch {
  constructor(eventBus, stateManager, options = {}) {
    this.eventBus = eventBus;
    this.state = stateManager;
    this.options = {
      hostId: typeof options.hostId === 'string' ? options.hostId : null,
    };
    this.hostElement = options.hostElement || null;

    this.container = null;
    this.searchInput = null;
    this.resultsContainer = null;
    this.errorContainer = null;

    this.searchQuery = '';
    this.results = [];
    this.isSearching = false;
    this.error = null;
    this.searchTimeout = null;

    this._initialized = false;
    this._onSearchInput = this.handleSearchInput.bind(this);
  }

  template() {
    return `
      <div class="concept-search__inner">
        <header class="concept-search__header">
          <h3 class="concept-search__title">Recherche de Concepts</h3>
          <p class="concept-search__subtitle">Recherchez dans votre base de connaissances</p>
        </header>
        <div class="concept-search__search">
          <input
            type="search"
            class="concept-search__input"
            data-role="concept-search-input"
            placeholder="Rechercher un concept (min. 3 caractères)..."
            aria-label="Rechercher des concepts"
          />
        </div>
        <div class="concept-search__body">
          <p class="concept-search__error" data-role="concept-error" hidden></p>
          <div class="concept-search__results" data-role="concept-results"></div>
        </div>
      </div>
    `;
  }

  init() {
    this.ensureContainer();
    if (!this.container) return;

    if (this.searchInput && !this.searchInput.hasAttribute('data-listener-attached')) {
      this.searchInput.addEventListener('input', this._onSearchInput);
      this.searchInput.setAttribute('data-listener-attached', 'true');
    }

    this._initialized = true;
    this.render();
  }

  destroy() {
    if (this.searchInput) {
      this.searchInput.removeEventListener('input', this._onSearchInput);
    }
    if (this.searchTimeout) {
      clearTimeout(this.searchTimeout);
      this.searchTimeout = null;
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

    if (!host.querySelector('[data-role="concept-search-input"]')) {
      host.classList.add('concept-search');
      host.innerHTML = this.template();
    } else {
      host.classList.add('concept-search');
    }

    this.container = host;
    this.searchInput = host.querySelector('[data-role="concept-search-input"]');
    this.resultsContainer = host.querySelector('[data-role="concept-results"]');
    this.errorContainer = host.querySelector('[data-role="concept-error"]');
  }

  handleSearchInput(event) {
    this.searchQuery = event.target.value.trim();

    // Clear previous timeout
    if (this.searchTimeout) {
      clearTimeout(this.searchTimeout);
    }

    // Require at least 3 characters
    if (this.searchQuery.length < 3) {
      this.results = [];
      this.error = null;
      this.render();
      return;
    }

    // Debounce search
    this.searchTimeout = setTimeout(() => {
      this.performSearch();
    }, 500);
  }

  async performSearch() {
    if (this.searchQuery.length < 3) return;

    this.isSearching = true;
    this.error = null;
    this.render();

    try {
      const response = await searchConcepts(this.searchQuery, 20);
      this.results = response.results || [];
      this.error = null;
      this.eventBus?.emit?.('concepts:search:success', { query: this.searchQuery, results: this.results });
    } catch (error) {
      this.error = error.message || 'Erreur lors de la recherche';
      this.results = [];
      this.eventBus?.emit?.('concepts:search:error', { query: this.searchQuery, error });
    } finally {
      this.isSearching = false;
      this.render();
    }
  }

  render() {
    if (!this.container) return;

    this.renderError();
    this.renderResults();
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

  renderResults() {
    if (!this.resultsContainer) return;

    if (this.isSearching) {
      this.resultsContainer.innerHTML = '<p class="concept-search__status">Recherche en cours...</p>';
      return;
    }

    if (!this.searchQuery || this.searchQuery.length < 3) {
      this.resultsContainer.innerHTML = '<p class="concept-search__status">Entrez au moins 3 caractères pour rechercher</p>';
      return;
    }

    if (!this.results.length) {
      this.resultsContainer.innerHTML = '<p class="concept-search__status">Aucun concept trouvé pour votre recherche</p>';
      return;
    }

    const resultsHtml = this.results.map((concept) => {
      const text = escapeHtml(concept.concept_text || 'Concept');
      const count = concept.occurrence_count || 0;
      const firstMentioned = formatDateTime(concept.first_mentioned);
      const lastMentioned = formatDateTime(concept.last_mentioned);
      const threads = Array.isArray(concept.thread_ids) ? concept.thread_ids : [];
      const threadsCount = threads.length;

      return `
        <div class="concept-search__result">
          <h4 class="concept-search__result-title">${text}</h4>
          <div class="concept-search__result-meta">
            <span class="concept-search__result-count">${count} occurrence${count > 1 ? 's' : ''}</span>
            <span class="concept-search__result-threads">${threadsCount} conversation${threadsCount > 1 ? 's' : ''}</span>
          </div>
          ${firstMentioned ? `<p class="concept-search__result-date">Première mention : ${escapeHtml(firstMentioned)}</p>` : ''}
          ${lastMentioned ? `<p class="concept-search__result-date">Dernière mention : ${escapeHtml(lastMentioned)}</p>` : ''}
        </div>
      `;
    }).join('');

    this.resultsContainer.innerHTML = `
      <div class="concept-search__results-list">
        ${resultsHtml}
      </div>
    `;
  }
}
