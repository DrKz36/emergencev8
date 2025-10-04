/**
 * @module features/admin/admin
 * @description Point d'entree du module Admin - encapsule AuthAdminModule et fournit l'API attendue par App.loadModule.
 */

import { AuthAdminModule } from './auth-admin-module.js';

export default class AdminModule {
  constructor(eventBus, state, options = {}) {
    this.eventBus = eventBus;
    this.state = state;
    this.options = options;

    this.container = null;
    this._initialized = false;
    this._module = new AuthAdminModule(eventBus, state, options);
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

  init() {
    if (this._initialized) return;
    if (typeof this._module?.init === 'function') {
      this._module.init();
    }
    this._initialized = true;
  }

  mount(container) {
    if (!container) return;
    if (!this._isAdmin()) {
      container.innerHTML = '';
      container.hidden = true;
      container.setAttribute('aria-hidden', 'true');
      return;
    }

    this.container = container;
    if (typeof this._module?.mount === 'function') {
      this._module.mount(container);
    }
  }

  unmount() {
    if (typeof this._module?.unmount === 'function') {
      this._module.unmount();
    }
    if (this.container) {
      this.container.innerHTML = '';
      this.container = null;
    }
  }
}
