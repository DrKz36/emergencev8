# ADR-002: Suppression du Module Agents (Profils fusionnés dans References)

**Date**: 2025-10-23
**Statut**: ✅ Accepté et Documenté (Changement déjà effectué)
**Décideurs**: Claude Code (Audit Architecture), Architecte FG
**Tags**: `architecture`, `frontend`, `modules`, `agents`, `references`

---

## Contexte

### État Découvert lors de l'Audit Architecture (2025-10-23)

Le module `features/agents/agents.js` était mentionné dans `docs/architecture/10-Components.md` avec la note :

> **`features/agents/agents.js`** : module retiré (profils agents fusionnés dans `ReferencesModule`).

**Problème** : Le module avait été retiré du code mais :
1. Toujours mentionné dans les docs architecture (confusion pour agents)
2. Aucun ADR documentant cette décision
3. Pas de raison explicite du changement

**Impact** : Agents (Claude Code, Codex GPT) pouvaient chercher ce module inexistant et perdre du temps.

---

## Décision

**Nous documentons rétroactivement la décision de supprimer le module Agents et de fusionner les profils agents dans le module References.**

### Changements Effectués (Avant Audit)

#### Frontend

**Module retiré** :
- `src/frontend/features/agents/agents.js` ❌ SUPPRIMÉ
- `src/frontend/features/agents/agents.css` ❌ SUPPRIMÉ

**Module de remplacement** :
- `src/frontend/features/references/references.js` ✅ ACTIF
  - Contient maintenant : About page + Galerie profils agents (Anima/Neo/Nexus)
  - Viewer markdown pour `/docs/agents-profils.md`

### Raison du Changement

**Avant** :
- 2 modules séparés : `agents/` (profils agents) + `references/` (about page)
- Navigation confuse : 2 onglets pour contenu connexe
- Duplication UI (viewer markdown dans 2 modules)

**Après** :
- 1 seul module `references/` : About page + Profils agents
- Navigation simplifiée : 1 onglet "À Propos"
- UI cohérente : même viewer markdown

**Bénéfices** :
- ✅ Moins de code (1 module au lieu de 2)
- ✅ UX améliorée (navigation simplifiée)
- ✅ Maintenance facilitée (1 seul viewer)

---

## Documentation de l'État Actuel

### Module References (Actif)

**Fichier** : `src/frontend/features/references/references.js`
**Styles** : `src/frontend/features/references/references.css`

**Responsabilité** : Page "À Propos" avec informations projet + galerie profils agents.

**Fonctionnalités** :
- Viewer markdown pour documentation projet
- Galerie horizontale profils agents (Anima, Neo, Nexus)
- Ancrages vers `/docs/agents-profils.md`
- Navigation sections

**État** : ✅ Module actif, accessible via menu navigation.

---

## Conséquences

### Positives

- ✅ **Docs architecture mises à jour** : Module fantôme supprimé de `10-Components.md`
- ✅ **ADR créé** : Décision documentée pour historique
- ✅ **Clarté** : Agents savent maintenant que module n'existe plus
- ✅ **Code plus simple** : 1 module au lieu de 2

### Négatives

- ⚠️ **Documentation rétroactive** : ADR créé après changement (pas idéal, mais nécessaire pour audit)
- ⚠️ **Historique incomplet** : Date exacte de suppression inconnue (estimée mi-2025)

---

## Alternatives Considérées

### Alternative 1 : Garder 2 Modules Séparés

**Argument** : Séparation des responsabilités (about ≠ profils agents)

**Rejet** : Over-engineering pour contenu connexe. Navigation fragmentée.

### Alternative 2 : Créer un Module "Documentation" Générique

**Argument** : Regrouper tous les viewers markdown

**Rejet** : Scope trop large, confusion avec module `documentation/` existant.

---

## Liens et Références

- **Audit Architecture** : Session 2025-10-23 (audit complet docs architecture)
- **Components Docs** : [10-Components.md](../10-Components.md) (section "Modules Frontend Additionnels")
- **ADR Template** : [ADR-001-sessions-threads-renaming.md](ADR-001-sessions-threads-renaming.md)

**Commits** :
- Suppression originale : Date inconnue (avant audit 2025-10-23)
- Documentation ADR : Session 2025-10-23

---

## Historique

| Date       | Statut          | Auteur              |
|------------|-----------------|---------------------|
| ~2025-08   | Implémenté      | Développeur inconnu |
| 2025-10-23 | Documenté (ADR) | Claude Code (Audit) |
| 2025-10-23 | Accepté         | Architecte FG       |

---

**Leçon Apprise** : **Toujours créer un ADR lors de suppression/fusion de modules**, même pour changements "mineurs". Les futurs développeurs (et agents) ont besoin de comprendre les décisions architecturales.

---

**Note pour Agents** : Si tu cherches les profils agents, ils sont maintenant dans `features/references/references.js`, pas dans `features/agents/`. Consulter `docs/architecture/AGENTS_CHECKLIST.md` pour éviter ce genre de confusion à l'avenir.
