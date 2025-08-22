// ÉMERGENCE — Threads List (auto-registration dans la nav + montage tab)
import { threadsStore } from './use-threads.js';

const TAB_ID = 'tab-threads';

function $(sel, root = document) { return root.querySelector(sel); }
function $all(sel, root = document) { return Array.from(root.querySelectorAll(sel)); }

function formatDateTime(d) {
  try {
    const date = typeof d === 'string' || typeof d === 'number' ? new Date(d) : d;
    return new Intl.DateTimeFormat('fr-CH', { day: '2-digit', month: '2-digit', year: 'numeric',
      hour: '2-digit', minute: '2-digit' }).format(date).replace(',', '');
  } catch { return ''; }
}

function ensureNav() {
  // Sidebar
  const sidebarNav = $('.sidebar-nav') || $('#app-tabs');
  if (sidebarNav && !sidebarNav.querySelector('[data-nav="threads"]')) {
    const li = document.createElement('li');
    const a = document.createElement('button');
    a.className = 'nav-link'; a.dataset.nav = 'threads';
    a.innerHTML = `<span class="nav-icon">🗂️</span><span class="nav-text">Threads</span>`;
    a.addEventListener('click', () => activateTab());
    li.appendChild(a); sidebarNav.appendChild(li);
  }
  // Header (mobile)
  const headerNav = $('.header-nav');
  if (headerNav && !headerNav.querySelector('[data-nav="threads"]')) {
    const b = document.createElement('button');
    b.className = 'header-nav-button'; b.dataset.nav = 'threads'; b.title = 'Threads';
    b.innerHTML = `🗂️`;
    b.addEventListener('click', () => activateTab());
    headerNav.appendChild(b);
  }
}

function ensureTabMount() {
  if (!$('#' + TAB_ID)) {
    const host = $('.app-content') || document.body;
    const tab = document.createElement('div');
    tab.id = TAB_ID; tab.className = 'tab-content';
    tab.innerHTML = `
      <div class="threads-header">
        <div class="threads-title">Threads</div>
        <div class="threads-actions">
          <div class="threads-toggle" role="tablist" aria-label="Filtre">
            <button type="button" data-filter="active" class="active">Actifs</button>
            <button type="button" data-filter="archived">Archivés</button>
          </div>
          <button type="button" class="button primary" id="threads-new">Nouveau</button>
          <button type="button" class="button" id="threads-refresh">Rafraîchir</button>
        </div>
      </div>

      <div class="threads-body">
        <section aria-label="Liste des threads">
          <div class="threads-list" id="threads-list"></div>
        </section>
        <section aria-label="Détail du thread" id="thread-detail"></section>
      </div>
    `;
    host.appendChild(tab);

    // Wire filter
    const toggle = tab.querySelector('.threads-toggle');
    toggle.addEventListener('click', (e) => {
      const btn = e.target.closest('button[data-filter]');
      if (!btn) return;
      toggle.querySelectorAll('button').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const archived = btn.dataset.filter === 'archived';
      threadsStore.setArchived(archived);
      // désélection
      renderList(); renderDetail(null);
    });

    // Buttons
    tab.querySelector('#threads-new').addEventListener('click', async () => {
      const title = prompt('Titre du thread ?') || '';
      const t = await threadsStore.create({ title });
      if (t?.id) { await threadsStore.select(t.id); activateTab(); }
    });
    tab.querySelector('#threads-refresh').addEventListener('click', () => threadsStore.load());
  }
}

function setActiveTab(id) {
  // Toggle .active sur .tab-content
  $all('.tab-content').forEach(el => el.classList.toggle('active', el.id === id));
  // Nav active states
  $all('.nav-link').forEach(el => el.classList.toggle('active', el.dataset.nav === 'threads'));
  $all('.header-nav-button').forEach(el => el.classList.toggle('active', el.dataset.nav === 'threads'));
}

function activateTab() {
  ensureTabMount();
  setActiveTab(TAB_ID);
  threadsStore.load();
}

