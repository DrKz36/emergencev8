/**
 * Settings Main Module
 * Integrates all settings components (models, UI, security)
 */

import { SettingsIcons, getIcon } from './settings-icons.js';
import { settingsModels } from './settings-models.js';
import { settingsUI } from './settings-ui.js';
import { settingsSecurity } from './settings-security.js';
import { settingsRAG } from './settings-rag.js';

export class Settings {
    constructor() {
        this.container = null;
        this.activeTab = 'models';
        this.modules = {
            models: settingsModels,
            ui: settingsUI,
            security: settingsSecurity,
            rag: settingsRAG
        };
        this.initialized = false;
        this.hasUnsavedChanges = false;
    }

    /**
     * Initialize settings
     */
    async init(containerId) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            console.error('Settings container not found');
            return;
        }

        this.render();
        await this.loadActiveView();
        this.initialized = true;
    }

    /**
     * Render settings structure
     */
    render() {
        this.container.innerHTML = `
            <div class="settings-container">
                <!-- Settings Header -->
                <div class="settings-main-header">
                    <div class="settings-title">
                        <h1>${getIcon('settings', 'header-icon')} Paramètres</h1>
                        <p class="settings-subtitle">Configuration et personnalisation</p>
                    </div>
                    <div class="settings-actions">
                        <button class="btn-reset-all" title="Tout réinitialiser">
                            ${getIcon('reset', 'btn-icon')} Réinitialiser tout
                        </button>
                        <button class="btn-save-all" title="Tout sauvegarder">
                            ${getIcon('save', 'btn-icon')} Tout sauvegarder
                        </button>
                    </div>
                </div>

                <!-- ÉMERGENCE Brand Panel -->
                <div class="emergence-brand-panel">
                    <img src="/assets/emergence_logo.png" alt="ÉMERGENCE" class="brand-logo">
                    <div class="brand-info">
                        <h2 class="brand-title">ÉMERGENCE V8</h2>
                        <p class="brand-version">Version 8.0.0</p>
                    </div>
                </div>

                <!-- Settings Navigation -->
                <div class="settings-nav">
                    <button class="settings-nav-item ${this.activeTab === 'models' ? 'active' : ''}"
                            data-tab="models">
                        <span class="nav-icon">${SettingsIcons.robot}</span>
                        <div class="nav-content">
                            <span class="nav-label">Modèles IA</span>
                            <span class="nav-hint">Configuration des agents</span>
                        </div>
                    </button>
                    <button class="settings-nav-item ${this.activeTab === 'rag' ? 'active' : ''}"
                            data-tab="rag">
                        <span class="nav-icon">${SettingsIcons.database}</span>
                        <div class="nav-content">
                            <span class="nav-label">RAG</span>
                            <span class="nav-hint">Recherche sémantique</span>
                        </div>
                    </button>
                    <button class="settings-nav-item ${this.activeTab === 'ui' ? 'active' : ''}"
                            data-tab="ui">
                        <span class="nav-icon">${SettingsIcons.palette}</span>
                        <div class="nav-content">
                            <span class="nav-label">Interface</span>
                            <span class="nav-hint">Thème et apparence</span>
                        </div>
                    </button>
                </div>

                <!-- Settings Content -->
                <div class="settings-main-content">
                    <!-- Models Tab -->
                    <div class="settings-panel ${this.activeTab === 'models' ? 'active' : ''}"
                         data-panel="models">
                        <div id="settings-models-container"></div>
                    </div>

                    <!-- RAG Tab -->
                    <div class="settings-panel ${this.activeTab === 'rag' ? 'active' : ''}"
                         data-panel="rag">
                        <div id="settings-rag-container"></div>
                    </div>

                    <!-- UI Tab -->
                    <div class="settings-panel ${this.activeTab === 'ui' ? 'active' : ''}"
                         data-panel="ui">
                        <div id="settings-ui-container"></div>
                    </div>
                </div>

                <!-- Unsaved Changes Warning -->
                ${this.hasUnsavedChanges ? `
                    <div class="unsaved-changes-bar">
                        <span class="unsaved-icon">${SettingsIcons.warning}</span>
                        <span class="unsaved-text">Vous avez des modifications non sauvegardées</span>
                        <div class="unsaved-actions">
                            <button class="btn-discard">Annuler</button>
                            <button class="btn-save-changes">Sauvegarder</button>
                        </div>
                    </div>
                ` : ''}
            </div>
        `;

        this.attachEventListeners();
    }

    /**
     * Render about section
     */
    renderAbout() {
        return `
            <div class="settings-about">
                <div class="about-sections">
                    <div class="about-section full-width">
                        <h3>${getIcon('clipboard', 'section-icon')} Informations Système</h3>
                        <div class="about-info-grid">
                            <div class="info-item">
                                <span class="info-label">Version:</span>
                                <span class="info-value">8.0.0</span>
                            </div>
                            <div class="info-item">
                                <span class="info-label">Build:</span>
                                <span class="info-value">${Date.now()}</span>
                            </div>
                            <div class="info-item">
                                <span class="info-label">Modules:</span>
                                <span class="info-value">15 modules actifs</span>
                            </div>
                        </div>
                    </div>

                    <div class="about-section full-width">
                        <h3>${getIcon('link', 'section-icon')} Liens Utiles</h3>
                        <div class="about-links">
                            <a href="#" class="about-link" data-action="documentation">${getIcon('book', 'link-icon')} Documentation</a>
                            <a href="#" class="about-link" data-action="support">${getIcon('messageCircle', 'link-icon')} Support</a>
                            <a href="#" class="about-link" data-action="bug-report">${getIcon('bug', 'link-icon')} Signaler un bug</a>
                        </div>
                    </div>

                    <div class="about-section full-width">
                        <h3>${getIcon('package', 'section-icon')} Modules Installés</h3>
                        <div class="modules-list">
                            <div class="module-item">
                                <span class="module-icon">${SettingsIcons.home}</span>
                                <div class="module-info">
                                    <span class="module-name">Home</span>
                                    <span class="module-version">v1.0</span>
                                </div>
                                <span class="module-status status-active">${SettingsIcons.check}</span>
                            </div>
                            <div class="module-item">
                                <span class="module-icon">${SettingsIcons.dashboard}</span>
                                <div class="module-info">
                                    <span class="module-name">Cockpit</span>
                                    <span class="module-version">v3.0</span>
                                </div>
                                <span class="module-status status-active">${SettingsIcons.check}</span>
                            </div>
                            <div class="module-item">
                                <span class="module-icon">${SettingsIcons.messageCircle}</span>
                                <div class="module-info">
                                    <span class="module-name">Chat</span>
                                    <span class="module-version">v2.5</span>
                                </div>
                                <span class="module-status status-active">${SettingsIcons.check}</span>
                            </div>
                            <div class="module-item">
                                <span class="module-icon">${SettingsIcons.mic}</span>
                                <div class="module-info">
                                    <span class="module-name">Voice</span>
                                    <span class="module-version">v1.2</span>
                                </div>
                                <span class="module-status status-active">${SettingsIcons.check}</span>
                            </div>
                            <div class="module-item">
                                <span class="module-icon">${SettingsIcons.brain}</span>
                                <div class="module-info">
                                    <span class="module-name">Memory</span>
                                    <span class="module-version">v2.0</span>
                                </div>
                                <span class="module-status status-active">${SettingsIcons.check}</span>
                            </div>
                            <div class="module-item">
                                <span class="module-icon">${SettingsIcons.thoughtBubble}</span>
                                <div class="module-info">
                                    <span class="module-name">Debate</span>
                                    <span class="module-version">v1.5</span>
                                </div>
                                <span class="module-status status-active">${SettingsIcons.check}</span>
                            </div>
                            <div class="module-item">
                                <span class="module-icon">${SettingsIcons.document}</span>
                                <div class="module-info">
                                    <span class="module-name">Documents</span>
                                    <span class="module-version">v1.8</span>
                                </div>
                                <span class="module-status status-active">${SettingsIcons.check}</span>
                            </div>
                            <div class="module-item">
                                <span class="module-icon">${SettingsIcons.bookmark}</span>
                                <div class="module-info">
                                    <span class="module-name">References</span>
                                    <span class="module-version">v1.0</span>
                                </div>
                                <span class="module-status status-active">${SettingsIcons.check}</span>
                            </div>
                            <div class="module-item">
                                <span class="module-icon">${SettingsIcons.thread}</span>
                                <div class="module-info">
                                    <span class="module-name">Threads</span>
                                    <span class="module-version">v1.3</span>
                                </div>
                                <span class="module-status status-active">${SettingsIcons.check}</span>
                            </div>
                            <div class="module-item">
                                <span class="module-icon">${SettingsIcons.messageCircle}</span>
                                <div class="module-info">
                                    <span class="module-name">Conversations</span>
                                    <span class="module-version">v1.4</span>
                                </div>
                                <span class="module-status status-active">${SettingsIcons.check}</span>
                            </div>
                            <div class="module-item">
                                <span class="module-icon">${SettingsIcons.timer}</span>
                                <div class="module-info">
                                    <span class="module-name">Timeline</span>
                                    <span class="module-version">v1.1</span>
                                </div>
                                <span class="module-status status-active">${SettingsIcons.check}</span>
                            </div>
                            <div class="module-item">
                                <span class="module-icon">${SettingsIcons.coins}</span>
                                <div class="module-info">
                                    <span class="module-name">Costs</span>
                                    <span class="module-version">v1.0</span>
                                </div>
                                <span class="module-status status-active">${SettingsIcons.check}</span>
                            </div>
                            <div class="module-item">
                                <span class="module-icon">${SettingsIcons.user}</span>
                                <div class="module-info">
                                    <span class="module-name">Preferences</span>
                                    <span class="module-version">v1.5</span>
                                </div>
                                <span class="module-status status-active">${SettingsIcons.check}</span>
                            </div>
                            <div class="module-item">
                                <span class="module-icon">${SettingsIcons.settings}</span>
                                <div class="module-info">
                                    <span class="module-name">Settings</span>
                                    <span class="module-version">v4.0</span>
                                </div>
                                <span class="module-status status-active">${SettingsIcons.check}</span>
                            </div>
                            <div class="module-item">
                                <span class="module-icon">${SettingsIcons.lock}</span>
                                <div class="module-info">
                                    <span class="module-name">Admin</span>
                                    <span class="module-version">v1.0</span>
                                </div>
                                <span class="module-status status-active">${SettingsIcons.check}</span>
                            </div>
                        </div>
                    </div>

                    <div class="about-section full-width">
                        <h3>${getIcon('scroll', 'section-icon')} Licence & Crédits</h3>
                        <p class="about-text">
                            ÉMERGENCE est une plateforme de gestion multi-agents développée pour orchestrer des systèmes d'IA complexes.
                        </p>
                        <p class="about-credits">
                            Développé par Fernando Gonzalez avec abnégation et surtout le soutien indéfectible de sa magnifique et charmante épouse Marem.
                        </p>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Attach event listeners
     */
    attachEventListeners() {
        // Navigation tabs
        this.container.querySelectorAll('.settings-nav-item').forEach(item => {
            item.addEventListener('click', (e) => {
                const tab = e.currentTarget.dataset.tab;
                this.switchTab(tab);
            });
        });

        // Save all button
        const saveAllBtn = this.container.querySelector('.btn-save-all');
        if (saveAllBtn) {
            saveAllBtn.addEventListener('click', () => this.saveAll());
        }

        // Reset all button
        const resetAllBtn = this.container.querySelector('.btn-reset-all');
        if (resetAllBtn) {
            resetAllBtn.addEventListener('click', () => this.resetAll());
        }

        // About links - Use event delegation on container
        this.container.addEventListener('click', (e) => {
            console.log('[Settings] Click detected on:', e.target);
            const aboutLink = e.target.closest('.about-link');
            console.log('[Settings] About link found:', aboutLink);
            if (aboutLink) {
                e.preventDefault();
                e.stopPropagation();
                const action = aboutLink.dataset.action;
                console.log('[Settings] About link clicked:', action);
                this.handleAboutAction(action);
            }
        });
    }

    /**
     * Handle about section actions
     */
    async handleAboutAction(action) {
        console.log('[Settings] handleAboutAction called with:', action);
        switch (action) {
            case 'documentation':
                // Load and show documentation in modal
                console.log('[Settings] Loading documentation');
                await this.showDocumentationPage();
                break;
            case 'support':
                this.showSupport();
                break;
            case 'bug-report':
                this.showBugReport();
                break;
        }
    }

    /**
     * Show documentation page in modal
     */
    async showDocumentationPage() {
        try {
            console.log('[Settings] Importing documentation module...');
            // Import documentation module
            const { documentation } = await import('../documentation/documentation.js');
            console.log('[Settings] Documentation module imported:', documentation);

            // Create modal with documentation content
            const modal = document.createElement('div');
            modal.className = 'modal-overlay documentation-modal';
            modal.style.cssText = `
                position: fixed !important;
                top: 0 !important;
                left: 0 !important;
                right: 0 !important;
                bottom: 0 !important;
                width: 100vw !important;
                height: 100vh !important;
                background: rgba(0, 0, 0, 0.85) !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
                z-index: 2147483646 !important;
                backdrop-filter: blur(4px) !important;
                pointer-events: auto !important;
            `;
            modal.innerHTML = `
                <div class="modal-container documentation-modal-container" style="
                    background: rgba(11, 18, 32, 0.98) !important;
                    border: 1px solid rgba(148, 163, 184, 0.3) !important;
                    border-radius: 20px !important;
                    max-width: 95vw !important;
                    width: 1600px !important;
                    max-height: 95vh !important;
                    height: 95vh !important;
                    display: flex !important;
                    flex-direction: column !important;
                    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5) !important;
                    position: relative !important;
                    z-index: 2147483647 !important;
                    overflow: hidden !important;
                ">
                    <div class="modal-header" style="
                        display: flex !important;
                        justify-content: space-between !important;
                        align-items: center !important;
                        padding: 24px 28px !important;
                        border-bottom: 1px solid rgba(148, 163, 184, 0.2) !important;
                        background: rgba(11, 18, 32, 0.98) !important;
                        flex-shrink: 0 !important;
                    ">
                        <h2 style="
                            font-size: 24px;
                            font-weight: 700;
                            color: rgba(226, 232, 240, 0.98);
                            margin: 0;
                        ">${getIcon('library', 'header-icon')} Documentation Technique</h2>
                        <button class="modal-close" onclick="this.closest('.modal-overlay').remove()" style="
                            background: transparent;
                            border: none;
                            font-size: 28px;
                            color: rgba(226, 232, 240, 0.7);
                            cursor: pointer;
                            padding: 0;
                            width: 36px;
                            height: 36px;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            border-radius: 8px;
                        ">✕</button>
                    </div>
                    <div class="modal-body documentation-modal-body" style="
                        padding: 0 !important;
                        overflow-y: auto !important;
                        flex: 1 !important;
                        background: rgba(11, 18, 32, 0.98) !important;
                        max-height: calc(95vh - 80px) !important;
                        min-height: 0 !important;
                    ">
                        <div id="documentation-modal-content" style="
                            width: 100% !important;
                            height: 100% !important;
                            min-height: 100% !important;
                        "></div>
                    </div>
                </div>
            `;

            console.log('[Settings] Appending modal to body...');
            document.body.appendChild(modal);
            console.log('[Settings] Modal appended. Computed style:', {
                display: window.getComputedStyle(modal).display,
                position: window.getComputedStyle(modal).position,
                zIndex: window.getComputedStyle(modal).zIndex,
                visibility: window.getComputedStyle(modal).visibility,
                opacity: window.getComputedStyle(modal).opacity
            });

            // Mount documentation in modal - use querySelector on modal to ensure it's found
            console.log('[Settings] Finding container...');
            const docContainer = modal.querySelector('#documentation-modal-content');
            console.log('[Settings] Container found:', docContainer);

            if (docContainer) {
                console.log('[Settings] Loading styles...');
                await documentation.loadStyles();
                console.log('[Settings] Rendering documentation...');
                documentation.render(docContainer);
                console.log('[Settings] Attaching event listeners...');
                documentation.attachEventListeners();
                console.log('[Settings] Documentation loaded successfully!');
            } else {
                console.error('[Settings] Documentation container not found!');
            }
        } catch (error) {
            console.error('[Settings] Error loading documentation:', error);
            this.showNotification('Erreur lors du chargement de la documentation', 'error');
        }
    }

    /**
     * Show documentation page
     */
    showDocumentation() {
        console.log('showDocumentation called');
        const content = this.getDocumentationContent();
        console.log('Content generated:', content.substring(0, 100));
        const modal = this.createModal('Documentation Technique', content);
        console.log('Modal created:', modal);
        document.body.appendChild(modal);
        console.log('Modal appended to body');
    }

    /**
     * Get documentation content
     */
    getDocumentationContent() {
        return `
            <div class="documentation-content">
                <section class="doc-section">
                    <h3>${getIcon('barChart', 'section-icon')} Statistiques du Projet</h3>
                    <div class="doc-stats">
                        <div class="doc-stat-item">
                            <span class="stat-label">Lignes de code totales:</span>
                            <span class="stat-value">~99,627 lignes (tous fichiers sources)</span>
                        </div>
                        <div class="doc-stat-item">
                            <span class="stat-label">Frontend:</span>
                            <span class="stat-value">~64,281 lignes (JavaScript/CSS)</span>
                        </div>
                        <div class="doc-stat-item">
                            <span class="stat-label">Backend:</span>
                            <span class="stat-value">~33,660 lignes (Python/FastAPI)</span>
                        </div>
                        <div class="doc-stat-item">
                            <span class="stat-label">Fichiers sources:</span>
                            <span class="stat-value">257 fichiers (JS, CSS, Python)</span>
                        </div>
                        <div class="doc-stat-item">
                            <span class="stat-label">Fichiers trackés Git:</span>
                            <span class="stat-value">906 fichiers au total</span>
                        </div>
                        <div class="doc-stat-item">
                            <span class="stat-label">Architecture:</span>
                            <span class="stat-value">Multi-agents avec orchestration centralisée</span>
                        </div>
                    </div>
                </section>

                <section class="doc-section">
                    <h3>${getIcon('package', 'section-icon')} Dépendances Principales</h3>
                    <div class="dependencies-grid">
                        <div class="dep-category">
                            <h4>Frontend (9 packages NPM)</h4>
                            <ul>
                                <li><strong>Vite 7.1.2</strong> - Build tool moderne ultra-rapide</li>
                                <li><strong>Marked 12.0.2</strong> - Parsing Markdown</li>
                                <li><strong>jsPDF 3.0.3</strong> - Génération de PDF</li>
                                <li><strong>PapaParse 5.5.3</strong> - Parsing CSV</li>
                                <li><strong>Playwright 1.48.2</strong> - Tests E2E</li>
                                <li><strong>Concurrently 9.2.0</strong> - Orchestration scripts</li>
                                <li>Vanilla JavaScript - Architecture légère sans framework</li>
                            </ul>
                        </div>
                        <div class="dep-category">
                            <h4>Backend (45+ packages Python)</h4>
                            <ul>
                                <li><strong>FastAPI 0.119.0</strong> - Framework web async haute performance</li>
                                <li><strong>Uvicorn 0.30.1</strong> - Serveur ASGI production-ready</li>
                                <li><strong>OpenAI, Anthropic, Google AI</strong> - Intégrations multi-LLM</li>
                                <li><strong>ChromaDB 0.5.23</strong> - Base vectorielle pour embeddings</li>
                                <li><strong>Qdrant Client</strong> - Backend vectoriel alternatif</li>
                                <li><strong>Google Cloud Firestore</strong> - Persistance cloud NoSQL</li>
                                <li><strong>Sentence-Transformers</strong> - Embeddings sémantiques</li>
                                <li><strong>PyTorch 2.1+</strong> - Deep learning backend</li>
                                <li><strong>Prometheus Client</strong> - Métriques et observabilité</li>
                                <li><strong>Dependency Injector</strong> - Architecture DI avancée</li>
                                <li><strong>Pydantic 2.6+</strong> - Validation de données typées</li>
                                <li><strong>PyJWT, BCrypt</strong> - Authentification et sécurité</li>
                                <li><strong>PyMuPDF, python-docx</strong> - Traitement documents</li>
                                <li><strong>Pytest, Ruff, MyPy</strong> - Suite de tests et qualité</li>
                            </ul>
                        </div>
                    </div>
                </section>

                <section class="doc-section">
                    <h3>${getIcon('plug', 'section-icon')} Architecture du Système</h3>
                    <div class="architecture-info">
                        <p><strong>Modules Frontend:</strong></p>
                        <ul>
                            <li><strong>Home:</strong> Tableau de bord principal et navigation</li>
                            <li><strong>Cockpit:</strong> Métriques et KPIs en temps réel</li>
                            <li><strong>Chat:</strong> Interface conversationnelle multi-agents</li>
                            <li><strong>Voice:</strong> Interaction vocale et transcription</li>
                            <li><strong>Memory:</strong> Gestion de la mémoire sémantique et graphe de concepts</li>
                            <li><strong>Debate:</strong> Orchestration de débats multi-agents</li>
                            <li><strong>Documents:</strong> Gestion et indexation de documents</li>
                            <li><strong>Threads/Conversations:</strong> Historique et contexte conversationnel</li>
                        </ul>

                        <p><strong>Backend Services:</strong></p>
                        <ul>
                            <li><strong>API Gateway:</strong> Point d'entrée unique (FastAPI)</li>
                            <li><strong>Agent Orchestrator:</strong> Coordination des agents IA</li>
                            <li><strong>Memory Service:</strong> Persistance et recall sémantique</li>
                            <li><strong>Vector Store:</strong> Recherche de similarité (ChromaDB)</li>
                            <li><strong>Document Processor:</strong> Extraction et indexation</li>
                            <li><strong>Metrics Collector:</strong> Observabilité Prometheus</li>
                        </ul>
                    </div>
                </section>

                <section class="doc-section">
                    <h3>${getIcon('trendingUp', 'section-icon')} Observabilité</h3>
                    <div class="observability-info">
                        <ul>
                            <li><strong>Métriques:</strong> Exposition Prometheus sur /metrics</li>
                            <li><strong>Logging:</strong> Structuré avec contexte de requête</li>
                            <li><strong>Tracing:</strong> Suivi des opérations multi-agents</li>
                            <li><strong>Dashboard:</strong> Visualisation en temps réel dans Cockpit</li>
                        </ul>
                    </div>
                </section>

                <section class="doc-section">
                    <h3>${getIcon('star', 'section-icon')} Genèse du Projet</h3>
                    <div class="genesis-content">
                        <p>
                            <strong>ÉMERGENCE</strong> est né de la vision d'orchestrer plusieurs agents IA de manière cohérente
                            et efficace, en exploitant leurs forces complémentaires pour résoudre des problèmes complexes.
                        </p>
                        <p>
                            Le projet a évolué à travers 8 versions majeures, intégrant progressivement :
                        </p>
                        <ul>
                            <li>La mémoire sémantique persistante avec graphe de concepts</li>
                            <li>L'orchestration multi-modèles (GPT-4, Claude, Gemini)</li>
                            <li>Le débat contradictoire entre agents</li>
                            <li>L'interface vocale naturelle (Speech-to-Text/Text-to-Speech)</li>
                            <li>L'observabilité temps réel avec Prometheus</li>
                            <li>La gestion intelligente de documents avec RAG sémantique</li>
                            <li>L'isolation mémoire par agent avec synchronisation automatique</li>
                        </ul>

                        <h4 style="margin-top: 24px; color: #60a5fa;">🤖 L'Écosystème Guardian Claude - Une Équipe IA Autonome</h4>
                        <p>
                            Parallèlement au développement d'ÉMERGENCE, un <strong>écosystème complet d'agents IA de développement</strong>
                            s'est formé naturellement, transformant radicalement la méthode de travail. Ces agents, basés sur Claude 3.5 Sonnet
                            et Claude Code, constituent aujourd'hui une <strong>véritable équipe de développement autonome</strong>.
                        </p>

                        <div class="guardian-team" style="background: rgba(30, 41, 59, 0.5); padding: 20px; border-radius: 12px; margin: 16px 0;">
                            <h5 style="color: #818cf8; margin-top: 0;">Les Agents Guardian - Rôles et Responsabilités</h5>
                            <ul style="list-style: none; padding-left: 0;">
                                <li style="margin: 12px 0; padding: 12px; background: rgba(51, 65, 85, 0.4); border-left: 3px solid #f59e0b; border-radius: 6px;">
                                    <strong style="color: #fbbf24;">📚 Anima (DocKeeper)</strong> - <em>Architecte Documentation</em><br/>
                                    Scanne en continu le code pour détecter les gaps de documentation, vérifie la cohérence entre
                                    le code et la doc, génère automatiquement les mises à jour nécessaires.
                                    <span style="color: #94a3b8; font-size: 0.9em;">→ Équivalent: Tech Writer senior (40h/mois)</span>
                                </li>
                                <li style="margin: 12px 0; padding: 12px; background: rgba(51, 65, 85, 0.4); border-left: 3px solid #10b981; border-radius: 6px;">
                                    <strong style="color: #34d399;">🔐 Neo (IntegrityWatcher)</strong> - <em>Gardien de l'Intégrité</em><br/>
                                    Vérifie l'intégrité structurelle backend/frontend, détecte les incohérences d'architecture,
                                    valide les contrats API, signale les violations de conventions.
                                    <span style="color: #94a3b8; font-size: 0.9em;">→ Équivalent: QA Engineer + Architecte (60h/mois)</span>
                                </li>
                                <li style="margin: 12px 0; padding: 12px; background: rgba(51, 65, 85, 0.4); border-left: 3px solid #ef4444; border-radius: 6px;">
                                    <strong style="color: #f87171;">🏭 ProdGuardian</strong> - <em>Moniteur Production</em><br/>
                                    Surveille l'état de la production via Cloud Run logs, détecte les erreurs critiques,
                                    analyse les patterns d'erreurs, bloque les déploiements si production instable.
                                    <span style="color: #94a3b8; font-size: 0.9em;">→ Équivalent: DevOps/SRE Engineer (50h/mois)</span>
                                </li>
                                <li style="margin: 12px 0; padding: 12px; background: rgba(51, 65, 85, 0.4); border-left: 3px solid #8b5cf6; border-radius: 6px;">
                                    <strong style="color: #a78bfa;">💰 Theia (CostWatcher)</strong> - <em>Optimisateur de Coûts IA</em><br/>
                                    Analyse l'utilisation des modèles IA, identifie les opportunités d'optimisation,
                                    recommande les modèles les plus rentables selon le contexte, track le ROI.
                                    <span style="color: #94a3b8; font-size: 0.9em;">→ Équivalent: FinOps Analyst (30h/mois)</span>
                                </li>
                                <li style="margin: 12px 0; padding: 12px; background: rgba(51, 65, 85, 0.4); border-left: 3px solid #06b6d4; border-radius: 6px;">
                                    <strong style="color: #22d3ee;">🎯 Nexus (Coordinator)</strong> - <em>Chef d'Orchestre</em><br/>
                                    Consolide les rapports de tous les agents, priorise les actions recommandées,
                                    génère un executive summary, orchestre les workflows complexes.
                                    <span style="color: #94a3b8; font-size: 0.9em;">→ Équivalent: Tech Lead/Project Manager (40h/mois)</span>
                                </li>
                                <li style="margin: 12px 0; padding: 12px; background: rgba(51, 65, 85, 0.4); border-left: 3px solid #3b82f6; border-radius: 6px;">
                                    <strong style="color: #60a5fa;">💻 Claude Code</strong> - <em>Développeur Principal</em><br/>
                                    Développement backend/frontend, refactoring, implémentation de nouvelles features,
                                    debugging complexe, optimisation de performance, architecture système.
                                    <span style="color: #94a3b8; font-size: 0.9em;">→ Équivalent: Senior Full-Stack Developer (160h/mois)</span>
                                </li>
                            </ul>
                        </div>

                        <h4 style="margin-top: 24px; color: #f59e0b;">💡 Comment Ils Travaillent Ensemble</h4>
                        <p>
                            L'écosystème Guardian fonctionne en <strong>automatisation complète</strong> grâce à des hooks Git :
                        </p>
                        <ul>
                            <li><strong>Pre-commit:</strong> Anima + Neo vérifient doc et intégrité AVANT chaque commit</li>
                            <li><strong>Post-commit:</strong> Nexus génère un rapport unifié et affiche un feedback détaillé</li>
                            <li><strong>Pre-push:</strong> ProdGuardian vérifie la production AVANT autorisation de déploiement</li>
                            <li><strong>Monitoring continu:</strong> Theia analyse les coûts et optimise les modèles en arrière-plan</li>
                        </ul>
                        <p>
                            Cette approche garantit une <strong>qualité continue, une documentation synchronisée et une production stable</strong>,
                            sans intervention humaine sur les tâches répétitives.
                        </p>

                        <h4 style="margin-top: 24px; color: #10b981;">📊 Comparaison avec une Équipe Humaine</h4>
                        <div class="team-comparison" style="background: rgba(16, 185, 129, 0.1); padding: 20px; border-radius: 12px; margin: 16px 0; border: 1px solid rgba(16, 185, 129, 0.3);">
                            <table style="width: 100%; border-collapse: collapse;">
                                <thead>
                                    <tr style="border-bottom: 2px solid rgba(148, 163, 184, 0.3);">
                                        <th style="text-align: left; padding: 12px; color: #e2e8f0;">Poste</th>
                                        <th style="text-align: center; padding: 12px; color: #e2e8f0;">Agent Guardian</th>
                                        <th style="text-align: center; padding: 12px; color: #e2e8f0;">Heures/mois</th>
                                        <th style="text-align: right; padding: 12px; color: #e2e8f0;">Coût mensuel (€)</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr style="border-bottom: 1px solid rgba(148, 163, 184, 0.2);">
                                        <td style="padding: 12px;">Senior Full-Stack Developer</td>
                                        <td style="text-align: center; padding: 12px;">Claude Code</td>
                                        <td style="text-align: center; padding: 12px;">160h</td>
                                        <td style="text-align: right; padding: 12px;">12,000€</td>
                                    </tr>
                                    <tr style="border-bottom: 1px solid rgba(148, 163, 184, 0.2);">
                                        <td style="padding: 12px;">QA Engineer + Architecte</td>
                                        <td style="text-align: center; padding: 12px;">Neo</td>
                                        <td style="text-align: center; padding: 12px;">60h</td>
                                        <td style="text-align: right; padding: 12px;">4,500€</td>
                                    </tr>
                                    <tr style="border-bottom: 1px solid rgba(148, 163, 184, 0.2);">
                                        <td style="padding: 12px;">DevOps/SRE Engineer</td>
                                        <td style="text-align: center; padding: 12px;">ProdGuardian</td>
                                        <td style="text-align: center; padding: 12px;">50h</td>
                                        <td style="text-align: right; padding: 12px;">4,000€</td>
                                    </tr>
                                    <tr style="border-bottom: 1px solid rgba(148, 163, 184, 0.2);">
                                        <td style="padding: 12px;">Tech Lead/PM</td>
                                        <td style="text-align: center; padding: 12px;">Nexus</td>
                                        <td style="text-align: center; padding: 12px;">40h</td>
                                        <td style="text-align: right; padding: 12px;">3,500€</td>
                                    </tr>
                                    <tr style="border-bottom: 1px solid rgba(148, 163, 184, 0.2);">
                                        <td style="padding: 12px;">Tech Writer Senior</td>
                                        <td style="text-align: center; padding: 12px;">Anima</td>
                                        <td style="text-align: center; padding: 12px;">40h</td>
                                        <td style="text-align: right; padding: 12px;">2,800€</td>
                                    </tr>
                                    <tr style="border-bottom: 1px solid rgba(148, 163, 184, 0.2);">
                                        <td style="padding: 12px;">FinOps Analyst</td>
                                        <td style="text-align: center; padding: 12px;">Theia</td>
                                        <td style="text-align: center; padding: 12px;">30h</td>
                                        <td style="text-align: right; padding: 12px;">2,400€</td>
                                    </tr>
                                    <tr style="border-top: 2px solid rgba(148, 163, 184, 0.4); background: rgba(16, 185, 129, 0.15); font-weight: 700;">
                                        <td style="padding: 12px; color: #10b981;">TOTAL ÉQUIPE HUMAINE</td>
                                        <td style="text-align: center; padding: 12px; color: #10b981;">6 postes</td>
                                        <td style="text-align: center; padding: 12px; color: #10b981;">380h</td>
                                        <td style="text-align: right; padding: 12px; color: #10b981;">29,200€/mois</td>
                                    </tr>
                                    <tr style="background: rgba(59, 130, 246, 0.15); font-weight: 700;">
                                        <td style="padding: 12px; color: #60a5fa;">COÛT AGENTS IA (estimation)</td>
                                        <td style="text-align: center; padding: 12px; color: #60a5fa;">Automatisé 24/7</td>
                                        <td style="text-align: center; padding: 12px; color: #60a5fa;">∞</td>
                                        <td style="text-align: right; padding: 12px; color: #60a5fa;">~150€/mois</td>
                                    </tr>
                                    <tr style="background: rgba(16, 185, 129, 0.25); font-weight: 900; font-size: 1.1em;">
                                        <td colspan="3" style="padding: 12px; color: #10b981;">ÉCONOMIE MENSUELLE</td>
                                        <td style="text-align: right; padding: 12px; color: #10b981;">~29,050€ (99.5%)</td>
                                    </tr>
                                </tbody>
                            </table>
                            <p style="margin-top: 16px; font-size: 0.95em; color: #cbd5e1;">
                                <strong>Note:</strong> Les coûts humains sont basés sur des taux freelance moyens en Europe (Suisse/France).
                                Le coût des agents IA comprend l'utilisation API Claude (Sonnet 4.5) avec les optimisations Theia.
                            </p>
                        </div>

                        <h4 style="margin-top: 24px; color: #ec4899;">🚀 Impact sur le Développement</h4>
                        <p>
                            Grâce à cette équipe IA, ÉMERGENCE bénéficie de :
                        </p>
                        <ul>
                            <li><strong>Vélocité multipliée par 10x:</strong> Développement, tests, documentation en parallèle 24/7</li>
                            <li><strong>Qualité constante:</strong> Revue de code automatique sur chaque commit, zéro régression documentaire</li>
                            <li><strong>Production ultra-stable:</strong> Monitoring continu, prévention proactive des incidents</li>
                            <li><strong>ROI optimisé:</strong> Choix intelligent des modèles selon le contexte, réduction des coûts IA de 40%</li>
                            <li><strong>Scalabilité infinie:</strong> Les agents s'adaptent automatiquement à la charge de travail</li>
                        </ul>

                        <p style="margin-top: 20px; padding: 16px; background: rgba(139, 92, 246, 0.1); border-left: 4px solid #8b5cf6; border-radius: 6px;">
                            <strong style="color: #a78bfa;">💎 Philosophie:</strong> ÉMERGENCE n'est pas seulement une plateforme multi-agents IA
                            pour les utilisateurs finaux - <strong>c'est aussi le premier projet développé EN COLLABORATION avec une équipe IA autonome</strong>.
                            Les agents Guardian ont co-créé le système qui les héberge, dans une boucle récursive d'amélioration continue.
                            C'est l'essence même de l'<strong>émergence</strong>.
                        </p>
                    </div>
                </section>

                <section class="doc-section">
                    <h3>${getIcon('user', 'section-icon')} À Propos de l'Auteur</h3>
                    <div class="author-bio">
                        <p><strong>Fernando Gonzalez</strong></p>
                        <p>
                            Développeur passionné par l'intelligence artificielle et les systèmes distribués.
                            ÉMERGENCE représente l'aboutissement de plusieurs années de recherche et développement
                            dans le domaine des architectures multi-agents.
                        </p>
                        <p>
                            Ce projet a été réalisé avec abnégation et le soutien constant de sa magnifique épouse Marem,
                            dont l'encouragement a été essentiel à chaque étape du développement.
                        </p>
                    </div>
                </section>
            </div>
        `;
    }

    /**
     * Show support page
     */
    showSupport() {
        const modal = this.createModal('Support & Contact', this.getSupportContent());
        document.body.appendChild(modal);
    }

    /**
     * Get support content
     */
    getSupportContent() {
        return `
            <div class="support-content">
                <div class="support-info">
                    <div class="support-card">
                        <h3>${getIcon('mail', 'section-icon')} Contact</h3>
                        <p><strong>Fernando Gonzalez</strong></p>
                        <p>Email: <a href="mailto:gonzalefernando@gmail.com">gonzalefernando@gmail.com</a></p>
                    </div>

                    <div class="support-card">
                        <h3>${getIcon('helpCircle', 'section-icon')} Besoin d'aide ?</h3>
                        <p>Pour toute question, suggestion ou problème technique, n'hésitez pas à me contacter directement par email.</p>
                        <p>Je m'efforce de répondre dans les plus brefs délais.</p>
                    </div>

                    <div class="support-card">
                        <h3>${getIcon('library', 'section-icon')} Ressources</h3>
                        <ul>
                            <li>Consultez la documentation technique pour plus d'informations</li>
                            <li>Utilisez le formulaire de bug report pour signaler les problèmes</li>
                            <li>Les suggestions d'amélioration sont toujours les bienvenues</li>
                        </ul>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Show bug report form
     */
    showBugReport() {
        const modal = this.createModal('Signaler un Bug', this.getBugReportContent());
        document.body.appendChild(modal);
        this.attachBugReportHandlers();
    }

    /**
     * Get bug report content
     */
    getBugReportContent() {
        return `
            <div class="bug-report-content">
                <form id="bug-report-form" class="bug-report-form">
                    <div class="form-group">
                        <label for="bug-module">Module concerné *</label>
                        <select id="bug-module" required>
                            <option value="">-- Sélectionnez un module --</option>
                            <option value="home">Home</option>
                            <option value="cockpit">Cockpit</option>
                            <option value="chat">Chat</option>
                            <option value="voice">Voice</option>
                            <option value="memory">Memory</option>
                            <option value="debate">Debate</option>
                            <option value="documents">Documents</option>
                            <option value="references">References</option>
                            <option value="threads">Threads</option>
                            <option value="conversations">Conversations</option>
                            <option value="timeline">Timeline</option>
                            <option value="costs">Costs</option>
                            <option value="preferences">Preferences</option>
                            <option value="settings">Settings</option>
                            <option value="admin">Admin</option>
                            <option value="other">Autre / Multiple</option>
                        </select>
                    </div>

                    <div class="form-group">
                        <label for="bug-type">Type de problème *</label>
                        <select id="bug-type" required>
                            <option value="">-- Sélectionnez un type --</option>
                            <option value="bug">Bug / Erreur</option>
                            <option value="performance">Performance</option>
                            <option value="ui">Interface / Design</option>
                            <option value="feature">Suggestion de fonctionnalité</option>
                            <option value="security">Sécurité</option>
                            <option value="other">Autre</option>
                        </select>
                    </div>

                    <div class="form-group">
                        <label for="bug-title">Titre *</label>
                        <input type="text" id="bug-title" placeholder="Résumé bref du problème" required>
                    </div>

                    <div class="form-group">
                        <label for="bug-description">Description détaillée *</label>
                        <textarea id="bug-description" rows="6" placeholder="Décrivez le problème rencontré ou votre suggestion..." required></textarea>
                    </div>

                    <div class="form-group">
                        <label for="bug-steps">Étapes pour reproduire (optionnel)</label>
                        <textarea id="bug-steps" rows="4" placeholder="1. Aller dans...&#10;2. Cliquer sur...&#10;3. Observer..."></textarea>
                    </div>

                    <div class="form-actions">
                        <button type="button" class="btn-cancel" onclick="this.closest('.modal-overlay').remove()">Annuler</button>
                        <button type="submit" class="btn-submit">${getIcon('send', 'btn-icon')} Envoyer</button>
                    </div>
                </form>
            </div>
        `;
    }

    /**
     * Attach bug report handlers
     */
    attachBugReportHandlers() {
        const form = document.getElementById('bug-report-form');
        if (form) {
            form.addEventListener('submit', (e) => {
                e.preventDefault();
                this.submitBugReport(form);
            });
        }
    }

    /**
     * Submit bug report
     */
    submitBugReport(form) {
        const formData = {
            module: form.querySelector('#bug-module').value,
            type: form.querySelector('#bug-type').value,
            title: form.querySelector('#bug-title').value,
            description: form.querySelector('#bug-description').value,
            steps: form.querySelector('#bug-steps').value
        };

        // Create email body
        const emailBody = `
Module: ${formData.module}
Type: ${formData.type}
Titre: ${formData.title}

Description:
${formData.description}

${formData.steps ? `Étapes pour reproduire:\n${formData.steps}` : ''}

---
Envoyé depuis ÉMERGENCE V8
        `.trim();

        const mailtoLink = `mailto:gonzalefernando@gmail.com?subject=[ÉMERGENCE Bug Report] ${formData.title}&body=${encodeURIComponent(emailBody)}`;

        window.location.href = mailtoLink;

        // Close modal
        document.querySelector('.modal-overlay').remove();

        this.showNotification('Votre client mail a été ouvert. Merci de votre retour !', 'success');
    }

    /**
     * Create modal
     */
    createModal(title, content) {
        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.75);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 10000;
            backdrop-filter: blur(4px);
        `;
        modal.innerHTML = `
            <div class="modal-container" style="
                background: rgba(11, 18, 32, 0.95);
                border: 1px solid rgba(148, 163, 184, 0.3);
                border-radius: 20px;
                max-width: 900px;
                width: 90%;
                max-height: 90vh;
                display: flex;
                flex-direction: column;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
                backdrop-filter: blur(20px);
                position: relative;
                z-index: 10001;
            ">
                <div class="modal-header" style="
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 24px 28px;
                    border-bottom: 1px solid rgba(148, 163, 184, 0.2);
                ">
                    <h2 style="
                        font-size: 24px;
                        font-weight: 700;
                        color: rgba(226, 232, 240, 0.98);
                        margin: 0;
                    ">${title}</h2>
                    <button class="modal-close" onclick="this.closest('.modal-overlay').remove()" style="
                        background: transparent;
                        border: none;
                        font-size: 28px;
                        color: rgba(226, 232, 240, 0.7);
                        cursor: pointer;
                        padding: 0;
                        width: 36px;
                        height: 36px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        border-radius: 8px;
                    ">✕</button>
                </div>
                <div class="modal-body" style="
                    padding: 28px;
                    overflow-y: auto;
                    flex: 1;
                    color: rgba(226, 232, 240, 0.85);
                ">
                    ${content}
                </div>
            </div>
        `;
        return modal;
    }

    /**
     * Switch active tab
     */
    async switchTab(tabName) {
        this.activeTab = tabName;

        // Update navigation
        this.container.querySelectorAll('.settings-nav-item').forEach(item => {
            item.classList.toggle('active', item.dataset.tab === tabName);
        });

        // Update panels
        this.container.querySelectorAll('.settings-panel').forEach(panel => {
            panel.classList.toggle('active', panel.dataset.panel === tabName);
        });

        // Load content for active tab
        await this.loadActiveView();
    }

    /**
     * Load content for active view
     */
    async loadActiveView() {
        switch (this.activeTab) {
            case 'models':
                await this.modules.models.init('settings-models-container');
                break;
            case 'rag':
                await this.modules.rag.init('settings-rag-container');
                break;
            case 'ui':
                await this.modules.ui.init('settings-ui-container');
                break;
        }
    }

    /**
     * Save all settings
     */
    async saveAll() {
        const saveAllBtn = this.container.querySelector('.btn-save-all');
        if (saveAllBtn) {
            saveAllBtn.disabled = true;
            saveAllBtn.innerHTML = `${getIcon('loader', 'btn-icon')} Sauvegarde...`;
        }

        try {
            await Promise.all([
                this.modules.models.saveSettings(),
                this.modules.rag.saveSettings(),
                this.modules.ui.saveSettings()
            ]);

            this.hasUnsavedChanges = false;
            this.showNotification('Tous les paramètres ont été sauvegardés', 'success');

            if (saveAllBtn) {
                saveAllBtn.innerHTML = `${getIcon('check', 'btn-icon')} Sauvegardé`;
                setTimeout(() => {
                    saveAllBtn.innerHTML = `${getIcon('save', 'btn-icon')} Tout sauvegarder`;
                    saveAllBtn.disabled = false;
                }, 2000);
            }
        } catch (error) {
            console.error('Error saving settings:', error);
            this.showNotification('Erreur lors de la sauvegarde', 'error');

            if (saveAllBtn) {
                saveAllBtn.innerHTML = `${getIcon('x', 'btn-icon')} Erreur`;
                saveAllBtn.disabled = false;
            }
        }
    }

    /**
     * Reset all settings
     */
    async resetAll() {
        if (!confirm('Réinitialiser TOUS les paramètres ? Cette action est irréversible.')) {
            return;
        }

        try {
            await Promise.all([
                this.modules.models.resetSettings(),
                this.modules.rag.resetSettings(),
                this.modules.ui.resetSettings()
            ]);

            this.hasUnsavedChanges = false;
            this.showNotification('Tous les paramètres ont été réinitialisés', 'success');

            // Reload active view
            await this.loadActiveView();
        } catch (error) {
            console.error('Error resetting settings:', error);
            this.showNotification('Erreur lors de la réinitialisation', 'error');
        }
    }

    /**
     * Show notification
     */
    showNotification(message, type = 'info') {
        // TODO: Integrate with global notification system
        console.log(`[${type.toUpperCase()}]`, message);
    }

    /**
     * Destroy settings
     */
    destroy() {
        Object.values(this.modules).forEach(module => {
            if (module.destroy) {
                module.destroy();
            }
        });

        if (this.container) {
            this.container.innerHTML = '';
        }

        this.initialized = false;
    }
}

// Export singleton instance
export const settings = new Settings();
