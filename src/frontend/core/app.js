/**
 * @module core/app
 * @description Coeur de l'application ÉMERGENCE - V35.2 "Concordance/Mobile"
 * - APP_READY émis dès le 1er module monté (pas de gating WS)
 * - Préchargement déféré (idle) en pré-import (sans init UI)
 */
import { EVENTS } from '../shared/constants.js';

const moduleLoaders = {
  chat:      () => import('../features/chat/chat.js'),
  debate:    () => import('../features/debate/debate.js'),
  documents: () => import('../features/documents/documents.js'),
  dashboard: () => import('../features/dashboard/dashboard.js'),
};

export class App {
  constructor(eventBus, state) {
    this.eventBus = eventBus;
    this.state = state;

    this.dom = {
      appContainer: document.getElementById('app-container'),
      header:       document.getElementById('app-header'),
      headerNav:    document.getElementById('app-header-nav'),
      sidebar:      document.getElementById('app-sidebar'),
      tabs:         document.getElementById('app-tabs'),
      content:      document.getElementById('app-content'),
    };

    this.modules = {};
    this._preloaded = {};
    this._wsReady = false;
    this._initialModuleMounted = false;
    this._appReadySent = false;

    this.moduleConfig = [
      {
        id: 'chat',
        name: 'Dialogue',
        icon: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="8.5" cy="8" r="3"></circle><path d="M3 18c0-3 3.5-5.5 7.5-5.5S18 15 18 18"></path><circle cx="16" cy="9.5" r="2.5"></circle><path d="M13.5 18c0-2 2.2-3.75 4.5-3.75S22.5 16 22.5 18"></path></svg>'
      },
      { id: 'debate', name: 'Débats',    icon: '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M12 20.25c4.97 0 9-3.694 9-8.25s-4.03-8.25-9-8.25S3 7.444 3 12c0 2.104.859 4.023 2.273 5.48.432.447.74 1.04.586 1.641a4.483 4.483 0 01-.923 1.785A5.969 5.969 0 006 21c1.282 0 2.47-.402 3.445-1.087.81.22 1.668.337 2.555.337z" /></svg>' },
      { id: 'documents', name: 'Documents', icon: '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" /></svg>' },
      { id: 'dashboard', name: 'Cockpit',  icon: '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M10.5 6a7.5 7.5 0 100 15 7.5 7.5 0 000-15z" /><path stroke-linecap="round" stroke-linejoin="round" d="M10.5 10.5c0 .678-.291 1.32-.782 1.752L6 15.252M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>' },
    ];
    this.activeModule = 'chat';

    // On garde le hook WS (pour infos/indicateurs éventuels), mais on ne gate plus APP_READY
    this.eventBus.on('ws:session_established', () => { this._wsReady = true; });

    console.log('✅ App V35.2 (Concordance/Mobile) Initialisée.');
    this.init();
  }

  init() {
    if (this.initialized) return;
    this.renderNavigation();
    this.listenToNavEvents();
    this.bootstrapFeatures();
    window.addEventListener('resize', () => this.renderNavigation());
    this.initialized = true;
  }

  isMobile() { return window.matchMedia('(max-width: 767px)').matches; }

  renderNavigation() {
    if (this.dom.tabs) {
      const sidebarHTML = this.moduleConfig.map(m => `
        <li class="nav-item">
          <a href="#" class="nav-link ${this.activeModule === m.id ? 'active' : ''}" data-module-id="${m.id}">
            <span class="nav-icon">${m.icon}</span>
            <span class="nav-text">${m.name}</span>
          </a>
        </li>
      `).join('');
      this.dom.tabs.innerHTML = sidebarHTML;
    }
    if (this.dom.headerNav) {
      if (this.isMobile()) {
        const headerHTML = this.moduleConfig.map(m => `
          <button class="header-nav-button ${this.activeModule === m.id ? 'active' : ''}" data-module-id="${m.id}" aria-label="${m.name}" title="${m.name}">
            ${m.icon}
          </button>
        `).join('');
        this.dom.headerNav.innerHTML = headerHTML;
      } else {
        this.dom.headerNav.innerHTML = '';
      }
    }
  }

