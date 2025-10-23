/**
 * @module core/app
 * @description Core of the Emergence application - V35.0 "ThreadBootstrap"
 * - Bootstrap du thread courant au premier affichage (persist inter-sessions).
 * - Navigation deleguee inchangee.
 */

import { EVENTS } from '../shared/constants.js';
import { api } from '../shared/api-client.js'; // + Threads API
import { t } from '../shared/i18n.js';
import { modals } from '../components/modals.js';

const THREAD_ID_HEX_RE = /^[0-9a-f]{32}$/i;
const THREAD_ID_UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

const AUTH_ERROR_STATUSES = new Set([401, 403, 419, 440]);
const THREAD_INACCESSIBLE_MARKER = 'thread non accessible pour cet utilisateur';
const THREAD_INACCESSIBLE_CODES = new Set(['thread_not_accessible', 'thread_inaccessible']);
const ONBOARDING_STORAGE_KEY = 'emergence.onboarding.v20250926';
function isNetworkError(error) {
  const status =
    error?.status ??
    error?.response?.status ??
    error?.cause?.status ??
    null;
  if (typeof status === 'number') {
    return false;
  }
  const code = (error?.code || error?.cause?.code || '').toString().toUpperCase();
  const name = (error?.name || '').toString().toLowerCase();
  const message = (
    error?.message ||
    error?.cause?.message ||
    ''
  ).toString().toLowerCase();
  return (
    name === 'typeerror' ||
    message.includes('failed to fetch') ||
    message.includes('network') ||
    message.includes('load failed') ||
    code === 'ECONNREFUSED' ||
    code === 'ECONNRESET'
  );
}

// [CORRECTION VITE]
const moduleLoaders = {
  chat: () => import('../features/chat/chat.js'),
  conversations: () => import('../features/conversations/conversations.js'),
  debate: () => import('../features/debate/debate.js'),
  documents: () => import('../features/documents/documents.js'),
  references: () => import('../features/references/references.js'),
  cockpit: () => import('../features/cockpit/cockpit.js'),
  memory: () => import('../features/memory/memory.js'),
  admin: () => import('../features/admin/admin.js'),
  preferences: () => import('../features/preferences/preferences.js'),
  documentation: () => import('../features/documentation/documentation.js'),
};

