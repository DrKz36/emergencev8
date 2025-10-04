/**
 * @module components/ui/DashboardCard
 * @description Cartes de dashboard modernisées avec effets métalliques et responsive
 */

export class DashboardCard {
  /**
   * Crée une carte de dashboard
   * @param {Object} options - Configuration de la carte
   * @param {string} options.title - Titre de la carte
   * @param {string} [options.icon] - Icône SVG ou emoji
   * @param {string} options.value - Valeur principale
   * @param {string} [options.unit] - Unité (ex: "$", "sessions")
   * @param {string} [options.description] - Description/sous-titre
   * @param {string} [options.variant] - 'primary' | 'secondary' | 'success' | 'warning' | 'danger'
   * @param {number} [options.progress] - Progression 0-100 (optionnel)
   * @param {number} [options.threshold] - Seuil pour la progress bar
   * @param {string} [options.className] - Classes CSS additionnelles
   * @returns {HTMLElement} - Élément carte
   */
  static create({
    title = '',
    icon = '📊',
    value = '0',
    unit = '',
    description = '',
    variant = 'primary',
    progress = null,
    threshold = null,
    className = ''
  }) {
    const card = document.createElement('div');
    card.className = `dashboard-card dashboard-card--${variant} ${className}`.trim();

    const progressHTML = (progress !== null && threshold !== null) ? `
      <div class="dashboard-card__progress">
        <div class="dashboard-card__progress-bar ${DashboardCard.getProgressClass(progress, threshold)}"
             style="width: ${Math.min(progress, 100)}%"></div>
      </div>
      <div class="dashboard-card__threshold">
        Limite : ${threshold.toFixed(2)} ${unit}
      </div>
    ` : '';

    card.innerHTML = `
      <div class="dashboard-card__header">
        <h3 class="dashboard-card__title">${title}</h3>
        <div class="dashboard-card__icon">${icon}</div>
      </div>
      <div class="dashboard-card__body">
        <div class="dashboard-card__value">
          ${value}
          ${unit ? `<span class="dashboard-card__unit">${unit}</span>` : ''}
        </div>
        ${description ? `<p class="dashboard-card__description">${description}</p>` : ''}
        ${progressHTML}
      </div>
    `;

    return card;
  }

  /**
   * Carte de coût avec progress bar
   */
  static cost(title, value, threshold, icon = '💰') {
    const percent = threshold > 0 ? (value / threshold) * 100 : 0;
    return DashboardCard.create({
      title,
      icon,
      value: value.toFixed(4),
      unit: '$',
      variant: DashboardCard.getCostVariant(percent),
      progress: percent,
      threshold
    });
  }

  /**
   * Carte métrique simple
   */
  static metric(title, value, unit, description, icon = '📈') {
    return DashboardCard.create({
      title,
      icon,
      value: value.toString(),
      unit,
      description,
      variant: 'secondary'
    });
  }

  /**
   * Carte benchmark
   */
  static benchmark(title, score, maxScore = 100, icon = '⚡') {
    const percent = (score / maxScore) * 100;
    return DashboardCard.create({
      title,
      icon,
      value: score.toFixed(1),
      unit: `/ ${maxScore}`,
      description: `Performance : ${percent.toFixed(0)}%`,
      variant: DashboardCard.getBenchmarkVariant(percent),
      progress: percent,
      threshold: maxScore
    });
  }

  /**
   * Détermine la classe de la progress bar selon le seuil
   */
  static getProgressClass(percent, threshold) {
    if (percent > 75) return 'dashboard-card__progress-bar--critical';
    if (percent > 50) return 'dashboard-card__progress-bar--high';
    return '';
  }

  /**
   * Détermine la variante selon le coût
   */
  static getCostVariant(percent) {
    if (percent > 75) return 'danger';
    if (percent > 50) return 'warning';
    return 'success';
  }

  /**
   * Détermine la variante selon le score benchmark
   */
  static getBenchmarkVariant(percent) {
    if (percent >= 80) return 'success';
    if (percent >= 60) return 'warning';
    return 'danger';
  }
}

/**
 * Styles CSS pour les cartes de dashboard
 * À importer dans votre fichier CSS principal
 */
