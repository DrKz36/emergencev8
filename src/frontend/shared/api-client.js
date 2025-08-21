/**
 * @file /src/frontend/shared/api-client.js
 * @description Client API centralisé pour les requêtes HTTP (Fetch).
 * @version V3.1 - Priorise AUTH.getToken(); fallback localStorage(AUTH.TOKEN_KEY); FormData safe.
 */

import { API_ENDPOINTS } from './config.js';
import { AUTH } from './constants.js';

/**
 * Appel générique fetch avec:
 * - gestion FormData (ne JAMAIS fixer Content-Type)
 * - ajout auto de Authorization: Bearer <token> si présent
 * - normalisation des erreurs et des réponses JSON
 */
async function fetchApi(endpoint, options = {}) {
  const { method = 'GET', body = null, headers = {} } = options;

  // 1) Base config
  const config = { method, headers: { Accept: 'application/json', ...headers } };

  // 2) Body & Content-Type
  if (body) {
    if (body instanceof FormData) {
      // Laisser le navigateur poser le boundary
      config.body = body;
    } else {
      config.body = JSON.stringify(body);
      config.headers['Content-Type'] = 'application/json';
    }
  }

  // 3) Auth header (token -> AUTH.getToken() puis localStorage fallback)
  try {
    let token = null;
    try {
      if (AUTH && typeof AUTH.getToken === 'function') token = AUTH.getToken();
    } catch { /* no-op */ }
    if (!token) {
      try { token = localStorage.getItem(AUTH?.TOKEN_KEY); } catch { /* no-op */ }
    }
    if (token && !config.headers.Authorization) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  } catch { /* ignore */ }

  // 4) Appel réseau
  let response;
  try {
    response = await fetch(endpoint, config); // NOTE: main.js patchera aussi fetch → double sécu
  } catch (networkErr) {
    console.error(`[API Client] Échec réseau vers ${endpoint}`, networkErr);
    throw new Error('Erreur réseau — vérifie la connexion.');
  }

  // 5) Gestion d’erreurs HTTP
  if (!response.ok) {
    let errorPayload = {};
    try { errorPayload = await response.json(); } catch { /* no-op */ }
    const msg = errorPayload.detail || errorPayload.message || `${response.status} ${response.statusText}`;
    console.error(`[API Client] Erreur sur l'endpoint ${endpoint}:`, msg);
    throw new Error(msg);
  }

  // 6) Normalisation de la réponse
  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    try { return await response.json(); } catch { return {}; }
  }
  return {};
}

export const api = {
  getDocuments: () => fetchApi(`${API_ENDPOINTS.DOCUMENTS}/`),
  uploadDocument: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return fetchApi(API_ENDPOINTS.DOCUMENTS_UPLOAD, { method: 'POST', body: formData });
  },
  deleteDocument: (docId) => fetchApi(`${API_ENDPOINTS.DOCUMENTS}/${docId}`, { method: 'DELETE' }),
};
