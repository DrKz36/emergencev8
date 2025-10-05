/**
 * @module components/tutorial/Tutorial
 * @description Système de tutoriel interactif pour la première connexion
 */

const TUTORIAL_STEPS = [
  {
    id: 'welcome',
    title: '🎯 Bienvenue sur Emergence',
    description: `<p><strong>Emergence</strong> est votre plateforme d'intelligence collective alimentée par l'IA.</p>
    <p>Ce tutoriel interactif vous guidera à travers les fonctionnalités principales pour vous aider à tirer le meilleur parti de l'application.</p>
    <p class="tutorial-tip">💡 <em>Astuce : Vous pourrez relancer ce tutoriel à tout moment depuis la barre latérale.</em></p>`,
    target: null,
    position: 'center'
  },
  {
    id: 'chat',
    title: '💬 Interface de Discussion',
    description: `<p><strong>Votre espace de conversation principal</strong> avec l'assistant IA multi-agents.</p>
    <ul class="tutorial-list">
      <li>🤖 <strong>3 agents spécialisés</strong> : Anima (créativité), Neo (analyse), Nexus (synthèse)</li>
      <li>🧠 <strong>Mémoire contextuelle</strong> : L'IA se souvient de vos échanges précédents</li>
      <li>📚 <strong>RAG activable</strong> : Recherche dans vos documents pour des réponses enrichies</li>
      <li>⚡ <strong>Streaming en temps réel</strong> : Voyez les réponses se construire instantanément</li>
    </ul>`,
    target: '.chat-container',
    position: 'left'
  },
  {
    id: 'input',
    title: '✍️ Zone de Saisie Intelligente',
    description: `<p><strong>Votre point d'entrée pour communiquer</strong> avec l'IA.</p>
    <ul class="tutorial-list">
      <li>📝 <strong>Questions complexes supportées</strong> : Posez des questions détaillées ou multi-parties</li>
      <li>🔄 <strong>Toggle RAG</strong> : Activez la recherche documentaire au besoin</li>
      <li>⌨️ <strong>Raccourcis clavier</strong> : Entrée pour envoyer, Maj+Entrée pour nouvelle ligne</li>
      <li>🎨 <strong>Markdown supporté</strong> : Formatez vos messages avec du markdown</li>
    </ul>`,
    target: '.chat-input-shell',
    position: 'top'
  },
  {
    id: 'sidebar-navigation',
    title: '📚 Navigation et Fonctionnalités',
    description: `<p><strong>Explorez toutes les fonctionnalités</strong> via la barre latérale.</p>
    <ul class="tutorial-list">
      <li>💬 <strong>Dialogue</strong> : Chat multi-agents principal</li>
      <li>📄 <strong>Documents</strong> : Gestion de vos fichiers et RAG</li>
      <li>💭 <strong>Débats</strong> : Organisez des débats multi-perspectives</li>
      <li>📊 <strong>Cockpit</strong> : Dashboard et métriques d'utilisation</li>
      <li>🧠 <strong>Mémoire</strong> : Base de connaissances et concepts</li>
      <li>📖 <strong>À propos</strong> : Documentation du projet</li>
      <li>❓ <strong>Tutoriel</strong> : Revoir ce guide à tout moment</li>
    </ul>`,
    target: '#app-sidebar',
    position: 'right'
  },
  {
    id: 'complete',
    title: '🚀 Vous êtes prêt à démarrer !',
    description: `<p><strong>Félicitations !</strong> Vous avez terminé le tutoriel d'introduction.</p>
    <p>Vous pouvez maintenant :</p>
    <ul class="tutorial-list">
      <li>💬 Commencer à discuter avec les agents IA</li>
      <li>📚 Uploader vos premiers documents</li>
      <li>🔍 Explorer les fonctionnalités avancées</li>
      <li>🎓 Relancer ce tutoriel depuis le menu "Tutoriel" dans la barre latérale</li>
    </ul>
    <p class="tutorial-tip">🌟 <em>N'hésitez pas à expérimenter, l'IA est là pour vous accompagner !</em></p>`,
    target: null,
    position: 'center'
  }
];

