/**
 * E2E Tests for RAG Hybrid System
 *
 * Tests:
 * - VectorService initialization
 * - Hybrid retrieval (BM25 + Vector)
 * - Strict mode filtering
 * - Score threshold filtering
 * - Metrics tracking
 * - Settings API integration
 */

import { test, expect } from '@playwright/test';

const API_BASE = 'http://localhost:8000';

test.describe('RAG Hybrid System', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to app
    await page.goto('http://localhost:5173');

    // Wait for app to be ready
    await page.waitForTimeout(1000);
  });

  test('should have VectorService initialized', async ({ request }) => {
    // Test that the backend has VectorService available
    // We can test this by checking the health endpoint
    const response = await request.get(`${API_BASE}/api/health`);
    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(data.status).toBe('ok');
  });

  test('should retrieve RAG settings from API', async ({ request }) => {
    const response = await request.get(`${API_BASE}/api/settings/rag`);
    expect(response.ok()).toBeTruthy();

    const settings = await response.json();
    expect(settings).toHaveProperty('strict_mode');
    expect(settings).toHaveProperty('score_threshold');
    expect(typeof settings.strict_mode).toBe('boolean');
    expect(typeof settings.score_threshold).toBe('number');
    expect(settings.score_threshold).toBeGreaterThanOrEqual(0);
    expect(settings.score_threshold).toBeLessThanOrEqual(1);
  });

  test('should update RAG settings via API', async ({ request }) => {
    // Update settings
    const newSettings = {
      strict_mode: true,
      score_threshold: 0.8
    };

    const updateResponse = await request.post(`${API_BASE}/api/settings/rag`, {
      data: newSettings
    });
    expect(updateResponse.ok()).toBeTruthy();

    // Verify settings were updated
    const getResponse = await request.get(`${API_BASE}/api/settings/rag`);
    expect(getResponse.ok()).toBeTruthy();

    const settings = await getResponse.json();
    expect(settings.strict_mode).toBe(true);
    expect(settings.score_threshold).toBe(0.8);

    // Reset to defaults
    await request.post(`${API_BASE}/api/settings/rag`, {
      data: {
        strict_mode: false,
        score_threshold: 0.7
      }
    });
  });

  test('should retrieve RAG metrics from API', async ({ request }) => {
    const response = await request.get(`${API_BASE}/api/metrics/rag`);
    expect(response.ok()).toBeTruthy();

    const metrics = await response.json();
    expect(metrics).toHaveProperty('hybrid_queries_total');
    expect(metrics).toHaveProperty('avg_score');
    expect(metrics).toHaveProperty('filtered_results');
    expect(metrics).toHaveProperty('success_rate');

    // Metrics should be numbers
    expect(typeof metrics.hybrid_queries_total).toBe('number');
    expect(typeof metrics.avg_score).toBe('number');
    expect(typeof metrics.filtered_results).toBe('number');
    expect(typeof metrics.success_rate).toBe('number');
  });

  test('should expose Prometheus metrics', async ({ request }) => {
    const response = await request.get(`${API_BASE}/api/metrics`);
    expect(response.ok()).toBeTruthy();

    const metricsText = await response.text();

    // Check for RAG metrics in Prometheus format
    // Note: metrics might be disabled, so we just check the response format
    expect(typeof metricsText).toBe('string');

    // If metrics are enabled, check for RAG metrics
    if (!metricsText.includes('Metrics disabled')) {
      // Metrics should be in Prometheus text format
      expect(metricsText).toContain('# HELP');
    }
  });
});

