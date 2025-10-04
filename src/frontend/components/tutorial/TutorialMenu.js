/**
 * @module components/tutorial/TutorialMenu
 * @description Menu de sélection et consultation des tutoriels
 */

import { TUTORIAL_GUIDES } from './tutorialGuides.js';

export class TutorialMenu {
  constructor(onStartInteractiveTutorial) {
    this.isOpen = false;
    this.container = null;
    this.onStartInteractiveTutorial = onStartInteractiveTutorial;
    this.currentGuide = null;
  }

  open() {
    this.isOpen = true;
    this.render();
  }

  close() {
    this.isOpen = false;
    if (this.container) {
      this.container.remove();
      this.container = null;
    }
  }

  render() {
    if (!this.isOpen) return;

    // Créer l'overlay
    this.container = document.createElement('div');
    this.container.className = 'tutorial-menu-overlay';

    // Backdrop
    const backdrop = document.createElement('div');
    backdrop.className = 'tutorial-menu-backdrop';
    backdrop.addEventListener('click', () => this.close());
    this.container.appendChild(backdrop);

    // Panneau principal
    const panel = document.createElement('div');
    panel.className = 'tutorial-menu-panel';

    // Header
    const header = document.createElement('div');
    header.className = 'tutorial-menu-header';
    header.innerHTML = `
      <div class="tutorial-menu-title">
        <svg class="tutorial-menu-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"></circle>
          <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path>
          <line x1="12" y1="17" x2="12.01" y2="17"></line>
        </svg>
        <h2>📚 Centre de Tutoriels</h2>
      </div>
      <button class="tutorial-menu-close" aria-label="Fermer">×</button>
    `;
    header.querySelector('.tutorial-menu-close').addEventListener('click', () => this.close());
    panel.appendChild(header);

    // Content
    const content = document.createElement('div');
    content.className = 'tutorial-menu-content';

    if (!this.currentGuide) {
      // Vue liste des tutoriels
      content.appendChild(this.renderList());
    } else {
      // Vue détail d'un tutoriel
      content.appendChild(this.renderGuide(this.currentGuide));
    }

    panel.appendChild(content);
    this.container.appendChild(panel);
    document.body.appendChild(this.container);
  }

  renderList() {
    const list = document.createElement('div');
    list.className = 'tutorial-menu-list';

    // Tutoriel interactif
    const interactiveCard = document.createElement('div');
    interactiveCard.className = 'tutorial-card tutorial-card-interactive';
    interactiveCard.innerHTML = `
      <div class="tutorial-card-icon">🎯</div>
      <div class="tutorial-card-content">
        <h3>Tutoriel Interactif</h3>
        <p>Découvrez les fonctionnalités d'Emergence avec un guide pas à pas interactif</p>
      </div>
      <button class="tutorial-card-btn">Lancer</button>
    `;
    interactiveCard.querySelector('.tutorial-card-btn').addEventListener('click', () => {
      this.close();
      if (this.onStartInteractiveTutorial) {
        this.onStartInteractiveTutorial();
      }
    });
    list.appendChild(interactiveCard);

    // Séparateur
    const separator = document.createElement('div');
    separator.className = 'tutorial-menu-separator';
    separator.innerHTML = '<span>Guides détaillés par fonctionnalité</span>';
    list.appendChild(separator);

    // Guides textuels
    TUTORIAL_GUIDES.forEach(guide => {
      const card = document.createElement('div');
      card.className = 'tutorial-card';
      card.innerHTML = `
        <div class="tutorial-card-icon">${guide.icon}</div>
        <div class="tutorial-card-content">
          <h3>${guide.title}</h3>
          <p>${guide.summary}</p>
        </div>
        <button class="tutorial-card-btn">Consulter</button>
      `;
      card.querySelector('.tutorial-card-btn').addEventListener('click', () => {
        this.currentGuide = guide;
        this.update();
      });
      list.appendChild(card);
    });

    return list;
  }

  renderGuide(guide) {
    const guideView = document.createElement('div');
    guideView.className = 'tutorial-guide-view';

    // Bouton retour
    const backBtn = document.createElement('button');
    backBtn.className = 'tutorial-guide-back';
    backBtn.innerHTML = '← Retour aux tutoriels';
    backBtn.addEventListener('click', () => {
      this.currentGuide = null;
      this.update();
    });
    guideView.appendChild(backBtn);

    // Header du guide
    const guideHeader = document.createElement('div');
    guideHeader.className = 'tutorial-guide-header';
    guideHeader.innerHTML = `
      <div class="tutorial-guide-icon">${guide.icon}</div>
      <h2>${guide.title}</h2>
      <p class="tutorial-guide-subtitle">${guide.summary}</p>
    `;
    guideView.appendChild(guideHeader);

    // Contenu du guide
    const guideContent = document.createElement('div');
    guideContent.className = 'tutorial-guide-content';
    guideContent.innerHTML = guide.content;
    guideView.appendChild(guideContent);

    return guideView;
  }

  update() {
    if (this.container) {
      this.container.remove();
    }
    this.render();
  }
}
