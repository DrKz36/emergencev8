/**
 * @file /src/frontend/shared/api-client.js
 * @description Client API centralisé pour les requêtes HTTP (Fetch).
 * @version V2.0 - Standardisé pour utiliser la nouvelle config.
 */

import { API_ENDPOINTS } from './config.js';

async function fetchApi(endpoint, options = {}) {
    const { method = 'GET', body = null, headers = {} } = options;
    const config = { method, headers };

    if (body) {
        if (body instanceof FormData) {
            config.body = body;
        } else {
            config.body = JSON.stringify(body);
            config.headers['Content-Type'] = 'application/json';
        }
    }

    try {
        const response = await fetch(endpoint, config);
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ message: response.statusText }));
            throw new Error(errorData.detail || errorData.message || `Erreur HTTP : ${response.status}`);
        }
        
        const contentType = response.headers.get("content-type");
        if (contentType && contentType.includes("application/json")) {
            return response.json();
        }
        return {};

    } catch (error) {
        console.error(`[API Client] Erreur sur l'endpoint ${endpoint}:`, error);
        throw error;
    }
}

export const api = {
    getDocuments: () => fetchApi(`${API_ENDPOINTS.DOCUMENTS}/`),

    uploadDocument: (file) => {
        const formData = new FormData();
        formData.append('file', file);
        return fetchApi(API_ENDPOINTS.DOCUMENTS_UPLOAD, {
            method: 'POST',
            body: formData,
        });
    },

    // ✅ CORRECTION: Construit l'URL de suppression correcte (ex: /api/documents/ID_DU_DOC)
    deleteDocument: (docId) => fetchApi(`${API_ENDPOINTS.DOCUMENTS}/${docId}`, {
        method: 'DELETE',
    }),
};
