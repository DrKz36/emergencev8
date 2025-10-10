# PROMPT SESSION - Nettoyage Projet Post-Audit

**Date:** 2025-10-10
**Priorité:** Maintenance (Non bloquant)
**Durée estimée:** 2-3 heures
**Basé sur:** AUDIT_COMPLET_EMERGENCE_V8_20251010.md (Section 4)

---

## 🎯 OBJECTIF DE LA SESSION

Nettoyer le projet Emergence V8 en supprimant **~13 Mo de fichiers obsolètes** et en archivant **~620 Ko de documents historiques** pour améliorer la maintenabilité et réduire le bruit dans le dépôt.

---

## 📋 CONTEXTE

### État actuel
✅ **Tous les bugs P0 résolus** (2025-10-10)
✅ **Tests validés** : 16/16 nouveaux tests passent
✅ **Code stabilisé** : Ruff + Mypy OK

⚠️ **Dette technique détectée** :
- 13 Mo de fichiers obsolètes (logs, arborescences, scripts temporaires)
- 620 Ko de prompts/sessions/rapports terminés
- ~7.5 Mo fichiers à valider avant suppression (backups anciens)

### Impact du nettoyage
- ✅ Réduction bruit dans le dépôt
- ✅ Amélioration vitesse git operations
- ✅ Clarification structure projet
- ✅ Facilitation onboarding nouveaux développeurs

---

## 📁 SUPPRESSION IMMÉDIATE (~13 Mo)

### A. Logs obsolètes (~130 Ko)
**Racine du projet :**
```bash
rm backend-uvicorn.log
rm backend_server.log backend_server.err.log
rm backend.log backend.err.log
rm backend_start.log backend_start.err.log
rm backend_dev_8001.out.log backend_dev_8001.err.log
```

**Dossier /tmp :**
```bash
rm tmp/backend*.log
rm tmp/npm-dev.log tmp/npm-dev.err.log
```

**Dossier /logs :**
```bash
rm -rf logs/vector-store/
```

**Commande consolidée :**
```bash
# Depuis la racine du projet
rm -f *.log *.err.log
rm -f tmp/*.log
rm -rf logs/vector-store/
```

---

### B. Arborescences anciennes (~10.5 Mo)
**Garder SEULEMENT la plus récente (20251008)**
```bash
rm arborescence_synchronisee_20251003.txt  # 5.2 Mo
rm arborescence_synchronisee_20251004.txt  # 5.2 Mo
# GARDER: arborescence_synchronisee_20251008.txt (4.0 Mo)
```

---

### C. Scripts temporaires /tmp (~180 Ko)
Scripts one-shot qui ont servi une seule fois :
```bash
cd tmp
rm apply_api_patch.py patch_api_client_clean.py patch_websocket.py websocket.patch
rm rewrite_api_utf8.py remove_bom.py update_docstring.py update_decay.py
rm clean_logs.py update_memory_doc.py update_table.py fix_row.py normalize_row.py
rm fix_init.py insert_row.py smoke_doc.txt table_snippet.txt table_repr.txt
rm doc_repr.txt voice_service_lines.txt dispatcher_lines.txt debate_lines.txt
rm head_chat.js app.js docker-tag.txt health_response.json codex_backend.pid pr_body.md
```

---

### D. OpenAPI dupliqués (~85 Ko)
**Garder SEULEMENT openapi.json**
```bash
rm openapi_canary.json  # 27 Ko
rm openapi.custom.json  # 29 Ko
rm openapi.run.json     # 29 Ko
# GARDER: openapi.json (10 Ko)
```

---

### E. Fichiers __pycache__ (~2 Mo)
**Normaux mais peuvent être regénérés**
```bash
# Méthode 1: find (Unix/Git Bash)
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

# Méthode 2: Python (cross-platform)
python -c "import pathlib, shutil; [shutil.rmtree(p) for p in pathlib.Path('.').rglob('__pycache__')]"
```

---

### F. Fichiers temporaires racine
```bash
rm body.json id_token.txt placeholder.tmp
```

---

### G. tmp_tests (~90 Ko)
Tests de smoke anciens (août-octobre 2025)
```bash
rm -rf tmp_tests/
```

---

## 📦 ARCHIVAGE RECOMMANDÉ (~620 Ko)

### Créer structure d'archivage
```bash
mkdir -p docs/archive/prompts
mkdir -p docs/archive/sessions
mkdir -p docs/archive/reports
```

