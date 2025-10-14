/**
 * @module features/admin/admin
 * @description Point d'entree du module Admin - Comprehensive administration interface
 * V2.0 - Includes AuthAdminModule and AdminDashboard with tabbed navigation
 */

import { AuthAdminModule } from './auth-admin-module.js';
import { adminDashboard } from './admin-dashboard.js';
import { BetaInvitationsModule } from './beta-invitations-module.js';

export default class AdminModule {
  constructor(eventBus, state, options = {}) {
    this.eventBus = eventBus;
    this.state = state;
    this.options = options;

    this.container = null;
    this._initialized = false;
    this._stylesLoaded = false;
    this._authModule = new AuthAdminModule(eventBus, state, options);
    this._betaModule = new BetaInvitationsModule(eventBus, state, options);
    this._currentView = 'dashboard'; // 'dashboard', 'auth', or 'beta'
  }

  _isAdmin() {
    try {
      const role = this.state?.get?.('auth.role');
      if (typeof role !== 'string') return false;
      return role.trim().toLowerCase() === 'admin';
    } catch (_err) {
      return false;
    }
  }

  async _loadStyles() {
    if (this._stylesLoaded) return;

    const cssPath = '/src/frontend/features/admin/admin-dashboard.css';
    const existingLink = document.querySelector(`link[href="${cssPath}"]`);
    if (existingLink) {
      this._stylesLoaded = true;
      return;
    }

    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = cssPath;
    document.head.appendChild(link);

    this._stylesLoaded = true;
  }

  init() {
    if (this._initialized) return;
    if (typeof this._authModule?.init === 'function') {
      this._authModule.init();
    }
    this._initialized = true;
  }

  async mount(container) {
    if (!container) return;

    if (!this._isAdmin()) {
      container.innerHTML = `
        <div class="admin-access-denied">
          <div class="access-denied-content">
            <div class="access-denied-icon">🔒</div>
            <h2>Accès Refusé</h2>
            <p>Vous devez disposer des privilèges administrateur pour accéder à cette section.</p>
          </div>
        </div>
      `;
      return;
    }

    this.container = container;

    // Load CSS
    await this._loadStyles();

    // Render admin interface with tabs
    container.innerHTML = `
      <div class="admin-module-wrapper">
        <div class="admin-navigation">
          <button class="admin-nav-btn ${this._currentView === 'dashboard' ? 'active' : ''}"
                  data-view="dashboard">
            📊 Dashboard Global
          </button>
          <button class="admin-nav-btn ${this._currentView === 'auth' ? 'active' : ''}"
                  data-view="auth">
            🔐 Gestion Utilisateurs
          </button>
          <button class="admin-nav-btn ${this._currentView === 'beta' ? 'active' : ''}"
                  data-view="beta">
            📧 Invitations Beta
          </button>
        </div>
        <div class="admin-views">
          <div id="admin-dashboard-view" class="admin-view ${this._currentView === 'dashboard' ? 'active' : ''}"></div>
          <div id="admin-auth-view" class="admin-view ${this._currentView === 'auth' ? 'active' : ''}"></div>
          <div id="admin-beta-view" class="admin-view ${this._currentView === 'beta' ? 'active' : ''}"></div>
        </div>
      </div>
    `;

    // Attach navigation handlers
    container.querySelectorAll('.admin-nav-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const view = e.target.dataset.view;
        this._switchView(view);
      });
    });

    // Mount active view
    await this._mountView(this._currentView);
  }

  async _switchView(view) {
    if (this._currentView === view) return;

    this._currentView = view;

    // Update navigation buttons
    this.container.querySelectorAll('.admin-nav-btn').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.view === view);
    });

    // Update views
    this.container.querySelectorAll('.admin-view').forEach(viewEl => {
      viewEl.classList.toggle('active', viewEl.id === `admin-${view}-view`);
    });

    // Mount the new view
    await this._mountView(view);
  }

  async _mountView(view) {
    if (view === 'dashboard') {
      const dashboardContainer = this.container.querySelector('#admin-dashboard-view');
      if (dashboardContainer && !dashboardContainer.hasChildNodes()) {
        await adminDashboard.init('admin-dashboard-view');
      }
    } else if (view === 'auth') {
      const authContainer = this.container.querySelector('#admin-auth-view');
      if (authContainer && !authContainer.hasChildNodes() && typeof this._authModule?.mount === 'function') {
        this._authModule.mount(authContainer);
      }
    } else if (view === 'beta') {
      const betaContainer = this.container.querySelector('#admin-beta-view');
      if (betaContainer && !betaContainer.hasChildNodes() && typeof this._betaModule?.mount === 'function') {
        this._betaModule.mount(betaContainer);
      }
    }
  }

  unmount() {
    // Unmount dashboard
    if (adminDashboard && typeof adminDashboard.destroy === 'function') {
      try {
        adminDashboard.destroy();
      } catch (err) {
        console.warn('[Admin] Error unmounting dashboard:', err);
      }
    }

    // Unmount auth module
    if (typeof this._authModule?.unmount === 'function') {
      try {
        this._authModule.unmount();
      } catch (err) {
        console.warn('[Admin] Error unmounting auth module:', err);
      }
    }

    // Unmount beta module
    if (typeof this._betaModule?.unmount === 'function') {
      try {
        this._betaModule.unmount();
      } catch (err) {
        console.warn('[Admin] Error unmounting beta module:', err);
      }
    }

    if (this.container) {
      this.container.innerHTML = '';
      this.container = null;
    }
  }
}
