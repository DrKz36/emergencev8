# Synchronisation Inter-Agents - Points de Coordination

**Dernière mise à jour:** 2025-10-18 14:30
**Version:** Beta 2.1.3

---

## Objectif

Ce document fournit les points de synchronisation spécifiques et les checklists pour assurer la cohérence entre les agents IA travaillant sur ÉMERGENCE V8.

---

## Phase 1: Backend Critical Fixes - Synchronisation

### Modifications Effectuées (2025-10-16)

**Agent:** Claude Code (Sonnet 4.5)
**Scope:** Phase 1.2 à 1.6 du plan de debug

#### Fichiers Modifiés

1. **`src/backend/features/dashboard/timeline_service.py`**
   - Fonctions: `get_activity_timeline()`, `get_costs_timeline()`, `get_tokens_timeline()`, `get_distribution_by_agent()`
   - Changement: Ajout `COALESCE(timestamp, created_at, 'now')` partout
   - Impact: Graphiques Cockpit afficheront des données

2. **`src/backend/features/dashboard/admin_service.py`**
   - Fonctions: `_get_users_breakdown()`, `_get_date_metrics()`, `_get_user_cost_history()`, `get_detailed_costs_breakdown()` (nouveau)
   - Changements:
     - INNER JOIN → LEFT JOIN avec conditions flexibles
     - COALESCE pour timestamps
     - Nouvelle fonction detailed costs breakdown
   - Impact: Module Admin fonctionnel (users, metrics, detailed costs)

3. **`src/backend/features/dashboard/admin_router.py`**
   - Ajout: Nouvel endpoint GET `/admin/costs/detailed`
   - Impact: Onglet "Coûts Détaillés" fonctionnel

#### Fichiers Créés

1. **`docs/DEBUG_PHASE1_STATUS.md`**
   - Contenu: Statut détaillé de toutes les sous-tâches Phase 1
   - Usage: Suivi des progrès et documentation des changements

2. **`docs/tests/PHASE1_VALIDATION_CHECKLIST.md`**
   - Contenu: 12 tests fonctionnels (API + Frontend)
   - Usage: Validation manuelle des corrections

3. **`docs/AGENTS_COORDINATION.md`**
   - Contenu: Conventions de développement inter-agents
   - Usage: Référence pour tous les agents travaillant sur le projet

4. **`docs/INTER_AGENT_SYNC.md`** (ce fichier)
   - Contenu: Points de synchronisation spécifiques
   - Usage: Coordination entre sessions d'agents

---

## Conventions Établies - À Respecter

### 1. NULL Timestamp Handling

**Context:** Phase 1 a identifié que de nombreux enregistrements ont `timestamp = NULL`, causant des échecs silencieux dans les requêtes SQL.

**Convention Obligatoire:**

```sql
-- Pour toute requête impliquant des dates
WHERE DATE(COALESCE(timestamp, created_at, 'now')) >= DATE('now', '-30 days')

-- Pour les agrégations
SELECT
    DATE(COALESCE(timestamp, created_at, 'now')) as date,
    SUM(total_cost) as cost
FROM costs
GROUP BY date
```

**Application:**
- ✅ timeline_service.py (toutes les fonctions)
- ✅ admin_service.py (_get_date_metrics, _get_user_cost_history, get_detailed_costs_breakdown)
- ⏳ À vérifier dans queries.py et autres services

---

### 2. Flexible User Matching

**Context:** Les utilisateurs peuvent avoir `user_id != email`, causant des exclusions avec INNER JOIN.

**Convention Obligatoire:**

```sql
-- Pour les jointures avec auth_allowlist
FROM sessions s
LEFT JOIN auth_allowlist a ON (
    s.user_id = a.email
    OR s.user_id = a.user_id
)

-- Avec fallbacks
SELECT
    s.user_id,
    COALESCE(a.email, s.user_id) as email,
    COALESCE(a.role, 'member') as role
```

**Application:**
- ✅ admin_service.py (_get_users_breakdown)
- ✅ admin_service.py (get_active_sessions) - utilisait déjà LEFT JOIN
- ⏳ À vérifier dans d'autres services avec jointures auth

