// src/frontend/core/app.js  (V35.4)
import { EVENTS } from '../shared/constants.js';

const moduleLoaders = {
  chat:      () => import('../features/chat/chat.js'),
  threads:   () => import('../features/threads/threads-list.js'),
  debate:    () => import('../features/debate/debate.js'),
  documents: () => import('../features/documents/documents.js'),
  dashboard: () => import('../features/dashboard/dashboard.js'),
};

export class App {
  constructor(eventBus, state) {
    this.eventBus = eventBus; this.state = state;
    this.dom = {
      appContainer: document.getElementById('app-container'),
      header:       document.getElementById('app-header'),
      headerNav:    document.getElementById('app-header-nav'),
      sidebar:      document.getElementById('app-sidebar'),
      tabs:         document.getElementById('app-tabs'),
      content:      document.getElementById('app-content'),
    };
    this.modules = {}; this._preloaded = {};
    this._wsReady = false; this._initialModuleMounted = false; this._appReadySent = false;

    this.moduleConfig = [
      { id: 'chat',     name: 'Dialogue',      icon: '<svg ...></svg>' },
      { id: 'threads',  name: 'Conversations', icon: '<svg ...></svg>' },
      { id: 'debate',   name: 'Débats',        icon: '<svg ...></svg>' },
      { id: 'documents',name: 'Documents',     icon: '<svg ...></svg>' },
      { id: 'dashboard',name: 'Cockpit',       icon: '<svg ...></svg>' },
    ];
    this.activeModule = 'chat';
    this.eventBus.on('ws:session_established', () => { this._wsReady = true; });
    console.log('✅ App V35.4 (Concordance/Mobile+Threads) Initialisée.');
    this.init();
  }

  init(){ if(this.initialized) return; this.renderNavigation(); this.listenToNavEvents(); this.bootstrapFeatures();
    window.addEventListener('resize', () => this.renderNavigation()); this.initialized = true; }
  isMobile(){ return window.matchMedia('(max-width: 767px)').matches; }

  renderNavigation(){
    if (this.dom.tabs) {
      this.dom.tabs.innerHTML = this.moduleConfig.map(m => `
        <li class="nav-item"><a href="#" class="nav-link ${this.activeModule===m.id?'active':''}" data-module-id="${m.id}">
          <span class="nav-icon">${m.icon}</span><span class="nav-text">${m.name}</span></a></li>`).join('');
    }
    if (this.dom.headerNav) {
      this.dom.headerNav.innerHTML = this.isMobile() ? this.moduleConfig.map(m => `
        <button class="header-nav-button ${this.activeModule===m.id?'active':''}" data-module-id="${m.id}" title="${m.name}">${m.icon}</button>`).join('') : '';
    }
  }

  listenToNavEvents(){
    const click = (e) => { const el = e.target.closest('.nav-link,.header-nav-button'); if(!el) return;
      e.preventDefault(); const id = el.dataset.moduleId; if(id) this.showModule(id); };
    this.dom.sidebar && this.dom.sidebar.addEventListener('click', click);
    this.dom.header  && this.dom.header.addEventListener('click', click);
  }

  bootstrapFeatures(){ this.showModule(this.activeModule, true); }

  // ✅ enlève ENFIN les skeletons et fixe le conteneur pour le scroll
  clearSkeleton(){
    try {
      const skels = this.dom.content ? this.dom.content.querySelectorAll('.skeleton') : [];
      skels.forEach(el => el.remove());
      if (this.dom.content) {
        // garanties layout pour la zone centrale
        this.dom.content.style.minHeight = '0';
        this.dom.content.style.display = 'flex';
        this.dom.content.style.flexDirection = 'column';
      }
    } catch(_) {}
  }

  preimportModule(id){ if(this.modules[id]||this._preloaded[id]||!moduleLoaders[id]) return;
    this._preloaded[id]=moduleLoaders[id]().then(x=>{this._preloaded[id]=x; return x;}).catch(()=>{delete this._preloaded[id];}); }

  async loadModule(id){
    if (this.modules[id]) return this.modules[id];
    let exportsMod = this._preloaded[id]; if(exportsMod && typeof exportsMod.then==='function') exportsMod = await exportsMod;
    if(!exportsMod) exportsMod = await (moduleLoaders[id]?moduleLoaders[id]():null);
    if(!exportsMod) { console.error(`❌ Aucun chargeur pour "${id}".`); return null; }
    const Cls = exportsMod.default || exportsMod[Object.keys(exportsMod)[0]];
    const inst = new Cls(this.eventBus, this.state); typeof inst.init==='function' && inst.init();
    this.modules[id]=inst; console.log(`✅ Module ${id} initialisé et mis en cache.`); return inst;
  }

  async showModule(id, initial=false){
    if(!id) return;
    if(this.activeModule===id && !initial){ this.eventBus.emit(EVENTS.MODULE_SHOW, id); return; }
    this.clearSkeleton(); this.activeModule=id; this.renderNavigation();
    this.dom.content.querySelectorAll('.tab-content').forEach(c=>c.classList.remove('active'));
    let container = this.dom.content.querySelector(`#tab-content-${id}`); if(!container) container=this.createModuleContainer(id);
    const mod = await this.loadModule(id);
    if(mod && typeof mod.mount==='function'){ mod.mount(container); container.classList.add('active'); this.eventBus.emit(EVENTS.MODULE_SHOW, id); }
    if(initial){ this._initialModuleMounted=true; this._sendAppReadyFast(); }
  }

  _sendAppReadyFast(){ if(this._appReadySent) return; this._appReadySent=true;
    const afterPaint=cb=>requestAnimationFrame(()=>requestAnimationFrame(cb));
    afterPaint(()=>{ this.eventBus.emit(EVENTS.APP_READY);
      const idle=cb=>window.requestIdleCallback?window.requestIdleCallback(cb,{timeout:1500}):setTimeout(cb,250);
      idle(()=>this.preloadOtherModules()); }); }

  preloadOtherModules(){ console.log('⚡ Pré-chargement (idle)…');
    this.moduleConfig.forEach(m=>{ if(m.id!==this.activeModule) this.preimportModule(m.id); }); }

  createModuleContainer(id){ const el=document.createElement('div'); el.id=`tab-content-${id}`; el.className='tab-content';
    this.dom.content.appendChild(el); return el; }
}
