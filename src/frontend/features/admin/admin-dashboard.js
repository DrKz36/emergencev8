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
        if (!data || data.length === 0) {
            return '<p class="admin-empty">Aucune donnée disponible</p>';
        }

        const maxCost = Math.max(...data.map(d => d.cost), 0.01);
        const barsHtml = data.map(item => {
            const height = (item.cost / maxCost) * 100;
            return `
                <div class="chart-bar">
                    <div class="bar-fill" style="height: ${height}%"
                         title="${item.date}: $${item.cost.toFixed(2)}"></div>
                    <div class="bar-label">${new Date(item.date).toLocaleDateString('fr-FR', { day: 'numeric', month: 'short' })}</div>
                    <div class="bar-value">$${item.cost.toFixed(2)}</div>
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