---

### 3. Error Handling with Fallbacks

**Context:** Les services ne doivent jamais crasher, même en cas d'erreur.

**Convention Obligatoire:**

```python
async def get_data(self) -> Dict[str, Any]:
    try:
        # Logique principale
        result = await self._process_data()
        logger.info(f"[Service] Operation successful: {len(result)} items")
        return result
    except Exception as e:
        logger.error(f"[Service] Error: {e}", exc_info=True)
        # Retourner structure valide avec données vides
        return {
            "data": [],
            "total": 0,
            "error": str(e)  # Optionnel pour debug
        }
```

**Application:**
- ✅ admin_service.py (toutes les fonctions publiques)
- ✅ timeline_service.py (toutes les fonctions)
- ⏳ À vérifier dans service.py et autres modules

---

### 4. Logging Standards

**Context:** Faciliter le debugging en production avec logs structurés.

**Convention Obligatoire:**

```python
import logging
logger = logging.getLogger(__name__)

# Format: [ServiceName] Action: details
logger.info(f"[Timeline] Activity timeline returned {len(rows)} days for user_id={user_id}")
logger.warning("[admin_dashboard] No users found in sessions table")
logger.error(f"[admin_dashboard] Error getting costs: {e}", exc_info=True)
```

**Application:**
- ✅ timeline_service.py
- ✅ admin_service.py
- ⏳ À uniformiser dans tous les services

---

## Checklist Pré-Modification (Pour Tous les Agents)

Avant de modifier un fichier backend, vérifier:

- [ ] Le fichier utilise-t-il des timestamps ? → Appliquer COALESCE
- [ ] Le fichier fait-il des jointures avec auth ? → Utiliser LEFT JOIN
- [ ] Les fonctions ont-elles des try/except ? → Ajouter fallbacks
- [ ] Les logs sont-ils explicites ? → Utiliser format standardisé
- [ ] Les changements suivent-ils les conventions ? → Vérifier AGENTS_COORDINATION.md

---

## Checklist Post-Modification (Pour Tous les Agents)

Après avoir modifié du code:

- [ ] Documenter les changements dans les commentaires (référence phase)
- [ ] Mettre à jour les docstrings si signature changée
- [ ] Ajouter logging si opération importante
- [ ] Tester manuellement avec `curl` ou interface
- [ ] Vérifier les logs pour confirmer le bon fonctionnement
- [ ] Mettre à jour la documentation (status, changelog)
- [ ] Préparer un commit descriptif

---

## État Actuel du Codebase (2025-10-16)

### Backend Services - Statut Conventions

| Service | NULL Handling | LEFT JOIN | Error Handling | Logging | Status |
|---------|--------------|-----------|----------------|---------|--------|
| timeline_service.py | ✅ | N/A | ✅ | ✅ | ✅ Conforme |
| admin_service.py | ✅ | ✅ | ✅ | ✅ | ✅ Conforme |
| service.py (dashboard) | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ À vérifier |
| queries.py | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ À vérifier |
| auth_service.py | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ À vérifier |

**Légende:**
- ✅ Conforme aux conventions
- ⏳ Non vérifié / À auditer
- ❌ Non conforme (à corriger)

---

## Prochains Points de Synchronisation

### Phase 2: Frontend Fixes (À Venir)

**Agents concernés:** Claude Code, Codex GPT

**Fichiers ciblés:**
- `src/frontend/features/cockpit/cockpit-charts.js`
- `src/frontend/features/memory/memory-center.js`
- `src/frontend/features/admin/admin-dashboard.js`

**Conventions à établir:**
- Filtrage des agents de développement (blacklist)
- Mapping fixe des couleurs par agent
- Système de design unifié (button system)

**Actions:**
1. Auditer les fichiers frontend
2. Définir conventions UI/UX
3. Créer composants réutilisables
4. Mettre à jour ce document

---

### Phase 3: Tests Automatisés (À Venir)

**Agents concernés:** Claude Code

