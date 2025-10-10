/**
 * @module features/memory/ProactiveHintsUI
 * ProactiveHintsUI Component - Sprint P3
 *
 * Affiche des banners de hints proactifs reçus via WebSocket (event: ws:proactive_hint)
 *
 * Fonctionnalités:
 * - Event listener ws:proactive_hint
 * - Affichage banners (max 3 simultanés, tri par relevance)
 * - Actions: Appliquer, Ignorer, Snooze (1h)
 * - Auto-dismiss après 10s
 * - LocalStorage pour snooze management
 */

import { EventBus } from '../../core/event-bus.js';

export class ProactiveHintsUI {
  constructor(container) {
    this.container = container;
    this.activeHints = [];
    this.maxHints = 3;
    this.autoDismissDelay = 10000; // 10 seconds
    this.snoozeDelay = 3600000; // 1 hour
    this.setupEventListeners();
    console.info('[ProactiveHintsUI] Initialized');
  }

  setupEventListeners() {
    const eventBus = EventBus.getInstance();

    // Listen to WebSocket proactive hints
    eventBus.on('ws:proactive_hint', this.handleProactiveHint.bind(this));

    console.info('[ProactiveHintsUI] Event listeners registered for ws:proactive_hint');
  }

  handleProactiveHint(data) {
    console.info('[ProactiveHintsUI] Received ws:proactive_hint event', data);

    const hints = data.hints || [];

    if (!Array.isArray(hints) || hints.length === 0) {
      console.warn('[ProactiveHintsUI] No hints in payload');
      return;
    }

    // Filter snoozed hints (check localStorage)
    const activeHints = hints.filter(h => !this.isHintSnoozed(h.id));

    if (activeHints.length === 0) {
      console.info('[ProactiveHintsUI] All hints are snoozed, skipping display');
      return;
    }

    // Sort by relevance score (descending)
    activeHints.sort((a, b) => (b.relevance_score || 0) - (a.relevance_score || 0));

    // Display max 3 hints
    const hintsToDisplay = activeHints.slice(0, this.maxHints);

    console.info(`[ProactiveHintsUI] Displaying ${hintsToDisplay.length} hints`);

    hintsToDisplay.forEach(hint => {
      this.displayHintBanner(hint);
    });
  }

  displayHintBanner(hint) {
    const banner = document.createElement('div');
    banner.className = `proactive-hint-banner hint-${hint.type}`;
    banner.dataset.hintId = hint.id;

    const iconHtml = `<div class="hint-icon">${this.getIconForType(hint.type)}</div>`;

    const contentHtml = `
      <div class="hint-content">
        <div class="hint-title">${this.escapeHtml(hint.title)}</div>
        <div class="hint-message">${this.escapeHtml(hint.message)}</div>
        <div class="hint-meta">
          <span class="hint-relevance">Pertinence: ${Math.round((hint.relevance_score || 0) * 100)}%</span>
        </div>
      </div>
    `;

    const actionsHtml = `
      <div class="hint-actions">
        ${hint.action_label ? `<button class="hint-action-primary" data-action="apply">${this.escapeHtml(hint.action_label)}</button>` : ''}
        <button class="hint-action-snooze" data-action="snooze" title="Rappeler dans 1h">🕐 Plus tard</button>
        <button class="hint-action-dismiss" data-action="dismiss" title="Ignorer">✕</button>
      </div>
    `;

    banner.innerHTML = iconHtml + contentHtml + actionsHtml;

    // Event listeners for actions
    const applyBtn = banner.querySelector('[data-action="apply"]');
    if (applyBtn) {
      applyBtn.addEventListener('click', () => {
        this.applyHint(hint);
        this.dismissHint(hint.id);
      });
    }

    banner.querySelector('[data-action="snooze"]').addEventListener('click', () => {
      this.snoozeHint(hint.id, this.snoozeDelay);
      this.dismissHint(hint.id);
    });

    banner.querySelector('[data-action="dismiss"]').addEventListener('click', () => {
      this.dismissHint(hint.id);
    });

    // Append to container with animation
    this.container.appendChild(banner);

    // Trigger animation (after DOM insertion)
    setTimeout(() => {
      banner.classList.add('visible');
    }, 10);

    // Auto-dismiss after delay
    const autoDismissTimer = setTimeout(() => {
      if (banner.parentNode) {
        this.dismissHint(hint.id);
      }
    }, this.autoDismissDelay);

    // Store timer reference to cancel if manually dismissed
    banner.dataset.autoDismissTimer = autoDismissTimer;

    console.info(`[ProactiveHintsUI] Banner displayed for hint ${hint.id}`);
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
    console.info('[ProactiveHintsUI] Applying hint', hint);

    // Logic to apply hint (e.g., copy to input, trigger action)
    if (hint.action_payload?.preference) {
      // Try to copy preference to chat input
      const chatInput = document.querySelector('#chat-input')
                     || document.querySelector('textarea[name="chat-input"]')
                     || document.querySelector('.chat-input');

      if (chatInput) {
        chatInput.value = hint.action_payload.preference;
        chatInput.focus();
        console.info('[ProactiveHintsUI] Preference copied to chat input');
      } else {
        // Fallback: copy to clipboard
        try {
          navigator.clipboard.writeText(hint.action_payload.preference);
          console.info('[ProactiveHintsUI] Preference copied to clipboard');

          // Show notification (if available)
          const eventBus = EventBus.getInstance();
          eventBus.emit('ui:notification', {
            type: 'success',
            message: 'Préférence copiée dans le presse-papier'
          });
        } catch (err) {
          console.error('[ProactiveHintsUI] Failed to copy to clipboard', err);
        }
      }
    }
  }

