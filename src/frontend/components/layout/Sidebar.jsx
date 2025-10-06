/**
 * @module components/layout/Sidebar
 * @description Sidebar responsive (desktop + mobile paysage) avec navigation verticale
 */

export class Sidebar {
  /**
   * Crée une sidebar responsive
   * @param {Object} options - Configuration de la sidebar
   * @param {Array} options.items - Items de navigation
   * @param {string} [options.activeItem] - ID de l'item actif
   * @param {Function} [options.onItemClick] - Callback au clic sur un item
   * @param {Object} [options.branding] - Configuration branding (logo, titre)
   * @returns {HTMLElement} - Élément sidebar
   */
  static create({
    items = [],
    activeItem = null,
    onItemClick = null,
    branding = null
  }) {
    const sidebar = document.createElement('aside');
    sidebar.className = 'app-sidebar';
    sidebar.setAttribute('role', 'navigation');
    sidebar.setAttribute('aria-label', 'Navigation principale');

    if (items.length === 0) {
      items = Sidebar.getDefaultItems();
    }

    const brand = branding || Sidebar.getDefaultBranding();
    const brandingHTML = `
      <div class="brand-block">
        ${brand.logo ? `<img src="${brand.logo}" alt="${brand.title}" class="brand-logo" />` : ''}
      </div>
    `;

    const navItemsHTML = items.map(item => {
      const isActive = item.id === activeItem;
      return `
        <button
          class="sidebar-nav__item ${isActive ? 'sidebar-nav__item--active' : ''}"
          data-nav-id="${item.id}"
          aria-label="${item.label}"
          aria-current="${isActive ? 'page' : 'false'}"
        >
          <span class="sidebar-nav__icon">${item.icon}</span>
          <span class="sidebar-nav__label">${item.label}</span>
        </button>
      `;
    }).join('');

    sidebar.innerHTML = `
      ${brandingHTML}
      <nav class="sidebar-nav" aria-label="Navigation">
        ${navItemsHTML}
      </nav>
    `;

    // Event delegation pour les clics
    if (onItemClick && typeof onItemClick === 'function') {
      const nav = sidebar.querySelector('.sidebar-nav');
      nav.addEventListener('click', (e) => {
        const item = e.target.closest('.sidebar-nav__item');
        if (item) {
          const navId = item.dataset.navId;
          const itemData = items.find(i => i.id === navId);
          if (itemData) {
            // Mise à jour visuelle
            nav.querySelectorAll('.sidebar-nav__item').forEach(btn => {
              btn.classList.remove('sidebar-nav__item--active');
              btn.setAttribute('aria-current', 'false');
            });
            item.classList.add('sidebar-nav__item--active');
            item.setAttribute('aria-current', 'page');

            onItemClick(itemData);
          }
        }
      });
    }

    return sidebar;
  }

  /**
   * Items de navigation par défaut
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
        label: 'Fils de discussion',
        icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"></path>
                <rect x="8" y="2" width="8" height="4" rx="1" ry="1"></rect>
              </svg>`,
      },
      {
        id: 'concepts',
        label: 'Concepts',
        icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"></path>
              </svg>`,
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
        id: 'documents',
        label: 'Documents',
        icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                <polyline points="14 2 14 8 20 8"></polyline>
              </svg>`
      },
      {
        id: 'settings',
        label: 'Paramètres',
        icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="3"></circle>
                <path d="M12 1v6m0 6v6m5.657-13.657l-4.243 4.243m-2.828 2.828l-4.243 4.243m16.97-.485l-6-1m-6 0l-6 1m13.657-5.657l-4.243-4.243m-2.828-2.828l-4.243-4.243m16.97 6.142l-6 1m-6 0l-6-1"></path>
              </svg>`,
      },
    ];
  }

  /**
   * Branding par défaut
   */
  static getDefaultBranding() {
    return {
      logo: '/assets/emergence-logo.svg',
      title: 'ÉMERGENCE'
    };
  }

  /**
   * Met à jour l'item actif
   * @param {HTMLElement} sidebarElement - Élément sidebar
   * @param {string} itemId - ID du nouvel item actif
   */
  static setActiveItem(sidebarElement, itemId) {
    if (!sidebarElement) return;

    const nav = sidebarElement.querySelector('.sidebar-nav');
    if (!nav) return;

    nav.querySelectorAll('.sidebar-nav__item').forEach(item => {
      const isActive = item.dataset.navId === itemId;
      item.classList.toggle('sidebar-nav__item--active', isActive);
      item.setAttribute('aria-current', isActive ? 'page' : 'false');
    });
  }
}

/**
 * Styles CSS pour la sidebar responsive
 * À importer dans votre fichier CSS principal
 */
