/**
 * @module core/app
 * @description Cœur de l'application ÉMERGENCE - V35.0 "ThreadBootstrap"
 * - Bootstrap du thread courant au premier affichage (persist inter-sessions).
 * - Navigation déléguée inchangée.
 */

import { EVENTS } from '../shared/constants.js';
import { api } from '../shared/api-client.js'; // + Threads API

// [CORRECTION VITE]
const moduleLoaders = {
  chat: () => import('../features/chat/chat.js'),
  debate: () => import('../features/debate/debate.js'),
  documents: () => import('../features/documents/documents.js'),
  dashboard: () => import('../features/dashboard/dashboard.js'),
  memory: () => import('../features/memory/memory.js'),
};

export class App {
  constructor(eventBus, state) {
    this.eventBus = eventBus;
    this.state = state;
    this.initialized = false;

    this.dom = {
      appContainer: document.getElementById('app-container'),
      header: document.getElementById('app-header'),
      headerNav: document.getElementById('app-header-nav'),
      sidebar: document.getElementById('app-sidebar'),
      tabs: document.getElementById('app-tabs'),
      content: document.getElementById('app-content'),
      memoryOverlay: document.getElementById('memory-overlay'),
    };

    this.modules = {};
    this.moduleConfig = [
      {
        id: 'chat',
        name: 'Dialogue',
        icon: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="8.5" cy="8" r="3"></circle><path d="M3 18c0-3 3.5-5.5 7.5-5.5S18 15 18 18"></path><circle cx="16" cy="9.5" r="2.5"></circle><path d="M13.5 18c0-2 2.2-3.75 4.5-3.75S22.5 16 22.5 18"></path></svg>'
      },
      { id: 'debate', name: 'Débats', icon: '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M12 20.25c4.97 0 9-3.694 9-8.25s-4.03-8.25-9-8.25S3 7.444 3 12c0 2.104.859 4.023 2.273 5.48.432.447.74 1.04.586 1.641a4.483 4.483 0 01-.923 1.785A5.969 5.969 0 006 21c1.282 0 2.47-.402 3.445-1.087.81.22 1.668.337 2.555.337z" /></svg>' },
      { id: 'documents', name: 'Documents', icon: '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" /></svg>' },
      { id: 'dashboard', name: 'Cockpit', icon: '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M10.5 6a7.5 7.5 0 100 15 7.5 7.5 0 000-15z" /><path stroke-linecap="round" stroke-linejoin="round" d="M10.5 10.5c0 .678-.291 1.32-.782 1.752L6 15.252M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>' },
      {
        id: 'memory',
        name: 'Mémoire',
        icon: '<svg class="nav-icon-brain" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true" focusable="false"><path d="M9.1 3.5c-2.1 0-3.8 1.66-3.8 3.7v1.08A3.6 3.6 0 0 0 3 11.9a3.55 3.55 0 0 0 2.08 3.2c.19.86.19 1.78 0 2.64A3.05 3.05 0 0 0 8 21h3V3.5H9.1z"></path><path d="M14.9 3.5c2.1 0 3.8 1.66 3.8 3.7v1.08A3.6 3.6 0 0 1 21 11.9a3.55 3.55 0 0 1-2.08 3.2c-.19.86-.19 1.78 0 2.64A3.05 3.05 0 0 1 16 21h-3V3.5h1.9z"></path><path d="M11 7.5h-1"></path><path d="M14 7.5h-1"></path><path d="M11 11.5h-1"></path><path d="M14 11.5h-1"></path><path d="M11 15.5h-1"></path><path d="M14 15.5h-1"></path></svg>'
      },
    ];
    this.activeModule = 'chat';

    console.log('✅ App V35.0 (ThreadBootstrap) Initialisée.');
    this.init();
  }

  init() {
    if (this.initialized) return;
    this.renderNavigation();
    this.listenToNavEvents();
    this.bootstrapFeatures();
    this.initialized = true;
  }

