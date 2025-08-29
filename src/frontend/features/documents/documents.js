/**
 * @module features/documents/documents
 * @description Logique du module Documents — V7.1
 * - Multi-fichiers (sélection + glisser/déposer)
 * - Upload séquentiel avec notifications
 * - Rafraîchissement intelligent (auto-refresh si 'processing')
 * - Toolbar: Tout sélectionner / Supprimer sélection / Tout effacer / Rafraîchir
 * - States et accessibilité soignés
 */
import { api } from '../../shared/api-client.js';
import { EVENTS } from '../../shared/constants.js';
import { formatDate } from '../../shared/utils.js';
import { DocumentsUI } from './document-ui.js';

export default class DocumentsModule {
    constructor(eventBus) {
        this.eventBus = eventBus;
        this.apiClient = api;
        this.ui = new DocumentsUI(eventBus);
        this.container = null;
        this.dom = {};
        this.documents = [];
        this.selectedFiles = [];
        this.selectedIds = new Set();
        this.isInitialized = false;
        this._autoRefreshTimer = null;
    }

    init() {
        if (this.isInitialized) return;
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
        // Sélection fichier(s)
        this.dom.fileInput.addEventListener('change', (e) => {
            const files = Array.from(e.target.files || []);
            this.setSelectedFiles(files);
        });

        // Drop-zone
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

        // Ouverture du picker via la drop-zone
        const openPicker = () => this.dom.fileInput.click();
        this.dom.dropZone.addEventListener('click', openPicker);
        this.dom.dropZone.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') openPicker();
        });

        // Effacer la sélection locale (fichiers)
        this.dom.clearSelectionBtn.addEventListener('click', () => this.setSelectedFiles([]));

        // Actions upload
        this.dom.uploadButton.addEventListener('click', () => this.uploadSelectedFiles());

        // Toolbar
        this.dom.selectAll.addEventListener('change', (e) => this.toggleSelectAll(e.target.checked));
        this.dom.deleteSelectedBtn.addEventListener('click', () => this.deleteSelected());
        this.dom.deleteAllBtn.addEventListener('click', () => this.deleteAll());
        this.dom.refreshBtn.addEventListener('click', () => this.fetchAndRenderDocuments(true));

        // Liste : délégation pour suppression unitaire + cases à cocher
        this.dom.listContainer.addEventListener('click', (e) => this.handleDelete(e));
        this.dom.listContainer.addEventListener('change', (e) => {
            const box = e.target.closest('.doc-select');
            if (!box) return;
            const id = box.dataset.id;
            if (!id) return;
            if (box.checked) this.selectedIds.add(id);
            else this.selectedIds.delete(id);
            this.updateSelectionUI();
        });

        // Auto-refresh au retour d'onglet
        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'visible') this.fetchAndRenderDocuments(true);
        });
    }

    /* ------------------------------- Sélection ------------------------------- */

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
        this.dom.uploadStatus.textContent = `Upload de ${this.selectedFiles.length} fichier(s)…`;

        const results = [];
        for (const file of this.selectedFiles) {
            try {
                await this.apiClient.uploadDocument(file);
                results.push({ ok: true, name: file.name });
                this.eventBus.emit(EVENTS.SHOW_NOTIFICATION, { type: 'success', message: `Uploadé : ${file.name}` });
            } catch (error) {
                results.push({ ok: false, name: file.name, error });
                this.eventBus.emit(EVENTS.SHOW_NOTIFICATION, { type: 'error', message: `Échec upload : ${file.name}` });
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
            this.eventBus.emit(EVENTS.SHOW_NOTIFICATION, { type: 'success', message: `Upload terminé (${okCount}/${results.length}).` });
        } else {
            this.eventBus.emit(EVENTS.SHOW_NOTIFICATION, { type: 'warning', message: `Upload partiel (${okCount}/${results.length}).` });
        }
    }

    /* -------------------------------- Listing -------------------------------- */

    async fetchAndRenderDocuments(force = false) {
        // Empêche le spam d'appels si on a déjà un timer actif et pas de force
        if (!force && this._autoRefreshTimer) return;

        this.dom.listContainer.innerHTML = '<div class="loader"></div>';
        this.selectedIds.clear();

        try {
            this.documents = await this.apiClient.getDocuments();

            if (!Array.isArray(this.documents) || this.documents.length === 0) {
                this.dom.listContainer.innerHTML = '';
                if (this.dom.emptyListMessage) this.dom.emptyListMessage.style.display = 'block';
                this.updateSelectionUI();
                // ➜ notifier l’UI stats
                this.eventBus.emit('documents:list:refreshed', { total: 0 });
                this._scheduleAutoRefresh(false);
                return;
            }

            if (this.dom.emptyListMessage) this.dom.emptyListMessage.style.display = 'none';

            this.dom.listContainer.innerHTML = this.documents.map((doc) => this.renderDocItem(doc)).join('');
            this.updateSelectionUI();

            // ➜ notifier l’UI stats
            this.eventBus.emit('documents:list:refreshed', { total: this.documents.length });

            // Auto-refresh si des items sont en 'processing'
            const hasProcessing = this.documents.some(d => String(d.status || '').toLowerCase() === 'processing');
            this._scheduleAutoRefresh(hasProcessing);
        } catch (e) {
            this.dom.listContainer.innerHTML = '<p class="placeholder">Erreur de chargement des documents.</p>';
            this.updateSelectionUI();
            // Émettre quand même un refresh (total inconnu → 0 si la liste est vide localement)
            this.eventBus.emit('documents:list:refreshed', { total: Array.isArray(this.documents) ? this.documents.length : 0 });
            this._scheduleAutoRefresh(false);
        }
    }

    _scheduleAutoRefresh(enabled) {
        if (this._autoRefreshTimer) {
            clearTimeout(this._autoRefreshTimer);
            this._autoRefreshTimer = null;
        }
        if (enabled) {
            this._autoRefreshTimer = setTimeout(() => this.fetchAndRenderDocuments(true), 3000);
        }
    }

    _escapeHTML(s) {
        return String(s ?? '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');
    }

    _escapeAttr(s) {
        return String(s ?? '')
            .replace(/&/g, '&amp;')
            .replace(/"/g, '&quot;')
            .replace(/</g, '&lt;');
    }

    renderDocItem(doc) {
        const id = doc.id;
        const rawName = doc.filename || 'Fichier';
        const name = this._escapeHTML(rawName);
        const nameAttr = this._escapeAttr(rawName);
        const date = doc.uploaded_at ? formatDate(doc.uploaded_at) : '';
        const status = (doc.status || 'ready').toLowerCase(); // ready | processing | error
        const statusClass = status === 'processing' ? 'status-processing'
                          : status === 'error' ? 'status-error'
                          : 'status-ready';

        return `
            <li class="document-item" data-id="${id}" data-name="${nameAttr}">
                <input type="checkbox" class="doc-select" data-id="${id}" aria-label="Sélectionner ${nameAttr}">
                <span class="doc-icon" aria-hidden="true">📄</span>
                <span class="doc-name">${name}</span>
                <span class="doc-date">${date}</span>
                <span class="doc-status ${statusClass}">${status}</span>
                <button class="button button-metal btn-delete" data-id="${id}" title="Supprimer ${nameAttr}" aria-label="Supprimer ${nameAttr}">✕</button>
            </li>`;
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
                this.eventBus.emit(EVENTS.SHOW_NOTIFICATION, { type: 'success', message: 'Document supprimé.' });
                await this.fetchAndRenderDocuments(true);
            } catch {
                this.eventBus.emit(EVENTS.SHOW_NOTIFICATION, { type: 'error', message: 'Erreur lors de la suppression.' });
            }
        }
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
            for (const d of this.documents) this.selectedIds.add(String(d.id));
        }
        // Refléter dans l’UI
        this.container.querySelectorAll('.doc-select').forEach(input => {
            input.checked = checked;
        });
        this.updateSelectionUI();
    }

    async deleteSelected() {
        const count = this.selectedIds.size;
        if (count === 0) return;
        if (!confirm(`Supprimer ${count} document(s) ?`)) return;

        const ids = Array.from(this.selectedIds);
        try {
            await Promise.allSettled(ids.map(id => this.apiClient.deleteDocument(id)));
            this.eventBus.emit(EVENTS.SHOW_NOTIFICATION, { type: 'success', message: `${count} document(s) supprimé(s).` });
        } catch {
            this.eventBus.emit(EVENTS.SHOW_NOTIFICATION, { type: 'error', message: 'Suppression partielle : vérifie les logs.' });
        } finally {
            await this.fetchAndRenderDocuments(true);
        }
    }

    async deleteAll() {
        if (!Array.isArray(this.documents) || this.documents.length === 0) return;
        if (!confirm(`Tout effacer ? (${this.documents.length} document(s))`)) return;

        const ids = this.documents.map(d => d.id);
        try {
            await Promise.allSettled(ids.map(id => this.apiClient.deleteDocument(id)));
            this.eventBus.emit(EVENTS.SHOW_NOTIFICATION, { type: 'success', message: 'Tous les documents ont été supprimés.' });
        } catch {
            this.eventBus.emit(EVENTS.SHOW_NOTIFICATION, { type: 'error', message: 'Suppression partielle : vérifie les logs.' });
        } finally {
            await this.fetchAndRenderDocuments(true);
        }
    }
}
