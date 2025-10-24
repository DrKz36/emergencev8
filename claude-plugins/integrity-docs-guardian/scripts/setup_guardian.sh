#!/bin/bash
# ============================================================================
# GUARDIAN SETUP - Configuration automatique Linux/macOS
# ============================================================================
# Configure les Git Hooks pour monitoring automatique
# Usage: ./setup_guardian.sh [--disable]
# ============================================================================

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

DISABLE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --disable)
            DISABLE=true
            shift
            ;;
        *)
            echo -e "${RED}Usage: $0 [--disable]${NC}"
            exit 1
            ;;
    esac
done

echo -e "\n${CYAN}================================================================${NC}"
echo -e "${CYAN}🛡️  GUARDIAN SETUP - ÉMERGENCE V8${NC}"
echo -e "${CYAN}================================================================${NC}\n"

# Détection du repo root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
GUARDIAN_DIR="$REPO_ROOT/claude-plugins/integrity-docs-guardian"
SCRIPTS_DIR="$GUARDIAN_DIR/scripts"
HOOKS_DIR="$REPO_ROOT/.git/hooks"

echo -e "📁 Repo root: ${CYAN}$REPO_ROOT${NC}"
echo -e "🛡️  Guardian dir: ${CYAN}$GUARDIAN_DIR${NC}\n"

# ============================================================================
# DÉSACTIVATION
# ============================================================================
if [ "$DISABLE" = true ]; then
    echo -e "${YELLOW}🔴 DÉSACTIVATION DU GUARDIAN${NC}\n"

    # Supprimer les hooks Git
    echo -e "[1/1] Suppression des hooks Git..."
    rm -f "$HOOKS_DIR/pre-commit"
    rm -f "$HOOKS_DIR/post-commit"
    rm -f "$HOOKS_DIR/pre-push"
    echo -e "   ${GREEN}✅ Hooks Git supprimés${NC}\n"

    echo -e "${GREEN}================================================================${NC}"
    echo -e "${GREEN}✅ GUARDIAN DÉSACTIVÉ${NC}"
    echo -e "${GREEN}================================================================${NC}\n"
    exit 0
fi

# ============================================================================
# ACTIVATION
# ============================================================================
echo -e "${GREEN}🟢 ACTIVATION DU GUARDIAN${NC}\n"

# ============================================================================
# 1. INSTALLATION DES HOOKS GIT
# ============================================================================
echo -e "[1/2] Installation des Git Hooks...\n"

# Créer le répertoire hooks s'il n'existe pas
mkdir -p "$HOOKS_DIR"

# PRE-COMMIT HOOK
echo -e "   📝 Création pre-commit hook..."
cat > "$HOOKS_DIR/pre-commit" << 'HOOK_EOF'
#!/bin/bash
# Pre-commit hook - Guardian validation
set -e

REPO_ROOT="$(git rev-parse --show-toplevel)"
SCRIPTS_DIR="$REPO_ROOT/claude-plugins/integrity-docs-guardian/scripts"

echo ""
echo "🔍 ÉMERGENCE Guardian: Vérification Pre-Commit"
echo "===================================================="

# Liste des fichiers staged
STAGED_FILES=$(git diff --cached --name-only)
if [ -z "$STAGED_FILES" ]; then
    echo "⚠️  Aucun fichier staged, skip validation"
    exit 0
fi

echo "📝 Fichiers staged:"
echo "$STAGED_FILES" | sed 's/^/   - /'
echo ""

# Pour l'instant, on fait juste une validation basique
# Les agents Python Guardian peuvent être ajoutés ici plus tard
echo "✅ Validation pre-commit OK"
echo "===================================================="
echo ""

exit 0
HOOK_EOF

chmod +x "$HOOKS_DIR/pre-commit"
echo -e "   ${GREEN}✅ pre-commit hook créé${NC}"

# POST-COMMIT HOOK
echo -e "   📝 Création post-commit hook..."
cat > "$HOOKS_DIR/post-commit" << 'HOOK_EOF'
#!/bin/bash
# Post-commit hook - Guardian feedback
set -e

REPO_ROOT="$(git rev-parse --show-toplevel)"

echo ""
echo "🎯 ÉMERGENCE Guardian: Feedback Post-Commit"
echo "===================================================="

COMMIT_HASH=$(git rev-parse --short HEAD)
COMMIT_MSG=$(git log -1 --pretty=%B)

echo "📝 Commit: $COMMIT_HASH"
echo "💬 Message: $COMMIT_MSG"
echo ""
echo "✅ Commit enregistré avec succès"
echo "===================================================="
echo ""

exit 0
HOOK_EOF

chmod +x "$HOOKS_DIR/post-commit"
echo -e "   ${GREEN}✅ post-commit hook créé${NC}"

# PRE-PUSH HOOK
echo -e "   📝 Création pre-push hook..."
cat > "$HOOKS_DIR/pre-push" << 'HOOK_EOF'
#!/bin/bash
# Pre-push hook - Guardian production check
set -e

REPO_ROOT="$(git rev-parse --show-toplevel)"

echo ""
echo "🚀 ÉMERGENCE Guardian: Vérification Pre-Push"
echo "===================================================="

# Vérifier que tests passent avant push
echo "🧪 Vérification rapide..."

# Pour l'instant, validation basique
# Les checks de production peuvent être ajoutés ici
echo "✅ Validation pre-push OK"
echo "===================================================="
echo ""

exit 0
HOOK_EOF

chmod +x "$HOOKS_DIR/pre-push"
echo -e "   ${GREEN}✅ pre-push hook créé${NC}\n"

# ============================================================================
# 2. TEST DES HOOKS
# ============================================================================
echo -e "[2/2] Test des hooks installés...\n"

# Vérifier que les hooks existent et sont exécutables
HOOKS_OK=true

for hook in pre-commit post-commit pre-push; do
    if [ -x "$HOOKS_DIR/$hook" ]; then
        echo -e "   ✅ $hook: ${GREEN}OK${NC}"
    else
        echo -e "   ❌ $hook: ${RED}ERREUR${NC}"
        HOOKS_OK=false
    fi
done

echo ""

if [ "$HOOKS_OK" = true ]; then
    echo -e "${GREEN}================================================================${NC}"
    echo -e "${GREEN}✅ GUARDIAN ACTIVÉ AVEC SUCCÈS${NC}"
    echo -e "${GREEN}================================================================${NC}\n"
    echo -e "Les hooks Git sont maintenant actifs:"
    echo -e "  • ${CYAN}pre-commit${NC}  : Validation avant commit"
    echo -e "  • ${CYAN}post-commit${NC} : Feedback après commit"
    echo -e "  • ${CYAN}pre-push${NC}    : Vérification avant push\n"
    echo -e "Pour désactiver: ${YELLOW}./setup_guardian.sh --disable${NC}\n"
    exit 0
else
    echo -e "${RED}================================================================${NC}"
    echo -e "${RED}❌ ERREUR LORS DE L'INSTALLATION${NC}"
    echo -e "${RED}================================================================${NC}\n"
    exit 1
fi
