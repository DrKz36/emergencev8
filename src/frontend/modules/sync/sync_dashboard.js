/**
 * Dashboard de synchronisation automatique inter-agents
 *
 * Affiche :
 * - Statut global (running, pending changes, last consolidation)
 * - Liste des fichiers surveillés avec checksums
 * - Changements en attente de consolidation
 * - Bouton de consolidation manuelle
 * - Métriques temps réel (via refresh automatique)
 */

// Utiliser les globals définis dans la page HTML ou fallback
const API_BASE_URL = window.API_BASE_URL || "http://localhost:8000";
const getAuthHeaders = window.getAuthHeaders || (() => ({
  'Content-Type': 'application/json',
  'x-dev-bypass': '1',
  'X-User-ID': 'dev-user'
}));

let refreshIntervalId = null;

/**
 * Initialise le module sync dashboard
 */
export function init() {
  console.log("[sync_dashboard] Module initialized");
  render();

  // Auto-refresh toutes les 10 secondes
  refreshIntervalId = setInterval(loadSyncStatus, 10000);
}

/**
 * Nettoie le module (appelé lors du changement de module)
 */
export function cleanup() {
  if (refreshIntervalId) {
    clearInterval(refreshIntervalId);
    refreshIntervalId = null;
  }
  console.log("[sync_dashboard] Module cleaned up");
}

/**
 * Affiche le dashboard
 */
function render() {
  const container = document.getElementById("module-container");
  if (!container) {
    console.error("[sync_dashboard] module-container not found");
    return;
  }

  container.innerHTML = `
    <div class="sync-dashboard">
      <div class="sync-header">
        <h1>🔄 Synchronisation automatique inter-agents</h1>
        <p class="subtitle">Option A - Détection automatique & consolidation intelligente</p>
      </div>

      <!-- Status global -->
      <div class="sync-status-card card">
        <h2>📊 Statut global</h2>
        <div id="sync-status-content">
          <p class="loading">Chargement du statut...</p>
        </div>
      </div>

      <!-- Changements en attente -->
      <div class="sync-pending-card card">
        <h2>⏳ Changements en attente</h2>
        <div id="sync-pending-content">
          <p class="loading">Chargement des changements...</p>
        </div>
      </div>

      <!-- Fichiers surveillés -->
      <div class="sync-files-card card">
        <h2>👁️ Fichiers surveillés</h2>
        <div id="sync-files-content">
          <p class="loading">Chargement des fichiers...</p>
        </div>
      </div>

      <!-- Actions -->
      <div class="sync-actions-card card">
        <h2>🎯 Actions</h2>
        <div class="sync-actions">
          <button id="sync-consolidate-btn" class="btn btn-primary">
            🔀 Déclencher consolidation manuelle
          </button>
          <button id="sync-refresh-btn" class="btn btn-secondary">
            🔄 Rafraîchir
          </button>
        </div>
      </div>
    </div>
  `;

  attachEventListeners();
  loadSyncStatus();
}

/**
 * Attache les event listeners
 */
function attachEventListeners() {
  const consolidateBtn = document.getElementById("sync-consolidate-btn");
  const refreshBtn = document.getElementById("sync-refresh-btn");

  if (consolidateBtn) {
    consolidateBtn.addEventListener("click", triggerConsolidation);
  }

  if (refreshBtn) {
    refreshBtn.addEventListener("click", loadSyncStatus);
  }
}

/**
 * Charge le statut de synchronisation
 */
async function loadSyncStatus() {
  try {
    // Charger en parallèle : status, pending changes, checksums
    const [statusRes, pendingRes, checksumsRes] = await Promise.all([
      fetch(`${API_BASE_URL}/api/sync/status`, { headers: getAuthHeaders() }),
      fetch(`${API_BASE_URL}/api/sync/pending-changes`, { headers: getAuthHeaders() }),
      fetch(`${API_BASE_URL}/api/sync/checksums`, { headers: getAuthHeaders() }),
    ]);

    if (!statusRes.ok || !pendingRes.ok || !checksumsRes.ok) {
      throw new Error("Failed to load sync data");
    }

    const statusData = await statusRes.json();
    const pendingData = await pendingRes.json();
    const checksumsData = await checksumsRes.json();

    renderStatus(statusData);
    renderPendingChanges(pendingData);
    renderChecksums(checksumsData);
  } catch (error) {
    console.error("[sync_dashboard] Error loading sync status:", error);
    showError("Erreur lors du chargement du statut de synchronisation");
  }
}

/**
 * Affiche le statut global
 */
