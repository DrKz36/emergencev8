# Coordination Inter-Agents - ÉMERGENCE V8

**Dernière mise à jour:** 2025-10-16 23:30
**Version:** Beta 1.1.0
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
