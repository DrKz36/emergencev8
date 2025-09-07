/**
 * @module features/debate/debate
 * Orchestrateur du module Débat - V26.8
 * - Anti-dup WS (throttle)
 * - Gestion 401/WS error -> statusText explicite
 * - Validation agentOrder (AGENTS)
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
    this.SHOW_SYNTH_MODAL = false;

    // Anti-dup WS
    this._lastSig = null;
    this._lastSigAt = 0;
    this._dupWindowMs = 250;

    console.log('✅ DebateModule V26.8 (robust WS + auth) prêt.');
  }

  init() {
    if (this.isInitialized) return;
    this.ui = new DebateUI(this.eventBus);
    this.registerEvents();
    this.registerStateChanges();
    this.isInitialized = true;
    console.log('✅ DebateModule V26.8 initialisé.');
  }

  mount(container) {
    this.container = container;
    this.ui.render(this.container, this.state.get('debate'));
  }

  destroy() {
    this.listeners.forEach(off => { try { off(); } catch {} });
    this.listeners = [];
    this.container = null;
  }

  registerStateChanges() {
    const off = this.state.subscribe('debate', (st) => {
      if (this.container) this.ui.render(this.container, st);
    });
    this.listeners.push(off);
  }

  registerEvents() {
    this.listeners.push(this.eventBus.on('debate:create', this.handleCreateDebate.bind(this)));
    this.listeners.push(this.eventBus.on('debate:reset', this.reset.bind(this)));
    this.listeners.push(this.eventBus.on('debate:export', this.handleExportDebate.bind(this)));

    // Flux serveur
    const onUpdate = this.handleServerUpdate.bind(this);
    this.listeners.push(this.eventBus.on('ws:debate_started', onUpdate));
    this.listeners.push(this.eventBus.on('ws:debate_turn_update', onUpdate));
    this.listeners.push(this.eventBus.on('ws:debate_result', onUpdate));
    this.listeners.push(this.eventBus.on('ws:debate_ended', onUpdate));
    this.listeners.push(this.eventBus.on('ws:debate_status_update', this.onDebateStatusUpdate.bind(this)));

    // Gestion erreurs/auth
    this.listeners.push(this.eventBus.on('ws:error', (payload) => {
      const msg = payload?.message || 'Erreur temps réel.';
      const st = this.state.get('debate') || {};
      st.status = 'error';
      st.statusText = msg;
      st.error = payload || { message: msg };
      this.state.set('debate', st);
    }));
    this.listeners.push(this.eventBus.on('auth:missing', () => {
      const st = this.state.get('debate') || {};
      st.status = 'pending';
      st.statusText = 'Authentification requise pour lancer un débat.';
      this.state.set('debate', st);
    }));
  }

  /* ------------------------------- State ------------------------------- */
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

  /* ----------------------------- Validation ---------------------------- */
  _validateConfig(config) {
    const topic = (config?.topic ?? '').trim();
    if (topic.length < 10) {
      return { ok: false, reason: 'topic_too_short', message: 'Sujet trop court (minimum 10 caractères).' };
    }
    const rounds = Number(config?.rounds ?? 3);
    if (!Number.isFinite(rounds) || rounds < 1) {
      return { ok: false, reason: 'invalid_rounds', message: 'Nombre de tours invalide (≥ 1 requis).' };
    }

    // Sanitize agentOrder contre AGENTS
    let order = Array.isArray(config?.agentOrder) ? config.agentOrder.filter(Boolean) : [];
    if (order.length) {
      order = order.filter(a => Object.prototype.hasOwnProperty.call(AGENTS || {}, a));
    }

    return { ok: true, topic, rounds, order };
  }

  /* ------------------------------- Handlers ---------------------------- */
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
      agentOrder: val.order,
      useRag: !!config?.useRag,
    };
    this.state.set('debate.statusText', 'Création du débat en cours…');
    this.eventBus.emit(EVENTS.WS_SEND, { type: 'debate:create', payload: sanitized });
  }

  handleServerUpdate(serverState) {
    // Anti-dup: signature légère (status + tour le plus récent)
    try {
      const now = Date.now();
      const lastTurn = (serverState?.history || [])[serverState?.history?.length - 1] || {};
      const sig = `${serverState?.status}|${lastTurn?.round_number ?? lastTurn?.round ?? ''}|${serverState?.synthesis ? 1 : 0}`;
      if (sig === this._lastSig && (now - this._lastSigAt) < this._dupWindowMs) return;
      this._lastSig = sig; this._lastSigAt = now;
    } catch {}

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

  onDebateStatusUpdate(payload) {
    const txt = payload?.message || payload?.status || '';
    const st = this.state.get('debate') || {};
    st.statusText = txt;
    this.state.set('debate', st);
  }

  /* ----------------------------- Normalisation ------------------------- */
  _normalizeServerState(serverData = {}) {
    const turnsRaw = serverData.history || serverData.turns || serverData.rounds_history || [];
    const history = (Array.isArray(turnsRaw) ? turnsRaw : []).map((turn, idx) => ({
      roundNumber: turn?.round_number ?? turn?.round ?? turn?.idx ?? (idx + 1),
      agentResponses: turn?.agent_responses ?? turn?.responses ?? turn?.agents ?? {}
    }));

    const cfg = serverData.config || {};
    const config = {
      topic: cfg.topic ?? cfg.subject ?? '',
      rounds: cfg.rounds ?? cfg.n_rounds ?? cfg.round_count ?? Math.max(1, history.length),
      agentOrder: cfg.agent_order ?? cfg.agentOrder ?? cfg.agents ?? [],
      useRag: (cfg.use_rag ?? cfg.useRag) === true
    };

    const pickSynth = (s) => {
      if (!s) return '';
      if (typeof s === 'string') return s;
      if (typeof s === 'object') return s.text || s.content || s.markdown || '';
      return '';
    };
    let synthesis = pickSynth(
      serverData.synthesis ??
      serverData.final_synthesis ??
      serverData.summary ??
      serverData.finalSummary ??
      serverData.synthese
    );

    const isPoor = (s) => (typeof s !== 'string') || s.trim().length < 20 || ((s.match(/\n/g) || []).length < 2);
    if (isPoor(synthesis)) synthesis = this._buildFallbackSynthesis({ config, history }) || synthesis;

    const ragContext = serverData.rag_context ?? serverData.ragContext ?? serverData.context ?? null;

    const normalized = {
      debateId: serverData.debate_id ?? serverData.id ?? null,
      status: serverData.status ?? serverData.state ?? 'unknown',
      config, history, synthesis, ragContext,
      isActive: ['in_progress', 'pending'].includes(serverData.status),
      error: null
    };
    normalized.statusText = this.getHumanReadableStatus(normalized);
    return normalized;
  }

  _buildFallbackSynthesis({ config, history }) {
    try {
      const shots = history.slice(-2);
      const lines = shots.flatMap((t, i) => {
        const ord = Array.isArray(config?.agentOrder) && config.agentOrder.length
          ? config.agentOrder : Object.keys(t.agentResponses || {});
        const parts = ord.map(a => t.agentResponses?.[a]).filter(Boolean);
        return [`• Tour ${Number(t.roundNumber) || i + 1} :`, ...parts.map(p => `  – ${String(p).slice(0, 160)}…`)];
      });
      return lines.join('\n');
    } catch { return ''; }
  }

  getHumanReadableStatus(st) {
    switch (st?.status) {
      case 'pending':      return 'Préparation du débat…';
      case 'in_progress':  return 'Débat en cours…';
      case 'completed':    return 'Synthèse disponible.';
      default:             return st?.statusText || 'Prêt';
    }
  }

  _maybeShowSynthesis(/* state */) { /* rendu inline : pas de modale */ }

  _notify(kind, message) {
    try { window?.showToast?.({ kind, text: message }); } catch {}
  }

  handleExportDebate() {
    const st = this.state.get('debate') || {};
    const lines = [];
    lines.push(`# Sujet du débat\n\n${st?.config?.topic || st?.topic || '—'}\n`);
    for (const [i, t] of (st.history || []).entries()) {
      lines.push(`\n## Tour ${Number(t.roundNumber) || i + 1}\n`);
      const ord = Array.isArray(st?.config?.agentOrder) && st.config.agentOrder.length
        ? st.config.agentOrder : Object.keys(t.agentResponses || {});
      for (const a of ord) {
        if (t.agentResponses?.[a]) {
          const name = AGENTS?.[a]?.name || a;
          lines.push(`\n### ${name}\n\n${t.agentResponses[a]}\n`);
        }
      }
    }
    if (st.synthesis) {
      lines.push(`\n## Synthèse\n\n${st.synthesis}\n`);
    }
    const blob = new Blob([lines.join('\n')], { type: 'text/markdown;charset=utf-8' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'debate.md';
    a.click();
    URL.revokeObjectURL(a.href);
  }
}