function renderList() {
  const root = $('#threads-list'); if (!root) return;
  const s = threadsStore.state;
  root.innerHTML = ''; // clear
  if (s.loading && !s.items.length) {
    root.innerHTML = `<div class="thread-sub">Chargement…</div>`;
    return;
  }
  if (!s.items.length) {
    root.innerHTML = `<div class="thread-sub">Aucun thread ${s.archived ? 'archivé' : 'actif'}.</div>`;
    return;
  }

  for (const t of s.items) {
    const row = document.createElement('div');
    row.className = 'thread-row' + (s.selectedId === t.id ? ' active' : '');
    row.innerHTML = `
      <div class="thread-meta">
        <div class="thread-title">${escapeHtml(t.title || t.id)}</div>
        <div class="thread-sub">MAJ ${formatDateTime(t.updated_at || t.update_time || t.modified_at || t.created_at || Date.now())}</div>
      </div>
      <div class="row-actions">
        <button class="icon-button" title="${t.archived ? 'Désarchiver' : 'Archiver'}" data-act="archive">${t.archived ? '📤' : '📥'}</button>
        <button class="icon-button" title="Exporter (Markdown)" data-act="export-md">📝</button>
        <button class="icon-button" title="Exporter (JSON)" data-act="export-json">🧾</button>
      </div>
    `;
    row.addEventListener('click', (e) => {
      const actBtn = e.target.closest('.icon-button');
      if (actBtn) return; // actions gérées plus bas
      threadsStore.select(t.id);
    });
    row.querySelector('[data-act="archive"]').addEventListener('click', async (e) => {
      e.stopPropagation();
      await threadsStore.toggleArchive(t);
    });
    row.querySelector('[data-act="export-md"]').addEventListener('click', async (e) => {
      e.stopPropagation();
      await threadsStore.export(t, 'md');
    });
    row.querySelector('[data-act="export-json"]').addEventListener('click', async (e) => {
      e.stopPropagation();
      await threadsStore.export(t, 'json');
    });
    root.appendChild(row);
  }
}

function renderDetail(thread) {
  const container = $('#thread-detail'); if (!container) return;
  const s = threadsStore.state;
  container.innerHTML = '';

  if (!s.selectedId) {
    container.innerHTML = `<div class="thread-sub">Sélectionne un thread pour afficher les messages.</div>`;
    return;
  }

  const box = document.createElement('div');
  box.className = 'thread-view';
  const title = thread?.title || (s.items.find(i => i.id === s.selectedId)?.title) || s.selectedId;

  box.innerHTML = `
    <div class="thread-view-header">
      <div class="thread-view-title">${escapeHtml(title)}</div>
      <div class="thread-view-tools"></div>
    </div>
    <div class="thread-messages" id="thread-messages"></div>
    <form class="thread-composer" id="thread-compose">
      <textarea name="content" placeholder="Écrire un message…"></textarea>
      <button type="submit" class="button primary">Envoyer</button>
    </form>
  `;
  container.appendChild(box);

  // messages
  const list = $('#thread-messages', box);
  list.innerHTML = '';
  for (const m of s.messages) {
    const item = document.createElement('div');
    item.className = 'message-item';
    const when = formatDateTime(m.created_at || m.timestamp || Date.now());
    item.innerHTML = `
      <div class="who">${escapeHtml(m.role || 'user')}</div>
      <div class="when">${when}</div>
      <div class="text">${escapeHtml(m.content || '')}</div>
    `;
    list.appendChild(item);
  }
  list.scrollTop = list.scrollHeight;

  // composer
  const form = $('#thread-compose', box);
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const content = new FormData(form).get('content')?.toString() || '';
    if (!content.trim()) return;
    await threadsStore.sendMessage(content);
    form.reset();
    renderDetail(); // refresh messages section (append optimiste déjà fait)
  });
}

function escapeHtml(s) {
  return (s ?? '').toString().replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
}

/* boot */
function boot() {
  ensureNav();
  ensureTabMount();
  threadsStore.addEventListener('change', () => {
    renderList();
    renderDetail();
  });
  // lazy: n'active pas l'onglet tout seul, l'utilisateur clique "Threads"
}

document.addEventListener('DOMContentLoaded', boot);
