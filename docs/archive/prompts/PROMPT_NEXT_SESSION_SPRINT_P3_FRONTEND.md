# 🎨 Prompt Session Sprint P3 - Frontend UI Hints Proactifs + Dashboard Mémoire

**Date création** : 2025-10-10
**Objectif** : Implémenter l'interface utilisateur pour les hints proactifs et le dashboard mémoire
**Prérequis** : Sprint P2 (backend) COMPLET ✅

---

## 🎯 Objectif Session

Implémenter le **Sprint 3 P2 (Frontend UI)** pour compléter la Phase P2 Mémoire LTM :

1. ✅ **Sprint 1 P2** : Optimisations performance (-71% latence) - FAIT
2. ✅ **Sprint 2 P2** : ProactiveHintEngine backend + intégration ChatService - FAIT
3. 🎨 **Sprint 3 P2** : Frontend UI hints proactifs + Dashboard mémoire utilisateur - **À FAIRE**

---

## 📋 Tâches Sprint P3

### 1. 🔔 Composant ProactiveHintsUI

**Fichier à créer** : `src/frontend/features/memory/ProactiveHintsUI.js`

#### Spécifications

**Event listener WebSocket** :
```javascript
// Écouter l'event ws:proactive_hint émis par le backend
EventBus.on('ws:proactive_hint', (data) => {
  const hints = data.hints || [];
  hints.forEach(hint => {
    displayProactiveHintBanner(hint);
  });
});
```

**Structure hint reçu** :
```javascript
{
  id: "hint_abc123",
  type: "preference_reminder",  // ou "intent_followup", "constraint_warning"
  title: "Rappel: Préférence détectée",
  message: "💡 Tu as mentionné 'python' 3 fois. Rappel: I prefer Python for scripting",
  relevance_score: 0.85,
  source_preference_id: "pref_123",
  action_label: "Appliquer",
  action_payload: {
    preference: "I prefer Python for scripting",
    concept: "python"
  }
}
```

#### Fonctionnalités UI

1. **Affichage banner hint** :
   - Position : Top-right de l'interface (non-intrusif)
   - Style : Bannière élégante avec icône selon type (💡 preference, 📋 intent, ⚠️ constraint)
   - Animation : Slide-in smooth
   - Auto-dismiss : 10 secondes (configurable)

2. **Actions utilisateur** :
   - ✅ **Appliquer** : Copier préférence dans input (si applicable)
   - ❌ **Ignorer** : Fermer hint immédiatement
   - 🕐 **Rappeler plus tard** : Snooze 1 heure (stocker dans localStorage)

3. **Gestion multiple hints** :
   - Stack vertical si plusieurs hints simultanés
   - Max 3 hints affichés (conformément backend config)
   - Priorité par relevance_score (tri descendant)

