// src/frontend/features/debate/debate.js
// DebateModule V27.8 — HOLD sticky + anti-recreate global

import { DebateUI } from './debate-ui.js';
import { EVENTS, AGENTS, PRIMARY_AGENT_IDS as _AGENT_IDS } from '../../shared/constants.js';

export default class DebateModule {
  constructor(eventBus, state) {
    this.eventBus = eventBus;
    this.state = state;
    this.ui = null;
    this.container = null;
    this.listeners = [];
    this.isInitialized = false;

    this.HOLD_MS = 30000;    // 30s
    this._completedAt = 0;   // volatile

    console.log('✅ DebateModule V27.8 (sticky HOLD + anti-recreate) prêt.');
  }

  init() {
    if (this.isInitialized) return;
    this.ui = new DebateUI(this.eventBus);
    this.registerEvents();
    this.registerStateChanges();
    if (!this.state.get('debate')) this.reset();
    this.isInitialized = true;
    console.log('✅ DebateModule V27.8 initialisé.');
  }

  mount(container) {
    this.container = container;
    this.ui.render(this.container, this.state.get('debate') || this._blank());
  }
  destroy() {
    this.listeners.forEach(off => { try { off(); } catch {} });
    this.listeners = [];
    this.container = null;
  }

  _blank() {
    return {
      isActive: false,
      debateId: null,
      status: 'idle',
      stage: 'idle',
      statusText: 'Pret a commencer.',
      topic: '',
      config: { topic:'', rounds:3, agentOrder:['neo','nexus','anima'], useRag:true },
      turns: [],
      history: [],
      synthesis: null,
      synthesisMeta: null,
      cost: null,
      ragContext: null,
      error: null,
      holdUntil: 0,          // sticky HOLD (ms epoch)
      currentRound: null,
      currentSpeaker: null,
      currentRole: null
    };
  }
  reset() {
    if (this._inHold()) { console.warn('[Debate] reset() ignoré (hold actif).'); return; }
    this._completedAt = 0;
    this.state.set('debate', this._blank());
  }

  registerStateChanges() {
    const off = this.state.subscribe('debate', (st) => {
      if (this.container) this.ui.render(this.container, st || this._blank());
    });
    this.listeners.push(off);
  }

  registerEvents() {
    // UI → Module
    this.listeners.push(this.eventBus.on(EVENTS.DEBATE_CREATE, (cfg) => this.handleCreateDebate(cfg)));
    this.listeners.push(this.eventBus.on(EVENTS.DEBATE_RESET,   ()   => this._guardedReset('debate:reset')));
    this.listeners.push(this.eventBus.on('debate:new',          ()   => this._guardedReset('debate:new')));

    // WS → Module
    this.listeners.push(this.eventBus.on('ws:debate_started',       (p) => this._applyStarted(p)));
    this.listeners.push(this.eventBus.on('ws:debate_turn_update',   (p) => this._applyTurnUpdate(p)));
    this.listeners.push(this.eventBus.on('ws:debate_result',        (p) => this._applyResult(p)));
    this.listeners.push(this.eventBus.on('ws:debate_ended',         (p) => this._applyEnded(p)));
    this.listeners.push(this.eventBus.on('ws:debate_status_update', (p) => this.onDebateStatusUpdate(p)));

    // Si on revient sur l’onglet Débat pendant HOLD, forcer re-render de l’état complété
    this.listeners.push(this.eventBus.on(EVENTS.MODULE_SHOW || 'module:show', (mod) => {
      if (mod === 'debate' && this._inHold()) {
        const st = this.state.get('debate');
        if (st && st.status === 'completed') this.state.set('debate', { ...st });
      }
    }));
  }

  _now() { return Date.now(); }
  _inHoldVolatile() { return (this._completedAt > 0) && ((this._now() - this._completedAt) < this.HOLD_MS); }
  _inHoldSticky() { const until = Number(this.state.get('debate')?.holdUntil || 0); return until > this._now(); }
  _inHold() { return this._inHoldVolatile() || this._inHoldSticky(); }

  _guardedReset(source) {
    if (this._inHold()) {
      const until = Number(this.state.get('debate')?.holdUntil || 0);
      const left = Math.max(0, Math.ceil((until - this._now())/1000));
      console.warn(`[Debate] ${source} ignoré (hold ${left || 1}s).`);
      return;
    }
    this.reset();
  }

  _normalizeAgentIds(){
    if (Array.isArray(AGENTS)) return AGENTS.map(String);
    const ids = _AGENT_IDS && Array.isArray(_AGENT_IDS) ? _AGENT_IDS : Object.keys(AGENTS||{});
    return ids.map(String);
  }

  _agentLabel(agentId) {
    const key = (agentId || '').toString();
    const entry = AGENTS?.[key];
    if (entry?.label) return entry.label;
    if (entry?.name) return entry.name;
    if (!key) return 'Agent';
    return key.charAt(0).toUpperCase() + key.slice(1);
  }

