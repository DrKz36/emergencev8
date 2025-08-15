/**
 * @module core/utils
 * @description Utilitaires Front — V16.0 (ARBO‑LOCK safe)
 * - loadCSS(path): construit une URL ABSOLUE à partir de ce module (…/src/frontend/core/utils.js)
 *   et tente automatiquement des FALLBACKS si 404 ( /src/frontend → /src ).
 * - Déduplication par id stable pour éviter le double chargement.
 * - Logs explicites pour le debug Cloud Run.
 */
export function loadCSS(path) {
  try {
    if (typeof path !== 'string' || !path.trim()) return;

    // Normalise le chemin fourni par l'appelant (ex: "features/debate/debate.css")
    const normPath = path.replace(/^\/+/, ''); // jamais de leading '/'

    // Base = ce module: .../src/frontend/core/utils.js
    const base = new URL(import.meta.url);

    // Cible prioritaire (canonique): /src/frontend/<normPath>
    const hrefPrimary = new URL('../' + normPath, base).pathname;

    // Fallback #1 : /src/<normPath> (certains déploiements ne publient pas "frontend/")
    const hrefFallback = new URL('../../' + normPath, base).pathname;

    // ID stable pour éviter les doublons
    const id = 'css_' + normPath.replace(/[^a-z0-9_-]/gi, '_');
    if (document.getElementById(id)) return;

    const link = document.createElement('link');
    link.id = id;
    link.rel = 'stylesheet';
    link.href = hrefPrimary;

    let triedFallback = false;

    link.onload = () => {
      console.debug('[CSS] ok:', link.href);
    };

    link.onerror = () => {
      if (!triedFallback && hrefFallback !== link.href) {
        triedFallback = true;
        console.warn('[CSS] fail primary, trying fallback →', hrefFallback);
        link.href = hrefFallback;
      } else {
        console.error('[CSS] fail:', link.href, '(no more fallbacks)');
      }
    };

    document.head.appendChild(link);
  } catch (err) {
    console.error('[CSS] loader exception:', err);
  }
}

/**
 * Charge en séquence une liste de CSS (ordre garanti).
 * Retourne une Promise résolue quand tout est chargé (ou a échoué).
 */
export async function loadCSSBatch(paths = []) {
  for (const p of paths) {
    await new Promise((resolve) => {
      try {
        if (typeof p !== 'string' || !p.trim()) return resolve();
        const norm = p.replace(/^\/+/, '');
        const id = 'css_' + norm.replace(/[^a-z0-9_-]/gi, '_');
        if (document.getElementById(id)) return resolve();

        const base = new URL(import.meta.url);
        const hrefPrimary = new URL('../' + norm, base).pathname;
        const hrefFallback = new URL('../../' + norm, base).pathname;

        const link = document.createElement('link');
        link.id = id;
        link.rel = 'stylesheet';
        link.href = hrefPrimary;

        let triedFallback = false;
        link.onload = () => resolve();
        link.onerror = () => {
          if (!triedFallback && hrefFallback !== link.href) {
            triedFallback = true;
            console.warn('[CSS/batch] fail primary, trying fallback →', hrefFallback);
            link.href = hrefFallback;
          } else {
            console.error('[CSS/batch] fail:', link.href);
            resolve(); // on continue malgré tout
          }
        };

        document.head.appendChild(link);
      } catch {
        resolve();
      }
    });
  }
}