#### Exemple markup
```javascript
export class ProactiveHintsUI {
  constructor(container) {
    this.container = container;
    this.activeHints = [];
    this.setupEventListeners();
  }

  setupEventListeners() {
    EventBus.on('ws:proactive_hint', this.handleProactiveHint.bind(this));
  }

  handleProactiveHint(data) {
    const hints = data.hints || [];

    // Filter snoozed hints (check localStorage)
    const activeHints = hints.filter(h => !this.isHintSnoozed(h.id));

    // Sort by relevance
    activeHints.sort((a, b) => b.relevance_score - a.relevance_score);

    // Display max 3 hints
    activeHints.slice(0, 3).forEach(hint => {
      this.displayHintBanner(hint);
    });
  }

  displayHintBanner(hint) {
    const banner = document.createElement('div');
    banner.className = `proactive-hint-banner hint-${hint.type}`;
    banner.dataset.hintId = hint.id;

    banner.innerHTML = `
      <div class="hint-icon">${this.getIconForType(hint.type)}</div>
      <div class="hint-content">
        <div class="hint-title">${hint.title}</div>
        <div class="hint-message">${hint.message}</div>
        <div class="hint-meta">
          <span class="hint-relevance">Pertinence: ${Math.round(hint.relevance_score * 100)}%</span>
        </div>
      </div>
      <div class="hint-actions">
        ${hint.action_label ? `<button class="hint-action-primary" data-action="apply">${hint.action_label}</button>` : ''}
        <button class="hint-action-snooze" data-action="snooze">🕐 Plus tard</button>
        <button class="hint-action-dismiss" data-action="dismiss">✕</button>
      </div>
    `;

    // Event listeners for actions
    banner.querySelector('[data-action="apply"]')?.addEventListener('click', () => {
      this.applyHint(hint);
      this.dismissHint(hint.id);
    });

    banner.querySelector('[data-action="snooze"]').addEventListener('click', () => {
      this.snoozeHint(hint.id, 3600000); // 1 hour
      this.dismissHint(hint.id);
    });

    banner.querySelector('[data-action="dismiss"]').addEventListener('click', () => {
      this.dismissHint(hint.id);
    });

    // Append to container with animation
    this.container.appendChild(banner);
    setTimeout(() => banner.classList.add('visible'), 10);

    // Auto-dismiss after 10s
    setTimeout(() => {
      if (banner.parentNode) {
        this.dismissHint(hint.id);
      }
    }, 10000);
  }

  getIconForType(type) {
    const icons = {
      preference_reminder: '💡',
      intent_followup: '📋',
      constraint_warning: '⚠️'
    };
    return icons[type] || '💡';
  }

  applyHint(hint) {
    // Logic to apply hint (e.g., copy to input, trigger action)
    if (hint.action_payload?.preference) {
      // Copy preference to chat input or clipboard
      const chatInput = document.querySelector('#chat-input');
      if (chatInput) {
        chatInput.value = hint.action_payload.preference;
        chatInput.focus();
      }
    }
  }

  snoozeHint(hintId, durationMs) {
    const snoozeUntil = Date.now() + durationMs;
    localStorage.setItem(`hint_snooze_${hintId}`, snoozeUntil);
  }

  isHintSnoozed(hintId) {
    const snoozeUntil = localStorage.getItem(`hint_snooze_${hintId}`);
    if (!snoozeUntil) return false;
    return Date.now() < parseInt(snoozeUntil);
  }

  dismissHint(hintId) {
    const banner = this.container.querySelector(`[data-hint-id="${hintId}"]`);
    if (banner) {
      banner.classList.add('dismissing');
      setTimeout(() => banner.remove(), 300);
    }
  }
}
```

---

### 2. 📊 Dashboard Mémoire Utilisateur

**Fichier à créer** : `src/frontend/features/memory/MemoryDashboard.js`

#### Spécifications

**Endpoint API backend** :
```javascript
GET /api/memory/user/stats
Authorization: Bearer {token}
```

**Réponse attendue** :
```json
{
  "preferences": {
    "total": 12,
    "top": [
      {"topic": "python", "confidence": 0.92, "type": "preference", "captured_at": "2025-10-05T10:00:00Z"},
      {"topic": "docker", "confidence": 0.87, "type": "preference", "captured_at": "2025-10-03T14:30:00Z"}
    ],
    "by_type": {"preference": 8, "intent": 3, "constraint": 1}
  },
  "concepts": {
    "total": 47,
    "top": [
      {"concept": "containerization", "mentions": 5, "last_mentioned": "2025-10-07T09:15:00Z"},
      {"concept": "CI/CD pipeline", "mentions": 3, "last_mentioned": "2025-10-06T16:20:00Z"}
    ]
  },
  "stats": {
    "sessions_analyzed": 23,
    "threads_archived": 5,
    "ltm_size_mb": 2.4
  }
}
```

#### Fonctionnalités UI

1. **Section Préférences** :
   - Liste top 10 préférences (score confiance descendant)
   - Badge type (preference/intent/constraint)
   - Date capture (format relatif : "il y a 3 jours")
   - Bouton "Modifier" / "Supprimer" (appeler API backend)

2. **Section Concepts** :
   - Liste top 10 concepts (mentions descendant)
   - Compteur mentions
   - Timeline mini (graphique mentions/temps avec Chart.js ou similaire)
   - Dernière mention (date relative)

3. **Statistiques globales** :
   - Cards avec métriques clés (sessions, threads, taille LTM)
   - Graphique évolution LTM (taille over time)
   - Hit rate cache (si métriques Prometheus accessibles)

