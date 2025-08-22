// src/frontend/lib/gis.js
const GIS_SRC = "https://accounts.google.com/gsi/client";
const TOKEN_KEY = "google_id_token";

function resolveClientId() {
  // 1) main.js legacy
  const legacy = (window.EMERGENCE_GOOGLE_CLIENT_ID || "").trim();
  if (legacy) return legacy;
  // 2) __CONFIG
  const cfg = (window.__CONFIG && window.__CONFIG.GOOGLE_CLIENT_ID) || "";
  if (cfg) return cfg;
  // 3) <meta>
  const meta = document.querySelector('meta[name="google-signin-client_id"]')?.content || "";
  return meta;
}

export function getStoredIdToken() {
  return sessionStorage.getItem(TOKEN_KEY) || localStorage.getItem(TOKEN_KEY) || "";
}

export function storeIdToken(token) {
  try { sessionStorage.setItem(TOKEN_KEY, token); } catch {}
}

export function clearIdToken() {
  try { sessionStorage.removeItem(TOKEN_KEY); } catch {}
  try { localStorage.removeItem(TOKEN_KEY); } catch {}
}

export async function loadGIS() {
  if (window.google?.accounts?.id) return;
  let s = document.querySelector('script[data-gsi]');
  if (!s) {
    s = document.createElement("script");
    s.src = GIS_SRC; s.async = true; s.defer = true; s.dataset.gsi = "1";
    document.head.appendChild(s);
  }
  await new Promise((resolve, reject) => {
    const t0 = Date.now();
    const timer = setInterval(() => {
      if (window.google?.accounts?.id) { clearInterval(timer); resolve(); }
      else if (Date.now() - t0 > 10000) { clearInterval(timer); reject(new Error("[GIS] Timeout")); }
    }, 50);
  });
}

export async function ensureIdToken({ promptIfNeeded = true } = {}) {
  const cached = getStoredIdToken();
  if (cached) return cached;

  await loadGIS();
  const client_id = resolveClientId();
  if (!client_id) throw new Error("[GIS] client_id introuvable (EMERGENCE_GOOGLE_CLIENT_ID / __CONFIG / <meta>).");

  return await new Promise((resolve, reject) => {
    try {
      google.accounts.id.initialize({
        client_id,
        callback: (resp) => {
          if (resp?.credential) { storeIdToken(resp.credential); resolve(resp.credential); }
          else reject(new Error("[GIS] Aucun credential"));
        },
        ux_mode: "popup", // local: évite soucis FedCM
        auto_select: false,
      });
      if (promptIfNeeded) {
        google.accounts.id.prompt((notif) => {
          if (notif?.isNotDisplayed?.()) console.warn("[GIS] prompt non affiché:", notif.getNotDisplayedReason?.());
          if (notif?.isSkippedMoment?.()) console.warn("[GIS] prompt ignoré:", notif.getSkippedReason?.());
        });
      }
    } catch (e) { reject(e); }
  });
}
