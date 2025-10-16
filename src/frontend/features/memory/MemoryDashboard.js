/**
 * @module features/memory/MemoryDashboard
 * MemoryDashboard Component - Sprint P3
 *
 * Dashboard mémoire utilisateur affichant:
 * - Stats globales (sessions, threads, taille LTM)
 * - Top 10 préférences (confiance, type, date)
 * - Top 10 concepts (mentions, dernière mention)
 *
 * Endpoint API: GET /api/memory/user/stats
 */

import { api } from '../../shared/api-client.js';
import { EventBus } from '../../core/event-bus.js';

export class MemoryDashboard {
  constructor(container) {
    this.container = container;
    this.stats = null;
    this.loading = false;
    console.info('[MemoryDashboard] Initialized');
  }

  /**
   * Render dashboard (fetch data + display)
   */
  async render() {
    console.info('[MemoryDashboard] Rendering dashboard...');

    this.showLoadingState();

    try {
      this.stats = await this.fetchMemoryStats();
      this.renderDashboard();
    } catch (err) {
      console.error('[MemoryDashboard] Failed to fetch stats', err);
      this.renderError(err);
    }
  }

  /**
   * Fetch memory stats from backend
   */
  async fetchMemoryStats() {
    console.info('[MemoryDashboard] Fetching /api/memory/user/stats...');

    try {
      const response = await api.get('/api/memory/user/stats');

      if (!response || typeof response !== 'object') {
        throw new Error('Invalid response format');
      }

      console.info('[MemoryDashboard] Stats fetched successfully', response);
      return response;
    } catch (err) {
      console.error('[MemoryDashboard] API error', err);
      throw err;
    }
  }

  /**
   * Show loading state
   */
  showLoadingState() {
    this.container.innerHTML = `
      <div class="memory-dashboard loading">
        <div class="loader-container">
          <div class="spinner"></div>
          <p>Chargement de votre mémoire...</p>
        </div>
      </div>
    `;
  }

  /**
   * Render error state
   */
  renderError(err) {
    const message = err?.message || 'Erreur inconnue';

    this.container.innerHTML = `
      <div class="memory-dashboard error">
        <h2>❌ Erreur</h2>
        <p>Impossible de charger le dashboard mémoire.</p>
        <p class="error-detail">${this.escapeHtml(message)}</p>
        <button class="btn-retry" onclick="location.reload()">Réessayer</button>
      </div>
    `;
  }

  /**
   * Render dashboard with stats
   */
  renderDashboard() {
    if (!this.stats) {
      this.renderError(new Error('No stats available'));
      return;
    }

    const { preferences = {}, concepts = {}, stats = {}, hints = {} } = this.stats;

    this.container.innerHTML = `
      <div class="memory-dashboard">
        <h2>🧠 Ta Mémoire à Long Terme</h2>

        <!-- Global stats -->
        <div class="stats-grid">
          ${this.renderStatCard('Sessions analysées', stats.sessions_analyzed || 0)}
          ${this.renderStatCard('Threads archivés', stats.threads_archived || 0)}
          ${this.renderStatCard('Taille LTM', `${stats.ltm_size_mb || 0} MB`)}
          ${this.renderStatCard('💡 Hints proactifs', hints.total || 0)}
        </div>

        <!-- Preferences section -->
        ${this.renderPreferencesSection(preferences)}

        <!-- Concepts section -->
        ${this.renderConceptsSection(concepts)}
      </div>
    `;

    console.info('[MemoryDashboard] Dashboard rendered successfully');
  }

  /**
   * Render stat card
   */
  renderStatCard(label, value) {
    return `
      <div class="stat-card">
        <div class="stat-label">${this.escapeHtml(label)}</div>
        <div class="stat-value">${this.escapeHtml(String(value))}</div>
      </div>
    `;
  }