  _buildStatusText(info = {}) {
    const status = (info.status || info.stage || '').toString();
    const roundNumber = Number.isFinite(info.round) ? Number(info.round) : null;
    const agentId = info.agent ? String(info.agent) : '';
    const role = info.role ? String(info.role) : '';
    if (!status) return '';
    if (status === 'completed') return 'Debat termine.';
    if (status === 'starting') return 'Initialisation du debat...';
    if (status === 'synthesizing') {
      const label = this._agentLabel(agentId || role);
      return `Synthese en cours (${label}).`;
    }
    if (status === 'speaking' || status === 'running') {
      const label = this._agentLabel(agentId || role);
      const prefix = roundNumber ? `Tour ${roundNumber} - ` : '';
      return `${prefix}${label} intervient.`;
    }
    return status.replace(/_/g, ' ').replace(/\w/g, (c) => c.toUpperCase());
  }

  _validateConfig(config) {
    const topic = (config?.topic ?? '').trim();
    if (topic.length < 10) return { ok:false, reason:'topic_too_short',  message:'Sujet trop court (minimum 10 caractères).' };
    const rounds = Number(config?.rounds ?? 3);
    if (!Number.isFinite(rounds) || rounds < 1) return { ok:false, reason:'invalid_rounds', message:'Nombre de tours invalide (≥ 1 requis).' };

    const agentIds = this._normalizeAgentIds();
    const order = Array.isArray(config?.agentOrder) && config.agentOrder.length >= 2
      ? config.agentOrder.slice(0,3).map(String)
      : ['neo','nexus','anima'];
    const allKnown = order.every(a => agentIds.includes(a));
    if (!allKnown) return { ok:false, reason:'invalid_agents', message:'Agents invalides dans agentOrder.' };

    return { ok:true, topic, rounds, order, useRag: !!config?.useRag };
  }

  handleCreateDebate(config) {
    // 🚫 Anti-recreate global pendant HOLD
    if (this._inHold()) {
      const until = Number(this.state.get('debate')?.holdUntil || 0);
      const left = Math.max(0, Math.ceil((until - this._now())/1000));
      this._notify('warning', `Résultats verrouillés ${left || 1}s — patiente avant un nouveau débat.`);
      console.warn('[Debate] debate:create ignoré (hold actif).');
      return;
    }

    const val = this._validateConfig(config);
    if (!val.ok) {
      const st = this.state.get('debate') || this._blank();
      st.statusText = val.message; st.error = val.reason;
      this.state.set('debate', st);
      this._notify('warning', val.message);
      return;
    }

    this._completedAt = 0;
    const st = this._blank();
    st.isActive = false;
    st.status = 'starting';
    st.statusText = 'Création du débat en cours…';
    st.topic = val.topic;
    st.config = { topic: val.topic, rounds: val.rounds, agentOrder: val.order, useRag: val.useRag };
    this.state.set('debate', st);

    try { this.eventBus.emit(EVENTS.MODULE_SHOW || 'module:show', 'debate'); } catch {}

    this.eventBus.emit(EVENTS.WS_SEND || 'ws:send', {
      type: 'debate:create',
      payload: {
        topic: st.config.topic,
        rounds: st.config.rounds,
        agentOrder: st.config.agentOrder,
        useRag: st.config.useRag,
        docIds: this.state.get('chat.selectedDocIds') || []
      }
    });
  }

  onDebateStatusUpdate(payload = {}) {
    const st = this.state.get('debate') || this._blank();
    const stage = (payload?.stage || payload?.status || '').toString();
    if (payload?.topic) st.topic = payload.topic;
    if (stage) {
      st.stage = stage;
      st.status = stage === 'completed' ? 'completed' : 'running';
    }
    if (Number.isFinite(payload?.round)) st.currentRound = Number(payload.round);
    if (payload?.agent) st.currentSpeaker = String(payload.agent);
    if (payload?.role) st.currentRole = String(payload.role);
    const message = payload?.message || this._buildStatusText({
      status: stage,
      stage,
      round: payload?.round,
      agent: payload?.agent,
      role: payload?.role,
    });
    if (message) st.statusText = String(message);
    this.state.set('debate', st);
  }

  _applyStarted(payload = {}) {
    const st = this.state.get('debate') || this._blank();
    st.isActive = true;
    st.stage = payload?.stage || 'starting';
    st.status = 'running';
    const cfg = payload?.config || {};
    st.topic = payload?.topic ?? st.topic;
    st.config = {
      topic: st.topic,
      rounds: Number.isFinite(cfg.rounds) ? Math.max(1, cfg.rounds) : st.config.rounds,
      agentOrder: Array.isArray(cfg.agentOrder) && cfg.agentOrder.length ? cfg.agentOrder.slice(0,3) : st.config.agentOrder,
      useRag: !!(cfg.useRag ?? st.config.useRag)
    };
    if (Number.isFinite(payload?.round)) st.currentRound = Number(payload.round);
    if (payload?.agent) st.currentSpeaker = String(payload.agent);
    if (payload?.role) st.currentRole = String(payload.role);
    st.statusText = payload?.message || this._buildStatusText({
      status: st.stage,
      stage: payload?.stage,
      round: payload?.round,
      agent: payload?.agent,
      role: payload?.role,
    }) || 'Debat lance.';
    st.error = null;
    this.state.set('debate', st);
  }

