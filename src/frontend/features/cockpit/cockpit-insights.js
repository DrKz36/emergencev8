/**
 * Cockpit Insights Module
 * Displays top concepts, threads, and documents with smart analytics
 */

import { api } from '../../shared/api-client.js';
import { getIcon, getTrendIcon, getDocumentIcon } from './cockpit-icons.js';

export class CockpitInsights {
    constructor() {
        this.container = null;
        this.insights = {
            topConcepts: [],
            topThreads: [],
            topDocuments: [],
            trends: {}
        };
    }

    /**
     * Initialize insights module
     */
    async init(containerId) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            console.error('Cockpit insights container not found:', containerId);
            return;
        }

        console.log('💡 Initializing Cockpit Insights...');
        this.render();

        // Wait for DOM to be fully ready
        await new Promise(resolve => setTimeout(resolve, 100));

        console.log('📊 Loading insights data...');
        await this.loadInsights();
        console.log('✅ Cockpit Insights initialized');
    }

    /**
     * Render insights UI structure
     */
    render() {
        this.container.innerHTML = `
            <div class="cockpit-insights">
                <div class="insights-header">
                    <h2>${getIcon('lightbulb')} Insights & Analyse</h2>
                    <div class="insights-period">
                        <span class="period-label">Période:</span>
                        <select class="period-selector">
                            <option value="7d">7 derniers jours</option>
                            <option value="30d" selected>30 derniers jours</option>
                            <option value="90d">90 derniers jours</option>
                            <option value="all">Tout</option>
                        </select>
                    </div>
                </div>

                <div class="insights-grid">
                    <!-- Top Concepts -->
                    <div class="insight-section top-concepts">
                        <div class="section-header">
                            <h3>${getIcon('star')} Top Concepts</h3>
                            <span class="section-badge" id="concepts-count">0</span>
                        </div>
                        <div class="section-content" id="top-concepts-list">
                            <div class="loading-state">Chargement...</div>
                        </div>
                        <div class="section-footer">
                            <button class="btn-view-all" data-target="concepts">
                                Voir tous les concepts →
                            </button>
                        </div>
                    </div>

                    <!-- Top Threads -->
                    <div class="insight-section top-threads">
                        <div class="section-header">
                            <h3>${getIcon('thread')} Top Threads</h3>
                            <span class="section-badge" id="threads-count">0</span>
                        </div>
                        <div class="section-content" id="top-threads-list">
                            <div class="loading-state">Chargement...</div>
                        </div>
                        <div class="section-footer">
                            <button class="btn-view-all" data-target="threads">
                                Voir tous les threads →
                            </button>
                        </div>
                    </div>

                    <!-- Top Documents -->
                    <div class="insight-section top-documents">
                        <div class="section-header">
                            <h3>${getIcon('file')} Top Documents</h3>
                            <span class="section-badge" id="documents-count">0</span>
                        </div>
                        <div class="section-content" id="top-documents-list">
                            <div class="loading-state">Chargement...</div>
                        </div>
                        <div class="section-footer">
                            <button class="btn-view-all" data-target="documents">
                                Voir tous les documents →
                            </button>
                        </div>
                    </div>

                    <!-- Trends & Patterns -->
                    <div class="insight-section trends-section">
                        <div class="section-header">
                            <h3>${getIcon('trendingUp')} Tendances & Patterns</h3>
                        </div>
                        <div class="section-content" id="trends-content">
                            <div class="loading-state">Chargement...</div>
                        </div>
                    </div>

                    <!-- Activity Heatmap -->
                    <div class="insight-section activity-section">
                        <div class="section-header">
                            <h3>${getIcon('flame')} Carte de Chaleur d'Activité</h3>
                        </div>
                        <div class="section-content" id="activity-heatmap">
                            <div class="loading-state">Chargement...</div>
                        </div>
                    </div>

                    <!-- Smart Recommendations -->
                    <div class="insight-section recommendations-section">
                        <div class="section-header">
                            <h3>${getIcon('target')} Recommandations Intelligentes</h3>
                        </div>
                        <div class="section-content" id="recommendations-list">
                            <div class="loading-state">Chargement...</div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        this.attachEventListeners();
    }

    /**
     * Attach event listeners
     */
    attachEventListeners() {
        const periodSelector = this.container.querySelector('.period-selector');
        const viewAllButtons = this.container.querySelectorAll('.btn-view-all');

        if (periodSelector) {
            periodSelector.addEventListener('change', (e) => {
                this.changePeriod(e.target.value);
            });
        }

        viewAllButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const target = e.target.dataset.target;
                this.navigateToSection(target);
            });
        });
    }

    /**
     * Load insights data
     */
    async loadInsights() {
        try {
            const periodSelector = this.container.querySelector('.period-selector');
            if (!periodSelector) {
                console.error('❌ Period selector not found!');
                return;
            }

            const period = periodSelector.value;
            console.log('📥 Fetching insights for period:', period);

            const [concepts, threads, documents, trends] = await Promise.all([
                this.fetchTopConcepts(period),
                this.fetchTopThreads(period),
                this.fetchTopDocuments(period),
                this.fetchTrends(period)
            ]);

            this.insights = {
                topConcepts: concepts || [],
                topThreads: threads || [],
                topDocuments: documents || [],
                trends: trends || {}
            };

            console.log('📦 Insights data loaded:', this.insights);
            console.log('  - Top Concepts:', this.insights.topConcepts.length);
            console.log('  - Top Threads:', this.insights.topThreads.length);
            console.log('  - Top Documents:', this.insights.topDocuments.length);
            console.log('  - Trends:', Object.keys(this.insights.trends).length, 'keys');

            this.updateUI();
            console.log('✅ UI updated successfully');
        } catch (error) {
            console.error('❌ Error loading insights:', error);
            this.showError('Impossible de charger les insights');
        }
    }

    /**
     * Fetch top concepts
     */
    async fetchTopConcepts(period) {
        // Mock data - replace with actual API call
        return [
            { id: 1, name: 'Architecture Agent', mentions: 142, trend: 'up', growth: 25 },
            { id: 2, name: 'Memory System', mentions: 128, trend: 'up', growth: 18 },
            { id: 3, name: 'RAG Pipeline', mentions: 95, trend: 'stable', growth: 0 },
            { id: 4, name: 'Vector Database', mentions: 87, trend: 'up', growth: 12 },
            { id: 5, name: 'Prompt Engineering', mentions: 76, trend: 'down', growth: -8 }
        ];
    }

    /**
     * Fetch top threads
     */
    async fetchTopThreads(period) {
        // Mock data with relative dates
        const now = new Date();
        const hoursAgo = (hours) => new Date(now.getTime() - hours * 60 * 60 * 1000).toISOString();

        return [
            { id: 1, title: 'Implémentation système de mémoire', messages: 45, lastActivity: hoursAgo(2), status: 'active' },
            { id: 2, title: 'Optimisation pipeline RAG', messages: 38, lastActivity: hoursAgo(6), status: 'active' },
            { id: 3, title: 'Architecture multi-agents', messages: 32, lastActivity: hoursAgo(24), status: 'archived' },
            { id: 4, title: 'Intégration base vectorielle', messages: 28, lastActivity: hoursAgo(48), status: 'active' },
            { id: 5, title: 'Tests système complet', messages: 24, lastActivity: hoursAgo(96), status: 'archived' }
        ];
    }

    /**
     * Fetch top documents
     */
    async fetchTopDocuments(period) {
        // Mock data with relative dates
        const now = new Date();
        const hoursAgo = (hours) => new Date(now.getTime() - hours * 60 * 60 * 1000).toISOString();

        return [
            { id: 1, title: 'Architecture.md', views: 156, lastAccess: hoursAgo(3), type: 'markdown' },
            { id: 2, title: 'Memory-System.pdf', views: 134, lastAccess: hoursAgo(8), type: 'pdf' },
            { id: 3, title: 'API-Documentation.md', views: 98, lastAccess: hoursAgo(18), type: 'markdown' },
            { id: 4, title: 'RAG-Pipeline.txt', views: 87, lastAccess: hoursAgo(36), type: 'text' },
            { id: 5, title: 'Testing-Guide.md', views: 76, lastAccess: hoursAgo(72), type: 'markdown' }
        ];
    }

    /**
     * Fetch trends data
     */
    async fetchTrends(period) {
        // Mock data - replace with actual API call
        return {
            mostActiveDay: 'Lundi',
            peakHour: '14h-15h',
            avgMessagesPerDay: 42,
            growthRate: 15.3,
            topAgent: 'Anima'
        };
    }

    /**
     * Update UI with insights data
     */
    updateUI() {
        this.renderTopConcepts();
        this.renderTopThreads();
        this.renderTopDocuments();
        this.renderTrends();
        this.renderActivityHeatmap();
        this.renderRecommendations();
    }

    /**
     * Render top concepts list
     */
    renderTopConcepts() {
        const container = this.container.querySelector('#top-concepts-list');
        const countBadge = this.container.querySelector('#concepts-count');

        if (!container) {
            console.warn('⚠️ top-concepts-list container not found in', this.container);
            return;
        }

        if (countBadge) {
            countBadge.textContent = this.insights.topConcepts.length;
        }

        if (!this.insights.topConcepts || this.insights.topConcepts.length === 0) {
            container.innerHTML = '<div class="no-data">Aucun concept disponible</div>';
            return;
        }

        const html = this.insights.topConcepts.map(concept => `
            <div class="insight-item concept-item">
                <div class="item-rank">#${this.insights.topConcepts.indexOf(concept) + 1}</div>
                <div class="item-content">
                    <div class="item-title">${concept.name}</div>
                    <div class="item-stats">
                        <span class="stat-mentions">${concept.mentions} mentions</span>
                        <span class="stat-trend trend-${concept.trend}">
                            ${getTrendIcon(concept.trend)} ${Math.abs(concept.growth)}%
                        </span>
                    </div>
                </div>
                <div class="item-action">
                    <button class="btn-explore" data-concept-id="${concept.id}">Explorer</button>
                </div>
            </div>
        `).join('');

        container.innerHTML = html;

        // Attach explore buttons
        container.querySelectorAll('.btn-explore').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const conceptId = e.target.dataset.conceptId;
                this.exploreConcept(conceptId);
            });
        });
    }

    /**
     * Render top threads list
     */
    renderTopThreads() {
        const container = this.container.querySelector('#top-threads-list');
        const countBadge = this.container.querySelector('#threads-count');

        if (!container) {
            console.warn('⚠️ top-threads-list container not found in', this.container);
            return;
        }

        if (countBadge) {
            countBadge.textContent = this.insights.topThreads.length;
        }

        if (!this.insights.topThreads || this.insights.topThreads.length === 0) {
            container.innerHTML = '<div class="no-data">Aucun thread disponible</div>';
            return;
        }

        const html = this.insights.topThreads.map(thread => `
            <div class="insight-item thread-item">
                <div class="item-rank">#${this.insights.topThreads.indexOf(thread) + 1}</div>
                <div class="item-content">
                    <div class="item-title">${thread.title}</div>
                    <div class="item-stats">
                        <span class="stat-messages">${thread.messages} messages</span>
                        <span class="stat-time">${this.formatTimeAgo(thread.lastActivity)}</span>
                        <span class="status-badge status-${thread.status}">${thread.status}</span>
                    </div>
                </div>
                <div class="item-action">
                    <button class="btn-open-thread" data-thread-id="${thread.id}">Ouvrir</button>
                </div>
            </div>
        `).join('');

        container.innerHTML = html;

        // Attach open buttons
        container.querySelectorAll('.btn-open-thread').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const threadId = e.target.dataset.threadId;
                this.openThread(threadId);
            });
        });
    }

    /**
     * Render top documents list
     */
    renderTopDocuments() {
        const container = this.container.querySelector('#top-documents-list');
        const countBadge = this.container.querySelector('#documents-count');

        if (!container) {
            console.warn('⚠️ top-documents-list container not found in', this.container);
            return;
        }

        if (countBadge) {
            countBadge.textContent = this.insights.topDocuments.length;
        }

        if (!this.insights.topDocuments || this.insights.topDocuments.length === 0) {
            container.innerHTML = '<div class="no-data">Aucun document disponible</div>';
            return;
        }

        const html = this.insights.topDocuments.map(doc => `
            <div class="insight-item document-item">
                <div class="item-rank">#${this.insights.topDocuments.indexOf(doc) + 1}</div>
                <div class="item-icon">${getDocumentIcon(doc.type)}</div>
                <div class="item-content">
                    <div class="item-title">${doc.title}</div>
                    <div class="item-stats">
                        <span class="stat-views">${doc.views} vues</span>
                        <span class="stat-time">${this.formatTimeAgo(doc.lastAccess)}</span>
                    </div>
                </div>
                <div class="item-action">
                    <button class="btn-view-doc" data-doc-id="${doc.id}">Voir</button>
                </div>
            </div>
        `).join('');

        container.innerHTML = html;

        // Attach view buttons
        container.querySelectorAll('.btn-view-doc').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const docId = e.target.dataset.docId;
                this.viewDocument(docId);
            });
        });
    }

    /**
     * Render trends section
     */
    renderTrends() {
        const container = this.container.querySelector('#trends-content');
        if (!container) {
            console.warn('⚠️ trends-content container not found in', this.container);
            return;
        }

        const trends = this.insights.trends || {};

        if (!trends || Object.keys(trends).length === 0) {
            container.innerHTML = '<div class="no-data">Aucune tendance disponible</div>';
            return;
        }

        container.innerHTML = `
            <div class="trends-grid">
                <div class="trend-card">
                    <div class="trend-icon">${getIcon('calendar')}</div>
                    <div class="trend-label">Jour le plus actif</div>
                    <div class="trend-value">${trends.mostActiveDay}</div>
                </div>
                <div class="trend-card">
                    <div class="trend-icon">${getIcon('clock')}</div>
                    <div class="trend-label">Heure de pointe</div>
                    <div class="trend-value">${trends.peakHour}</div>
                </div>
                <div class="trend-card">
                    <div class="trend-icon">${getIcon('barChart')}</div>
                    <div class="trend-label">Moy. messages/jour</div>
                    <div class="trend-value">${trends.avgMessagesPerDay}</div>
                </div>
                <div class="trend-card">
                    <div class="trend-icon">${getIcon('trendingUp')}</div>
                    <div class="trend-label">Taux de croissance</div>
                    <div class="trend-value">+${trends.growthRate}%</div>
                </div>
                <div class="trend-card">
                    <div class="trend-icon">${getIcon('robot')}</div>
                    <div class="trend-label">Agent le plus utilisé</div>
                    <div class="trend-value">${trends.topAgent}</div>
                </div>
            </div>
        `;
    }

    /**
     * Render activity heatmap
     */
    renderActivityHeatmap() {
        const container = this.container.querySelector('#activity-heatmap');
        if (!container) {
            console.warn('⚠️ activity-heatmap container not found in', this.container);
            return;
        }

        // Simple text-based heatmap for now
        const days = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'];
        const hours = Array.from({ length: 24 }, (_, i) => i);

        const heatmapData = this.generateHeatmapData(days.length, hours.length);

        let html = '<div class="heatmap-grid">';
        html += '<div class="heatmap-header">';
        days.forEach(day => {
            html += `<div class="heatmap-day">${day}</div>`;
        });
        html += '</div>';

        html += '<div class="heatmap-body">';
        heatmapData.forEach((row, i) => {
            html += '<div class="heatmap-row">';
            row.forEach(value => {
                const intensity = Math.floor(value / 25);
                html += `<div class="heatmap-cell intensity-${intensity}" title="${value} activités"></div>`;
            });
            html += '</div>';
        });
        html += '</div></div>';

        container.innerHTML = html;
    }

    /**
     * Render smart recommendations
     */
    renderRecommendations() {
        const container = this.container.querySelector('#recommendations-list');
        if (!container) {
            console.warn('⚠️ recommendations-list container not found in', this.container);
            return;
        }

        const recommendations = [
            { icon: getIcon('lightbulb'), text: 'Concept "Architecture Agent" est en forte croissance. Considérez créer une documentation dédiée.', priority: 'high' },
            { icon: getIcon('alertTriangle'), text: 'Thread "Tests système complet" est inactif depuis 4 jours. Relancer les tests?', priority: 'medium' },
            { icon: getIcon('book'), text: 'Document "API-Documentation.md" est très consulté. Vérifier sa mise à jour.', priority: 'low' },
            { icon: getIcon('target'), text: 'Pic d\'activité détecté à 14h-15h. Optimiser les ressources à cette période.', priority: 'medium' }
        ];

        const html = recommendations.map((rec, index) => `
            <div class="recommendation-item priority-${rec.priority}">
                <div class="rec-icon">${rec.icon}</div>
                <div class="rec-content">
                    <div class="rec-text">${rec.text}</div>
                    <div class="rec-priority">Priorité: ${rec.priority}</div>
                </div>
                <button class="btn-rec-action" data-rec-index="${index}">Action</button>
            </div>
        `).join('');

        container.innerHTML = html;

        // Attach recommendation action buttons
        container.querySelectorAll('.btn-rec-action').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const recIndex = parseInt(e.target.dataset.recIndex);
                this.handleRecommendationAction(recommendations[recIndex]);
            });
        });
    }

    /**
     * Generate heatmap data (mock)
     */
    generateHeatmapData(days, hours) {
        const data = [];
        for (let i = 0; i < hours; i++) {
            const row = [];
            for (let j = 0; j < days; j++) {
                // Peak activity during work hours (9-18) on weekdays
                const isWeekday = j < 5;
                const isWorkHours = i >= 9 && i <= 18;
                const baseActivity = isWeekday && isWorkHours ? 60 : 20;
                row.push(Math.floor(Math.random() * 40 + baseActivity));
            }
            data.push(row);
        }
        return data;
    }


    /**
     * Format time ago
     */
    formatTimeAgo(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const diff = Math.floor((now - date) / 1000); // seconds

        if (diff < 60) return 'À l\'instant';
        if (diff < 3600) return `Il y a ${Math.floor(diff / 60)}min`;
        if (diff < 86400) return `Il y a ${Math.floor(diff / 3600)}h`;
        return `Il y a ${Math.floor(diff / 86400)}j`;
    }

    /**
     * Navigate to section
     */
    navigateToSection(target) {
        console.log('Navigate to:', target);

        // Get eventBus from multiple possible sources
        const eventBus = window.emergenceApp?.eventBus || window.App?.eventBus || window.app?.eventBus;

        // Emit navigation event based on target
        if (eventBus) {
            const moduleMap = {
                'concepts': 'memory',
                'threads': 'chat',
                'documents': 'documents'
            };
            const targetModule = moduleMap[target] || target;
            eventBus.emit('app:navigate', { moduleId: targetModule });
            console.log('✅ Navigation émise vers:', targetModule);
        } else {
            console.warn('⚠️ EventBus non disponible pour la navigation');
        }
    }

    /**
     * Explore concept
     */
    exploreConcept(conceptId) {
        console.log('Explore concept:', conceptId);

        // Get eventBus from multiple possible sources
        const eventBus = window.emergenceApp?.eventBus || window.App?.eventBus || window.app?.eventBus;

        // Navigate to memory module with concept highlighted
        if (eventBus) {
            eventBus.emit('app:navigate', { moduleId: 'memory', data: { conceptId } });
            console.log('✅ Navigation émise vers memory avec conceptId:', conceptId);
        } else {
            console.warn('⚠️ EventBus non disponible pour la navigation');
        }

        // Show notification
        if (window.notifications) {
            window.notifications.info(`Navigation vers le concept #${conceptId}`);
        }
    }

    /**
     * Open thread
     */
    openThread(threadId) {
        console.log('Open thread:', threadId);

        // Get eventBus from multiple possible sources
        const eventBus = window.emergenceApp?.eventBus || window.App?.eventBus || window.app?.eventBus;

        // Navigate to chat module and load thread
        if (eventBus) {
            eventBus.emit('app:navigate', { moduleId: 'chat' });
            console.log('✅ Navigation émise vers chat');

            // Emit thread change event after a short delay
            setTimeout(() => {
                eventBus.emit('thread:change', { threadId });
                console.log('✅ Changement de thread émis:', threadId);
            }, 300);
        } else {
            console.warn('⚠️ EventBus non disponible pour la navigation');
        }

        // Show notification
        if (window.notifications) {
            window.notifications.info(`Ouverture du thread...`);
        }
    }

    /**
     * View document
     */
    viewDocument(docId) {
        console.log('View document:', docId);

        // Get eventBus from multiple possible sources
        const eventBus = window.emergenceApp?.eventBus || window.App?.eventBus || window.app?.eventBus;

        // Navigate to documents module with document selected
        if (eventBus) {
            eventBus.emit('app:navigate', { moduleId: 'documents', data: { docId } });
            console.log('✅ Navigation émise vers documents avec docId:', docId);
        } else {
            console.warn('⚠️ EventBus non disponible pour la navigation');
        }

        // Show notification
        if (window.notifications) {
            window.notifications.info(`Ouverture du document #${docId}`);
        }
    }

    /**
     * Handle recommendation action
     */
    handleRecommendationAction(recommendation) {
        console.log('Recommendation action:', recommendation);

        // Show notification with the action
        if (window.notifications) {
            window.notifications.success(`Action: ${recommendation.text}`);
        }

        // Navigate based on recommendation content
        if (recommendation.text.includes('Concept')) {
            this.navigateToSection('concepts');
        } else if (recommendation.text.includes('Thread')) {
            this.navigateToSection('threads');
        } else if (recommendation.text.includes('Document')) {
            this.navigateToSection('documents');
        }
    }

    /**
     * Change period
     */
    async changePeriod(period) {
        await this.loadInsights();
    }

    /**
     * Show error message
     */
    showError(message) {
        console.error('✗', message);
        // TODO: Integrate with notification system
    }

    /**
     * Cleanup
     */
    destroy() {
        if (this.container) {
            this.container.innerHTML = '';
        }
    }
}

// Export singleton instance
export const cockpitInsights = new CockpitInsights();