  renderNavigation() {
    if (!this.dom.tabs) return;
    const navItemsHTML = this.moduleConfig.map((m) => {
      const navClasses = ['nav-item'];
      const linkClasses = ['nav-link'];
      const iconClasses = ['nav-icon', `nav-icon--${m.id}`];
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
    this.dom.tabs.innerHTML = navItemsHTML;
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

  async loadModule(moduleId) {
    if (this.modules[moduleId]) return this.modules[moduleId];
    const moduleLoader = moduleLoaders[moduleId];
    if (!moduleLoader) { console.error(`❌ CRITICAL: Aucun chargeur de module pour "${moduleId}".`); return null; }
    try {
      const module = await moduleLoader();
      const ModuleClass = module.default || module[Object.keys(module)[0]];
      const moduleInstance = new ModuleClass(this.eventBus, this.state);
      moduleInstance.init?.();
      this.modules[moduleId] = moduleInstance;
      console.log(`✅ Module ${moduleId} initialisé et mis en cache.`);
      return moduleInstance;
    } catch (error) {
      console.error(`❌ CRITICAL: Échec du chargement du module "${moduleId}".`, error);
      return null;
    }
  }

  /**
   * Assure qu'un thread courant existe et charge son contenu.
   * - Cherche le dernier thread type=chat (limit=1)
   * - Sinon en crée un
   * - Stocke l'id dans state.threads.currentId
   * - Charge le thread (messages_limit=50) et le stocke dans state.threads.map.{id}
   * - Emet 'threads:ready' puis 'threads:loaded'
   */
  async ensureCurrentThread() {
    try {
      let currentId = this.state.get('threads.currentId');
      if (!currentId || typeof currentId !== 'string' || currentId.length < 8) {
        const list = await api.listThreads({ type: 'chat', limit: 1 });
        // tolère 'items' ou liste brute
        const found = Array.isArray(list?.items) ? list.items[0] : Array.isArray(list) ? list[0] : null;
        if (found?.id) {
          currentId = found.id;
        } else {
          const created = await api.createThread({ type: 'chat', title: 'Conversation' });
          currentId = created?.id;
        }
      }

      if (currentId) {
        this.state.set('threads.currentId', currentId);
        this._syncSessionWithThread(currentId);
        try { localStorage.setItem('emergence.threadId', currentId); } catch (_) {}
        this.eventBus.emit('threads:ready', { id: currentId });
        const thread = await api.getThreadById(currentId, { messages_limit: 50 });
        if (thread?.id) {
          this.state.set(`threads.map.${thread.id}`, thread);
          this._syncSessionWithThread(thread.id);
          this.eventBus.emit('threads:loaded', thread);
        }
      }
    } catch (error) {
      console.error('[App] ensureCurrentThread() a échoué :', error);
    }
  }

  async showModule(moduleId, isInitialLoad = false) {
    if (!moduleId || !this.dom.content) return;
    if (this.isMemoryMenuOpen()) this.closeMemoryMenu();
    this.clearSkeleton();

    // Bootstrap thread AVANT le premier mount du module 'chat'
    if (isInitialLoad) {
      await this.ensureCurrentThread();
    }

    this.activeModule = moduleId;
    this.renderNavigation();

    this.dom.content.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    let container = this.dom.content.querySelector(`#tab-content-${moduleId}`);
    if (!container) container = this.createModuleContainer(moduleId);

    const moduleInstance = await this.loadModule(moduleId);
    if (moduleInstance?.mount) {
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
    console.log('⚡️ Pré-chargement des autres modules…');
    this.moduleConfig.forEach(m => { if (m.id !== this.activeModule) this.loadModule(m.id); });
  }

  createModuleContainer(moduleId) {
    const container = document.createElement('div');
    container.id = `tab-content-${moduleId}`;
    container.className = 'tab-content';
    this.dom.content?.appendChild(container);
    return container;
  }
}