function renderStatus(data) {
  const container = document.getElementById("sync-status-content");
  if (!container) return;

  const statusIcon = data.running ? "✅" : "❌";
  const statusText = data.running ? "Actif" : "Arrêté";
  const statusClass = data.running ? "status-active" : "status-inactive";

  const lastConsolidation = data.last_consolidation
    ? new Date(data.last_consolidation).toLocaleString("fr-FR")
    : "Jamais";

  container.innerHTML = `
    <div class="sync-status-grid">
      <div class="status-item">
        <span class="status-label">État du service :</span>
        <span class="status-value ${statusClass}">${statusIcon} ${statusText}</span>
      </div>
      <div class="status-item">
        <span class="status-label">Changements en attente :</span>
        <span class="status-value ${data.pending_changes > 0 ? 'status-warning' : ''}">${data.pending_changes}</span>
      </div>
      <div class="status-item">
        <span class="status-label">Fichiers surveillés :</span>
        <span class="status-value">${data.watched_files}</span>
      </div>
      <div class="status-item">
        <span class="status-label">Checksums trackés :</span>
        <span class="status-value">${data.checksums_tracked}</span>
      </div>
      <div class="status-item">
        <span class="status-label">Seuil consolidation :</span>
        <span class="status-value">${data.consolidation_threshold} changements</span>
      </div>
      <div class="status-item">
        <span class="status-label">Intervalle vérification :</span>
        <span class="status-value">${data.check_interval_seconds}s</span>
      </div>
      <div class="status-item full-width">
        <span class="status-label">Dernière consolidation :</span>
        <span class="status-value">${lastConsolidation}</span>
      </div>
    </div>
  `;
}

/**
 * Affiche les changements en attente
 */
function renderPendingChanges(data) {
  const container = document.getElementById("sync-pending-content");
  if (!container) return;

  if (data.count === 0) {
    container.innerHTML = `
      <p class="no-data">✅ Aucun changement en attente - Tout est synchronisé</p>
    `;
    return;
  }

  const changesHtml = data.changes
    .map(
      (change) => `
    <div class="change-item">
      <div class="change-header">
        <span class="change-type ${change.event_type}">${getEventIcon(change.event_type)} ${change.event_type}</span>
        <span class="change-file">${change.file_path}</span>
        <span class="change-time">${new Date(change.timestamp).toLocaleString("fr-FR")}</span>
      </div>
      <div class="change-details">
        ${change.agent_owner ? `<span class="change-agent">Agent: ${change.agent_owner}</span>` : ""}
        ${change.old_checksum ? `<span class="change-checksum">Old: ${change.old_checksum.substring(0, 8)}...</span>` : ""}
        ${change.new_checksum ? `<span class="change-checksum">New: ${change.new_checksum.substring(0, 8)}...</span>` : ""}
      </div>
    </div>
  `
    )
    .join("");

  container.innerHTML = `
    <div class="changes-list">
      <p class="changes-count">⚠️ ${data.count} changement(s) en attente de consolidation</p>
      ${changesHtml}
    </div>
  `;
}

/**
 * Affiche les fichiers surveillés
 */
function renderChecksums(data) {
  const container = document.getElementById("sync-files-content");
  if (!container) return;

  if (data.count === 0) {
    container.innerHTML = `<p class="no-data">Aucun fichier surveillé</p>`;
    return;
  }

  const filesHtml = Object.entries(data.checksums)
    .map(
      ([path, info]) => `
    <div class="file-item">
      <div class="file-path">📄 ${path}</div>
      <div class="file-details">
        <span class="file-checksum">Checksum: ${info.checksum.substring(0, 12)}...</span>
        <span class="file-modified">Modifié: ${new Date(info.last_modified).toLocaleString("fr-FR")}</span>
        ${info.agent_owner ? `<span class="file-agent">Agent: ${info.agent_owner}</span>` : ""}
      </div>
    </div>
  `
    )
    .join("");

  container.innerHTML = `
    <div class="files-list">
      <p class="files-count">${data.count} fichier(s) surveillé(s)</p>
      ${filesHtml}
    </div>
  `;
}

/**
 * Déclenche une consolidation manuelle
 */
async function triggerConsolidation() {
  const btn = document.getElementById("sync-consolidate-btn");
  if (!btn) return;

  try {
    btn.disabled = true;
    btn.textContent = "⏳ Consolidation en cours...";

    const res = await fetch(`${API_BASE_URL}/api/sync/consolidate`, {
      method: "POST",
      headers: getAuthHeaders(),
    });

    if (!res.ok) {
      throw new Error("Failed to trigger consolidation");
    }

    const result = await res.json();
    console.log("[sync_dashboard] Consolidation result:", result);

    showSuccess(`Consolidation réussie : ${result.changes_consolidated} changements consolidés`);

    // Recharger le statut après consolidation
    setTimeout(loadSyncStatus, 1000);
  } catch (error) {
    console.error("[sync_dashboard] Error triggering consolidation:", error);
    showError("Erreur lors du déclenchement de la consolidation");
  } finally {
    btn.disabled = false;
    btn.textContent = "🔀 Déclencher consolidation manuelle";
  }
}

/**
 * Retourne l'icône pour un type d'événement
 */
function getEventIcon(eventType) {
  switch (eventType) {
    case "modified":
      return "✏️";
    case "created":
      return "➕";
    case "deleted":
      return "🗑️";
    default:
      return "📝";
  }
}

/**
 * Affiche un message d'erreur
 */
function showError(message) {
  // TODO: Intégrer avec le système de notifications global
  console.error("[sync_dashboard]", message);
  alert(`❌ ${message}`);
}

/**
 * Affiche un message de succès
 */
function showSuccess(message) {
  // TODO: Intégrer avec le système de notifications global
  console.log("[sync_dashboard]", message);
  alert(`✅ ${message}`);
}
