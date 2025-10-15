/**
 * @module components/agents/AgentAvatars
 * @description Gestionnaire des avatars des agents avec chargement optimisé
 */

export const AGENT_AVATARS = {
    anima: '/assets/anima.png',
    neo: '/assets/neo.png',
    nexus: '/assets/nexus.png'
};

export const AGENT_INFO = {
    anima: {
        name: 'Anima',
        avatar: AGENT_AVATARS.anima,
        role: 'Présence Empathique',
        color: '#FFB74D', // Orange doux
        description: 'Accueillir, clarifier et maintenir le rythme des échanges'
    },
    neo: {
        name: 'Neo',
        avatar: AGENT_AVATARS.neo,
        role: 'Analyste Stratégique',
        color: '#64B5F6', // Bleu clair
        description: 'Structurer les idées, cartographier les hypothèses'
    },
    nexus: {
        name: 'Nexus',
        avatar: AGENT_AVATARS.nexus,
        role: 'Architecte Systémique',
        color: '#9575CD', // Violet
        description: 'Traduire les besoins en flux opérationnels concrets'
    }
};

/**
 * Génère une carte d'agent avec avatar
 * @param {string} agentId - ID de l'agent (anima, neo, nexus)
 * @param {string} content - Contenu HTML de la carte
 * @returns {string} HTML de la carte
 */
export function createAgentCard(agentId, content) {
    const agent = AGENT_INFO[agentId];
    if (!agent) return content;

    return `
        <div class="agent-card" data-agent="${agentId}" style="border-left: 3px solid ${agent.color}">
            <div class="agent-card-header">
                <img
                    src="${agent.avatar}"
                    alt="${agent.name}"
                    class="agent-avatar"
                    onerror="this.style.display='none'"
                />
                <div class="agent-card-info">
                    <h4>${agent.name} - ${agent.role}</h4>
                    <p class="agent-card-description">${agent.description}</p>
                </div>
            </div>
            <div class="agent-card-content">
                ${content}
            </div>
        </div>
    `;
}

/**
 * Génère un avatar inline
 * @param {string} agentId - ID de l'agent
 * @param {number} size - Taille en pixels (défaut: 32)
 * @returns {string} HTML de l'avatar
 */
export function createAgentAvatar(agentId, size = 32) {
    const agent = AGENT_INFO[agentId];
    if (!agent) return '';

    return `
        <img
            src="${agent.avatar}"
            alt="${agent.name}"
            class="agent-avatar-inline"
            style="width: ${size}px; height: ${size}px; border: 2px solid ${agent.color}"
            onerror="this.style.display='none'"
            title="${agent.name} - ${agent.role}"
        />
    `;
}
