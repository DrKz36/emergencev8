# Correctif de Sécurité - Isolation des Données Utilisateurs

**Date:** 12 octobre 2025
**Sévérité:** CRITIQUE
**Statut:** CORRIGÉ

## Résumé

Un problème critique d'isolation des données a été identifié et corrigé dans le système. Les documents et autres ressources uploadés par un utilisateur étaient accessibles par d'autres utilisateurs connectés à l'application.

## Problème Identifié

### Description
Le module de documents (et plusieurs autres modules) utilisaient une logique de filtrage insuffisante qui permettait d'accéder aux données en utilisant uniquement `session_id` sans vérifier `user_id`. Cela signifiait qu'un utilisateur pouvait accéder aux documents d'un autre utilisateur.

### Modules Affectés
1. **Documents** (`src/backend/features/documents/`)
   - `get_all_documents`
   - `get_document_by_id`
   - `search_documents`
   - `delete_document` (vecteurs)

2. **Base de données** (`src/backend/core/database/queries.py`)
   - `get_all_documents` (ligne 510)
   - `get_document_by_id` (ligne 528)
   - `get_threads` (ligne 703)
   - `get_thread` (ligne 732)
   - `get_messages` (ligne 925)
   - `get_thread_docs` (ligne 1010)

3. **Dashboard** (`src/backend/features/dashboard/service.py`)
   - `get_costs_by_agent` (ligne 100)

### Code Vulnérable (Exemple)
```python
# AVANT (vulnérable)
async def get_all_documents(
    db: DatabaseManager,
    session_id: Optional[str] = None,
    *,
    user_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    if user_id or session_id:  # ❌ Permet filtrage par session_id seul
        scope_sql, scope_params = _build_scope_condition(user_id, session_id)
        rows = await db.fetch_all(
            f"SELECT ... WHERE {scope_sql}",
            scope_params,
        )
    else:
        rows = await db.fetch_all("SELECT ...")  # ❌ Pas de filtrage du tout
    return [dict(row) for row in rows]
```

## Solution Implémentée

### Changements Principaux

#### 1. Obligation du user_id pour toutes les requêtes de lecture
```python
# APRÈS (sécurisé)
async def get_all_documents(
    db: DatabaseManager,
    session_id: Optional[str] = None,
    *,
    user_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    # ✅ user_id est OBLIGATOIRE
    if not user_id:
        raise ValueError("user_id est obligatoire pour accéder aux documents")

    # ✅ Toujours filtrer par user_id
    scope_sql, scope_params = _build_scope_condition(user_id, session_id)
    rows = await db.fetch_all(
        f"SELECT ... WHERE {scope_sql}",
        scope_params,
    )
    return [dict(row) for row in rows]
```

#### 2. Fichiers Modifiés

**queries.py** ([src/backend/core/database/queries.py](src/backend/core/database/queries.py))
- ✅ `get_all_documents` (lignes 510-519)
- ✅ `get_document_by_id` (lignes 527-536)
- ✅ `get_threads` (lignes 693-712)
- ✅ `get_thread` (lignes 735-744)
- ✅ `get_messages` (lignes 927-945)
- ✅ `get_thread_docs` (lignes 1015-1039)

**dashboard/service.py** ([src/backend/features/dashboard/service.py](src/backend/features/dashboard/service.py))
- ✅ `get_costs_by_agent` (lignes 96-108)

**documents/service.py** ([src/backend/features/documents/service.py](src/backend/features/documents/service.py))
- ✅ `search_documents` (lignes 503-512)
- ✅ `delete_document` vecteurs (lignes 459-464)

### 3. Tests d'Isolation

Un script de test complet a été créé pour vérifier l'isolation :
- [test_isolation.py](test_isolation.py)

```bash
$ python test_isolation.py
Test d'isolation des donnees utilisateurs

Test 1: get_all_documents sans user_id
OK: user_id est obligatoire pour accéder aux documents

Test 2: get_document_by_id sans user_id
OK: user_id est obligatoire pour accéder aux documents

[... 6 autres tests ...]

============================================================
TOUS LES TESTS SONT PASSES!
============================================================
```

## Impact

### Avant le Correctif
- ❌ Un utilisateur admin pouvait uploader un document
- ❌ Un utilisateur membre pouvait voir et accéder à ce document
- ❌ Aucune isolation entre les comptes utilisateurs

### Après le Correctif
- ✅ Chaque utilisateur ne peut accéder qu'à ses propres documents
- ✅ L'isolation est vérifiée au niveau de la base de données
- ✅ Tentative d'accès sans user_id = erreur explicite
- ✅ Les vecteurs ChromaDB sont aussi filtrés par user_id

## Modules Non Affectés

Le module **dialogues/chat** était déjà correctement protégé et utilisait l'isolation par user_id de manière appropriée.

## Recommandations

### Pour le Déploiement
1. ✅ Déployer immédiatement ce correctif en production
2. ✅ Exécuter le script de test pour vérifier l'isolation
3. ✅ Monitorer les logs pour détecter toute tentative d'accès non autorisé

### Pour l'Avenir
1. **Audit de sécurité régulier** : Vérifier périodiquement que tous les nouveaux endpoints respectent l'isolation par user_id
2. **Tests automatisés** : Intégrer les tests d'isolation dans la CI/CD
3. **Revue de code** : S'assurer que chaque nouvelle fonction de lecture de données exige user_id
4. **Principe du moindre privilège** : Ne jamais permettre l'accès aux données sans user_id valide

## Conclusion

Ce correctif élimine une vulnérabilité critique qui permettait l'accès non autorisé aux données entre utilisateurs. L'isolation est maintenant correctement implémentée dans tous les modules.

**Action requise :** Déployer immédiatement en production.

---

**Rapport généré le :** 12 octobre 2025
**Vérifié par :** Tests automatisés (test_isolation.py)
**Statut :** ✅ CORRIGÉ ET TESTÉ
