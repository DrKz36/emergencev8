/**
 * @module core/app
 * @description Coeur de l'application ÉMERGENCE - V34.0 "Concordance"
 * - Correction du chargement des modules pour être 100% compatible avec Vite.
 * - Correction du rendu de la navigation pour éviter la duplication du contenu sidebar/header.
 * - Architecture de chargement plus robuste et explicite.
 */
import { EVENTS } from '../shared/constants.js';

// [CORRECTION VITE]
// On définit une carte statique des modules.
// Cela permet à Vite d'analyser et de préparer tous les modules nécessaires au moment du build,
// résolvant ainsi l'erreur d'import dynamique.
const moduleLoaders = {
    chat: () => import('../features/chat/chat.js'),
    debate: () => import('../features/debate/debate.js'),
    documents: () => import('../features/documents/documents.js'),
    dashboard: () => import('../features/dashboard/dashboard.js'),
};

export class App {
    constructor(eventBus, state) {
        this.eventBus = eventBus;
        this.state = state;
        this.initialized = false;

        this.dom = {
            appContainer: document.getElementById('app-container'),
            header: document.getElementById('app-header'),
            headerNav: document.getElementById('app-header-nav'), // L'en-tête pour les onglets d'agents
            sidebar: document.getElementById('app-sidebar'),
            tabs: document.getElementById('app-tabs'), // La sidebar pour la navigation principale
            content: document.getElementById('app-content'),
        };

        this.modules = {}; 
        this.moduleConfig = [
            { id: 'chat', name: 'Dialogue', icon: '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M20.25 8.511c.884.284 1.5 1.128 1.5 2.097v4.286c0 1.136-.847 2.1-1.98 2.193l-3.72 3.72a1.125 1.125 0 01-1.59 0l-3.72-3.72h-1.294a2.126 2.126 0 01-2.125-2.125v-4.286c0-.97.616-1.813 1.5-2.097m6.02-3.093a2.125 2.125 0 00-2.125-2.125H7.5c-1.178 0-2.125.947-2.125 2.125v4.286c0 .97-.616 1.813-1.5 2.097" /></svg>' },
            { id: 'debate', name: 'Débats', icon: '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M12 20.25c4.97 0 9-3.694 9-8.25s-4.03-8.25-9-8.25S3 7.444 3 12c0 2.104.859 4.023 2.273 5.48.432.447.74 1.04.586 1.641a4.483 4.483 0 01-.923 1.785A5.969 5.969 0 006 21c1.282 0 2.47-.402 3.445-1.087.81.22 1.668.337 2.555.337z" /></svg>' },
            { id: 'documents', name: 'Documents', icon: '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" /></svg>' },
            { id: 'dashboard', name: 'Cockpit', icon: '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M10.5 6a7.5 7.5 0 100 15 7.5 7.5 0 000-15z" /><path stroke-linecap="round" stroke-linejoin="round" d="M10.5 10.5c0 .678-.291 1.32-.782 1.752L6 15.252M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>' }, 
        ];
        this.activeModule = 'chat';

        console.log("✅ App V34.0 (Concordance) Initialisée.");
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
        // [CORRECTION AFFICHAGE]
        // On ne cible que la sidebar (`this.dom.tabs`) pour la navigation principale.
        if (!this.dom.tabs) return;
        
        const navItemsHTML = this.moduleConfig.map(module => `
            <li class="nav-item">
                <a href="#" class="nav-link ${this.activeModule === module.id ? 'active' : ''}" data-module-id="${module.id}">
                    <span class="nav-icon">${module.icon}</span>
                    <span class="nav-text">${module.name}</span>
                </a>
            </li>
        `).join('');

        this.dom.tabs.innerHTML = navItemsHTML;
    }

    listenToNavEvents() {
        const handleNavClick = (e) => {
            e.preventDefault();
            const link = e.target.closest('.nav-link');
            if (link && link.dataset.moduleId) {
                this.showModule(link.dataset.moduleId);
            }
        };
        this.dom.sidebar.addEventListener('click', handleNavClick);
        this.dom.header.addEventListener('click', handleNavClick);
    }

    bootstrapFeatures() {
        this.showModule(this.activeModule, true);
    }

    // --- NEW: retire les placeholders skeleton pré-boot ---
    clearSkeleton() {
        if (this._skeletonCleared) return;
        this._skeletonCleared = true;
        const c = this.dom.content;
        if (!c) return;
        c.querySelectorAll('.skeleton').forEach(el => el.remove());
    }

    async loadModule(moduleId) {
        if (this.modules[moduleId]) return this.modules[moduleId];

        // [CORRECTION VITE] Utilisation de la carte de chargement statique.
        const moduleLoader = moduleLoaders[moduleId];
        if (!moduleLoader) {
            console.error(`❌ CRITICAL: Aucun chargeur de module défini pour "${moduleId}".`);
            return null;
        }

        try {
            const module = await moduleLoader();
            const ModuleClass = module.default || module[Object.keys(module)[0]];
            const moduleInstance = new ModuleClass(this.eventBus, this.state);
            moduleInstance.init(); // Initialisation logique unique
            this.modules[moduleId] = moduleInstance;
            console.log(`✅ Module ${moduleId} initialisé et mis en cache.`);
            return moduleInstance;
        } catch (error) {
            console.error(`❌ CRITICAL: Échec du chargement du module "${moduleId}".`, error);
            return null;
        }
    }

    async showModule(moduleId, isInitialLoad = false) {
        if (!moduleId) return;

        // Retire immédiatement les skeletons qui occupent le haut de la zone principale
        this.clearSkeleton();
        
        this.activeModule = moduleId;
        this.renderNavigation(); // Met à jour l'UI de navigation (uniquement la sidebar maintenant)

        this.dom.content.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        let container = this.dom.content.querySelector(`#tab-content-${moduleId}`);
        if (!container) {
            container = this.createModuleContainer(moduleId);
        }
        
        const moduleInstance = await this.loadModule(moduleId);
        if (moduleInstance && typeof moduleInstance.mount === 'function') {
            moduleInstance.mount(container); // Montage graphique
            container.classList.add('active');
            this.eventBus.emit(EVENTS.MODULE_SHOW, moduleId);
        }

        if (isInitialLoad) {
            this.eventBus.emit(EVENTS.APP_READY);
            this.preloadOtherModules();
        }
    }

    preloadOtherModules() {
        console.log("⚡️ Pré-chargement des autres modules en arrière-plan...");
        this.moduleConfig.forEach(module => {
            if (module.id !== this.activeModule) {
                this.loadModule(module.id);
            }
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
