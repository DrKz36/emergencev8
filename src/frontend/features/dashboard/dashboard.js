/**
 * @module features/dashboard/dashboard
 * @description Logique du module Dashboard - V4.1 "Concordance" avec matrice benchmarks.
 */
import { DashboardUI } from './dashboard-ui.js';
import { BenchmarksMatrix } from './benchmarks.js';
import { api } from '../../shared/api-client.js';

export class DashboardModule {
    constructor(eventBus, state) {
        this.eventBus = eventBus;
        this.state = state;
        this.ui = null;
        this.container = null;
        this.isInitialized = false;
        this.listeners = [];
        this.benchmarksMatrix = null;
        console.log('✅ DashboardModule V4.1 (Concordance) prêt.');
    }

    init() {
        if (this.isInitialized) return;
        this.ui = new DashboardUI();
        this.benchmarksMatrix = new BenchmarksMatrix();
        this.isInitialized = true;
        console.log('✅ DashboardModule V4.1 (Concordance) initialisé.');
    }

    mount(container) {
        this.container = container;
        this.ui.renderInitialLayout(this.container);
        const panel = this.container?.querySelector?.('#benchmarks-panel');
        if (panel && this.benchmarksMatrix) {
            this.benchmarksMatrix.mount(panel);
        }
        this.registerEventListeners();
        this.loadDashboardData();
    }

    destroy() {
        this.listeners.forEach((unsubscribe) => unsubscribe());
        this.listeners = [];
        this.container = null;
    }

    registerEventListeners() {
        if (!this.container) return;
        this.container.addEventListener('click', (e) => {
            if (e.target.id === 'refresh-costs-btn') {
                this.loadDashboardData();
            }
        });
    }

    async loadDashboardData() {
        if (!this.container) return;
        const panel = this.container.querySelector?.('#benchmarks-panel');
        this.ui.showLoading(this.container, true);
        if (this.benchmarksMatrix && panel) {
            this.benchmarksMatrix.showLoading();
        }

        try {
            const [dashboardData, benchmarkPayload, scenariosPayload] = await Promise.all([
                api.getDashboardSummary(),
                api.getBenchmarkResults({ limit: 12 }).catch((error) => {
                    console.warn('Benchmarks results request failed:', error);
                    return null;
                }),
                api.getBenchmarkScenarios().catch((error) => {
                    console.warn('Benchmarks scenarios request failed:', error);
                    return null;
                }),
            ]);

            this.ui.renderDashboardData(this.container, dashboardData);

            if (this.benchmarksMatrix && panel) {
                const matrices = benchmarkPayload?.results ?? [];
                const scenarios = scenariosPayload?.scenarios ?? [];
                this.benchmarksMatrix.render(panel, { matrices, scenarios });
            }
        } catch (error) {
            console.error('Erreur lors de la récupération des données du cockpit:', error);
            const message = error?.message || 'Erreur inconnue.';
            this.ui.showError(this.container, `Impossible de charger les données. (${message})`);
            if (this.benchmarksMatrix && panel) {
                this.benchmarksMatrix.showError('Impossible de récupérer les benchmarks.');
            }
        } finally {
            this.ui.showLoading(this.container, false);
        }
    }
}
