@echo off
chcp 65001 > nul
REM Script tout-en-un pour envoyer les invitations beta
REM Double-cliquez pour lancer

echo.
echo ╔═══════════════════════════════════════════════════╗
echo ║     ÉMERGENCE - Envoi d'invitations Beta          ║
echo ╚═══════════════════════════════════════════════════╝
echo.

REM Configuration des variables d'environnement
echo [1/4] Configuration de l'email...
set EMAIL_ENABLED=1
set SMTP_HOST=smtp.gmail.com
set SMTP_PORT=587
set SMTP_USER=gonzalefernando@gmail.com
set SMTP_PASSWORD=dfshbvvsmyqrfkja
set SMTP_FROM_EMAIL=gonzalefernando@gmail.com
echo ✓ Email configuré

echo.
echo [2/4] Vérification du backend...
echo.
echo IMPORTANT: Le backend doit être démarré.
echo.
echo Si ce n'est pas déjà fait, ouvrez un autre terminal et lancez:
echo   npm run backend
echo.
echo Ou pour utiliser l'environnement virtuel:
echo   npm run start:venv
echo.
pause

echo.
echo [3/4] Ouverture de l'interface web...
start "" "beta_invitations.html"
echo ✓ Interface ouverte dans votre navigateur

echo.
echo [4/4] Instructions:
echo.
echo Dans l'interface qui vient de s'ouvrir:
echo.
echo   1. Cliquez sur "📋 Charger l'allowlist"
echo      → Tous les emails s'afficheront automatiquement
echo.
echo   2. Cliquez sur "🚀 Envoyer les invitations"
echo      → Confirmez l'envoi
echo.
echo   3. Consultez les résultats!
echo      → Nombre d'emails envoyés / échoués
echo.
echo.
echo ═══════════════════════════════════════════════════
echo  Besoin d'aide ?
echo  📖 Consultez: COMMENT_ENVOYER_INVITATIONS.md
echo  📧 Contact: gonzalefernando@gmail.com
echo ═══════════════════════════════════════════════════
echo.
echo Appuyez sur une touche pour fermer cette fenêtre...
pause > nul
