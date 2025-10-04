/**
 * Concept Recall Banner - Phase 3 + Option A
 * Displays recurring concept notifications in the chat UI
 */

import { ConceptRecallHistoryModal } from './concept-recall-history-modal.js';

export class ConceptRecallBanner {
    constructor(container) {
        if (!container) {
            throw new Error('ConceptRecallBanner: container element required');
        }
        this.container = container;
        this.isVisible = false;
        this.currentRecalls = [];
        this.historyModal = new ConceptRecallHistoryModal();
    }

    /**
     * Show banner with concept recalls
     * @param {Array} recalls - Array of recall objects from ws:concept_recall
     */
    show(recalls) {
        if (!recalls || recalls.length === 0) {
            this.hide();
            return;
        }

        this.currentRecalls = recalls;
        const html = this._buildBannerHTML(recalls);
        this.container.innerHTML = html;
        this.container.style.display = 'block';
        this.isVisible = true;

        // Attach event listeners
        this._attachEventListeners();

        // Auto-hide after 15 seconds
        setTimeout(() => {
            if (this.isVisible) {
                this.hide();
            }
        }, 15000);
    }

    /**
     * Hide banner
     */
    hide() {
        this.container.style.display = 'none';
        this.container.innerHTML = '';
        this.isVisible = false;
        this.currentRecalls = [];
    }

    /**
     * Build banner HTML
     * @private
     */
    _buildBannerHTML(recalls) {
        const recall = recalls[0]; // Show first concept
        const hasMultiple = recalls.length > 1;

        return `
            <div class="concept-recall-banner" data-recall-banner>
                <div class="banner-icon">🔗</div>
                <div class="banner-content">
                    <div class="banner-title">Concept déjà abordé</div>
                    <div class="banner-concept">${this._escapeHtml(recall.concept)}</div>
                    <div class="banner-meta">
                        Première mention : ${this._formatDate(recall.first_date)}<br>
                        Mentionné ${recall.count} fois dans ${recall.thread_count} thread${recall.thread_count > 1 ? 's' : ''}
                        ${hasMultiple ? `<br><em>+${recalls.length - 1} autre${recalls.length > 2 ? 's' : ''} concept${recalls.length > 2 ? 's' : ''}</em>` : ''}
                    </div>
                </div>
                <div class="banner-actions">
                    <button class="btn-secondary btn-sm" data-action="view-history">
                        Voir l'historique
                    </button>
                    <button class="btn-text btn-sm" data-action="dismiss">
                        Ignorer
                    </button>
                </div>
            </div>
        `;
    }

    /**
     * Attach event listeners to banner buttons
     * @private
     */
    _attachEventListeners() {
        const banner = this.container.querySelector('[data-recall-banner]');
        if (!banner) return;

        // Dismiss button
        const dismissBtn = banner.querySelector('[data-action="dismiss"]');
        if (dismissBtn) {
            dismissBtn.addEventListener('click', () => this.hide());
        }

        // View history button
        const historyBtn = banner.querySelector('[data-action="view-history"]');
        if (historyBtn) {
            historyBtn.addEventListener('click', () => this._onViewHistory());
        }
    }

    /**
     * Handle "View history" button click
     * @private
     */
    async _onViewHistory() {
        console.log('[ConceptRecallBanner] Opening history modal:', this.currentRecalls);

        // Open detailed history modal
        await this.historyModal.open(this.currentRecalls);

        // Keep banner visible (user might want to dismiss after viewing)
        // Or uncomment to auto-hide:
        // this.hide();
    }

    /**
     * Format ISO 8601 date to French locale
     * @private
     */
    _formatDate(isoDate) {
        if (!isoDate) return 'Date inconnue';

        try {
            const date = new Date(isoDate);
            return date.toLocaleDateString('fr-FR', {
                day: 'numeric',
                month: 'short',
                year: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
        } catch (e) {
            return isoDate;
        }
    }

    /**
     * Escape HTML to prevent XSS
     * @private
     */
    _escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}
