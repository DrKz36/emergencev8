import { chromium } from "playwright";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, "..", "..");
const assetsDir = path.join(repoRoot, "docs", "assets", "ui");

const BASE_URL = process.env.EMERGENCE_FRONT_URL ?? "http://127.0.0.1:5173/";
const API_BASE = process.env.EMERGENCE_API_URL ?? "http://127.0.0.1:8000";
const QA_EMAIL = process.env.EMERGENCE_QA_EMAIL ?? "gonzalefernando@gmail.com";
const DATE_STAMP = new Date().toISOString().slice(0, 10).replace(/-/g, "");

async function ensureDir(dir) {
  await fs.mkdir(dir, { recursive: true });
}

async function fetchLoginToken(email) {
  const response = await fetch(`${API_BASE}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email })
  });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`Login failed (${response.status} ${response.statusText}): ${body}`);
  }
  const data = await response.json();
  if (!data?.token) {
    throw new Error(`Login succeeded but no token in payload: ${JSON.stringify(data)}`);
  }
  return data.token;
}

async function captureMetricsOverlay(page, label, filename) {
  await page.evaluate(({ overlayId, labelText }) => {
    const existing = document.getElementById(overlayId);
    if (existing) existing.remove();
    const metrics = window.__EMERGENCE_QA_METRICS__ || {};
    const auth = metrics.authRequired || {};
    const payload = {
      requiredCount: auth.requiredCount ?? 0,
      missingCount: auth.missingCount ?? 0,
      restoredCount: auth.restoredCount ?? 0,
      events: Array.isArray(auth.events) ? auth.events.slice(-6) : []
    };
    const overlay = document.createElement("div");
    overlay.id = overlayId;
    overlay.style.position = "fixed";
    overlay.style.right = "24px";
    overlay.style.bottom = "24px";
    overlay.style.width = "520px";
    overlay.style.maxHeight = "60vh";
    overlay.style.overflow = "auto";
    overlay.style.background = "rgba(15, 23, 42, 0.92)";
    overlay.style.color = "#e2e8f0";
    overlay.style.padding = "18px";
    overlay.style.border = "1px solid rgba(148, 163, 184, 0.6)";
    overlay.style.borderRadius = "14px";
    overlay.style.boxShadow = "0 18px 48px rgba(2, 6, 23, 0.55)";
    overlay.style.fontFamily = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace";
    overlay.style.fontSize = "12px";
    overlay.style.lineHeight = "1.45";
    overlay.style.zIndex = "99999";

    const title = document.createElement("div");
    title.textContent = labelText;
    title.style.fontFamily = "Inter, Segoe UI, system-ui, sans-serif";
    title.style.fontSize = "14px";
    title.style.fontWeight = "600";
    title.style.marginBottom = "10px";
    overlay.appendChild(title);

    const pre = document.createElement("pre");
    pre.textContent = JSON.stringify(payload, null, 2);
    pre.style.margin = "0";
    overlay.appendChild(pre);

    document.body.appendChild(overlay);
  }, { overlayId: "qa-metrics-overlay", labelText: label });

  const overlayLocator = page.locator("#qa-metrics-overlay");
  await overlayLocator.waitFor({ state: "visible", timeout: 5000 }).catch(() => {});
  await overlayLocator.screenshot({ path: filename });
  await page.evaluate(() => {
    const node = document.getElementById("qa-metrics-overlay");
    if (node) node.remove();
  });
}

async function captureState(page, label) {
  const safeLabel = label.replace(/[^a-z0-9-]+/gi, "-").toLowerCase();
  const uiPath = path.join(assetsDir, `home-${safeLabel}-${DATE_STAMP}.png`);
  const consolePath = path.join(assetsDir, `home-${safeLabel}-console-${DATE_STAMP}.png`);

  await page.screenshot({ path: uiPath, fullPage: true });
  await captureMetricsOverlay(page, `QA metrics - ${label}`, consolePath);

  const metrics = await page.evaluate(() => {
    const snapshot = window.__EMERGENCE_QA_METRICS__ || {};
    try { return JSON.parse(JSON.stringify(snapshot)); }
    catch { return snapshot; }
  });

  return { uiPath, consolePath, metrics };
}

async function run() {
  await ensureDir(assetsDir);

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();

  const consoleBuffer = [];
  page.on("console", (msg) => {
    consoleBuffer.push(`[${msg.type()}] ${msg.text()}`);
  });

  // --- Unauthenticated state ---
  await page.goto(BASE_URL, { waitUntil: "networkidle" });
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(1500);

  await page.waitForFunction(() => {
    return document.body.classList.contains('home-active')
      && !!document.querySelector('#home-root [data-role=\"home-form\"]');
  }, { timeout: 15000 }).catch(() => {});

  await page.waitForFunction(() => {
    const metrics = window.__EMERGENCE_QA_METRICS__;
    if (!metrics) return false;
    const events = metrics.authRequired?.events;
    return Array.isArray(events) && events.length > 0;
  }, { timeout: 15000 }).catch(() => {});

  await page.waitForSelector(".notifications-container .notification", { timeout: 8000 }).catch(() => {});
  await page.waitForTimeout(800);

  const unauth = await captureState(page, "auth-required");

  // --- Authenticated state ---
  const token = await fetchLoginToken(QA_EMAIL);
  await page.evaluate((sessionToken) => {
    if (!sessionToken) return;
    try { localStorage.setItem("emergence.id_token", sessionToken); } catch {}
    try { sessionStorage.setItem("emergence.id_token", sessionToken); } catch {}
  }, token);

  await page.reload({ waitUntil: "networkidle" });
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(2000);

  await page.waitForFunction(() => {
    return !document.body.classList.contains('home-active');
  }, { timeout: 20000 }).catch(() => {});

  await page.waitForFunction(() => {
    const metrics = window.__EMERGENCE_QA_METRICS__;
    if (!metrics) return false;
    const auth = metrics.authRequired || {};
    return (auth.restoredCount ?? 0) > 0;
  }, { timeout: 20000 }).catch(() => {});

  await page.waitForTimeout(800);

  const authd = await captureState(page, "authenticated");

  await browser.close();

  const logPath = path.join(assetsDir, `home-console-log-${DATE_STAMP}.txt`);
  await fs.writeFile(logPath, consoleBuffer.join("\n"), "utf8");

  const summary = {
    baseUrl: BASE_URL,
    apiBase: API_BASE,
    emailTested: QA_EMAIL,
    unauth,
    authenticated: authd,
    consoleLog: logPath
  };

  console.log(JSON.stringify(summary, null, 2));
}

run().catch((error) => {
  console.error("[home-qa] failure", error);
  process.exitCode = 1;
});
