#!/bin/bash

# Emergence V8 - Monitoring Stack Start Script
# This script starts the complete monitoring stack (Prometheus + Grafana + AlertManager)

set -e

echo "============================================"
echo "   Emergence V8 - Monitoring Stack"
echo "============================================"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running!"
    echo "Please start Docker and try again."
    exit 1
fi

echo "✅ Docker is running"
echo ""

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Error: docker-compose is not installed!"
    echo "Please install docker-compose and try again."
    exit 1
fi

echo "✅ docker-compose is available"
echo ""

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p prometheus/alerts
mkdir -p grafana/provisioning/datasources
mkdir -p grafana/provisioning/dashboards
mkdir -p grafana/dashboards
mkdir -p alertmanager
echo "✅ Directories created"
echo ""

# Check if monitoring stack is already running
if docker-compose ps | grep -q "Up"; then
    echo "⚠️  Monitoring stack is already running"
    echo ""
    read -p "Do you want to restart it? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🔄 Restarting monitoring stack..."
        docker-compose down
        docker-compose up -d
    else
        echo "Keeping current stack running"
    fi
else
    echo "🚀 Starting monitoring stack..."
    docker-compose up -d
fi

echo ""
echo "⏳ Waiting for services to be ready..."
sleep 5

# Check service status
echo ""
echo "📊 Service Status:"
echo "===================="
docker-compose ps

echo ""
echo "✅ Monitoring stack is ready!"
echo ""
echo "🌐 Access URLs:"
echo "   • Prometheus:  http://localhost:9090"
echo "   • Grafana:     http://localhost:3000"
echo "   • AlertManager: http://localhost:9093"
echo ""
echo "🔐 Grafana Credentials:"
echo "   Username: admin"
echo "   Password: emergence2025"
echo ""
echo "📈 To view logs:"
echo "   docker-compose logs -f"
echo ""
echo "🛑 To stop the stack:"
echo "   docker-compose down"
echo ""
echo "⚠️  Don't forget to enable metrics in your backend:"
echo "   export CONCEPT_RECALL_METRICS_ENABLED=true"
echo ""
echo "============================================"
