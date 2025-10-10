#!/bin/bash
# Hook Post-Commit pour ÉMERGENCE Integrity & Docs Guardian
# Déclenche Anima (DocKeeper) et Neo (IntegrityWatcher) après chaque commit

set -e

# Remonter à la racine du repo et aller au plugin
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PLUGIN_DIR="$REPO_ROOT/claude-plugins/integrity-docs-guardian"
REPORTS_DIR="$PLUGIN_DIR/reports"
SCRIPTS_DIR="$PLUGIN_DIR/scripts"

echo "🔍 ÉMERGENCE Guardian d'Intégrité: Vérification Post-Commit"
echo "============================================================="
echo ""

# Assure que le dossier reports existe
mkdir -p "$REPORTS_DIR"

# Info du commit
COMMIT_HASH=$(git rev-parse HEAD)
COMMIT_MSG=$(git log -1 --pretty=%B)
echo "📝 Commit: $COMMIT_HASH"
echo "   Message: $COMMIT_MSG"
echo ""

# Étape 1: Lancer Anima (DocKeeper) - Vérification documentation
echo "📚 [1/3] Lancement d'Anima (DocKeeper)..."
if command -v python &> /dev/null; then
    python "$SCRIPTS_DIR/scan_docs.py"
    if [ $? -eq 0 ]; then
        echo "   ✅ Anima terminé avec succès"
    else
        echo "   ⚠️  Anima a détecté des problèmes (voir reports/docs_report.json)"
    fi
else
    echo "   ⚠️  Python introuvable, Anima skip"
fi
echo ""

# Étape 2: Lancer Neo (IntegrityWatcher) - Vérification intégrité
echo "🔐 [2/3] Lancement de Neo (IntegrityWatcher)..."
if command -v python &> /dev/null; then
    python "$SCRIPTS_DIR/check_integrity.py"
    if [ $? -eq 0 ]; then
        echo "   ✅ Neo terminé avec succès"
    else
        echo "   ⚠️  Neo a détecté des problèmes (voir reports/integrity_report.json)"
    fi
else
    echo "   ⚠️  Python introuvable, Neo skip"
fi
echo ""

# Étape 3: Lancer Nexus (Coordinator) - Génération rapport unifié
echo "🎯 [3/3] Lancement de Nexus (Coordinator)..."
if command -v python &> /dev/null && [ -f "$SCRIPTS_DIR/generate_report.py" ]; then
    python "$SCRIPTS_DIR/generate_report.py"
    if [ $? -eq 0 ]; then
        echo "   ✅ Nexus terminé avec succès"
        echo ""
        echo "📊 Rapports disponibles:"
        echo "   - Anima:  $REPORTS_DIR/docs_report.json"
        echo "   - Neo:    $REPORTS_DIR/integrity_report.json"
        echo "   - Nexus:  $REPORTS_DIR/unified_report.json"
    else
        echo "   ⚠️  Nexus a planté"
    fi
else
    echo "   ℹ️  Nexus pas dispo (lance scripts/generate_report.py manuellement)"
fi

echo ""
echo "============================================================="
echo "✅ Vérification Guardian d'Intégrité terminée!"
echo ""

# Optionnel: Afficher le résumé si dispo
if [ -f "$REPORTS_DIR/unified_report.json" ]; then
    echo "📋 Résumé Rapide:"
    if command -v jq &> /dev/null; then
        jq -r '.executive_summary.headline' "$REPORTS_DIR/unified_report.json" 2>/dev/null || echo "   (jq pas dispo pour parser le JSON)"
    else
        echo "   (installe 'jq' pour un résumé formaté)"
    fi
fi
