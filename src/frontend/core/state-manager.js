/**
 * @module core/state-manager
 * @description Gestionnaire d'état V14. "Input Validation"
 * - Ajout d'une validation dans la méthode set() pour empêcher de stocker des valeurs 'undefined'.
 * @version V14.0
 */

import { AGENTS } from '../shared/constants.js';

export class StateManager {
    constructor() {
        this.DEFAULT_STATE = this.getInitialState();
        this.state = this.DEFAULT_STATE;
        
        this.subscribers = new Map();
        console.log("✅ StateManager V14 (Input Validation) Constructor: Default state is set.");
    }

    async init() {
        const savedState = this.loadFromStorage();
        let mergedState = this._deepMerge(this.DEFAULT_STATE, savedState);
        this.state = this.sanitize(mergedState);
        console.log("[StateManager] V14 Initialized: State loaded from localStorage and sanitized.");
        this.persist();
    }

    sanitize(stateToClean) {
        let cleanState = { ...stateToClean };

        cleanState.agents = cleanState.agents || {};
        for (const agentId of Object.keys(AGENTS)) {
            cleanState.agents[agentId] = cleanState.agents[agentId] || { status: 'disconnected', history: [] };
        }

        cleanState.connection = cleanState.connection || { status: 'disconnected', attempt: 0 };
        cleanState.costs = cleanState.costs || { total: 0, last_session: 0 };
        cleanState.debate = cleanState.debate || { status: 'idle', topic: null, history: [] };
        cleanState.user = cleanState.user || { id: 'FG', name: 'Fernando' };
        
        return cleanState;
    }

    getInitialState() {
        return this.sanitize({});
    }

    get(key) {
        return key.split('.').reduce((acc, part) => acc && acc[part], this.state);
    }

    set(key, value) {
        // ACTION 2.2: Validation d'entrée pour empêcher les données corrompues.
        if (value === undefined) {
            console.warn(`[StateManager] Tentative de 'set' avec une valeur 'undefined' pour la clé '${key}'. Opération bloquée.`);
            return;
        }

        const keys = key.split('.');
        const lastKey = keys.pop();
        let target = this.state;

        for (let part of keys) {
            if (!target[part] || typeof target[part] !== 'object') {
                target[part] = {};
            }
            target = target[part];
        }

        target[lastKey] = value;
        
        this.notify(key);
        this.persist();
    }

    subscribe(key, callback) {
        if (!this.subscribers.has(key)) {
            this.subscribers.set(key, []);
        }
        this.subscribers.get(key).push(callback);
        // On pourrait retourner une fonction de désinscription ici aussi.
        // return () => this.unsubscribe(key, callback);
    }

    notify(changedKey) {
        this.subscribers.forEach((callbacks, key) => {
            if (changedKey.startsWith(key)) {
                const value = this.get(key);
                callbacks.forEach(cb => cb(value));
            }
        });
    }

    persist() {
        try {
            localStorage.setItem('emergenceState-V14', JSON.stringify(this.state));
        } catch (error) {
            console.error('[StateManager] Error persisting state:', error);
        }
    }

    loadFromStorage() {
        try {
            const savedState = localStorage.getItem('emergenceState-V14');
            return savedState ? JSON.parse(savedState) : {};
        } catch (error) {
            console.error('[StateManager] Error loading state, returning empty object.', error);
            return {};
        }
    }

    _deepMerge(target, source) {
        const output = { ...target };
        if (source && typeof source === 'object') {
            for (const key in source) {
                if (Object.prototype.hasOwnProperty.call(source, key)) {
                    if (source[key] && typeof source[key] === 'object' && !Array.isArray(source[key])) {
                        output[key] = this._deepMerge(target[key] || {}, source[key]);
                    } else {
                        output[key] = source[key];
                    }
                }
            }
        }
        return output;
    }
}