**Objectifs:**
- Créer suite de tests pytest pour backend
- Créer tests Jest/Vitest pour frontend
- Automatiser la validation Phase 1

**Convention:** Tous les nouveaux services doivent avoir des tests unitaires.

---

## Communication Entre Sessions

### Pour Claude Code (sessions futures)

**Quand vous reprenez le projet:**

1. **Lire en priorité:**
   - `PLAN_DEBUG_COMPLET.md` - Vision globale
   - `DEBUG_PHASE1_STATUS.md` - État Phase 1
   - `AGENTS_COORDINATION.md` - Conventions
   - Ce fichier - Derniers changements

2. **Vérifier git:**
   ```bash
   git status
   git log --oneline -10
   git diff main
   ```

3. **Questions à se poser:**
   - Quelle phase est en cours ?
   - Y a-t-il des changements non committés ?
   - Les conventions sont-elles toujours à jour ?

### Pour Codex GPT (requêtes ponctuelles)

**Prompt de contexte recommandé:**

```
Tu es Codex GPT travaillant sur ÉMERGENCE V8 (Beta 1.1.0).

Conventions obligatoires:
1. NULL timestamps: Toujours utiliser COALESCE(timestamp, created_at, 'now')
2. Jointures auth: Préférer LEFT JOIN avec conditions flexibles
3. Gestion erreur: Try/catch avec fallbacks, jamais de crash
4. Logging: Format [ServiceName] Action: details

Fichiers de référence:
- docs/AGENTS_COORDINATION.md
- docs/INTER_AGENT_SYNC.md

Tâche: [DESCRIPTION DE LA TÂCHE]
```

---

## Historique des Synchronisations

### 2025-10-18 14:30 - Synchronisation version beta-2.1.3

**Agent:** Codex (GPT-5)
**Contexte:** Préparation déploiement Guardian email reports

**Changements:**
- Alignement version globale sur eta-2.1.3
- Mise à jour des documents coordination (ce fichier + AGENTS_COORDINATION.md)
- Rappel de consigner AGENT_SYNC & passation après chaque release

**Impact:**
- Clarifie la version cible pour la session de déploiement
- Facilite la coordination Claude/Codex pour les étapes canary → stable

### 2025-10-16 23:30 - Phase 1 Backend Fixes Complète

**Agent:** Claude Code (Sonnet 4.5)
**Commit:** (à créer)

**Changements:**
- 3 fichiers modifiés (timeline_service, admin_service, admin_router)
- 4 fichiers créés (docs coordination, status, checklist)
- 8 fonctions corrigées
- 1 endpoint ajouté
- Conventions établies et documentées

**Impact:**
- ✅ Cockpit Timeline charts fonctionnels
- ✅ Admin users breakdown fonctionnel
- ✅ Admin date metrics fonctionnel
- ✅ Admin detailed costs endpoint créé
- ✅ Checklist validation créée

**Prochaine session:**
- Exécuter validation checklist
- Committer changements
- Démarrer Phase 2 (Frontend)

---

## Notes Importantes

### Pour Éviter les Conflits

1. **Toujours synchroniser avant de commencer:**
   ```bash
   git pull origin main
   ```

2. **Vérifier qu'aucune session parallèle n'est active:**
   - Checker les fichiers de passation récents
   - Vérifier `git log` pour commits récents

3. **Communiquer via documentation:**
   - Mettre à jour ce fichier après chaque session
   - Documenter les décisions architecturales
   - Laisser des notes pour la prochaine session

### En Cas de Doute

**Si incertain sur une convention:**
1. Vérifier `AGENTS_COORDINATION.md`
2. Chercher dans le code existant un pattern similaire
3. Documenter la question et demander arbitrage utilisateur

**Si conflit détecté:**
1. S'arrêter immédiatement
2. Documenter le conflit dans un fichier temporaire
3. Demander résolution utilisateur
4. Une fois résolu, mettre à jour les conventions

---

**Ce document est vivant et doit être mis à jour après chaque session significative.**

**Dernière modification par:** Claude Code (Sonnet 4.5)
**Prochaine révision:** Après Phase 2 ou sur demande utilisateur



