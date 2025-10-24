# 🔧 TÂCHE CODEX GPT — PWA Mode Hors Ligne (P3.10)

**Branche:** `feature/pwa-offline`
**Durée estimée:** 4 jours
**Priorité:** P3 (BASSE - Nice-to-have)
**Assigné à:** Codex GPT
**Date d'attribution:** 2025-10-24

---

## 🎯 Objectif

Implémenter le mode hors ligne (Progressive Web App) pour permettre l'accès aux conversations récentes sans connexion internet.

---

## 📋 Tâches Détaillées

### 1. Créer `manifest.json` (PWA config)

**Fichier:** `public/manifest.json`

```json
{
  "name": "Emergence V8",
  "short_name": "Emergence",
  "description": "Multi-agent AI conversation platform",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#0a0a0a",
  "theme_color": "#00d4ff",
  "orientation": "portrait-primary",
  "icons": [
    {
      "src": "/icon-192x192.png",
      "sizes": "192x192",
      "type": "image/png",
      "purpose": "any maskable"
    },
    {
      "src": "/icon-512x512.png",
      "sizes": "512x512",
      "type": "image/png",
      "purpose": "any maskable"
    }
  ]
}
```

**Actions:**
- [ ] Créer fichier `public/manifest.json`
- [ ] Générer icônes 192x192 et 512x512 depuis logo (ou placeholder)
- [ ] Ajouter `<link rel="manifest" href="/manifest.json">` dans `index.html`
- [ ] Tester installabilité PWA (Chrome DevTools → Lighthouse → PWA)

---

### 2. Service Worker cache-first strategy

**Fichier:** `src/frontend/sw.js`

**Stratégie:**
- **Cache-First** pour assets statiques (HTML, CSS, JS, fonts, images)
- **Network-First** pour API calls (avec fallback cache si offline)
- **Versioning** cache pour invalider ancien cache lors updates

**Implémentation:**

```javascript
const CACHE_VERSION = 'v1';
const STATIC_CACHE = `emergence-static-${CACHE_VERSION}`;
const DYNAMIC_CACHE = `emergence-dynamic-${CACHE_VERSION}`;

const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/src/frontend/app.js',
  '/src/frontend/styles/main.css',
  // ... autres assets critiques
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then((cache) => {
      return cache.addAll(STATIC_ASSETS);
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys
          .filter((key) => key !== STATIC_CACHE && key !== DYNAMIC_CACHE)
          .map((key) => caches.delete(key))
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const { request } = event;

  // API calls: Network-First
  if (request.url.includes('/api/')) {
    event.respondWith(
      fetch(request)
        .then((response) => {
          const clone = response.clone();
          caches.open(DYNAMIC_CACHE).then((cache) => cache.put(request, clone));
          return response;
        })
        .catch(() => caches.match(request))
    );
  }
  // Static assets: Cache-First
  else {
    event.respondWith(
      caches.match(request).then((cached) => cached || fetch(request))
    );
  }
});
```

**Actions:**
- [ ] Créer `src/frontend/sw.js`
- [ ] Implémenter install/activate/fetch handlers
- [ ] Ajouter versioning cache
- [ ] Enregistrer service worker dans `app.js`:
  ```javascript
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js');
  }
  ```

---

### 3. Cacher conversations récentes (IndexedDB)

**Fichier:** `src/frontend/features/pwa/offline-storage.js`

**Installation dépendance:**
```bash
npm install idb
```

**Structure DB:**
```javascript
import { openDB } from 'idb';

const DB_NAME = 'emergence-offline';
const DB_VERSION = 1;

async function initDB() {
  return openDB(DB_NAME, DB_VERSION, {
    upgrade(db) {
      // Store threads
      if (!db.objectStoreNames.contains('threads')) {
        const threadsStore = db.createObjectStore('threads', { keyPath: 'id' });
        threadsStore.createIndex('updated_at', 'updated_at');
      }

      // Store messages
      if (!db.objectStoreNames.contains('messages')) {
        const messagesStore = db.createObjectStore('messages', { keyPath: 'id' });
        messagesStore.createIndex('thread_id', 'thread_id');
      }
    },
  });
}

// API functions
async function saveThread(thread) { /* ... */ }
async function getThread(id) { /* ... */ }
async function getAllThreads() { /* ... */ }
async function saveMessage(message) { /* ... */ }
async function getThreadMessages(threadId) { /* ... */ }
```

**Actions:**
- [ ] Installer `idb` library
- [ ] Créer `offline-storage.js` avec initDB + CRUD functions
- [ ] Implémenter sync automatique (sync 20 dernières conversations actives)
- [ ] Limit 50 MB de données offline (cleanup old threads si dépassé)

---

### 4. Indicateur "Mode hors ligne"

**Fichier:** `src/frontend/styles/pwa.css`

**Design:**
- Badge rouge "Offline" en haut à droite du header
- Message d'info: "Vous êtes hors ligne. Conversations récentes disponibles."
- Désactiver fonctions nécessitant connexion (nouveau thread, export PDF, etc.)

