/**
 * @module features/documents/document-ui
 * @description UI du module Documents — V5.2 (verre/halo/métal + stats canvas, data-first, 2e tick)
 * - Upload : drop-zone + preview multi-fichiers
 * - Liste : toolbar (sélection, suppression, rafraîchir)
 * - Stats : canvas responsive (répartition par extension) + total
 */
export class DocumentsUI {
    constructor(eventBus) {
        this.eventBus = eventBus;
        this._resizeObserver = null;
        this._mo = null;
        this._cleanupFns = [];
        this._lastItems = null; // données brutes pour stats (source > DOM)
    }

    render(container) {
        // ----- UI de base -----
        container.innerHTML = `
            <div class="documents-view-wrapper">
                <div class="card">
                    <div class="card-header">
                        <h2 class="card-title">Gérer les documents</h2>
                        <p class="card-subtitle">Ajoute des fichiers pour les rendre accessibles via RAG.</p>
                    </div>

                    <div class="card-body">
                        <section class="upload-section" aria-label="Upload de documents">
                            <input type="file" id="file-input" multiple accept=".pdf,txt,docx,md" />

                            <div id="drop-zone" class="drop-zone" tabindex="0" role="button" aria-label="Choisir un fichier ou déposer ici">
                                <div class="drop-zone-prompt">
                                    <svg class="upload-icon" viewBox="0 0 24 24" aria-hidden="true">
                                        <path d="M12 16V4m0 0l-4 4m4-4l4 4M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2"
                                              fill="none" stroke="currentColor" stroke-width="2"
                                              stroke-linecap="round" stroke-linejoin="round"/>
                                    </svg>
                                    <p><strong>Glisse-dépose</strong> un ou plusieurs fichiers ici, ou clique pour choisir.</p>
                                </div>

                                <div class="drop-zone-preview" id="drop-zone-preview" aria-live="polite">
                                    <div class="preview-icon">📄</div>
                                    <div class="preview-name" id="preview-name"></div>
                                    <button type="button" id="btn-clear-selection" class="btn-clear-selection" title="Effacer la sélection" aria-label="Effacer la sélection">×</button>
                                </div>
                            </div>

                            <div class="upload-actions">
                                <button id="upload-button" class="button primary">Uploader</button>
                                <div id="upload-status" class="upload-status info" aria-live="polite"></div>
                            </div>
                        </section>

                        <section class="list-section" aria-label="Documents indexés">
                            <div class="list-toolbar">
                                <label class="select-all">
                                    <input type="checkbox" id="select-all" />
                                    <span>Tout sélectionner</span>
                                </label>
                                <div class="toolbar-actions">
                                    <button id="btn-refresh-list" class="button" title="Rafraîchir la liste">Rafraîchir</button>
                                    <button id="btn-delete-selected" class="button" disabled>Supprimer la sélection</button>
                                    <button id="btn-delete-all" class="button">Tout effacer</button>
                                </div>
                            </div>

                            <h3 class="list-title">Documents indexés</h3>
                            <ul id="document-list-container" class="document-list"></ul>
                            <p class="empty-list-message" style="display:none;">Aucun document indexé.</p>
                        </section>

                        <!-- === Statistiques === -->
                        <section class="stats-section" aria-label="Statistiques des documents" style="margin-top: 24px;">
                            <h3 class="list-title">Statistiques</h3>
                            <div id="doc-stats-summary" class="doc-stats-summary" aria-live="polite" style="margin: 6px 0 10px;">
                                Total : 0 · (aucune extension)
                            </div>
                            <div class="doc-stats-canvas-wrap" style="width:100%;max-width:100%;overflow:hidden;border-radius:12px;border:1px solid rgba(255,255,255,.08);background:linear-gradient(180deg, rgba(255,255,255,.02), rgba(255,255,255,.01));box-shadow:0 10px 30px rgba(0,0,0,.25) inset;">
                                <canvas id="doc-stats-canvas" width="640" height="220" role="img" aria-label="Répartition des documents par extension"></canvas>
                            </div>
                            <p id="doc-stats-empty" style="display:none;margin-top:8px;opacity:.8;">Aucune donnée à afficher.</p>
                        </section>
                    </div>
                </div>
            </div>`;

        // ----- Wiring Stats (chart) : data-first (puis fallback DOM) -----
        const listEl = container.querySelector('#document-list-container');
        const canvas = container.querySelector('#doc-stats-canvas');
        const ctx = canvas.getContext('2d');
        const summaryEl = container.querySelector('#doc-stats-summary');
        const emptyStatsEl = container.querySelector('#doc-stats-empty');
        const wrap = container.querySelector('.doc-stats-canvas-wrap');

        const pickColor = (i) => {
            const palette = [
                '#60a5fa', '#34d399', '#fbbf24', '#f472b6', '#a78bfa', '#38bdf8',
                '#f87171', '#22c55e', '#eab308', '#f97316', '#10b981', '#c084fc'
            ];
            return palette[i % palette.length];
        };

        const extFromName = (name) => {
            if (!name) return 'sans_ext';
            const idx = name.lastIndexOf('.');
            return (idx > 0 ? name.slice(idx + 1) : 'sans_ext').toLowerCase();
        };

        const computeStatsFromData = (items) => {
            const exts = new Map(); let total = 0;
            for (const d of (items || [])) {
                const nm = d?.filename || d?.original_filename || d?.name || d?.title || d?.path || d?.stored_name || '';
                if (!nm) continue;
                total += 1;
                const ext = extFromName(nm);
                exts.set(ext, (exts.get(ext) || 0) + 1);
            }
            return { total, exts };
        };

        const getItemNameFromLI = (li) => {
            const attr = li.getAttribute('data-name') || li.getAttribute('data-filename');
            if (attr && attr.trim()) return attr.trim();
            const nameNode = li.querySelector?.('.doc-name, [data-role="doc-name"]');
            const txt = (nameNode?.textContent ?? li.textContent ?? '').trim();
            return txt;
        };

        const computeStatsFromDOM = () => {
            const items = Array.from(listEl?.children || []);
            const exts = new Map(); let total = 0;
            for (const li of items) {
                const name = getItemNameFromLI(li);
                if (!name) continue;
                total += 1;
                const ext = extFromName(name);
                exts.set(ext, (exts.get(ext) || 0) + 1);
            }
            return { total, exts };
        };

        const drawChart = ({ total, exts }) => {
            try {
                const w = wrap.clientWidth || canvas.width;
                const h = canvas.height;
                canvas.width = Math.max(480, w);
                canvas.height = h;

                const pairs = Array.from(exts.entries()).sort((a,b) => b[1]-a[1]);
                const pad = 18, gap = 8, barW = Math.max(16, (canvas.width - pad*2 - gap*(pairs.length-1)) / Math.max(1, pairs.length));
                const maxVal = Math.max(1, ...pairs.map(([,v]) => v));
                const axisX = pad, axisY = h - 32;
                const scale = (axisY - 24) / maxVal;

                ctx.clearRect(0, 0, canvas.width, canvas.height);
                emptyStatsEl.style.display = (total === 0) ? '' : 'none';

                // Axes
                ctx.save();
                ctx.strokeStyle = 'rgba(255,255,255,.15)';
                ctx.lineWidth = 1;
                ctx.beginPath();
                ctx.moveTo(axisX, axisY + 0.5);
                ctx.lineTo(canvas.width - pad, axisY + 0.5);
                ctx.stroke();
                ctx.restore();

                // Barres
                let x = axisX;
                pairs.forEach(([ext, value], i) => {
                    const hBar = Math.max(2, value * scale);
                    const y = axisY - hBar;

                    ctx.fillStyle = pickColor(i);
                    ctx.globalAlpha = 0.85;
                    ctx.fillRect(x, y, barW, hBar);

                    ctx.globalAlpha = 1;
                    ctx.fillStyle = '#e5e7eb';
                    ctx.font = '12px system-ui, -apple-system, Segoe UI, Roboto, Ubuntu';
                    ctx.textAlign = 'center';
                    ctx.fillText(String(value), x + barW / 2, y - 6);

                    ctx.globalAlpha = 0.9;
                    ctx.fillStyle = '#cbd5e1';
                    const labelY = axisY + 14;
                    if (barW < 28) {
                        ctx.save();
                        ctx.translate(x + barW / 2, labelY + 8);
                        ctx.rotate(-Math.PI / 4);
                        ctx.fillText(ext, 0, 0);
                        ctx.restore();
                    } else {
                        ctx.fillText(ext, x + barW / 2, labelY);
                    }
                    x += barW + gap;
                });
            } catch (e) {
                console.error('[DocumentsUI] drawChart failed:', e);
            }
        };

        const updateSummary = ({ total, exts }) => {
            if (!summaryEl) return;
            if (!total || exts.size === 0) {
                summaryEl.textContent = 'Total : 0 · (aucune extension)';
                return;
            }
            const top = Array.from(exts.entries()).sort((a,b) => b[1]-a[1]).slice(0, 3);
            const topStr = top.map(([k,v]) => `${k}: ${v}`).join(' · ');
            summaryEl.textContent = `Total : ${total} · ${topStr}${exts.size > 3 ? ' · …' : ''}`;
        };

        const refreshStats = () => {
            try {
                const stats = Array.isArray(this._lastItems)
                    ? computeStatsFromData(this._lastItems)
                    : computeStatsFromDOM();
                updateSummary(stats);
                drawChart(stats);
            } catch (e) {
                console.error('[DocumentsUI] refreshStats failed:', e);
            }
        };

        // MutationObserver (fallback DOM)
        if (listEl) {
            this._mo?.disconnect?.();
            this._mo = new MutationObserver(() => refreshStats());
            this._mo.observe(listEl, { childList: true, subtree: true, characterData: true });
            this._cleanupFns.push(() => this._mo?.disconnect?.());
        }

        // Resize responsive
        this._resizeObserver?.disconnect?.();
        if (window && 'ResizeObserver' in window) {
            this._resizeObserver = new ResizeObserver(() => refreshStats());
            this._resizeObserver.observe(wrap);
            this._cleanupFns.push(() => this._resizeObserver?.disconnect?.());
        } else {
            const onResize = () => refreshStats();
            window.addEventListener('resize', onResize);
            this._cleanupFns.push(() => window.removeEventListener('resize', onResize));
        }

        // Premier rendu + 2e tick après layout
        refreshStats();
        setTimeout(() => refreshStats(), 0);

        // Rafraîchissement sur évènement module (données brutes)
        try {
            const off = this.eventBus?.on?.('documents:list:refreshed', (payload = {}) => {
                if (Array.isArray(payload.items)) this._lastItems = payload.items;
                refreshStats();
            });
            if (typeof off === 'function') this._cleanupFns.push(off);
        } catch {}
    }

    destroy() {
        try { this._cleanupFns.forEach(fn => { try { fn(); } catch {} }); } catch {}
        this._cleanupFns = [];
        try { this._mo?.disconnect?.(); } catch {}
        try { this._resizeObserver?.disconnect?.(); } catch {}
    }
}