export const DASHBOARD_CARD_STYLES = `
/* === DASHBOARD CARDS === */

.dashboard-card {
  display: flex;
  flex-direction: column;
  padding: var(--card-padding, 1.25rem);
  border-radius: var(--card-radius, 1rem);
  background: var(--card-bg, rgba(22, 22, 26, 0.55));
  border: 1px solid var(--card-border, rgba(255, 255, 255, 0.10));
  box-shadow: var(--card-shadow, 0 10px 30px rgba(0, 0, 0, 0.35));
  backdrop-filter: blur(18px);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

.dashboard-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 15px 40px rgba(0, 0, 0, 0.45);
  border-color: rgba(255, 255, 255, 0.15);
}

/* === VARIANTS === */
.dashboard-card--primary {
  border-color: rgba(16, 185, 129, 0.3);
}

.dashboard-card--success {
  border-color: rgba(34, 197, 94, 0.3);
  background: linear-gradient(135deg, rgba(22, 163, 74, 0.08), var(--card-bg));
}

.dashboard-card--warning {
  border-color: rgba(245, 158, 11, 0.3);
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.08), var(--card-bg));
}

.dashboard-card--danger {
  border-color: rgba(239, 68, 68, 0.3);
  background: linear-gradient(135deg, rgba(220, 38, 38, 0.08), var(--card-bg));
}

/* === HEADER === */
.dashboard-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.dashboard-card__title {
  font-size: 0.95rem;
  font-weight: 600;
  letter-spacing: 0.02em;
  color: rgba(226, 232, 240, 0.95);
  margin: 0;
}

.dashboard-card__icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 0.5rem;
  background: rgba(255, 255, 255, 0.06);
  font-size: 1.25rem;
}

/* === BODY === */
.dashboard-card__body {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.dashboard-card__value {
  font-size: 2rem;
  font-weight: 700;
  line-height: 1.2;
  color: #f8fafc;
  display: flex;
  align-items: baseline;
  gap: 0.375rem;
}

.dashboard-card__unit {
  font-size: 1rem;
  font-weight: 500;
  color: rgba(148, 163, 184, 0.85);
}

.dashboard-card__description {
  font-size: 0.875rem;
  color: rgba(148, 163, 184, 0.8);
  margin: 0;
  line-height: 1.4;
}

.dashboard-card__threshold {
  font-size: 0.8125rem;
  color: rgba(148, 163, 184, 0.75);
  margin-top: 0.25rem;
}

/* === PROGRESS BAR === */
.dashboard-card__progress {
  width: 100%;
  height: 6px;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 999px;
  overflow: hidden;
  margin-top: 0.5rem;
}

.dashboard-card__progress-bar {
  height: 100%;
  background: var(--metal-emerald-gradient, linear-gradient(to right, #34d399, #10b981));
  border-radius: inherit;
  transition: width 0.5s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

.dashboard-card__progress-bar::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
  transform: translateX(-100%);
  animation: shimmer 2s infinite;
}

@keyframes shimmer {
  to {
    transform: translateX(100%);
  }
}

.dashboard-card__progress-bar--high {
  background: var(--metal-blue-gradient, linear-gradient(to right, #60a5fa, #3b82f6));
}

.dashboard-card__progress-bar--critical {
  background: var(--metal-red-gradient, linear-gradient(to right, #ef4444, #dc2626));
}

/* === GRILLE RESPONSIVE === */
.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1.25rem;
  margin: 1.5rem 0;
}

/* === RESPONSIVE === */

/* Tablettes */
@media (max-width: 1024px) {
  .dashboard-grid {
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 1rem;
  }

  .dashboard-card__value {
    font-size: 1.75rem;
  }
}

/* Mobile paysage: 2 colonnes */
@media (max-width: 920px) and (orientation: landscape) {
  .dashboard-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 0.875rem;
  }

  .dashboard-card {
    padding: 1rem;
  }

  .dashboard-card__header {
    margin-bottom: 0.75rem;
  }

  .dashboard-card__value {
    font-size: 1.5rem;
  }

  .dashboard-card__icon {
    width: 32px;
    height: 32px;
    font-size: 1.125rem;
  }
}

/* Mobile portrait: 1 colonne */
@media (max-width: 640px) and (orientation: portrait) {
  .dashboard-grid {
    grid-template-columns: 1fr;
    gap: 0.75rem;
  }

  .dashboard-card {
    padding: 1rem;
  }

  .dashboard-card__title {
    font-size: 0.875rem;
  }

  .dashboard-card__value {
    font-size: 1.5rem;
  }

  .dashboard-card__icon {
    width: 28px;
    height: 28px;
    font-size: 1rem;
  }

  .dashboard-card__description {
    font-size: 0.8125rem;
  }
}

/* Très petits écrans */
@media (max-width: 360px) {
  .dashboard-card {
    padding: 0.875rem;
  }

  .dashboard-card__value {
    font-size: 1.375rem;
  }
}
`;
