/**
 * @module features/memory/ConceptSplitModal
 * @description Modal for splitting a concept into multiple concepts
 * V1.0.0 - P1.3 Implementation
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

async function getConcept(conceptId) {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_BASE}/concepts/${conceptId}`, {
    method: 'GET',
    headers,
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  return response.json();
}

async function splitConcept(sourceId, newConcepts) {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_BASE}/concepts/split`, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      source_id: sourceId,
      new_concepts: newConcepts,
    }),
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  return response.json();
}

export class ConceptSplitModal {
  constructor(eventBus, stateManager) {
    this.eventBus = eventBus;
    this.state = stateManager;

    this.modal = null;
    this.conceptId = null;
    this.concept = null;
    this.newConcepts = [
      { concept_text: '', description: '', tags: [], weight: 0.5 },
      { concept_text: '', description: '', tags: [], weight: 0.5 },
    ];
    this.isLoading = false;
    this.isSplitting = false;

    this._boundCloseHandler = this.close.bind(this);
    this._boundKeyHandler = this.handleKeyDown.bind(this);
  }

  async open(conceptId) {
    this.conceptId = conceptId;
    this.isLoading = true;

    try {
      this.concept = await getConcept(conceptId);
    } catch (error) {
      this.eventBus?.emit?.('notification:show', {
        type: 'error',
        message: 'Impossible de charger le concept: ' + error.message,
      });
      return;
    } finally {
      this.isLoading = false;
    }

    this.render();
    this.bindEvents();
  }

  close() {
    if (this.modal) {
      this.modal.remove();
      this.modal = null;
    }
    document.removeEventListener('keydown', this._boundKeyHandler);
    this.eventBus?.emit?.('concepts:split:closed');
  }

  render() {
    // Remove existing modal if any
    const existingModal = document.querySelector('.concept-split-modal');
    if (existingModal) {
      existingModal.remove();
    }

    const modal = document.createElement('div');
    modal.className = 'concept-split-modal';

    modal.innerHTML = `
      <div class="concept-split-modal__backdrop" data-action="close"></div>
      <div class="concept-split-modal__content">
        <header class="concept-split-modal__header">
          <h3 class="concept-split-modal__title">✂️ Diviser un Concept</h3>
          <button class="concept-split-modal__close" data-action="close" aria-label="Fermer">✕</button>
        </header>

        <div class="concept-split-modal__body">
          ${this.isLoading ? '<p class="concept-split-modal__loading">Chargement...</p>' : this.renderForm()}
        </div>

        <footer class="concept-split-modal__footer">
          <button class="concept-split-modal__btn concept-split-modal__btn--secondary" data-action="close">Annuler</button>
          <button class="concept-split-modal__btn concept-split-modal__btn--primary" data-action="split" ${this.isSplitting ? 'disabled' : ''}>
            ${this.isSplitting ? 'Division en cours...' : 'Diviser'}
          </button>
        </footer>
      </div>
    `;

    document.body.appendChild(modal);
    this.modal = modal;
  }

  renderForm() {
    const conceptText = escapeHtml(this.concept?.concept_text || '');
    const occurrences = this.concept?.occurrence_count || 0;

    const newConceptsHtml = this.newConcepts.map((newConcept, index) => {
      const estimatedOccurrences = Math.round(occurrences * newConcept.weight);

      return `
        <div class="split-concept-card" data-index="${index}">
          <div class="split-concept-card__header">
            <h4 class="split-concept-card__number">Nouveau Concept ${index + 1}</h4>
            <button type="button" class="split-concept-card__remove" data-action="remove-concept" data-index="${index}" ${this.newConcepts.length <= 2 ? 'disabled' : ''}>✕</button>
          </div>

          <div class="split-concept-card__field">
            <label class="split-concept-card__label">Texte du concept *</label>
            <input
              type="text"
              class="split-concept-card__input"
              data-role="concept-text"
              data-index="${index}"
              value="${escapeHtml(newConcept.concept_text)}"
              placeholder="Ex: ${conceptText} (aspect 1)"
              required
            />
          </div>

          <div class="split-concept-card__field">
            <label class="split-concept-card__label">Description</label>
            <textarea
              class="split-concept-card__textarea"
              data-role="description"
              data-index="${index}"
              placeholder="Description du nouveau concept..."
              rows="2"
            >${escapeHtml(newConcept.description)}</textarea>
          </div>

          <div class="split-concept-card__field">
            <label class="split-concept-card__label">
              Poids (${Math.round(newConcept.weight * 100)}% = ~${estimatedOccurrences} occurrences)
            </label>
            <input
              type="range"
              class="split-concept-card__slider"
              data-role="weight"
              data-index="${index}"
              min="0"
              max="1"
              step="0.05"
              value="${newConcept.weight}"
            />
          </div>

          <div class="split-concept-card__field">
            <label class="split-concept-card__label">Tags (séparés par des virgules)</label>
            <input
              type="text"
              class="split-concept-card__input"
              data-role="tags"
              data-index="${index}"
              value="${(newConcept.tags || []).join(', ')}"
              placeholder="tag1, tag2, tag3"
            />
          </div>
        </div>
      `;
    }).join('');

    const totalWeight = this.newConcepts.reduce((sum, c) => sum + c.weight, 0);
    const weightWarning = Math.abs(totalWeight - 1.0) > 0.01;

    return `
      <div class="concept-split-form">
        <div class="concept-split-form__source">
          <h4 class="concept-split-form__source-title">Concept source :</h4>
          <p class="concept-split-form__source-text">${conceptText}</p>
          <p class="concept-split-form__source-meta">
            🔁 ${occurrences} occurrences · 💬 ${(this.concept?.thread_ids || []).length} conversations
          </p>
        </div>

        <p class="concept-split-form__hint">
          Divisez ce concept en plusieurs concepts distincts. Le concept source sera supprimé et remplacé par les nouveaux concepts.
        </p>

        <div class="split-concepts-list">
          ${newConceptsHtml}
        </div>

        <div class="concept-split-form__actions">
          <button type="button" class="concept-split-form__add-btn" data-action="add-concept">
            + Ajouter un concept
          </button>
        </div>

        <div class="concept-split-form__summary ${weightWarning ? 'concept-split-form__summary--warning' : ''}">
          <h4 class="concept-split-form__summary-title">Résumé :</h4>
          <ul class="concept-split-form__summary-list">
            <li>📊 Poids total : <strong>${Math.round(totalWeight * 100)}%</strong> ${weightWarning ? '⚠️ (doit être 100%)' : '✅'}</li>
            <li>📝 <strong>${this.newConcepts.length}</strong> nouveau(x) concept(s) créé(s)</li>
            <li>🗑️ Le concept source sera supprimé</li>
          </ul>
        </div>
      </div>
    `;
  }

  bindEvents() {
    if (!this.modal) return;

    // Close handlers
    this.modal.querySelectorAll('[data-action="close"]').forEach((btn) => {
      btn.addEventListener('click', this._boundCloseHandler);
    });

    // Split handler
    const splitBtn = this.modal.querySelector('[data-action="split"]');
    if (splitBtn) {
      splitBtn.addEventListener('click', () => this.executeSplit());
    }

    // Add concept button
    const addBtn = this.modal.querySelector('[data-action="add-concept"]');
    if (addBtn) {
      addBtn.addEventListener('click', () => this.addNewConcept());
    }

    // Remove concept buttons
    this.modal.querySelectorAll('[data-action="remove-concept"]').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        const index = parseInt(e.target.dataset.index, 10);
        this.removeConcept(index);
      });
    });

    // Input handlers
    this.modal.querySelectorAll('[data-role="concept-text"]').forEach((input) => {
      input.addEventListener('input', (e) => {
        const index = parseInt(e.target.dataset.index, 10);
        this.newConcepts[index].concept_text = e.target.value;
      });
    });

    this.modal.querySelectorAll('[data-role="description"]').forEach((textarea) => {
      textarea.addEventListener('input', (e) => {
        const index = parseInt(e.target.dataset.index, 10);
        this.newConcepts[index].description = e.target.value;
      });
    });

    this.modal.querySelectorAll('[data-role="weight"]').forEach((slider) => {
      slider.addEventListener('input', (e) => {
        const index = parseInt(e.target.dataset.index, 10);
        this.newConcepts[index].weight = parseFloat(e.target.value);
        this.updateFormOnly();
      });
    });

    this.modal.querySelectorAll('[data-role="tags"]').forEach((input) => {
      input.addEventListener('input', (e) => {
        const index = parseInt(e.target.dataset.index, 10);
        const tags = e.target.value.split(',').map(t => t.trim()).filter(t => t);
        this.newConcepts[index].tags = tags;
      });
    });

    // Keyboard shortcuts
    document.addEventListener('keydown', this._boundKeyHandler);
  }

  handleKeyDown(e) {
    if (e.key === 'Escape') {
      this.close();
    }
  }

  addNewConcept() {
    const remainingWeight = Math.max(0, 1.0 - this.newConcepts.reduce((sum, c) => sum + c.weight, 0));
    this.newConcepts.push({
      concept_text: '',
      description: '',
      tags: [],
      weight: Math.max(0.1, remainingWeight),
    });
    this.updateFormOnly();
  }

  removeConcept(index) {
    if (this.newConcepts.length <= 2) return; // Au moins 2 concepts requis
    this.newConcepts.splice(index, 1);
    this.updateFormOnly();
  }

  updateFormOnly() {
    const bodyEl = this.modal?.querySelector('.concept-split-modal__body');
    if (bodyEl) {
      bodyEl.innerHTML = this.renderForm();
      this.bindEvents();
    }
  }

  async executeSplit() {
    if (this.isSplitting) return;

    // Validate
    const totalWeight = this.newConcepts.reduce((sum, c) => sum + c.weight, 0);
    if (Math.abs(totalWeight - 1.0) > 0.01) {
      this.eventBus?.emit?.('notification:show', {
        type: 'error',
        message: 'Les poids doivent totaliser 100%',
      });
      return;
    }

    const emptyTexts = this.newConcepts.filter(c => !c.concept_text.trim());
    if (emptyTexts.length > 0) {
      this.eventBus?.emit?.('notification:show', {
        type: 'error',
        message: 'Tous les concepts doivent avoir un texte',
      });
      return;
    }

    this.isSplitting = true;
    this.render();
    this.bindEvents();

    try {
      const result = await splitConcept(this.conceptId, this.newConcepts);

      this.eventBus?.emit?.('notification:show', {
        type: 'success',
        message: `Concept divisé en ${result.split_count} nouveau(x) concept(s)`,
      });

      this.eventBus?.emit?.('concepts:split', {
        sourceId: result.source_id,
        newIds: result.new_ids,
        splitCount: result.split_count,
      });

      this.close();
    } catch (error) {
      this.eventBus?.emit?.('notification:show', {
        type: 'error',
        message: 'Erreur lors de la division: ' + error.message,
      });
      this.isSplitting = false;
      this.render();
      this.bindEvents();
    }
  }
}
