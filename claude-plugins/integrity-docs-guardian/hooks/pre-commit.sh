#!/bin/bash
# Hook Pre-Commit pour ÉMERGENCE Integrity & Docs Guardian
# Validation rapide pour éviter les commits avec des gaps de doc évidents

set -e

PLUGIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPTS_DIR="$PLUGIN_DIR/scripts"

echo "🔍 ÉMERGENCE Guardian d'Intégrité: Check Pre-Commit"
echo "===================================================="
echo ""

# Récup les fichiers staged
STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACM)

if [ -z "$STAGED_FILES" ]; then
    echo "ℹ️  Aucun fichier staged détecté"
    exit 0
fi

echo "📝 Fichiers staged:"
echo "$STAGED_FILES" | sed 's/^/   - /'
echo ""

# Vérifs rapides
WARNINGS=0

# Check 1: Les nouveaux fichiers .py devraient avoir des tests
echo "🧪 [1/3] Vérif de la couverture de tests..."
NEW_PY_FILES=$(echo "$STAGED_FILES" | grep '\.py$' | grep -v '^tests/' | grep -v '__pycache__' || true)
if [ -n "$NEW_PY_FILES" ]; then
    for file in $NEW_PY_FILES; do
        # Check if it's a new file (not just modified)
        if ! git diff --cached --diff-filter=A --name-only | grep -q "$file"; then
            continue
        fi

        # Extrait le nom du module et check le test correspondant
        module_name=$(basename "$file" .py)
        if ! find tests -name "test_${module_name}.py" -o -name "test_*${module_name}*.py" 2>/dev/null | grep -q .; then
            echo "   ⚠️  Pas de fichier de test trouvé pour le nouveau module: $file"
            WARNINGS=$((WARNINGS + 1))
        fi
    done
fi
echo "   ✅ Check de couverture de tests terminé"
echo ""

# Check 2: Les changements d'endpoint API devraient avoir des mises à jour OpenAPI
echo "🔌 [2/3] Vérif de la doc des endpoints API..."
ROUTER_FILES=$(echo "$STAGED_FILES" | grep 'routers/.*\.py$' || true)
if [ -n "$ROUTER_FILES" ]; then
    # Check si openapi.json est aussi staged
    if ! echo "$STAGED_FILES" | grep -q 'openapi.json'; then
        echo "   ⚠️  Fichiers router modifiés mais openapi.json pas staged"
        echo "      Pense à régénérer le schéma OpenAPI"
        WARNINGS=$((WARNINGS + 1))
    fi
fi
echo "   ✅ Check de doc API terminé"
echo ""

# Check 3: Les changements de composants frontend devraient avoir des mises à jour de types
echo "🎨 [3/3] Vérif des définitions de types frontend..."
COMPONENT_FILES=$(echo "$STAGED_FILES" | grep -E '\.(jsx|tsx)$' || true)
if [ -n "$COMPONENT_FILES" ]; then
    # Heuristique simple - peut être améliorée
    echo "   ℹ️  Composants frontend modifiés - assure-toi que les types sont à jour"
fi
echo "   ✅ Check des définitions de types terminé"
echo ""

# Résumé
echo "===================================================="
if [ $WARNINGS -eq 0 ]; then
    echo "✅ Validation pre-commit passée!"
    echo ""
    exit 0
else
    echo "⚠️  Validation pre-commit terminée avec $WARNINGS warning(s)"
    echo ""
    echo "Tu peux quand même commit, mais pense à adresser les warnings ci-dessus."
    echo "Pour bypass ce check, utilise: git commit --no-verify"
    echo ""

    # Bloque pas le commit, juste un warning
    # Pour bloquer, change le exit code à 1
    exit 0
fi