  snoozeHint(hintId, durationMs) {
    const snoozeUntil = Date.now() + durationMs;

    try {
      localStorage.setItem(`hint_snooze_${hintId}`, snoozeUntil.toString());
      console.info(`[ProactiveHintsUI] Hint ${hintId} snoozed until ${new Date(snoozeUntil).toISOString()}`);

      // Show notification (if available)
      const eventBus = EventBus.getInstance();
      eventBus.emit('ui:notification', {
        type: 'info',
        message: 'Hint reporté d\'1 heure'
      });
    } catch (err) {
      console.error('[ProactiveHintsUI] Failed to snooze hint', err);
    }
  }

  isHintSnoozed(hintId) {
    try {
      const snoozeUntil = localStorage.getItem(`hint_snooze_${hintId}`);
      if (!snoozeUntil) return false;

      const snoozeTimestamp = parseInt(snoozeUntil, 10);
      const isSnoozed = Date.now() < snoozeTimestamp;

      // Clean up expired snooze
      if (!isSnoozed) {
        localStorage.removeItem(`hint_snooze_${hintId}`);
      }

      return isSnoozed;
    } catch (err) {
      console.error('[ProactiveHintsUI] Error checking snooze status', err);
      return false;
    }
  }

  dismissHint(hintId) {
    const banner = this.container.querySelector(`[data-hint-id="${hintId}"]`);

    if (!banner) {
      console.warn(`[ProactiveHintsUI] Banner not found for hint ${hintId}`);
      return;
    }

    // Cancel auto-dismiss timer if exists
    const timerId = banner.dataset.autoDismissTimer;
    if (timerId) {
      clearTimeout(parseInt(timerId, 10));
    }

    // Add dismissing animation
    banner.classList.add('dismissing');
    banner.classList.remove('visible');

    // Remove from DOM after animation
    setTimeout(() => {
      if (banner.parentNode) {
        banner.remove();
      }
    }, 300); // Match CSS transition duration

    console.info(`[ProactiveHintsUI] Banner dismissed for hint ${hintId}`);
  }

  /**
   * Escape HTML to prevent XSS
   */
  escapeHtml(text) {
    if (typeof text !== 'string') return '';

    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  /**
   * Clear all active hints (useful for cleanup)
   */
  clearAllHints() {
    const banners = this.container.querySelectorAll('.proactive-hint-banner');
    banners.forEach(banner => {
      const hintId = banner.dataset.hintId;
      if (hintId) {
        this.dismissHint(hintId);
      }
    });
    console.info('[ProactiveHintsUI] All hints cleared');
  }

  /**
   * Destroy component (cleanup)
   */
  destroy() {
    this.clearAllHints();

    // Remove event listeners
    const eventBus = EventBus.getInstance();
    eventBus.off('ws:proactive_hint', this.handleProactiveHint);

    console.info('[ProactiveHintsUI] Component destroyed');
  }
}
