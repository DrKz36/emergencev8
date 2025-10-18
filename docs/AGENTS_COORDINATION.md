# Coordination Inter-Agents - ÉMERGENCE V8

**Dernière mise à jour:** 2025-10-18 14:30
**Version:** Beta 2.1.3
**Agents impliqués:** Claude Code, Codex GPT, Claude Local

---

## Objectif

Ce document définit les conventions, pratiques et points de synchronisation entre les différents agents IA travaillant sur ÉMERGENCE V8.

---

## Agents Actifs

### 1. Claude Code (Anthropic)
- **Rôle:** Agent principal de développement et refactoring
- **Spécialités:** Architecture backend, debugging, optimisations
- **Accès:** Codebase complet, Git, documentation
- **Sessions:** Basées sur contexte conversationnel

### 2. Codex GPT (OpenAI)
- **Rôle:** Génération de code, prototypage rapide
- **Spécialités:** Frontend, patterns UI, scripts utilitaires
- **Accès:** Via API, prompts structurés
- **Sessions:** Stateless, requêtes ponctuelles

### 3. Claude Local (si déployé)
- **Rôle:** Agent de développement local pour tests
- **Spécialités:** Expérimentations, validations rapides
- **Accès:** Environnement local

---

## Conventions de Développement

### 1. Gestion des Timestamps NULL

**Décision Architecturale (Phase 1):**

Tous les agents DOIVENT utiliser `COALESCE` pour les requêtes SQL impliquant des timestamps.

**Pattern standard:**
```sql
-- ❌ ÉVITER
WHERE DATE(timestamp) = DATE('now')

-- ✅ UTILISER
WHERE DATE(COALESCE(timestamp, created_at, 'now')) = DATE('now')
```

**Fonction helper (à créer si nécessaire):**
```python
def get_safe_date_column(table: str) -> str:
    """
    Retourne une expression SQL robuste pour obtenir une date.
    Essaie timestamp, puis created_at, puis 'now'.
    """
    if table == "costs":
        return "DATE(COALESCE(timestamp, created_at, 'now'), 'localtime')"
    elif table == "messages":
        return "DATE(COALESCE(created_at, timestamp, 'now'), 'localtime')"
    else:
        return "DATE(COALESCE(created_at, 'now'), 'localtime')"
```

---

### 2. Jointures Flexibles

**Décision Architecturale (Phase 1):**

Préférer `LEFT JOIN` aux `INNER JOIN` pour éviter l'exclusion de données valides.

**Pattern standard:**
```sql
-- ❌ ÉVITER (trop restrictif)
FROM sessions s
INNER JOIN auth_allowlist a ON s.user_id = a.email

-- ✅ UTILISER (inclusif)
FROM sessions s
LEFT JOIN auth_allowlist a ON (
    s.user_id = a.email
    OR s.user_id = a.user_id
)
```

**Avec fallbacks:**
```sql
SELECT
    s.user_id,
    COALESCE(a.email, s.user_id) as email,
    COALESCE(a.role, 'member') as role
FROM sessions s
LEFT JOIN auth_allowlist a ON (...)
```

---

### 3. Logging Standardisé

**Convention:**

Tous les services backend doivent logger les opérations importantes avec un préfixe identifiable.

**Format:**
```python
logger.info(f"[{service_name}] {action}: {details}")
logger.warning(f"[{service_name}] {warning_message}")
logger.error(f"[{service_name}] Error {action}: {error}", exc_info=True)
```

**Exemples:**
```python
logger.info(f"[Timeline] Activity timeline returned {len(rows)} days for user_id={user_id}")
logger.warning("[admin_dashboard] No users found in sessions table")
logger.error(f"[admin_dashboard] Error getting detailed costs: {e}", exc_info=True)
```

---

### 4. Gestion d'Erreurs Robuste

**Convention:**

Toutes les fonctions de service doivent avoir des fallbacks et ne jamais crasher.

