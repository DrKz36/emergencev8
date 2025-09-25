import { api } from '../../shared/api-client.js';
import { t } from '../../shared/i18n.js';

function formatDateTime(value) {
  if (!value) return '-';
  try {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return '-';
    return date.toLocaleString();
  } catch (err) {
    console.warn('[AuthAdmin] formatDateTime failed', err, value);
    return '-';
  }
}

function escapeHtml(value) {
  if (value === null || value === undefined) return '';
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function encodeNote(value) {
  if (!value) return '';
  try {
    return encodeURIComponent(String(value));
  } catch (err) {
    console.warn('[AuthAdmin] encodeNote failed', err);
    return '';
  }
}

function decodeNote(value) {
  if (!value) return '';
  try {
    return decodeURIComponent(value);
  } catch (err) {
    console.warn('[AuthAdmin] decodeNote failed', err, value);
    return value;
  }
}

export class AuthAdminModule {
  constructor(eventBus, state, options = {}) {
    this.eventBus = eventBus;
    this.state = state;
    this.options = options;

    this.container = null;
    this.form = null;
    this.emailInput = null;
    this.roleSelect = null;
    this.noteInput = null;
    this.passwordInput = null;
    this.generateButton = null;
    this.submitButton = null;
    this.copyButton = null;
    this.messageNode = null;
    this.summaryNode = null;
    this.generatedBlock = null;
    this.generatedValueNode = null;
    this.statusSelect = null;
    this.searchInput = null;
    this.tableBody = null;
    this.prevPageButton = null;
    this.nextPageButton = null;
    this.paginationInfo = null;

    this.isSubmitting = false;
    this.listeners = [];

    this.status = 'active';
    this.page = 1;
    this.pageSize = 20;
    this.total = 0;
    this.totalPages = 1;
    this.query = '';
    this.hasMore = false;
    this.searchTimer = null;
  }

  mount(container) {
    if (!container) return;
    this.container = container;
    container.innerHTML = this.render();
    this.cacheElements();
    this.bindEvents();
    this.loadAllowlist();
  }

  unmount() {
    if (this.searchTimer) {
      clearTimeout(this.searchTimer);
      this.searchTimer = null;
    }
    this.listeners.forEach((unbind) => {
      try { unbind?.(); } catch (_) {}
    });
    this.listeners = [];
    if (this.form) {
      try { this.form.reset(); } catch (_) {}
    }
    if (this.container) {
      this.container.innerHTML = '';
    }
    this.container = null;
    this.form = null;
    this.emailInput = null;
    this.roleSelect = null;
    this.noteInput = null;
    this.passwordInput = null;
    this.generateButton = null;
    this.submitButton = null;
    this.copyButton = null;
    this.messageNode = null;
    this.summaryNode = null;
    this.generatedBlock = null;
    this.generatedValueNode = null;
    this.statusSelect = null;
    this.searchInput = null;
    this.tableBody = null;
    this.prevPageButton = null;
    this.nextPageButton = null;
    this.paginationInfo = null;
  }

  cacheElements() {
    if (!this.container) return;
    this.form = this.container.querySelector('[data-role="allowlist-form"]');
    this.emailInput = this.container.querySelector('[data-role="input-email"]');
    this.roleSelect = this.container.querySelector('[data-role="input-role"]');
    this.noteInput = this.container.querySelector('[data-role="input-note"]');
    this.passwordInput = this.container.querySelector('[data-role="input-password"]');
    this.generateButton = this.container.querySelector('[data-role="btn-generate"]');
    this.submitButton = this.container.querySelector('[data-role="btn-submit"]');
    this.copyButton = this.container.querySelector('[data-role="copy-password"]');
    this.messageNode = this.container.querySelector('[data-role="allowlist-message"]');
    this.summaryNode = this.container.querySelector('[data-role="allowlist-summary"]');
    this.generatedBlock = this.container.querySelector('[data-role="generated-password"]');
    this.generatedValueNode = this.container.querySelector('[data-role="generated-password-value"]');
    this.statusSelect = this.container.querySelector('[data-role="status-filter"]');
    this.searchInput = this.container.querySelector('[data-role="input-search"]');
    this.tableBody = this.container.querySelector('[data-role="allowlist-rows"]');
    this.prevPageButton = this.container.querySelector('[data-role="page-prev"]');
    this.nextPageButton = this.container.querySelector('[data-role="page-next"]');
    this.paginationInfo = this.container.querySelector('[data-role="pagination-info"]');
    if (this.statusSelect) {
      this.statusSelect.value = this.status;
    }
    if (this.searchInput) {
      this.searchInput.value = this.query;
    }
  }

  bindEvents() {
    if (this.form) {
      const onSubmit = (event) => {
        event.preventDefault();
        this.handleSubmit();
      };
      this.form.addEventListener('submit', onSubmit);
      this.listeners.push(() => this.form.removeEventListener('submit', onSubmit));
    }

    if (this.generateButton) {
      const onGenerate = (event) => {
        event.preventDefault();
        this.handleGenerateClick();
      };
      this.generateButton.addEventListener('click', onGenerate);
      this.listeners.push(() => this.generateButton.removeEventListener('click', onGenerate));
    }

    if (this.copyButton) {
      const onCopy = (event) => {
        event.preventDefault();
        const value = this.generatedValueNode?.textContent || '';
        this.copyToClipboard(value);
      };
      this.copyButton.addEventListener('click', onCopy);
      this.listeners.push(() => this.copyButton.removeEventListener('click', onCopy));
    }

    if (this.tableBody) {
      const onTableClick = (event) => {
        const target = event.target.closest('[data-action]');
        if (!target) return;
        const action = target.getAttribute('data-action');
        if (action === 'generate') {
          event.preventDefault();
          const email = target.getAttribute('data-email');
          if (!email) return;
          const encodedRole = target.getAttribute('data-role-value') || 'member';
          const encodedNote = target.getAttribute('data-note') || '';
          const role = decodeURIComponent(encodedRole);
          const note = decodeNote(encodedNote) || null;
          this.handleRowGenerate(email, role, note);
        }
      };
      this.tableBody.addEventListener('click', onTableClick);
      this.listeners.push(() => this.tableBody.removeEventListener('click', onTableClick));
    }

    if (this.statusSelect) {
      const onStatusChange = (event) => {
        const value = event.target?.value || 'active';
        this.handleStatusChange(value);
      };
      this.statusSelect.addEventListener('change', onStatusChange);
      this.listeners.push(() => this.statusSelect.removeEventListener('change', onStatusChange));
    }

    if (this.searchInput) {
      const onSearch = (event) => {
        const value = event.target?.value || '';
        this.scheduleSearch(value);
      };
      this.searchInput.addEventListener('input', onSearch);
      this.listeners.push(() => this.searchInput.removeEventListener('input', onSearch));
    }

    if (this.prevPageButton) {
      const onPrev = (event) => {
        event.preventDefault();
        if (this.page <= 1) return;
        this.loadAllowlist({ page: this.page - 1 });
      };
      this.prevPageButton.addEventListener('click', onPrev);
      this.listeners.push(() => this.prevPageButton.removeEventListener('click', onPrev));
    }

    if (this.nextPageButton) {
      const onNext = (event) => {
        event.preventDefault();
        if (this.page >= this.totalPages) return;
        this.loadAllowlist({ page: this.page + 1 });
      };
      this.nextPageButton.addEventListener('click', onNext);
      this.listeners.push(() => this.nextPageButton.removeEventListener('click', onNext));
    }
  }

  render() {
    const title = t('admin.title');
    const subtitle = t('admin.subtitle');
    const emailLabel = t('admin.email_label');
    const roleLabel = t('admin.role_label');
    const roleMember = t('admin.role_member');
    const roleAdmin = t('admin.role_admin');
    const noteLabel = t('admin.note_label');
    const passwordLabel = t('admin.password_label');
    const passwordPlaceholder = t('admin.password_placeholder');
    const submitLabel = t('admin.submit');
    const generateLabel = t('admin.generate');
    const searchLabel = t('admin.search_label') || 'Recherche';
    const searchPlaceholder = t('admin.search_placeholder') || 'Email ou note';
    const statusLabel = t('admin.status_filter_label') || 'Statut';
    const statusActive = t('admin.status_active') || 'Actives';
    const statusAll = t('admin.status_all') || 'Toutes';
    const statusRevoked = t('admin.status_revoked') || 'Révoquées';
    const tableEmail = t('admin.table_email');
    const tableRole = t('admin.table_role');
    const tableNote = t('admin.table_note');
    const tableStatus = t('admin.table_status') || 'Statut';
    const tablePasswordUpdated = t('admin.table_password_updated');
    const tableActions = t('admin.table_actions');
    const generatedPasswordLabel = t('admin.generated_password_label');
    const copyLabel = t('admin.copy');
    const prevLabel = t('admin.prev_page') || 'Précédent';
    const nextLabel = t('admin.next_page') || 'Suivant';

    return `
      <section class="auth-admin" data-role="auth-admin">
        <header class="auth-admin__header">
          <h2 class="auth-admin__title">${title}</h2>
          <p class="auth-admin__subtitle">${subtitle}</p>
        </header>
        <form data-role="allowlist-form" class="auth-admin__form">
          <div class="auth-admin__form-grid">
            <label class="auth-admin__field">
              <span>${emailLabel}</span>
              <input data-role="input-email" type="email" required autocomplete="off" />
            </label>
            <label class="auth-admin__field">
              <span>${roleLabel}</span>
              <select data-role="input-role">
                <option value="member">${roleMember}</option>
                <option value="admin">${roleAdmin}</option>
              </select>
            </label>
            <label class="auth-admin__field">
              <span>${noteLabel}</span>
              <input data-role="input-note" type="text" autocomplete="off" />
            </label>
            <label class="auth-admin__field">
              <span>${passwordLabel}</span>
              <input data-role="input-password" type="text" autocomplete="off" placeholder="${passwordPlaceholder}" />
            </label>
          </div>
          <div class="auth-admin__actions">
            <button data-role="btn-submit" type="submit" class="auth-admin__button auth-admin__button--primary">${submitLabel}</button>
            <button data-role="btn-generate" type="button" class="auth-admin__button">${generateLabel}</button>
          </div>
        </form>
        <div data-role="allowlist-message" class="auth-admin__message" aria-live="polite"></div>
        <div data-role="generated-password" class="auth-admin__generated" hidden>
          <div class="auth-admin__generated-header">
            <span>${generatedPasswordLabel}</span>
            <button type="button" data-role="copy-password" class="auth-admin__button auth-admin__button--ghost">${copyLabel}</button>
          </div>
          <code data-role="generated-password-value" class="auth-admin__generated-value"></code>
        </div>
        <div class="auth-admin__filters">
          <label class="auth-admin__filter">
            <span>${searchLabel}</span>
            <input data-role="input-search" type="search" autocomplete="off" placeholder="${searchPlaceholder}" />
          </label>
          <label class="auth-admin__filter">
            <span>${statusLabel}</span>
            <select data-role="status-filter">
              <option value="active">${statusActive}</option>
              <option value="all">${statusAll}</option>
              <option value="revoked">${statusRevoked}</option>
            </select>
          </label>
        </div>
        <div data-role="allowlist-summary" class="auth-admin__summary"></div>
        <div class="auth-admin__table-wrapper">
          <table class="auth-admin__table">
            <thead>
              <tr>
                <th scope="col">${tableEmail}</th>
                <th scope="col">${tableRole}</th>
                <th scope="col">${tableNote}</th>
                <th scope="col">${tableStatus}</th>
                <th scope="col">${tablePasswordUpdated}</th>
                <th scope="col">${tableActions}</th>
              </tr>
            </thead>
            <tbody data-role="allowlist-rows"></tbody>
          </table>
        </div>
        <div class="auth-admin__pagination" data-role="pagination">
          <button type="button" class="auth-admin__button auth-admin__button--ghost" data-role="page-prev" disabled>${prevLabel}</button>
          <span data-role="pagination-info" class="auth-admin__pagination-info"></span>
          <button type="button" class="auth-admin__button auth-admin__button--ghost" data-role="page-next" disabled>${nextLabel}</button>
        </div>
      </section>
    `;
  }

  setLoading(isLoading) {
    this.isSubmitting = !!isLoading;
    const targets = [
      this.emailInput,
      this.roleSelect,
      this.noteInput,
      this.passwordInput,
      this.submitButton,
      this.generateButton,
      this.statusSelect,
      this.searchInput,
      this.prevPageButton,
      this.nextPageButton,
    ];
    targets.forEach((input) => {
      if (!input) return;
      try {
        if (isLoading) input.setAttribute('disabled', 'disabled');
        else input.removeAttribute('disabled');
      } catch (_) {}
    });
    if (this.submitButton) {
      this.submitButton.setAttribute('aria-busy', isLoading ? 'true' : 'false');
    }
  }

  async handleSubmit() {
    if (this.isSubmitting) return;
    const { email, role, note, password } = this.getFormData();
    this.clearGeneratedPassword();
    if (!email) {
      this.notify('error', t('home.error_invalid'));
      return;
    }
    if (password && password.length < 8) {
      this.notify('error', t('home.error_password_short'));
      return;
    }
    await this.submitAllowlist({ email, role, note, password, generatePassword: false });
  }

  async handleGenerateClick() {
    if (this.isSubmitting) return;
    const { email, role, note } = this.getFormData();
    this.clearGeneratedPassword();
    if (!email) {
      this.notify('error', t('home.error_invalid'));
      return;
    }
    await this.submitAllowlist({ email, role, note, password: null, generatePassword: true });
  }

  async handleRowGenerate(email, role, note) {
    if (this.isSubmitting) return;
    const normalizedRole = typeof role === 'string' && role.trim() ? role.trim().toLowerCase() : 'member';
    const normalizedNote = typeof note === 'string' && note.trim() ? note.trim() : null;
    this.clearGeneratedPassword();
    await this.submitAllowlist({ email, role: normalizedRole, note: normalizedNote, password: null, generatePassword: true });
  }

  handleStatusChange(value) {
    const normalized = (value || '').trim().toLowerCase();
    const allowed = new Set(['active', 'all', 'revoked']);
    this.status = allowed.has(normalized) ? normalized : 'active';
    if (this.statusSelect && this.statusSelect.value !== this.status) {
      this.statusSelect.value = this.status;
    }
    this.page = 1;
    this.loadAllowlist({ page: 1 });
  }

  scheduleSearch(rawValue) {
    const value = (rawValue || '').trim();
    if (this.searchTimer) {
      clearTimeout(this.searchTimer);
      this.searchTimer = null;
    }
    this.searchTimer = setTimeout(() => {
      this.searchTimer = null;
      this.query = value;
      this.page = 1;
      this.loadAllowlist({ page: 1 });
    }, 300);
  }

  getFormData() {
    const email = (this.emailInput?.value || '').trim().toLowerCase();
    const role = (this.roleSelect?.value || 'member').trim().toLowerCase();
    const noteRaw = this.noteInput?.value;
    const note = typeof noteRaw === 'string' ? noteRaw.trim() : null;
    const passwordRaw = this.passwordInput?.value || '';
    const password = passwordRaw.trim();
    return { email, role, note, password: password || null };
  }

  notify(kind, message) {
    const text = typeof message === 'string' ? message : '';
    if (text) {
      this.showMessage(kind, text);
      try {
        this.eventBus?.emit?.('ui:toast', { kind, text });
      } catch (err) {
        console.warn('[AuthAdmin] toast emit failed', err);
      }
    } else {
      this.clearMessage();
    }
  }

  showMessage(kind, message) {
    if (!this.messageNode) return;
    const text = typeof message === 'string' ? message : '';
    this.messageNode.textContent = text;
    this.messageNode.classList.remove('is-error', 'is-success', 'is-info');
    if (!text) return;
    if (kind === 'error') this.messageNode.classList.add('is-error');
    else if (kind === 'success') this.messageNode.classList.add('is-success');
    else this.messageNode.classList.add('is-info');
  }

  clearMessage() {
    if (!this.messageNode) return;
    this.messageNode.textContent = '';
    this.messageNode.classList.remove('is-error', 'is-success', 'is-info');
  }

  showGeneratedPassword(password, email) {
    if (!this.generatedBlock || !this.generatedValueNode) return;
    const safePassword = (password || '').trim();
    this.generatedValueNode.textContent = safePassword;
    this.generatedBlock.hidden = safePassword.length === 0;
    if (safePassword.length) {
      this.generatedBlock.setAttribute('data-email', email || '');
    }
  }

  clearGeneratedPassword() {
    if (this.generatedBlock) {
      this.generatedBlock.hidden = true;
      this.generatedBlock.removeAttribute('data-email');
    }
    if (this.generatedValueNode) {
      this.generatedValueNode.textContent = '';
    }
  }

  async submitAllowlist({ email, role, note, password, generatePassword }) {
    this.setLoading(true);
    try {
      const response = await api.authAdminUpsertAllowlist({ email, role, note, password, generatePassword });
      const entry = response?.entry;
      if (generatePassword && response?.clear_password) {
        this.showGeneratedPassword(response.clear_password, email);
        this.notify('success', t('admin.message_generated'));
      } else {
        this.clearGeneratedPassword();
        this.notify('success', t('admin.message_saved'));
      }
      if (this.passwordInput) {
        this.passwordInput.value = '';
      }
      if (entry?.email && this.emailInput) {
        this.emailInput.value = entry.email;
      }
      if (entry?.note !== undefined && this.noteInput) {
        this.noteInput.value = entry.note || '';
      }
      if (entry?.role && this.roleSelect) {
        this.roleSelect.value = entry.role;
      }
      await this.loadAllowlist({ page: 1 });
    } catch (error) {
      console.error('[AuthAdmin] upsert failed', error);
      this.notify('error', t('admin.message_error'));
    } finally {
      this.setLoading(false);
    }
  }

  async loadAllowlist({ page } = {}) {
    if (!this.tableBody) return;
    if (Number.isFinite(page)) {
      this.page = Math.max(1, Number(page));
    }
    const currentStatus = this.status || 'active';
    const trimmedQuery = (this.query || '').trim();
    this.tableBody.innerHTML = `<tr><td colspan="6">${t('admin.table_loading') || 'Chargement...'}</td></tr>`;
    try {
      const data = await api.authAdminListAllowlist({
        status: currentStatus,
        query: trimmedQuery,
        page: this.page,
        pageSize: this.pageSize,
      });
      const items = Array.isArray(data?.items) ? data.items : [];
      this.total = Number.isFinite(data?.total) ? Number(data.total) : items.length;
      this.page = Number.isFinite(data?.page) ? Number(data.page) : this.page;
      this.pageSize = Number.isFinite(data?.page_size) ? Number(data.page_size) : this.pageSize;
      this.status = typeof data?.status === 'string' ? data.status : currentStatus;
      if (this.statusSelect && this.statusSelect.value !== this.status) {
        this.statusSelect.value = this.status;
      }
      this.query = typeof data?.query === 'string' ? data.query : trimmedQuery;
      if (this.searchInput && this.searchInput.value !== this.query) {
        this.searchInput.value = this.query;
      }
      this.hasMore = Boolean(data?.has_more);
      this.totalPages = Math.max(1, Math.ceil(this.total / this.pageSize));
      this.updateAllowlistTable(items);
      this.updateSummary();
      if (!items.length) {
        this.tableBody.innerHTML = `<tr><td colspan="6">${t('admin.table_empty') || 'Aucune entrée'}</td></tr>`;
      }
    } catch (error) {
      console.error('[AuthAdmin] list allowlist failed', error);
      this.tableBody.innerHTML = `<tr><td colspan="6">${t('admin.table_empty') || 'Aucune entrée'}</td></tr>`;
      this.notify('error', t('admin.message_error'));
    }
  }

  updateSummary() {
    if (!this.summaryNode) return;
    const entriesLabel = t('admin.summary_entries') || 'entrées';
    const statusLabel = this.status === 'revoked'
      ? (t('admin.status_revoked') || 'Révoquées')
      : this.status === 'all'
        ? (t('admin.status_all') || 'Toutes')
        : (t('admin.status_active') || 'Actives');
    const pageWord = t('admin.pagination_page') || 'Page';
    const separatorWord = t('admin.pagination_separator') || 'sur';
    const trimmedQuery = (this.query || '').trim();
    const pieces = [`${this.total} ${entriesLabel}`, statusLabel];
    if (trimmedQuery) pieces.push(`"${trimmedQuery}"`);
    this.summaryNode.textContent = pieces.join(' • ');
    if (this.paginationInfo) {
      this.paginationInfo.textContent = `${pageWord} ${this.page} ${separatorWord} ${this.totalPages}`;
    }
    if (this.prevPageButton) {
      this.prevPageButton.disabled = this.page <= 1;
    }
    if (this.nextPageButton) {
      this.nextPageButton.disabled = this.page >= this.totalPages;
    }
  }

  updateAllowlistTable(items) {
    if (!this.tableBody) return;
    if (!Array.isArray(items) || !items.length) {
      this.tableBody.innerHTML = `<tr><td colspan="6">${t('admin.table_empty') || 'Aucune entrée'}</td></tr>`;
      return;
    }
    const actionLabel = t('admin.action_generate');
    const neverLabel = t('admin.never') || 'Jamais';
    const activeLabel = t('admin.status_active') || 'Actives';
    const revokedLabel = t('admin.status_revoked') || 'Révoquées';
    const rows = items.map((item) => {
      const emailRaw = item?.email || '';
      const roleRaw = item?.role || 'member';
      const noteRaw = item?.note || '';
      const passwordUpdated = formatDateTime(item?.password_updated_at);
      const isRevoked = Boolean(item?.revoked_at);
      const email = escapeHtml(emailRaw);
      const role = escapeHtml(roleRaw);
      const note = noteRaw ? escapeHtml(noteRaw) : `<span class="auth-admin__muted">—</span>`;
      const statusBadgeLabel = escapeHtml(isRevoked ? revokedLabel : activeLabel);
      const statusBadgeClass = isRevoked
        ? 'auth-admin__status-badge auth-admin__status-badge--revoked'
        : 'auth-admin__status-badge auth-admin__status-badge--active';
      const passwordCell = passwordUpdated === '-' ? neverLabel : passwordUpdated;
      const rowClass = isRevoked ? 'auth-admin__row auth-admin__row--revoked' : 'auth-admin__row';
      const encodedNote = encodeNote(noteRaw);
      const safeRoleAttr = encodeURIComponent(roleRaw);
      return `
        <tr class="${rowClass}">
          <td>${email}</td>
          <td>${role}</td>
          <td>${note}</td>
          <td><span class="${statusBadgeClass}">${statusBadgeLabel}</span></td>
          <td>${passwordCell}</td>
          <td>
            <button type="button" data-action="generate" data-email="${escapeHtml(emailRaw)}" data-role-value="${safeRoleAttr}" data-note="${encodedNote}" class="auth-admin__button">${escapeHtml(actionLabel)}</button>
          </td>
        </tr>
      `;
    }).join('');
    this.tableBody.innerHTML = rows;
  }

  async copyToClipboard(value) {
    const text = (value || '').trim();
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
      this.notify('success', t('admin.copied'));
    } catch (error) {
      console.warn('[AuthAdmin] clipboard error', error);
      this.notify('error', t('admin.message_error'));
    }
  }
}

export default AuthAdminModule;

