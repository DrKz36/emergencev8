/**
 * @module features/memory/ConceptMergeModal
 * @description Modal for merging multiple concepts into one
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

async function getConcepts(conceptIds) {
  const headers = await getAuthHeaders();
  const promises = conceptIds.map(id =>
    fetch(`${API_BASE}/concepts/${id}`, {
      method: 'GET',
      headers,
    }).then(res => res.ok ? res.json() : null)
  );

  const results = await Promise.all(promises);
  return results.filter(c => c !== null);
}

async function mergeConcepts(sourceIds, targetId, newConceptText) {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_BASE}/concepts/merge`, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      source_ids: sourceIds,
      target_id: targetId,
      new_concept_text: newConceptText || undefined,
    }),
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  return response.json();
}

export class ConceptMergeModal {
  constructor(eventBus, stateManager) {
    this.eventBus = eventBus;
    this.state = stateManager;

    this.modal = null;
    this.conceptIds = [];
    this.concepts = [];
    this.targetId = null;
    this.isLoading = false;
    this.isMerging = false;

    this._boundCloseHandler = this.close.bind(this);
    this._boundKeyHandler = this.handleKeyDown.bind(this);
  }

  async open(conceptIds) {
    if (!conceptIds || conceptIds.length < 2) {
      this.eventBus?.emit?.('notification:show', {
        type: 'error',
        message: 'Au moins 2 concepts requis pour fusionner',
      });
      return;
    }

    this.conceptIds = conceptIds;
    this.targetId = conceptIds[0]; // Default: premier concept comme cible
    this.isLoading = true;

    try {
      this.concepts = await getConcepts(conceptIds);
      if (this.concepts.length < 2) {
        throw new Error('Impossible de charger tous les concepts');
      }
    } catch (error) {
      this.eventBus?.emit?.('notification:show', {
        type: 'error',
        message: 'Impossible de charger les concepts: ' + error.message,
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
    this.eventBus?.emit?.('concepts:merge:closed');
  }

  render() {
    // Remove existing modal if any
    const existingModal = document.querySelector('.concept-merge-modal');
    if (existingModal) {
      existingModal.remove();
    }

    const modal = document.createElement('div');
    modal.className = 'concept-merge-modal';

    modal.innerHTML = `
      <div class="concept-merge-modal__backdrop" data-action="close"></div>
      <div class="concept-merge-modal__content">
        <header class="concept-merge-modal__header">
          <h3 class="concept-merge-modal__title">🔗 Fusionner des Concepts</h3>
          <button class="concept-merge-modal__close" data-action="close" aria-label="Fermer">✕</button>
        </header>

        <div class="concept-merge-modal__body">
          ${this.isLoading ? '<p class="concept-merge-modal__loading">Chargement...</p>' : this.renderForm()}
        </div>

        <footer class="concept-merge-modal__footer">
          <button class="concept-merge-modal__btn concept-merge-modal__btn--secondary" data-action="close">Annuler</button>
          <button class="concept-merge-modal__btn concept-merge-modal__btn--primary" data-action="merge" ${this.isMerging ? 'disabled' : ''}>
            ${this.isMerging ? 'Fusion en cours...' : 'Fusionner'}
          </button>
        </footer>
      </div>
    `;

    document.body.appendChild(modal);
    this.modal = modal;
  }

  renderForm() {
    const conceptsHtml = this.concepts.map((concept, index) => {
      const conceptId = concept.id || concept.concept_id;
      const isTarget = conceptId === this.targetId;

      return `
        <div class="merge-concept-card ${isTarget ? 'merge-concept-card--target' : ''}" data-concept-id="${escapeHtml(conceptId)}">
          <div class="merge-concept-card__header">
            <input
              type="radio"
              name="target-concept"
              value="${escapeHtml(conceptId)}"
              data-role="target-selector"
              ${isTarget ? 'checked' : ''}
            />
            <label class="merge-concept-card__label">
              ${isTarget ? '🎯 Concept cible' : `📌 Concept ${index + 1}`}
            </label>
          </div>
          <h4 class="merge-concept-card__title">${escapeHtml(concept.concept_text)}</h4>
          <div class="merge-concept-card__meta">
            <span>🔁 ${concept.occurrence_count || 0} occurrences</span>
            <span>💬 ${(concept.thread_ids || []).length} conversations</span>
            ${concept.tags && concept.tags.length > 0 ? `
              <div class="merge-concept-card__tags">
                ${concept.tags.map(tag => `<span class="tag">${escapeHtml(tag)}</span>`).join('')}
              </div>
            ` : ''}
          </div>
        </div>
      `;
    }).join('');

    const totalOccurrences = this.concepts.reduce((sum, c) => sum + (c.occurrence_count || 0), 0);
    const allTags = new Set();
    this.concepts.forEach(c => {
      (c.tags || []).forEach(tag => allTags.add(tag));
    });

    return `
      <div class="concept-merge-form">
        <p class="concept-merge-form__hint">
          Sélectionnez le concept qui recevra les données fusionnées. Les autres concepts seront supprimés.
        </p>

        <div class="merge-concepts-list">
          ${conceptsHtml}
        </div>

        <div class="concept-merge-form__field">
          <label class="concept-merge-form__label" for="merged-concept-text">
            Texte du concept fusionné (optionnel)
          </label>
          <input
            type="text"
            id="merged-concept-text"
            class="concept-merge-form__input"
            data-role="new-concept-text"
            placeholder="Laissez vide pour garder le texte du concept cible"
          />
          <p class="concept-merge-form__hint-small">
            Si renseigné, le concept fusionné aura ce nouveau texte
          </p>
        </div>

        <div class="concept-merge-form__summary">
          <h4 class="concept-merge-form__summary-title">Résumé de la fusion :</h4>
          <ul class="concept-merge-form__summary-list">
            <li>📊 <strong>${totalOccurrences}</strong> occurrences totales</li>
            <li>🏷️ <strong>${allTags.size}</strong> tags uniques</li>
            <li>📝 <strong>${this.concepts.length - 1}</strong> concept(s) seront supprimés</li>
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

    // Merge handler
    const mergeBtn = this.modal.querySelector('[data-action="merge"]');
    if (mergeBtn) {
      mergeBtn.addEventListener('click', () => this.executeMerge());
    }

    // Target selector
    this.modal.querySelectorAll('[data-role="target-selector"]').forEach((radio) => {
      radio.addEventListener('change', (e) => {
        this.targetId = e.target.value;
        this.render();
        this.bindEvents();
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

  async executeMerge() {
    if (this.isMerging) return;

    const newConceptTextInput = this.modal?.querySelector('[data-role="new-concept-text"]');
    const newConceptText = newConceptTextInput?.value?.trim() || null;

    // Prepare source IDs (all except target)
    const sourceIds = this.conceptIds.filter(id => id !== this.targetId);

    if (sourceIds.length === 0) {
      this.eventBus?.emit?.('notification:show', {
        type: 'error',
        message: 'Aucun concept source à fusionner',
      });
      return;
    }

    this.isMerging = true;
    this.render();
    this.bindEvents();

    try {
      const result = await mergeConcepts(sourceIds, this.targetId, newConceptText);

      this.eventBus?.emit?.('notification:show', {
        type: 'success',
        message: `${result.merged_count} concept(s) fusionné(s) avec succès`,
      });

      this.eventBus?.emit?.('concepts:merged', {
        targetId: result.target_id,
        mergedCount: result.merged_count,
        totalOccurrences: result.total_occurrences,
      });

      this.close();
    } catch (error) {
      this.eventBus?.emit?.('notification:show', {
        type: 'error',
        message: 'Erreur lors de la fusion: ' + error.message,
      });
      this.isMerging = false;
      this.render();
      this.bindEvents();
    }
  }
}
