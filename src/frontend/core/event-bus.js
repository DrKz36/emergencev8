/**
 * @module core/event-bus
 * EventBus V3.1 (ESM) — singleton + class + import styles multiples
 *
 * ✅ Utilisations possibles :
 *   import EventBus from '../../core/event-bus.js'
 *   const bus = EventBus.getInstance()
 *
 *   import { EventBus, eventBus } from '../../core/event-bus.js'
 *   eventBus.emit('event', payload)
 */
class EventBus {
  constructor() {
    this.listeners = new Map(); // Map<string, Set<Function>>
    this._debug = false;
  }

  /** Retourne l'instance globale (idempotent) */
  static getInstance() {
    const g = (typeof globalThis !== 'undefined') ? globalThis : window;
    if (!g.__EMERGENCE_EVENT_BUS__) {
      g.__EMERGENCE_EVENT_BUS__ = new EventBus();
    }
    return g.__EMERGENCE_EVENT_BUS__;
  }

  /** Subscribe; retourne une fonction d’unsubscribe */
  on(event, fn) {
    if (!event || typeof fn !== 'function') return () => {};
    if (!this.listeners.has(event)) this.listeners.set(event, new Set());
    this.listeners.get(event).add(fn);
    return () => this.off(event, fn);
  }

  /** Subscribe once (corrigé) */
  once(event, fn) {
    const off = this.on(event, (...args) => {
      try { fn(...args); } finally { off(); }
    });
    return off;
  }

  /** Unsubscribe */
  off(event, fn) {
    if (!this.listeners.has(event)) return;
    if (!fn) this.listeners.get(event).clear();
    else this.listeners.get(event).delete(fn);
  }

  /** Emit */
  emit(event, payload) {
    if (this._debug) console.log(`[EventBus] Emitting: ${event}`, payload);
    const fns = Array.from(this.listeners.get(event) ?? []);
    for (const fn of fns) {
      try { fn(payload); } catch (err) { console.error(`[EventBus] listener error for ${event}`, err); }
    }
  }

  /** Aliases */
  subscribe(event, fn) { return this.on(event, fn); }
  unsubscribe(event, fn) { this.off(event, fn); }

  /** Misc */
  enableDebug(v = true) { this._debug = !!v; }
  removeAllListeners() { this.listeners.clear(); }
}

const eventBus = EventBus.getInstance();
export { EventBus, eventBus };
export default EventBus;
