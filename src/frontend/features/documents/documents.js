/**
 * @module features/documents/documents
 * Logique du module Documents — V7.4
 * - Gardes DOM (robuste si template partiel)
 * - 401/403 -> auth:missing + stop refresh
 * - Auto-refresh borné + backoff
 * - Événements { total, items } + retick (data-first)
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
    this._autoRefreshIntervalMs = 45000;

    // bornage processing
    this._processingCycles = 0;
    this._processingMaxCycles = 10; // ~10 * (backoff moyen) ≈ 30-60s
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
    this._processingCycles = 0;
  }

  cacheDOM() {
    if (!this.container) return;
    const q = (sel) => this.container.querySelector(sel);

    this.dom = {
      fileInput: q('#file-input'),
      dropZone: q('#drop-zone'),
      dropZonePrompt: this.container.querySelector('.drop-zone-prompt'),
      dropZonePreview: q('#drop-zone-preview'),
      previewName: q('#preview-name'),
      clearSelectionBtn: q('#btn-clear-selection'),
      uploadButton: q('#upload-button'),
      uploadStatus: q('#upload-status'),
      listContainer: q('#document-list-container'),
      emptyListMessage: this.container.querySelector('.empty-list-message'),
      selectAll: q('#select-all'),
      deleteSelectedBtn: q('#btn-delete-selected'),
      deleteAllBtn: q('#btn-delete-all'),
      refreshBtn: q('#btn-refresh-list'),
    };
  }

  registerDOMListeners() {
    // Gardes DOM
    const D = this.dom;
    if (!D) return;

    // Sélection fichier(s)
    if (D.fileInput) {
      D.fileInput.addEventListener('change', (e) => {
        const files = Array.from(e.target.files || []);
        this.setSelectedFiles(files);
      });
    }

    // Drop-zone : DnD
    const prevent = (ev) => { ev.preventDefault(); ev.stopPropagation(); };
    if (D.dropZone) {
      ['dragenter', 'dragover'].forEach(evt =>
        D.dropZone.addEventListener(evt, (e) => {
          prevent(e);
          D.dropZone.classList.add('highlight');
        })
      );
      ['dragleave', 'drop'].forEach(evt =>
        D.dropZone.addEventListener(evt, (e) => {
          prevent(e);
          D.dropZone.classList.remove('highlight');
        })
      );
      D.dropZone.addEventListener('drop', (e) => {
        const files = Array.from((e.dataTransfer && e.dataTransfer.files) || []);
        this.setSelectedFiles(files);
      });
      // Click + clavier
      D.dropZone.addEventListener('click', () => { try { D.fileInput?.click(); } catch {} });
      D.dropZone.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); try { D.fileInput?.click(); } catch {} }
      });
    }

    // Clear selection
    D.clearSelectionBtn?.addEventListener('click', () => this.setSelectedFiles([]));

    // Upload
    D.uploadButton?.addEventListener('click', () => this.uploadSelectedFiles());

    // Toolbar list
    D.selectAll?.addEventListener('change', (e) => this.toggleSelectAll(e.target.checked));
    D.deleteSelectedBtn?.addEventListener('click', () => this.deleteSelected());
    D.deleteAllBtn?.addEventListener('click', () => this.deleteAll());
    D.refreshBtn?.addEventListener('click', () => this.fetchAndRenderDocuments(true));

    // Délégation suppression par ligne
    D.listContainer?.addEventListener('click', (e) => this.handleDelete(e));
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
      '—'
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
    const maybe = Object.values(resp).find(v => Array.isArray(v));
    return Array.isArray(maybe) ? maybe : [];
  }

  /* ------------------------------- Sélection ------------------------------- */

  setSelectedFiles(files) {
    const D = this.dom;
    this.selectedFiles = Array.isArray(files) ? files.filter(Boolean) : [];
    if (!D) return;

    if (this.selectedFiles.length) {
      const names = this.selectedFiles.map(f => f.name).join(', ');
      D.previewName && (D.previewName.textContent = names);
      D.dropZonePrompt && (D.dropZonePrompt.style.display = 'none');
      D.dropZonePreview && (D.dropZonePreview.style.display = 'flex');
      if (D.uploadButton) D.uploadButton.disabled = false;
      if (D.uploadStatus) D.uploadStatus.textContent = '';
    } else {
      D.previewName && (D.previewName.textContent = '');
      D.dropZonePrompt && (D.dropZonePrompt.style.display = 'flex');
      D.dropZonePreview && (D.dropZonePreview.style.display = 'none');
      if (D.uploadButton) D.uploadButton.disabled = true;
    }
  }

  /* --------------------------------- Upload -------------------------------- */

  async uploadSelectedFiles() {
    if (!this.selectedFiles.length) return;

    const D = this.dom;
    if (D.uploadButton) D.uploadButton.disabled = true;
    D.uploadStatus?.classList.remove('error', 'success', 'info');
    D.uploadStatus?.classList.add('info');
    if (D.uploadStatus) D.uploadStatus.textContent = `Upload de ${this.selectedFiles.length} fichier(s)…`;

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
    try { if (D.fileInput) D.fileInput.value = ''; } catch {}

    // Refresh & statut
    await this.fetchAndRenderDocuments(true);

    const okCount = results.filter(r => r.ok).length;
    const koCount = results.length - okCount;
    if (D.uploadStatus) D.uploadStatus.textContent = '';
    if (koCount === 0) {
      this.eventBus.emit(EVENTS.SHOW_NOTIFICATION, { type: 'success', message: `Upload terminé (${okCount}/${results.length}).` });
    } else {
      this.eventBus.emit(EVENTS.SHOW_NOTIFICATION, { type: 'warning', message: `Upload partiel (${okCount}/${results.length}).` });
    }
    if (D.uploadButton) D.uploadButton.disabled = false;
  }

  /* -------------------------------- Listing -------------------------------- */

  async fetchAndRenderDocuments(force = false) {
    if (!force && this._autoRefreshTimer) return;

    const D = this.dom;
    if (D.listContainer) D.listContainer.innerHTML = '<div class="loader"></div>';
    this.selectedIds.clear();

    try {
      const resp = await this.apiClient.getDocuments();
      this.documents = this._normalizeDocumentsResponse(resp);

      if (!Array.isArray(this.documents) || this.documents.length === 0) {
        if (D.listContainer) D.listContainer.innerHTML = '';
        if (D.emptyListMessage) D.emptyListMessage.style.display = 'block';
        this.updateSelectionUI();

        const payload = { total: 0, items: [] };
        try { this.eventBus.emit('documents:list:refreshed', payload); } catch {}
        try { if (EVENTS?.DOCUMENTS_LIST_REFRESHED) this.eventBus.emit(EVENTS.DOCUMENTS_LIST_REFRESHED, payload); } catch {}
        setTimeout(() => { try { this.eventBus.emit('documents:list:retick', payload); } catch {} }, 0);

        this._processingCycles = 0;
        this._scheduleAutoRefresh(false);
        return;
      }

      if (D.emptyListMessage) D.emptyListMessage.style.display = 'none';
      if (D.listContainer) D.listContainer.innerHTML = this.documents.map((doc) => this.renderDocItem(doc)).join('');
      this.updateSelectionUI();

      const payload = { total: this.documents.length, items: this.documents.slice() };
      try { this.eventBus.emit('documents:list:refreshed', payload); } catch {}
      try { if (EVENTS?.DOCUMENTS_LIST_REFRESHED) this.eventBus.emit(EVENTS.DOCUMENTS_LIST_REFRESHED, payload); } catch {}
      setTimeout(() => { try { this.eventBus.emit('documents:list:retick', payload); } catch {} }, 0);

      const hasProcessing = this.documents.some(d => String(d.status || '').toLowerCase() === 'processing');
      if (hasProcessing) this._processingCycles += 1; else this._processingCycles = 0;

      this._scheduleAutoRefresh(hasProcessing);
    } catch (e) {
      // 401/403: auth manquante → stop auto refresh + notif
      if (e?.status === 401 || e?.status === 403) {
        try { window.dispatchEvent(new CustomEvent('auth:missing', { detail: { status: e.status } })); } catch {}
        if (D.listContainer) D.listContainer.innerHTML = '<p class="error">Authentification requise.</p>';
        this.updateSelectionUI();

        const payload = { total: 0, items: [] };
        try { this.eventBus.emit('documents:list:refreshed', payload); } catch {}
        try { if (EVENTS?.DOCUMENTS_LIST_REFRESHED) this.eventBus.emit(EVENTS.DOCUMENTS_LIST_REFRESHED, payload); } catch {}
        setTimeout(() => { try { this.eventBus.emit('documents:list:retick', payload); } catch {} }, 0);

        this._processingCycles = 0;
        this._scheduleAutoRefresh(false);
        return;
      }

      console.error('[Documents] Échec de récupération de la liste', e);
      if (D.listContainer) D.listContainer.innerHTML = '<p class="error">Erreur lors du chargement des documents.</p>';
      this.updateSelectionUI();

      const payload = { total: 0, items: [] };
      try { this.eventBus.emit('documents:list:refreshed', payload); } catch {}
      try { if (EVENTS?.DOCUMENTS_LIST_REFRESHED) this.eventBus.emit(EVENTS.DOCUMENTS_LIST_REFRESHED, payload); } catch {}
      setTimeout(() => { try { this.eventBus.emit('documents:list:retick', payload); } catch {} }, 0);

      this._processingCycles = 0;
      this._scheduleAutoRefresh(false);
    }
  }

  _scheduleAutoRefresh(enable) {
    if (this._autoRefreshTimer) { clearTimeout(this._autoRefreshTimer); this._autoRefreshTimer = null; }
    if (!enable) return;

    // Si trop de cycles "processing", on arrête poliment pour éviter le loop infini
    if (this._processingCycles > this._processingMaxCycles) return;

    // Petit backoff pour laisser le backend terminer la vectorisation
    const delay = Math.min(1000 + this._processingCycles * 2000, 8000);
    this._autoRefreshTimer = setTimeout(() => this.fetchAndRenderDocuments(true), delay);
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
        <input type="checkbox" class="doc-select" data-id="${id}" aria-label="Sélectionner ${name}">
        <span class="doc-icon" aria-hidden="true">📄</span>
        <span class="doc-name" data-role="doc-name">${name}</span>
        <span class="doc-date">${when}</span>
        <span class="doc-status ${statusClass}">${status}</span>
        <button class="button button-metal btn-delete" data-id="${id}" title="Supprimer ${name}" aria-label="Supprimer ${name}">✕</button>
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
      for (const d of this.documents) this.selectedIds.add(this._getId(d));
    }
    this.container?.querySelectorAll('.doc-select').forEach(input => { input.checked = checked; });
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

    const ids = this.documents.map(d => this._getId(d)).filter(Boolean);
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
