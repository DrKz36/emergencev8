/**
 * E2E Tests for Proactive Hints UI - Sprint P3
 *
 * Tests:
 * - Display hint banner when ws:proactive_hint received
 * - Dismiss hint
 * - Snooze hint (localStorage)
 * - Max 3 hints enforcement
 * - Dashboard render
 * - API mock integration
 */

import { test, expect } from '@playwright/test';

test.describe('Proactive Hints UI', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to app (Vite dev server on port 5173)
    await page.goto('http://localhost:5173');

    // Wait for EventBus to be ready
    await page.waitForFunction(() => {
      return window.EventBus && typeof window.EventBus.getInstance === 'function';
    });
  });

  test('should display hint banner when ws:proactive_hint received', async ({ page }) => {
    // Simulate WebSocket event
    await page.evaluate(() => {
      const eventBus = window.EventBus.getInstance();
      eventBus.emit('ws:proactive_hint', {
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
    const banner = page.locator('.proactive-hint-banner');
    await expect(banner).toBeVisible({ timeout: 2000 });
    await expect(banner).toHaveClass(/visible/);

    // Check content
    await expect(page.locator('.hint-title')).toHaveText('Test Hint');
    await expect(page.locator('.hint-message')).toHaveText('This is a test hint');
    await expect(page.locator('.hint-relevance')).toContainText('85%');
  });

  test('should display correct icon for hint type', async ({ page }) => {
    // Test preference_reminder icon
    await page.evaluate(() => {
      const eventBus = window.EventBus.getInstance();
      eventBus.emit('ws:proactive_hint', {
        hints: [{
          id: 'hint_pref',
          type: 'preference_reminder',
          title: 'Preference',
          message: 'Test',
          relevance_score: 0.8
        }]
      });
    });

    let icon = page.locator('.hint-icon');
    await expect(icon).toHaveText('💡');

    // Clear and test intent_followup
    await page.evaluate(() => {
      window.__proactiveHintsUI?.clearAllHints();
    });

    await page.evaluate(() => {
      const eventBus = window.EventBus.getInstance();
      eventBus.emit('ws:proactive_hint', {
        hints: [{
          id: 'hint_intent',
          type: 'intent_followup',
          title: 'Intent',
          message: 'Test',
          relevance_score: 0.7
        }]
      });
    });

    icon = page.locator('.hint-icon').last();
    await expect(icon).toHaveText('📋');
  });

  test('should dismiss hint on dismiss button click', async ({ page }) => {
    // Trigger hint
    await page.evaluate(() => {
      const eventBus = window.EventBus.getInstance();
      eventBus.emit('ws:proactive_hint', {
        hints: [{
          id: 'hint_test_456',
          type: 'intent_followup',
          title: 'Test Intent',
          message: 'Test message',
          relevance_score: 0.75
        }]
      });
    });

    // Wait for banner
    const banner = page.locator('.proactive-hint-banner');
    await expect(banner).toBeVisible();

    // Click dismiss
    await page.click('.hint-action-dismiss');

    // Check banner dismissed (has dismissing class)
    await expect(banner).toHaveClass(/dismissing/);

    // Wait for animation and removal
    await page.waitForTimeout(400);
    await expect(banner).not.toBeAttached();
  });

  test('should snooze hint and not show again', async ({ page }) => {
    const hintId = 'hint_snooze_test';

    // Trigger hint
    await page.evaluate((id) => {
      const eventBus = window.EventBus.getInstance();
      eventBus.emit('ws:proactive_hint', {
        hints: [{
          id,
          type: 'preference_reminder',
          title: 'Snooze Test',
          message: 'Test',
          relevance_score: 0.8
        }]
      });
    }, hintId);

    // Wait for banner
    await expect(page.locator('.proactive-hint-banner')).toBeVisible();

    // Click snooze
    await page.click('.hint-action-snooze');

    // Wait for dismissal
    await page.waitForTimeout(400);

    // Check localStorage
    const snoozeValue = await page.evaluate((id) => {
      return localStorage.getItem(`hint_snooze_${id}`);
    }, hintId);

    expect(snoozeValue).toBeTruthy();
    expect(parseInt(snoozeValue)).toBeGreaterThan(Date.now());

    // Re-emit same hint
    await page.evaluate((id) => {
      const eventBus = window.EventBus.getInstance();
      eventBus.emit('ws:proactive_hint', {
        hints: [{
          id,
          type: 'preference_reminder',
          title: 'Snooze Test',
          message: 'Test',
          relevance_score: 0.8
        }]
      });
    }, hintId);

    // Should not appear (snoozed)
    await page.waitForTimeout(300);
    const banners = await page.locator('.proactive-hint-banner').count();
    expect(banners).toBe(0);
  });

  test('should display max 3 hints when multiple received', async ({ page }) => {
    // Emit 5 hints
    await page.evaluate(() => {
      const eventBus = window.EventBus.getInstance();
      eventBus.emit('ws:proactive_hint', {
        hints: Array.from({ length: 5 }, (_, i) => ({
          id: `hint_${i}`,
          type: 'preference_reminder',
          title: `Hint ${i}`,
          message: `Message ${i}`,
          relevance_score: 0.9 - (i * 0.1)
        }))
      });
    });

    // Wait for banners
    await page.waitForTimeout(300);

    // Should display exactly 3
    const banners = await page.locator('.proactive-hint-banner').count();
    expect(banners).toBe(3);

    // Verify highest relevance hints are shown (0, 1, 2)
    const titles = await page.locator('.hint-title').allTextContents();
    expect(titles).toContain('Hint 0');
    expect(titles).toContain('Hint 1');
    expect(titles).toContain('Hint 2');
    expect(titles).not.toContain('Hint 3');
    expect(titles).not.toContain('Hint 4');
  });

  test('should apply hint to chat input when apply button clicked', async ({ page }) => {
    // Create a mock chat input
    await page.evaluate(() => {
      const input = document.createElement('textarea');
      input.id = 'chat-input';
      document.body.appendChild(input);
    });

    // Trigger hint with action_payload
    await page.evaluate(() => {
      const eventBus = window.EventBus.getInstance();
      eventBus.emit('ws:proactive_hint', {
        hints: [{
          id: 'hint_apply_test',
          type: 'preference_reminder',
          title: 'Apply Test',
          message: 'Test',
          relevance_score: 0.9,
          action_label: 'Apply Preference',
          action_payload: {
            preference: 'I prefer Python for scripting'
          }
        }]
      });
    });

    // Wait for banner
    await expect(page.locator('.proactive-hint-banner')).toBeVisible();

    // Click apply
    await page.click('.hint-action-primary');

    // Check input value
    const inputValue = await page.inputValue('#chat-input');
    expect(inputValue).toBe('I prefer Python for scripting');

    // Banner should be dismissed
    await page.waitForTimeout(400);
    await expect(page.locator('.proactive-hint-banner')).not.toBeAttached();
  });

  test('should auto-dismiss hint after 10 seconds', async ({ page }) => {
    // Trigger hint
    await page.evaluate(() => {
      const eventBus = window.EventBus.getInstance();
      eventBus.emit('ws:proactive_hint', {
        hints: [{
          id: 'hint_auto_dismiss',
          type: 'preference_reminder',
          title: 'Auto Dismiss Test',
          message: 'This should auto-dismiss',
          relevance_score: 0.7
        }]
      });
    });

    // Wait for banner
    const banner = page.locator('.proactive-hint-banner');
    await expect(banner).toBeVisible();

    // Wait for auto-dismiss (10s + animation)
    await page.waitForTimeout(10500);

    // Banner should be gone
    await expect(banner).not.toBeAttached();
  });
});

test.describe('Memory Dashboard', () => {
  test('should render dashboard with stats', async ({ page }) => {
    // Mock API response
    await page.route('/api/memory/user/stats', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          preferences: {
            total: 12,
            top: [
              {
                topic: 'python',
                confidence: 0.92,
                type: 'preference',
                captured_at: '2025-10-05T10:00:00Z'
              },
              {
                topic: 'docker',
                confidence: 0.87,
                type: 'intent',
                captured_at: '2025-10-03T14:30:00Z'
              }
            ],
            by_type: { preference: 8, intent: 3, constraint: 1 }
          },
          concepts: {
            total: 47,
            top: [
              {
                concept: 'containerization',
                mentions: 5,
                last_mentioned: '2025-10-07T09:15:00Z'
              },
              {
                concept: 'CI/CD pipeline',
                mentions: 3,
                last_mentioned: '2025-10-06T16:20:00Z'
              }
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

    // Create dashboard container and render
    await page.evaluate(async () => {
      const { MemoryDashboard } = await import('./features/memory/MemoryDashboard.js');
      const container = document.createElement('div');
      container.id = 'memory-dashboard-root';
      document.body.appendChild(container);

      const dashboard = new MemoryDashboard(container);
      await dashboard.render();
    });

    // Wait for dashboard to render
    await page.waitForSelector('.memory-dashboard', { timeout: 3000 });

    // Check stats cards
    const statValues = await page.locator('.stat-value').allTextContents();
    expect(statValues).toContain('23');
    expect(statValues).toContain('5');
    expect(statValues).toContain('2.4 MB');

    // Check preferences section
    await expect(page.locator('.preference-topic').first()).toHaveText('python');
    await expect(page.locator('.preference-confidence').first()).toContainText('92%');

    // Check concepts section
    await expect(page.locator('.concept-text').first()).toHaveText('containerization');
    await expect(page.locator('.concept-mentions').first()).toContainText('5 mentions');
  });

  test('should show loading state', async ({ page }) => {
    // Delay API response
    await page.route('/api/memory/user/stats', async (route) => {
      await new Promise(resolve => setTimeout(resolve, 2000));
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          preferences: { total: 0, top: [], by_type: {} },
          concepts: { total: 0, top: [] },
          stats: { sessions_analyzed: 0, threads_archived: 0, ltm_size_mb: 0 }
        })
      });
    });

    // Create dashboard and render
    await page.evaluate(async () => {
      const { MemoryDashboard } = await import('./features/memory/MemoryDashboard.js');
      const container = document.createElement('div');
      container.id = 'memory-dashboard-root';
      document.body.appendChild(container);

      const dashboard = new MemoryDashboard(container);
      dashboard.render(); // Don't await
    });

    // Check loading state
    await expect(page.locator('.memory-dashboard.loading')).toBeVisible();
    await expect(page.locator('.spinner')).toBeVisible();
  });

  test('should show error state on API failure', async ({ page }) => {
    // Mock API error
    await page.route('/api/memory/user/stats', (route) => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Internal server error' })
      });
    });

    // Create dashboard and render
    await page.evaluate(async () => {
      const { MemoryDashboard } = await import('./features/memory/MemoryDashboard.js');
      const container = document.createElement('div');
      container.id = 'memory-dashboard-root';
      document.body.appendChild(container);

      const dashboard = new MemoryDashboard(container);
      await dashboard.render();
    });

    // Check error state
    await expect(page.locator('.memory-dashboard.error')).toBeVisible();
    await expect(page.locator('.error-detail')).toBeVisible();
  });
});
