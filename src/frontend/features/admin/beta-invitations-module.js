/**
 * @module features/admin/member-emails-module
 * @description Module d'envoi d'emails aux membres - Admin interface for sending emails to members
 * V2.0 - Send various types of emails to allowlist members
 * Supports: beta invitations, auth issue notifications, custom messages
 */

import { api } from '../../shared/api-client.js';
import { t } from '../../shared/i18n.js';

function escapeHtml(value) {
  if (value === null || value === undefined) return '';
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

export class BetaInvitationsModule {
  constructor(eventBus, state, options = {}) {
    this.eventBus = eventBus;
    this.state = state;
    this.options = options;

    this.container = null;
    this.emailsList = [];
    this.selectedEmails = new Set();
    this.isLoading = false;
    this.isSending = false;
    this.emailType = 'beta_invitation'; // Default type

    // UI Elements
    this.emailsContainer = null;
    this.selectAllCheckbox = null;
    this.sendButton = null;
    this.messageNode = null;
    this.searchInput = null;
    this.emailTypeSelect = null;
    this.filteredEmails = [];

    this.listeners = [];
  }

  mount(container) {
    if (!container) return;
    this.container = container;
    container.innerHTML = this.render();
    this.cacheElements();
    this.bindEvents();
    this.loadAllowlistEmails();
  }

  unmount() {
    this.listeners.forEach((unbind) => {
      try { unbind?.(); } catch (_) {}
    });
    this.listeners = [];
    if (this.container) {
      this.container.innerHTML = '';
    }
    this.container = null;
    this.emailsList = [];
    this.selectedEmails.clear();
    this.filteredEmails = [];
  }

  cacheElements() {
    if (!this.container) return;
    this.emailsContainer = this.container.querySelector('[data-role="emails-list"]');
    this.selectAllCheckbox = this.container.querySelector('[data-role="select-all"]');
    this.sendButton = this.container.querySelector('[data-role="send-invitations"]');
    this.messageNode = this.container.querySelector('[data-role="message"]');
    this.searchInput = this.container.querySelector('[data-role="search-emails"]');
    this.emailTypeSelect = this.container.querySelector('[data-role="email-type"]');
  }

  bindEvents() {
    // Select all checkbox
    if (this.selectAllCheckbox) {
      const onSelectAll = (event) => {
        const checked = event.target.checked;
        this.toggleSelectAll(checked);
      };
      this.selectAllCheckbox.addEventListener('change', onSelectAll);
      this.listeners.push(() => this.selectAllCheckbox.removeEventListener('change', onSelectAll));
    }

    // Send button
    if (this.sendButton) {
      const onSend = async (event) => {
        event.preventDefault();
        await this.handleSendInvitations();
      };
      this.sendButton.addEventListener('click', onSend);
      this.listeners.push(() => this.sendButton.removeEventListener('click', onSend));
    }

    // Email checkboxes (delegated event)
    if (this.emailsContainer) {
      const onEmailToggle = (event) => {
        const target = event.target;
        if (target.matches('[data-role="email-checkbox"]')) {
          const email = target.dataset.email;
          if (target.checked) {
            this.selectedEmails.add(email);
          } else {
            this.selectedEmails.delete(email);
          }
          this.updateSendButton();
          this.updateSelectAllCheckbox();
        }
      };
      this.emailsContainer.addEventListener('change', onEmailToggle);
      this.listeners.push(() => this.emailsContainer.removeEventListener('change', onEmailToggle));
    }

    // Search input
    if (this.searchInput) {
      const onSearch = (event) => {
        const query = event.target.value.toLowerCase().trim();
        this.filterEmails(query);
      };
      this.searchInput.addEventListener('input', onSearch);
      this.listeners.push(() => this.searchInput.removeEventListener('input', onSearch));
    }

    // Email type selector
    if (this.emailTypeSelect) {
      const onTypeChange = (event) => {
        this.emailType = event.target.value;
        this.updateSendButtonLabel();
      };
      this.emailTypeSelect.addEventListener('change', onTypeChange);
      this.listeners.push(() => this.emailTypeSelect.removeEventListener('change', onTypeChange));
    }
  }

  render() {
    return `
      <section class="beta-invitations" data-role="beta-invitations">
        <header class="auth-admin__header">
          <h2 class="auth-admin__title">📧 Envoi de mails aux membres</h2>
          <p class="auth-admin__subtitle">Envoyez différents types d'emails aux membres de l'allowlist</p>
        </header>

        <div data-role="message" class="auth-admin__message" aria-live="polite"></div>

        <div class="beta-invitations__controls">
          <label class="auth-admin__field">
            <span>📋 Type d'email</span>
            <select data-role="email-type" class="auth-admin__select">
              <option value="beta_invitation">🎉 Invitation Beta</option>
              <option value="auth_issue">🔧 Notification problème d'authentification</option>
            </select>
          </label>

          <label class="auth-admin__field">
            <span>🔍 Rechercher</span>
            <input
              data-role="search-emails"
              type="search"
              autocomplete="off"
              placeholder="Filtrer par email..."
            />
          </label>

          <label class="beta-invitations__select-all">
            <input
              data-role="select-all"
              type="checkbox"
            />
            <span>Tout sélectionner</span>
          </label>

          <button
            data-role="send-invitations"
            type="button"
            class="auth-admin__button auth-admin__button--primary"
            disabled
          >
            <span data-role="button-label">✉️ Envoyer les invitations</span> (<span data-role="selected-count">0</span>)
          </button>
        </div>

        <div class="beta-invitations__emails-wrapper">
          <div data-role="emails-list" class="beta-invitations__emails-list">
            <p class="auth-admin__muted">Chargement des emails...</p>
          </div>
        </div>
      </section>
    `;
  }

  async loadAllowlistEmails() {
    if (this.isLoading) return;
    this.isLoading = true;
    this.setLoadingMessage('Chargement des emails de l\'allowlist...');

    try {
      const response = await fetch('/api/admin/allowlist/emails', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this.getAuthToken()}`,
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      this.emailsList = data.emails || [];
      this.filteredEmails = [...this.emailsList];
      this.renderEmailsList();
      this.clearMessage();
    } catch (error) {
      console.error('[BetaInvitations] Failed to load emails:', error);
      this.notify('error', 'Erreur lors du chargement des emails');
      if (this.emailsContainer) {
        this.emailsContainer.innerHTML = '<p class="auth-admin__muted">Erreur lors du chargement</p>';
      }
    } finally {
      this.isLoading = false;
    }
  }

  filterEmails(query) {
    if (!query) {
      this.filteredEmails = [...this.emailsList];
    } else {
      this.filteredEmails = this.emailsList.filter(email =>
        email.toLowerCase().includes(query)
      );
    }
    this.renderEmailsList();
  }

  renderEmailsList() {
    if (!this.emailsContainer) return;

    if (this.filteredEmails.length === 0) {
      this.emailsContainer.innerHTML = '<p class="auth-admin__muted">Aucun email trouvé</p>';
      return;
    }

    const emailsHtml = this.filteredEmails.map(email => {
      const checked = this.selectedEmails.has(email) ? 'checked' : '';
      return `
        <label class="beta-invitations__email-item">
          <input
            data-role="email-checkbox"
            data-email="${escapeHtml(email)}"
            type="checkbox"
            ${checked}
          />
          <span>${escapeHtml(email)}</span>
        </label>
      `;
    }).join('');

    this.emailsContainer.innerHTML = emailsHtml;
    this.updateSelectAllCheckbox();
  }

  toggleSelectAll(checked) {
    if (checked) {
      this.filteredEmails.forEach(email => this.selectedEmails.add(email));
    } else {
      this.filteredEmails.forEach(email => this.selectedEmails.delete(email));
    }
    this.renderEmailsList();
    this.updateSendButton();
  }

  updateSelectAllCheckbox() {
    if (!this.selectAllCheckbox) return;

    const visibleEmails = this.filteredEmails;
    const allSelected = visibleEmails.length > 0 &&
                       visibleEmails.every(email => this.selectedEmails.has(email));

    this.selectAllCheckbox.checked = allSelected;
  }

  updateSendButton() {
    if (!this.sendButton) return;

    const count = this.selectedEmails.size;
    const countSpan = this.sendButton.querySelector('[data-role="selected-count"]');
    if (countSpan) {
      countSpan.textContent = count;
    }

    this.sendButton.disabled = count === 0 || this.isSending;
    this.updateSendButtonLabel();
  }

  updateSendButtonLabel() {
    if (!this.sendButton) return;

    const labelSpan = this.sendButton.querySelector('[data-role="button-label"]');
    if (!labelSpan) return;

    const labels = {
      'beta_invitation': '✉️ Envoyer les invitations',
      'auth_issue': '🔧 Envoyer les notifications',
      'custom': '📤 Envoyer les messages',
    };

    labelSpan.textContent = labels[this.emailType] || '✉️ Envoyer';
  }

  async handleSendInvitations() {
    if (this.isSending || this.selectedEmails.size === 0) return;

    const confirmMessages = {
      'beta_invitation': `Êtes-vous sûr de vouloir envoyer ${this.selectedEmails.size} invitation(s) beta ?`,
      'auth_issue': `Êtes-vous sûr de vouloir envoyer ${this.selectedEmails.size} notification(s) de problème d'authentification ?`,
      'custom': `Êtes-vous sûr de vouloir envoyer ${this.selectedEmails.size} message(s) personnalisé(s) ?`,
    };

    const confirmed = confirm(
      confirmMessages[this.emailType] || `Êtes-vous sûr de vouloir envoyer ${this.selectedEmails.size} email(s) ?`
    );

    if (!confirmed) return;

    this.isSending = true;
    this.updateSendButton();

    const sendingMessages = {
      'beta_invitation': `Envoi de ${this.selectedEmails.size} invitation(s) en cours...`,
      'auth_issue': `Envoi de ${this.selectedEmails.size} notification(s) en cours...`,
      'custom': `Envoi de ${this.selectedEmails.size} message(s) en cours...`,
    };

    this.notify('info', sendingMessages[this.emailType] || `Envoi de ${this.selectedEmails.size} email(s) en cours...`);

    try {
      const response = await fetch('/api/admin/emails/send', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this.getAuthToken()}`,
        },
        body: JSON.stringify({
          emails: Array.from(this.selectedEmails),
          base_url: window.location.origin,
          email_type: this.emailType,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const result = await response.json();

      const typeLabels = {
        'beta_invitation': 'invitation(s)',
        'auth_issue': 'notification(s)',
        'custom': 'message(s)',
      };

      const label = typeLabels[this.emailType] || 'email(s)';
      const successMessage = `✅ ${result.sent}/${result.total} ${label} envoyée(s) avec succès`;

      if (result.failed > 0) {
        this.notify('warning', `${successMessage}. ${result.failed} échec(s).`);
        console.warn('[MemberEmails] Failed emails:', result.failed_emails);
      } else {
        this.notify('success', successMessage);
      }

      // Clear selection after successful send
      this.selectedEmails.clear();
      this.renderEmailsList();
      this.updateSendButton();

    } catch (error) {
      console.error('[MemberEmails] Failed to send emails:', error);
      this.notify('error', 'Erreur lors de l\'envoi des emails');
    } finally {
      this.isSending = false;
      this.updateSendButton();
    }
  }

  getAuthToken() {
    // Get token from localStorage (same as admin dashboard)
    try {
      return localStorage.getItem('emergence.id_token') ||
             localStorage.getItem('id_token') ||
             sessionStorage.getItem('emergence.id_token') ||
             sessionStorage.getItem('id_token') ||
             '';
    } catch {
      return '';
    }
  }

  notify(kind, message) {
    const text = typeof message === 'string' ? message : '';
    if (text) {
      this.showMessage(kind, text);
      try {
        this.eventBus?.emit?.('ui:toast', { kind, text });
      } catch (err) {
        console.warn('[BetaInvitations] toast emit failed', err);
      }
    } else {
      this.clearMessage();
    }
  }

  showMessage(kind, message) {
    if (!this.messageNode) return;
    const text = typeof message === 'string' ? message : '';
    this.messageNode.textContent = text;
    this.messageNode.classList.remove('is-error', 'is-success', 'is-info', 'is-warning');
    if (!text) return;
    if (kind === 'error') this.messageNode.classList.add('is-error');
    else if (kind === 'success') this.messageNode.classList.add('is-success');
    else if (kind === 'warning') this.messageNode.classList.add('is-warning');
    else this.messageNode.classList.add('is-info');
  }

  setLoadingMessage(message) {
    if (this.emailsContainer) {
      this.emailsContainer.innerHTML = `<p class="auth-admin__muted">${escapeHtml(message)}</p>`;
    }
  }

  clearMessage() {
    if (!this.messageNode) return;
    this.messageNode.textContent = '';
    this.messageNode.classList.remove('is-error', 'is-success', 'is-info', 'is-warning');
  }
}

export default BetaInvitationsModule;
