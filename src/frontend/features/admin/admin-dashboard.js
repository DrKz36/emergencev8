/**
 * Admin Dashboard Module
 * Global statistics and user management for administrators
 * V1.0 - Comprehensive admin analytics
 */

import { AdminIcons, getIcon } from './admin-icons.js';

export class AdminDashboard {
    constructor() {
        this.container = null;
        this.activeView = 'global';
        this.refreshInterval = null;
        this.currentUserDetails = null;
    }

    /**
     * Initialize admin dashboard
     */
    async init(containerId) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            console.error('[AdminDashboard] Container not found');
            return;
        }

        // Verify admin role
        const isAdmin = await this.verifyAdminRole();
        if (!isAdmin) {
            this.renderAccessDenied();
            return;
        }

        this.render();
        await this.loadGlobalData();
        this.startAutoRefresh();
    }

    /**
     * Verify user has admin role
     */
    async verifyAdminRole() {
        try {
            const state = JSON.parse(localStorage.getItem('emergenceState-V14') || '{}');
            return state.auth?.role === 'admin';
        } catch (e) {
            return false;
        }
    }

    /**
     * Render access denied message
     */
    renderAccessDenied() {
        this.container.innerHTML = `
            <div class="admin-access-denied">
                <div class="access-denied-icon">${AdminIcons.lock}</div>
                <h2>Accès Refusé</h2>
                <p>Vous devez être administrateur pour accéder à cette section.</p>
            </div>
        `;
    }

    /**
     * Render admin dashboard UI
     */
    render() {
        this.container.innerHTML = `
            <div class="admin-dashboard">
                <!-- Header -->
                <div class="admin-header">
                    <div class="admin-title">
                        <h1>${getIcon('shield', 'header-icon')} Administration</h1>
                        <p class="admin-subtitle">Vue d'ensemble globale du système</p>
                    </div>
                    <div class="admin-actions">
                        <button class="btn-refresh-admin" title="Actualiser">
                            ${getIcon('refresh', 'btn-icon')} Actualiser
                        </button>
                    </div>
                </div>

                <!-- Tabs -->
                <div class="admin-tabs">
                    <button class="admin-tab ${this.activeView === 'global' ? 'active' : ''}"
                            data-view="global">
                        <span class="tab-icon">${AdminIcons.barChart}</span>
                        <span class="tab-label">Vue Globale</span>
                    </button>
                    <button class="admin-tab ${this.activeView === 'users' ? 'active' : ''}"
                            data-view="users">
                        <span class="tab-icon">${AdminIcons.users}</span>
                        <span class="tab-label">Utilisateurs</span>
                    </button>
                    <button class="admin-tab ${this.activeView === 'costs' ? 'active' : ''}"
                            data-view="costs">
                        <span class="tab-icon">${AdminIcons.dollarSign}</span>
                        <span class="tab-label">Coûts Détaillés</span>
                    </button>
                    <button class="admin-tab ${this.activeView === 'analytics' ? 'active' : ''}"
                            data-view="analytics">
                        <span class="tab-icon">${AdminIcons.activity}</span>
                        <span class="tab-label">Analytics</span>
                    </button>
                </div>

                <!-- Content Area -->
                <div class="admin-content">
                    <!-- Global View -->
                    <div class="admin-view ${this.activeView === 'global' ? 'active' : ''}"
                         data-view="global">
                        <div id="global-stats" class="admin-section"></div>
                        <div id="date-metrics" class="admin-section"></div>
                    </div>

                    <!-- Users View -->
                    <div class="admin-view ${this.activeView === 'users' ? 'active' : ''}"
                         data-view="users">
                        <div id="users-list" class="admin-section"></div>
                    </div>

                    <!-- Costs View -->
                    <div class="admin-view ${this.activeView === 'costs' ? 'active' : ''}"
                         data-view="costs">
                        <div id="costs-breakdown" class="admin-section"></div>
                    </div>

                    <!-- Analytics View -->
                    <div class="admin-view ${this.activeView === 'analytics' ? 'active' : ''}"
                         data-view="analytics">
                        <div id="analytics-sessions" class="admin-section"></div>
                        <div id="analytics-metrics" class="admin-section"></div>
                    </div>
                </div>

                <!-- User Details Modal -->
                <div id="user-details-modal" class="modal hidden">
                    <div class="modal-overlay"></div>
                    <div class="modal-content">
                        <div class="modal-header">
                            <h3>Détails Utilisateur</h3>
                            <button class="modal-close">${AdminIcons.x}</button>
                        </div>
                        <div id="user-details-content" class="modal-body"></div>
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
        // Tab switching
        this.container.querySelectorAll('.admin-tab').forEach(tab => {
            tab.addEventListener('click', (e) => {
                const view = e.currentTarget.dataset.view;
                this.switchView(view);
            });
        });

        // Refresh button
        const refreshBtn = this.container.querySelector('.btn-refresh-admin');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.refresh());
        }

        // Modal close
        const modalClose = this.container.querySelector('.modal-close');
        const modalOverlay = this.container.querySelector('.modal-overlay');
        if (modalClose) {
            modalClose.addEventListener('click', () => this.closeUserModal());
        }
        if (modalOverlay) {
            modalOverlay.addEventListener('click', () => this.closeUserModal());
        }
    }

    /**
     * Switch active view
     */
    async switchView(view) {
        this.activeView = view;

        // Update tabs
        this.container.querySelectorAll('.admin-tab').forEach(tab => {
            tab.classList.toggle('active', tab.dataset.view === view);
        });

        // Update views
        this.container.querySelectorAll('.admin-view').forEach(viewEl => {
            viewEl.classList.toggle('active', viewEl.dataset.view === view);
        });

        // Load view data
        await this.loadViewData(view);
    }

    /**
     * Load global dashboard data
     */
    async loadGlobalData() {
        try {
            const token = this._getAuthToken();
            const response = await fetch('/api/admin/dashboard/global', {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error(`Admin API error: ${response.status}`);
            }

            const data = await response.json();
            this.globalData = data;

            // Render current view
            await this.loadViewData(this.activeView);

        } catch (error) {
            console.error('[AdminDashboard] Error loading global data:', error);
            this.showError('Impossible de charger les données globales');
        }
    }

    /**
     * Load data for specific view
     */
    async loadViewData(view) {
        switch (view) {
            case 'global':
                this.renderGlobalView();
                break;
            case 'users':
                this.renderUsersView();
                break;
            case 'costs':
                this.renderCostsView();
                break;
            case 'analytics':
                await this.renderAnalyticsView();
                break;
        }
    }

    /**
     * Render global statistics view
     */
    renderGlobalView() {
        if (!this.globalData) return;

        const statsContainer = this.container.querySelector('#global-stats');
        const dateContainer = this.container.querySelector('#date-metrics');

        // Global stats
        const costs = this.globalData.global_costs || {};
        const monitoring = this.globalData.global_monitoring || {};

        statsContainer.innerHTML = `
            <h3>${getIcon('barChart', 'section-icon')} Statistiques Globales</h3>
            <div class="admin-stats-grid">
                <div class="admin-stat-card">
                    <div class="stat-icon">${AdminIcons.users}</div>
                    <div class="stat-value">${monitoring.total_users || 0}</div>
                    <div class="stat-label">Utilisateurs</div>
                </div>
                <div class="admin-stat-card">
                    <div class="stat-icon">${AdminIcons.messageCircle}</div>
                    <div class="stat-value">${monitoring.total_sessions || 0}</div>
                    <div class="stat-label">Sessions</div>
                </div>
                <div class="admin-stat-card">
                    <div class="stat-icon">${AdminIcons.files}</div>
                    <div class="stat-value">${monitoring.total_documents || 0}</div>
                    <div class="stat-label">Documents</div>
                </div>
                <div class="admin-stat-card highlight">
                    <div class="stat-icon">${AdminIcons.dollarSign}</div>
                    <div class="stat-value">$${(costs.total_cost || 0).toFixed(2)}</div>
                    <div class="stat-label">Coût Total</div>
                </div>
            </div>

            <div class="admin-costs-timeline">
                <div class="cost-item">
                    <span class="cost-period">Aujourd'hui</span>
                    <span class="cost-value">$${(costs.today_cost || 0).toFixed(2)}</span>
                </div>
                <div class="cost-item">
                    <span class="cost-period">Cette semaine</span>
                    <span class="cost-value">$${(costs.current_week_cost || 0).toFixed(2)}</span>
                </div>
                <div class="cost-item">
                    <span class="cost-period">Ce mois</span>
                    <span class="cost-value">$${(costs.current_month_cost || 0).toFixed(2)}</span>
                </div>
            </div>
        `;

        // Date metrics
        const dateMetrics = this.globalData.date_metrics?.last_7_days || [];
        const chartHtml = this.renderCostsChart(dateMetrics);
        dateContainer.innerHTML = `
            <h3>${getIcon('trendingUp', 'section-icon')} Évolution des Coûts (7 derniers jours)</h3>
            ${chartHtml}
        `;
    }

    /**
     * Render users list view
     */
    renderUsersView() {
        if (!this.globalData) return;

        const usersContainer = this.container.querySelector('#users-list');
        const users = this.globalData.users_breakdown || [];

        if (users.length === 0) {
            usersContainer.innerHTML = `
                <div class="admin-empty">
                    <p>Aucun utilisateur trouvé</p>
                </div>
            `;
            return;
        }

        // Get current filter from data attribute or default to 'all'
        const currentFilter = usersContainer.dataset.roleFilter || 'all';

        // Filter users based on role
        const filteredUsers = currentFilter === 'all'
            ? users
            : users.filter(user => {
                const role = (user.role || 'member').toLowerCase();
                return role === currentFilter;
            });

        // Count users by role
        const adminCount = users.filter(u => (u.role || 'member').toLowerCase() === 'admin').length;
        const memberCount = users.filter(u => (u.role || 'member').toLowerCase() === 'member').length;

        const usersHtml = filteredUsers.map(user => {
            const email = user.email || user.user_id;
            const role = user.role || 'member';
            const roleBadge = role === 'admin'
                ? '<span class="user-role-badge admin">Admin</span>'
                : '<span class="user-role-badge member">Membre</span>';

            const usageTimeHours = user.total_usage_time_minutes
                ? (user.total_usage_time_minutes / 60).toFixed(1)
                : '0';

            const firstSessionDate = user.first_session
                ? new Date(user.first_session).toLocaleString('fr-FR', {
                    year: 'numeric',
                    month: 'short',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit'
                  })
                : 'Jamais';

            const lastActivityDate = user.last_activity
                ? new Date(user.last_activity).toLocaleString('fr-FR', {
                    year: 'numeric',
                    month: 'short',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit'
                  })
                : 'Jamais';

            const modulesCount = user.modules_used ? user.modules_used.length : 0;
            const modulesText = modulesCount > 0
                ? `${modulesCount} module${modulesCount > 1 ? 's' : ''}`
                : 'Aucun module';

            return `
                <div class="admin-user-card" data-user-id="${user.user_id}">
                    <div class="user-header">
                        <div class="user-email-section">
                            ${getIcon('user', 'user-icon')}
                            <div class="user-email-info">
                                <strong>${email}</strong>
                                ${roleBadge}
                            </div>
                        </div>
                    </div>
                    <div class="user-info-grid">
                        <div class="user-info-item">
                            <span class="info-label">${getIcon('clock', 'info-icon')} Première connexion</span>
                            <span class="info-value">${firstSessionDate}</span>
                        </div>
                        <div class="user-info-item">
                            <span class="info-label">${getIcon('activity', 'info-icon')} Dernière activité</span>
                            <span class="info-value">${lastActivityDate}</span>
                        </div>
                        <div class="user-info-item">
                            <span class="info-label">${getIcon('clock', 'info-icon')} Temps d'utilisation</span>
                            <span class="info-value">${usageTimeHours}h</span>
                        </div>
                        <div class="user-info-item">
                            <span class="info-label">${getIcon('barChart', 'info-icon')} Modules utilisés</span>
                            <span class="info-value">${modulesText}</span>
                        </div>
                    </div>
                    <div class="user-stats">
                        <span class="user-stat">${getIcon('messageCircle', 'stat-icon')} ${user.session_count} sessions</span>
                        <span class="user-stat">${getIcon('file', 'stat-icon')} ${user.document_count} docs</span>
                        <span class="user-stat highlight">${getIcon('dollarSign', 'stat-icon')} $${user.total_cost.toFixed(2)}</span>
                    </div>
                    <button class="btn-view-user" data-user-id="${user.user_id}">
                        Voir détails ${getIcon('arrowRight', 'btn-icon')}
                    </button>
                </div>
            `;
        }).join('');

        usersContainer.innerHTML = `
            <div class="admin-users-header">
                <h3>${getIcon('users', 'section-icon')} Utilisateurs (${filteredUsers.length}/${users.length})</h3>
                <div class="admin-users-filters">
                    <button class="user-filter-btn ${currentFilter === 'all' ? 'active' : ''}"
                            data-filter="all">
                        Tous (${users.length})
                    </button>
                    <button class="user-filter-btn ${currentFilter === 'member' ? 'active' : ''}"
                            data-filter="member">
                        ${getIcon('user', 'filter-icon')} Membres (${memberCount})
                    </button>
                    <button class="user-filter-btn ${currentFilter === 'admin' ? 'active' : ''}"
                            data-filter="admin">
                        ${getIcon('shield', 'filter-icon')} Admins (${adminCount})
                    </button>
                </div>
            </div>
            <div class="admin-users-list">
                ${usersHtml.length > 0 ? usersHtml : '<div class="admin-empty"><p>Aucun utilisateur avec ce filtre</p></div>'}
            </div>
        `;

        // Attach click handlers for filters
        usersContainer.querySelectorAll('.user-filter-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const filter = e.currentTarget.dataset.filter;
                usersContainer.dataset.roleFilter = filter;
                this.renderUsersView();
            });
        });

        // Attach click handlers for user details
        usersContainer.querySelectorAll('.btn-view-user').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const userId = e.target.closest('.btn-view-user').dataset.userId;
                this.showUserDetails(userId);
            });
        });
    }

    /**
     * Render costs breakdown view
     */
    renderCostsView() {
        if (!this.globalData) return;

        const costsContainer = this.container.querySelector('#costs-breakdown');
        const users = this.globalData.users_breakdown || [];

        // Sort by cost descending
        const sortedUsers = [...users].sort((a, b) => b.total_cost - a.total_cost);

        const costsHtml = sortedUsers.map((user, index) => {
            const email = user.email || user.user_id;
            const costsByModule = user.costs_by_module || {};
            const modulesHtml = Object.keys(costsByModule).length > 0
                ? Object.entries(costsByModule)
                    .sort((a, b) => b[1] - a[1])
                    .map(([module, cost]) => `
                        <div class="module-cost-item">
                            <span class="module-name">${module}</span>
                            <span class="module-cost">$${cost.toFixed(2)}</span>
                        </div>
                    `).join('')
                : '<p class="no-modules">Aucune donnée de module</p>';

            return `
                <div class="admin-cost-row">
                    <div class="cost-rank">#${index + 1}</div>
                    <div class="cost-user-info">
                        <div class="cost-user">${email}</div>
                        <div class="cost-modules-breakdown">
                            ${modulesHtml}
                        </div>
                    </div>
                    <div class="cost-bar-container">
                        <div class="cost-bar" style="width: ${this.calculateBarWidth(user.total_cost, sortedUsers)}%"></div>
                        <div class="cost-amount">$${user.total_cost.toFixed(2)}</div>
                    </div>
                </div>
            `;
        }).join('');

        costsContainer.innerHTML = `
            <h3>${getIcon('dollarSign', 'section-icon')} Répartition des Coûts par Utilisateur et Module</h3>
            <div class="admin-costs-breakdown">
                ${costsHtml}
            </div>
        `;
    }

    /**
     * Calculate bar width percentage for cost visualization
     */
    calculateBarWidth(cost, allUsers) {
        if (allUsers.length === 0) return 0;
        const maxCost = Math.max(...allUsers.map(u => u.total_cost));
        if (maxCost === 0) return 0;
        return (cost / maxCost) * 100;
    }

    /**
     * Render costs chart
     */
    renderCostsChart(data) {
        // Check if data exists and is not empty
        if (!data || data.length === 0) {
            return '<p class="admin-empty">Aucune donnée disponible</p>';
        }

        // Check if all costs are 0 or null/undefined
        const totalCost = data.reduce((sum, d) => sum + (d.cost || 0), 0);
        if (totalCost === 0) {
            return '<p class="admin-empty">Aucune donnée de coûts pour la période (tous les coûts sont à $0.00)</p>';
        }

        // Calculate max cost for bar height scaling
        const maxCost = Math.max(...data.map(d => d.cost || 0), 0.01);

        // Render chart bars
        const barsHtml = data.map(item => {
            const cost = item.cost || 0;
            const height = (cost / maxCost) * 100;
            return `
                <div class="chart-bar">
                    <div class="bar-fill" style="height: ${height}%"
                         title="${item.date}: $${cost.toFixed(2)}"></div>
                    <div class="bar-label">${new Date(item.date).toLocaleDateString('fr-FR', { day: 'numeric', month: 'short' })}</div>
                    <div class="bar-value">$${cost.toFixed(2)}</div>
                </div>
            `;
        }).join('');

        return `
            <div class="admin-chart">
                ${barsHtml}
            </div>
        `;
    }

    /**
     * Show user details modal
     */
    async showUserDetails(userId) {
        try {
            const token = this._getAuthToken();
            const response = await fetch(`/api/admin/dashboard/user/${userId}`, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error(`User details API error: ${response.status}`);
            }

            const data = await response.json();
            this.currentUserDetails = data;

            // Render modal content
            const modalContent = this.container.querySelector('#user-details-content');
            modalContent.innerHTML = this.renderUserDetailsContent(data);

            // Show modal
            const modal = this.container.querySelector('#user-details-modal');
            modal.classList.remove('hidden');

        } catch (error) {
            console.error('[AdminDashboard] Error loading user details:', error);
            this.showError('Impossible de charger les détails utilisateur');
        }
    }

    /**
     * Render user details modal content
     */
    renderUserDetailsContent(data) {
        const costs = data.costs || {};
        const sessions = data.sessions || [];
        const documents = data.documents || [];
        const history = data.cost_history || [];

        return `
            <div class="user-details">
                <div class="user-details-header">
                    <h4>${data.user_id}</h4>
                </div>

                <div class="user-details-section">
                    <h5>${getIcon('dollarSign', 'section-icon')} Coûts</h5>
                    <div class="details-grid">
                        <div class="detail-item">
                            <span class="detail-label">Total</span>
                            <span class="detail-value">$${(costs.total_cost || 0).toFixed(2)}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Aujourd'hui</span>
                            <span class="detail-value">$${(costs.today_cost || 0).toFixed(2)}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Cette semaine</span>
                            <span class="detail-value">$${(costs.current_week_cost || 0).toFixed(2)}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Ce mois</span>
                            <span class="detail-value">$${(costs.current_month_cost || 0).toFixed(2)}</span>
                        </div>
                    </div>
                </div>

                <div class="user-details-section">
                    <h5>${getIcon('messageCircle', 'section-icon')} Sessions (${sessions.length})</h5>
                    <div class="sessions-list">
                        ${sessions.slice(0, 5).map(s => `
                            <div class="session-item">
                                <span class="session-id">${s.id}</span>
                                <span class="session-date">${new Date(s.created_at).toLocaleString('fr-FR')}</span>
                            </div>
                        `).join('')}
                        ${sessions.length > 5 ? `<p class="more-items">... et ${sessions.length - 5} autres</p>` : ''}
                    </div>
                </div>

                <div class="user-details-section">
                    <h5>${getIcon('files', 'section-icon')} Documents (${documents.length})</h5>
                    ${documents.length === 0 ? '<p>Aucun document</p>' : `
                        <div class="documents-list">
                            ${documents.slice(0, 5).map(d => `
                                <div class="document-item">
                                    <span class="doc-name">${d.filename || d.title}</span>
                                    <span class="doc-date">${new Date(d.uploaded_at || d.created_at).toLocaleDateString('fr-FR')}</span>
                                </div>
                            `).join('')}
                            ${documents.length > 5 ? `<p class="more-items">... et ${documents.length - 5} autres</p>` : ''}
                        </div>
                    `}
                </div>

                <div class="user-details-section">
                    <h5>${getIcon('activity', 'section-icon')} Historique des Coûts (30 derniers jours)</h5>
                    ${history.length === 0 ? '<p>Aucun historique</p>' : `
                        <div class="cost-history-list">
                            ${history.slice(0, 10).map(h => `
                                <div class="history-item">
                                    <span class="history-date">${new Date(h.timestamp).toLocaleString('fr-FR')}</span>
                                    <span class="history-agent">${h.agent}</span>
                                    <span class="history-model">${h.model}</span>
                                    <span class="history-cost">$${h.cost.toFixed(4)}</span>
                                </div>
                            `).join('')}
                            ${history.length > 10 ? `<p class="more-items">... et ${history.length - 10} autres</p>` : ''}
                        </div>
                    `}
                </div>
            </div>
        `;
    }

    /**
     * Close user details modal
     */
    closeUserModal() {
        const modal = this.container.querySelector('#user-details-modal');
        if (modal) {
            modal.classList.add('hidden');
        }
        this.currentUserDetails = null;
    }

    /**
     * Refresh dashboard data
     */
    async refresh() {
        const btn = this.container.querySelector('.btn-refresh-admin');
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = `${getIcon('clock', 'btn-icon')} Actualisation...`;
        }

        await this.loadGlobalData();

        if (btn) {
            btn.innerHTML = `${getIcon('check', 'btn-icon')} Actualisé`;
            setTimeout(() => {
                btn.innerHTML = `${getIcon('refresh', 'btn-icon')} Actualiser`;
                btn.disabled = false;
            }, 2000);
        }
    }

    /**
     * Start auto-refresh
     */
    startAutoRefresh() {
        // Refresh every 2 minutes
        this.refreshInterval = setInterval(() => {
            this.loadGlobalData();
        }, 2 * 60 * 1000);
    }

    /**
     * Stop auto-refresh
     */
    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }

    /**
     * Get auth token from storage
     */
    _getAuthToken() {
        try {
            return localStorage.getItem('emergence.id_token') ||
                   localStorage.getItem('id_token') ||
                   sessionStorage.getItem('emergence.id_token') ||
                   sessionStorage.getItem('id_token');
        } catch (e) {
            return null;
        }
    }

    /**
     * Render analytics view with threads and system metrics
     */
    async renderAnalyticsView() {
        const sessionsContainer = this.container.querySelector('#analytics-sessions');
        const metricsContainer = this.container.querySelector('#analytics-metrics');

        // Show loading state
        sessionsContainer.innerHTML = '<p class="loading">Chargement des threads...</p>';
        metricsContainer.innerHTML = '<p class="loading">Chargement des métriques...</p>';

        try {
            // Load threads and metrics in parallel
            const [threadsData, metricsData] = await Promise.all([
                this.loadActiveThreads(),
                this.loadSystemMetrics()
            ]);

            // Render threads list
            this.renderThreadsList(threadsData, sessionsContainer);

            // Render system metrics
            this.renderSystemMetrics(metricsData, metricsContainer);

        } catch (error) {
            console.error('[AdminDashboard] Error loading analytics:', error);
            sessionsContainer.innerHTML = '<p class="error">Erreur lors du chargement des threads</p>';
            metricsContainer.innerHTML = '<p class="error">Erreur lors du chargement des métriques</p>';
        }
    }

    /**
     * Load active threads from API
     */
    async loadActiveThreads() {
        const token = this._getAuthToken();
        const response = await fetch('/api/admin/analytics/threads', {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error(`Threads API error: ${response.status}`);
        }

        return await response.json();
    }

    /**
     * Load system metrics from API
     */
    async loadSystemMetrics() {
        const token = this._getAuthToken();
        const response = await fetch('/api/admin/metrics/system', {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error(`Metrics API error: ${response.status}`);
        }

        return await response.json();
    }

    /**
     * Render threads list with revoke buttons
     */
    renderThreadsList(data, container) {
        const threads = data.threads || [];

        if (threads.length === 0) {
            container.innerHTML = `
                <h3>${getIcon('messageCircle', 'section-icon')} Threads de Conversation Actifs (0)</h3>
                <div class="admin-empty">
                    <p>Aucun thread actif</p>
                </div>
            `;
            return;
        }

        // Separate active and inactive threads
        const activeThreads = threads.filter(t => t.is_active);
        const inactiveThreads = threads.filter(t => !t.is_active);

        const threadsHtml = threads.map(thread => {
            const isActive = thread.is_active;
            const statusBadge = isActive
                ? '<span class="session-status active">Actif</span>'
                : '<span class="session-status inactive">Inactif</span>';

            const lastActivity = thread.last_activity
                ? new Date(thread.last_activity).toLocaleString('fr-FR', {
                    year: 'numeric',
                    month: 'short',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit'
                  })
                : 'Jamais';

            const createdAt = thread.created_at
                ? new Date(thread.created_at).toLocaleString('fr-FR', {
                    year: 'numeric',
                    month: 'short',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit'
                  })
                : 'Inconnu';

            return `
                <div class="session-card ${isActive ? 'active' : 'inactive'}">
                    <div class="session-header">
                        <div class="session-user-info">
                            ${getIcon('user', 'session-icon')}
                            <div>
                                <strong>${thread.email}</strong>
                                ${statusBadge}
                            </div>
                        </div>
                        <button class="btn-revoke-session" data-session-id="${thread.session_id}">
                            ${getIcon('x', 'btn-icon')} Révoquer
                        </button>
                    </div>
                    <div class="session-details">
                        <div class="session-detail">
                            <span class="detail-label">${getIcon('hash', 'detail-icon')} ID Thread</span>
                            <span class="detail-value session-id">${thread.session_id}</span>
                        </div>
                        <div class="session-detail">
                            <span class="detail-label">${getIcon('clock', 'detail-icon')} Créé le</span>
                            <span class="detail-value">${createdAt}</span>
                        </div>
                        <div class="session-detail">
                            <span class="detail-label">${getIcon('activity', 'detail-icon')} Dernière activité</span>
                            <span class="detail-value">${lastActivity}</span>
                        </div>
                        <div class="session-detail">
                            <span class="detail-label">${getIcon('clock', 'detail-icon')} Durée</span>
                            <span class="detail-value">${thread.duration_minutes.toFixed(0)} min</span>
                        </div>
                        <div class="session-detail">
                            <span class="detail-label">${getIcon('monitor', 'detail-icon')} Appareil</span>
                            <span class="detail-value">${thread.device}</span>
                        </div>
                        <div class="session-detail">
                            <span class="detail-label">${getIcon('globe', 'detail-icon')} IP</span>
                            <span class="detail-value">${thread.ip_address}</span>
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        container.innerHTML = `
            <div class="info-banner">
                <div class="info-icon">${getIcon('info', 'info-icon')}</div>
                <div class="info-content">
                    <strong>Note :</strong> Cette vue affiche les <strong>threads de conversation</strong> (table <code>sessions</code>).
                    Pour consulter les <strong>sessions d'authentification JWT</strong> (table <code>auth_sessions</code>),
                    utilisez le module <strong>Auth Admin</strong>.
                </div>
            </div>
            <h3>${getIcon('messageCircle', 'section-icon')} Threads de Conversation (${threads.length})</h3>
            <div class="sessions-summary">
                <div class="summary-item">
                    <span class="summary-label">Actifs</span>
                    <span class="summary-value active">${activeThreads.length}</span>
                </div>
                <div class="summary-item">
                    <span class="summary-label">Inactifs</span>
                    <span class="summary-value">${inactiveThreads.length}</span>
                </div>
            </div>
            <div class="sessions-grid">
                ${threadsHtml}
            </div>
        `;

        // Attach revoke button handlers
        container.querySelectorAll('.btn-revoke-session').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const sessionId = e.currentTarget.dataset.sessionId;
                await this.revokeSession(sessionId);
            });
        });
    }

    /**
     * Revoke a session
     */
    async revokeSession(sessionId) {
        if (!confirm(`Voulez-vous vraiment révoquer la session ${sessionId} ?\n\nL'utilisateur sera déconnecté immédiatement.`)) {
            return;
        }

        try {
            const token = this._getAuthToken();
            const response = await fetch(`/api/admin/sessions/${sessionId}/revoke`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error(`Revoke API error: ${response.status}`);
            }

            // Reload analytics view
            await this.renderAnalyticsView();

            // Show success notification
            this.showSuccessNotification('Session révoquée avec succès');

        } catch (error) {
            console.error('[AdminDashboard] Error revoking session:', error);
            this.showError('Impossible de révoquer la session');
        }
    }

    /**
     * Render system metrics dashboard
     */
    renderSystemMetrics(data, container) {
        const uptime = data.uptime || {};
        const performance = data.performance || {};
        const reliability = data.reliability || {};
        const database = data.database || {};

        container.innerHTML = `
            <h3>${getIcon('activity', 'section-icon')} Métriques Système</h3>

            <div class="metrics-grid">
                <!-- Uptime -->
                <div class="metric-card uptime">
                    <div class="metric-icon">${getIcon('clock', 'metric-icon-lg')}</div>
                    <div class="metric-content">
                        <div class="metric-label">Uptime</div>
                        <div class="metric-value">${uptime.formatted || 'N/A'}</div>
                        <div class="metric-subtitle">Démarré ${uptime.start_time ? new Date(uptime.start_time).toLocaleString('fr-FR', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }) : 'Inconnu'}</div>
                    </div>
                </div>

                <!-- CPU -->
                <div class="metric-card cpu">
                    <div class="metric-icon">${getIcon('cpu', 'metric-icon-lg')}</div>
                    <div class="metric-content">
                        <div class="metric-label">CPU</div>
                        <div class="metric-value">${performance.cpu_percent || 0}%</div>
                        <div class="metric-subtitle">Utilisation processeur</div>
                    </div>
                </div>

                <!-- Memory -->
                <div class="metric-card memory">
                    <div class="metric-icon">${getIcon('database', 'metric-icon-lg')}</div>
                    <div class="metric-content">
                        <div class="metric-label">Mémoire</div>
                        <div class="metric-value">${performance.memory_mb || 0} MB</div>
                        <div class="metric-subtitle">RAM utilisée</div>
                    </div>
                </div>

                <!-- Latency -->
                <div class="metric-card latency">
                    <div class="metric-icon">${getIcon('zap', 'metric-icon-lg')}</div>
                    <div class="metric-content">
                        <div class="metric-label">Latence Moyenne</div>
                        <div class="metric-value">${performance.average_latency_ms || 0} ms</div>
                        <div class="metric-subtitle">Temps de réponse API</div>
                    </div>
                </div>

                <!-- Error Rate -->
                <div class="metric-card errors ${reliability.error_rate_percent > 5 ? 'warning' : ''}">
                    <div class="metric-icon">${getIcon('alertCircle', 'metric-icon-lg')}</div>
                    <div class="metric-content">
                        <div class="metric-label">Taux d'Erreur</div>
                        <div class="metric-value">${reliability.error_rate_percent || 0}%</div>
                        <div class="metric-subtitle">${reliability.total_errors_last_hour || 0} erreurs (1h)</div>
                    </div>
                </div>

                <!-- Database -->
                <div class="metric-card database">
                    <div class="metric-icon">${getIcon('hardDrive', 'metric-icon-lg')}</div>
                    <div class="metric-content">
                        <div class="metric-label">Base de Données</div>
                        <div class="metric-value">${database.size_mb || 0} MB</div>
                        <div class="metric-subtitle">${database.total_tables || 0} tables</div>
                    </div>
                </div>
            </div>

            <div class="metrics-timestamp">
                Dernière mise à jour : ${data.timestamp ? new Date(data.timestamp).toLocaleString('fr-FR') : 'Inconnu'}
            </div>
        `;
    }

    /**
     * Show success notification
     */
    showSuccessNotification(message) {
        const successDiv = document.createElement('div');
        successDiv.className = 'admin-success-notification';
        successDiv.innerHTML = `
            <div class="success-content">
                <span class="success-icon">${getIcon('check', 'notification-icon')}</span>
                <span class="success-message">${message}</span>
                <button class="success-close">${AdminIcons.x || '×'}</button>
            </div>
        `;

        this.container.insertBefore(successDiv, this.container.firstChild);

        const closeBtn = successDiv.querySelector('.success-close');
        const remove = () => successDiv.remove();
        closeBtn.addEventListener('click', remove);
        setTimeout(remove, 3000);
    }

    /**
     * Show error message
     */
    showError(message) {
        console.error('[AdminDashboard]', message);

        // Create error notification
        const errorDiv = document.createElement('div');
        errorDiv.className = 'admin-error-notification';
        errorDiv.innerHTML = `
            <div class="error-content">
                <span class="error-icon">${AdminIcons.alertCircle || '⚠️'}</span>
                <span class="error-message">${message}</span>
                <button class="error-close">${AdminIcons.x || '×'}</button>
            </div>
        `;

        // Add to container
        this.container.insertBefore(errorDiv, this.container.firstChild);

        // Auto-remove after 5 seconds
        const closeBtn = errorDiv.querySelector('.error-close');
        const remove = () => errorDiv.remove();
        closeBtn.addEventListener('click', remove);
        setTimeout(remove, 5000);
    }

    /**
     * Cleanup
     */
    destroy() {
        this.stopAutoRefresh();
        if (this.container) {
            this.container.innerHTML = '';
        }
    }
}

// Export singleton instance
export const adminDashboard = new AdminDashboard();
