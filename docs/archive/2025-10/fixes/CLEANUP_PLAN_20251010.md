# PLAN DE NETTOYAGE - Emergence V8
**Date:** 2025-10-10
**Basé sur:** AUDIT_COMPLET_EMERGENCE_V8_20251010.md

---

## ÉTAPE 1 : SUPPRESSION IMMÉDIATE (~13 Mo)

### A. Logs obsolètes

```bash
# Racine
rm backend-uvicorn.log backend_server.log backend_server.err.log
rm backend.log backend.err.log backend_start.log backend_start.err.log
rm backend_dev_8001.out.log backend_dev_8001.err.log

# /tmp
rm tmp/*.log

# Fichiers temporaires racine
rm body.json id_token.txt placeholder.tmp
```

### B. Arborescences anciennes (garder seulement 20251008)

```bash
rm arborescence_synchronisee_20251003.txt
rm arborescence_synchronisee_20251004.txt
# GARDER: arborescence_synchronisee_20251008.txt
```

### C. OpenAPI dupliqués (garder seulement openapi.json)

```bash
rm openapi_canary.json openapi.custom.json openapi.run.json
# GARDER: openapi.json
```

### D. Scripts tmp temporaires one-shot

```bash
cd tmp
rm apply_api_patch.py patch_api_client_clean.py patch_websocket.py websocket.patch
rm rewrite_api_utf8.py remove_bom.py update_docstring.py update_decay.py
rm clean_logs.py update_memory_doc.py update_table.py fix_row.py normalize_row.py
rm fix_init.py insert_row.py smoke_doc.txt table_snippet.txt table_repr.txt
rm doc_repr.txt voice_service_lines.txt dispatcher_lines.txt debate_lines.txt
rm head_chat.js app.js docker-tag.txt health_response.json codex_backend.pid
```

### E. tmp_tests anciens

```bash
rm -rf tmp_tests/
```

### F. __pycache__ (régénérables)

```bash
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
python -Bc "import pathlib; [p.unlink() for p in pathlib.Path('.').rglob('*.pyc')]"
```

---

## ÉTAPE 2 : ARCHIVAGE (créer docs/archive/)

### A. Créer structure archive

```bash
mkdir -p docs/archive/prompts
mkdir -p docs/archive/sessions
mkdir -p docs/archive/reports
```

### B. Archiver prompts obsolètes

```bash
# Prompts de phases terminées
mv PROMPT_COCKPIT_DEBUG_IMPLEMENTATION.md docs/archive/prompts/
mv PROMPT_COCKPIT_NEXT_FEATURES.md docs/archive/prompts/
mv PROMPT_CODEX_DEPLOY_P1.md docs/archive/prompts/
mv PROMPT_CODEX_DEPLOY_PHASE3.md docs/archive/prompts/
mv PROMPT_CODEX_ENABLE_METRICS.md docs/archive/prompts/
mv PROMPT_DEBUG_COCKPIT_METRICS.md docs/archive/prompts/
mv PROMPT_P1_MEMORY_ENRICHMENT.md docs/archive/prompts/
mv PROMPT_VALIDATION_PHASE2.md docs/archive/prompts/
mv PROMPT_FIX_PREFERENCE_EXTRACTOR_CRITICAL.md docs/archive/prompts/  # Bug résolu

# Prompts actifs à GARDER
# PROMPT_NEXT_SESSION.md ✅
# PROMPT_DOCKER_BUILD_DEPLOY.md ✅
# PROMPT_NEXT_SESSION_MEMORY_P2.md ✅
# PROMPT_NEXT_SESSION_SPRINT_P3_FRONTEND.md ✅
```

### C. Archiver sessions récapitulatives

```bash
mv SESSION_HOTFIX_P1_3_RECAP.txt docs/archive/sessions/
mv SESSION_P0_RECAP.txt docs/archive/sessions/
mv SESSION_P1_2_RECAP.txt docs/archive/sessions/
mv SESSION_P1_RECAP.txt docs/archive/sessions/
mv SESSION_P1_VALIDATION_PREP.md docs/archive/sessions/
mv SESSION_P1_VALIDATION_RESULTS.md docs/archive/sessions/
mv SESSION_SUMMARY_20251009.md docs/archive/sessions/
```

### D. Archiver rapports terminés

```bash
mv SYNC_REPORT.md docs/archive/reports/
mv TESTS_VALIDATION_REPORT.md docs/archive/reports/
mv TEST_E2E_HOTFIX_P1_3.md docs/archive/reports/
mv VALIDATION_P1_INSTRUCTIONS.md docs/archive/reports/
mv README_AUDIT_IMPORTS.md docs/archive/reports/
```

### E. Archiver PR_DESCRIPTION.md (obsolète)

```bash
mv PR_DESCRIPTION.md docs/archive/reports/pr-description-20251005.md
```

### F. Archiver fichiers implementation terminés

```bash
mv PRODGUARDIAN_IMPLEMENTATION.md docs/archive/reports/
```

