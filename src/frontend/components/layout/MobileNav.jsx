/**
 * @module components/layout/MobileNav
 * @description Bottom navigation bar pour mobile portrait avec icônes + labels
 */

export class MobileNav {
  /**
   * Crée une bottom nav bar responsive pour mobile portrait
   * @param {Object} options - Configuration de la nav
   * @param {Array} options.items - Items de navigation
   * @param {string} [options.activeItem] - ID de l'item actif
   * @param {Function} [options.onItemClick] - Callback au clic sur un item
   * @returns {HTMLElement} - Élément nav
   */
  static create({
    items = [],
    activeItem = null,
    onItemClick = null
  }) {
    const nav = document.createElement('nav');
    nav.className = 'mobile-nav';
    nav.setAttribute('role', 'navigation');
    nav.setAttribute('aria-label', 'Navigation principale mobile');

    if (items.length === 0) {
      items = MobileNav.getDefaultItems();
    }

    const itemsHTML = items.map(item => {
      const isActive = item.id === activeItem;
      return `
        <button
          class="mobile-nav__item ${isActive ? 'mobile-nav__item--active' : ''}"
          data-nav-id="${item.id}"
          aria-label="${item.label}"
          aria-current="${isActive ? 'page' : 'false'}"
        >
          <span class="mobile-nav__icon">${item.icon}</span>
          <span class="mobile-nav__label">${item.label}</span>
        </button>
      `;
    }).join('');

    nav.innerHTML = `<div class="mobile-nav__container">${itemsHTML}</div>`;

    // Event delegation pour les clics
    if (onItemClick && typeof onItemClick === 'function') {
      nav.addEventListener('click', (e) => {
        const item = e.target.closest('.mobile-nav__item');
        if (item) {
          const navId = item.dataset.navId;
          const itemData = items.find(i => i.id === navId);
          if (itemData) {
            // Mise à jour visuelle
            nav.querySelectorAll('.mobile-nav__item').forEach(btn => {
              btn.classList.remove('mobile-nav__item--active');
              btn.setAttribute('aria-current', 'false');
            });
            item.classList.add('mobile-nav__item--active');
            item.setAttribute('aria-current', 'page');

            onItemClick(itemData);
          }
        }
      });
    }

    return nav;
  }

  /**
   * Items par défaut (adaptés à Emergence)
   */
  static getDefaultItems() {
    return [
      {
        id: 'home',
        label: 'Accueil',
        icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path>
                <polyline points="9 22 9 12 15 12 15 22"></polyline>
              </svg>`
      },
      {
        id: 'chat',
        label: 'Chat',
        icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
              </svg>`
      },
      {
        id: 'threads',
        label: 'Fils',
        icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"></path>
                <rect x="8" y="2" width="8" height="4" rx="1" ry="1"></rect>
              </svg>`
      },
      {
        id: 'dashboard',
        label: 'Cockpit',
        icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="3" width="7" height="7"></rect>
                <rect x="14" y="3" width="7" height="7"></rect>
                <rect x="14" y="14" width="7" height="7"></rect>
                <rect x="3" y="14" width="7" height="7"></rect>
              </svg>`
      },
      {
        id: 'more',
        label: 'Plus',
        icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="1"></circle>
                <circle cx="12" cy="5" r="1"></circle>
                <circle cx="12" cy="19" r="1"></circle>
              </svg>`
      }
    ];
  }

  /**
   * Met à jour l'item actif
   * @param {HTMLElement} navElement - Élément nav
   * @param {string} itemId - ID du nouvel item actif
   */
  static setActiveItem(navElement, itemId) {
    if (!navElement) return;

    navElement.querySelectorAll('.mobile-nav__item').forEach(item => {
      const isActive = item.dataset.navId === itemId;
      item.classList.toggle('mobile-nav__item--active', isActive);
      item.setAttribute('aria-current', isActive ? 'page' : 'false');
    });
  }
}

/**
 * Styles CSS pour la mobile nav
 * À importer dans votre fichier CSS principal
 */
export const MOBILE_NAV_STYLES = `
/* === MOBILE NAV (Bottom Bar Portrait) === */

.mobile-nav {
  display: none; /* Masqué par défaut, visible en mobile portrait */
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: var(--z-header, 10);
  background: rgba(11, 15, 26, 0.95);
  backdrop-filter: blur(12px);
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  padding-bottom: env(safe-area-inset-bottom, 0);
  box-shadow: 0 -10px 30px rgba(0, 0, 0, 0.35);
}

.mobile-nav__container {
  display: flex;
  align-items: center;
  justify-content: space-around;
  height: var(--mobile-nav-height, 64px);
  max-width: 100%;
  margin: 0 auto;
  padding: 0 0.5rem;
  gap: var(--mobile-nav-gap, 4px);
}

/* === ITEMS === */
.mobile-nav__item {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.25rem;
  flex: 1;
  min-width: 0;
  padding: 0.5rem 0.25rem;
  border: none;
  background: transparent;
  color: rgba(226, 232, 240, 0.85);
  cursor: pointer;
  transition: color 0.2s ease, transform 0.2s ease;
  border-radius: 0.5rem;
  position: relative;
}

.mobile-nav__item::before {
  content: '';
  position: absolute;
  top: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 0;
  height: 2px;
  background: var(--metal-emerald-gradient, linear-gradient(to right, #34d399, #10b981));
  border-radius: 0 0 2px 2px;
  transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.mobile-nav__item--active::before {
  width: 32px;
}

.mobile-nav__item:hover,
.mobile-nav__item:focus-visible {
  color: rgba(255, 255, 255, 1);
}

.mobile-nav__item--active {
  color: #10b981;
}

.mobile-nav__item:active {
  transform: scale(0.95);
}

/* === ICÔNE === */
.mobile-nav__icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: var(--mobile-nav-icon-size, 24px);
  height: var(--mobile-nav-icon-size, 24px);
}

.mobile-nav__icon svg {
  width: 100%;
  height: 100%;
  stroke-width: 2;
}

/* === LABEL === */
.mobile-nav__label {
  font-size: 0.6875rem;
  font-weight: 500;
  line-height: 1;
  letter-spacing: 0.02em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
}

/* === RESPONSIVE === */

/* Mobile portrait: afficher la bottom nav */
@media (max-width: 767px) and (orientation: portrait) {
  .mobile-nav {
    display: block;
  }

  /* Ajuster le padding de l'app-content pour compenser */
  .app-content {
    padding-bottom: calc(var(--mobile-nav-height, 64px) + env(safe-area-inset-bottom, 0) + 1rem) !important;
  }
}

/* Mobile paysage: masquer (on garde la sidebar) */
@media (max-width: 920px) and (orientation: landscape) {
  .mobile-nav {
    display: none;
  }
}

/* Très petits écrans: réduire les tailles */
@media (max-width: 360px) {
  .mobile-nav__container {
    height: 56px;
    gap: 2px;
  }

  .mobile-nav__icon {
    width: 20px;
    height: 20px;
  }

  .mobile-nav__label {
    font-size: 0.625rem;
  }

  .mobile-nav__item {
    padding: 0.375rem 0.125rem;
  }
}
`;