**Implémentation:**
```javascript
// Dans app.js
window.addEventListener('online', () => {
  document.body.classList.remove('offline');
  showToast('Connexion rétablie', 'success');
});

window.addEventListener('offline', () => {
  document.body.classList.add('offline');
  showToast('Mode hors ligne activé', 'warning');
});
```

**CSS:**
```css
.offline-badge {
  position: fixed;
  top: 20px;
  right: 20px;
  background: #ff4444;
  color: white;
  padding: 8px 16px;
  border-radius: 20px;
  display: none;
}

.offline .offline-badge {
  display: block;
}
```

**Actions:**
- [ ] Créer badge offline (HTML + CSS)
- [ ] Écouter événements online/offline
- [ ] Désactiver boutons nécessitant connexion quand offline

---

### 5. Sync automatique au retour en ligne

**Fichier:** `src/frontend/features/pwa/sync-manager.js`

**Logique:**
```javascript
class SyncManager {
  constructor() {
    this.pendingSync = [];
  }

  async queueSync(action, data) {
    this.pendingSync.push({ action, data, timestamp: Date.now() });
    await this.savePendingSync();
  }

  async syncAll() {
    const pending = await this.loadPendingSync();
    for (const item of pending) {
      try {
        await this.syncItem(item);
      } catch (err) {
        console.error('Sync failed:', err);
      }
    }
    await this.clearPendingSync();
  }

  async syncItem(item) {
    // POST vers backend
    if (item.action === 'send_message') {
      await fetch('/api/chat/message', {
        method: 'POST',
        body: JSON.stringify(item.data),
      });
    }
  }
}
```

**Actions:**
- [ ] Créer `sync-manager.js`
- [ ] Queue messages créés offline (localStorage)
- [ ] Sync automatique au retour en ligne (événement 'online')
- [ ] Résolution conflits: backend wins (messages offline marqués "non-synced")
- [ ] Notification: "Synchronisation terminée" (toast)

---

### 6. Tests: offline → conversations dispo → online → sync

**Scénario de test:**
1. Créer 3 conversations en ligne
2. Passer en mode avion (Chrome DevTools → Network → Offline)
3. Vérifier que les 3 conversations sont accessibles
4. Créer un message dans une conversation (doit être enregistré IndexedDB)
5. Repasser en ligne
6. Vérifier sync automatique vers backend (message visible dans DB backend)

**Actions:**
- [ ] Tester scénario complet
- [ ] Vérifier cache service worker (DevTools → Application → Cache Storage)
- [ ] Vérifier IndexedDB (DevTools → Application → IndexedDB)
- [ ] Documenter bugs rencontrés

---

## 📁 Fichiers à Créer

- `public/manifest.json`
- `public/icon-192x192.png`
- `public/icon-512x512.png`
- `src/frontend/sw.js` (Service Worker)
- `src/frontend/features/pwa/offline-storage.js` (IndexedDB wrapper)
- `src/frontend/features/pwa/sync-manager.js` (Sync logic)
- `src/frontend/styles/pwa.css` (Indicateur offline)

## 📝 Fichiers à Modifier

- `index.html` (ajout `<link rel="manifest">`)
- `src/frontend/features/chat/chat.js` (intégration offline storage)
- `src/frontend/app.js` (enregistrer service worker + sync)

---

## ✅ Acceptance Criteria

- [ ] PWA installable (bouton "Installer" navigateur visible)
- [ ] Conversations récentes accessibles offline (20+ threads minimum)
- [ ] Messages créés offline synchronisés au retour en ligne
- [ ] Indicateur offline visible (badge rouge header)
- [ ] Cache assets statiques (instant load offline)
- [ ] Tests passent (scénario offline → online → sync)

---

## 📚 Ressources

**Documentation PWA:**
- https://web.dev/progressive-web-apps/
- https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps

**IndexedDB:**
- https://github.com/jakearchibald/idb (library)
- https://developer.mozilla.org/en-US/docs/Web/API/IndexedDB_API

**Service Workers:**
- https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API

---

## ⚠️ Notes Importantes

1. **HTTPS Obligatoire:** Service Worker ne fonctionne qu'en HTTPS (ou localhost)
2. **Cache Versioning:** Incrémenter `CACHE_VERSION` à chaque déploiement
3. **IndexedDB Async:** Utiliser `await` partout
4. **Tester Chrome DevTools:** Application → Service Workers / Cache Storage / IndexedDB
5. **Limit 50 MB:** Nettoyer vieilles conversations si dépassement

---

## 🔄 Prochaines Étapes Après PWA

Une fois PWA terminé et PR mergée:
- Option A: Enchaîner sur P3.11 Webhooks (si Claude Web pas encore fini)
- Option B: Enchaîner sur P3.12 API Publique
- Option C: Attendre validation FG pour décider

**Coordination:** Consulter `AGENT_SYNC.md` pour voir progression Claude Web sur Webhooks

---

**Contact Architecte:** gonzalefernando@gmail.com
**Dernière mise à jour:** 2025-10-24
