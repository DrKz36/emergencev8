/**
 * @module ui/modals
 * @description Gestionnaire de modales avec focus trap
 */

import { ANIMATIONS, EVENTS } from '../shared/constants.js';
import { generateId } from '../shared/utils.js';
import { eventBus } from '../core/event-bus.js';

class ModalManager {
  constructor() {
    this.modals = new Map();
    this.activeModal = null;
    this.container = null;
    this.init();
  }

  /**
   * Initialize modal container
   */
  init() {
    this.container = document.createElement('div');
    this.container.className = 'modals-container';
    document.body.appendChild(this.container);
    
    // Close on ESC
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && this.activeModal) {
        const modal = this.modals.get(this.activeModal);
        if (modal && !modal.persistent) {
          this.close(this.activeModal);
        }
      }
    });
  }

  /**
   * Open modal
   * @param {Object} options
   * @returns {string} Modal ID
   */
  open({
    title = '',
    content = '',
    footer = null,
    size = 'medium', // small, medium, large, full
    closable = true,
    persistent = false,
    className = '',
    onOpen = null,
    onClose = null
  }) {
    const id = generateId();
    
    // Create backdrop
    const backdrop = document.createElement('div');
    backdrop.className = 'modal-backdrop fade-in';
    
    // Create modal
    const modal = document.createElement('div');
    modal.className = `modal modal--${size} ${className} slide-up`;
    modal.setAttribute('role', 'dialog');
    modal.setAttribute('aria-modal', 'true');
    if (title) modal.setAttribute('aria-labelledby', `modal-title-${id}`);
    
    let html = '<div class="modal__content">';
    
    // Header
    if (title || closable) {
      html += '<div class="modal__header">';
      if (title) {
        html += `<h2 class="modal__title" id="modal-title-${id}">${title}</h2>`;
      }
      if (closable) {
        html += '<button class="modal__close" aria-label="Fermer">';
        html += '<i class="icon icon--x"></i>';
        html += '</button>';
      }
      html += '</div>';
    }
    
    // Body
    html += '<div class="modal__body">';
    if (typeof content === 'string') {
      html += content;
    }
    html += '</div>';
    
    // Footer
    if (footer) {
      html += '<div class="modal__footer">';
      if (typeof footer === 'string') {
        html += footer;
      }
      html += '</div>';
    }
    
    html += '</div>';
    modal.innerHTML = html;
    
    // Append HTML content if not string
    if (typeof content !== 'string') {
      modal.querySelector('.modal__body').appendChild(content);
    }
    if (footer && typeof footer !== 'string') {
      modal.querySelector('.modal__footer').appendChild(footer);
    }
    
    // Event listeners
    if (closable) {
      const closeBtn = modal.querySelector('.modal__close');
      closeBtn.addEventListener('click', () => this.close(id));
      
      if (!persistent) {
        backdrop.addEventListener('click', () => this.close(id));
      }
    }
    
    // Store modal data
    const modalData = {
      id,
      modal,
      backdrop,
      persistent,
      closable,
      onClose,
      previousFocus: document.activeElement
    };
    
    this.modals.set(id, modalData);
    
    // Add to DOM
    this.container.appendChild(backdrop);
    this.container.appendChild(modal);
    
    // Set active
    this.activeModal = id;
    
    // Focus trap
    this.setupFocusTrap(modal);
    
    // Focus first focusable element
    setTimeout(() => {
      const focusable = modal.querySelector(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );
      if (focusable) focusable.focus();
    }, 100);
    
    // Prevent body scroll
    document.body.style.overflow = 'hidden';
    
    // Emit event
    eventBus.emit(EVENTS.MODAL_OPEN, { id });
    
    // Callback
    if (onOpen) onOpen();
    
    return id;
  }

  /**
   * Close modal
   * @param {string} id
   */
  close(id) {
    const modalData = this.modals.get(id);
    if (!modalData) return;
    
    const { modal, backdrop, onClose, previousFocus } = modalData;
    
    // Animate out
    modal.classList.add('slide-down');
    backdrop.classList.add('fade-out');
    
    setTimeout(() => {
      modal.remove();
      backdrop.remove();
      this.modals.delete(id);
      
      // Update active modal
      if (this.activeModal === id) {
        this.activeModal = null;
        // Check if there are other modals
        if (this.modals.size > 0) {
          this.activeModal = Array.from(this.modals.keys()).pop();
        }
      }
      
      // Restore body scroll if no more modals
      if (this.modals.size === 0) {
        document.body.style.overflow = '';
      }
      
      // Restore focus
      if (previousFocus && previousFocus.focus) {
        previousFocus.focus();
      }
      
      // Emit event
      eventBus.emit(EVENTS.MODAL_CLOSE, { id });
      
      // Callback
      if (onClose) onClose();
    }, 300);
  }

  /**
   * Close all modals
   */
  closeAll() {
    this.modals.forEach((_, id) => this.close(id));
  }

  /**
   * Setup focus trap
   * @param {HTMLElement} modal
   */
  setupFocusTrap(modal) {
    const focusableElements = modal.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    
    if (focusableElements.length === 0) return;
    
    const firstFocusable = focusableElements[0];
    const lastFocusable = focusableElements[focusableElements.length - 1];
    
    modal.addEventListener('keydown', (e) => {
      if (e.key !== 'Tab') return;
      
      if (e.shiftKey) {
        if (document.activeElement === firstFocusable) {
          e.preventDefault();
          lastFocusable.focus();
        }
      } else {
        if (document.activeElement === lastFocusable) {
          e.preventDefault();
          firstFocusable.focus();
        }
      }
    });
  }

  /**
   * Confirm dialog
   * @param {Object} options
   * @returns {Promise<boolean>}
   */
  confirm({
    title = 'Confirmation',
    message = 'Êtes-vous sûr ?',
    confirmText = 'Confirmer',
    cancelText = 'Annuler',
    type = 'warning' // info, warning, danger
  }) {
    return new Promise((resolve) => {
      const footer = document.createElement('div');
      footer.className = 'modal__actions';
      
      const cancelBtn = document.createElement('button');
      cancelBtn.className = 'btn btn--secondary';
      cancelBtn.textContent = cancelText;
      
      const confirmBtn = document.createElement('button');
      confirmBtn.className = `btn btn--${type === 'danger' ? 'danger' : 'primary'}`;
      confirmBtn.textContent = confirmText;
      
      footer.appendChild(cancelBtn);
      footer.appendChild(confirmBtn);
      
      const modalId = this.open({
        title,
        content: `<p class="modal__message">${message}</p>`,
        footer,
        size: 'small',
        persistent: true
      });
      
      cancelBtn.addEventListener('click', () => {
        this.close(modalId);
        resolve(false);
      });
      
      confirmBtn.addEventListener('click', () => {
        this.close(modalId);
        resolve(true);
      });
    });
  }

  /**
   * Alert dialog
   * @param {Object} options
   * @returns {Promise<void>}
   */
  alert({
    title = 'Information',
    message = '',
    buttonText = 'OK',
    type = 'info'
  }) {
    return new Promise((resolve) => {
      const footer = document.createElement('div');
      footer.className = 'modal__actions';
      
      const okBtn = document.createElement('button');
      okBtn.className = 'btn btn--primary';
      okBtn.textContent = buttonText;
      
      footer.appendChild(okBtn);
      
      const modalId = this.open({
        title,
        content: `<p class="modal__message modal__message--${type}">${message}</p>`,
        footer,
        size: 'small'
      });
      
      okBtn.addEventListener('click', () => {
        this.close(modalId);
        resolve();
      });
    });
  }
}

// Export singleton instance
export const modals = new ModalManager();

// Also export for custom usage
export { ModalManager };