// ÉMERGENCE — API Client v3 (GIS Bearer + retry 401)
import { ensureIdToken, getStoredIdToken, clearIdToken } from "./gis.js";

const API_BASE = "/api";

function normPath(path) {
  if (!path) return API_BASE + "/";
  if (path.startsWith("http://") || path.startsWith("https://")) return path;
  if (path.startsWith("/api/")) return path;
  if (path.startsWith("/")) return "/api" + path;
  return API_BASE + (path.startsWith("/") ? path : "/" + path);
}

async function withAuthHeaders(headers = {}) {
  const h = new Headers(headers);
  let token = getStoredIdToken();
  if (!token) {
    try { token = await ensureIdToken({ promptIfNeeded: true }); }
    catch (e) { console.warn("[API Client] Impossible d’obtenir un ID token via GIS:", e); }
  }
  if (token) h.set("Authorization", "Bearer " + token);
  return h;
}

async function coreFetch(path, options = {}, _retry = false) {
  const url = normPath(path);
  const headers = await withAuthHeaders(options.headers);
  const res = await fetch(url, { ...options, headers, credentials: "include" });

  if (res.status === 401 && !_retry) {
    console.warn(`[API Client] 401 sur ${path} → flush token + retry`);
    clearIdToken();
    const headers2 = await withAuthHeaders(options.headers);
    const res2 = await fetch(url, { ...options, headers: headers2, credentials: "include" });
    return res2;
  }
  return res;
}

/** API générique — garde la signature fetchApi(path, opts) */
export async function fetchApi(path, opts = {}) {
  const res = await coreFetch(path, opts);
  if (!res.ok) {
    let detail = "";
    try { detail = await res.text(); } catch {}
    console.error(`[API Client] Erreur sur l'endpoint ${normPath(path)}: ${detail || res.statusText}`);
    throw new Error(detail || res.statusText);
  }
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) return res.json();
  return res.text();
}

/** Helpers confort */
export async function getJson(path) {
  return fetchApi(path, { method: "GET", headers: { "Accept": "application/json" } });
}

export async function postJson(path, body) {
  return fetchApi(path, {
    method: "POST",
    headers: { "Content-Type": "application/json", "Accept": "application/json" },
    body: JSON.stringify(body ?? {})
  });
}

export async function uploadFile(path, file, fields = {}) {
  const fd = new FormData();
  fd.append("file", file);
  for (const [k, v] of Object.entries(fields)) fd.append(k, v);
  return fetchApi(path, { method: "POST", body: fd });
}
