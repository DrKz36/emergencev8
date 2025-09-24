// src/frontend/shared/constants.js
// V5.3 - Exporte WS_CONFIG (attendu par main.js) + EVENTS + AGENTS(mapping) + AGENT_IDS
// - URL WS auto-deduite (overrides supportes): localStorage 'em.ws_url', window.EMERGENCE_WS_URL
// - wss:// force si page en https:// ; sinon ws://
// - Aucun impact d'architecture : fichier autonome, aucun import externe

/* ------------------- WS URL Resolver ------------------- */
function resolveWsUrl() {
  try {
    // 1) Overrides (dev/ops)
    const ls = (typeof localStorage !== 'undefined') ? localStorage.getItem('em.ws_url') : null;
    if (ls && typeof ls === 'string' && ls.trim()) return ls.trim();

    const win = (typeof window !== 'undefined') ? window : {};
    const ov = (win && win.EMERGENCE_WS_URL) ? String(win.EMERGENCE_WS_URL) : '';
    if (ov && ov.trim()) return ov.trim();

    // 2) Auto-deduction
    const loc = win.location || { protocol: 'http:', host: '127.0.0.1:8000' };
    const isHttps = String(loc.protocol || '').toLowerCase().startsWith('https');
    const scheme = isHttps ? 'wss' : 'ws';

    // Si on tourne en local sans port precise, garder 8000
    let host = String(loc.host || '').trim() || '127.0.0.1:8000';
    if (!host.includes(':') && !isHttps) host = `${host}:8000`;

    return `${scheme}://${host}/ws`;
  } catch {
    // Fallback raisonnable
    return 'ws://127.0.0.1:8000/ws';
  }
}

/* ------------------- Exports attendus ------------------- */
export const WS_CONFIG = Object.freeze({
  URL: resolveWsUrl(),
});

export const EVENTS = {
  // Core
  APP_READY: 'app:ready',
  MODULE_SHOW: 'module:show',
  MODULE_NAVIGATE: 'app:navigate',

  // WebSocket (client)
  WS_CONNECTED: 'ws:connected',
  WS_SEND: 'ws:send',
  WS_ERROR: 'ws:error',
  SERVER_NOTIFICATION: 'notification',

  // Server push (chat & session)
  WS_SESSION_ESTABLISHED: 'ws:session_established',
  WS_CHAT_STREAM_START: 'ws:chat_stream_start',
  WS_CHAT_STREAM_CHUNK: 'ws:chat_stream_chunk',
  WS_CHAT_STREAM_END: 'ws:chat_stream_end',
  WS_RAG_STATUS: 'ws:rag_status',
  WS_MESSAGE_PERSISTED: 'ws:message_persisted',

  // Server push (debate)
  WS_DEBATE_STARTED: 'ws:debate_started',
  WS_DEBATE_TURN_UPDATE: 'ws:debate_turn_update',
  WS_DEBATE_RESULT: 'ws:debate_result',
  WS_DEBATE_ENDED: 'ws:debate_ended',
  WS_DEBATE_STATUS_UPDATE: 'ws:debate_status_update',

  // UI (chat)
  CHAT_SEND: 'ui:chat:send',
  CHAT_CLEAR: 'ui:chat:clear',
  CHAT_EXPORT: 'ui:chat:export',
  CHAT_EXPORT_SELECTION_CHANGED: 'ui:chat:export_selection_changed',
  CHAT_MODE_TOGGLED: 'ui:chat:mode_toggled',
  CHAT_AGENT_SELECTED: 'ui:chat:agent_selected',
  CHAT_PARALLEL_AGENTS_CHANGED: 'ui:chat:parallel_agents_changed',
  CHAT_RAG_TOGGLED: 'ui:chat:rag_toggled',

  // UI (debate)
  DEBATE_CREATE: 'debate:create',
  DEBATE_RESET: 'debate:reset',
  DEBATE_EXPORT: 'debate:export',

  // Documents
  DOCUMENTS_SELECTION_CHANGED: 'documents:selection_changed',
  DOCUMENTS_CMD_DESELECT: 'documents:cmd:deselect',

  // Threads
  THREADS_LIST_UPDATED: 'threads:list_updated',
  THREADS_SELECTED: 'threads:selected',
  THREADS_CREATED: 'threads:created',
  THREADS_UPDATED: 'threads:updated',
  THREADS_ARCHIVED: 'threads:archived',
  THREADS_ERROR: 'threads:error',
  THREADS_READY: 'threads:ready',
  THREADS_LOADED: 'threads:loaded',
  THREADS_REFRESH_REQUEST: 'threads:refresh',

  // Generic UI helpers
  AUTH_REQUIRED: 'ui:auth:required',
  AUTH_RESTORED: 'ui:auth:restored',
  SHOW_MODAL: 'ui:show_modal',
  SHOW_NOTIFICATION: 'ui:show_notification',
};

export const AGENTS = {
  anima: { id: 'anima', label: 'Anima', color: '#fb7185', cssClass: 'message--anima' },
  neo:   { id: 'neo',   label: 'Neo',   color: '#38bdf8', cssClass: 'message--neo' },
  nexus: { id: 'nexus', label: 'Nexus', color: '#34d399', cssClass: 'message--nexus' },
  global:{ id: 'global', label: 'Global', color: '#facc15', cssClass: 'message--global', isBroadcast: true },
};

// Liste d'IDs utilisable partout (legacy friendly)
export const AGENT_IDS = Object.keys(AGENTS);
export const PRIMARY_AGENT_IDS = AGENT_IDS.filter((id) => id !== 'global');
export const BROADCAST_AGENT_IDS = PRIMARY_AGENT_IDS;


