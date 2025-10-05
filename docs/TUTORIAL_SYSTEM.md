# Système de Tutoriel ÉMERGENCE V8

## Vue d'ensemble

Le système de tutoriel d'ÉMERGENCE V8 fournit une expérience d'onboarding complète pour les nouveaux utilisateurs et une documentation exhaustive accessible à tout moment.

## Architecture

### Composants

1. **Tutorial Interactif** ([Tutorial.js](../src/frontend/components/tutorial/Tutorial.js))
   - Système de guidage pas à pas avec spotlight
   - 5 étapes couvrant les fonctionnalités principales
   - Interface draggable et responsive
   - Sauvegarde de l'état (ne plus afficher)

2. **Guides Détaillés** ([tutorialGuides.js](../src/frontend/components/tutorial/tutorialGuides.js))
   - 6 guides exhaustifs des fonctionnalités
   - Documentation HTML enrichie
   - Exemples concrets et bonnes pratiques

3. **Module Paramètres Tutoriel** ([settings-tutorial.js](../src/frontend/features/settings/settings-tutorial.js))
   - Intégration dans les paramètres de l'application
   - Lancement du tutoriel interactif
   - Consultation des guides
   - Astuces rapides et raccourcis clavier

## Fonctionnalités

### Tutoriel Interactif

Le tutoriel interactif guide l'utilisateur à travers les fonctionnalités clés :

- **Étape 1 - Bienvenue** : Introduction à ÉMERGENCE
- **Étape 2 - Chat** : Interface de discussion multi-agents
- **Étape 3 - Input** : Zone de saisie intelligente
- **Étape 4 - Navigation** : Barre latérale et modules
- **Étape 5 - Complétion** : Prochaines étapes

#### Caractéristiques

- **Spotlight** : Mise en évidence des éléments avec mask SVG
- **Positioning** : Placement intelligent du tooltip (top/bottom/left/right/center)
- **Draggable** : Le tooltip peut être déplacé par drag & drop
- **Progression** : Dots de progression et navigation prev/next
- **Persistance** : Option "Ne plus afficher" sauvegardée dans localStorage

### Guides Détaillés

Six guides couvrant toutes les fonctionnalités :

1. **💬 Chat Multi-Agents**
   - Présentation des 3 agents (Anima, Neo, Nexus)
   - Mode RAG et mémoire conversationnelle
   - Consultation ponctuelle d'autres agents
   - Raccourcis clavier

2. **📂 Gestion des Conversations**
   - Création, ouverture, archivage
   - Organisation et nommage
   - Contexte et mémoire par conversation

3. **🧠 Base de Connaissances**
   - Extraction automatique de concepts
   - Visualisation du graphe de connaissances
   - Concept recall et enrichissement contextuel
   - Gestion et édition manuelle

4. **📚 Gestion des Documents**
   - Formats supportés et upload
   - Chunking et indexation vectorielle
   - Utilisation avec le RAG
   - Configuration avancée

5. **📊 Dashboard & Métriques**
   - Métriques d'utilisation
   - Coûts et tokens
   - Performance et insights
   - Export et rapports

6. **⚙️ Paramètres et Configuration**
   - Configuration des modèles IA
   - Personnalisation de l'interface
   - Sécurité et confidentialité
   - Intégrations et avancé

### Module Paramètres

Accessible via **Paramètres > Tutoriel** :

- **Section Hero** : Bouton CTA pour lancer le tutoriel interactif
- **Grille de fonctionnalités** : Cards cliquables pour chaque guide
- **Astuces rapides** : 6 tips essentiels
- **Raccourcis clavier** : Liste complète des shortcuts

#### Modal de Guide

Chaque guide s'ouvre dans un modal élégant :

- Header avec icône et titre
- Contenu scrollable avec styles enrichis
- Footer avec bouton "Lancer le tutoriel interactif"
- Fermeture par X, bouton, overlay ou Échap

## Utilisation

### Lancement du Tutoriel

Plusieurs points d'entrée :

1. **Au premier lancement** (automatique si non désactivé)
2. **Depuis la sidebar** : Menu "Tutoriel"
3. **Depuis les Paramètres** : Paramètres > Tutoriel > Bouton "Lancer"
4. **Depuis un guide** : Bouton dans le footer du modal