export class App {
  constructor(eventBus, state) {
    this.eventBus = eventBus;
    this.state = state;
    this.initialized = false;
    this._authToastShown = false;
    this._authBannerShown = false;
    this.onboardingTour = null;
    this.onboardingScheduled = false;
    this.onboardingRetryCount = 0;


    this.dom = {
      appContainer: document.getElementById('app-container'),
      header: document.getElementById('app-header'),
      headerNavContainer: document.getElementById('app-header-nav'),
      headerNav: document.getElementById('app-header-nav-list'),
      mobileNavToggle: document.getElementById('mobile-nav-toggle'),
      sidebar: document.getElementById('app-sidebar'),
      tabs: document.getElementById('app-tabs'),
      content: document.getElementById('app-content'),
      memoryOverlay: document.getElementById('memory-overlay'),
      authStatus: document.getElementById('sidebar-auth-status'),
    };

    this.openMobileNav = null;
    this.closeMobileNav = null;
    this.toggleMobileNav = null;
    this.isMobileNavOpen = () => false;
    this._mobileNavDetach = [];

    this.modules = {};
    this.baseModules = [
      {
        id: 'chat',
        name: 'Dialogue',
        icon: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="8.5" cy="8" r="3"></circle><path d="M3 18c0-3 3.5-5.5 7.5-5.5S18 15 18 18"></path><circle cx="16" cy="9.5" r="2.5"></circle><path d="M13.5 18c0-2 2.2-3.75 4.5-3.75S22.5 16 22.5 18"></path></svg>'
      },
      {
        id: 'conversations',
        name: 'Conversations',
        icon: '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>'
      },
      { id: 'documents', name: 'Documents', icon: '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" /></svg>' },
      { id: 'debate', name: 'Debats', icon: '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M12 20.25c4.97 0 9-3.694 9-8.25s-4.03-8.25-9-8.25S3 7.444 3 12c0 2.104.859 4.023 2.273 5.48.432.447.74 1.04.586 1.641a4.483 4.483 0 01-.923 1.785A5.969 5.969 0 006 21c1.282 0 2.47-.402 3.445-1.087.81.22 1.668.337 2.555.337z" /></svg>' },
      {
        id: 'cockpit',
        name: 'Cockpit',
        icon: '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" /></svg>',
        requiresRole: ['admin', 'member', 'tester'],
      },
      {
        id: 'memory',
        name: 'Memoire',
        icon: '<svg class="nav-icon-brain" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true" focusable="false"><path d="M9.1 3.5c-2.1 0-3.8 1.66-3.8 3.7v1.08A3.6 3.6 0 0 0 3 11.9a3.55 3.55 0 0 0 2.08 3.2c.19.86.19 1.78 0 2.64A3.05 3.05 0 0 0 8 21h3V3.5H9.1z"></path><path d="M14.9 3.5c2.1 0 3.8 1.66 3.8 3.7v1.08A3.6 3.6 0 0 1 21 11.9a3.55 3.55 0 0 1-2.08 3.2c-.19.86-.19 1.78 0 2.64A3.05 3.05 0 0 1 16 21h-3V3.5h1.9z"></path><path d="M11 7.5h-1"></path><path d="M14 7.5h-1"></path><path d="M11 11.5h-1"></path><path d="M14 11.5h-1"></path><path d="M11 15.5h-1"></path><path d="M14 15.5h-1"></path></svg>',
        requiresRole: ['admin', 'member', 'tester'],
      },
      {
        id: 'preferences',
        name: 'Réglages',
        icon: '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 011.37.49l1.296 2.247a1.125 1.125 0 01-.26 1.431l-1.003.827c-.293.24-.438.613-.431.992a6.759 6.759 0 010 .255c-.007.378.138.75.43.99l1.005.828c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 01-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.57 6.57 0 01-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 01-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 01-1.369-.49l-1.297-2.247a1.125 1.125 0 01.26-1.431l1.004-.827c.292-.24.437-.613.43-.992a6.932 6.932 0 010-.255c.007-.378-.138-.75-.43-.99l-1.004-.828a1.125 1.125 0 01-.26-1.43l1.297-2.247a1.125 1.125 0 011.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.644-.869l.214-1.281z" /><path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /></svg>',
        requiresRole: 'admin',
      },
      {
        id: 'documentation',
        name: 'À propos',
        icon: '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z" /></svg>',
        requiresRole: ['admin', 'member', 'tester'],
      },
      {
        id: 'admin',
        name: 'Admin',
        icon: '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M10.5 6a3.75 3.75 0 117 0m-7 0H6.75A2.25 2.25 0 004.5 8.25v7.5A2.25 2.25 0 006.75 18h8.5A2.25 2.25 0 0017.5 15.75V11.5m0-5.5v5.25" /></svg>',
        requiresRole: 'admin',
      },
    ];
    this.activeModule = 'chat';
    this._mobileNavSetup = false;

    if (this.state?.subscribe) {
      try {
        this.state.subscribe('auth.role', (role) => {
          this.handleRoleChange(role);
        });
      } catch (err) {
        console.warn('[App] Impossible de souscrire a auth.role', err);
      }
    }

    console.log('[App] V35.0 (ThreadBootstrap) ready.');
    this.init();
  }

  getModuleConfig() {
    const modules = Array.isArray(this.baseModules) ? this.baseModules : [];
    const roleRaw = this.state?.get?.('auth.role');
    const role = (typeof roleRaw === 'string' && roleRaw.trim()) ? roleRaw.trim().toLowerCase() : 'member';
    return modules.filter((module) => {
      const requirement = module.requiresRole;
      if (!requirement) return true;
      if (Array.isArray(requirement)) {
        return requirement.map((item) => (typeof item === 'string' ? item.toLowerCase() : item)).includes(role);
      }
      return requirement === role;
    });
  }

