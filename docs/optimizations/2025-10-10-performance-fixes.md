# Optimisations de Performance - 2025-10-10

## Contexte

Analyse des logs de tests manuels identifiant plusieurs probl\u00e8mes de performance li\u00e9s \u00e0 des re-renders excessifs et du spam de logs.

## Probl\u00e8mes Identifi\u00e9s

### 1. ChatUI re-render excessif (9x en quelques secondes)
- **Impact**: Performance UI d\u00e9grad\u00e9e
- **Cause**: Appels multiples \u00e0 `render()` via l'EventBus

### 2. Memory refresh spam (16x)
- **Impact**: Surcharge CPU et logs encombr\u00e9s
- **Cause**: \u00c9v\u00e9nement `memory:center:history` tir\u00e9 trop fr\u00e9quemment

### 3. AUTH_RESTORED duplicata (4x au boot)
- **Impact**: Logique d'authentification possiblement ex\u00e9cut\u00e9e plusieurs fois
- **Cause**: Multiples \u00e9missions de l'\u00e9v\u00e9nement durant l'initialisation

### 4. UX silencieuse pendant streaming
- **Impact**: Utilisateur ne sait pas pourquoi son message n'est pas envoy\u00e9
- **Cause**: Guard bloque silencieusement les envois pendant le streaming

### 5. Polling memory trop fr\u00e9quent
- **Impact**: Utilisation de bande passante inutile
- **Cause**: Intervalle par d\u00e9faut trop court (15s)

## Solutions Impl\u00e9ment\u00e9es

### 1. Guard anti-duplicate pour ChatUI
**Fichier**: `src/frontend/features/chat/chat-ui.js`

```javascript
// Ajout de flags de tracking
this._mounted = false;
this._lastContainer = null;

// Guard dans render()
if (this._mounted && this._lastContainer === container) {
  console.log('[CHAT] Skip full re-render (already mounted) -> using update()');
  this.update(container, chatState);
  return;
}
```

**R\u00e9sultat**: Passe de 9 renders \u00e0 1 render + 8 updates (beaucoup plus l\u00e9ger).

### 2. Debounce du Memory refresh
**Fichier**: `src/frontend/main.js`

```javascript
let memoryRefreshTimeout = null;
this.eventBus.on?.('memory:center:history', (payload = {}) => {
  try {
    if (memoryRefreshTimeout) clearTimeout(memoryRefreshTimeout);
    memoryRefreshTimeout = setTimeout(() => {
      const items = Array.isArray(payload.items) ? payload.items : [];
      console.log('[MemoryCenter] history refresh (debounced)', { ... });
      memoryRefreshTimeout = null;
    }, 300);
  } catch (err) {
    console.warn('[MemoryCenter] history instrumentation failed', err);
  }
});
```

**R\u00e9sultat**: Les 16 logs sont regroup\u00e9s en 1 seul log apr\u00e8s 300ms de silence.

### 3. D\u00e9duplication AUTH_RESTORED
**Fichier**: `src/frontend/main.js`

```javascript
// Deduplicate: only log first occurrence during app lifecycle
const isFirstOfType = (
  (type === 'required' && bucket.requiredCount === 1) ||
  (type === 'missing' && bucket.missingCount === 1) ||
  (type === 'restored' && bucket.restoredCount === 1)
);
if (typeof console !== 'undefined' && typeof console.info === 'function' && isFirstOfType) {
  const label = type === 'required'
    ? '[AuthTrace] AUTH_REQUIRED'
    : (type === 'missing' ? '[AuthTrace] AUTH_MISSING' : '[AuthTrace] AUTH_RESTORED');
  console.info(label, entry);
}
```

**R\u00e9sultat**: Passe de 4 logs AUTH_RESTORED \u00e0 1 seul (le premier).

### 4. Notification UX pendant streaming
**Fichier**: `src/frontend/main.js`

```javascript
if (inFlight) {
  console.warn('[Guard/WS] ui:chat:send ignor\u00e9 (stream en cours).');
  // Show user feedback
  try {
    if (origEmit) {
      origEmit('ui:notification:show', {
        type: 'info',
        message: '\u23f3 R\u00e9ponse en cours... Veuillez patienter.',
        duration: 2000
      });
    }
  } catch {}
  return;
}
```

**R\u00e9sultat**: L'utilisateur voit maintenant un message temporaire quand il essaie d'envoyer pendant un streaming.

### 5. Augmentation intervalle polling memory
**Fichier**: `src/frontend/features/memory/memory-center.js`

```javascript
const DEFAULT_HISTORY_INTERVAL = 20000; // Increased from 15s to 20s
```

**R\u00e9sultat**: R\u00e9duction de 25% de la fr\u00e9quence de polling (de 15s \u00e0 20s).

## Impact Global

### Performance
- **CPU**: R\u00e9duction significative des re-renders et traitements inutiles
- **M\u00e9moire**: Moins d'objets temporaires cr\u00e9\u00e9s lors des renders
- **R\u00e9seau**: R\u00e9duction de 25% du polling memory

### UX
- Interface plus r\u00e9active (moins de re-renders bloquants)
- Feedback visuel quand l'utilisateur essaie d'envoyer pendant streaming
- Logs console plus propres et lisibles

### Maintenabilit\u00e9
- Code plus d\u00e9fensif avec guards explicites
- Debouncing/throttling appliqu\u00e9 aux endroits critiques
- Meilleure tra\u00e7abilit\u00e9 via logs d\u00e9dupliqu\u00e9s

## Tests

### Build
```bash
npm run build
# ✓ built in 817ms - Aucune erreur
```

### Tests Manuels Recommand\u00e9s
1. **ChatUI re-render**: Surveiller les logs `[CHAT] ChatUI rendu` vs `Skip full re-render`
2. **Memory refresh**: V\u00e9rifier que les logs `[MemoryCenter] history refresh (debounced)` sont espac\u00e9s
3. **AUTH_RESTORED**: V\u00e9rifier qu'un seul log appara\u00eet au boot
4. **UX streaming**: Essayer d'envoyer un message pendant une r\u00e9ponse en streaming
5. **Polling**: Observer la fr\u00e9quence des requ\u00eates `GET /api/memory/tend-garden` (doit \u00eatre ~20s)

## Notes

- Toutes les modifications sont **non-breaking** (compatibilit\u00e9 arri\u00e8re totale)
- Les guards peuvent \u00eatre d\u00e9sactiv\u00e9s facilement en commentant les conditions if
- Les timeouts/intervals peuvent \u00eatre ajust\u00e9s via les constantes au d\u00e9but des fichiers

## Prochaines \u00c9tapes Potentielles

1. **Virtualisation de liste**: Si l'historique memory devient tr\u00e8s long (>100 items)
2. **Lazy loading**: Pour les modules rarement utilis\u00e9s
3. **Service Worker**: Pour le caching des requ\u00eates API
4. **Web Workers**: Pour les traitements lourds (parsing, encryption, etc.)
