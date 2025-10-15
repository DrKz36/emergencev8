# Système de Navigation Tutoriel/Glossaire

## Vue d'ensemble

Ce document décrit le système de navigation intelligent pour le tutoriel et le glossaire d'ÉMERGENCE, permettant aux utilisateurs de naviguer facilement entre les termes techniques et leurs définitions tout en gardant leur position de lecture.

## Problématique

Lorsqu'un utilisateur lit le tutoriel et rencontre un terme technique, il peut cliquer sur un lien hypertexte pour consulter la définition dans le glossaire. Le défi était de permettre à l'utilisateur de **revenir exactement à l'endroit où il lisait** après avoir consulté la définition.

## Solution Implémentée

### Architecture

Le système repose sur trois composants principaux :

1. **GlossaryNavigator** (`src/frontend/utils/glossary-navigation.js`)
   - Gère l'historique de navigation
   - Détecte le conteneur de scroll actif
   - Sauvegarde les positions des éléments cliqués
   - Gère le bouton "Retour" flottant

2. **Documentation Module** (`src/frontend/features/documentation/documentation.js`)
   - Interface avec le système de navigation
   - Charge les documents markdown (tutoriel et glossaire)
   - Nettoie l'historique lors du changement de document

3. **Navigation UI** (barre de navigation en haut)
   - Bouton "Tutoriel" → charge `/docs/EMERGENCE_TUTORIEL_VULGARISE_V2.md`
   - Bouton "Glossaire" → charge `/docs/glossaire.md`
   - Bouton "Statistiques" → affiche les stats du projet

### Fonctionnement Détaillé

#### 1. Détection du Conteneur de Scroll

Le système détecte automatiquement le conteneur HTML qui gère le scroll :

```javascript
getScrollContainer() {
    // Teste plusieurs conteneurs dans l'ordre de priorité :
    // 1. .documentation-modal-body
    // 2. #tab-content-documentation
    // 3. .tab-content.active
    // 4. .app-content
    // 5. window (par défaut)
}
```

#### 2. Sauvegarde de la Position d'un Élément

Quand l'utilisateur clique sur un lien vers une définition :

```javascript
saveScrollPositionForElement(element, targetHash) {
    // 1. Calcule la position absolue de l'élément lien
    const elementRect = element.getBoundingClientRect();
    const elementPosition = container.scrollTop + (elementRect.top - containerRect.top);

    // 2. Crée un ID unique pour retrouver l'élément
    const elementId = `elem_${Date.now()}`;
    element.setAttribute('data-nav-id', elementId);

    // 3. Sauvegarde dans l'historique
    this.scrollHistory.push({
        position: elementPosition,
        elementId: elementId,
        targetHash: targetHash,
        timestamp: Date.now()
    });
}
```

**Pourquoi cette approche ?**
- Simple position de scroll ne suffit pas car le lien déclenche un scroll automatique vers la définition
- Il faut sauvegarder l'élément cliqué lui-même pour y revenir exactement

#### 3. Retour à la Position Exacte

Quand l'utilisateur clique sur "Retour" :

```javascript
goBack() {
    const previousEntry = this.scrollHistory[this.scrollHistory.length - 1];

    // Priorité 1 : Retrouver l'élément par son ID
    if (previousEntry.elementId) {
        const element = document.querySelector(`[data-nav-id="${previousEntry.elementId}"]`);
        if (element) {
            element.scrollIntoView({ behavior: 'smooth', block: 'center' });
            return;
        }
    }

    // Priorité 2 : Utiliser la position sauvegardée
    container.scrollTo({ top: previousEntry.position, behavior: 'smooth' });
}
```

### Interface Utilisateur

#### Bouton "Retour" Flottant

- **Position** : Bas à droite de l'écran
- **Apparence** : Bouton circulaire avec icône flèche + texte "Retour"
- **Comportement** :
  - Apparaît quand l'utilisateur clique sur un lien
  - Disparaît après retour si l'historique est vide
  - Animation smooth d'apparition/disparition

#### Barre de Navigation Principale

La navigation en haut de la page "À propos" a été simplifiée :

**AVANT** :
```
Bienvenue dans ÉMERGENCE...
[Tutoriel] [Statistiques] [Qu'est-ce que l'IA ?]
```

**APRÈS** :
```
Navigation en haut :
[Tutoriel] [Glossaire] [Statistiques] [Architecture] [Dépendances] [Technologies] [Observabilité] [Genèse] [Hymne]
```

### Gestion de l'Historique