---

## ÉTAPE 3 : SUPPRESSION APRÈS VALIDATION

**⚠️ VALIDER AVANT SUPPRESSION**

### A. Database temporaire test

```bash
# Si tests auth terminés et base production stable
rm tmp-auth.db  # 124 Ko
```

### B. Fichiers QA obsolètes

```bash
# Si qa-p1 terminé et validé
rm qa-p1-baseline.json
rm qa_metrics_validation.py
```

### C. sync-dashboard.html

```bash
# Si tableau de bord synchronisation non utilisé
rm sync-dashboard.html
```

---

## ÉTAPE 4 : FICHIERS À CONSERVER (NE PAS TOUCHER)

### Documentation active

✅ `README.md` - Point d'entrée principal
✅ `CODEV_PROTOCOL.md` - Protocole collaboration agents
✅ `AGENTS.md` - Consignes agents
✅ `CODex_GUIDE.md` - Guide Codex
✅ `TESTING.md` - Guide tests
✅ `AUDIT_COMPLET_EMERGENCE_V8_20251010.md` - **Nouveau rapport audit**
✅ `HANDOFF_NEXT_SESSION.txt` - Passation courante

### Prompts actifs

✅ `PROMPT_NEXT_SESSION.md`
✅ `PROMPT_DOCKER_BUILD_DEPLOY.md`
✅ `PROMPT_NEXT_SESSION_MEMORY_P2.md`
✅ `PROMPT_NEXT_SESSION_SPRINT_P3_FRONTEND.md`

### Documentation docs/

✅ `docs/passation.md` - Journal inter-agents
✅ `docs/Memoire.md` - Documentation mémoire
✅ `docs/architecture/` - Architecture C4
✅ `docs/MEMORY_CAPABILITIES.md`
✅ `docs/MONITORING_GUIDE.md`

### Configuration

✅ `requirements.txt`
✅ `package.json`
✅ `pytest.ini`
✅ `vite.config.js`
✅ `run-local.ps1`

---

## RÉSUMÉ GAINS

| Catégorie | Fichiers | Taille | Action |
|-----------|----------|--------|--------|
| **Logs obsolètes** | ~15 | 130 Ko | Suppression |
| **Arborescences anciennes** | 2 | 10.5 Mo | Suppression |
| **OpenAPI dupliqués** | 3 | 85 Ko | Suppression |
| **Scripts tmp** | ~30 | 180 Ko | Suppression |
| **__pycache__** | ~160 | 2 Mo | Suppression |
| **tmp_tests** | ~20 | 90 Ko | Suppression |
| **Fichiers racine tmp** | 3 | 1 Ko | Suppression |
| **TOTAL SUPPRESSION** | **~230** | **~13 Mo** | ✅ |
| **Prompts obsolètes** | 9 | 250 Ko | Archivage |
| **Sessions recap** | 7 | 60 Ko | Archivage |
| **Rapports terminés** | 6 | 60 Ko | Archivage |
| **TOTAL ARCHIVAGE** | **22** | **~370 Ko** | 📦 |

**Gain total:** ~13.4 Mo + meilleure organisation

---

## COMMANDES COMPLÈTES POUR EXÉCUTION

### Script de nettoyage complet

