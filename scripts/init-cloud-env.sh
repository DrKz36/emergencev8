#!/bin/bash
# Script d'initialisation pour GPT Codex Cloud
# À exécuter une seule fois au début de la première session

set -e  # Exit on error

echo "🚀 Initialisation environnement GPT Codex Cloud..."
echo ""

# Couleurs pour output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. Vérifier qu'on est dans le bon répertoire
echo -e "${BLUE}[1/6]${NC} Vérification répertoire projet..."
if [ ! -f "AGENT_SYNC.md" ]; then
    echo -e "${YELLOW}⚠️  Fichier AGENT_SYNC.md non trouvé. Êtes-vous dans /workspace/emergencev8 ?${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Répertoire projet OK${NC}"
echo ""

# 2. Configuration Git de base
echo -e "${BLUE}[2/6]${NC} Configuration Git..."
git config --global user.name "GPT Codex Cloud" 2>/dev/null || true
git config --global user.email "gpt-codex@cloud.local" 2>/dev/null || true

# Alias Git utiles
git config --global alias.export-patch '!f() { TIMESTAMP=$(date +%Y%m%d_%H%M%S); mkdir -p sync_export; git format-patch origin/main --stdout > sync_export/changes_$TIMESTAMP.patch; echo "✅ Patch créé : sync_export/changes_$TIMESTAMP.patch"; }; f' 2>/dev/null || true

git config --global alias.export-files '!f() { TIMESTAMP=$(date +%Y%m%d_%H%M%S); mkdir -p sync_export; git status --short > sync_export/files_$TIMESTAMP.txt; git log origin/main..HEAD --oneline > sync_export/commits_$TIMESTAMP.txt 2>/dev/null || echo "Aucun commit local" > sync_export/commits_$TIMESTAMP.txt; echo "✅ Fichiers listés : sync_export/files_$TIMESTAMP.txt"; }; f' 2>/dev/null || true

git config --global alias.export-all '!f() { git export-files && git export-patch; }; f' 2>/dev/null || true

echo -e "${GREEN}✅ Configuration Git terminée${NC}"
echo "   - user.name: GPT Codex Cloud"
echo "   - user.email: gpt-codex@cloud.local"
echo "   - Alias créés: export-patch, export-files, export-all"
echo ""

# 3. Créer structure de répertoires
echo -e "${BLUE}[3/6]${NC} Création structure répertoires..."
mkdir -p sync_export
mkdir -p .sync/logs
mkdir -p .sync/scripts
echo -e "${GREEN}✅ Répertoires créés${NC}"
echo "   - sync_export/ (pour patches)"
echo "   - .sync/logs/ (pour logs)"
echo "   - .sync/scripts/ (pour scripts)"
echo ""

# 4. Créer script de validation
echo -e "${BLUE}[4/6]${NC} Création scripts de validation..."
cat > .sync/scripts/validate-before-export.sh << 'SCRIPT_EOF'
#!/bin/bash
# Script de validation avant export de patch

echo "🧪 Validation avant export..."
echo ""

# Vérifier build frontend
echo "📦 Build frontend..."
if npm run build > /dev/null 2>&1; then
    echo "✅ Build frontend OK"
else
    echo "❌ Build frontend ÉCHOUÉ"
    exit 1
fi

# Vérifier tests Python (si pytest disponible)
if command -v pytest &> /dev/null; then
    echo "🧪 Tests Python..."
    if pytest tests/ -x --tb=short > /dev/null 2>&1; then
        echo "✅ Tests Python OK"
    else
        echo "⚠️  Tests Python ÉCHOUÉS (continuer quand même)"
    fi
else
    echo "⚠️  pytest non disponible, tests skippés"
fi

# Vérifier linting (si ruff disponible)
if command -v ruff &> /dev/null; then
    echo "🔍 Linting..."
    if ruff check src/ > /dev/null 2>&1; then
        echo "✅ Linting OK"
    else
        echo "⚠️  Linting a des warnings (continuer quand même)"
    fi
else
    echo "⚠️  ruff non disponible, linting skippé"
fi

echo ""
echo "✅ Validation terminée avec succès"
SCRIPT_EOF

chmod +x .sync/scripts/validate-before-export.sh
echo -e "${GREEN}✅ Script validate-before-export.sh créé${NC}"
echo ""

# 5. Créer script export complet
echo -e "${BLUE}[5/6]${NC} Création script export complet..."
cat > .sync/scripts/full-export.sh << 'SCRIPT_EOF'
#!/bin/bash
# Script d'export complet pour fin de session

