# Gestion Avancée des Concepts - Documentation Technique

**Version** : 1.0.0
**Date** : 2025-10-16
**Phase** : P1.3 - UX Essentielle
**Statut** : ✅ Complété

---

## 📋 Vue d'Ensemble

La fonctionnalité de **Gestion Avancée des Concepts** permet aux utilisateurs de manipuler leurs concepts mémorisés de manière sophistiquée. Elle offre des opérations en masse, la fusion de concepts similaires, la division de concepts trop larges, et une gestion avancée des tags.

### Objectifs
- ✂️ **Division** : Diviser un concept générique en plusieurs concepts spécifiques
- 🔗 **Fusion** : Fusionner plusieurs concepts similaires en un seul concept
- 🏷️ **Tagging en masse** : Ajouter/remplacer des tags sur plusieurs concepts simultanément
- 🗑️ **Suppression multiple** : Supprimer plusieurs concepts d'un coup
- 📊 **Export/Import** : Sauvegarder et restaurer les concepts

---

## 🏗️ Architecture

### Backend - Endpoints API

Tous les endpoints sont dans `src/backend/features/memory/router.py` (lignes 1089-1900).

#### 1. Liste et Lecture

**`GET /api/memory/concepts`**
- **Description** : Liste paginée des concepts utilisateur
- **Paramètres** :
  - `limit` (int, 1-100) : Nombre de concepts par page (défaut: 20)
  - `offset` (int, ≥0) : Offset pour pagination (défaut: 0)
  - `sort` (str) : Tri - `recent`, `frequent`, `alphabetical` (défaut: `recent`)
- **Réponse** :
```json
{
  "concepts": [
    {
      "id": "concept_user123_abc456",
      "concept_text": "Docker",
      "description": "Conteneurisation d'applications",
      "tags": ["devops", "infrastructure"],
      "relations": [],
      "occurrence_count": 15,
      "first_mentioned": "2025-01-15T10:30:00",
      "last_mentioned": "2025-01-20T14:45:00",
      "thread_ids": ["thread_1", "thread_2"]
    }
  ],
  "total": 47,
  "limit": 20,
  "offset": 0
}
```

**`GET /api/memory/concepts/{concept_id}`**
- **Description** : Détails d'un concept spécifique
- **Auth** : Vérifie ownership (user_id)
- **Réponse** : Objet concept complet

#### 2. Édition

**`PATCH /api/memory/concepts/{concept_id}`**
- **Description** : Mise à jour métadonnées (description, tags, relations)
- **Body** :
```json
{
  "description": "Nouvelle description",
  "tags": ["tag1", "tag2"],
  "relations": [
    {"concept": "Kubernetes", "type": "related"}
  ]
}
```
- **Réponse** :
```json
{
  "status": "success",
  "concept_id": "concept_user123_abc456",
  "updated": true
}
```

#### 3. Suppression

**`DELETE /api/memory/concepts/{concept_id}`**
- **Description** : Suppression d'un concept
- **Auth** : Vérifie ownership
- **Réponse** :
```json
{
  "status": "success",
  "concept_id": "concept_user123_abc456",
  "deleted": true
}
```

#### 4. Fusion de Concepts

**`POST /api/memory/concepts/merge`**
- **Description** : Fusionne N concepts en 1
- **Body** :
```json
{
  "source_ids": ["concept_1", "concept_2", "concept_3"],
  "target_id": "concept_1",
  "new_concept_text": "Conteneurisation" // Optionnel
}
```
- **Logique** :
  - Les `source_ids` sont fusionnés dans `target_id`
  - Tags : union de tous les tags
  - Relations : concaténation sans doublons
  - Thread IDs : union
  - Occurrences : somme
  - Dates : min(first_mentioned), max(last_mentioned)
  - Les concepts sources sont supprimés
- **Réponse** :
```json
{
  "status": "success",
  "target_id": "concept_1",
  "merged_count": 3,
  "merged_ids": ["concept_1", "concept_2", "concept_3"],
  "new_concept_text": "Conteneurisation",
  "total_occurrences": 42
}
```

#### 5. Division de Concept

**`POST /api/memory/concepts/split`**
- **Description** : Divise 1 concept en N concepts
- **Body** :
```json
{
  "source_id": "concept_1",
  "new_concepts": [
    {
      "concept_text": "Docker",
      "description": "Conteneurisation avec Docker",
      "tags": ["docker", "containers"],
      "weight": 0.6
    },
    {
      "concept_text": "Kubernetes",
      "description": "Orchestration de containers",
      "tags": ["kubernetes", "orchestration"],
      "weight": 0.4
    }
  ]
}
```
- **Validation** :
  - Au moins 2 `new_concepts` requis
  - Sum(weights) doit égaler 1.0 (tolérance ±0.01)
  - Tous les `concept_text` doivent être non vides
