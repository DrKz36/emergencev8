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
      password_label: 'Mot de passe',
      password_placeholder: 'Mot de passe (8 caracteres minimum)',
      submit: 'Recevoir l’accès',
      pending: 'Connexion en cours...',
      success: 'Connexion réussie. Préparation de votre session...',
      error_invalid: 'Veuillez saisir une adresse email valide.',
      error_unauthorized: 'Adresse non autorisée. Contactez un administrateur.',
      error_rate: 'Trop de tentatives. Réessayez dans quelques minutes.',
      error_locked: 'Session verrouillée. Vérifiez votre boîte mail ou contactez le support.',
      error_generic: 'Connexion impossible pour le moment. Reessayez plus tard.',
      error_password_short: 'Mot de passe trop court (8 caracteres minimum).',
      error_password_invalid: 'Mot de passe invalide. Verifiez vos identifiants.',
      legal: 'Accès réservé aux comptes autorisés. Chaque demande est journalisée (IP, user-agent) pour la traçabilité.',
      brand_alt: 'Logo EMERGENCE',
      agents_title: 'Vos copilotes IA',
      agents_subtitle: 'Anima, Neo et Nexus orchestrent vos conversations, débats et mémoires en tandem.',
      agent_anima: 'Anima',
      agent_neo: 'Neo',
      agent_nexus: 'Nexus',
    admin: {
      title: 'Administration allowlist',
      subtitle: 'Ajoutez, mettez a jour ou regenerez les acces testeurs.',
      email_label: 'Adresse email',
      role_label: 'Role',
      role_member: 'Membre',
      role_admin: 'Admin',
      note_label: 'Note (optionnelle)',
      password_label: 'Mot de passe (facultatif)',
      password_placeholder: 'Laissez vide pour conserver le mot de passe actuel',
      submit: 'Enregistrer',
      generate: 'Generer un mot de passe',
      include_revoked: 'Afficher les comptes revoques',
      table_email: 'Email',
      table_role: 'Role',
      table_note: 'Note',
      table_password_updated: 'Mot de passe mis a jour',
      table_actions: 'Actions',
      action_generate: 'Generer',
      message_saved: 'Entree mise a jour.',
      message_generated: 'Nouveau mot de passe genere.',
      message_error: "Impossible de mettre a jour l'allowlist.",
      generated_password_label: 'Mot de passe genere',
      copy: 'Copier',
      copied: 'Copie dans le presse-papiers.',
      search_label: 'Recherche',
      search_placeholder: 'Email ou note',
      status_filter_label: 'Statut',
      status_active: 'Actives',
      status_all: 'Toutes',
      status_revoked: 'Revoquees',
      table_status: 'Statut',
      table_loading: 'Chargement...',
      table_empty: 'Aucune entree',
      summary_entries: 'entrees',
      pagination_page: 'Page',
      pagination_separator: 'sur',
      prev_page: 'Precedent',
      next_page: 'Suivant',
      never: 'Jamais',
    },
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
      password_label: 'Password',
      password_placeholder: 'Password (min. 8 characters)',
      submit: 'Request access',
      pending: 'Signing you in...',
      success: 'Signed in successfully. Preparing your workspace...',
      error_invalid: 'Please enter a valid email address.',
      error_unauthorized: 'Email not allowed. Contact an administrator.',
      error_rate: 'Too many attempts. Try again in a few minutes.',
      error_locked: 'Session locked. Check your inbox or contact support.',
      message_error: "Failed to update the allowlist.",
      error_password_short: 'Password must be at least 8 characters long.',
      error_password_invalid: 'Invalid password. Please try again.',
      legal: 'Access is restricted to allowlisted accounts. Each request is logged (IP, user agent) for auditing.',
      brand_alt: 'EMERGENCE logo',
      agents_title: 'Your AI copilots',
      agents_subtitle: 'Anima, Neo and Nexus keep your conversations, debates and memory flows in sync.',
      agent_anima: 'Anima',
      agent_neo: 'Neo',
      agent_nexus: 'Nexus',
    },
    admin: {
      title: 'Allowlist administration',
      subtitle: 'Add or update authorized accounts and regenerate passwords.',
      email_label: 'Email address',
      role_label: 'Role',
      role_member: 'Member',
      role_admin: 'Admin',
      note_label: 'Note (optional)',
      password_label: 'Password (optional)',
      password_placeholder: 'Leave blank to keep the current password',
      submit: 'Save entry',
      generate: 'Generate password',
      include_revoked: 'Show revoked entries',
      table_email: 'Email',
      table_role: 'Role',
      table_note: 'Note',
      table_password_updated: 'Password updated',
      table_actions: 'Actions',
      action_generate: 'Generate',
      message_saved: 'Allowlist entry updated.',
      message_generated: 'Generated a new password.',
      message_error: "Failed to update the allowlist.",
      generated_password_label: 'Generated password',
      copy: 'Copy',
      copied: 'Copied to clipboard.',
      search_label: 'Search',
      search_placeholder: 'Email or note',
      status_filter_label: 'Status',
      status_active: 'Active',
      status_all: 'All',
      status_revoked: 'Revoked',
      table_status: 'Status',
      table_loading: 'Loading...',
      table_empty: 'No entries',
      summary_entries: 'entries',
      pagination_page: 'Page',
      pagination_separator: 'of',
      prev_page: 'Previous',
      next_page: 'Next',
      never: 'Never',
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




