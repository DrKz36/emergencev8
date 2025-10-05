/**
 * Cockpit Module - Unified Analytics & Metrics Dashboard
 * Combines all analytics functionality in one place
 */

import { cockpit } from './cockpit-main.js';
import { notifications } from '../../shared/notifications.js';

export class CockpitModule {
    constructor() {
        this.initialized = false;
    }

    init() {
        // Called by app.js loadModule() - just mark as ready
        console.log('[Cockpit] Module loaded');
    }

    async mount(container) {
        if (this.initialized) {
            console.warn('[Cockpit] Already mounted');
            return;
        }

        try {
            // Initialize notification system if not already done
            if (!notifications.container) {
                notifications.init();
            }

            // Initialize cockpit
            await cockpit.init(container.id);

            this.initialized = true;
            console.log('[Cockpit] Mounted successfully');
        } catch (error) {
            console.error('[Cockpit] Mount error:', error);
            notifications.error('Erreur lors du chargement du Cockpit');
        }
    }

    unmount() {
        if (cockpit && cockpit.destroy) {
            cockpit.destroy();
        }
        this.initialized = false;
    }
}

export const cockpitModule = new CockpitModule();
