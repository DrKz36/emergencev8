#!/bin/bash
# Script d'export pour GPT Codex Cloud
# Génère un patch complet avec métadonnées pour synchronisation avec environnement local

set -e

# Configuration
SYNC_DIR="${SYNC_DIR:-.sync}"
PATCH_DIR="$SYNC_DIR/patches"
LOG_DIR="$SYNC_DIR/logs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
PATCH_NAME="sync_cloud_${TIMESTAMP}.patch"
METADATA_NAME="sync_cloud_${TIMESTAMP}.json"

# Créer les dossiers si nécessaire
mkdir -p "$PATCH_DIR" "$LOG_DIR"

echo "=== GPT Codex Cloud - Export de Synchronisation ==="
echo "Timestamp: $TIMESTAMP"
echo ""

# 1. Vérifier l'état Git
echo "[1/6] Vérification état Git..."
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "❌ ERREUR: Pas dans un dépôt Git"
    exit 1
fi

# 2. Récupérer informations Git
echo "[2/6] Collecte informations Git..."
CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "detached")
LAST_COMMIT=$(git rev-parse HEAD 2>/dev/null || echo "none")
LAST_COMMIT_MSG=$(git log -1 --pretty=%B 2>/dev/null || echo "N/A")
UNCOMMITTED_CHANGES=$(git status --short | wc -l)
COMMITS_AHEAD=$(git rev-list --count @{u}..HEAD 2>/dev/null || echo "0")

echo "  Branche: $CURRENT_BRANCH"
echo "  Dernier commit: ${LAST_COMMIT:0:8}"
echo "  Changements non commités: $UNCOMMITTED_CHANGES"
echo "  Commits en avance: $COMMITS_AHEAD"

# 3. Générer le patch
echo "[3/6] Génération du patch..."
if [ "$UNCOMMITTED_CHANGES" -gt 0 ]; then
    # Il y a des changements non commités
    git diff HEAD > "$PATCH_DIR/$PATCH_NAME"
    PATCH_TYPE="uncommitted"
    echo "  ✓ Patch créé avec changements non commités"
elif [ "$COMMITS_AHEAD" -gt 0 ]; then
    # Il y a des commits non pushés
    git format-patch @{u} --stdout > "$PATCH_DIR/$PATCH_NAME"
    PATCH_TYPE="commits"
    echo "  ✓ Patch créé avec $COMMITS_AHEAD commit(s)"
else
    echo "  ⚠️  Aucune modification à exporter"
    PATCH_TYPE="empty"
    touch "$PATCH_DIR/$PATCH_NAME"
fi

# Vérifier si le patch est vide
PATCH_SIZE=$(wc -c < "$PATCH_DIR/$PATCH_NAME")
if [ "$PATCH_SIZE" -eq 0 ]; then
    echo "  ℹ️  Le patch est vide (aucune modification)"
    PATCH_TYPE="empty"
fi

# 4. Lister fichiers modifiés
echo "[4/6] Liste des fichiers modifiés..."
git status --short > "$PATCH_DIR/files_${TIMESTAMP}.txt"
git diff --name-only HEAD >> "$PATCH_DIR/files_${TIMESTAMP}.txt" 2>/dev/null || true
MODIFIED_FILES=$(sort -u "$PATCH_DIR/files_${TIMESTAMP}.txt" | grep -v '^$' | wc -l)
echo "  Fichiers modifiés: $MODIFIED_FILES"

# 5. Générer métadonnées JSON
echo "[5/6] Génération métadonnées..."
cat > "$PATCH_DIR/$METADATA_NAME" <<EOF
{
  "export_timestamp": "$TIMESTAMP",
  "export_date": "$(date -Iseconds 2>/dev/null || date)",
  "agent": "GPT Codex Cloud",
  "git": {
    "branch": "$CURRENT_BRANCH",
    "last_commit": "$LAST_COMMIT",
    "last_commit_message": $(echo "$LAST_COMMIT_MSG" | jq -Rs .),
    "commits_ahead": $COMMITS_AHEAD,
    "uncommitted_changes": $UNCOMMITTED_CHANGES
  },
  "patch": {
    "filename": "$PATCH_NAME",
    "type": "$PATCH_TYPE",
    "size_bytes": $PATCH_SIZE,
    "modified_files": $MODIFIED_FILES
  },
  "status": "ready_for_sync"
}
EOF

echo "  ✓ Métadonnées créées"

# 6. Créer log d'export
echo "[6/6] Création log d'export..."
cat > "$LOG_DIR/export_${TIMESTAMP}.log" <<EOF
=== Export Cloud → Local ===
Date: $(date)
Agent: GPT Codex Cloud
Patch: $PATCH_NAME
Type: $PATCH_TYPE
Fichiers modifiés: $MODIFIED_FILES
Taille patch: $PATCH_SIZE bytes

=== État Git ===
$(git status)

=== Derniers commits ===
$(git log --oneline -5)

=== Fichiers modifiés ===
$(cat "$PATCH_DIR/files_${TIMESTAMP}.txt")
EOF

echo "  ✓ Log créé"

# Résumé final
echo ""
echo "=== ✅ Export Terminé ==="
echo "Patch: $PATCH_DIR/$PATCH_NAME"
echo "Métadonnées: $PATCH_DIR/$METADATA_NAME"
echo "Log: $LOG_DIR/export_${TIMESTAMP}.log"
echo ""
echo "📦 Fichiers à transférer vers l'environnement local:"
echo "  1. $PATCH_DIR/$PATCH_NAME"
echo "  2. $PATCH_DIR/$METADATA_NAME"
echo ""
echo "🚀 Prochaine étape: Transférer ces fichiers et exécuter 'local-import.sh' sur la machine locale"
echo ""

# Afficher instructions pour le développeur
cat > "$PATCH_DIR/INSTRUCTIONS_${TIMESTAMP}.txt" <<EOF
=== Instructions pour Agent Local (Claude Code) ===

Fichiers à transférer:
1. $PATCH_DIR/$PATCH_NAME
2. $PATCH_DIR/$METADATA_NAME

Commande à exécuter sur la machine locale:
  cd C:\\dev\\emergenceV8
  bash .sync/scripts/local-import.sh $PATCH_NAME

OU en utilisant le script Python:
  cd C:\\dev\\emergenceV8
  python .sync/scripts/local-import.py $PATCH_NAME

Résumé des modifications:
- Fichiers modifiés: $MODIFIED_FILES
- Type: $PATCH_TYPE
- Commits en avance: $COMMITS_AHEAD
- Branche: $CURRENT_BRANCH
EOF

echo "📄 Instructions créées: $PATCH_DIR/INSTRUCTIONS_${TIMESTAMP}.txt"
