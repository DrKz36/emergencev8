/**
 * @module core/main
 * Point d'entrée universel — PROD sans bundler : aucun import CSS ici.
 */
import { App } from './core/app.js';
import { EventBus } from './core/event-bus.js';
import { StateManager } from './core/state-manager.js';
import { WebSocketClient } from './core/websocket.js';
import { WS_CONFIG, EVENTS } from './shared/constants.js';
import { setGisClientId, ensureAuth, getIdToken } from './core/auth.js';

/* ---------------- WS-first Chat dedupe & reroute (main.js patch V1) ----------------
   (inchangé vs base) */
(function () {
  try {
    const EB = (typeof EventBus !== 'undefined') ? EventBus : null;
    if (!EB || EB.__patched_dedupe_reroute) return;
    const proto = EB.prototype;
    const origEmit = proto.emit;
    let streamOpen = false;
    const seen = new Set();
    proto.emit = function(name, payload) {
      if (name === 'ws:chat_stream_start') { streamOpen = true; }
      else if (name === 'ws:chat_stream_end' || name === 'ws:close') { streamOpen = false; }
      if (name === 'ui:chat:send') {
        const p = payload || {};
        const enriched = (p && p.__enriched === true);
        if (!enriched && streamOpen) { console.warn('[Guard/WS] ui:chat:send ignoré (stream en cours).'); return; }
        if (enriched) {
          const uid = p.msg_uid || '';
          if (uid && seen.has(uid)) { console.warn('[Guard/Dedupe] dupe:', uid); return; }
          if (uid) { seen.add(uid); setTimeout(() => seen.delete(uid), 30000); }
          return origEmit.call(this, 'ws:send', { type:'chat.message', payload:{ text:p.text, agent_id:p.agent_id, use_rag:!!p.use_rag } });
        }
      }
      return origEmit.call(this, name, payload);
    };
    EB.__patched_dedupe_reroute = true;
    console.info('[main.js patch] WS-first Chat dedupe & reroute appliqué.');
  } catch (e) { console.error('[main.js patch] échec du patch', e); }
})();

