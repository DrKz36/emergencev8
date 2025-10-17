# Guide du Système de Versioning ÉMERGENCE

## Vue d'ensemble

Le système ÉMERGENCE utilise un système de versioning centralisé basé sur un fichier source unique de vérité: **[src/version.js](../src/version.js)**

## Architecture

### Source de Vérité Unique

**Fichier:** `src/version.js`

Ce fichier contient toutes les informations de version du système:
- Version actuelle (format `beta-X.Y.Z`)
- Nom de la version
- Date de build
- Phase de développement
- Pourcentage de complétion
- Statut de chaque phase
- Helpers de formatage

### Synchronisation Automatique

Les composants suivants **importent automatiquement** depuis `src/version.js`:

1. **Frontend - Page d'accueil**
   - Fichier: [src/frontend/core/version-display.js](../src/frontend/core/version-display.js)
   - Affiche: Version, features complétées, pourcentage

2. **Frontend - Module À propos (Paramètres)**
   - Fichier: [src/frontend/features/settings/settings-main.js](../src/frontend/features/settings/settings-main.js)
   - Affiche: Version complète, phase, date de build, progression

3. **Package.json**
   - Doit être synchronisé manuellement avec `src/version.js`

## Format de Versioning

### Versioning Sémantique

Format: `beta-MAJOR.MINOR.PATCH`

- **MAJOR (X)**: Phase complète (P0 = 1, P1 = 2, P2 = 3, P3 = 4)
- **MINOR (Y)**: Nouvelle fonctionnalité complétée dans la phase
- **PATCH (Z)**: Bugfixes et hotfixes

### Exemples

```
beta-1.0.0 → Phase P0 complète (Quick Wins)
beta-2.0.0 → Phase P1 complète (UX Essentielle)
beta-2.1.0 → P1 + 1 feature supplémentaire
beta-2.1.1 → P1 + 1 feature + 1 bugfix
```

### Mapping Phase → Version

| Phase | Description | Version |
|-------|-------------|---------|
| P0 | Quick Wins (3 features) | `beta-1.x.x` |
| P1 | UX Essentielle (3 features) | `beta-2.x.x` |
| P2 | Collaboration (6 features) | `beta-3.x.x` |
| P3 | Intelligence (4 features) | `beta-4.x.x` |
| P4 | Perfectionnement (7 features) | `beta-5.x.x` |
| Production | Release finale | `v1.0.0` |

## Workflow de Mise à Jour

### Étape 1: Modifier src/version.js

```javascript
// Exemple: Passage de beta-2.1.0 à beta-2.1.1
export const VERSION = 'beta-2.1.1';  // ← Incrémenter ici
export const VERSION_NAME = 'Phase P1 + Debug & Audit';
export const VERSION_DATE = '2025-10-17';  // ← Mettre à jour la date
export const COMPLETION_PERCENTAGE = 61;  // ← Ajuster si nécessaire
```

### Étape 2: Synchroniser package.json

```json
{
  "name": "emergence-v8",
  "version": "beta-2.1.1",  // ← Doit correspondre à src/version.js
  ...
}
```

### Étape 3: Mettre à jour CHANGELOG.md

Ajouter une entrée pour la nouvelle version:

```markdown
## [beta-2.1.1] - 2025-10-17

### Added
- Système de versioning centralisé

### Changed
- Module À propos synchronisé avec version.js

### Fixed
- Incohérence entre versions affichées
```

### Étape 4: Mettre à jour ROADMAP_OFFICIELLE.md

Ajuster les métriques et le statut des fonctionnalités si nécessaire.

## Règles d'Incrémentation

### Patch (Z) - `beta-X.Y.Z+1`

**Quand:**
- Correction de bug
- Amélioration mineure
- Mise à jour de documentation
- Refactoring interne sans changement d'interface

**Exemple:** `beta-2.1.0` → `beta-2.1.1`

### Minor (Y) - `beta-X.Y+1.0`

**Quand:**
- Nouvelle fonctionnalité implémentée
- Feature de la roadmap complétée
- Amélioration significative
- Nouvelle API endpoint (non breaking)

**Exemple:** `beta-2.1.1` → `beta-2.2.0`

### Major (X) - `beta-X+1.0.0`

**Quand:**
- Phase complète (toutes les features de la phase)
- Breaking change
- Changement d'architecture majeur
- Migration vers nouvelle version de dépendance majeure

**Exemple:** `beta-2.9.3` → `beta-3.0.0` (Phase P2 complète)

## Rôle des Guardians

### Anima (DocKeeper)