  _applyTurnUpdate(payload = {}) {
    const st = this.state.get('debate') || this._blank();
    st.isActive = true;
    st.status = 'running';
    st.stage = 'speaking';
    const roundNumber = Number.isFinite(payload?.round) ? Number(payload.round) : null;
    if (roundNumber !== null) st.currentRound = roundNumber;
    const agent = (payload?.agent || '').toString() || 'anima';
    st.currentSpeaker = agent;
    const role = payload?.speaker || payload?.meta?.role || null;
    if (role) st.currentRole = String(role);
    const text = (payload?.text || '').toString();
    if (text) {
      const meta = (payload?.meta && typeof payload.meta === 'object') ? { ...payload.meta } : {};
      if (role && !meta.role) meta.role = role;
      if (roundNumber !== null && typeof meta.round === 'undefined') meta.round = roundNumber;
      st.turns.push({ agent, text, round: roundNumber, meta });
    }
    st.statusText = this._buildStatusText({ status: 'speaking', round: roundNumber, agent, role }) || 'Intervention en cours.';
    this.state.set('debate', st);
  }

  _applyResult(serverData = {}) {
    const next = this._normalizeServerState(serverData);
    next.isActive = false;
    next.status = 'completed';
    next.stage = serverData?.stage || 'completed';
    next.statusText = serverData?.message || (next.synthesis ? 'Debat termine - synthese disponible.' : 'Debat termine.');
    next.currentRound = null;
    next.currentSpeaker = null;
    next.currentRole = null;
    this._completedAt = Date.now();
    next.holdUntil = this._completedAt + this.HOLD_MS;
    this.state.set('debate', next);
    if (next.synthesis) this._notify('success', 'Debat termine - synthese disponible.');
  }

  _applyEnded(serverData = {}) {
    const hasUseful =
      (Array.isArray(serverData.turns) && serverData.turns.length) ||
      (Array.isArray(serverData.history) && serverData.history.length) ||
      (Array.isArray(serverData.rounds_history) && serverData.rounds_history.length) ||
      (typeof serverData.synthesis === 'string' && serverData.synthesis.trim()) ||
      !!(serverData.synthesis && (serverData.synthesis.text || serverData.synthesis.content));
    if (hasUseful) return this._applyResult(serverData);

    const st = this.state.get('debate') || this._blank();
    st.isActive = false;
    st.stage = 'completed';
    st.status = 'completed';
    st.statusText = st.statusText || 'Debat termine.';
    st.currentRound = null;
    st.currentSpeaker = null;
    st.currentRole = null;
    this._completedAt = Date.now();
    st.holdUntil = this._completedAt + this.HOLD_MS;
    this.state.set('debate', st);
  }

  _normalizeServerState(serverData = {}) {
    const prev = this.state.get('debate') || this._blank();
    const cfg = serverData.config || {};
    const config = {
      topic: cfg.topic ?? serverData.topic ?? prev.topic ?? '',
      rounds: Number.isFinite(cfg.rounds) ? Math.max(1, cfg.rounds) : (prev.config?.rounds || 1),
      agentOrder: Array.isArray(cfg.agentOrder) && cfg.agentOrder.length ? cfg.agentOrder.slice(0,3) : (prev.config?.agentOrder || ['neo','nexus','anima']),
      useRag: !!(cfg.useRag ?? (prev.config?.useRag ?? true))
    };

    const raw = Array.isArray(serverData.turns) ? serverData.turns
      : (Array.isArray(serverData.history) ? serverData.history
      : (Array.isArray(serverData.rounds_history) ? serverData.rounds_history : []));
    const turns = Array.isArray(raw)
      ? raw.map((t) => {
          const agent = (t.agent || '').toString() || 'anima';
          const text = (t.text || '').toString();
          if (!text) return null;
          const round = Number.isFinite(t.round) ? Number(t.round) : null;
          const meta = (t.meta && typeof t.meta === 'object') ? { ...t.meta } : {};
          if (round !== null && typeof meta.round === 'undefined') meta.round = round;
          return { agent, text, round, meta };
        }).filter(Boolean)
      : [];

    const syn = typeof serverData.synthesis === 'string'
      ? serverData.synthesis
      : (serverData.synthesis?.text || serverData.synthesis?.content || '');
    const synthesis = (syn && syn.trim()) ? syn : null;
    const synthesisMeta = (serverData.synthesis_meta && typeof serverData.synthesis_meta === 'object')
      ? { ...serverData.synthesis_meta }
      : prev.synthesisMeta;
    const cost = (serverData.cost && typeof serverData.cost === 'object') ? { ...serverData.cost } : prev.cost;
    const stage = typeof serverData.stage === 'string' ? serverData.stage : prev.stage;

    return {
      ...prev,
      topic: config.topic,
      config,
      turns,
      synthesis,
      synthesisMeta,
      cost,
      stage,
    };
  }

  _notify(kind, message) {
    try { this.eventBus.emit(EVENTS.SHOW_NOTIFICATION || 'ui:show_notification', { type: kind, message }); } catch {}
  }
}