export class Tutorial {
  constructor() {
    this.currentStep = 0;
    this.isOpen = false;
    this.container = null;
    this.spotlightElement = null;
    this.tooltipElement = null;
    this.backdropElement = null;
    this.svgElement = null;

    // Pour le drag & drop
    this.isDragging = false;
    this.dragStartX = 0;
    this.dragStartY = 0;
    this.tooltipStartX = 0;
    this.tooltipStartY = 0;
  }

  open() {
    this.isOpen = true;
    this.currentStep = 0;
    this.render();
    this.updateSpotlight();
  }

  close(dontShowAgain = false) {
    if (dontShowAgain) {
      localStorage.setItem('emergence_tutorial_completed', 'true');
    }
    this.isOpen = false;
    if (this.container) {
      this.container.remove();
      this.container = null;
    }
  }

  setupDragging() {
    if (!this.tooltipElement) return;

    const header = this.tooltipElement.querySelector('.tutorial-header');
    if (!header) return;

    header.style.cursor = 'move';
    header.title = 'Glissez pour déplacer';

    const onMouseDown = (e) => {
      // Ne pas démarrer le drag si on clique sur le bouton fermer
      if (e.target.closest('.tutorial-close')) return;

      this.isDragging = true;
      this.dragStartX = e.clientX;
      this.dragStartY = e.clientY;

      const rect = this.tooltipElement.getBoundingClientRect();
      this.tooltipStartX = rect.left;
      this.tooltipStartY = rect.top;

      document.addEventListener('mousemove', onMouseMove);
      document.addEventListener('mouseup', onMouseUp);

      this.tooltipElement.style.transition = 'none';
      e.preventDefault();
    };

    const onMouseMove = (e) => {
      if (!this.isDragging) return;

      const deltaX = e.clientX - this.dragStartX;
      const deltaY = e.clientY - this.dragStartY;

      const newX = this.tooltipStartX + deltaX;
      const newY = this.tooltipStartY + deltaY;

      this.tooltipElement.style.left = `${newX}px`;
      this.tooltipElement.style.top = `${newY}px`;
      this.tooltipElement.style.transform = 'none';
    };

    const onMouseUp = () => {
      this.isDragging = false;
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('mouseup', onMouseUp);

      setTimeout(() => {
        if (this.tooltipElement) {
          this.tooltipElement.style.transition = '';
        }
      }, 100);
    };

    header.addEventListener('mousedown', onMouseDown);
  }

  render() {
    if (!this.isOpen) return;

    // Créer le conteneur principal
    this.container = document.createElement('div');
    this.container.className = 'tutorial-overlay active';

    // Backdrop - NE PAS écouter les clics ici pour ne pas bloquer l'interaction
    this.backdropElement = document.createElement('div');
    this.backdropElement.className = 'tutorial-backdrop';
    this.container.appendChild(this.backdropElement);

    // SVG pour le spotlight
    this.svgElement = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    this.svgElement.setAttribute('class', 'tutorial-spotlight-svg');
    this.container.appendChild(this.svgElement);

    // Spotlight
    this.spotlightElement = document.createElement('div');
    this.spotlightElement.className = 'tutorial-spotlight';
    this.container.appendChild(this.spotlightElement);

    // Tooltip
    this.renderTooltip();

    document.body.appendChild(this.container);

    // Écouter le redimensionnement
    window.addEventListener('resize', () => this.updateSpotlight());
  }

