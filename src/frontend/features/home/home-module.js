/**
 * @module features/home/home-module
 * @description Landing page pour l’authentification par email (allowlist).
 */

import { EVENTS } from '../../shared/constants.js';
import { t } from '../../shared/i18n.js';
import { api } from '../../shared/api-client.js';

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function getEmailDomain(email) {
  if (!email || typeof email !== 'string') return null;
  const parts = email.split('@');
  return parts.length === 2 ? parts[1].toLowerCase() : null;
}

function buildMeta() {
  try {
    const navigatorData = typeof navigator !== 'undefined' ? navigator : {};
    const locale = navigatorData.language || (Array.isArray(navigatorData.languages) ? navigatorData.languages[0] : null);
    return {
      locale: locale || 'fr',
      user_agent: navigatorData.userAgent || 'unknown',
      platform: navigatorData.platform || 'unknown',
      timezone: Intl?.DateTimeFormat?.().resolvedOptions?.().timeZone || 'UTC',
    };
  } catch (_) {
    return { locale: 'fr', user_agent: 'unknown' };
  }
}

export class HomeModule {
  constructor(eventBus, stateManager, options = {}) {
    this.eventBus = eventBus;
    this.state = stateManager;
    this.qaRecorder = options.qaRecorder || null;

    this.container = null;
    this.root = null;
    this.form = null;
    this.emailInput = null;
    this.messageNode = null;
    this.submitButton = null;
    this.status = 'idle';
    this.pendingController = null;

    this.handleSubmit = this.handleSubmit.bind(this);
    this.handleInput = this.handleInput.bind(this);
  }

  mount(container) {
    if (!container || this.root) return;
    this.container = container;
    container.innerHTML = this.render();
    container.removeAttribute('hidden');
    container.setAttribute('aria-hidden', 'false');

    this.root = container.querySelector('[data-role="home"]');
    this.form = container.querySelector('[data-role="home-form"]');
    this.emailInput = container.querySelector('[data-role="home-email"]');
    this.passwordInput = container.querySelector('[data-role="home-password"]');
    this.messageNode = container.querySelector('[data-role="home-message"]');
    this.submitButton = container.querySelector('[data-role="home-submit"]');

    if (this.form) {
      this.form.addEventListener('submit', this.handleSubmit);
    }
    if (this.emailInput) {
      this.emailInput.addEventListener('input', this.handleInput);
      setTimeout(() => {
        try { this.emailInput.focus(); } catch (_) {}
      }, 25);
    }
    if (this.passwordInput) {
      this.passwordInput.addEventListener('input', this.handleInput);
    }
  }

  unmount() {
    if (!this.container) return;
    if (this.form) this.form.removeEventListener('submit', this.handleSubmit);
    if (this.emailInput) this.emailInput.removeEventListener('input', this.handleInput);
    if (this.passwordInput) this.passwordInput.removeEventListener('input', this.handleInput);
    this.abortPending();

    this.container.setAttribute('hidden', 'true');
    this.container.setAttribute('aria-hidden', 'true');
    this.container.innerHTML = '';

    this.root = null;
    this.form = null;
    this.emailInput = null;
    this.passwordInput = null;
    this.messageNode = null;
    this.submitButton = null;
    this.status = 'idle';
  }

  render() {
    const title = t('home.title');
    const subtitle = t('home.subtitle');
    const emailLabel = t('home.email_label');
    const emailPlaceholder = t('home.email_placeholder');
    const passwordLabel = t('home.password_label');
    const passwordPlaceholder = t('home.password_placeholder');
    const submit = t('home.submit');
    const legal = t('home.legal');
    const highlights = t('home.highlights');
    const brandAlt = t('home.brand_alt');
    const agentsTitle = t('home.agents_title');
    const agentsSubtitle = t('home.agents_subtitle');
    const agentAnima = t('home.agent_anima');
    const agentNeo = t('home.agent_neo');
    const agentNexus = t('home.agent_nexus');

    return `
      <section class="home" data-role="home">
        <div class="home__panel">
          <div class="home__branding">
            <img src="/assets/emergence_logo.png" alt="${brandAlt}" class="home__logo" loading="lazy" />
          </div>
          <div class="home__hero">
            <span class="home__badge">${highlights}</span>
            <h1 class="home__title">${title}</h1>
            <p class="home__subtitle">${subtitle}</p>
          </div>
          <section class="home__agents" aria-labelledby="home-agents-title">
            <header class="home__agents-header">
              <h2 id="home-agents-title" class="home__agents-title">${agentsTitle}</h2>
              <p class="home__agents-subtitle">${agentsSubtitle}</p>
            </header>
            <div class="home__agents-grid">
              <figure class="home__agent-card">
                <img src="/assets/anima.png" alt="${agentAnima}" loading="lazy" class="home__agent-image" />
                <figcaption class="home__agent-label">${agentAnima}</figcaption>
              </figure>
              <figure class="home__agent-card">
                <img src="/assets/neo.png" alt="${agentNeo}" loading="lazy" class="home__agent-image" />
                <figcaption class="home__agent-label">${agentNeo}</figcaption>
              </figure>
              <figure class="home__agent-card">
                <img src="/assets/nexus.png" alt="${agentNexus}" loading="lazy" class="home__agent-image" />
                <figcaption class="home__agent-label">${agentNexus}</figcaption>
              </figure>
            </div>
          </section>
          <form class="home__form" data-role="home-form" novalidate>
            <label class="home__label" for="home-email">${emailLabel}</label>
            <div class="home__form-row">
              <input id="home-email" name="email" type="email" autocomplete="email" required placeholder="${emailPlaceholder}" class="home__input" data-role="home-email" />
            </div>
            <label class="home__label" for="home-password">${passwordLabel}</label>
            <div class="home__form-row">
              <input id="home-password" name="password" type="password" autocomplete="current-password" required minlength="8" placeholder="${passwordPlaceholder}" class="home__input" data-role="home-password" />
            </div>
            <div class="home__form-row">
              <button type="submit" class="btn btn--primary home__submit" data-role="home-submit">${submit}</button>
            </div>
            <p class="home__message" data-role="home-message" aria-live="assertive"></p>
          </form>
          <p class="home__legal">${legal}</p>
        </div>
      </section>`;
  }