- **Capacité** : Jusqu'à 20 entrées dans l'historique
- **Persistance** : En mémoire de session uniquement (pas de localStorage pour les IDs d'éléments)
- **Nettoyage** : Automatique lors du chargement d'un nouveau document

## Modifications Apportées

### Fichiers Modifiés

1. **`src/frontend/features/documentation/documentation.js`**
   - Suppression du panneau avec 3 boutons (ligne 165-197)
   - Ajout des boutons "Tutoriel" et "Glossaire" dans la navigation principale
   - Nettoyage de l'historique lors du chargement d'un nouveau document
   - Réattachement des listeners après chargement du contenu

2. **`src/frontend/utils/glossary-navigation.js`**
   - Nouvelle méthode `getScrollContainer()` pour détecter le bon conteneur
   - Nouvelle méthode `getCurrentScrollPosition()` qui fonctionne avec n'importe quel conteneur
   - Nouvelle méthode `saveScrollPositionForElement()` pour sauvegarder la position d'un élément
   - Amélioration de `goBack()` pour utiliser l'ID de l'élément en priorité
   - Ajout de logs de débogage complets
   - Exposition globale via `window.glossaryNavigator`

### Fichiers CSS (inchangés mais pertinents)

- **`src/frontend/features/documentation/documentation.css`** : Styles de la page
- **`src/frontend/utils/glossary-navigation.js`** : Styles du bouton "Retour" (injectés dynamiquement)

## Cas d'Usage

### Scénario Type

1. **Utilisateur** : Clique sur "À propos" dans le menu
2. **Utilisateur** : Clique sur "Tutoriel" en haut
3. **Système** : Charge `/docs/EMERGENCE_TUTORIEL_VULGARISE_V2.md`
4. **Utilisateur** : Lit le tutoriel et rencontre le terme "[émergence](#emergence)"
5. **Utilisateur** : Clique sur le lien
6. **Système** :
   - Sauvegarde la position exacte du lien cliqué
   - Affiche le bouton "Retour"
   - Scrolle vers la définition de "émergence"
7. **Utilisateur** : Lit la définition
8. **Utilisateur** : Clique sur "Retour"
9. **Système** :
   - Retrouve l'élément par son ID
   - Scrolle vers cet élément (centré à l'écran)
   - Cache le bouton si l'historique est vide

### Cas Limites Gérés

- **Document rechargé** : L'historique est nettoyé automatiquement
- **Élément supprimé** : Fallback sur la position numérique
- **Multiples clics** : Historique empilé (jusqu'à 20 entrées)
- **Conteneur de scroll changeant** : Redétection automatique

## Points Techniques Importants

### Pourquoi Sauvegarder l'Élément et pas seulement scrollTop ?

Quand on clique sur un lien `<a href="#emergence">`, le navigateur :
1. Met à jour `window.location.hash`
2. **Scrolle automatiquement** vers l'élément `id="emergence"`

Si on sauvegardait seulement `scrollTop` **avant** le clic, on sauvegarderait la position **avant** le scroll automatique du navigateur. Mais nous voulons revenir à l'élément cliqué lui-même, pas à une position arbitraire.

### Détection du Conteneur de Scroll

ÉMERGENCE utilise un système de tabs avec des conteneurs différents :
- En modal : `.documentation-modal-body`
- En tab : `#tab-content-documentation`
- Fallback : `window`

Le système teste plusieurs sélecteurs et choisit le premier qui a du scroll actif.

### Performance

- Utilisation de `scrollIntoView({ behavior: 'smooth' })` pour animations fluides
- Debouncing implicite via `setTimeout()`
- Historique limité à 20 entrées max
- Pas de sauvegarde localStorage (évite la pollution)

## Logs de Débogage

Pour déboguer, ouvrez la console (F12) et cherchez :

```
[GlossaryNavigator] Initializing...
[GlossaryNavigator] Found X links to enhance
[GlossaryNavigator] Link clicked: #term
[GlossaryNavigator] Saving element position: XXX
[GlossaryNavigator] Scrolling to element: elem_TIMESTAMP
```

## Améliorations Futures

1. **Historique visuel** : Afficher le chemin de navigation (breadcrumb)
2. **Raccourcis clavier** : Alt+← pour revenir
3. **Persistance intelligente** : Sauvegarder dans sessionStorage avec des identifiants stables
4. **Animation de highlight** : Surligner brièvement l'élément de retour
5. **Support multi-documents** : Naviguer entre tutoriel ET glossaire avec historique commun

## Conclusion

Ce système offre une expérience de navigation fluide et intuitive pour les utilisateurs consultant le tutoriel et le glossaire. La solution est robuste, performante et maintenable.

---

**Date de création** : 15 octobre 2025
**Auteur** : Claude (Anthropic) + Équipe ÉMERGENCE
**Version** : 1.0
