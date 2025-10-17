/**
 * @module components/tutorial/GlossaryModal
 * @description Modal interactif pour afficher les définitions du glossaire
 */

import { getGlossaryEntry, getAllGlossaryEntries, searchGlossary } from './GlossaryData.js';
import { TutorialIcons } from './TutorialIcons.js';

export class GlossaryModal {
  constructor() {
    this.isOpen = false;
    this.currentEntryId = null;
    this.modal = null;
    this.init();
  }

  init() {
    // Créer le modal au chargement
    this.createModal();

    // Gérer les clics sur les liens glossaire
    document.addEventListener('click', (e) => {
      if (e.target.classList.contains('glossary-link')) {
        e.preventDefault();
        const glossaryId = e.target.dataset.glossary;
        if (glossaryId) {
          this.show(glossaryId);
        }
      }
    });

    // Fermer avec Escape
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && this.isOpen) {
        this.close();
      }
    });
  }

  createModal() {
    const modalHTML = `
      <div id="glossary-modal" class="glossary-modal" style="display: none;">
        <div class="glossary-modal-backdrop"></div>
        <div class="glossary-modal-container">
          <div class="glossary-modal-header">
            <div class="glossary-modal-title">
              <span class="glossary-modal-icon" id="glossary-modal-icon"></span>
              <h2 id="glossary-modal-term">Glossaire</h2>
            </div>
            <button class="glossary-modal-close" id="glossary-modal-close">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
              </svg>
            </button>
          </div>
          <div class="glossary-modal-content" id="glossary-modal-content">
            <!-- Le contenu sera injecté dynamiquement -->
          </div>
          <div class="glossary-modal-footer">
            <div class="glossary-modal-related" id="glossary-modal-related">
              <!-- Les termes liés seront affichés ici -->
            </div>
            <button class="btn-secondary" id="glossary-modal-show-all">
              ${TutorialIcons.book} Voir tout le glossaire
            </button>
          </div>
        </div>
      </div>
    `;

    // Injecter le modal dans le body
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = modalHTML;
    document.body.appendChild(tempDiv.firstElementChild);

    this.modal = document.getElementById('glossary-modal');

    // Attacher les événements
    this.attachEventListeners();

    // Injecter les styles
    this.injectStyles();
  }

  attachEventListeners() {
    // Fermer le modal
    const closeBtn = document.getElementById('glossary-modal-close');
    const backdrop = this.modal.querySelector('.glossary-modal-backdrop');

    closeBtn.addEventListener('click', () => this.close());
    backdrop.addEventListener('click', () => this.close());

    // Bouton "Voir tout le glossaire"
    const showAllBtn = document.getElementById('glossary-modal-show-all');
    showAllBtn.addEventListener('click', () => this.showAll());
  }

  show(entryId) {
    const entry = getGlossaryEntry(entryId);
    if (!entry) {
      console.error(`Glossary entry not found: ${entryId}`);
      return;
    }

    this.currentEntryId = entryId;
    this.renderEntry(entry);
    this.modal.style.display = 'block';
    this.isOpen = true;

    // Animation d'entrée
    setTimeout(() => {
      this.modal.querySelector('.glossary-modal-container').style.transform = 'scale(1)';
      this.modal.querySelector('.glossary-modal-container').style.opacity = '1';
    }, 10);
  }

  renderEntry(entry) {
    const iconEl = document.getElementById('glossary-modal-icon');
    const termEl = document.getElementById('glossary-modal-term');
    const contentEl = document.getElementById('glossary-modal-content');
    const relatedEl = document.getElementById('glossary-modal-related');

    iconEl.innerHTML = entry.icon;
    termEl.textContent = entry.term;

    // Construire le contenu
    let contentHTML = `
      <section class="glossary-section">
        <h3><span class="tutorial-icon">${TutorialIcons.info}</span> Définition</h3>
        <p>${entry.definition}</p>
      </section>
    `;

    if (entry.howItWorks) {
      contentHTML += `
        <section class="glossary-section">
          <h3><span class="tutorial-icon">${TutorialIcons.settings}</span> Comment ça fonctionne ?</h3>
          <div>${entry.howItWorks}</div>
        </section>
      `;
    }

    if (entry.examples) {
      contentHTML += `
        <section class="glossary-section">
          <h3><span class="tutorial-icon">${TutorialIcons.lightbulb}</span> Exemples</h3>
          <div>${entry.examples}</div>
        </section>
      `;
    }

    if (entry.inEmergence) {
      contentHTML += `
        <section class="glossary-section">
          <h3><span class="tutorial-icon">${TutorialIcons.zap}</span> Dans ÉMERGENCE</h3>
          <div>${entry.inEmergence}</div>
        </section>
      `;
    }

    if (entry.analogy) {
      contentHTML += `
        <section class="glossary-section glossary-analogy">
          <h3><span class="tutorial-icon">${TutorialIcons.lightbulb}</span> Analogie</h3>
          <p>${entry.analogy}</p>
        </section>
      `;
    }

    if (entry.why) {
      contentHTML += `
        <section class="glossary-section">
          <h3><span class="tutorial-icon">${TutorialIcons.target}</span> Pourquoi c'est important</h3>
          <p>${entry.why}</p>
        </section>
      `;
    }

    if (entry.advantages) {
      contentHTML += `
        <section class="glossary-section">
          <h3><span class="tutorial-icon">${TutorialIcons.checkCircle}</span> Avantages</h3>
          <div>${entry.advantages}</div>
        </section>
      `;
    }

    if (entry.limits || entry.howToAvoid) {
      contentHTML += `
        <section class="glossary-section">
          <h3><span class="tutorial-icon">${TutorialIcons.alertCircle}</span> ${entry.limits ? 'Limites' : 'Comment éviter'}</h3>
          <div>${entry.limits || entry.howToAvoid}</div>
        </section>
      `;
    }

    contentEl.innerHTML = contentHTML;

    // Afficher les termes liés
    if (entry.relatedTerms && entry.relatedTerms.length > 0) {
      const relatedHTML = `
        <h4><span class="tutorial-icon">${TutorialIcons.link}</span> Termes liés</h4>
        <div class="glossary-related-terms">
          ${entry.relatedTerms.map(relatedId => {
            const relatedEntry = getGlossaryEntry(relatedId);
            if (!relatedEntry) return '';
            return `
              <a href="#glossaire-${relatedId}"
                 class="glossary-link glossary-tag"
                 data-glossary="${relatedId}">
                ${relatedEntry.term}
              </a>
            `;
          }).join('')}
        </div>
      `;
      relatedEl.innerHTML = relatedHTML;
    } else {
      relatedEl.innerHTML = '';
    }
  }

  showAll() {
    const contentEl = document.getElementById('glossary-modal-content');
    const termEl = document.getElementById('glossary-modal-term');
    const iconEl = document.getElementById('glossary-modal-icon');
    const relatedEl = document.getElementById('glossary-modal-related');

    termEl.textContent = 'Glossaire Complet IA - ÉMERGENCE';
    iconEl.innerHTML = TutorialIcons.book;
    relatedEl.innerHTML = '';

    const allEntries = getAllGlossaryEntries();

    let contentHTML = `
      <p class="glossary-intro">Votre dictionnaire de l'intelligence artificielle. Ce glossaire explique les termes clés utilisés dans ÉMERGENCE et le monde de l'IA conversationnelle.</p>
      <div class="glossary-all-entries">
    `;

    allEntries.forEach(entry => {
      contentHTML += `
        <div class="glossary-entry-card">
          <h3>
            <span class="tutorial-icon">${entry.icon}</span>
            <a href="#glossaire-${entry.id}" class="glossary-link" data-glossary="${entry.id}">
              ${entry.term}
            </a>
          </h3>
          <p>${entry.definition}</p>
        </div>
      `;
    });

    contentHTML += '</div>';
    contentEl.innerHTML = contentHTML;

    this.currentEntryId = null;
  }

  close() {
    const container = this.modal.querySelector('.glossary-modal-container');
    container.style.transform = 'scale(0.95)';
    container.style.opacity = '0';

    setTimeout(() => {
      this.modal.style.display = 'none';
      this.isOpen = false;
    }, 200);
  }

  injectStyles() {
    if (document.getElementById('glossary-modal-styles')) return;

    const styles = `
      <style id="glossary-modal-styles">
        .glossary-modal {
          position: fixed;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          z-index: 10000;
        }

        .glossary-modal-backdrop {
          position: absolute;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          background: rgba(0, 0, 0, 0.7);
          backdrop-filter: blur(4px);
        }

        .glossary-modal-container {
          position: relative;
          max-width: 800px;
          max-height: 85vh;
          margin: 5vh auto;
          background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
          border-radius: 16px;
          box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
          display: flex;
          flex-direction: column;
          overflow: hidden;
          transform: scale(0.95);
          opacity: 0;
          transition: all 0.2s ease;
        }

        .glossary-modal-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 1.5rem 2rem;
          background: rgba(255, 255, 255, 0.05);
          border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }

        .glossary-modal-title {
          display: flex;
          align-items: center;
          gap: 1rem;
        }

        .glossary-modal-icon {
          width: 32px;
          height: 32px;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .glossary-modal-icon svg {
          width: 32px;
          height: 32px;
          stroke: #60a5fa;
        }

        .glossary-modal-title h2 {
          margin: 0;
          font-size: 1.5rem;
          font-weight: 600;
          color: #fff;
        }

        .glossary-modal-close {
          background: none;
          border: none;
          cursor: pointer;
          width: 40px;
          height: 40px;
          display: flex;
          align-items: center;
          justify-content: center;
          border-radius: 8px;
          transition: all 0.2s ease;
        }

        .glossary-modal-close svg {
          width: 20px;
          height: 20px;
          stroke: rgba(255, 255, 255, 0.7);
        }

        .glossary-modal-close:hover {
          background: rgba(255, 255, 255, 0.1);
        }

        .glossary-modal-close:hover svg {
          stroke: #fff;
        }

        .glossary-modal-content {
          flex: 1;
          padding: 2rem;
          overflow-y: auto;
          color: rgba(255, 255, 255, 0.9);
          line-height: 1.7;
        }

        .glossary-modal-content::-webkit-scrollbar {
          width: 8px;
        }

        .glossary-modal-content::-webkit-scrollbar-track {
          background: rgba(255, 255, 255, 0.05);
        }

        .glossary-modal-content::-webkit-scrollbar-thumb {
          background: rgba(255, 255, 255, 0.2);
          border-radius: 4px;
        }

        .glossary-section {
          margin-bottom: 2rem;
        }

        .glossary-section h3 {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          font-size: 1.1rem;
          font-weight: 600;
          color: #60a5fa;
          margin-bottom: 0.75rem;
        }

        .glossary-section .tutorial-icon svg {
          width: 20px;
          height: 20px;
          stroke: #60a5fa;
        }

        .glossary-section p {
          margin: 0.5rem 0;
        }

        .glossary-section ul, .glossary-section ol {
          margin: 0.5rem 0;
          padding-left: 1.5rem;
        }

        .glossary-section li {
          margin: 0.3rem 0;
        }

        .glossary-analogy {
          background: rgba(96, 165, 250, 0.1);
          border-left: 3px solid #60a5fa;
          padding: 1rem 1.5rem;
          border-radius: 8px;
        }

        .glossary-modal-footer {
          padding: 1.5rem 2rem;
          background: rgba(255, 255, 255, 0.05);
          border-top: 1px solid rgba(255, 255, 255, 0.1);
        }

        .glossary-modal-related h4 {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          font-size: 0.9rem;
          font-weight: 600;
          color: rgba(255, 255, 255, 0.7);
          margin-bottom: 0.75rem;
        }

        .glossary-modal-related .tutorial-icon svg {
          width: 16px;
          height: 16px;
          stroke: rgba(255, 255, 255, 0.7);
        }

        .glossary-related-terms {
          display: flex;
          flex-wrap: wrap;
          gap: 0.5rem;
          margin-bottom: 1rem;
        }

        .glossary-tag {
          display: inline-flex;
          align-items: center;
          padding: 0.4rem 0.8rem;
          background: rgba(96, 165, 250, 0.2);
          color: #60a5fa;
          border-radius: 6px;
          font-size: 0.85rem;
          text-decoration: none;
          transition: all 0.2s ease;
          border: 1px solid rgba(96, 165, 250, 0.3);
        }

        .glossary-tag:hover {
          background: rgba(96, 165, 250, 0.3);
          border-color: #60a5fa;
          transform: translateY(-1px);
        }

        .glossary-link {
          color: #60a5fa;
          text-decoration: none;
          border-bottom: 1px dashed rgba(96, 165, 250, 0.5);
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .glossary-link:hover {
          color: #93c5fd;
          border-bottom-color: #93c5fd;
        }

        .btn-secondary {
          display: inline-flex;
          align-items: center;
          gap: 0.5rem;
          padding: 0.75rem 1.5rem;
          background: rgba(96, 165, 250, 0.1);
          color: #60a5fa;
          border: 1px solid rgba(96, 165, 250, 0.3);
          border-radius: 8px;
          font-size: 0.9rem;
          font-weight: 500;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .btn-secondary svg {
          width: 18px;
          height: 18px;
          stroke: currentColor;
          fill: none;
        }

        .btn-secondary:hover {
          background: rgba(96, 165, 250, 0.2);
          border-color: #60a5fa;
          transform: translateY(-1px);
        }

        .glossary-intro {
          font-size: 1rem;
          color: rgba(255, 255, 255, 0.8);
          margin-bottom: 1.5rem;
          padding: 1rem;
          background: rgba(96, 165, 250, 0.1);
          border-radius: 8px;
          border-left: 3px solid #60a5fa;
        }

        .glossary-all-entries {
          display: grid;
          gap: 1rem;
        }

        .glossary-entry-card {
          background: rgba(255, 255, 255, 0.05);
          padding: 1.5rem;
          border-radius: 12px;
          border: 1px solid rgba(255, 255, 255, 0.1);
          transition: all 0.2s ease;
        }

        .glossary-entry-card:hover {
          background: rgba(255, 255, 255, 0.08);
          border-color: rgba(96, 165, 250, 0.3);
          transform: translateX(4px);
        }

        .glossary-entry-card h3 {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          margin: 0 0 0.75rem 0;
          font-size: 1.1rem;
          color: #fff;
        }

        .glossary-entry-card h3 .tutorial-icon svg {
          width: 24px;
          height: 24px;
          stroke: #60a5fa;
        }

        .glossary-entry-card p {
          margin: 0;
          color: rgba(255, 255, 255, 0.7);
          line-height: 1.6;
        }
      </style>
    `;

    document.head.insertAdjacentHTML('beforeend', styles);
  }
}

// Initialiser le modal glossaire au chargement
let glossaryModalInstance = null;

export function initGlossaryModal() {
  if (!glossaryModalInstance) {
    glossaryModalInstance = new GlossaryModal();
  }
  return glossaryModalInstance;
}
