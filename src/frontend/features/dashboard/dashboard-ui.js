/**
 * @module features/dashboard/dashboard-ui
 * @description UI du Cockpit - V3.0 "Concordance"
 * - Ne stocke plus le conteneur, le reçoit en paramètre.
 */
export class DashboardUI {
    constructor() {
        console.log("✅ DashboardUI V3.0 (Concordance) Initialisé.");
    }

    renderInitialLayout(container) {
        if (!container) return;
        container.innerHTML = `
            <div class="dashboard-container">
                <div class="dashboard-header">
                    <h2>Cockpit de Pilotage</h2>
                    <button id="refresh-costs-btn" class="btn btn-secondary">Rafraîchir</button>
                </div>
                <div id="dashboard-content" class="dashboard-content">
                    <div id="dashboard-loader" class="loader" style="display: none;"></div>
                    <div id="dashboard-error" class="error-message" style="display: none;"></div>
                    <h3 class="dashboard-section-title">Suivi des Coûts</h3>
                    <div id="costs-grid" class="dashboard-grid"></div>
                    <h3 class="dashboard-section-title">Monitoring Système</h3>
                    <div id="monitoring-grid" class="dashboard-grid"></div>
                    <h3 class="dashboard-section-title">Benchmarks Agentiques</h3>
                    <div id="benchmarks-panel" class="dashboard-benchmarks"></div>
                </div>
            </div>
        `;
    }

    showLoading(container, isLoading) {
        const loader = container.querySelector('#dashboard-loader');
        if (loader) loader.style.display = isLoading ? 'block' : 'none';
    }

    showError(container, message) {
        const errorContainer = container.querySelector('#dashboard-error');
        if (errorContainer) {
            errorContainer.textContent = message;
            errorContainer.style.display = 'block';
        }
        const costsGrid = container.querySelector('#costs-grid');
        const monitoringGrid = container.querySelector('#monitoring-grid');
        const benchmarksPanel = container.querySelector('#benchmarks-panel');
        if (costsGrid) costsGrid.style.display = 'none';
        if (monitoringGrid) monitoringGrid.style.display = 'none';
        if (benchmarksPanel) benchmarksPanel.style.display = 'none';
    }

    renderDashboardData(container, data) {
        const costsGrid = container.querySelector('#costs-grid');
        const monitoringGrid = container.querySelector('#monitoring-grid');
        const benchmarksPanel = container.querySelector('#benchmarks-panel');
        if (!costsGrid || !monitoringGrid) return;

        costsGrid.style.display = 'grid';
        monitoringGrid.style.display = 'grid';
        if (benchmarksPanel) benchmarksPanel.style.display = 'block';
        const errorContainer = container.querySelector('#dashboard-error');
        if (errorContainer) errorContainer.style.display = 'none';

        const { costs = {}, monitoring = {}, thresholds = {} } = data;
        const totalCostFormatted = (costs.total_cost || 0).toFixed(4);

        costsGrid.innerHTML = `
            ${this._createCostCard('Jour', costs.today_cost, thresholds.daily_threshold, '☀️')}
            ${this._createCostCard('Semaine', costs.current_week_cost, thresholds.weekly_threshold, '📅')}
            ${this._createCostCard('Mois', costs.current_month_cost, thresholds.monthly_threshold, '🗓️')}
            ${this._createMonitorCard('Coût Total', totalCostFormatted, '$', 'Depuis le début', '💰')}
        `;
        
        monitoringGrid.innerHTML = `
            ${this._createMonitorCard('Sessions Archivées', monitoring.total_sessions, 'sessions', 'Interactions complètes', '🗂️')}
            ${this._createMonitorCard('Documents Traités', monitoring.total_documents, 'documents', 'Fichiers analysés', '📄')}
        `;
    }

    _createCostCard(title, value, threshold, icon) {
        const val = value || 0;
        const thresh = threshold || 1;
        const percent = Math.min((val / thresh) * 100, 100);
        let progressClass = percent > 75 ? 'critical' : percent > 50 ? 'high' : '';
        return `
            <div class="summary-card cost"><div class="card-header"><h3>${title}</h3><div class="card-icon">${icon}</div></div><div class="card-body"><div class="metric-value">${val.toFixed(4)} $</div><div class="progress-bar-container"><div class="progress-bar ${progressClass}" style="width: ${percent}%;"></div></div><p>Limite : ${thresh.toFixed(2)} $</p></div></div>`;
    }

    _createMonitorCard(title, value, unit, description, icon) {
        return `
            <div class="summary-card monitor"><div class="card-header"><h3>${title}</h3><div class="card-icon">${icon}</div></div><div class="card-body"><div class="metric-value">${value || 0} <span class="unit">${unit}</span></div><p>${description}</p></div></div>`;
    }
}
