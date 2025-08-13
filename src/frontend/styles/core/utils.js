/**
 * @module core/utils
 * @description Fonctions utilitaires pour l'application.
 */

/**
 * Charge dynamiquement une feuille de style CSS dans le <head> du document.
 * Empêche le chargement de doublons.
 * @param {string} path - Le chemin vers le fichier CSS depuis la racine du frontend.
 */
export function loadCSS(path) {
    const fullPath = `/src/frontend/${path}`;
    if (document.querySelector(`link[href="${fullPath}"]`)) {
        // Le style est déjà chargé, on ne fait rien.
        return;
    }
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = fullPath;
    document.head.appendChild(link);
}
