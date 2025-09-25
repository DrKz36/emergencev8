/**
 * @module core/app
 * @description Câ”¼Ã´ur de l'application â”œÃ«MERGENCE - V35.0 "ThreadBootstrap"
 * - Bootstrap du thread courant au premier affichage (persist inter-sessions).
 * - Navigation dâ”œÂ®lâ”œÂ®guâ”œÂ®e inchangâ”œÂ®e.
 */

import { EVENTS } from '../shared/constants.js';
import { api } from '../shared/api-client.js'; // + Threads API
import { t } from '../shared/i18n.js';
import { modals } from '../components/modals.js';

const AUTH_ERROR_STATUSES = new Set([401, 403, 419, 440]);
const THREAD_INACCESSIBLE_MARKER = 'thread non accessible pour cet utilisateur';
const THREAD_INACCESSIBLE_CODES = new Set(['thread_not_accessible', 'thread_inaccessible']);

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
  dashboard: () => import('../features/dashboard/dashboard.js'),
  memory: () => import('../features/memory/memory.js'),
  admin: () => import('../features/admin/admin.js'),
};

export class App {
  constructor(eventBus, state) {
    this.eventBus = eventBus;
    this.state = state;
    this.initialized = false;
    this._authToastShown = false;
    this._authBannerShown = false;

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
    };

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
        icon: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 6.75h14"></path><path d="M5 12h10"></path><path d="M5 17.25h6"></path><path d="M17 17.25h2"></path></svg>'
      },
      { id: 'documents', name: 'Documents', icon: '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" /></svg>' },
      { id: 'debate', name: 'Debats', icon: '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M12 20.25c4.97 0 9-3.694 9-8.25s-4.03-8.25-9-8.25S3 7.444 3 12c0 2.104.859 4.023 2.273 5.48.432.447.74 1.04.586 1.641a4.483 4.483 0 01-.923 1.785A5.969 5.969 0 006 21c1.282 0 2.47-.402 3.445-1.087.81.22 1.668.337 2.555.337z" /></svg>' },
      { id: 'dashboard', name: 'Cockpit', icon: '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M10.5 6a7.5 7.5 0 100 15 7.5 7.5 0 000-15z" /><path stroke-linecap="round" stroke-linejoin="round" d="M10.5 10.5c0 .678-.291 1.32-.782 1.752L6 15.252M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>' },
      {
        id: 'memory',
        name: 'Memoire',
        icon: '<svg class="nav-icon-brain" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true" focusable="false"><path d="M9.1 3.5c-2.1 0-3.8 1.66-3.8 3.7v1.08A3.6 3.6 0 0 0 3 11.9a3.55 3.55 0 0 0 2.08 3.2c.19.86.19 1.78 0 2.64A3.05 3.05 0 0 0 8 21h3V3.5H9.1z"></path><path d="M14.9 3.5c2.1 0 3.8 1.66 3.8 3.7v1.08A3.6 3.6 0 0 1 21 11.9a3.55 3.55 0 0 1-2.08 3.2c-.19.86-.19 1.78 0 2.64A3.05 3.05 0 0 1 16 21h-3V3.5h1.9z"></path><path d="M11 7.5h-1"></path><path d="M14 7.5h-1"></path><path d="M11 11.5h-1"></path><path d="M14 11.5h-1"></path><path d="M11 15.5h-1"></path><path d="M14 15.5h-1"></path></svg>'
      },

      {
        id: 'admin',
        name: 'Admin',
        icon: '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M10.5 6a3.75 3.75 0 117 0m-7 0H6.75A2.25 2.25 0 004.5 8.25v7.5A2.25 2.25 0 006.75 18h8.5A2.25 2.25 0 0017.5 15.75V11.5m0-5.5v5.25" /></svg>',
        requiresRole: 'admin',
      },
    ];
    this.activeModule = 'chat';
    this.closeMobileNav = null;
    this._mobileNavSetup = false;

    if (this.state?.subscribe) {
      try {
        this.state.subscribe('auth.role', () => {
          this.renderNavigation();
        });
      } catch (err) {
        console.warn('[App] Impossible de souscrire a auth.role', err);
      }
    }

    console.log('Ã”Â£Ã  App V35.0 (ThreadBootstrap) Initialisâ”œÂ®e.');
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
    }
  }

  setupMobileNav() {
    if (this._mobileNavSetup) return;
    const toggle = this.dom.mobileNavToggle;
    const navContainer = this.dom.headerNavContainer;
    if (!toggle || !navContainer) return;

    const applyState = (expanded) => {
      toggle.setAttribute('aria-expanded', expanded ? 'true' : 'false');
      navContainer.classList.toggle('is-open', expanded);
      navContainer.setAttribute('aria-hidden', expanded ? 'false' : 'true');
      if (typeof document !== 'undefined' && document.body) {
        document.body.classList.toggle('mobile-nav-open', expanded);
      }
    };

    const closeNav = () => applyState(false);
    const openNav = () => applyState(true);

    toggle.addEventListener('click', (event) => {
      event.preventDefault();
      event.stopPropagation();
      const expanded = toggle.getAttribute('aria-expanded') === 'true';
      if (expanded) {
        closeNav();
      } else {
        openNav();
      }
    });

    document.addEventListener('click', (event) => {
      if (!navContainer.classList.contains('is-open')) return;
      if (navContainer.contains(event.target) || toggle.contains(event.target)) return;
      closeNav();
    });

    document.addEventListener('keydown', (event) => {
      if (event.key !== 'Escape') return;
      if (!navContainer.classList.contains('is-open')) return;
      closeNav();
    });

    applyState(false);
    this.closeMobileNav = closeNav;
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
      this.showModule(link.dataset.moduleId);
    };
    root.addEventListener('click', handleNavClick);
    this.dom.header?.addEventListener('click', handleNavClick);
    this.dom.headerNavContainer?.addEventListener('click', handleNavClick);

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

  _syncSessionWithThread(threadId) {
    if (!threadId || typeof threadId !== 'string') return;
    try {
      const current = this.state.get('websocket.sessionId');
      if (current === threadId) return;
      this.state.set('websocket.sessionId', threadId);
    } catch (err) {
      console.warn('[App] sync sessionId -> threadId impossible', err);
    }
  }

  _persistCurrentThreadId(threadId) {
    if (!this._isValidThreadId(threadId)) return;
    try { this.state.set('threads.currentId', threadId); } catch (err) { console.warn('[App] Impossible de mettre a jour threads.currentId', err); }
    this._syncSessionWithThread(threadId);
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
    return typeof value === 'string' && value.length >= 8;
  }

  async loadModule(moduleId) {
    if (this.modules[moduleId]) return this.modules[moduleId];
    const moduleLoader = moduleLoaders[moduleId];
    if (!moduleLoader) { console.error(`Ã”Ã˜Ã® CRITICAL: Aucun chargeur de module pour "${moduleId}".`); return null; }
    try {
      const module = await moduleLoader();
      const ModuleClass = module.default || module[Object.keys(module)[0]];
      const moduleInstance = new ModuleClass(this.eventBus, this.state);
      moduleInstance.init?.();
      this.modules[moduleId] = moduleInstance;
      console.log(`Ã”Â£Ã  Module ${moduleId} initialisâ”œÂ® et mis en cache.`);
      return moduleInstance;
    } catch (error) {
      console.error(`Ã”Ã˜Ã® CRITICAL: â”œÃ«chec du chargement du module "${moduleId}".`, error);
      return null;
    }
  }

  /**
   * Assure qu'un thread courant existe et charge son contenu.
   * - Cherche le dernier thread type=chat (limit=1)
   * - Sinon en crâ”œÂ®e un
   * - Stocke l'id dans state.threads.currentId
   * - Charge le thread (messages_limit=50) et le stocke dans state.threads.map.{id}
   * - Emet 'threads:ready' puis 'threads:loaded'
   */
  async ensureCurrentThread() {
    try {
      let currentId = this.state.get('threads.currentId');
      if (!this._isValidThreadId(currentId)) {
        const list = await api.listThreads({ type: 'chat', limit: 1 });
        // tol├¿re 'items' ou liste brute
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
        this._syncSessionWithThread(threadPayload.id);
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
    if (isInitialLoad) {
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
    }
  }

  preloadOtherModules() {
    console.log('Ã”ÃœÃ­Â´Â©Ã… Prâ”œÂ®-chargement des autres modulesÃ”Ã‡Âª');
    this.getModuleConfig().forEach((m) => { if (m.id !== this.activeModule) this.loadModule(m.id); });
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
}





