# 🎨 Composants UI Modernisés - Emergence V8

Guide d'intégration des composants harmonisés avec effets métalliques et responsive mobile.

---

## 📦 Structure des composants

```
src/frontend/components/
├── ui/
│   ├── Button.jsx              # Boutons métalliques (primaire, secondaire, danger)
│   ├── ChatBubble.jsx          # Bulles de chat harmonisées (user + agents)
│   └── DashboardCard.jsx       # Cartes dashboard responsive
├── layout/
│   ├── MobileNav.jsx           # Bottom nav bar (mobile portrait)
│   └── Sidebar.jsx             # Sidebar responsive (desktop + paysage)
└── README.md                   # Ce fichier
```

---

## 🚀 Installation rapide

### 1. Importer les design tokens

Ajoutez dans votre fichier CSS principal (`main-styles.css` ou équivalent) :

```css
@import '../styles/design-tokens.css';
```

### 2. Importer les styles des composants

Chaque composant expose une constante `*_STYLES` à ajouter à votre CSS :

```javascript
import { BUTTON_STYLES } from './components/ui/Button.jsx';
import { CHAT_BUBBLE_STYLES } from './components/ui/ChatBubble.jsx';
import { DASHBOARD_CARD_STYLES } from './components/ui/DashboardCard.jsx';
import { MOBILE_NAV_STYLES } from './components/layout/MobileNav.jsx';
import { SIDEBAR_STYLES } from './components/layout/Sidebar.jsx';

// Injecter dans une balise <style> ou ajouter à votre CSS
```

**OU** créez un fichier `src/frontend/styles/components-modern.css` :

```css
/* Import des styles des composants modernisés */

/* Boutons */
/* Copiez le contenu de BUTTON_STYLES ici */

/* Chat Bubbles */
/* Copiez le contenu de CHAT_BUBBLE_STYLES ici */

/* Dashboard Cards */
/* Copiez le contenu de DASHBOARD_CARD_STYLES ici */

/* Mobile Nav */
/* Copiez le contenu de MOBILE_NAV_STYLES ici */

/* Sidebar */
/* Copiez le contenu de SIDEBAR_STYLES ici */
```

Puis importez-le dans `main-styles.css` :

```css
@import './components-modern.css';
```

---

## 🎯 Utilisation des composants

### Button (Boutons harmonisés)

```javascript
import { Button } from './components/ui/Button.jsx';

// Méthode 1 : Factory complète
const btn = Button.create({
  variant: 'primary',     // 'primary' | 'secondary' | 'danger'
  text: 'Valider',
  icon: '<svg>...</svg>', // SVG optionnel
  onClick: () => console.log('Clic!'),
  id: 'my-button',
  className: 'extra-class',
  disabled: false,
  shimmer: true           // Effet shimmer au hover
});

document.body.appendChild(btn);

// Méthode 2 : Raccourcis
const primaryBtn = Button.primary('Envoyer', {
  icon: '<svg>...</svg>',
  onClick: handleSend
});

const secondaryBtn = Button.secondary('Annuler');
const dangerBtn = Button.danger('Supprimer');
```

**Variantes disponibles :**
- `primary` → Émeraude métallique
- `secondary` → Acier
- `danger` → Rouge métallique

---

### ChatBubble (Bulles de chat)

```javascript
import { ChatBubble } from './components/ui/ChatBubble.jsx';

// Méthode 1 : Factory complète
const bubble = ChatBubble.create({
  role: 'user',               // 'user' | 'anima' | 'neo' | 'nexus' | 'global' | 'assistant'
  content: '<p>Bonjour !</p>',
  name: 'Jean',               // Optionnel
  timestamp: '14:32',         // Optionnel
  showActions: true,          // Afficher actions (copier, etc.)
  actions: []                 // Actions personnalisées (optionnel)
});

messagesContainer.appendChild(bubble);

// Méthode 2 : Raccourcis
const userMsg = ChatBubble.user('Bonjour !', {
  timestamp: '14:32'
});

const animaMsg = ChatBubble.anima('Salut ! Comment puis-je t\'aider ?');
const neoMsg = ChatBubble.neo('Analyse en cours...');
const nexusMsg = ChatBubble.nexus('Données récupérées.');
```

