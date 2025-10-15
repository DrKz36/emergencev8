@echo off
echo ========================================
echo Demarrage validation memoire Phase 3
echo ========================================

REM Charger les variables d'environnement
set AUTH_DEV_MODE=1
set CONCEPT_RECALL_METRICS_ENABLED=true
set AUTH_ADMIN_EMAILS=test@example.com
set AUTH_DEV_DEFAULT_EMAIL=test@example.com

echo.
echo Configuration:
echo - AUTH_DEV_MODE=%AUTH_DEV_MODE%
echo - CONCEPT_RECALL_METRICS_ENABLED=%CONCEPT_RECALL_METRICS_ENABLED%
echo.

REM Demarrer le serveur en arriere-plan
echo Demarrage du serveur backend...
start /B cmd /c "cd src\backend && python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000 > ..\..\logs\backend.log 2>&1"

REM Attendre que le serveur demarre
echo Attente du demarrage du serveur...
timeout /t 10 /nobreak > nul

REM Verifier que le serveur repond
echo Verification de l'etat du serveur...
curl -s http://127.0.0.1:8000/api/health
echo.

REM Executer les tests de validation
echo.
echo Execution de la suite de validation...
cd tests
python memory_validation_automated.py

REM Sauvegarder le code de retour
set VALIDATION_EXIT_CODE=%ERRORLEVEL%

echo.
echo ========================================
echo Validation terminee (code: %VALIDATION_EXIT_CODE%)
echo ========================================

REM Retourner au repertoire racine
cd ..

exit /b %VALIDATION_EXIT_CODE%
