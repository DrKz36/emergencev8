/**
 * @module features/dashboard/benchmarks
 * @description Renderer for the benchmarks matrix displayed in the dashboard.
 */
const ESCAPE_LOOKUP = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "\"": "&quot;",
    "'": "&#39;",
};

function escapeHtml(value) {
    if (value === null || value === undefined) return '';
    return String(value).replace(/[&<>"']/g, (char) => ESCAPE_LOOKUP[char] || char);
}

export class BenchmarksMatrix {
    constructor() {
        this.container = null;
    }

    mount(container) {
        if (!container) return;
        this.container = container;
        this.showLoading();
    }

    showLoading(message = 'Chargement des benchmarks…') {
        const target = this.container;
        if (!target) return;
        target.innerHTML = `<div class="benchmarks-loading">${message}</div>`;
    }

    showError(message) {
        const target = this.container;
        if (!target) return;
        target.innerHTML = `<div class="benchmarks-error">${message}</div>`;
    }

    render(container, { matrices = [], scenarios = [] } = {}) {
        if (container) {
            this.container = container;
        }
        if (!this.container) return;
        if (!Array.isArray(matrices) || matrices.length === 0) {
            this.container.innerHTML = `
                <div class="benchmarks-empty">
                    <p>Aucun run de benchmark n'a été enregistré pour l'instant.</p>
                    <p class="benchmarks-empty__hint">Déclenchez un run depuis l'interface admin pour remplir la matrice.</p>
                </div>
            `;
            return;
        }

        const scenarioLookup = new Map((scenarios || []).map((item) => [item.id, item]));
        const sections = matrices.map((matrix) => this._renderMatrixSection(matrix, scenarioLookup.get(matrix.scenario_id)));
        this.container.innerHTML = `<div class="benchmarks-matrix">${sections.join('')}</div>`;
    }

    _renderMatrixSection(matrix, scenarioMeta) {
        const summary = matrix.summary || {};
        const runs = Array.isArray(matrix.runs) ? matrix.runs : [];
        const successRate = this._formatPercent(summary.success_rate ?? (summary.runs_count ? summary.success_count / summary.runs_count : 0));
        const title = escapeHtml(scenarioMeta?.name || matrix.scenario_id);
        const description = escapeHtml(scenarioMeta?.description || '');
        const descriptionMarkup = description
            ? `<p class="benchmarks-matrix__description">${description}</p>`
            : '';
        const header = `
            <div class="benchmarks-matrix__header">
                <div>
                    <h4 class="benchmarks-matrix__title">${title}</h4>
                    ${descriptionMarkup}
                </div>
                <div class="benchmarks-matrix__summary">
                    <span class="benchmarks-chip ${summary.success_rate >= 0.7 ? 'ok' : 'warn'}">${successRate} de réussite</span>
                    <span class="benchmarks-matrix__totals">${summary.success_count || 0}/${summary.runs_count || runs.length} configurations</span>
                </div>
            </div>
        `;

        const tableRows = runs.map((run) => this._renderRunRow(run)).join('');
        const table = `
            <table class="benchmarks-table" aria-label="Matrice des benchmarks">
                <thead>
                    <tr>
                        <th scope="col">Configuration</th>
                        <th scope="col">Statut</th>
                        <th scope="col">Coût</th>
                        <th scope="col">Latence</th>
                        <th scope="col">Score</th>
                    </tr>
                </thead>
                <tbody>
                    ${tableRows}
                </tbody>
            </table>
        `;

        return `<section class="benchmarks-matrix__section">${header}${table}</section>`;
    }

    _renderRunRow(run) {
        const config = run.config || {};
        const label = [config.agent_topology, config.orchestration_mode, config.memory_mode]
            .filter(Boolean)
            .map((part) => escapeHtml(part))
            .join(' / ');
        const statusClass = run.success ? 'ok' : 'ko';
        const statusLabel = run.success ? 'Succès' : 'Échec';
        const cost = this._formatCurrency(run.cost);
        const latency = this._formatLatency(run.latency_ms);
        const details = run.executor_details || {};
        const score = details.score != null ? `${this._formatPercent(details.score)}` : '—';

        return `
            <tr>
                <td data-label="Configuration">
                    <div class="benchmarks-config">${label || escapeHtml(run.slug)}</div>
                    ${config.metadata && Object.keys(config.metadata).length ? `<div class="benchmarks-config__meta">${this._formatMetadata(config.metadata)}</div>` : ''}
                </td>
                <td data-label="Statut"><span class="benchmarks-status ${statusClass}">${statusLabel}</span></td>
                <td data-label="Coût">${cost}</td>
                <td data-label="Latence">${latency}</td>
                <td data-label="Score">${score}</td>
            </tr>
        `;
    }

    _formatCurrency(value) {
        const numeric = Number(value);
        if (!Number.isFinite(numeric)) return '—';
        return `${numeric.toFixed(4)} $`;
    }

    _formatLatency(value) {
        const numeric = Number(value);
        if (!Number.isFinite(numeric)) return '—';
        if (numeric >= 1000) {
            return `${(numeric / 1000).toFixed(2)} s`;
        }
        return `${Math.round(numeric)} ms`;
    }

    _formatPercent(value) {
        const numeric = Number(value);
        if (!Number.isFinite(numeric)) return '0%';
        return `${Math.round(numeric * 100)}%`;
    }

    _formatMetadata(metadata) {
        return Object.entries(metadata)
            .map(([key, val]) => `<span class="benchmarks-meta"><span class="benchmarks-meta__key">${escapeHtml(key)}</span>: ${escapeHtml(val)}</span>`)
            .join(' ');
    }
}
