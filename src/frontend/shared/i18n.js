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
    home: {
      title: 'ÉMERGENCE V8',
      subtitle: 'La plateforme multi-agents pour orchestrer vos conversations, débats et mémoires IA.',
      highlights: 'Multi-agents - Mémoire - RAG temps réel',
      email_label: 'Adresse email professionnelle',
      email_placeholder: 'prenom@entreprise.com',
      submit: 'Recevoir l’accès',
      pending: 'Connexion en cours...',
      success: 'Connexion réussie. Préparation de votre session...',
      error_invalid: 'Veuillez saisir une adresse email valide.',
      error_unauthorized: 'Adresse non autorisée. Contactez un administrateur.',
      error_rate: 'Trop de tentatives. Réessayez dans quelques minutes.',
      error_locked: 'Session verrouillée. Vérifiez votre boîte mail ou contactez le support.',
      error_generic: 'Connexion impossible pour le moment. Réessayez plus tard.',
      legal: 'Accès réservé aux comptes autorisés. Chaque demande est journalisée (IP, user-agent) pour la traçabilité.',
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
    home: {
      title: 'EMERGENCE V8',
      subtitle: 'The multi-agent workspace for conversations, debates and memory workflows.',
      highlights: 'Multi-agent - Memory - Real-time RAG',
      email_label: 'Work email address',
      email_placeholder: 'firstname@company.com',
      submit: 'Request access',
      pending: 'Signing you in...',
      success: 'Signed in successfully. Preparing your workspace...',
      error_invalid: 'Please enter a valid email address.',
      error_unauthorized: 'Email not allowed. Contact an administrator.',
      error_rate: 'Too many attempts. Try again in a few minutes.',
      error_locked: 'Session locked. Check your inbox or contact support.',
      error_generic: 'Unable to sign in right now. Please try again later.',
      legal: 'Access is restricted to allowlisted accounts. Each request is logged (IP, user agent) for auditing.',
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
