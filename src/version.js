/**
 * ÉMERGENCE V8 - Version centralisée
 *
 * Ce fichier est la source unique de vérité pour le versioning de l'application.
 * Toutes les références de version doivent importer depuis ce fichier.
 *
 * Versioning sémantique : beta-MAJOR.MINOR.PATCH
 * - MAJOR : Phase complète (P0 = 1, P1 = 2, P2 = 3, etc.)
 * - MINOR : Fonctionnalité complétée dans la phase
 * - PATCH : Bugfixes et hotfixes
 *
 * Historique :
 * - beta-1.0.0 : Phase P0 complétée (Quick Wins - 3/3)
 * - beta-1.1.0 : Phase P1 complétée (UX Essentielle - 3/3) [ACTUEL]
 */

export const VERSION = 'beta-1.1.0';
export const VERSION_NAME = 'Phase P1 - UX Essentielle';
export const VERSION_DATE = '2025-10-16';
export const BUILD_PHASE = 'P1';
export const COMPLETION_PERCENTAGE = 61; // 14/23 features

export default {
  version: VERSION,
  versionName: VERSION_NAME,
  versionDate: VERSION_DATE,
  buildPhase: BUILD_PHASE,
  completionPercentage: COMPLETION_PERCENTAGE,

  // Detailed phase breakdown
  phases: {
    P0: { status: 'completed', features: 3, completion: 100 },
    P1: { status: 'completed', features: 3, completion: 100 },
    P2: { status: 'pending', features: 6, completion: 0 },
    P3: { status: 'pending', features: 4, completion: 0 },
    P4: { status: 'pending', features: 7, completion: 0 },
  },

  // Display helpers
  get fullVersion() {
    return `${VERSION} - ${VERSION_NAME}`;
  },

  get shortVersion() {
    return VERSION;
  },

  get displayVersion() {
    return VERSION.replace('beta-', 'β');
  }
};
