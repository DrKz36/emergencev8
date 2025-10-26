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
 * - beta-3.1.3 : Métrique nDCG@k temporelle (benchmarking fraîcheur/entropie) [ACTUEL]
 * - beta-3.1.3 : Chat mobile composer guard (offset bottom nav) [ACTUEL]
 * - beta-3.1.2 : Refactor docs inter-agents (fichiers séparés - zéro conflit merge)
 * - beta-3.1.1 : Dialogue - Modal reprise multi-conversations
 * - beta-3.1.0 : Webhooks + Health Check Scripts + Qualité (mypy 100%)
 */

export const VERSION = 'beta-3.1.3';
export const VERSION_NAME = 'Temporal nDCG Metric + Chat Composer Guard';
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
    version: 'beta-3.1.3',
    date: '2025-10-26',
    changes: [
      { type: 'feature', text: 'Métrique nDCG@k temporelle - Évalue qualité ranking avec pénalisation fraîcheur exponentielle' },
      { type: 'feature', text: 'Endpoint POST /api/benchmarks/metrics/ndcg-temporal - Calcul métrique à la demande' },
      { type: 'quality', text: 'BenchmarksService.calculate_temporal_ndcg() - Méthode helper pour intégrations futures' },
      { type: 'quality', text: 'Tests complets (18 tests) - Cas edge, décroissance temporelle, trade-offs, validation params' },
      { type: 'quality', text: 'Documentation formule DCG temporelle - Mesure impact boosts fraîcheur/entropie moteur ranking' },
      { type: 'fix', text: 'Dialogue mobile – Le composer reste accessible en mode portrait (offset bottom nav + sticky guard)' },
      { type: 'quality', text: 'Messages mobile – Padding dynamique pour éviter les zones mortes sous la barre de navigation' }
    ]
  },
  {
    version: 'beta-3.1.2',
    date: '2025-10-26',
    changes: [
      { type: 'quality', text: 'Refactor complet docs inter-agents - Fichiers séparés par agent (AGENT_SYNC_CLAUDE.md / AGENT_SYNC_CODEX.md)' },
      { type: 'quality', text: 'Nouvelle structure passation - Journaux séparés (passation_claude.md / passation_codex.md) avec rotation 48h stricte' },
      { type: 'quality', text: 'SYNC_STATUS.md - Vue d\'ensemble centralisée des activités multi-agents' },
      { type: 'quality', text: 'Résultat : Zéro conflit merge sur docs de sync, meilleure coordination agents' },
      { type: 'quality', text: 'Mise à jour prompts agents (CLAUDE.md, CODEV_PROTOCOL.md, CODEX_GPT_GUIDE.md)' }
    ]
  },
  {
    version: 'beta-3.1.1',
    date: '2025-10-26',
    changes: [
      { type: 'fix', text: 'Module Dialogue - L\'option "Reprendre" réapparaît dès que des conversations existent (attente bootstrap threads)' },
      { type: 'quality', text: 'Modal d\'accueil dynamique selon la disponibilité des conversations (mise à jour live du contenu)' }
    ]
  },
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