**Pattern standard:**
```python
async def get_data(self) -> Dict[str, Any]:
    try:
        # Logique principale
        result = await self._fetch_data()
        logger.info(f"[Service] Data fetched successfully")
        return result
    except Exception as e:
        logger.error(f"[Service] Error fetching data: {e}", exc_info=True)
        # Retourner structure valide avec données vides
       return {
           "data": [],
           "total": 0,
           "status": "error"
       }
```

---

### 5. Utilitaires mémoire & monitoring (2025-10-18)

**Scripts partagés (racine repo)** :
- `check_archived_threads.py` : inventaire rapide des threads archivés (structure + compte messages) pour diagnostiquer la base SQLite.
- `consolidate_archives_manual.py` : consolidation manuelle des threads archivés vers Chroma (mode offline). **⚠️** À exécuter uniquement après validation avec Claude Code (fix SQL encore nécessaire).
- `test_archived_memory_fix.py` : vérifie la récupération des concepts legacy / filtrage permissif (`agent_id`). À lancer dès qu'une base Chroma contient des souvenirs réels.
- `test_anima_context.py` : contrôle que l’absence de mémoire renvoie bien un contexte vide (doit déclencher le toast côté UI).
- `claude-plugins/integrity-docs-guardian/scripts/argus_simple.py` : mini-monitor pour valider que backend (8000) et frontend (5173) tournent avant tests manuels.

**Documentation associée** :
- `RAPPORT_TEST_MEMOIRE_ARCHIVEE.md` – synthèse des constats & plan d’action (Chroma vide, scripts à corriger, protocole QA).

**Coordination Claude Code / Codex** :
1. **Préparation** : lancer `argus_simple.py` pour vérifier que les services sont bien démarrés (évite des tests mémoire à vide).
2. **Diagnostic DB** : `python check_archived_threads.py` (Claude Code) pour confirmer l’état des threads avant consolidation.
3. **Consolidation** : `python consolidate_archives_manual.py` (Codex peut exécuter mais doit consigner tout échec dans passation + ping Claude pour ajustement SQL).
4. **Validation mémoire** :
   - `python test_archived_memory_fix.py` → attendu : concepts listés par agent, legacy inclus.
   - `python test_anima_context.py` → attendu : message “contexte vide” si aucune donnée.
5. **Feedback** : mettre à jour `docs/passation.md` + section correspondante dans `AGENT_SYNC.md` pour garder la traçabilité (tests exécutés, résultats, follow-up).

Ces outils servent de check-list rapide avant de confier une séance de QA mémoire à un autre agent ou à l’architecte.

---

## Points de Synchronisation

### 1. Avant de Commencer une Tâche

**Claude Code doit vérifier:**
- [ ] État git (branch, modifications non committées)
- [ ] Documentation existante (plan de debug, roadmap)
- [ ] Conventions établies dans ce document
- [ ] Travaux en cours des autres agents

**Codex GPT doit recevoir:**
- Contexte du projet (architecture, conventions)
- Objectif précis de la tâche
- Contraintes techniques (patterns à suivre)
- Exemples de code existant

---

### 2. Pendant le Développement

**Pratiques communes:**

1. **Commentaires de référence aux phases:**
   ```python
   # Fix Phase 1.2: Use COALESCE to handle NULL timestamps
   query = "SELECT DATE(COALESCE(timestamp, created_at, 'now')) as date ..."
   ```

2. **Documentation inline:**
   ```python
   async def get_detailed_costs_breakdown(self) -> Dict[str, Any]:
       """
       Get detailed cost breakdown by user and module.
       Fix Phase 1.5: New endpoint to provide granular cost analysis.
       Returns costs aggregated by user, then by module/feature.
       """
   ```

3. **Validation des changements:**
   - Tests manuels avec données réelles
   - Vérification des logs
   - Validation de la structure de réponse

---

### 3. Après Avoir Terminé une Tâche

**Claude Code doit:**
1. Mettre à jour les documents de statut (ex: `DEBUG_PHASE1_STATUS.md`)
2. Créer/mettre à jour la checklist de validation
3. Documenter les décisions architecturales
4. Préparer un commit descriptif
5. Mettre à jour ce fichier si nouvelles conventions

