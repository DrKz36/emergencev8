/**
 * @module features/debate/debate
 * @description Orchestrateur du module Débat - V26.0 "Concordance"
 * - Applique le pattern init/mount pour une initialisation découplée du DOM.
 */
import { DebateUI } from './debate-ui.js';
import { EVENTS, AGENTS } from '../../shared/constants.js';

export default class DebateModule {
    constructor(eventBus, state) {
        this.eventBus = eventBus;
        this.state = state;
        this.ui = null;
        this.container = null;
        this.listeners = [];
        this.isInitialized = false;
        console.log("✅ DebateModule V26.0 (Concordance) Prêt.");
    }
    
    init() {
        if (this.isInitialized) return;
        this.ui = new DebateUI(this.eventBus);
        this.registerEvents();
        this.registerStateChanges();
        this.isInitialized = true;
        console.log("✅ DebateModule V26.0 (Concordance) Initialisé UNE SEULE FOIS.");
    }

    mount(container) {
        this.container = container;
        this.ui.render(this.container, this.state.get('debate'));
    }

    destroy() {
        this.listeners.forEach(unsubscribe => unsubscribe());
        this.listeners = [];
        this.container = null;
    }
    
    registerStateChanges() {
        const unsubscribe = this.state.subscribe('debate', (debateState) => {
            if (this.container) {
                this.ui.render(this.container, debateState);
            }
        });
        this.listeners.push(unsubscribe);
    }

    registerEvents() {
        this.listeners.push(this.eventBus.on('debate:create', this.handleCreateDebate.bind(this)));
        this.listeners.push(this.eventBus.on('debate:reset', this.reset.bind(this)));
        this.listeners.push(this.eventBus.on('debate:export', this.handleExportDebate.bind(this)));
        
        this.listeners.push(this.eventBus.on('ws:debate_started', this.handleServerUpdate.bind(this)));
        this.listeners.push(this.eventBus.on('ws:debate_turn_update', this.handleServerUpdate.bind(this)));
        this.listeners.push(this.eventBus.on('ws:debate_ended', this.handleServerUpdate.bind(this)));
        this.listeners.push(this.eventBus.on('ws:debate_status_update', this.onDebateStatusUpdate.bind(this)));
    }

    reset() {
        this.state.set('debate', {
            isActive: false,
            debateId: null,
            status: null,
            statusText: 'Prêt à commencer.',
            config: null,
            history: [],
            synthesis: null,
            ragContext: null
        });
    }

    handleCreateDebate(config) {
        this.reset();
        this.state.set('debate.statusText', 'Création du débat en cours...');
        this.eventBus.emit(EVENTS.WS_SEND, { type: "debate:create", payload: config });
    }

    handleServerUpdate(serverState) {
        const clientState = this._normalizeServerState(serverState);
        this.state.set('debate', clientState);
    }

    _normalizeServerState(serverData) {
        const history = (serverData.history || []).map(turn => ({
            roundNumber: turn.round_number,
            agentResponses: turn.agent_responses
        }));
        const config = serverData.config ? {
            topic: serverData.config.topic,
            rounds: serverData.config.rounds,
            agentOrder: serverData.config.agent_order,
            useRag: serverData.config.use_rag
        } : null;
        const normalized = {
            debateId: serverData.debate_id,
            status: serverData.status,
            config: config,
            history: history,
            synthesis: serverData.synthesis,
            ragContext: serverData.rag_context,
            isActive: serverData.status === 'in_progress' || serverData.status === 'pending',
        };
        normalized.statusText = this.getHumanReadableStatus(normalized);
        return normalized;
    }

    onDebateStatusUpdate(payload) {
        this.state.set('debate.statusText', payload.status);
    }

    getHumanReadableStatus(state) {
        if (!state) return '';
        switch(state.status) {
            case 'pending': return 'En attente de démarrage...';
            case 'in_progress':
                const lastTurn = state.history[state.history.length - 1];
                return lastTurn ? `Tour ${lastTurn.roundNumber} / ${state.config.rounds}` : 'Débat en cours...';
            case 'completed': return 'Débat terminé. Synthèse disponible.';
            case 'failed': return 'Le débat a rencontré une erreur.';
            default: return state.status || 'Prêt';
        }
    }

    handleExportDebate(debateState) {
        const markdownContent = this._generateMarkdown(debateState);
        const blob = new Blob([markdownContent], { type: 'text/markdown;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        const safeTopic = debateState.config.topic.replace(/[^a-z0-9]/gi, '_').toLowerCase();
        a.download = `debat_${safeTopic.substring(0, 20)}.md`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        this.eventBus.emit(EVENTS.SHOW_NOTIFICATION, { type: 'success', message: 'Exportation Markdown réussie.' });
    }

    _generateMarkdown(state) {
        const { config, ragContext, history, synthesis } = state;
        const synthesizer = AGENTS[config.agentOrder[config.agentOrder.length - 1]]?.name || 'Nexus';
        let md = `# Débat : ${config.topic}\n\n`;
        md += `- **Participants :** ${config.agentOrder.slice(0, -1).map(id => AGENTS[id]?.name || id).join(', ')}\n`;
        md += `- **Synthèse :** ${synthesizer}\n`;
        md += `- **Rounds :** ${config.rounds}\n`;
        md += `- **RAG Activé :** ${config.useRag ? 'Oui' : 'Non'}\n\n`;
        if (ragContext) {
            md += `## Contexte Documentaire (RAG)\n\n\`\`\`\n${ragContext}\n\`\`\`\n`;
        }
        history.forEach(turn => {
            md += `## Tour ${turn.roundNumber}\n`;
            for (const agentId in turn.agentResponses) {
                const agentName = AGENTS[agentId]?.name || agentId;
                md += `\n### Intervention de ${agentName}\n\n> ${turn.agentResponses[agentId].replace(/\n/g, '\n> ')}\n`;
            }
        });
        if (synthesis) {
            md += `\n## Synthèse Finale par ${synthesizer}\n\n${synthesis}\n`;
        }
        return md.trim();
    }
}