- **Logique** :
  - Distribution des occurrences selon les poids
  - Réutilisation de l'embedding source (si disponible)
  - Preservation des thread_ids, timestamps
  - Le concept source est supprimé
- **Réponse** :
```json
{
  "status": "success",
  "source_id": "concept_1",
  "new_ids": ["concept_new1", "concept_new2"],
  "split_count": 2
}
```

#### 6. Opérations en Masse

**`POST /api/memory/concepts/bulk-delete`**
- **Body** : `{"concept_ids": ["id1", "id2", "id3"]}`
- **Réponse** :
```json
{
  "status": "success",
  "deleted_count": 3,
  "deleted_ids": ["id1", "id2", "id3"]
}
```

**`POST /api/memory/concepts/bulk-tag`**
- **Body** :
```json
{
  "concept_ids": ["id1", "id2"],
  "tags": ["important", "review"],
  "mode": "add" // ou "replace"
}
```
- **Modes** :
  - `add` : Ajoute les tags aux tags existants
  - `replace` : Remplace tous les tags existants
- **Réponse** :
```json
{
  "status": "success",
  "updated_count": 2,
  "updated_ids": ["id1", "id2"],
  "tags": ["important", "review"],
  "mode": "add"
}
```

#### 7. Export/Import

**`GET /api/memory/concepts/export`**
- **Réponse** : JSON complet avec tous les concepts utilisateur + métadonnées

**`POST /api/memory/concepts/import`**
- **Body** :
```json
{
  "concepts": [...],
  "mode": "merge" // ou "replace"
}
```
- **Modes** :
  - `merge` : Ajoute aux concepts existants
  - `replace` : Supprime tous les concepts existants avant import

---

## 🎨 Frontend - Composants UI

### 1. ConceptList (amélioré)

**Fichier** : `src/frontend/features/memory/concept-list.js`

#### Nouveautés

**Mode Sélection**
```javascript
this.selectionMode = false;  // Mode sélection activé/désactivé
this.selectedIds = new Set(); // IDs des concepts sélectionnés
```

**Méthodes principales** :
- `toggleSelectionMode()` : Active/désactive le mode sélection
- `toggleSelect(conceptId)` : Sélectionne/désélectionne un concept
- `updateBulkActionsBar()` : Affiche/cache la barre d'actions bulk
- `bulkTag()` : Prompt pour tags + appel API bulk-tag
- `bulkMerge()` : Émet événement pour ouvrir modal merge
- `bulkDelete()` : Confirmation + appel API bulk-delete
- `cancelSelection()` : Quitte le mode sélection

**UI Template** :
```html
<!-- Toolbar avec bouton sélection -->
<button data-action="toggle-selection">☑️ Sélectionner</button>

<!-- Barre d'actions bulk (masquée par défaut) -->
<div class="concept-list__bulk-actions" data-role="bulk-actions" hidden>
  <span data-role="selection-count">0 sélectionné(s)</span>
  <button data-action="bulk-tag">🏷️ Tags</button>
  <button data-action="bulk-merge">🔗 Fusionner</button>
  <button data-action="bulk-delete">🗑️ Supprimer</button>
  <button data-action="cancel-selection">Annuler</button>
</div>

<!-- Carte concept avec checkbox (en mode sélection) -->
<div class="concept-card concept-card--selectable concept-card--selected">
  <div class="concept-card__checkbox">
    <input type="checkbox" data-action="toggle-select" checked />
  </div>
  <h4 class="concept-card__title">Docker</h4>
  ...
  <!-- Bouton diviser (hors mode sélection) -->
  <button data-action="split">✂️ Diviser</button>
</div>
```

### 2. ConceptMergeModal

**Fichier** : `src/frontend/features/memory/ConceptMergeModal.js`

#### Usage
```javascript
import { ConceptMergeModal } from './ConceptMergeModal.js';

const mergeModal = new ConceptMergeModal(eventBus, stateManager);
mergeModal.open(['concept_1', 'concept_2', 'concept_3']);

// Écoute événements
eventBus.on('concepts:merged', (data) => {
  console.log(`Merged ${data.mergedCount} concepts into ${data.targetId}`);
});
```

#### Fonctionnalités
- Charge automatiquement les détails des concepts via API
- Radio buttons pour sélectionner le concept cible
- Affiche métadonnées : occurrences, threads, tags
- Champ optionnel pour nouveau texte du concept fusionné
- Résumé dynamique : total occurrences, tags uniques, concepts supprimés
- Validation ownership côté backend
- Événement `concepts:merged` émis après succès

