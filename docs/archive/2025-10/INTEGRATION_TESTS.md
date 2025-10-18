# 🧪 TESTS D'INTÉGRATION - Phases 3 & 4

## ✅ Checklist d'Intégration Terminée

### Code Integration
- [x] Modules Analytics et Preferences créés
- [x] Modules ajoutés à `moduleLoaders` dans app.js
- [x] Onglets ajoutés à `baseModules` avec icônes
- [x] Système de notifications importé dans main.js
- [x] Notifications initialisées au boot
- [x] CSS importés dans index.html

### Fichiers Créés pour l'Intégration
- [x] `/src/frontend/features/analytics/analytics.js` (wrapper Dashboard)
- [x] `/src/frontend/features/preferences/preferences.js` (wrapper Settings)
- [x] `/src/frontend/shared/notifications.js` (système global)
- [x] `/src/frontend/shared/notifications.css` (styles)

---

## 🧪 PLAN DE TESTS

### 1. Test Navigation (Console Browser)

#### Test 1.1 : Vérifier les onglets sont visibles
```javascript
// Dans la console du navigateur
const tabs = document.querySelectorAll('.sidebar-nav button');
console.log('Nombre d\'onglets:', tabs.length);
console.log('Onglets:', Array.from(tabs).map(t => t.textContent.trim()));

// Devrait afficher "Analytics" et "Réglages"
```

#### Test 1.2 : Navigation vers Analytics
```javascript
// Cliquer sur Analytics
const analyticsBtn = Array.from(document.querySelectorAll('.sidebar-nav button'))
  .find(btn => btn.textContent.includes('Analytics'));

if (analyticsBtn) {
  analyticsBtn.click();
  console.log('✓ Cliqué sur Analytics');

  // Vérifier après 1 seconde
  setTimeout(() => {
    const container = document.getElementById('app-content');
    console.log('Contenu Analytics chargé:', container.querySelector('.dashboard-container') !== null);
  }, 1000);
}
```

#### Test 1.3 : Navigation vers Réglages
```javascript
// Cliquer sur Réglages
const prefsBtn = Array.from(document.querySelectorAll('.sidebar-nav button'))
  .find(btn => btn.textContent.includes('Réglages'));

if (prefsBtn) {
  prefsBtn.click();
  console.log('✓ Cliqué sur Réglages');

  // Vérifier après 1 seconde
  setTimeout(() => {
    const container = document.getElementById('app-content');
    console.log('Contenu Settings chargé:', container.querySelector('.settings-container') !== null);
  }, 1000);
}
```

### 2. Test Notifications (Console Browser)

#### Test 2.1 : Système initialisé
```javascript
console.log('Notifications disponibles:', typeof notifications !== 'undefined');
console.log('Container créé:', document.querySelector('.notification-container') !== null);
```

#### Test 2.2 : Toast Success
```javascript
notifications.success('Test de notification réussie !');
// Devrait afficher un toast vert en haut à droite
```

#### Test 2.3 : Toast Error
```javascript
notifications.error('Test d\'erreur');
// Devrait afficher un toast rouge
```

#### Test 2.4 : Toast Warning
```javascript
notifications.warning('Attention, test d\'avertissement');
// Devrait afficher un toast orange
```

#### Test 2.5 : Toast Info
```javascript
notifications.info('Information de test');
// Devrait afficher un toast bleu
```

#### Test 2.6 : Multiples notifications
```javascript
for (let i = 1; i <= 3; i++) {
  setTimeout(() => {
    notifications.info(`Notification ${i}/3`);
  }, i * 500);
}
// Devrait empiler 3 notifications
```

### 3. Test Dashboard Features

#### Test 3.1 : Onglets Dashboard
```javascript
// Une fois sur Analytics, vérifier les onglets
const dashTabs = document.querySelectorAll('.dashboard-tab');
console.log('Onglets Dashboard:', dashTabs.length);
console.log('Noms:', Array.from(dashTabs).map(t => t.textContent.trim()));
// Devrait afficher : Vue d'ensemble, Métriques, Graphiques, Insights
```

