#!/bin/bash
# cleanup.sh - Nettoyage Emergence V8
# Basé sur: CLEANUP_PLAN_20251010.md

set -e  # Arrêter en cas d'erreur

echo "🧹 Nettoyage Emergence V8"
echo "=========================="
echo ""

# Compteurs
deleted_files=0
deleted_size=0
archived_files=0

echo "📋 Étape 1: Suppression immédiate"
echo "----------------------------------"

# A. Logs obsolètes
echo "  Suppression logs racine..."
for file in backend-uvicorn.log backend_server.log backend_server.err.log backend.log backend.err.log backend_start.log backend_start.err.log backend_dev_8001.out.log backend_dev_8001.err.log body.json id_token.txt placeholder.tmp; do
    if [ -f "$file" ]; then
        rm -f "$file" && echo "    ✓ $file" && ((deleted_files++))
    fi
done

echo "  Suppression logs tmp/..."
if [ -d "tmp" ]; then
    rm -f tmp/*.log 2>/dev/null || true
    echo "    ✓ tmp/*.log"
fi

# B. Arborescences anciennes
echo "  Suppression arborescences anciennes..."
for file in arborescence_synchronisee_20251003.txt arborescence_synchronisee_20251004.txt; do
    if [ -f "$file" ]; then
        size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null || echo "0")
        rm -f "$file" && echo "    ✓ $file ($(numfmt --to=iec $size 2>/dev/null || echo "$size bytes"))" && ((deleted_files++))
        deleted_size=$((deleted_size + size))
    fi
done

# C. OpenAPI dupliqués
echo "  Suppression OpenAPI dupliqués..."
for file in openapi_canary.json openapi.custom.json openapi.run.json; do
    if [ -f "$file" ]; then
        rm -f "$file" && echo "    ✓ $file" && ((deleted_files++))
    fi
done

# D. Scripts tmp
echo "  Suppression scripts tmp/..."
if [ -d "tmp" ]; then
    cd tmp 2>/dev/null && {
        for file in apply_api_patch.py patch_api_client_clean.py patch_websocket.py websocket.patch rewrite_api_utf8.py remove_bom.py update_docstring.py update_decay.py clean_logs.py update_memory_doc.py update_table.py fix_row.py normalize_row.py fix_init.py insert_row.py smoke_doc.txt table_snippet.txt table_repr.txt doc_repr.txt voice_service_lines.txt dispatcher_lines.txt debate_lines.txt head_chat.js app.js docker-tag.txt health_response.json codex_backend.pid; do
            if [ -f "$file" ]; then
                rm -f "$file" && ((deleted_files++))
            fi
        done
        echo "    ✓ Scripts temporaires supprimés"
        cd ..
    }
fi

# E. tmp_tests
echo "  Suppression tmp_tests/..."
if [ -d "tmp_tests" ]; then
    rm -rf tmp_tests/ && echo "    ✓ tmp_tests/" && ((deleted_files++))
fi

# F. __pycache__
echo "  Suppression __pycache__/..."
pycache_count=$(find . -type d -name "__pycache__" 2>/dev/null | wc -l)
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
echo "    ✓ $pycache_count dossiers __pycache__ supprimés"

# Suppression .pyc
pyc_count=$(find . -name "*.pyc" 2>/dev/null | wc -l)
find . -name "*.pyc" -delete 2>/dev/null || true
echo "    ✓ $pyc_count fichiers .pyc supprimés"

echo ""
echo "✅ Étape 1 terminée: $deleted_files fichiers supprimés"
echo ""

echo "📦 Étape 2: Archivage"
echo "---------------------"

# Créer structure archive
mkdir -p docs/archive/prompts
mkdir -p docs/archive/sessions
mkdir -p docs/archive/reports

# Archiver prompts
echo "  Archivage prompts..."
for file in PROMPT_COCKPIT_DEBUG_IMPLEMENTATION.md PROMPT_COCKPIT_NEXT_FEATURES.md PROMPT_CODEX_DEPLOY_P1.md PROMPT_CODEX_DEPLOY_PHASE3.md PROMPT_CODEX_ENABLE_METRICS.md PROMPT_DEBUG_COCKPIT_METRICS.md PROMPT_P1_MEMORY_ENRICHMENT.md PROMPT_VALIDATION_PHASE2.md PROMPT_FIX_PREFERENCE_EXTRACTOR_CRITICAL.md; do
    if [ -f "$file" ]; then
        mv "$file" docs/archive/prompts/ && echo "    ✓ $file → docs/archive/prompts/" && ((archived_files++))
    fi
done

# Archiver sessions
echo "  Archivage sessions..."
for file in SESSION_HOTFIX_P1_3_RECAP.txt SESSION_P0_RECAP.txt SESSION_P1_2_RECAP.txt SESSION_P1_RECAP.txt SESSION_P1_VALIDATION_PREP.md SESSION_P1_VALIDATION_RESULTS.md SESSION_SUMMARY_20251009.md; do
    if [ -f "$file" ]; then
        mv "$file" docs/archive/sessions/ && echo "    ✓ $file → docs/archive/sessions/" && ((archived_files++))
    fi
done

# Archiver rapports
echo "  Archivage rapports..."
for file in SYNC_REPORT.md TESTS_VALIDATION_REPORT.md TEST_E2E_HOTFIX_P1_3.md VALIDATION_P1_INSTRUCTIONS.md README_AUDIT_IMPORTS.md PRODGUARDIAN_IMPLEMENTATION.md; do
    if [ -f "$file" ]; then
        mv "$file" docs/archive/reports/ && echo "    ✓ $file → docs/archive/reports/" && ((archived_files++))
    fi
done

# Archiver PR_DESCRIPTION.md
if [ -f "PR_DESCRIPTION.md" ]; then
    mv PR_DESCRIPTION.md docs/archive/reports/pr-description-20251005.md && echo "    ✓ PR_DESCRIPTION.md → docs/archive/reports/pr-description-20251005.md" && ((archived_files++))
fi

echo ""
echo "✅ Étape 2 terminée: $archived_files fichiers archivés"
echo ""

echo "🎉 Nettoyage terminé!"
echo "===================="
echo "  Fichiers supprimés: $deleted_files"
echo "  Fichiers archivés: $archived_files"
echo "  Structure docs/archive/ créée"
echo ""
echo "📝 Prochaines étapes:"
echo "  1. Vérifier avec: git status"
echo "  2. Tester build: npm run build"
echo "  3. Tester tests: pytest tests/backend/features/ -v"
echo "  4. Committer si OK: git add -A && git commit -m \"chore: cleanup obsolete files + archive (~13 Mo)\""