  init() {
    if (this.initialized) return;
    this.renderNavigation();
    this.setupMobileNav();
    this.listenToNavEvents();
    this.bootstrapFeatures();
    this.initialized = true;
    this.handleRoleChange(this.state?.get?.('auth.role'));
  }

  handleRoleChange(role) {
    const normalizedRole = typeof role === 'string' && role.trim()
      ? role.trim().toLowerCase()
      : (this.state?.get?.('auth.role') || 'member');

    this.updateAuthStatus(normalizedRole);
    try {
      if (document?.body) {
        document.body.dataset.authRole = normalizedRole;
      }
    } catch (err) {
      console.warn('[App] Impossible de positionner data-auth-role', err);
    }

    const modules = this.getModuleConfig();
    const allowedIds = modules.map((m) => m.id);
    const hasMemory = allowedIds.includes('memory');
    const hasAdmin = allowedIds.includes('admin');

    if (!hasMemory) {
      try { this.closeMemoryMenu(); } catch (err) { console.warn('[App] Impossible de fermer le panneau memoire', err); }
      if (this.modules?.memory?.unmount) {
        try { this.modules.memory.unmount(); } catch (err) { console.warn('[App] Impossible de nettoyer le module memoire', err); }
      }
      if (this.modules) delete this.modules.memory;
      const memoryContainer = this.dom.content?.querySelector?.('#tab-content-memory');
      if (memoryContainer?.remove) {
        try { memoryContainer.remove(); } catch (err) { console.warn('[App] Impossible de retirer le container memoire', err); }
      }
    }

    if (!hasAdmin) {
      if (this.modules?.admin?.unmount) {
        try { this.modules.admin.unmount(); } catch (err) { console.warn('[App] Impossible de nettoyer le module admin', err); }
      }
      if (this.modules) delete this.modules.admin;
      const adminContainer = this.dom.content?.querySelector?.('#tab-content-admin');
      if (adminContainer?.remove) {
        try { adminContainer.remove(); } catch (err) { console.warn('[App] Impossible de retirer le container admin', err); }
      }
    }

    const currentIsAllowed = allowedIds.includes(this.activeModule);
    if (!currentIsAllowed) {
      const fallback = allowedIds.includes('chat') ? 'chat' : (allowedIds[0] || null);
      if (fallback) {
        this.showModule(fallback);
        return;
      }
    }

    this.renderNavigation();
  }

  updateAuthStatus(role) {
    const target = this.dom?.authStatus;
    if (!target) return;

    const normalizedRole = typeof role === 'string' && role.trim() ? role.trim().toLowerCase() : null;
    const emailRaw = this.state?.get?.('auth.email');
    const email = typeof emailRaw === 'string' && emailRaw.trim() ? emailRaw.trim().toLowerCase() : null;

    if (!normalizedRole) {
      target.textContent = 'Non connecté.';
      return;
    }

    const roleLabels = {
      admin: 'Administrateur',
      member: 'Membre',
      tester: 'Testeur',
    };
    const label = roleLabels[normalizedRole] || normalizedRole;
    const emailPart = email ? ` (${email})` : '';
    target.innerHTML = `Vous êtes connecté en tant que <strong>${label}</strong>${emailPart}`;

    // FIX: Émettre un événement pour notifier l'UI du changement d'état
    try {
      this.eventBus?.emit?.(EVENTS.AUTH_STATE_UPDATED || 'auth:state:updated', {
        role: normalizedRole,
        email: email,
        connected: true
      });
    } catch (err) {
      console.warn('[App] Impossible d\'émettre auth:state:updated', err);
    }
  }