#### Test 3.2 : Switch entre onglets
```javascript
const metricsTab = Array.from(document.querySelectorAll('.dashboard-tab'))
  .find(t => t.textContent.includes('Métriques'));

if (metricsTab) {
  metricsTab.click();
  setTimeout(() => {
    console.log('Tab Métriques active:',
      document.querySelector('.dashboard-view[data-view="metrics"].active') !== null);
  }, 500);
}
```

#### Test 3.3 : Bouton Refresh
```javascript
const refreshBtn = document.querySelector('.btn-refresh-all');
if (refreshBtn) {
  refreshBtn.click();
  console.log('✓ Refresh déclenché');
}
```

#### Test 3.4 : Export Rapport
```javascript
const exportBtn = document.querySelector('.btn-export-report');
if (exportBtn) {
  exportBtn.click();
  console.log('✓ Export déclenché (vérifier le téléchargement)');
}
```

### 4. Test Settings Features

#### Test 4.1 : Navigation Settings
```javascript
// Naviguer vers Réglages puis vérifier les sections
const sections = document.querySelectorAll('.settings-nav-item');
console.log('Sections Settings:', sections.length);
console.log('Noms:', Array.from(sections).map(s => s.textContent.trim()));
// Devrait afficher : Modèles IA, Interface, Sécurité, À propos
```

#### Test 4.2 : Section Modèles IA
```javascript
const modelsBtn = Array.from(document.querySelectorAll('.settings-nav-item'))
  .find(btn => btn.textContent.includes('Modèles'));

if (modelsBtn) {
  modelsBtn.click();
  setTimeout(() => {
    const agentCards = document.querySelectorAll('.agent-config');
    console.log('Cartes agents:', agentCards.length);
    console.log('Agents configurables:',
      Array.from(agentCards).map(c => c.querySelector('h3')?.textContent));
  }, 500);
}
```

#### Test 4.3 : Section Interface
```javascript
const uiBtn = Array.from(document.querySelectorAll('.settings-nav-item'))
  .find(btn => btn.textContent.includes('Interface'));

if (uiBtn) {
  uiBtn.click();
  setTimeout(() => {
    const themeOptions = document.querySelectorAll('.theme-option');
    console.log('Options de thème:', themeOptions.length);
  }, 500);
}
```

#### Test 4.4 : Section Sécurité
```javascript
const secBtn = Array.from(document.querySelectorAll('.settings-nav-item'))
  .find(btn => btn.textContent.includes('Sécurité'));

if (secBtn) {
  secBtn.click();
  setTimeout(() => {
    const apiKeys = document.querySelectorAll('.api-key-item');
    console.log('Providers API:', apiKeys.length);
  }, 500);
}
```

### 5. Test Responsive

#### Test 5.1 : Mobile (< 768px)
```javascript
// Redimensionner la fenêtre
window.resizeTo(375, 667);
// Ou utiliser DevTools responsive mode

// Vérifier que les onglets Dashboard sont en mode icône seulement
const tabLabels = document.querySelectorAll('.dashboard-tab .tab-label');
console.log('Labels visibles:', Array.from(tabLabels).some(l =>
  getComputedStyle(l).display !== 'none'));
// Devrait être false sur mobile
```

#### Test 5.2 : Tablet (768px - 1024px)
```javascript
window.resizeTo(768, 1024);
// Vérifier que tout s'affiche correctement
```

### 6. Test Dark Mode

#### Test 6.1 : Activer Dark Mode
```javascript
// Si settings UI est disponible
const darkModeBtn = Array.from(document.querySelectorAll('.theme-option'))
  .find(btn => btn.textContent.includes('Sombre'));

if (darkModeBtn) {
  darkModeBtn.click();
  console.log('✓ Dark mode activé');

  // Vérifier l'attribut
  setTimeout(() => {
    console.log('Theme:', document.documentElement.getAttribute('data-theme'));
  }, 300);
}
```

