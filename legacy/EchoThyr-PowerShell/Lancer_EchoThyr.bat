@echo off
REM ===================================================================
REM Lanceur automatique pour le script EchoThyr.ps1
REM Double-cliquez sur ce fichier pour demarrer le monitoring
REM ===================================================================

echo.
echo ========================================
echo   LANCEMENT ECHOTHYR MONITOR
echo ========================================
echo.

REM Change le repertoire vers le dossier du script
cd /d "%~dp0"

REM Lance le script PowerShell avec les permissions necessaires
powershell.exe -ExecutionPolicy Bypass -NoProfile -File "%~dp0EchoThyr.ps1"

REM Si le script s'arrete, attendre avant de fermer la fenetre
echo.
echo ========================================
echo   Script arrete
echo ========================================
echo.
pause
