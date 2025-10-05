/**
 * Preferences Module - Integration wrapper for Settings features
 * Wraps settings-main.js for app.js integration
 */

import { settings } from '../settings/settings-main.js';
import { notifications } from '../../shared/notifications.js';

export class Preferences {
    constructor() {
        this.initialized = false;
    }

    init() {
        // Called by app.js loadModule() - just mark as ready
        console.log('[Preferences] Module loaded');
    }

    async mount(container) {
        if (this.initialized) {
            console.warn('[Preferences] Already mounted');
            return;
        }

        try {
            // Initialize notification system if not already done
            if (!notifications.container) {
                notifications.init();
            }

            // Initialize settings
            await settings.init(container.id);

            this.initialized = true;
            console.log('[Preferences] Mounted successfully');
        } catch (error) {
            console.error('[Preferences] Mount error:', error);
            notifications.error('Erreur lors du chargement du module Preferences');
        }
    }

    unmount() {
        if (settings && settings.destroy) {
            settings.destroy();
        }
        this.initialized = false;
    }
}

export const preferences = new Preferences();