/* ---------------- Helpers token (legacy compat minimal) ---------------- */
function getCookie(name) {
  const m = document.cookie.match(new RegExp('(?:^|; )' + name + '=([^;]*)'));
  return m ? decodeURIComponent(m[1]) : null;
}
function pickTokenFromLocation() {
  const blob = (window.location.hash || '') + '&' + (window.location.search || '');
  const m = blob.match(/(?:^|[?#&])(id_token|token)=([^&#]+)/i);
  return m ? decodeURIComponent(m[2]) : '';
}
function saveToken(tok) {
  if (!tok) return;
  try { localStorage.setItem('emergence.id_token', tok); } catch {}
  try { localStorage.setItem('id_token', tok); } catch {}
}
function hasAnyToken() {
  try {
    const z = (localStorage.getItem('emergence.id_token') || localStorage.getItem('id_token') ||
               sessionStorage.getItem('id_token') || getCookie('id_token') || '').trim();
    return !!z;
  } catch { return false; }
}
function isLocalHost() {
  const h = (window.location && window.location.hostname || '').toLowerCase();
  return h === 'localhost' || h === '127.0.0.1' || h === '0.0.0.0';
}

/* ---------------------- Toast minimal (identique) ---------------------- */
function mountToastHost(){let h=document.getElementById('toast-host');if(h)return h;h=document.createElement('div');h.id='toast-host';h.style.cssText='position:fixed;bottom:16px;right:16px;z-index:2147483647;display:flex;flex-direction:column;gap:8px;pointer-events:none';document.body.appendChild(h);return h;}
function showToast({ kind='info', text='' }={}){const host=mountToastHost();const card=document.createElement('div');card.role='status';card.style.cssText='min-width:260px;max-width:420px;padding:.6rem .8rem;border-radius:12px;background:#111a;color:#eee;border:1px solid #333;box-shadow:0 10px 30px rgba(0,0,0,.45);pointer-events:auto';const chip=kind==='warning'?'#f59e0b':(kind==='error'?'#ef4444':'#22c55e');card.innerHTML=`<div style="display:flex;align-items:center;gap:.6rem"><span style="width:10px;height:10px;border-radius:50%;background:${chip};display:inline-block"></span><div style="font-family:system-ui,Segoe UI,Roboto,Arial;font-size:.95rem;line-height:1.3">${text}</div></div>`;host.appendChild(card);setTimeout(()=>{try{card.remove();}catch{}},3200);}

/* ---------------------- Guards EventBus (identique) -------------------- */
function installEventBusGuards(eventBus){if(!eventBus||eventBus.__guardsInstalled)return;eventBus.__guardsInstalled=true;let inFlight=false;eventBus.on?.('ws:chat_stream_start',()=>{inFlight=true;});eventBus.on?.('ws:chat_stream_end',()=>{inFlight=false;});const UI_DEDUP_MS=800,WS_DEDUP_MS=30000;let lastUiAt=0,lastUiTxtN='';let lastWsAt=0,lastWsTxtN='',lastWsUid='';const origEmit=eventBus.emit?.bind(eventBus);eventBus.emit=function(name,payload){if(name!=='ui:chat:send'){return origEmit?origEmit(name,payload):undefined;}const now=Date.now();const INVISIBLES_RE=/[\u200B-\u200D\uFEFF\u00A0]/g,CURSOR_GLYPHS_RE=/[▍▌▎▏▮▯█]+$/,BLOCKS_RE=/[\u2580-\u259F\u25A0-\u25FF]+$/;const normalize=(s)=>String(s||'').replace(INVISIBLES_RE,'').replace(CURSOR_GLYPHS_RE,'').replace(BLOCKS_RE,'').replace(/\s+/g,' ').trim();const enriched=!!(payload&&(payload.__enriched||payload.msg_uid));if(!enriched){const txtN=normalize((payload&&(payload.text||payload.content))||'');if(txtN&&txtN===lastUiTxtN&&(now-lastUiAt)<UI_DEDUP_MS){console.warn('[Guard/UI] ui:chat:send ignoré (double submit court).');return;}lastUiAt=now;lastUiTxtN=txtN;return origEmit?origEmit(name,payload):undefined;}else{const txtN=normalize((payload&&(payload.text||payload.content))||'');const uid=String((payload&&(payload.msg_uid||payload.uid||payload.id))||'');if(inFlight){console.warn('[Guard/WS] ui:chat:send ignoré (stream en cours).');return;}if(uid&&uid===lastWsUid&&(now-lastWsAt)<WS_DEDUP_MS){console.warn('[Guard/WS] dupe uid <30s:',uid);return;}if(!uid&&txtN&&txtN===lastWsTxtN&&(now-lastWsAt)<WS_DEDUP_MS){console.warn('[Guard/WS] dupe texte <30s:',txtN);return;}lastWsAt=now;lastWsUid=uid||lastWsUid;lastWsTxtN=txtN;return origEmit?origEmit(name,payload):undefined;}};const origOn=eventBus.on?.bind(eventBus);const seenHandlers=new WeakSet();eventBus.on=function(name,handler){if(name==='ui:chat:send'&&handler){if(seenHandlers.has(handler)){console.warn('[Guard] listener ui:chat:send ignoré (déjà enregistré).');return this;}seenHandlers.add(handler);}return origOn?origOn(name,handler):this;};const cleanCursorGlyphs=()=>{try{const cands=document.querySelectorAll('[data-role="assistant"], .assistant, .message.assistant, [data-message-role="assistant"]');const re=new RegExp(`${/[▍▌▎▏▮▯█]+$/.source}|${/[\u2580-\u259F\u25A0-\u25FF]+$/.source}`,'g');cands.forEach(el=>{const walker=document.createTreeWalker(el,NodeFilter.SHOW_TEXT,null,false);let t;while((t=walker.nextNode())){const before=t.nodeValue;const after=before&&before.replace(re,'');if(after!==before)t.nodeValue=after;}});}catch{}};eventBus.on?.('ws:chat_stream_end',()=>{cleanCursorGlyphs();setTimeout(cleanCursorGlyphs,30);requestAnimationFrame(cleanCursorGlyphs);});console.debug('[Guard] EventBus guards V3 installés.');}

/* --------------- Badge Login (identique fonctionnel) ------------------- */
function mountAuthBadge(eventBus){const host=document.body;let box=document.getElementById('auth-badge');if(!box){box=document.createElement('div');box.id='auth-badge';box.style.cssText='position:fixed;top:12px;right:12px;z-index:2147483647;display:flex;gap:.5rem;align-items:center;font-family:system-ui,Segoe UI,Roboto,Arial;color:#eee;pointer-events:auto;';box.innerHTML=`<span id="auth-dot" style="width:10px;height:10px;border-radius:50%;background:#f97316;display:inline-block"></span><button id="auth-btn" type="button" style="padding:.35rem .75rem;border-radius:999px;border:1px solid #666;background:#111;color:#eee;cursor:pointer;pointer-events:auto">Se connecter</button><span id="model-chip" style="display:none;padding:.2rem .5rem;border-radius:999px;border:1px solid #555;background:#0b0b0b;color:#ddd;font-size:.8rem"></span>`;host.appendChild(box);}const dot=box.querySelector('#auth-dot');const btn=box.querySelector('#auth-btn');const chip=box.querySelector('#model-chip');const setConnected=(ok)=>{if(dot)dot.style.background=ok?'#22c55e':'#f97316';};const setLogged=(logged)=>{if(!btn)return;btn.textContent=logged?'Se déconnecter':'Se connecter';btn.onclick=logged?()=>eventBus.emit('auth:logout'):()=>{eventBus.emit('auth:login',{});setTimeout(()=>{if(!getIdToken()&& !hasAnyToken()){try{window.open('/dev-auth.html','_blank','noopener');}catch{}}},300);};};const setModel=(provider,model,fallback=false)=>{if(!chip)return;const txt=provider&&model?`${provider} • ${model}${fallback?' (fallback)':''}`:'';chip.textContent=txt;chip.style.display=txt?'inline-block':'none';};eventBus.on?.('auth:missing',()=>{setLogged(false);setConnected(false);});eventBus.on?.('auth:logout',()=>{setLogged(false);setConnected(false);});eventBus.on?.(EVENTS.WS_CONNECTED||'ws:connected',()=>{setLogged(true);setConnected(true);});eventBus.on?.('ws:close',()=>{setConnected(false);});eventBus.on?.('chat:model_info',(p)=>{if(p)setModel(p.provider,p.model,false);});eventBus.on?.('chat:last_message_meta',(m)=>{if(m)setModel(m.provider,m.model,!!m.fallback);});try{if(!window.__em_auth_listeners__){window.addEventListener('storage',(ev)=>{if(ev.key==='emergence.id_token'||ev.key==='id_token'){const has=!!(ev.newValue&&ev.newValue.trim());setLogged(has);}});window.__em_auth_listeners__=true;}}catch{}setLogged(!!getIdToken()||hasAnyToken());setConnected(false);return{setLogged,setConnected};}

/* -------------------- App bootstrap -------------------- */
class EmergenceClient {
  constructor() { this.initialize(); }

  async initialize() {
    console.log("🚀 ÉMERGENCE - Lancement du client.");
    const eventBus = new EventBus();
    installEventBusGuards(eventBus);

    // Configure GIS clientId depuis <meta>, si présent
    try {
      const meta = document.querySelector('meta[name="google-signin-client_id"]');
      if (meta && meta.content) setGisClientId(meta.content.trim());
    } catch {}

    const stateManager = new StateManager();
    await stateManager.init();

    // Toasts
    eventBus.on('ui:toast', (p) => { if (p?.text) showToast(p); });

    const badge = mountAuthBadge(eventBus);

    const websocket = new WebSocketClient(WS_CONFIG.URL, eventBus, stateManager);
    eventBus.on(EVENTS.APP_READY, () => this.hideLoader());

    const app = new App(eventBus, stateManager);

    // ====== Auth avant WS ======
    const tokenFromUrl = pickTokenFromLocation();
    if (tokenFromUrl) saveToken(tokenFromUrl);

    // Auth silencieuse (One-Tap ou storage) avant d'ouvrir le WS
    try {
      await ensureAuth({ interactive: isLocalHost() }); // en local, autorise dev-auth fallback
    } catch {}

    const hasToken = !!getIdToken() || hasAnyToken();
    if (hasToken) {
      try { websocket.connect(); } catch (e) { console.error('[WS] connect error', e); }
    } else {
      try { eventBus.emit('auth:missing'); } catch {}
      // Sync multi-onglets → connexion automatique dès qu’un token apparaît
      const onStorage = (ev) => {
        if (ev.key === 'emergence.id_token' || ev.key === 'id_token') {
          if (ev.newValue && ev.newValue.trim()) {
            window.removeEventListener('storage', onStorage);
            try { websocket.connect(); } catch (e) { console.error('[WS] connect error', e); }
          }
        }
      };
      window.addEventListener('storage', onStorage);
    }

    console.log("✅ Client ÉMERGENCE prêt. En attente du signal APP_READY...");
  }

  hideLoader() {
    const loader = document.getElementById('app-loader');
    if (!loader) return;
    loader.classList.add('fade-out');
    setTimeout(() => { try { loader.remove(); } catch {} document.body.classList.remove('loading'); }, 300);
  }
}

/* ---------- Boot guard ---------- */
(function bootOnce() {
  const FLAG = '__emergence_boot_v25_4__';
  if (window[FLAG]) { console.warn('[Boot] Client déjà initialisé — second bootstrap ignoré.'); return; }
  window[FLAG] = true;
  window.emergenceApp = new EmergenceClient();
})();
