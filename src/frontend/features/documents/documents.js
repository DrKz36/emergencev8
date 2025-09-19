/**
 * @module features/documents/documents
 * @description Logique du module Documents  V7.3 (normalize {items}, id/name helpers, events { total, items } + retick)
 */
import { api } from '../../shared/api-client.js';
import { EVENTS } from '../../shared/constants.js';
import { formatDate } from '../../shared/utils.js';
import { DocumentsUI } from './document-ui.js';

export default class DocumentsModule {
    constructor(eventBus, stateManager) {
        this.eventBus = eventBus;
        this.state = stateManager;
        this.apiClient = api;
        this.ui = new DocumentsUI(eventBus);
        this.container = null;
        this.dom = {};
        this.documents = [];
        this.selectedFiles = [];
        this.selectedIds = new Set();
        this.isInitialized = false;
        this._autoRefreshTimer = null;
        this._autoRefreshIntervalMs = 45000;
        this._lastSelectionHash = '';
        this._offDeselectCmd = null;
    }

    init() {
        if (this.isInitialized) return;
        if (this.eventBus?.on && !this._offDeselectCmd) {
            const off = this.eventBus.on(
                EVENTS?.DOCUMENTS_CMD_DESELECT || 'documents:cmd:deselect',
                (payload) => this._handleExternalDeselect(payload)
            );
            if (typeof off === 'function') this._offDeselectCmd = off;
        }
        if (this.state?.get) {
            const saved = this.state.get('documents.selectedIds');
            if (Array.isArray(saved) && saved.length) {
                this.selectedIds = new Set(saved.map((id) => String(id)));
            }
        }
        this.isInitialized = true;
    }

    mount(container) {
        this.container = container;
        this.ui.render(container);
        this.cacheDOM();
        this.registerDOMListeners();
        this.fetchAndRenderDocuments();
    }

    destroy() {
        if (this._autoRefreshTimer) {
            clearTimeout(this._autoRefreshTimer);
            this._autoRefreshTimer = null;
        }
        if (this._offDeselectCmd) {
            try { this._offDeselectCmd(); } catch {}
            this._offDeselectCmd = null;
        }
        this.container = null;
        this.dom = {};
        this.selectedFiles = [];
        this.selectedIds.clear();
    }

    cacheDOM() {
        this.dom = {
            fileInput: this.container.querySelector('#file-input'),
            dropZone: this.container.querySelector('#drop-zone'),
            dropZonePrompt: this.container.querySelector('.drop-zone-prompt'),
            dropZonePreview: this.container.querySelector('#drop-zone-preview'),
            previewName: this.container.querySelector('#preview-name'),
            clearSelectionBtn: this.container.querySelector('#btn-clear-selection'),
            uploadButton: this.container.querySelector('#upload-button'),
            uploadStatus: this.container.querySelector('#upload-status'),
            listContainer: this.container.querySelector('#document-list-container'),
            emptyListMessage: this.container.querySelector('.empty-list-message'),
            selectAll: this.container.querySelector('#select-all'),
            deleteSelectedBtn: this.container.querySelector('#btn-delete-selected'),
            deleteAllBtn: this.container.querySelector('#btn-delete-all'),
            refreshBtn: this.container.querySelector('#btn-refresh-list'),
        };
    }

