/**
 * @module ui/notifications
 * @description Système de notifications toast
 */

import { TIMEOUTS, ANIMATIONS } from '../shared/constants.js';
import { generateId } from '../shared/utils.js';

class NotificationManager {
  constructor() {
    this.container = null;
    this.notifications = new Map();
    this.queue = [];
    this.maxVisible = 3;
    this.init();
  }

  /**
   * Initialize notification container
   */
  init() {
    this.container = document.createElement('div');
    this.container.className = 'notifications-container';
    this.container.setAttribute('role', 'status');
    this.container.setAttribute('aria-live', 'polite');
    document.body.appendChild(this.container);
  }

  /**
   * Show notification
   * @param {Object} options
   * @returns {string} Notification ID
   */
  show({
    type = 'info', // success, error, warning, info
    title = '',
    message = '',
    duration = TIMEOUTS.NOTIFICATION,
    persistent = false,
    action = null,
    onClose = null
  }) {
    const id = generateId();
    
    const notification = {
      id,
      type,
      title,
      message,
      duration,
      persistent,
      action,
      onClose,
      element: null,
      timer: null
    };

    // Add to queue if too many visible
    if (this.notifications.size >= this.maxVisible) {
      this.queue.push(notification);
      return id;
    }

    this.render(notification);
    return id;
  }

  /**
   * Render notification
   * @param {Object} notification
   */
  render(notification) {
    const element = document.createElement('div');
    element.className = `notification notification--${notification.type} fade-in`;
    element.setAttribute('role', 'alert');
    
    let html = '<div class="notification__content">';
    
    // Icon
    const icons = {
      success: 'check-circle',
      error: 'x-circle',
      warning: 'alert-triangle',
      info: 'info-circle'
    };
    html += `<i class="notification__icon icon icon--${icons[notification.type]}"></i>`;
    
    // Text content
    html += '<div class="notification__text">';
    if (notification.title) {
      html += `<div class="notification__title">${notification.title}</div>`;
    }
    if (notification.message) {
      html += `<div class="notification__message">${notification.message}</div>`;
    }
    html += '</div>';
    
    // Close button
    html += '<button class="notification__close" aria-label="Fermer">';
    html += '<i class="icon icon--x"></i>';
    html += '</button>';
    
    html += '</div>';
    
    // Action button
    if (notification.action) {
      html += '<div class="notification__actions">';
      html += `<button class="notification__action">${notification.action.label}</button>`;
      html += '</div>';
    }
    
    element.innerHTML = html;
    
    // Event listeners
    const closeBtn = element.querySelector('.notification__close');
    closeBtn.addEventListener('click', () => this.close(notification.id));
    
    if (notification.action) {
      const actionBtn = element.querySelector('.notification__action');
      actionBtn.addEventListener('click', () => {
        notification.action.onClick();
        this.close(notification.id);
      });
    }
    
    // Add to DOM
    this.container.appendChild(element);
    notification.element = element;
    this.notifications.set(notification.id, notification);
    
    // Auto close
    if (!notification.persistent) {
      notification.timer = setTimeout(() => {
        this.close(notification.id);
      }, notification.duration);
    }
  }

  /**
   * Close notification
   * @param {string} id
   */
  close(id) {
    const notification = this.notifications.get(id);
    if (!notification) return;
    
    // Clear timer
    if (notification.timer) {
      clearTimeout(notification.timer);
    }
    
    // Animate out
    notification.element.classList.add('fade-out');
    
    setTimeout(() => {
      notification.element.remove();
      this.notifications.delete(id);
      
      // Call onClose callback
      if (notification.onClose) {
        notification.onClose();
      }
      
      // Process queue
      if (this.queue.length > 0) {
        const next = this.queue.shift();
        this.render(next);
      }
    }, 300);
  }

  /**
   * Close all notifications
   */
  closeAll() {
    this.notifications.forEach((_, id) => this.close(id));
    this.queue = [];
  }

  /**
   * Success notification shorthand
   * @param {string} message
   * @param {Object} options
   */
  success(message, options = {}) {
    return this.show({
      type: 'success',
      message,
      ...options
    });
  }

  /**
   * Error notification shorthand
   * @param {string} message
   * @param {Object} options
   */
  error(message, options = {}) {
    return this.show({
      type: 'error',
      message,
      duration: TIMEOUTS.NOTIFICATION * 2, // Errors stay longer
      ...options
    });
  }

  /**
   * Warning notification shorthand
   * @param {string} message
   * @param {Object} options
   */
  warning(message, options = {}) {
    return this.show({
      type: 'warning',
      message,
      ...options
    });
  }

  /**
   * Info notification shorthand
   * @param {string} message
   * @param {Object} options
   */
  info(message, options = {}) {
    return this.show({
      type: 'info',
      message,
      ...options
    });
  }

  /**
   * Loading notification
   * @param {string} message
   * @returns {Function} Close function
   */
  loading(message = 'Chargement...') {
    const id = this.show({
      type: 'info',
      message,
      persistent: true
    });
    
    return () => this.close(id);
  }
}

// Export singleton instance
export const notifications = new NotificationManager();

// Also export for custom usage
export { NotificationManager };