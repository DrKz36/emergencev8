// src/frontend/features/admin/audit-history.js
// Audit History Widget for Admin Dashboard
// Displays the last N audit reports with status, integrity score, and details

class AuditHistoryWidget {
    constructor(apiClient) {
        this.apiClient = apiClient;
        this.container = null;
        this.audits = [];
        this.refreshInterval = null;
    }

    /**
     * Initialize the widget and render it to the container
     */
    async init(containerId) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            console.error(`[AuditHistory] Container #${containerId} not found`);
            return;
        }

        await this.fetchAudits();
        this.render();

        // Auto-refresh every 5 minutes
        this.refreshInterval = setInterval(() => {
            this.fetchAudits();
        }, 5 * 60 * 1000);
    }

    /**
     * Fetch audit history from backend
     */
    async fetchAudits() {
        try {
            const response = await this.apiClient.get('/api/admin/dashboard/audits?limit=10');
            this.audits = response.audits || [];
            this.stats = response.stats || {};
            this.latest = response.latest || null;

            console.log(`[AuditHistory] Fetched ${this.audits.length} audit reports`);

            if (this.container) {
                this.render();
            }
        } catch (error) {
            console.error('[AuditHistory] Error fetching audits:', error);
        }
    }

    /**
     * Render the widget HTML
     */
    render() {
        if (!this.container) return;

        const html = `
            <div class="audit-history-widget">
                <div class="audit-header">
                    <h2>📊 Historique des Audits Guardian</h2>
                    <button class="refresh-btn" onclick="window.auditHistoryWidget.fetchAudits()">🔄 Actualiser</button>
                </div>

                ${this.renderStats()}
                ${this.renderLatest()}
                ${this.renderAuditList()}
            </div>
        `;

        this.container.innerHTML = html;
    }

    /**
     * Render stats summary
     */
    renderStats() {
        if (!this.stats) return '';

        const total = this.audits.length;
        const okPercent = total > 0 ? Math.round((this.stats.ok / total) * 100) : 0;

        return `
            <div class="audit-stats">
                <div class="stat-card stat-ok">
                    <div class="stat-value">${this.stats.ok || 0}</div>
                    <div class="stat-label">✅ OK</div>
                </div>
                <div class="stat-card stat-warning">
                    <div class="stat-value">${this.stats.warning || 0}</div>
                    <div class="stat-label">⚠️ Warnings</div>
                </div>
                <div class="stat-card stat-critical">
                    <div class="stat-value">${this.stats.critical || 0}</div>
                    <div class="stat-label">🚨 Critical</div>
                </div>
                <div class="stat-card stat-score">
                    <div class="stat-value">${this.stats.average_score || '0%'}</div>
                    <div class="stat-label">📈 Score moyen</div>
                </div>
            </div>
        `;
    }

    /**
     * Render latest audit highlight
     */
    renderLatest() {
        if (!this.latest) {
            return `
                <div class="latest-audit">
                    <p class="no-data">Aucun audit disponible</p>
                </div>
            `;
        }

        const timestamp = new Date(this.latest.timestamp).toLocaleString('fr-FR');
        const statusClass = this.latest.status.toLowerCase();
        const statusEmoji = this.getStatusEmoji(this.latest.status);

        return `
            <div class="latest-audit status-${statusClass}">
                <div class="latest-header">
                    <h3>${statusEmoji} Dernier Audit</h3>
                    <span class="latest-time">${timestamp}</span>
                </div>
                <div class="latest-details">
                    <div class="latest-metric">
                        <span class="metric-label">Révision:</span>
                        <span class="metric-value">${this.latest.revision}</span>
                    </div>
                    <div class="latest-metric">
                        <span class="metric-label">Statut:</span>
                        <span class="metric-value status-badge status-${statusClass}">${this.latest.status}</span>
                    </div>
                    <div class="latest-metric">
                        <span class="metric-label">Intégrité:</span>
                        <span class="metric-value">${this.latest.integrity_score}</span>
                    </div>
                    <div class="latest-metric">
                        <span class="metric-label">Checks:</span>
                        <span class="metric-value">${this.latest.checks.passed}/${this.latest.checks.total} passés</span>
                    </div>
                </div>

                ${this.latest.issues && this.latest.issues.length > 0 ? `
                    <div class="latest-issues">
                        <strong>⚠️ Problèmes détectés:</strong>
                        <ul>
                            ${this.latest.issues.map(issue => `<li>${issue}</li>`).join('')}
                        </ul>
                    </div>
                ` : ''}
            </div>
        `;
    }

    /**
     * Render audit list
     */
    renderAuditList() {
        if (this.audits.length === 0) {
            return '<div class="no-audits"><p>Aucun historique disponible</p></div>';
        }

        return `
            <div class="audit-list">
                <h3>📋 Historique (${this.audits.length} derniers audits)</h3>
                <div class="audit-table">
                    <table>
                        <thead>
                            <tr>
                                <th>Date/Heure</th>
                                <th>Révision</th>
                                <th>Statut</th>
                                <th>Score</th>
                                <th>Checks</th>
                                <th>Détails</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${this.audits.map(audit => this.renderAuditRow(audit)).join('')}
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    }

    /**
     * Render individual audit row
     */
    renderAuditRow(audit) {
        const timestamp = new Date(audit.timestamp).toLocaleString('fr-FR');
        const statusClass = audit.status.toLowerCase();
        const statusEmoji = this.getStatusEmoji(audit.status);

        return `
            <tr class="audit-row status-${statusClass}">
                <td class="audit-time">${timestamp}</td>
                <td class="audit-revision">${audit.revision}</td>
                <td class="audit-status">
                    <span class="status-badge status-${statusClass}">${statusEmoji} ${audit.status}</span>
                </td>
                <td class="audit-score">${audit.integrity_score}</td>
                <td class="audit-checks">${audit.checks.passed}/${audit.checks.total}</td>
                <td class="audit-details">
                    <button class="details-btn" onclick="window.auditHistoryWidget.showDetails('${audit.timestamp}')">
                        👁️ Voir
                    </button>
                </td>
            </tr>
        `;
    }

    /**
     * Show audit details modal
     */
    showDetails(timestamp) {
        const audit = this.audits.find(a => a.timestamp === timestamp);
        if (!audit) return;

        const modal = document.createElement('div');
        modal.className = 'audit-modal';
        modal.innerHTML = `
            <div class="audit-modal-content">
                <div class="modal-header">
                    <h2>📊 Détails de l'Audit</h2>
                    <button class="modal-close" onclick="this.closest('.audit-modal').remove()">✕</button>
                </div>
                <div class="modal-body">
                    <div class="detail-section">
                        <h3>Informations générales</h3>
                        <div class="detail-grid">
                            <div><strong>Date:</strong> ${new Date(audit.timestamp).toLocaleString('fr-FR')}</div>
                            <div><strong>Révision:</strong> ${audit.revision}</div>
                            <div><strong>Statut:</strong> ${audit.status}</div>
                            <div><strong>Score:</strong> ${audit.integrity_score}</div>
                        </div>
                    </div>

                    <div class="detail-section">
                        <h3>Résumé des vérifications</h3>
                        <div class="summary-grid">
                            ${Object.entries(audit.summary || {}).map(([key, value]) => `
                                <div class="summary-item">
                                    <span class="summary-key">${key.replace(/_/g, ' ')}:</span>
                                    <span class="summary-value status-badge status-${value.toLowerCase()}">${value}</span>
                                </div>
                            `).join('')}
                        </div>
                    </div>

                    ${audit.issues && audit.issues.length > 0 ? `
                        <div class="detail-section">
                            <h3>⚠️ Problèmes détectés (${audit.issues.length})</h3>
                            <ul class="issues-list">
                                ${audit.issues.map(issue => `<li>${issue}</li>`).join('')}
                            </ul>
                        </div>
                    ` : ''}
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // Close on backdrop click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.remove();
            }
        });
    }

    /**
     * Get emoji for status
     */
    getStatusEmoji(status) {
        const statusLower = status.toLowerCase();
        if (statusLower === 'ok') return '✅';
        if (statusLower === 'warning') return '⚠️';
        if (statusLower === 'critical') return '🚨';
        return '📊';
    }

    /**
     * Cleanup
     */
    destroy() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
    }
}

// Export for use in admin dashboard
export { AuditHistoryWidget };