  renderNavigation() {
    const modules = this.getModuleConfig();
    const navItemsHTML = modules.map((m) => {
      const navClasses = ['nav-item'];
      const linkClasses = ['nav-link'];
      const iconClasses = ['nav-icon', 'nav-icon--' + m.id];
      if (this.activeModule === m.id) linkClasses.push('active');
      if (m.id === 'memory') {
        navClasses.push('nav-item--memory');
        linkClasses.push('nav-link--memory');
      }
      const navClassStr = navClasses.join(' ');
      const linkClassStr = linkClasses.filter(Boolean).join(' ');
      const iconClassStr = iconClasses.join(' ');
      return '<li class="' + navClassStr + '">' +
        '<a href="#" class="' + linkClassStr + '" data-module-id="' + m.id + '">' +
          '<span class="' + iconClassStr + '">' + m.icon + '</span>' +
          '<span class="nav-text">' + m.name + '</span>' +
        '</a>' +
      '</li>';
    }).join('');

    if (this.dom.tabs) {
      this.dom.tabs.innerHTML = navItemsHTML;
    }

    if (this.dom.headerNav) {
      const headerNavItemsHTML = modules.map((m) => {
        const linkClasses = ['nav-link', 'mobile-nav-link'];
        if (this.activeModule === m.id) linkClasses.push('active');
        const linkClassStr = linkClasses.join(' ');
        return '<li class="nav-item">' +
          '<a href="#" class="' + linkClassStr + '" data-module-id="' + m.id + '" aria-label="' + m.name + '">' +
            '<span class="nav-icon">' + m.icon + '</span>' +
            '<span class="nav-text">' + m.name + '</span>' +
          '</a>' +
        '</li>';
      }).join('');
      this.dom.headerNav.innerHTML = headerNavItemsHTML;

      // Ajouter un listener direct sur chaque lien pour garantir la capture
      const links = this.dom.headerNav.querySelectorAll('.nav-link');
      links.forEach(link => {
        link.addEventListener('click', (e) => {
          e.preventDefault();
          e.stopPropagation();
          this.showModule(link.dataset.moduleId);
          // Fermer le menu après navigation
          setTimeout(() => {
            if (this.closeMobileNav) this.closeMobileNav();
          }, 50);
        }, { capture: true });
      });

    }
  }

