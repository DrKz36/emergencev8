/**
 * Global Notification System
 * Toast notifications for user feedback
 */

export class NotificationSystem {
    constructor() {
        this.container = null;
        this.notifications = [];
        this.maxNotifications = 5;
        this.defaultDuration = 4000;
    }

    /**
     * Initialize notification system
     */
    init() {
        if (this.container) return;

        this.container = document.createElement('div');
        this.container.className = 'notification-container';
        this.container.setAttribute('aria-live', 'polite');
        this.container.setAttribute('aria-atomic', 'true');
        document.body.appendChild(this.container);
    }

    /**
     * Show notification
     */
    show(message, type = 'info', duration = this.defaultDuration) {
        if (!this.container) {
            this.init();
        }

        const notification = this.createNotification(message, type, duration);
        this.notifications.push(notification);

        // Remove oldest if exceeding max
        if (this.notifications.length > this.maxNotifications) {
            const oldest = this.notifications.shift();
            oldest.element.remove();
        }

        return notification;
    }

    /**
     * Create notification element
     */
    createNotification(message, type, duration) {
        const id = `notification-${Date.now()}-${Math.random()}`;
        const element = document.createElement('div');
        element.className = `notification notification-${type}`;
        element.id = id;
        element.setAttribute('role', 'alert');

        const icon = this.getIcon(type);
        const closeBtn = document.createElement('button');
        closeBtn.className = 'notification-close';
        closeBtn.innerHTML = '×';
        closeBtn.setAttribute('aria-label', 'Fermer la notification');
        closeBtn.onclick = () => this.remove(id);

        element.innerHTML = `
            <span class="notification-icon">${icon}</span>
            <span class="notification-message">${message}</span>
        `;
        element.appendChild(closeBtn);

        this.container.appendChild(element);

        // Trigger animation
        requestAnimationFrame(() => {
            element.classList.add('notification-show');
        });

        // Auto remove
        let timeoutId = null;
        if (duration > 0) {
            timeoutId = setTimeout(() => this.remove(id), duration);
        }

        return {
            id,
            element,
            type,
            timeoutId,
            remove: () => this.remove(id)
        };
    }

    /**
     * Get icon for notification type
     */
    getIcon(type) {
        const icons = {
            success: '✓',
            error: '✗',
            warning: '⚠',
            info: 'ℹ'
        };
        return icons[type] || icons.info;
    }

    /**
     * Remove notification
     */
    remove(id) {
        const notification = this.notifications.find(n => n.id === id);
        if (!notification) return;

        // Clear timeout
        if (notification.timeoutId) {
            clearTimeout(notification.timeoutId);
        }

        // Fade out animation
        notification.element.classList.remove('notification-show');
        notification.element.classList.add('notification-hide');

        setTimeout(() => {
            notification.element.remove();
            this.notifications = this.notifications.filter(n => n.id !== id);
        }, 300);
    }

    /**
     * Convenience methods
     */
    success(message, duration) {
        return this.show(message, 'success', duration);
    }

    error(message, duration) {
        return this.show(message, 'error', duration);
    }

    warning(message, duration) {
        return this.show(message, 'warning', duration);
    }

    info(message, duration) {
        return this.show(message, 'info', duration);
    }

    /**
     * Clear all notifications
     */
    clearAll() {
        this.notifications.forEach(n => this.remove(n.id));
    }

    /**
     * Destroy notification system
     */
    destroy() {
        this.clearAll();
        if (this.container) {
            this.container.remove();
            this.container = null;
        }
    }
}

// Export singleton instance
export const notifications = new NotificationSystem();