---

## 🚀 DÉMARRAGE DES TESTS

### Option 1 : Dev Server (Recommandé)
```bash
npm run dev
```
Puis ouvrir http://localhost:5173

### Option 2 : Avec Backend
```bash
npm run start:win  # Windows
# ou
npm run start      # Linux/Mac
```

### Option 3 : Build Production
```bash
npm run build
npm run preview
```

---

## 📋 CHECKLIST DE VALIDATION

### ✅ Tests Fonctionnels
- [ ] Navigation vers Analytics fonctionne
- [ ] Navigation vers Réglages fonctionne
- [ ] Système de notifications s'affiche
- [ ] Tous les types de notifications fonctionnent
- [ ] Onglets Dashboard switchent correctement
- [ ] Sections Settings switchent correctement
- [ ] Bouton Refresh fonctionne
- [ ] Bouton Export fonctionne
- [ ] Bouton Save All fonctionne

### ✅ Tests Visuels
- [ ] Styles CSS chargés correctement
- [ ] Icônes SVG s'affichent
- [ ] Animations fonctionnent
- [ ] Hover states corrects
- [ ] Responsive sur mobile
- [ ] Responsive sur tablet
- [ ] Dark mode fonctionne

### ✅ Tests Console
- [ ] Aucune erreur JavaScript
- [ ] Modules se chargent sans erreur
- [ ] Notifications s'initialisent
- [ ] Analytics s'initialise
- [ ] Preferences s'initialise

---

## 🐛 TROUBLESHOOTING

### Problème : Onglets Analytics/Réglages invisibles
**Solution:**
1. Vérifier le rôle utilisateur (doit être admin/member/tester)
2. Check console: `window.emergenceApp?.app?.state?.get('auth.role')`

### Problème : Notifications ne s'affichent pas
**Solution:**
1. Vérifier import: `console.log(notifications)`
2. Vérifier container: `document.querySelector('.notification-container')`
3. Réinitialiser: `notifications.init()`

### Problème : Dashboard ne charge pas
**Solution:**
1. Vérifier import module: `console.log(window.emergenceApp?.app?.modules?.analytics)`
2. Check erreurs console
3. Vérifier containers existent

### Problème : CSS manquants
**Solution:**
1. Vérifier index.html a tous les imports
2. Hard refresh: Ctrl+Shift+R
3. Vider cache navigateur

---

## 📊 MÉTRIQUES DE SUCCÈS

### Performance
- [ ] Chargement Analytics < 500ms
- [ ] Chargement Settings < 500ms
- [ ] Switch onglets < 100ms
- [ ] Notification apparaît < 50ms

### UX
- [ ] Navigation intuitive
- [ ] Feedback visuel clair
- [ ] Responsive fluide
- [ ] Aucun lag visible

### Code Quality
- [ ] Aucune erreur console
- [ ] Aucun warning important
- [ ] Modules isolés
- [ ] Cleanup propre

---

## 🎉 VALIDATION FINALE

Une fois tous les tests passés :

```javascript
// Test final global
const finalTest = {
  navigation: typeof analytics !== 'undefined' && typeof preferences !== 'undefined',
  notifications: typeof notifications !== 'undefined' && notifications.container !== null,
  css: getComputedStyle(document.body).getPropertyValue('--accent-color') !== '',
  modules: document.querySelectorAll('.sidebar-nav button').length >= 8
};

console.log('✅ Tests Finaux:', finalTest);
console.log('🎉 Intégration Phases 3 & 4:',
  Object.values(finalTest).every(v => v) ? 'RÉUSSIE !' : 'À corriger');
```

**Si tout est ✅ : Les Phases 3 & 4 sont pleinement intégrées et fonctionnelles !** 🚀
