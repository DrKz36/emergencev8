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
 * - beta-2.0.0 : Phase P1 complétée (UX Essentielle - 3/3)
 * - beta-2.1.0 : Phase 1 & 3 Debug (Backend fixes + UI/UX improvements)
 * - beta-2.1.1 : Audit système multi-agents + versioning unifié
 * - beta-2.1.2 : Guardian automation + pre-deployment validation
 * - beta-2.1.3 : Guardian email reports automation
 * - beta-2.1.4 : Fix 404 production (reset-password, favicon)
 * - beta-2.1.5 : Fix responsive mobile admin dashboard
 * - beta-2.2.0 : Mypy 100% clean (0 errors) + monitoring router fix
 * - beta-3.0.0 : Phase P2 complétée (Admin & Sécurité - 3/3) [ACTUEL]
 */

export const VERSION = 'beta-3.0.0';
export const VERSION_NAME = 'Admin & Sécurité (P2 Complétée)';
export const VERSION_DATE = '2025-10-22';
export const BUILD_PHASE = 'P2';
export const COMPLETION_PERCENTAGE = 74; // 17/23 features
export const TOTAL_FEATURES = 23;

export default {
  version: VERSION,
  versionName: VERSION_NAME,
  versionDate: VERSION_DATE,
  buildPhase: BUILD_PHASE,
  completionPercentage: COMPLETION_PERCENTAGE,
  totalFeatures: TOTAL_FEATURES,

  // Detailed phase breakdown
  phases: {
    P0: { status: 'completed', features: 3, completion: 100 },
    P1: { status: 'completed', features: 3, completion: 100 },
    P2: { status: 'completed', features: 3, completion: 100 },
    P3: { status: 'pending', features: 4, completion: 0 },
    P4: { status: 'pending', features: 10, completion: 0 },
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
  },

  // Feature count helpers
  get completedFeatures() {
    return Object.values(this.phases)
      .filter(phase => phase.status === 'completed')
      .reduce((sum, phase) => sum + phase.features, 0);
  },

  get featuresDisplay() {
    return `${this.completedFeatures}/${this.totalFeatures}`;
  }
};