#### Interface
```
🔗 Fusionner des Concepts
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Sélectionnez le concept qui recevra les données fusionnées.

┌─────────────────────────┐
│ ⦿ 🎯 Concept cible      │
│ Docker                  │
│ 🔁 15 occurrences       │
│ 💬 3 conversations      │
│ 🏷️ devops, containers  │
└─────────────────────────┘

┌─────────────────────────┐
│ ○ 📌 Concept 2          │
│ Conteneurisation        │
│ 🔁 8 occurrences        │
│ 💬 2 conversations      │
└─────────────────────────┘

Texte du concept fusionné (optionnel)
[_____________________]

Résumé de la fusion :
• 📊 23 occurrences totales
• 🏷️ 4 tags uniques
• 📝 2 concept(s) seront supprimés

        [Annuler]  [Fusionner]
```

### 3. ConceptSplitModal

**Fichier** : `src/frontend/features/memory/ConceptSplitModal.js`

#### Usage
```javascript
import { ConceptSplitModal } from './ConceptSplitModal.js';

const splitModal = new ConceptSplitModal(eventBus, stateManager);
splitModal.open('concept_1');

// Écoute événements
eventBus.on('concepts:split', (data) => {
  console.log(`Split into ${data.splitCount} concepts: ${data.newIds}`);
});
```

#### Fonctionnalités
- Charge le concept source via API
- Interface dynamique pour créer N concepts (min 2)
- Sliders de poids (0-100%) pour distribution des occurrences
- Validation : sum(weights) = 100%, textes non vides
- Boutons "Ajouter un concept" / "Retirer" (min 2 concepts)
- Résumé dynamique avec warning si poids ≠ 100%
- Événement `concepts:split` émis après succès

#### Interface
```
✂️ Diviser un Concept
━━━━━━━━━━━━━━━━━━━━━━━

Concept source :
Conteneurisation
🔁 20 occurrences · 💬 5 conversations

Divisez ce concept en plusieurs concepts distincts.

┌─── Nouveau Concept 1 ──────┐
│ Texte : [Docker________] * │
│ Desc  : [______________]   │
│ Poids : [====●====] 60%    │
│        (~12 occurrences)   │
│ Tags  : [docker, containers]│
└─────────────────────────────┘

┌─── Nouveau Concept 2 ──────┐
│ Texte : [Kubernetes____] * │
│ Desc  : [______________]   │
│ Poids : [===●=====] 40%    │
│        (~8 occurrences)    │
│ Tags  : [k8s, orchestration]│
└─────────────────────────────┘

      [+ Ajouter un concept]

Résumé :
• 📊 Poids total : 100% ✅
• 📝 2 nouveau(x) concept(s) créé(s)
• 🗑️ Le concept source sera supprimé

        [Annuler]  [Diviser]
```

---

## 🎨 Styling CSS

**Fichier** : `src/frontend/features/memory/concept-management.css` (850+ lignes)

### Classes principales

#### Mode Sélection
```css
.concept-card--selectable { /* Carte en mode sélection */ }
.concept-card--selected { /* Carte sélectionnée */ }
.concept-card__checkbox { /* Container checkbox */ }
```

#### Barre Bulk Actions
```css
.concept-list__bulk-actions { /* Barre d'actions */ }
.bulk-actions__count { /* Compteur sélection */ }
.bulk-actions__btn { /* Boutons d'action */ }
.bulk-actions__btn--danger { /* Bouton delete */ }
```

#### Modales
```css
.concept-merge-modal { /* Modal fusion */ }
.concept-split-modal { /* Modal division */ }
.merge-concept-card { /* Carte concept dans modal merge */ }
.split-concept-card { /* Carte concept dans modal split */ }
```

#### Animations
- `fadeIn` : Fade du backdrop (0.2s)
- `slideUp` : Slide modal content (0.3s cubic-bezier)

#### Responsive
- Breakpoint `@media (max-width: 768px)`
- Bulk actions bar en wrap sur mobile
- Modales en fullwidth (95%)

---

## 🔗 Événements EventBus

### Émis par les modales

```javascript
// Après fusion réussie
eventBus.emit('concepts:merged', {
  targetId: 'concept_1',
  mergedCount: 3,
  totalOccurrences: 42
});

// Après division réussie
eventBus.emit('concepts:split', {
  sourceId: 'concept_1',
  newIds: ['concept_new1', 'concept_new2'],
  splitCount: 2
});
```

### Émis par concept-list