#### Exemple markup
```javascript
export class MemoryDashboard {
  constructor(container) {
    this.container = container;
    this.stats = null;
  }

  async render() {
    this.stats = await this.fetchMemoryStats();

    this.container.innerHTML = `
      <div class="memory-dashboard">
        <h2>🧠 Ta Mémoire à Long Terme</h2>

        <!-- Global stats -->
        <div class="stats-grid">
          <div class="stat-card">
            <div class="stat-label">Sessions analysées</div>
            <div class="stat-value">${this.stats.stats.sessions_analyzed}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">Threads archivés</div>
            <div class="stat-value">${this.stats.stats.threads_archived}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">Taille LTM</div>
            <div class="stat-value">${this.stats.stats.ltm_size_mb} MB</div>
          </div>
        </div>

        <!-- Preferences section -->
        <div class="dashboard-section">
          <h3>💡 Tes Préférences (${this.stats.preferences.total})</h3>
          <div class="preferences-breakdown">
            ${Object.entries(this.stats.preferences.by_type).map(([type, count]) => `
              <span class="badge badge-${type}">${type}: ${count}</span>
            `).join('')}
          </div>
          <div class="preferences-list">
            ${this.stats.preferences.top.map(pref => `
              <div class="preference-item">
                <div class="preference-content">
                  <span class="preference-topic">${pref.topic}</span>
                  <span class="preference-confidence">${Math.round(pref.confidence * 100)}%</span>
                </div>
                <div class="preference-meta">
                  <span class="preference-date">${this.formatRelativeDate(pref.captured_at)}</span>
                  <span class="badge badge-${pref.type}">${pref.type}</span>
                </div>
              </div>
            `).join('')}
          </div>
        </div>

        <!-- Concepts section -->
        <div class="dashboard-section">
          <h3>🔍 Concepts Récurrents (${this.stats.concepts.total})</h3>
          <div class="concepts-list">
            ${this.stats.concepts.top.map(concept => `
              <div class="concept-item">
                <div class="concept-content">
                  <span class="concept-text">${concept.concept}</span>
                  <span class="concept-mentions">${concept.mentions} mentions</span>
                </div>
                <div class="concept-meta">
                  <span class="concept-date">Dernier: ${this.formatRelativeDate(concept.last_mentioned)}</span>
                </div>
              </div>
            `).join('')}
          </div>
          <canvas id="concepts-timeline" width="400" height="200"></canvas>
        </div>
      </div>
    `;

    // Render timeline chart
    this.renderConceptsTimeline();
  }

  async fetchMemoryStats() {
    const response = await fetch('/api/memory/user/stats', {
      headers: {
        'Authorization': `Bearer ${this.getAuthToken()}`
      }
    });
    return await response.json();
  }

  formatRelativeDate(isoDate) {
    const date = new Date(isoDate);
    const now = new Date();
    const diffMs = now - date;
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return "Aujourd'hui";
    if (diffDays === 1) return "Hier";
    if (diffDays < 7) return `Il y a ${diffDays} jours`;
    if (diffDays < 30) return `Il y a ${Math.floor(diffDays / 7)} semaines`;
    return `Il y a ${Math.floor(diffDays / 30)} mois`;
  }

  renderConceptsTimeline() {
    // Use Chart.js or similar to render timeline
    const canvas = document.getElementById('concepts-timeline');
    if (!canvas) return;

    // Placeholder - implement with Chart.js
    // Show mentions over time for top concepts
  }

  getAuthToken() {
    // Get token from localStorage or context
    return localStorage.getItem('auth_token');
  }
}
```

---

### 3. 🎨 Styles CSS

**Fichier à créer** : `src/frontend/styles/proactive-hints.css`

