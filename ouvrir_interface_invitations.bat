@echo off
REM Script pour ouvrir facilement l'interface d'envoi des invitations beta
REM Double-cliquez sur ce fichier pour lancer l'interface

echo.
echo ========================================
echo   EMERGENCE - Invitations Beta
echo ========================================
echo.
echo Ouverture de l'interface web...
echo.

REM Ouvrir l'interface dans le navigateur par defaut
start "" "beta_invitations.html"

echo.
echo Interface ouverte dans votre navigateur!
echo.
echo IMPORTANT: Le backend doit etre demarre.
echo Si ce n'est pas le cas, executez:
echo   npm run backend
echo.
echo Appuyez sur une touche pour fermer cette fenetre...
pause > nul