**Harmonisation User/Agent :**
- **User** → Gradient bleu métallique cohérent avec les agents
- **Agents** → Conservent leurs gradients existants (Anima rose, Neo bleu, Nexus émeraude, etc.)
- Même `border-radius`, `padding`, et `shadow` pour tous

---

### DashboardCard (Cartes de dashboard)

```javascript
import { DashboardCard } from './components/ui/DashboardCard.jsx';

// Méthode 1 : Factory complète
const card = DashboardCard.create({
  title: 'Coût Jour',
  icon: '☀️',
  value: '0.45',
  unit: '$',
  description: 'Consommation quotidienne',
  variant: 'success',         // 'primary' | 'secondary' | 'success' | 'warning' | 'danger'
  progress: 45,               // 0-100 (optionnel)
  threshold: 1.0,             // Seuil pour progress bar (optionnel)
  className: 'custom-class'
});

dashboardGrid.appendChild(card);

// Méthode 2 : Raccourcis spécialisés
const costCard = DashboardCard.cost('Jour', 0.45, 1.0, '☀️');
const metricCard = DashboardCard.metric('Sessions', 142, 'sessions', 'Interactions complètes', '🗂️');
const benchCard = DashboardCard.benchmark('Anima', 85.5, 100, '🔥');
```

**Responsive automatique :**
- Desktop : grille auto-fit (min 280px)
- Tablette : grille auto-fit (min 240px)
- Mobile paysage : 2 colonnes
- Mobile portrait : 1 colonne

---

### MobileNav (Bottom nav mobile portrait)

```javascript
import { MobileNav } from './components/layout/MobileNav.jsx';

const nav = MobileNav.create({
  items: [
    {
      id: 'home',
      label: 'Accueil',
      icon: '<svg>...</svg>'
    },
    {
      id: 'chat',
      label: 'Chat',
      icon: '<svg>...</svg>'
    }
    // ...
  ],
  activeItem: 'home',
  onItemClick: (item) => {
    console.log('Navigation vers:', item.id);
    // Logique de navigation
  }
});

document.body.appendChild(nav);

// Ou utiliser les items par défaut
const navDefault = MobileNav.create({
  activeItem: 'chat',
  onItemClick: handleNavigation
});

// Changer l'item actif dynamiquement
MobileNav.setActiveItem(nav, 'dashboard');
```

**Affichage responsive :**
- Masquée par défaut
- Visible uniquement en **mobile portrait** (≤767px)
- Masquée en **mobile paysage** (on garde la sidebar)

---

### Sidebar (Navigation desktop + paysage)

```javascript
import { Sidebar } from './components/layout/Sidebar.jsx';

const sidebar = Sidebar.create({
  items: [
    {
      id: 'home',
      label: 'Accueil',
      icon: '<svg>...</svg>'
    },
    {
      id: 'chat',
      label: 'Chat',
      icon: '<svg>...</svg>'
    }
    // ...
  ],
  activeItem: 'home',
  onItemClick: (item) => {
    console.log('Navigation vers:', item.id);
  },
  branding: {
    logo: '/assets/emergence-logo.svg',
    title: 'ÉMERGENCE'
  }
});

document.querySelector('.app-container').appendChild(sidebar);

// Changer l'item actif
Sidebar.setActiveItem(sidebar, 'dashboard');
```

**Affichage responsive :**
- **Desktop** (≥768px) : sidebar verticale gauche (320px)
- **Mobile paysage** : sidebar compacte (240px)
- **Mobile portrait** : masquée (on utilise MobileNav)

---

## 📱 Stratégie Responsive

### Mode Portrait Mobile (≤767px)
- **Sidebar** : masquée
- **MobileNav** : affichée (bottom nav bar)
- **Cards** : 1 colonne
- **Header** : logo centré

