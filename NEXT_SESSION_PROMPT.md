# 🚀 PROMPT NEXT SESSION - Émergence V8

**Date création** : 2025-10-21 20:45 CET
**Session précédente** : Priority 1.3 Mypy batch 1 (100 → 66 erreurs) ✅
**Prochaine session** : Priority 1.3 Mypy batch 2 (66 → 50 erreurs) ou Priority 2

---

## 📊 ÉTAT ACTUEL DU PROJET

### ✅ Ce qui fonctionne parfaitement
- **Tests backend** : 45/45 passent (100%)
- **Build frontend** : Succès (warnings mineurs)
- **Production GCP** : Stable (beta-2.1.6 déployé, 100% trafic)
- **Guardian** : Fonctionnel (faux positifs filtrés: 9 → 7 warnings bots)
- **Docker Compose** : Stack dev complète opérationnelle
- **Priority 1** : **3/3 complétées** ✅
  - 1.1 ProdGuardian faux positifs ✅
  - 1.2 Pre-commit hook V2 ✅
  - 1.3 Mypy batch 1 ✅ (100 → 66 erreurs, -34)

### ⚠️ Ce qui nécessite encore du travail
- **Mypy** : 66 erreurs (amélioration de 95 → 66, batch 1 complété)
- **Documentation Guardian** : 45 fichiers (à réduire à 5)
- **Warnings build frontend** : Chunks trop gros, import mixte
- **Tests HTTP endpoints** : Désactivés (couverture à améliorer)

---

## 🎯 PROCHAINE PRIORITÉ RECOMMANDÉE

### Option A : Mypy Batch 2 (2-3 heures) ⭐ RECOMMANDÉ

**Objectif** : Réduire erreurs de 66 → 50 (-16 erreurs minimum)

**Focus** :
1. **Google Cloud imports** (erreurs critiques) :
   - `google.cloud.storage` attribute not found
   - `google.cloud.firestore` attribute not found
   - **Solution** : Installer stubs : `pip install types-google-cloud-storage types-google-cloud-firestore`

2. **Prometheus metrics** (weighted_retrieval_metrics.py ligne 34) :
   - Incompatible assignment CollectorRegistry
   - **Solution** : Fix type annotation ou restructurer

3. **Unified retriever** (unified_retriever.py lignes 409, 418, 423) :
   - Float → int assignments
   - Object → dict[str, Any] conversion
   - **Solution** : Add explicit casts or type annotations

**Commandes** :
```bash
# Lancer mypy pour voir erreurs restantes
cd src && mypy backend/ --explicit-package-bases --no-error-summary 2>&1 | head -n 50

# Installer stubs Google Cloud
pip install types-google-cloud-storage types-google-cloud-firestore

# Re-tester après corrections
pytest -v
```

**Temps estimé** : 2-3 heures
**Difficulté** : Moyenne (imports externes, libs tierces)

---

### Option B : Nettoyer Documentation Guardian (2 heures)

**Objectif** : Passer de 45 fichiers → 5 fichiers essentiels

**Fichiers à garder** :
1. `README.md` - Vue d'ensemble
2. `SYSTEM_STATUS.md` - État actuel
3. `CONFIGURATION.md` - Config Guardian
4. `TROUBLESHOOTING.md` - Debug
5. `CHANGELOG.md` - Historique

**Fichiers à archiver** : Déplacer vers `docs/archive/`

**Commandes** :
```bash
# Lister fichiers Guardian
ls -la claude-plugins/integrity-docs-guardian/docs/

# Créer archive
mkdir -p claude-plugins/integrity-docs-guardian/docs/archive

# Déplacer fichiers non essentiels
mv claude-plugins/integrity-docs-guardian/docs/*.md claude-plugins/integrity-docs-guardian/docs/archive/
# (sauf les 5 à garder)
```

**Temps estimé** : 2 heures
**Difficulté** : Facile

---

### Option C : Corriger Warnings Build Frontend (2 heures)

**Objectif** : Éliminer warnings Vite

**Changements** :

**1. Fix admin-icons.js (import mixte)**
- Fichier : `src/frontend/features/admin/admin-dashboard.js`
- Remplacer import statique par dynamique

**2. Code-split vendor chunk**
- Fichier : `vite.config.js`
- Configurer manualChunks pour vendor libs

**Commandes** :
```bash
# Build frontend pour voir warnings
npm run build

# Vérifier chunks
ls -lh dist/assets/
```

**Temps estimé** : 2 heures
**Difficulté** : Facile

---

## 📋 INSTRUCTIONS POUR LA PROCHAINE SESSION

### Étape 1 : Lecture obligatoire (5 min)

**Dans cet ordre :**
1. **`AGENT_SYNC.md`** ← État sync + dernière session
2. **`AUDIT_COMPLET_2025-10-21.md`** ← Section Priority 1 et 2
3. **`docs/passation.md`** ← 3 dernières entrées
4. **`git status`** + **`git log --oneline -10`** ← État Git

### Étape 2 : Choisir priorité (30 sec)

**Recommandation** : **Option A (Mypy Batch 2)** pour continuer momentum sur qualité code.

**Alternative** : Si mypy est trop complexe, basculer sur **Option B (Nettoyer docs)** ou **Option C (Frontend warnings)**.

### Étape 3 : Exécuter (2-3h)

**Mode de travail** :
- ✅ **Autonome** : Fonce directement sans demander
- ✅ **Tests systématiques** : Après chaque batch de fixes
- ✅ **Commits atomiques** : Un commit par batch de corrections
- ✅ **Documentation** : Mettre à jour `AGENT_SYNC.md` et `docs/passation.md` en fin de session

### Étape 4 : Clôture (10 min)

