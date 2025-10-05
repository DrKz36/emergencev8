/**
 * @module features/memory/concept-editor
 * @description Modal editor for editing concept details, tags, and relations
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

async function updateConcept(conceptId, updates) {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_BASE}/concepts/${conceptId}`, {
    method: 'PATCH',
    headers,
    body: JSON.stringify(updates),
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  return response.json();
}

export class ConceptEditor {
  constructor(eventBus, stateManager) {
    this.eventBus = eventBus;
    this.state = stateManager;

    this.modal = null;
    this.conceptId = null;
    this.concept = null;
    this.tags = [];
    this.relations = [];
    this.isLoading = false;
    this.isSaving = false;

    this._boundCloseHandler = this.close.bind(this);
    this._boundKeyHandler = this.handleKeyDown.bind(this);
  }

  async open(conceptId) {
    this.conceptId = conceptId;
    this.isLoading = true;

    try {
      this.concept = await getConcept(conceptId);
      this.tags = Array.isArray(this.concept.tags) ? [...this.concept.tags] : [];
      this.relations = Array.isArray(this.concept.relations) ? [...this.concept.relations] : [];
    } catch (error) {
      this.eventBus?.emit?.('notification:show', {
        type: 'error',
        message: 'Impossible de charger le concept',
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
    this.eventBus?.emit?.('concepts:editor:closed');
  }

  render() {
    // Remove existing modal if any
    const existingModal = document.querySelector('.concept-editor-modal');
    if (existingModal) {
      existingModal.remove();
    }

    const modal = document.createElement('div');
    modal.className = 'concept-editor-modal';

    const conceptText = escapeHtml(this.concept?.concept_text || 'Concept');
    const description = escapeHtml(this.concept?.description || '');

    modal.innerHTML = `
      <div class="concept-editor-modal__backdrop" data-action="close"></div>
      <div class="concept-editor-modal__content">
        <header class="concept-editor-modal__header">
          <h3 class="concept-editor-modal__title">Éditer le Concept</h3>
          <button class="concept-editor-modal__close" data-action="close" aria-label="Fermer">✕</button>
        </header>

        <div class="concept-editor-modal__body">
          ${this.isLoading ? '<p class="concept-editor-modal__loading">Chargement...</p>' : this.renderForm()}
        </div>

        <footer class="concept-editor-modal__footer">
          <button class="concept-editor-modal__btn concept-editor-modal__btn--secondary" data-action="close">Annuler</button>
          <button class="concept-editor-modal__btn concept-editor-modal__btn--primary" data-action="save" ${this.isSaving ? 'disabled' : ''}>
            ${this.isSaving ? 'Enregistrement...' : 'Enregistrer'}
          </button>
        </footer>
      </div>
    `;

    document.body.appendChild(modal);
    this.modal = modal;
  }

  renderForm() {
    const conceptText = escapeHtml(this.concept?.concept_text || 'Concept');
    const description = this.concept?.description || '';

    const tagsHtml = this.tags.map((tag, index) => `
      <span class="concept-tag" data-index="${index}">
        ${escapeHtml(tag)}
        <button class="concept-tag__remove" data-action="remove-tag" data-index="${index}" aria-label="Retirer ${escapeHtml(tag)}">✕</button>
      </span>
    `).join('');

    const relationsHtml = this.relations.map((relation, index) => `
      <div class="concept-relation" data-index="${index}">
        <span class="concept-relation__text">${escapeHtml(relation.concept || relation.related_concept || 'Concept lié')}</span>
        <span class="concept-relation__type">${escapeHtml(relation.type || 'lié à')}</span>
        <button class="concept-relation__remove" data-action="remove-relation" data-index="${index}" aria-label="Retirer">✕</button>
      </div>
    `).join('');

    return `
      <div class="concept-editor-form">
        <div class="concept-editor-field">
          <label class="concept-editor-label">Concept</label>
          <input
            type="text"
            class="concept-editor-input"
            value="${conceptText}"
            readonly
            disabled
          />
          <p class="concept-editor-hint">Le texte du concept ne peut pas être modifié</p>
        </div>

        <div class="concept-editor-field">
          <label class="concept-editor-label" for="concept-description">Description</label>
          <textarea
            id="concept-description"
            class="concept-editor-textarea"
            data-role="description"
            placeholder="Ajoutez une description pour ce concept..."
            rows="4"
          >${description}</textarea>
        </div>

        <div class="concept-editor-field">
          <label class="concept-editor-label">Tags</label>
          <div class="concept-tags-list">
            ${tagsHtml}
          </div>
          <div class="concept-editor-add">
            <input
              type="text"
              class="concept-editor-input concept-editor-input--small"
              data-role="new-tag"
              placeholder="Nouveau tag..."
            />
            <button class="concept-editor-add-btn" data-action="add-tag">+ Ajouter</button>
          </div>
        </div>

        <div class="concept-editor-field">
          <label class="concept-editor-label">Relations</label>
          <div class="concept-relations-list">
            ${relationsHtml || '<p class="concept-editor-empty">Aucune relation définie</p>'}
          </div>
          <div class="concept-editor-add-relation">
            <input
              type="text"
              class="concept-editor-input concept-editor-input--small"
              data-role="new-relation-concept"
              placeholder="Concept lié..."
            />
            <select class="concept-editor-select" data-role="new-relation-type">
              <option value="related">lié à</option>
              <option value="parent">parent de</option>
              <option value="child">enfant de</option>
              <option value="similar">similaire à</option>
              <option value="opposite">opposé à</option>
            </select>
            <button class="concept-editor-add-btn" data-action="add-relation">+ Ajouter</button>
          </div>
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

    // Save handler
    const saveBtn = this.modal.querySelector('[data-action="save"]');
    if (saveBtn) {
      saveBtn.addEventListener('click', () => this.save());
    }

    // Tag management
    const addTagBtn = this.modal.querySelector('[data-action="add-tag"]');
    if (addTagBtn) {
      addTagBtn.addEventListener('click', () => this.addTag());
    }

    this.modal.querySelectorAll('[data-action="remove-tag"]').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        const index = parseInt(e.target.dataset.index, 10);
        this.removeTag(index);
      });
    });

    // Relation management
    const addRelationBtn = this.modal.querySelector('[data-action="add-relation"]');
    if (addRelationBtn) {
      addRelationBtn.addEventListener('click', () => this.addRelation());
    }

    this.modal.querySelectorAll('[data-action="remove-relation"]').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        const index = parseInt(e.target.dataset.index, 10);
        this.removeRelation(index);
      });
    });

    // Keyboard shortcuts
    document.addEventListener('keydown', this._boundKeyHandler);
  }

  handleKeyDown(e) {
    if (e.key === 'Escape') {
      this.close();
    } else if ((e.ctrlKey || e.metaKey) && e.key === 's') {
      e.preventDefault();
      this.save();
    }
  }

  addTag() {
    const input = this.modal?.querySelector('[data-role="new-tag"]');
    if (!input) return;

    const tagValue = input.value.trim();
    if (!tagValue) return;

    if (this.tags.includes(tagValue)) {
      this.eventBus?.emit?.('notification:show', {
        type: 'warning',
        message: 'Ce tag existe déjà',
      });
      return;
    }

    this.tags.push(tagValue);
    input.value = '';
    this.updateFormOnly();
  }

  removeTag(index) {
    if (index >= 0 && index < this.tags.length) {
      this.tags.splice(index, 1);
      this.updateFormOnly();
    }
  }

  addRelation() {
    const conceptInput = this.modal?.querySelector('[data-role="new-relation-concept"]');
    const typeSelect = this.modal?.querySelector('[data-role="new-relation-type"]');

    if (!conceptInput || !typeSelect) return;

    const conceptValue = conceptInput.value.trim();
    const typeValue = typeSelect.value;

    if (!conceptValue) return;

    this.relations.push({
      concept: conceptValue,
      type: typeValue,
    });

    conceptInput.value = '';
    typeSelect.selectedIndex = 0;
    this.updateFormOnly();
  }

  removeRelation(index) {
    if (index >= 0 && index < this.relations.length) {
      this.relations.splice(index, 1);
      this.updateFormOnly();
    }
  }

  updateFormOnly() {
    // Re-render only the form part to avoid losing focus
    const bodyEl = this.modal?.querySelector('.concept-editor-modal__body');
    if (bodyEl) {
      bodyEl.innerHTML = this.renderForm();
      this.bindEvents();
    }
  }

  async save() {
    if (this.isSaving) return;

    const descriptionEl = this.modal?.querySelector('[data-role="description"]');
    const description = descriptionEl?.value || '';

    this.isSaving = true;
    this.render();

    try {
      await updateConcept(this.conceptId, {
        description,
        tags: this.tags,
        relations: this.relations,
      });

      this.eventBus?.emit?.('notification:show', {
        type: 'success',
        message: 'Concept mis à jour',
      });

      this.eventBus?.emit?.('concepts:updated', {
        conceptId: this.conceptId,
        description,
        tags: this.tags,
        relations: this.relations,
      });

      this.close();
    } catch (error) {
      this.eventBus?.emit?.('notification:show', {
        type: 'error',
        message: 'Erreur lors de la sauvegarde',
      });
      this.isSaving = false;
      this.render();
    }
  }
}