```bash
#!/bin/bash
# cleanup.sh - Nettoyage Emergence V8

echo "🧹 Nettoyage Emergence V8 - Étape 1: Suppression immédiate"

# A. Logs obsolètes
echo "  Suppression logs..."
rm -f backend-uvicorn.log backend_server.log backend_server.err.log
rm -f backend.log backend.err.log backend_start.log backend_start.err.log
rm -f backend_dev_8001.out.log backend_dev_8001.err.log
rm -f tmp/*.log
rm -f body.json id_token.txt placeholder.tmp

# B. Arborescences anciennes
echo "  Suppression arborescences anciennes..."
rm -f arborescence_synchronisee_20251003.txt
rm -f arborescence_synchronisee_20251004.txt

# C. OpenAPI dupliqués
echo "  Suppression OpenAPI dupliqués..."
rm -f openapi_canary.json openapi.custom.json openapi.run.json

# D. Scripts tmp
echo "  Suppression scripts tmp..."
cd tmp 2>/dev/null && {
    rm -f apply_api_patch.py patch_api_client_clean.py patch_websocket.py websocket.patch
    rm -f rewrite_api_utf8.py remove_bom.py update_docstring.py update_decay.py
    rm -f clean_logs.py update_memory_doc.py update_table.py fix_row.py normalize_row.py
    rm -f fix_init.py insert_row.py smoke_doc.txt table_snippet.txt table_repr.txt
    rm -f doc_repr.txt voice_service_lines.txt dispatcher_lines.txt debate_lines.txt
    rm -f head_chat.js app.js docker-tag.txt health_response.json codex_backend.pid
    cd ..
}

# E. tmp_tests
echo "  Suppression tmp_tests..."
rm -rf tmp_tests/

# F. __pycache__
echo "  Suppression __pycache__..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
python -Bc "import pathlib; [p.unlink() for p in pathlib.Path('.').rglob('*.pyc')]" 2>/dev/null || true

echo "✅ Étape 1 terminée (~13 Mo libérés)"
echo ""
echo "📦 Étape 2: Archivage"

# Créer structure archive
mkdir -p docs/archive/prompts
mkdir -p docs/archive/sessions
mkdir -p docs/archive/reports

# Archiver prompts
echo "  Archivage prompts..."
mv PROMPT_COCKPIT_DEBUG_IMPLEMENTATION.md docs/archive/prompts/ 2>/dev/null || true
mv PROMPT_COCKPIT_NEXT_FEATURES.md docs/archive/prompts/ 2>/dev/null || true
mv PROMPT_CODEX_DEPLOY_P1.md docs/archive/prompts/ 2>/dev/null || true
mv PROMPT_CODEX_DEPLOY_PHASE3.md docs/archive/prompts/ 2>/dev/null || true
mv PROMPT_CODEX_ENABLE_METRICS.md docs/archive/prompts/ 2>/dev/null || true
mv PROMPT_DEBUG_COCKPIT_METRICS.md docs/archive/prompts/ 2>/dev/null || true
mv PROMPT_P1_MEMORY_ENRICHMENT.md docs/archive/prompts/ 2>/dev/null || true
mv PROMPT_VALIDATION_PHASE2.md docs/archive/prompts/ 2>/dev/null || true
mv PROMPT_FIX_PREFERENCE_EXTRACTOR_CRITICAL.md docs/archive/prompts/ 2>/dev/null || true

# Archiver sessions
echo "  Archivage sessions..."
mv SESSION_HOTFIX_P1_3_RECAP.txt docs/archive/sessions/ 2>/dev/null || true
mv SESSION_P0_RECAP.txt docs/archive/sessions/ 2>/dev/null || true
mv SESSION_P1_2_RECAP.txt docs/archive/sessions/ 2>/dev/null || true
mv SESSION_P1_RECAP.txt docs/archive/sessions/ 2>/dev/null || true
mv SESSION_P1_VALIDATION_PREP.md docs/archive/sessions/ 2>/dev/null || true
mv SESSION_P1_VALIDATION_RESULTS.md docs/archive/sessions/ 2>/dev/null || true
mv SESSION_SUMMARY_20251009.md docs/archive/sessions/ 2>/dev/null || true

# Archiver rapports
echo "  Archivage rapports..."
mv SYNC_REPORT.md docs/archive/reports/ 2>/dev/null || true
mv TESTS_VALIDATION_REPORT.md docs/archive/reports/ 2>/dev/null || true
mv TEST_E2E_HOTFIX_P1_3.md docs/archive/reports/ 2>/dev/null || true
mv VALIDATION_P1_INSTRUCTIONS.md docs/archive/reports/ 2>/dev/null || true
mv README_AUDIT_IMPORTS.md docs/archive/reports/ 2>/dev/null || true
mv PR_DESCRIPTION.md docs/archive/reports/pr-description-20251005.md 2>/dev/null || true
mv PRODGUARDIAN_IMPLEMENTATION.md docs/archive/reports/ 2>/dev/null || true

echo "✅ Étape 2 terminée (22 fichiers archivés)"
echo ""
echo "🎉 Nettoyage terminé!"
echo "   - ~13 Mo libérés"
echo "   - 22 fichiers archivés dans docs/archive/"
echo "   - Structure projet nettoyée et organisée"
```

### Exécution

```bash
# Rendre exécutable
chmod +x cleanup.sh

# Exécuter
./cleanup.sh

# Vérifier résultats
git status
```

---

## VALIDATION POST-NETTOYAGE

### Checklist

- [ ] Tous les logs supprimés
- [ ] Arborescences anciennes supprimées (garder 20251008)
- [ ] OpenAPI dupliqués supprimés (garder openapi.json)
- [ ] Scripts tmp supprimés
- [ ] __pycache__ supprimés
- [ ] Structure docs/archive/ créée
- [ ] 9 prompts archivés
- [ ] 7 sessions archivées
- [ ] 6 rapports archivés
- [ ] README.md mis à jour avec référence audit
- [ ] docs/architecture/ mis à jour
- [ ] Tests passent encore (`pytest`, `npm run build`)
- [ ] Git status propre (sauf fichiers à committer)

### Commandes de validation

```bash
# Vérifier structure archive
ls -R docs/archive/

# Vérifier prompts actifs restants
ls PROMPT_*.md

# Vérifier taille projet
du -sh .

# Vérifier tests
npm run build
pytest tests/backend/features/ -v

# Vérifier git
git status
```

---

**Rapport généré le:** 2025-10-10
**Basé sur:** AUDIT_COMPLET_EMERGENCE_V8_20251010.md
**Gain attendu:** ~13.4 Mo + meilleure organisation
