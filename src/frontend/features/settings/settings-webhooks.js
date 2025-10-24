/**
 * Settings Webhooks Module
 * Manages webhook subscriptions for external integrations (Slack, Discord, Zapier)
 */

import { getIcon } from './settings-icons.js';

class WebhooksSettings {
    constructor() {
        this.webhooks = [];
        this.showCreateModal = false;
        this.showDeliveriesModal = false;
        this.selectedWebhook = null;
    }

    /**
     * Initialize webhooks settings
     */
    async init(container) {
        this.container = container;
        await this.loadWebhooks();
        this.render();
    }

    /**
     * Load webhooks from API
     */
    async loadWebhooks() {
        try {
            const token = localStorage.getItem('id_token');
            if (!token) {
                console.error('No auth token found');
                return;
            }

            const response = await fetch('/api/webhooks', {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (!response.ok) {
                throw new Error(`Failed to load webhooks: ${response.status}`);
            }

            const data = await response.json();
            this.webhooks = data.items || [];
        } catch (error) {
            console.error('Failed to load webhooks:', error);
            this.showToast('Échec du chargement des webhooks', 'error');
        }
    }

    /**
     * Create new webhook
     */
    async createWebhook(formData) {
        try {
            const token = localStorage.getItem('id_token');
            const response = await fetch('/api/webhooks', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    url: formData.url,
                    events: formData.events,
                    description: formData.description || null,
                    active: formData.active !== false
                })
            });

            if (!response.ok) {
                throw new Error(`Failed to create webhook: ${response.status}`);
            }

            const webhook = await response.json();
            this.webhooks.unshift(webhook);
            this.showCreateModal = false;
            this.render();
            this.showToast('Webhook créé avec succès', 'success');
        } catch (error) {
            console.error('Failed to create webhook:', error);
            this.showToast('Échec de la création du webhook', 'error');
        }
    }

    /**
     * Delete webhook
     */
    async deleteWebhook(webhookId) {
        if (!confirm('Êtes-vous sûr de vouloir supprimer ce webhook ? Les logs de livraison seront également supprimés.')) {
            return;
        }

        try {
            const token = localStorage.getItem('id_token');
            const response = await fetch(`/api/webhooks/${webhookId}`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (!response.ok) {
                throw new Error(`Failed to delete webhook: ${response.status}`);
            }

            this.webhooks = this.webhooks.filter(w => w.id !== webhookId);
            this.render();
            this.showToast('Webhook supprimé', 'success');
        } catch (error) {
            console.error('Failed to delete webhook:', error);
            this.showToast('Échec de la suppression', 'error');
        }
    }

    /**
     * Toggle webhook active status
     */
    async toggleWebhook(webhookId, active) {
        try {
            const token = localStorage.getItem('id_token');
            const response = await fetch(`/api/webhooks/${webhookId}`, {
                method: 'PUT',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ active })
            });

            if (!response.ok) {
                throw new Error(`Failed to toggle webhook: ${response.status}`);
            }

            const updated = await response.json();
            const index = this.webhooks.findIndex(w => w.id === webhookId);
            if (index >= 0) {
                this.webhooks[index] = updated;
            }
            this.render();
            this.showToast(active ? 'Webhook activé' : 'Webhook désactivé', 'success');
        } catch (error) {
            console.error('Failed to toggle webhook:', error);
            this.showToast('Échec de la mise à jour', 'error');
        }
    }

    /**
     * Show webhook deliveries
     */
    async showDeliveries(webhookId) {
        try {
            const token = localStorage.getItem('id_token');
            const response = await fetch(`/api/webhooks/${webhookId}/deliveries?limit=50`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (!response.ok) {
                throw new Error(`Failed to load deliveries: ${response.status}`);
            }

            const data = await response.json();
            this.selectedWebhook = this.webhooks.find(w => w.id === webhookId);
            this.selectedWebhook.deliveries = data.items || [];
            this.showDeliveriesModal = true;
            this.render();
        } catch (error) {
            console.error('Failed to load deliveries:', error);
            this.showToast('Échec du chargement des logs', 'error');
        }
    }

    /**
     * Render webhooks settings
     */
    render() {
        if (!this.container) return;

        this.container.innerHTML = `
            <div class="settings-webhooks">
                <div class="settings-section-header">
                    <div class="section-header-content">
                        <h2>${getIcon('link', 'section-icon')} Webhooks</h2>
                        <p class="section-hint">Intégrations externes via HTTP (Slack, Discord, Zapier)</p>
                    </div>
                    <button class="btn-primary btn-create-webhook">
                        ${getIcon('plus', 'btn-icon')} Nouveau Webhook
                    </button>
                </div>

                ${this.webhooks.length === 0 ? this.renderEmpty() : this.renderWebhooksList()}

                ${this.showCreateModal ? this.renderCreateModal() : ''}
                ${this.showDeliveriesModal ? this.renderDeliveriesModal() : ''}
            </div>
        `;

        this.attachEventListeners();
    }

    /**
     * Render empty state
     */
    renderEmpty() {
        return `
            <div class="webhooks-empty">
                <div class="empty-icon">${getIcon('link', '')}</div>
                <h3>Aucun webhook configuré</h3>
                <p>Créez votre premier webhook pour recevoir des notifications d'événements</p>
                <button class="btn-primary btn-create-first">
                    ${getIcon('plus', 'btn-icon')} Créer un webhook
                </button>
            </div>
        `;
    }

    /**
     * Render webhooks list
     */
    renderWebhooksList() {
        return `
            <div class="webhooks-list">
                ${this.webhooks.map(webhook => this.renderWebhookCard(webhook)).join('')}
            </div>
        `;
    }

    /**
     * Render webhook card
     */
    renderWebhookCard(webhook) {
        const successRate = webhook.total_deliveries > 0
            ? Math.round((webhook.successful_deliveries / webhook.total_deliveries) * 100)
            : 0;

        return `
            <div class="webhook-card ${webhook.active ? '' : 'inactive'}">
                <div class="webhook-header">
                    <div class="webhook-title">
                        <span class="webhook-status ${webhook.active ? 'active' : 'inactive'}"></span>
                        <div>
                            <h3>${this.truncateUrl(webhook.url)}</h3>
                            ${webhook.description ? `<p class="webhook-desc">${webhook.description}</p>` : ''}
                        </div>
                    </div>
                    <div class="webhook-actions">
                        <button class="btn-icon btn-toggle-webhook" data-id="${webhook.id}" data-active="${!webhook.active}" title="${webhook.active ? 'Désactiver' : 'Activer'}">
                            ${getIcon(webhook.active ? 'toggleOn' : 'toggleOff', '')}
                        </button>
                        <button class="btn-icon btn-view-deliveries" data-id="${webhook.id}" title="Voir les logs">
                            ${getIcon('list', '')}
                        </button>
                        <button class="btn-icon btn-delete-webhook" data-id="${webhook.id}" title="Supprimer">
                            ${getIcon('trash', '')}
                        </button>
                    </div>
                </div>

                <div class="webhook-events">
                    ${webhook.events.map(event => `<span class="event-tag">${event}</span>`).join('')}
                </div>

                <div class="webhook-stats">
                    <div class="stat">
                        <span class="stat-label">Livraisons</span>
                        <span class="stat-value">${webhook.total_deliveries}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Succès</span>
                        <span class="stat-value stat-success">${webhook.successful_deliveries}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Échecs</span>
                        <span class="stat-value stat-error">${webhook.failed_deliveries}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Taux de succès</span>
                        <span class="stat-value">${successRate}%</span>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Render create modal
     */
    renderCreateModal() {
        return `
            <div class="modal-overlay">
                <div class="modal-content">
                    <div class="modal-header">
                        <h2>${getIcon('plus', 'modal-icon')} Nouveau Webhook</h2>
                        <button class="btn-close-modal">${getIcon('x', '')}</button>
                    </div>

                    <form class="webhook-form" id="webhookForm">
                        <div class="form-group">
                            <label for="webhookUrl">URL de destination *</label>
                            <input type="url" id="webhookUrl" name="url" required
                                   placeholder="https://hooks.slack.com/services/..." />
                            <small>L'URL qui recevra les événements via POST</small>
                        </div>

                        <div class="form-group">
                            <label for="webhookDesc">Description (optionnel)</label>
                            <input type="text" id="webhookDesc" name="description"
                                   placeholder="Slack #general, Discord #alerts, etc." />
                        </div>

                        <div class="form-group">
                            <label>Événements à surveiller *</label>
                            <div class="checkbox-group">
                                <label class="checkbox-label">
                                    <input type="checkbox" name="events" value="thread.created" />
                                    <span>thread.created - Nouveau thread créé</span>
                                </label>
                                <label class="checkbox-label">
                                    <input type="checkbox" name="events" value="message.sent" checked />
                                    <span>message.sent - Message envoyé</span>
                                </label>
                                <label class="checkbox-label">
                                    <input type="checkbox" name="events" value="analysis.completed" />
                                    <span>analysis.completed - Analyse mémoire terminée</span>
                                </label>
                                <label class="checkbox-label">
                                    <input type="checkbox" name="events" value="debate.completed" />
                                    <span>debate.completed - Débat terminé</span>
                                </label>
                                <label class="checkbox-label">
                                    <input type="checkbox" name="events" value="document.uploaded" />
                                    <span>document.uploaded - Document uploadé</span>
                                </label>
                            </div>
                        </div>

                        <div class="form-group">
                            <label class="checkbox-label">
                                <input type="checkbox" name="active" checked />
                                <span>Activer immédiatement</span>
                            </label>
                        </div>

                        <div class="modal-footer">
                            <button type="button" class="btn-secondary btn-cancel-create">Annuler</button>
                            <button type="submit" class="btn-primary">Créer</button>
                        </div>
                    </form>

                    <div class="webhook-help">
                        <h4>${getIcon('info', '')} Signature HMAC</h4>
                        <p>Les requêtes incluent un header <code>X-Webhook-Signature</code> (HMAC SHA256).</p>
                        <p>Votre endpoint peut vérifier l'authenticité avec le secret fourni après création.</p>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Render deliveries modal
     */
    renderDeliveriesModal() {
        if (!this.selectedWebhook) return '';

        return `
            <div class="modal-overlay">
                <div class="modal-content modal-lg">
                    <div class="modal-header">
                        <h2>${getIcon('list', 'modal-icon')} Logs de livraison</h2>
                        <button class="btn-close-deliveries">${getIcon('x', '')}</button>
                    </div>

                    <div class="deliveries-list">
                        ${this.selectedWebhook.deliveries.length === 0 ? `
                            <div class="deliveries-empty">
                                <p>Aucune livraison enregistrée</p>
                            </div>
                        ` : this.selectedWebhook.deliveries.map(d => this.renderDeliveryRow(d)).join('')}
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Render delivery row
     */
    renderDeliveryRow(delivery) {
        const isSuccess = delivery.status >= 200 && delivery.status < 300;
        const statusClass = isSuccess ? 'success' : 'error';

        return `
            <div class="delivery-row ${statusClass}">
                <div class="delivery-header">
                    <span class="delivery-event">${delivery.event_type}</span>
                    <span class="delivery-status status-${statusClass}">${delivery.status || 'Timeout'}</span>
                    <span class="delivery-attempt">Tentative ${delivery.attempt}/3</span>
                    <span class="delivery-time">${new Date(delivery.created_at).toLocaleString()}</span>
                </div>
                ${delivery.error ? `
                    <div class="delivery-error">
                        <strong>Erreur:</strong> ${delivery.error}
                    </div>
                ` : ''}
            </div>
        `;
    }

    /**
     * Attach event listeners
     */
    attachEventListeners() {
        // Create webhook buttons
        this.container.querySelectorAll('.btn-create-webhook, .btn-create-first').forEach(btn => {
            btn.addEventListener('click', () => {
                this.showCreateModal = true;
                this.render();
            });
        });

        // Close create modal
        this.container.querySelectorAll('.btn-close-modal, .btn-cancel-create').forEach(btn => {
            btn.addEventListener('click', () => {
                this.showCreateModal = false;
                this.render();
            });
        });

        // Submit webhook form
        const form = this.container.querySelector('#webhookForm');
        if (form) {
            form.addEventListener('submit', async (e) => {
                e.preventDefault();
                const formData = new FormData(form);
                const data = {
                    url: formData.get('url'),
                    description: formData.get('description') || null,
                    active: formData.get('active') === 'on',
                    events: Array.from(formData.getAll('events'))
                };

                if (data.events.length === 0) {
                    this.showToast('Sélectionnez au moins un événement', 'error');
                    return;
                }

                await this.createWebhook(data);
            });
        }

        // Delete webhook
        this.container.querySelectorAll('.btn-delete-webhook').forEach(btn => {
            btn.addEventListener('click', () => {
                const webhookId = btn.dataset.id;
                this.deleteWebhook(webhookId);
            });
        });

        // Toggle webhook
        this.container.querySelectorAll('.btn-toggle-webhook').forEach(btn => {
            btn.addEventListener('click', () => {
                const webhookId = btn.dataset.id;
                const active = btn.dataset.active === 'true';
                this.toggleWebhook(webhookId, active);
            });
        });

        // View deliveries
        this.container.querySelectorAll('.btn-view-deliveries').forEach(btn => {
            btn.addEventListener('click', () => {
                const webhookId = btn.dataset.id;
                this.showDeliveries(webhookId);
            });
        });

        // Close deliveries modal
        const closeDeliveriesBtn = this.container.querySelector('.btn-close-deliveries');
        if (closeDeliveriesBtn) {
            closeDeliveriesBtn.addEventListener('click', () => {
                this.showDeliveriesModal = false;
                this.selectedWebhook = null;
                this.render();
            });
        }
    }

    /**
     * Show toast notification
     */
    showToast(message, type = 'info') {
        // Use global toast system if available
        if (window.EventBus) {
            window.EventBus.emit('toast:show', { message, type });
        } else {
            console.log(`[Toast ${type}]`, message);
        }
    }

    /**
     * Truncate URL for display
     */
    truncateUrl(url) {
        if (url.length <= 50) return url;
        return url.substring(0, 47) + '...';
    }
}

export const settingsWebhooks = new WebhooksSettings();
