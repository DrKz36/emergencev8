// src/frontend/features/memory/memory-center.js
// Minimal MemoryCenter stub to keep chat module compatible while the overlay evolves.

export class MemoryCenter {
  constructor(eventBus, stateManager) {
    this.eventBus = eventBus || null;
    this.stateManager = stateManager || null;
    this._initialized = false;
  }

  init() {
    this._initialized = true;
  }

  open() {}
  refresh() {}
  hydrate() {}
}
