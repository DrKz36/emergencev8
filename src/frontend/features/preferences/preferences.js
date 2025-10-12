/**
 * Preferences Module - Integration wrapper for Settings features
 * Wraps settings-main.js for app.js integration
 * ADMIN ONLY - Members see work-in-progress notification
 */

import { settings } from '../settings/settings-main.js';
import { notifications } from '../../shared/notifications.js';

export class Preferences {
    constructor(eventBus, state) {
        this.eventBus = eventBus;
        this.state = state;
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

            // Check user role - admin only access
            const userRole = this.state?.get?.('auth.role') || 'member';
            const normalizedRole = typeof userRole === 'string' ? userRole.trim().toLowerCase() : 'member';

            if (normalizedRole !== 'admin') {
                // Show work-in-progress notification for non-admin users
                container.innerHTML = `
                    <div style="
                        display: flex;
                        flex-direction: column;
                        align-items: center;
                        justify-content: center;
                        height: 100%;
                        padding: 2rem;
                        text-align: center;
                        color: rgba(226, 232, 240, 0.9);
                    ">
                        <svg xmlns="http://www.w3.org/2000/svg" style="
                            width: 80px;
                            height: 80px;
                            margin-bottom: 1.5rem;
                            color: rgba(148, 163, 184, 0.6);
                        " fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                        </svg>
                        <h2 style="
                            font-size: 1.5rem;
                            font-weight: 600;
                            margin-bottom: 1rem;
                            color: rgba(226, 232, 240, 0.95);
                        ">⚙️ Réglages en développement</h2>
                        <p style="
                            font-size: 1.05rem;
                            max-width: 500px;
                            line-height: 1.6;
                            color: rgba(226, 232, 240, 0.8);
                            margin-bottom: 0.5rem;
                        ">
                            Les paramètres de configuration sont actuellement en cours de développement
                            et seront bientôt disponibles pour tous les utilisateurs.
                        </p>
                        <p style="
                            font-size: 0.95rem;
                            max-width: 500px;
                            line-height: 1.5;
                            color: rgba(148, 163, 184, 0.8);
                        ">
                            Cette fonctionnalité arrivera prochainement dans une mise à jour.
                            Merci de votre patience ! 🚀
                        </p>
                    </div>
                `;

                notifications.info('Les réglages sont en cours de développement et seront bientôt disponibles.');
                this.initialized = true;
                console.log('[Preferences] Work-in-progress notification shown for non-admin user');
                return;
            }

            // Admin users get full access to settings
            await settings.init(container.id);

            this.initialized = true;
            console.log('[Preferences] Mounted successfully for admin user');
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