  setupMobileNav(retryCount = 0) {
    if (typeof document === 'undefined') return;

    const toggle = document.getElementById('mobile-nav-toggle');
    const navContainer = document.getElementById('app-header-nav');

    if (!toggle || !navContainer) {
      if (retryCount < 5) {
        setTimeout(() => this.setupMobileNav(retryCount + 1), 50 * (retryCount + 1));
      }
      return;
    }

    if (Array.isArray(this._mobileNavDetach) && this._mobileNavDetach.length) {
      this._mobileNavDetach.forEach((detach) => {
        try { if (typeof detach === 'function') detach(); } catch (_) {}
      });
    }
    this._mobileNavDetach = [];

    this.dom.mobileNavToggle = toggle;
    this.dom.headerNavContainer = navContainer;

    // Référence qui sera mise à jour après le clonage
    let activeToggle = toggle;

    const applyState = (expanded) => {
      const isExpanded = !!expanded;
      activeToggle.setAttribute('aria-expanded', isExpanded ? 'true' : 'false');
      navContainer.classList.toggle('is-open', isExpanded);
      navContainer.setAttribute('aria-hidden', isExpanded ? 'false' : 'true');
      if (document.body) {
        document.body.classList.toggle('mobile-nav-open', isExpanded);
        document.body.classList.toggle('mobile-menu-open', isExpanded);
        if (isExpanded) document.body.classList.remove('brain-panel-open');
        if (typeof window !== 'undefined') {
          try {
            window.dispatchEvent(new CustomEvent('emergence:mobile-menu-state', { detail: { open: isExpanded } }));
          } catch (_) {}
        }
      }
    };

    const isExpanded = () => activeToggle.getAttribute('aria-expanded') === 'true';

    const handleToggle = (event) => {
      if (event) {
        if (typeof event.preventDefault === 'function') event.preventDefault();
        if (typeof event.stopPropagation === 'function') event.stopPropagation();
      }
      applyState(!isExpanded());
    };

    const handleKeydown = (event) => {
      if (!event) return;
      const key = event.key;
      if (key !== 'Enter' && key !== ' ') return;
      handleToggle(event);
    };

    const handleDocumentClick = (event) => {
      if (!isExpanded()) return;
      const target = event?.target || null;
      const navLink = target?.closest?.('.nav-link');
      const isInNav = navContainer.contains(target);
      const isInToggle = activeToggle.contains(target);
      // Si on a cliqué sur un lien de navigation, laisser le listener du lien gérer la navigation
      if (navLink && navLink.dataset.moduleId) {
        return;
      }
      if (isInNav || isInToggle) return;
      applyState(false);
    };

    const handleDocumentKeydown = (event) => {
      if (event?.key !== 'Escape') return;
      if (!isExpanded()) return;
      applyState(false);
    };

    // Marquer le toggle comme lié AVANT d'ajouter les écouteurs
    // Cela empêche les écouteurs fallback dans main.js de se réattacher
    try { toggle.dataset.mobileNavBound = 'app'; } catch (_) {}

    // Cloner et remplacer le toggle pour retirer tous les anciens écouteurs
    const newToggle = toggle.cloneNode(true);
    toggle.parentNode.replaceChild(newToggle, toggle);
    this.dom.mobileNavToggle = newToggle;
    activeToggle = newToggle;

    newToggle.addEventListener('click', handleToggle, { passive: false });
    newToggle.addEventListener('keydown', handleKeydown, { passive: false });
    document.addEventListener('click', handleDocumentClick);
    document.addEventListener('keydown', handleDocumentKeydown);

    this._mobileNavDetach.push(() => newToggle.removeEventListener('click', handleToggle));
    this._mobileNavDetach.push(() => newToggle.removeEventListener('keydown', handleKeydown));
    this._mobileNavDetach.push(() => document.removeEventListener('click', handleDocumentClick));
    this._mobileNavDetach.push(() => document.removeEventListener('keydown', handleDocumentKeydown));

    applyState(false);

    this.openMobileNav = () => applyState(true);
    this.closeMobileNav = () => applyState(false);
    this.toggleMobileNav = () => applyState(!isExpanded());
    this.isMobileNavOpen = () => isExpanded();
    this._mobileNavSetup = true;
  }

  isMemoryMenuOpen() {
    return typeof document !== 'undefined' && document.body.classList.contains('brain-panel-open');
  }

  closeMemoryMenu() {
    const handle = typeof window !== 'undefined' ? window.__EMERGENCE_MEMORY__ : null;
    if (handle && typeof handle.close === 'function') {
      handle.close();
    } else if (typeof document !== 'undefined') {
      document.body.classList.remove('brain-panel-open');
    }
    this.renderNavigation();
  }

  listenToNavEvents() {
    const root = this.dom.sidebar || document;
    const handleNavClick = (e) => {
      const link = e.target.closest('.nav-link');
      if (!link || !link.dataset.moduleId) return;
      e.preventDefault();
      e.stopPropagation();
      this.showModule(link.dataset.moduleId);
    };
    root.addEventListener('click', handleNavClick);
    this.dom.header?.addEventListener('click', handleNavClick);

    const navigateEvent = (EVENTS && EVENTS.MODULE_NAVIGATE) ? EVENTS.MODULE_NAVIGATE : 'app:navigate';
    this.eventBus.on?.(navigateEvent, (payload) => {
      const target = typeof payload === 'string' ? payload : payload && payload.moduleId;
      if (target) this.showModule(target);
    });
  }

  bootstrapFeatures() { this.showModule(this.activeModule, true); }

  clearSkeleton() {
    if (this._skeletonCleared) return;
    this._skeletonCleared = true;
    const c = this.dom.content;
    if (!c) return;
    c.querySelectorAll('.skeleton').forEach(el => el.remove());
  }


