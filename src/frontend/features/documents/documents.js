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
        this._offThreadSelected = null;
        this._unsubscribeSelectedIds = null;
        this._unsubscribeSelectionMeta = null;
        this._skipNextPersist = false;
        this._currentThreadId = null;
    }

    _handleAuthError(error, source) {
        const status = error?.status ?? error?.response?.status;
        if (status !== 401 && status !== 403) return false;

        try { this.eventBus?.emit?.('auth:missing', { reason: status, source }); } catch {}
        const message = 'Session expir\u00e9e. Merci de vous reconnecter.';
        try {
            const notifyEvent = EVENTS?.SHOW_NOTIFICATION || 'app:notify';
            this.eventBus?.emit?.(notifyEvent, { type: 'error', message });
        } catch {}
        try { if (this.dom?.uploadStatus) this.dom.uploadStatus.textContent = message; } catch {}
        return true;
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
        if (this.eventBus?.on && !this._offThreadSelected) {
            const off = this.eventBus.on(
                EVENTS?.THREADS_SELECTED || 'threads:selected',
                (payload) => this._handleThreadSelected(payload)
            );
            if (typeof off === 'function') this._offThreadSelected = off;
        }
        if (this.state?.get) {
            const saved = this.state.get('documents.selectedIds');
            if (Array.isArray(saved) && saved.length) {
                this.selectedIds = new Set(saved.map((id) => String(id)));
                this._lastSelectionHash = Array.from(this.selectedIds).join('|');
            }
            const currentThread = this.state.get('threads.currentId');
            if (currentThread) this._currentThreadId = String(currentThread);
        }
        if (this.state?.subscribe && !this._unsubscribeSelectedIds) {
            this._unsubscribeSelectedIds = this.state.subscribe('documents.selectedIds', (ids) => {
                this._applySelectionFromState(ids);
            });
        }
        if (this.state?.subscribe && !this._unsubscribeSelectionMeta) {
            this._unsubscribeSelectionMeta = this.state.subscribe('threads.currentId', (threadId) => {
                this._currentThreadId = threadId ? String(threadId) : null;
            });
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
        if (this._offThreadSelected) {
            try { this._offThreadSelected(); } catch {}
            this._offThreadSelected = null;
        }
        if (typeof this._unsubscribeSelectedIds === 'function') {
            try { this._unsubscribeSelectedIds(); } catch {}
            this._unsubscribeSelectedIds = null;
        }
        if (typeof this._unsubscribeSelectionMeta === 'function') {
            try { this._unsubscribeSelectionMeta(); } catch {}
            this._unsubscribeSelectionMeta = null;
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

    _emitSelectionChanged({ force = false } = {}) {
        const ids = Array.from(this.selectedIds);
        const hash = ids.join('|');
        if (!force && hash === this._lastSelectionHash) return;

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

        this._lastSelectionHash = hash;

        if (this._skipNextPersist) return;
        this._persistSelectionToThread(ids).catch((error) => {
            console.error('[Documents] thread docs persist failed', error);
        });
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

    _getActiveThreadId() {
        try {
            const current = this.state?.get?.('threads.currentId');
            if (current) return String(current);
        } catch {}
        return this._currentThreadId;
    }

    _applySelectionFromState(ids) {
        const normalized = Array.isArray(ids)
            ? ids.map((id) => String(id)).filter((id) => id)
            : [];
        this.selectedIds = new Set(normalized);
        this._lastSelectionHash = normalized.join('|');

        if (this.container) {
            this.container.querySelectorAll('.doc-select').forEach((input) => {
                const id = input.dataset.id;
                if (!id) return;
                input.checked = this.selectedIds.has(id);
            });
        }
        this.updateSelectionUI();
    }

    _handleThreadSelected(payload) {
        const threadId = payload?.id || payload?.thread?.id || payload?.thread_id || payload?.threadId;
        if (threadId) this._currentThreadId = String(threadId);

        const docs = Array.isArray(payload?.docs) ? payload.docs : [];
        const normalizedIds = docs.map((doc) => this._getId(doc)).filter(Boolean);

        this._applySelectionFromState(normalizedIds);
        this._skipNextPersist = true;
        this._emitSelectionChanged({ force: true });
        this._skipNextPersist = false;
    }

    async _persistSelectionToThread(ids) {
        const threadId = this._getActiveThreadId();
        if (!threadId) return;

        try {
            const response = await this.apiClient.setThreadDocs(threadId, ids);
            const docs = Array.isArray(response?.docs) ? this._normalizeThreadDocs(response.docs) : [];
            try { this.state?.set?.(`threads.map.${threadId}.docs`, docs); } catch {}
        } catch (error) {
            try {
                this.eventBus.emit(EVENTS.SHOW_NOTIFICATION, {
                    type: 'error',
                    message: 'Sauvegarde des documents du thread impossible.'
                });
            } catch {}
            throw error;
        }
    }

    _normalizeThreadDocs(docs) {
        const sanitized = [];
        const seen = new Set();
        for (const doc of docs || []) {
            const rawId = doc?.doc_id ?? doc?.id ?? doc;
            const num = Number(rawId);
            if (!Number.isFinite(num)) continue;
            const docId = Math.trunc(num);
            if (seen.has(docId)) continue;
            seen.add(docId);

            const statusRaw = doc?.status;
            const status = statusRaw == null ? 'ready' : (String(statusRaw).toLowerCase() || 'ready');
            sanitized.push({
                doc_id: docId,
                id: docId,
                filename: doc?.filename ?? doc?.name ?? null,
                name: doc?.filename || doc?.name || doc?.title || `Document ${docId}`,
                status,
                weight: Number.isFinite(doc?.weight) ? Number(doc.weight) : 1,
                last_used_at: doc?.last_used_at ?? null,
            });
        }
        return sanitized;
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
        this.dom.uploadStatus.textContent = `Televersement de ${this.selectedFiles.length} fichier(s).`;

        const results = [];
        let authErrorEncountered = false;

        for (const file of this.selectedFiles) {
            if (authErrorEncountered) break;
            try {
                const response = await this.apiClient.uploadDocument(file);
                const vectorized = response?.vectorized !== false;
                const warnMessage = response?.warning
                    || response?.message
                    || null;
                results.push({ ok: vectorized, name: file.name, response });

                if (vectorized) {
                    if (warnMessage) {
                        this.eventBus.emit(EVENTS.SHOW_NOTIFICATION, { type: 'warning', message: warnMessage });
                    } else {
                        this.eventBus.emit(EVENTS.SHOW_NOTIFICATION, { type: 'success', message: `Televersement : ${file.name}` });
                    }
                } else {
                    this.eventBus.emit(EVENTS.SHOW_NOTIFICATION, {
                        type: 'warning',
                        message: warnMessage || `Indexation vectorielle indisponible pour ${file.name}.`,
                    });
                }
            } catch (error) {
                results.push({ ok: false, name: file.name, error });
                if (this._handleAuthError(error, 'documents:upload')) {
                    authErrorEncountered = true;
                    continue;
                }
                const errorDetail = error?.message || 'Erreur inconnue';
                this.eventBus.emit(EVENTS.SHOW_NOTIFICATION, {
                    type: 'error',
                    message: `Echec upload ${file.name}: ${errorDetail}`
                });
            }
        }

        if (authErrorEncountered) {
            this.dom.uploadButton.disabled = false;
            return;
        }

        this.setSelectedFiles([]);
        this.dom.fileInput.value = '';

        await this.fetchAndRenderDocuments(true);

        const okCount = results.filter(r => r.ok).length;
        const koCount = results.length - okCount;
        this.dom.uploadStatus.textContent = '';
        if (koCount === 0) {
            this.eventBus.emit(EVENTS.SHOW_NOTIFICATION, { type: 'success', message: `Televersement termine (${okCount}/${results.length}).` });
        } else {
            this.eventBus.emit(EVENTS.SHOW_NOTIFICATION, { type: 'warning', message: `Televersement partiel (${okCount}/${results.length}).` });
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
            console.error('[Documents] echec de recuperation de la liste', e);
            const authHandled = this._handleAuthError(e, 'documents:list');
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

            if (authHandled && this.dom?.uploadStatus) {
                this.dom.uploadStatus.textContent = 'Connexion requise pour afficher les documents.';
            }
            this._scheduleAutoRefresh(false);
        }
    }

    _scheduleAutoRefresh(enable) {
        if (this._autoRefreshTimer) { clearTimeout(this._autoRefreshTimer); this._autoRefreshTimer = null; }
        if (!enable) return;
        this._autoRefreshTimer = setTimeout(() => this.fetchAndRenderDocuments(true), 3000);
    }

    _getFileIcon(filename) {
        const ext = (filename || '').split('.').pop()?.toLowerCase() || '';
        const iconSvg = `<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
            <polyline points="14 2 14 8 20 8"></polyline>
        </svg>`;
        return iconSvg;
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

        const eyeIcon = `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
            <circle cx="12" cy="12" r="3"></circle>
        </svg>`;

        const downloadIcon = `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
            <polyline points="7 10 12 15 17 10"></polyline>
            <line x1="12" y1="15" x2="12" y2="3"></line>
        </svg>`;

        const refreshIcon = `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="23 4 23 10 17 10"></polyline>
            <polyline points="1 20 1 14 7 14"></polyline>
            <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
        </svg>`;

        const trashIcon = `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="3 6 5 6 21 6"></polyline>
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
            <line x1="10" y1="11" x2="10" y2="17"></line>
            <line x1="14" y1="11" x2="14" y2="17"></line>
        </svg>`;

        return `
            <li class="document-item" data-id="${id}" data-name="${name}">
                <input type="checkbox" class="doc-select" data-id="${id}" aria-label="Slectionner ${name}">
                <span class="doc-icon" aria-hidden="true">${this._getFileIcon(name)}</span>
                <span class="doc-name" data-role="doc-name" title="${name}">${name}</span>
                <span class="doc-date">${when}</span>
                <span class="doc-status ${statusClass}">${status}</span>
                <div class="doc-actions">
                    <button class="doc-action doc-preview" data-action="preview" data-id="${id}" title="Prévisualiser ${name}" aria-label="Prévisualiser ${name}">
                        ${eyeIcon}
                    </button>
                    <button class="doc-action doc-download" data-action="download" data-id="${id}" title="Télécharger ${name}" aria-label="Télécharger ${name}">
                        ${downloadIcon}
                    </button>
                    <button class="doc-action doc-reindex" data-action="reindex" data-id="${id}" title="Ré-indexer ${name}" aria-label="Ré-indexer ${name}">
                        ${refreshIcon}
                    </button>
                    <button class="doc-action doc-remove" data-action="delete" data-id="${id}" title="Supprimer ${name}" aria-label="Supprimer ${name}">
                        ${trashIcon}
                    </button>
                </div>
            </li>
        `;
    }

    /* ------------------------------- Actions UI ------------------------------ */

    async handleDelete(e) {
        const btn = e.target.closest('[data-action]');
        if (!btn) return;

        const action = btn.dataset.action;
        const docId = btn.dataset.id;
        if (!docId) return;

        switch (action) {
            case 'preview':
                await this.previewDocument(docId);
                break;
            case 'download':
                await this.downloadDocument(docId);
                break;
            case 'reindex':
                await this.reindexDocument(docId);
                break;
            case 'delete':
                if (confirm('Supprimer ce document ?')) {
                    try {
                        await this.apiClient.deleteDocument(docId);
                        this.selectedIds.delete(docId);
                        this.eventBus.emit(EVENTS.SHOW_NOTIFICATION, { type: 'success', message: 'Document supprimé.' });
                        await this.fetchAndRenderDocuments(true);
                    } catch {
                        this.eventBus.emit(EVENTS.SHOW_NOTIFICATION, { type: 'error', message: 'Erreur lors de la suppression.' });
                    }
                }
                break;
        }
    }

    async previewDocument(docId) {
        try {
            const content = await this.apiClient.getDocumentContent(docId);
            const doc = this.documents.find(d => this._getId(d) === docId);
            const name = doc ? this._getName(doc) : 'Document';

            // Create modal
            const modal = document.createElement('div');
            modal.className = 'doc-preview-modal';
            modal.innerHTML = `
                <div class="doc-preview-modal__backdrop" data-action="close-preview"></div>
                <div class="doc-preview-modal__content">
                    <header class="doc-preview-modal__header">
                        <h3 class="doc-preview-modal__title">${name}</h3>
                        <button class="doc-preview-modal__close" data-action="close-preview" aria-label="Fermer">✕</button>
                    </header>
                    <div class="doc-preview-modal__body">
                        <pre class="doc-preview-modal__text">${content.content || content.text || JSON.stringify(content, null, 2)}</pre>
                    </div>
                </div>
            `;

            document.body.appendChild(modal);

            modal.addEventListener('click', (e) => {
                if (e.target.closest('[data-action="close-preview"]')) {
                    modal.remove();
                }
            });
        } catch (error) {
            this.eventBus.emit(EVENTS.SHOW_NOTIFICATION, { type: 'error', message: 'Impossible de prévisualiser le document.' });
        }
    }

    async downloadDocument(docId) {
        try {
            const blob = await this.apiClient.downloadDocument(docId);
            const doc = this.documents.find(d => this._getId(d) === docId);
            const name = doc ? this._getName(doc) : `document-${docId}`;

            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = name;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

            this.eventBus.emit(EVENTS.SHOW_NOTIFICATION, { type: 'success', message: 'Document téléchargé.' });
        } catch (error) {
            this.eventBus.emit(EVENTS.SHOW_NOTIFICATION, { type: 'error', message: 'Erreur lors du téléchargement.' });
        }
    }

    async reindexDocument(docId) {
        try {
            const response = await this.apiClient.reindexDocument(docId);
            const vectorized = response?.vectorized !== false;
            const warnMessage = response?.warning
                || response?.message
                || null;
            if (vectorized) {
                if (warnMessage) {
                    this.eventBus.emit(EVENTS.SHOW_NOTIFICATION, { type: 'warning', message: warnMessage });
                } else {
                    this.eventBus.emit(EVENTS.SHOW_NOTIFICATION, { type: 'success', message: 'Ré-indexation lancée.' });
                }
            } else {
                this.eventBus.emit(EVENTS.SHOW_NOTIFICATION, {
                    type: 'warning',
                    message: warnMessage || 'Ré-indexation partielle : index vectoriel indisponible.',
                });
            }
            await this.fetchAndRenderDocuments(true);
        } catch (error) {
            this.eventBus.emit(EVENTS.SHOW_NOTIFICATION, { type: 'error', message: 'Erreur lors de la ré-indexation.' });
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