export const SIDEBAR_STYLES = `
/* === SIDEBAR RESPONSIVE === */

.app-sidebar {
  display: flex;
  flex-direction: column;
  padding: 1rem 1rem;
  background-color: transparent;
  border-right: 1px solid rgba(255, 255, 255, 0.08);
  min-height: 100vh;
  height: 100vh;
  align-items: center;
  gap: 0.5rem;
  width: var(--sidebar-width, 224px);
  overflow-y: auto;
  overflow-x: hidden;
}

/* === BRANDING === */
.brand-block {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.25rem 0;
  text-align: center;
  width: 100%;
  max-width: 260px;
  flex-shrink: 0;
}

.brand-logo {
  width: auto;
  height: auto;
  max-height: 57px;
  object-fit: contain;
  filter: drop-shadow(0 0 22px rgba(56, 189, 248, 0.45));
  animation: emergenceLogoPulse 8s cubic-bezier(0.22, 1, 0.36, 1) infinite;
}

.brand-title {
  font-size: clamp(20px, 2.6vw, 28px);
  line-height: 1.05;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  background: linear-gradient(120deg, rgba(125, 211, 252, 1) 0%, rgba(59, 130, 246, 1) 45%, rgba(168, 85, 247, 1) 100%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  text-shadow: 0 0 24px rgba(59, 130, 246, 0.35);
}

@supports not (-webkit-background-clip: text) {
  .brand-title {
    color: #e2e8f0;
  }
}

@keyframes emergenceLogoPulse {
  0%, 100% {
    transform: translateY(0) scale(1);
    filter: drop-shadow(0 0 18px rgba(56, 189, 248, 0.38));
  }
  45% {
    transform: translateY(-6px) scale(1.04);
    filter: drop-shadow(0 0 24px rgba(168, 85, 247, 0.45));
  }
  65% {
    transform: translateY(-3px) scale(1.02);
    filter: drop-shadow(0 0 20px rgba(59, 130, 246, 0.5));
  }
}

/* === NAVIGATION === */
.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  width: 100%;
  max-width: 280px;
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding-bottom: 2rem;
  min-height: 0;
}

.sidebar-nav__item {
  display: flex;
  align-items: center;
  gap: 0.875rem;
  padding: 0.75rem 1rem;
  border: 1px solid transparent;
  border-radius: 0.75rem;
  background: transparent;
  color: rgba(148, 163, 184, 0.85);
  font-size: 1.045rem;
  font-weight: 500;
  letter-spacing: 0.01em;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
  text-align: left;
}

/* Subtle glow on hover */
.sidebar-nav__item::before {
  content: '';
  position: absolute;
  inset: 0;
  background: var(--metal-emerald-gradient, linear-gradient(to right, #34d399, #10b981));
  opacity: 0;
  transition: opacity 0.3s ease;
  border-radius: inherit;
  z-index: -1;
}

.sidebar-nav__item:hover {
  color: rgba(226, 232, 240, 0.95);
  border-color: rgba(148, 163, 184, 0.25);
  background: rgba(15, 23, 42, 0.35);
  transform: translateX(4px);
}

.sidebar-nav__item--active {
  color: #10b981;
  border-color: rgba(16, 185, 129, 0.4);
  background: rgba(16, 185, 129, 0.12);
  font-weight: 600;
}

.sidebar-nav__item--active::before {
  opacity: 0.1;
}

.sidebar-nav__item:active {
  transform: translateX(2px) scale(0.98);
}

/* === ICÔNE === */
.sidebar-nav__icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  flex-shrink: 0;
}

.sidebar-nav__icon svg {
  width: 100%;
  height: 100%;
  stroke-width: 2;
}

/* === LABEL === */
.sidebar-nav__label {
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* === RESPONSIVE === */

/* Desktop: sidebar visible */
@media (min-width: 768px) {
  .app-sidebar {
    display: flex;
  }
}

/* Mobile portrait: masquer la sidebar (on utilise la bottom nav) */
@media (max-width: 767px) and (orientation: portrait) {
  .app-sidebar {
    display: none !important;
  }
}

/* Mobile paysage: sidebar compacte verticale gauche */
@media (max-width: 920px) and (orientation: landscape) {
  .app-sidebar {
    display: flex;
    width: 240px;
    padding: 0.75rem 0.5rem;
    gap: 1rem;
  }

  .brand-logo {
    max-height: 34px;
  }

  .brand-title {
    font-size: 18px;
  }

  .sidebar-nav {
    max-width: 100%;
    gap: 0.25rem;
  }

  .sidebar-nav__item {
    padding: 0.625rem 0.75rem;
    font-size: 0.875rem;
    gap: 0.625rem;
  }

  .sidebar-nav__icon {
    width: 20px;
    height: 20px;
  }
}

/* Très petits écrans paysage */
@media (max-width: 640px) and (orientation: landscape) {
  .app-sidebar {
    width: 200px;
  }

  .brand-title {
    display: none; /* Masquer le titre, garder juste le logo */
  }

  .sidebar-nav__label {
    font-size: 0.8125rem;
  }
}
`;