```css
/* Proactive Hints Banner */
.proactive-hint-banner {
  position: fixed;
  top: 20px;
  right: 20px;
  width: 400px;
  max-width: 90vw;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.2);
  padding: 16px;
  display: flex;
  gap: 12px;
  opacity: 0;
  transform: translateX(100%);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  z-index: 1000;
}

.proactive-hint-banner.visible {
  opacity: 1;
  transform: translateX(0);
}

.proactive-hint-banner.dismissing {
  opacity: 0;
  transform: translateX(100%);
}

/* Type variants */
.proactive-hint-banner.hint-preference_reminder {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.proactive-hint-banner.hint-intent_followup {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
}

.proactive-hint-banner.hint-constraint_warning {
  background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
}

.hint-icon {
  font-size: 32px;
  flex-shrink: 0;
}

.hint-content {
  flex: 1;
}

.hint-title {
  font-weight: 600;
  font-size: 14px;
  margin-bottom: 4px;
}

.hint-message {
  font-size: 13px;
  line-height: 1.4;
  margin-bottom: 8px;
}

.hint-meta {
  font-size: 11px;
  opacity: 0.8;
}

.hint-actions {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex-shrink: 0;
}

.hint-actions button {
  padding: 6px 12px;
  border: none;
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}

.hint-action-primary {
  background: rgba(255,255,255,0.9);
  color: #667eea;
  font-weight: 600;
}

.hint-action-primary:hover {
  background: white;
}

.hint-action-snooze,
.hint-action-dismiss {
  background: rgba(255,255,255,0.2);
  color: white;
}

.hint-action-snooze:hover,
.hint-action-dismiss:hover {
  background: rgba(255,255,255,0.3);
}

/* Stacking multiple hints */
.proactive-hint-banner:nth-child(2) {
  top: 130px;
}

.proactive-hint-banner:nth-child(3) {
  top: 240px;
}

/* Memory Dashboard */
.memory-dashboard {
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
}

.memory-dashboard h2 {
  font-size: 28px;
  margin-bottom: 24px;
  color: #2d3748;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 32px;
}

.stat-card {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.stat-label {
  font-size: 13px;
  color: #718096;
  margin-bottom: 8px;
}

.stat-value {
  font-size: 32px;
  font-weight: 700;
  color: #2d3748;
}

.dashboard-section {
  background: white;
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 24px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.dashboard-section h3 {
  font-size: 20px;
  margin-bottom: 16px;
  color: #2d3748;
}

.preferences-breakdown {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}

.badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
}

.badge-preference {
  background: #e6fffa;
  color: #047857;
}

.badge-intent {
  background: #fef3c7;
  color: #92400e;
}

.badge-constraint {
  background: #fee2e2;
  color: #991b1b;
}

.preference-item,
.concept-item {
  padding: 12px;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.preference-item:last-child,
.concept-item:last-child {
  border-bottom: none;
}

.preference-topic,
.concept-text {
  font-weight: 600;
  color: #2d3748;
}

.preference-confidence {
  margin-left: 8px;
  padding: 2px 8px;
  background: #e6fffa;
  color: #047857;
  border-radius: 8px;
  font-size: 11px;
  font-weight: 600;
}

.concept-mentions {
  margin-left: 8px;
  padding: 2px 8px;
  background: #e0e7ff;
  color: #3730a3;
  border-radius: 8px;
  font-size: 11px;
  font-weight: 600;
}

.preference-meta,
.concept-meta {
  display: flex;
  gap: 8px;
  align-items: center;
}

.preference-date,
.concept-date {
  font-size: 12px;
  color: #718096;
}
```

---

### 4. 🔗 Intégration dans l'App

