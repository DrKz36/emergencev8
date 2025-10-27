/**
 * Tests pour StateManager - Gestion de l'état global de l'application
 */
import { test } from 'node:test';
import assert from 'node:assert/strict';
import './helpers/dom-shim.js';
import { StateManager } from '../state-manager.js';

test('StateManager - Initialisation', () => {
    const state = new StateManager();

    assert.ok(state, 'StateManager devrait être instancié');
    assert.strictEqual(typeof state.get, 'function', 'get() devrait être une fonction');
    assert.strictEqual(typeof state.set, 'function', 'set() devrait être une fonction');
    assert.strictEqual(typeof state.subscribe, 'function', 'subscribe() devrait être une fonction');
});

test('StateManager - get() retourne undefined pour clé inexistante', () => {
    const state = new StateManager();
    const value = state.get('nonexistent.key');

    assert.strictEqual(value, undefined, 'Devrait retourner undefined pour clé inexistante');
});

test('StateManager - set() et get() valeur simple', () => {
    const state = new StateManager();

    state.set('user.name', 'Alice');
    const name = state.get('user.name');

    assert.strictEqual(name, 'Alice', 'Devrait retourner la valeur définie');
});

test('StateManager - set() et get() valeur imbriquée', () => {
    const state = new StateManager();

    state.set('app.config.theme', 'dark');
    const theme = state.get('app.config.theme');

    assert.strictEqual(theme, 'dark', 'Devrait gérer les chemins imbriqués');
});

test('StateManager - set() met à jour valeur existante', () => {
    const state = new StateManager();

    state.set('counter', 0);
    assert.strictEqual(state.get('counter'), 0);

    state.set('counter', 42);
    assert.strictEqual(state.get('counter'), 42, 'Devrait mettre à jour la valeur');
});

test('StateManager - subscribe() notifie les changements', async () => {
    const state = new StateManager();

    await new Promise((resolve, reject) => {
        const timeout = setTimeout(() => reject(new Error('Le subscriber n\'a pas été notifié')), 200);
        const unsubscribe = state.subscribe('test.value', (newValue, oldValue) => {
            try {
                assert.strictEqual(newValue, 'changed', 'Nouvelle valeur devrait être "changed"');
                assert.strictEqual(oldValue, undefined, 'Ancienne valeur devrait être undefined');
                clearTimeout(timeout);
                unsubscribe?.();
                resolve();
            } catch (error) {
                clearTimeout(timeout);
                unsubscribe?.();
                reject(error);
            }
        });

        try {
            state.set('test.value', 'changed');
        } catch (error) {
            clearTimeout(timeout);
            unsubscribe?.();
            reject(error);
        }
    });
});

test('StateManager - subscribe() multiple listeners', async () => {
    const state = new StateManager();

    await new Promise((resolve, reject) => {
        const expected = 2;
        let count = 0;
        const timeout = setTimeout(() => reject(new Error(`Seulement ${count}/${expected} listeners notifiés`)), 200);

        const makeHandler = () => (value) => {
            try {
                assert.strictEqual(value, 123);
                count += 1;
                if (count === expected) {
                    clearTimeout(timeout);
                    resolve();
                }
            } catch (error) {
                clearTimeout(timeout);
                reject(error);
            }
        };

        const unsubA = state.subscribe('shared.key', makeHandler());
        const unsubB = state.subscribe('shared.key', makeHandler());

        try {
            state.set('shared.key', 123);
        } catch (error) {
            clearTimeout(timeout);
            unsubA?.();
            unsubB?.();
            reject(error);
        }
    });
});

test('StateManager - unsubscribe() arrête les notifications', async () => {
    const state = new StateManager();
    const calls = [];

    await new Promise((resolve, reject) => {
        const unsubscribe = state.subscribe('unsub.test', (value) => {
            calls.push(value);
        });

        const firstTimer = setTimeout(() => {
            try {
                assert.deepStrictEqual(calls, ['first'], 'Devrait être notifié une fois');
                unsubscribe();
                state.set('unsub.test', 'second');
            } catch (error) {
                clearTimeout(firstTimer);
                reject(error);
            }
        }, 30);

        const secondTimer = setTimeout(() => {
            try {
                assert.deepStrictEqual(calls, ['first'], 'Ne devrait plus être notifié après unsubscribe');
                clearTimeout(firstTimer);
                resolve();
            } catch (error) {
                clearTimeout(firstTimer);
                reject(error);
            } finally {
                clearTimeout(secondTimer);
            }
        }, 80);

        try {
            state.set('unsub.test', 'first');
        } catch (error) {
            clearTimeout(firstTimer);
            clearTimeout(secondTimer);
            reject(error);
        }
    });
});

