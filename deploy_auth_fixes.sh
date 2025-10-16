#!/bin/bash
# Script de déploiement des corrections d'authentification
# Date: 2025-10-16
# Urgence: CRITIQUE

set -e  # Exit on error

echo "================================================"
echo "🔧 DÉPLOIEMENT DES CORRECTIONS D'AUTHENTIFICATION"
echo "================================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="emergence-469005"
SERVICE_NAME="emergence-app"
REGION="europe-west1"

echo "📋 Configuration:"
echo "  Projet: $PROJECT_ID"
echo "  Service: $SERVICE_NAME"
echo "  Région: $REGION"
echo ""

# Vérification des prérequis
echo "🔍 Vérification des prérequis..."
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}❌ gcloud CLI non installé${NC}"
    exit 1
fi

echo -e "${GREEN}✅ gcloud CLI détecté${NC}"

# Authentification
echo ""
echo "🔐 Vérification de l'authentification..."
CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null)
if [ "$CURRENT_PROJECT" != "$PROJECT_ID" ]; then
    echo -e "${YELLOW}⚠️  Projet actuel: $CURRENT_PROJECT${NC}"
    echo "  Basculement vers: $PROJECT_ID"
    gcloud config set project $PROJECT_ID
fi

echo -e "${GREEN}✅ Authentifié sur le projet $PROJECT_ID${NC}"

# Méthode de déploiement
echo ""
echo "📦 Choisissez la méthode de déploiement:"
echo "  1) Mise à jour rapide (env vars seulement) - 2 minutes"
echo "  2) Déploiement complet (rebuild + deploy) - 10 minutes"
echo ""
read -p "Votre choix (1/2): " DEPLOY_METHOD

if [ "$DEPLOY_METHOD" == "1" ]; then
    echo ""
    echo "⚡ Mise à jour rapide des variables d'environnement..."

    gcloud run services update $SERVICE_NAME \
        --region=$REGION \
        --set-env-vars="SESSION_INACTIVITY_TIMEOUT_MINUTES=30,SESSION_CLEANUP_INTERVAL_SECONDS=60,SESSION_WARNING_BEFORE_TIMEOUT_SECONDS=120,AUTH_DEV_MODE=0" \
        --quiet

    echo -e "${GREEN}✅ Variables d'environnement mises à jour${NC}"

elif [ "$DEPLOY_METHOD" == "2" ]; then
    echo ""
    echo "🏗️  Déploiement complet avec rebuild..."

    # Vérifier si cloudbuild.yaml existe
    if [ ! -f "cloudbuild.yaml" ]; then
        echo -e "${RED}❌ cloudbuild.yaml introuvable${NC}"
        exit 1
    fi

    echo "  Building and deploying..."
    gcloud builds submit --config cloudbuild.yaml

    echo -e "${GREEN}✅ Déploiement complet terminé${NC}"

else
    echo -e "${RED}❌ Choix invalide${NC}"
    exit 1
fi

# Vérification du déploiement
echo ""
echo "🔍 Vérification du déploiement..."
sleep 5

SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
    --region=$REGION \
    --format='value(status.url)')

echo "  URL du service: $SERVICE_URL"

# Test de santé
echo ""
echo "🏥 Test de santé du service..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$SERVICE_URL/health")

if [ "$HTTP_CODE" == "200" ]; then
    echo -e "${GREEN}✅ Service opérationnel (HTTP $HTTP_CODE)${NC}"
else
    echo -e "${YELLOW}⚠️  Service répond avec HTTP $HTTP_CODE${NC}"
fi

# Afficher les logs récents
echo ""
echo "📋 Logs récents (30 dernières secondes):"
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE_NAME" \
    --limit=10 \
    --format="table(timestamp,severity,textPayload)" \
    --freshness=30s

# Afficher la configuration finale
echo ""
echo "⚙️  Configuration active:"
gcloud run services describe $SERVICE_NAME \
    --region=$REGION \
    --format="yaml(spec.template.spec.containers[0].env)" | grep -A 3 "SESSION_INACTIVITY"

echo ""
echo "================================================"
echo -e "${GREEN}✅ DÉPLOIEMENT TERMINÉ${NC}"
echo "================================================"
echo ""
echo "📊 Prochaines étapes:"
echo "  1. Monitorer les logs pendant 10 minutes"
echo "  2. Tester la connexion avec un beta testeur"
echo "  3. Vérifier les métriques Prometheus"
echo ""
echo "📝 Commandes utiles:"
echo "  Logs en temps réel:"
echo "    gcloud logging tail \"resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE_NAME\""
echo ""
echo "  Revenir en arrière si problème:"
echo "    gcloud run services update-traffic $SERVICE_NAME --region=$REGION --to-revisions=PREVIOUS_REVISION=100"
echo ""
echo "📖 Rapport complet: AUTH_FIXES_REPORT.md"
echo ""
