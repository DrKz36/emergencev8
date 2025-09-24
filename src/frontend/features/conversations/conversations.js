/**
 * @module features/conversations/conversations
 * @description Module centralise pour la gestion des conversations.
 */

import { ThreadsPanel } from '../threads/threads.js';
import { EVENTS } from '../../shared/constants.js';

export default class ConversationsModule {
  constructor(eventBus, stateManager) {
    this.eventBus = eventBus;
    this.state = stateManager;
    this.container = null;

    this.panel = new ThreadsPanel(eventBus, stateManager, { keepMarkup: true });
    this._offThreadsDeleted = null;
    this._offThreadsList = null;
    this._initialized = false;
  }

  init() {
    if (this._initialized) return;
    if (this.eventBus?.on && !this._offThreadsDeleted) {
      const off = this.eventBus.on(
        EVENTS?.THREADS_DELETED || 'threads:deleted',
        () => this.updateEmptyState()
      );
      if (typeof off === 'function') this._offThreadsDeleted = off;
    }
    if (this.eventBus?.on && !this._offThreadsList) {
      const off = this.eventBus.on(
        EVENTS?.THREADS_LIST_UPDATED || 'threads:list_updated',
        () => this.updateEmptyState()
      );
      if (typeof off === 'function') this._offThreadsList = off;
    }
    this._initialized = true;
  }

  mount(container) {
    if (!container) return;
    this.container = container;
    container.classList.add('conversations-module');
    this.panel.setHostElement(container);
    this.panel.init();
    this.updateEmptyState();
  }

  updateEmptyState() {
    if (!this.container) return;
    const order = this.state?.get ? (this.state.get('threads.order') || []) : [];
    if (order.length === 0) {
      this.container.classList.add('conversations-module--empty');
    } else {
      this.container.classList.remove('conversations-module--empty');
    }
  }

  destroy() {
    this.panel.destroy();
    if (typeof this._offThreadsDeleted === 'function') {
      this._offThreadsDeleted();
      this._offThreadsDeleted = null;
    }
    if (typeof this._offThreadsList === 'function') {
      this._offThreadsList();
      this._offThreadsList = null;
    }
    this._initialized = false;
    this.container = null;
  }
}
