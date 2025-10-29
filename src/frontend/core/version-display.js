/**
 * @module core/version-display
 * @description Updates version displays across the application
 */

import versionInfo from '../../version.js';

/**
 * Updates all version displays in the DOM
 */
export function updateVersionDisplays() {
  // Update main header version
  const headerVersion = document.getElementById('app-version-display');
  if (headerVersion) {
    headerVersion.textContent = versionInfo.version;
  }

  // Update documentation version
  const docVersion = document.getElementById('doc-version-display');
  if (docVersion) {
    docVersion.textContent = versionInfo.version;
  }

  // Update documentation features count
  const docFeaturesCount = document.getElementById('doc-features-count');
  if (docFeaturesCount) {
    docFeaturesCount.textContent = versionInfo.featuresDisplay;
  }

  // Update documentation completion percentage
  const docCompletionPct = document.getElementById('doc-completion-pct');
  if (docCompletionPct) {
    docCompletionPct.textContent = `${versionInfo.completionPercentage}% complété`;
  }

  console.info(
    `[Version] ${versionInfo.fullVersion} (${versionInfo.completionPercentage}% completed)`
  );
}

/**
 * Gets the current version info
 * @returns {Object} Version information
 */
export function getVersionInfo() {
  return versionInfo;
}

/**
 * Initialize version displays on DOM ready
 */
if (typeof document !== 'undefined') {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', updateVersionDisplays);
  } else {
    updateVersionDisplays();
  }
}
