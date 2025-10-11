@echo off
REM Emergence V8 - Monitoring Stack Start Script (Windows)
REM This script starts the complete monitoring stack (Prometheus + Grafana + AlertManager)

echo ============================================
echo    Emergence V8 - Monitoring Stack
echo ============================================
echo.

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo Error: Docker is not running!
    echo Please start Docker Desktop and try again.
    pause
    exit /b 1
)

echo Docker is running
echo.

REM Check if docker-compose is available
docker-compose version >nul 2>&1
if errorlevel 1 (
    echo Error: docker-compose is not installed!
    echo Please install docker-compose and try again.
    pause
    exit /b 1
)

echo docker-compose is available
echo.

REM Create necessary directories
echo Creating necessary directories...
if not exist "prometheus\alerts" mkdir "prometheus\alerts"
if not exist "grafana\provisioning\datasources" mkdir "grafana\provisioning\datasources"
if not exist "grafana\provisioning\dashboards" mkdir "grafana\provisioning\dashboards"
if not exist "grafana\dashboards" mkdir "grafana\dashboards"
if not exist "alertmanager" mkdir "alertmanager"
echo Directories created
echo.

REM Start monitoring stack
echo Starting monitoring stack...
docker-compose up -d

if errorlevel 1 (
    echo.
    echo Error: Failed to start monitoring stack
    echo Check the error message above for details
    pause
    exit /b 1
)

echo.
echo Waiting for services to be ready...
timeout /t 5 /nobreak >nul

REM Check service status
echo.
echo Service Status:
echo ====================
docker-compose ps

echo.
echo Monitoring stack is ready!
echo.
echo Access URLs:
echo    * Prometheus:   http://localhost:9090
echo    * Grafana:      http://localhost:3000
echo    * AlertManager: http://localhost:9093
echo.
echo Grafana Credentials:
echo    Username: admin
echo    Password: emergence2025
echo.
echo To view logs:
echo    docker-compose logs -f
echo.
echo To stop the stack:
echo    docker-compose down
echo.
echo WARNING: Don't forget to enable metrics in your backend:
echo    set CONCEPT_RECALL_METRICS_ENABLED=true
echo.
echo ============================================
echo.

pause
