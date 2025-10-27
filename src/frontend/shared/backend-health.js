/**
 * @module shared/backend-health
 * Health check helper pour attendre que le backend soit prêt avant de bootstrap l'app.
 *
 * Résout le problème de race condition lors du warm-up backend (3+ secondes).
 * Implémente retry avec exponential backoff pour robustesse maximale.
 */

/**
 * Attend que le backend réponde sur /ready avec retry exponential backoff.
 *
 * @param {object} options - Options de configuration
 * @param {number} options.maxRetries - Nombre max de tentatives (default: 20)
 * @param {number} options.initialDelayMs - Délai initial en ms (default: 500)
 * @param {number} options.maxDelayMs - Délai max entre retries en ms (default: 3000)
 * @param {number} options.timeoutMs - Timeout global en ms (default: 30000)
 * @param {function} options.onRetry - Callback appelé à chaque retry (retry, delay, error)
 * @returns {Promise<object>} - Résultat du health check { ok, db, vector }
 * @throws {Error} - Si le backend ne répond pas après maxRetries ou timeout global
 */
export async function waitForBackendReady(options = {}) {
  const {
    maxRetries = 20,
    initialDelayMs = 500,
    maxDelayMs = 3000,
    timeoutMs = 30000,
    onRetry = null,
  } = options;

  const startTime = Date.now();

  for (let attempt = 0; attempt < maxRetries; attempt++) {
    // Check timeout global
    if (Date.now() - startTime > timeoutMs) {
      const err = new Error(`Backend health check timeout after ${timeoutMs}ms`);
      err.code = 'HEALTH_CHECK_TIMEOUT';
      throw err;
    }

    try {
      // Ping /ready (rapide, ne force pas le chargement du modèle)
      const response = await fetch('/ready', {
        method: 'GET',
        headers: { 'Accept': 'application/json' },
        signal: AbortSignal.timeout(5000), // 5s timeout par requête
      });

      if (response.ok) {
        const data = await response.json();
        if (data.ok === true) {
          console.log(`[Health] Backend ready in ${Date.now() - startTime}ms (attempt ${attempt + 1}/${maxRetries})`);
          return data;
        }
      }

      // Backend répond mais pas encore ready (503)
      if (response.status === 503) {
        const data = await response.json().catch(() => ({ error: 'unknown' }));
        console.log(`[Health] Backend not ready (503): ${JSON.stringify(data)}`);
      }
    } catch (error) {
      // Network error, timeout, ou autre erreur
      console.debug(`[Health] Attempt ${attempt + 1}/${maxRetries} failed:`, error.message);
    }

    // Calculer délai avec exponential backoff
    const delay = Math.min(initialDelayMs * Math.pow(1.5, attempt), maxDelayMs);

    // Callback optionnel
    if (typeof onRetry === 'function') {
      try {
        onRetry(attempt + 1, delay, null);
      } catch (callbackError) {
        console.warn('[Health] onRetry callback failed:', callbackError);
      }
    }

    // Attendre avant retry (sauf dernier essai)
    if (attempt < maxRetries - 1) {
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }

  // Échec après maxRetries
  const err = new Error(`Backend health check failed after ${maxRetries} attempts`);
  err.code = 'HEALTH_CHECK_FAILED';
  throw err;
}

/**
 * Wrapper simple qui attend le backend et affiche feedback visuel dans le loader.
 *
 * @returns {Promise<object>} - Résultat du health check
 * @throws {Error} - Si le backend ne répond pas
 */
export async function waitForBackendReadyWithFeedback() {
  // Trouver le loader element si existe
  const loader = document.getElementById('app-loader');
  const loaderText = loader?.querySelector('.loader-word');

  let lastAttempt = 0;

  try {
    const result = await waitForBackendReady({
      maxRetries: 10, // Réduit de 20 → 10 pour timeout plus rapide
      initialDelayMs: 300, // Réduit de 500ms → 300ms pour démarrage plus rapide
      maxDelayMs: 2000, // Réduit de 3000ms → 2000ms
      timeoutMs: 8000, // Réduit de 30s → 8s pour fallback rapide si backend down
      onRetry: (attempt, delay, error) => {
        lastAttempt = attempt;
        if (loaderText) {
          const dots = '.'.repeat((attempt % 3) + 1);
          loaderText.textContent = `Connexion au serveur${dots} (${attempt}/10)`;
        }
        console.log(`[Health] Retry ${attempt}/20 (waiting ${delay}ms)...`);
      },
    });

    // Succès - message de confirmation
    if (loaderText) {
      loaderText.textContent = 'Serveur prêt ! Chargement...';
    }

    return result;
  } catch (error) {
    // Échec - message d'erreur
    if (loaderText) {
      loaderText.textContent = `Erreur de connexion après ${lastAttempt} tentatives`;
      loaderText.style.color = '#ef4444'; // Rouge
    }

    console.error('[Health] Backend health check failed:', error);
    throw error;
  }
}