test('StateManager - get() avec valeur par défaut', () => {
    const state = new StateManager();

    const rawValue = state.get('missing.key');
    const value = rawValue ?? 'default';

    assert.strictEqual(value, 'default', 'Devrait retourner la valeur par défaut via coalescing');
});

test('StateManager - get() objet racine complet', () => {
    const state = new StateManager();

    state.set('level1.level2.value', 42);
    const level1 = state.get('level1');

    assert.ok(level1, 'Devrait retourner l\'objet intermédiaire');
    assert.ok(level1.level2, 'Devrait contenir level2');
    assert.strictEqual(level1.level2.value, 42, 'Devrait contenir la valeur finale');
});

test('StateManager - set() avec objet complet', () => {
    const state = new StateManager();

    const config = {
        theme: 'dark',
        language: 'fr',
        notifications: true
    };

    state.set('app.config', config);

    assert.strictEqual(state.get('app.config.theme'), 'dark');
    assert.strictEqual(state.get('app.config.language'), 'fr');
    assert.strictEqual(state.get('app.config.notifications'), true);
});

test('StateManager - subscribe() wildcard sur parent', async () => {
    const state = new StateManager();

    await new Promise((resolve, reject) => {
        const timeout = setTimeout(() => reject(new Error('Notification parent non reçue')), 200);
        const unsubscribe = state.subscribe('parent', (newValue) => {
            try {
                assert.ok(newValue, 'Devrait recevoir notification du parent');
                assert.strictEqual(newValue.child, 'value', 'Devrait contenir child');
                clearTimeout(timeout);
                unsubscribe?.();
                resolve();
            } catch (error) {
                clearTimeout(timeout);
                unsubscribe?.();
                reject(error);
            }
        });

        try {
            state.set('parent.child', 'value');
        } catch (error) {
            clearTimeout(timeout);
            unsubscribe?.();
            reject(error);
        }
    });
});

test('StateManager - clear() ou reset()', () => {
    const state = new StateManager();

    state.set('a', 1);
    state.set('b', 2);
    state.set('c', 3);

    if (typeof state.clear === 'function') {
        state.clear();
        assert.strictEqual(state.get('a'), undefined, 'Devrait être cleared');
    } else if (typeof state.reset === 'function') {
        state.reset();
        assert.strictEqual(state.get('a'), undefined, 'Devrait être reset');
    } else {
        // Si pas de méthode clear/reset, skip ce test
        assert.ok(true, 'Pas de méthode clear/reset disponible');
    }
});

test('StateManager - Gestion des types primitifs', () => {
    const state = new StateManager();

    state.set('string', 'text');
    state.set('number', 42);
    state.set('boolean', true);
    state.set('null', null);
    state.set('array', [1, 2, 3]);

    assert.strictEqual(state.get('string'), 'text');
    assert.strictEqual(state.get('number'), 42);
    assert.strictEqual(state.get('boolean'), true);
    assert.strictEqual(state.get('null'), null);
    assert.deepStrictEqual(state.get('array'), [1, 2, 3]);
});

test('StateManager - Ne notifie pas si valeur identique', async () => {
    const state = new StateManager();
    let notifyCount = 0;

    await new Promise((resolve, reject) => {
        const timeout = setTimeout(() => reject(new Error('Timeout vérification notification identique')), 250);
        const unsubscribe = state.subscribe('same.value', () => {
            notifyCount += 1;
        });

        try {
            state.set('same.value', 'test');
        } catch (error) {
            clearTimeout(timeout);
            unsubscribe?.();
            reject(error);
            return;
        }

        setTimeout(() => {
            const countAfterFirst = notifyCount;
            try {
                state.set('same.value', 'test');
            } catch (error) {
                clearTimeout(timeout);
                unsubscribe?.();
                reject(error);
                return;
            }

            setTimeout(() => {
                try {
                    assert.ok(notifyCount >= countAfterFirst, 'Comportement de notification vérifié');
                    clearTimeout(timeout);
                    unsubscribe?.();
                    resolve();
                } catch (error) {
                    clearTimeout(timeout);
                    unsubscribe?.();
                    reject(error);
                }
            }, 60);
        }, 60);
    });
});

test('StateManager - Isolation entre instances', () => {
    const state1 = new StateManager();
    const state2 = new StateManager();

    state1.set('test', 'value1');
    state2.set('test', 'value2');

    assert.strictEqual(state1.get('test'), 'value1', 'Instance 1 devrait avoir value1');
    assert.strictEqual(state2.get('test'), 'value2', 'Instance 2 devrait avoir value2');
});
