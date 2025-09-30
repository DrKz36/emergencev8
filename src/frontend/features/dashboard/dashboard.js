/**
 * @module features/dashboard/dashboard
 * @description Logique du module Dashboard - V4.0 "Concordance"
 * - Applique le pattern init/mount.
 */
import { DashboardUI } from './dashboard-ui.js';
import { api } from '../../shared/api-client.js';

export class DashboardModule {
    constructor(eventBus, state) {
        this.eventBus = eventBus;
        this.state = state;
        this.ui = null;
        this.container = null;
        this.isInitialized = false;
        this.listeners = [];
        console.log("✅ DashboardModule V4.0 (Concordance) Prêt.");
    }

    init() {
        if (this.isInitialized) return;
        this.ui = new DashboardUI();
        this.isInitialized = true;
        console.log("✅ DashboardModule V4.0 (Concordance) Initialisé UNE SEULE FOIS.");
    }

    mount(container) {
        this.container = container;
        this.ui.renderInitialLayout(this.container);
        this.registerEventListeners();
        this.loadDashboardData();
    }

    destroy() {
        this.listeners.forEach(unsubscribe => unsubscribe());
        this.listeners = [];
        this.container = null;
    }

    registerEventListeners() {
        this.container.addEventListener('click', (e) => {
            if (e.target.id === 'refresh-costs-btn') {
                this.loadDashboardData();
            }
        });
    }

    async loadDashboardData() {
        if (!this.container) return;
        this.ui.showLoading(this.container, true);
        try {
            const data = await api.getDashboardSummary();
            this.ui.renderDashboardData(this.container, data);
        } catch (error) {
            console.error("Erreur lors de la récupération des données du cockpit:", error);
            const message = error?.message || 'Erreur inconnue.';
            this.ui.showError(this.container, `Impossible de charger les données. (${message})`);
        } finally {
            this.ui.showLoading(this.container, false);
        }
    }
}