**Checklist finale :**
- [ ] Tests backend : `pytest -v` ✅
- [ ] Mypy (si batch 2) : Compter erreurs restantes
- [ ] Build frontend (si warnings) : `npm run build` ✅
- [ ] Mettre à jour `AGENT_SYNC.md`
- [ ] Nouvelle entrée `docs/passation.md`
- [ ] Mettre à jour `AUDIT_COMPLET_2025-10-21.md` (progression)
- [ ] Commit + push

---

## 🎯 EXEMPLE DE PROMPT POUR DÉMARRER

**Copier-coller ceci dans la prochaine session :**

```
Salut ! Je continue le travail sur Émergence V8.

CONTEXTE :
Session précédente a complété Priority 1.3 Mypy batch 1 (100 → 66 erreurs, -34 erreurs).
L'audit complet est dans AUDIT_COMPLET_2025-10-21.md.

PROCHAINE PRIORITÉ :
Option A recommandée : Mypy Batch 2 (66 → 50 erreurs)
Focus sur Google Cloud imports, Prometheus metrics, Unified retriever.

ACTIONS IMMÉDIATES :
1. Lis AGENT_SYNC.md (état sync)
2. Lis AUDIT_COMPLET_2025-10-21.md (section Priority 1.3)
3. Lance mypy pour voir erreurs restantes
4. Corrige batch 2 (Google Cloud imports + Prometheus + Unified retriever)
5. Teste avec pytest
6. Commit + mets à jour docs (AGENT_SYNC.md, passation.md, AUDIT_COMPLET_2025-10-21.md)

Commence par lire AGENT_SYNC.md puis fonce sur le batch 2 ! 🚀
```

---

## 📊 MÉTRIQUES CIBLES

| Métrique | État actuel | Objectif batch 2 | Objectif final |
|----------|-------------|------------------|----------------|
| Mypy erreurs | 66 | 50 | 35 |
| Tests backend | 45/45 | 45/45 | 65/65 |
| Warnings frontend | 2 | 0 | 0 |
| Docs Guardian | 45 fichiers | 5 fichiers | 5 fichiers |

---

## ⚠️ POINTS D'ATTENTION

1. **Google Cloud stubs** : Installer `types-google-cloud-*` AVANT de corriger erreurs
2. **Tests après mypy** : Toujours re-lancer pytest après corrections de types
3. **Prometheus metrics** : Peut nécessiter refactoring (pas juste type annotations)
4. **Git hooks** : Guardian tourne automatiquement (pre-commit/post-commit)
5. **Documentation** : Mettre à jour `AUDIT_COMPLET_2025-10-21.md` avec progression

---

## 🔗 RESSOURCES UTILES

**Fichiers clés :**
- `AGENT_SYNC.md` - Sync inter-agents (dernière session: 2025-10-21 20:30)
- `AUDIT_COMPLET_2025-10-21.md` - État projet (Priority 1: 3/3 ✅)
- `docs/passation.md` - Journal sessions (dernière: 2025-10-21 20:30)
- `mypy_clean_output.txt` - Erreurs mypy (premières 100 lignes)
- `reports/unified_report.json` - Rapport Guardian unifié

**Commandes rapides :**
```bash
# Mypy check
cd src && mypy backend/ --explicit-package-bases --no-error-summary 2>&1 | head -n 50

# Tests
pytest -v

# Build frontend
npm run build

# Git status
git status && git log --oneline -10
```

---

## 📂 DÉTAILS BATCH 2 MYPY

### Erreurs identifiées (66 erreurs totales)

**Catégorie 1: Google Cloud imports (~10-15 erreurs)**
```
backend\features\guardian\storage_service.py:20: error: Module "google.cloud" has no attribute "storage"
backend\features\guardian\storage_service.py:184: error: Item "None" of "Any | None" has no attribute "list_blobs"
```

**Solution** :
```bash
pip install types-google-cloud-storage types-google-cloud-firestore
```

**Catégorie 2: Prometheus metrics (~5 erreurs)**
```
backend\features\memory\weighted_retrieval_metrics.py:34: error: Incompatible types in assignment (expression has type "tuple[Any, ...]", target has type "CollectorRegistry")
```

**Solution** : Vérifier si confusion entre import/assignment, restructurer si nécessaire.

**Catégorie 3: Unified retriever (~6-8 erreurs)**
```
backend\features\memory\unified_retriever.py:409: error: Incompatible types in assignment (expression has type "float", variable has type "int")
backend\features\memory\unified_retriever.py:423: error: Incompatible types in assignment (expression has type "object", variable has type "dict[str, Any]")
```

**Solution** : Type annotations explicites (float, cast to int si nécessaire).

**Reste (~35-40 erreurs)** : Union-attr, import-untyped, notes, etc. (à traiter en batch 3)

---

## 📝 HISTORIQUE SESSIONS

**Session 2025-10-21 20:30** :
- ✅ Priority 1.3 Mypy batch 1 complété
- ✅ 9 fichiers backend corrigés
- ✅ 34 erreurs mypy éliminées (100 → 66)
- ✅ Tests: 45/45 passent
- ✅ Commits: `c837a15`, `3ba97e9`, `8d84393`

**Session 2025-10-21 18:15** :
- ✅ Priority 1.1 ProdGuardian complété
- ✅ 13 patterns bot scans ajoutés
- ✅ Warnings production réduits (9 → 7)
- ✅ Commit: `092d5c6`

**Session 2025-10-21 15:10** :
- ✅ Docker Compose testé
- ✅ Pre-commit hook V2 vérifié
- ✅ Rapports Guardian non versionnés (fix boucle infinie)

---

**Bonne session ! 🚀**