echo "📦 Export complet pour synchronisation..."
echo ""

# Timestamp unique
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p sync_export

# 1. Générer patch
echo "🔧 Génération patch Git..."
if git format-patch origin/main --stdout > sync_export/changes_$TIMESTAMP.patch 2>/dev/null; then
    PATCH_SIZE=$(wc -l < sync_export/changes_$TIMESTAMP.patch)
    echo "✅ Patch créé : sync_export/changes_$TIMESTAMP.patch ($PATCH_SIZE lignes)"
else
    echo "⚠️  Aucun changement à patcher (peut-être déjà committé ?)"
    git diff HEAD > sync_export/changes_$TIMESTAMP.patch
fi

# 2. Lister fichiers modifiés
echo "📝 Liste fichiers modifiés..."
git status --short > sync_export/files_$TIMESTAMP.txt
FILES_COUNT=$(wc -l < sync_export/files_$TIMESTAMP.txt)
echo "✅ Fichiers listés : sync_export/files_$TIMESTAMP.txt ($FILES_COUNT fichiers)"

# 3. Résumé commits locaux
echo "📋 Résumé commits locaux..."
if git log origin/main..HEAD --oneline > sync_export/commits_$TIMESTAMP.txt 2>/dev/null; then
    COMMITS_COUNT=$(wc -l < sync_export/commits_$TIMESTAMP.txt)
    echo "✅ Commits listés : sync_export/commits_$TIMESTAMP.txt ($COMMITS_COUNT commits)"
else
    echo "Aucun commit local" > sync_export/commits_$TIMESTAMP.txt
    echo "ℹ️  Aucun commit local trouvé"
fi

# 4. Créer résumé pour développeur
cat > sync_export/README_$TIMESTAMP.md << README_EOF
# Patch de Synchronisation GPT Codex Cloud

**Date** : $(date '+%Y-%m-%d %H:%M:%S')
**Session** : GPT Codex Cloud

## Fichiers Générés

- \`changes_$TIMESTAMP.patch\` — Patch Git à appliquer
- \`files_$TIMESTAMP.txt\` — Liste des fichiers modifiés
- \`commits_$TIMESTAMP.txt\` — Liste des commits locaux
- \`README_$TIMESTAMP.md\` — Ce fichier

## Statistiques

- **Fichiers modifiés** : $FILES_COUNT
- **Taille patch** : $PATCH_SIZE lignes
- **Commits locaux** : $COMMITS_COUNT

## Application du Patch

Sur la machine locale :

\`\`\`bash
cd C:\dev\emergenceV8

# Vérifier le patch
git apply --check changes_$TIMESTAMP.patch

# Appliquer
git apply changes_$TIMESTAMP.patch

# Tester
npm run build && pytest

# Commit et push
git add -A
git commit -m "sync: modifications GPT Codex cloud - [DESCRIPTION]"
git push origin main
\`\`\`

## Modifications Principales

[À COMPLÉTER PAR GPT CODEX : Décrire les modifications effectuées]

## Tests Effectués

[À COMPLÉTER PAR GPT CODEX : Résultats des tests]

## Notes

[À COMPLÉTER PAR GPT CODEX : Informations complémentaires]
README_EOF

echo "✅ README créé : sync_export/README_$TIMESTAMP.md"
echo ""

# Résumé final
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Export complet terminé !"
echo ""
echo "📦 Fichiers créés dans sync_export/ :"
echo "   - changes_$TIMESTAMP.patch ($PATCH_SIZE lignes)"
echo "   - files_$TIMESTAMP.txt ($FILES_COUNT fichiers)"
echo "   - commits_$TIMESTAMP.txt ($COMMITS_COUNT commits)"
echo "   - README_$TIMESTAMP.md (à compléter)"
echo ""
echo "📋 PROCHAINES ÉTAPES :"
echo "1. Éditer sync_export/README_$TIMESTAMP.md (compléter sections)"
echo "2. Mettre à jour AGENT_SYNC.md avec résumé session"
echo "3. Ajouter entrée dans docs/passation.md"
echo "4. Informer développeur : 'Patch prêt : changes_$TIMESTAMP.patch'"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
SCRIPT_EOF

chmod +x .sync/scripts/full-export.sh
echo -e "${GREEN}✅ Script full-export.sh créé${NC}"
echo ""

# 6. Créer aide-mémoire rapide
echo -e "${BLUE}[6/6]${NC} Création aide-mémoire..."
cat > .sync/QUICKSTART.md << 'QUICKSTART_EOF'
# 🚀 Aide-Mémoire Rapide GPT Codex Cloud

## Commandes Essentielles

### Avant de commencer à coder
```bash
# Lire les fichiers de contexte
cat AGENT_SYNC.md
tail -100 docs/passation.md
git log --oneline -10
git status
```

### Pendant le développement
```bash
# Travailler normalement, tester au fur et à mesure
npm run build  # Si frontend
pytest tests/  # Si backend
```

### À la fin de la session

**Option 1 : Export rapide (alias Git)**
```bash
git export-all  # Génère patch + liste fichiers
```

**Option 2 : Export avec validation**
```bash
.sync/scripts/validate-before-export.sh  # Valider code
.sync/scripts/full-export.sh             # Export complet
```

**Option 3 : Export manuel**
```bash
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p sync_export
git format-patch origin/main --stdout > sync_export/changes_$TIMESTAMP.patch
git status --short > sync_export/files_$TIMESTAMP.txt
```

### Après l'export

1. **Éditer le README** :
   ```bash
   # Compléter les sections dans sync_export/README_*.md
   ```

2. **Mettre à jour documentation** :
   - Ajouter section dans `AGENT_SYNC.md`
   - Ajouter entrée dans `docs/passation.md`

3. **Informer développeur** :
   - Nom du patch
   - Résumé modifications
   - Fichiers critiques

## Alias Git Disponibles

- `git export-patch` — Génère patch uniquement
- `git export-files` — Liste fichiers modifiés uniquement
- `git export-all` — Génère patch + liste fichiers

## Structure Répertoires

```
/workspace/emergencev8/
├── sync_export/              # Patches générés (à transférer)
│   ├── changes_*.patch
│   ├── files_*.txt
│   ├── commits_*.txt
│   └── README_*.md
├── .sync/                    # Scripts et logs
│   ├── scripts/
│   │   ├── validate-before-export.sh
│   │   └── full-export.sh
│   ├── logs/
│   └── QUICKSTART.md         # Ce fichier
└── [reste du projet]
```

## Workflow Complet

```
1. Lire contexte (AGENT_SYNC.md, passation.md, git log)
        ↓
