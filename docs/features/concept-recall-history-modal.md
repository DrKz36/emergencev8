# Concept Recall - Modal "Voir l'historique"

**Date** : 2025-10-04
**Version** : 1.0
**Status** : ✅ Implémenté (Option A)

## Vue d'ensemble

Modal détaillé permettant d'explorer l'historique complet des concepts récurrents détectés dans les conversations.

## Fonctionnalités

### 1. Affichage des concepts

Pour chaque concept détecté :
- **Titre du concept** avec badge de similarité (ex: "87% similaire")
- **Métadonnées** :
  - Date de première mention
  - Date de dernière mention
  - Nombre total de mentions
- **Liste des threads** où le concept a été abordé

### 2. Navigation vers threads

Chaque thread affiché inclut :
- **Icône** (💬 pour thread accessible, 🔒 pour thread supprimé/inaccessible)
- **Titre du thread**
- **Métadonnées** : nombre de messages, date de création
- **Bouton "Ouvrir"** pour navigation directe vers le thread

### 3. Interactions

- **Clic sur "Ouvrir"** : Ferme le modal et charge le thread dans le chat
- **Événement custom** : `navigate-to-thread` émis pour intégration avec ChatUI
- **Auto-close** sur navigation réussie

## Architecture

### Fichiers créés

#### Frontend
```
src/frontend/features/chat/
├── concept-recall-banner.js (✅ Mis à jour)
├── concept-recall-history-modal.js (✅ Nouveau)

src/frontend/styles/components/
├── concept-recall.css (existant)
├── concept-recall-history.css (✅ Nouveau)
```

#### Configuration
```
index.html (✅ Import CSS ajouté)
```

### Composant principal

**ConceptRecallHistoryModal** ([concept-recall-history-modal.js](../../src/frontend/features/chat/concept-recall-history-modal.js))

```javascript
import { ConceptRecallHistoryModal } from './concept-recall-history-modal.js';

const modal = new ConceptRecallHistoryModal();
await modal.open(recalls); // recalls from ws:concept_recall
```

## API Backend utilisée

### GET /api/threads/{threadId}

Récupère les détails d'un thread :
- Thread metadata (title, created_at)
- Messages (pour compter)
- Documents associés

**Authentification** : Session cookie requise

**Réponse** :
```json
{
  "thread": {
    "id": "thread_abc",
    "title": "Discussion DevOps",
    "created_at": "2025-10-01T10:00:00+00:00",
    "type": "chat"
  },
  "messages": [...],
  "docs": [...]
}
```

## Flux utilisateur

### Scénario typique

1. **Détection concept** → Banner s'affiche
2. **Clic "Voir l'historique"** → Modal s'ouvre
3. **Exploration** :
   - Voir 1-3 concepts détectés
   - Consulter métadonnées (dates, fréquence)
   - Lire liste des threads associés
4. **Navigation** :
   - Clic "Ouvrir" sur un thread
   - Modal se ferme
   - ChatUI charge le thread sélectionné

### Cas limites gérés

- **Thread supprimé** : Affiché avec icône 🔒 et label "Thread inaccessible"
- **Erreur réseau** : Thread marqué "Erreur de chargement"
- **Aucun thread** : (ne devrait pas arriver, car recall.thread_ids toujours non vide)

## Intégration avec ChatUI

### Événement `navigate-to-thread`

```javascript
window.addEventListener('navigate-to-thread', (event) => {
  const { threadId } = event.detail;
  chatUI.switchThread(threadId);
});
```

### Alternative : API directe

Si `window.chatUI` est disponible :

```javascript
if (window.chatUI && typeof window.chatUI.switchThread === 'function') {
  window.chatUI.switchThread(threadId);
}
```

## Styles

### Variables CSS utilisées

```css
--surface-1: #111827     /* Card background */
--surface-2: #1f2937     /* Nested elements */
--surface-3: #374151     /* Hover states */
--border: #374151        /* Borders */
--accent-blue: #3b82f6   /* Primary accent */
--text-primary: #e5e7eb  /* Main text */
--text-secondary: #9ca3af /* Muted text */
```

### Responsive design

- **Desktop** : Layout 2 colonnes (info + actions)
- **Mobile (<640px)** :
  - Stack vertical
  - Boutons pleine largeur
  - Métadonnées condensées

## Tests manuels

### Checklist

- [ ] Modal s'ouvre au clic "Voir l'historique"
- [ ] Affichage correct de 1-3 concepts
- [ ] Badge similarité affiché (50-100%)
- [ ] Dates formatées en français
- [ ] Threads chargés depuis API
- [ ] Bouton "Ouvrir" fonctionne
- [ ] Navigation vers thread réussit
- [ ] Modal se ferme après navigation
- [ ] Thread inaccessible affiché correctement
- [ ] Responsive (mobile + desktop)

### Test E2E

1. Backend actif : `pwsh -File scripts/run-backend.ps1`
2. Thread "DevOps" → message CI/CD → Jardiner
3. Thread "Automation" → message CI/CD similaire
4. Banner apparaît → "Voir l'historique"
5. Modal affiche concept + threads
6. Clic "Ouvrir" sur thread "DevOps"
7. ChatUI charge thread DevOps

## Métriques

Interactions modal trackées via [concept_recall_metrics.py](../../src/backend/features/memory/concept_recall_metrics.py) :

```python
# Quand modal s'ouvre
concept_recall_metrics.record_interaction(user_id, 'view_history')

# Quand navigation vers thread
# (à implémenter côté frontend via API call)
```

## Prochaines étapes (optionnel)

### Améliorations futures

1. **Extraits de messages** : Afficher contexte où concept a été mentionné
2. **Filtrage** : Recherche/filtre dans la liste de threads
3. **Export** : Télécharger historique concept en JSON/Markdown
4. **Timeline** : Graphique temporel des mentions
5. **Suggestions** : "Concepts similaires" à explorer

## Références

- [Modal component](../../src/frontend/components/modals.js) - Infrastructure modal
- [ConceptRecallBanner](../../src/frontend/features/chat/concept-recall-banner.js) - Banner intégré
- [Threads API](../../src/backend/features/threads/router.py) - Endpoint GET /api/threads/{id}

## Support

**Questions** : Voir [concept-recall-manual-qa.md](../qa/concept-recall-manual-qa.md)
**Tests** : [test_concept_recall_tracker.py](../../tests/backend/features/test_concept_recall_tracker.py)
