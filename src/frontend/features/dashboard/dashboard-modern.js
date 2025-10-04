/**
 * @module features/dashboard/dashboard-modern
 * @description Dashboard modernisé avec cartes responsive et effets métalliques
 * Version intégrant les nouveaux composants UI harmonisés
 */

import { DashboardCard } from '../../components/ui/DashboardCard.jsx';
import { Button } from '../../components/ui/Button.jsx';

export class DashboardModern {
  constructor(eventBus, state) {
    this.eventBus = eventBus;
    this.state = state;
    this.container = null;
    this.isInitialized = false;
    console.log('✅ DashboardModern V8 (Harmonisé) prêt.');
  }

  init() {
    if (this.isInitialized) return;
    this.isInitialized = true;
    console.log('✅ DashboardModern V8 initialisé.');
  }

  mount(container) {
    this.container = container;
    this.renderLayout();
    this.loadDashboardData();
  }

  destroy() {
    this.container = null;
  }

  /**
   * Rendu du layout initial
   */
  renderLayout() {
    if (!this.container) return;

    const refreshBtn = Button.primary('Rafraîchir', {
      id: 'refresh-modern-dashboard',
      icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="23 4 23 10 17 10"></polyline>
              <polyline points="1 20 1 14 7 14"></polyline>
              <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
            </svg>`,
      onClick: () => this.loadDashboardData()
    });

    this.container.innerHTML = `
      <div class="dashboard-modern">
        <div class="dashboard-modern__header">
          <h2 class="dashboard-modern__title">Cockpit de Pilotage</h2>
          <div id="refresh-btn-container"></div>
        </div>

        <div id="dashboard-loader" class="dashboard-loader" style="display: none;">
          <div class="loader"></div>
        </div>

        <div id="dashboard-error" class="dashboard-error" style="display: none;"></div>

        <div id="dashboard-content" class="dashboard-modern__content">
          <section class="dashboard-modern__section">
            <h3 class="dashboard-modern__section-title">Suivi des Coûts</h3>
            <div id="costs-grid" class="dashboard-grid"></div>
          </section>

          <section class="dashboard-modern__section">
            <h3 class="dashboard-modern__section-title">Monitoring Système</h3>
            <div id="monitoring-grid" class="dashboard-grid"></div>
          </section>

          <section class="dashboard-modern__section">
            <h3 class="dashboard-modern__section-title">Benchmarks Agentiques</h3>
            <div id="benchmarks-grid" class="dashboard-grid"></div>
          </section>
        </div>
      </div>
    `;

    // Injecter le bouton refresh
    const btnContainer = this.container.querySelector('#refresh-btn-container');
    if (btnContainer) {
      btnContainer.appendChild(refreshBtn);
    }
  }

  /**
   * Affiche/masque le loader
   */
  showLoading(isLoading) {
    const loader = this.container?.querySelector('#dashboard-loader');
    const content = this.container?.querySelector('#dashboard-content');
    if (loader) loader.style.display = isLoading ? 'flex' : 'none';
    if (content) content.style.opacity = isLoading ? '0.5' : '1';
  }

  /**
   * Affiche une erreur
   */
  showError(message) {
    const errorContainer = this.container?.querySelector('#dashboard-error');
    const content = this.container?.querySelector('#dashboard-content');
    if (errorContainer) {
      errorContainer.textContent = message;
      errorContainer.style.display = 'block';
    }
    if (content) content.style.display = 'none';
  }

  /**
   * Charge les données du dashboard
   */
  async loadDashboardData() {
    if (!this.container) return;

    this.showLoading(true);

    try {
      // Simuler un appel API (à remplacer par l'API réelle)
      const data = await this.fetchDashboardData();

      this.renderDashboardData(data);
    } catch (error) {
      console.error('Erreur lors du chargement du dashboard:', error);
      this.showError(`Impossible de charger les données. (${error.message})`);
    } finally {
      this.showLoading(false);
    }
  }

  /**
   * Récupère les données du dashboard (à adapter avec votre API)
   */
  async fetchDashboardData() {
    // Simuler un délai réseau
    await new Promise(resolve => setTimeout(resolve, 500));

    // Données de démo (à remplacer par un vrai appel API)
    return {
      costs: {
        today_cost: 0.45,
        current_week_cost: 2.8,
        current_month_cost: 8.5,
        total_cost: 125.3
      },
      thresholds: {
        daily_threshold: 1.0,
        weekly_threshold: 5.0,
        monthly_threshold: 15.0
      },
      monitoring: {
        total_sessions: 142,
        total_documents: 89,
        active_threads: 12
      },
      benchmarks: [
        { name: 'Anima', score: 85.5, maxScore: 100 },
        { name: 'Neo', score: 92.3, maxScore: 100 },
        { name: 'Nexus', score: 78.9, maxScore: 100 },
        { name: 'Global', score: 88.7, maxScore: 100 }
      ]
    };
  }

  /**
   * Rendu des données du dashboard
   */
  renderDashboardData(data) {
    const costsGrid = this.container?.querySelector('#costs-grid');
    const monitoringGrid = this.container?.querySelector('#monitoring-grid');
    const benchmarksGrid = this.container?.querySelector('#benchmarks-grid');
    const content = this.container?.querySelector('#dashboard-content');
    const errorContainer = this.container?.querySelector('#dashboard-error');

    if (!costsGrid || !monitoringGrid || !benchmarksGrid) return;

    // Afficher le contenu, masquer l'erreur
    if (content) content.style.display = 'block';
    if (errorContainer) errorContainer.style.display = 'none';

    // Rendu des coûts
    const { costs = {}, thresholds = {} } = data;
    costsGrid.innerHTML = '';
    costsGrid.appendChild(DashboardCard.cost('Jour', costs.today_cost || 0, thresholds.daily_threshold || 1, '☀️'));
    costsGrid.appendChild(DashboardCard.cost('Semaine', costs.current_week_cost || 0, thresholds.weekly_threshold || 5, '📅'));
    costsGrid.appendChild(DashboardCard.cost('Mois', costs.current_month_cost || 0, thresholds.monthly_threshold || 15, '🗓️'));
    costsGrid.appendChild(DashboardCard.metric('Coût Total', (costs.total_cost || 0).toFixed(2), '$', 'Depuis le début', '💰'));

    // Rendu du monitoring
    const { monitoring = {} } = data;
    monitoringGrid.innerHTML = '';
    monitoringGrid.appendChild(DashboardCard.metric('Sessions Archivées', monitoring.total_sessions || 0, 'sessions', 'Interactions complètes', '🗂️'));
    monitoringGrid.appendChild(DashboardCard.metric('Documents Traités', monitoring.total_documents || 0, 'documents', 'Fichiers analysés', '📄'));
    monitoringGrid.appendChild(DashboardCard.metric('Fils Actifs', monitoring.active_threads || 0, 'threads', 'Conversations en cours', '💬'));

    // Rendu des benchmarks
    const { benchmarks = [] } = data;
    benchmarksGrid.innerHTML = '';
    benchmarks.forEach(bench => {
      const icon = this.getBenchmarkIcon(bench.name);
      benchmarksGrid.appendChild(DashboardCard.benchmark(bench.name, bench.score, bench.maxScore, icon));
    });
  }

  /**
   * Retourne l'icône pour un agent benchmark
   */
  getBenchmarkIcon(agentName) {
    const icons = {
      'Anima': '🔥',
      'Neo': '⚡',
      'Nexus': '🌿',
      'Global': '🌍'
    };
    return icons[agentName] || '🤖';
  }
}

/**
 * Styles CSS additionnels pour le dashboard moderne
 * À ajouter à votre fichier CSS principal
 */
export const DASHBOARD_MODERN_STYLES = `
/* === DASHBOARD MODERNE === */

.dashboard-modern {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  width: 100%;
  max-width: 1400px;
  margin: 0 auto;
  padding: 1.5rem;
}

.dashboard-modern__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: wrap;
}

.dashboard-modern__title {
  font-size: 1.75rem;
  font-weight: 700;
  letter-spacing: 0.02em;
  color: #f8fafc;
  margin: 0;
  background: linear-gradient(120deg, #7dd3fc 0%, #3b82f6 45%, #a855f7 100%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

@supports not (-webkit-background-clip: text) {
  .dashboard-modern__title {
    color: #f8fafc;
  }
}

.dashboard-modern__content {
  display: flex;
  flex-direction: column;
  gap: 2rem;
  transition: opacity 0.3s ease;
}

.dashboard-modern__section {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.dashboard-modern__section-title {
  font-size: 1.125rem;
  font-weight: 600;
  letter-spacing: 0.02em;
  color: rgba(226, 232, 240, 0.95);
  margin: 0;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

/* === LOADER === */
.dashboard-loader {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 3rem;
}

.loader {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  border: 3px solid rgba(255, 255, 255, 0.15);
  border-top-color: #10b981;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* === ERROR === */
.dashboard-error {
  padding: 1.5rem;
  border-radius: 0.75rem;
  background: rgba(220, 38, 38, 0.12);
  border: 1px solid rgba(239, 68, 68, 0.3);
  color: #fca5a5;
  text-align: center;
  font-size: 0.95rem;
}

/* === RESPONSIVE === */

@media (max-width: 1024px) {
  .dashboard-modern {
    padding: 1.25rem;
  }

  .dashboard-modern__title {
    font-size: 1.5rem;
  }
}

@media (max-width: 640px) {
  .dashboard-modern {
    padding: 1rem;
    gap: 1.25rem;
  }

  .dashboard-modern__header {
    flex-direction: column;
    align-items: flex-start;
  }

  .dashboard-modern__title {
    font-size: 1.375rem;
  }

  .dashboard-modern__content {
    gap: 1.5rem;
  }

  .dashboard-modern__section {
    gap: 0.75rem;
  }

  .dashboard-modern__section-title {
    font-size: 1rem;
  }
}
`;