### A. Prompts de sessions passées (~450 Ko)
```bash
# Prompts obsolètes (fonctionnalités déjà implémentées)
mv NEXT_SESSION_CONCEPT_RECALL.md docs/archive/prompts/
mv AUDIT_FIXES_PROMPT.md docs/archive/prompts/
mv CODEX_PR_PROMPT.md docs/archive/prompts/
mv CODEX_SYNC_UPDATE_PROMPT.md docs/archive/prompts/
mv CODEX_BUILD_DEPLOY_PROMPT.md docs/archive/prompts/
mv PROMPT_VALIDATION_PHASE2.md docs/archive/prompts/
mv PROMPT_CODEX_ENABLE_METRICS.md docs/archive/prompts/
mv PROMPT_DEBUG_COCKPIT_METRICS.md docs/archive/prompts/
mv PROMPT_CODEX_DEPLOY_PHASE3.md docs/archive/prompts/
mv PROMPT_COCKPIT_NEXT_FEATURES.md docs/archive/prompts/
mv PROMPT_COCKPIT_DEBUG_IMPLEMENTATION.md docs/archive/prompts/
mv PROMPT_P1_MEMORY_ENRICHMENT.md docs/archive/prompts/
mv PROMPT_CODEX_DEPLOY_P1.md docs/archive/prompts/

# ⚠️ NE PAS ARCHIVER (utilisés cette semaine):
# - PROMPT_NEXT_SESSION_AUDIT_FIXES_P0.md (session actuelle)
# - PROMPT_NEXT_SESSION_P1_FIXES.md (prochaine session)
# - PROMPT_NEXT_SESSION_CLEANUP.md (ce fichier)
```

### B. Récapitulatifs de sessions (~100 Ko)
```bash
mv SESSION_SUMMARY_20251009.md docs/archive/sessions/
mv SESSION_P1_RECAP.txt docs/archive/sessions/
mv SESSION_P1_2_RECAP.txt docs/archive/sessions/
mv SESSION_P0_RECAP.txt docs/archive/sessions/
mv SESSION_HOTFIX_P1_3_RECAP.txt docs/archive/sessions/
mv SESSION_P1_VALIDATION_PREP.md docs/archive/sessions/
mv SESSION_P1_VALIDATION_RESULTS.md docs/archive/sessions/
```

### C. Rapports terminés (~30 Ko)
```bash
mv SYNC_REPORT.md docs/archive/reports/
mv TESTS_VALIDATION_REPORT.md docs/archive/reports/
mv AUDIT_FINAL_REPORT.md docs/archive/reports/

# ⚠️ NE PAS ARCHIVER (document actif):
# - AUDIT_COMPLET_EMERGENCE_V8_20251010.md (référence active)
```

---

## ⚠️ VALIDATION HUMAINE REQUISE (~7.5 Mo)

### A. Backup vector_store ancien (6.7 Mo)
**Backup du 26 août 2025** (il y a 1.5 mois)

**Action recommandée :** SI la base vectorielle actuelle fonctionne bien :
```bash
# ⚠️ DEMANDER CONFIRMATION AVANT D'EXÉCUTER
rm -rf backup/vector_store_20250826_052559/
```

**Alternative :** Archiver dans un stockage externe (Google Drive, etc.)

---

### B. Database temporaire de test (124 Ko)
```bash
# ⚠️ DEMANDER CONFIRMATION
rm tmp-auth.db
```

---

### C. Sessions débats anciennes (100 Ko)
**12 fichiers JSON datant de juillet 2025** (il y a 3 mois)

**Action recommandée :** SI la fonctionnalité débat n'utilise plus ces données :
```bash
# ⚠️ DEMANDER CONFIRMATION
rm -f data/sessions/debates/202507*.json
```

---

### D. Logs téléchargés (540 Ko)
```bash
# ⚠️ DEMANDER CONFIRMATION
rm downloaded-logs-20251010-041801.json
```

---

## 📝 CHECKLIST D'EXÉCUTION

### Préparation (10 min)
- [ ] Créer branche git : `git checkout -b chore/cleanup-obsolete-files`
- [ ] Vérifier que rien d'important n'est en cours (pas de changements non commités)
- [ ] Backup complet local (au cas où) : `git stash --include-untracked`

### Phase 1 - Suppression immédiate (30 min)
- [ ] **A.** Supprimer logs obsolètes (~130 Ko)
- [ ] **B.** Supprimer arborescences anciennes (~10.5 Mo)
- [ ] **C.** Supprimer scripts /tmp (~180 Ko)
- [ ] **D.** Supprimer OpenAPI dupliqués (~85 Ko)
- [ ] **E.** Supprimer __pycache__ (~2 Mo)
- [ ] **F.** Supprimer fichiers temporaires racine
- [ ] **G.** Supprimer tmp_tests (~90 Ko)
- [ ] Vérifier git status : `git status`

