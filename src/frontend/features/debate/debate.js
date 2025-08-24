/**
 * @module features/debate/debate
 * @description Orchestrateur du module Débat - V26.1 "Concordance + Validation"
 * - Pattern init/mount découplé du DOM.
 * - Validation locale du sujet (topic.trim().length >= 10).
 * - Feedback utilisateur clair (toast + statusText) y.c. erreurs WS.
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
        console.log("✅ DebateModule V26.1 (Concordance + Validation) Prêt.");
    }
    
    init() {
        if (this.isInitialized) return;
        this.ui = new DebateUI(this.eventBus);
        this.registerEvents();
        this.registerStateChanges();
        this.isInitialized = true;
        console.log("✅ DebateModule V26.1 (Concordance + Validation) Initialisé UNE SEULE FOIS.");
    }

    mount(container) {
        this.container = container;
        this.ui.render(this.container, this.state.get('debate'));
    }

    destroy() {
        this.listeners.forEach(unsubscribe => { try { unsubscribe(); } catch {} });
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

    /* --------------------------------- State --------------------------------- */

    reset() {
        this.state.set('debate', {
            isActive: false,
            debateId: null,
            status: null,
            statusText: 'Prêt à commencer.',
            config: null,
            history: [],
            synthesis: null,
            ragContext: null,
            error: null,
        });
    }

    /* ------------------------------- Validation ------------------------------ */

    _validateConfig(config) {
        const topic = (config?.topic ?? '').trim();
        if (topic.length < 10) {
            return { ok: false, reason: 'topic_too_short', message: 'Sujet trop court (minimum 10 caractères).' };
        }
        const rounds = Number(config?.rounds ?? 3);
        if (!Number.isFinite(rounds) || rounds < 1) {
            return { ok: false, reason: 'invalid_rounds', message: 'Nombre de tours invalide (≥ 1 requis).' };
        }
        return { ok: true, topic, rounds };
    }

    /* -------------------------------- Handlers -------------------------------- */

    handleCreateDebate(config) {
        // 1) Validation locale (évite un aller/retour WS inutile + erreur Pydantic)
        const val = this._validateConfig(config);
        if (!val.ok) {
            this.state.set('debate.error', val.reason);
            this.state.set('debate.statusText', val.message);
            this._notify('warning', val.message);
            return;
        }

        // 2) Reset propre et démarrage
        this.reset();
        const sanitized = {
            topic: val.topic,
            rounds: val.rounds,
            agentOrder: Array.isArray(config?.agentOrder) ? config.agentOrder : [],
            useRag: !!config?.useRag,
        };
        this.state.set('debate.statusText', 'Création du débat en cours…');
        this.eventBus.emit(EVENTS.WS_SEND, { type: "debate:create", payload: sanitized });
    }

    handleServerUpdate(serverState) {
        const clientState = this._normalizeServerState(serverState);
        this.state.set('debate', clientState);
        // Petits messages d’avancement
        if (clientState.status === 'in_progress') {
            const lastTurn = clientState.history[clientState.history.length - 1];
            if (lastTurn) this._notify('info', `Tour ${lastTurn.roundNumber} / ${clientState.config.rounds}`);
        } else if (clientState.status === 'completed') {
            this._notify('success', 'Débat terminé — synthèse disponible.');
        }
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
            error: null
        };
        normalized.statusText = this.getHumanReadableStatus(normalized);
        return normalized;
    }

    onDebateStatusUpdate(payload) {
        // Payload attendu: { status: 'pending'|'in_progress'|'completed'|'failed'|'error', reason?, message? }
        const status = payload?.status || 'unknown';
        let msg = payload?.message || '';

        if (status === 'error' || status === 'failed') {
            const reason = payload?.reason || 'unknown_error';
            if (!msg) {
                // mapping minimal des raisons connues
                msg = (reason === 'topic_too_short')
                    ? 'Sujet trop court (minimum 10 caractères).'
                    : 'Erreur lors du démarrage du débat.';
            }
            this.state.set('debate.error', reason);
            this.state.set('debate.statusText', msg);
            this._notify('warning', msg);
            return;
        }

        // Statuts non erronés → mise à jour textuelle légère
        const text = (status === 'pending')
            ? 'En attente de démarrage…'
            : (status === 'in_progress')
                ? 'Débat en cours…'
                : (status === 'completed')
                    ? 'Débat terminé. Synthèse disponible.'
                    : (msg || status);
        this.state.set('debate.statusText', text);
        if (status === 'completed') this._notify('success', 'Débat terminé — synthèse disponible.');
    }

    getHumanReadableStatus(state) {
        if (!state) return '';
        switch(state.status) {
            case 'pending': return 'En attente de démarrage…';
            case 'in_progress': {
                const lastTurn = state.history[state.history.length - 1];
                return lastTurn ? `Tour ${lastTurn.roundNumber} / ${state.config.rounds}` : 'Débat en cours…';
            }
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
        this._notify('success', 'Exportation Markdown réussie.');
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

    /* ------------------------------ Helpers UI ------------------------------ */

    _notify(type, message) {
        try {
            this.eventBus.emit(EVENTS.SHOW_NOTIFICATION, { type: type || 'info', message: message || '' });
        } catch (e) {
            // fallback ultra-léger si le système de notif n'est pas monté
            try { console.log(`[${type?.toUpperCase() || 'INFO'}] ${message}`); } catch {}
        }
    }
}