  _persistCurrentThreadId(threadId) {
    if (!this._isValidThreadId(threadId)) return;
    try { this.state.set('threads.currentId', threadId); } catch (err) { console.warn('[App] Impossible de mettre a jour threads.currentId', err); }
    try { localStorage.setItem('emergence.threadId', threadId); } catch (_) {}
  }

  _purgePersistedThreadId(previousId) {
    try { this.state.set('threads.currentId', null); } catch (err) { console.warn('[App] Impossible de purger threads.currentId', err); }
    if (previousId) {
      try { this.state.set(`threads.map.${previousId}`, null); } catch (err) { console.warn('[App] Impossible de purger threads.map', err); }
    }
    try { localStorage.removeItem('emergence.threadId'); } catch (_) {}
  }

  async _recoverInaccessibleThread(previousId) {
    console.warn(`[App] Thread ${previousId} inaccessible. Regeneration en cours.`);
    this._purgePersistedThreadId(previousId);
    const created = await api.createThread({ type: 'chat', title: 'Conversation' });
    return created?.id ?? null;
  }

  _isThreadInaccessibleError(error) {
    if (!error) return false;
    const status = error?.status ?? error?.response?.status ?? error?.cause?.status ?? null;
    if (status !== 403 && status !== 404) return false;
    const codeCandidate = error?.code ?? error?.detail_code ?? error?.errorCode;
    if (typeof codeCandidate === 'string' && THREAD_INACCESSIBLE_CODES.has(codeCandidate.trim().toLowerCase())) {
      return true;
    }
    const detailCandidates = [
      error?.detail,
      error?.message,
      error?.response?.detail,
      error?.response?.data?.detail,
      error?.body?.detail,
      error?.body?.message,
      error?.cause?.detail,
    ].filter((value) => typeof value === 'string' && value);
    if (!detailCandidates.length) return false;
    return detailCandidates.some((value) => value.toLowerCase().includes(THREAD_INACCESSIBLE_MARKER));
  }

  _isValidThreadId(value) {
    if (typeof value !== 'string') return false;
    const candidate = value.trim();
    if (!candidate) return false;
    if (THREAD_ID_HEX_RE.test(candidate) || THREAD_ID_UUID_RE.test(candidate)) {
      return true;
    }
    if (/^[a-z0-9][a-z0-9_-]{2,}$/i.test(candidate) && !candidate.toLowerCase().startsWith('session-')) {
      return true;
    }
    return false;
  }

  async loadModule(moduleId) {
    if (this.modules[moduleId]) return this.modules[moduleId];
    const moduleLoader = moduleLoaders[moduleId];
    if (!moduleLoader) { console.error(`[App] Critical: no loader registered for "${moduleId}".`); return null; }
    try {
      const module = await moduleLoader();
      const ModuleClass = module.default || module[Object.keys(module)[0]];
      const moduleInstance = new ModuleClass(this.eventBus, this.state);
      moduleInstance.init?.();
      this.modules[moduleId] = moduleInstance;
      console.log(`[App] Module ${moduleId} initialized and cached.`);
      return moduleInstance;
    } catch (error) {
      console.error(`[App] Critical: failed to load module "${moduleId}".`, error);
      return null;
    }
  }