  /**
   * Render preferences section
   */
  renderPreferencesSection(preferences) {
    const total = preferences.total || 0;
    const top = preferences.top || [];
    const byType = preferences.by_type || {};

    if (total === 0) {
      return `
        <div class="dashboard-section">
          <h3>💡 Tes Préférences (0)</h3>
          <p class="empty-state">Aucune préférence enregistrée pour le moment.</p>
        </div>
      `;
    }

    const breakdownHtml = Object.entries(byType)
      .map(([type, count]) => `<span class="badge badge-${type}">${type}: ${count}</span>`)
      .join('');

    const preferencesListHtml = top
      .map(pref => this.renderPreferenceItem(pref))
      .join('');

    return `
      <div class="dashboard-section">
        <h3>💡 Tes Préférences (${total})</h3>
        <div class="preferences-breakdown">
          ${breakdownHtml}
        </div>
        <div class="preferences-list">
          ${preferencesListHtml}
        </div>
      </div>
    `;
  }

  /**
   * Render single preference item
   */
  renderPreferenceItem(pref) {
    const topic = pref.topic || 'Unknown';
    const confidence = Math.round((pref.confidence || 0) * 100);
    const type = pref.type || 'preference';
    const capturedAt = pref.captured_at || pref.created_at;
    const relativeDate = this.formatRelativeDate(capturedAt);

    return `
      <div class="preference-item">
        <div class="preference-content">
          <span class="preference-topic">${this.escapeHtml(topic)}</span>
          <span class="preference-confidence">${confidence}%</span>
        </div>
        <div class="preference-meta">
          <span class="preference-date">${this.escapeHtml(relativeDate)}</span>
          <span class="badge badge-${type}">${type}</span>
        </div>
      </div>
    `;
  }

  /**
   * Render concepts section
   */
  renderConceptsSection(concepts) {
    const total = concepts.total || 0;
    const top = concepts.top || [];

    if (total === 0) {
      return `
        <div class="dashboard-section">
          <h3>🔍 Concepts Récurrents (0)</h3>
          <p class="empty-state">Aucun concept enregistré pour le moment.</p>
        </div>
      `;
    }

    const conceptsListHtml = top
      .map(concept => this.renderConceptItem(concept))
      .join('');

    return `
      <div class="dashboard-section">
        <h3>🔍 Concepts Récurrents (${total})</h3>
        <div class="concepts-list">
          ${conceptsListHtml}
        </div>
      </div>
    `;
  }

  /**
   * Render single concept item
   */
  renderConceptItem(concept) {
    const conceptText = concept.concept || 'Unknown';
    const mentions = concept.mentions || 1;
    const lastMentioned = concept.last_mentioned || concept.created_at;
    const relativeDate = this.formatRelativeDate(lastMentioned);

    return `
      <div class="concept-item">
        <div class="concept-content">
          <span class="concept-text">${this.escapeHtml(conceptText)}</span>
          <span class="concept-mentions">${mentions} mentions</span>
        </div>
        <div class="concept-meta">
          <span class="concept-date">Dernier: ${this.escapeHtml(relativeDate)}</span>
        </div>
      </div>
    `;
  }

  /**
   * Format date relative (e.g., "Il y a 3 jours")
   */
  formatRelativeDate(isoDate) {
    if (!isoDate) return 'Date inconnue';

    try {
      const date = new Date(isoDate);
      const now = new Date();
      const diffMs = now - date;
      const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

      if (diffDays === 0) return "Aujourd'hui";
      if (diffDays === 1) return "Hier";
      if (diffDays < 7) return `Il y a ${diffDays} jours`;
      if (diffDays < 30) return `Il y a ${Math.floor(diffDays / 7)} semaines`;
      if (diffDays < 365) return `Il y a ${Math.floor(diffDays / 30)} mois`;
      return `Il y a ${Math.floor(diffDays / 365)} ans`;
    } catch (err) {
      console.error('[MemoryDashboard] Error formatting date', err);
      return 'Date invalide';
    }
  }

  /**
   * Escape HTML to prevent XSS
   */
  escapeHtml(text) {
    if (typeof text !== 'string') return '';

    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  /**
   * Refresh dashboard (re-fetch stats)
   */
  async refresh() {
    console.info('[MemoryDashboard] Refreshing dashboard...');
    await this.render();
  }

  /**
   * Destroy component (cleanup)
   */
  destroy() {
    this.container.innerHTML = '';
    this.stats = null;
    console.info('[MemoryDashboard] Component destroyed');
  }
}