**Fichier à modifier** : `src/frontend/main.js` (ou point d'entrée principal)

```javascript
import { ProactiveHintsUI } from './features/memory/ProactiveHintsUI.js';
import { MemoryDashboard } from './features/memory/MemoryDashboard.js';

// Initialize ProactiveHintsUI
const hintsContainer = document.createElement('div');
hintsContainer.id = 'proactive-hints-container';
document.body.appendChild(hintsContainer);

const proactiveHints = new ProactiveHintsUI(hintsContainer);

// Initialize MemoryDashboard (on /memory route)
if (window.location.pathname === '/memory') {
  const dashboardContainer = document.getElementById('memory-dashboard-root');
  const dashboard = new MemoryDashboard(dashboardContainer);
  dashboard.render();
}
```

---

### 5. 🧪 Tests E2E (Playwright)

**Fichier à créer** : `tests/e2e/proactive-hints.spec.js`

```javascript
import { test, expect } from '@playwright/test';

test.describe('Proactive Hints', () => {
  test('should display hint banner when ws:proactive_hint received', async ({ page }) => {
    await page.goto('http://localhost:3000');

    // Simulate WebSocket event
    await page.evaluate(() => {
      window.EventBus.emit('ws:proactive_hint', {
        hints: [{
          id: 'hint_test_123',
          type: 'preference_reminder',
          title: 'Test Hint',
          message: 'This is a test hint',
          relevance_score: 0.85,
          action_label: 'Apply'
        }]
      });
    });

    // Wait for banner to appear
    const banner = await page.locator('.proactive-hint-banner');
    await expect(banner).toBeVisible();
    await expect(banner).toHaveClass(/visible/);

    // Check content
    await expect(page.locator('.hint-title')).toHaveText('Test Hint');
    await expect(page.locator('.hint-message')).toHaveText('This is a test hint');
  });

  test('should dismiss hint on dismiss button click', async ({ page }) => {
    await page.goto('http://localhost:3000');

    // Trigger hint
    await page.evaluate(() => {
      window.EventBus.emit('ws:proactive_hint', {
        hints: [{
          id: 'hint_test_456',
          type: 'intent_followup',
          title: 'Test Intent',
          message: 'Test message',
          relevance_score: 0.75
        }]
      });
    });

    // Click dismiss
    await page.click('.hint-action-dismiss');

    // Check banner dismissed
    const banner = page.locator('.proactive-hint-banner');
    await expect(banner).toHaveClass(/dismissing/);
    await page.waitForTimeout(400); // Animation duration
    await expect(banner).not.toBeVisible();
  });

  test('should snooze hint and not show again', async ({ page }) => {
    await page.goto('http://localhost:3000');

    const hintId = 'hint_snooze_test';

    // Trigger hint
    await page.evaluate((id) => {
      window.EventBus.emit('ws:proactive_hint', {
        hints: [{ id, type: 'preference_reminder', title: 'Snooze Test', message: 'Test', relevance_score: 0.8 }]
      });
    }, hintId);

    // Click snooze
    await page.click('.hint-action-snooze');

    // Re-emit same hint
    await page.evaluate((id) => {
      window.EventBus.emit('ws:proactive_hint', {
        hints: [{ id, type: 'preference_reminder', title: 'Snooze Test', message: 'Test', relevance_score: 0.8 }]
      });
    }, hintId);

    // Should not appear (snoozed)
    await page.waitForTimeout(200);
    const banner = page.locator('.proactive-hint-banner');
    await expect(banner).not.toBeVisible();
  });

  test('should display max 3 hints when multiple received', async ({ page }) => {
    await page.goto('http://localhost:3000');

    // Emit 5 hints
    await page.evaluate(() => {
      window.EventBus.emit('ws:proactive_hint', {
        hints: Array.from({ length: 5 }, (_, i) => ({
          id: `hint_${i}`,
          type: 'preference_reminder',
          title: `Hint ${i}`,
          message: `Message ${i}`,
          relevance_score: 0.9 - (i * 0.1)
        }))
      });
    });

    // Should display exactly 3
    const banners = await page.locator('.proactive-hint-banner').count();
    expect(banners).toBe(3);
  });
});

test.describe('Memory Dashboard', () => {
  test('should render dashboard with stats', async ({ page }) => {
    // Mock API response
    await page.route('/api/memory/user/stats', (route) => {
      route.fulfill({
        status: 200,
        body: JSON.stringify({
          preferences: {
            total: 12,
            top: [
              { topic: 'python', confidence: 0.92, type: 'preference', captured_at: '2025-10-05T10:00:00Z' }
            ],
            by_type: { preference: 8, intent: 3, constraint: 1 }
          },
          concepts: {
            total: 47,
            top: [
              { concept: 'docker', mentions: 5, last_mentioned: '2025-10-07T09:15:00Z' }
            ]
          },
          stats: {
            sessions_analyzed: 23,
            threads_archived: 5,
            ltm_size_mb: 2.4
          }
        })
      });
    });

    await page.goto('http://localhost:3000/memory');

    // Check stats cards
    await expect(page.locator('.stat-value').first()).toHaveText('23');

    // Check preferences section
    await expect(page.locator('.preference-topic').first()).toHaveText('python');

    // Check concepts section
    await expect(page.locator('.concept-text').first()).toHaveText('docker');
  });
});
```

---

## 📊 Backend - Endpoint à Créer

**IMPORTANT** : Le backend doit implémenter l'endpoint stats utilisateur.

**Fichier à modifier** : `src/backend/features/memory/router.py`

```python
@router.get("/user/stats")
async def get_user_memory_stats(
    request: Request,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get user's memory statistics and top items.

    Returns:
        {
          "preferences": {
            "total": 12,
            "top": [...],
            "by_type": {"preference": 8, "intent": 3, "constraint": 1}
          },
          "concepts": {
            "total": 47,
            "top": [...]
          },
          "stats": {
            "sessions_analyzed": 23,
            "threads_archived": 5,
            "ltm_size_mb": 2.4
          }
        }
    """
    container = _get_container(request)
    vector_service = container.vector_service()
    db_manager = container.db_manager()
    user_id = current_user.get("sub") or current_user.get("user_id")

    collection = vector_service.get_or_create_collection("emergence_knowledge")

    # Fetch user's preferences
    try:
        prefs_results = collection.get(
            where={"$and": [
                {"user_id": user_id},
                {"type": {"$in": ["preference", "intent", "constraint"]}}
            ]},
            include=["documents", "metadatas"]
        )

        prefs_docs = prefs_results.get("documents", [])
        prefs_meta = prefs_results.get("metadatas", [])

        # Parse preferences
        preferences = []
        type_counts = {"preference": 0, "intent": 0, "constraint": 0}

        for doc, meta in zip(prefs_docs, prefs_meta):
            pref_type = meta.get("type", "preference")
            type_counts[pref_type] = type_counts.get(pref_type, 0) + 1

            preferences.append({
                "topic": meta.get("topic", "Unknown"),
                "confidence": meta.get("confidence", 0.5),
                "type": pref_type,
                "captured_at": meta.get("captured_at") or meta.get("created_at"),
                "text": doc
            })

        # Sort by confidence
        preferences.sort(key=lambda x: x["confidence"], reverse=True)

    except Exception as e:
        logger.error(f"Failed to fetch preferences: {e}")
        preferences = []
        type_counts = {}

    # Fetch user's concepts
    try:
        concepts_results = collection.get(
            where={"$and": [
                {"user_id": user_id},
                {"type": "concept"}
            ]},
            include=["documents", "metadatas"]
        )

        concepts_docs = concepts_results.get("documents", [])
        concepts_meta = concepts_results.get("metadatas", [])

        # Parse concepts
        concepts = []
        for doc, meta in zip(concepts_docs, concepts_meta):
            concepts.append({
                "concept": meta.get("concept_text") or doc,
                "mentions": meta.get("mention_count", 1),
                "last_mentioned": meta.get("last_mentioned_at") or meta.get("created_at")
            })

        # Sort by mentions
        concepts.sort(key=lambda x: x["mentions"], reverse=True)

    except Exception as e:
        logger.error(f"Failed to fetch concepts: {e}")
        concepts = []

    # Database stats
    try:
        # Count sessions analyzed
        sessions_count = await queries.count_sessions(db_manager, user_id=user_id)

        # Count archived threads
        threads = await queries.get_threads(
            db_manager,
            user_id=user_id,
            archived_only=True,
            limit=1000
        )
        archived_count = len(threads)

        # Estimate LTM size (rough)
        ltm_size_mb = (len(prefs_docs) + len(concepts_docs)) * 0.001  # ~1KB per item

    except Exception as e:
        logger.error(f"Failed to fetch database stats: {e}")
        sessions_count = 0
        archived_count = 0
        ltm_size_mb = 0.0

    return {
        "preferences": {
            "total": len(preferences),
            "top": preferences[:10],
            "by_type": type_counts
        },
        "concepts": {
            "total": len(concepts),
            "top": concepts[:10]
        },
        "stats": {
            "sessions_analyzed": sessions_count,
            "threads_archived": archived_count,
            "ltm_size_mb": round(ltm_size_mb, 2)
        }
    }
```

---

## ✅ Critères de Complétion Sprint P3

### Frontend
- [x] Composant ProactiveHintsUI créé et fonctionnel
- [x] Event listener ws:proactive_hint implémenté
- [x] Affichage banners avec animations smooth
- [x] Actions utilisateur (Appliquer, Ignorer, Snooze)
- [x] Gestion multiple hints (max 3, tri relevance)
- [x] LocalStorage pour snooze hints
- [x] Dashboard MemoryDashboard créé
- [x] Fetch et affichage stats utilisateur
- [x] Sections Préférences, Concepts, Stats globales
- [x] Styles CSS complets (proactive-hints.css)
- [x] Intégration dans app principale (main.js)

### Backend
- [x] Endpoint GET /api/memory/user/stats implémenté
- [x] Fetch preferences, concepts, stats depuis ChromaDB
- [x] Tri et formatage données (top 10 items)
- [x] Gestion erreurs gracieuse

### Tests
- [x] Tests E2E Playwright (proactive-hints.spec.js)
- [x] Test affichage hint
- [x] Test dismiss hint
- [x] Test snooze hint
- [x] Test max 3 hints
- [x] Test dashboard render

### Documentation
- [x] Mettre à jour MEMORY_CAPABILITIES.md (section Frontend UI)
- [x] Mettre à jour memory-roadmap.md (marquer Sprint 3 COMPLET)
- [x] Créer P3_SPRINT3_FRONTEND_STATUS.md (document validation)
- [x] Mettre à jour P2_COMPLETION_FINAL_STATUS.md (ajouter Sprint 3)

---

## 📚 Documentation à Mettre à Jour en Fin de Sprint

### 1. MEMORY_CAPABILITIES.md

**Ajouter section 11bis** : Frontend UI (après section 11)

```markdown
## 🎨 11bis. INTERFACE UTILISATEUR HINTS PROACTIFS

### **ProactiveHintsUI Component**

**Fichier**: [ProactiveHintsUI.js](../src/frontend/features/memory/ProactiveHintsUI.js)

**Fonctionnalités**:
- Affichage banners hints (top-right, non-intrusif)
- 3 types visuels (💡 preference, 📋 intent, ⚠️ constraint)
- Actions: Appliquer, Ignorer, Snooze (1h)
- Auto-dismiss 10s
- Max 3 hints simultanés (tri relevance_score)

**Event WebSocket**: `ws:proactive_hint`

**Screenshot**: (ajouter screenshot si possible)

### **MemoryDashboard Component**

**Fichier**: [MemoryDashboard.js](../src/frontend/features/memory/MemoryDashboard.js)

**Sections**:
1. Stats globales (sessions, threads, taille LTM)
2. Top 10 préférences (confiance, type, date)
3. Top 10 concepts (mentions, dernière mention)
4. Timeline concepts (Chart.js)

**Endpoint API**: `GET /api/memory/user/stats`

**Route**: `/memory`
```

### 2. memory-roadmap.md

**Mettre à jour section P2** :

```markdown
### P2 — Performance & Réactivité proactive ✅ COMPLÉTÉ (2025-10-10)
- ✅ **P2 Sprint 1** : Optimisations performance (-71% latence)
- ✅ **P2 Sprint 2** : ProactiveHints backend + intégration ChatService
- ✅ **P2 Sprint 3** : Frontend UI hints proactifs + Dashboard mémoire
  - ✅ ProactiveHintsUI component (banners, actions, snooze)
  - ✅ MemoryDashboard component (stats, préférences, concepts)
  - ✅ Endpoint backend GET /api/memory/user/stats
  - ✅ Tests E2E Playwright (5 tests hints + 1 test dashboard)
  - ✅ Styles CSS complets (proactive-hints.css)
  - ✅ Commit : `XXXXXX` feat(P2 Sprint3): ProactiveHints UI + MemoryDashboard

- ✅ **Phase P2 TERMINÉE** : Backend + Frontend complets, prêt production
```

### 3. Créer P2_SPRINT3_FRONTEND_STATUS.md

**Fichier à créer** : `docs/validation/P2_SPRINT3_FRONTEND_STATUS.md`

**Contenu** :
- Vue d'ensemble Sprint 3
- Objectifs (ProactiveHintsUI + MemoryDashboard)
- Travaux accomplis (composants, backend endpoint, tests)
- Screenshots UI (si possible)
- Fichiers créés/modifiés
- Tests E2E résultats
- Prochaines étapes (optimisations UI, A/B testing hints)

### 4. Mettre à jour P2_COMPLETION_FINAL_STATUS.md

**Ajouter section Sprint 3** après Sprint 2 :

```markdown
## ✅ Sprint 3 - Frontend UI (COMPLET)

**Durée**: 2-3 jours
**Statut**: ✅ **TERMINÉ**
**Documentation**: [P2_SPRINT3_FRONTEND_STATUS.md](./P2_SPRINT3_FRONTEND_STATUS.md)

### Réalisations

#### 1. 🔔 ProactiveHintsUI Component
- Event listener ws:proactive_hint
- Affichage banners (3 types visuels)
- Actions: Appliquer, Ignorer, Snooze
- LocalStorage snooze management
- Max 3 hints simultanés

#### 2. 📊 MemoryDashboard Component
- Fetch stats via GET /api/memory/user/stats
- Sections: Préférences, Concepts, Stats globales
- Timeline concepts (Chart.js)
- Responsive design

#### 3. 🎨 Styles CSS
- proactive-hints.css (200+ lignes)
- Animations smooth (slide-in/out)
- Type variants (gradient backgrounds)
- Dashboard cards et grids

#### 4. 🔌 Backend Endpoint
- GET /api/memory/user/stats
- Fetch preferences, concepts depuis ChromaDB
- Database stats (sessions, threads)
- Error handling gracieux

#### 5. 🧪 Tests E2E
- Playwright tests (6 tests)
- Coverage: hints display, dismiss, snooze, max 3, dashboard render

### Métriques Sprint 3
- Composants créés: 2 (ProactiveHintsUI, MemoryDashboard)
- Lignes CSS: ~300
- Tests E2E: 6/6 passants
- Endpoint backend: 1 (user/stats)
```

---

## 🚀 Commandes Utiles

### Démarrage développement
```bash
# Frontend
npm run dev

# Backend (si besoin restart)
python -m uvicorn src.backend.main:app --reload --port 8000
```

### Tests
```bash
# Tests E2E Playwright
npx playwright test tests/e2e/proactive-hints.spec.js

# Tests backend endpoint
python -m pytest tests/backend/features/memory/test_user_stats_endpoint.py -v
```

### Build production
```bash
npm run build
```

---

## 📋 Checklist Session

Avant de commencer :
- [ ] Lire ce prompt en entier
- [ ] Vérifier état backend Sprint P2 (doit être COMPLET)
- [ ] Vérifier event ws:proactive_hint émis par backend

Pendant développement :
- [ ] Créer ProactiveHintsUI.js
- [ ] Créer MemoryDashboard.js
- [ ] Créer proactive-hints.css
- [ ] Implémenter endpoint backend GET /api/memory/user/stats
- [ ] Écrire tests E2E Playwright
- [ ] Tester manuellement UI (affichage hints, dashboard)

Avant de terminer session :
- [ ] Valider tous tests E2E passent
- [ ] Mettre à jour MEMORY_CAPABILITIES.md (section Frontend)
- [ ] Mettre à jour memory-roadmap.md (marquer Sprint 3 COMPLET)
- [ ] Créer P2_SPRINT3_FRONTEND_STATUS.md
- [ ] Mettre à jour P2_COMPLETION_FINAL_STATUS.md
- [ ] Créer commit(s) propres avec messages détaillés
- [ ] Vérifier cross-références docs

---

## 🎯 Objectif Final Session

À la fin de cette session, la **Phase P2 complète (Sprints 1+2+3)** doit être TERMINÉE avec :

✅ **Backend** : Performance + ProactiveHints engine (Sprint 1+2)
✅ **Frontend** : UI hints + Dashboard mémoire (Sprint 3)
✅ **Tests** : 21 tests backend + 6 tests E2E frontend
✅ **Documentation** : 4 docs status + 2 docs architecture mis à jour

**Prêt pour déploiement production P2 complet ! 🚀**

---

**Dernière mise à jour** : 2025-10-10
**Auteur** : Claude Code
**Statut** : Prompt prêt pour Sprint P3