**Codex GPT doit:**
1. Documenter le code généré
2. Fournir des exemples d'utilisation
3. Lister les dépendances ajoutées

---

## Fichiers Critiques de Coordination

### Documentation de Debug
- [`PLAN_DEBUG_COMPLET.md`](../PLAN_DEBUG_COMPLET.md) - Plan détaillé avec causes racines
- [`DEBUG_PHASE1_STATUS.md`](DEBUG_PHASE1_STATUS.md) - Statut Phase 1
- [`PHASE1_VALIDATION_CHECKLIST.md`](tests/PHASE1_VALIDATION_CHECKLIST.md) - Tests de validation

### Architecture
- [`ROADMAP_OFFICIELLE.md`](../ROADMAP_OFFICIELLE.md) - Roadmap produit
- [`ROADMAP_PROGRESS.md`](../ROADMAP_PROGRESS.md) - Suivi des progrès
- [`agents-profils.md`](agents-profils.md) - Profils des agents système

### Développement
- Ce fichier - Coordination inter-agents
- [`INTER_AGENT_SYNC.md`](INTER_AGENT_SYNC.md) - Points de synchronisation détaillés
- `test_archived_memory_fix.py` - Script de validation mutualisé pour le fix « souvenirs archivés »
  - ⚙️ À lancer par Claude Code **et** Codex GPT avant handoff lorsqu'un changement touche la mémoire
  - ⚠️ Utiliser l'attribut `TopicSummary.topic` pour tout affichage ou logging (l'attribut `name` est obsolète)

---

## Résolution de Conflits

### Cas 1: Modifications Concurrentes

**Symptôme:** Deux agents modifient le même fichier.

**Solution:**
1. L'agent détectant le conflit doit s'arrêter
2. Vérifier `git status` et `git diff`
3. Analyser les changements de l'autre agent
4. Fusionner manuellement ou demander arbitrage utilisateur

### Cas 2: Conventions Contradictoires

**Symptôme:** Un agent suit une convention différente.

**Solution:**
1. Identifier la convention la plus récente dans ce document
2. Mettre à jour le code pour uniformiser
3. Documenter la décision dans ce fichier

### Cas 3: Approches Architecturales Différentes

**Symptôme:** Deux solutions valides pour un même problème.

**Solution:**
1. Documenter les deux approches avec pros/cons
2. Demander validation utilisateur
3. Une fois décidé, mettre à jour ce document

---

## Changelog des Conventions

### 2025-10-18 - Synchronisation version beta-2.1.3

**Ajouts:**
- Mise à jour des références de version (beta-2.1.3)
- Rappel de garder AGENT_SYNC/passation alignés après déploiements

**Impacts:**
- Codex & Claude se basent sur une version unique actualisée
- Facilite la préparation des releases Guardian (email reports)

### 2025-10-16 - Phase 1 Backend Fixes

**Ajouts:**
- Convention COALESCE pour NULL timestamps
- Préférence LEFT JOIN sur INNER JOIN
- Format logging standardisé avec préfixes
- Pattern gestion d'erreur avec fallbacks
- Documentation des décisions dans les commentaires

**Motivations:**
- Phase 1 du debug a identifié des problèmes de gestion NULL
- Besoin d'uniformiser les pratiques backend
- Faciliter la maintenance future

**Impacts:**
- Tous les nouveaux services doivent suivre ces conventions
- Le code existant sera progressivement refactoré

---

## Contact et Questions

Pour toute question sur ces conventions ou pour proposer des améliorations :

1. **Dans le chat:** Mentionner explicitement le besoin de clarification
2. **Documentation:** Créer une issue dans les fichiers de passation
3. **Urgent:** Demander arbitrage utilisateur direct

---

**Maintenu par:** Les agents IA collaboratifs
**Approuvé par:** Équipe de développement ÉMERGENCE V8
**Révision:** Trimestrielle ou après chaque phase majeure


