/**
 * @file /src/frontend/shared/i18n.js
 * @description Helpers de localisation très légers utilisés côté front.
 */

const MESSAGES = {
  fr: {
    auth: {
      login_required: 'Connexion requise',
      session_expired: 'Session expirée',
      login_hint: 'Veuillez vous reconnecter pour poursuivre la conversation.',
      login_action: 'Se connecter',
    },
    errors: {
      generic: 'Une erreur est survenue.',
    },
  },
  en: {
    auth: {
      login_required: 'Sign-in required',
      session_expired: 'Session expired',
      login_hint: 'Please sign in again to continue the conversation.',
      login_action: 'Sign in',
    },
    errors: {
      generic: 'Something went wrong.',
    },
  },
};

const DEFAULT_LOCALE = 'fr';

function detectLocale() {
  const nav = typeof navigator !== 'undefined' ? navigator : null;
  const lang = nav?.language || (Array.isArray(nav?.languages) ? nav.languages[0] : null);
  if (!lang) return DEFAULT_LOCALE;
  const short = lang.toLowerCase().split('-')[0];
  return MESSAGES[short] ? short : DEFAULT_LOCALE;
}

function getMessage(dict, path) {
  if (!dict) return undefined;
  return path.split('.').reduce((acc, part) => {
    if (acc && typeof acc === 'object' && part in acc) return acc[part];
    return undefined;
  }, dict);
}

export function t(path, { locale, fallbackLocale } = {}) {
  if (!path || typeof path !== 'string') return '';
  const primary = locale && MESSAGES[locale] ? locale : detectLocale();
  const fallback = fallbackLocale && MESSAGES[fallbackLocale] ? fallbackLocale : DEFAULT_LOCALE;
  return (
    getMessage(MESSAGES[primary], path)
    ?? getMessage(MESSAGES[fallback], path)
    ?? path
  );
}

export function getMessages() {
  return MESSAGES;
}

export const LOCALES = Object.freeze(Object.keys(MESSAGES));
