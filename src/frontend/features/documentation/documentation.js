/**
 * Documentation Module
 * Comprehensive technical documentation for ÉMERGENCE
 */

export class Documentation {
    constructor() {
        this.initialized = false;
        this.loadStyles();
    }

    /**
     * Load CSS styles dynamically
     */
    async loadStyles() {
        // Check if styles are already loaded
        const existingLink = document.querySelector('link[href*="documentation.css"]');
        if (existingLink) {
            return Promise.resolve();
        }

        return new Promise((resolve, reject) => {
            const link = document.createElement('link');
            link.rel = 'stylesheet';
            link.href = '/src/frontend/features/documentation/documentation.css';
            link.onload = () => resolve();
            link.onerror = () => reject(new Error('Failed to load documentation CSS'));
            document.head.appendChild(link);
        });
    }

    init() {
        console.log('[Documentation] Module loaded');
    }

    async mount(container) {
        if (this.initialized) {
            console.warn('[Documentation] Already mounted');
            return;
        }

        try {
            // Wait for styles to load
            await this.loadStyles();
            this.render(container);
            this.attachEventListeners();
            this.initialized = true;
            console.log('[Documentation] Mounted successfully');
        } catch (error) {
            console.error('[Documentation] Mount error:', error);
        }
    }

    render(container) {
        container.innerHTML = `
            <div class="documentation-page">
                <!-- Header -->
                <div class="doc-header">
                    <div class="doc-header-content">
                        <h1>📚 Documentation Technique</h1>
                        <p class="doc-subtitle">Spécifications complètes du système ÉMERGENCE</p>
                    </div>
                </div>

                <!-- Navigation rapide -->
                <div class="doc-quick-nav">
                    <a href="#stats" class="doc-nav-link">📊 Statistiques</a>
                    <a href="#architecture" class="doc-nav-link">🏗️ Architecture</a>
                    <a href="#dependencies" class="doc-nav-link">📦 Dépendances</a>
                    <a href="#technologies" class="doc-nav-link">⚙️ Technologies</a>
                    <a href="#observability" class="doc-nav-link">📈 Observabilité</a>
                    <a href="#genesis" class="doc-nav-link">🌟 Genèse</a>
                </div>

                <!-- Content -->
                <div class="doc-content">
                    <!-- Statistics Section -->
                    <section id="stats" class="doc-section">
                        <h2>📊 Statistiques du Projet</h2>
                        <div class="stats-grid">
                            <div class="stat-card">
                                <div class="stat-icon">💻</div>
                                <div class="stat-info">
                                    <div class="stat-value">~15,000</div>
                                    <div class="stat-label">Lignes de code Frontend</div>
                                    <div class="stat-detail">JavaScript / CSS / HTML</div>
                                </div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-icon">🐍</div>
                                <div class="stat-info">
                                    <div class="stat-value">~8,000</div>
                                    <div class="stat-label">Lignes de code Backend</div>
                                    <div class="stat-detail">Python / FastAPI</div>
                                </div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-icon">📦</div>
                                <div class="stat-info">
                                    <div class="stat-value">17</div>
                                    <div class="stat-label">Modules Frontend</div>
                                    <div class="stat-detail">Architecture modulaire</div>
                                </div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-icon">🔌</div>
                                <div class="stat-info">
                                    <div class="stat-value">30+</div>
                                    <div class="stat-label">Dépendances</div>
                                    <div class="stat-detail">Frontend + Backend</div>
                                </div>
                            </div>
                        </div>
                    </section>

                    <!-- Architecture Section -->
                    <section id="architecture" class="doc-section">
                        <h2>🏗️ Architecture du Système</h2>

                        <div class="arch-subsection">
                            <h3>Architecture Globale</h3>
                            <div class="arch-diagram">
                                <div class="arch-layer">
                                    <div class="arch-layer-title">Frontend (Client)</div>
                                    <div class="arch-components">
                                        <span class="arch-comp">SPA Vanilla JS</span>
                                        <span class="arch-comp">WebSocket Client</span>
                                        <span class="arch-comp">State Manager</span>
                                    </div>
                                </div>
                                <div class="arch-arrow">↕️</div>
                                <div class="arch-layer">
                                    <div class="arch-layer-title">Backend (API)</div>
                                    <div class="arch-components">
                                        <span class="arch-comp">FastAPI</span>
                                        <span class="arch-comp">WebSocket Server</span>
                                        <span class="arch-comp">Agent Orchestrator</span>
                                    </div>
                                </div>
                                <div class="arch-arrow">↕️</div>
                                <div class="arch-layer">
                                    <div class="arch-layer-title">Services & Data</div>
                                    <div class="arch-components">
                                        <span class="arch-comp">ChromaDB</span>
                                        <span class="arch-comp">Firestore</span>
                                        <span class="arch-comp">LLM APIs</span>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div class="arch-subsection">
                            <h3>Modules Frontend</h3>
                            <div class="modules-grid">
                                <div class="module-card">
                                    <div class="module-icon">🏠</div>
                                    <div class="module-name">Home</div>
                                    <div class="module-desc">Tableau de bord principal</div>
                                </div>
                                <div class="module-card">
                                    <div class="module-icon">📊</div>
                                    <div class="module-name">Cockpit</div>
                                    <div class="module-desc">Métriques et KPIs temps réel</div>
                                </div>
                                <div class="module-card">
                                    <div class="module-icon">💬</div>
                                    <div class="module-name">Chat</div>
                                    <div class="module-desc">Interface conversationnelle</div>
                                </div>
                                <div class="module-card">
                                    <div class="module-icon">🎙️</div>
                                    <div class="module-name">Voice</div>
                                    <div class="module-desc">Interaction vocale</div>
                                </div>
                                <div class="module-card">
                                    <div class="module-icon">🧠</div>
                                    <div class="module-name">Memory</div>
                                    <div class="module-desc">Mémoire sémantique</div>
                                </div>
                                <div class="module-card">
                                    <div class="module-icon">💭</div>
                                    <div class="module-name">Debate</div>
                                    <div class="module-desc">Débats multi-agents</div>
                                </div>
                                <div class="module-card">
                                    <div class="module-icon">📄</div>
                                    <div class="module-name">Documents</div>
                                    <div class="module-desc">Gestion documentaire</div>
                                </div>
                                <div class="module-card">
                                    <div class="module-icon">🧵</div>
                                    <div class="module-name">Threads</div>
                                    <div class="module-desc">Fils de conversation</div>
                                </div>
                                <div class="module-card">
                                    <div class="module-icon">⚙️</div>
                                    <div class="module-name">Settings</div>
                                    <div class="module-desc">Configuration et paramètres</div>
                                </div>
                                <div class="module-card">
                                    <div class="module-icon">🎓</div>
                                    <div class="module-name">Tutorial</div>
                                    <div class="module-desc">Guides et tutoriel interactif</div>
                                </div>
                            </div>
                        </div>

                        <div class="arch-subsection">
                            <h3>Services Backend</h3>
                            <ul class="service-list">
                                <li><strong>API Gateway:</strong> Point d'entrée unique (FastAPI) avec routage REST et WebSocket</li>
                                <li><strong>Agent Orchestrator:</strong> Coordination et orchestration des agents IA</li>
                                <li><strong>Memory Service:</strong> Persistance et recall sémantique avec embeddings</li>
                                <li><strong>Vector Store:</strong> Recherche de similarité via ChromaDB</li>
                                <li><strong>Document Processor:</strong> Extraction et indexation de documents (PDF, DOCX)</li>
                                <li><strong>Metrics Collector:</strong> Collecte et exposition de métriques Prometheus</li>
                                <li><strong>Authentication Service:</strong> Gestion des utilisateurs et JWT</li>
                            </ul>
                        </div>
                    </section>

                    <!-- Dependencies Section -->
                    <section id="dependencies" class="doc-section">
                        <h2>📦 Dépendances</h2>

                        <div class="dep-category">
                            <h3>Frontend</h3>
                            <table class="dep-table">
                                <thead>
                                    <tr>
                                        <th>Package</th>
                                        <th>Version</th>
                                        <th>Usage</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr>
                                        <td><strong>Vite</strong></td>
                                        <td>^7.1.2</td>
                                        <td>Build tool et dev server moderne</td>
                                    </tr>
                                    <tr>
                                        <td><strong>Marked</strong></td>
                                        <td>^12.0.2</td>
                                        <td>Parsing et rendu Markdown</td>
                                    </tr>
                                    <tr>
                                        <td><strong>Vanilla JS</strong></td>
                                        <td>ES6+</td>
                                        <td>Framework-less, modules natifs</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>

                        <div class="dep-category">
                            <h3>Backend - Core</h3>
                            <table class="dep-table">
                                <thead>
                                    <tr>
                                        <th>Package</th>
                                        <th>Version</th>
                                        <th>Usage</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr>
                                        <td><strong>FastAPI</strong></td>
                                        <td>0.109.2</td>
                                        <td>Framework web async haute performance</td>
                                    </tr>
                                    <tr>
                                        <td><strong>Uvicorn</strong></td>
                                        <td>0.30.1</td>
                                        <td>Serveur ASGI avec uvloop/httptools</td>
                                    </tr>
                                    <tr>
                                        <td><strong>WebSockets</strong></td>
                                        <td>11.0.2+</td>
                                        <td>Communication temps réel</td>
                                    </tr>
                                    <tr>
                                        <td><strong>Pydantic</strong></td>
                                        <td>2.6+</td>
                                        <td>Validation de données et settings</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>

                        <div class="dep-category">
                            <h3>Backend - AI & ML</h3>
                            <table class="dep-table">
                                <thead>
                                    <tr>
                                        <th>Package</th>
                                        <th>Version</th>
                                        <th>Usage</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr>
                                        <td><strong>OpenAI</strong></td>
                                        <td>1.35+</td>
                                        <td>Intégration GPT-4, GPT-4o</td>
                                    </tr>
                                    <tr>
                                        <td><strong>Anthropic</strong></td>
                                        <td>0.64.0</td>
                                        <td>Intégration Claude 3.5</td>
                                    </tr>
                                    <tr>
                                        <td><strong>Google GenAI</strong></td>
                                        <td>0.8.5</td>
                                        <td>Intégration Gemini Pro</td>
                                    </tr>
                                    <tr>
                                        <td><strong>Sentence Transformers</strong></td>
                                        <td>2.7+</td>
                                        <td>Génération d'embeddings</td>
                                    </tr>
                                    <tr>
                                        <td><strong>ChromaDB</strong></td>
                                        <td>0.4.22</td>
                                        <td>Base de données vectorielle</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>

                        <div class="dep-category">
                            <h3>Backend - Infrastructure</h3>
                            <table class="dep-table">
                                <thead>
                                    <tr>
                                        <th>Package</th>
                                        <th>Version</th>
                                        <th>Usage</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr>
                                        <td><strong>Firestore</strong></td>
                                        <td>2.16+</td>
                                        <td>Persistance cloud NoSQL</td>
                                    </tr>
                                    <tr>
                                        <td><strong>Prometheus Client</strong></td>
                                        <td>0.20+</td>
                                        <td>Exposition de métriques</td>
                                    </tr>
                                    <tr>
                                        <td><strong>PyJWT</strong></td>
                                        <td>2.9+</td>
                                        <td>Authentification JWT</td>
                                    </tr>
                                    <tr>
                                        <td><strong>Bcrypt</strong></td>
                                        <td>4.1+</td>
                                        <td>Hashing de mots de passe</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </section>

                    <!-- Technologies Section -->
                    <section id="technologies" class="doc-section">
                        <h2>⚙️ Technologies & Paradigmes</h2>

                        <div class="tech-grid">
                            <div class="tech-card">
                                <h3>🎨 Frontend</h3>
                                <ul>
                                    <li><strong>Architecture:</strong> SPA modulaire sans framework</li>
                                    <li><strong>Pattern:</strong> Component-based avec modules ES6</li>
                                    <li><strong>State:</strong> StateManager centralisé + LocalStorage</li>
                                    <li><strong>Communication:</strong> WebSocket + REST API</li>
                                    <li><strong>UI/UX:</strong> Glassmorphism, design system cohérent</li>
                                    <li><strong>Build:</strong> Vite avec HMR</li>
                                    <li><strong>Tutoriel:</strong> Système interactif avec guides détaillés</li>
                                </ul>
                            </div>

                            <div class="tech-card">
                                <h3>⚡ Backend</h3>
                                <ul>
                                    <li><strong>Framework:</strong> FastAPI (async/await)</li>
                                    <li><strong>Pattern:</strong> Dependency Injection, Repository</li>
                                    <li><strong>Architecture:</strong> Microservices-ready, modulaire</li>
                                    <li><strong>API:</strong> REST + WebSocket bidirectionnel</li>
                                    <li><strong>Validation:</strong> Pydantic schemas</li>
                                    <li><strong>Testing:</strong> Pytest avec fixtures async</li>
                                </ul>
                            </div>

                            <div class="tech-card">
                                <h3>🤖 Intelligence Artificielle</h3>
                                <ul>
                                    <li><strong>LLMs:</strong> Multi-provider (OpenAI, Anthropic, Google)</li>
                                    <li><strong>Embeddings:</strong> Sentence-BERT pour sémantique</li>
                                    <li><strong>Vector DB:</strong> ChromaDB pour recherche similaire</li>
                                    <li><strong>RAG:</strong> Retrieval-Augmented Generation</li>
                                    <li><strong>Orchestration:</strong> Agent coordination patterns</li>
                                    <li><strong>Memory:</strong> Persistance contexte long terme</li>
                                </ul>
                            </div>

                            <div class="tech-card">
                                <h3>🗄️ Data & Storage</h3>
                                <ul>
                                    <li><strong>Cloud:</strong> Google Cloud Firestore (NoSQL)</li>
                                    <li><strong>Vector:</strong> ChromaDB (embeddings)</li>
                                    <li><strong>Local:</strong> SQLite (development)</li>
                                    <li><strong>Cache:</strong> LocalStorage (frontend state)</li>
                                    <li><strong>Files:</strong> PyMuPDF, python-docx pour parsing</li>
                                </ul>
                            </div>
                        </div>
                    </section>

                    <!-- Observability Section -->
                    <section id="observability" class="doc-section">
                        <h2>📈 Observabilité & Monitoring</h2>

                        <div class="obs-grid">
                            <div class="obs-card">
                                <h3>📊 Métriques</h3>
                                <ul>
                                    <li>Exposition Prometheus sur <code>/metrics</code></li>
                                    <li>Compteurs de requêtes par endpoint</li>
                                    <li>Latences et durées d'exécution</li>
                                    <li>Métriques custom pour agents IA</li>
                                    <li>Coûts LLM tracking (tokens, $)</li>
                                </ul>
                            </div>

                            <div class="obs-card">
                                <h3>📝 Logging</h3>
                                <ul>
                                    <li>Logging structuré avec contexte</li>
                                    <li>Niveaux: DEBUG, INFO, WARNING, ERROR</li>
                                    <li>Rotation automatique des logs</li>
                                    <li>Correlation IDs pour traçabilité</li>
                                </ul>
                            </div>

                            <div class="obs-card">
                                <h3>🔍 Tracing</h3>
                                <ul>
                                    <li>Suivi des opérations multi-agents</li>
                                    <li>Timeline des événements</li>
                                    <li>Profiling des requêtes lentes</li>
                                    <li>Debug mode avec traces détaillées</li>
                                </ul>
                            </div>

                            <div class="obs-card">
                                <h3>📺 Dashboard</h3>
                                <ul>
                                    <li>Cockpit en temps réel</li>
                                    <li>Graphiques de métriques live</li>
                                    <li>Historique de conversations</li>
                                    <li>Analyse des coûts et usage</li>
                                </ul>
                            </div>
                        </div>
                    </section>

                    <!-- Genesis Section -->
                    <section id="genesis" class="doc-section">
                        <h2>🌟 Genèse du Projet</h2>

                        <div class="genesis-content">
                            <div class="genesis-intro">
                                <p>
                                    <strong>ÉMERGENCE</strong> est né de la vision d'orchestrer plusieurs agents IA
                                    de manière cohérente et efficace, en exploitant leurs forces complémentaires
                                    pour résoudre des problèmes complexes.
                                </p>
                            </div>

                            <div class="timeline">
                                <div class="timeline-item">
                                    <div class="timeline-marker">V1-V2</div>
                                    <div class="timeline-content">
                                        <h4>Fondations</h4>
                                        <p>Architecture de base, intégration première génération LLM</p>
                                    </div>
                                </div>
                                <div class="timeline-item">
                                    <div class="timeline-marker">V3-V4</div>
                                    <div class="timeline-content">
                                        <h4>Multi-agents</h4>
                                        <p>Orchestration multi-modèles, débats contradictoires</p>
                                    </div>
                                </div>
                                <div class="timeline-item">
                                    <div class="timeline-marker">V5-V6</div>
                                    <div class="timeline-content">
                                        <h4>Mémoire Sémantique</h4>
                                        <p>Système de mémoire persistante, embeddings, RAG</p>
                                    </div>
                                </div>
                                <div class="timeline-item">
                                    <div class="timeline-marker">V7-V8</div>
                                    <div class="timeline-content">
                                        <h4>Production Ready</h4>
                                        <p>Interface vocale, observabilité complète, stabilisation</p>
                                    </div>
                                </div>
                            </div>

                            <div class="genesis-values">
                                <h3>Principes Directeurs</h3>
                                <div class="values-grid">
                                    <div class="value-card">
                                        <div class="value-icon">🎯</div>
                                        <h4>Excellence Technique</h4>
                                        <p>Code propre, architecture solide, patterns éprouvés</p>
                                    </div>
                                    <div class="value-card">
                                        <div class="value-icon">🔄</div>
                                        <h4>Itération Continue</h4>
                                        <p>Amélioration progressive, feedback constant</p>
                                    </div>
                                    <div class="value-card">
                                        <div class="value-icon">🚀</div>
                                        <h4>Innovation</h4>
                                        <p>Exploration des limites de l'IA multi-agents</p>
                                    </div>
                                    <div class="value-card">
                                        <div class="value-icon">💎</div>
                                        <h4>Qualité</h4>
                                        <p>Attention aux détails, UX soignée</p>
                                    </div>
                                </div>
                            </div>

                            <div class="author-section">
                                <h3>👤 À Propos de l'Auteur</h3>
                                <div class="author-card">
                                    <div class="author-info">
                                        <h4>Fernando Gonzalez</h4>
                                        <p>
                                            Développeur passionné par l'intelligence artificielle et les systèmes distribués.
                                            ÉMERGENCE représente l'aboutissement de plusieurs années de recherche et développement
                                            dans le domaine des architectures multi-agents.
                                        </p>
                                        <p class="author-dedication">
                                            Ce projet a été réalisé avec abnégation et le soutien constant de sa magnifique
                                            épouse Marem, dont l'encouragement a été essentiel à chaque étape du développement.
                                        </p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </section>
                </div>
            </div>
        `;
    }

    attachEventListeners() {
        // Smooth scroll for navigation links
        const navLinks = document.querySelectorAll('.doc-nav-link');
        navLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const targetId = link.getAttribute('href').substring(1);
                const targetElement = document.getElementById(targetId);
                if (targetElement) {
                    targetElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            });
        });
    }

    unmount() {
        this.initialized = false;
    }
}

export const documentation = new Documentation();