### Consultation des Guides

1. Aller dans **Paramètres > Tutoriel**
2. Cliquer sur une carte de fonctionnalité
3. Le guide s'ouvre dans un modal
4. Navigation possible vers le tutoriel interactif

### Gestion de la Persistance

Le tutoriel se souvient de la préférence "Ne plus afficher" :

```javascript
localStorage.setItem('emergence_tutorial_completed', 'true');
```

Pour réinitialiser :

```javascript
localStorage.removeItem('emergence_tutorial_completed');
```

## Fichiers

### Frontend Components

- `src/frontend/components/tutorial/Tutorial.js` - Tutoriel interactif
- `src/frontend/components/tutorial/Tutorial.css` - Styles du tutoriel
- `src/frontend/components/tutorial/tutorialGuides.js` - Contenu des guides
- `src/frontend/components/tutorial/TutorialMenu.js` - Menu d'accès

### Settings Module

- `src/frontend/features/settings/settings-tutorial.js` - Module tutoriel
- `src/frontend/features/settings/settings-tutorial.css` - Styles du module
- `src/frontend/features/settings/settings-main.js` - Intégration (lignes 9, 19, 89-96, 121-125, 905-907)

## Personnalisation

### Ajouter une Étape au Tutoriel

Dans `Tutorial.js`, ajouter un objet au tableau `TUTORIAL_STEPS` :

```javascript
{
  id: 'nouvelle-etape',
  title: '✨ Nouvelle Fonctionnalité',
  description: `<p>Description détaillée...</p>`,
  target: '.selecteur-css-element',
  position: 'right' // top, bottom, left, right, center
}
```

### Ajouter un Guide

Dans `tutorialGuides.js`, ajouter un objet au tableau `TUTORIAL_GUIDES` :

```javascript
{
  id: 'nouveau-guide',
  icon: '🎯',
  title: 'Nouvelle Fonctionnalité',
  summary: 'Description courte',
  content: `
    <section class="guide-section">
      <h3>Titre de section</h3>
      <p>Contenu HTML enrichi...</p>
    </section>
  `
}
```

### Styles

Les styles suivent le design system ÉMERGENCE :

- **Couleurs** : rgba(56, 189, 248) (cyan) et rgba(139, 92, 246) (violet)
- **Glassmorphism** : backdrop-filter et transparence
- **Animations** : transitions 0.3s cubic-bezier
- **Responsive** : breakpoint à 768px

## Accessibilité

- **Navigation clavier** : Tab, Enter, Escape
- **ARIA labels** : Boutons avec aria-label
- **Contraste** : Respecte WCAG AA
- **Focus visible** : Outline sur focus
- **Screen readers** : Sémantique HTML correcte

## Performance

- **Lazy loading** : Les guides ne sont chargés que lors de la consultation
- **Optimisation DOM** : Création/destruction dynamique des modals
- **CSS optimisé** : Utilisation de transform pour les animations
- **Images** : Aucune image lourde, utilisation d'émojis

## Maintenance

### Mise à jour du contenu

1. Modifier `tutorialGuides.js` pour les guides
2. Modifier `Tutorial.js` pour les étapes interactives
3. Rebuild : `npm run build`

### Tests

Vérifier :

- ✅ Lancement du tutoriel depuis tous les points d'entrée
- ✅ Navigation prev/next dans le tutoriel
- ✅ Positionnement correct du tooltip
- ✅ Dragging fonctionnel
- ✅ Persistance "Ne plus afficher"
- ✅ Ouverture des modals de guides
- ✅ Fermeture par X, bouton, overlay, Escape
- ✅ Responsive mobile

## Évolutions Futures

- [ ] Tracking analytics des étapes du tutoriel
- [ ] Tutoriels contextuels (aide au survol)
- [ ] Vidéos d'introduction
- [ ] Quiz interactif de validation
- [ ] Personnalisation du parcours selon le profil
- [ ] Traductions multi-langues
- [ ] Mode sombre/clair pour les modals
- [ ] Recherche dans les guides

## Références

- **Design Pattern** : Guided Tour / Product Tour
- **Inspiration** : Intro.js, Shepherd.js, Driver.js
- **Documentation** : Voir [documentation.js](../src/frontend/features/documentation/documentation.js)
