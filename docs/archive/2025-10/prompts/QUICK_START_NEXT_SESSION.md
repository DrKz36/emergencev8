# Quick Start - Prochaine Session RAG

**Contexte** : Phase 3 + 3.1 implémentées, tests en cours par utilisateur

---

## ⚡ TL;DR

**Problème** : Agents paraphrasent au lieu de citer textuellement
**Solution** : Triple renforcement (RAG + prompts + marqueurs visuels)
**Status** : Implémenté, en test utilisateur

---

## 🎯 Ta Mission (1 ligne)

Analyser résultats tests utilisateur → Débugger si KO → Améliorer si OK

---

## 📋 Checklist Rapide

### 1. Lire Feedback Utilisateur (10 min)
- [ ] Citations poème fondateur exactes ? (oui/non)
- [ ] Citations thématiques exactes ? (oui/non)
- [ ] Satisfaction globale (1-10) ?

### 2. Examiner Logs Backend (10 min)
```bash
grep "RAG" app.log | tail -100

# Chercher :
# - [RAG Cache] HIT/MISS
# - [RAG Merge] Top 1: ... keywords=fondateur
# - INSTRUCTION PRIORITAIRE (doit apparaître)
```

### 3. Action Selon Résultat

#### Si SUCCÈS (citations exactes)
→ Passer à Phase 4 (optimisations avancées)
→ Voir section "Scénario Optimiste" dans [NEXT_SESSION_RAG_PHASE3_TESTS.md](docs/passation/NEXT_SESSION_RAG_PHASE3_TESTS.md)

#### Si ÉCHEC (citations incorrectes)
→ Débugger selon hypothèses
→ Voir section "Scénario A/B" dans [NEXT_SESSION_RAG_PHASE3_TESTS.md](docs/passation/NEXT_SESSION_RAG_PHASE3_TESTS.md)

#### Si SUCCÈS PARTIEL (50-70%)
→ Ajuster pondérations scoring
→ Voir section "Itérer Si Succès Partiel" dans [NEXT_SESSION_RAG_PHASE3_TESTS.md](docs/passation/NEXT_SESSION_RAG_PHASE3_TESTS.md)

---

## 🔍 Débogage Rapide

### Problème : Citations incorrectes

**1. Vérifier top-10 chunks**
```bash
# Dans logs, chercher :
[RAG Merge] Top 1: lines 1-14, type=poem, merged=3, keywords=fondateur
```

**2. Vérifier instructions RAG**
```bash
# Dans logs, doit apparaître :
[RAG Context] Generated instructions: has_poem=True, has_complete=True
```

**3. Correctif rapide**
```python
# Si top-10 ne contient pas bon chunk :
# service.py ligne 1823 : augmenter n_results
n_results=50,  # Au lieu de 30
```

### Problème : Refus de citer

**Correctif rapide**
```python
# service.py ligne 563 : augmenter boost keyword
keyword_score = 1.0 - (match_ratio * 0.8)  # Au lieu de 0.5
```

### Problème : Cache ne marche pas

**Correctif rapide**
```python
# Invalider cache
self.rag_cache.invalidate_all()

# Ou désactiver temporairement
# .env : RAG_CACHE_ENABLED=false
```

---

## 📁 Fichiers Clés

**Code** :
- `src/backend/features/chat/service.py` (ligne 847-961 : formatting, ligne 482-642 : scoring)

**Prompts** :
- `prompts/anima_system_v2.md` (ligne 16)
- `prompts/neo_system_v3.md` (ligne 16)
- `prompts/nexus_system_v2.md` (ligne 18)

**Documentation** :
- [NEXT_SESSION_RAG_PHASE3_TESTS.md](docs/passation/NEXT_SESSION_RAG_PHASE3_TESTS.md) ← LIRE EN PRIORITÉ
- [rag_phase3.1_exact_citations.md](docs/rag_phase3.1_exact_citations.md)

---

## 💬 Questions à Poser

1. **Le poème fondateur est cité EXACTEMENT ?** (oui/non)
2. **Les citations thématiques sont textuelles ?** (oui/non)
3. **Satisfaction (1-10) ?**

---

## 🚀 Si Tout Fonctionne

**Prochaines étapes** :
1. Documenter succès dans PHASE3.1_CHANGELOG
2. Commencer Phase 4 : Learning-to-Rank avec feedback
3. Déploiement production (merge main + Cloud Run)

---

**Pour détails complets** → [NEXT_SESSION_RAG_PHASE3_TESTS.md](docs/passation/NEXT_SESSION_RAG_PHASE3_TESTS.md)
