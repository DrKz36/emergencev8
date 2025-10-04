/**
 * Concept Recall History Modal - Option A
 * Displays detailed history of concept mentions across threads
 */

import { modals } from '../../components/modals.js';

export class ConceptRecallHistoryModal {
    constructor() {
        this.currentRecalls = [];
    }

    /**
     * Open history modal for concept recalls
     * @param {Array} recalls - Recalls from concept banner
     */
    async open(recalls) {
        if (!recalls || recalls.length === 0) {
            return;
        }

        this.currentRecalls = recalls;

        // Build modal content
        const content = await this._buildHistoryContent(recalls);

        modals.open({
            title: '🔗 Historique des concepts récurrents',
            content,
            size: 'large',
            closable: true,
            className: 'concept-recall-history-modal'
        });
    }

    /**
     * Build modal content HTML
     * @private
     */
    async _buildHistoryContent(recalls) {
        const container = document.createElement('div');
        container.className = 'concept-history-container';

        // Intro text
        const intro = document.createElement('p');
        intro.className = 'concept-history-intro';
        intro.textContent = recalls.length === 1
            ? 'Ce concept a déjà été abordé dans les conversations suivantes :'
            : `${recalls.length} concepts récurrents détectés dans vos conversations passées :`;
        container.appendChild(intro);

        // Fetch thread details for all recalls
        const threadDetailsMap = await this._fetchThreadDetails(recalls);

        // Build list of concepts
        for (const recall of recalls) {
            const conceptCard = this._buildConceptCard(recall, threadDetailsMap);
            container.appendChild(conceptCard);
        }

        return container;
    }

    /**
     * Fetch thread details for all thread IDs mentioned in recalls
     * @private
     */
    async _fetchThreadDetails(recalls) {
        const threadMap = new Map();
        const threadIds = new Set();

        // Collect all unique thread IDs
        for (const recall of recalls) {
            if (recall.thread_ids && Array.isArray(recall.thread_ids)) {
                recall.thread_ids.forEach(tid => threadIds.add(tid));
            }
        }

        // Fetch details for each thread
        const fetchPromises = Array.from(threadIds).map(async (threadId) => {
            try {
                const response = await fetch(`/api/threads/${threadId}`, {
                    credentials: 'include'
                });

                if (response.ok) {
                    const data = await response.json();
                    threadMap.set(threadId, {
                        id: threadId,
                        title: data.thread?.title || 'Sans titre',
                        created_at: data.thread?.created_at,
                        message_count: data.messages?.length || 0
                    });
                } else {
                    // Thread not accessible or deleted
                    threadMap.set(threadId, {
                        id: threadId,
                        title: 'Thread inaccessible',
                        deleted: true
                    });
                }
            } catch (error) {
                console.warn(`[ConceptHistory] Failed to fetch thread ${threadId}:`, error);
                threadMap.set(threadId, {
                    id: threadId,
                    title: 'Erreur de chargement',
                    error: true
                });
            }
        });

        await Promise.all(fetchPromises);
        return threadMap;
    }

    /**
     * Build concept card with thread list
     * @private
     */
    _buildConceptCard(recall, threadDetailsMap) {
        const card = document.createElement('div');
        card.className = 'concept-history-card';

        // Concept header
        const header = document.createElement('div');
        header.className = 'concept-card-header';

        const conceptName = document.createElement('h3');
        conceptName.className = 'concept-card-title';
        conceptName.textContent = recall.concept;

        const similarityBadge = document.createElement('span');
        similarityBadge.className = 'concept-similarity-badge';
        similarityBadge.textContent = `${Math.round(recall.similarity * 100)}% similaire`;

        header.appendChild(conceptName);
        header.appendChild(similarityBadge);
        card.appendChild(header);

        // Concept metadata
        const meta = document.createElement('div');
        meta.className = 'concept-card-meta';
        meta.innerHTML = `
            <div class="meta-item">
                <span class="meta-label">Première mention :</span>
                <span class="meta-value">${this._formatDate(recall.first_date)}</span>
            </div>
            <div class="meta-item">
                <span class="meta-label">Dernière mention :</span>
                <span class="meta-value">${this._formatDate(recall.last_date)}</span>
            </div>
            <div class="meta-item">
                <span class="meta-label">Nombre de mentions :</span>
                <span class="meta-value">${recall.count}</span>
            </div>
        `;
        card.appendChild(meta);

        // Thread list
        if (recall.thread_ids && recall.thread_ids.length > 0) {
            const threadSection = document.createElement('div');
            threadSection.className = 'concept-threads-section';

            const threadTitle = document.createElement('h4');
            threadTitle.className = 'concept-threads-title';
            threadTitle.textContent = `Mentionné dans ${recall.thread_count} thread${recall.thread_count > 1 ? 's' : ''} :`;
            threadSection.appendChild(threadTitle);

            const threadList = document.createElement('ul');
            threadList.className = 'concept-thread-list';

            for (const threadId of recall.thread_ids) {
                const threadDetails = threadDetailsMap.get(threadId);
                const threadItem = this._buildThreadListItem(threadId, threadDetails);
                threadList.appendChild(threadItem);
            }

            threadSection.appendChild(threadList);
            card.appendChild(threadSection);
        }

        return card;
    }

    /**
     * Build thread list item
     * @private
     */
    _buildThreadListItem(threadId, details) {
        const li = document.createElement('li');
        li.className = 'thread-list-item';

        if (details?.deleted || details?.error) {
            li.className += ' thread-unavailable';
            li.innerHTML = `
                <div class="thread-icon">🔒</div>
                <div class="thread-info">
                    <div class="thread-title">${this._escapeHtml(details.title)}</div>
                    <div class="thread-meta">Thread non accessible</div>
                </div>
            `;
        } else {
            li.className += ' thread-clickable';
            li.innerHTML = `
                <div class="thread-icon">💬</div>
                <div class="thread-info">
                    <div class="thread-title">${this._escapeHtml(details?.title || threadId)}</div>
                    <div class="thread-meta">
                        ${details?.message_count || 0} messages ·
                        ${this._formatDate(details?.created_at)}
                    </div>
                </div>
                <div class="thread-action">
                    <button class="btn-link-thread" data-thread-id="${threadId}">
                        Ouvrir →
                    </button>
                </div>
            `;

            // Add click handler to navigate to thread
            const openBtn = li.querySelector('.btn-link-thread');
            if (openBtn) {
                openBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    this._navigateToThread(threadId);
                });
            }
        }

        return li;
    }

    /**
     * Navigate to thread (close modal and switch thread in UI)
     * @private
     */
    _navigateToThread(threadId) {
        console.log(`[ConceptHistory] Navigating to thread: ${threadId}`);

        // Close the modal
        modals.closeAll();

        // Emit custom event to notify the chat UI
        const event = new CustomEvent('navigate-to-thread', {
            detail: { threadId }
        });
        window.dispatchEvent(event);

        // Alternative: Direct navigation if chat UI is available
        if (window.chatUI && typeof window.chatUI.switchThread === 'function') {
            window.chatUI.switchThread(threadId);
        }
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
