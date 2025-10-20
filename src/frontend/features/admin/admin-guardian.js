/**
 * Admin Guardian Module
 * Interface pour lancer audit Guardian manuellement et afficher résultats
 * Phase 4 Guardian Cloud Implementation
 */

export class AdminGuardianModule {
    constructor() {
        this.container = null;
        this.isAuditRunning = false;
    }

    /**
     * Initialise le module Guardian dans l'Admin Dashboard
     */
    init(container) {
        this.container = container;
        this.render();
        this.attachEventListeners();
    }

    /**
     * Render le module Guardian
     */
    render() {
        if (!this.container) return;

        const html = `
            <div class="guardian-module">
                <div class="guardian-header">
                    <h2>🛡️ Guardian Cloud Monitoring</h2>
                    <p class="guardian-subtitle">
                        Surveillance automatique production, documentation, intégrité système
                    </p>
                </div>

                <div class="guardian-actions">
                    <button id="generate-guardian-reports" class="btn btn-success">
                        📊 Générer Rapports
                    </button>
                    <button id="run-guardian-audit" class="btn btn-primary">
                        🚀 Lancer Audit Guardian
                    </button>
                    <button id="refresh-guardian-status" class="btn btn-secondary">
                        🔄 Rafraîchir Status
                    </button>
                </div>

                <div id="guardian-status" class="guardian-status">
                    <p class="text-muted">Cliquez sur "Lancer Audit Guardian" pour charger les rapports</p>
                </div>

                <div id="guardian-results" class="guardian-results" style="display: none;">
                    <!-- Results will be rendered here -->
                </div>
            </div>
        `;

        this.container.innerHTML = html;
    }