### Mode Paysage Mobile (≤920px landscape)
- **Sidebar** : affichée (verticale gauche, compacte)
- **MobileNav** : masquée
- **Cards** : 2 colonnes
- **Header** : logo aligné gauche

### Desktop (≥768px)
- **Sidebar** : affichée (verticale gauche, pleine largeur)
- **MobileNav** : masquée
- **Cards** : grille auto-fit responsive

---

## 🎨 Design Tokens disponibles

Les tokens sont définis dans `src/frontend/styles/design-tokens.css` :

### Gradients métalliques
```css
--metal-emerald-gradient   /* Primaire (émeraude) */
--metal-steel-gradient     /* Secondaire (acier) */
--metal-red-gradient       /* Danger (rouge) */
--metal-blue-gradient      /* User bubbles (bleu) */
```

### Shadows & Effects
```css
--metal-emerald-shadow
--metal-steel-shadow
--metal-red-shadow
--metal-blue-shadow
--shimmer-gradient         /* Effet reflet hover */
```

### Boutons
```css
--btn-height               /* 42px (38px mobile) */
--btn-padding
--btn-radius
--btn-font-size
--btn-transition
```

### Chat Bubbles
```css
--bubble-radius            /* 1.125rem */
--bubble-padding
--bubble-max-width
--bubble-shadow
```

### Cards
```css
--card-radius              /* 1rem */
--card-padding
--card-shadow
--card-bg
--card-border
```

### Mobile Nav
```css
--mobile-nav-height        /* 64px (56px très petits écrans) */
--mobile-nav-icon-size
--mobile-nav-gap
```

---

## 🧪 Exemple Dashboard complet

Voir `src/frontend/features/dashboard/dashboard-modern.js` pour un exemple d'intégration complète avec :
- Cartes de coûts avec progress bars
- Cartes de monitoring
- Cartes de benchmarks
- Bouton refresh harmonisé
- Responsive complet (portrait + paysage)

```javascript
import { DashboardModern } from './features/dashboard/dashboard-modern.js';

const dashboard = new DashboardModern(eventBus, state);
dashboard.init();
dashboard.mount(document.querySelector('#dashboard-container'));
```

---

## ✅ Checklist d'intégration

- [ ] Importer `design-tokens.css` dans le CSS principal
- [ ] Importer les styles des composants (via `*_STYLES` ou fichier dédié)
- [ ] Remplacer les anciens boutons par `Button.jsx`
- [ ] Harmoniser les bulles user avec `ChatBubble.user()`
- [ ] Créer la `MobileNav` pour mobile portrait
- [ ] Adapter la `Sidebar` pour desktop + paysage
- [ ] Moderniser le Dashboard avec `DashboardCard.jsx`
- [ ] Tester le responsive (portrait, paysage, desktop)

---

## 🎯 Palette limitée & Cohérence

**3 tailles typographiques standard :**
- `--text-sm` (0.875rem / 14px)
- `--text-base` (1rem / 16px)
- `--text-lg` (1.125rem / 18px)

**Polices :**
- Primaire : `Inter` (via `--font-primary`)
- Secondaire : `Manrope` (via `--font-secondary`)

**Animations :**
- `--transition-fast` (150ms)
- `--transition-normal` (300ms)
- `--transition-slow` (500ms)

---

## 🔧 Personnalisation

Tous les tokens sont modifiables via CSS :

```css
:root {
  /* Surcharger un token */
  --btn-height: 48px;
  --bubble-radius: 1.5rem;
  --metal-emerald-gradient: linear-gradient(to right, #custom1, #custom2);
}
```

---

## 📚 Ressources

- [Design Tokens](../styles/design-tokens.css)
- [Dashboard Moderne](../features/dashboard/dashboard-modern.js)
- [Variables Core](../styles/core/_variables.css)
- [Layout Responsive](../styles/core/_layout.css)

---

**Emergence V8** - UI/UX cohérente, moderne et responsive ✨
