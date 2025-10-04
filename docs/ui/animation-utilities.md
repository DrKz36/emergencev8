# Animation Utilities

## Contexte
- Les utilitaires globaux d'animation sont centralisés dans `src/frontend/shared/constants.js` via `ANIMATIONS` (classes + durées + courbes) et `TIMEOUTS`.
- Les classes CSS correspondantes (`fade-in`, `fade-out`, `slide-up`, `slide-down`, `scale-in`) sont définies dans `src/frontend/styles/main-styles.css`.
- Les composants historiques (loader, modales, notifications) consomment ces constantes pour rester cohérents côté durée et easing.

## Bonnes pratiques
- Utiliser `ANIMATIONS.CLASSES` plutôt que des chaînes littérales dès qu'une animation est ajoutée dans le code.
- Toujours retirer les classes d'entrée (`fade-in`, `slide-up`, etc.) une fois l'élément terminé si l'élément reste dans le DOM.
- Lors d'une sortie (`fade-out`, `slide-down`), s'assurer que l'élément est retiré ou masqué après le délai `TIMEOUTS.ANIMATION_EXIT`.
- Depuis le correctif du 25/09/2025, `App.showModule()` applique l'attribut `hidden` et `aria-hidden="true"` aux modules inactifs : ne pas surcharger `display`/`visibility` sur `.tab-content`.
- Patch 26/09/2025 : `.tab-content[hidden] { display: none !important; }` sécurise le masquage même si un module ajoute ses propres règles `display`.
- L'utilisation de `fade-out` désactive automatiquement les interactions (`pointer-events: none`) pendant la phase de disparition.

## Tests recommandés
- Vérifier le switch entre Chat ⇄ Conversations ⇄ Documents : seul le module actif doit rester visible dans le DOM (`.tab-content` actif sans attribut `hidden`).
- Contrôler qu'une modale fermée via `modals.close()` n'est plus interactive pendant l'animation de sortie et est retirée une fois le timeout écoulé.
- S'assurer que les notifications n'empilent pas de conteneurs transparents après fermeture (classe `fade-out` décroche bien l'élément).
