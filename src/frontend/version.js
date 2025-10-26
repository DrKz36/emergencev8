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
 * - beta-3.0.0 : Phase P2 complétée (Admin & Sécurité - 3/3)
 * - beta-3.1.0 : Webhooks + Health Check Scripts + Qualité (mypy 100%) [ACTUEL]
 */

export const VERSION = 'beta-3.1.0';
export const VERSION_NAME = 'Webhooks & Scripts Monitoring';
export const VERSION_DATE = '2025-10-26';
export const BUILD_PHASE = 'P3';
export const COMPLETION_PERCENTAGE = 78; // 18/23 features (P3.11 webhooks complété)
export const TOTAL_FEATURES = 23;

/**
 * Patch notes pour la version actuelle
 * Affichées dans le module "À propos" des paramètres
 */
export const PATCH_NOTES = [
  {
    version: 'beta-3.1.0',
    date: '2025-10-26',
    changes: [
      { type: 'feature', text: 'Système de webhooks complet (P3.11) - Intégrations externes avec retry automatique' },
      { type: 'feature', text: 'Scripts de monitoring production (health check avec JWT auth)' },
      { type: 'quality', text: 'Mypy 100% clean - 471 erreurs corrigées (0 erreurs restantes)' },
      { type: 'fix', text: 'Cockpit - 3 bugs SQL critiques résolus (graphiques distribution)' },
      { type: 'fix', text: 'Module Documents - Layout desktop/mobile corrigé' },
      { type: 'fix', text: 'Module Chat - 4 bugs UI/UX critiques résolus (modal, scroll, routing)' },
      { type: 'perf', text: 'Bundle optimization - Lazy loading Chart.js, jsPDF, PapaParse' },
      { type: 'fix', text: 'Tests - 5 flaky tests corrigés (ChromaDB Windows + mocks RAG)' }
    ]
  },
  {
    version: 'beta-3.0.0',
    date: '2025-10-22',
    changes: [
      { type: 'phase', text: 'Phase P2 complétée - Admin & Sécurité (3/3 features)' },
      { type: 'feature', text: 'Système de permissions avancé' },
      { type: 'feature', text: 'Audit logs et traçabilité' }
    ]
  }
];

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
    P3: { status: 'in_progress', features: 4, completion: 25 }, // P3.11 webhooks done
    P4: { status: 'pending', features: 10, completion: 0 },
  },

  // Patch notes (newest first)
  patchNotes: PATCH_NOTES,

  /**
   * Get patch notes for current version
   * @returns {Object|null} Current version patch notes
   */
  getCurrentPatchNotes() {
    return this.patchNotes.find(note => note.version === VERSION) || null;
  },

  /**
   * Get patch notes formatted for display
   * @param {number} limit - Maximum number of versions to show
   * @returns {Array} Formatted patch notes
   */
  getFormattedPatchNotes(limit = 2) {
    return this.patchNotes.slice(0, limit);
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
