/**
 * @module components/ui/Button
 * @description Bouton harmonisé avec effets métalliques (primaire, secondaire, danger)
 */

export class Button {
  /**
   * Crée un bouton harmonisé avec effet métallique
   * @param {Object} options - Configuration du bouton
   * @param {string} options.variant - 'primary' | 'secondary' | 'danger'
   * @param {string} options.text - Texte du bouton
   * @param {string} [options.icon] - SVG icon (optionnel)
   * @param {Function} [options.onClick] - Callback au clic
   * @param {string} [options.id] - ID HTML
   * @param {string} [options.className] - Classes CSS additionnelles
   * @param {boolean} [options.disabled] - État désactivé
   * @param {boolean} [options.shimmer] - Activer l'effet shimmer
   * @returns {HTMLButtonElement} - Élément bouton
   */
  static create({
    variant = 'primary',
    text = '',
    icon = null,
    onClick = null,
    id = '',
    className = '',
    disabled = false,
    shimmer = true
  }) {
    const button = document.createElement('button');

    // Classes de base
    button.className = `btn-modern btn-modern--${variant} ${shimmer ? 'metallic-shimmer' : ''} ${className}`.trim();

    if (id) button.id = id;
    if (disabled) button.disabled = true;

    // Contenu avec icône optionnelle
    const content = `
      ${icon ? `<span class="btn-modern__icon">${icon}</span>` : ''}
      <span class="btn-modern__text">${text}</span>
    `;

    button.innerHTML = content;

    if (onClick && typeof onClick === 'function') {
      button.addEventListener('click', onClick);
    }

    return button;
  }

  /**
   * Raccourci pour bouton primaire (émeraude métallique)
   */
  static primary(text, options = {}) {
    return Button.create({ ...options, variant: 'primary', text });
  }

  /**
   * Raccourci pour bouton secondaire (acier)
   */
  static secondary(text, options = {}) {
    return Button.create({ ...options, variant: 'secondary', text });
  }

  /**
   * Raccourci pour bouton danger (rouge métallique)
   */
  static danger(text, options = {}) {
    return Button.create({ ...options, variant: 'danger', text });
  }
}

/**
 * Styles CSS pour les boutons modernisés
 * À importer dans votre fichier CSS principal
 */
export const BUTTON_STYLES = `
/* === BOUTONS MODERNISÉS AVEC EFFETS MÉTALLIQUES === */

.btn-modern {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  height: var(--btn-height, 42px);
  padding: var(--btn-padding, 0 1rem);
  border-radius: var(--btn-radius, 0.75rem);
  font-size: var(--btn-font-size, 0.95rem);
  font-weight: var(--btn-font-weight, 500);
  font-family: var(--font-primary, 'Inter', sans-serif);
  border: none;
  cursor: pointer;
  transition: var(--btn-transition, all 0.3s cubic-bezier(0.4, 0, 0.2, 1));
  position: relative;
  overflow: hidden;
  outline: none;
}

.btn-modern:focus-visible {
  outline: 2px solid currentColor;
  outline-offset: 2px;
}

/* === VARIANT PRIMAIRE (Émeraude métallique) === */
.btn-modern--primary {
  background: var(--metal-emerald-gradient);
  color: white;
  box-shadow: var(--metal-emerald-shadow);
}

.btn-modern--primary:hover:not(:disabled) {
  background: var(--metal-emerald-hover);
  transform: scale(var(--scale-hover, 1.05));
}

.btn-modern--primary:active:not(:disabled) {
  transform: scale(var(--scale-active, 0.98));
}

/* === VARIANT SECONDAIRE (Acier) === */
.btn-modern--secondary {
  background: var(--metal-steel-gradient);
  color: white;
  box-shadow: var(--metal-steel-shadow);
}

.btn-modern--secondary:hover:not(:disabled) {
  background: var(--metal-steel-hover);
  transform: scale(var(--scale-hover, 1.05));
}

.btn-modern--secondary:active:not(:disabled) {
  transform: scale(var(--scale-active, 0.98));
}

/* === VARIANT DANGER (Rouge métallique) === */
.btn-modern--danger {
  background: var(--metal-red-gradient);
  color: white;
  box-shadow: var(--metal-red-shadow);
}

.btn-modern--danger:hover:not(:disabled) {
  background: var(--metal-red-hover);
  transform: scale(var(--scale-hover, 1.05));
}

.btn-modern--danger:active:not(:disabled) {
  transform: scale(var(--scale-active, 0.98));
}

/* === ÉTAT DISABLED === */
.btn-modern:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none !important;
  box-shadow: none !important;
}

/* === ICÔNE & TEXTE === */
.btn-modern__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
}

.btn-modern__icon svg {
  width: 100%;
  height: 100%;
}

.btn-modern__text {
  line-height: 1.2;
}

/* === RESPONSIVE === */
@media (max-width: 640px) {
  .btn-modern {
    height: 38px;
    padding: 0 0.875rem;
    font-size: 0.875rem;
  }

  .btn-modern__icon {
    width: 18px;
    height: 18px;
  }
}
`;
