/**
 * @module features/debate/debate
 * @description Orchestrateur du module Débat - V26.3 "Flux-only Synthèse"
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

        // ⚙️ Désactive la modale de synthèse : rendu "flux" uniquement (DebateUI)
        this.SHOW_SYNTH_MODAL = false;

        console.log("✅ DebateModule V26.3 (Flux-only Synthèse) Prêt.");
    }
    
    init() {
        if (this.isInitialized) return;
        this.ui = new DebateUI(this.eventBus);
        this.registerEvents();
        this.registerStateChanges();
        this.isInitialized = true;
        console.log("✅ DebateModule V26.3 (Flux-only Synthèse) Initialisé UNE SEULE FOIS.");
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
            if (this.container) this.ui.render(this.container, debateState);
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
        const val = this._validateConfig(config);
        if (!val.ok) {
            this.state.set('debate.error', val.reason);
            this.state.set('debate.statusText', val.message);
            this._notify('warning', val.message);
            return;
        }
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

        if (clientState.status === 'in_progress') {
            const lastTurn = clientState.history[clientState.history.length - 1];
            if (lastTurn) this._notify('info', `Tour ${lastTurn.roundNumber} / ${clientState.config.rounds}`);
        } else if (clientState.status === 'completed') {
            this._notify('success', 'Débat terminé — synthèse disponible.');
            this._maybeShowSynthesis(clientState);
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
        const status = payload?.status || 'unknown';
        let msg = payload?.message || '';

        if (status === 'error' || status === 'failed') {
            const reason = payload?.reason || 'unknown_error';
            if (!msg) {
                msg = (reason === 'topic_too_short')
                    ? 'Sujet trop court (minimum 10 caractères).'
                    : 'Erreur lors du démarrage du débat.';
            }
            this.state.set('debate.error', reason);
            this.state.set('debate.statusText', msg);
            this._notify('warning', msg);
            return;
        }

        const text = (status === 'pending')
            ? 'En attente de démarrage…'
            : (status === 'in_progress')
                ? 'Débat en cours…'
                : (status === 'completed')
                    ? 'Débat terminé. Synthèse disponible.'
                    : (msg || status);
        this.state.set('debate.statusText', text);

        if (status === 'completed') {
            const st = this.state.get('debate');
            this._maybeShowSynthesis(st);
        }
    }

    _maybeShowSynthesis(state) {
        const synth = (state && typeof state.synthesis === 'string') ? state.synthesis.trim() : '';
        if (!synth) {
            this._notify('warning', 'Synthèse indisponible (le moteur a renvoyé un contenu vide). Essaie “Exporter”.');
            return;
        }
        // ❌ Plus de modale : on s’appuie sur le rendu “flux” géré par DebateUI.
        if (this.SHOW_SYNTH_MODAL === true) {
            this._showSynthesisModal(synth); // optionnel (dev)
        }
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
            try { console.log(`[${type?.toUpperCase() || 'INFO'}] ${message}`); } catch {}
        }
    }

    // _showSynthesisModal(content) reste dispo mais n'est plus appelé en prod (voir flag SHOW_SYNTH_MODAL).
    _showSynthesisModal(content) {
        const root = document.createElement('div');
        root.setAttribute('role', 'dialog');
        root.ariaLabel = 'Synthèse du débat';
        root.style.position = 'fixed';
        root.style.inset = '0';
        root.style.background = 'rgba(0,0,0,.5)';
        root.style.display = 'flex';
        root.style.alignItems = 'center';
        root.style.justifyContent = 'center';
        root.style.zIndex = '9999';

        const card = document.createElement('div');
        card.style.width = 'min(900px, 92vw)';
        card.style.maxHeight = '80vh';
        card.style.background = 'linear-gradient(180deg, rgba(20,20,24,.96), rgba(14,14,18,.96))';
        card.style.border = '1px solid rgba(255,255,255,.08)';
        card.style.borderRadius = '16px';
        card.style.boxShadow = '0 12px 28px rgba(0,0,0,.35)';
        card.style.padding = '18px 18px 14px';
        card.style.color = '#fff';
        card.style.display = 'flex';
        card.style.flexDirection = 'column';
        card.style.gap = '12px';

        const title = document.createElement('div');
        title.textContent = 'Synthèse du débat';
        title.style.font = '600 18px/1.2 system-ui, -apple-system, Segoe UI, Roboto';
        title.style.letterSpacing = '.2px';

        const pre = document.createElement('pre');
        pre.textContent = content;
        pre.style.whiteSpace = 'pre-wrap';
        pre.style.font = '13px/1.45 ui-monospace, SFMono-Regular, Menlo, Consolas';
        pre.style.margin = '0';
        pre.style.padding = '12px';
        pre.style.borderRadius = '12px';
        pre.style.background = 'rgba(255,255,255,.04)';
        pre.style.overflow = 'auto';
        pre.style.flex = '1 1 auto';

        const actions = document.createElement('div');
        actions.style.display = 'flex';
        actions.style.gap = '8px';
        actions.style.justifyContent = 'flex-end';

        const copyBtn = document.createElement('button');
        copyBtn.textContent = 'Copier';
        copyBtn.className = 'button';
        copyBtn.onclick = async () => {
            try { await navigator.clipboard.writeText(content); this._notify('success','Synthèse copiée.'); }
            catch { this._notify('warning','Impossible de copier.'); }
        };

        const closeBtn = document.createElement('button');
        closeBtn.textContent = 'Fermer';
        closeBtn.className = 'button button-metal';
        closeBtn.onclick = () => root.remove();

        actions.append(copyBtn, closeBtn);
        card.append(title, pre, actions);
        root.append(card);
        document.body.appendChild(root);
    }
}