  handleInput() {
    if (this.status === 'error') {
      this.clearMessage();
      this.status = 'idle';
    }
  }

  async handleSubmit(event) {
    event.preventDefault();
    if (!this.emailInput) return;

    const rawEmail = this.emailInput.value || '';
    const email = rawEmail.trim().toLowerCase();
    const passwordValue = this.passwordInput ? (this.passwordInput.value || '') : '';
    const password = passwordValue;

    if (!EMAIL_REGEX.test(email)) {
      this.showMessage('error', t('home.error_invalid'));
      this.status = 'error';
      try { this.emailInput.focus(); } catch (_) {}
      return;
    }

    if (!password || password.length < 8) {
      this.showMessage('error', t('home.error_password_short'));
      this.status = 'error';
      if (this.passwordInput) {
        try { this.passwordInput.focus(); } catch (_) {}
      }
      return;
    }

    this.setLoading(true);
    this.showMessage('info', t('home.pending'));
    this.status = 'pending';

    this.eventBus.emit?.(EVENTS.AUTH_LOGIN_SUBMIT, { email });
    if (this.qaRecorder) {
      this.qaRecorder.record('home_login_submit', {
        email_domain: getEmailDomain(email),
        source: 'home-module',
      });
    }

    try {
      const data = await this.login(email, password);
      this.status = 'success';
      this.showMessage('success', t('home.success'));

      if (this.qaRecorder) {
        this.qaRecorder.record('home_login_success', {
          email_domain: getEmailDomain(email),
          session_id: data?.session_id ?? data?.sessionId ?? null,
          role: data?.role ?? null,
        });
      }

      this.eventBus.emit?.(EVENTS.AUTH_LOGIN_SUCCESS, {
        email,
        token: data?.token ?? null,
        sessionId: data?.session_id ?? data?.sessionId ?? null,
        role: data?.role ?? null,
        expiresAt: data?.expires_at ?? data?.expiresAt ?? null,
        response: data,
      });
    } catch (error) {
      const status = error?.status ?? null;
      let message = t('home.error_generic');
      if (status === 401) {
        const detail = String(error?.message || '').toLowerCase();
        if (detail.includes('identifiant')) message = t('home.error_password_invalid');
        else message = t('home.error_unauthorized');
      } else if (status === 429) message = t('home.error_rate');
      else if (status === 423) message = t('home.error_locked');

      this.status = 'error';
      this.showMessage('error', message);

      if (this.qaRecorder) {
        this.qaRecorder.record('home_login_error', {
          email_domain: getEmailDomain(email),
          status,
          message,
        });
      }

      this.eventBus.emit?.(EVENTS.AUTH_LOGIN_ERROR, {
        email,
        status,
        error,
      });
    } finally {
      this.setLoading(false);
    }
  }

  async login(email, password) {
    this.abortPending();
    this.pendingController = typeof AbortController !== 'undefined' ? new AbortController() : null;

    const meta = buildMeta();
    if (meta && typeof meta === 'object') {
      meta.email_domain = getEmailDomain(email);
      meta.source = 'home-module';
    }
    let data;

    try {
      data = await api.authLogin({
        email,
        password,
        meta,
        signal: this.pendingController ? this.pendingController.signal : undefined,
      });
    } catch (error) {
      if (error?.name === 'AbortError') {
        const abortErr = new Error('Connexion annulee');
        abortErr.status = 499;
        throw abortErr;
      }
      throw error;
    }

    if (!data || typeof data !== 'object' || !data.token) {
      const err = new Error('Login succeeded without token');
      err.status = 500;
      err.body = data;
      throw err;
    }

    return data;
  }


  abortPending() {
    if (this.pendingController) {
      try { this.pendingController.abort(); }
      catch (_) {}
    }
    this.pendingController = null;
  }

  setLoading(isLoading) {
    if (this.submitButton) {
      this.submitButton.disabled = !!isLoading;
      this.submitButton.setAttribute('aria-busy', isLoading ? 'true' : 'false');
    }
    if (this.emailInput) {
      this.emailInput.disabled = !!isLoading;
    }
    if (this.passwordInput) {
      this.passwordInput.disabled = !!isLoading;
    }
  }

  showMessage(kind, message) {
    if (!this.messageNode) return;
    const text = (typeof message === 'string') ? message.trim() : '';
    this.messageNode.textContent = text;
    this.messageNode.classList.remove('is-error', 'is-success', 'is-info');
    if (kind === 'error') this.messageNode.classList.add('is-error');
    else if (kind === 'success') this.messageNode.classList.add('is-success');
    else this.messageNode.classList.add('is-info');
  }

  clearMessage() {
    if (!this.messageNode) return;
    this.messageNode.textContent = '';
    this.messageNode.classList.remove('is-error', 'is-success', 'is-info');
  }
}
