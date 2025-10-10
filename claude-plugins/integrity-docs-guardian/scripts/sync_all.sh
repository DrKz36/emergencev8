#!/bin/bash
################################################################################
# sync_all.sh - Orchestrateur global ÉMERGENCE
# Coordonne tous les agents, fusionne les rapports et synchronise les dépôts
################################################################################

set -e

# Couleurs pour l'output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PLUGIN_DIR="$REPO_ROOT/claude-plugins/integrity-docs-guardian"
REPORTS_DIR="$PLUGIN_DIR/reports"
SCRIPTS_DIR="$PLUGIN_DIR/scripts"

# Créer les répertoires nécessaires
mkdir -p "$REPORTS_DIR"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                                                                ║${NC}"
echo -e "${BLUE}║          🚀 ORCHESTRATEUR GLOBAL ÉMERGENCE                     ║${NC}"
echo -e "${BLUE}║          Synchronisation Multi-Agents & Multi-Sources          ║${NC}"
echo -e "${BLUE}║                                                                ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Timestamp de début
START_TIME=$(date +%s)
TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")

echo -e "${BLUE}🕒 Démarrage:${NC} $TIMESTAMP"
echo ""

################################################################################
# ÉTAPE 1: DÉTECTION DU CONTEXTE
################################################################################

echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}📍 ÉTAPE 1: DÉTECTION DU CONTEXTE${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

CURRENT_COMMIT=$(git rev-parse HEAD)
CURRENT_BRANCH=$(git branch --show-current)

echo "   📍 Commit actuel: ${CURRENT_COMMIT:0:8}"
echo "   🌿 Branche: $CURRENT_BRANCH"
echo ""

################################################################################
# ÉTAPE 2: EXÉCUTION DES AGENTS
################################################################################

echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}🤖 ÉTAPE 2: EXÉCUTION DES AGENTS${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

AGENTS_SUCCESS=0
AGENTS_TOTAL=3

# Agent 1: Anima (DocKeeper)
echo -e "${BLUE}📚 [1/3] Lancement d'Anima (DocKeeper)...${NC}"
if command -v python &> /dev/null && [ -f "$SCRIPTS_DIR/scan_docs.py" ]; then
    if python "$SCRIPTS_DIR/scan_docs.py" > /dev/null 2>&1; then
        echo -e "   ${GREEN}✅ Anima terminé avec succès${NC}"
        ((AGENTS_SUCCESS++))
    else
        echo -e "   ${YELLOW}⚠️  Anima a détecté des problèmes (voir reports/docs_report.json)${NC}"
    fi
else
    echo -e "   ${YELLOW}⚠️  Anima non disponible${NC}"
fi
echo ""

# Agent 2: Neo (IntegrityWatcher)
echo -e "${BLUE}🔐 [2/3] Lancement de Neo (IntegrityWatcher)...${NC}"
if command -v python &> /dev/null && [ -f "$SCRIPTS_DIR/check_integrity.py" ]; then
    if python "$SCRIPTS_DIR/check_integrity.py" > /dev/null 2>&1; then
        echo -e "   ${GREEN}✅ Neo terminé avec succès${NC}"
        ((AGENTS_SUCCESS++))
    else
        echo -e "   ${YELLOW}⚠️  Neo a détecté des incohérences (voir reports/integrity_report.json)${NC}"
    fi
else
    echo -e "   ${YELLOW}⚠️  Neo non disponible${NC}"
fi
echo ""

# Agent 3: ProdGuardian (Production Monitor)
echo -e "${BLUE}☁️  [3/3] Lancement de ProdGuardian (Production Monitor)...${NC}"
if command -v python &> /dev/null && command -v gcloud &> /dev/null && [ -f "$SCRIPTS_DIR/check_prod_logs.py" ]; then
    if python "$SCRIPTS_DIR/check_prod_logs.py" > /dev/null 2>&1; then
        echo -e "   ${GREEN}✅ ProdGuardian terminé - Production OK${NC}"
        ((AGENTS_SUCCESS++))
    elif [ $? -eq 1 ]; then
        echo -e "   ${YELLOW}⚠️  ProdGuardian - Production DEGRADED${NC}"
    elif [ $? -eq 2 ]; then
        echo -e "   ${RED}🔴 ProdGuardian - Production CRITICAL${NC}"
    fi
else
    echo -e "   ${YELLOW}⚠️  ProdGuardian non disponible (gcloud ou python manquant)${NC}"
fi
echo ""

################################################################################
# ÉTAPE 3: FUSION DES RAPPORTS
################################################################################

echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}📊 ÉTAPE 3: FUSION DES RAPPORTS${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if [ -f "$SCRIPTS_DIR/merge_reports.py" ]; then
    echo -e "${BLUE}🔄 Fusion des rapports en cours...${NC}"
    python "$SCRIPTS_DIR/merge_reports.py"
    MERGE_EXIT_CODE=$?

    if [ $MERGE_EXIT_CODE -eq 0 ]; then
        echo -e "${GREEN}✅ Fusion terminée - Statut global: OK${NC}"
    elif [ $MERGE_EXIT_CODE -eq 1 ]; then
        echo -e "${YELLOW}⚠️  Fusion terminée - Statut global: DEGRADED/WARNING${NC}"
    elif [ $MERGE_EXIT_CODE -eq 2 ]; then
        echo -e "${RED}🔴 Fusion terminée - Statut global: CRITICAL${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Script merge_reports.py introuvable${NC}"
fi
echo ""

################################################################################
# ÉTAPE 4: VÉRIFICATION DES CHANGEMENTS
################################################################################

echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}🔍 ÉTAPE 4: VÉRIFICATION DES CHANGEMENTS${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Vérifier s'il y a des modifications à committer
if [ -n "$(git status --porcelain)" ]; then
    echo -e "${BLUE}📝 Modifications détectées:${NC}"
    git status --short | head -10
    echo ""

    # Demander confirmation pour commit (sauf si AUTO_COMMIT=1)
    if [ "$AUTO_COMMIT" = "1" ]; then
        COMMIT_CHANGES=true
    else
        echo -e "${YELLOW}Voulez-vous committer ces changements? (y/N)${NC}"
        read -r -p "> " RESPONSE
        if [[ "$RESPONSE" =~ ^[Yy]$ ]]; then
            COMMIT_CHANGES=true
        else
            COMMIT_CHANGES=false
        fi
    fi

    if [ "$COMMIT_CHANGES" = true ]; then
        echo ""
        echo -e "${BLUE}📤 Commit des modifications...${NC}"
        git add .
        COMMIT_MSG="chore(sync): mise à jour automatique - agents ÉMERGENCE $(date +%F_%T)"
        git commit -m "$COMMIT_MSG" || echo "Rien à committer"
        echo -e "${GREEN}✅ Commit effectué${NC}"
    else
        echo -e "${YELLOW}⏭️  Commit ignoré${NC}"
    fi
else
    echo -e "${GREEN}✅ Aucune modification à committer${NC}"
fi
echo ""

################################################################################
# ÉTAPE 5: SYNCHRONISATION GITHUB
################################################################################

echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}🔗 ÉTAPE 5: SYNCHRONISATION GITHUB${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if [ "$SKIP_PUSH" != "1" ]; then
    # Vérifier si origin existe
    if git remote get-url origin &> /dev/null; then
        echo -e "${BLUE}📤 Push vers GitHub (origin/$CURRENT_BRANCH)...${NC}"
        if git push origin "$CURRENT_BRANCH" 2>&1; then
            echo -e "${GREEN}✅ Synchronisé avec GitHub${NC}"
        else
            echo -e "${RED}❌ Erreur lors du push vers GitHub${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  Remote 'origin' non configuré${NC}"
    fi
else
    echo -e "${YELLOW}⏭️  Push vers GitHub ignoré (SKIP_PUSH=1)${NC}"
fi
echo ""

################################################################################
# ÉTAPE 6: SYNCHRONISATION CODEX CLOUD (optionnel)
################################################################################

echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}☁️  ÉTAPE 6: SYNCHRONISATION CODEX CLOUD${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if [ "$SKIP_PUSH" != "1" ]; then
    # Vérifier si remote codex existe
    if git remote get-url codex &> /dev/null; then
        echo -e "${BLUE}📤 Push vers Codex Cloud (codex/$CURRENT_BRANCH)...${NC}"
        if git push codex "$CURRENT_BRANCH" 2>&1; then
            echo -e "${GREEN}✅ Synchronisé avec Codex Cloud${NC}"
        else
            echo -e "${YELLOW}⚠️  Erreur lors du push vers Codex (peut ne pas exister)${NC}"
        fi
    else
        echo -e "${YELLOW}ℹ️  Remote 'codex' non configuré (optionnel)${NC}"
    fi
else
    echo -e "${YELLOW}⏭️  Push vers Codex ignoré (SKIP_PUSH=1)${NC}"
fi
echo ""

################################################################################
# ÉTAPE 7: RAPPORT FINAL
################################################################################

echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}📋 RAPPORT FINAL${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Calculer la durée
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo -e "${GREEN}✅ Synchronisation terminée !${NC}"
echo ""
echo "   🕒 Durée totale: ${DURATION}s"
echo "   🤖 Agents exécutés: $AGENTS_SUCCESS/$AGENTS_TOTAL"
echo "   📁 Rapports générés: $REPORTS_DIR"
echo ""

# Afficher le statut du rapport global si disponible
if [ -f "$REPORTS_DIR/global_report.json" ]; then
    echo "   📊 Rapport global: $REPORTS_DIR/global_report.json"

    # Extraire le statut avec jq si disponible
    if command -v jq &> /dev/null; then
        GLOBAL_STATUS=$(jq -r '.statut_global' "$REPORTS_DIR/global_report.json" 2>/dev/null)
        if [ "$GLOBAL_STATUS" = "OK" ]; then
            echo -e "   ${GREEN}🟢 Statut global: $GLOBAL_STATUS${NC}"
        elif [ "$GLOBAL_STATUS" = "DEGRADED" ] || [ "$GLOBAL_STATUS" = "WARNING" ]; then
            echo -e "   ${YELLOW}🟡 Statut global: $GLOBAL_STATUS${NC}"
        elif [ "$GLOBAL_STATUS" = "CRITICAL" ]; then
            echo -e "   ${RED}🔴 Statut global: $GLOBAL_STATUS${NC}"
        fi
    fi
fi
echo ""

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║          ✅ ORCHESTRATION TERMINÉE                             ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Code de sortie basé sur le statut global
if [ -f "$REPORTS_DIR/global_report.json" ] && command -v jq &> /dev/null; then
    GLOBAL_STATUS=$(jq -r '.statut_global' "$REPORTS_DIR/global_report.json" 2>/dev/null)
    if [ "$GLOBAL_STATUS" = "CRITICAL" ]; then
        exit 2
    elif [ "$GLOBAL_STATUS" = "DEGRADED" ] || [ "$GLOBAL_STATUS" = "WARNING" ]; then
        exit 1
    fi
fi

exit 0