  /**
   * Assure qu'un thread courant existe et charge son contenu.
   * - Cherche le dernier thread type=chat (limit=1)
    * - Sinon en cree un
   * - Stocke l'id dans state.threads.currentId
   * - Charge le thread (messages_limit=50) et le stocke dans state.threads.map.{id}
   * - Emet 'threads:ready' puis 'threads:loaded'
   */
  async ensureCurrentThread() {
    try {
      let currentId = this.state.get('threads.currentId');
      let needsNewThread = false;

      // Si un currentId existe, vérifier s'il est archivé
      if (this._isValidThreadId(currentId)) {
        try {
          const threadData = await api.getThreadById(currentId, { messages_limit: 1 });
          const thread = threadData?.thread || threadData;
          if (thread?.archived === true) {
            console.log('[App] Thread courant archivé, création d\'un nouveau thread frais');
            needsNewThread = true;
            currentId = null; // Reset pour créer un nouveau thread
          }
        } catch (err) {
          // Si le thread n'est plus accessible, on en créera un nouveau
          console.warn('[App] Thread courant inaccessible, création d\'un nouveau thread', err);
          needsNewThread = true;
          currentId = null;
        }
      }

      if (!this._isValidThreadId(currentId)) {
        const list = await api.listThreads({ type: 'chat', limit: 1 });
        // tolere 'items' ou liste brute
        const found = Array.isArray(list?.items) ? list.items[0] : Array.isArray(list) ? list[0] : null;
        if (found?.id) {
          currentId = found.id;
        } else {
          const created = await api.createThread({ type: 'chat', title: 'Conversation' });
          currentId = created?.id;
        }
      }
      if (!this._isValidThreadId(currentId)) {
        return;
      }
      let activeThreadId = currentId;
      this._persistCurrentThreadId(activeThreadId);
      this.eventBus.emit('threads:ready', { id: activeThreadId });
      let threadPayload;
      try {
        threadPayload = await api.getThreadById(activeThreadId, { messages_limit: 50 });
      } catch (threadError) {
        if (this._isThreadInaccessibleError(threadError)) {
          const regeneratedId = await this._recoverInaccessibleThread(activeThreadId);
          if (!this._isValidThreadId(regeneratedId)) {
            return;
          }
          activeThreadId = regeneratedId;
          this._persistCurrentThreadId(activeThreadId);
          this.eventBus.emit('threads:ready', { id: activeThreadId });
          threadPayload = await api.getThreadById(activeThreadId, { messages_limit: 50 });
        } else {
          throw threadError;
        }
      }
      if (threadPayload?.id) {
        this.state.set(`threads.map.${threadPayload.id}`, threadPayload);
        this.eventBus.emit('threads:loaded', threadPayload);
        this._authToastShown = false;
        this._authBannerShown = false;
        try { this.state.set('chat.authRequired', false); }
        catch (stateErr) { console.warn('[App] Impossible de mettre a jour chat.authRequired', stateErr); }
        try { this.eventBus.emit?.(EVENTS.AUTH_RESTORED, { source: 'ensureCurrentThread', threadId: threadPayload.id }); }
        catch (emitErr) { console.warn('[App] Impossible d\'emettre ui:auth:restored', emitErr); }
      }
    } catch (error) {
      console.error('[App] ensureCurrentThread() a echoue :', error);
      if (this._isThreadInaccessibleError(error)) {
        return;
      }
      const status = error?.status ?? error?.response?.status ?? error?.cause?.status ?? null;
      const networkError = isNetworkError(error);
      if (AUTH_ERROR_STATUSES.has(status) || networkError) {
        const message = t('auth.login_required');
        const reason = networkError ? 'threads_boot_failed_network' : 'threads_boot_failed';
        const payload = { reason, status, message };
        try { this.state.set('chat.authRequired', true); }
        catch (stateErr) { console.warn('[App] Impossible de mettre a jour chat.authRequired', stateErr); }
        try { this.state.set('auth.hasToken', false); }
        catch (stateErr) { console.warn('[App] Impossible de mettre a jour auth.hasToken', stateErr); }
        try { this.eventBus.emit?.('auth:missing', payload); }
        catch (emitErr) { console.warn("[App] Impossible d'emettre auth:missing", emitErr); }
        if (!this._authBannerShown) {
          this._authBannerShown = true;
          try { this.eventBus.emit?.(EVENTS.AUTH_REQUIRED, payload); }
          catch (emitErr) { console.warn("[App] Impossible d'emettre ui:auth:required", emitErr); }
        }
        if (!this._authToastShown) {
          this._authToastShown = true;
          try { this.eventBus.emit?.('ui:toast', { kind: 'error', text: message }); }
          catch (toastErr) { console.warn("[App] Impossible d'emettre ui:toast", toastErr); }
        }
      }
    }
  }
  async showModule(moduleId, isInitialLoad = false) {
    if (!moduleId || !this.dom.content) return;
    const availableModules = this.getModuleConfig();
    const moduleIds = availableModules.map((m) => m.id);
    if (!moduleIds.includes(moduleId)) {
      moduleId = moduleIds[0] || 'chat';
    }
    if (this.isMemoryMenuOpen()) this.closeMemoryMenu();

    const previousModuleId = (this.activeModule && this.activeModule !== moduleId)
      ? this.activeModule
      : null;

    if (previousModuleId) {
      const previousInstance = this.modules[previousModuleId];
      if (previousInstance?.unmount) {
        try {
          previousInstance.unmount();
        } catch (error) {
          console.error(`[App] Failed to unmount module "${previousModuleId}"`, error);
        }
      }
      this.eventBus.emit(EVENTS.MODULE_HIDE, previousModuleId);

      if (modals && typeof modals.closeAll === 'function') {
        try {
          modals.closeAll();
        } catch (modalError) {
          console.error('[App] Failed to close modals while switching module.', modalError);
        }
      }
    }

    this.clearSkeleton();

    // Bootstrap thread AVANT le premier mount du module 'chat'
    // OU à chaque fois qu'on affiche le module 'chat' (fix mobile)
    if (isInitialLoad || moduleId === 'chat') {
      await this.ensureCurrentThread();
    }

    this.activeModule = moduleId;
    this.renderNavigation();
    this.closeMobileNav?.();

    this.dom.content.querySelectorAll('.tab-content').forEach((c) => {
      c.classList.remove('active');
      c.setAttribute('aria-hidden', 'true');
      c.hidden = true;
    });
    let container = this.dom.content.querySelector(`#tab-content-${moduleId}`);
    if (!container) container = this.createModuleContainer(moduleId);

    const moduleInstance = await this.loadModule(moduleId);
    if (moduleInstance?.mount) {
      container.hidden = false;
      container.setAttribute('aria-hidden', 'false');
      moduleInstance.mount(container);
      container.classList.add('active');
      this.eventBus.emit(EVENTS.MODULE_SHOW, moduleId);
    }

    if (isInitialLoad) {
      this.eventBus.emit(EVENTS.APP_READY);
      this.preloadOtherModules();
      this.scheduleOnboardingTour();
    }
  }