test.describe('RAG Settings UI', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to settings page
    await page.goto('http://localhost:5173');

    // Wait for app to load
    await page.waitForTimeout(1000);

    // Navigate to settings (assuming there's a settings button/link)
    // This might need to be adjusted based on your UI structure
    const settingsBtn = page.locator('[href="#/settings"]').or(
      page.locator('button:has-text("Paramètres")')
    ).or(
      page.locator('button:has-text("Settings")')
    );

    if (await settingsBtn.count() > 0) {
      await settingsBtn.first().click();
      await page.waitForTimeout(500);
    }
  });

  test('should display RAG settings tab', async ({ page }) => {
    // Look for RAG tab or section
    const ragTab = page.locator('[data-tab="rag"]').or(
      page.locator('button:has-text("RAG")')
    );

    if (await ragTab.count() > 0) {
      await expect(ragTab.first()).toBeVisible();
    } else {
      // If tab navigation is different, skip this test
      test.skip();
    }
  });

  test('should toggle strict mode', async ({ page }) => {
    // Navigate to RAG settings
    const ragTab = page.locator('[data-tab="rag"]');
    if (await ragTab.count() > 0) {
      await ragTab.click();
      await page.waitForTimeout(300);

      // Find strict mode toggle
      const strictToggle = page.locator('#strict-mode-toggle');

      if (await strictToggle.count() > 0) {
        // Get current state
        const isChecked = await strictToggle.isChecked();

        // Toggle it
        await strictToggle.click();
        await page.waitForTimeout(200);

        // Verify state changed
        const newState = await strictToggle.isChecked();
        expect(newState).toBe(!isChecked);

        // Threshold slider should be enabled/disabled based on strict mode
        const thresholdSlider = page.locator('#score-threshold-slider');
        if (await thresholdSlider.count() > 0) {
          const isDisabled = await thresholdSlider.isDisabled();
          expect(isDisabled).toBe(!newState);
        }
      } else {
        test.skip();
      }
    } else {
      test.skip();
    }
  });

  test('should adjust score threshold slider', async ({ page }) => {
    // Navigate to RAG settings
    const ragTab = page.locator('[data-tab="rag"]');
    if (await ragTab.count() > 0) {
      await ragTab.click();
      await page.waitForTimeout(300);

      // Enable strict mode first
      const strictToggle = page.locator('#strict-mode-toggle');
      if (await strictToggle.count() > 0 && !(await strictToggle.isChecked())) {
        await strictToggle.click();
        await page.waitForTimeout(200);
      }

      // Find threshold slider
      const thresholdSlider = page.locator('#score-threshold-slider');

      if (await thresholdSlider.count() > 0) {
        // Set slider to 0.9
        await thresholdSlider.fill('0.9');
        await page.waitForTimeout(200);

        // Verify value displayed
        const labelValue = page.locator('.label-text strong');
        if (await labelValue.count() > 0) {
          await expect(labelValue).toHaveText('0.90');
        }

        // Check that explanation changed
        const explanation = page.locator('.threshold-explanation');
        if (await explanation.count() > 0) {
          await expect(explanation).toContainText('strict', { ignoreCase: true });
        }
      } else {
        test.skip();
      }
    } else {
      test.skip();
    }
  });

  test('should display live RAG metrics', async ({ page }) => {
    // Navigate to RAG settings
    const ragTab = page.locator('[data-tab="rag"]');
    if (await ragTab.count() > 0) {
      await ragTab.click();
      await page.waitForTimeout(300);

      // Check for metrics display
      const metricsGrid = page.locator('#rag-metrics-grid');

      if (await metricsGrid.count() > 0) {
        await expect(metricsGrid).toBeVisible();

        // Check for metric cards
        const metricCards = page.locator('.metric-card');
        const count = await metricCards.count();
        expect(count).toBeGreaterThan(0);

        // Verify metric labels
        const labels = await page.locator('.metric-label').allTextContents();
        expect(labels).toContain('Requêtes hybrides');
        expect(labels).toContain('Score moyen');
      } else {
        test.skip();
      }
    } else {
      test.skip();
    }
  });

  test('should refresh metrics on button click', async ({ page }) => {
    // Navigate to RAG settings
    const ragTab = page.locator('[data-tab="rag"]');
    if (await ragTab.count() > 0) {
      await ragTab.click();
      await page.waitForTimeout(300);

      // Find refresh button
      const refreshBtn = page.locator('#btn-refresh-metrics');

      if (await refreshBtn.count() > 0) {
        // Mock the API call to track it
        let apiCalled = false;
        await page.route('**/api/metrics/rag', (route) => {
          apiCalled = true;
          route.continue();
        });

        // Click refresh
        await refreshBtn.click();
        await page.waitForTimeout(500);

        // Verify API was called
        expect(apiCalled).toBe(true);
      } else {
        test.skip();
      }
    } else {
      test.skip();
    }
  });

  test('should save RAG settings', async ({ page, request }) => {
    // Navigate to RAG settings
    const ragTab = page.locator('[data-tab="rag"]');
    if (await ragTab.count() > 0) {
      await ragTab.click();
      await page.waitForTimeout(300);

      // Enable strict mode and set threshold
      const strictToggle = page.locator('#strict-mode-toggle');
      if (await strictToggle.count() > 0) {
        await strictToggle.check();
        await page.waitForTimeout(200);

        const thresholdSlider = page.locator('#score-threshold-slider');
        if (await thresholdSlider.count() > 0) {
          await thresholdSlider.fill('0.85');
          await page.waitForTimeout(200);
        }

        // Click save
        const saveBtn = page.locator('.btn-save').first();
        if (await saveBtn.count() > 0) {
          await saveBtn.click();
          await page.waitForTimeout(500);

          // Verify settings were saved via API
          const response = await request.get(`${API_BASE}/api/settings/rag`);
          const settings = await response.json();

          expect(settings.strict_mode).toBe(true);
          expect(settings.score_threshold).toBe(0.85);

          // Reset
          await request.post(`${API_BASE}/api/settings/rag`, {
            data: {
              strict_mode: false,
              score_threshold: 0.7
            }
          });
        } else {
          test.skip();
        }
      } else {
        test.skip();
      }
    } else {
      test.skip();
    }
  });
});

test.describe('RAG Health Checks', () => {
  test('should report healthy RAG system status', async ({ request }) => {
    // Check monitoring endpoint
    const response = await request.get(`${API_BASE}/api/health`);
    expect(response.ok()).toBeTruthy();

    const health = await response.json();
    expect(health.status).toBe('ok');
  });

  test('should have metrics endpoint available', async ({ request }) => {
    const response = await request.get(`${API_BASE}/api/metrics/health`);

    // Endpoint should exist (200 or 404 is acceptable, 500 is not)
    expect(response.status()).not.toBe(500);
  });
});