**Responsabilités:**
- Surveiller les changements de code
- Déterminer l'impact sur la version (patch/minor/major)
- Proposer l'incrémentation de version appropriée
- Mettre à jour `src/version.js`
- Synchroniser `package.json`
- Ajouter entrée dans `CHANGELOG.md`
- Mettre à jour `ROADMAP_OFFICIELLE.md`

**Checklist:** Voir [agents/anima_dockeeper.md](../claude-plugins/integrity-docs-guardian/agents/anima_dockeeper.md#version-tracking-checklist)

### Neo (IntegrityWatcher)

**Responsabilités:**
- Vérifier la cohérence version entre `src/version.js` et `package.json`
- Détecter les breaking changes (→ major version bump)
- Signaler les incohérences de version dans l'UI

### Nexus (Coordinator)

**Responsabilités:**
- Consolider les recommandations de version d'Anima et Neo
- Valider la cohérence globale du versioning
- Générer le rapport de version dans le rapport unifié

## Structure de src/version.js

### Exports Principaux

```javascript
export const VERSION = 'beta-2.1.1';
export const VERSION_NAME = 'Phase P1 + Debug & Audit';
export const VERSION_DATE = '2025-10-16';
export const BUILD_PHASE = 'P1';
export const COMPLETION_PERCENTAGE = 61;
export const TOTAL_FEATURES = 23;
```

### Object par Défaut

```javascript
export default {
  version: VERSION,
  versionName: VERSION_NAME,
  versionDate: VERSION_DATE,
  buildPhase: BUILD_PHASE,
  completionPercentage: COMPLETION_PERCENTAGE,
  totalFeatures: TOTAL_FEATURES,

  phases: {
    P0: { status: 'completed', features: 3, completion: 100 },
    P1: { status: 'completed', features: 3, completion: 100 },
    P2: { status: 'pending', features: 6, completion: 0 },
    // ...
  },

  // Getters
  get fullVersion() { return `${VERSION} - ${VERSION_NAME}`; },
  get shortVersion() { return VERSION; },
  get displayVersion() { return VERSION.replace('beta-', 'β'); },
  get completedFeatures() { /* calcul */ },
  get featuresDisplay() { return `${completedFeatures}/${totalFeatures}`; }
}
```

## Utilisation dans le Code

### Import dans un composant frontend

```javascript
import versionInfo from '../../version.js';

// Utilisation
console.log(versionInfo.version);  // "beta-2.1.1"
console.log(versionInfo.fullVersion);  // "beta-2.1.1 - Phase P1 + Debug & Audit"
console.log(versionInfo.completionPercentage);  // 61
console.log(versionInfo.featuresDisplay);  // "14/23"
```

### Affichage dans l'UI

```javascript
// Version simple
<p class="version">{versionInfo.version}</p>

// Version complète avec progression
<p class="version">{versionInfo.fullVersion}</p>
<p class="progress">{versionInfo.featuresDisplay} • {versionInfo.completionPercentage}% complété</p>
```

## Bonnes Pratiques

### ✅ À FAIRE

1. **Toujours modifier `src/version.js` en premier**
2. **Synchroniser immédiatement `package.json`**
3. **Ajouter entrée dans `CHANGELOG.md`** avec date et description
4. **Commit avec message de version** (ex: `chore: bump version to beta-2.1.1`)
5. **Vérifier que l'UI reflète la bonne version** après commit

### ❌ À ÉVITER

1. **Ne JAMAIS modifier directement l'UI** pour changer la version
2. **Ne PAS oublier de synchroniser `package.json`**
3. **Ne PAS skip le CHANGELOG**
4. **Ne PAS utiliser de version hardcodée** ailleurs que dans `src/version.js`
5. **Ne PAS créer de branches de version** (utiliser tags git à la place)

## Historique des Versions

Voir [CHANGELOG.md](../CHANGELOG.md) pour l'historique complet.

### Versions Majeures

- **beta-1.0.0** (Phase P0) - Quick Wins complétés
- **beta-2.0.0** (Phase P1) - UX Essentielle complétée
- **beta-2.1.0** - Debug Phase 1 & 3
- **beta-2.1.1** - Audit multi-agents + versioning unifié [ACTUEL]

## Références

- [src/version.js](../src/version.js) - Source de vérité
- [CHANGELOG.md](../CHANGELOG.md) - Historique des changements
- [ROADMAP_OFFICIELLE.md](../ROADMAP_OFFICIELLE.md) - Progression des features
- [Anima DocKeeper](../claude-plugins/integrity-docs-guardian/agents/anima_dockeeper.md) - Agent de versioning

## Support

Pour toute question sur le versioning:
1. Consulter ce guide
2. Vérifier `src/version.js`
3. Contacter l'équipe de développement