### Phase 2 - Archivage (30 min)
- [ ] Créer structure `docs/archive/`
- [ ] **A.** Archiver prompts sessions passées (~450 Ko)
- [ ] **B.** Archiver récapitulatifs sessions (~100 Ko)
- [ ] **C.** Archiver rapports terminés (~30 Ko)
- [ ] Vérifier structure : `tree docs/archive/`

### Phase 3 - Validation humaine (15 min)
- [ ] Lister fichiers à valider humainement
- [ ] Documenter décision dans PR (pourquoi garder/supprimer)
- [ ] Proposer alternative (archivage externe si important)

### Validation finale (20 min)
- [ ] Tests passent : `pytest tests/backend/features/ -v`
- [ ] Backend démarre : `python -m uvicorn --app-dir src backend.main:app`
- [ ] Frontend build : `npm run build`
- [ ] Git diff review : `git diff --stat`

### Commit + PR (15 min)
- [ ] Stage changes : `git add -A`
- [ ] Commit : `git commit -m "chore: nettoyage ~13 Mo fichiers obsolètes + archivage 620 Ko docs"`
- [ ] Push : `git push origin chore/cleanup-obsolete-files`
- [ ] Créer PR avec détails (fichiers supprimés, gains espace)

---

## 🎯 CRITÈRES DE SUCCÈS

### Résultats attendus
✅ **~13 Mo libérés** (suppression immédiate)
✅ **~620 Ko archivés** (docs/archive/)
✅ **Structure clarifiée** (moins de bruit dans racine)
✅ **Tests toujours OK** (aucune régression)

### Métriques
- **Avant nettoyage :** ~XXX Mo (mesurer avec `du -sh .`)
- **Après nettoyage :** ~XXX Mo (réduction attendue : ~13 Mo)
- **Fichiers racine :** Avant XX, Après XX (réduction attendue : -20+)

---

## 📊 RÉSUMÉ GAINS NETTOYAGE

| Catégorie | Taille | Action | Priorité |
|-----------|--------|--------|----------|
| **Logs** | 130 Ko | Suppression immédiate | ✅ |
| **Arborescences anciennes** | 10.5 Mo | Suppression immédiate | ✅ |
| **Scripts tmp** | 180 Ko | Suppression immédiate | ✅ |
| **__pycache__** | 2 Mo | Suppression immédiate | ✅ |
| **OpenAPI dupliqués** | 85 Ko | Suppression immédiate | ✅ |
| **tmp_tests** | 90 Ko | Suppression immédiate | ✅ |
| **Fichiers racine** | 1 Ko | Suppression immédiate | ✅ |
| **TOTAL IMMÉDIAT** | **~13 Mo** | ✅ | - |
| **Backup vector_store** | 6.7 Mo | Après validation | ⚠️ |
| **Sessions débats** | 100 Ko | Après validation | ⚠️ |
| **DB test** | 124 Ko | Après validation | ⚠️ |
| **Logs téléchargés** | 540 Ko | Après validation | ⚠️ |
| **TOTAL APRÈS VALIDATION** | **~7.5 Mo** | ⚠️ | - |
| **Prompts/sessions** | 450 Ko | Archivage | 📦 |
| **Rapports** | 30 Ko | Archivage | 📦 |
| **TOTAL ARCHIVAGE** | **~620 Ko** | 📦 | - |

**Gain total possible :** ~21 Mo

---

## ⚠️ POINTS D'ATTENTION

### Sécurité
❌ **NE PAS** supprimer sans backup git (créer branche dédiée)
❌ **NE PAS** supprimer fichiers .env, credentials, ou configs production
❌ **NE PAS** toucher à `data/vector_store/` actuel (seulement backup ancien)

### Bonnes pratiques
✅ Créer PR pour review avant merge
✅ Tester backend/frontend après nettoyage
✅ Documenter décisions dans PR (pourquoi garder/supprimer)
✅ Proposer archivage externe pour fichiers importants historiquement

---

## 🚀 APRÈS CETTE SESSION

### Ordre suggéré des priorités
1. ✅ **Nettoyage** (CETTE SESSION - 2-3h)
2. **Bugs P1-P2** (voir `PROMPT_NEXT_SESSION_P1_FIXES.md` - 4-6h)
3. **Déploiement production** (déployer tous fixes P0 + nettoyage)
4. **Refactoring architectural** (Phase 2 audit - 4-6 semaines)

---

**Prompt généré le:** 2025-10-10 10:35
**Basé sur:** AUDIT_COMPLET_EMERGENCE_V8_20251010.md (Section 4)
**Priorité:** Maintenance (utile mais non bloquant)
**Durée estimée:** 2-3 heures
**Agent recommandé:** Claude Code (bash/git/maintenance)