  renderTooltip() {
    const step = TUTORIAL_STEPS[this.currentStep];
    const isFirstStep = this.currentStep === 0;
    const isLastStep = this.currentStep === TUTORIAL_STEPS.length - 1;

    this.tooltipElement = document.createElement('div');
    this.tooltipElement.className = 'tutorial-tooltip';

    // Header
    const header = document.createElement('div');
    header.className = 'tutorial-header';
    header.innerHTML = `
      <h2>${step.title}</h2>
      <button class="tutorial-close" aria-label="Fermer">×</button>
    `;
    header.querySelector('.tutorial-close').addEventListener('click', () => this.handleSkip());

    // Content
    const content = document.createElement('div');
    content.className = 'tutorial-content';
    content.innerHTML = `<p>${step.description}</p>`;

    // Footer
    const footer = document.createElement('div');
    footer.className = 'tutorial-footer';

    // Progress dots
    const progress = document.createElement('div');
    progress.className = 'tutorial-progress';
    TUTORIAL_STEPS.forEach((_, index) => {
      const dot = document.createElement('div');
      dot.className = 'tutorial-progress-dot';
      if (index === this.currentStep) dot.classList.add('active');
      if (index < this.currentStep) dot.classList.add('completed');
      progress.appendChild(dot);
    });
    footer.appendChild(progress);

    // Checkbox "Ne plus afficher"
    if (isFirstStep) {
      const checkbox = document.createElement('div');
      checkbox.className = 'tutorial-checkbox';
      checkbox.innerHTML = `
        <input type="checkbox" id="tutorial-dont-show" />
        <label for="tutorial-dont-show">Ne plus afficher</label>
      `;
      footer.appendChild(checkbox);
    }

    // Buttons
    const buttons = document.createElement('div');
    buttons.className = 'tutorial-buttons';

    if (!isFirstStep) {
      const prevBtn = document.createElement('button');
      prevBtn.className = 'tutorial-btn tutorial-btn-secondary';
      prevBtn.textContent = 'Précédent';
      prevBtn.addEventListener('click', () => this.handlePrevious());
      buttons.appendChild(prevBtn);
    }

    if (isFirstStep) {
      const skipBtn = document.createElement('button');
      skipBtn.className = 'tutorial-btn tutorial-btn-secondary';
      skipBtn.textContent = 'Passer';
      skipBtn.addEventListener('click', () => this.handleSkip());
      buttons.appendChild(skipBtn);
    }

    const nextBtn = document.createElement('button');
    nextBtn.className = 'tutorial-btn tutorial-btn-primary';
    nextBtn.textContent = isLastStep ? 'Terminer' : 'Suivant';
    nextBtn.addEventListener('click', () => this.handleNext());
    buttons.appendChild(nextBtn);

    footer.appendChild(buttons);

    this.tooltipElement.appendChild(header);
    this.tooltipElement.appendChild(content);
    this.tooltipElement.appendChild(footer);

    if (this.container) {
      this.container.appendChild(this.tooltipElement);
      // Activer le drag & drop après avoir ajouté le tooltip au DOM
      this.setupDragging();
    }
  }

  updateSpotlight() {
    const step = TUTORIAL_STEPS[this.currentStep];

    if (step.target) {
      const element = document.querySelector(step.target);
      if (element) {
        const rect = element.getBoundingClientRect();

        // Mettre à jour le spotlight
        if (this.spotlightElement) {
          this.spotlightElement.style.top = `${rect.top}px`;
          this.spotlightElement.style.left = `${rect.left}px`;
          this.spotlightElement.style.width = `${rect.width}px`;
          this.spotlightElement.style.height = `${rect.height}px`;
          this.spotlightElement.style.display = 'block';
        }

        // Mettre à jour le SVG mask
        if (this.svgElement) {
          this.svgElement.innerHTML = `
            <defs>
              <mask id="spotlight-mask">
                <rect x="0" y="0" width="100%" height="100%" fill="white" />
                <rect
                  x="${rect.left - 8}"
                  y="${rect.top - 8}"
                  width="${rect.width + 16}"
                  height="${rect.height + 16}"
                  rx="12"
                  fill="black"
                />
              </mask>
            </defs>
            <rect
              x="0"
              y="0"
              width="100%"
              height="100%"
              fill="rgba(0, 0, 0, 0.35)"
              mask="url(#spotlight-mask)"
            />
          `;
        }

        // Positionner le tooltip
        this.positionTooltip(rect, step.position);
      }
    } else {
      // Pas de spotlight pour cette étape
      if (this.spotlightElement) {
        this.spotlightElement.style.display = 'none';
      }
      if (this.svgElement) {
        this.svgElement.innerHTML = '';
      }
      // Centrer le tooltip
      if (this.tooltipElement) {
        this.tooltipElement.style.top = '50%';
        this.tooltipElement.style.left = '50%';
        this.tooltipElement.style.transform = 'translate(-50%, -50%)';
      }
    }
  }

