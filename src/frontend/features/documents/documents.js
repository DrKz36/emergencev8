/**
 * @module features/documents/documents
 * @description Logique du module Documents — liste stylée + drop-zone + multi-suppression
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
        this.selectedFile = null;
        this.selectedIds = new Set();
        this.isInitialized = false;
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
        };
    }

    registerDOMListeners() {
        // Sélection fichier(s)
        this.dom.fileInput.addEventListener('change', (e) => {
            const file = e.target.files && e.target.files[0];
            this.setSelectedFile(file || null);
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
            const file = (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0]) || null;
            this.setSelectedFile(file);
        });

        // Ouverture du picker via la drop‑zone
        const openPicker = () => this.dom.fileInput.click();
        this.dom.dropZone.addEventListener('click', openPicker);
        this.dom.dropZone.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') openPicker();
        });

        // Effacer la sélection locale (fichier)
        this.dom.clearSelectionBtn.addEventListener('click', () => this.setSelectedFile(null));

        // Actions upload
        this.dom.uploadButton.addEventListener('click', () => this.uploadFile());

        // Liste : délégation pour suppression unitaire
        this.dom.listContainer.addEventListener('click', (e) => this.handleDelete(e));

        // Liste : délégation pour cases à cocher
        this.dom.listContainer.addEventListener('change', (e) => {
            const box = e.target.closest('.doc-select');
            if (!box) return;
            const id = box.dataset.id;
            if (!id) return;
            if (box.checked) this.selectedIds.add(id);
            else this.selectedIds.delete(id);
            this.updateSelectionUI();
        });

        // Toolbar
        this.dom.selectAll.addEventListener('change', (e) => this.toggleSelectAll(e.target.checked));
        this.dom.deleteSelectedBtn.addEventListener('click', () => this.deleteSelected());
        this.dom.deleteAllBtn.addEventListener('click', () => this.deleteAll());
    }

    setSelectedFile(file) {
        this.selectedFile = file || null;

        if (this.selectedFile) {
            this.dom.previewName.textContent = this.selectedFile.name;
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

    async uploadFile() {
        if (!this.selectedFile) return;
        this.dom.uploadButton.disabled = true;
        this.dom.uploadStatus.textContent = `Upload de ${this.selectedFile.name}…`;

        try {
            const response = await this.apiClient.uploadDocument(this.selectedFile);
            this.eventBus.emit(EVENTS.SHOW_NOTIFICATION, { type: 'success', message: (response && response.message) || 'Fichier uploadé.' });
            // Reset sélection
            this.setSelectedFile(null);
            this.dom.fileInput.value = '';
            await this.fetchAndRenderDocuments();
        } catch (error) {
            this.eventBus.emit(EVENTS.SHOW_NOTIFICATION, { type: 'error', message: error.message || 'Erreur upload.' });
        } finally {
            this.dom.uploadStatus.textContent = '';
        }
    }

    async fetchAndRenderDocuments() {
        this.dom.listContainer.innerHTML = '<div class="loader"></div>';
        this.selectedIds.clear();

        try {
            this.documents = await this.apiClient.getDocuments();
            if (!Array.isArray(this.documents) || this.documents.length === 0) {
                this.dom.listContainer.innerHTML = '';
                if (this.dom.emptyListMessage) this.dom.emptyListMessage.style.display = 'block';
                this.updateSelectionUI();
                return;
            }
            if (this.dom.emptyListMessage) this.dom.emptyListMessage.style.display = 'none';

            this.dom.listContainer.innerHTML = this.documents.map((doc) => this.renderDocItem(doc)).join('');
            this.updateSelectionUI();
        } catch {
            this.dom.listContainer.innerHTML = '<p class="placeholder">Erreur de chargement des documents.</p>';
            this.updateSelectionUI();
        }
    }

    renderDocItem(doc) {
        const id = doc.id;
        const name = doc.filename || 'Fichier';
        const date = doc.uploaded_at ? formatDate(doc.uploaded_at) : '';
        const status = (doc.status || 'ready').toLowerCase(); // ready | processing | error
        const statusClass = status === 'processing' ? 'status-processing'
                          : status === 'error' ? 'status-error'
                          : 'status-ready';

        return `
            <li class="document-item" data-id="${id}">
                <input type="checkbox" class="doc-select" data-id="${id}" aria-label="Sélectionner ${name}">
                <span class="doc-icon" aria-hidden="true">📄</span>
                <span class="doc-name">${name}</span>
                <span class="doc-date">${date}</span>
                <span class="doc-status ${statusClass}">${status}</span>
                <button class="button button-metal btn-delete" data-id="${id}" title="Supprimer ${name}" aria-label="Supprimer ${name}">✕</button>
            </li>`;
    }

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
                await this.fetchAndRenderDocuments();
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
            await this.fetchAndRenderDocuments();
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
            await this.fetchAndRenderDocuments();
        }
    }
}
