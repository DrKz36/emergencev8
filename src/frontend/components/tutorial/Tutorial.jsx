import React, { useState, useEffect } from 'react';
import './Tutorial.css';

const TUTORIAL_STEPS = [
  {
    id: 'welcome',
    title: 'Bienvenue sur Emergence',
    description: 'Découvrez les fonctionnalités principales de votre assistant IA personnel. Ce tutoriel vous guidera pas à pas.',
    target: null,
    position: 'center'
  },
  {
    id: 'chat',
    title: 'Zone de Chat',
    description: 'Interagissez avec votre IA ici. Posez des questions, demandez des analyses ou discutez de vos idées. L\'IA se souvient de vos conversations précédentes.',
    target: '.chat-container',
    position: 'left'
  },
  {
    id: 'input',
    title: 'Zone de Saisie',
    description: 'Écrivez vos messages ici. Vous pouvez poser des questions complexes, demander des analyses ou simplement discuter.',
    target: '.chat-input-container',
    position: 'top'
  },
  {
    id: 'sidebar-threads',
    title: 'Historique des Conversations',
    description: 'Accédez à toutes vos conversations passées. Chaque thread garde le contexte pour des discussions continues.',
    target: '[data-tutorial="threads"]',
    position: 'right'
  },
  {
    id: 'sidebar-concepts',
    title: 'Concepts Mémorisés',
    description: 'L\'IA mémorise automatiquement les concepts importants de vos conversations. Consultez et gérez vos concepts ici.',
    target: '[data-tutorial="concepts"]',
    position: 'right'
  },
  {
    id: 'sidebar-settings',
    title: 'Paramètres',
    description: 'Personnalisez votre expérience : choix du modèle IA, gestion de la base de connaissances et configuration avancée.',
    target: '[data-tutorial="settings"]',
    position: 'right'
  },
  {
    id: 'complete',
    title: 'Vous êtes prêt !',
    description: 'Vous pouvez relancer ce tutoriel à tout moment depuis le menu de la barre latérale. Bonne exploration !',
    target: null,
    position: 'center'
  }
];

const Tutorial = ({ isOpen, onClose, startAtBeginning = true }) => {
  const [currentStep, setCurrentStep] = useState(0);
  const [showDontAskAgain, setShowDontAskAgain] = useState(true);
  const [spotlightPosition, setSpotlightPosition] = useState(null);

  useEffect(() => {
    if (isOpen) {
      updateSpotlight();
      window.addEventListener('resize', updateSpotlight);
      return () => window.removeEventListener('resize', updateSpotlight);
    }
  }, [isOpen, currentStep]);

  const updateSpotlight = () => {
    const step = TUTORIAL_STEPS[currentStep];
    if (step.target) {
      const element = document.querySelector(step.target);
      if (element) {
        const rect = element.getBoundingClientRect();
        setSpotlightPosition({
          top: rect.top,
          left: rect.left,
          width: rect.width,
          height: rect.height
        });
      }
    } else {
      setSpotlightPosition(null);
    }
  };

  const handleNext = () => {
    if (currentStep < TUTORIAL_STEPS.length - 1) {
      setCurrentStep(currentStep + 1);
    } else {
      handleClose(false);
    }
  };

  const handlePrevious = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleClose = (dontShowAgain = false) => {
    if (dontShowAgain) {
      localStorage.setItem('emergence_tutorial_completed', 'true');
    }
    setCurrentStep(0);
    onClose();
  };

  const handleSkip = () => {
    const dontShow = document.getElementById('tutorial-dont-show')?.checked;
    handleClose(dontShow);
  };

  if (!isOpen) return null;

  const step = TUTORIAL_STEPS[currentStep];
  const isFirstStep = currentStep === 0;
  const isLastStep = currentStep === TUTORIAL_STEPS.length - 1;

  const getTooltipPosition = () => {
    if (!spotlightPosition) return { top: '50%', left: '50%', transform: 'translate(-50%, -50%)' };

    const tooltipWidth = 400;
    const tooltipHeight = 250;
    const padding = 20;

    let position = {};

    switch (step.position) {
      case 'right':
        position = {
          top: `${spotlightPosition.top + spotlightPosition.height / 2}px`,
          left: `${spotlightPosition.left + spotlightPosition.width + padding}px`,
          transform: 'translateY(-50%)'
        };
        break;
      case 'left':
        position = {
          top: `${spotlightPosition.top + spotlightPosition.height / 2}px`,
          left: `${spotlightPosition.left - tooltipWidth - padding}px`,
          transform: 'translateY(-50%)'
        };
        break;
      case 'top':
        position = {
          top: `${spotlightPosition.top - tooltipHeight - padding}px`,
          left: `${spotlightPosition.left + spotlightPosition.width / 2}px`,
          transform: 'translateX(-50%)'
        };
        break;
      case 'bottom':
        position = {
          top: `${spotlightPosition.top + spotlightPosition.height + padding}px`,
          left: `${spotlightPosition.left + spotlightPosition.width / 2}px`,
          transform: 'translateX(-50%)'
        };
        break;
      default:
        position = {
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)'
        };
    }

    return position;
  };

  return (
    <div className="tutorial-overlay">
      {/* Overlay obscurci */}
      <div className="tutorial-backdrop" onClick={handleSkip} />

      {/* Spotlight sur l'élément ciblé */}
      {spotlightPosition && (
        <>
          <div
            className="tutorial-spotlight"
            style={{
              top: `${spotlightPosition.top}px`,
              left: `${spotlightPosition.left}px`,
              width: `${spotlightPosition.width}px`,
              height: `${spotlightPosition.height}px`
            }}
          />
          <svg className="tutorial-spotlight-svg">
            <defs>
              <mask id="spotlight-mask">
                <rect x="0" y="0" width="100%" height="100%" fill="white" />
                <rect
                  x={spotlightPosition.left - 8}
                  y={spotlightPosition.top - 8}
                  width={spotlightPosition.width + 16}
                  height={spotlightPosition.height + 16}
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
              fill="rgba(0, 0, 0, 0.75)"
              mask="url(#spotlight-mask)"
            />
          </svg>
        </>
      )}

      {/* Tooltip avec contenu */}
      <div
        className="tutorial-tooltip"
        style={getTooltipPosition()}
      >
        <div className="tutorial-header">
          <h2>{step.title}</h2>
          <button className="tutorial-close" onClick={handleSkip}>×</button>
        </div>

        <div className="tutorial-content">
          <p>{step.description}</p>
        </div>

        <div className="tutorial-footer">
          <div className="tutorial-progress">
            {TUTORIAL_STEPS.map((_, index) => (
              <div
                key={index}
                className={`tutorial-progress-dot ${index === currentStep ? 'active' : ''} ${index < currentStep ? 'completed' : ''}`}
              />
            ))}
          </div>

          {isFirstStep && showDontAskAgain && (
            <div className="tutorial-checkbox">
              <input type="checkbox" id="tutorial-dont-show" />
              <label htmlFor="tutorial-dont-show">Ne plus afficher</label>
            </div>
          )}

          <div className="tutorial-buttons">
            {!isFirstStep && (
              <button className="tutorial-btn tutorial-btn-secondary" onClick={handlePrevious}>
                Précédent
              </button>
            )}
            {isFirstStep && (
              <button className="tutorial-btn tutorial-btn-secondary" onClick={handleSkip}>
                Passer
              </button>
            )}
            <button className="tutorial-btn tutorial-btn-primary" onClick={handleNext}>
              {isLastStep ? 'Terminer' : 'Suivant'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Tutorial;