  preloadOtherModules() {
    console.log('[App] Preloading other modules');
    // Ne précharger que les modules essentiels pour éviter les erreurs 429
    const essentialModules = ['conversations', 'memory', 'documents'];
    this.getModuleConfig().forEach((m) => {
      if (m.id !== this.activeModule && essentialModules.includes(m.id)) {
        this.loadModule(m.id);
      }
    });
  }

  createModuleContainer(moduleId) {
    const container = document.createElement('div');
    container.id = `tab-content-${moduleId}`;
    container.className = 'tab-content';
    container.setAttribute('aria-hidden', 'true');
    container.hidden = true;
    this.dom.content?.appendChild(container);
    return container;
  }
  shouldShowOnboarding() {
    return false;
  }

  finishOnboarding(persist = true) {
    if (persist) {
      try { localStorage.setItem(ONBOARDING_STORAGE_KEY, '1'); } catch (_) {}
    }
    if (this.onboardingTour) {
      try { this.onboardingTour.destroy(); } catch (_) {}
    }
    this.onboardingRetryCount = 0;
    this.onboardingTour = null;
    this.onboardingScheduled = true;
  }

  buildOnboardingSteps() {
    const steps = [
      {
        id: 'chat',
        target: '[data-module-id="chat"]',
        title: 'Dialoguer',
        description: 'Envoyez vos messages et recevez les reponses coordonnees des agents.'
      },
      {
        id: 'references',
        target: '[data-module-id="references"]',
        title: 'A propos',
        description: 'Retrouvez les documents clefs et la vision du projet Emergence.'
      }
    ];
    return steps.filter((step) => step && document.querySelector(step.target));
  }

  scheduleOnboardingTour() {
    this.finishOnboarding(true);
  }
}



