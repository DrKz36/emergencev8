/**
 * @module core/utils
 * @description Fonctions utilitaires pour l'application. V15.1
 * - loadCSS: calcule l'URL absolue à partir de import.meta.url (robuste)
 * - Log onload/onerror pour debug immédiat
 */
export function loadCSS(path) {
  if (!path || typeof path !== 'string') return;

  // Base = ce module: .../src/frontend/core/utils.js
  const base = new URL(import.meta.url);
  // On remonte d'un dossier ("core/") vers "frontend/" puis on applique "path"
  const fullURL = new URL('../' + path.replace(/^\/+/, ''), base); // -> /src/frontend/...
  const href = fullURL.pathname;

  // Dé-duplication via ID stable
  const id = 'css_' + href.replace(/[^a-z0-9_-]/gi, '_');
  if (document.getElementById(id)) return;

  const link = document.createElement('link');
  link.id = id;
  link.rel = 'stylesheet';
  link.href = href;

  link.onload = () => console.debug('[CSS] ok:', href);
  link.onerror = () => console.error('[CSS] fail:', href);

  document.head.appendChild(link);
}
