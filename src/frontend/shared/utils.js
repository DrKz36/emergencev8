/**
 * @file /src/frontend/shared/utils.js
 * @description Fonctions utilitaires partagées.
 * @version V18.0 - Fusion de la V17.3 existante avec les nouvelles fonctions d'export.
 * Modernisation en module ES6 standard (suppression du namespace global).
 */

/**
 * Génère un ID unique.
 * @returns {string} ID unique format timestamp-random.
 */
export function generateId() {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * Formate une date en français.
 * @param {Date|string|number} date - Date à formater.
 * @returns {string} Date formatée.
 */
export function formatDate(date) {
    return new Date(date).toLocaleString('fr-CH', { // Standardisé sur fr-CH
        day: '2-digit', month: '2-digit', year: 'numeric',
        hour: '2-digit', minute: '2-digit'
    });
}

/**
 * Formate une date pour l'affichage ou les noms de fichiers.
 * @returns {{display: string, filename: string}} Un objet avec la date locale et un timestamp simple.
 */
export function getFormattedDate() {
    const now = new Date();
    const display = now.toLocaleString('fr-CH', {
        year: 'numeric', month: '2-digit', day: '2-digit',
        hour: '2-digit', minute: '2-digit', second: '2-digit'
    });
    const filename = now.toISOString().slice(0, 19).replace(/[-:T]/g, ''); // YYYYMMDDHHMMSS
    
    return { display, filename };
}

/**
 * Clone profond d'un objet.
 * @param {*} obj - Objet à cloner.
 * @returns {*} Clone de l'objet.
 */
export function deepClone(obj) {
    // Utilise la méthode standard et performante de l'industrie
    return JSON.parse(JSON.stringify(obj));
}

/**
 * Sanitize HTML pour éviter les injections XSS simples.
 * @param {string} text - Texte à nettoyer.
 * @returns {string} Texte sécurisé.
 */
export function escapeHtml(text) {
    const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#x27;', "/": '&#x2F;' };
    return text.replace(/[&<>"'/]/g, char => map[char]);
}

/**
 * Déclenche le téléchargement d'un fichier texte créé côté client.
 * @param {string} filename - Le nom du fichier à télécharger (ex: "mon-fichier.txt").
 * @param {string} text - Le contenu du fichier.
 */
export function downloadFile(filename, text) {
    const element = document.createElement('a');
    element.setAttribute('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(text));
    element.setAttribute('download', filename);
    element.style.display = 'none';
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
}

/**
 * Exporte un historique de conversation au format Markdown.
 * @param {Array<Object>} history - L'array de messages.
 * @param {string} title - Le titre du document.
 * @param {Object} agentsMap - La map des agents (depuis constants.js).
 */
export function exportToMarkdown(history, title, agentsMap) {
    let markdownContent = `# ${title}\n\n`;
    markdownContent += `*Exporté le ${formatDate(new Date())}*\n\n---\n\n`;

    history.forEach(msg => {
        const authorName = msg.role === 'user' ? 'Vous' : (agentsMap[msg.agent_id]?.name || msg.agent_id || 'Assistant');
        const roundInfo = msg.round_number ? ` (Round ${msg.round_number})` : '';
        const content = msg.content || '';
        markdownContent += `**${authorName}${roundInfo} :**\n\n${content}\n\n---\n\n`;
    });

    const blob = new Blob([markdownContent], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    
    a.href = url;
    a.download = `${title.replace(/[^a-z0-9]/gi, '_').toLowerCase()}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    console.log(`[Utils] Exportation de "${title}" terminée.`);
}

console.log('[Utils] V18.0 (ESM Ready) Initialized successfully ✅');