    /**
     * Attache les event listeners
     */
    attachEventListeners() {
        const generateBtn = document.getElementById('generate-guardian-reports');
        const runBtn = document.getElementById('run-guardian-audit');
        const refreshBtn = document.getElementById('refresh-guardian-status');

        if (generateBtn) {
            generateBtn.addEventListener('click', () => this.generateReports());
        }

        if (runBtn) {
            runBtn.addEventListener('click', () => this.runAudit());
        }

        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.runAudit());
        }
    }

    /**
     * Génère les rapports Guardian via API (production logs)
     */
    async generateReports() {
        if (this.isAuditRunning) {
            console.log('[AdminGuardian] Operation already running');
            return;
        }

        this.isAuditRunning = true;
        this.showLoading();

        try {
            console.log('[AdminGuardian] Generating Guardian reports...');

            const response = await fetch('/api/guardian/generate-reports', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Content-Length': '0'
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP error ${response.status}`);
            }

            const data = await response.json();

            console.log('[AdminGuardian] Generate response:', data);

            if (data && data.status === 'success') {
                const statusDiv = document.getElementById('guardian-status');
                if (statusDiv) {
                    statusDiv.innerHTML = `
                        <div class="alert alert-success">
                            <strong>✅ Succès:</strong> ${data.message}
                            <p class="text-muted mt-2">
                                Rapport généré: ${data.report.logs_analyzed} logs analysés,
                                ${data.report.summary.errors} erreurs,
                                ${data.report.summary.warnings} warnings
                            </p>
                            <p class="text-muted"><em>Cliquez sur "Lancer Audit" pour voir les détails</em></p>
                        </div>
                    `;
                }
            } else {
                throw new Error('Invalid response format');
            }

        } catch (error) {
            console.error('[AdminGuardian] Generate error:', error);
            this.displayError(error.message || 'Erreur lors de la génération des rapports');
        } finally {
            this.isAuditRunning = false;
        }
    }

    /**
     * Lance l'audit Guardian via API
     */
    async runAudit() {
        if (this.isAuditRunning) {
            console.log('[AdminGuardian] Audit already running');
            return;
        }

        this.isAuditRunning = true;
        this.showLoading();

        try {
            console.log('[AdminGuardian] Running Guardian audit...');

            const response = await fetch('/api/guardian/run-audit', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP error ${response.status}`);
            }

            const data = await response.json();

            console.log('[AdminGuardian] Audit response:', data);

            if (data && data.status === 'success') {
                this.displayResults(data);
            } else if (data && data.status === 'warning') {
                this.displayWarning(data.message);
            } else {
                throw new Error('Invalid response format');
            }

        } catch (error) {
            console.error('[AdminGuardian] Audit error:', error);
            this.displayError(error.message || 'Erreur lors de l\'audit Guardian');
        } finally {
            this.isAuditRunning = false;
        }
    }

    /**
     * Affiche l'état de chargement
     */
    showLoading() {
        const statusDiv = document.getElementById('guardian-status');
        if (!statusDiv) return;

        statusDiv.innerHTML = `
            <div class="loading-spinner">
                <div class="spinner"></div>
                <p>Chargement des rapports Guardian...</p>
            </div>
        `;
    }

    /**
     * Affiche un warning
     */
    displayWarning(message) {
        const statusDiv = document.getElementById('guardian-status');
        const resultsDiv = document.getElementById('guardian-results');

        if (statusDiv) {
            statusDiv.innerHTML = `
                <div class="alert alert-warning">
                    <strong>⚠️ Attention:</strong> ${message}
                </div>
            `;
        }

        if (resultsDiv) {
            resultsDiv.style.display = 'none';
        }
    }

    /**
     * Affiche une erreur
     */
    displayError(message) {
        const statusDiv = document.getElementById('guardian-status');
        const resultsDiv = document.getElementById('guardian-results');

        if (statusDiv) {
            statusDiv.innerHTML = `
                <div class="alert alert-danger">
                    <strong>❌ Erreur:</strong> ${message}
                </div>
            `;
        }

        if (resultsDiv) {
            resultsDiv.style.display = 'none';
        }
    }

    /**
     * Affiche les résultats de l'audit
     */
    displayResults(data) {
        const statusDiv = document.getElementById('guardian-status');
        const resultsDiv = document.getElementById('guardian-results');

        if (!data) return;

        // Status summary
        const statusClass = this.getStatusClass(data.global_status);
        const statusIcon = this.getStatusIcon(data.global_status);

        if (statusDiv) {
            statusDiv.innerHTML = `
                <div class="alert alert-${statusClass}">
                    <strong>${statusIcon} Status Global:</strong> ${data.global_status}
                    <span class="text-muted" style="float: right; font-size: 0.9em;">
                        ${new Date(data.timestamp).toLocaleString('fr-FR')}
                    </span>
                </div>
            `;
        }

        // Detailed results
        if (resultsDiv) {
            resultsDiv.style.display = 'block';

            const reportsLoaded = data.reports_loaded || [];
            const reportsMissing = data.reports_missing || [];
            const details = data.details || {};

            let html = `
                <div class="guardian-summary">
                    <h3>📊 Résumé Audit</h3>
                    <div class="summary-cards">
                        <div class="summary-card">
                            <div class="summary-value">${reportsLoaded.length}</div>
                            <div class="summary-label">Rapports Chargés</div>
                        </div>
                        <div class="summary-card">
                            <div class="summary-value critical">${data.total_critical || 0}</div>
                            <div class="summary-label">Critiques</div>
                        </div>
                        <div class="summary-card">
                            <div class="summary-value warning">${data.total_warnings || 0}</div>
                            <div class="summary-label">Warnings</div>
                        </div>
                        <div class="summary-card">
                            <div class="summary-value">${data.total_recommendations || 0}</div>
                            <div class="summary-label">Recommendations</div>
                        </div>
                    </div>
                </div>

                <div class="guardian-reports">
                    <h3>📋 Détails par Rapport</h3>
            `;

            // Détails de chaque rapport
            for (const reportName of reportsLoaded) {
                const reportDetails = details[reportName];
                if (!reportDetails) continue;

                const reportStatus = reportDetails.status || 'UNKNOWN';
                const reportSummary = reportDetails.summary || {};
                const recsCount = reportDetails.recommendations_count || 0;

                const reportIcon = this.getReportIcon(reportName);
                const reportLabel = this.getReportLabel(reportName);
                const reportStatusClass = this.getStatusClass(reportStatus);
                const reportStatusIcon = this.getStatusIcon(reportStatus);

                html += `
                    <div class="report-card">
                        <div class="report-header">
                            <span class="report-title">${reportIcon} ${reportLabel}</span>
                            <span class="badge badge-${reportStatusClass}">
                                ${reportStatusIcon} ${reportStatus}
                            </span>
                        </div>
                        <div class="report-body">
                            ${this.renderReportSummary(reportName, reportSummary)}
                            ${recsCount > 0 ? `<p><strong>Recommendations:</strong> ${recsCount}</p>` : ''}
                        </div>
                    </div>
                `;
            }

            // Rapports manquants
            if (reportsMissing.length > 0) {
                html += `
                    <div class="report-card report-missing">
                        <div class="report-header">
                            <span class="report-title">⚠️ Rapports Manquants</span>
                        </div>
                        <div class="report-body">
                            <ul>
                                ${reportsMissing.map(name => `<li>${name}</li>`).join('')}
                            </ul>
                        </div>
                    </div>
                `;
            }

            html += `</div>`; // Close guardian-reports

            resultsDiv.innerHTML = html;
        }
    }

    /**
     * Render summary spécifique selon le type de rapport
     */
    renderReportSummary(reportName, summary) {
        if (!summary || Object.keys(summary).length === 0) {
            return '<p class="text-muted">Aucun summary disponible</p>';
        }

        let html = '<div class="report-summary">';

        // Production report
        if (reportName === 'prod_report.json') {
            html += `
                <p><strong>Logs:</strong> ${summary.total_logs || 0}</p>
                <p><strong>Erreurs:</strong> ${summary.error_count || 0}</p>
                <p><strong>Warnings:</strong> ${summary.warning_count || 0}</p>
            `;
        }
        // Documentation report
        else if (reportName === 'docs_report.json') {
            html += `
                <p><strong>Gaps:</strong> ${summary.total_gaps || 0}</p>
                <p><strong>Updates proposées:</strong> ${summary.proposed_updates || 0}</p>
            `;
        }
        // Usage report
        else if (reportName === 'usage_report.json') {
            html += `
                <p><strong>Users actifs:</strong> ${summary.active_users_count || 0}</p>
                <p><strong>Requêtes totales:</strong> ${summary.total_requests || 0}</p>
                <p><strong>Erreurs:</strong> ${summary.total_errors || 0}</p>
            `;
        }
        // Generic summary
        else {
            for (const [key, value] of Object.entries(summary)) {
                if (typeof value === 'number' || typeof value === 'string') {
                    html += `<p><strong>${key}:</strong> ${value}</p>`;
                }
            }
        }

        html += '</div>';
        return html;
    }

    /**
     * Retourne la classe CSS selon le status
     */
    getStatusClass(status) {
        const statusUpper = (status || '').toUpperCase();
        if (statusUpper === 'OK') return 'success';
        if (statusUpper === 'CRITICAL' || statusUpper === 'ERROR') return 'danger';
        if (statusUpper === 'WARNING' || statusUpper === 'NEEDS_UPDATE') return 'warning';
        return 'secondary';
    }

    /**
     * Retourne l'icône selon le status
     */
    getStatusIcon(status) {
        const statusUpper = (status || '').toUpperCase();
        if (statusUpper === 'OK') return '✅';
        if (statusUpper === 'CRITICAL' || statusUpper === 'ERROR') return '🚨';
        if (statusUpper === 'WARNING' || statusUpper === 'NEEDS_UPDATE') return '⚠️';
        return '❓';
    }

    /**
     * Retourne l'icône du rapport
     */
    getReportIcon(reportName) {
        if (reportName.includes('prod')) return '☁️';
        if (reportName.includes('docs')) return '📚';
        if (reportName.includes('integrity')) return '🔐';
        if (reportName.includes('usage')) return '👥';
        if (reportName.includes('unified')) return '🎯';
        return '📄';
    }

    /**
     * Retourne le label du rapport
     */
    getReportLabel(reportName) {
        if (reportName === 'prod_report.json') return 'Production Cloud Run';
        if (reportName === 'docs_report.json') return 'Documentation (Anima)';
        if (reportName === 'integrity_report.json') return 'Intégrité Système (Neo)';
        if (reportName === 'usage_report.json') return 'Usage Utilisateurs';
        if (reportName === 'unified_report.json') return 'Rapport Unifié (Nexus)';
        return reportName;
    }

    /**
     * Cleanup
     */
    destroy() {
        if (this.container) {
            this.container.innerHTML = '';
        }
        this.container = null;
        this.isAuditRunning = false;
    }
}

// Export singleton
export const adminGuardianModule = new AdminGuardianModule();