    registerDOMListeners() {
        // Slection fichier(s)
        this.dom.fileInput.addEventListener('change', (e) => {
            const files = Array.from(e.target.files || []);
            this.setSelectedFiles(files);
        });

        // Drop-zone : DnD
        const prevent = (ev) => { ev.preventDefault(); ev.stopPropagation(); };
        ['dragenter', 'dragover'].forEach(evt =>
            this.dom.dropZone.addEventListener(evt, (e) => {
                prevent(e);
                this.dom.dropZone.classList.add('highlight');
            })
        );
        ['dragleave', 'drop'].forEach(evt =>
            this.dom.dropZone.addEventListener(evt, (e) => {
                prevent(e);
                this.dom.dropZone.classList.remove('highlight');
            })
        );
        this.dom.dropZone.addEventListener('drop', (e) => {
            const files = Array.from((e.dataTransfer && e.dataTransfer.files) || []);
            this.setSelectedFiles(files);
        });

        // Drop-zone : click + clavier  ouvre le picker (accessibilit)
        this.dom.dropZone.addEventListener('click', () => { try { this.dom.fileInput?.click(); } catch {} });
        this.dom.dropZone.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); try { this.dom.fileInput?.click(); } catch {} }
        });

        // Clear selection
        this.dom.clearSelectionBtn.addEventListener('click', () => this.setSelectedFiles([]));

        // Upload
        this.dom.uploadButton.addEventListener('click', () => this.uploadSelectedFiles());

        // Toolbar list
        this.dom.selectAll.addEventListener('change', (e) => this.toggleSelectAll(e.target.checked));
        this.dom.deleteSelectedBtn.addEventListener('click', () => this.deleteSelected());
        this.dom.deleteAllBtn.addEventListener('click', () => this.deleteAll());
        this.dom.refreshBtn.addEventListener('click', () => this.fetchAndRenderDocuments(true));

        // Dlgation suppression par ligne
        this.dom.listContainer.addEventListener('click', (e) => this.handleDelete(e));
        this.dom.listContainer.addEventListener('change', (e) => this.handleCheckboxChange(e));
    }

    _emitSelectionChanged() {
        const ids = Array.from(this.selectedIds);
        const items = ids
            .map((id) => this.documents.find((doc) => this._getId(doc) === id))
            .filter(Boolean)
            .map((doc) => ({
                id: this._getId(doc),
                name: this._getName(doc),
                status: (doc?.status || '').toString().toLowerCase() || 'ready'
            }));
        try { this.state?.set?.('documents.selectedIds', ids); } catch {}
        try { this.state?.set?.('documents.selectionMeta', items); } catch {}
        try { this.eventBus.emit(EVENTS?.DOCUMENTS_SELECTION_CHANGED || 'documents:selection_changed', { ids, items }); } catch {}
        this._lastSelectionHash = ids.join('|');
    }

    _handleExternalDeselect(payload) {
        const raw = payload && (payload.id ?? payload.doc_id ?? payload);
        if (!raw && raw !== 0) return;
        const id = String(raw);
        if (!this.selectedIds.has(id)) {
            return;
        }
        this.selectedIds.delete(id);
        if (this.container) {
            const esc = (typeof CSS !== 'undefined' && typeof CSS.escape === 'function')
                ? CSS.escape(id)
                : id.replace(/"/g, '\\"');
            const checkbox = this.container.querySelector(`.doc-select[data-id="${esc}"]`);
            if (checkbox) checkbox.checked = false;
        }
        this.updateSelectionUI();
        this._emitSelectionChanged();
    }

    /* ------------------------------- Helpers -------------------------------- */

    _getId(doc) {
        return String(
            doc?.id ??
            doc?.document_id ??
            doc?._id ??
            doc?.uuid ??
            doc?.documentId ??
            ''
        );
    }

    _getName(doc) {
        return (
            doc?.filename ||
            doc?.original_filename ||
            doc?.name ||
            doc?.title ||
            doc?.path ||
            doc?.stored_name ||
            this._getId(doc) ||
            ''
        );
    }

    _normalizeDocumentsResponse(resp) {
        // Accepte tableau direct ou enveloppes communes {items}, {documents}, {data}, {results}
        if (Array.isArray(resp)) return resp;
        if (!resp || typeof resp !== 'object') return [];
        if (Array.isArray(resp.items)) return resp.items;
        if (Array.isArray(resp.documents)) return resp.documents;
        if (Array.isArray(resp.data)) return resp.data;
        if (Array.isArray(resp.results)) return resp.results;
        // Dernier recours: essayer de dtecter un unique item
        const maybe = Object.values(resp).find(v => Array.isArray(v));
        return Array.isArray(maybe) ? maybe : [];
    }

    /* ------------------------------- Slection ------------------------------- */

    setSelectedFiles(files) {
        this.selectedFiles = Array.isArray(files) ? files.filter(Boolean) : [];
        if (this.selectedFiles.length) {
            const names = this.selectedFiles.map(f => f.name).join(', ');
            this.dom.previewName.textContent = names;
            this.dom.dropZonePrompt.style.display = 'none';
            this.dom.dropZonePreview.style.display = 'flex';
            this.dom.uploadButton.disabled = false;
            this.dom.uploadStatus.textContent = '';
        } else {
            this.dom.previewName.textContent = '';
            this.dom.dropZonePrompt.style.display = 'flex';
            this.dom.dropZonePreview.style.display = 'none';
            this.dom.uploadButton.disabled = true;
        }
    }

    /* --------------------------------- Upload -------------------------------- */

    async uploadSelectedFiles() {
        if (!this.selectedFiles.length) return;

        this.dom.uploadButton.disabled = true;
        this.dom.uploadStatus.classList.remove('error', 'success', 'info');
        this.dom.uploadStatus.classList.add('info');
        this.dom.uploadStatus.textContent = `Téléversement de ${this.selectedFiles.length} fichier(s).`;

        const results = [];
        for (const file of this.selectedFiles) {
            try {
                await this.apiClient.uploadDocument(file);
                results.push({ ok: true, name: file.name });
                this.eventBus.emit(EVENTS.SHOW_NOTIFICATION, { type: 'success', message: `Téléversement : ${file.name}` });
            } catch (error) {
                results.push({ ok: false, name: file.name, error });
                this.eventBus.emit(EVENTS.SHOW_NOTIFICATION, { type: 'error', message: `chec upload : ${file.name}` });
            }
        }

        // Reset sélection
        this.setSelectedFiles([]);
        this.dom.fileInput.value = '';

        // Refresh & statut
        await this.fetchAndRenderDocuments(true);

        const okCount = results.filter(r => r.ok).length;
        const koCount = results.length - okCount;
        this.dom.uploadStatus.textContent = '';
        if (koCount === 0) {
            this.eventBus.emit(EVENTS.SHOW_NOTIFICATION, { type: 'success', message: `Téléversement terminé (${okCount}/${results.length}).` });
        } else {
            this.eventBus.emit(EVENTS.SHOW_NOTIFICATION, { type: 'warning', message: `Téléversement partiel (${okCount}/${results.length}).` });
        }
        this.dom.uploadButton.disabled = false;
    }

    /* -------------------------------- Listing -------------------------------- */

    async fetchAndRenderDocuments(force = false) {
        if (!force && this._autoRefreshTimer) return;

        this.dom.listContainer.innerHTML = '<div class="loader"></div>';
        if (!this.selectedIds.size && this.state?.get) {
            const savedIds = this.state.get('documents.selectedIds');
            if (Array.isArray(savedIds) && savedIds.length) {
                this.selectedIds = new Set(savedIds.map((id) => String(id)));
            }
        }
        const previousSelection = new Set(this.selectedIds);

        try {
            const resp = await this.apiClient.getDocuments();
            this.documents = this._normalizeDocumentsResponse(resp);

            if (!Array.isArray(this.documents) || this.documents.length === 0) {
                this.dom.listContainer.innerHTML = '';
                if (this.dom.emptyListMessage) this.dom.emptyListMessage.style.display = 'block';
                this.updateSelectionUI();
                if (this.selectedIds.size) {
                    this.selectedIds.clear();
                }
                this._emitSelectionChanged();

                const payload = { total: 0, items: [] };
                try { this.eventBus.emit('documents:list:refreshed', payload); } catch {}
                try { if (EVENTS?.DOCUMENTS_LIST_REFRESHED) this.eventBus.emit(EVENTS.DOCUMENTS_LIST_REFRESHED, payload); } catch {}
                setTimeout(() => { try { this.eventBus.emit('documents:list:retick', payload); } catch {} }, 0);

                this._scheduleAutoRefresh(false);
                return;
            }

            if (this.dom.emptyListMessage) this.dom.emptyListMessage.style.display = 'none';
            this.dom.listContainer.innerHTML = this.documents.map((doc) => this.renderDocItem(doc)).join('');
            const availableIds = new Set(this.documents.map((doc) => this._getId(doc)));
            this.selectedIds = new Set([...previousSelection].filter((id) => availableIds.has(id)));
            this.container?.querySelectorAll('.doc-select').forEach((input) => {
                const id = input.dataset.id;
                if (!id) return;
                input.checked = this.selectedIds.has(id);
            });
            this.updateSelectionUI();
            this._emitSelectionChanged();

            const payload = { total: this.documents.length, items: this.documents.slice() };
            try { this.eventBus.emit('documents:list:refreshed', payload); } catch {}
            try { if (EVENTS?.DOCUMENTS_LIST_REFRESHED) this.eventBus.emit(EVENTS.DOCUMENTS_LIST_REFRESHED, payload); } catch {}
            setTimeout(() => { try { this.eventBus.emit('documents:list:retick', payload); } catch {} }, 0);

            const hasProcessing = this.documents.some(d => String(d.status || '').toLowerCase() === 'processing');
            this._scheduleAutoRefresh(hasProcessing);
        } catch (e) {
            console.error('[Documents] chec de rcupration de la liste', e);
            this.dom.listContainer.innerHTML = '<p class="error">Erreur lors du chargement des documents.</p>';
            this.updateSelectionUI();
            if (this.selectedIds.size) {
                this.selectedIds.clear();
            }
            this._emitSelectionChanged();

            const payload = { total: 0, items: [] };
            try { this.eventBus.emit('documents:list:refreshed', payload); } catch {}
            try { if (EVENTS?.DOCUMENTS_LIST_REFRESHED) this.eventBus.emit(EVENTS.DOCUMENTS_LIST_REFRESHED, payload); } catch {}
            setTimeout(() => { try { this.eventBus.emit('documents:list:retick', payload); } catch {} }, 0);

            this._scheduleAutoRefresh(false);
        }
    }

    _scheduleAutoRefresh(enable) {
        if (this._autoRefreshTimer) { clearTimeout(this._autoRefreshTimer); this._autoRefreshTimer = null; }
        if (!enable) return;
        this._autoRefreshTimer = setTimeout(() => this.fetchAndRenderDocuments(true), 3000);
    }

    renderDocItem(doc) {
        const id = this._getId(doc);
        const name = this._getName(doc);
        const dateIso = doc?.uploaded_at || doc?.created_at || doc?.createdAt || doc?.timestamp || null;
        const when = dateIso ? formatDate(dateIso) : '';
        const status = (doc?.status || 'ready').toLowerCase(); // ready | processing | error
        const statusClass = status === 'processing' ? 'status-processing'
                          : status === 'error' ? 'status-error'
                          : 'status-ready';

        return `
            <li class="document-item" data-id="${id}" data-name="${name}">
                <input type="checkbox" class="doc-select" data-id="${id}" aria-label="Slectionner ${name}">
                <span class="doc-icon" aria-hidden="true"></span>
                <span class="doc-name" data-role="doc-name">${name}</span>
                <span class="doc-date">${when}</span>
                <span class="doc-status ${statusClass}">${status}</span>
                <button class="button button-metal btn-delete" data-id="${id}" title="Supprimer ${name}" aria-label="Supprimer ${name}"></button>
            </li>
        `;
    }

    /* ------------------------------- Actions UI ------------------------------ */

    async handleDelete(e) {
        const btn = e.target.closest('.btn-delete');
        if (!btn) return;
        const docId = btn.dataset.id;
        if (!docId) return;

        if (confirm('Supprimer ce document ?')) {
            try {
                await this.apiClient.deleteDocument(docId);
                this.selectedIds.delete(docId);
                this.eventBus.emit(EVENTS.SHOW_NOTIFICATION, { type: 'success', message: 'Document supprim.' });
                await this.fetchAndRenderDocuments(true);
            } catch {
                this.eventBus.emit(EVENTS.SHOW_NOTIFICATION, { type: 'error', message: 'Erreur lors de la suppression.' });
            }
        }
    }

    handleCheckboxChange(e) {
        const input = e.target?.closest?.('.doc-select');
        if (!input) return;
        const docId = input.dataset.id;
        if (!docId) return;
        if (input.checked) {
            this.selectedIds.add(docId);
        } else {
            this.selectedIds.delete(docId);
        }
        this.updateSelectionUI();
        this._emitSelectionChanged();
    }

    updateSelectionUI() {
        const total = this.documents.length;
        const selected = this.selectedIds.size;

        if (this.dom.selectAll) {
            this.dom.selectAll.indeterminate = selected > 0 && selected < total;
            this.dom.selectAll.checked = selected > 0 && selected === total;
        }
        if (this.dom.deleteSelectedBtn) {
            this.dom.deleteSelectedBtn.disabled = selected === 0;
        }
    }

    toggleSelectAll(checked) {
        this.selectedIds.clear();
        if (checked) {
            for (const d of this.documents) {
                this.selectedIds.add(this._getId(d));
            }
        }
        this.container.querySelectorAll('.doc-select').forEach((input) => { input.checked = checked; });
        this.updateSelectionUI();
        this._emitSelectionChanged();
    }

    async deleteSelected() {
        const count = this.selectedIds.size;
        if (count === 0) return;
        if (!confirm(`Supprimer ${count} document(s) ?`)) return;

        const ids = Array.from(this.selectedIds);
        try {
            await Promise.allSettled(ids.map(id => this.apiClient.deleteDocument(id)));
            this.eventBus.emit(EVENTS.SHOW_NOTIFICATION, { type: 'success', message: `${count} document(s) supprim(s).` });
        } catch {
            this.eventBus.emit(EVENTS.SHOW_NOTIFICATION, { type: 'error', message: 'Suppression partielle : vrifie les logs.' });
        } finally {
            await this.fetchAndRenderDocuments(true);
        }
    }

    async deleteAll() {
        if (!Array.isArray(this.documents) || this.documents.length === 0) return;
        if (!confirm(`Tout effacer ? (${this.documents.length} document(s))`)) return;

        const ids = this.documents.map(d => this._getId(d)).filter(Boolean);
        try {
            await Promise.allSettled(ids.map(id => this.apiClient.deleteDocument(id)));
            this.eventBus.emit(EVENTS.SHOW_NOTIFICATION, { type: 'success', message: 'Tous les documents ont t supprims.' });
        } catch {
            this.eventBus.emit(EVENTS.SHOW_NOTIFICATION, { type: 'error', message: 'Suppression partielle : vrifie les logs.' });
        } finally {
            await this.fetchAndRenderDocuments(true);
        }
    }
}