  listenToNavEvents() {
    const handleNavClick = (e) => {
      const link = e.target.closest('.nav-link, .header-nav-button');
      if (!link) return;
      e.preventDefault();
      const id = link.dataset.moduleId;
      if (id) this.showModule(id);
    };
    if (this.dom.sidebar) this.dom.sidebar.addEventListener('click', handleNavClick);
    if (this.dom.header)  this.dom.header.addEventListener('click', handleNavClick);
  }

  bootstrapFeatures() { this.showModule(this.activeModule, true); }

  clearSkeleton() {
    if (this._skeletonCleared) return;
    this._skeletonCleared = true;
    const c = this.dom.content;
    if (!c) return;
    c.querySelectorAll('.skeleton').forEach(el => el.remove());
  }

  preimportModule(moduleId) {
    if (this.modules[moduleId] || this._preloaded[moduleId]) return;
    const loader = moduleLoaders[moduleId];
    if (!loader) return;
    const p = loader().then(exports => { this._preloaded[moduleId] = exports; return exports; })
                      .catch(() => { delete this._preloaded[moduleId]; });
    this._preloaded[moduleId] = p;
  }

  async loadModule(moduleId) {
    if (this.modules[moduleId]) return this.modules[moduleId];

    let exportsMod = this._preloaded[moduleId];
    try {
      if (exportsMod && typeof exportsMod.then === 'function') {
        exportsMod = await exportsMod; // attend le pré-import
      }
      if (!exportsMod) {
        exportsMod = await (moduleLoaders[moduleId] ? moduleLoaders[moduleId]() : null);
      }
      if (!exportsMod) {
        console.error(`❌ CRITICAL: Aucun chargeur pour "${moduleId}".`);
        return null;
      }
      const ModuleClass = exportsMod.default || exportsMod[Object.keys(exportsMod)[0]];
      const moduleInstance = new ModuleClass(this.eventBus, this.state);
      moduleInstance.init();
      this.modules[moduleId] = moduleInstance;
      console.log(`✅ Module ${moduleId} initialisé et mis en cache.`);
      return moduleInstance;
    } catch (error) {
      console.error(`❌ CRITICAL: Échec du chargement/instanciation du module "${moduleId}".`, error);
      return null;
    }
  }

  async showModule(moduleId, isInitialLoad = false) {
    if (!moduleId) return;

    if (this.activeModule === moduleId && !isInitialLoad) {
      this.eventBus.emit(EVENTS.MODULE_SHOW, moduleId);
      return;
    }

    this.clearSkeleton();
    this.activeModule = moduleId;
    this.renderNavigation();

    this.dom.content.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    let container = this.dom.content.querySelector(`#tab-content-${moduleId}`);
    if (!container) container = this.createModuleContainer(moduleId);

    const moduleInstance = await this.loadModule(moduleId);
    if (moduleInstance && typeof moduleInstance.mount === 'function') {
      moduleInstance.mount(container);
      container.classList.add('active');
      this.eventBus.emit(EVENTS.MODULE_SHOW, moduleId);
    }

    if (isInitialLoad) {
      this._initialModuleMounted = true;
      this._sendAppReadyFast(); // 🔑 pas de gating WS
    }
  }

  _sendAppReadyFast() {
    if (this._appReadySent) return;
    this._appReadySent = true;

    // double rAF pour garantir un paint stable avant de retirer le loader
    const afterPaint = (cb) => requestAnimationFrame(() => requestAnimationFrame(cb));
    afterPaint(() => {
      this.eventBus.emit(EVENTS.APP_READY);

      const idle = (cb) => (window.requestIdleCallback
        ? window.requestIdleCallback(cb, { timeout: 1500 })
        : setTimeout(cb, 250));

      idle(() => this.preloadOtherModules());
    });
  }

  preloadOtherModules() {
    console.log('⚡️ Pré-chargement (idle) des autres modules (pré-import sans init UI)…');
    this.moduleConfig.forEach(m => {
      if (m.id !== this.activeModule) this.preimportModule(m.id);
    });
  }

  createModuleContainer(moduleId) {
    const container = document.createElement('div');
    container.id = `tab-content-${moduleId}`;
    container.className = 'tab-content';
    this.dom.content.appendChild(container);
    return container;
  }
}
