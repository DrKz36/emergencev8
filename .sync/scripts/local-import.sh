#!/bin/bash
# Script d'import pour Agent Local (Claude Code)
# Applique un patch reçu de GPT Codex Cloud et synchronise avec GitHub

set -e

# Configuration
SYNC_DIR="${SYNC_DIR:-.sync}"
PATCH_DIR="$SYNC_DIR/patches"
LOG_DIR="$SYNC_DIR/logs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Couleurs pour output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonction d'affichage
log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✓ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }

# Vérifier argument
if [ $# -eq 0 ]; then
    log_error "Usage: $0 <patch_name>"
    echo "Exemple: $0 sync_cloud_20251010_123456.patch"
    echo ""
    echo "Patches disponibles:"
    ls -1 "$PATCH_DIR"/*.patch 2>/dev/null || echo "  Aucun patch trouvé"
    exit 1
fi

PATCH_NAME="$1"
PATCH_PATH="$PATCH_DIR/$PATCH_NAME"
METADATA_NAME="${PATCH_NAME%.patch}.json"
METADATA_PATH="$PATCH_DIR/$METADATA_NAME"

echo "=== Agent Local (Claude Code) - Import Synchronisation ==="
echo "Timestamp: $TIMESTAMP"
echo "Patch: $PATCH_NAME"
echo ""

# 1. Vérifications préliminaires
log_info "[1/8] Vérifications préliminaires..."

if [ ! -f "$PATCH_PATH" ]; then
    log_error "Patch introuvable: $PATCH_PATH"
    exit 1
fi
log_success "Patch trouvé"

if [ ! -f "$METADATA_PATH" ]; then
    log_warning "Métadonnées introuvables: $METADATA_PATH"
    HAS_METADATA=false
else
    log_success "Métadonnées trouvées"
    HAS_METADATA=true
fi

# Vérifier qu'on est dans un dépôt Git
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    log_error "Pas dans un dépôt Git"
    exit 1
fi
log_success "Dépôt Git détecté"

# 2. Afficher métadonnées si disponibles
if [ "$HAS_METADATA" = true ]; then
    log_info "[2/8] Lecture métadonnées..."
    if command -v jq >/dev/null 2>&1; then
        echo "Agent source: $(jq -r '.agent' "$METADATA_PATH")"
        echo "Date export: $(jq -r '.export_date' "$METADATA_PATH")"
        echo "Branche: $(jq -r '.git.branch' "$METADATA_PATH")"
        echo "Type: $(jq -r '.patch.type' "$METADATA_PATH")"
        echo "Fichiers modifiés: $(jq -r '.patch.modified_files' "$METADATA_PATH")"
    else
        log_warning "jq non installé, affichage métadonnées brut:"
        cat "$METADATA_PATH"
    fi
else
    log_info "[2/8] Pas de métadonnées disponibles"
fi
echo ""

# 3. Vérifier l'état Git local
log_info "[3/8] Vérification état Git local..."
if ! git diff-index --quiet HEAD -- 2>/dev/null; then
    log_warning "Working tree contient des modifications non commitées"
    echo "Voulez-vous continuer? (y/N)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        log_error "Import annulé par l'utilisateur"
        exit 1
    fi
else
    log_success "Working tree propre"
fi

CURRENT_BRANCH=$(git branch --show-current)
log_success "Branche courante: $CURRENT_BRANCH"

# 4. Créer une branche de sécurité
log_info "[4/8] Création branche de sécurité..."
BACKUP_BRANCH="backup/before-sync-${TIMESTAMP}"
git branch "$BACKUP_BRANCH" 2>/dev/null || log_warning "Impossible de créer branche backup"
log_success "Branche backup créée: $BACKUP_BRANCH"

# 5. Appliquer le patch
log_info "[5/8] Application du patch..."
PATCH_SIZE=$(wc -c < "$PATCH_PATH")

if [ "$PATCH_SIZE" -eq 0 ]; then
    log_warning "Le patch est vide (aucune modification)"
    PATCH_APPLIED=false
else
    # Essayer d'abord git apply
    if git apply --check "$PATCH_PATH" 2>/dev/null; then
        git apply "$PATCH_PATH"
        PATCH_APPLIED=true
        PATCH_METHOD="git apply"
        log_success "Patch appliqué avec git apply"
    # Sinon essayer git am
    elif git am --check "$PATCH_PATH" 2>/dev/null; then
        git am "$PATCH_PATH"
        PATCH_APPLIED=true
        PATCH_METHOD="git am"
        log_success "Patch appliqué avec git am"
    else
        log_error "Impossible d'appliquer le patch"
        log_info "Essai de réparation..."

        # Essayer avec --3way
        if git apply --3way "$PATCH_PATH" 2>/dev/null; then
            PATCH_APPLIED=true
            PATCH_METHOD="git apply --3way"
            log_success "Patch appliqué avec résolution 3-way"
        else
            log_error "Échec de l'application du patch"
            log_info "Restauration de l'état précédent..."
            git checkout "$BACKUP_BRANCH"
            exit 1
        fi
    fi
fi

# 6. Vérifier les modifications
log_info "[6/8] Vérification des modifications..."
MODIFIED_FILES=$(git diff --name-only | wc -l)
echo "Fichiers modifiés: $MODIFIED_FILES"

if [ "$MODIFIED_FILES" -gt 0 ]; then
    echo ""
    echo "Fichiers modifiés:"
    git diff --name-status | head -20
    if [ "$(git diff --name-only | wc -l)" -gt 20 ]; then
        echo "... ($(( $(git diff --name-only | wc -l) - 20 )) autres fichiers)"
    fi
else
    log_info "Aucun fichier modifié après application du patch"
fi
echo ""

# 7. Valider les changements (optionnel)
log_info "[7/8] Validation des changements (optionnel)..."
if [ -f "package.json" ] && command -v npm >/dev/null 2>&1; then
    log_info "Voulez-vous exécuter npm run build? (y/N)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        npm run build || log_warning "Build échoué"
    fi
fi

if command -v pytest >/dev/null 2>&1; then
    log_info "Voulez-vous exécuter les tests? (y/N)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        pytest tests/ -x || log_warning "Tests échoués"
    fi
fi

# 8. Commit et push (interactif)
log_info "[8/8] Commit et push vers GitHub..."

if [ "$PATCH_APPLIED" = false ] || [ "$MODIFIED_FILES" -eq 0 ]; then
    log_warning "Aucune modification à commiter"
else
    echo "Voulez-vous commiter et pusher vers GitHub? (y/N)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        # Générer message de commit
        if [ "$HAS_METADATA" = true ] && command -v jq >/dev/null 2>&1; then
            COMMIT_MSG="sync: intégration modifications GPT Codex Cloud

Export: $(jq -r '.export_timestamp' "$METADATA_PATH")
Type: $(jq -r '.patch.type' "$METADATA_PATH")
Fichiers: $(jq -r '.patch.modified_files' "$METADATA_PATH")
Branche source: $(jq -r '.git.branch' "$METADATA_PATH")

🤖 Synchronisation automatique Cloud → Local → GitHub"
        else
            COMMIT_MSG="sync: intégration modifications GPT Codex Cloud

Patch: $PATCH_NAME
Méthode: $PATCH_METHOD
Fichiers modifiés: $MODIFIED_FILES

🤖 Synchronisation automatique Cloud → Local → GitHub"
        fi

        git add -A
        git commit -m "$COMMIT_MSG"
        log_success "Modifications commitées"

        echo "Voulez-vous pusher vers origin/$CURRENT_BRANCH? (y/N)"
        read -r response
        if [[ "$response" =~ ^[Yy]$ ]]; then
            git push origin "$CURRENT_BRANCH"
            log_success "Modifications pushées vers GitHub"
        else
            log_info "Push annulé (vous pouvez le faire manuellement avec: git push)"
        fi
    else
        log_info "Commit annulé (modifications dans working tree)"
    fi
fi

# Créer log d'import
mkdir -p "$LOG_DIR"
cat > "$LOG_DIR/import_${TIMESTAMP}.log" <<EOF
=== Import Local ← Cloud ===
Date: $(date)
Agent: Claude Code (Local)
Patch: $PATCH_NAME
Méthode: ${PATCH_METHOD:-N/A}
Fichiers modifiés: $MODIFIED_FILES
Branche: $CURRENT_BRANCH
Backup: $BACKUP_BRANCH

=== État Git après import ===
$(git status)

=== Derniers commits ===
$(git log --oneline -5)
EOF

# Résumé final
echo ""
echo "=== ✅ Import Terminé ==="
echo "Patch appliqué: $PATCH_NAME"
echo "Méthode: ${PATCH_METHOD:-N/A}"
echo "Fichiers modifiés: $MODIFIED_FILES"
echo "Branche backup: $BACKUP_BRANCH"
echo "Log: $LOG_DIR/import_${TIMESTAMP}.log"
echo ""
log_success "Synchronisation Cloud → Local terminée avec succès!"
echo ""
echo "💡 Prochaines étapes suggérées:"
echo "  1. Vérifier les modifications: git diff HEAD~1"
echo "  2. Tester l'application localement"
echo "  3. Mettre à jour AGENT_SYNC.md et docs/passation.md"
echo "  4. Si problème: git checkout $BACKUP_BRANCH"