```javascript
// Demande d'ouverture modal merge (depuis bulk merge)
eventBus.emit('concepts:bulk-merge:requested', {
  conceptIds: ['id1', 'id2', 'id3']
});

// Demande d'ouverture modal split (depuis bouton diviser)
eventBus.emit('concepts:split:requested', {
  conceptId: 'concept_1'
});
```

### Écoutés par concept-list

```javascript
// Concept édité (déclenche reload)
eventBus.on('concepts:updated', () => this.loadConcepts());

// Concepts fusionnés (déclenche reload)
eventBus.on('concepts:merged', () => this.loadConcepts());

// Concept divisé (déclenche reload)
eventBus.on('concepts:split', () => this.loadConcepts());
```

---

## 🔒 Sécurité

### Validation côté backend

1. **Authentification** : Tous les endpoints requièrent `get_user_id(request)`
2. **Ownership** : Vérification `meta.get("user_id") != user_id` → 403 Forbidden
3. **Validation des poids** : `abs(sum(weights) - 1.0) > 0.01` → 400 Bad Request
4. **Validation des IDs** : Vérification existence concepts avant opérations
5. **Protection contre doublons** : `target_id in source_ids` → 400 Bad Request

### Isolation des données
- Requêtes ChromaDB avec filtre `{"user_id": user_id, "type": "concept"}`
- Impossible de fusionner/diviser les concepts d'un autre utilisateur

---

## 📊 Performance

### Optimisations backend

1. **Pagination** : Limit max 100 concepts par requête
2. **Batch operations** : Une seule requête ChromaDB pour bulk operations
3. **Réutilisation embeddings** : Split réutilise embedding source (évite re-embed)
4. **Validation early** : Checks avant opérations lourdes

### Optimisations frontend

1. **Lazy loading** : Concepts chargés uniquement à l'ouverture modales
2. **Debouncing** : Mise à jour bulk actions bar
3. **Virtual scrolling** : (TODO pour listes >1000 concepts)
4. **Event delegation** : Un seul listener pour tous les checkboxes

---

## 🧪 Tests

### Tests backend (à créer)

```python
# tests/backend/features/memory/test_concept_management.py

async def test_merge_concepts_success():
    # Créer 3 concepts
    # Appeler POST /api/memory/concepts/merge
    # Vérifier target_id existe, sources supprimés
    # Vérifier sum(occurrences), union(tags)

async def test_split_concept_weights_validation():
    # Créer concept avec 20 occurrences
    # Appeler POST /api/memory/concepts/split avec weights != 1.0
    # Vérifier 400 Bad Request

async def test_bulk_delete_ownership():
    # User A crée concept
    # User B tente bulk-delete
    # Vérifier 403 Forbidden
```

### Tests frontend (à créer)

```javascript
// tests/frontend/features/memory/concept-list.test.js

test('selection mode toggles checkboxes', () => {
  const list = new ConceptList(eventBus, state);
  expect(list.selectionMode).toBe(false);

  list.toggleSelectionMode();
  expect(list.selectionMode).toBe(true);
  // Vérifier présence checkboxes dans DOM
});

test('bulk actions bar shows selection count', () => {
  const list = new ConceptList(eventBus, state);
  list.toggleSelectionMode();
  list.toggleSelect('concept_1');
  list.toggleSelect('concept_2');

  // Vérifier "2 sélectionné(s)" dans DOM
});
```

---

## 📚 Références

- [ROADMAP_PROGRESS.md](../../ROADMAP_PROGRESS.md) - P1.3 complété
- [router.py](../../src/backend/features/memory/router.py) - Endpoints backend
- [concept-list.js](../../src/frontend/features/memory/concept-list.js) - Liste concepts
- [ConceptMergeModal.js](../../src/frontend/features/memory/ConceptMergeModal.js) - Modal fusion
- [ConceptSplitModal.js](../../src/frontend/features/memory/ConceptSplitModal.js) - Modal division
- [concept-management.css](../../src/frontend/features/memory/concept-management.css) - Styling

---

## 🚀 Évolutions futures (Phase P2+)

1. **Auto-merge suggestions** : ML pour suggérer concepts à fusionner
2. **Concept clustering** : Visualisation clusters similaires
3. **Historique modifications** : Traçabilité fusion/split
4. **Undo/Redo** : Annuler fusion/split
5. **Export formats** : CSV, Markdown, Mind Map
6. **Import assisté** : Mapping automatique lors de l'import
7. **Bulk edit** : Éditer description/tags en masse
8. **Concept templates** : Templates pour création rapide

---

**Auteur** : Claude Code
**Date de création** : 2025-10-16
**Dernière mise à jour** : 2025-10-16
