# Makefile for Emergence Cloud Run Microservices
# Simplifies deployment and management commands

# Configuration
PROJECT_ID := emergence-469005
REGION := europe-west1

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
NC := \033[0m # No Color

.PHONY: help setup deploy-auth deploy-session deploy-all test clean logs-auth logs-session secrets

# Default target
help:
	@echo "$(BLUE)Emergence Cloud Run Deployment Commands$(NC)"
	@echo "========================================"
	@echo ""
	@echo "$(GREEN)Setup:$(NC)"
	@echo "  make setup          - Configure gcloud and make scripts executable"
	@echo "  make secrets        - List configured secrets"
	@echo ""
	@echo "$(GREEN)Deployment:$(NC)"
	@echo "  make deploy-auth    - Deploy authentication service"
	@echo "  make deploy-session - Deploy session service"
	@echo "  make deploy-all     - Deploy all services interactively"
	@echo ""
	@echo "$(GREEN)Testing:$(NC)"
	@echo "  make test           - Run integration tests"
	@echo "  make test-auth      - Test auth service only"
	@echo "  make test-session   - Test session service only"
	@echo ""
	@echo "$(GREEN)Monitoring:$(NC)"
	@echo "  make logs-auth      - Tail auth service logs"
	@echo "  make logs-session   - Tail session service logs"
	@echo "  make status         - Show service status"
	@echo "  make urls           - Display service URLs"
	@echo ""
	@echo "$(GREEN)Maintenance:$(NC)"
	@echo "  make clean          - Clean Docker images"
	@echo "  make rollback-auth  - Rollback auth service"
	@echo "  make rollback-session - Rollback session service"
	@echo ""

# Setup
setup:
	@echo "$(BLUE)Setting up environment...$(NC)"
	@chmod +x *.sh
	@gcloud config set project $(PROJECT_ID)
	@echo "$(GREEN)✅ Setup complete$(NC)"

# Secrets management
secrets:
	@echo "$(BLUE)Configured secrets:$(NC)"
	@gcloud secrets list --project=$(PROJECT_ID)

create-jwt-secret:
	@echo "$(BLUE)Creating JWT secret...$(NC)"
	@openssl rand -hex 32 | gcloud secrets create AUTH_JWT_SECRET \
		--data-file=- \
		--replication-policy=automatic \
		--project=$(PROJECT_ID)
	@echo "$(GREEN)✅ JWT secret created$(NC)"

# Deployment targets
deploy-auth:
	@echo "$(BLUE)Deploying authentication service...$(NC)"
	@./deploy-auth-service.sh

deploy-session:
	@echo "$(BLUE)Deploying session service...$(NC)"
	@./deploy-session-service.sh

deploy-all:
	@echo "$(BLUE)Deploying all services...$(NC)"
	@./deploy-all-services.sh

# Testing
test:
	@echo "$(BLUE)Running integration tests...$(NC)"
	@./test-services.sh

test-auth:
	@echo "$(BLUE)Testing authentication service...$(NC)"
	@AUTH_URL=$$(gcloud run services describe emergence-auth-service \
		--region=$(REGION) \
		--project=$(PROJECT_ID) \
		--format="value(status.url)"); \
	echo "URL: $$AUTH_URL"; \
	curl -s "$$AUTH_URL/api/health" | jq .

test-session:
	@echo "$(BLUE)Testing session service...$(NC)"
	@SESSION_URL=$$(gcloud run services describe emergence-session-service \
		--region=$(REGION) \
		--project=$(PROJECT_ID) \
		--format="value(status.url)"); \
	echo "URL: $$SESSION_URL"; \
	curl -s "$$SESSION_URL/api/health" | jq .

# Monitoring
logs-auth:
	@gcloud run services logs tail emergence-auth-service \
		--region=$(REGION) \
		--project=$(PROJECT_ID)

logs-session:
	@gcloud run services logs tail emergence-session-service \
		--region=$(REGION) \
		--project=$(PROJECT_ID)

status:
	@echo "$(BLUE)Service Status:$(NC)"
	@gcloud run services list \
		--region=$(REGION) \
		--project=$(PROJECT_ID) \
		--filter="metadata.labels.app=emergence"

urls:
	@echo "$(BLUE)Service URLs:$(NC)"
	@echo ""
	@echo "$(GREEN)🔐 Auth Service:$(NC)"
	@gcloud run services describe emergence-auth-service \
		--region=$(REGION) \
		--project=$(PROJECT_ID) \
		--format="value(status.url)" 2>/dev/null || echo "Not deployed"
	@echo ""
	@echo "$(GREEN)💬 Session Service:$(NC)"
	@gcloud run services describe emergence-session-service \
		--region=$(REGION) \
		--project=$(PROJECT_ID) \
		--format="value(status.url)" 2>/dev/null || echo "Not deployed"
	@echo ""
	@echo "$(GREEN)📦 Main App:$(NC)"
	@gcloud run services describe emergence-app \
		--region=$(REGION) \
		--project=$(PROJECT_ID) \
		--format="value(status.url)" 2>/dev/null || echo "Not deployed"

# Rollback
rollback-auth:
	@echo "$(YELLOW)Rolling back auth service...$(NC)"
	@REVISIONS=$$(gcloud run revisions list \
		--service=emergence-auth-service \
		--region=$(REGION) \
		--project=$(PROJECT_ID) \
		--limit=5 \
		--format="table(name,status)"); \
	echo "$$REVISIONS"; \
	read -p "Enter revision name to rollback to: " REVISION; \
	gcloud run services update-traffic emergence-auth-service \
		--to-revisions=$$REVISION=100 \
		--region=$(REGION) \
		--project=$(PROJECT_ID)

rollback-session:
	@echo "$(YELLOW)Rolling back session service...$(NC)"
	@REVISIONS=$$(gcloud run revisions list \
		--service=emergence-session-service \
		--region=$(REGION) \
		--project=$(PROJECT_ID) \
		--limit=5 \
		--format="table(name,status)"); \
	echo "$$REVISIONS"; \
	read -p "Enter revision name to rollback to: " REVISION; \
	gcloud run services update-traffic emergence-session-service \
		--to-revisions=$$REVISION=100 \
		--region=$(REGION) \
		--project=$(PROJECT_ID)

# Cleanup
clean:
	@echo "$(YELLOW)Cleaning Docker images...$(NC)"
	@docker system prune -f
	@echo "$(GREEN)✅ Cleanup complete$(NC)"

clean-all:
	@echo "$(RED)WARNING: This will remove ALL Docker images and containers$(NC)"
	@read -p "Are you sure? (y/N) " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker system prune -a -f; \
		echo "$(GREEN)✅ Full cleanup complete$(NC)"; \
	fi

# Development helpers
dev-auth:
	@echo "$(BLUE)Building auth service for local development...$(NC)"
	@docker build -f auth-service.Dockerfile -t emergence-auth-local ../..
	@echo "$(GREEN)✅ Build complete. Run with:$(NC)"
	@echo "docker run -p 8080:8080 -e AUTH_JWT_SECRET=test emergence-auth-local"

dev-session:
	@echo "$(BLUE)Building session service for local development...$(NC)"
	@docker build -f session-service.Dockerfile -t emergence-session-local ../..
	@echo "$(GREEN)✅ Build complete. Run with:$(NC)"
	@echo "docker run -p 8080:8080 emergence-session-local"

# Info
info:
	@echo "$(BLUE)Project Information:$(NC)"
	@echo "Project ID: $(PROJECT_ID)"
	@echo "Region: $(REGION)"
	@echo ""
	@echo "$(BLUE)Installed Services:$(NC)"
	@gcloud run services list --project=$(PROJECT_ID) --region=$(REGION) --format="table(name,status.url)"
	@echo ""
	@echo "$(BLUE)Recent Deployments:$(NC)"
	@gcloud run operations list --limit=5 --project=$(PROJECT_ID)