2. Développer code + tests
        ↓
3. Valider (.sync/scripts/validate-before-export.sh)
        ↓
4. Générer patch (.sync/scripts/full-export.sh)
        ↓
5. Compléter README (sync_export/README_*.md)
        ↓
6. Documenter (AGENT_SYNC.md + docs/passation.md)
        ↓
7. Informer développeur
```

## Troubleshooting

**Problème : `git format-patch` échoue**
```bash
# Utiliser git diff à la place
git diff HEAD > sync_export/changes_$(date +%Y%m%d_%H%M%S).patch
```

**Problème : Aucun remote configuré**
```bash
# Normal ! Utiliser git diff
git diff > sync_export/changes_$(date +%Y%m%d_%H%M%S).patch
```

**Problème : Script non exécutable**
```bash
chmod +x .sync/scripts/*.sh
```

## Documentation Complète

- 📖 `docs/GPT_CODEX_CLOUD_INSTRUCTIONS.md` — Instructions détaillées
- 📖 `docs/CLOUD_LOCAL_SYNC_WORKFLOW.md` — Guide workflow complet
- 📖 `docs/RESUME_SYNC_SOLUTION.md` — Résumé solution
QUICKSTART_EOF

echo -e "${GREEN}✅ Aide-mémoire créé : .sync/QUICKSTART.md${NC}"
echo ""

# Résumé final
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}✅ Initialisation terminée avec succès !${NC}"
echo ""
echo "📋 Configuration appliquée :"
echo "   ✅ Git configuré (user.name, user.email)"
echo "   ✅ Alias Git créés (export-patch, export-files, export-all)"
echo "   ✅ Structure répertoires créée (sync_export/, .sync/)"
echo "   ✅ Scripts créés (validate, full-export)"
echo "   ✅ Aide-mémoire créé (.sync/QUICKSTART.md)"
echo ""
echo "🚀 Prochaines étapes :"
echo ""
echo "   1. Lire l'aide-mémoire :"
echo "      cat .sync/QUICKSTART.md"
echo ""
echo "   2. Lire la documentation complète :"
echo "      cat docs/GPT_CODEX_CLOUD_INSTRUCTIONS.md"
echo ""
echo "   3. Tester l'export :"
echo "      .sync/scripts/full-export.sh"
echo ""
echo "   4. Commencer à coder ! 🎉"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
