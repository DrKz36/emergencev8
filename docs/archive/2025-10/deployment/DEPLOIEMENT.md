# Guide de Déploiement - Correctif d'Isolation des Données

## Changements Effectués

### 1. Sécurité Critique
- **Isolation des données utilisateurs** : Tous les endpoints API exigent maintenant `user_id` pour accéder aux données
- **Modules affectés** : Documents, Threads, Messages, Coûts, Dashboard

### 2. Fichiers Modifiés

#### Backend
- [`src/backend/core/database/queries.py`](src/backend/core/database/queries.py) - Fonctions de base de données
  - `get_all_documents` - Exige user_id
  - `get_document_by_id` - Exige user_id
  - `get_threads` - Exige user_id
  - `get_thread` - Exige user_id
  - `get_messages` - Exige user_id
  - `get_thread_docs` - Exige user_id
  - `_build_costs_where_clause` - Exige user_id
  - `get_messages_by_period` - Exige user_id

- [`src/backend/features/dashboard/service.py`](src/backend/features/dashboard/service.py)
  - `get_costs_by_agent` - Filtre toujours par user_id

- [`src/backend/features/documents/service.py`](src/backend/features/documents/service.py)
  - `search_documents` - Filtre toujours par user_id
  - `delete_document` - Amélioration du filtrage des vecteurs

### 3. Tests
- [`test_isolation.py`](test_isolation.py) - Tests d'isolation des données (TOUS PASSÉS ✅)

## Procédure de Déploiement

### 1. Vérification Préalable

```bash
# 1. Vérifier que vous êtes sur la bonne branche
git branch

# 2. S'assurer que les tests passent
python test_isolation.py
```

### 2. Build du Frontend

```bash
cd src/frontend
npm run build
cd ../..
```

### 3. Sauvegarde de la Base de Données

```bash
# Créer une sauvegarde avant déploiement
python scripts/backup.py
```

### 4. Déploiement

```bash
# Option A: Déploiement automatique (si configuré)
./deploy.sh

# Option B: Déploiement manuel
# 1. Arrêter le serveur actuel
pm2 stop emergence

# 2. Mettre à jour le code
git pull

# 3. Redémarrer le serveur
pm2 restart emergence

# 4. Vérifier les logs
pm2 logs emergence --lines 50
```

### 5. Vérification Post-Déploiement

1. **Tester l'authentification**
   - Se connecter avec un compte admin
   - Se connecter avec un compte membre

2. **Tester l'isolation des documents**
   - Avec compte admin : uploader un document
   - Avec compte membre : vérifier qu'il n'apparaît PAS dans la liste
   - Avec compte admin : vérifier que le document est visible

3. **Tester les autres fonctionnalités**
   - Threads/conversations
   - Dashboard/cockpit
   - Coûts et statistiques

### 6. En Cas de Problème

Si des erreurs 500 apparaissent :

```bash
# 1. Consulter les logs
pm2 logs emergence --err --lines 100

# 2. Vérifier la base de données
sqlite3 data/emergence.db "PRAGMA integrity_check;"

# 3. Si nécessaire, rollback
git reset --hard HEAD~1
pm2 restart emergence
```

## Points d'Attention

### Erreurs Attendues

Si vous voyez dans les logs :
```
ValueError: user_id est obligatoire pour accéder aux documents
```

C'est **NORMAL** et **SOUHAITÉ** - cela signifie que la sécurité fonctionne correctement.

### Endpoints Affectés

Tous ces endpoints nécessitent maintenant une authentification valide :
- `GET /api/documents/`
- `GET /api/documents/{id}`
- `GET /api/threads/`
- `GET /api/threads/{id}`
- `GET /api/dashboard/costs/summary`
- `GET /api/memory/tend-garden`

### Compatibilité Backend

Les modifications sont **rétrocompatibles** avec les anciennes bases de données :
- Si `user_id` n'existe pas dans la table, les requêtes retournent des résultats vides (sécurité par défaut)
- Les logs d'avertissement indiquent les colonnes manquantes

## Support

En cas de problème après déploiement :

1. **Vérifier les logs** : `pm2 logs emergence`
2. **Tester l'isolation** : `python test_isolation.py`
3. **Consulter** : [SECURITY_FIX_2025-10-12.md](SECURITY_FIX_2025-10-12.md)

## Checklist de Déploiement

- [ ] Sauvegarde de la base de données effectuée
- [ ] Tests d'isolation exécutés et passés
- [ ] Frontend buildé
- [ ] Code déployé en production
- [ ] Serveur redémarré
- [ ] Authentification testée (admin + membre)
- [ ] Isolation des documents vérifiée
- [ ] Dashboard accessible
- [ ] Logs vérifiés (pas d'erreurs critiques)

---

**Date de création :** 12 octobre 2025
**Version :** 1.0
**Statut :** Prêt pour déploiement