  positionTooltip(targetRect, position) {
    if (!this.tooltipElement) return;

    const tooltipWidth = 480;
    const tooltipHeight = 400; // Augmenté pour contenu plus long
    const padding = 30;
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;

    let style = {};
    let finalTop, finalLeft;

    switch (position) {
      case 'right':
        finalTop = targetRect.top + targetRect.height / 2;
        finalLeft = targetRect.left + targetRect.width + padding;

        // Vérifier débordement à droite
        if (finalLeft + tooltipWidth > viewportWidth - 20) {
          // Positionner à gauche plutôt
          finalLeft = targetRect.left - tooltipWidth - padding;
        }

        // Vérifier débordement vertical
        if (finalTop - tooltipHeight / 2 < 20) {
          finalTop = 20 + tooltipHeight / 2;
        } else if (finalTop + tooltipHeight / 2 > viewportHeight - 20) {
          finalTop = viewportHeight - 20 - tooltipHeight / 2;
        }

        style = {
          top: `${finalTop}px`,
          left: `${finalLeft}px`,
          transform: 'translateY(-50%)'
        };
        break;

      case 'left':
        finalTop = targetRect.top + targetRect.height / 2;
        finalLeft = targetRect.left - tooltipWidth - padding;

        // Vérifier débordement à gauche
        if (finalLeft < 20) {
          // Positionner au centre plutôt
          finalLeft = (viewportWidth - tooltipWidth) / 2;
          finalTop = viewportHeight / 2;
          style = {
            top: `${finalTop}px`,
            left: `${finalLeft}px`,
            transform: 'none'
          };
        } else {
          // Vérifier débordement vertical
          if (finalTop - tooltipHeight / 2 < 20) {
            finalTop = 20 + tooltipHeight / 2;
          } else if (finalTop + tooltipHeight / 2 > viewportHeight - 20) {
            finalTop = viewportHeight - 20 - tooltipHeight / 2;
          }

          style = {
            top: `${finalTop}px`,
            left: `${finalLeft}px`,
            transform: 'translateY(-50%)'
          };
        }
        break;

      case 'top':
        finalTop = targetRect.top - tooltipHeight - padding;
        finalLeft = targetRect.left + targetRect.width / 2;

        // Vérifier débordement en haut
        if (finalTop < 20) {
          // Positionner en bas plutôt
          finalTop = targetRect.top + targetRect.height + padding;
        }

        // Vérifier débordement horizontal
        if (finalLeft - tooltipWidth / 2 < 20) {
          finalLeft = 20 + tooltipWidth / 2;
        } else if (finalLeft + tooltipWidth / 2 > viewportWidth - 20) {
          finalLeft = viewportWidth - 20 - tooltipWidth / 2;
        }

        style = {
          top: `${finalTop}px`,
          left: `${finalLeft}px`,
          transform: 'translateX(-50%)'
        };
        break;

      case 'bottom':
        finalTop = targetRect.top + targetRect.height + padding;
        finalLeft = targetRect.left + targetRect.width / 2;

        // Vérifier débordement en bas
        if (finalTop + tooltipHeight > viewportHeight - 20) {
          // Positionner en haut plutôt
          finalTop = targetRect.top - tooltipHeight - padding;
        }

        // Vérifier débordement horizontal
        if (finalLeft - tooltipWidth / 2 < 20) {
          finalLeft = 20 + tooltipWidth / 2;
        } else if (finalLeft + tooltipWidth / 2 > viewportWidth - 20) {
          finalLeft = viewportWidth - 20 - tooltipWidth / 2;
        }

        style = {
          top: `${finalTop}px`,
          left: `${finalLeft}px`,
          transform: 'translateX(-50%)'
        };
        break;

      default:
        // Centré avec contraintes
        style = {
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          maxWidth: 'calc(100vw - 40px)',
          maxHeight: 'calc(100vh - 40px)'
        };
    }

    Object.assign(this.tooltipElement.style, style);
  }

  handleNext() {
    if (this.currentStep < TUTORIAL_STEPS.length - 1) {
      this.currentStep++;
      this.updateStep();
    } else {
      this.close(false);
    }
  }

  handlePrevious() {
    if (this.currentStep > 0) {
      this.currentStep--;
      this.updateStep();
    }
  }

  handleSkip() {
    const checkbox = document.getElementById('tutorial-dont-show');
    const dontShow = checkbox ? checkbox.checked : false;
    this.close(dontShow);
  }

  updateStep() {
    // Supprimer l'ancien tooltip
    if (this.tooltipElement) {
      this.tooltipElement.remove();
    }

    // Créer le nouveau tooltip
    this.renderTooltip();

    // Mettre à jour le spotlight
    this.updateSpotlight();
  }
}
