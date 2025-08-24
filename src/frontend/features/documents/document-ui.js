/**
 * @module features/documents/document-ui
 * @description UI du module Documents — V4.0 (verre/halo/métal)
 * - Upload : drop-zone + preview multi-fichiers
 * - Liste : toolbar (sélection, suppression, rafraîchir)
 */
export class DocumentsUI {
    constructor(eventBus) {
        this.eventBus = eventBus;
    }

    render(container) {
        container.innerHTML = `
            <div class="documents-view-wrapper">
                <div class="card">
                    <div class="card-header">
                        <h2 class="card-title">Gérer les documents</h2>
                        <p class="card-subtitle">Ajoute des fichiers pour les rendre accessibles via RAG.</p>
                    </div>

                    <div class="card-body">
                        <section class="upload-section" aria-label="Upload de documents">
                            <input type="file" id="file-input" multiple accept=".pdf,.txt,.docx,.md" />

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

                            <button id="upload-button" class="button button-metal" disabled>Uploader</button>
                            <div id="upload-status" class="upload-status info" aria-live="polite"></div>
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
                    </div>
                </div>
            </div>`;
    }
}
