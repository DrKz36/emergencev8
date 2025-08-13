/**
 * @module core/event-bus
 * @description Système d'événements V9.0 - "Béton Armé"
 * - Logique de 'off' confirmée et utilisée pour le nettoyage de la mémoire.
 * - Ajout de logs pour le désabonnement.
 */

export class EventBus {
  constructor() {
    this.events = new Map();
    this.debug = true;
  }

  on(event, handler) {
    if (!this.events.has(event)) {
      this.events.set(event, new Set());
    }
    this.events.get(event).add(handler);
    if (this.debug) {
      if (event) console.log(`[EventBus] Subscribed to: ${event}`);
    }
    // Retourne une fonction de désinscription pour un usage facile
    return () => this.off(event, handler);
  }

  off(event, handler) {
    if (this.events.has(event)) {
      const eventHandlers = this.events.get(event);
      if (eventHandlers.has(handler)) {
        eventHandlers.delete(handler);
        if (this.debug) {
            console.log(`[EventBus] Unsubscribed from: ${event}`);
        }
        if (eventHandlers.size === 0) {
          this.events.delete(event);
          if (this.debug) {
            console.log(`[EventBus] No more listeners for: ${event}. Event removed.`);
          }
        }
      }
    }
  }

  emit(event, data = null) {
    if (event === undefined || event === 'undefined') {
        console.trace('%c[EventBus] ALERTE: Tentative d\'émission d\'un événement UNDEFINED.', 'color: red; font-weight: bold;', data);
        return;
    }

    if (this.debug) {
      console.log(`%c[EventBus] Emitting: ${event}`, 'color: #84cc16;', data);
    }

    if (this.events.has(event)) {
      this.events.get(event).forEach(handler => {
        try {
          handler(data);
        } catch (error) {
          console.error(`[EventBus] Error in handler for event ${event}:`, error);
        }
      });
    }
  }
}
