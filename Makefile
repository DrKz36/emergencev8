# ==============================
# ÉMERGENCE - Makefile
# FastAPI 0.118.0 + LiteLLM Proxy
# ==============================

.PHONY: help install build up down restart logs test test-stream clean rebuild health

# Default target
help:
	@echo "ÉMERGENCE - Commandes disponibles:"
	@echo ""
	@echo "  make install       - Installer les dépendances Python"
	@echo "  make build         - Build les containers Docker"
	@echo "  make up            - Démarrer les services (detached)"
	@echo "  make down          - Arrêter les services"
	@echo "  make restart       - Redémarrer les services"
	@echo "  make logs          - Voir les logs (backend + litellm)"
	@echo "  make test          - Lancer tous les tests"
	@echo "  make test-stream   - Tester le streaming yield cleanup"
	@echo "  make health        - Vérifier la santé des services"
	@echo "  make clean         - Nettoyer containers et volumes"
	@echo "  make rebuild       - Clean + build + up"
	@echo ""

# Installation locale des dépendances
install:
	@echo "📦 Installation des dépendances..."
	pip install -r requirements.txt

# Build des containers
build:
	@echo "🔨 Build des containers..."
	docker-compose build

# Démarrer les services
up:
	@echo "🚀 Démarrage des services..."
	docker-compose up -d
	@echo "✅ Services démarrés:"
	@echo "   - Backend:      http://localhost:8000"
	@echo "   - LiteLLM Proxy: http://localhost:4000"

# Arrêter les services
down:
	@echo "🛑 Arrêt des services..."
	docker-compose down

# Redémarrer
restart: down up

# Voir les logs
logs:
	@echo "📋 Logs des services (Ctrl+C pour quitter)..."
	docker-compose logs -f

# Lancer tous les tests
test:
	@echo "🧪 Lancement des tests..."
	pytest src/backend/tests/ -v

# Test spécifique streaming
test-stream:
	@echo "🧪 Test streaming yield cleanup..."
	pytest src/backend/tests/test_stream_yield.py -v

# Vérifier la santé des services
health:
	@echo "🏥 Vérification de la santé des services..."
	@echo ""
	@echo "Backend (health endpoint):"
	@curl -s http://localhost:8000/api/health | python -m json.tool || echo "❌ Backend non accessible"
	@echo ""
	@echo "LiteLLM Proxy (test gpt-4o-mini):"
	@curl -s -X POST http://localhost:4000/chat/completions \
		-H "Content-Type: application/json" \
		-d '{"model":"gpt-4o-mini","messages":[{"role":"user","content":"ping"}],"max_tokens":5}' \
		| python -m json.tool || echo "❌ LiteLLM Proxy non accessible"

# Nettoyer
clean:
	@echo "🧹 Nettoyage des containers et volumes..."
	docker-compose down -v
	@echo "✅ Nettoyage terminé"

# Rebuild complet
rebuild: clean build up
	@echo "✅ Rebuild complet terminé"
